"""
FastAPI backend for Meta-Agent System
Provides REST API endpoints for the React frontend to interact with the meta-agent pipeline
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
import os
import json
import logging
from pathlib import Path
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import existing Phase 1 & 2 components
from src.agents.graph import run_meta_agent
from src.agents.models import WorkflowSpec
from src.generators.agent_generator import AgentGenerator
from src.agents.errors import MetaAgentError, ParsingError, ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Meta-Agent Pipeline API",
    version="1.0.0",
    description="Transform natural language workflow specifications into executable Python agents",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Security: Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0", "backend", "*.anthropic.com"]
)

# CORS Middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3002",  # Vite dev server (changed from 5173 to avoid Codespaces conflict)
        "http://localhost:3000",  # Alternative React port
        "http://localhost",       # Production frontend
        "http://127.0.0.1:3002",  # Changed from 5173
        "http://127.0.0.1:3000",
        "http://127.0.0.1"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    max_age=3600,
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)

    # Content Security Policy - Monaco Editor requires 'unsafe-eval'
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; "  # Monaco needs eval and blob:
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; "  # Monaco uses data: URIs for fonts
        "img-src 'self' data: blob:; "
        "worker-src 'self' blob:;"  # Monaco uses web workers
    )

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    return response

# Request/Response Models
class GenerateRequest(BaseModel):
    """Request model for agent generation"""
    spec: str = Field(..., description="Natural language workflow specification")
    provider: str = Field(default="claude", description="LLM provider (claude, aimlapi, gemini)")
    model_version: Optional[str] = Field(None, description="Specific model version to use")

    @validator('spec')
    def validate_spec(cls, v):
        """Validate the specification input"""
        if not v or not v.strip():
            raise ValueError("Specification cannot be empty")
        if len(v) > 50000:  # 50KB limit
            raise ValueError("Specification too large (max 50KB)")

        # Basic validation for required sections
        spec_lower = v.lower()
        required_sections = ["workflow:", "inputs:", "steps:", "outputs:"]
        missing_sections = [s for s in required_sections if s not in spec_lower]

        if missing_sections:
            raise ValueError(f"Missing required sections: {', '.join(missing_sections)}")

        return v.strip()

    @validator('provider')
    def validate_provider(cls, v):
        """Validate LLM provider"""
        valid_providers = ["claude", "aimlapi", "gemini"]
        if v not in valid_providers:
            raise ValueError(f"Invalid provider. Must be one of: {', '.join(valid_providers)}")
        return v

class GenerateResponse(BaseModel):
    """Response model for agent generation"""
    json_output: str = Field(..., description="Generated JSON workflow specification")
    python_code: str = Field(..., description="Generated Python agent code")
    execution_status: str = Field(..., description="Pipeline execution status")
    confidence_score: float = Field(..., description="Confidence score of generation")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata about generation")
    warnings: List[str] = Field(default_factory=list, description="Any warnings during generation")

class ExampleSpec(BaseModel):
    """Model for example specifications"""
    content: str = Field(..., description="Specification content")
    filename: str = Field(..., description="Original filename")
    type: str = Field(..., description="Inferred workflow type")
    description: Optional[str] = Field(None, description="Brief description")

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    service: str
    version: str
    timestamp: str
    checks: Dict[str, bool]

# API Endpoints

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for monitoring and Docker health checks

    Returns system status and component availability
    """
    checks = {
        "api": True,
        "imports": False,
        "examples": False
    }

    # Check if core imports work
    try:
        from src.agents.graph import run_meta_agent
        from src.generators.agent_generator import AgentGenerator
        checks["imports"] = True
    except ImportError:
        pass

    # Check if examples directory exists
    examples_dir = Path(__file__).parent.parent / "specs" / "examples"
    checks["examples"] = examples_dir.exists()

    # Check if at least one API key is configured
    checks["api_key_configured"] = bool(
        os.getenv("ANTHROPIC_API_KEY") or
        os.getenv("AIMLAPI_KEY") or
        os.getenv("GEMINI_API_KEY")
    )

    all_healthy = all(checks.values())

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        service="meta-agent-api",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        checks=checks
    )

