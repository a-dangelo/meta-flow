"""
Comprehensive test logging system for meta-agent v2.

Captures detailed test execution information including:
- Request/response data
- Execution metadata
- Error details
- Performance metrics

Organizes logs in structured directories for easy debugging and analysis.
"""

import json
import hashlib
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class TestRunMetadata:
    """Metadata for a single test run."""
    timestamp: str
    test_id: str
    provider: str
    model: str
    input_file_path: str
    input_file_size: int
    input_content_hash: str
    configuration: Dict[str, Any]
    exit_status: str  # "success", "failure", "error"
    exit_code: int
    execution_time_ms: int
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    validation_errors: Optional[List[str]] = None
    retry_count: int = 0
    confidence_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class TestLogger:
    """Manages structured logging for test runs."""

    def __init__(self, base_log_dir: str = "logs"):
        """
        Initialize test logger.

        Args:
            base_log_dir: Base directory for all logs (default: "logs/")
        """
        self.base_log_dir = Path(base_log_dir)
        self.test_runs_dir = self.base_log_dir / "test-runs"
        self.summary_file = self.base_log_dir / "summary.jsonl"

        # Create directories
        self.base_log_dir.mkdir(exist_ok=True)
        self.test_runs_dir.mkdir(exist_ok=True)

        # Current test run state
        self.current_run_dir: Optional[Path] = None
        self.current_metadata: Optional[TestRunMetadata] = None
        self.start_time: Optional[datetime] = None

        # Captured stdout/stderr
        self.stdout_capture = []
        self.stderr_capture = []

    def start_test_run(
        self,
        provider: str,
        model: str,
        input_file_path: str,
        configuration: Dict[str, Any]
    ) -> str:
        """
        Start a new test run and create log directory.

        Args:
            provider: LLM provider name (e.g., "gemini", "aimlapi")
            model: Model identifier
            input_file_path: Path to input specification file
            configuration: Test configuration parameters

        Returns:
            Test run ID
        """
        # Generate test run ID
        self.start_time = datetime.now(timezone.utc)
        timestamp_str = self.start_time.strftime("%Y-%m-%d_%H-%M-%S")
        test_id = f"{timestamp_str}_{provider}_{model.replace('/', '-')}"

        # Create run directory
        self.current_run_dir = self.test_runs_dir / test_id
        self.current_run_dir.mkdir(exist_ok=True)

        # Read and hash input file
        input_path = Path(input_file_path)
        input_content = input_path.read_text(encoding='utf-8')
        content_hash = hashlib.sha256(input_content.encode('utf-8')).hexdigest()[:16]

        # Copy input file to log directory
        (self.current_run_dir / "input_file.txt").write_text(input_content, encoding='utf-8')

        # Initialize metadata
        self.current_metadata = TestRunMetadata(
            timestamp=self.start_time.isoformat(),
            test_id=test_id,
            provider=provider,
            model=model,
            input_file_path=str(input_path),
            input_file_size=len(input_content),
            input_content_hash=content_hash,
            configuration=configuration,
            exit_status="running",
            exit_code=-1,
            execution_time_ms=0
        )

        logger.info(f"Started test run: {test_id}")
        return test_id

    def log_request(self, request_data: Dict[str, Any]) -> None:
        """
        Log the request sent to LLM provider.

        Args:
            request_data: Request data (system prompt, user prompt, etc.)
        """
        if not self.current_run_dir:
            logger.warning("No active test run, skipping request log")
            return

        request_file = self.current_run_dir / "request.json"
        with request_file.open('w', encoding='utf-8') as f:
            json.dump(request_data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Logged request to {request_file}")

    def log_response(self, response_data: Any, is_json: bool = True) -> None:
        """
        Log the response from LLM provider.

        Args:
            response_data: Response data (can be dict, string, etc.)
            is_json: Whether the response is JSON (default: True)
        """
        if not self.current_run_dir:
            logger.warning("No active test run, skipping response log")
            return

        if is_json:
            response_file = self.current_run_dir / "response.json"
            with response_file.open('w', encoding='utf-8') as f:
                if isinstance(response_data, str):
                    # Try to parse as JSON
                    try:
                        parsed = json.loads(response_data)
                        json.dump(parsed, f, indent=2, ensure_ascii=False)
                    except json.JSONDecodeError:
                        # Not valid JSON, save as text
                        response_file = self.current_run_dir / "response.txt"
                        response_file.write_text(response_data, encoding='utf-8')
                else:
                    json.dump(response_data, f, indent=2, ensure_ascii=False)
        else:
            response_file = self.current_run_dir / "response.txt"
            response_file.write_text(str(response_data), encoding='utf-8')

        logger.debug(f"Logged response to {response_file}")

    def log_validation_errors(self, errors: List[str]) -> None:
        """
        Log validation errors.

        Args:
            errors: List of validation error messages
        """
        if not self.current_metadata:
            logger.warning("No active test run, skipping validation errors")
            return

        self.current_metadata.validation_errors = errors

        # Also write to separate file for easy reading
        if self.current_run_dir:
            errors_file = self.current_run_dir / "validation_errors.txt"
            errors_file.write_text("\n".join(errors), encoding='utf-8')

    def log_state(self, state: Dict[str, Any]) -> None:
        """
        Log the final state of the meta-agent execution.

        Args:
            state: MetaAgentState dictionary
        """
        if not self.current_run_dir:
            logger.warning("No active test run, skipping state log")
            return

        state_file = self.current_run_dir / "final_state.json"

        # Create a clean copy (remove non-serializable items)
        clean_state = {}
        for key, value in state.items():
            try:
                json.dumps(value)  # Test if serializable
                clean_state[key] = value
            except (TypeError, ValueError):
                clean_state[key] = str(value)

        with state_file.open('w', encoding='utf-8') as f:
            json.dump(clean_state, f, indent=2, ensure_ascii=False)

        # Extract metadata from state
        if self.current_metadata:
            self.current_metadata.retry_count = state.get('retry_count', 0)
            self.current_metadata.confidence_score = state.get('confidence_score')

        logger.debug(f"Logged state to {state_file}")

    def log_stdout(self, message: str) -> None:
        """Capture stdout message."""
        self.stdout_capture.append(message)

    def log_stderr(self, message: str) -> None:
        """Capture stderr message."""
        self.stderr_capture.append(message)

    def end_test_run(
        self,
        exit_status: str,
        exit_code: int = 0,
        error: Optional[Exception] = None
    ) -> None:
        """
        End the current test run and finalize logs.

        Args:
            exit_status: "success", "failure", or "error"
            exit_code: Exit code (0 for success, non-zero for failure)
            error: Exception if test failed
        """
        if not self.current_metadata or not self.current_run_dir or not self.start_time:
            logger.warning("No active test run to end")
            return

        # Calculate execution time
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - self.start_time).total_seconds() * 1000

        # Update metadata
        self.current_metadata.exit_status = exit_status
        self.current_metadata.exit_code = exit_code
        self.current_metadata.execution_time_ms = int(execution_time)

        # Log error details if present
        if error:
            self.current_metadata.error_type = type(error).__name__
            self.current_metadata.error_message = str(error)

            # Write full traceback to file
            traceback_file = self.current_run_dir / "traceback.txt"
            traceback_file.write_text(
                "".join(traceback.format_exception(type(error), error, error.__traceback__)),
                encoding='utf-8'
            )

        # Write captured stdout/stderr
        if self.stdout_capture:
            (self.current_run_dir / "stdout.log").write_text(
                "\n".join(self.stdout_capture),
                encoding='utf-8'
            )

        if self.stderr_capture:
            (self.current_run_dir / "stderr.log").write_text(
                "\n".join(self.stderr_capture),
                encoding='utf-8'
            )

        # Write metadata
        metadata_file = self.current_run_dir / "metadata.json"
        with metadata_file.open('w', encoding='utf-8') as f:
            json.dump(self.current_metadata.to_dict(), f, indent=2, ensure_ascii=False)

        # Append to summary log
        self._append_to_summary(self.current_metadata)

        logger.info(
            f"Test run completed: {self.current_metadata.test_id} "
            f"({exit_status}, {execution_time:.0f}ms)"
        )

        # Reset state
        self.current_run_dir = None
        self.current_metadata = None
        self.start_time = None
        self.stdout_capture = []
        self.stderr_capture = []

    def _append_to_summary(self, metadata: TestRunMetadata) -> None:
        """Append test run summary to JSONL file."""
        with self.summary_file.open('a', encoding='utf-8') as f:
            f.write(json.dumps(metadata.to_dict(), ensure_ascii=False) + '\n')

    @contextmanager
    def capture_output(self):
        """
        Context manager to capture stdout/stderr during test execution.

        Usage:
            with logger.capture_output():
                # Test code here
                print("This will be captured")
        """
        # Create custom stdout/stderr handlers
        class TeeWriter:
            def __init__(self, original, capture_list):
                self.original = original
                self.capture_list = capture_list

            def write(self, message):
                self.original.write(message)
                self.original.flush()
                if message.strip():  # Don't capture empty lines
                    self.capture_list.append(message.rstrip())

            def flush(self):
                self.original.flush()

        # Save original streams
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            # Replace with tee writers
            sys.stdout = TeeWriter(original_stdout, self.stdout_capture)
            sys.stderr = TeeWriter(original_stderr, self.stderr_capture)

            yield

        finally:
            # Restore original streams
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics from all test runs.

        Returns:
            Dictionary with statistics
        """
        if not self.summary_file.exists():
            return {
                "total_runs": 0,
                "success_count": 0,
                "failure_count": 0,
                "error_count": 0
            }

        stats = {
            "total_runs": 0,
            "success_count": 0,
            "failure_count": 0,
            "error_count": 0,
            "avg_execution_time_ms": 0,
            "by_provider": {},
            "by_model": {},
            "recent_failures": []
        }

        execution_times = []

        with self.summary_file.open('r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                run = json.loads(line)
                stats["total_runs"] += 1

                # Count by status
                status = run.get("exit_status", "unknown")
                if status == "success":
                    stats["success_count"] += 1
                elif status == "failure":
                    stats["failure_count"] += 1
                else:
                    stats["error_count"] += 1

                # Track execution time
                exec_time = run.get("execution_time_ms", 0)
                if exec_time > 0:
                    execution_times.append(exec_time)

                # Count by provider
                provider = run.get("provider", "unknown")
                stats["by_provider"][provider] = stats["by_provider"].get(provider, 0) + 1

                # Count by model
                model = run.get("model", "unknown")
                stats["by_model"][model] = stats["by_model"].get(model, 0) + 1

                # Track recent failures
                if status in ["failure", "error"]:
                    stats["recent_failures"].append({
                        "test_id": run.get("test_id"),
                        "provider": provider,
                        "model": model,
                        "error": run.get("error_message", "Unknown error")[:100]
                    })

        # Calculate average
        if execution_times:
            stats["avg_execution_time_ms"] = int(sum(execution_times) / len(execution_times))

        # Keep only last 10 failures
        stats["recent_failures"] = stats["recent_failures"][-10:]

        return stats


# Global test logger instance
_global_test_logger: Optional[TestLogger] = None


def get_test_logger(base_log_dir: str = "logs") -> TestLogger:
    """
    Get or create global test logger instance.

    Args:
        base_log_dir: Base directory for logs

    Returns:
        TestLogger instance
    """
    global _global_test_logger

    if _global_test_logger is None:
        _global_test_logger = TestLogger(base_log_dir)

    return _global_test_logger


# Example usage
if __name__ == "__main__":
    # Demo the logging system
    test_logger = TestLogger("logs")

    # Start a test run
    test_id = test_logger.start_test_run(
        provider="gemini",
        model="gemini-2.5-pro",
        input_file_path="specs/examples/simple_sequential.txt",
        configuration={"temperature": 0.05, "use_structured_output": True}
    )

    # Log request
    test_logger.log_request({
        "system_prompt": "You are a workflow parser...",
        "user_prompt": "Convert this spec..."
    })

    # Simulate test execution
    import time
    time.sleep(0.1)

    # Log response
    test_logger.log_response({
        "name": "test_workflow",
        "workflow": {"type": "sequential"}
    })

    # Log state
    test_logger.log_state({
        "execution_status": "complete",
        "retry_count": 0,
        "confidence_score": 0.9
    })

    # End test run
    test_logger.end_test_run(exit_status="success", exit_code=0)

    # Print stats
    stats = test_logger.get_summary_stats()
    print("\nTest Statistics:")
    print(json.dumps(stats, indent=2))