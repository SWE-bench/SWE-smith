#!/bin/bash

# This script comes in handy when you want to test building an image 
# for a specific NON-PYTHON repo when one builds the profile for it.

# TODO: Fill in the Github token
# export GITHUB_TOKEN=""

# TODO: Fill in the image name
image_name="richardzhuang0412/swesmith.x86_64.burntsushi_1776_rust-csv.da000888"

# TODO: Fill in the test command
test_cmd="cargo test --verbose"

# NOTE: The image name should be of the form:
#   <github_username>/swesmith.x86_64.<repo_owner>.<repo_name>.<commit_hash>
# The original script had an incorrect image name format (with _1776_ in it).

# Build the image
python -m swesmith.build_repo.create_images --profiles $image_name -y

# Test the docker image by running the test command
docker run -it --rm $image_name $test_cmd