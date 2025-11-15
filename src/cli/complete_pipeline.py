"""
Complete pipeline CLI: Text specification → Executable Python agent.

Integrates Phase 1 (meta-agent JSON generation) and Phase 2 (code generation)
into a single command-line interface.

Usage:
    python -m src.cli.complete_pipeline specs/example.txt --verbose
    python -m src.cli.complete_pipeline specs/example.txt --output-dir ./agents
    python -m src.cli.complete_pipeline specs/example.txt --validate-only
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import py_compile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Phase 1: Meta-agent
from src.agents_v2.graph import create_meta_agent_graph
from src.agents_v2.state import create_initial_state
from src.agents_v2.models import WorkflowSpec

# Phase 2: Code generator
from src.generators.agent_generator import AgentGenerator


def setup_logging(verbose: bool) -> logging.Logger:
    """
    Configure logging for the pipeline.

    Args:
        verbose: If True, use DEBUG level; else INFO

    Returns:
        Configured logger instance
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=level
    )
    return logging.getLogger(__name__)


def read_spec_file(spec_path: Path, logger: logging.Logger) -> str:
    """
    Read text specification from file.

    Args:
        spec_path: Path to .txt specification file
        logger: Logger instance

    Returns:
        Specification text content

    Raises:
        FileNotFoundError: If spec file doesn't exist
        IOError: If file can't be read
    """
    if not spec_path.exists():
        logger.error(f"Specification file not found: {spec_path}")
        logger.info(f"Current directory: {Path.cwd()}")
        logger.info(f"Looking for: {spec_path.absolute()}")
        raise FileNotFoundError(f"Spec file not found: {spec_path}")

    logger.debug(f"Reading specification from: {spec_path}")

    try:
        with open(spec_path) as f:
            content = f.read()

        logger.info(f"✓ Loaded specification: {len(content)} characters")
        return content

    except IOError as e:
        logger.error(f"Failed to read spec file: {e}")
        raise


