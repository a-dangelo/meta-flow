"""
LangGraph state machine for meta-agent v2.

This module creates the StateGraph that orchestrates the workflow:
    START → Parser → Reasoner → Validator → Generator → END
              ↓         ↓          ↓
          [Error]  [Escalate] [Retry/Error]
"""

import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .state import MetaAgentState, should_retry, build_feedback_message
from .nodes import (
    parser_node,
    reasoner_node,
    validator_node,
    generator_node,
    escalation_node
)

logger = logging.getLogger(__name__)


def create_meta_agent_graph(
    checkpointer: SqliteSaver = None,
    enable_tracing: bool = False
) -> StateGraph:
    """
    Create the LangGraph state machine for meta-agent v2.

    Args:
        checkpointer: SQLite saver for checkpointing (optional)
        enable_tracing: Enable LangSmith tracing (optional)

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create state graph
    workflow = StateGraph(MetaAgentState)

    # Add nodes
    workflow.add_node("parser", parser_node)
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("escalation", escalation_node)

    # Set entry point
    workflow.set_entry_point("parser")

    # Add edges with conditional routing
    workflow.add_conditional_edges(
        "parser",
        _route_from_parser,
        {
            "reasoner": "reasoner",
            "escalation": "escalation",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "reasoner",
        _route_from_reasoner,
        {
            "validator": "validator",
            "escalation": "escalation",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "validator",
        _route_from_validator,
        {
            "generator": "generator",
            "reasoner": "reasoner",  # Retry with feedback
            "escalation": "escalation",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "generator",
        _route_from_generator,
        {
            "end": END,
            "escalation": "escalation"
        }
    )

    # Escalation always ends
    workflow.add_edge("escalation", END)

    # Compile graph
    compiled = workflow.compile(checkpointer=checkpointer)

    logger.info("✓ LangGraph state machine compiled")
    return compiled


# ===== Routing Functions =====

def _route_from_parser(state: MetaAgentState) -> Literal["reasoner", "escalation", "end"]:
    """
    Route from parser node based on parsing results.

    Returns:
        - "reasoner": If parsing succeeded
        - "escalation": If parsing failed with unrecoverable errors
        - "end": Should not happen from parser
    """
    if state.get('parsing_errors'):
        logger.warning("Parser failed, escalating")
        return "escalation"

    if state.get('execution_status') == 'error':
        return "escalation"

    return "reasoner"


def _route_from_reasoner(state: MetaAgentState) -> Literal["validator", "escalation", "end"]:
    """
    Route from reasoner node based on LLM reasoning results.

    Returns:
        - "validator": If LLM produced structure (proceed to validation)
        - "escalation": If confidence too low or should escalate
        - "end": Should not happen from reasoner
    """
    if state.get('should_escalate'):
        logger.warning(f"Low confidence ({state.get('confidence_score', 0):.2f}), escalating")
        return "escalation"

    if state.get('execution_status') == 'error':
        return "escalation"

    return "validator"


def _route_from_validator(
    state: MetaAgentState
) -> Literal["generator", "reasoner", "escalation", "end"]:
    """
    Route from validator node based on validation results.

    Returns:
        - "generator": If validation passed
        - "reasoner": If validation failed but retry is possible
        - "escalation": If retry limit reached or unrecoverable error
        - "end": Should not happen from validator
    """
    if state.get('validation_errors'):
        # Validation failed
        if should_retry(state):
            # Increment retry count
            state['retry_count'] = state.get('retry_count', 0) + 1
            logger.info(f"Validation failed, retry {state['retry_count']}/3")

            # Add feedback for LLM
            state['feedback_messages'] = state.get('validation_errors', [])[:5]

            return "reasoner"
        else:
            # Retry limit reached
            logger.warning("Retry limit reached, escalating")
            return "escalation"

    if state.get('execution_status') == 'generating':
        return "generator"

    # Unexpected state
    logger.error(f"Unexpected state in validator routing: {state.get('execution_status')}")
    return "escalation"


def _route_from_generator(state: MetaAgentState) -> Literal["end", "escalation"]:
    """
    Route from generator node.

    Returns:
        - "end": If generation succeeded
        - "escalation": If generation failed (should be rare)
    """
    if state.get('execution_status') == 'complete':
        return "end"

    # Generation failed (should not happen often)
    logger.error("Generator failed, escalating")
    return "escalation"


# ===== Main Execution Function =====

def run_meta_agent(
    raw_spec: str,
    checkpointer: SqliteSaver = None,
    model_version: str = "x-ai/grok-4-fast-reasoning",
    prompt_version: str = "2.0.0",
    config: dict = None
) -> MetaAgentState:
    """
    Run the meta-agent state machine on a text specification.

    Args:
        raw_spec: Text workflow specification
        checkpointer: SQLite saver for checkpointing (optional)
        model_version: LLM model to use
        prompt_version: Prompt template version
        config: LangGraph configuration (for thread_id, etc.)

    Returns:
        Final state after execution

    Example:
        >>> from langgraph.checkpoint.sqlite import SqliteSaver
        >>> checkpointer = SqliteSaver.from_conn_string(":memory:")
        >>> result = run_meta_agent(
        ...     raw_spec="Workflow: test\\nDescription: test\\nSteps:\\n1. Do something",
        ...     checkpointer=checkpointer
        ... )
        >>> print(result['execution_status'])
        'complete'
    """
    from .state import create_initial_state

    # Create graph
    graph = create_meta_agent_graph(checkpointer=checkpointer)

    # Create initial state
    initial_state = create_initial_state(
        raw_spec=raw_spec,
        model_version=model_version,
        prompt_version=prompt_version
    )

    # Run graph
    logger.info(f"Starting meta-agent execution (ID: {initial_state['execution_id']})")

    if config is None:
        config = {"configurable": {"thread_id": initial_state['execution_id']}}

    final_state = graph.invoke(initial_state, config=config)

    logger.info(f"Execution complete. Status: {final_state.get('execution_status')}")

    return final_state
