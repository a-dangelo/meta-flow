"""LangGraph nodes for chatbot conversation flow."""

from pathlib import Path
from datetime import datetime
from typing import Any

from chatbot.src.conversation.state import ChatbotState, Message
from chatbot.src.workflow_matching.repository import WorkflowRepository
from chatbot.src.integration.meta_agent_client import MetaAgentClient


# Initialize repository (singleton pattern for caching)
_repository = None


def get_repository() -> WorkflowRepository:
    """Get or create workflow repository singleton."""
    global _repository
    if _repository is None:
        workflows_dir = Path(__file__).parent.parent.parent / "workflows"
        _repository = WorkflowRepository(workflows_dir)
    return _repository


async def intent_recognition_node(state: ChatbotState) -> ChatbotState:
    """
    Extract user intent from latest message.

    For MVP: Simply use the message content as intent.
    For production: Use LLM to extract structured intent.
    """
    messages = state.get("messages", [])
    if not messages:
        return {
            **state,
            "error_message": "No messages in conversation",
            "execution_status": "failed"
        }

    # Get latest user message
    latest_message = messages[-1]
    user_intent = latest_message.content

    return {
        **state,
        "user_intent": user_intent,
        "execution_status": "matching_workflow"
    }


async def workflow_matching_node(state: ChatbotState) -> ChatbotState:
    """
    Match user intent to workflow using semantic search.
    """
    user_intent = state.get("user_intent", "")
    user_access_level = state.get("access_level", "employee")

    repository = get_repository()

    # Find best matching workflow
    workflow, confidence = repository.find_by_intent(user_intent, user_access_level)

    if workflow is None:
        # No match found - return options
        all_workflows = repository.list_all_workflows(user_access_level)

        response_message = Message(
            role="assistant",
            content=f"I couldn't find a workflow for '{user_intent}'. "
                   f"Available workflows:\n" +
                   "\n".join(f"• {wf.name}: {wf.description}" for wf in all_workflows[:5]),
            timestamp=datetime.utcnow().isoformat()
        )

        return {
            **state,
            "messages": state.get("messages", []) + [response_message],
            "execution_status": "failed",
            "error_message": f"No workflow matched with confidence >= {repository.confidence_threshold}"
        }

    # Get full workflow specification
    spec_content = repository.get_workflow_spec(workflow.name)

    return {
        **state,
        "matched_workflow_name": workflow.name,
        "matched_workflow_path": str(workflow.file_path),
        "matched_workflow_spec": spec_content,
        "confidence_score": confidence,
        "execution_status": "generating_agent"
    }


async def agent_generation_node(state: ChatbotState) -> ChatbotState:
    """
    Generate Python agent from matched workflow specification.

    Calls existing meta-agent pipeline (Phase 1 + Phase 2).
    """
    spec_content = state.get("matched_workflow_spec")
    if not spec_content:
        return {
            **state,
            "error_message": "No workflow specification to generate from",
            "execution_status": "failed"
        }

    try:
        client = MetaAgentClient()

        # Generate agent (both JSON and Python code)
        json_output, python_code = await client.generate_agent_from_spec(
            spec_content,
            provider="claude"  # Default to Claude for MVP
        )

        return {
            **state,
            "generated_json": json_output,
            "generated_agent_code": python_code,
            "execution_status": "extracting_parameters"
        }

    except Exception as e:
        return {
            **state,
            "error_message": f"Agent generation failed: {str(e)}",
            "execution_status": "failed"
        }


async def parameter_extraction_node(state: ChatbotState) -> ChatbotState:
    """
    Extract required parameters from generated JSON.

    Uses the inputs field from WorkflowSpec JSON.
    """
    json_output = state.get("generated_json")
    if not json_output:
        return {
            **state,
            "error_message": "No generated JSON to extract parameters from",
            "execution_status": "failed"
        }

    # Extract parameters from inputs field
    inputs = json_output.get("inputs", [])

    from chatbot.src.conversation.state import Parameter

    required_params = [
        Parameter(
            name=inp["name"],
            type=inp.get("type", "string"),
            description=inp.get("description"),
            required=True  # All inputs are required for MVP
        )
        for inp in inputs
    ]

    # Build user-friendly parameter prompt
    param_list = "\n".join(
        f"• {p.name} ({p.type})" + (f": {p.description}" if p.description else "")
        for p in required_params
    )

    response_message = Message(
        role="assistant",
        content=f"I can help with {state.get('matched_workflow_name')}. "
               f"Please provide the following information:\n{param_list}",
        timestamp=datetime.utcnow().isoformat()
    )

    return {
        **state,
        "required_parameters": required_params,
        "collected_parameters": {},
        "missing_parameters": [p.name for p in required_params],
        "current_parameter_index": 0,
        "messages": state.get("messages", []) + [response_message],
        "execution_status": "collecting_parameters"
    }


async def parameter_collection_node(state: ChatbotState) -> ChatbotState:
    """
    Collect parameters from user messages.

    For MVP: Simple key-value extraction.
    For production: Use LLM for natural language parsing.
    """
    # This is a placeholder for MVP
    # In Day 2, we'll implement conversational parameter collection

    return {
        **state,
        "execution_status": "ready_to_execute"
    }


async def validation_node(state: ChatbotState) -> ChatbotState:
    """
    Validate collected parameters against required types.

    For MVP: Basic type checking.
    For production: Business rule validation.
    """
    # Placeholder for Day 2 implementation

    return {
        **state,
        "execution_status": "validated"
    }


async def execution_node(state: ChatbotState) -> ChatbotState:
    """
    Execute generated agent with collected parameters.

    For MVP: Placeholder simulation.
    For Day 2: Actual sandboxed execution with streaming.
    """
    # Placeholder for Day 2 implementation

    response_message = Message(
        role="assistant",
        content="[Execution placeholder - to be implemented in Day 2]",
        timestamp=datetime.utcnow().isoformat()
    )

    return {
        **state,
        "messages": state.get("messages", []) + [response_message],
        "execution_status": "completed"
    }


async def result_formatting_node(state: ChatbotState) -> ChatbotState:
    """
    Format execution results for user-friendly display.
    """
    execution_result = state.get("execution_result")

    if execution_result:
        # Format result as human-readable message
        response_message = Message(
            role="assistant",
            content=f"Workflow completed successfully!\n\nResults:\n{execution_result}",
            timestamp=datetime.utcnow().isoformat()
        )
    else:
        # No result yet (placeholder mode)
        response_message = Message(
            role="assistant",
            content="Workflow processing initiated. Full execution to be implemented.",
            timestamp=datetime.utcnow().isoformat()
        )

    return {
        **state,
        "messages": state.get("messages", []) + [response_message],
        "execution_status": "completed"
    }
