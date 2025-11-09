"""
Custom exception types for meta-agent v2.

Provides granular error handling for different failure modes:
- Parsing errors (malformed text specs)
- Validation errors (schema violations)
- Reasoning errors (LLM failures)
- Generation errors (serialization issues)
"""

from typing import List, Optional, Dict, Any


class MetaAgentError(Exception):
    """Base exception for all meta-agent errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False
    ):
        """
        Initialize meta-agent error.

        Args:
            message: Human-readable error message
            details: Additional context (e.g., validation errors, line numbers)
            recoverable: Whether error can be fixed with retry/feedback
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.recoverable = recoverable

    def __str__(self) -> str:
        """Format error message with details."""
        base = f"{self.__class__.__name__}: {self.message}"
        if self.details:
            details_str = "\n".join(f"  {k}: {v}" for k, v in self.details.items())
            return f"{base}\nDetails:\n{details_str}"
        return base

    def to_dict(self) -> Dict[str, Any]:
        """Serialize error to dictionary for state persistence."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable
        }


class ParsingError(MetaAgentError):
    """
    Error during text specification parsing.

    Examples:
    - Missing required sections (Workflow, Steps, etc.)
    - Malformed section headers
    - Invalid input/output format
    """

    def __init__(
        self,
        message: str,
        missing_sections: Optional[List[str]] = None,
        line_number: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize parsing error.

        Args:
            message: Error description
            missing_sections: List of missing required sections
            line_number: Line number where error occurred (if applicable)
        """
        details = kwargs.get('details', {})
        if missing_sections:
            details['missing_sections'] = missing_sections
        if line_number:
            details['line_number'] = line_number

        super().__init__(
            message=message,
            details=details,
            recoverable=True  # Can often fix with spec clarification
        )
        self.missing_sections = missing_sections or []
        self.line_number = line_number


class ValidationError(MetaAgentError):
    """
    Error during Pydantic schema validation.

    Examples:
    - Invalid parameter names (not snake_case)
    - Unsafe condition patterns
    - Undefined variable references
    - Circular dependencies
    """

    def __init__(
        self,
        message: str,
        field_errors: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        """
        Initialize validation error.

        Args:
            message: Error description
            field_errors: List of Pydantic validation errors
        """
        details = kwargs.get('details', {})
        if field_errors:
            details['field_errors'] = field_errors

        super().__init__(
            message=message,
            details=details,
            recoverable=True  # Can often fix with LLM retry
        )
        self.field_errors = field_errors or []

    @classmethod
    def from_pydantic_error(cls, pydantic_error) -> 'ValidationError':
        """
        Create ValidationError from Pydantic ValidationError.

        Args:
            pydantic_error: Pydantic validation error

        Returns:
            ValidationError with formatted field errors
        """
        field_errors = []
        for error in pydantic_error.errors():
            field_errors.append({
                'field': '.'.join(str(loc) for loc in error['loc']),
                'message': error['msg'],
                'type': error['type']
            })

        # Create summary message
        error_count = len(field_errors)
        first_error = field_errors[0]['field'] if field_errors else 'unknown'
        message = f"Schema validation failed: {error_count} error(s) starting with '{first_error}'"

        return cls(message=message, field_errors=field_errors)


class ReasoningError(MetaAgentError):
    """
    Error during LLM reasoning phase.

    Examples:
    - LLM API failures (rate limits, timeouts)
    - Malformed JSON output
    - Low confidence scores
    - Ambiguous specifications
    """

    def __init__(
        self,
        message: str,
        confidence_score: Optional[float] = None,
        llm_response: Optional[str] = None,
        retry_count: int = 0,
        **kwargs
    ):
        """
        Initialize reasoning error.

        Args:
            message: Error description
            confidence_score: LLM confidence (0.0-1.0)
            llm_response: Raw LLM response for debugging
            retry_count: Number of retries attempted
        """
        details = kwargs.get('details', {})
        if confidence_score is not None:
            details['confidence_score'] = confidence_score
        if llm_response:
            # Truncate long responses
            details['llm_response'] = llm_response[:500] + ('...' if len(llm_response) > 500 else '')
        if retry_count > 0:
            details['retry_count'] = retry_count

        # Recoverable if we haven't exhausted retries
        recoverable = retry_count < 3

        super().__init__(
            message=message,
            details=details,
            recoverable=recoverable
        )
        self.confidence_score = confidence_score
        self.llm_response = llm_response
        self.retry_count = retry_count


class GenerationError(MetaAgentError):
    """
    Error during JSON generation phase.

    Examples:
    - Serialization failures
    - Round-trip consistency check failures
    - Invalid JSON syntax
    """

    def __init__(
        self,
        message: str,
        json_output: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize generation error.

        Args:
            message: Error description
            json_output: Generated JSON (if any) for debugging
        """
        details = kwargs.get('details', {})
        if json_output:
            # Truncate long JSON
            details['json_output'] = json_output[:500] + ('...' if len(json_output) > 500 else '')

        super().__init__(
            message=message,
            details=details,
            recoverable=False  # Generation failures usually indicate serious bugs
        )
        self.json_output = json_output


class EscalationRequired(MetaAgentError):
    """
    Signals that human intervention is required.

    Not a failure, but a request for human review due to:
    - Low confidence score (<0.8)
    - Ambiguous specification
    - Multiple validation failures
    """

    def __init__(
        self,
        message: str,
        reason: str,
        confidence_score: Optional[float] = None,
        **kwargs
    ):
        """
        Initialize escalation request.

        Args:
            message: Escalation message
            reason: Why escalation is needed
            confidence_score: LLM confidence (if applicable)
        """
        details = kwargs.get('details', {})
        details['reason'] = reason
        if confidence_score is not None:
            details['confidence_score'] = confidence_score

        super().__init__(
            message=message,
            details=details,
            recoverable=True  # Can be resolved with human input
        )
        self.reason = reason
        self.confidence_score = confidence_score
