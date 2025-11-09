#!/usr/bin/env python3
"""
Quick test script for the meta_agent module.
This tests basic functionality without requiring the full test suite.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path (parent of tests directory)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file BEFORE importing anything else
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.agents.meta_agent import MetaAgent
from src.core.workflow_ast import WorkflowSpec

def test_spec_parsing():
    """Test that we can parse specification files correctly."""
    print("Testing specification parsing...")

    agent = MetaAgent()

    # Test parsing simple_sequential.txt
    spec_path = project_root / "specs/examples/simple_sequential.txt"
    if not spec_path.exists():
        raise FileNotFoundError(f"Test spec file not found: {spec_path}")
    sections = agent._read_spec(str(spec_path))

    print(f"Workflow name: {sections['workflow']}")
    print(f"Description: {sections['description']}")
    print(f"Number of inputs: {len(sections['inputs'])}")
    print(f"Number of steps: {len(sections['steps'])}")
    print(f"Number of outputs: {len(sections['outputs'])}")

    assert sections['workflow'] == 'data_processing_pipeline'
    assert len(sections['inputs']) == 2
    assert len(sections['steps']) == 4
    assert len(sections['outputs']) == 3

    print("✓ Specification parsing works!\n")

def test_tool_schema():
    """Test that tool schema is properly defined."""
    print("Testing tool schema generation...")

    agent = MetaAgent()
    schema = agent._create_tool_schema()

    assert schema['type'] == 'function'
    assert schema['function']['name'] == 'generate_workflow'
    assert 'parameters' in schema['function']

    # Check required properties
    required = schema['function']['parameters']['required']
    assert 'name' in required
    assert 'description' in required
    assert 'workflow' in required

    print("✓ Tool schema is properly defined!\n")

def test_workflow_extraction_mock():
    """Test workflow extraction with a mock response."""
    print("Testing workflow extraction (mocked)...")

    # Create a mock JSON response that would come from the LLM
    mock_json = {
        "name": "data_processing_pipeline",
        "description": "Simple sequential workflow for processing customer data",
        "version": "1.0.0",
        "inputs": [
            {"name": "customer_id", "type": "string", "description": "The customer ID to process"},
            {"name": "database_url", "type": "string", "description": "Database connection URL"}
        ],
        "outputs": [
            {"name": "customer_data", "type": "object", "description": "Complete customer profile"},
            {"name": "lifetime_value", "type": "float", "description": "Calculated customer lifetime value"},
            {"name": "update_status", "type": "boolean", "description": "Whether the update was successful"}
        ],
        "workflow": {
            "type": "sequential",
            "steps": [
                {
                    "type": "tool_call",
                    "tool_name": "fetch_customer_data",
                    "parameters": {
                        "customer_id": "{{customer_id}}",
                        "database_url": "{{database_url}}"
                    },
                    "assigns_to": "raw_data"
                },
                {
                    "type": "tool_call",
                    "tool_name": "validate_data",
                    "parameters": {
                        "data": "{{raw_data}}"
                    },
                    "assigns_to": "validated_data"
                },
                {
                    "type": "tool_call",
                    "tool_name": "calculate_lifetime_value",
                    "parameters": {
                        "customer_data": "{{validated_data}}"
                    },
                    "assigns_to": "lifetime_value"
                },
                {
                    "type": "tool_call",
                    "tool_name": "update_customer_record",
                    "parameters": {
                        "customer_id": "{{customer_id}}",
                        "lifetime_value": "{{lifetime_value}}",
                        "database_url": "{{database_url}}"
                    },
                    "assigns_to": "update_status"
                }
            ]
        }
    }

    # Test conversion to AST
    agent = MetaAgent()
    workflow_spec = agent._json_to_ast(mock_json)

    assert workflow_spec.name == "data_processing_pipeline"
    assert len(workflow_spec.inputs) == 2
    assert len(workflow_spec.outputs) == 3

    # Validate the AST
    errors = workflow_spec.validate()
    if errors:
        print(f"Validation errors: {errors}")
        assert False, "Workflow validation failed"

    print("✓ Workflow extraction and validation works!\n")

    # Print the workflow for verification
    print("Generated Workflow JSON:")
    print(json.dumps(workflow_spec.to_dict(), indent=2))

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Meta-Agent Implementation")
    print("=" * 60 + "\n")

    # Check if API key is set (note: no API integration tests in this suite)
    if not os.getenv("AIMLAPI_KEY"):
        print("⚠️  Note: AIMLAPI_KEY not set. API integration tests are not included in this suite.\n")

    try:
        test_spec_parsing()
        test_tool_schema()
        test_workflow_extraction_mock()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()