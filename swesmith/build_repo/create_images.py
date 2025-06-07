"""
Purpose: Automated construction of Docker images for a Python repository at a specific commit.

Usage: python -m swesmith.build_repo.create_images --force-rebuild --max-workers 4
"""

import argparse
import docker
import traceback

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor, as_completed
from swesmith.build_repo.create_mirror_repo import create_mirror_repo
from swebench.harness.constants import (
    BASE_IMAGE_BUILD_DIR,
    ENV_IMAGE_BUILD_DIR,
    DOCKER_WORKDIR,
)
from swebench.harness.docker_build import (
    build_image,
    remove_image,
    BuildImageError,
)
from swebench.harness.dockerfiles import (
    get_dockerfile_base,
    get_dockerfile_env,
)
from swesmith.constants import (
    _DOCKERFILE_BASE_EXTENDED,
    CONDA_VERSION,
    ENV_NAME,
    MAP_REPO_TO_SPECS,
    ORG_NAME,
    UBUNTU_VERSION,
)
from swesmith.utils import (
    get_arch_and_platform,
    get_env_yml_path,
    get_repo_commit_from_image_name,
    get_image_name,
    get_repo_name,
)
from tqdm import tqdm


def get_repo_setup_script(repo: str, commit: str, org: str):
    """
    Create a setup script for a repository at a specific commit.
    """
    # Get environment.yml path
    path_to_reqs = "swesmith_environment.yml"
    env_yml_path = get_env_yml_path(repo, commit)

    # Construct setup script
    HEREDOC_DELIMITER = "EOF_59812759871"
    specs = MAP_REPO_TO_SPECS[repo][commit]
    reqs = open(env_yml_path).read()

    repo_name = get_repo_name(repo, commit)
    setup_commands = [
        "#!/bin/bash",
        "set -euxo pipefail",
        f"git clone -o origin https://github.com/{org}/{repo_name} {DOCKER_WORKDIR}",
        f"cd {DOCKER_WORKDIR}",
        "source /opt/miniconda3/bin/activate",
        f"cat <<'{HEREDOC_DELIMITER}' > {path_to_reqs}\n{reqs}\n{HEREDOC_DELIMITER}",
        f"conda env create --file {path_to_reqs}",
        f"conda activate {ENV_NAME} && conda install python={specs['python']} -y",
        f"rm {path_to_reqs}",
        f"conda activate {ENV_NAME}",
        'echo "Current environment: $CONDA_DEFAULT_ENV"',
    ] + specs["install"]
    return "\n".join(setup_commands) + "\n"


def build_base_image(
    client: docker.DockerClient,
    force_rebuild: bool = False,
):
    """
    Build the base image for the current architecture and platform.
    """
    arch, platform = get_arch_and_platform()
    base_dockerfile = (
        get_dockerfile_base(
            platform,
            arch,
            "py",
            ubuntu_version=UBUNTU_VERSION,
            conda_version=CONDA_VERSION,
        )
        + _DOCKERFILE_BASE_EXTENDED
    )
    base_image_key = f"swesmith.{arch}"
    try:
        # Check if the base image already exists
        client.images.get(base_image_key)
        if force_rebuild:
            # Remove the base image if it exists and force rebuild is enabled
            remove_image(client, base_image_key, "quiet")
        else:
            print(f"Base image {base_image_key} already exists, skipping build.")
            return base_image_key
    except docker.errors.ImageNotFound:
        pass
    # Build the base image (if it does not exist or force rebuild is enabled)
    print(f"Building base image ({base_image_key})")
    build_image(
        image_name=base_image_key,
        setup_scripts={},
        dockerfile=base_dockerfile,
        platform=platform,
        client=client,
        build_dir=BASE_IMAGE_BUILD_DIR / base_image_key,
    )
    return base_image_key


