"""
Schema converter for Pydantic models to JSON Schema format.

This module provides utilities to convert Pydantic models (like WorkflowSpec)
to JSON Schema format for use with Gemini's structured output mode.
"""

from typing import Type, Any, Dict, List, Union
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


def pydantic_to_json_schema(model: Type[BaseModel], max_depth: int = 3) -> Dict[str, Any]:
    """
    Convert a Pydantic model to JSON Schema format suitable for Gemini.

    Args:
        model: The Pydantic model class to convert
        max_depth: Maximum recursion depth for nested models (default 3)

    Returns:
        JSON Schema dictionary
    """
    try:
        # Get base schema from Pydantic
        schema = model.model_json_schema()

        # Apply Gemini-specific constraints
        schema = _apply_gemini_constraints(schema, max_depth)

        # Add variable reference patterns
        schema = _add_variable_patterns(schema)

        # Simplify complex unions if needed
        schema = _simplify_unions(schema)

        logger.debug(f"Generated JSON schema for {model.__name__}")
        return schema

    except Exception as e:
        logger.error(f"Failed to convert Pydantic model to JSON schema: {e}")
        raise


def _apply_gemini_constraints(schema: Dict[str, Any], max_depth: int, current_depth: int = 0) -> Dict[str, Any]:
    """
    Apply Gemini-specific constraints to the schema.

    - Flatten deeply nested structures beyond max_depth
    - Remove unsupported JSON Schema features
    - Ensure compatibility with Gemini's schema parser
    """
    if current_depth >= max_depth:
        # Replace deep nesting with empty object schema (depth limit reached)
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {},
            "description": "Nested workflow structure (depth limit reached)"
        }

    if isinstance(schema, dict):
        # Remove $ref references (Gemini doesn't support them well)
        if "$ref" in schema:
            # This is a simplified approach - in production, properly resolve refs
            schema = {"type": "object", "additionalProperties": False, "properties": {}}

        # Process nested structures
        for key, value in list(schema.items()):
            if key == "properties" and isinstance(value, dict):
                for prop_name, prop_schema in value.items():
                    schema["properties"][prop_name] = _apply_gemini_constraints(
                        prop_schema, max_depth, current_depth + 1
                    )
            elif key == "items":
                schema["items"] = _apply_gemini_constraints(
                    value, max_depth, current_depth + 1
                )
            elif isinstance(value, dict):
                schema[key] = _apply_gemini_constraints(
                    value, max_depth, current_depth
                )

    return schema


def _add_variable_patterns(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add regex patterns to enforce correct variable reference format.

    Ensures variables follow the {{name}} pattern, not {{{{name}}}} or {{name.property}}.
    """
    def add_pattern(obj: Any) -> Any:
        if isinstance(obj, dict):
            # If it's a string type that might contain variable references
            if obj.get("type") == "string":
                # Check if description suggests it might contain variables
                desc = obj.get("description", "").lower()
                if any(word in desc for word in ["variable", "reference", "parameter", "assigns"]):
                    # Add pattern to ensure proper variable format
                    if "pattern" not in obj:
                        # Allow either plain text or properly formatted variables
                        obj["pattern"] = r"^([^{]|\{\{[a-z_][a-z0-9_]*\}\})*$"
                        obj["description"] = f"{obj.get('description', '')} (use {{name}} format for variables)"

            # Recursively process nested objects
            for key, value in obj.items():
                if key not in ["pattern", "description"]:  # Don't recurse into these
                    obj[key] = add_pattern(value)

        elif isinstance(obj, list):
            return [add_pattern(item) for item in obj]

        return obj

    return add_pattern(schema)


def _simplify_unions(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplify complex union types for better Gemini compatibility.

    Gemini sometimes struggles with complex anyOf/oneOf constructs.
    This simplifies them where possible.
    """
    def simplify(obj: Any) -> Any:
        if isinstance(obj, dict):
            # Handle anyOf with simple types
            if "anyOf" in obj and len(obj["anyOf"]) == 2:
                types = [item.get("type") for item in obj["anyOf"]]
                if "null" in types:
                    # Optional field - just use the non-null type
                    non_null_items = [item for item in obj["anyOf"] if item.get("type") != "null"]
                    if non_null_items:
                        return simplify(non_null_items[0])
                    # If all items are null, return the original object
                    return obj

            # Handle oneOf similarly
            if "oneOf" in obj:
                # For workflow types, convert to enum if possible
                if all(item.get("type") == "object" for item in obj["oneOf"]):
                    # Keep the oneOf but add discriminator hint
                    obj["discriminator"] = {"propertyName": "type"}

            # Recursively process
            return {key: simplify(value) for key, value in obj.items()}

        elif isinstance(obj, list):
            return [simplify(item) for item in obj]

        return obj

    return simplify(schema)


def generate_workflow_schema() -> Dict[str, Any]:
    """
    Generate the specific JSON Schema for WorkflowSpec.

    This is optimized for the meta-agent use case.
    """
    # Import here to avoid circular dependency
    from src.core.workflow_ast import WorkflowSpec

    # Get base schema
    schema = pydantic_to_json_schema(WorkflowSpec, max_depth=3)

    # Add specific constraints for workflow types
    if "properties" in schema and "workflow" in schema["properties"]:
        workflow_schema = schema["properties"]["workflow"]

        # Add enum constraint for workflow types
        workflow_schema["properties"] = workflow_schema.get("properties", {})
        workflow_schema["properties"]["type"] = {
            "type": "string",
            "enum": ["tool_call", "sequential", "conditional", "parallel", "orchestrator"],
            "description": "The type of workflow node"
        }

    # Add specific variable tracking
    schema["properties"]["_available_variables"] = {
        "type": "array",
        "items": {"type": "string"},
        "description": "Track available variables for validation"
    }

    return schema


def validate_schema_for_gemini(schema: Dict[str, Any]) -> List[str]:
    """
    Validate that a schema is compatible with Gemini's structured output.

    Returns:
        List of warning/error messages (empty if valid)
    """
    issues = []

    def check_schema(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            # Check for unsupported features
            if "$ref" in obj:
                issues.append(f"{path}: Contains $ref (not fully supported)")

            if "additionalProperties" in obj and obj["additionalProperties"] is True:
                issues.append(f"{path}: Has additionalProperties=true (may cause issues)")

            # Check for deep nesting
            depth = path.count(".")
            if depth > 5:
                issues.append(f"{path}: Deeply nested (depth={depth}), may cause issues")

            # Recurse
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                check_schema(value, new_path)

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_schema(item, f"{path}[{i}]")

    check_schema(schema)
    return issues


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Test with WorkflowSpec
    try:
        from src.core.workflow_ast import WorkflowSpec, ToolCall, SequentialWorkflow

        # Generate schema
        schema = generate_workflow_schema()

        # Validate it
        issues = validate_schema_for_gemini(schema)

        if issues:
            print("Schema validation warnings:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✓ Schema is valid for Gemini")

        # Print a sample of the schema
        import json
        print("\nGenerated Schema (excerpt):")
        print(json.dumps(schema, indent=2)[:1000] + "...")

    except ImportError as e:
        print(f"Could not import WorkflowSpec: {e}")
        print("Using generic test...")

        # Test with a simple model
        from typing import Optional

        class SimpleModel(BaseModel):
            name: str
            value: int
            optional: Optional[str] = None

        schema = pydantic_to_json_schema(SimpleModel)
        print("Simple model schema:")
        print(json.dumps(schema, indent=2))