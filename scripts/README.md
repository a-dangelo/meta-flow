# Development Scripts

This directory contains helper scripts for development and Docker deployment.

## Service Management Scripts

### Interactive Launchers (Recommended)

#### `start.sh` - Interactive Service Launcher
Interactive menu to start Meta-Agent, Chatbot, or both services.

**Usage:**
```bash
bash scripts/start.sh
```

**Options:**
- Meta-Agent: Workflow generator (ports 3001, 8000)
- Chatbot: Interactive assistant (ports 3002, 8001)
- Both services: Run simultaneously

#### `stop.sh` - Interactive Service Stopper
Interactive menu to stop running services.

**Usage:**
```bash
bash scripts/stop.sh
```

### Direct Service Scripts

#### `meta-agent-start.sh` / `meta-agent-stop.sh`
Directly start/stop the meta-agent workflow generator.

**Usage:**
```bash
# Start meta-agent
bash scripts/meta-agent-start.sh

# Stop meta-agent
bash scripts/meta-agent-stop.sh
```

**Environment Variables:**
- `DOCKER_BUILD_NO_CACHE=1` - Force clean rebuild (uses more disk space)

**Ports:**
- Frontend: http://127.0.0.1:3001
- Backend: http://127.0.0.1:8000

#### `chatbot-start.sh` / `chatbot-stop.sh`
Directly start/stop the chatbot interactive assistant.

**Usage:**
```bash
# Start chatbot
bash scripts/chatbot-start.sh

# Stop chatbot
bash scripts/chatbot-stop.sh
```

**Environment Variables:**
- `DOCKER_BUILD_NO_CACHE=1` - Force clean rebuild (uses more disk space)

**Ports:**
- Frontend: http://127.0.0.1:3002
- Backend: http://127.0.0.1:8001

## Development Scripts

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
