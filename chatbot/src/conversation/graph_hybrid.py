"""
Hybrid decomposition LangGraph for chatbot conversations.

Combines deterministic nodes (search, extraction, validation) with
LLM-powered nodes (clarification, value collection).
"""

import time
from typing import Dict
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage

from chatbot.src.conversation.state import WorkflowState
from chatbot.src.workflow_matching.repository import WorkflowRepository
from chatbot.src.integration.meta_agent_client import MetaAgentClient
from chatbot.src.parameter_handling.extractor import (
    extract_parameters_from_json,
    get_required_parameters,
    format_parameter_for_prompt
)
from chatbot.src.parameter_handling.collector import (
    create_collection_prompt,
    extract_values_from_message,
    create_missing_parameters_prompt
)
from chatbot.src.parameter_handling.validator import (
    validate_all_parameters,
    get_missing_required_parameters
)
from chatbot.src.execution.orchestrator import (
    execute_agent_safely,
    validate_execution_inputs
)


# Global repository singleton
_repository = None


def get_repository() -> WorkflowRepository:
    """
    Get or create workflow repository singleton.

    Uses BGE-small-en-v1.5 model with 60% confidence threshold for
    efficient semantic search with minimal disk usage.
    """
    global _repository
    if _repository is None:
        workflows_dir = Path(__file__).parent.parent.parent / "workflows"
        _repository = WorkflowRepository(
            workflows_dir,
            model_name="BAAI/bge-small-en-v1.5",
            confidence_threshold=0.60
        )
    return _repository


# ==================== DETERMINISTIC NODES ====================

def search_workflows_node(state: WorkflowState) -> Dict:
    """
    Deterministic semantic search for workflow matching.

    Uses sentence-transformer embeddings and cosine similarity.
    No LLM involved - pure mathematical operation.
    """
    start_time = time.time()

    user_input = state.get("user_input", "")
    access_level = state.get("access_level", "employee")

    repo = get_repository()
    workflow, confidence = repo.find_by_intent(user_input, access_level)

    elapsed = time.time() - start_time

    if workflow and confidence >= 0.60:
        # High confidence match (BGE-M3 threshold: 60%)
        return {
            "matched_workflow_name": workflow.name,
            "matched_workflow_path": str(workflow.file_path),
            "search_confidence": confidence,
            "requires_clarification": False,
            "node_timings": {**state.get("node_timings", {}), "search": elapsed}
        }
    else:
        # Low confidence - need clarification
        all_workflows = repo.list_all_workflows(access_level)
        candidates = [
            {
                "name": wf.name,
                "description": wf.description,
                "category": wf.category
            }
            for wf in all_workflows[:5]
        ]

        return {
            "search_confidence": confidence if workflow else 0.0,
            "search_candidates": candidates,
            "requires_clarification": True,
            "node_timings": {**state.get("node_timings", {}), "search": elapsed}
        }


async def generate_agent_node(state: WorkflowState) -> Dict:
    """
    Call existing meta-agent pipeline to generate agent.

    Returns both JSON AST and Python code.
    """
    start_time = time.time()

    workflow_path = state.get("matched_workflow_path")
    if not workflow_path:
        return {
            "error_message": "No workflow selected",
            "execution_status": "failed"
        }

    # Load workflow spec
    spec_content = Path(workflow_path).read_text()

    # Call meta-agent
    client = MetaAgentClient()

    try:
        json_ast, python_code = await client.generate_agent_from_spec(
            spec_content,
            provider="claude"
        )

        elapsed = time.time() - start_time

        return {
            "json_ast": json_ast,
            "python_code": python_code,
            "node_timings": {**state.get("node_timings", {}), "generate": elapsed}
        }

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "error_message": f"Agent generation failed: {str(e)}",
            "execution_status": "failed",
            "node_timings": {**state.get("node_timings", {}), "generate": elapsed}
        }


def extract_parameters_node(state: WorkflowState) -> Dict:
    """
    Deterministic parameter extraction from JSON AST.

    No LLM needed - direct JSON parsing provides 100% accuracy.
    """
    start_time = time.time()

    json_ast = state.get("json_ast")
    if not json_ast:
        return {"error_message": "No JSON AST available"}

    # Extract parameters from JSON
    parameters = extract_parameters_from_json(json_ast)
    required = get_required_parameters(parameters)

    elapsed = time.time() - start_time

    return {
        "required_parameters": parameters,
        "pending_parameters": [p["name"] for p in required],
        "collected_parameters": {},
        "node_timings": {**state.get("node_timings", {}), "extract": elapsed}
    }


