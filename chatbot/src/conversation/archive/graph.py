"""LangGraph state machine for chatbot conversation flow."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from chatbot.src.conversation.state import ChatbotState
from chatbot.src.conversation.nodes import (
    intent_recognition_node,
    workflow_matching_node,
    agent_generation_node,
    parameter_extraction_node,
    parameter_collection_node,
    validation_node,
    execution_node,
    result_formatting_node
)


def should_continue_collection(state: ChatbotState) -> str:
    """
    Routing function for parameter collection.

    Returns:
    - "collect": More parameters needed
    - "validate": All parameters collected
    - "execute": Parameters validated (skip validation for MVP)
    """
    missing = state.get("missing_parameters", [])

    if missing:
        return "collect"

    # For MVP, skip validation and go straight to execution
    return "execute"


def should_retry(state: ChatbotState) -> str:
    """
    Routing function for error recovery.

    Returns:
    - "retry": Retry workflow matching
    - "end": Max retries reached or unrecoverable error
    """
    retry_count = state.get("retry_count", 0)
    max_retries = 2

    if state.get("should_retry") and retry_count < max_retries:
        return "retry"

    return "end"


def create_chatbot_graph(checkpoint_path: str = ".checkpoints/chatbot.db", use_checkpointing: bool = False):
    """
    Create compiled chatbot state machine.

    Graph structure:
    START → Intent Recognition → Workflow Matching → Agent Generation
                                        ↓
                                Parameter Extraction
                                        ↓
                                Parameter Collection ←─┐
                                        ↓              │
                                Validation (skip MVP)  │
                                        ↓              │
                                    [check]  ──────────┘
                                        ↓
                                Execution → Result Formatting → END

    Args:
        checkpoint_path: Path to SQLite checkpoint database
        use_checkpointing: Enable state persistence (default: False for MVP)

    Returns:
        Compiled LangGraph state machine
    """
    # Create state graph
    graph = StateGraph(ChatbotState)

    # Add nodes
    graph.add_node("intent_recognition", intent_recognition_node)
    graph.add_node("workflow_matching", workflow_matching_node)
    graph.add_node("agent_generation", agent_generation_node)
    graph.add_node("parameter_extraction", parameter_extraction_node)
    graph.add_node("parameter_collection", parameter_collection_node)
    graph.add_node("validation", validation_node)
    graph.add_node("execution", execution_node)
    graph.add_node("result_formatting", result_formatting_node)

    # Define edges (conversation flow)
    graph.set_entry_point("intent_recognition")

    # Linear flow from intent to parameter extraction
    graph.add_edge("intent_recognition", "workflow_matching")
    graph.add_edge("workflow_matching", "agent_generation")
    graph.add_edge("agent_generation", "parameter_extraction")

    # Parameter collection loop
    graph.add_edge("parameter_extraction", "parameter_collection")
    graph.add_conditional_edges(
        "parameter_collection",
        should_continue_collection,
        {
            "collect": "parameter_collection",  # Loop back for more params
            "validate": "validation",           # Validate collected params
            "execute": "execution"              # Skip validation (MVP)
        }
    )

    # Validation to execution
    graph.add_edge("validation", "execution")

    # Execution to result formatting
    graph.add_edge("execution", "result_formatting")

    # Result formatting to end
    graph.add_edge("result_formatting", END)

    # Compile with optional checkpointing
    if use_checkpointing:
        import sqlite3
        from pathlib import Path

        # Create checkpoint directory if needed
        Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)

        # Create connection
        conn = sqlite3.connect(checkpoint_path, check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        compiled_graph = graph.compile(checkpointer=checkpointer)
    else:
        # No checkpointing for MVP
        compiled_graph = graph.compile()

    return compiled_graph


async def run_chatbot(
    user_message: str,
    session_id: str,
    user_id: str = "anonymous",
    access_level: str = "employee"
) -> ChatbotState:
    """
    Run chatbot conversation for a single user message.

    Args:
        user_message: User's message text
        session_id: Unique session identifier
        user_id: User identifier
        access_level: User's access level (employee, manager, hr, admin)

    Returns:
        Updated conversation state
    """
    from datetime import datetime
    from chatbot.src.conversation.state import Message

    # Create compiled graph
    graph = create_chatbot_graph()

    # Initialize state with user message
    initial_state: ChatbotState = {
        "user_id": user_id,
        "session_id": session_id,
        "access_level": access_level,
        "messages": [
            Message(
                role="user",
                content=user_message,
                timestamp=datetime.utcnow().isoformat()
            )
        ],
        "execution_status": "idle",
        "collected_parameters": {},
        "missing_parameters": [],
        "current_parameter_index": 0,
        "retry_count": 0,
        "should_retry": False
    }

    # Run graph
    config = {"configurable": {"thread_id": session_id}}
    result = await graph.ainvoke(initial_state, config=config)

    return result
