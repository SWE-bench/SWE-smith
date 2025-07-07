"""
Purpose: Automated construction of Docker images for repositories using profile registry.

Usage: python -m swesmith.build_repo.create_images --max-workers 4
"""

import argparse
import docker
import traceback
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from swesmith.profiles import global_registry


def build_profile_image(profile):
    """
    Build a Docker image for a specific profile.

    Args:
        profile: A RepoProfile instance

    Returns:
        tuple: (profile_name, success: bool, error_message: str)
    """
    try:
        profile.create_mirror()
        profile.build_image()
        return (profile.image_name, True, None)
    except Exception as e:
        error_msg = f"Error building {profile.image_name}: {str(e)}"
        return (profile.image_name, False, error_msg)


def build_all_images(workers=4, profile_filter=None, proceed=False):
    """
    Build Docker images for all registered profiles in parallel.

    Args:
        workers: Maximum number of parallel workers
        profile_filter: Optional list of profile mirror names to filter by
        proceed: Whether to proceed without confirmation

    Returns:
        tuple: (successful_builds, failed_builds)
    """
    # Get all available profiles
    all_profiles = global_registry.values()

    # Remove environments that have already been built
    client = docker.from_env()

    # Filter out profiles that already have images built
    profiles_to_build = []
    for profile in all_profiles:
        try:
            # Check if image already exists
            client.images.get(profile.image_name)
        except docker.errors.ImageNotFound:
            profiles_to_build.append(profile)

    # Filter profiles if specified
    if profile_filter:
        filtered_profiles = []
        for profile in profiles_to_build:
            if profile.image_name in profile_filter:
                filtered_profiles.append(profile)
        profiles_to_build = filtered_profiles

    if not profiles_to_build:
        print("No profiles to build.")
        return [], []

    # Deduplicate profiles_to_build by image_name (more efficiently)
    profiles_to_build = list(
        OrderedDict(
            (profile.image_name, profile) for profile in profiles_to_build
        ).values()
    )

    print(f"Total profiles to build: {len(profiles_to_build)}")
    for profile in profiles_to_build:
        print(f"- {profile.image_name}")

    if not proceed:
        proceed = input("Proceed with building images? (y/n): ").lower() == "y"
    if not proceed:
        return [], []

    # Build images in parallel
    successful, failed = [], []

    with tqdm(
        total=len(profiles_to_build), smoothing=0, desc="Building environment images"
    ) as pbar:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all build tasks
            future_to_profile = {
                executor.submit(build_profile_image, profile): profile
                for profile in profiles_to_build
            }

            # Process completed tasks
            for future in as_completed(future_to_profile):
                pbar.update(1)
                profile_name, success, error_msg = future.result()

                if success:
                    successful.append(profile_name)
                else:
                    failed.append(profile_name)
                    if error_msg:
                        print(f"\n{error_msg}")
                        traceback.print_exc()

    # Show results
    if len(failed) == 0:
        print("All environment images built successfully.")
    else:
        print(f"{len(failed)} environment images failed to build.")

    return successful, failed


def main():
    parser = argparse.ArgumentParser(
        description="Build Docker images for all registered repository profiles"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Maximum number of parallel workers (default: 4)",
    )
    parser.add_argument(
        "--profiles",
        type=str,
        nargs="+",
        help="Specific profile mirror names to build (space-separated)",
    )
    parser.add_argument(
        "-y", "--proceed", action="store_true", help="Proceed without confirmation"
    )
    parser.add_argument(
        "--list-envs", action="store_true", help="List all available profiles and exit"
    )

    args = parser.parse_args()

    if args.list_envs:
        print("All execution environment Docker images:")
        for profile in global_registry.values():
            print(f"  {profile.image_name}")
        return

    successful, failed = build_all_images(
        workers=args.workers, profile_filter=args.profiles, proceed=args.proceed
    )

    if failed:
        print(f"- Failed builds: {failed}")
    if successful:
        print(f"- Successful builds: {len(successful)}")


if __name__ == "__main__":
    main()
