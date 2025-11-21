"""
JSON-based parameter extraction from meta-agent output.

This module extracts parameters directly from the structured JSON AST
provided by the meta-agent, eliminating the need for Python code parsing
and providing 100% accuracy.
"""

from typing import List, Dict, Optional


def extract_parameters_from_json(json_ast: dict) -> List[Dict]:
    """
    Extract parameters directly from meta-agent JSON output.

    Args:
        json_ast: The structured JSON AST from meta-agent (WorkflowSpec.to_dict())

    Returns:
        List of parameter dictionaries with name, type, description, required, default

    Example JSON structure:
        {
            "name": "expense_approval",
            "inputs": [
                {
                    "name": "amount",
                    "type": "float",
                    "description": "Expense amount in USD"
                },
                ...
            ],
            "outputs": [...],
            "workflow": {...}
        }
    """
    parameters = []

    # Extract from inputs field in JSON
    inputs = json_ast.get("inputs", [])

    for input_def in inputs:
        param = {
            "name": input_def["name"],
            "type": input_def.get("type", "string"),
            "description": input_def.get("description", ""),
            "required": input_def.get("required", True),
            "default": input_def.get("default")
        }
        parameters.append(param)

    return parameters


def format_parameter_for_prompt(param: Dict) -> str:
    """
    Format a parameter for user-friendly display.

    Args:
        param: Parameter dictionary from extract_parameters_from_json

    Returns:
        Formatted string for display to user
    """
    parts = [f"**{param['name']}**"]

    if param.get('description'):
        parts.append(param['description'])

    type_hints = {
        "float": "number (e.g., 450.00)",
        "int": "whole number (e.g., 5)",
        "string": "text",
        "str": "text",
        "date": "date (YYYY-MM-DD)",
        "datetime": "date and time",
        "email": "email address",
        "url": "web URL"
    }

    param_type = param.get('type', 'string').lower()
    if param_type in type_hints:
        parts.append(f"({type_hints[param_type]})")

    if not param.get('required', True) and param.get('default') is not None:
        parts.append(f"[optional, default: {param['default']}]")
    elif not param.get('required', True):
        parts.append("[optional]")

    return " - ".join(parts)


def get_parameter_names(parameters: List[Dict]) -> List[str]:
    """
    Extract just the parameter names.

    Args:
        parameters: List of parameter dictionaries

    Returns:
        List of parameter names
    """
    return [p["name"] for p in parameters]


def get_required_parameters(parameters: List[Dict]) -> List[Dict]:
    """
    Filter to only required parameters.

    Args:
        parameters: List of parameter dictionaries

    Returns:
        List of required parameters only
    """
    return [p for p in parameters if p.get("required", True)]


def group_related_parameters(parameters: List[Dict]) -> List[List[Dict]]:
    """
    Group related parameters for conversational collection.

    Groups parameters that are logically related (e.g., date fields,
    contact information, amounts) to ask for them together.

    Args:
        parameters: List of parameter dictionaries

    Returns:
        List of parameter groups
    """
    # Simple grouping strategy: group by common prefixes or types
    groups = []
    current_group = []

    for param in parameters:
        name = param["name"]
        param_type = param.get("type", "string")

        # Start new group for date/datetime fields
        if param_type in ["date", "datetime"]:
            if current_group:
                groups.append(current_group)
            groups.append([param])
            current_group = []
        # Group email/contact fields
        elif "email" in name.lower() or "phone" in name.lower():
            if current_group:
                groups.append(current_group)
            groups.append([param])
            current_group = []
        else:
            current_group.append(param)

        # Limit group size to 3 parameters
        if len(current_group) >= 3:
            groups.append(current_group)
            current_group = []

    # Add remaining parameters
    if current_group:
        groups.append(current_group)

    return groups if groups else [parameters]
