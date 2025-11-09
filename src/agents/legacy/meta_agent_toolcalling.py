"""
Meta-Agent: LLM-powered specification parser using tool calling.

This module extracts structured workflow specifications from natural language
text files and converts them into typed AST (Abstract Syntax Tree) objects.

Environment Variables:
    AIMLAPI_KEY: API key for AIML API service (required)

Example:
    >>> from src.agents.meta_agent import MetaAgent
    >>> agent = MetaAgent()
    >>> workflow_spec = agent.extract_workflow("specs/expense_approval.txt")
    >>> print(workflow_spec.name)
    expense_approval
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file in project root
# Find the project root (2 levels up from this file: src/agents/meta_agent.py)
_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")

from src.core.workflow_ast import (
    ConditionalWorkflow,
    OrchestratorWorkflow,
    ParallelWorkflow,
    SequentialWorkflow,
    ToolCall,
    WorkflowSpec,
)

# Configure logging
logger = logging.getLogger(__name__)


class MetaAgent:
    """LLM-powered specification parser using tool calling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_aimlapi: bool = True,
        model: Optional[str] = None
    ):
        """
        Initialize the meta-agent with API credentials.

        Args:
            api_key: API key for the service. If None, reads from environment.
            use_aimlapi: If True, use AIMLAPI. If False, use direct provider.
            model: Model to use. If None, uses AIMLAPI_MODEL env var or default.
        """
        if api_key is None:
            api_key = os.getenv("AIMLAPI_KEY")
            if not api_key:
                raise ValueError(
                    "Missing AIMLAPI_KEY environment variable. "
                    "Set it with: export AIMLAPI_KEY=your_key_here"
                )

        self.api_key = api_key
        self.use_aimlapi = use_aimlapi

        # Initialize OpenAI client for AIMLAPI
        if use_aimlapi:
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.aimlapi.com/v1"
            )
            # Get model from parameter, environment, or use default
            if model:
                self.model = model
            else:
                self.model = os.getenv("AIMLAPI_MODEL", "x-ai/grok-4-fast-reasoning")

            logger.info(f"Initialized AIMLAPI client with model: {self.model}")
        else:
            # For direct provider (future enhancement)
            raise NotImplementedError("Direct provider not yet implemented")

    def extract_workflow(self, spec_path: str) -> WorkflowSpec:
        """
        Main entry point: extract workflow from specification file.

        Args:
            spec_path: Path to the text specification file.

        Returns:
            WorkflowSpec: Parsed and validated workflow AST.

        Raises:
            FileNotFoundError: If spec file doesn't exist.
            ValueError: If specification is invalid.
            RuntimeError: If extraction fails after retry.
        """
        logger.info(f"Extracting workflow from: {spec_path}")

        # Read and parse specification
        spec_sections = self._read_spec(spec_path)

        # Call LLM with tool calling to generate structured output
        try:
            json_output = self._call_llm_with_tools(spec_sections)

            # Log the raw JSON output for debugging
            logger.info("=" * 80)
            logger.info("LLM Response (Attempt 1):")
            logger.info(json.dumps(json_output, indent=2))
            logger.info("=" * 80)

            # Convert JSON to AST
            workflow_spec = self._json_to_ast(json_output)

            # Validate the AST
            errors = workflow_spec.validate()
            if errors:
                logger.warning(f"Validation errors, retrying: {errors}")

                # Log what we got that failed validation
                logger.info("Failed workflow structure:")
                logger.info(json.dumps(workflow_spec.to_dict(), indent=2))

                # Retry once with error context
                json_output = self._call_llm_with_tools(
                    spec_sections,
                    retry_context=errors
                )

                # Log the retry response
                logger.info("=" * 80)
                logger.info("LLM Response (Retry):")
                logger.info(json.dumps(json_output, indent=2))
                logger.info("=" * 80)

                workflow_spec = self._json_to_ast(json_output)

                # Final validation
                errors = workflow_spec.validate()
                if errors:
                    logger.error("Failed workflow structure after retry:")
                    logger.error(json.dumps(workflow_spec.to_dict(), indent=2))
                    raise ValueError(f"Invalid workflow after retry: {errors}")

            logger.info(f"Successfully extracted workflow: {workflow_spec.name}")
            return workflow_spec

        except Exception as e:
            raise RuntimeError(f"Failed to extract workflow: {e}")

    def _read_spec(self, spec_path: str) -> Dict[str, Any]:
        """
        Parse text specification into structured sections.

        Args:
            spec_path: Path to the specification file.

        Returns:
            Dictionary with parsed sections: workflow, description, inputs, steps, outputs.
        """
        path = Path(spec_path)
        if not path.exists():
            raise FileNotFoundError(f"Specification file not found: {spec_path}")

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse sections using regex
        sections = {
            'workflow': '',
            'description': '',
            'inputs': [],
            'steps': [],
            'outputs': [],
            'raw_text': content
        }

        # Extract workflow name
        workflow_match = re.search(r'^Workflow:\s*(.+)$', content, re.MULTILINE)
        if workflow_match:
            sections['workflow'] = workflow_match.group(1).strip()

        # Extract description
        desc_match = re.search(r'^Description:\s*(.+)$', content, re.MULTILINE)
        if desc_match:
            sections['description'] = desc_match.group(1).strip()

        # Extract inputs section
        inputs_match = re.search(r'^Inputs:\s*\n((?:[-•]\s*.+\n?)+)', content, re.MULTILINE)
        if inputs_match:
            inputs_text = inputs_match.group(1)
            for line in inputs_text.strip().split('\n'):
                # Parse format: - param_name (type): description
                input_match = re.match(r'^[-•]\s*(\w+)\s*\((\w+)\)(?:\s*:\s*(.+))?', line)
                if input_match:
                    sections['inputs'].append({
                        'name': input_match.group(1),
                        'type': input_match.group(2),
                        'description': input_match.group(3) or ''
                    })

        # Extract steps section
        steps_match = re.search(r'^Steps:\s*\n((?:\d+\..+\n?)+)', content, re.MULTILINE)
        if steps_match:
            steps_text = steps_match.group(1)
            for line in steps_text.strip().split('\n'):
                # Parse format: 1. Step description
                step_match = re.match(r'^\d+\.\s*(.+)', line)
                if step_match:
                    sections['steps'].append(step_match.group(1))

        # Extract outputs section
        outputs_match = re.search(r'^Outputs:\s*\n((?:[-•]\s*.+\n?)+)', content, re.MULTILINE)
        if outputs_match:
            outputs_text = outputs_match.group(1)
            for line in outputs_text.strip().split('\n'):
                # Parse format: - output_name (type): description
                output_match = re.match(r'^[-•]\s*(\w+)\s*\((\w+)\)(?:\s*:\s*(.+))?', line)
                if output_match:
                    sections['outputs'].append({
                        'name': output_match.group(1),
                        'type': output_match.group(2),
                        'description': output_match.group(3) or ''
                    })

        logger.debug(f"Parsed sections: {json.dumps(sections, indent=2)}")
        return sections

    def _create_tool_schema(self) -> Dict[str, Any]:
        """
        Define the generate_workflow tool schema for LLM tool calling.

        Returns:
            Tool schema matching WorkflowSpec structure.
        """
        return {
            "type": "function",
            "function": {
                "name": "generate_workflow",
                "description": "Generate a structured workflow specification from natural language",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The workflow name (identifier)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Human-readable description of the workflow"
                        },
                        "version": {
                            "type": "string",
                            "description": "Version of the workflow",
                            "default": "1.0.0"
                        },
                        "inputs": {
                            "type": "array",
                            "description": "List of workflow inputs",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "description": {"type": "string"}
                                },
                                "required": ["name", "type"]
                            }
                        },
                        "outputs": {
                            "type": "array",
                            "description": "List of workflow outputs",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "description": {"type": "string"}
                                },
                                "required": ["name", "type"]
                            }
                        },
                        "workflow": {
                            "type": "object",
                            "description": "The workflow structure (sequential, conditional, parallel, etc). For sequential: MUST include 'steps' array with tool_call objects.",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["tool_call", "sequential", "conditional", "parallel", "orchestrator"],
                                    "description": "The type of workflow node"
                                }
                            },
                            "required": ["type"],
                            "additionalProperties": true
                        }
                    },
                    "required": ["name", "description", "inputs", "outputs", "workflow"]
                }
            }
        }

    def _call_llm_with_tools(
        self,
        spec_sections: Dict[str, Any],
        retry_context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Call LLM with tool calling to generate structured workflow JSON.

        Args:
            spec_sections: Parsed specification sections.
            retry_context: Optional validation errors from previous attempt.

        Returns:
            JSON output from the generate_workflow tool call.
        """
        # Load the system prompt from file
        prompt_file = _project_root / "prompts" / "meta_agent_system.md"
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
            logger.debug(f"Loaded system prompt from: {prompt_file}")
        except FileNotFoundError:
            logger.error(f"System prompt file not found: {prompt_file}")
            raise ValueError(f"Missing system prompt file: {prompt_file}")

        # Build the user prompt
        user_prompt = f"""Parse the following workflow specification:

Workflow: {spec_sections['workflow']}
Description: {spec_sections['description']}

Inputs:
{json.dumps(spec_sections['inputs'], indent=2)}

Steps:
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(spec_sections['steps']))}

