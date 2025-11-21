"""
Log streaming and interception for agent execution.

This module provides real-time log capture during agent execution,
with credential sanitization and structured formatting.
"""

import sys
import re
from typing import Callable, List, Optional
from io import StringIO


# Patterns to detect and sanitize credentials in logs
CREDENTIAL_PATTERNS = [
    (re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE), "api_key=***"),
    (re.compile(r'token["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE), "token=***"),
    (re.compile(r'password["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE), "password=***"),
    (re.compile(r'secret["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE), "secret=***"),
    (re.compile(r'bearer\s+([a-zA-Z0-9\-._~+/]+=*)', re.IGNORECASE), "bearer ***"),
    (re.compile(r'sk-[a-zA-Z0-9]{20,}', re.IGNORECASE), "sk-***"),  # Anthropic/OpenAI keys
]


def sanitize_log_message(message: str) -> str:
    """
    Remove credentials from log messages.

    Args:
        message: Raw log message

    Returns:
        Sanitized message with credentials replaced
    """
    sanitized = message

    for pattern, replacement in CREDENTIAL_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


class LogInterceptor:
    """
    Context manager to intercept and stream execution logs.

    Captures stdout/stderr during agent execution and forwards
    to a callback function for real-time streaming.

    Example:
        def my_callback(log_line: str):
            print(f"LOG: {log_line}")

        with LogInterceptor(my_callback):
            print("This will be intercepted")
    """

    def __init__(
        self,
        callback: Optional[Callable[[str], None]] = None,
        sanitize: bool = True,
        capture_stderr: bool = True
    ):
        """
        Initialize log interceptor.

        Args:
            callback: Function to call for each log line (optional)
            sanitize: Whether to sanitize credentials (default: True)
            capture_stderr: Whether to also capture stderr (default: True)
        """
        self.callback = callback
        self.sanitize = sanitize
        self.capture_stderr = capture_stderr

        # Store original streams
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        # Buffer for captured logs
        self.captured_logs: List[str] = []

        # Create string buffers for interception
        self.stdout_buffer = StringIO()
        self.stderr_buffer = StringIO() if capture_stderr else None

    def write(self, message: str):
        """Write method for stream-like interface."""
        if message and message.strip():
            # Sanitize if enabled
            if self.sanitize:
                message = sanitize_log_message(message)

            # Store in buffer
            self.captured_logs.append(message)

            # Call callback if provided
            if self.callback:
                self.callback(message)

        # Always write to original stdout for debugging
        self.original_stdout.write(message)

    def flush(self):
        """Flush method for stream-like interface."""
        self.original_stdout.flush()
        if self.original_stderr:
            self.original_stderr.flush()

    def __enter__(self):
        """Enter context manager."""
        # Replace stdout
        sys.stdout = self

        # Replace stderr if enabled
        if self.capture_stderr:
            sys.stderr = self

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and restore streams."""
        # Restore original streams
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

        return False  # Don't suppress exceptions

    def get_logs(self) -> List[str]:
        """
        Get all captured logs.

        Returns:
            List of log messages
        """
        return self.captured_logs.copy()

    def get_logs_as_string(self) -> str:
        """
        Get all captured logs as a single string.

        Returns:
            Concatenated log messages
        """
        return "".join(self.captured_logs)


class StreamCollector:
    """
    Simpler log collector without callback (for testing).

    Example:
        collector = StreamCollector()
        with collector:
            print("Test log")

        logs = collector.get_logs()
    """

    def __init__(self, sanitize: bool = True):
        """
        Initialize stream collector.

        Args:
            sanitize: Whether to sanitize credentials
        """
        self.interceptor = LogInterceptor(callback=None, sanitize=sanitize)

    def __enter__(self):
        """Enter context manager."""
        return self.interceptor.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        return self.interceptor.__exit__(exc_type, exc_val, exc_tb)

    def get_logs(self) -> List[str]:
        """Get captured logs."""
        return self.interceptor.get_logs()

    def get_logs_as_string(self) -> str:
        """Get logs as string."""
        return self.interceptor.get_logs_as_string()


def create_log_callback(log_list: List[str]) -> Callable[[str], None]:
    """
    Create a callback function that appends logs to a list.

    Useful for collecting logs in a stateful way.

    Args:
        log_list: List to append log messages to

    Returns:
        Callback function
    """
    def callback(message: str):
        log_list.append(message)

    return callback
