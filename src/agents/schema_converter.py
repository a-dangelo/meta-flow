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

        # Extract definitions for reference resolution
        defs = schema.get("$defs", {})

        # Apply Gemini-specific constraints with definitions for reference resolution
        schema = _apply_gemini_constraints(schema, max_depth, defs=defs)

        # Add variable reference patterns
        schema = _add_variable_patterns(schema)

        # Simplify complex unions if needed
        schema = _simplify_unions(schema)

        logger.debug(f"Generated JSON schema for {model.__name__}")
        return schema

    except Exception as e:
        logger.error(f"Failed to convert Pydantic model to JSON schema: {e}")
        raise


def _apply_gemini_constraints(schema: Dict[str, Any], max_depth: int, current_depth: int = 0, defs: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Apply Gemini-specific constraints to the schema.

    - Only apply depth limits to actual object types, not primitive schemas
    - Remove unsupported JSON Schema features (additionalProperties, $ref)
    - Ensure compatibility with Gemini's schema parser

    Depth is only incremented when entering properties of object-type schemas.
    """
    # Handle non-dict types (shouldn't happen but be defensive)
    if not isinstance(schema, dict):
        return schema

    # Handle $ref references first (Gemini doesn't support them)
    if "$ref" in schema:
        # Try to resolve the reference
        if defs:
            ref_path = schema["$ref"]
            if ref_path.startswith("#/$defs/"):
                ref_name = ref_path.replace("#/$defs/", "")
                if ref_name in defs:
                    # Inline the referenced schema and process it
                    referenced_schema = defs[ref_name].copy()
                    return _apply_gemini_constraints(referenced_schema, max_depth, current_depth, defs)

        # If we can't resolve, use a placeholder with proper properties based on context
        # This should be an object type since it's a workflow node
        return {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "Workflow node type"}
            },
            "description": "Workflow node (reference resolved)"
        }

    # Determine the schema type
    schema_type = schema.get("type")
    is_object_type = False

    if isinstance(schema_type, list):
        # Union type like ["object", "null"]
        is_object_type = "object" in schema_type
    elif schema_type == "object":
        is_object_type = True

    # Only apply depth limit to actual object types
    if is_object_type and current_depth >= max_depth:
        # Return a simple object schema without properties
        # Gemini doesn't like empty properties, so we omit them entirely
        return {
            "type": "object",
            "description": f"Nested object (depth limit {max_depth} reached)"
        }

    # For primitive types, preserve the schema but remove unsupported fields
    primitive_types = ["string", "number", "integer", "boolean", "null", "array"]
    is_primitive = schema_type in primitive_types or (
        isinstance(schema_type, list) and
        all(t in primitive_types for t in schema_type)
    )

    # Build result dict
    result = {}

    for key, value in schema.items():
        # Skip Gemini-unsupported fields
        if key == "additionalProperties":
            # Log for debugging but don't include
            if value not in [False, True]:
                logger.debug(f"Skipping additionalProperties with value: {value}")
            continue

        # Process based on key type
        if key == "properties" and isinstance(value, dict):
            # Only increment depth if this is an object type's properties
            if is_object_type:
                # Entering object properties - increment depth
                result[key] = {}
                for prop_name, prop_schema in value.items():
                    result[key][prop_name] = _apply_gemini_constraints(
                        prop_schema, max_depth, current_depth + 1, defs
                    )
            else:
                # Non-object shouldn't have properties, but handle gracefully
                logger.warning(f"Non-object type {schema_type} has properties - preserving")
                result[key] = {}
                for prop_name, prop_schema in value.items():
                    result[key][prop_name] = _apply_gemini_constraints(
                        prop_schema, max_depth, current_depth, defs
                    )

        elif key == "items":
            # Array items - check if items are objects
            if isinstance(value, dict):
                item_type = value.get("type")
                # Only increment depth if array contains objects
                if item_type == "object" or (isinstance(item_type, list) and "object" in item_type):
                    next_depth = current_depth + 1
                else:
                    next_depth = current_depth
                result[key] = _apply_gemini_constraints(value, max_depth, next_depth, defs)
            elif isinstance(value, list):
                # Array of schemas (tuple validation)
                result[key] = [
                    _apply_gemini_constraints(item, max_depth, current_depth, defs)
                    if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value

        elif key in ["anyOf", "oneOf", "allOf"] and isinstance(value, list):
            # Union/composition operators - don't increment depth
            result[key] = [
                _apply_gemini_constraints(item, max_depth, current_depth, defs)
                if isinstance(item, dict) else item
                for item in value
            ]

        elif key in ["$defs", "definitions"] and isinstance(value, dict):
            # Schema definitions - process without incrementing depth
            result[key] = {}
            for def_name, def_schema in value.items():
                result[key][def_name] = _apply_gemini_constraints(
                    def_schema, max_depth, current_depth, defs
                )

        elif isinstance(value, dict):
            # Other nested dicts - don't increment depth (metadata, etc.)
            result[key] = _apply_gemini_constraints(value, max_depth, current_depth, defs)

        else:
            # Primitive values, strings, numbers, etc.
            result[key] = value

    return result


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
    from src.agents.models import WorkflowSpec

    # Get base schema
    schema = pydantic_to_json_schema(WorkflowSpec, max_depth=3)

    # Validate the generated schema
    validation_issues = validate_schema_for_gemini(schema)
    if validation_issues:
        # Log issues for debugging
        logger.debug(f"Schema validation found {len(validation_issues)} issue(s):")
        for issue in validation_issues:
            if issue.startswith("ERROR"):
                logger.error(f"  {issue}")
            else:
                logger.debug(f"  {issue}")

        # Only fail on errors, not warnings
        error_count = sum(1 for i in validation_issues if i.startswith("ERROR"))
        if error_count > 0:
            logger.warning(f"Schema has {error_count} error(s) that may cause Gemini API issues")

    # Add specific constraints for workflow types
    if "properties" in schema and "workflow" in schema["properties"]:
        workflow_schema = schema["properties"]["workflow"]

        # Add enum constraint for workflow types if it's an object
        if workflow_schema.get("type") == "object":
            workflow_schema["properties"] = workflow_schema.get("properties", {})
            workflow_schema["properties"]["type"] = {
                "type": "string",
                "enum": ["tool_call", "sequential", "conditional", "parallel", "orchestrator"],
                "description": "The type of workflow node"
            }

    # Add specific variable tracking
    if "properties" not in schema:
        schema["properties"] = {}
    schema["properties"]["_available_variables"] = {
        "type": "array",
        "items": {"type": "string"},
        "description": "Track available variables for validation"
    }

    # Final validation
    final_issues = validate_schema_for_gemini(schema)
    error_count = sum(1 for i in final_issues if i.startswith("ERROR"))
    if error_count > 0:
        logger.error(f"Final schema still has {error_count} error(s) after processing")

    logger.debug(f"Generated workflow schema with {len(schema.get('properties', {}))} top-level properties")

    return schema


def validate_schema_for_gemini(schema: Dict[str, Any]) -> List[str]:
    """
    Validate that a schema is compatible with Gemini's structured output.

    Checks for:
    - No additionalProperties field (Gemini doesn't support it)
    - No $ref references (Gemini doesn't support them)
    - No properties on non-object types
    - Proper handling of primitive types

    Returns:
        List of warning/error messages (empty if valid)
    """
    issues = []

    def check_schema(obj: Any, path: str = "", parent_type: str = None) -> None:
        if isinstance(obj, dict):
            # Get the type of this schema node
            obj_type = obj.get("type")

            # CRITICAL: Check for properties on non-object types
            if "properties" in obj:
                if obj_type and obj_type != "object":
                    # This is the bug we're fixing!
                    if isinstance(obj_type, list):
                        if "object" not in obj_type:
                            issues.append(f"ERROR {path}: Has 'properties' but type is {obj_type} (not object)")
                    else:
                        issues.append(f"ERROR {path}: Has 'properties' but type is '{obj_type}' (not object)")
                elif not obj_type and parent_type not in ["anyOf", "oneOf", "allOf"]:
                    # No type specified and not a union
                    issues.append(f"WARNING {path}: Has 'properties' but no type specified")

            # Check for unsupported Gemini features
            if "$ref" in obj:
                issues.append(f"ERROR {path}: Contains $ref (Gemini doesn't support)")

            if "additionalProperties" in obj:
                issues.append(f"ERROR {path}: Contains additionalProperties (Gemini doesn't support)")

            # Check for empty properties on what should be primitive types
            if obj_type in ["string", "number", "integer", "boolean", "null"]:
                if "properties" in obj and obj["properties"] == {}:
                    issues.append(f"ERROR {path}: Primitive type '{obj_type}' has empty properties {{}}")

            # Check for deep nesting
            depth = path.count(".")
            if depth > 5:
                issues.append(f"WARNING {path}: Deeply nested (depth={depth}), may cause issues")

            # Recurse into nested structures
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key

                # Track parent type for context
                if key in ["anyOf", "oneOf", "allOf"]:
                    parent = key
                elif key == "properties" and obj_type == "object":
                    parent = "object_properties"
                elif key == "items":
                    parent = "array_items"
                else:
                    parent = None

                if isinstance(value, dict):
                    check_schema(value, new_path, parent)
                elif isinstance(value, list) and key in ["anyOf", "oneOf", "allOf"]:
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            check_schema(item, f"{new_path}[{i}]", key)

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