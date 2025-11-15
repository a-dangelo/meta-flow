"""
JSON repair utilities for fixing common Gemini generation errors.

This module provides functions to repair malformed JSON output from LLMs,
particularly targeting known issues with Gemini models.
"""

import re
import json
import logging
from typing import Optional, Set, Dict, Any

logger = logging.getLogger(__name__)


def repair_gemini_json(raw_output: str, available_vars: Optional[Set[str]] = None) -> str:
    """
    Repair common JSON generation errors from Gemini models.

    Fixes:
    - Quadruple braces {{{{ -> {{
    - Extra text after JSON object
    - Missing commas between properties
    - Escaped braces
    - Invalid variable references

    Args:
        raw_output: Raw LLM output that may contain invalid JSON
        available_vars: Set of valid variable names for reference validation

    Returns:
        Repaired JSON string (best effort - may still be invalid)
    """
    logger.debug(f"Attempting to repair JSON ({len(raw_output)} chars)")

    # Track what we fixed for logging
    fixes_applied = []

    # Step 1: Fix quadruple braces (most common Gemini issue)
    if '{{{{' in raw_output or '}}}}' in raw_output:
        raw_output = raw_output.replace('{{{{', '{{').replace('}}}}', '}}')
        fixes_applied.append("quadruple braces")

    # Step 2: Fix accidentally escaped braces
    if r'\{' in raw_output or r'\}' in raw_output:
        raw_output = raw_output.replace(r'\{', '{').replace(r'\}', '}')
        fixes_applied.append("escaped braces")

    # Step 3: Extract JSON object (remove extra text before/after)
    json_str = _extract_json_object(raw_output)
    if json_str != raw_output:
        fixes_applied.append("extracted JSON from surrounding text")
        raw_output = json_str

    # Step 4: Fix missing commas (basic cases)
    before_comma_fix = raw_output
    raw_output = _fix_missing_commas(raw_output)
    if raw_output != before_comma_fix:
        fixes_applied.append("missing commas")

    # Step 5: Fix invalid variable references if we have the available vars
    if available_vars:
        before_var_fix = raw_output
        raw_output = _fix_variable_references(raw_output, available_vars)
        if raw_output != before_var_fix:
            fixes_applied.append("variable references")

    # Step 6: Validate the result
    try:
        json.loads(raw_output)
        if fixes_applied:
            logger.info(f"JSON repair successful. Fixes applied: {', '.join(fixes_applied)}")
        return raw_output
    except json.JSONDecodeError as e:
        logger.warning(f"JSON still invalid after repair: {e}")
        # Return our best attempt anyway
        return raw_output


def _extract_json_object(text: str) -> str:
    """
    Extract the main JSON object from text that may contain extra content.

    Handles cases where LLM adds explanation before/after the JSON.
    """
    # Remove markdown code fences if present
    if '```json' in text or '```' in text:
        text = re.sub(r'```json?\s*', '', text)
        text = re.sub(r'```', '', text)

    # Try to find the outermost { } pair
    stack = []
    start_idx = None
    end_idx = None

    for i, char in enumerate(text):
        if char == '{':
            if start_idx is None:
                start_idx = i
            stack.append(char)
        elif char == '}':
            if stack:
                stack.pop()
                if not stack and start_idx is not None:
                    end_idx = i + 1
                    break

    if start_idx is not None and end_idx is not None:
        return text[start_idx:end_idx]

    # Fallback: try to find JSON-like content with regex (limited nesting support)
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        logger.warning(
            f"Falling back to regex extraction (limited nesting support). "
            f"Match length: {len(json_match.group())} chars"
        )
        return json_match.group()

    return text


def _fix_missing_commas(json_str: str) -> str:
    """
    Add missing commas between JSON properties.

    This is a heuristic approach and may not catch all cases.
    """
    # Add comma between "}" and "{" on new lines
    json_str = re.sub(r'}\s*\n\s*{', '},\n{', json_str)

    # Add comma between "]" and "[" on new lines
    json_str = re.sub(r']\s*\n\s*\[', '],\n[', json_str)

    # Add comma between string properties on new lines
    # Match: "property": "value"\n"nextproperty":
    json_str = re.sub(r'("\s*:\s*"[^"]*")\s*\n\s*(")', r'\1,\n\2', json_str)

    # Add comma between number/boolean and next property
    # Match: "property": 123\n"nextproperty":
    json_str = re.sub(r'("\s*:\s*(?:true|false|null|\d+(?:\.\d+)?))\s*\n\s*(")', r'\1,\n\2', json_str)

    # Add comma between closing bracket/brace and next property
    json_str = re.sub(r'([}\]])\s*\n\s*(")', r'\1,\n\2', json_str)

    return json_str


