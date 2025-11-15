"""
Meta-Agent v2: LangGraph-based production implementation.

This package contains the redesigned meta-agent system using:
- LangGraph for state machine management
- Enhanced Pydantic models with comprehensive validation
- LangSmith for observability and tracing
- SQLite for checkpointing and recovery
"""

from .models import (
    WorkflowInput,
    WorkflowOutput,
    ToolCall,
    SequentialWorkflow,
    ConditionalWorkflow,
    ParallelWorkflow,
    OrchestratorWorkflow,
    WorkflowSpec,
)
from .state import MetaAgentState, create_initial_state
from .errors import (
    MetaAgentError,
    ParsingError,
    ValidationError,
    ReasoningError,
    GenerationError,
)
from .graph import create_meta_agent_graph, run_meta_agent
from .nodes import (
    parser_node,
    reasoner_node,
    validator_node,
    generator_node,
    escalation_node,
)

__all__ = [
    # Models
    "WorkflowInput",
    "WorkflowOutput",
    "ToolCall",
    "SequentialWorkflow",
    "ConditionalWorkflow",
    "ParallelWorkflow",
    "OrchestratorWorkflow",
    "WorkflowSpec",
    # State
    "MetaAgentState",
    "create_initial_state",
    # Errors
    "MetaAgentError",
    "ParsingError",
    "ValidationError",
    "ReasoningError",
    "GenerationError",
    # Graph
    "create_meta_agent_graph",
    "run_meta_agent",
    # Nodes
    "parser_node",
    "reasoner_node",
    "validator_node",
    "generator_node",
    "escalation_node",
]
