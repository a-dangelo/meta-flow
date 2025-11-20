# Development Scripts

This directory contains helper scripts for development and setup.

## `setup_dev.sh`

Automated development environment setup script.

**What it does:**
- Checks Python version (requires 3.9+)
- Creates `.venv` virtual environment
- Installs all dependencies from `requirements.txt`
- Creates necessary directories

**Usage:**
```bash
# From the project root
bash scripts/setup_dev.sh

# Then activate the environment
source .venv/bin/activate
```

**Manual alternative:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
