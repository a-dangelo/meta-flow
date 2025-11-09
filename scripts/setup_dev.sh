#!/bin/bash

# Setup script for meta-flow development environment

echo "Setting up meta-flow development environment..."

# Check if Python 3.9+ is installed
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.9+ is required (found $python_version)"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (.venv)..."
    python3 -m venv .venv --prompt venv
else
    echo "Virtual environment (.venv) already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Install package in editable mode
echo "Installing meta-flow in editable mode..."
pip install -e .

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p specs/examples
mkdir -p generated_agents

echo ""
echo "✓ Development environment setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "    source .venv/bin/activate"
echo ""
echo "To test the installation, run:"
echo "    python src/core/workflow_ast.py"
echo ""
echo "To run tests, use:"
echo "    pytest tests/ -v"