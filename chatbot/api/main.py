"""
FastAPI application for chatbot automation layer.

Provides REST API and WebSocket endpoints for conversational
workflow automation.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from chatbot.api.models import HealthResponse, ErrorResponse

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== LIFESPAN MANAGEMENT ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown.

    Initializes resources on startup and cleans up on shutdown.
    """
    # Startup
    logger.info("=" * 80)
    logger.info("🤖 Meta-Flow Chatbot API")
    logger.info("=" * 80)
    logger.info("Version: 1.0.0")
    logger.info("Docs: http://localhost:8000/docs")
    logger.info("Health: http://localhost:8000/health")
    logger.info("=" * 80)

    # Verify environment variables are loaded
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        logger.info(f"✓ ANTHROPIC_API_KEY loaded (ends with: ...{api_key[-4:]})")
    else:
        logger.warning("⚠ ANTHROPIC_API_KEY not found - meta-agent generation will fail")

    # Initialize workflow repository (lazy-loaded singleton)
    from chatbot.src.conversation.graph_hybrid import get_repository
    try:
        repo = get_repository()
        logger.info(f"✓ Loaded {len(repo.workflows)} workflows")
    except Exception as e:
        logger.error(f"✗ Failed to load workflows: {e}")

    logger.info("Chatbot API started successfully")
    logger.info("=" * 80)

    yield

    # Shutdown
    logger.info("Shutting down chatbot API...")


# ==================== APP INITIALIZATION ====================

app = FastAPI(
    title="Meta-Flow Chatbot API",
    description="Conversational workflow automation API with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# ==================== MIDDLEWARE ====================

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Alternative frontend port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(f"{request.method} {request.url.path}")
    start_time = datetime.utcnow()

    response = await call_next(request)

    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(
        f"{request.method} {request.url.path} "
        f"- {response.status_code} ({duration:.3f}s)"
    )

    return response


# ==================== EXCEPTION HANDLERS ====================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    """Handle Pydantic validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation error",
            detail=str(exc.errors()),
            status_code=422,
            timestamp=datetime.utcnow()
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            status_code=500,
            timestamp=datetime.utcnow()
        ).model_dump()
    )


# ==================== ROOT ENDPOINTS ====================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Meta-Flow Chatbot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns API health status and dependent service status.
    """
    from chatbot.src.conversation.graph_hybrid import get_repository

    services = {}

    # Check workflow repository
    try:
        repo = get_repository()
        services["workflow_repository"] = f"healthy ({len(repo.workflows)} workflows)"
    except Exception as e:
        services["workflow_repository"] = f"unhealthy: {str(e)}"

    # Check execution engine
    try:
        from chatbot.src.execution.orchestrator import execute_agent_safely
        services["execution_engine"] = "healthy"
    except Exception as e:
        services["execution_engine"] = f"unhealthy: {str(e)}"

    overall_status = "healthy" if all(
        "healthy" in s for s in services.values()
    ) else "degraded"

    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        timestamp=datetime.utcnow(),
        services=services
    )


# ==================== ROUTE REGISTRATION ====================

# Import and register route modules
from chatbot.api.routes import chat, workflows

app.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat"]
)

app.include_router(
    workflows.router,
    prefix="/workflows",
    tags=["Workflows"]
)


# ==================== WEBSOCKET ====================

from chatbot.api import websocket as ws

app.include_router(
    ws.router,
    tags=["WebSocket"]
)


# Note: Startup message moved to lifespan context manager above


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "chatbot.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
