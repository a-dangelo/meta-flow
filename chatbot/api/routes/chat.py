"""
Chat API routes for conversational workflow automation.

Handles chat messages, session management, and conversation state.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict
from datetime import datetime
import logging

from chatbot.api.models import (
    ChatMessageRequest,
    ChatMessageResponse,
    SessionStateResponse,
    ParameterInfo,
    ExecutionResult
)
from chatbot.src.conversation.graph_hybrid import run_hybrid_chatbot
from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== SESSION STORAGE ====================
# MVP: In-memory session storage
# Production: Use Redis or database

_sessions: Dict[str, Dict] = {}


def get_session(session_id: str) -> Dict:
    """
    Get session data by ID.

    Args:
        session_id: Session identifier

    Returns:
        Session data dictionary

    Raises:
        HTTPException: If session not found
    """
    if session_id not in _sessions:
        # Initialize new session
        _sessions[session_id] = {
            "session_id": session_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "conversation_history": [],
            "state": {}
        }

    return _sessions[session_id]


def update_session(session_id: str, state: Dict) -> None:
    """
    Update session with new state.

    Args:
        session_id: Session identifier
        state: Updated state dictionary
    """
    session = get_session(session_id)
    session["state"] = state
    session["updated_at"] = datetime.utcnow()


def delete_session(session_id: str) -> bool:
    """
    Delete session by ID.

    Args:
        session_id: Session identifier

    Returns:
        True if deleted, False if not found
    """
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


# ==================== API ENDPOINTS ====================

@router.post("/message", response_model=ChatMessageResponse)
async def send_message(request: ChatMessageRequest):
    """
    Process a chat message and return agent response.

    This is the main endpoint for conversational interaction.
    The chatbot will:
    1. Match the user's intent to a workflow
    2. Generate an agent for that workflow
    3. Extract required parameters
    4. Collect parameter values conversationally
    5. Validate and execute the workflow
    """
    try:
        logger.info(
            f"Processing message for session {request.session_id}: "
            f"{request.message[:50]}..."
        )

        # Get session and conversation history
        session = get_session(request.session_id)
        conversation_history = session.get("conversation_history", [])
        previous_state = session.get("state")

        # Run chatbot
        result = await run_hybrid_chatbot(
            user_message=request.message,
            session_id=request.session_id,
            conversation_history=conversation_history,
            previous_state=previous_state,
            user_id=request.user_id,
            access_level=request.access_level
        )

        # Update session
        update_session(request.session_id, result)

        # Extract messages for response
        messages = result.get("messages", [])
        if messages:
            # Update conversation history
            session["conversation_history"] = messages

            # Get last AI message
            ai_messages = [m for m in messages if isinstance(m, AIMessage)]
            last_message = ai_messages[-1].content if ai_messages else None
        else:
            last_message = None

        # Build response
        response = ChatMessageResponse(
            session_id=request.session_id,
            status=result.get("execution_status", "pending"),
            message=last_message,
            matched_workflow=result.get("matched_workflow_name"),
            search_confidence=result.get("search_confidence"),
            required_parameters=[
                ParameterInfo(**p) for p in result.get("required_parameters", [])
            ] if result.get("required_parameters") else None,
            collected_parameters=result.get("collected_parameters"),
            pending_parameters=result.get("pending_parameters"),
            validation_errors=result.get("validation_errors"),
            execution_result=ExecutionResult(**result["execution_result"])
            if result.get("execution_result") else None,
            python_code=result.get("python_code"),  # Generated agent code
            error_message=result.get("error_message"),
            node_timings=result.get("node_timings")
        )

        logger.info(
            f"Response for session {request.session_id}: "
            f"status={response.status}, workflow={response.matched_workflow}"
        )

        return response

    except Exception as e:
        logger.error(
            f"Error processing message for session {request.session_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=SessionStateResponse)
async def get_session_state(session_id: str):
    """
    Get current state of a conversation session.

    Returns the full session state including workflow match,
    parameters, execution status, etc.
    """
    try:
        session = get_session(session_id)
        state = session.get("state", {})

        response = SessionStateResponse(
            session_id=session_id,
            user_id=state.get("user_id", "anonymous"),
            access_level=state.get("access_level", "employee"),
            status=state.get("execution_status", "pending"),
            matched_workflow=state.get("matched_workflow_name"),
            search_confidence=state.get("search_confidence"),
            required_parameters=[
                ParameterInfo(**p) for p in state.get("required_parameters", [])
            ] if state.get("required_parameters") else None,
            collected_parameters=state.get("collected_parameters"),
            execution_result=ExecutionResult(**state["execution_result"])
            if state.get("execution_result") else None,
            python_code=state.get("python_code"),  # Generated agent code
            error_message=state.get("error_message"),
            message_count=len(session.get("conversation_history", [])),
            created_at=session.get("created_at"),
            updated_at=session.get("updated_at")
        )

        return response

    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session state: {str(e)}"
        )


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """
    Clear a conversation session.

    Deletes all session data including conversation history
    and execution state.
    """
    try:
        deleted = delete_session(session_id)

        if deleted:
            logger.info(f"Deleted session {session_id}")
            return {
                "success": True,
                "message": f"Session {session_id} cleared"
            }
        else:
            logger.warning(f"Session {session_id} not found for deletion")
            return {
                "success": True,
                "message": f"Session {session_id} not found (already cleared)"
            }

    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.get("/sessions")
async def list_sessions():
    """
    List all active sessions (for debugging/admin).

    MVP: Returns basic session info.
    Production: Add pagination, filtering, auth.
    """
    return {
        "total": len(_sessions),
        "sessions": [
            {
                "session_id": sid,
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at"),
                "message_count": len(session.get("conversation_history", [])),
                "status": session.get("state", {}).get("execution_status", "unknown")
            }
            for sid, session in _sessions.items()
        ]
    }
