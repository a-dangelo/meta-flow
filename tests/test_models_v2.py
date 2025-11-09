"""
Unit tests for enhanced Pydantic models (v2).

Tests cover:
- Field validation (names, types, formats)
- Model validation (business logic)
- Credential detection
- Variable reference validation
- DAG validation
- Error messages
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.agents_v2.models import (
    WorkflowInput,
    WorkflowOutput,
    ToolCall,
    SequentialWorkflow,
    ConditionalWorkflow,
    ParallelWorkflow,
    RoutingRule,
    OrchestratorWorkflow,
    WorkflowSpec,
)


# ===== WorkflowInput Tests =====

def test_workflow_input_valid():
    """Test valid workflow input creation."""
    inp = WorkflowInput(
        name="customer_id",
        type="string",
        description="Customer identifier"
    )
    assert inp.name == "customer_id"
    assert inp.type == "string"
    assert inp.is_credential is False


def test_workflow_input_credential_detection():
    """Test automatic credential detection."""
    # Test various credential patterns
    credential_names = [
        "api_key", "apikey", "token", "password", "secret",
        "database_url", "db_url", "auth_token", "bearer_token"
    ]

    for name in credential_names:
        inp = WorkflowInput(name=name, type="string")
        assert inp.is_credential is True, f"{name} should be detected as credential"


def test_workflow_input_invalid_name():
    """Test invalid parameter names."""
    invalid_names = [
        "123invalid",  # Starts with number
        "kebab-case",  # Hyphens not allowed
        "UPPERCASE",   # Must be lowercase
        "has space",   # Spaces not allowed
        "has.dot",     # Dots not allowed
    ]

    for name in invalid_names:
        with pytest.raises(PydanticValidationError) as exc_info:
            WorkflowInput(name=name, type="string")
        assert "Invalid parameter name" in str(exc_info.value)


def test_workflow_input_invalid_type():
    """Test invalid parameter types."""
    with pytest.raises(PydanticValidationError) as exc_info:
        WorkflowInput(name="param", type="invalid_type")
    assert "Invalid type" in str(exc_info.value)


def test_workflow_input_name_too_long():
    """Test parameter name length limit."""
    long_name = "a" * 65  # 65 chars, max is 64
    with pytest.raises(PydanticValidationError) as exc_info:
        WorkflowInput(name=long_name, type="string")
    assert "too long" in str(exc_info.value)


# ===== ToolCall Tests =====

def test_tool_call_valid():
    """Test valid tool call creation."""
    tool = ToolCall(
        tool_name="fetch_data",
        parameters={"id": "{{customer_id}}"},
        assigns_to="customer_data"
    )
    assert tool.tool_name == "fetch_data"
    assert tool.parameters == {"id": "{{customer_id}}"}
    assert tool.assigns_to == "customer_data"


def test_tool_call_invalid_tool_name():
    """Test invalid tool names."""
    invalid_names = ["123start", "has-dash", "HAS_CAPS", "has space"]

    for name in invalid_names:
        with pytest.raises(PydanticValidationError) as exc_info:
            ToolCall(tool_name=name, parameters={})
        assert "Invalid tool name" in str(exc_info.value)


def test_tool_call_invalid_variable_reference():
    """Test invalid variable reference format."""
    with pytest.raises(PydanticValidationError) as exc_info:
        ToolCall(
            tool_name="test_tool",
            parameters={"data": "{{INVALID_CAPS}}"}  # Must be lowercase
        )
    assert "Invalid variable reference" in str(exc_info.value)


def test_tool_call_invalid_parameter_key():
    """Test invalid parameter keys."""
    with pytest.raises(PydanticValidationError) as exc_info:
        ToolCall(
            tool_name="test_tool",
            parameters={"invalid-key": "value"}  # Hyphens not allowed
        )
    assert "Invalid parameter key" in str(exc_info.value)


# ===== SequentialWorkflow Tests =====

def test_sequential_workflow_valid():
    """Test valid sequential workflow."""
    workflow = SequentialWorkflow(
        steps=[
            ToolCall(tool_name="step1", parameters={}),
            ToolCall(tool_name="step2", parameters={}),
        ]
    )
    assert len(workflow.steps) == 2


def test_sequential_workflow_empty_steps():
    """Test that empty steps are rejected."""
    with pytest.raises(PydanticValidationError) as exc_info:
        SequentialWorkflow(steps=[])
    assert "at least one step" in str(exc_info.value)


def test_sequential_workflow_too_many_steps():
    """Test workflow complexity limit."""
    steps = [ToolCall(tool_name=f"step_{i}", parameters={}) for i in range(101)]
    with pytest.raises(PydanticValidationError) as exc_info:
        SequentialWorkflow(steps=steps)
    assert "too complex" in str(exc_info.value)


# ===== ConditionalWorkflow Tests =====

def test_conditional_workflow_valid():
    """Test valid conditional workflow."""
    workflow = ConditionalWorkflow(
        condition="{{status}} == 'approved'",
        if_branch=ToolCall(tool_name="approve", parameters={}),
        else_branch=ToolCall(tool_name="reject", parameters={})
    )
    assert workflow.condition == "{{status}} == 'approved'"


def test_conditional_workflow_no_operator():
    """Test condition requires comparison operator."""
    with pytest.raises(PydanticValidationError) as exc_info:
        ConditionalWorkflow(
            condition="just_a_variable",  # No operator
            if_branch=ToolCall(tool_name="test", parameters={})
        )
    assert "comparison operator" in str(exc_info.value)


def test_conditional_workflow_dangerous_patterns():
    """Test detection of dangerous condition patterns."""
    dangerous_conditions = [
        "import os",
        "exec('code')",
        "eval('code')",
        "__import__('os')",
        "open('file')",
        "lambda x: x",
    ]

    for condition in dangerous_conditions:
        with pytest.raises(PydanticValidationError) as exc_info:
            ConditionalWorkflow(
                condition=condition,
                if_branch=ToolCall(tool_name="test", parameters={})
            )
        # These patterns are rejected by either:
        # 1. "Unsafe pattern" check (if they contain dangerous keywords)
        # 2. "Condition must contain comparison operator" (if they lack operators)
        # Both are valid rejections
        error_msg = str(exc_info.value)
        assert ("Unsafe pattern" in error_msg or "comparison operator" in error_msg)


def test_conditional_workflow_dangerous_patterns_with_operators():
    """Test that dangerous patterns with operators are still caught."""
    # These have valid operators but contain dangerous patterns
    dangerous_with_ops = [
        "import('os') == True",
        "exec('code') > 0",
        "eval('x') in list",
        "__import__('os') is not None",
    ]

    for condition in dangerous_with_ops:
        with pytest.raises(PydanticValidationError) as exc_info:
            ConditionalWorkflow(
                condition=condition,
                if_branch=ToolCall(tool_name="test", parameters={})
            )
        # These MUST be caught by "Unsafe pattern" check
        assert "Unsafe pattern" in str(exc_info.value)


def test_conditional_workflow_valid_operators():
    """Test all valid comparison operators."""
    valid_conditions = [
        "{{x}} > 5",
        "{{x}} < 10",
        "{{x}} == 'value'",
        "{{x}} != 'value'",
        "{{x}} >= 5",
        "{{x}} <= 10",
        "{{x}} > 5 and {{y}} < 10",
        "{{x}} == 'a' or {{y}} == 'b'",
        "not {{flag}}",
        "{{item}} in {{list}}",
    ]

    for condition in valid_conditions:
        workflow = ConditionalWorkflow(
            condition=condition,
            if_branch=ToolCall(tool_name="test", parameters={})
        )
        assert workflow.condition == condition


# ===== ParallelWorkflow Tests =====

def test_parallel_workflow_valid():
    """Test valid parallel workflow."""
    workflow = ParallelWorkflow(
        branches=[
            ToolCall(tool_name="branch1", parameters={}),
            ToolCall(tool_name="branch2", parameters={}),
        ],
        wait_for_all=True
    )
    assert len(workflow.branches) == 2
    assert workflow.wait_for_all is True


def test_parallel_workflow_single_branch():
    """Test parallel workflow requires at least 2 branches."""
    with pytest.raises(PydanticValidationError) as exc_info:
        ParallelWorkflow(
            branches=[ToolCall(tool_name="only_one", parameters={})]
        )
    assert "at least 2 branches" in str(exc_info.value)


def test_parallel_workflow_too_many_branches():
    """Test parallel workflow branch limit."""
    branches = [ToolCall(tool_name=f"branch_{i}", parameters={}) for i in range(11)]
    with pytest.raises(PydanticValidationError) as exc_info:
        ParallelWorkflow(branches=branches)
    assert "Too many parallel branches" in str(exc_info.value)


# ===== OrchestratorWorkflow Tests =====

def test_orchestrator_workflow_valid():
    """Test valid orchestrator workflow."""
    workflow = OrchestratorWorkflow(
        sub_workflows={
            "route_a": ToolCall(tool_name="handle_a", parameters={}),
            "route_b": ToolCall(tool_name="handle_b", parameters={}),
        },
        routing_rules=[
            RoutingRule(condition="{{type}} == 'A'", workflow_name="route_a"),
            RoutingRule(condition="{{type}} == 'B'", workflow_name="route_b"),
        ],
        default_workflow="route_a"
    )
    assert len(workflow.sub_workflows) == 2
    assert len(workflow.routing_rules) == 2


def test_orchestrator_undefined_route():
    """Test routing rule references undefined workflow."""
    with pytest.raises(PydanticValidationError) as exc_info:
        OrchestratorWorkflow(
            sub_workflows={
                "route_a": ToolCall(tool_name="handle_a", parameters={})
            },
            routing_rules=[
                RoutingRule(condition="{{x}} == 1", workflow_name="undefined_route")
            ]
        )
    assert "undefined workflow" in str(exc_info.value)


def test_orchestrator_undefined_default():
    """Test default workflow must exist."""
    with pytest.raises(PydanticValidationError) as exc_info:
        OrchestratorWorkflow(
            sub_workflows={
                "route_a": ToolCall(tool_name="handle_a", parameters={})
            },
            routing_rules=[
                RoutingRule(condition="{{x}} == 1", workflow_name="route_a")
            ],
            default_workflow="nonexistent"
        )
    assert "not found in sub_workflows" in str(exc_info.value)


# ===== WorkflowSpec Tests =====

def test_workflow_spec_valid():
    """Test valid workflow spec creation."""
    spec = WorkflowSpec(
        name="test_workflow",
        description="Test workflow",
        version="1.0.0",
        inputs=[
            WorkflowInput(name="input_data", type="string")
        ],
        outputs=[
            WorkflowOutput(name="result", type="string")
        ],
        workflow=ToolCall(
            tool_name="process_data",
            parameters={"data": "{{input_data}}"},
            assigns_to="result"
        )
    )
    assert spec.name == "test_workflow"


def test_workflow_spec_invalid_name():
    """Test workflow spec name validation."""
    with pytest.raises(PydanticValidationError) as exc_info:
        WorkflowSpec(
            name="Invalid-Name",  # Hyphens not allowed
            description="Test",
            workflow=ToolCall(tool_name="test", parameters={})
        )
    assert "Invalid workflow name" in str(exc_info.value)


def test_workflow_spec_invalid_version():
    """Test semantic version validation."""
    with pytest.raises(PydanticValidationError) as exc_info:
        WorkflowSpec(
            name="test_workflow",
            description="Test",
            version="1.0",  # Must be X.Y.Z
            workflow=ToolCall(tool_name="test", parameters={})
        )
    assert "semantic version" in str(exc_info.value)


def test_workflow_spec_undefined_variable():
    """Test detection of undefined variable references."""
    with pytest.raises(PydanticValidationError) as exc_info:
        WorkflowSpec(
            name="test_workflow",
            description="Test",
            inputs=[WorkflowInput(name="valid_input", type="string")],
            outputs=[],
            workflow=ToolCall(
                tool_name="test",
                parameters={"data": "{{undefined_var}}"}  # Not in inputs
            )
        )
    assert "undefined variable" in str(exc_info.value)


def test_workflow_spec_variable_flow():
    """Test valid variable flow through workflow."""
    spec = WorkflowSpec(
        name="test_workflow",
        description="Test variable flow",
        inputs=[WorkflowInput(name="input_data", type="string")],
        outputs=[WorkflowOutput(name="final_result", type="string")],
        workflow=SequentialWorkflow(
            steps=[
                ToolCall(
                    tool_name="step1",
                    parameters={"data": "{{input_data}}"},
                    assigns_to="intermediate"
                ),
                ToolCall(
                    tool_name="step2",
                    parameters={"data": "{{intermediate}}"},  # Uses step1's output
                    assigns_to="final_result"
                ),
            ]
        )
    )
    assert spec.name == "test_workflow"


def test_workflow_spec_json_serialization():
    """Test JSON serialization and deserialization."""
    original = WorkflowSpec(
        name="test_workflow",
        description="Test",
        inputs=[WorkflowInput(name="input1", type="string")],
        outputs=[WorkflowOutput(name="output1", type="string")],
        workflow=ToolCall(
            tool_name="process",
            parameters={"data": "{{input1}}"},
            assigns_to="output1"
        )
    )

    # Serialize to JSON
    json_str = original.to_json()
    assert isinstance(json_str, str)

    # Deserialize back
    restored = WorkflowSpec.from_json(json_str)
    assert restored.name == original.name
    assert restored.description == original.description


def test_workflow_spec_dict_serialization():
    """Test dict serialization (v1 compatibility)."""
    spec = WorkflowSpec(
        name="test_workflow",
        description="Test",
        workflow=ToolCall(tool_name="test", parameters={})
    )

    data = spec.to_dict()
    assert isinstance(data, dict)
    assert data['name'] == "test_workflow"

    # Deserialize back
    restored = WorkflowSpec.from_dict(data)
    assert restored.name == spec.name


# ===== Edge Cases =====

def test_nested_workflows():
    """Test deeply nested workflow structures."""
    spec = WorkflowSpec(
        name="nested_workflow",
        description="Test nesting",
        inputs=[WorkflowInput(name="x", type="int")],
        outputs=[WorkflowOutput(name="result", type="string")],
        workflow=SequentialWorkflow(
            steps=[
                ConditionalWorkflow(
                    condition="{{x}} > 10",
                    if_branch=SequentialWorkflow(
                        steps=[
                            ToolCall(tool_name="step1", parameters={"x": "{{x}}"}, assigns_to="y"),
                            ToolCall(tool_name="step2", parameters={"y": "{{y}}"}, assigns_to="result"),
                        ]
                    ),
                    else_branch=ToolCall(tool_name="default", parameters={}, assigns_to="result")
                )
            ]
        )
    )
    assert spec.name == "nested_workflow"


def test_minimal_workflow():
    """Test minimal valid workflow."""
    spec = WorkflowSpec(
        name="minimal",
        description="Minimal workflow",
        workflow=ToolCall(tool_name="single_step", parameters={})
    )
    assert spec.name == "minimal"
    assert len(spec.inputs) == 0
    assert len(spec.outputs) == 0


def test_unicode_in_descriptions():
    """Test Unicode characters in descriptions."""
    spec = WorkflowSpec(
        name="unicode_test",
        description="Test with emoji 🚀 and Unicode: ℃ °C ™",
        workflow=ToolCall(
            tool_name="test",
            parameters={},
            description="Process data 📊"
        )
    )
    assert "🚀" in spec.description


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
