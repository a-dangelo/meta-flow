"""
Enhanced Pydantic models with comprehensive validation for meta-agent v2.

This module replaces the basic dataclasses from v1 with Pydantic v2 models
that include field validators, model validators, and business logic checks.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Any, Optional, Literal, Union
import re
import json


def _validate_safe_condition(v: str, context: str = "condition") -> str:
    """
    Shared validation logic for conditions.

    Validates that a condition is safe to evaluate by:
    1. Checking it's not empty
    2. Rejecting dangerous patterns FIRST (before operator check)
    3. Ensuring allowed operators are present
    4. Validating variable reference syntax

    Args:
        v: The condition string to validate
        context: Context name for error messages (e.g., "condition", "routing condition")

    Returns:
        The validated condition string

    Raises:
        ValueError: If validation fails
    """
    if not v or not v.strip():
        raise ValueError(f"{context.capitalize()} cannot be empty")

    # Check for dangerous patterns FIRST (before operator check to prevent bypass)
    dangerous_patterns = [
        'import', 'from', 'exec', 'eval', 'lambda', 'compile',
        'open', 'file', 'input', 'raw_input', 'globals', 'locals',
        'vars', 'dir', 'getattr', 'setattr', 'delattr', 'hasattr',
        'os.', 'sys.', 'subprocess', '__builtins__'
    ]
    v_lower = v.lower()
    for pattern in dangerous_patterns:
        if pattern in v_lower:
            raise ValueError(
                f"Unsafe pattern '{pattern}' detected in {context}. "
                f"Only simple comparisons are allowed."
            )

    # Check for dunder patterns using regex (more specific than substring)
    if re.search(r'\b__\w+__\b', v):
        raise ValueError(
            f"Dunder methods/attributes not allowed in {context}. "
            f"Only simple comparisons are allowed."
        )

    # Check for allowed operators
    allowed_operators = ['>', '<', '==', '!=', '>=', '<=', 'and', 'or', 'not', 'in', 'is']
    has_operator = any(op in v for op in allowed_operators)
    if not has_operator:
        raise ValueError(
            f"{context.capitalize()} must contain a comparison operator: {', '.join(allowed_operators)}"
        )

    # Check for variable references - should use {{var}} or {{obj.property}}
    if '$' in v or '{' in v:
        # Support both simple variables and nested properties
        if not re.search(r'\{\{[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*\}\}', v):
            raise ValueError(
                f"Variable references in {context} must use {{{{variable_name}}}} or {{{{object.property}}}} syntax"
            )

    return v


class WorkflowInput(BaseModel):
    """Validated input parameter for workflow."""

    name: str = Field(..., description="Parameter name (snake_case)")
    type: str = Field(..., description="Parameter type (string, int, dict, etc.)")
    description: Optional[str] = Field(default=None, description="Human-readable description")
    is_credential: bool = Field(default=False, description="Whether this is a credential parameter")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure parameter name is valid Python identifier."""
        if not re.match(r'^[a-z_][a-z0-9_]*$', v):
            raise ValueError(
                f"Invalid parameter name '{v}'. Must be snake_case starting with letter or underscore."
            )
        if len(v) > 64:
            raise ValueError(f"Parameter name too long: {len(v)} chars (max 64)")
        return v

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate parameter type."""
        valid_types = {
            'string', 'str', 'int', 'float', 'bool', 'dict', 'list',
            'object', 'array', 'number', 'boolean', 'any'
        }
        if v.lower() not in valid_types:
            raise ValueError(
                f"Invalid type '{v}'. Must be one of: {', '.join(sorted(valid_types))}"
            )
        return v

    @model_validator(mode='after')
    def detect_credential(self) -> 'WorkflowInput':
        """Auto-detect credential parameters based on name patterns."""
        # Only auto-detect if not explicitly set to True already
        if self.is_credential:
            return self

        credential_patterns = [
            'api_key', 'apikey', 'token', 'password', 'secret',
            'credential', 'auth', 'authorization', 'bearer',
            'database_url', 'db_url', 'connection_string', 'dsn',
            'private_key', 'secret_key', 'access_key'
        ]
        name_lower = self.name.lower()
        if any(pattern in name_lower for pattern in credential_patterns):
            self.is_credential = True
        return self

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Serialize to dict, excluding is_credential if False."""
        data = super().model_dump(**kwargs)
        if not self.is_credential:
            data.pop('is_credential', None)
        return data


