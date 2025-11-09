"""Quick test of v2 meta-agent with example spec - with comprehensive logging."""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path to import src module
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from src.agents_v2 import run_meta_agent
from src.agents_v2.test_logger import get_test_logger

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Test meta-agent v2 with a specification file')
parser.add_argument('--spec', type=str, default='specs/examples/simple_sequential.txt',
                    help='Path to specification file (default: specs/examples/simple_sequential.txt)')
parser.add_argument('--provider', type=str, default='aimlapi', choices=['aimlapi', 'gemini'],
                    help='LLM provider to use (default: aimlapi)')
parser.add_argument('--model', type=str, default=None,
                    help='Model name override (optional, reads from AIMLAPI_MODEL or GEMINI_MODEL env vars)')
parser.add_argument('--log-dir', type=str, default='logs',
                    help='Directory for test logs (default: logs/)')
parser.add_argument('--no-log', action='store_true',
                    help='Disable test logging (default: logging enabled)')
args = parser.parse_args()

# Read the specification
try:
    with open(args.spec, 'r') as f:
        spec = f.read()
except FileNotFoundError:
    print(f"Error: Specification file not found: {args.spec}")
    sys.exit(1)

# Determine model
if args.model:
    model = args.model
else:
    model = os.getenv(f"{args.provider.upper()}_MODEL", "default")

print("=" * 60)
print(f"Testing Meta-Agent v2 with: {args.spec}")
print(f"Provider: {args.provider}")
print(f"Model: {model}" + (" (from env var)" if not args.model else ""))
print("=" * 60)
print("\nInput Spec:")
print(spec)
print("\n" + "=" * 60)

# Initialize test logger (if enabled)
test_logger = None
test_id = None

if not args.no_log:
    test_logger = get_test_logger(args.log_dir)

    # Start test run with logging
    test_id = test_logger.start_test_run(
        provider=args.provider,
        model=model,
        input_file_path=args.spec,
        configuration={
            "use_structured_output": True,
            "temperature": 0.05 if args.provider == "gemini" else 0.1
        }
    )

    print(f"\nTest ID: {test_id}")
    print(f"Logs will be saved to: {test_logger.current_run_dir}")
else:
    print("\n[Logging disabled]")

print("=" * 60)

# Run test with comprehensive logging
exit_code = 0
error = None

try:
    # Use checkpointer within context manager to ensure proper lifecycle
    with SqliteSaver.from_conn_string(":memory:") as checkpointer:
        # Log the request (if logging enabled)
        if test_logger:
            test_logger.log_request({
                "provider": args.provider,
                "model": model,
                "raw_spec": spec,
                "configuration": {
                    "use_structured_output": True,
                    "temperature": 0.05 if args.provider == "gemini" else 0.1
                }
            })

        # Capture output during execution (if logging enabled)
        if test_logger:
            with test_logger.capture_output():
                # Run meta-agent
                result = run_meta_agent(
                    raw_spec=spec,
                    checkpointer=checkpointer,
                    llm_provider=args.provider,
                    model_version=args.model
                )
        else:
            # Run without output capture
            result = run_meta_agent(
                raw_spec=spec,
                checkpointer=checkpointer,
                llm_provider=args.provider,
                model_version=args.model
            )

    # Log the response (if logging enabled)
    if test_logger:
        if result.get('inferred_structure'):
            test_logger.log_response(result['inferred_structure'], is_json=True)

        # Log validation errors if any
        if result.get('validation_errors'):
            test_logger.log_validation_errors(result['validation_errors'])

        # Log final state
        test_logger.log_state(result)

    # Display results
    print("\nExecution Status:", result['execution_status'])
    print("Confidence Score:", result.get('confidence_score', 'N/A'))
    print("Retry Count:", result.get('retry_count', 0))

    if result.get('parsing_errors'):
        print("\nParsing Errors:")
        for error in result['parsing_errors']:
            print(f"  - {error}")

    if result.get('validation_errors'):
        print("\nValidation Errors:")
        for error in result['validation_errors']:
            print(f"  - {error}")

    if result['execution_status'] == 'complete':
        print("\n" + "=" * 60)
        print("✓ SUCCESS - Generated JSON:")
        print("=" * 60)
        print(result['generated_json'])
        if test_logger:
            test_logger.end_test_run(exit_status="success", exit_code=0)
    elif result['execution_status'] == 'escalated':
        print("\n⚠ ESCALATED - Needs human review")
        print(f"Reason: Confidence {result.get('confidence_score', 0):.2f} < 0.8")
        if test_logger:
            test_logger.end_test_run(exit_status="failure", exit_code=1)
        exit_code = 1
    else:
        print(f"\n✗ FAILED - Status: {result['execution_status']}")
        if test_logger:
            test_logger.end_test_run(exit_status="failure", exit_code=1)
        exit_code = 1

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    if test_logger:
        test_logger.end_test_run(exit_status="error", exit_code=2, error=e)
    exit_code = 2
    error = e

# Print summary stats (if logging enabled)
if test_logger:
    print("\n" + "=" * 60)
    print("Test Run Complete")
    print("=" * 60)
    stats = test_logger.get_summary_stats()
    print(f"Total runs: {stats['total_runs']}")
    print(f"Success rate: {stats['success_count']}/{stats['total_runs']}")
    if stats.get('avg_execution_time_ms'):
        print(f"Average execution time: {stats['avg_execution_time_ms']}ms")

sys.exit(exit_code)
