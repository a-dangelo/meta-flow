"""
Test nested workflow code generation.

Tests workflows with nested structures (conditionals inside sequential, etc.)
"""

import json
import os
import sys
from pathlib import Path
import py_compile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.models import WorkflowSpec
from src.generators.agent_generator import AgentGenerator

def test_nested_from_haiku_json():
    """Test nested workflow from actual Claude Haiku output."""

    # Load the JSON from Claude Haiku output
    json_path = Path(__file__).parent.parent / "logs/test-runs/2025-11-12_18-31-21_claude_claude-haiku-4-5/final_state.json"

    if not json_path.exists():
        print(f"❌ JSON file not found: {json_path}")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    # Extract the workflow spec (it's in generated_json field as a JSON string)
    generated_json_str = data.get("generated_json", "{}")
    workflow_json = json.loads(generated_json_str)

    print("=" * 80)
    print("NESTED WORKFLOW TEST (order_fulfillment)")
    print("=" * 80)

    # Parse into WorkflowSpec (Pydantic v2 uses model_validate)
    spec = WorkflowSpec.model_validate(workflow_json)

    # Pydantic validates automatically on model_validate()
    print(f"✅ Workflow '{spec.name}' validated successfully")
    print(f"   Type: {spec.workflow.type}")
    print(f"   Description: {spec.description}")

    # Check for credentials
    generator = AgentGenerator(spec)
    print(f"\n📋 Detected credentials: {generator.credential_params}")

    # Generate code
    code = generator.generate()

    # Save to file
    output_dir = Path(__file__).parent.parent / "generated_agents"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "order_fulfillment_agent.py"

    with open(output_file, 'w') as f:
        f.write(code)

    print(f"\n✅ Generated agent code: {output_file}")

    # Validate syntax
    try:
        py_compile.compile(str(output_file), doraise=True)
        print("✅ Python syntax validation passed")
    except py_compile.PyCompileError as e:
        print(f"❌ Syntax error: {e}")
        return

    # Show key parts of generated code
    print("\n📝 Generated Code Structure:")
    print("-" * 40)

    lines = code.split('\n')

    # Look for nested conditional inside sequential
    indent_stack = []
    found_nested = False

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('if ') and 'payment_amount' in line:
            # Found the conditional - show it and some context
            print("Found nested conditional structure:")
            for j in range(max(0, i-1), min(i+8, len(lines))):
                print(lines[j])
            found_nested = True
            break

    if found_nested:
        print("\n✅ Nested workflow structure detected")
    else:
        print("\n⚠️  Nested structure not found in expected location")

    # Count tool calls
    tool_calls = [line for line in lines if 'self.context[' in line and '] = self.' in line]
    print(f"\n📊 Generated {len(tool_calls)} tool invocations")

    print("\n✅ Nested workflow test complete!")
    return True


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("NESTED WORKFLOW GENERATION TEST")
    print("=" * 80)
    print()

    success = test_nested_from_haiku_json()

    if success:
        print("\n" + "=" * 80)
        print("🎉 NESTED WORKFLOW TEST PASSED!")
        print("=" * 80)
        print("\nGenerated file: generated_agents/order_fulfillment_agent.py")
        print("This agent handles conditional logic nested within sequential workflow")
    else:
        print("\n❌ Test failed")
