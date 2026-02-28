"""
Purpose: Test out whether a set of installation commands works for a given repository at a specific commit.

Usage: python -m swesmith.build_repo.try_install_py owner/repo --commit <commit>
"""

import argparse
import os
import subprocess

from swesmith.constants import ENV_NAME
from swesmith.profiles.python import PythonProfile


DEFAULT_PROFILE_INSTALL_CMDS = ["python -m pip install -e ."]


def _profile_install_cmds(profile: PythonProfile) -> str | None:
    """
    Convert profile install_cmds to a single shell string for the install script.
    Skip if the profile uses the default editable install to avoid duplication.
    """
    if profile.install_cmds == DEFAULT_PROFILE_INSTALL_CMDS:
        return None
    return " && ".join(profile.install_cmds)


def _pytest_available(env: dict) -> bool:
    """Check if pytest is importable inside the target conda env."""
    check_cmd = (
        f"conda run -n {ENV_NAME} python - <<'PY'\n"
        "import importlib.util, sys\n"
        "sys.exit(0 if importlib.util.find_spec('pytest') else 1)\n"
        "PY"
    )
    result = subprocess.run(
        check_cmd,
        check=False,
        shell=True,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def cleanup(repo_name: str, env_name: str | None = None):
    if os.path.exists(repo_name):
        subprocess.run(
            f"rm -rf {repo_name}",
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("> Removed repository")
    # If env not found, skip removal
    if env_name is not None:
        try:
            env_list = subprocess.run(
                "conda env list", check=True, shell=True, text=True, capture_output=True
            ).stdout
            if env_name in env_list:
                subprocess.run(
                    f"conda env remove -n {env_name} -y",
                    check=True,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print("> Removed conda environment")
            else:
                print(f"> Environment '{env_name}' not found, skipping removal")
        except subprocess.CalledProcessError as e:
            print(
                f"> Warning: Failed to check/remove conda environment '{env_name}': {e}"
            )


def main(
    repo: str,
    install_script: str,
    commit: str,
    no_cleanup: bool,
    force: bool,
    python_version: str | None = None,
    smoke_cmd: str | None = None,
    skip_smoke: bool = False,
    extra_test_deps: str | None = None,
):
    print(f"> Building image for {repo} at commit {commit or 'latest'}")
    owner, repo = repo.split("/")
    p = PythonProfile()
    p.owner = owner
    p.repo = repo
    if python_version:
        p.python_version = python_version

    assert os.path.exists(install_script), (
        f"Installation script {install_script} does not exist"
    )
    assert install_script.endswith(".sh"), "Installation script must be a bash script"
    install_script = os.path.abspath(install_script)

    env = os.environ.copy()
    env["SWESMITH_PYTHON_VERSION"] = p.python_version
    profile_install_cmds = _profile_install_cmds(p)
    if profile_install_cmds:
        env["SWESMITH_PROFILE_INSTALL_CMDS"] = profile_install_cmds
    if extra_test_deps:
        env["SWESMITH_EXTRA_TEST_DEPS"] = extra_test_deps

    base_cwd = os.getcwd()
    try:
        # Shallow clone repository at the specified commit
        p._configure_ssh_env()
        if not os.path.exists(p.repo):
            subprocess.run(
                f"git clone {p._source_read_url}",
                check=True,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        os.chdir(p.repo)
        if commit != "latest":
            subprocess.run(
                f"git checkout {commit}",
                check=True,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            commit = subprocess.check_output(
                "git rev-parse HEAD", shell=True, text=True
            ).strip()
        print(f"> Cloned {p.repo} at commit {commit}")
        p.commit = commit

        if (
            os.path.exists(os.path.join("..", str(p._env_yml)))
            and not force
            and input(
                f"> Environment file {p._env_yml} already exists. Do you want to overwrite it? (y/n) "
            )
            != "y"
        ):
            raise Exception("(No Error) Terminating")

        # Run installation
        print("> Installing repo...")
        subprocess.run(
            ["bash", "-lc", f". {install_script}"],
            check=True,
            env=env,
        )
        print("> Successfully installed repo")

        if not skip_smoke:
            resolved_smoke_cmd = smoke_cmd
            if resolved_smoke_cmd is None and _pytest_available(env):
                resolved_smoke_cmd = "pytest -q --maxfail=1"
            if resolved_smoke_cmd:
                print(f"> Running smoke test: {resolved_smoke_cmd}")
                subprocess.run(
                    f"conda run -n {ENV_NAME} {resolved_smoke_cmd}",
                    check=True,
                    shell=True,
                    env=env,
                )
                print("> Smoke test passed")
            else:
                print("> Skipping smoke test (pytest not available)")

        # If installation succeeded, export the conda environment + record install script
        os.chdir("..")
        p._env_yml.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            f"conda env export -n {ENV_NAME} > {p._env_yml}",
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Edit env.yml such that name of package is excluded from `pip`
        with open(p._env_yml, "r") as f:
            lines = f.readlines()
        with open(p._env_yml, "w") as f:
            for line in lines:
                # Exclude the package by both repository name and lowercase package name
                if line.strip().startswith(f"- {p.repo}==") or line.strip().startswith(
                    f"- {p.repo.lower()}=="
                ):
                    continue
                f.write(line)

        with open(install_script) as install_f:
            install_lines = [
                l.strip("\n") for l in install_f.readlines() if len(l.strip()) > 0
            ]

        with open(str(p._env_yml).replace(".yml", ".sh"), "w") as f:
            f.write(
                "\n".join(
                    [
                        "#!/bin/bash\n",
                        f"git clone {p._source_read_url}",
                        f"git checkout {p.commit}",
                    ]
                    + install_lines
                )
                + "\n"
            )
        print(f"> Exported conda environment to {p._env_yml}")
    except Exception as e:
        print(f"> Installation procedure failed: {e}")
    finally:
        os.chdir(base_cwd)
        if not no_cleanup:
            cleanup(p.repo, ENV_NAME)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "repo", type=str, help="Repository name in the format of 'owner/repo'"
    )
    parser.add_argument(
        "install_script",
        type=str,
        help="Bash script with installation commands (e.g. install.sh)",
    )
    parser.add_argument(
        "-c",
        "--commit",
        type=str,
        help="Commit hash to build the image at (default: latest)",
        default="latest",
    )
    parser.add_argument(
        "--no_cleanup",
        action="store_true",
        help="Do not remove the repository and conda environment after installation",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force overwrite of existing conda environment file (if it exists)",
    )
    parser.add_argument(
        "-p",
        "--python-version",
        type=str,
        help="Python version to use when creating the conda environment",
        default=None,
    )
    parser.add_argument(
        "--smoke-cmd",
        type=str,
        help="Optional smoke test command to run inside the conda env (default: pytest -q --maxfail=1 if pytest is installed)",
        default=None,
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Skip running a smoke test after installation",
    )
    parser.add_argument(
        "--extra-test-deps",
        type=str,
        help="Additional space-separated pip packages to install as test deps (passed to install script)",
        default=None,
    )

    args = parser.parse_args()
    main(**vars(args))
