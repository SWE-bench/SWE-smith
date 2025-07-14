#!/bin/bash
# Initialize conda for the current shell session
eval "$(conda shell.bash hook)"
conda create -n testbed python=3.10 -yq
conda activate testbed
pip install -e .
pip install pytest

# Set up bash to automatically activate testbed environment
echo "source /opt/miniconda3/etc/profile.d/conda.sh" >> /root/.bashrc
echo "conda activate testbed" >> /root/.bashrc