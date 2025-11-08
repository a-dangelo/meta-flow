"""
Workflow AST (Abstract Syntax Tree) definitions for the meta-agent system.

This module defines the data structures that represent workflows as typed ASTs.
Each workflow is composed of nodes that can be:
- ToolCall: Single tool invocation
- SequentialWorkflow: Linear step-by-step execution
- ConditionalWorkflow: If/else branching
- ParallelWorkflow: Concurrent execution (placeholder for PoC)
- OrchestratorWorkflow: Dynamic delegation pattern

All nodes support JSON serialization/deserialization for persistence and
intermediate representation between the meta-agent and code generator.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import json


class WorkflowNodeType(Enum):
    """Enumeration of all workflow node types."""
    TOOL_CALL = "tool_call"
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    ORCHESTRATOR = "orchestrator"


@dataclass
class ToolCall:
    """
    Represents a single tool invocation with parameters.

    This is the atomic unit of workflow execution - a call to a specific
    tool with bound parameters (which may reference context variables).
    """
    type: str = field(default="tool_call", init=False)
    tool_name: str
    parameters: Dict[str, Any]
    description: Optional[str] = None
    assigns_to: Optional[str] = None  # Variable name to store result

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "type": self.type,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "description": self.description,
            "assigns_to": self.assigns_to
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolCall':
        """Create instance from dictionary."""
        return cls(
            tool_name=data["tool_name"],
            parameters=data.get("parameters", {}),
            description=data.get("description"),
            assigns_to=data.get("assigns_to")
        )

    def validate(self) -> List[str]:
        """Validate the node and return list of errors."""
        errors = []
        if not self.tool_name:
            errors.append("ToolCall must have a tool_name")
        if not isinstance(self.parameters, dict):
            errors.append("ToolCall parameters must be a dictionary")
        return errors

    def __str__(self) -> str:
        """Pretty string representation."""
        params_str = ", ".join(f"{k}={v}" for k, v in self.parameters.items())
        result = f"ToolCall({self.tool_name}({params_str})"
        if self.assigns_to:
            result = f"{self.assigns_to} = {result}"
        return result + ")"


@dataclass
class SequentialWorkflow:
    """
    Represents a linear sequence of workflow steps.

    Steps are executed one after another, with each step having access to
    the results of previous steps through the context.
    """
    type: str = field(default="sequential", init=False)
    steps: List[Union['ToolCall', 'SequentialWorkflow', 'ConditionalWorkflow',
                      'ParallelWorkflow', 'OrchestratorWorkflow']]
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "type": self.type,
            "steps": [step.to_dict() for step in self.steps],
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SequentialWorkflow':
        """Create instance from dictionary."""
        steps = []
        for step_data in data.get("steps", []):
            step = _node_from_dict(step_data)
            if step:
                steps.append(step)

        return cls(
            steps=steps,
            description=data.get("description")
        )

    def validate(self) -> List[str]:
        """Validate the node and return list of errors."""
        errors = []
        if not self.steps:
            errors.append("SequentialWorkflow must have at least one step")

        for i, step in enumerate(self.steps):
            if hasattr(step, 'validate'):
                step_errors = step.validate()
                errors.extend([f"Step {i+1}: {e}" for e in step_errors])

        return errors

    def __str__(self) -> str:
        """Pretty string representation."""
        desc = f"SequentialWorkflow ({self.description})" if self.description else "SequentialWorkflow"
        steps_str = "\n  ".join(str(step) for step in self.steps)
        return f"{desc}:\n  {steps_str}"


@dataclass
class ConditionalWorkflow:
    """
    Represents conditional branching (if/else) in a workflow.

    The condition is evaluated and either the if_branch or else_branch
    (if present) is executed based on the result.
    """
    type: str = field(default="conditional", init=False)
    condition: str  # Expression to evaluate (e.g., "amount > 10000")
    if_branch: Union['ToolCall', 'SequentialWorkflow', 'ConditionalWorkflow',
                     'ParallelWorkflow', 'OrchestratorWorkflow']
    else_branch: Optional[Union['ToolCall', 'SequentialWorkflow', 'ConditionalWorkflow',
                                'ParallelWorkflow', 'OrchestratorWorkflow']] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        result = {
            "type": self.type,
            "condition": self.condition,
            "if_branch": self.if_branch.to_dict(),
            "description": self.description
        }
        if self.else_branch:
            result["else_branch"] = self.else_branch.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConditionalWorkflow':
        """Create instance from dictionary."""
        if_branch = _node_from_dict(data.get("if_branch", {}))
        else_branch = None
        if "else_branch" in data and data["else_branch"]:
            else_branch = _node_from_dict(data["else_branch"])

        return cls(
            condition=data.get("condition", ""),
            if_branch=if_branch,
            else_branch=else_branch,
            description=data.get("description")
        )

    def validate(self) -> List[str]:
        """Validate the node and return list of errors."""
        errors = []
        if not self.condition:
            errors.append("ConditionalWorkflow must have a condition")
        if not self.if_branch:
            errors.append("ConditionalWorkflow must have an if_branch")

        if self.if_branch and hasattr(self.if_branch, 'validate'):
            branch_errors = self.if_branch.validate()
            errors.extend([f"if_branch: {e}" for e in branch_errors])

        if self.else_branch and hasattr(self.else_branch, 'validate'):
            branch_errors = self.else_branch.validate()
            errors.extend([f"else_branch: {e}" for e in branch_errors])

        return errors

    def __str__(self) -> str:
        """Pretty string representation."""
        result = f"ConditionalWorkflow:\n  if ({self.condition}):\n    {self.if_branch}"
        if self.else_branch:
            result += f"\n  else:\n    {self.else_branch}"
        return result


@dataclass
class ParallelWorkflow:
    """
    Represents parallel execution of multiple workflow branches.

    Note: For the PoC, this will be implemented as sequential execution
    with a clear TODO comment in the generated code.
    """
    type: str = field(default="parallel", init=False)
    branches: List[Union['ToolCall', 'SequentialWorkflow', 'ConditionalWorkflow',
                        'ParallelWorkflow', 'OrchestratorWorkflow']]
    description: Optional[str] = None
    wait_for_all: bool = True  # Whether to wait for all branches to complete

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "type": self.type,
            "branches": [branch.to_dict() for branch in self.branches],
            "description": self.description,
            "wait_for_all": self.wait_for_all
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParallelWorkflow':
        """Create instance from dictionary."""
        branches = []
        for branch_data in data.get("branches", []):
            branch = _node_from_dict(branch_data)
            if branch:
                branches.append(branch)

        return cls(
            branches=branches,
            description=data.get("description"),
            wait_for_all=data.get("wait_for_all", True)
        )

    def validate(self) -> List[str]:
        """Validate the node and return list of errors."""
        errors = []
        if not self.branches:
            errors.append("ParallelWorkflow must have at least one branch")
        if len(self.branches) < 2:
            errors.append("ParallelWorkflow should have at least 2 branches for parallelism")

        for i, branch in enumerate(self.branches):
            if hasattr(branch, 'validate'):
                branch_errors = branch.validate()
                errors.extend([f"Branch {i+1}: {e}" for e in branch_errors])

        return errors

    def __str__(self) -> str:
        """Pretty string representation."""
        desc = f"ParallelWorkflow ({self.description})" if self.description else "ParallelWorkflow"
        branches_str = "\n  || ".join(str(branch) for branch in self.branches)
        return f"{desc}:\n  || {branches_str}"


@dataclass
class OrchestratorWorkflow:
    """
    Represents an orchestrator that delegates to other workflows dynamically.

    The orchestrator evaluates conditions and routes to appropriate sub-workflows
    based on the context and defined routing rules.
    """
    type: str = field(default="orchestrator", init=False)
    sub_workflows: Dict[str, Union['ToolCall', 'SequentialWorkflow', 'ConditionalWorkflow',
                                   'ParallelWorkflow', 'OrchestratorWorkflow']]
    routing_rules: List[Dict[str, str]]  # List of {condition: str, workflow: str}
    default_workflow: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "type": self.type,
            "sub_workflows": {name: wf.to_dict() for name, wf in self.sub_workflows.items()},
            "routing_rules": self.routing_rules,
            "default_workflow": self.default_workflow,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OrchestratorWorkflow':
        """Create instance from dictionary."""
        sub_workflows = {}
        for name, wf_data in data.get("sub_workflows", {}).items():
            workflow = _node_from_dict(wf_data)
            if workflow:
                sub_workflows[name] = workflow

        return cls(
            sub_workflows=sub_workflows,
            routing_rules=data.get("routing_rules", []),
            default_workflow=data.get("default_workflow"),
            description=data.get("description")
        )

    def validate(self) -> List[str]:
        """Validate the node and return list of errors."""
        errors = []
        if not self.sub_workflows:
            errors.append("OrchestratorWorkflow must have at least one sub-workflow")
        if not self.routing_rules:
            errors.append("OrchestratorWorkflow must have routing rules")

        # Validate routing rules reference existing workflows
        workflow_names = set(self.sub_workflows.keys())
        for rule in self.routing_rules:
            if "workflow" in rule and rule["workflow"] not in workflow_names:
                errors.append(f"Routing rule references unknown workflow: {rule['workflow']}")

        if self.default_workflow and self.default_workflow not in workflow_names:
            errors.append(f"Default workflow '{self.default_workflow}' not found in sub_workflows")

        # Validate sub-workflows
        for name, workflow in self.sub_workflows.items():
            if hasattr(workflow, 'validate'):
                wf_errors = workflow.validate()
                errors.extend([f"Sub-workflow '{name}': {e}" for e in wf_errors])

        return errors

    def __str__(self) -> str:
        """Pretty string representation."""
        desc = f"OrchestratorWorkflow ({self.description})" if self.description else "OrchestratorWorkflow"
        if self.routing_rules:
            rules_str = "\n  ".join(
                f"if {r.get('condition', 'N/A')}: -> {r.get('workflow', 'N/A')}"
                for r in self.routing_rules
            )
        else:
            rules_str = "No rules defined"
        return f"{desc}:\n  Rules:\n  {rules_str}\n  Default: {self.default_workflow}"


@dataclass
class WorkflowSpec:
    """
    Top-level container for a complete workflow specification.

    This is the root of the AST and contains all metadata about the workflow
    along with the actual workflow definition.
    """
    name: str
    description: str
    version: str = "1.0.0"
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    workflow: Optional[Union[ToolCall, SequentialWorkflow, ConditionalWorkflow,
                            ParallelWorkflow, OrchestratorWorkflow]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        result = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metadata": self.metadata
        }
        if self.workflow:
            result["workflow"] = self.workflow.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowSpec':
        """Create instance from dictionary."""
        workflow = None
        if "workflow" in data and data["workflow"]:
            workflow = _node_from_dict(data["workflow"])

        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            workflow=workflow,
            metadata=data.get("metadata", {})
        )

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> 'WorkflowSpec':
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def validate(self) -> List[str]:
        """Validate the entire workflow specification."""
        errors = []

        if not self.name:
            errors.append("WorkflowSpec must have a name")
        if not self.description:
            errors.append("WorkflowSpec must have a description")
        if not self.workflow:
            errors.append("WorkflowSpec must have a workflow definition")

        # Validate inputs/outputs structure
        for i, input_spec in enumerate(self.inputs):
            if "name" not in input_spec:
                errors.append(f"Input {i+1} must have a name")
            if "type" not in input_spec:
                errors.append(f"Input {i+1} must have a type")

        for i, output_spec in enumerate(self.outputs):
            if "name" not in output_spec:
                errors.append(f"Output {i+1} must have a name")
            if "type" not in output_spec:
                errors.append(f"Output {i+1} must have a type")

        # Validate the workflow itself
        if self.workflow and hasattr(self.workflow, 'validate'):
            workflow_errors = self.workflow.validate()
            errors.extend([f"Workflow: {e}" for e in workflow_errors])

        return errors

    def __str__(self) -> str:
        """Pretty string representation."""
        inputs_str = ", ".join(f"{i['name']}: {i['type']}" for i in self.inputs)
        outputs_str = ", ".join(f"{o['name']}: {o['type']}" for o in self.outputs)

        result = f"WorkflowSpec: {self.name}\n"
        result += f"  Description: {self.description}\n"
        result += f"  Version: {self.version}\n"
        result += f"  Inputs: ({inputs_str})\n"
        result += f"  Outputs: ({outputs_str})\n"
        if self.workflow:
            result += f"  Workflow:\n    {str(self.workflow).replace(chr(10), chr(10) + '    ')}"

        return result


def _node_from_dict(data: Dict[str, Any]) -> Optional[Union[ToolCall, SequentialWorkflow,
                                                             ConditionalWorkflow, ParallelWorkflow,
                                                             OrchestratorWorkflow]]:
    """
    Factory function to create the appropriate node type from a dictionary.

    Uses the 'type' field to determine which class to instantiate.
    """
    if not data or "type" not in data:
        return None

    node_type = data["type"]

    if node_type == "tool_call":
        return ToolCall.from_dict(data)
    elif node_type == "sequential":
        return SequentialWorkflow.from_dict(data)
    elif node_type == "conditional":
        return ConditionalWorkflow.from_dict(data)
    elif node_type == "parallel":
        return ParallelWorkflow.from_dict(data)
    elif node_type == "orchestrator":
        return OrchestratorWorkflow.from_dict(data)
    else:
        raise ValueError(f"Unknown node type: {node_type}")


if __name__ == "__main__":
    # Example usage and demonstration
    print("Workflow AST Module - Example Usage\n")

    # Create a simple sequential workflow
    workflow = SequentialWorkflow(
        steps=[
            ToolCall(
                tool_name="fetch_expense_data",
                parameters={"expense_id": "${inputs.expense_id}"},
                assigns_to="expense_data"
            ),
            ConditionalWorkflow(
                condition="expense_data.amount > 10000",
                if_branch=ToolCall(
                    tool_name="require_manager_approval",
                    parameters={"expense": "${expense_data}"},
                    assigns_to="approval_result"
                ),
                else_branch=ToolCall(
                    tool_name="auto_approve",
                    parameters={"expense": "${expense_data}"},
                    assigns_to="approval_result"
                )
            ),
            ToolCall(
                tool_name="notify_submitter",
                parameters={
                    "expense_id": "${inputs.expense_id}",
                    "result": "${approval_result}"
                }
            )
        ],
        description="Example expense approval workflow"
    )

    # Create a workflow specification
    spec = WorkflowSpec(
        name="expense_approval",
        description="Automated expense approval workflow with manager escalation",
        inputs=[
            {"name": "expense_id", "type": "string", "description": "ID of the expense to process"}
        ],
        outputs=[
            {"name": "approval_result", "type": "object", "description": "Approval decision and details"}
        ],
        workflow=workflow,
        metadata={"author": "meta-agent", "category": "finance"}
    )

    # Demonstrate serialization
    print("Original Workflow:")
    print(spec)
    print("\n" + "="*50 + "\n")

    # Convert to JSON
    json_str = spec.to_json()
    print("JSON Representation:")
    print(json_str)
    print("\n" + "="*50 + "\n")

    # Deserialize from JSON
    spec_copy = WorkflowSpec.from_json(json_str)
    print("Deserialized Workflow:")
    print(spec_copy)
    print("\n" + "="*50 + "\n")

    # Validate the workflow
    errors = spec.validate()
    if errors:
        print("Validation Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✓ Workflow validation passed!")