"""
Unit tests for agent_generator.py

Tests code generation from WorkflowSpec AST to executable Python agents.
Covers credential detection, tool stub generation, and workflow node traversal.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.agents.models import WorkflowSpec
from src.generators.agent_generator import AgentGenerator


class TestAgentGenerator:
    """Test suite for AgentGenerator class."""

    @pytest.fixture
    def simple_sequential_spec(self):
        """Load simple_sequential example from logs."""
        log_path = Path('logs/test-runs/2025-11-12_18-31-12_claude_claude-haiku-4-5/final_state.json')
        with open(log_path) as f:
            state = json.load(f)
        return WorkflowSpec.model_validate(state['workflow_spec'])

    def test_generator_initialization(self, simple_sequential_spec):
        """Test AgentGenerator initializes correctly."""
        generator = AgentGenerator(simple_sequential_spec)

        assert generator.spec == simple_sequential_spec
        assert isinstance(generator.credential_params, set)
        assert isinstance(generator.all_tools, set)

    def test_credential_detection(self, simple_sequential_spec):
        """Test credential parameter detection."""
        generator = AgentGenerator(simple_sequential_spec)

        # simple_sequential has database_url as credential
        assert 'database_url' in generator.credential_params
        assert 'customer_id' not in generator.credential_params

    def test_tool_collection(self, simple_sequential_spec):
        """Test all tools are collected from workflow."""
        generator = AgentGenerator(simple_sequential_spec)

        expected_tools = {
            'fetch_customer_data',
            'validate_customer_data',
            'calculate_customer_lifetime_value',
            'update_customer_record'
        }
        assert generator.all_tools == expected_tools

    def test_is_credential_parameter(self, simple_sequential_spec):
        """Test credential parameter pattern matching."""
        generator = AgentGenerator(simple_sequential_spec)

        # Should detect these as credentials
        assert generator._is_credential_parameter('api_key')
        assert generator._is_credential_parameter('DATABASE_URL')
        assert generator._is_credential_parameter('auth_token')
        assert generator._is_credential_parameter('webhook')

        # Should not detect these
        assert not generator._is_credential_parameter('customer_id')
        assert not generator._is_credential_parameter('user_name')
        assert not generator._is_credential_parameter('amount')

    def test_class_name_conversion(self, simple_sequential_spec):
        """Test snake_case to PascalCase conversion."""
        generator = AgentGenerator(simple_sequential_spec)

        assert generator._to_class_name('data_processing_pipeline') == 'DataProcessingPipelineAgent'
        assert generator._to_class_name('simple_workflow') == 'SimpleWorkflowAgent'

    def test_variable_resolution(self, simple_sequential_spec):
        """Test {{variable}} to self.context['variable'] conversion."""
        generator = AgentGenerator(simple_sequential_spec)

        # Simple variable
        assert generator._resolve_variable_reference('{{customer_id}}') == "self.context['customer_id']"

        # Nested property
        result = generator._resolve_variable_reference('{{customer.name}}')
        assert 'customer' in result
        assert 'name' in result

        # Non-variable string
        assert generator._resolve_variable_reference('literal_string') == "'literal_string'"

    def test_generate_produces_valid_python(self, simple_sequential_spec):
        """Test that generated code is syntactically valid Python."""
        generator = AgentGenerator(simple_sequential_spec)
        code = generator.generate()

        # Should be non-empty
        assert len(code) > 0

        # Should contain expected elements
        assert 'import os' in code
        assert 'class DataProcessingPipelineAgent:' in code
        assert 'def execute(self, **inputs)' in code
        assert 'def __init__(self)' in code

        # Should have module docstring
        assert '"""' in code
        assert 'Auto-generated agent' in code

        # Should have credential setup instructions
        assert 'SETUP INSTRUCTIONS' in code
        assert 'DATABASE_URL' in code
        assert 'export DATABASE_URL' in code

    def test_no_hardcoded_credentials(self, simple_sequential_spec):
        """Test that generated code has no hardcoded credentials."""
        generator = AgentGenerator(simple_sequential_spec)
        code = generator.generate()

        # All credential parameters should use os.getenv()
        assert 'os.getenv(' in code
        assert 'DATABASE_URL' in code

        # Should have error handling for missing env vars
        assert 'Missing DATABASE_URL environment variable' in code
        assert 'raise ValueError' in code

    def test_tool_stubs_generated(self, simple_sequential_spec):
        """Test that all tool stubs are generated."""
        generator = AgentGenerator(simple_sequential_spec)
        code = generator.generate()

        # All 4 tools should have stub methods
        assert 'def fetch_customer_data(' in code
        assert 'def validate_customer_data(' in code
        assert 'def calculate_customer_lifetime_value(' in code
        assert 'def update_customer_record(' in code

        # Stubs should have TODO comments
        assert 'TODO: Implement actual tool logic' in code

    def test_main_block_generated(self, simple_sequential_spec):
        """Test that example usage block is generated."""
        generator = AgentGenerator(simple_sequential_spec)
        code = generator.generate()

        assert 'if __name__ == "__main__":' in code
        assert 'agent = DataProcessingPipelineAgent()' in code
        assert 'agent.execute(**inputs)' in code


class TestGenerateAndSave:
    """Integration test: generate agent and save to file."""

    def test_generate_simple_sequential_agent(self):
        """Generate agent from simple_sequential and save to file."""
        # Load spec
        log_path = Path('logs/test-runs/2025-11-12_18-31-12_claude_claude-haiku-4-5/final_state.json')
        with open(log_path) as f:
            state = json.load(f)
        spec = WorkflowSpec.model_validate(state['workflow_spec'])

        # Generate code
        generator = AgentGenerator(spec)
        python_code = generator.generate()

        # Save to generated_agents/
        output_file = Path('generated_agents/data_processing_pipeline_agent.py')
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(python_code)

        print(f"\n✓ Generated agent saved to: {output_file}")
        print(f"✓ Code length: {len(python_code)} characters")
        print(f"✓ Lines: {len(python_code.splitlines())}")

        # Verify file was created
        assert output_file.exists()

        # Verify it's valid Python syntax
        import py_compile
        py_compile.compile(str(output_file), doraise=True)

        print("✓ Generated code passes Python syntax validation")


if __name__ == '__main__':
    # Run the integration test directly
    test = TestGenerateAndSave()
    test.test_generate_simple_sequential_agent()
