"""
Agent execution orchestrator with timeout and error handling.

This module provides the main execution function that:
- Executes generated agents in a sandboxed environment
- Injects validated parameters
- Captures logs in real-time
- Handles timeouts and errors gracefully
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass

from .sandbox import (
    create_safe_namespace,
    execute_in_sandbox,
    instantiate_agent
)
from .streaming import LogInterceptor, create_log_callback


@dataclass
class ExecutionResult:
    """Result of agent execution."""

    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    logs: List[str] = None
    execution_time: float = 0.0

    def __post_init__(self):
        """Initialize logs if None."""
        if self.logs is None:
            self.logs = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "error_type": self.error_type,
            "logs": self.logs,
            "execution_time": self.execution_time
        }


def execute_agent_sync(
    agent_code: str,
    parameters: Dict[str, Any],
    log_callback: Optional[Callable[[str], None]] = None,
    timeout: Optional[float] = None
) -> ExecutionResult:
    """
    Execute agent synchronously with timeout and log capture.

    Args:
        agent_code: Generated Python agent code
        parameters: Validated parameters to pass to agent
        log_callback: Optional callback for real-time log streaming
        timeout: Execution timeout in seconds (None = no timeout)

    Returns:
        ExecutionResult with success status, result, or error
    """
    start_time = time.time()
    captured_logs: List[str] = []

    # Create log callback that appends to list
    def log_handler(message: str):
        captured_logs.append(message)
        if log_callback:
            log_callback(message)

    try:
        # Create sandboxed namespace
        namespace = create_safe_namespace()

        # Execute agent code in sandbox with log interception
        with LogInterceptor(callback=log_handler, sanitize=True):
            namespace = execute_in_sandbox(agent_code, namespace)

            # Find and instantiate agent class
            agent_instance = instantiate_agent(namespace)

            # Execute agent with parameters
            result = agent_instance.execute(**parameters)

        execution_time = time.time() - start_time

        return ExecutionResult(
            success=True,
            result=result,
            logs=captured_logs,
            execution_time=execution_time
        )

    except SyntaxError as e:
        execution_time = time.time() - start_time
        return ExecutionResult(
            success=False,
            error=f"Syntax error in generated code: {str(e)}",
            error_type="SyntaxError",
            logs=captured_logs,
            execution_time=execution_time
        )

    except ValueError as e:
        # Agent instantiation or parameter errors
        execution_time = time.time() - start_time
        return ExecutionResult(
            success=False,
            error=str(e),
            error_type="ValueError",
            logs=captured_logs,
            execution_time=execution_time
        )

    except TypeError as e:
        # Parameter type mismatch
        execution_time = time.time() - start_time
        return ExecutionResult(
            success=False,
            error=f"Parameter type error: {str(e)}",
            error_type="TypeError",
            logs=captured_logs,
            execution_time=execution_time
        )

    except Exception as e:
        # Any other runtime error
        execution_time = time.time() - start_time
        return ExecutionResult(
            success=False,
            error=f"Runtime error: {type(e).__name__}: {str(e)}",
            error_type=type(e).__name__,
            logs=captured_logs,
            execution_time=execution_time
        )


async def execute_agent_async(
    agent_code: str,
    parameters: Dict[str, Any],
    log_callback: Optional[Callable[[str], None]] = None,
    timeout: float = 30.0
) -> ExecutionResult:
    """
    Execute agent asynchronously with timeout.

    This is the main execution function for the chatbot. It runs
    the agent in a separate thread to enable timeout without
    blocking the event loop.

    Args:
        agent_code: Generated Python agent code
        parameters: Validated parameters to pass to agent
        log_callback: Optional callback for real-time log streaming
        timeout: Execution timeout in seconds (default: 30s)

    Returns:
        ExecutionResult with success status, result, or error

    Note:
        For MVP, we execute synchronously in a thread. For production,
        consider using subprocess with proper isolation.
    """
    start_time = time.time()

    try:
        # Run synchronous execution in thread pool with timeout
        result = await asyncio.wait_for(
            asyncio.to_thread(
                execute_agent_sync,
                agent_code,
                parameters,
                log_callback,
                timeout
            ),
            timeout=timeout
        )

        return result

    except asyncio.TimeoutError:
        execution_time = time.time() - start_time
        return ExecutionResult(
            success=False,
            error=f"Execution timed out after {timeout} seconds",
            error_type="TimeoutError",
            logs=[f"⏱️ Execution exceeded {timeout}s timeout"],
            execution_time=execution_time
        )

    except Exception as e:
        execution_time = time.time() - start_time
        return ExecutionResult(
            success=False,
            error=f"Unexpected error during async execution: {str(e)}",
            error_type=type(e).__name__,
            logs=[],
            execution_time=execution_time
        )


async def execute_agent_safely(
    agent_code: str,
    parameters: Dict[str, Any],
    log_callback: Optional[Callable[[str], None]] = None,
    timeout: float = 30.0
) -> ExecutionResult:
    """
    Main entry point for safe agent execution.

    This is the function that should be called from the LangGraph node.

    Args:
        agent_code: Generated Python agent code
        parameters: Validated parameters to pass to agent
        log_callback: Optional callback for real-time log streaming
        timeout: Execution timeout in seconds (default: 30s)

    Returns:
        ExecutionResult with execution outcome
    """
    return await execute_agent_async(
        agent_code=agent_code,
        parameters=parameters,
        log_callback=log_callback,
        timeout=timeout
    )


def validate_execution_inputs(
    agent_code: Optional[str],
    parameters: Optional[Dict[str, Any]]
) -> Optional[str]:
    """
    Validate inputs before execution.

    Args:
        agent_code: Agent code to validate
        parameters: Parameters to validate

    Returns:
        Error message if invalid, None if valid
    """
    if not agent_code:
        return "No agent code provided"

    if not isinstance(agent_code, str):
        return "Agent code must be a string"

    if not agent_code.strip():
        return "Agent code is empty"

    if parameters is None:
        return "Parameters cannot be None (use empty dict for no parameters)"

    if not isinstance(parameters, dict):
        return "Parameters must be a dictionary"

    return None
