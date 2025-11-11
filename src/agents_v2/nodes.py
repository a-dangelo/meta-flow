"""
LangGraph node implementations for meta-agent v2.

Each node is a function that takes MetaAgentState and returns updated state.
Nodes are composed into a LangGraph StateGraph with conditional routing.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .state import MetaAgentState, add_error_to_state
from .errors import ParsingError, ValidationError, ReasoningError
from .models import WorkflowSpec
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)


# ===== Parser Node (Deterministic) =====

def parser_node(state: MetaAgentState) -> MetaAgentState:
    """
    Parse text specification into structured sections.

    This is a deterministic node that uses regex to extract:
    - Workflow name
    - Description
    - Inputs
    - Steps
    - Outputs

    Args:
        state: Current state with raw_spec

    Returns:
        Updated state with parsed_sections and parsing_errors
    """
    logger.info("Parser node: Extracting sections from text spec")
    raw_spec = state['raw_spec']

    try:
        sections = {}
        errors = []

        # Extract workflow name
        workflow_match = re.search(
            r'^Workflow:\s*(.+)$',
            raw_spec,
            re.MULTILINE | re.IGNORECASE
        )
        if workflow_match:
            sections['workflow'] = workflow_match.group(1).strip()
        else:
            errors.append("Missing 'Workflow:' section")

        # Extract description
        desc_match = re.search(
            r'^Description:\s*(.+)$',
            raw_spec,
            re.MULTILINE | re.IGNORECASE
        )
        if desc_match:
            sections['description'] = desc_match.group(1).strip()
        else:
            errors.append("Missing 'Description:' section")

        # Extract inputs
        inputs_match = re.search(
            r'^Inputs:\s*$(.*?)^(?:\w+:|$)',
            raw_spec,
            re.MULTILINE | re.IGNORECASE | re.DOTALL
        )
        if inputs_match:
            inputs_text = inputs_match.group(1).strip()
            sections['inputs'] = _parse_list_items(inputs_text)
        else:
            sections['inputs'] = []  # Inputs are optional

        # Extract steps
        steps_match = re.search(
            r'^Steps:\s*$(.*?)^(?:\w+:|$)',
            raw_spec,
            re.MULTILINE | re.IGNORECASE | re.DOTALL
        )
        if steps_match:
            steps_text = steps_match.group(1).strip()
            sections['steps'] = _parse_numbered_steps(steps_text)
        else:
            errors.append("Missing 'Steps:' section")

        # Extract outputs
        outputs_match = re.search(
            r'^Outputs:\s*$(.*?)^(?:\w+:|$)',
            raw_spec,
            re.MULTILINE | re.IGNORECASE | re.DOTALL
        )
        if outputs_match:
            outputs_text = outputs_match.group(1).strip()
            sections['outputs'] = _parse_list_items(outputs_text)
        else:
            sections['outputs'] = []  # Outputs are optional

        # Update state
        return {
            **state,
            'parsed_sections': sections,
            'parsing_errors': errors,
            'execution_status': 'reasoning' if not errors else 'error'
        }

    except Exception as e:
        logger.error(f"Parser node failed: {e}")
        return add_error_to_state(
            state,
            stage='parser',
            error_type=type(e).__name__,
            message=str(e),
            recoverable=False
        )


def _parse_list_items(text: str) -> List[str]:
    """
    Parse bulleted/dashed list items.

    Example:
        - item1 (type): description
        - item2 (type): description

    Returns:
        List of item strings
    """
    items = []
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('-') or line.startswith('*'):
            item = line[1:].strip()
            if item:
                items.append(item)
    return items


def _parse_numbered_steps(text: str) -> List[str]:
    """
    Parse numbered steps.

    Example:
        1. First step
        2. Second step
        3. Third step

    Returns:
        List of step descriptions
    """
    steps = []
    for line in text.split('\n'):
        line = line.strip()
        # Match numbered items: "1. ", "2. ", etc.
        match = re.match(r'^\d+\.\s+(.+)$', line)
        if match:
            step = match.group(1).strip()
            if step:
                steps.append(step)
    return steps


# ===== Reasoner Node (LLM-Powered) =====

def reasoner_node(state: MetaAgentState) -> MetaAgentState:
    """
    Use LLM to infer workflow structure from parsed sections.

    This node:
    1. Builds a structured prompt from parsed sections
    2. Calls LLM to generate workflow JSON
    3. Calculates confidence score
    4. Stores reasoning trace

    Args:
        state: Current state with parsed_sections

    Returns:
        Updated state with inferred_structure, confidence_score, reasoning_trace
    """
    logger.info("Reasoner node: Using LLM to infer workflow structure")

    try:
        # Get provider from state (default to aimlapi)
        from .providers import create_provider

        provider_name = state.get('llm_provider', 'aimlapi')
        model_override = state.get('model_version')

        logger.info(f"Using provider: {provider_name}")

        # Create provider instance
        provider = create_provider(provider_name, model=model_override)

        # Build prompt from parsed sections
        prompt = _build_reasoning_prompt(
            state['parsed_sections'],
            state.get('feedback_messages', [])
        )

        # NEW: Add validation error feedback if retrying
        if state.get('retry_count', 0) > 0 and state.get('validation_errors'):
            validation_feedback = _format_validation_feedback(
                state['validation_errors'],
                state.get('last_generated_json')
            )
            prompt += f"\n{validation_feedback}"
            logger.info(f"Added validation feedback for retry #{state['retry_count']}")

        # Determine if we should use structured output
        use_structured = (
            provider_name == 'gemini' and
            hasattr(provider, 'generate_structured') and
            state.get('use_structured_output', True)  # Can be disabled via state
        )

        # Check if we should use Claude's JSON generation
        use_claude_json = (
            provider_name in ('claude', 'anthropic') and
            hasattr(provider, 'generate_json')
        )

        if use_structured:
            # Use structured output for Gemini (guaranteed JSON validity)
            logger.info("Using Gemini structured output mode")

            # Get JSON schema for WorkflowSpec
            from .schema_converter import generate_workflow_schema

            try:
                workflow_schema = generate_workflow_schema()
                logger.debug(f"Generated schema with {len(workflow_schema.get('properties', {}))} properties")

                llm_output = provider.generate_structured(
                    system_prompt=_get_system_prompt(),
                    user_prompt=prompt,
                    response_schema=workflow_schema,
                    temperature=0.05,  # Lower for Gemini
                    max_tokens=4000
                )

                # With structured output, JSON is guaranteed valid
                inferred_structure = json.loads(llm_output)
                logger.info("Structured output produced valid JSON")

            except Exception as e:
                logger.warning(f"Structured output failed, falling back to regular: {e}")
                # Fall back to regular generation
                use_structured = False

        if use_claude_json and not use_structured:
            # Use Claude's JSON generation capability
            logger.info("Using Claude JSON generation mode")
            try:
                llm_output = provider.generate_json(
                    system_prompt=_get_system_prompt(),
                    user_prompt=prompt,
                    temperature=0.1,
                    max_tokens=4000,
                    retry_on_invalid=True  # Claude will retry once if JSON is invalid
                )
                # Claude's generate_json returns validated JSON string
                inferred_structure = json.loads(llm_output)
                logger.info("Claude produced valid JSON")
            except Exception as e:
                logger.warning(f"Claude JSON generation failed: {e}")
                raise ReasoningError(
                    f"Claude JSON generation failed: {e}",
                    llm_response=str(e),
                    retry_count=state.get('retry_count', 0)
                )

        elif not use_structured and not use_claude_json:
            # Regular generation (original code)
            logger.debug(f"Calling LLM: {provider.get_model_name()}")
            llm_output = provider.generate(
                system_prompt=_get_system_prompt(),
                user_prompt=prompt,
                temperature=0.1 if provider_name != 'gemini' else 0.05,
                max_tokens=4000
            )

            logger.debug(f"LLM response length: {len(llm_output)} chars")

            # Clean markdown code fences if present
            if llm_output.startswith('```'):
                llm_output = re.sub(r'^```(?:json)?\s*', '', llm_output)
                llm_output = re.sub(r'\s*```$', '', llm_output)

            # Parse JSON with repair fallback
            try:
                inferred_structure = json.loads(llm_output)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed, attempting repair: {e}")

                # Try to repair if using Gemini
                if provider_name == 'gemini':
                    from .json_repair import repair_gemini_json

                    # Get available variables for repair
                    available_vars = set()
                    # Add input variables
                    for inp in state['parsed_sections'].get('inputs', []):
                        # Extract variable name from either:
                        # - "var_name (type): description" format
                        # - "var_name: description" format
                        if '(' in inp and ')' in inp:
                            # Format with type in parentheses
                            var_name = inp.split('(')[0].strip()
                        elif ':' in inp:
                            # Simple format without parentheses
                            var_name = inp.split(':')[0].strip()
                        else:
                            # Fallback: use whole string as variable name
                            var_name = inp.strip()

                        if var_name:  # Only add non-empty variable names
                            available_vars.add(var_name)

                    repaired_json = repair_gemini_json(llm_output, available_vars)

                    try:
                        inferred_structure = json.loads(repaired_json)
                        logger.info("JSON repair successful")
                    except json.JSONDecodeError:
                        logger.error(f"JSON repair failed, original error: {e}")
                        raise ReasoningError(
                            f"LLM output is not valid JSON even after repair: {e}",
                            llm_response=llm_output,
                            retry_count=state.get('retry_count', 0)
                        )
                else:
                    # Non-Gemini providers don't need repair typically
                    raise ReasoningError(
                        f"LLM output is not valid JSON: {e}",
                        llm_response=llm_output,
                        retry_count=state.get('retry_count', 0)
                    )

        # Calculate confidence score
        confidence = _calculate_confidence(
            inferred_structure,
            state['parsed_sections']
        )

        logger.info(f"Reasoning complete. Confidence: {confidence:.2f}")

        # Update state
        return {
            **state,
            'inferred_structure': inferred_structure,
            'last_generated_json': llm_output,  # NEW: Store for feedback on retry
            'confidence_score': confidence,
            'reasoning_trace': [f"LLM inference at {datetime.utcnow().isoformat()}"],
            'execution_status': 'validating',
            'should_escalate': confidence < 0.8
        }

    except ReasoningError:
        raise
    except Exception as e:
        logger.error(f"Reasoner node failed: {e}")
        return add_error_to_state(
            state,
            stage='reasoner',
            error_type=type(e).__name__,
            message=str(e),
            recoverable=True
        )


def _build_reasoning_prompt(
    sections: Dict[str, Any],
    feedback: List[str]
) -> str:
    """Build prompt for LLM reasoning."""
    prompt_parts = [
        "Convert this workflow specification to JSON:",
        "",
        f"Workflow: {sections.get('workflow', 'N/A')}",
        f"Description: {sections.get('description', 'N/A')}",
        "",
        "Inputs:"
    ]

    for inp in sections.get('inputs', []):
        prompt_parts.append(f"  - {inp}")

    prompt_parts.append("")
    prompt_parts.append("Steps:")
    for i, step in enumerate(sections.get('steps', []), 1):
        prompt_parts.append(f"  {i}. {step}")

    prompt_parts.append("")
    prompt_parts.append("Outputs:")
    for out in sections.get('outputs', []):
        prompt_parts.append(f"  - {out}")

    # Add feedback from previous attempts if any
    if feedback:
        prompt_parts.append("")
        prompt_parts.append("Previous attempt had these issues:")
        for msg in feedback:
            prompt_parts.append(f"  - {msg}")

    return "\n".join(prompt_parts)


def _get_system_prompt() -> str:
    """
    Get system prompt for LLM reasoning.

    Loads the v2.1 Gemini-optimized prompt from file.
    Falls back to inline prompt if file not found.
    """
    from pathlib import Path

    # Try to load from file
    prompt_file = Path(__file__).parent.parent.parent / "prompts" / "meta_agent_v2_system_prompt.md"

    if prompt_file.exists():
        try:
            return prompt_file.read_text(encoding='utf-8')
        except Exception as e:
            logger.warning(f"Failed to load prompt from file: {e}, using fallback")

    # Fallback inline prompt (simplified)
    return """You are a workflow parser. Convert specifications into JSON with ZERO tolerance for errors.

