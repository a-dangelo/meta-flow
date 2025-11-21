"""
Pydantic models for API request/response validation.

Defines type-safe schemas for all API endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== REQUEST MODELS ====================

class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message."""

    session_id: str = Field(
        ...,
        description="Unique session identifier",
        min_length=1,
        max_length=100
    )
    message: str = Field(
        ...,
        description="User's message",
        min_length=1,
        max_length=5000
    )
    user_id: Optional[str] = Field(
        default="anonymous",
        description="User identifier"
    )
    access_level: str = Field(
        default="employee",
        description="User's access level (employee, manager, hr, admin)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-123",
                "message": "I need to submit an expense report",
                "user_id": "user-456",
                "access_level": "employee"
            }
        }


# ==================== RESPONSE MODELS ====================

class ParameterInfo(BaseModel):
    """Information about a workflow parameter."""

    name: str
    type: str
    description: Optional[str] = None
    required: bool = True
    default: Optional[Any] = None


class ExecutionResult(BaseModel):
    """Result of workflow execution."""

    workflow: str
    status: str
    reference_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    logs: List[str] = Field(default_factory=list)
    execution_time: Optional[float] = None


class ChatMessageResponse(BaseModel):
    """Response model for chat message."""

    session_id: str
    status: str = Field(
        description="Current execution status (pending, collecting_parameters, "
                    "executing, completed, failed)"
    )
    message: Optional[str] = Field(
        default=None,
        description="Agent's response message"
    )
    matched_workflow: Optional[str] = Field(
        default=None,
        description="Matched workflow name"
    )
    search_confidence: Optional[float] = Field(
        default=None,
        description="Workflow match confidence (0.0-1.0)"
    )
    required_parameters: Optional[List[ParameterInfo]] = Field(
        default=None,
        description="Parameters needed for execution"
    )
    collected_parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Parameters collected so far"
    )
    pending_parameters: Optional[List[str]] = Field(
        default=None,
        description="Parameters still needed"
    )
    validation_errors: Optional[List[str]] = Field(
        default=None,
        description="Validation errors if any"
    )
    execution_result: Optional[ExecutionResult] = Field(
        default=None,
        description="Execution result if completed"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    node_timings: Optional[Dict[str, float]] = Field(
        default=None,
        description="Performance timings for each node"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-123",
                "status": "collecting_parameters",
                "message": "Please provide: amount, date, category",
                "matched_workflow": "expense_approval",
                "search_confidence": 0.72,
                "required_parameters": [
                    {
                        "name": "amount",
                        "type": "float",
                        "description": "Expense amount",
                        "required": True
                    }
                ],
                "pending_parameters": ["amount", "date", "category"]
            }
        }


class SessionStateResponse(BaseModel):
    """Response model for session state."""

    session_id: str
    user_id: str
    access_level: str
    status: str
    matched_workflow: Optional[str] = None
    search_confidence: Optional[float] = None
    required_parameters: Optional[List[ParameterInfo]] = None
    collected_parameters: Optional[Dict[str, Any]] = None
    execution_result: Optional[ExecutionResult] = None
    error_message: Optional[str] = None
    message_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WorkflowMetadataResponse(BaseModel):
    """Response model for workflow metadata."""

    name: str
    description: str
    category: str
    access_level: str
    file_path: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "expense_approval",
                "description": "Submit and approve expense reports",
                "category": "hr",
                "access_level": "employee"
            }
        }


class WorkflowListResponse(BaseModel):
    """Response model for workflow list."""

    workflows: List[WorkflowMetadataResponse]
    total: int
    access_level: str

    class Config:
        json_schema_extra = {
            "example": {
                "workflows": [
                    {
                        "name": "expense_approval",
                        "description": "Submit expense reports",
                        "category": "hr",
                        "access_level": "employee"
                    }
                ],
                "total": 3,
                "access_level": "employee"
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    version: str = "1.0.0"
    timestamp: datetime
    services: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of dependent services"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2025-11-21T10:30:00Z",
                "services": {
                    "workflow_repository": "healthy",
                    "execution_engine": "healthy"
                }
            }
        }


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str
    detail: Optional[str] = None
    status_code: int
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid session",
                "detail": "Session 'abc123' not found",
                "status_code": 404,
                "timestamp": "2025-11-21T10:30:00Z"
            }
        }


# ==================== WEBSOCKET MODELS ====================

class WSMessage(BaseModel):
    """WebSocket message model."""

    type: str = Field(
        description="Message type: log, status, result, error"
    )
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "type": "log",
                "content": "Processing expense report...",
                "timestamp": "2025-11-21T10:30:00Z"
            }
        }


class WSStatusMessage(WSMessage):
    """WebSocket status update message."""

    type: str = "status"
    status: str = Field(description="Current status")
    progress: Optional[int] = Field(
        default=None,
        description="Progress percentage (0-100)"
    )


class WSLogMessage(WSMessage):
    """WebSocket log message."""

    type: str = "log"
    level: str = Field(default="info", description="Log level")


class WSResultMessage(WSMessage):
    """WebSocket result message."""

    type: str = "result"
    result: Dict[str, Any] = Field(description="Execution result")
    reference_id: Optional[str] = None


class WSErrorMessage(WSMessage):
    """WebSocket error message."""

    type: str = "error"
    error: str = Field(description="Error message")
    error_type: Optional[str] = None
