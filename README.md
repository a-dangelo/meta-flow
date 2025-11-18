# Meta-Flow: Automated Workflow-to-Agent Code Generation

A system that transforms natural language workflow descriptions into executable Python agents using LLM-powered code generation.

## Project Overview

Meta-Flow operates in two phases:
- **Phase 1**: Converts text workflow specifications into structured JSON using LLM's.
- **Phase 2**: Transforms JSON into executable Python agents with error handling and credential management.

## Quick Start

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

# 4. Access application
# Frontend: http://localhost
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

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
curl http://localhost/health
```

**Issue: Port already in use**
```bash
# Change ports in docker-compose.yml:
# Frontend: Change "80:80" to "3000:80"
# Backend: Change "8000:8000" to "8001:8000"
```

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
├── specs/examples/          # Example workflow specifications
├── generated_agents/        # Output directory for generated agents
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

## License

This project is licensed under **AGPL-3.0** - see the [LICENSE](LICENSE) file for details.

**What this means:**
- Free to use for personal and open source projects
- You can modify and redistribute
- If you use this in a web service, you must open-source your service too

---

**Note**: This is a proof-of-concept developed to demonstrate the technical feasibility of automated agent generation. While functional and well-tested within its scope, production deployment would require additional hardening, observability, and scale testing.