"""
Code generator that transforms WorkflowSpec AST into executable Python agents.

This module implements the Phase 2 component that takes validated JSON workflow
specifications and generates self-contained Python agent classes with:
- Type hints throughout
- Environment variable handling for credentials
- Tool stub implementations
- Error handling with context preservation
- Setup instructions and example usage
"""

from typing import Dict, Any, Set, List, Optional
from datetime import datetime
import re
import json

# Import Phase 1 models
from src.agents.models import (
    WorkflowSpec,
    WorkflowInput,
    WorkflowOutput,
    ToolCall,
    SequentialWorkflow,
    ConditionalWorkflow,
    ParallelWorkflow,
    OrchestratorWorkflow,
)

# Import tool registry
from src.tools import TOOL_REGISTRY


class AgentGenerator:
    """
    Transforms WorkflowSpec AST into executable Python code.

    This class implements a programmatic code generation approach (not template-based)
    that recursively traverses the workflow AST and generates idiomatic Python code.

    Security: All credential parameters are detected and handled via environment
    variables. Generated code NEVER contains hardcoded credentials.

    Example:
        >>> spec = WorkflowSpec.model_validate(json_data)
        >>> generator = AgentGenerator(spec)
        >>> python_code = generator.generate()
        >>> with open('agent.py', 'w') as f:
        ...     f.write(python_code)
    """

    def __init__(self, workflow_spec: WorkflowSpec):
        """
        Initialize generator with validated workflow specification.

        Args:
            workflow_spec: Validated Pydantic WorkflowSpec model
        """
        self.spec = workflow_spec
        self.credential_params = self._detect_credentials()
        self.all_tools = self._collect_all_tools()
        # Categorize tools: library vs stub
        self.library_tools = {tool for tool in self.all_tools if tool in TOOL_REGISTRY}
        self.stub_tools = self.all_tools - self.library_tools

    def generate(self) -> str:
        """
        Generate complete Python agent code.

        Returns:
            String containing complete, executable Python code
        """
        parts = [
            self._generate_module_docstring(),
            self._generate_imports(),
            "",
            self._generate_agent_class(),
            "",
            self._generate_main_block()
        ]
        return "\n\n".join(parts)

    def _detect_credentials(self) -> Set[str]:
        """
        Detect credential parameters from workflow inputs.

        Uses the is_credential field that was auto-detected in Phase 1.

        Returns:
            Set of parameter names that are credentials
        """
        credentials = set()
        for inp in self.spec.inputs:
            # Handle both dict and object formats
            if isinstance(inp, dict):
                if inp.get('is_credential', False):
                    credentials.add(inp['name'])
            else:
                if inp.is_credential:
                    credentials.add(inp.name)
        return credentials

    def _is_credential_parameter(self, param_name: str) -> bool:
        """
        Check if a parameter name suggests it's a credential.

        This matches the pattern from REQUIREMENTS.md for detection in tool parameters.

        Args:
            param_name: Parameter name to check

        Returns:
            True if parameter appears to be a credential
        """
        credential_patterns = [
            'api_key', 'apikey', 'token', 'password', 'secret',
            'credential', 'auth', 'authorization', 'bearer',
            'database_url', 'db_url', 'connection_string', 'dsn',
            'private_key', 'secret_key', 'access_key', 'webhook'
        ]
        param_lower = param_name.lower()
        return any(pattern in param_lower for pattern in credential_patterns)

    def _collect_all_tools(self) -> Set[str]:
        """
        Collect all unique tool names from the workflow.

        Recursively traverses the workflow AST to find all ToolCall nodes.

        Returns:
            Set of unique tool names
        """
        tools = set()
        self._collect_tools_recursive(self.spec.workflow, tools)
        return tools

    def _collect_tools_recursive(self, node, tools: Set[str]):
        """Recursively collect tool names from workflow nodes."""
        if isinstance(node, ToolCall):
            tools.add(node.tool_name)
        elif isinstance(node, SequentialWorkflow):
            for step in node.steps:
                self._collect_tools_recursive(step, tools)
        elif isinstance(node, ConditionalWorkflow):
            self._collect_tools_recursive(node.if_branch, tools)
            if node.else_branch:
                self._collect_tools_recursive(node.else_branch, tools)
        elif isinstance(node, ParallelWorkflow):
            for branch in node.branches:
                self._collect_tools_recursive(branch, tools)
        elif isinstance(node, OrchestratorWorkflow):
            for sub_workflow in node.sub_workflows.values():
                self._collect_tools_recursive(sub_workflow, tools)

    def _generate_module_docstring(self) -> str:
        """
        Generate module-level docstring with setup instructions.

        Includes:
        - Workflow name and description
        - List of required environment variables
        - Setup examples for each credential
        - Generation timestamp

        Returns:
            Formatted module docstring
        """
        lines = [
            '"""',
            f"Auto-generated agent: {self.spec.name}",
            "",
            f"Description: {self.spec.description}",
            ""
        ]

        # Add setup instructions if there are credentials
        if self.credential_params:
            lines.extend([
                "SETUP INSTRUCTIONS:",
                "=" * 50,
                "This agent requires the following environment variables:",
                ""
            ])

            for inp in self.spec.inputs:
                # Handle both dict and object formats
                is_cred = inp.get('is_credential', False) if isinstance(inp, dict) else inp.is_credential
                if is_cred:
                    name = inp['name'] if isinstance(inp, dict) else inp.name
                    desc = inp.get('description') if isinstance(inp, dict) else inp.description
                    env_var = name.upper()
                    desc_text = desc or "Authentication credential"
                    lines.extend([
                        f"- {env_var}: {desc_text}",
                        f"  Setup: export {env_var}=<your-value-here>",
                        ""
                    ])

        lines.extend([
            f"Generated: {datetime.now().isoformat()}",
            f"Version: {self.spec.version}",
            '"""'
        ])

        return "\n".join(lines)

    def _generate_imports(self) -> str:
        """
        Generate import statements.

        Includes imports for tool library functions if any tools have implementations.

        Returns:
            Import statements for generated code
        """
        imports = [
            "import os",
            "import asyncio",
            "from typing import Any, Dict, Optional"
        ]

        # Add tool library imports if any tools have implementations
        if self.library_tools:
            imports.append("")
            imports.append("# Tool library imports")

            # Group imports by module
            tool_modules = {}
            for tool in sorted(self.library_tools):
                module_path = TOOL_REGISTRY[tool]
                if module_path not in tool_modules:
                    tool_modules[module_path] = []
                tool_modules[module_path].append(tool)

            # Generate import statements
            for module_path, tools in sorted(tool_modules.items()):
                tools_str = ", ".join(sorted(tools))
                imports.append(f"from {module_path} import {tools_str}")

        return "\n".join(imports)

    def _generate_agent_class(self) -> str:
        """
        Generate the main agent class.

        Returns:
            Complete agent class code
        """
        class_name = self._to_class_name(self.spec.name)

        parts = [
            f"class {class_name}:",
            f'    """Executable agent for {self.spec.name} workflow."""',
            "",
            self._indent(self._generate_init_method(), 1),
            "",
            self._indent(self._generate_execute_method(), 1),
            "",
            self._indent(self._generate_tool_methods(), 1)
        ]

        return "\n".join(parts)

    def _to_class_name(self, snake_case: str) -> str:
        """Convert snake_case to PascalCase."""
        return ''.join(word.capitalize() for word in snake_case.split('_')) + 'Agent'

    def _generate_init_method(self) -> str:
        """
        Generate __init__ method.

        Returns:
            __init__ method code
        """
        lines = [
            "def __init__(self):",
            '    """Initialize agent with empty context."""',
            "    self.context: Dict[str, Any] = {}"
        ]
        return "\n".join(lines)

    def _generate_execute_method(self) -> str:
        """
        Generate execute() method with workflow logic.

        Returns:
            Complete execute() method code
        """
        lines = [
            "def execute(self, **inputs) -> Dict[str, Any]:",
            '    """',
            f'    Execute {self.spec.name} workflow.',
            '    ',
            '    Args:',
        ]

        # Document input parameters
        for inp in self.spec.inputs:
            name = inp['name'] if isinstance(inp, dict) else inp.name
            desc = inp.get('description') if isinstance(inp, dict) else inp.description
            typ = inp.get('type') if isinstance(inp, dict) else inp.type
            lines.append(f'        {name}: {desc or typ}')

        lines.extend([
            '    ',
            '    Returns:',
            '        Dictionary containing workflow outputs',
            '    ',
            '    Raises:',
            '        ValueError: If required inputs are missing',
            '        RuntimeError: If workflow execution fails',
            '    """',
            '    try:',
            '        # Validate and initialize inputs',
        ])

        # Add input validation
        for inp in self.spec.inputs:
            name = inp['name'] if isinstance(inp, dict) else inp.name
            lines.append(f'        if "{name}" not in inputs:')
            lines.append(f'            raise ValueError("Missing required input: {name}")')

        lines.extend([
            '        ',
            '        # Initialize context with inputs',
            '        for key, value in inputs.items():',
            '            self.context[key] = value',
            '        ',
            '        # Execute workflow',
        ])

        # Generate workflow execution code
        workflow_code = self._generate_workflow_node(self.spec.workflow, indent=2)
        lines.append(workflow_code)

        lines.extend([
            '        ',
            '        # Return outputs',
        ])

        if self.spec.outputs:
            def get_output_name(out):
                return out['name'] if isinstance(out, dict) else out.name

            output_dict = ', '.join(
                f'"{get_output_name(out)}": self.context.get("{get_output_name(out)}")'
                for out in self.spec.outputs
            )
            lines.append(f'        return {{{output_dict}}}')
        else:
            lines.append('        return self.context')

        lines.extend([
            '        ',
            '    except Exception as e:',
            '        # Preserve context for debugging',
            '        error_context = {',
            '            "error": str(e),',
            '            "context_at_failure": self.context.copy(),',
            '            "inputs": inputs',
            '        }',
            '        raise RuntimeError(',
            '            f"Workflow execution failed: {e}\\n"',
            '            f"Context: {error_context}"',
            '        ) from e',
        ])

        return "\n".join(lines)

    def _generate_workflow_node(self, node, indent: int = 0) -> str:
        """
        Recursively generate code for workflow nodes.

        Args:
            node: Workflow node (ToolCall, Sequential, Conditional, etc.)
            indent: Base indentation level

        Returns:
            Generated code for this node
        """
        if isinstance(node, ToolCall):
            return self._generate_tool_call_code(node, indent)
        elif isinstance(node, SequentialWorkflow):
            return self._generate_sequential_code(node, indent)
        elif isinstance(node, ConditionalWorkflow):
            return self._generate_conditional_code(node, indent)
        elif isinstance(node, ParallelWorkflow):
            return self._generate_parallel_code(node, indent)
        elif isinstance(node, OrchestratorWorkflow):
            return self._generate_orchestrator_code(node, indent)
        else:
            return f"{'    ' * indent}# TODO: Unsupported node type: {type(node).__name__}"

    def _generate_tool_call_code(self, node: ToolCall, indent: int) -> str:
        """Generate code for a ToolCall node."""
        lines = []
        indent_str = "    " * indent

        # Add comment
        if node.description:
            lines.append(f"{indent_str}# {node.description}")

        # Generate parameter list (key=value for function calls, not dict syntax)
        params = []
        for key, value in node.parameters.items():
            # Resolve {{variable}} references
            resolved_value = self._resolve_variable_reference(value)
            params.append(f'{key}={resolved_value}')

        params_str = ", ".join(params)

        # Generate method call
        if node.assigns_to:
            lines.append(
                f"{indent_str}self.context['{node.assigns_to}'] = "
                f"self.{node.tool_name}({params_str})"
            )
        else:
            lines.append(f"{indent_str}self.{node.tool_name}({params_str})")

        return "\n".join(lines)

    def _resolve_variable_reference(self, value: str) -> str:
        """
        Resolve {{variable}} references to context lookups.

        Args:
            value: Parameter value that may contain {{var}} references

        Returns:
            Python code for accessing the variable
        """
        if not isinstance(value, str):
            return repr(value)

        # Check for {{variable}} pattern
        match = re.match(r'^{{([a-z_][a-z0-9_.]*)}}$', value, re.IGNORECASE)
        if match:
            var_path = match.group(1)
            # Handle nested properties: {{obj.property}}
            if '.' in var_path:
                parts = var_path.split('.')
                result = f"self.context['{parts[0]}']"
                for part in parts[1:]:
                    result += f"['{part}']"
                return result
            else:
                return f"self.context['{var_path}']"

        # Not a variable reference, return as string literal
        return repr(value)

    def _generate_sequential_code(self, node: SequentialWorkflow, indent: int) -> str:
        """Generate code for sequential workflow."""
        lines = []
        indent_str = "    " * indent

        if node.description:
            lines.append(f"{indent_str}# Sequential: {node.description}")

        for step in node.steps:
            step_code = self._generate_workflow_node(step, indent)
            lines.append(step_code)

        return "\n".join(lines)

    def _generate_conditional_code(self, node: ConditionalWorkflow, indent: int) -> str:
        """Generate code for conditional workflow."""
        lines = []
        indent_str = "    " * indent

        if node.description:
            lines.append(f"{indent_str}# Conditional: {node.description}")

        # Generate condition evaluation
        condition_code = self._generate_condition_eval(node.condition)
        lines.append(f"{indent_str}if {condition_code}:")

        # Generate if branch
        if_code = self._generate_workflow_node(node.if_branch, indent + 1)
        lines.append(if_code)

        # Generate else branch if present
        if node.else_branch:
            lines.append(f"{indent_str}else:")
            else_code = self._generate_workflow_node(node.else_branch, indent + 1)
            lines.append(else_code)

        return "\n".join(lines)

    def _generate_condition_eval(self, condition: str) -> str:
        """
        Generate safe condition evaluation code.

        Replaces {{variable}} with self.context['variable']

        Args:
            condition: Condition string with {{var}} references

        Returns:
            Python condition expression
        """
        # Replace all {{variable}} references
        result = condition
        for match in re.finditer(r'{{([a-z_][a-z0-9_.]*)}}', condition, re.IGNORECASE):
            var_ref = match.group(0)
            var_path = match.group(1)

            # Handle nested properties
            if '.' in var_path:
                parts = var_path.split('.')
                python_expr = f"self.context['{parts[0]}']"
                for part in parts[1:]:
                    python_expr += f".get('{part}')" if part != parts[-1] else f"['{part}']"
            else:
                python_expr = f"self.context.get('{var_path}')"

            result = result.replace(var_ref, python_expr)

        return result

    def _generate_parallel_code(self, node: ParallelWorkflow, indent: int) -> str:
        """Generate code for parallel workflow using asyncio.gather()."""
        lines = []
        indent_str = "    " * indent

        if node.description:
            lines.append(f"{indent_str}# Parallel: {node.description}")

        lines.append(f"{indent_str}# Execute branches concurrently using asyncio")
        lines.append(f"{indent_str}async def _parallel_executor():")

        # Generate async wrapper for each branch
        for i, branch in enumerate(node.branches, 1):
            lines.append(f"{indent_str}    async def branch_{i}():")
            # Generate the branch code with additional indentation
            branch_code = self._generate_workflow_node(branch, indent + 2)
            lines.append(branch_code)
            lines.append("")  # Blank line between branches

        # Generate gather or wait based on wait_for_all flag
        if node.wait_for_all:
            branch_calls = ", ".join(f"branch_{i}()" for i in range(1, len(node.branches) + 1))
            lines.append(f"{indent_str}    # Wait for all branches to complete")
            lines.append(f"{indent_str}    await asyncio.gather({branch_calls})")
        else:
            # wait_for_all is False - wait for first to complete
            lines.append(f"{indent_str}    # Wait for first branch to complete")
            tasks_list = ", ".join(f"branch_{i}()" for i in range(1, len(node.branches) + 1))
            lines.append(f"{indent_str}    tasks = [{tasks_list}]")
            lines.append(f"{indent_str}    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)")
            lines.append(f"{indent_str}    for task in pending:")
            lines.append(f"{indent_str}        task.cancel()")

        lines.append("")
        lines.append(f"{indent_str}# Run parallel execution")
        lines.append(f"{indent_str}asyncio.run(_parallel_executor())")

        return "\n".join(lines)

    def _generate_orchestrator_code(self, node: OrchestratorWorkflow, indent: int) -> str:
        """Generate code for orchestrator workflow (if-elif-else chain)."""
        lines = []
        indent_str = "    " * indent

        if node.description:
            lines.append(f"{indent_str}# Orchestrator: {node.description}")

        # Generate if-elif-else chain from routing rules
        for i, rule in enumerate(node.routing_rules):
            keyword = "if" if i == 0 else "elif"
            condition_code = self._generate_condition_eval(rule.condition)
            lines.append(f"{indent_str}{keyword} {condition_code}:")

            # Get the target workflow by name (fixed: was rule.target_workflow)
            target_workflow = node.sub_workflows[rule.workflow_name]
            workflow_code = self._generate_workflow_node(target_workflow, indent + 1)
            lines.append(workflow_code)

        # Generate default workflow if present
        if node.default_workflow:
            lines.append(f"{indent_str}else:")
            # Fixed: default_workflow is a string (workflow name), not a workflow object
            default_wf = node.sub_workflows[node.default_workflow]
            default_code = self._generate_workflow_node(default_wf, indent + 1)
            lines.append(default_code)

        return "\n".join(lines)

    def _generate_tool_methods(self) -> str:
        """
        Generate tool methods (library delegations or stubs).

        For tools in TOOL_REGISTRY: Generates delegation methods that call library functions.
        For unknown tools: Generates stub implementations with TODO comments.

        Returns:
            All tool method implementations
        """
        methods = []

        for tool_name in sorted(self.all_tools):
            if tool_name in TOOL_REGISTRY:
                # Tool has library implementation - generate delegation method
                method_code = self._generate_library_delegation(tool_name)
            else:
                # Tool not in library - generate stub as before
                tool_params = self._get_tool_parameters(tool_name)
                has_credentials = any(
                    self._is_credential_parameter(param)
                    for param in tool_params
                )

                if has_credentials:
                    method_code = self._generate_credential_tool_stub(tool_name, tool_params)
                else:
                    method_code = self._generate_simple_tool_stub(tool_name)

            methods.append(method_code)

        return "\n\n".join(methods)

    def _get_tool_parameters(self, tool_name: str) -> Set[str]:
        """Collect all parameter names used with this tool."""
        params = set()
        self._collect_tool_params_recursive(self.spec.workflow, tool_name, params)
        return params

    def _collect_tool_params_recursive(self, node, tool_name: str, params: Set[str]):
        """Recursively collect parameters for a specific tool."""
        if isinstance(node, ToolCall):
            if node.tool_name == tool_name:
                params.update(node.parameters.keys())
        elif isinstance(node, SequentialWorkflow):
            for step in node.steps:
                self._collect_tool_params_recursive(step, tool_name, params)
        elif isinstance(node, ConditionalWorkflow):
            self._collect_tool_params_recursive(node.if_branch, tool_name, params)
            if node.else_branch:
                self._collect_tool_params_recursive(node.else_branch, tool_name, params)
        elif isinstance(node, ParallelWorkflow):
            for branch in node.branches:
                self._collect_tool_params_recursive(branch, tool_name, params)
        elif isinstance(node, OrchestratorWorkflow):
            for sub_workflow in node.sub_workflows.values():
                self._collect_tool_params_recursive(sub_workflow, tool_name, params)

    def _generate_simple_tool_stub(self, tool_name: str) -> str:
        """Generate a simple tool stub without credentials."""
        lines = [
            f"def {tool_name}(self, **kwargs) -> Any:",
            f'    """Tool: {tool_name}"""',
            "    # TODO: Implement actual tool logic",
            '    return {"status": "not_implemented", "data": kwargs}'
        ]
        return "\n".join(lines)

    def _generate_credential_tool_stub(self, tool_name: str, params: Set[str]) -> str:
        """Generate a tool stub that handles credentials via environment variables."""
        lines = [
            f"def {tool_name}(self, **kwargs) -> Any:",
            f'    """Tool: {tool_name} - Uses credentials from environment variables"""',
        ]

        # Add environment variable handling for each credential parameter
        credential_params = [p for p in params if self._is_credential_parameter(p)]
        for param in sorted(credential_params):
            env_var = param.upper()
            lines.extend([
                "    ",
                f"    {param} = os.getenv('{env_var}')",
                f"    if not {param}:",
                "        raise ValueError(",
                f'            "Missing {env_var} environment variable\\n"',
                f'            "Setup: export {env_var}=<your-value-here>"',
                "        )",
            ])

        lines.extend([
            "    ",
            "    # TODO: Implement actual tool logic with credentials",
            '    return {"status": "not_implemented", "data": kwargs}'
        ])

        return "\n".join(lines)

    def _generate_library_delegation(self, tool_name: str) -> str:
        """
        Generate delegation method that calls tool library function.

        Args:
            tool_name: Name of the tool (must be in TOOL_REGISTRY)

        Returns:
            Delegation method code
        """
        lines = [
            f"def {tool_name}(self, **kwargs) -> Any:",
            f'    """Delegates to tool library implementation."""',
            f"    return {tool_name}(**kwargs)"
        ]
        return "\n".join(lines)

    def _generate_main_block(self) -> str:
        """
        Generate if __name__ == "__main__" block with example usage.

        Returns:
            Main block code
        """
        class_name = self._to_class_name(self.spec.name)

        lines = [
            'if __name__ == "__main__":',
            '    """Example usage of generated agent."""',
            f'    agent = {class_name}()',
            '    ',
            '    # Example inputs',
            '    inputs = {',
        ]

        for inp in self.spec.inputs:
            name = inp['name'] if isinstance(inp, dict) else inp.name
            is_cred = inp.get('is_credential', False) if isinstance(inp, dict) else inp.is_credential
            if is_cred:
                example = f"<{name}_from_env>"
            else:
                example = f"example_{name}"
            lines.append(f'        "{name}": "{example}",')

        lines.extend([
            '    }',
            '    ',
            '    try:',
            '        result = agent.execute(**inputs)',
            '        print("Workflow completed successfully!")',
            '        print(f"Result: {result}")',
            '    except Exception as e:',
            '        print(f"Workflow failed: {e}")',
        ])

        return "\n".join(lines)

    def _indent(self, text: str, levels: int) -> str:
        """Add indentation to multi-line text."""
        indent = "    " * levels
        lines = text.split("\n")
        return "\n".join(indent + line if line.strip() else line for line in lines)
