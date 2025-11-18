# Meta-Flow: Automated Workflow-to-Agent Code Generation

A system that transforms natural language workflow descriptions into executable Python agents using LLM-powered code generation.

## Project Overview

Meta-Flow operates in two phases:
- **Phase 1**: Converts text workflow specifications into structured JSON using LLM's.
- **Phase 2**: Transforms JSON into executable Python agents with error handling and credential management.

## Quick Start

Choose your preferred interface:
- **Web UI (Recommended)**: Visual interface with real-time generation → [Docker Deployment](#docker-deployment-recommended)
- **CLI**: Command-line interface for automation → [CLI Usage](#cli-usage)

### Quick CLI Example

```bash
# Clone repository
git clone https://github.com/yourusername/meta-flow.git
cd meta-flow

# Set up environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure API key
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env

# Generate an agent
python -m src.cli.complete_pipeline specs/examples/simple_sequential.txt
```

## Docker Deployment (Recommended)

The easiest way to run Meta-Flow is using Docker, which packages all dependencies and provides a production-ready environment.

### Docker Prerequisites

- **Docker Engine**: 20.10 or higher ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose**: 2.0 or higher (included with Docker Desktop)
- **LLM API Key**: At least one provider key (Anthropic, AIMLAPI, or Gemini)

### Docker Quick Start

```bash
# 1. Clone repository
git clone https://github.com/yourusername/meta-flow.git
cd meta-flow

# 2. Configure environment
cp .env.docker.example .env
# Edit .env and add your API key(s)

# 3. Start services (one command!)
./scripts/start.sh

# 4. Access the Web Interface
# 🌐 Open http://localhost:3001 in your browser
#
# You'll see the Meta-Flow Agent Generator with:
# - Workflow editor with syntax highlighting
# - Example templates to get started
# - Real-time generation pipeline
# - Generated Python code and JSON output
#
# API endpoints:
# - Backend: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

That's it! The web interface is now running. See the [Web Interface](#web-interface) section below for a detailed tour.

### Docker Commands

```bash
# Start services (with build)
./scripts/start.sh

# Start in background
./scripts/start.sh -d

# Start without rebuilding
./scripts/start.sh --no-build

# Stop services
./scripts/stop.sh

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart services
docker-compose restart

# Rebuild images (force clean build)
docker-compose build --no-cache
```

### Docker Troubleshooting

**Issue: Backend fails to start**
```bash
# Check logs
docker-compose logs backend

# Verify API key is set
docker-compose exec backend env | grep API_KEY

# Test health endpoint
curl http://localhost:8000/api/health
```

**Issue: Frontend can't connect to backend**
```bash
# Check if both services are healthy
docker-compose ps

# Test backend directly
curl http://localhost:8000/api/health

# Test frontend nginx
curl http://localhost:3001/health
```

**Issue: Port already in use**
```bash
# Change ports in docker-compose.yml:
# Frontend: Change "80:80" to "3000:80"
# Backend: Change "8000:8000" to "8001:8000"
```

## Web Interface

Meta-Flow provides a modern web interface that makes workflow creation intuitive and visual. The interface guides you through the entire process from specification to generated code.

### Features

- **Three-Panel Layout**: Editor, visualizer, and output panels for comprehensive workflow management
- **Syntax Highlighting**: Color-coded specifications and generated code for easy reading
- **Example Templates**: Pre-built workflow templates to get you started quickly
- **Real-Time Generation**: Watch the generation pipeline progress step-by-step
- **Dark Mode Support**: Easy on the eyes for extended usage
- **Multiple Output Formats**: View generated Python code, JSON AST, and metadata

### Main Editor Interface

![Meta-Flow Editor](artifacts/image_1.png)

The editor provides a clean interface for writing workflow specifications:
- **Workflow Type Selector**: Choose from sequential, conditional, parallel, or orchestrator patterns
- **Specification Editor**: Write natural language workflow descriptions with syntax highlighting
- **Generate Button**: One-click transformation to executable agent code
- **Backend Status**: Real-time connection status to ensure everything is working

### Generation Pipeline & Results

![Generation Pipeline](artifacts/image_2.png)

Watch your specification transform into code:
- **Progress Tracking**: Visual feedback for each pipeline stage
- **Generated Code**: Syntax-highlighted Python agent with proper structure
- **JSON AST Tab**: View the intermediate JSON representation
- **Metadata Tab**: Access generation details and configuration

### Getting Started with the Web Interface

1. **Access the Interface**: Navigate to `http://localhost:3001` after starting Docker services
2. **Load an Example**: Click on any example from the dropdown to see a complete specification
3. **Write Your Workflow**: Modify the example or write your own following the format
4. **Generate Agent**: Click "Generate Agent" to create your Python code
5. **Download Results**: Copy the generated code or download as a file

### Local Development (Frontend Only)

If you want to run the frontend separately for development:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Configure environment (uses Vite proxy for API calls)
cp .env.example .env

# Start development server
npm run dev

# Access at http://localhost:3002
```

**Important Notes**:
- Ensure the backend is running at `http://localhost:8000` before starting frontend
- The frontend uses Vite's built-in proxy to forward `/api/*` requests to the backend
- Keep `VITE_API_URL` empty in `.env` to use the proxy (recommended)
- This avoids CORS issues and mirrors the production nginx proxy setup

## Prerequisites (Manual Installation)

- **Python**: 3.12 or higher.
- **LLM API Key**: Every provider lets you get their own API key. For example for Anthropic API keys, you an obtain one from [Anthropic Console](https://console.anthropic.com/).

## Installation

### Environment Setup

```bash
# Clone repository
git clone https://github.com/yourusername/meta-flow.git
cd meta-flow

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### API Key Configuration

```bash
# Create .env file with your API key
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" > .env

# Verify configuration
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API key configured' if os.getenv('ANTHROPIC_API_KEY') else 'API key missing')"
```

## CLI Usage

The primary interface for Meta-Flow is the command-line interface. All operations are performed through the `complete_pipeline` module.

### Basic Usage

```bash
python -m src.cli.complete_pipeline <specification_file> [options]
```

### Workflow Examples

#### Sequential Workflow
```bash
# Generate a simple step-by-step data processing agent
python -m src.cli.complete_pipeline specs/examples/simple_sequential.txt

# Output:
# Phase 1 complete (confidence: 1.00)
# Workflow: data_processing_pipeline
# Code generation complete
# Generated 4609 characters
# Python agent: generated_agents/data_processing_pipeline_agent.py
```

#### Conditional Workflow
```bash
# Generate an expense approval agent with if/else branching
python -m src.cli.complete_pipeline specs/examples/conditional_branch.txt
```

#### Orchestrator Pattern
```bash
# Generate a support ticket routing system with dynamic delegation
python -m src.cli.complete_pipeline specs/examples/orchestrator_example.txt
```

#### Parallel Execution
```bash
# Generate an agent that runs compliance checks concurrently
python -m src.cli.complete_pipeline specs/examples/parallel_example.txt
```

#### Nested Workflows
```bash
# Generate complex order fulfillment with nested conditional logic
python -m src.cli.complete_pipeline specs/examples/nested_workflow.txt
```

### Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--verbose` | Enable detailed logging output | `--verbose` |
| `--validate-only` | Validate specification without generating code | `--validate-only` |
| `--output-dir` | Specify custom output directory | `--output-dir ./my_agents` |
| `--provider` | Select LLM provider (claude, aimlapi, gemini) | `--provider claude` |
| `--model` | Override default model | `--model claude-3-5-sonnet-20241022` |
| `--no-json` | Skip saving intermediate JSON | `--no-json` |

### Complete Examples

```bash
# Verbose mode for debugging
python -m src.cli.complete_pipeline specs/examples/simple_sequential.txt --verbose

# Validation only (no code generation)
python -m src.cli.complete_pipeline specs/examples/simple_sequential.txt --validate-only

# Custom output location
python -m src.cli.complete_pipeline specs/examples/simple_sequential.txt --output-dir ./custom_agents

# Use Claude Sonnet for complex workflows
python -m src.cli.complete_pipeline specs/examples/nested_workflow.txt --model claude-haiku-4-5
```

## Project Structure

```
meta-flow/
├── src/
│   ├── agents/              # Phase 1: LLM-based JSON generation
│   │   ├── graph.py         # LangGraph state machine
│   │   ├── nodes.py         # Processing nodes (parse, reason, validate)
│   │   ├── providers.py     # LLM provider abstraction
│   │   └── models.py        # Pydantic schemas
│   ├── generators/          # Phase 2: Code generation
│   │   └── agent_generator.py  # JSON to Python transformation
│   └── cli/
│       └── complete_pipeline.py  # Main CLI interface
├── api/                     # FastAPI backend
│   └── main.py             # REST API endpoints
├── frontend/               # React web interface
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── features/       # Feature modules (editor, generator)
│   │   ├── hooks/          # Custom React hooks
│   │   └── services/       # API client
│   └── Dockerfile          # Frontend container configuration
├── specs/examples/          # Example workflow specifications
├── generated_agents/        # Output directory for generated agents
├── docker-compose.yml       # Multi-container orchestration
└── requirements.txt         # Python dependencies
```

## Architecture

```
┌─────────────────────┐
│  Text Specification │  (Natural language workflow)
└──────────┬──────────┘
           │
    ┌──────▼──────────────────────┐
    │   PHASE 1: Meta-Agent       │
    │  ┌────────────────────┐     │
    │  │ Parser → Reasoner  │     │  (LangGraph + Claude Haiku 4.5)
    │  │    → Validator     │     │
    │  └────────────────────┘     │
    └──────────┬──────────────────┘
               │
        ┌──────▼──────┐
        │  JSON AST   │  (Structured workflow representation)
        └──────┬──────┘
               │
    ┌──────────▼──────────────────┐
    │  PHASE 2: Code Generator    │
    │  ┌────────────────────┐     │
    │  │  AST Traversal →   │     │  (Deterministic transformation)
    │  │  Python Generation │     │
    │  └────────────────────┘     │
    └──────────┬──────────────────┘
               │
        ┌──────▼──────────┐
        │  Python Agent   │  (Executable code with error handling)
        └─────────────────┘
```

## Writing Specifications

Specifications follow a structured format:

```
Workflow: workflow_name
Description: Brief description of the workflow

Inputs:
- parameter_name (type): Description
- another_param (type): Description

Steps:
1. First step description
2. If condition, then action A
3. Otherwise, action B
4. Final step

Outputs:
- output_name (type): Description
```

### Supported Workflow Patterns

1. **Sequential**: Numbered steps executed in order
2. **Conditional**: If/then/else branching logic
3. **Parallel**: Steps marked as concurrent/simultaneous
4. **Orchestrator**: Multiple named sub-workflows with routing rules
5. **Nested**: Combinations of the above patterns

## Environment Variables

Create a `.env` file in the project root:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional
ANTHROPIC_MODEL=claude-haiku-4-5
```

## Troubleshooting

### Missing ANTHROPIC_API_KEY
```bash
# Ensure .env file exists and contains your key
cat .env  # Should show: ANTHROPIC_API_KEY=sk-ant-...
```

### File Not Found Errors
```bash
# Verify you're in the project root directory
pwd  # Should end with /meta-flow
```

### Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### API Key Validation
```bash
# Test API key validity
python -c "from anthropic import Anthropic; c=Anthropic(); print('API key valid')"
```

### Frontend Issues

**CORS Errors in Console**
```bash
# Ensure backend is running and accessible
curl http://localhost:8000/api/health

# Check VITE_API_URL in frontend/.env
# Should be empty to use proxy (recommended for both local and Docker)
# Vite proxy: http://localhost:3002 → http://localhost:8000
# Docker proxy: nginx → backend:8000
```

**Build Failures**
```bash
# Check Node version (requires 18+)
node --version

# Clean install dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Connection to Backend Failed**
```bash
# For Docker: Services should be on same network
docker-compose ps  # Both should show "healthy"

# For local dev: Check backend is running
lsof -i :8000  # Should show uvicorn process
```

## License

This project is licensed under **AGPL-3.0** - see the [LICENSE](LICENSE) file for details.

**What this means:**
- Free to use for personal and open source projects
- You can modify and redistribute
- If you use this in a web service, you must open-source your service too

---

**Note**: This is a proof-of-concept developed to demonstrate the technical feasibility of automated agent generation. While functional and well-tested within its scope, production deployment would require additional hardening, observability, and scale testing.