@app.post("/api/generate", response_model=GenerateResponse)
async def generate_agent(request: GenerateRequest):
    """
    Execute the complete pipeline: Text Specification → JSON Workflow → Python Agent

    This endpoint:
    1. Parses the natural language specification using the meta-agent
    2. Validates the generated JSON against the workflow schema
    3. Generates executable Python code from the validated specification

    Args:
        request: GenerateRequest containing the specification and options

    Returns:
        GenerateResponse with JSON, Python code, and metadata

    Raises:
        HTTPException: On validation errors or pipeline failures
    """
    logger.info(f"Starting generation for workflow with provider: {request.provider}")

    # Check API key is configured for the requested provider
    api_key_map = {
        "claude": "ANTHROPIC_API_KEY",
        "aimlapi": "AIMLAPI_KEY",
        "gemini": "GEMINI_API_KEY"
    }

    required_key = api_key_map.get(request.provider)
    if required_key and not os.getenv(required_key):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "API key not configured",
                "message": f"Missing {required_key} environment variable for provider '{request.provider}'",
                "type": "ConfigurationError",
                "suggestions": [
                    f"Set the environment variable: export {required_key}=your_key_here",
                    f"Or choose a different provider (available: {', '.join(k for k, v in api_key_map.items() if os.getenv(v))})"
                ]
            }
        )

    try:
        # Phase 1: Run meta-agent (text → JSON)
        logger.info("Phase 1: Running meta-agent...")

        result = run_meta_agent(
            raw_spec=request.spec,
            llm_provider=request.provider,
            model_version=request.model_version,
            checkpointer=None  # In-memory for demo
        )

        # Check execution status
        if result.get("execution_status") != "complete":
            error_msg = result.get("error", "Unknown error occurred during meta-agent execution")
            logger.error(f"Meta-agent failed: {error_msg}")

            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Meta-agent pipeline failed",
                    "stage": result.get("current_stage", "unknown"),
                    "message": error_msg,
                    "suggestions": [
                        "Check that the specification follows the required format",
                        "Ensure all sections are present: Workflow, Inputs, Steps, Outputs",
                        "Verify step descriptions are clear and unambiguous",
                        "Check for typos in section headers"
                    ]
                }
            )

        # Extract generated JSON
        json_output = result.get("generated_json", "")
        if not json_output:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "No JSON output generated",
                    "message": "Meta-agent completed but produced no output"
                }
            )

        logger.info("Phase 1 complete: JSON generated successfully")

        # Phase 2: Generate Python code (JSON → Python)
        logger.info("Phase 2: Generating Python code...")

        # Parse and validate the JSON into WorkflowSpec
        spec = WorkflowSpec.model_validate_json(json_output)

        # Generate Python code
        generator = AgentGenerator(spec)
        python_code = generator.generate()

        logger.info("Phase 2 complete: Python code generated successfully")

        # Prepare metadata
        metadata = {
            "workflow_name": spec.name,
            "workflow_type": spec.workflow.type if hasattr(spec.workflow, 'type') else "unknown",
            "num_inputs": len(spec.inputs),
            "num_outputs": len(spec.outputs),
            "num_steps": _count_workflow_steps(spec.workflow),
            "credentials_detected": list(generator.credential_params) if generator.credential_params else [],
            "tools_used": list(generator.all_tools) if generator.all_tools else [],
            "generation_time": datetime.utcnow().isoformat(),
            "provider_used": request.provider
        }

        # Collect warnings
        warnings = []
        if generator.credential_params:
            warnings.append(f"Detected {len(generator.credential_params)} credential parameters - using environment variables")

        if result.get("confidence_score", 1.0) < 0.8:
            warnings.append("Low confidence score - review generated code carefully")

        return GenerateResponse(
            json_output=json_output,
            python_code=python_code,
            execution_status=result.get("execution_status", "complete"),
            confidence_score=result.get("confidence_score", 0.95),
            metadata=metadata,
            warnings=warnings
        )

    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Validation error",
                "message": str(e),
                "type": "ValidationError",
                "suggestions": [
                    "Check that the specification structure is correct",
                    "Ensure all required fields are present",
                    "Verify data types match expected formats"
                ]
            }
        )

    except ParsingError as e:
        logger.error(f"Parsing error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Parsing error",
                "message": str(e),
                "type": "ParsingError",
                "suggestions": [
                    "Check specification syntax",
                    "Ensure proper indentation",
                    "Verify section headers are correctly formatted"
                ]
            }
        )

    except MetaAgentError as e:
        logger.error(f"Meta-agent error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Meta-agent error",
                "message": str(e),
                "type": type(e).__name__
            }
        )

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Invalid JSON generated",
                "message": f"Failed to parse generated JSON: {str(e)}",
                "type": "JSONDecodeError"
            }
        )

    except HTTPException:
        # Re-raise HTTPException without wrapping
        raise

    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": str(e),
                "type": type(e).__name__
            }
        )