OUTPUT STRUCTURE:
{
  "name": "workflow_name_from_spec",
  "description": "copy from spec Description field",
  "version": "1.0.0",
  "inputs": [
    {"name": "input_name", "type": "string", "description": "from spec"}
  ],
  "outputs": [
    {"name": "output_name", "type": "string", "description": "from spec"}
  ],
  "workflow": {
    "type": "sequential",
    "steps": [
      {
        "type": "tool_call",
        "tool_name": "action_verb_noun",
        "parameters": {"key": "{{variable_name}}"},
        "assigns_to": "output_variable"
      }
    ]
  }
}

MANDATORY RULES:
1. Count the numbered steps in the specification
2. Create EXACTLY that many tool_call objects in the "steps" array
3. One tool_call per numbered step - no exceptions

Return ONLY valid JSON. No explanations. No markdown. No code fences."""


def _format_validation_feedback(
    validation_errors: List[str],
    last_json: Optional[str] = None
) -> str:
    """
    Format Pydantic validation errors into actionable feedback for LLM.

    Groups errors by type (type fields, missing fields, variable refs)
    and provides specific guidance for each category.
    """
    feedback_parts = [
        "\nVALIDATION ERRORS FROM PREVIOUS ATTEMPT:",
        "Your previous JSON had these issues:\n"
    ]

    # Group errors by pattern
    type_errors = [e for e in validation_errors if "type: Input should be" in e]
    field_errors = [e for e in validation_errors if "Field required" in e]
    variable_errors = [e for e in validation_errors if "references undefined variable" in e]
    other_errors = [e for e in validation_errors
                   if e not in type_errors + field_errors + variable_errors]

    # Check if this looks like a discriminated union error (many type errors across different workflow types)
    has_many_type_errors = len(type_errors) > 10
    is_discriminated_union_issue = has_many_type_errors and any(
        "OrchestratorWorkflow" in e or "ConditionalWorkflow" in e or "ParallelWorkflow" in e
        for e in type_errors
    )

    if is_discriminated_union_issue:
        feedback_parts.extend([
            "DISCRIMINATED UNION ERROR DETECTED:",
            "Pydantic couldn't match your JSON to ANY valid workflow type.",
            "This usually means the top-level 'workflow' field has the wrong structure.",
            "",
            "COMMON MISTAKES:",
            "1. Missing or incorrect 'type' field at the top level of 'workflow'",
            "2. Using wrong workflow type (e.g., sequential when should be orchestrator)",
            "3. Nested structures missing their 'type' fields",
            "",
            "WORKFLOW TYPE SELECTION GUIDE:",
            "- Use 'sequential' for: Linear steps without branching",
            "- Use 'conditional' for: Single if/else decision",
            "- Use 'orchestrator' for: Multiple routing rules with sub-workflows",
            "- Use 'parallel' for: Concurrent execution of independent tasks",
            "",
            "ORCHESTRATOR STRUCTURE (if multiple 'if X route to Y' patterns):",
            "{",
            "  \"type\": \"orchestrator\",",
            "  \"sub_workflows\": {",
            "    \"workflow_name\": { \"type\": \"sequential\", \"steps\": [...] },",
            "    ...",
            "  },",
            "  \"routing_rules\": [",
            "    { \"condition\": \"...\", \"target_workflow\": \"workflow_name\" }",
            "  ],",
            "  \"default_workflow\": \"default_workflow_name\"",
            "}",
            "",
            f"You generated {len(validation_errors)} errors. The top-level workflow type is WRONG.",
            "Analyze the specification again and choose the correct workflow type."
        ])
    elif type_errors:
        # Regular type errors
        feedback_parts.extend([
            "TYPE FIELD ERRORS:",
            "CRITICAL: Every workflow node MUST have a 'type' field:",
            "  - tool_call: {\"type\": \"tool_call\", \"tool_name\": \"...\", ...}",
            "  - sequential: {\"type\": \"sequential\", \"steps\": [...]}",
            "  - conditional: {\"type\": \"conditional\", \"condition\": \"...\", ...}",
            "  - parallel: {\"type\": \"parallel\", \"branches\": [...]}",
            "  - orchestrator: {\"type\": \"orchestrator\", \"sub_workflows\": {...}, \"routing_rules\": [...]}",
            "\nYour errors:"
        ])
        for error in type_errors[:5]:
            feedback_parts.append(f"  × {error}")

    # Handle missing field errors
    if field_errors and not is_discriminated_union_issue:
        feedback_parts.extend([
            "\nMISSING REQUIRED FIELDS:"
        ])
        for error in field_errors[:5]:
            feedback_parts.append(f"  × {error}")

    # Handle variable reference errors (common in parallel)
    if variable_errors:
        feedback_parts.extend([
            "\nVARIABLE REFERENCE ERRORS:",
            "CRITICAL: Use DOUBLE braces {{variable_name}}, NOT {{{{ref}}}}",
            "Variables must be defined by previous steps' 'assigns_to' fields.",
            "\nYour errors:"
        ])
        for error in variable_errors:
            feedback_parts.append(f"  × {error}")

    # Handle other errors
    if other_errors and not is_discriminated_union_issue:
        feedback_parts.append("\nOTHER ERRORS:")
        for error in other_errors[:5]:
            feedback_parts.append(f"  × {error}")

    feedback_parts.extend([
        "\nPlease regenerate the COMPLETE JSON fixing these specific issues.",
        "Read the specification carefully and choose the RIGHT workflow type first."
    ])

    return "\n".join(feedback_parts)


def _calculate_confidence(
    structure: Dict[str, Any],
    sections: Dict[str, Any]
) -> float:
    """
    Calculate confidence score for inferred structure.

    Factors:
    - Completeness (all sections present)
    - Step count matches
    - Variable references valid
    - Structure complexity

    Returns:
        Confidence score (0.0 to 1.0)
    """
    score = 1.0

    # Check completeness
    if 'name' not in structure:
        score -= 0.3
    if 'description' not in structure:
        score -= 0.1
    if 'workflow' not in structure:
        score -= 0.5

    # Check step count
    expected_steps = len(sections.get('steps', []))
    if 'workflow' in structure:
        workflow = structure['workflow']
        if workflow.get('type') == 'sequential':
            actual_steps = len(workflow.get('steps', []))
            if actual_steps != expected_steps:
                score -= 0.2

    # Ensure score is in valid range
    return max(0.0, min(1.0, score))


# ===== Validator Node (Pydantic-Based) =====

def validator_node(state: MetaAgentState) -> MetaAgentState:
    """
    Validate inferred structure using Pydantic models.

    This node:
    1. Attempts to create WorkflowSpec from inferred_structure
    2. Catches Pydantic validation errors
    3. Formats errors for feedback
    4. Determines if retry or escalation needed

    Args:
        state: Current state with inferred_structure

    Returns:
        Updated state with workflow_spec, validation_errors
    """
    logger.info("Validator node: Validating structure with Pydantic")

    try:
        # Attempt to create WorkflowSpec
        spec = WorkflowSpec(**state['inferred_structure'])

        logger.info("✓ Validation passed")

        # Update state with validated spec
        return {
            **state,
            'workflow_spec': spec.to_dict(),
            'validation_errors': [],
            'execution_status': 'generating'
        }

    except PydanticValidationError as e:
        # Parse Pydantic errors into readable format
        errors = []
        for error in e.errors():
            field = '.'.join(str(loc) for loc in error['loc'])
            message = error['msg']
            errors.append(f"{field}: {message}")

        logger.warning(f"✗ Validation failed with {len(errors)} error(s)")
        for error in errors[:5]:  # Log first 5 errors
            logger.warning(f"  - {error}")

        # Update state
        return {
            **state,
            'workflow_spec': None,
            'validation_errors': errors,
            'execution_status': 'error',
            'feedback_messages': errors[:5],  # Use for retry (limit to 5)
            'retry_count': state.get('retry_count', 0) + 1
        }

    except Exception as e:
        logger.error(f"Validator node failed: {e}")
        return add_error_to_state(
            state,
            stage='validator',
            error_type=type(e).__name__,
            message=str(e),
            recoverable=False
        )


# ===== Generator Node (Serialization) =====

def generator_node(state: MetaAgentState) -> MetaAgentState:
    """
    Generate final JSON from validated WorkflowSpec.

    This node:
    1. Serializes WorkflowSpec to JSON
    2. Verifies round-trip consistency
    3. Marks execution as complete

    Args:
        state: Current state with workflow_spec

    Returns:
        Updated state with generated_json
    """
    logger.info("Generator node: Generating final JSON")

    try:
        # Serialize to JSON
        spec = WorkflowSpec(**state['workflow_spec'])
        json_output = spec.to_json(indent=2)

        # Verify round-trip consistency
        parsed_back = WorkflowSpec.from_json(json_output)
        if parsed_back.to_dict() != state['workflow_spec']:
            raise ValueError("Round-trip validation failed: JSON serialization produced different structure")

        logger.info("✓ Generation complete")

        return {
            **state,
            'generated_json': json_output,
            'execution_status': 'complete'
        }

    except Exception as e:
        logger.error(f"Generator node failed: {e}")
        return add_error_to_state(
            state,
            stage='generator',
            error_type=type(e).__name__,
            message=str(e),
            recoverable=False
        )


# ===== Escalation Node (Human-in-Loop) =====

def escalation_node(state: MetaAgentState) -> MetaAgentState:
    """
    Handle escalation to human review.

    This node:
    1. Generates human-readable report
    2. Logs escalation details
    3. Marks execution as escalated

    Args:
        state: Current state

    Returns:
        Updated state with execution_status='escalated'
    """
    logger.warning("Escalation node: Preparing for human review")

    # Build escalation report
    report_parts = [
        "=== ESCALATION REQUIRED ===",
        f"Execution ID: {state.get('execution_id', 'unknown')}",
        f"Confidence Score: {state.get('confidence_score', 0.0):.2f}",
        f"Retry Count: {state.get('retry_count', 0)}",
        "",
        "Parsed Sections:"
    ]

    for key, value in state.get('parsed_sections', {}).items():
        report_parts.append(f"  {key}: {value}")

    if state.get('parsing_errors'):
        report_parts.append("")
        report_parts.append("Parsing Errors:")
        for error in state['parsing_errors']:
            report_parts.append(f"  - {error}")

    if state.get('validation_errors'):
        report_parts.append("")
        report_parts.append("Validation Errors:")
        for error in state['validation_errors'][:10]:  # Limit to 10
            report_parts.append(f"  - {error}")

    report = "\n".join(report_parts)
    logger.warning(f"\n{report}")

    return {
        **state,
        'execution_status': 'escalated'
    }
