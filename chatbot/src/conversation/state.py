"""State schema for hybrid LangGraph conversation flow."""

from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class WorkflowState(TypedDict, total=False):
    """
    State for hybrid decomposition chatbot architecture.

    Combines deterministic operations (search, extraction, validation)
    with LLM-powered conversation (clarification, value collection).

    All fields optional for incremental building during graph execution.
    """
    # Core identifiers
    user_id: str
    session_id: str
    access_level: str  # employee, manager, hr, admin

    # User interaction
    user_input: str  # Current user message
    messages: Annotated[list[BaseMessage], add_messages]  # LangGraph message tracking

    # Workflow selection (deterministic search)
    matched_workflow_name: Optional[str]
    matched_workflow_path: Optional[str]
    search_confidence: float
    search_candidates: Optional[list[dict]]  # If ambiguous results
    requires_clarification: bool

    # Agent generation (meta-agent)
    json_ast: Optional[dict]  # Structured JSON from meta-agent
    python_code: Optional[str]  # Generated Python code

    # Parameter handling (hybrid: extract from JSON, collect with LLM)
    required_parameters: list[dict]  # Extracted from JSON AST
    collected_parameters: dict  # User-provided values
    pending_parameters: list[str]  # Still need values for these

    # Validation (deterministic)
    validation_errors: Optional[list[str]]

    # Execution
    execution_status: str  # pending, running, completed, failed
    execution_result: Optional[dict]
    error_message: Optional[str]

    # Observability
    node_timings: dict  # Performance tracking per node
