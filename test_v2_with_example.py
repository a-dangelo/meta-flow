"""Quick test of v2 meta-agent with example spec."""

import os
import sys
import argparse
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from src.agents_v2 import run_meta_agent

# Load environment variables from .env file
load_dotenv()

# Parse command line arguments
parser = argparse.ArgumentParser(description='Test meta-agent v2 with a specification file')
parser.add_argument('--spec', type=str, default='specs/examples/simple_sequential.txt',
                    help='Path to specification file (default: specs/examples/simple_sequential.txt)')
args = parser.parse_args()

# Read the specification
try:
    with open(args.spec, 'r') as f:
        spec = f.read()
except FileNotFoundError:
    print(f"Error: Specification file not found: {args.spec}")
    sys.exit(1)

print("=" * 60)
print(f"Testing Meta-Agent v2 with: {args.spec}")
print("=" * 60)
print("\nInput Spec:")
print(spec)
print("\n" + "=" * 60)

# Use checkpointer within context manager to ensure proper lifecycle
with SqliteSaver.from_conn_string(":memory:") as checkpointer:
    # Run meta-agent
    result = run_meta_agent(
        raw_spec=spec,
        checkpointer=checkpointer
    )

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
elif result['execution_status'] == 'escalated':
    print("\n⚠ ESCALATED - Needs human review")
    print(f"Reason: Confidence {result.get('confidence_score', 0):.2f} < 0.8")
else:
    print(f"\n✗ FAILED - Status: {result['execution_status']}")
