"""
End-to-end integration tests for complete pipeline.

Tests the full flow: Text spec → JSON → Python agent
"""

import pytest
import sys
from pathlib import Path
import importlib.util
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli.complete_pipeline import (
    read_spec_file,
    run_phase1_meta_agent,
    run_phase2_code_generation,
    validate_python_syntax,
    save_outputs,
    setup_logging
)


class TestCompletePipeline:
    """End-to-end pipeline tests."""

    @pytest.fixture
    def specs_dir(self):
        """Path to example specifications."""
        return Path(__file__).parent.parent / "specs" / "examples"

    @pytest.fixture
    def output_dir(self, tmp_path):
        """Temporary output directory for tests."""
        return tmp_path / "test_outputs"

    @pytest.fixture
    def logger(self):
        """Test logger instance."""
        return setup_logging(verbose=False)

    EXAMPLE_SPECS = [
        'simple_sequential.txt',
        'conditional_branch.txt',
        'nested_workflow.txt',
        'orchestrator_example.txt',
        'parallel_example.txt'
    ]

    @pytest.mark.parametrize('spec_name', EXAMPLE_SPECS)
    def test_end_to_end_pipeline(self, spec_name, specs_dir, output_dir, logger):
        """
        Test complete pipeline for each example spec.

        Flow:
        1. Read text specification
        2. Run Phase 1 (meta-agent)
        3. Run Phase 2 (code generation)
        4. Validate Python syntax
        5. Save outputs
        6. Verify agent is importable
        """
        spec_path = specs_dir / spec_name

        # Step 1: Read spec
        spec_text = read_spec_file(spec_path, logger)
        assert len(spec_text) > 0

        # Step 2: Phase 1 (meta-agent)
        final_state = run_phase1_meta_agent(
            spec_text,
            llm_provider='claude',
            model_version=None,  # Use default
            logger=logger
        )
        assert final_state['execution_status'] == 'complete'
        assert 'workflow_spec' in final_state

        workflow_spec = final_state['workflow_spec']
        assert workflow_spec.name is not None

        # Step 3: Phase 2 (code generation)
        python_code = run_phase2_code_generation(workflow_spec, logger)
        assert len(python_code) > 0
        assert 'import os' in python_code or 'from typing import' in python_code

        # Step 4: Validate syntax
        output_path = output_dir / f"{workflow_spec.name}_agent.py"
        syntax_valid = validate_python_syntax(python_code, output_path, logger)
        assert syntax_valid, f"Generated code for {spec_name} has syntax errors"

        # Step 5: Save outputs
        outputs = save_outputs(workflow_spec, python_code, output_dir, True, logger)
        assert 'python' in outputs
        assert 'json' in outputs
        assert outputs['python'].exists()
        assert outputs['json'].exists()

        # Step 6: Verify importable
        agent_module = self._import_agent(outputs['python'])
        assert agent_module is not None

        # Step 7: Verify execute method exists
        class_name = self._get_class_name(workflow_spec.name)
        assert hasattr(agent_module, class_name)

        agent_class = getattr(agent_module, class_name)
        assert hasattr(agent_class, 'execute')

    def _import_agent(self, agent_path: Path):
        """Dynamically import generated agent module."""
        spec = importlib.util.spec_from_file_location("test_agent", agent_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _get_class_name(self, workflow_name: str) -> str:
        """Convert workflow name to PascalCase class name."""
        return ''.join(word.capitalize() for word in workflow_name.split('_')) + 'Agent'

    def test_validate_only_mode(self, specs_dir, logger):
        """Test validate-only mode (no code generation)."""
        spec_path = specs_dir / 'simple_sequential.txt'
        spec_text = read_spec_file(spec_path, logger)

        # Run Phase 1 only
        final_state = run_phase1_meta_agent(
            spec_text,
            llm_provider='claude',
            model_version=None,  # Use default
            logger=logger
        )
        assert final_state['execution_status'] == 'complete'
        assert 'workflow_spec' in final_state

        # In validate-only mode, we would stop here (tested via CLI)

    def test_error_handling_missing_file(self, logger):
        """Test error handling for missing spec file."""
        missing_path = Path("/nonexistent/spec.txt")

        with pytest.raises(FileNotFoundError):
            read_spec_file(missing_path, logger)

    def test_read_spec_file(self, specs_dir, logger):
        """Test reading specification files."""
        for spec_name in self.EXAMPLE_SPECS:
            spec_path = specs_dir / spec_name
            content = read_spec_file(spec_path, logger)

            # Should have content
            assert len(content) > 0

            # Should have basic structure
            assert 'Workflow:' in content or 'workflow:' in content.lower()


class TestOutputGeneration:
    """Test output file generation."""

    @pytest.fixture
    def logger(self):
        """Test logger instance."""
        return setup_logging(verbose=False)

    def test_save_outputs_with_json(self, tmp_path, logger):
        """Test saving outputs with JSON enabled."""
        from src.agents.models import WorkflowSpec, SequentialWorkflow, ToolCall

        # Create a simple workflow spec
        spec = WorkflowSpec(
            name="test_workflow",
            description="Test workflow",
            version="1.0.0",
            inputs=[{"name": "input1", "type": "string"}],
            outputs=[{"name": "output1", "type": "string"}],
            workflow=SequentialWorkflow(
                steps=[
                    ToolCall(
                        tool_name="test_tool",
                        parameters={"param": "{{input1}}"},
                        assigns_to="output1"
                    )
                ]
            )
        )

        python_code = "# Test code\nprint('hello')"

        outputs = save_outputs(spec, python_code, tmp_path, True, logger)

        # Should have both files
        assert 'python' in outputs
        assert 'json' in outputs
        assert outputs['python'].exists()
        assert outputs['json'].exists()

        # Verify JSON content
        with open(outputs['json']) as f:
            json_data = json.load(f)
        assert json_data['name'] == 'test_workflow'

        # Verify Python content
        with open(outputs['python']) as f:
            python_content = f.read()
        assert python_content == python_code

    def test_save_outputs_without_json(self, tmp_path, logger):
        """Test saving outputs with JSON disabled."""
        from src.agents.models import WorkflowSpec, SequentialWorkflow, ToolCall

        spec = WorkflowSpec(
            name="test_workflow_no_json",
            description="Test workflow",
            version="1.0.0",
            inputs=[{"name": "input1", "type": "string"}],
            outputs=[{"name": "output1", "type": "string"}],
            workflow=SequentialWorkflow(
                steps=[
                    ToolCall(
                        tool_name="test_tool",
                        parameters={"param": "{{input1}}"},
                        assigns_to="output1"
                    )
                ]
            )
        )

        python_code = "# Test code\nprint('hello')"

        outputs = save_outputs(spec, python_code, tmp_path, False, logger)

        # Should only have Python file
        assert 'python' in outputs
        assert 'json' not in outputs
        assert outputs['python'].exists()

        # JSON should not exist
        json_path = tmp_path / f"{spec.name}.json"
        assert not json_path.exists()


class TestSyntaxValidation:
    """Test Python syntax validation."""

    @pytest.fixture
    def logger(self):
        """Test logger instance."""
        return setup_logging(verbose=False)

    def test_valid_python_syntax(self, tmp_path, logger):
        """Test validation of valid Python code."""
        valid_code = """
import os
from typing import Any

def hello():
    return "world"

class TestClass:
    def __init__(self):
        self.value = 42
"""
        output_path = tmp_path / "test_valid.py"
        result = validate_python_syntax(valid_code, output_path, logger)
        assert result is True

    def test_invalid_python_syntax(self, tmp_path, logger):
        """Test validation of invalid Python code."""
        invalid_code = """
def broken_function(
    print("missing closing paren"
"""
        output_path = tmp_path / "test_invalid.py"
        result = validate_python_syntax(invalid_code, output_path, logger)
        assert result is False
