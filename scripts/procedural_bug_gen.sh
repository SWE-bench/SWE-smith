#!/bin/bash

# Java Procedural Bug Generation Script for SWE-smith
# Usage: ./scripts/procedural_bug_gen.sh [REPO_NAME] [MAX_BUGS] [--new-only]
# Example: ./scripts/procedural_bug_gen.sh google/gson 200
# Example (new modifiers only): ./scripts/procedural_bug_gen.sh google/gson 50 --new-only
# Default: google/gson with 100 bugs per modifier

set -e  # Exit on error

# On Windows WSL with Docker Desktop, connect to Windows Docker daemon
# On macOS, need to set DOCKER_HOST, otherwise docker APIClient will fail
if [[ "$OSTYPE" == "linux-gnu"* ]] && [[ -f /proc/version ]] && grep -q Microsoft /proc/version; then
    # WSL environment - connect to Windows Docker Desktop
    export DOCKER_HOST=tcp://localhost:2375
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - use Unix socket
    export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock
fi

# Clean up stale containers from previous run
docker ps -a | grep swesmith.val | awk '{print $1}' | xargs docker rm -f 2>/dev/null || true

REPO_NAME="${1:-google/gson}"
MAX_BUGS="${2:-5}"
NEW_ONLY_FLAG=""

# Check if --new-only flag is present
if [[ "$3" == "--new-only" ]] || [[ "$2" == "--new-only" ]]; then
    NEW_ONLY_FLAG="--new-only"
    # If --new-only was in position 2, reset MAX_BUGS to default
    if [[ "$2" == "--new-only" ]]; then
        MAX_BUGS="100"
    fi
fi

export REPO_OWNER=$(echo "$REPO_NAME" | cut -d'/' -f1)
export REPO_NAME_ONLY=$(echo "$REPO_NAME" | cut -d'/' -f2)

# Auto-detect REPO_ID by finding matching profile in registry
REPO_ID=$(python << 'PYSCRIPT'
from swesmith.profiles import registry
import sys
import os

# Get repo info from environment
owner = os.environ.get('REPO_OWNER', '')
repo = os.environ.get('REPO_NAME_ONLY', '')
target = f'{owner}/{repo}'

# Try to find a profile matching owner/repo
for key in registry.keys():
    try:
        profile = registry.get(key)
        if f'{profile.owner}/{profile.repo}' == target:
            print(profile.mirror_name)
            sys.exit(0)
    except Exception:
        continue

print(f'Error: No profile found for {target}', file=sys.stderr)
sys.exit(1)
PYSCRIPT
)

if [ $? -ne 0 ]; then
    echo "Error: No profile registered for $REPO_NAME"
    echo "Available profiles can be listed with: python -c 'from swesmith.profiles import registry; print(list(registry.keys()))'"
    exit 1
fi

# Get the Docker image name from the profile registry
DOCKER_IMAGE=$(python -c "from swesmith.profiles import registry; print(registry.get('$REPO_ID').image_name)")

echo "=========================================="
echo "Java Procedural Bug Generation for SWE-smith"
echo "=========================================="
echo "Repository: $REPO_NAME"
echo "Repository ID: $REPO_ID"
echo "Max bugs per modifier: $MAX_BUGS"
echo "Docker image: $DOCKER_IMAGE"
echo "=========================================="
echo ""

echo "[Step 1/4] Verifying Docker image..."
if docker image inspect "$DOCKER_IMAGE" > /dev/null 2>&1; then
    echo "✓ Docker image found: $DOCKER_IMAGE"
else
    echo "✗ Docker image not found: $DOCKER_IMAGE"
    echo "Attempting to pull the image..."
    if docker pull "$DOCKER_IMAGE" 2>/dev/null; then
        echo "✓ Successfully pulled Docker image"
    else
        echo "Image not available on Docker Hub. Building locally..."
        python -m swesmith.build_repo.create_images --profiles "$DOCKER_IMAGE" -y || {
            echo "Error: Failed to build Docker image."
        exit 1
    }
    fi
fi
echo ""

echo "[Step 2/4] Generating bugs procedurally..."
if [ -n "$NEW_ONLY_FLAG" ]; then
    echo "Running: python -m swesmith.bug_gen.procedural.generate $REPO_ID --max_bugs $MAX_BUGS $NEW_ONLY_FLAG"
    python -m swesmith.bug_gen.procedural.generate "$REPO_ID" --max_bugs "$MAX_BUGS" "$NEW_ONLY_FLAG" || {
        echo "Error: Bug generation failed."
        exit 1
    }
else
echo "Running: python -m swesmith.bug_gen.procedural.generate $REPO_ID --max_bugs $MAX_BUGS"
python -m swesmith.bug_gen.procedural.generate "$REPO_ID" --max_bugs "$MAX_BUGS" || {
    echo "Error: Bug generation failed."
    exit 1
}
fi
echo ""

echo "[Step 3/4] Collecting all patches..."
PATCHES_FILE="logs/bug_gen/${REPO_ID}_all_patches.json"
echo "Running: python -m swesmith.bug_gen.collect_patches logs/bug_gen/$REPO_ID"
python -m swesmith.bug_gen.collect_patches "logs/bug_gen/$REPO_ID" || {
    echo "Error: Patch collection failed."
    exit 1
}

if [ -f "$PATCHES_FILE" ]; then
    NUM_PATCHES=$(jq length "$PATCHES_FILE")
    echo "✓ Collected $NUM_PATCHES patches to $PATCHES_FILE"
else
    echo "✗ Patches file not found: $PATCHES_FILE"
    exit 1
fi
echo ""

 # Determine number of CPU cores for parallel validation
 if command -v nproc >/dev/null 2>&1; then
     NUM_CORES=$(nproc)
 elif command -v sysctl >/dev/null 2>&1; then
     NUM_CORES=$(sysctl -n hw.ncpu || echo 8)
 else
     NUM_CORES=8
 fi

echo "[Step 4/4] Running validation..."
echo "Running: python -m swesmith.harness.valid $PATCHES_FILE -w 12"
python -m swesmith.harness.valid "$PATCHES_FILE" -w "$NUM_CORES" || {
    echo "Warning: Validation encountered errors but may have partial results."
}
echo ""

echo "=========================================="
echo "Java Bug Generation Complete!"
echo "=========================================="
echo "Generated patches: $PATCHES_FILE"
echo "Validation results: logs/run_validation/$REPO_ID/"
echo ""
echo "Next steps:"
echo "  1. Review validation results in logs/run_validation/$REPO_ID/"
echo "  2. Analyze Java bugs with: python scripts/analyze_bugs.py $REPO_ID"
echo "  3. Collect validated instances: python -m swesmith.harness.gather logs/run_validation/$REPO_ID"
echo "  4. Check generated .diff files in logs/bug_gen/$REPO_ID/"
echo "=========================================="
