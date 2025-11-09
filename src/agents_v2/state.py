"""
MetaAgentState definition for LangGraph state machine.

This TypedDict defines the complete state that flows through all nodes
in the LangGraph state machine, enabling checkpointing and recovery.
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal
from datetime import datetime, timezone
import uuid


class MetaAgentState(TypedDict, total=False):
    """
    Central state for the meta-agent workflow.

    This state flows through all nodes and is persisted at each checkpoint.
    All fields are optional (total=False) to support incremental state building.

    State Flow:
        START → Parser → Reasoner → Validator → Generator → END
                  ↓         ↓          ↓           ↓
              [Error]  [Low Conf] [Invalid]   [Success]
                  ↓         ↓          ↓
              [Log]    [Escalate] [Feedback]
    """

    # ===== Input/Output =====
    raw_spec: str
    """Original text specification provided by user"""

    generated_json: Optional[str]
    """Final JSON output (WorkflowSpec serialized)"""

    # ===== Parsing Stage =====
    parsed_sections: Dict[str, Any]
    """
    Extracted sections from text spec:
    {
        'workflow': str,
        'description': str,
        'inputs': List[str],
        'steps': List[str],
        'outputs': List[str]
    }
    """

    parsing_errors: List[str]
    """List of errors encountered during parsing"""

    # ===== Reasoning Stage =====
    inferred_structure: Dict[str, Any]
    """
    LLM's interpretation of workflow structure.
    Should conform to WorkflowSpec schema but not yet validated.
    """

    confidence_score: float
    """
    LLM confidence in inferred structure (0.0 to 1.0).
    <0.5: Low confidence, likely errors
    0.5-0.8: Medium confidence, may need human review
    >0.8: High confidence, proceed
    """

    reasoning_trace: List[str]
    """
    LLM's thought process (if using ReAct pattern).
    Useful for debugging and escalation reports.
    """

    # ===== Validation Stage =====
    workflow_spec: Optional[Dict[str, Any]]
    """
    Validated WorkflowSpec as dictionary.
    Only set if validation passes.
    """

    validation_errors: List[str]
    """List of Pydantic validation errors (if any)"""

    # ===== Control Flow =====
    execution_status: Literal[
        "parsing",      # Currently parsing text spec
        "reasoning",    # LLM is inferring structure
        "validating",   # Validating against Pydantic schema
        "generating",   # Generating final JSON
        "complete",     # Successfully completed
        "error",        # Unrecoverable error
        "escalated"     # Escalated to human review
    ]
    """Current execution state in the FSM"""

    retry_count: int
    """Number of retry attempts (max 3)"""

    should_escalate: bool
    """
    Whether to escalate to human review.
    Set to True if:
    - Confidence score < 0.8
    - Retry count >= 3
    - Critical validation errors
    """

    # ===== Metadata =====
    timestamp: str
    """ISO 8601 timestamp when execution started"""

    llm_provider: str
    """LLM provider to use ('aimlapi' or 'gemini')"""

    model_version: str
    """LLM model used (e.g., 'x-ai/grok-4-fast-reasoning' or 'gemini-2.0-flash-lite')"""

    prompt_version: str
    """Version of prompt template used"""

    execution_id: str
    """Unique identifier for this execution (UUID)"""

    # ===== Error Tracking =====
    error_history: List[Dict[str, Any]]
    """
    List of all errors encountered during execution.
    Each entry: {
        'stage': str,           # Which node failed
        'error_type': str,      # Error class name
        'message': str,         # Error message
        'timestamp': str,       # When error occurred
        'recoverable': bool     # Can retry?
    }
    """

    # ===== Feedback Loop =====
    feedback_messages: List[str]
    """
    Messages to send back to LLM on retry.
    E.g., "Step 3 references undefined variable 'data'"
    """


def create_initial_state(
    raw_spec: str,
    llm_provider: str = "aimlapi",
    model_version: str = None,
    prompt_version: str = "2.0.0"
) -> MetaAgentState:
    """
    Create initial state for new workflow processing.

    Args:
        raw_spec: Text specification to process
        llm_provider: LLM provider to use ('aimlapi' or 'gemini')
        model_version: LLM model identifier (optional, reads from env vars or uses hardcoded default)
        prompt_version: Prompt template version

    Returns:
        MetaAgentState initialized for processing
    """
    import os

    # Set model based on: 1) explicit param, 2) env var, 3) hardcoded default
    if model_version is None:
        if llm_provider == "gemini":
            model_version = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
        else:
            model_version = os.getenv("AIMLAPI_MODEL", "x-ai/grok-4-fast-reasoning")

    return MetaAgentState(
        # Input
        raw_spec=raw_spec,
        generated_json=None,

        # Parsing
        parsed_sections={},
        parsing_errors=[],

        # Reasoning
        inferred_structure={},
        confidence_score=0.0,
        reasoning_trace=[],

        # Validation
        workflow_spec=None,
        validation_errors=[],

        # Control
        execution_status="parsing",
        retry_count=0,
        should_escalate=False,

        # Metadata
        timestamp=datetime.now(timezone.utc).isoformat(),
        llm_provider=llm_provider,
        model_version=model_version,
        prompt_version=prompt_version,
        execution_id=str(uuid.uuid4()),

        # Error tracking
        error_history=[],
        feedback_messages=[]
    )


def add_error_to_state(
    state: MetaAgentState,
    stage: str,
    error_type: str,
    message: str,
    recoverable: bool = True
) -> MetaAgentState:
    """
    Add error to state history.

    Args:
        state: Current state
        stage: Which node failed (e.g., 'parser', 'reasoner')
        error_type: Error class name
        message: Error message
        recoverable: Whether retry is possible

    Returns:
        Updated state with error added
    """
    error_entry = {
        'stage': stage,
        'error_type': error_type,
        'message': message,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'recoverable': recoverable
    }

    if 'error_history' not in state:
        state['error_history'] = []

    state['error_history'].append(error_entry)

    return state


def should_retry(state: MetaAgentState) -> bool:
    """
    Determine if workflow should retry based on state.

    Args:
        state: Current state

    Returns:
        True if retry is warranted, False otherwise
    """
    # Don't retry if already escalated or complete
    if state.get('execution_status') in ['escalated', 'complete']:
        return False

    # Don't retry if retry limit reached
    if state.get('retry_count', 0) >= 3:
        return False

    # Don't retry if explicitly marked for escalation
    if state.get('should_escalate', False):
        return False

    # Retry if there are validation errors and retries remain
    if state.get('validation_errors'):
        return True

    # Retry if confidence is very low
    if state.get('confidence_score', 1.0) < 0.5:
        return True

    # Otherwise, don't retry
    return False


def build_feedback_message(state: MetaAgentState) -> str:
    """
    Build feedback message for LLM retry based on state.

    Args:
        state: Current state with errors

    Returns:
        Human-readable feedback for LLM
    """
    messages = []

    # Add validation errors
    if state.get('validation_errors'):
        messages.append("Validation Errors:")
        for error in state['validation_errors'][:5]:  # Limit to 5 errors
            messages.append(f"  - {error}")

    # Add parsing errors
    if state.get('parsing_errors'):
        messages.append("\nParsing Errors:")
        for error in state['parsing_errors'][:5]:
            messages.append(f"  - {error}")

    # Add confidence warning
    if state.get('confidence_score', 1.0) < 0.5:
        messages.append(f"\nLow confidence score: {state['confidence_score']:.2f}")
        messages.append("Please review the specification more carefully.")

    # Add retry count
    retry_count = state.get('retry_count', 0)
    messages.append(f"\nRetry attempt: {retry_count + 1}/3")

    return "\n".join(messages)
