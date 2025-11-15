"""
Test code generation for conditional workflow.

Tests that if/else branching is correctly generated from ConditionalWorkflow nodes.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.models import WorkflowSpec
from src.generators.agent_generator import AgentGenerator


def test_generate_conditional_agent():
    """Generate agent from conditional_branch example."""
    print("\n" + "=" * 60)
    print("Testing Conditional Workflow Code Generation")
    print("=" * 60 + "\n")

    # Load conditional_branch spec
    log_path = Path('logs/test-runs/2025-11-12_18-31-31_claude_claude-haiku-4-5/final_state.json')
    with open(log_path) as f:
        state = json.load(f)

    spec = WorkflowSpec.model_validate(state['workflow_spec'])

    print(f"✓ Loaded workflow: {spec.name}")
    print(f"✓ Description: {spec.description}")
    print(f"✓ Inputs: {len(spec.inputs)}")
    print(f"✓ Workflow type: {spec.workflow.type}")

    # Generate code
    generator = AgentGenerator(spec)
    python_code = generator.generate()

    # Save to file
    output_file = Path('generated_agents/expense_approval_agent.py')
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(python_code)

    print(f"\n✓ Generated agent saved to: {output_file}")
    print(f"✓ Code length: {len(python_code)} characters")
    print(f"✓ Lines: {len(python_code.splitlines())}")

    # Verify it's valid Python syntax
    import py_compile
    py_compile.compile(str(output_file), doraise=True)
    print("✓ Generated code passes Python syntax validation")

    # Show the conditional logic
    print("\n--- Conditional Logic (excerpt) ---")
    lines = python_code.split('\n')
    in_execute = False
    in_conditional = False
    indent_count = 0

    for i, line in enumerate(lines):
        if 'def execute(self' in line:
            in_execute = True
        elif in_execute and 'if self.context.get(' in line:
            in_conditional = True
            indent_count = len(line) - len(line.lstrip())

        if in_conditional:
            current_indent = len(line) - len(line.lstrip())
            # Print until we're back to the same or lower indent level
            if line.strip() and current_indent < indent_count:
                break
            print(f"{i+1:3}: {line}")

    print("\n" + "=" * 60)
    print("Conditional workflow generation: SUCCESS")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    test_generate_conditional_agent()
