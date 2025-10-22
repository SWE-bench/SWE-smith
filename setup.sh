# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv --python 3.12
source .venv/bin/activate
uv sync