def validate_parameters_node(state: WorkflowState) -> Dict:
    """
    Deterministic validation against JSON schema.

    Type checking and constraint validation without LLM.
    """
    start_time = time.time()

    parameters = state.get("required_parameters", [])
    collected = state.get("collected_parameters", {})

    all_valid, validated_values, errors = validate_all_parameters(
        parameters, collected
    )

    elapsed = time.time() - start_time

    if all_valid:
        return {
            "collected_parameters": validated_values,
            "validation_errors": None,
            "execution_status": "validated",
            "node_timings": {**state.get("node_timings", {}), "validate": elapsed}
        }
    else:
        return {
            "validation_errors": errors,
            "execution_status": "validation_failed",
            "node_timings": {**state.get("node_timings", {}), "validate": elapsed}
        }


# ==================== LLM-POWERED NODES ====================

async def clarify_workflow_node(state: WorkflowState) -> Dict:
    """
    LLM-powered workflow clarification (only when confidence < 0.75).

    Asks user to select from ambiguous candidates.
    """
    candidates = state.get("search_candidates", [])

    if not candidates:
        return {"error_message": "No workflow candidates available"}

    # Format candidates for display
    options = "\n".join([
        f"{i+1}. **{c['name']}**: {c.get('description', '')}"
        for i, c in enumerate(candidates)
    ])

    message = f"""I found multiple workflows that might match. Which one would you like?

{options}

Please respond with the number (1-{len(candidates)}) or describe what you want to do."""

    # Add to conversation
    messages = state.get("messages", [])
    messages.append(AIMessage(content=message))

    return {
        "messages": messages,
        "execution_status": "awaiting_clarification"
    }


async def collect_parameters_node(state: WorkflowState) -> Dict:
    """
    LLM-assisted parameter value collection.

    Extracts values from natural language, grounded by JSON schema.
    """
    start_time = time.time()

    parameters = state.get("required_parameters", [])
    collected = state.get("collected_parameters", {})
    messages = state.get("messages", [])

    # Check if this is first collection or follow-up
    if not collected:
        # First time - ask for all parameters
        prompt = create_collection_prompt(parameters)
        messages.append(AIMessage(content=prompt))

        elapsed = time.time() - start_time
        return {
            "messages": messages,
            "execution_status": "collecting_parameters",
            "node_timings": {**state.get("node_timings", {}), "collect": elapsed}
        }

    else:
        # Extract values from latest user message
        if messages and isinstance(messages[-1], HumanMessage):
            user_message = messages[-1].content

            # Use LLM to extract values
            extracted = await extract_values_from_message(
                user_message,
                parameters
            )

            # Merge with existing collected values
            collected.update(extracted)

            # Check what's still missing
            missing = get_missing_required_parameters(parameters, collected)

            elapsed = time.time() - start_time

            if not missing:
                # All parameters collected
                return {
                    "collected_parameters": collected,
                    "pending_parameters": [],
                    "execution_status": "ready_to_validate",
                    "node_timings": {**state.get("node_timings", {}), "collect": elapsed}
                }
            else:
                # Still need more parameters
                missing_params = [p for p in parameters if p["name"] in missing]
                prompt = create_missing_parameters_prompt(missing_params)
                messages.append(AIMessage(content=prompt))

                return {
                    "collected_parameters": collected,
                    "pending_parameters": missing,
                    "messages": messages,
                    "execution_status": "collecting_parameters",
                    "node_timings": {**state.get("node_timings", {}), "collect": elapsed}
                }

        else:
            elapsed = time.time() - start_time
            return {
                "error_message": "No user message to extract from",
                "node_timings": {**state.get("node_timings", {}), "collect": elapsed}
            }


