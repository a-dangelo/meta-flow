"""
Unit tests for workflow AST implementation.

Tests cover:
- JSON serialization/deserialization for all node types
- Validation of required fields
- Nested workflow composition
- Edge cases (empty workflows, missing fields)
- Round-trip consistency (JSON → AST → JSON)
"""

import pytest
from typing import Any, Dict
from src.core.workflow_ast import (
    ToolCall,
    SequentialWorkflow,
    ConditionalWorkflow,
    ParallelWorkflow,
    OrchestratorWorkflow,
    WorkflowSpec,
)


class TestToolCall:
    """Tests for ToolCall node."""

    def test_basic_creation(self):
        """Test creating a simple ToolCall."""
        tool = ToolCall(
            tool_name="fetch_expense",
            parameters={"expense_id": "12345"},
            assigns_to="expense_data"
        )
        assert tool.tool_name == "fetch_expense"
        assert tool.parameters == {"expense_id": "12345"}
        assert tool.assigns_to == "expense_data"

    def test_to_dict(self):
        """Test ToolCall serialization to dict."""
        tool = ToolCall(
            tool_name="analyze_fraud",
            parameters={"expense_data": "{{expense_data}}", "api_key": "{{claude_api_key}}"},
            assigns_to="fraud_analysis"
        )
        result = tool.to_dict()

        assert result["type"] == "tool_call"
        assert result["tool_name"] == "analyze_fraud"
        assert result["parameters"]["expense_data"] == "{{expense_data}}"
        assert result["assigns_to"] == "fraud_analysis"

    def test_from_dict(self):
        """Test ToolCall deserialization from dict."""
        data = {
            "type": "tool_call",
            "tool_name": "send_email",
            "parameters": {"to": "manager@company.com", "subject": "Approval Required"},
            "assigns_to": "email_result"
        }
        tool = ToolCall.from_dict(data)

        assert tool.tool_name == "send_email"
        assert tool.parameters["to"] == "manager@company.com"
        assert tool.assigns_to == "email_result"

    def test_round_trip(self):
        """Test JSON round-trip: ToolCall → dict → ToolCall."""
        original = ToolCall(
            tool_name="query_database",
            parameters={"query": "SELECT * FROM expenses", "db_url": "{{database_url}}"},
            assigns_to="query_results"
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = ToolCall.from_dict(data)

        # Should be identical
        assert restored.to_dict() == original.to_dict()

    def test_validation_success(self):
        """Test validation passes for valid ToolCall."""
        tool = ToolCall(
            tool_name="valid_tool",
            parameters={"param": "value"},
            assigns_to="result"
        )
        errors = tool.validate()
        assert len(errors) == 0

    def test_validation_missing_tool_name(self):
        """Test validation fails when tool_name is missing."""
        tool = ToolCall(
            tool_name="",
            parameters={"param": "value"},
            assigns_to="result"
        )
        errors = tool.validate()
        assert any("tool_name" in err for err in errors)

    def test_optional_assigns_to(self):
        """Test that assigns_to is optional."""
        tool = ToolCall(
            tool_name="some_tool",
            parameters={"param": "value"},
            assigns_to=None
        )
        errors = tool.validate()
        assert len(errors) == 0  # Should be valid even without assigns_to


class TestSequentialWorkflow:
    """Tests for SequentialWorkflow node."""

    def test_basic_creation(self):
        """Test creating a simple sequential workflow."""
        step1 = ToolCall("tool1", {"x": 1}, assigns_to="result1")
        step2 = ToolCall("tool2", {"y": "{{result1}}"}, assigns_to="result2")

        workflow = SequentialWorkflow(steps=[step1, step2])
        assert len(workflow.steps) == 2

    def test_to_dict(self):
        """Test SequentialWorkflow serialization."""
        step1 = ToolCall("tool1", {"x": 1}, assigns_to="result1")
        step2 = ToolCall("tool2", {"y": "{{result1}}"}, assigns_to="result2")
        workflow = SequentialWorkflow(steps=[step1, step2])

        result = workflow.to_dict()

        assert result["type"] == "sequential"
        assert len(result["steps"]) == 2
        assert result["steps"][0]["tool_name"] == "tool1"
        assert result["steps"][1]["tool_name"] == "tool2"

    def test_from_dict(self):
        """Test SequentialWorkflow deserialization."""
        data = {
            "type": "sequential",
            "steps": [
                {
                    "type": "tool_call",
                    "tool_name": "step1",
                    "parameters": {},
                    "assigns_to": "out1"
                },
                {
                    "type": "tool_call",
                    "tool_name": "step2",
                    "parameters": {},
                    "assigns_to": "out2"
                }
            ]
        }

        workflow = SequentialWorkflow.from_dict(data)
        assert len(workflow.steps) == 2
        assert isinstance(workflow.steps[0], ToolCall)
        assert workflow.steps[0].tool_name == "step1"

    def test_round_trip(self):
        """Test JSON round-trip for SequentialWorkflow."""
        original = SequentialWorkflow(steps=[
            ToolCall("tool1", {"a": 1}, assigns_to="r1"),
            ToolCall("tool2", {"b": "{{r1}}"}, assigns_to="r2"),
            ToolCall("tool3", {"c": "{{r2}}"}, assigns_to="r3")
        ])

        data = original.to_dict()
        restored = SequentialWorkflow.from_dict(data)

        assert restored.to_dict() == original.to_dict()

    def test_validation_empty_steps(self):
        """Test validation fails for empty steps list."""
        workflow = SequentialWorkflow(steps=[])
        errors = workflow.validate()
        assert any("at least one step" in err for err in errors)

    def test_validation_invalid_nested_step(self):
        """Test validation catches errors in nested steps."""
        invalid_tool = ToolCall("", {}, assigns_to="out")  # Invalid: empty tool_name
        workflow = SequentialWorkflow(steps=[invalid_tool])

        errors = workflow.validate()
        assert len(errors) > 0  # Should catch nested validation errors


class TestConditionalWorkflow:
    """Tests for ConditionalWorkflow node."""

    def test_basic_creation(self):
        """Test creating a conditional workflow."""
        if_branch = ToolCall("approve", {}, assigns_to="result")
        else_branch = ToolCall("reject", {}, assigns_to="result")

        workflow = ConditionalWorkflow(
            condition="{{amount}} > 10000",
            if_branch=if_branch,
            else_branch=else_branch
        )

        assert workflow.condition == "{{amount}} > 10000"
        assert isinstance(workflow.if_branch, ToolCall)

    def test_to_dict(self):
        """Test ConditionalWorkflow serialization."""
        workflow = ConditionalWorkflow(
            condition="{{fraud_score}} > 0.7",
            if_branch=ToolCall("escalate", {}, assigns_to="result"),
            else_branch=ToolCall("auto_approve", {}, assigns_to="result")
        )

        result = workflow.to_dict()

        assert result["type"] == "conditional"
        assert result["condition"] == "{{fraud_score}} > 0.7"
        assert result["if_branch"]["tool_name"] == "escalate"
        assert result["else_branch"]["tool_name"] == "auto_approve"

    def test_from_dict(self):
        """Test ConditionalWorkflow deserialization."""
        data = {
            "type": "conditional",
            "condition": "{{x}} == 5",
            "if_branch": {
                "type": "tool_call",
                "tool_name": "branch_a",
                "parameters": {},
                "assigns_to": "out_a"
            },
            "else_branch": {
                "type": "tool_call",
                "tool_name": "branch_b",
                "parameters": {},
                "assigns_to": "out_b"
            }
        }

        workflow = ConditionalWorkflow.from_dict(data)
        assert workflow.condition == "{{x}} == 5"
        assert workflow.if_branch.tool_name == "branch_a"
        assert workflow.else_branch.tool_name == "branch_b"

    def test_round_trip(self):
        """Test JSON round-trip for ConditionalWorkflow."""
        original = ConditionalWorkflow(
            condition="{{status}} == 'active'",
            if_branch=ToolCall("process", {"id": "{{user_id}}"}, assigns_to="result"),
            else_branch=ToolCall("skip", {}, assigns_to="result")
        )

        data = original.to_dict()
        restored = ConditionalWorkflow.from_dict(data)

        assert restored.to_dict() == original.to_dict()

    def test_optional_else_branch(self):
        """Test conditional workflow without else branch."""
        workflow = ConditionalWorkflow(
            condition="{{flag}}",
            if_branch=ToolCall("action", {}, assigns_to="result"),
            else_branch=None
        )

        data = workflow.to_dict()
        # Verify that else_branch key is NOT included when it's None
        assert "else_branch" not in data

        # Round-trip should preserve None
        restored = ConditionalWorkflow.from_dict(data)
        assert restored.else_branch is None

    def test_validation_missing_condition(self):
        """Test validation fails when condition is missing."""
        workflow = ConditionalWorkflow(
            condition="",
            if_branch=ToolCall("tool", {}, assigns_to="out"),
            else_branch=None
        )
        errors = workflow.validate()
        assert any("condition" in err for err in errors)

    def test_validation_missing_if_branch(self):
        """Test validation fails when if_branch is missing."""
        workflow = ConditionalWorkflow(
            condition="{{x}} > 0",
            if_branch=None,
            else_branch=None
        )
        errors = workflow.validate()
        assert any("if_branch" in err for err in errors)


class TestParallelWorkflow:
    """Tests for ParallelWorkflow node."""

    def test_basic_creation(self):
        """Test creating a parallel workflow."""
        branch1 = ToolCall("task1", {}, assigns_to="result1")
        branch2 = ToolCall("task2", {}, assigns_to="result2")

        workflow = ParallelWorkflow(
            branches=[branch1, branch2],
            wait_for_all=True
        )

        assert len(workflow.branches) == 2
        assert workflow.wait_for_all is True

    def test_to_dict(self):
        """Test ParallelWorkflow serialization."""
        workflow = ParallelWorkflow(
            branches=[
                ToolCall("parallel_task_1", {"param": "a"}, assigns_to="out1"),
                ToolCall("parallel_task_2", {"param": "b"}, assigns_to="out2")
            ],
            wait_for_all=False
        )

        result = workflow.to_dict()

        assert result["type"] == "parallel"
        assert len(result["branches"]) == 2
        assert result["wait_for_all"] is False

    def test_from_dict(self):
        """Test ParallelWorkflow deserialization."""
        data = {
            "type": "parallel",
            "branches": [
                {"type": "tool_call", "tool_name": "t1", "parameters": {}, "assigns_to": "o1"},
                {"type": "tool_call", "tool_name": "t2", "parameters": {}, "assigns_to": "o2"}
            ],
            "wait_for_all": True
        }

        workflow = ParallelWorkflow.from_dict(data)
        assert len(workflow.branches) == 2
        assert workflow.wait_for_all is True

    def test_round_trip(self):
        """Test JSON round-trip for ParallelWorkflow."""
        original = ParallelWorkflow(
            branches=[
                ToolCall("task_a", {"x": 1}, assigns_to="result_a"),
                ToolCall("task_b", {"y": 2}, assigns_to="result_b"),
                ToolCall("task_c", {"z": 3}, assigns_to="result_c")
            ],
            wait_for_all=True
        )

        data = original.to_dict()
        restored = ParallelWorkflow.from_dict(data)

        assert restored.to_dict() == original.to_dict()

    def test_validation_empty_branches(self):
        """Test validation fails for empty branches."""
        workflow = ParallelWorkflow(branches=[], wait_for_all=True)
        errors = workflow.validate()
        assert any("at least one branch" in err for err in errors)

    def test_validation_single_branch(self):
        """Test validation fails for single branch (parallel needs 2+)."""
        workflow = ParallelWorkflow(
            branches=[ToolCall("single", {}, assigns_to="out")],
            wait_for_all=True
        )
        errors = workflow.validate()
        assert any("at least 2 branches" in err for err in errors)

    def test_default_wait_for_all(self):
        """Test that wait_for_all defaults to True."""
        workflow = ParallelWorkflow(
            branches=[
                ToolCall("t1", {}, assigns_to="o1"),
                ToolCall("t2", {}, assigns_to="o2")
            ]
        )
        assert workflow.wait_for_all is True


class TestOrchestratorWorkflow:
    """Tests for OrchestratorWorkflow node."""

    def test_basic_creation(self):
        """Test creating an orchestrator workflow."""
        workflow = OrchestratorWorkflow(
            sub_workflows={
                "travel_approval": ToolCall("approve_travel", {}, assigns_to="result"),
                "equipment_approval": ToolCall("approve_equipment", {}, assigns_to="result"),
                "standard_approval": ToolCall("approve_standard", {}, assigns_to="result")
            },
            routing_rules=[
                {"condition": "{{expense_type}} == 'travel'", "workflow": "travel_approval"},
                {"condition": "{{expense_type}} == 'equipment'", "workflow": "equipment_approval"}
            ],
            default_workflow="standard_approval",
            description="Dynamic routing based on expense type"
        )

        assert len(workflow.routing_rules) == 2
        assert workflow.default_workflow == "standard_approval"
        assert len(workflow.sub_workflows) == 3

    def test_to_dict(self):
        """Test OrchestratorWorkflow serialization."""
        workflow = OrchestratorWorkflow(
            sub_workflows={
                "fast_track": ToolCall("fast_process", {}, assigns_to="result"),
                "normal_processing": ToolCall("normal_process", {}, assigns_to="result")
            },
            routing_rules=[
                {"condition": "{{priority}} == 'high'", "workflow": "fast_track"}
            ],
            default_workflow="normal_processing",
            description="Route by priority"
        )

        result = workflow.to_dict()

        assert result["type"] == "orchestrator"
        assert result["description"] == "Route by priority"
        assert len(result["routing_rules"]) == 1
        assert result["default_workflow"] == "normal_processing"
        assert len(result["sub_workflows"]) == 2

    def test_from_dict(self):
        """Test OrchestratorWorkflow deserialization."""
        data = {
            "type": "orchestrator",
            "description": "Test orchestrator",
            "sub_workflows": {
                "workflow_a": {
                    "type": "tool_call",
                    "tool_name": "tool_a",
                    "parameters": {},
                    "assigns_to": "result_a"
                },
                "workflow_b": {
                    "type": "tool_call",
                    "tool_name": "tool_b",
                    "parameters": {},
                    "assigns_to": "result_b"
                },
                "workflow_default": {
                    "type": "tool_call",
                    "tool_name": "tool_default",
                    "parameters": {},
                    "assigns_to": "result_default"
                }
            },
            "routing_rules": [
                {"condition": "{{x}} > 5", "workflow": "workflow_a"},
                {"condition": "{{x}} <= 5", "workflow": "workflow_b"}
            ],
            "default_workflow": "workflow_default"
        }

        workflow = OrchestratorWorkflow.from_dict(data)
        assert workflow.description == "Test orchestrator"
        assert len(workflow.routing_rules) == 2
        assert workflow.default_workflow == "workflow_default"
        assert len(workflow.sub_workflows) == 3

    def test_round_trip(self):
        """Test JSON round-trip for OrchestratorWorkflow."""
        original = OrchestratorWorkflow(
            sub_workflows={
                "active_flow": ToolCall("process_active", {}, assigns_to="result"),
                "pending_flow": ToolCall("process_pending", {}, assigns_to="result"),
                "default_flow": ToolCall("process_default", {}, assigns_to="result")
            },
            routing_rules=[
                {"condition": "{{status}} == 'active'", "workflow": "active_flow"},
                {"condition": "{{status}} == 'pending'", "workflow": "pending_flow"}
            ],
            default_workflow="default_flow",
            description="Complex routing"
        )

        data = original.to_dict()
        restored = OrchestratorWorkflow.from_dict(data)

        assert restored.to_dict() == original.to_dict()

    def test_validation_missing_sub_workflows(self):
        """Test validation fails when sub_workflows is empty."""
        workflow = OrchestratorWorkflow(
            sub_workflows={},
            routing_rules=[{"condition": "{{x}}", "workflow": "flow"}],
            default_workflow="default"
        )
        errors = workflow.validate()
        assert any("at least one sub-workflow" in err for err in errors)

    def test_validation_missing_routing_rules(self):
        """Test validation fails when routing_rules is empty."""
        workflow = OrchestratorWorkflow(
            sub_workflows={"default": ToolCall("tool", {}, assigns_to="result")},
            routing_rules=[],
            default_workflow="default"
        )
        errors = workflow.validate()
        assert any("routing rules" in err for err in errors)

    def test_validation_invalid_workflow_reference(self):
        """Test validation fails when routing rule references non-existent workflow."""
        workflow = OrchestratorWorkflow(
            sub_workflows={
                "workflow_a": ToolCall("tool_a", {}, assigns_to="result")
            },
            routing_rules=[
                {"condition": "{{x}}", "workflow": "non_existent_workflow"}
            ],
            default_workflow="workflow_a"
        )
        errors = workflow.validate()
        assert any("unknown workflow" in err.lower() for err in errors)

    def test_validation_invalid_default_workflow(self):
        """Test validation fails when default_workflow doesn't exist in sub_workflows."""
        workflow = OrchestratorWorkflow(
            sub_workflows={
                "workflow_a": ToolCall("tool_a", {}, assigns_to="result")
            },
            routing_rules=[
                {"condition": "{{x}}", "workflow": "workflow_a"}
            ],
            default_workflow="non_existent_default"
        )
        errors = workflow.validate()
        assert any("default workflow" in err.lower() and "not found" in err.lower() for err in errors)


class TestWorkflowSpec:
    """Tests for WorkflowSpec top-level container."""

    def test_basic_creation(self):
        """Test creating a complete WorkflowSpec."""
        workflow = SequentialWorkflow(steps=[
            ToolCall("step1", {"x": 1}, assigns_to="result1"),
            ToolCall("step2", {"y": "{{result1}}"}, assigns_to="result2")
        ])

        spec = WorkflowSpec(
            name="test_workflow",
            description="A test workflow",
            inputs=[{"name": "x", "type": "int"}],
            outputs=[{"name": "result2", "type": "any"}],
            workflow=workflow
        )

        assert spec.name == "test_workflow"
        assert spec.inputs == [{"name": "x", "type": "int"}]
        assert isinstance(spec.workflow, SequentialWorkflow)

    def test_to_dict(self):
        """Test WorkflowSpec serialization."""
        spec = WorkflowSpec(
            name="expense_approval",
            description="Approve expenses",
            inputs=[
                {"name": "expense_id", "type": "string"},
                {"name": "amount", "type": "float"}
            ],
            outputs=[{"name": "approved", "type": "boolean"}],
            workflow=ToolCall("approve", {}, assigns_to="result"),
            metadata={"version": "1.0", "author": "system"}
        )

        result = spec.to_dict()

        assert result["name"] == "expense_approval"
        assert result["description"] == "Approve expenses"
        assert result["inputs"][0]["name"] == "expense_id"
        assert result["inputs"][0]["type"] == "string"
        assert result["outputs"][0]["name"] == "approved"
        assert result["outputs"][0]["type"] == "boolean"
        assert result["workflow"]["type"] == "tool_call"
        assert result["metadata"]["version"] == "1.0"

    def test_from_dict(self):
        """Test WorkflowSpec deserialization."""
        data = {
            "name": "test_spec",
            "description": "Test workflow spec",
            "inputs": [{"name": "param1", "type": "string"}],
            "outputs": [{"name": "result", "type": "any"}],
            "workflow": {
                "type": "tool_call",
                "tool_name": "test_tool",
                "parameters": {},
                "assigns_to": "result"
            },
            "metadata": {"key": "value"}
        }

        spec = WorkflowSpec.from_dict(data)
        assert spec.name == "test_spec"
        assert spec.inputs[0]["name"] == "param1"
        assert isinstance(spec.workflow, ToolCall)
        assert spec.metadata["key"] == "value"

    def test_round_trip_simple(self):
        """Test JSON round-trip for simple WorkflowSpec."""
        original = WorkflowSpec(
            name="simple",
            description="Simple workflow",
            inputs=[{"name": "x", "type": "int"}],
            outputs=[{"name": "y", "type": "int"}],
            workflow=ToolCall("add_one", {"value": "{{x}}"}, assigns_to="y")
        )

        data = original.to_dict()
        restored = WorkflowSpec.from_dict(data)

        assert restored.to_dict() == original.to_dict()

    def test_round_trip_complex(self):
        """Test JSON round-trip for complex nested WorkflowSpec."""
        # Build a complex workflow with nesting
        conditional = ConditionalWorkflow(
            condition="{{amount}} > 1000",
            if_branch=ToolCall("manager_approval", {}, assigns_to="approval"),
            else_branch=ToolCall("auto_approve", {}, assigns_to="approval")
        )

        sequential = SequentialWorkflow(steps=[
            ToolCall("fetch_data", {"id": "{{expense_id}}"}, assigns_to="data"),
            conditional,
            ToolCall("notify", {"result": "{{approval}}"}, assigns_to="notification")
        ])

        original = WorkflowSpec(
            name="complex_approval",
            description="Complex approval workflow",
            inputs=[
                {"name": "expense_id", "type": "string"},
                {"name": "amount", "type": "float"}
            ],
            outputs=[
                {"name": "approval", "type": "boolean"},
                {"name": "notification", "type": "string"}
            ],
            workflow=sequential,
            metadata={"complexity": "high"}
        )

        # Full round-trip
        data = original.to_dict()
        restored = WorkflowSpec.from_dict(data)

        assert restored.to_dict() == original.to_dict()

    def test_validation_missing_name(self):
        """Test validation fails when name is missing."""
        spec = WorkflowSpec(
            name="",
            description="Test",
            inputs=[],
            outputs=[],
            workflow=ToolCall("tool", {}, assigns_to="out")
        )
        errors = spec.validate()
        assert any("name" in err for err in errors)

    def test_validation_missing_workflow(self):
        """Test validation fails when workflow is missing."""
        spec = WorkflowSpec(
            name="test",
            description="Test",
            inputs=[],
            outputs=[],
            workflow=None
        )
        errors = spec.validate()
        assert any("workflow" in err for err in errors)

    def test_validation_nested_errors(self):
        """Test validation propagates errors from nested workflows."""
        invalid_tool = ToolCall("", {}, assigns_to="out")  # Invalid: empty tool_name
        spec = WorkflowSpec(
            name="test",
            description="Test",
            inputs=[],
            outputs=[],
            workflow=invalid_tool
        )
        errors = spec.validate()
        assert len(errors) > 0  # Should have errors from nested tool

    def test_validation_input_structure(self):
        """Test validation checks inputs have name and type."""
        spec = WorkflowSpec(
            name="test",
            description="Test",
            inputs=[{"name": "x"}],  # Missing type
            outputs=[],
            workflow=ToolCall("tool", {}, assigns_to="out")
        )
        errors = spec.validate()
        assert any("Input 1" in err and "type" in err for err in errors)

    def test_validation_output_structure(self):
        """Test validation checks outputs have name and type."""
        spec = WorkflowSpec(
            name="test",
            description="Test",
            inputs=[],
            outputs=[{"type": "string"}],  # Missing name
            workflow=ToolCall("tool", {}, assigns_to="out")
        )
        errors = spec.validate()
        assert any("Output 1" in err and "name" in err for err in errors)

    def test_str_representation(self):
        """Test WorkflowSpec string representation for debugging."""
        spec = WorkflowSpec(
            name="test_workflow",
            description="A test workflow for debugging",
            inputs=[{"name": "x", "type": "int"}, {"name": "y", "type": "int"}],
            outputs=[{"name": "result", "type": "int"}],
            workflow=ToolCall("add", {}, assigns_to="result")
        )

        str_repr = str(spec)

        # Should contain key information
        assert "test_workflow" in str_repr
        assert "A test workflow for debugging" in str_repr
        assert "Inputs:" in str_repr
        assert "Outputs:" in str_repr


class TestNestedWorkflows:
    """Tests for complex nested workflow compositions."""

    def test_sequential_of_conditionals(self):
        """Test sequential workflow containing conditional workflows."""
        cond1 = ConditionalWorkflow(
            condition="{{step}} == 1",
            if_branch=ToolCall("action1", {}, assigns_to="r1"),
            else_branch=ToolCall("skip1", {}, assigns_to="r1")
        )

        cond2 = ConditionalWorkflow(
            condition="{{step}} == 2",
            if_branch=ToolCall("action2", {}, assigns_to="r2"),
            else_branch=ToolCall("skip2", {}, assigns_to="r2")
        )

        sequential = SequentialWorkflow(steps=[cond1, cond2])

        # Round-trip test
        data = sequential.to_dict()
        restored = SequentialWorkflow.from_dict(data)
        assert restored.to_dict() == sequential.to_dict()

    def test_conditional_with_sequential_branches(self):
        """Test conditional workflow with sequential workflows as branches."""
        if_seq = SequentialWorkflow(steps=[
            ToolCall("if_step1", {}, assigns_to="r1"),
            ToolCall("if_step2", {}, assigns_to="r2")
        ])

        else_seq = SequentialWorkflow(steps=[
            ToolCall("else_step1", {}, assigns_to="r1"),
            ToolCall("else_step2", {}, assigns_to="r2")
        ])

        conditional = ConditionalWorkflow(
            condition="{{flag}}",
            if_branch=if_seq,
            else_branch=else_seq
        )

        # Round-trip test
        data = conditional.to_dict()
        restored = ConditionalWorkflow.from_dict(data)
        assert restored.to_dict() == conditional.to_dict()

    def test_parallel_with_mixed_branches(self):
        """Test parallel workflow with different node types as branches."""
        branch1 = ToolCall("simple_task", {}, assigns_to="r1")
        branch2 = SequentialWorkflow(steps=[
            ToolCall("step1", {}, assigns_to="tmp"),
            ToolCall("step2", {}, assigns_to="r2")
        ])
        branch3 = ConditionalWorkflow(
            condition="{{x}}",
            if_branch=ToolCall("yes", {}, assigns_to="r3"),
            else_branch=ToolCall("no", {}, assigns_to="r3")
        )

        parallel = ParallelWorkflow(
            branches=[branch1, branch2, branch3],
            wait_for_all=True
        )

        # Round-trip test
        data = parallel.to_dict()
        restored = ParallelWorkflow.from_dict(data)
        assert restored.to_dict() == parallel.to_dict()

    def test_deeply_nested_workflow(self):
        """Test deeply nested workflow structure (5 levels)."""
        # Level 5: ToolCall
        tool = ToolCall("deepest_tool", {}, assigns_to="result")

        # Level 4: Conditional
        cond = ConditionalWorkflow("{{x}}", tool, None)

        # Level 3: Sequential
        seq = SequentialWorkflow(steps=[cond])

        # Level 2: Parallel
        par = ParallelWorkflow(branches=[seq, seq], wait_for_all=True)

        # Level 1: WorkflowSpec
        spec = WorkflowSpec(
            name="deeply_nested",
            description="Test deep nesting",
            inputs=[{"name": "x", "type": "bool"}],
            outputs=[{"name": "result", "type": "any"}],
            workflow=par
        )

        # Full round-trip
        data = spec.to_dict()
        restored = WorkflowSpec.from_dict(data)
        assert restored.to_dict() == spec.to_dict()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_parameters(self):
        """Test ToolCall with empty parameters dict."""
        tool = ToolCall("no_params_tool", {}, assigns_to="result")
        assert tool.parameters == {}

        # Round-trip should preserve empty dict
        data = tool.to_dict()
        restored = ToolCall.from_dict(data)
        assert restored.parameters == {}

    def test_none_metadata(self):
        """Test WorkflowSpec with None metadata."""
        spec = WorkflowSpec(
            name="test",
            description="Test",
            inputs=[],
            outputs=[],
            workflow=ToolCall("tool", {}, assigns_to="out"),
            metadata=None
        )

        data = spec.to_dict()
        assert data["metadata"] is None

        restored = WorkflowSpec.from_dict(data)
        assert restored.metadata is None

    def test_empty_metadata(self):
        """Test WorkflowSpec with empty metadata dict."""
        spec = WorkflowSpec(
            name="test",
            description="Test",
            inputs=[],
            outputs=[],
            workflow=ToolCall("tool", {}, assigns_to="out"),
            metadata={}
        )

        data = spec.to_dict()
        assert data["metadata"] == {}

    def test_complex_parameters(self):
        """Test ToolCall with nested dict/list parameters."""
        tool = ToolCall(
            tool_name="complex_tool",
            parameters={
                "simple": "value",
                "nested_dict": {"a": 1, "b": 2},
                "nested_list": [1, 2, 3],
                "mixed": {"list": [{"key": "value"}]}
            },
            assigns_to="result"
        )

        # Should serialize and deserialize correctly
        data = tool.to_dict()
        restored = ToolCall.from_dict(data)
        assert restored.parameters == tool.parameters

    def test_unicode_in_strings(self):
        """Test handling of unicode characters in strings."""
        spec = WorkflowSpec(
            name="unicode_test",
            description="测试 Unicode 支持",
            inputs=[{"name": "名前", "type": "string"}],
            outputs=[{"name": "結果", "type": "string"}],
            workflow=ToolCall("处理", {"データ": "{{名前}}"}, assigns_to="結果")
        )

        # Full round-trip with unicode
        data = spec.to_dict()
        restored = WorkflowSpec.from_dict(data)
        assert restored.description == "测试 Unicode 支持"
        assert restored.inputs[0]["name"] == "名前"

    def test_special_characters_in_bindings(self):
        """Test variable bindings with underscores, numbers."""
        tool = ToolCall(
            tool_name="test",
            parameters={"var_1": "{{input_2}}", "x_y_z": "{{a_b_c_123}}"},
            assigns_to="result_final_1"
        )

        data = tool.to_dict()
        restored = ToolCall.from_dict(data)
        assert restored.assigns_to == "result_final_1"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
