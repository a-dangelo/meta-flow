"""Client for integrating with existing meta-agent pipeline."""

import sys
from pathlib import Path
from typing import Optional

# Add src/ to path for importing existing modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.agents.graph import run_meta_agent
from src.generators.agent_generator import AgentGenerator
from src.agents.models import WorkflowSpec


class MetaAgentClient:
    """
    Client wrapper for calling existing meta-agent pipeline.

    Responsibilities:
    - Call Phase 1: spec → JSON (existing meta-agent)
    - Call Phase 2: JSON → Python code (existing code generator)
    - Return both JSON and generated code
    """

    async def generate_agent_from_spec(
        self,
        spec_content: str,
        provider: str = "claude",
        model_version: Optional[str] = None
    ) -> tuple[dict, str]:
        """
        Generate agent from workflow specification.

        Args:
            spec_content: Full .txt specification content
            provider: LLM provider (claude, aimlapi, gemini)
            model_version: Optional model version override

        Returns:
            Tuple of (json_output dict, python_code string)

        Raises:
            ValueError: If meta-agent fails or validation errors
        """
        # Phase 1: Run meta-agent to generate JSON
        # Note: run_meta_agent is synchronous, not async
        result = run_meta_agent(
            raw_spec=spec_content,
            llm_provider=provider,
            model_version=model_version
        )

        # Check for errors
        # Note: meta-agent returns "complete" not "completed"
        if result.get("execution_status") != "complete":
            error_msg = result.get("error_message", "Unknown error")
            raise ValueError(f"Meta-agent generation failed: {error_msg}")

        # Get workflow_spec dict from result
        workflow_spec_dict = result.get("workflow_spec")
        if not workflow_spec_dict:
            raise ValueError("No workflow_spec in meta-agent result")

        # Convert dict to Pydantic WorkflowSpec model (v2)
        workflow_spec = WorkflowSpec.model_validate(workflow_spec_dict)

        # Convert to plain dict for JSON output
        json_output = workflow_spec.model_dump()

        # Phase 2: Generate Python code
        generator = AgentGenerator(workflow_spec)
        python_code = generator.generate()

        return json_output, python_code

    def validate_spec(self, spec_content: str) -> tuple[bool, list[str]]:
        """
        Validate specification format without generating agent.

        Args:
            spec_content: Specification text

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        required_sections = ["Workflow:", "Description:", "Inputs:", "Steps:", "Outputs:"]
        errors = []

        for section in required_sections:
            if section not in spec_content:
                errors.append(f"Missing required section: {section}")

        # Check for empty sections
        if not errors:
            lines = spec_content.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith(tuple(required_sections)):
                    # Check if next non-empty line exists
                    next_content = False
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip() and not lines[j].strip().startswith(tuple(required_sections)):
                            next_content = True
                            break
                        if lines[j].strip().startswith(tuple(required_sections)):
                            break

                    if not next_content:
                        errors.append(f"Empty section: {line.strip()}")

        return len(errors) == 0, errors
