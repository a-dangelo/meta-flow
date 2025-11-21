"""
Deterministic parameter validation against JSON schema.

Validates user-provided values against the type information from
the JSON AST, providing type checking and constraint validation.
"""

from typing import Any, Tuple, Optional, List, Dict
from datetime import datetime
import re


def validate_parameter(
    param_name: str,
    value: Any,
    param_type: str,
    required: bool = True
) -> Tuple[bool, Optional[Any], Optional[str]]:
    """
    Validate a single parameter value against its type.

    Args:
        param_name: Name of the parameter
        value: User-provided value
        param_type: Expected type from JSON schema
        required: Whether parameter is required

    Returns:
        Tuple of (is_valid, parsed_value, error_message)
    """
    # Check if value is provided for required parameter
    if value is None or value == "":
        if required:
            return False, None, f"{param_name} is required"
        return True, None, None

    # Type-specific validation
    param_type = param_type.lower()

    try:
        if param_type in ["float", "number"]:
            parsed = float(value)
            return True, parsed, None

        elif param_type in ["int", "integer"]:
            parsed = int(value)
            return True, parsed, None

        elif param_type in ["str", "string", "text"]:
            return True, str(value), None

        elif param_type == "date":
            # Try parsing as ISO date
            if isinstance(value, str):
                parsed = datetime.fromisoformat(value.split("T")[0])
                return True, parsed.date().isoformat(), None
            return True, value, None

        elif param_type == "datetime":
            # Try parsing as ISO datetime
            if isinstance(value, str):
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return True, parsed.isoformat(), None
            return True, value, None

        elif param_type == "email":
            # Basic email validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if isinstance(value, str) and re.match(email_pattern, value):
                return True, value, None
            return False, None, f"{param_name} must be a valid email address"

        elif param_type == "url":
            # Basic URL validation
            if isinstance(value, str) and (value.startswith("http://") or value.startswith("https://")):
                return True, value, None
            return False, None, f"{param_name} must be a valid URL starting with http:// or https://"

        elif param_type == "bool" or param_type == "boolean":
            if isinstance(value, bool):
                return True, value, None
            if isinstance(value, str):
                if value.lower() in ["true", "yes", "1"]:
                    return True, True, None
                if value.lower() in ["false", "no", "0"]:
                    return True, False, None
            return False, None, f"{param_name} must be true or false"

        else:
            # Unknown type - accept as-is
            return True, value, None

    except (ValueError, TypeError) as e:
        return False, None, f"{param_name} must be {param_type} (error: {str(e)})"


def validate_all_parameters(
    parameters: List[Dict],
    collected_values: Dict[str, Any]
) -> Tuple[bool, Dict[str, Any], List[str]]:
    """
    Validate all collected parameters against their schemas.

    Args:
        parameters: List of parameter dictionaries from extractor
        collected_values: Dictionary of user-provided values

    Returns:
        Tuple of (all_valid, validated_values, error_messages)
    """
    validated = {}
    errors = []

    for param in parameters:
        name = param["name"]
        param_type = param.get("type", "string")
        required = param.get("required", True)
        value = collected_values.get(name)

        is_valid, parsed_value, error = validate_parameter(
            name, value, param_type, required
        )

        if not is_valid:
            errors.append(error)
        else:
            if parsed_value is not None:
                validated[name] = parsed_value

    return len(errors) == 0, validated, errors


def get_missing_required_parameters(
    parameters: List[Dict],
    collected_values: Dict[str, Any]
) -> List[str]:
    """
    Get list of required parameters that are still missing.

    Args:
        parameters: List of parameter dictionaries
        collected_values: Dictionary of user-provided values

    Returns:
        List of missing required parameter names
    """
    missing = []

    for param in parameters:
        if param.get("required", True):
            name = param["name"]
            value = collected_values.get(name)
            if value is None or value == "":
                missing.append(name)

    return missing


def check_parameter_constraints(
    param_name: str,
    value: Any,
    constraints: Optional[Dict] = None
) -> Tuple[bool, Optional[str]]:
    """
    Check additional constraints on parameter values.

    Args:
        param_name: Name of the parameter
        value: Validated value
        constraints: Dictionary of constraints (min, max, pattern, etc.)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not constraints:
        return True, None

    try:
        # Numeric constraints
        if "min" in constraints:
            if isinstance(value, (int, float)) and value < constraints["min"]:
                return False, f"{param_name} must be at least {constraints['min']}"

        if "max" in constraints:
            if isinstance(value, (int, float)) and value > constraints["max"]:
                return False, f"{param_name} must be at most {constraints['max']}"

        # String length constraints
        if "minLength" in constraints:
            if isinstance(value, str) and len(value) < constraints["minLength"]:
                return False, f"{param_name} must be at least {constraints['minLength']} characters"

        if "maxLength" in constraints:
            if isinstance(value, str) and len(value) > constraints["maxLength"]:
                return False, f"{param_name} must be at most {constraints['maxLength']} characters"

        # Pattern matching
        if "pattern" in constraints:
            if isinstance(value, str) and not re.match(constraints["pattern"], value):
                return False, f"{param_name} does not match required format"

        # Enum values
        if "enum" in constraints:
            if value not in constraints["enum"]:
                allowed = ", ".join(str(v) for v in constraints["enum"])
                return False, f"{param_name} must be one of: {allowed}"

        return True, None

    except Exception as e:
        return False, f"Constraint validation error for {param_name}: {str(e)}"
