#!/bin/bash

# Try to find conda installation
if [ -f "/root/miniconda3/bin/activate" ]; then
    . /root/miniconda3/bin/activate
elif [ -f "/opt/miniconda3/bin/activate" ]; then
    . /opt/miniconda3/bin/activate
elif [ -f "$HOME/miniconda3/bin/activate" ]; then
    . $HOME/miniconda3/bin/activate
else
    echo "Error: Could not find conda installation"
    exit 1
fi
conda create -n testbed python=3.10 -yq
conda activate testbed
pip install -e .
pip install pytest