async def execute_workflow_node(state: WorkflowState) -> Dict:
    """
    Execute the generated workflow agent in sandboxed environment.

    Uses the execution orchestrator to safely run the agent with
    validated parameters, capturing logs and handling errors.
    """
    start_time = time.time()

    workflow_name = state.get("matched_workflow_name", "unknown")
    python_code = state.get("python_code")
    parameters = state.get("collected_parameters", {})

    # Validate inputs
    error = validate_execution_inputs(python_code, parameters)
    if error:
        elapsed = time.time() - start_time
        return {
            "error_message": error,
            "execution_status": "failed",
            "node_timings": {**state.get("node_timings", {}), "execute": elapsed}
        }

    # Execute agent safely
    execution_logs = []

    def log_callback(message: str):
        """Capture logs during execution."""
        execution_logs.append(message)

    try:
        result = await execute_agent_safely(
            agent_code=python_code,
            parameters=parameters,
            log_callback=log_callback,
            timeout=30.0
        )

        elapsed = time.time() - start_time

        if result.success:
            # Generate reference ID for tracking
            import random
            reference_id = f"REF-{random.randint(1000, 9999)}"

            execution_result = {
                "workflow": workflow_name,
                "status": "completed",
                "reference_id": reference_id,
                "result": result.result,
                "parameters": parameters,
                "logs": result.logs,
                "execution_time": result.execution_time
            }

            return {
                "execution_result": execution_result,
                "execution_logs": result.logs,
                "execution_status": "completed",
                "node_timings": {**state.get("node_timings", {}), "execute": elapsed}
            }
        else:
            # Execution failed
            return {
                "error_message": result.error,
                "error_type": result.error_type,
                "execution_logs": result.logs,
                "execution_status": "failed",
                "node_timings": {**state.get("node_timings", {}), "execute": elapsed}
            }

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "error_message": f"Unexpected error during execution: {str(e)}",
            "execution_logs": execution_logs,
            "execution_status": "failed",
            "node_timings": {**state.get("node_timings", {}), "execute": elapsed}
        }


# ==================== ROUTING FUNCTIONS ====================

def route_after_search(state: WorkflowState) -> str:
    """Route after workflow search based on confidence."""
    if state.get("requires_clarification"):
        return "clarify"
    return "generate"


def route_after_collection(state: WorkflowState) -> str:
    """Route after parameter collection."""
    pending = state.get("pending_parameters", [])

    if not pending:
        return "validate"
    return "collect"  # Loop back for more collection


def route_after_validation(state: WorkflowState) -> str:
    """Route after validation."""
    errors = state.get("validation_errors")

    if errors:
        return "collect"  # Go back to fix errors
    return "execute"


# ==================== GRAPH CONSTRUCTION ====================

def create_hybrid_graph():
    """
    Create hybrid decomposition graph.

    Architecture:
    START → search (det) → clarify (LLM)? → generate (meta-agent)
         → extract (det) → collect (LLM) → validate (det) → execute → END
    """
    graph = StateGraph(WorkflowState)

    # Add nodes
    graph.add_node("search", search_workflows_node)
    graph.add_node("clarify", clarify_workflow_node)
    graph.add_node("generate", generate_agent_node)
    graph.add_node("extract", extract_parameters_node)
    graph.add_node("collect", collect_parameters_node)
    graph.add_node("validate", validate_parameters_node)
    graph.add_node("execute", execute_workflow_node)

    # Define edges
    graph.add_edge(START, "search")

    # Conditional routing after search
    graph.add_conditional_edges(
        "search",
        route_after_search,
        {"clarify": "clarify", "generate": "generate"}
    )

    graph.add_edge("clarify", "generate")  # After clarification, generate
    graph.add_edge("generate", "extract")  # After generation, extract params

    # After extraction, start collection
    graph.add_edge("extract", "collect")

    # Conditional routing after collection
    graph.add_conditional_edges(
        "collect",
        route_after_collection,
        {"validate": "validate", "collect": "collect"}
    )

    # Conditional routing after validation
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {"collect": "collect", "execute": "execute"}
    )

    graph.add_edge("execute", END)

    return graph.compile()


# ==================== MAIN ENTRY POINT ====================

async def run_hybrid_chatbot(
    user_message: str,
    session_id: str,
    conversation_history: list = None,
    user_id: str = "anonymous",
    access_level: str = "employee"
) -> WorkflowState:
    """
    Run hybrid chatbot for a single turn.

    Args:
        user_message: User's message
        session_id: Session identifier
        conversation_history: Previous messages (optional)
        user_id: User identifier
        access_level: User's access level (employee, manager, hr, admin)

    Returns:
        Updated workflow state
    """
    graph = create_hybrid_graph()

    # Initialize state
    messages = conversation_history or []
    messages.append(HumanMessage(content=user_message))

    initial_state: WorkflowState = {
        "user_id": user_id,
        "session_id": session_id,
        "access_level": access_level,
        "user_input": user_message,
        "messages": messages,
        "search_confidence": 0.0,
        "requires_clarification": False,
        "collected_parameters": {},
        "pending_parameters": [],
        "execution_status": "pending",
        "node_timings": {}
    }

    # Run graph
    result = await graph.ainvoke(initial_state)

    return result