@app.get("/api/examples", response_model=Dict[str, ExampleSpec])
async def get_examples():
    """
    Return all example workflow specifications from specs/examples/

    Returns:
        Dictionary of example specifications keyed by name
    """
    examples = {}
    examples_dir = Path(__file__).parent.parent / "specs" / "examples"

    if not examples_dir.exists():
        logger.error(f"Examples directory not found: {examples_dir}")
        raise HTTPException(
            status_code=500,
            detail="Examples directory not found. Please ensure specs/examples/ exists."
        )

    # Read all .txt files in examples directory
    for file_path in sorted(examples_dir.glob("*.txt")):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Infer workflow type and description
            workflow_type = _infer_workflow_type(content)
            description = _extract_description(content)

            examples[file_path.stem] = ExampleSpec(
                content=content,
                filename=file_path.name,
                type=workflow_type,
                description=description
            )

            logger.info(f"Loaded example: {file_path.name} (type: {workflow_type})")

        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            continue

    if not examples:
        raise HTTPException(
            status_code=500,
            detail="No example specifications could be loaded"
        )

    return examples

# Utility functions

def _infer_workflow_type(content: str) -> str:
    """
    Infer the workflow type from specification content

    Args:
        content: Specification text content

    Returns:
        Workflow type string
    """
    content_lower = content.lower()

    # Check for specific workflow patterns
    if "route" in content_lower and ("tier" in content_lower or "priority" in content_lower):
        return "orchestrator"
    elif "if " in content_lower and ("then" in content_lower or "otherwise" in content_lower):
        return "conditional"
    elif "parallel" in content_lower or "concurrent" in content_lower or "simultaneously" in content_lower:
        return "parallel"
    elif "nested" in content_lower or "sub-workflow" in content_lower:
        return "nested"
    else:
        return "sequential"

def _extract_description(content: str) -> Optional[str]:
    """
    Extract description from specification content

    Args:
        content: Specification text content

    Returns:
        Description if found, None otherwise
    """
    lines = content.split('\n')

    # Look for Description: line
    for line in lines:
        if line.strip().startswith('Description:'):
            desc = line.split('Description:', 1)[1].strip()
            if desc:
                return desc

    # Fall back to workflow name
    for line in lines:
        if line.strip().startswith('Workflow:'):
            name = line.split('Workflow:', 1)[1].strip()
            if name:
                return f"{name} workflow"

    return None

def _count_workflow_steps(workflow: Any) -> int:
    """
    Count the number of steps in a workflow recursively

    Args:
        workflow: Workflow object

    Returns:
        Number of steps
    """
    if not workflow:
        return 0

    if hasattr(workflow, 'type'):
        if workflow.type == 'tool_call':
            return 1
        elif workflow.type == 'sequential' and hasattr(workflow, 'steps'):
            return len(workflow.steps)
        elif workflow.type == 'conditional':
            count = 1  # The condition itself
            if hasattr(workflow, 'if_branch'):
                count += _count_workflow_steps(workflow.if_branch)
            if hasattr(workflow, 'else_branch'):
                count += _count_workflow_steps(workflow.else_branch)
            return count
        elif workflow.type == 'parallel' and hasattr(workflow, 'branches'):
            return sum(_count_workflow_steps(b) for b in workflow.branches)
        elif workflow.type == 'orchestrator' and hasattr(workflow, 'sub_workflows'):
            return len(workflow.sub_workflows)

    return 1

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - provides API information"""
    return {
        "service": "Meta-Agent Pipeline API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "generate": "/api/generate",
            "examples": "/api/examples",
            "docs": "/api/docs",
            "redoc": "/api/redoc"
        },
        "description": "Transform natural language workflow specifications into executable Python agents"
    }

# Exception handler for better error responses
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors with detailed responses"""
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation error",
            "message": str(exc),
            "type": "ValueError"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "type": type(exc).__name__
        }
    )

if __name__ == "__main__":
    import uvicorn

    # Run the application
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True  # Enable hot reload for development
    )