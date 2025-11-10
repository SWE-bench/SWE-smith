#!/bin/bash
set -e

echo "🔧 Java Procedural Bug Generation (Official Implementation via WSL)"
echo "========================================================================"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv_wsl" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv_wsl
fi

# Activate virtual environment
source venv_wsl/bin/activate

# Upgrade pip
# echo "⬆️  Upgrading pip..."
# pip install --upgrade pip

# Install core dependencies (skip problematic ones like sglang, modal)
echo ""
echo "📦 Installing core dependencies..."
echo "   This may take a few minutes..."
echo ""
pip install \
    libcst \
    datasets \
    ghapi \
    rich \
    tqdm \
    tiktoken \
    tree-sitter \
    tree-sitter-c \
    tree-sitter-cpp \
    tree-sitter-c-sharp \
    tree-sitter-go \
    tree-sitter-javascript \
    tree-sitter-java \
    tree-sitter-python \
    tree-sitter-ruby \
    tree-sitter-rust \
    unidiff \
    PyGithub \
    requests

# Install swebench (has resource module, but works in Linux)
echo ""
echo "📦 Installing swebench..."
pip install swebench 2>&1 || echo "⚠️  swebench installation had warnings (continuing anyway)"

# Add project to PYTHONPATH instead of editable install
export PYTHONPATH="/mnt/c/Users/PRIYANK/Stanford/SWE-smith:$PYTHONPATH"

echo ""
echo "✅ Environment ready!"
echo ""
echo "🐛 Running OFFICIAL procedural bug generation..."
echo "   Command: python3 -m swesmith.bug_gen.procedural.generate"
echo "   Repository: google__gson.dd2fe59c"
echo "   Max bugs: UNLIMITED (no limit)"
echo "   Seed: 42"
echo ""

# Run the OFFICIAL generate script
# Note: Use repo_name format: owner__repo.commit[:8]
# max_bugs=-1 means no limit (generate for all candidates)
python3 -m swesmith.bug_gen.procedural.generate google__gson.dd2fe59c --max_bugs -1 --seed 42

echo ""
echo "✅ Complete! Check logs/bug_gen/google__gson.dd2fe59c/ for results"
