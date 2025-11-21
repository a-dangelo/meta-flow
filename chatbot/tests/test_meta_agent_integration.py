"""Direct test of meta-agent integration."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from chatbot.src.integration.meta_agent_client import MetaAgentClient

# Load environment variables
load_dotenv()


async def test_direct():
    """Test meta-agent directly without API."""

    # Load simple workflow spec
    spec_path = Path("chatbot/workflows/test/simple_test.txt")
    spec_content = spec_path.read_text()

    print("=" * 80)
    print("Testing Meta-Agent Integration Directly")
    print("=" * 80)
    print(f"\nSpec file: {spec_path}")
    print(f"Spec content:\n{spec_content[:200]}...\n")

    # Create client
    client = MetaAgentClient()

    try:
        print("Calling meta-agent...")
        json_ast, python_code = await client.generate_agent_from_spec(
            spec_content,
            provider="claude"
        )

        print("\n✓ SUCCESS!")
        print(f"\nJSON AST keys: {list(json_ast.keys())}")
        print(f"Python code length: {len(python_code)} characters")
        print(f"\nFirst 500 chars of generated code:")
        print(python_code[:500])

    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_direct())
