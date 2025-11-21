"""LLM-powered conversation graph (ReAct agent with tools)."""

from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from chatbot.src.conversation.agent import create_chatbot_agent, run_agent_turn


class ConversationState(TypedDict):
    """
    Simplified state for LLM-powered conversation.

    The LLM agent handles all orchestration internally using tools.
    """
    # Conversation
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    session_id: str
    access_level: str

    # Tracking (optional)
    workflow_in_progress: str | None
    parameters_collected: dict


async def chatbot_node(state: ConversationState) -> ConversationState:
    """
    Main LLM agent node - handles entire conversation with tool calling.

    The agent decides when to:
    - Search for workflows
    - Generate agents
    - Collect parameters
    - Execute workflows
    """
    # Create agent
    agent = create_chatbot_agent()

    # Get latest user message
    messages = state["messages"]
    if not messages:
        return state

    # Run agent turn
    agent_response, updated_messages = await run_agent_turn(
        agent,
        messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1]),
        messages[:-1]  # Previous conversation history
    )

    return {
        **state,
        "messages": updated_messages
    }


def create_conversational_graph():
    """
    Create simplified LLM-powered conversation graph.

    Architecture:
    START → Chatbot Agent Node → END

    The agent node handles all logic using tool calling:
    - Searches workflows when needed
    - Generates agents when workflow found
    - Collects parameters through conversation
    - Executes when parameters are complete
    """
    graph = StateGraph(ConversationState)

    # Single agent node handles everything
    graph.add_node("chatbot", chatbot_node)

    # Simple flow
    graph.set_entry_point("chatbot")
    graph.add_edge("chatbot", END)

    return graph.compile()


async def run_conversational_chatbot(
    user_message: str,
    session_id: str,
    conversation_history: list[BaseMessage] | None = None,
    user_id: str = "anonymous",
    access_level: str = "employee"
) -> ConversationState:
    """
    Run conversational chatbot for a single turn.

    Args:
        user_message: User's message
        session_id: Session identifier
        conversation_history: Previous messages (optional)
        user_id: User identifier
        access_level: User's access level

    Returns:
        Updated conversation state with agent response
    """
    from langchain_core.messages import HumanMessage

    # Create graph
    graph = create_conversational_graph()

    # Initialize state
    messages = conversation_history or []
    messages.append(HumanMessage(content=user_message))

    initial_state: ConversationState = {
        "messages": messages,
        "user_id": user_id,
        "session_id": session_id,
        "access_level": access_level,
        "workflow_in_progress": None,
        "parameters_collected": {}
    }

    # Run graph
    config = {"configurable": {"thread_id": session_id}}
    result = await graph.ainvoke(initial_state, config=config)

    return result
