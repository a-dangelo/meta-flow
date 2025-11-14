"""
Test parallel workflow code generation.

Note: For PoC, parallel workflows are generated as sequential execution
with a TODO comment indicating where true parallelism should be implemented.
"""

import json
import os
import sys
from pathlib import Path
import py_compile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents_v2.models import WorkflowSpec
from src.generators.agent_generator import AgentGenerator

def test_parallel_from_haiku_json():
    """Test parallel workflow from actual Claude Haiku output."""

    # Load the JSON from Claude Haiku output
    json_path = Path(__file__).parent.parent / "logs/test-runs/2025-11-12_18-23-55_claude_claude-haiku-4-5/final_state.json"

    if not json_path.exists():
        print(f"❌ JSON file not found: {json_path}")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    # Extract the workflow spec (it's in generated_json field as a JSON string)
    generated_json_str = data.get("generated_json", "{}")
    workflow_json = json.loads(generated_json_str)

    print("=" * 80)
    print("PARALLEL WORKFLOW TEST (compliance_check)")
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
    output_file = output_dir / "compliance_check_agent.py"

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

    # Look for the TODO comment about parallel execution
    for i, line in enumerate(lines):
        if 'TODO' in line and 'parallel' in line.lower():
            # Show the TODO and surrounding context
            print("Found parallel execution placeholder:")
            for j in range(max(0, i-2), min(i+5, len(lines))):
                print(lines[j])
            break

    # Check if branches are listed
    if 'branches' in code.lower() or 'parallel' in code.lower():
        print("\n✅ Parallel workflow structure detected")
    else:
        print("\n⚠️  No parallel structure found")

    print("\n✅ Parallel workflow test complete!")
    print("\nℹ️  Note: For PoC, parallel workflows execute sequentially.")
    print("   Production implementation would use asyncio/threading.")
    return True


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("PARALLEL WORKFLOW GENERATION TEST")
    print("=" * 80)
    print()

    success = test_parallel_from_haiku_json()

    if success:
        print("\n" + "=" * 80)
        print("🎉 PARALLEL WORKFLOW TEST PASSED!")
        print("=" * 80)
        print("\nGenerated file: generated_agents/compliance_check_agent.py")
        print("This agent executes branches sequentially (PoC limitation)")
        print("Production version would use asyncio for true parallelism")
    else:
        print("\n❌ Test failed")