def run_phase1_meta_agent(
    spec_text: str,
    llm_provider: str,
    model_version: Optional[str],
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Run Phase 1: Convert text specification to JSON workflow.

    Args:
        spec_text: Text specification content
        llm_provider: LLM provider to use (claude, aimlapi, gemini)
        model_version: Optional model version override
        logger: Logger instance

    Returns:
        Final state from meta-agent execution

    Raises:
        RuntimeError: If meta-agent fails or produces invalid JSON
    """
    logger.info("=" * 60)
    logger.info("PHASE 1: Meta-Agent (Text → JSON)")
    logger.info("=" * 60)

    # Create meta-agent graph
    graph = create_meta_agent_graph()

    # Create initial state
    initial_state = create_initial_state(
        raw_spec=spec_text,
        llm_provider=llm_provider,
        model_version=model_version
    )

    logger.info("Executing meta-agent workflow...")
    logger.info(f"Provider: {llm_provider}, Model: {initial_state.get('model_version', 'default')}")
    logger.debug(f"Initial state: {initial_state}")

    try:
        # Run the graph
        final_state = graph.invoke(initial_state)

        # Check execution status
        status = final_state.get('execution_status')
        logger.info(f"Meta-agent status: {status}")

        if status != 'complete':
            error = final_state.get('error', 'Unknown error')
            logger.error(f"Meta-agent failed: {error}")
            raise RuntimeError(f"Meta-agent execution failed: {error}")

        # Validate we have workflow_spec
        if 'workflow_spec' not in final_state or final_state['workflow_spec'] is None:
            logger.error("Meta-agent completed but no workflow_spec generated")
            raise RuntimeError("No workflow_spec in final state")

        # Convert workflow_spec dict to Pydantic WorkflowSpec object
        # (Following pattern from tests/test_agent_generator.py)
        workflow_spec = WorkflowSpec.model_validate(final_state['workflow_spec'])

        logger.info(f"✓ Phase 1 complete (confidence: {final_state.get('confidence_score', 0.0):.2f})")
        logger.info(f"✓ Workflow: {workflow_spec.name}")
        logger.info(f"✓ Retry count: {final_state.get('retry_count', 0)}")

        # Update final_state with Pydantic object for Phase 2
        final_state['workflow_spec'] = workflow_spec

        return final_state

    except Exception as e:
        logger.error(f"Meta-agent execution failed: {e}", exc_info=True)
        raise RuntimeError(f"Phase 1 failed: {e}") from e


def run_phase2_code_generation(
    workflow_spec: WorkflowSpec,
    logger: logging.Logger
) -> str:
    """
    Run Phase 2: Generate Python code from WorkflowSpec.

    Args:
        workflow_spec: Validated Pydantic WorkflowSpec
        logger: Logger instance

    Returns:
        Generated Python code as string

    Raises:
        RuntimeError: If code generation fails
    """
    logger.info("=" * 60)
    logger.info("PHASE 2: Code Generation (JSON → Python)")
    logger.info("=" * 60)

    logger.info(f"Generating agent for: {workflow_spec.name}")
    logger.debug(f"Workflow type: {workflow_spec.workflow.type}")

    try:
        generator = AgentGenerator(workflow_spec)
        python_code = generator.generate()

        logger.info(f"✓ Code generation complete")
        logger.info(f"✓ Generated {len(python_code)} characters")
        logger.info(f"✓ Lines: {len(python_code.splitlines())}")
        logger.info(f"✓ Credentials detected: {len(generator.credential_params)}")
        logger.info(f"✓ Tools generated: {len(generator.all_tools)}")

        return python_code

    except Exception as e:
        logger.error(f"Code generation failed: {e}", exc_info=True)
        raise RuntimeError(f"Phase 2 failed: {e}") from e


def validate_python_syntax(
    code: str,
    output_path: Path,
    logger: logging.Logger
) -> bool:
    """
    Validate generated Python code syntax.

    Args:
        code: Python code to validate
        output_path: Where code will be saved (for error messages)
        logger: Logger instance

    Returns:
        True if syntax is valid, False otherwise
    """
    logger.info("Validating Python syntax...")

    # Write to temp file for compilation
    temp_file = output_path.with_suffix('.tmp.py')

    # Ensure parent directory exists
    temp_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(temp_file, 'w') as f:
            f.write(code)

        # Compile to check syntax
        py_compile.compile(str(temp_file), doraise=True)

        logger.info("✓ Python syntax validation passed")
        return True

    except py_compile.PyCompileError as e:
        logger.error(f"Syntax validation failed:")
        logger.error(f"  File: {e.file}")
        logger.error(f"  Line: {e.exc_value[1][1] if hasattr(e.exc_value, '__getitem__') else 'unknown'}")
        logger.error(f"  Message: {e.msg}")
        return False

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()


def save_outputs(
    workflow_spec: WorkflowSpec,
    python_code: str,
    output_dir: Path,
    save_json: bool,
    logger: logging.Logger
) -> Dict[str, Path]:
    """
    Save generated outputs to files.

    Args:
        workflow_spec: Workflow specification
        python_code: Generated Python code
        output_dir: Output directory
        save_json: Whether to save intermediate JSON
        logger: Logger instance

    Returns:
        Dictionary mapping output type to file path
    """
    logger.info(f"Saving outputs to: {output_dir}")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {}

    # Save JSON if requested
    if save_json:
        json_path = output_dir / f"{workflow_spec.name}.json"
        with open(json_path, 'w') as f:
            json.dump(workflow_spec.model_dump(), f, indent=2)
        logger.info(f"✓ Saved JSON: {json_path}")
        outputs['json'] = json_path

    # Save Python agent
    python_path = output_dir / f"{workflow_spec.name}_agent.py"
    with open(python_path, 'w') as f:
        f.write(python_code)
    logger.info(f"✓ Saved Python agent: {python_path}")
    outputs['python'] = python_path

    return outputs


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate executable Python agents from text specifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate agent with default settings (Claude Haiku 4.5)
  python -m src.cli.complete_pipeline specs/example.txt

  # Generate with verbose logging
  python -m src.cli.complete_pipeline specs/example.txt --verbose

  # Use Claude Sonnet for more complex workflows
  python -m src.cli.complete_pipeline specs/example.txt --model claude-3-5-sonnet-20241022

  # Use different provider
  python -m src.cli.complete_pipeline specs/example.txt --provider aimlapi

  # Custom output directory
  python -m src.cli.complete_pipeline specs/example.txt --output-dir ./agents

  # Validate specification only (no code generation)
  python -m src.cli.complete_pipeline specs/example.txt --validate-only

  # Skip saving intermediate JSON
  python -m src.cli.complete_pipeline specs/example.txt --no-json
        """
    )

    parser.add_argument(
        'spec_file',
        type=Path,
        help='Path to text specification file (.txt)'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('generated_agents'),
        help='Output directory (default: generated_agents/)'
    )

    parser.add_argument(
        '--save-json',
        action='store_true',
        default=True,
        help='Save intermediate JSON (default: true)'
    )

    parser.add_argument(
        '--no-json',
        action='store_false',
        dest='save_json',
        help='Skip saving intermediate JSON'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate specification without generating code'
    )

    parser.add_argument(
        '--provider',
        type=str,
        default='claude',
        choices=['claude', 'anthropic', 'aimlapi', 'gemini'],
        help='LLM provider to use (default: claude)'
    )

    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='Model version (default: claude-haiku-4-5 for Claude, auto for others)'
    )

    args = parser.parse_args()

    # Normalize provider name (claude/anthropic are the same)
    if args.provider == 'anthropic':
        args.provider = 'claude'

    # Setup logging
    logger = setup_logging(args.verbose)

    logger.info("Meta-Flow Agent Generator")
    logger.info("=" * 60)

    try:
        # Read specification
        spec_text = read_spec_file(args.spec_file, logger)

        # Phase 1: Meta-agent (text → JSON)
        final_state = run_phase1_meta_agent(
            spec_text,
            llm_provider=args.provider,
            model_version=args.model,
            logger=logger
        )
        workflow_spec = final_state['workflow_spec']

        if args.validate_only:
            logger.info("=" * 60)
            logger.info("VALIDATION ONLY MODE - Stopping here")
            logger.info(f"✓ Specification is valid: {workflow_spec.name}")
            logger.info("=" * 60)
            sys.exit(0)

        # Phase 2: Code generation (JSON → Python)
        python_code = run_phase2_code_generation(workflow_spec, logger)

        # Validate syntax
        output_path = args.output_dir / f"{workflow_spec.name}_agent.py"
        syntax_valid = validate_python_syntax(python_code, output_path, logger)

        if not syntax_valid:
            logger.error("Generated code has syntax errors!")
            sys.exit(1)

        # Save outputs
        outputs = save_outputs(
            workflow_spec,
            python_code,
            args.output_dir,
            args.save_json,
            logger
        )

        # Final summary
        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Workflow: {workflow_spec.name}")
        logger.info(f"Type: {workflow_spec.workflow.type}")
        logger.info(f"Inputs: {len(workflow_spec.inputs)}")
        logger.info(f"Outputs: {len(workflow_spec.outputs)}")
        logger.info(f"Python agent: {outputs['python']}")
        if 'json' in outputs:
            logger.info(f"JSON spec: {outputs['json']}")
        logger.info("=" * 60)

        sys.exit(0)

    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    except RuntimeError as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
