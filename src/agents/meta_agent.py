#!/usr/bin/env python3
"""
Meta-agent that converts natural language workflow specifications to typed AST.
Uses direct JSON generation for reliable structured output with various LLM providers.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from src.core.workflow_ast import WorkflowSpec

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file in project root
_project_root = Path(__file__).parent.parent.parent
_env_file = _project_root / ".env"

if _env_file.exists():
    load_dotenv(_env_file)
    logger.debug(f"Loaded .env file from: {_env_file}")
else:
    logger.warning(f".env file not found at: {_env_file}")
    load_dotenv()


class MetaAgent:
    """
    Meta-agent that converts text specifications to WorkflowSpec AST.
    Uses direct JSON generation instead of tool calling for better compatibility.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_aimlapi: bool = True,
        model: Optional[str] = None,
        api_timeout: float = 30.0
    ):
        """
        Initialize the meta-agent with API credentials.

        Args:
            api_key: API key for the service. If None, reads from environment.
            use_aimlapi: If True, use AIMLAPI. If False, use direct provider.
            model: Model to use. If None, uses AIMLAPI_MODEL env var or default.
            api_timeout: Timeout in seconds for API calls (default: 30s).
        """
        # Get API key from environment or parameter
        if api_key is None:
            api_key = os.getenv("AIMLAPI_KEY")
            if not api_key:
                raise ValueError(
                    "Missing AIMLAPI_KEY environment variable.\n"
                    "Please set it in your .env file or pass it as a parameter."
                )

        # Configure client for AIMLAPI
        if use_aimlapi:
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.aimlapi.com/v1"
            )
        else:
            self.client = OpenAI(api_key=api_key)

        # Get model from parameter, environment, or use default
        if model:
            self.model = model
        else:
            self.model = os.getenv("AIMLAPI_MODEL", "x-ai/grok-4-fast-reasoning")

        # Store timeout setting
        self.api_timeout = api_timeout

        logger.info(f"Initialized AIMLAPI client with model: {self.model}")

    def extract_workflow(self, spec_path: str) -> WorkflowSpec:
        """
        Extract workflow from a text specification file.

        Args:
            spec_path: Path to the specification file.

        Returns:
            WorkflowSpec: The extracted and validated workflow AST.
        """
        logger.info(f"Extracting workflow from: {spec_path}")

        # Parse the specification file
        spec_sections = self._read_spec(spec_path)

        # Call LLM to generate JSON directly
        try:
            json_output = self._call_llm_direct(spec_sections)

            # Log the raw JSON output for debugging
            logger.info("=" * 80)
            logger.info("LLM Response (Attempt 1):")
            logger.info(json_output)
            logger.info("=" * 80)

            # Parse JSON string
            json_data = json.loads(json_output)

            # Convert JSON to AST
            workflow_spec = self._json_to_ast(json_data)

            # Validate the AST
            errors = workflow_spec.validate()
            if errors:
                logger.warning(f"Validation errors, retrying: {errors}")

                # Retry once with error context
                json_output = self._call_llm_direct(spec_sections, retry_context=errors)

                # Log the retry response
                logger.info("=" * 80)
                logger.info("LLM Response (Retry):")
                logger.info(json_output)
                logger.info("=" * 80)

                json_data = json.loads(json_output)
                workflow_spec = self._json_to_ast(json_data)

                # Final validation
                errors = workflow_spec.validate()
                if errors:
                    logger.error("Failed workflow structure after retry:")
                    logger.error(json.dumps(workflow_spec.to_dict(), indent=2))
                    raise ValueError(f"Invalid workflow after retry: {errors}")

            logger.info(f"Successfully extracted workflow: {workflow_spec.name}")
            return workflow_spec

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON from LLM: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to extract workflow: {e}")

    def _read_spec(self, spec_path: str) -> Dict[str, Any]:
        """Parse text specification into structured sections."""
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
        else:
            raise ValueError("Missing required 'Workflow:' section in specification")

        # Extract description
        desc_match = re.search(r'^Description:\s*(.+)$', content, re.MULTILINE)
        if desc_match:
            sections['description'] = desc_match.group(1).strip()
        else:
            raise ValueError("Missing required 'Description:' section in specification")

        # Extract inputs section
        inputs_match = re.search(r'^Inputs:\s*\n((?:[-•]\s*.+\n?)+)', content, re.MULTILINE)
        if inputs_match:
            inputs_text = inputs_match.group(1)
            for line in inputs_text.strip().split('\n'):
                input_match = re.match(r'^[-•]\s*([\w-]+)\s*\(([\w-]+)\)(?:\s*:\s*(.+))?', line)
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
                step_match = re.match(r'^\d+\.\s*(.+)', line)
                if step_match:
                    sections['steps'].append(step_match.group(1))

        # Extract outputs section
        outputs_match = re.search(r'^Outputs:\s*\n((?:[-•]\s*.+\n?)+)', content, re.MULTILINE)
        if outputs_match:
            outputs_text = outputs_match.group(1)
            for line in outputs_text.strip().split('\n'):
                output_match = re.match(r'^[-•]\s*([\w-]+)\s*\(([\w-]+)\)(?:\s*:\s*(.+))?', line)
                if output_match:
                    sections['outputs'].append({
                        'name': output_match.group(1),
                        'type': output_match.group(2),
                        'description': output_match.group(3) or ''
                    })

        logger.debug(f"Parsed sections: {json.dumps(sections, indent=2)}")
        return sections

    def _call_llm_direct(
        self,
        spec_sections: Dict[str, Any],
        retry_context: Optional[List[str]] = None
    ) -> str:
        """
        Call LLM to generate JSON directly without tool calling.

        Returns:
            JSON string from the LLM.
        """
        # Load the system prompt from file
        prompt_file = _project_root / "prompts" / "simple_meta_agent_system_prompt.md"
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
            logger.debug(f"Loaded system prompt from: {prompt_file}")
        except FileNotFoundError:
            logger.error(f"System prompt file not found: {prompt_file}")
            raise ValueError(f"Missing system prompt file: {prompt_file}")

        # Build the user prompt
        user_prompt = f"""Parse this workflow specification into JSON:

Workflow: {spec_sections['workflow']}
Description: {spec_sections['description']}

Inputs:
{json.dumps(spec_sections['inputs'], indent=2)}

Steps:
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(spec_sections['steps']))}

Outputs:
{json.dumps(spec_sections['outputs'], indent=2)}

IMPORTANT: Create one tool_call object in the steps array for EACH numbered step above.
Each step should become: {{"type": "tool_call", "tool_name": "...", "parameters": {{...}}, "assigns_to": "..."}}"""

        if retry_context:
            user_prompt += f"\n\nPrevious attempt had validation errors:\n{chr(10).join(retry_context)}\n\n"
            user_prompt += "Fix these by ensuring the steps array contains tool_call objects for each numbered step."

        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        logger.debug(f"Calling LLM with model: {self.model}")

        # Make the API call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,  # Lower temperature for more consistent output
            max_tokens=4000,
            timeout=self.api_timeout
        )

        # Extract the response text
        if response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            if message and hasattr(message, 'content') and message.content:
                content = message.content
                # Clean up the response - remove markdown code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                return content.strip()

        raise RuntimeError("LLM did not return a valid response")

    def _json_to_ast(self, json_data: Dict[str, Any]) -> WorkflowSpec:
        """Convert JSON output from LLM to typed WorkflowSpec AST."""
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
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()