Outputs:
{json.dumps(spec_sections['outputs'], indent=2)}
"""

        if retry_context:
            user_prompt += f"\n\nPrevious attempt had validation errors:\n{chr(10).join(retry_context)}\n\n"
            user_prompt += """IMPORTANT: Fix these errors by ensuring:
- SequentialWorkflow has a non-empty "steps" array with ToolCall objects
- Each ToolCall has: type, tool_name, parameters (can be empty {{}}), and optional assigns_to
- ConditionalWorkflow has both condition and if_branch (else_branch is optional)
- ParallelWorkflow has at least 2 branches
- All referenced variables exist in inputs or previous step outputs"""

        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        logger.debug(f"Calling LLM with model: {self.model}")

        # Call the LLM with tool calling
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=[self._create_tool_schema()],
            tool_choice={"type": "function", "function": {"name": "generate_workflow"}}
        )

        # Extract the tool call result
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            if tool_call.function.name == "generate_workflow":
                json_str = tool_call.function.arguments
                logger.debug(f"LLM returned JSON: {json_str}")
                return json.loads(json_str)

        raise RuntimeError("LLM did not return a valid tool call")

    def _json_to_ast(self, json_data: Dict[str, Any]) -> WorkflowSpec:
        """
        Convert JSON output from LLM to typed WorkflowSpec AST.

        Args:
            json_data: JSON dictionary from LLM tool call.

        Returns:
            WorkflowSpec: Typed AST object.
        """
        # Use WorkflowSpec.from_dict to handle the conversion
        # This leverages the existing deserialization logic
        return WorkflowSpec.from_dict(json_data)


def main():
    """Example usage of the MetaAgent."""
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m src.agents.meta_agent <spec_file>")
        sys.exit(1)

    spec_file = sys.argv[1]

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        # Initialize agent
        agent = MetaAgent()

        # Extract workflow
        workflow = agent.extract_workflow(spec_file)

        # Print result
        print(f"\nExtracted Workflow: {workflow.name}")
        print(f"Description: {workflow.description}")
        print(f"Inputs: {len(workflow.inputs)}")
        print(f"Outputs: {len(workflow.outputs)}")
        print(f"\nJSON Output:")
        print(json.dumps(workflow.to_dict(), indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()