"""
Test orchestrator workflow code generation.

Tests both nested conditional approach (what Claude Haiku generates)
and true OrchestratorWorkflow type (theoretical pattern).
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

def test_orchestrator_from_haiku_json():
    """Test orchestrator pattern from actual Claude Haiku output (nested conditionals)."""

    # Load the JSON from Claude Haiku output
    json_path = Path(__file__).parent.parent / "logs/test-runs/2025-11-12_18-31-40_claude_claude-haiku-4-5/final_state.json"

    if not json_path.exists():
        print(f"❌ JSON file not found: {json_path}")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    # Extract the workflow spec (it's in generated_json field as a JSON string)
    generated_json_str = data.get("generated_json", "{}")
    workflow_json = json.loads(generated_json_str)

    print("=" * 80)
    print("ORCHESTRATOR WORKFLOW TEST (support_ticket_router)")
    print("=" * 80)

    # Parse into WorkflowSpec (Pydantic v2 uses model_validate)
    spec = WorkflowSpec.model_validate(workflow_json)

    # Pydantic validates automatically on model_validate()
    # If we got here without exception, validation passed
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
    output_file = output_dir / "support_ticket_router_agent.py"

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
    print("\n📝 Generated Code Structure (excerpt):")
    print("-" * 40)

    # Extract the conditional logic part
    lines = code.split('\n')
    in_execute = False
    condition_lines = []

    for i, line in enumerate(lines):
        if 'def execute(self' in line:
            in_execute = True
        elif in_execute and ('if ' in line or 'elif ' in line or 'else:' in line):
            # Capture conditional lines and a few after
            for j in range(i, min(i+3, len(lines))):
                if lines[j].strip():
                    condition_lines.append(lines[j])

    if condition_lines:
        print("Conditional routing logic found:")
        for line in condition_lines[:20]:  # Show first 20 lines of conditions
            print(line)

    print("\n✅ Orchestrator pattern test complete!")
    return True

def test_true_orchestrator_workflow():
    """Test code generation for true OrchestratorWorkflow type with routing_rules."""

    from src.agents.models import (
        WorkflowSpec,
        OrchestratorWorkflow,
        RoutingRule,
        ToolCall
    )

    print("\n" + "=" * 80)
    print("TRUE ORCHESTRATORWORKFLOW TYPE TEST")
    print("=" * 80)

    # Create an OrchestratorWorkflow directly
    orchestrator = OrchestratorWorkflow(
        sub_workflows={
            "billing_route": ToolCall(
                tool_name="handle_billing",
                parameters={"ticket_id": "{{ticket_id}}"},
                assigns_to="billing_result"
            ),
            "technical_route": ToolCall(
                tool_name="handle_technical",
                parameters={"ticket_id": "{{ticket_id}}"},
                assigns_to="tech_result"
            ),
            "general_route": ToolCall(
                tool_name="handle_general",
                parameters={"ticket_id": "{{ticket_id}}"},
                assigns_to="general_result"
            ),
        },
        routing_rules=[
            RoutingRule(
                condition="{{ticket_type}} == 'billing'",
                workflow_name="billing_route"
            ),
            RoutingRule(
                condition="{{ticket_type}} == 'technical'",
                workflow_name="technical_route"
            ),
        ],
        default_workflow="general_route",
        description="Route tickets based on type"
    )

    # Wrap in WorkflowSpec
    spec = WorkflowSpec(
        name="ticket_router",
        description="Routes tickets to appropriate handlers",
        version="1.0.0",
        inputs=[
            {"name": "ticket_id", "type": "string", "description": "Ticket ID"},
            {"name": "ticket_type", "type": "string", "description": "Type of ticket"},
        ],
        outputs=[
            {"name": "result", "type": "object", "description": "Routing result"},
        ],
        workflow=orchestrator
    )

    # Pydantic validates automatically on creation
    # If we got here without exception, validation passed
    print("✅ OrchestratorWorkflow validated successfully")

    # Generate code
    generator = AgentGenerator(spec)
    code = generator.generate()

    # Save to file
    output_dir = Path(__file__).parent.parent / "generated_agents"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "ticket_router_orchestrator_agent.py"

    with open(output_file, 'w') as f:
        f.write(code)

    print(f"✅ Generated agent code: {output_file}")

    # Validate syntax
    try:
        py_compile.compile(str(output_file), doraise=True)
        print("✅ Python syntax validation passed")
    except py_compile.PyCompileError as e:
        print(f"❌ Syntax error: {e}")
        return

    # Show the if-elif-else structure
    print("\n📝 Generated if-elif-else structure:")
    print("-" * 40)
    lines = code.split('\n')
    for i, line in enumerate(lines):
        if 'Route tickets based on type' in line:
            # Show the orchestrator section
            for j in range(i, min(i+15, len(lines))):
                print(lines[j])
            break

    print("\n✅ True OrchestratorWorkflow test complete!")
    return True

if __name__ == "__main__":
    # Test both patterns
    success1 = test_orchestrator_from_haiku_json()
    success2 = test_true_orchestrator_workflow()

    if success1 and success2:
        print("\n" + "=" * 80)
        print("🎉 ALL ORCHESTRATOR TESTS PASSED!")
        print("=" * 80)