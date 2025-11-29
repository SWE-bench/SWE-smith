import argparse

import swesmith.profiles.python  # noqa: F401
import shutil
import tempfile

from swesmith.profiles import registry


def _resolve_profile(repo_key: str):
    try:
        return registry.get(repo_key)
    except KeyError:
        matches = [
            key for key in registry.keys()
            if repo_key in key or repo_key.replace("/", "__") in key
        ]
        if not matches:
            raise
        return registry.get(matches[0])


def verify_mirror(repo: str):
    rp = _resolve_profile(repo)
    print(f"Verifying access to {rp.mirror_name}")
    if not rp._mirror_exists():
        raise RuntimeError(f"Mirror {rp.mirror_name} is not accessible via GitHub API.")
    tmp_dir = tempfile.mkdtemp(prefix="mirror_check_")
    try:
        rp.clone(dest=f"{tmp_dir}/{rp.repo_name}")
        print("Mirror access verified via clone.")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create or update mirror repositories for SWE-smith."
    )
    parser.add_argument(
        "--repo",
        default="pylint-dev__astroid.b114f6b5",
        help="Repo key registered in swesmith profiles (e.g., owner__repo.commit).",
    )
    args = parser.parse_args()
    verify_mirror(args.repo)

