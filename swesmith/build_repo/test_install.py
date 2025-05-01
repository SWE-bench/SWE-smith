"""
Purpose: Test out whether a set of installation commands works for a given repository at a specific commit.

Usage: python -m swesmith.build_repo.test_install owner/repo --commit <commit>
"""

import argparse
import os
import subprocess

from swesmith.constants import ENV_NAME, LOG_DIR_ENV_RECORDS


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
    env_list = subprocess.run(
        "conda env list", check=True, shell=True, text=True, capture_output=True
    ).stdout
    if env_name is not None and env_name in env_list:
        subprocess.run(
            f"conda env remove -n {env_name} -y",
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("> Removed conda environment")


def main(
    repo: str,
    install_script: str,
    commit: str,
    no_pytest: bool,
    python_version: str,
    no_cleanup: bool,
):
    print(f"> Building image for {repo} at commit {commit or 'latest'}")
    repo_name = repo.split("/")[-1]

    assert os.path.exists(
        install_script
    ), f"Installation script {install_script} does not exist"
    assert install_script.endswith(".sh"), "Installation script must be a bash script"
    install_script = os.path.abspath(install_script)

    try:
        # Shallow clone repository at the specified commit
        if not os.path.exists(repo_name):
            subprocess.run(
                f"git clone git@github.com:{repo}.git",
                check=True,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        os.chdir(repo_name)
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
        print(f"> Cloned {repo} at commit {commit}")

        # Construct installation script
        installation_cmds = [
            ". /opt/miniconda3/bin/activate",
            f"conda create -n {ENV_NAME} python={python_version} -yq",
            f"conda activate {ENV_NAME}",
            f". {install_script}",
        ]
        if not no_pytest:
            installation_cmds.append("pip install pytest")

        # Run installation
        print("> Installing repo...")
        temp = "\n- ".join(installation_cmds)
        print(f"> Script:{temp}\n")
        subprocess.run(" && ".join(installation_cmds), check=True, shell=True)
        print("> Successfully installed repo")

        # Check that pytest is installed. If not, install it.
        if not no_pytest:
            subprocess.run("pip install pytest", check=True, shell=True)
            print("> Installed pytest")

        # If installation succeeded, export the conda environment + record install script
        os.chdir("..")
        env_yml = f"sweenv_{repo.replace('/', '__')}_{commit}.yml"
        subprocess.run(
            f"conda env export -n {ENV_NAME} > {env_yml}",
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Edit env.yml such that name of package is excluded from `pip`
        with open(env_yml, "r") as f:
            lines = f.readlines()
            with open(env_yml, "w") as f:
                for line in lines:
                    if line.strip().startswith(f"- {repo_name}=="):
                        continue
                    f.write(line)

        subprocess.run(
            f"mv {env_yml} {LOG_DIR_ENV_RECORDS}",
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with open(f"{LOG_DIR_ENV_RECORDS}/{env_yml.replace('.yml', '.sh')}", "w") as f:
            f.write(
                "\n".join(
                    [
                        "#!/bin/bash\n",
                        f"git clone git@github.com:{repo}.git",
                        f"git checkout {commit}",
                    ]
                    + installation_cmds
                )
            )
        print(f"> Exported conda environment to {LOG_DIR_ENV_RECORDS}/{env_yml}")
    except Exception as e:
        print(f"> Installation procedure failed: {e}")
    finally:
        if not no_cleanup:
            cleanup(repo_name, ENV_NAME)


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
        "--commit",
        type=str,
        help="Commit hash to build the image at (default: latest)",
        default="latest",
    )
    parser.add_argument(
        "--no_pytest", action="store_true", help="Do not run pytest after installation"
    )
    parser.add_argument(
        "--python_version",
        type=str,
        help="Python version to use for the environment",
        default="3.10",
    )
    parser.add_argument(
        "--no_cleanup",
        action="store_true",
        help="Do not remove the repository and conda environment after installation",
    )

    args = parser.parse_args()
    main(**vars(args))