def build_repo_image(
    image_name: str,
    setup_scripts: dict,
    dockerfile: str,
    platform: str,
    client: docker.DockerClient,
    build_dir: str,
    org: str,
):
    repo, commit = get_repo_commit_from_image_name(image_name)
    create_mirror_repo(repo, commit, org)
    build_image(
        image_name=image_name,
        setup_scripts=setup_scripts,
        dockerfile=dockerfile,
        platform=platform,
        client=client,
        build_dir=build_dir,
    )


def build_repo_images(
    client: docker.DockerClient,
    force_rebuild: bool = False,
    max_workers: int = 4,
    repos: str = None,
    org: str = ORG_NAME,
    proceed: bool = False,
):
    """
    Build Docker images for each repository at a specific commit(s).
    """
    # Construct base image
    arch, platform = get_arch_and_platform()
    base_image_key = build_base_image(client, force_rebuild)
    env_dockerfile = get_dockerfile_env(
        platform, arch, "py", base_image_key=base_image_key
    )

    # Filter out repositories
    map_repo_to_specs = deepcopy(MAP_REPO_TO_SPECS)
    if repos is not None:
        repos = repos.split()
        map_repo_to_specs = {
            repo: specs for repo, specs in map_repo_to_specs.items() if repo in repos
        }
        if not map_repo_to_specs:
            print("No repositories to build.")
            return None, None

    # Construct repo level build scripts
    repo_build_scripts = {}
    for repo, specs in map_repo_to_specs.items():
        for commit, spec in specs.items():
            image_name = get_image_name(repo, commit)
            image_exists = False
            if not force_rebuild:
                try:
                    client.images.get(image_name)
                    image_exists = True
                except docker.errors.ImageNotFound:
                    pass
            if not image_exists:
                repo_build_scripts[image_name] = {
                    "setup_script": get_repo_setup_script(repo, commit, org),
                    "dockerfile": env_dockerfile,
                    "platform": platform,
                }
    if not repo_build_scripts:
        print("No images to build.")
        return None, None

    print(f"Total repo images to build: {len(repo_build_scripts)}")
    for image_name in repo_build_scripts:
        print(f"- {image_name}")

    if not proceed:
        proceed = input("Proceed with building images? (y/n): ").lower() == "y"
    if not proceed:
        return None, None

    # Build repo images in parallel
    successful, failed = list(), list()
    with tqdm(
        total=len(repo_build_scripts), smoothing=0, desc="Building environment images"
    ) as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a future for each image to build
            futures = {
                executor.submit(
                    build_repo_image,
                    image_name,
                    {"setup_env.sh": config["setup_script"]},
                    config["dockerfile"],
                    config["platform"],
                    client,
                    ENV_IMAGE_BUILD_DIR / image_name,
                    org,
                ): image_name
                for image_name, config in repo_build_scripts.items()
            }

            # Wait for each future to complete
            for future in as_completed(futures):
                pbar.update(1)
                try:
                    # Update progress bar, check if image built successfully
                    future.result()
                    successful.append(futures[future])
                except BuildImageError as e:
                    print(f"BuildImageError {e.image_name}")
                    traceback.print_exc()
                    failed.append(futures[future])
                    continue
                except Exception:
                    print("Error building image")
                    traceback.print_exc()
                    failed.append(futures[future])
                    continue

    # Show how many images failed to build
    if len(failed) == 0:
        print("All environment images built successfully.")
    else:
        print(f"{len(failed)} environment images failed to build.")

    # Return the list of (un)successfuly built images
    return successful, failed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-rebuild", action="store_true")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument(
        "--repos",
        type=str,
        default=None,
        help="List of space-separated repositories to build",
    )
    parser.add_argument(
        "--org",
        type=str,
        default=ORG_NAME,
        help="GitHub organization to create repo for (default: 'swesmith')",
    )
    parser.add_argument(
        "-y", "--proceed", action="store_true", help="Proceed without confirmation"
    )
    args = parser.parse_args()

    client = docker.from_env()
    build_repo_images(client, **vars(args))


if __name__ == "__main__":
    main()
