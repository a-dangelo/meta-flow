"""Test LLM-powered conversational chatbot."""

import asyncio
import sys
from pathlib import Path

# Add chatbot to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from chatbot.src.conversation.graph_v2 import run_conversational_chatbot


async def test_expense_conversation():
    """Test multi-turn conversation for expense approval."""
    print("=" * 80)
    print("TEST: Conversational Expense Approval")
    print("=" * 80)

    session_id = "test-conv-001"
    conversation_history = []

    # Turn 1: User initiates
    print("\nUser: I need to submit an expense report")
    result = await run_conversational_chatbot(
        user_message="I need to submit an expense report",
        session_id=session_id,
        conversation_history=conversation_history
    )

    # Get agent response
    messages = result["messages"]
    last_message = messages[-1]
    print(f"\nAgent: {last_message.content}")

    # Update conversation history
    conversation_history = messages

    print("\n" + "=" * 80)
    print("Conversation State:")
    print(f"  Messages: {len(conversation_history)}")
    print(f"  Workflow: {result.get('workflow_in_progress')}")
    print("=" * 80)

    # Turn 2: User provides parameters
    print("\nUser: The amount is $450, date is 2025-11-21, category is meals, "
          "department is Engineering, receipt is https://example.com/receipt.jpg, "
          "and my employee ID is EMP123")

    result = await run_conversational_chatbot(
        user_message="The amount is $450, date is 2025-11-21, category is meals, "
                    "department is Engineering, receipt is https://example.com/receipt.jpg, "
                    "and my employee ID is EMP123",
        session_id=session_id,
        conversation_history=conversation_history
    )

    messages = result["messages"]
    last_message = messages[-1]
    print(f"\nAgent: {last_message.content}")

    print("\n✓ Conversation test completed")


async def test_simple_query():
    """Test simple workflow query."""
    print("\n" + "=" * 80)
    print("TEST: Simple Query")
    print("=" * 80)

    session_id = "test-simple-001"

    print("\nUser: What workflows can I use?")
    result = await run_conversational_chatbot(
        user_message="What workflows can I use?",
        session_id=session_id
    )

    messages = result["messages"]
    last_message = messages[-1]
    print(f"\nAgent: {last_message.content[:500]}...")

    print("\n✓ Simple query test completed")


async def main():
    """Run all conversational tests."""
    print("\n🤖 LLM-Powered Conversational Chatbot Test Suite\n")

    try:
        await test_expense_conversation()
        await test_simple_query()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("All conversational tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