class WorkflowOutput(BaseModel):
    """Validated output parameter for workflow."""

    name: str = Field(..., description="Output variable name (snake_case)")
    type: str = Field(..., description="Output type")
    description: Optional[str] = Field(default=None, description="Human-readable description")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure output name is valid Python identifier."""
        if not re.match(r'^[a-z_][a-z0-9_]*$', v):
            raise ValueError(
                f"Invalid output name '{v}'. Must be snake_case starting with letter or underscore."
            )
        if len(v) > 64:
            raise ValueError(f"Output name too long: {len(v)} chars (max 64)")
        return v

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate output type."""
        valid_types = {
            'string', 'str', 'int', 'float', 'bool', 'dict', 'list',
            'object', 'array', 'number', 'boolean', 'any'
        }
        if v.lower() not in valid_types:
            raise ValueError(
                f"Invalid type '{v}'. Must be one of: {', '.join(sorted(valid_types))}"
            )
        return v


class ToolCall(BaseModel):
    """Single tool invocation with validated parameters."""

    type: Literal["tool_call"] = Field(default="tool_call", description="Node type")
    tool_name: str = Field(..., description="Tool function name (snake_case)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    assigns_to: Optional[str] = Field(default=None, description="Variable to assign result to")
    description: Optional[str] = Field(default=None, description="Human-readable description")

    @field_validator('tool_name')
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Ensure tool name is valid Python function name."""
        if not v or not v.strip():
            raise ValueError("tool_name cannot be empty")
        if not re.match(r'^[a-z_][a-z0-9_]*$', v):
            raise ValueError(
                f"Invalid tool name '{v}'. Must be snake_case starting with letter or underscore."
            )
        if len(v) > 64:
            raise ValueError(f"Tool name too long: {len(v)} chars (max 64)")
        return v

    @field_validator('assigns_to')
    @classmethod
    def validate_assigns_to(cls, v: Optional[str]) -> Optional[str]:
        """Validate variable assignment target."""
        if v is None:
            return v
        if not re.match(r'^[a-z_][a-z0-9_]*$', v):
            raise ValueError(
                f"Invalid variable name '{v}'. Must be snake_case starting with letter or underscore."
            )
        if len(v) > 64:
            raise ValueError(f"Variable name too long: {len(v)} chars (max 64)")
        return v

    @field_validator('parameters')
    @classmethod
    def validate_parameters(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameter structure and variable references."""
        for key, value in v.items():
            # Validate parameter key is valid identifier
            if not re.match(r'^[a-z_][a-z0-9_]*$', key):
                raise ValueError(
                    f"Invalid parameter key '{key}'. Must be snake_case."
                )

            # Validate variable references ({{var_name}} or {{obj.property}})
            if isinstance(value, str) and '{{' in value:
                # Extract all variable references - support nested properties
                # Pattern: variable name optionally followed by .property (can repeat)
                refs = re.findall(r'\{\{([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*)\}\}', value)
                if not refs:
                    raise ValueError(
                        f"Invalid variable reference format in '{value}'. "
                        f"Use {{{{variable_name}}}} or {{{{object.property}}}} syntax."
                    )

        return v

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Serialize to dict, compatible with v1 format."""
        data = super().model_dump(**kwargs)
        # Remove None values for cleaner output
        return {k: v for k, v in data.items() if v is not None}


class SequentialWorkflow(BaseModel):
    """Linear sequence of workflow steps with validation."""

    type: Literal["sequential"] = Field(default="sequential", description="Workflow type")
    steps: List[Union['ToolCall', 'ConditionalWorkflow', 'ParallelWorkflow']] = Field(
        ..., description="Ordered list of workflow steps"
    )
    description: Optional[str] = Field(default=None, description="Human-readable description")

    @field_validator('steps')
    @classmethod
    def validate_steps(cls, v: List[Any]) -> List[Any]:
        """Validate steps list."""
        if not v:
            raise ValueError("Sequential workflow must have at least one step")
        if len(v) > 100:
            raise ValueError(
                f"Workflow too complex: {len(v)} steps (max 100). "
                f"Consider breaking into sub-workflows."
            )
        return v

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Serialize to dict."""
        data = super().model_dump(**kwargs)
        return {k: v for k, v in data.items() if v is not None}


class ConditionalWorkflow(BaseModel):
    """If-else branching logic with safe condition validation."""

    type: Literal["conditional"] = Field(default="conditional", description="Workflow type")
    condition: str = Field(..., description="Boolean condition to evaluate")
    if_branch: Union['ToolCall', 'SequentialWorkflow', 'ParallelWorkflow', 'ConditionalWorkflow'] = Field(
        ..., description="Workflow to execute if condition is true"
    )
    else_branch: Optional[Union['ToolCall', 'SequentialWorkflow', 'ParallelWorkflow', 'ConditionalWorkflow']] = Field(
        default=None, description="Workflow to execute if condition is false"
    )
    description: Optional[str] = Field(default=None, description="Human-readable description")

    @field_validator('condition')
    @classmethod
    def validate_condition(cls, v: str) -> str:
        """Ensure condition is safe to evaluate."""
        return _validate_safe_condition(v, "condition")

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Serialize to dict."""
        data = super().model_dump(**kwargs)
        return {k: v for k, v in data.items() if v is not None}


class ParallelWorkflow(BaseModel):
    """Concurrent execution of multiple branches (PoC: sequential implementation)."""

    type: Literal["parallel"] = Field(default="parallel", description="Workflow type")
    branches: List[Union['ToolCall', 'SequentialWorkflow', 'ConditionalWorkflow']] = Field(
        ..., description="List of workflows to execute in parallel"
    )
    wait_for_all: bool = Field(default=True, description="Wait for all branches to complete")
    description: Optional[str] = Field(default=None, description="Human-readable description")

    @field_validator('branches')
    @classmethod
    def validate_branches(cls, v: List[Any]) -> List[Any]:
        """Validate branches list."""
        if not v:
            raise ValueError("Parallel workflow must have at least one branch")
        if len(v) < 2:
            raise ValueError(
                "Parallel workflow needs at least 2 branches. Use SequentialWorkflow for single branch."
            )
        if len(v) > 10:
            raise ValueError(
                f"Too many parallel branches: {len(v)} (max 10). Consider grouping."
            )
        return v

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Serialize to dict."""
        data = super().model_dump(**kwargs)
        return {k: v for k, v in data.items() if v is not None}


class RoutingRule(BaseModel):
    """Routing rule for orchestrator workflow."""

    condition: str = Field(..., description="Condition to evaluate for routing")
    workflow_name: str = Field(..., description="Name of sub-workflow to route to")

    @field_validator('condition')
    @classmethod
    def validate_condition(cls, v: str) -> str:
        """Validate routing condition (same as ConditionalWorkflow)."""
        return _validate_safe_condition(v, "routing condition")

    @field_validator('workflow_name')
    @classmethod
    def validate_workflow_name(cls, v: str) -> str:
        """Validate workflow name reference."""
        if not re.match(r'^[a-z_][a-z0-9_]*$', v):
            raise ValueError(
                f"Invalid workflow name '{v}'. Must be snake_case."
            )
        return v


class OrchestratorWorkflow(BaseModel):
    """Dynamic workflow delegation with routing rules."""

    type: Literal["orchestrator"] = Field(default="orchestrator", description="Workflow type")
    sub_workflows: Dict[str, Union['ToolCall', 'SequentialWorkflow', 'ConditionalWorkflow', 'ParallelWorkflow']] = Field(
        ..., description="Named sub-workflows"
    )
    routing_rules: List[RoutingRule] = Field(..., description="Ordered routing rules")
    default_workflow: Optional[str] = Field(default=None, description="Fallback workflow name")
    description: Optional[str] = Field(default=None, description="Human-readable description")

    @field_validator('sub_workflows')
    @classmethod
    def validate_sub_workflows(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate sub-workflows dictionary."""
        if not v:
            raise ValueError("Orchestrator must have at least one sub-workflow")
        for name in v.keys():
            if not re.match(r'^[a-z_][a-z0-9_]*$', name):
                raise ValueError(
                    f"Invalid sub-workflow name '{name}'. Must be snake_case."
                )
        return v

    @field_validator('routing_rules')
    @classmethod
    def validate_routing_rules(cls, v: List[RoutingRule]) -> List[RoutingRule]:
        """Validate routing rules."""
        if not v:
            raise ValueError("Orchestrator must have at least one routing rule")
        return v

    @model_validator(mode='after')
    def validate_routing_references(self) -> 'OrchestratorWorkflow':
        """Ensure routing rules reference existing sub-workflows."""
        workflow_names = set(self.sub_workflows.keys())

        # Check routing rules
        for rule in self.routing_rules:
            if rule.workflow_name not in workflow_names:
                raise ValueError(
                    f"Routing rule references undefined workflow '{rule.workflow_name}'. "
                    f"Available: {', '.join(sorted(workflow_names))}"
                )

        # Check default workflow
        if self.default_workflow and self.default_workflow not in workflow_names:
            raise ValueError(
                f"Default workflow '{self.default_workflow}' not found in sub_workflows. "
                f"Available: {', '.join(sorted(workflow_names))}"
            )

        return self

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Serialize to dict."""
        data = super().model_dump(**kwargs)
        return {k: v for k, v in data.items() if v is not None}


class WorkflowSpec(BaseModel):
    """Top-level workflow specification with comprehensive validation."""

    name: str = Field(..., description="Workflow name (snake_case)")
    description: str = Field(..., description="Human-readable description")
    version: str = Field(default="1.0.0", description="Semantic version")
    inputs: List[WorkflowInput] = Field(default_factory=list, description="Input parameters")
    outputs: List[WorkflowOutput] = Field(default_factory=list, description="Output parameters")
    workflow: Union[ToolCall, SequentialWorkflow, ConditionalWorkflow, ParallelWorkflow, OrchestratorWorkflow] = Field(
        ..., description="Root workflow node"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure workflow name is valid Python identifier."""
        if not re.match(r'^[a-z_][a-z0-9_]*$', v):
            raise ValueError(
                f"Invalid workflow name '{v}'. Must be snake_case starting with letter or underscore."
            )
        if len(v) > 64:
            raise ValueError(f"Workflow name too long: {len(v)} chars (max 64)")
        return v

    @field_validator('version')
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semantic version format."""
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError(
                f"Invalid version '{v}'. Must be semantic version (e.g., '1.0.0')"
            )
        return v

    @model_validator(mode='after')
    def validate_variable_references(self) -> 'WorkflowSpec':
        """Ensure all variable references in workflow are valid."""
        # Collect all input variable names
        available_vars = {inp.name for inp in self.inputs}

        # Recursively validate workflow nodes
        self._validate_node_references(self.workflow, available_vars.copy())

        return self

    def _validate_node_references(self, node: Any, available_vars: set) -> None:
        """Recursively validate variable references in workflow nodes."""
        if isinstance(node, ToolCall):
            # Check parameters for variable references
            for param_value in node.parameters.values():
                if isinstance(param_value, str):
                    refs = re.findall(
                        r'\{\{([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*)\}\}',
                        param_value
                    )
                    for ref in refs:
                        root_ref = ref.split('.')[0]
                        if root_ref not in available_vars:
                            raise ValueError(
                                f"Tool '{node.tool_name}' references undefined variable '{{{{{ref}}}}}'. "
                                f"Available: {', '.join(sorted(available_vars))}"
                            )

            # Add assigns_to to available vars for subsequent nodes
            if node.assigns_to:
                available_vars.add(node.assigns_to)

        elif isinstance(node, SequentialWorkflow):
            for step in node.steps:
                self._validate_node_references(step, available_vars)

        elif isinstance(node, ConditionalWorkflow):
            # Validate condition variables
            refs = re.findall(
                r'\{\{([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*)\}\}',
                node.condition
            )
            for ref in refs:
                root_ref = ref.split('.')[0]
                if root_ref not in available_vars:
                    raise ValueError(
                        f"Condition references undefined variable '{ref}'. "
                        f"Available: {', '.join(sorted(available_vars))}"
                    )

            # Validate branches and collect variables assigned in each
            if_vars = available_vars.copy()
            self._validate_node_references(node.if_branch, if_vars)

            if node.else_branch:
                else_vars = available_vars.copy()
                self._validate_node_references(node.else_branch, else_vars)

                # Variables assigned in BOTH branches are available after the conditional
                # (intersection of new variables from each branch)
                if_new_vars = if_vars - available_vars
                else_new_vars = else_vars - available_vars
                guaranteed_vars = if_new_vars & else_new_vars
                available_vars.update(guaranteed_vars)
            else:
                # If there's no else branch, no variables are guaranteed to be assigned
                pass

        elif isinstance(node, ParallelWorkflow):
            # All branches see same input variables, validate each branch
            branch_vars_list = []

            for branch in node.branches:
                # Track variables assigned in this branch
                branch_vars = available_vars.copy()
                self._validate_node_references(branch, branch_vars)

                # Collect new variables from this branch
                new_vars = branch_vars - available_vars
                branch_vars_list.append(new_vars)

            # Since ALL parallel branches execute (wait_for_all semantics),
            # ALL variables assigned in ANY branch are available after parallel node
            all_parallel_vars = set()
            for branch_vars in branch_vars_list:
                all_parallel_vars.update(branch_vars)

            available_vars.update(all_parallel_vars)

        elif isinstance(node, OrchestratorWorkflow):
            # Validate each sub-workflow
            for sub_workflow in node.sub_workflows.values():
                self._validate_node_references(sub_workflow, available_vars.copy())

    def to_json(self, **kwargs) -> str:
        """Serialize to JSON string with validation."""
        return self.model_dump_json(exclude_none=True, **kwargs)

    @classmethod
    def from_json(cls, json_str: str) -> 'WorkflowSpec':
        """Deserialize from JSON string with validation."""
        data = json.loads(json_str)
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (compatible with v1 format)."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowSpec':
        """Deserialize from dictionary with validation."""
        return cls(**data)


# Update forward references for recursive types
SequentialWorkflow.model_rebuild()
ConditionalWorkflow.model_rebuild()
ParallelWorkflow.model_rebuild()
OrchestratorWorkflow.model_rebuild()
WorkflowSpec.model_rebuild()
