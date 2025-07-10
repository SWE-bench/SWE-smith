#!/bin/bash

# Initialize conda for the current shell session
eval "$(conda shell.bash hook)"

conda create -n testbed python=3.10 -yq
conda activate testbed
pip install -e .
pip install pytest