def _fix_variable_references(json_str: str, available_vars: Set[str]) -> str:
    """
    Fix invalid variable references like {{order.items}} -> {{order}}.

    Args:
        json_str: JSON string with variable references
        available_vars: Set of valid variable names

    Returns:
        JSON with corrected variable references
    """
    def fix_single_reference(match):
        full_ref = match.group(0)  # e.g., "{{order.items}}"
        var_content = match.group(1)  # e.g., "order.items"

        # If it's already valid, keep it
        if var_content in available_vars:
            return full_ref

        # Try to extract base variable name (before .)
        if '.' in var_content:
            base_var = var_content.split('.')[0]
            if base_var in available_vars:
                logger.debug(f"Fixed variable reference: {full_ref} -> {{{{{base_var}}}}}")
                return f"{{{{{base_var}}}}}"

        # Try to extract base variable name (before [)
        if '[' in var_content:
            base_var = var_content.split('[')[0]
            if base_var in available_vars:
                logger.debug(f"Fixed variable reference: {full_ref} -> {{{{{base_var}}}}}")
                return f"{{{{{base_var}}}}}"

        # Try to find a similar variable
        for available in available_vars:
            if available in var_content or var_content in available:
                logger.debug(f"Fixed variable reference: {full_ref} -> {{{{{available}}}}}")
                return f"{{{{{available}}}}}"

        # If no match found, log warning but keep original
        logger.warning(f"Could not fix variable reference: {full_ref}")
        return full_ref

    # Find and fix all variable references
    pattern = r'\{\{([^}]+)\}\}'
    return re.sub(pattern, fix_single_reference, json_str)


def validate_and_repair_workflow(workflow_dict: Dict[str, Any], available_vars: Set[str]) -> Dict[str, Any]:
    """
    Validate and repair a workflow dictionary after JSON parsing.

    This operates on the parsed dictionary rather than raw JSON string.

    Args:
        workflow_dict: Parsed workflow dictionary
        available_vars: Set of valid variable names

    Returns:
        Repaired workflow dictionary
    """
    def repair_value(value: Any) -> Any:
        if isinstance(value, str):
            # Check if it looks like a variable reference
            if value.startswith('{{') and value.endswith('}}'):
                var_name = value[2:-2]

                # Fix nested property access
                if '.' in var_name:
                    base_var = var_name.split('.')[0]
                    if base_var in available_vars:
                        return f"{{{{{base_var}}}}}"

                # Fix array indexing
                if '[' in var_name:
                    base_var = var_name.split('[')[0]
                    if base_var in available_vars:
                        return f"{{{{{base_var}}}}}"

                # Check if it's valid
                if var_name not in available_vars:
                    # Try to find a match
                    for available in available_vars:
                        if available in var_name or var_name in available:
                            return f"{{{{{available}}}}}"

        elif isinstance(value, dict):
            return {k: repair_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [repair_value(item) for item in value]

        return value

    return repair_value(workflow_dict)


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Test cases
    test_cases = [
        # Quadruple braces
        ('{"var": "{{{{ref}}}}"}', {"ref"}),
        # Nested property
        ('{"var": "{{order.items}}"}', {"order", "items"}),
        # Missing comma
        ('{"a": "1"\n"b": "2"}', set()),
        # Extra text
        ('Here is the JSON:\n```json\n{"test": true}\n```\nThat\'s the output', set()),
        # Complex case
        ('{"steps": [{"var": "{{{{data}}}}"}]\n"next": "value"}', {"data"}),
    ]

    for raw_json, vars_set in test_cases:
        print(f"\nInput: {raw_json[:50]}...")
        repaired = repair_gemini_json(raw_json, vars_set)
        print(f"Output: {repaired[:50]}...")

        try:
            parsed = json.loads(repaired)
            print("✓ Valid JSON")
        except json.JSONDecodeError as e:
            print(f"✗ Still invalid: {e}")