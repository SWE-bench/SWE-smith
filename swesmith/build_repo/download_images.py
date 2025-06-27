"""
Purpose: Standalone script to download all SWEFT images

Usage: python -m swesmith.build_repo.download_images
"""

import argparse
import docker
import os
import json
import requests

DOCKER_ORG = "jyangballin"
TAG = "latest"


def get_docker_hub_login():
    docker_config_path = os.path.expanduser("~/.docker/config.json")

    try:
        with open(docker_config_path, "r") as config_file:
            docker_config = json.load(config_file)

        auths = docker_config.get("auths", {})
        docker_hub = auths.get("https://index.docker.io/v1/")

        if not docker_hub:
            raise Exception(
                "Docker Hub credentials not found. Please log in using 'docker login'."
            )

        # The token is encoded in Base64 (username:password), decode it
        from base64 import b64decode

        auth_token = docker_hub.get("auth")
        if not auth_token:
            raise Exception("No auth token found in Docker config.")

        decoded_auth = b64decode(auth_token).decode("utf-8")
        username, password = decoded_auth.split(":", 1)
        return username, password

    except FileNotFoundError:
        raise Exception(
            "Docker config file not found. Have you logged in using 'docker login'?"
        )
    except Exception as e:
        raise Exception(f"Error retrieving Docker Hub token: {e}")


def get_dockerhub_token(username, password):
    """Get DockerHub authentication token"""
    auth_url = "https://hub.docker.com/v2/users/login"
    auth_data = {"username": username, "password": password}
    response = requests.post(auth_url, json=auth_data)
    response.raise_for_status()
    return response.json()["token"]


def get_docker_repositories(username, token):
    url = f"https://hub.docker.com/v2/repositories/{username}/"
    headers = {"Authorization": f"Bearer {token}"}

    repositories = []
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(
                f"Failed to fetch repositories: {response.status_code}, {response.text}"
            )

        data = response.json()
        repositories.extend(data.get("results", []))
        url = data.get("next")  # Get the next page URL, if any

    return repositories


def main(repo: str, proceed: bool = True):
    username, password = get_docker_hub_login()
    token = get_dockerhub_token(username, password)
    client = docker.from_env()

    # Get list of swesmith repositories
    repos = get_docker_repositories(DOCKER_ORG, token)
    repos = [r for r in repos if r["name"].startswith("swesmith")]
    if repo:
        repos = [
            r
            for r in repos
            if repo.replace("__", "_1776_") in r["name"]
            or repo in r["name"]
            or repo.replace("/", "_1776_") in r["name"]
        ]
        if len(repos) == 0:
            print(f"Could not find image for {repo}, exiting...")
            return

    print(f"Found {len(repos)} environments:")
    for idx, r in enumerate(repos):
        print("-", r["name"])
        if idx == 4:
            print(f"(+ {len(repos) - 5} more...)")
            break
    if not proceed and input("Proceed with downloading images? (y/n): ").lower() != "y":
        return

    # Download images
    for r in repos:
        print(f"Downloading {r['name']}...")
        client.images.pull(f"{DOCKER_ORG}/{r['name']}:{TAG}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=str, help="Repository name", default=None)
    parser.add_argument(
        "-y",
        "--proceed",
        action="store_true",
        help="Proceed with downloading images",
    )
    args = parser.parse_args()
    main(**vars(args))
