"""
LLM-assisted parameter value collection from natural language.

This module uses an LLM to extract parameter values from user messages,
grounded by the parameter schema from the JSON AST.
"""

from typing import Dict, List, Optional
import json
import anthropic


def create_collection_prompt(parameters: List[Dict]) -> str:
    """
    Generate a friendly prompt asking for parameter values.

    Args:
        parameters: List of parameter dictionaries to collect

    Returns:
        User-friendly prompt string
    """
    lines = ["I need some information to process your request:\n"]

    for param in parameters:
        name = param["name"]
        description = param.get("description", "")
        param_type = param.get("type", "string")
        required = param.get("required", True)

        # Format parameter name nicely
        display_name = name.replace("_", " ").title()

        # Build prompt line
        if description:
            line = f"• **{display_name}**: {description}"
        else:
            line = f"• **{display_name}**"

        # Add type hint
        type_hints = {
            "float": " (number)",
            "int": " (whole number)",
            "date": " (YYYY-MM-DD)",
            "email": " (email address)",
            "url": " (web link)"
        }
        if param_type in type_hints:
            line += type_hints[param_type]

        if not required:
            line += " [optional]"

        lines.append(line)

    lines.append("\nPlease provide these values.")

    return "\n".join(lines)


async def extract_values_from_message(
    user_message: str,
    parameters: List[Dict],
    model_name: str = "claude-haiku-4-20250514",
    temperature: float = 0.0
) -> Dict[str, any]:
    """
    Extract parameter values from user's natural language message.

    Uses LLM with structured output to extract values, grounded by
    the parameter schema from JSON AST.

    Args:
        user_message: User's message containing parameter values
        parameters: List of parameter dictionaries (schema)
        model_name: Claude model to use
        temperature: Sampling temperature (0 = deterministic)

    Returns:
        Dictionary of extracted parameter values
    """
    import os

    # Build parameter schema for LLM
    schema_lines = []
    for param in parameters:
        name = param["name"]
        param_type = param.get("type", "string")
        description = param.get("description", "")
        required = param.get("required", True)

        schema_line = f"- {name} ({param_type})"
        if description:
            schema_line += f": {description}"
        if required:
            schema_line += " [REQUIRED]"

        schema_lines.append(schema_line)

    user_prompt = f"""Parameter Schema:
{chr(10).join(schema_lines)}

User Message:
"{user_message}"

Extract values as JSON. Example:
{{"amount": 450.0, "date": "2025-11-21", "category": "meals"}}

Instructions:
1. Only extract values explicitly mentioned in the message
2. Match the expected type for each parameter
3. Return null for parameters not mentioned
4. Do not invent or guess values

Return ONLY valid JSON, no explanation."""

    # Call Anthropic API
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        message = client.messages.create(
            model=model_name,
            max_tokens=1024,
            temperature=temperature,
            system="You are a parameter extraction assistant. Extract parameter values from the user's message based on the provided schema. Return JSON with extracted values.",
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        content = message.content[0].text

        # Parse JSON response
        # Remove markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        extracted = json.loads(content)

        # Filter to only include non-null values
        return {k: v for k, v in extracted.items() if v is not None}

    except (json.JSONDecodeError, Exception) as e:
        # LLM failed to return valid JSON - return empty dict
        print(f"Warning: Failed to extract values from message: {e}")
        return {}


def create_missing_parameters_prompt(missing_parameters: List[Dict]) -> str:
    """
    Generate prompt for missing parameters only.

    Args:
        missing_parameters: List of parameters still needed

    Returns:
        Prompt string asking for missing values
    """
    if not missing_parameters:
        return ""

    lines = ["I still need:\n"]

    for param in missing_parameters:
        name = param["name"]
        description = param.get("description", "")
        display_name = name.replace("_", " ").title()

        if description:
            lines.append(f"• **{display_name}**: {description}")
        else:
            lines.append(f"• **{display_name}**")

    lines.append("\nPlease provide these values.")

    return "\n".join(lines)


def format_collected_summary(
    parameters: List[Dict],
    collected_values: Dict[str, any]
) -> str:
    """
    Format a summary of collected values for confirmation.

    Args:
        parameters: All parameters
        collected_values: Values collected so far

    Returns:
        Formatted summary string
    """
    lines = ["Here's what I have so far:\n"]

    for param in parameters:
        name = param["name"]
        display_name = name.replace("_", " ").title()
        value = collected_values.get(name)

        if value is not None:
            lines.append(f"• {display_name}: {value}")

    return "\n".join(lines)
