"""Quick test script for chatbot end-to-end functionality."""

import asyncio
import sys
from pathlib import Path

# Add both chatbot and parent directory to path for proper imports
chatbot_root = Path(__file__).parent.parent
project_root = chatbot_root.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(chatbot_root))

# Now import from chatbot.src
from chatbot.src.conversation.graph import run_chatbot


async def test_expense_workflow():
    """Test expense approval workflow matching and generation."""
    print("=" * 80)
    print("TEST: Expense Approval Workflow")
    print("=" * 80)

    user_message = "I need to submit an expense report"
    session_id = "test-session-001"

    print(f"\nUser: {user_message}")
    print("\nRunning chatbot pipeline...\n")

    try:
        result = await run_chatbot(
            user_message=user_message,
            session_id=session_id,
            user_id="test-user",
            access_level="employee"
        )

        print("✓ Pipeline completed successfully!\n")
        print(f"Status: {result.get('execution_status')}")
        print(f"Matched Workflow: {result.get('matched_workflow_name')}")
        print(f"Confidence: {result.get('confidence_score', 0):.2%}")

        # Show assistant response
        messages = result.get("messages", [])
        if len(messages) > 1:
            last_message = messages[-1]
            print(f"\nAssistant: {last_message.content}")

        # Show required parameters
        params = result.get("required_parameters", [])
        if params:
            print(f"\nExtracted {len(params)} parameters:")
            for param in params:
                print(f"  • {param.name} ({param.type})")

        # Show generated agent code snippet
        agent_code = result.get("generated_agent_code")
        if agent_code:
            lines = agent_code.split("\n")
            print(f"\nGenerated agent code ({len(lines)} lines)")
            print("First 10 lines:")
            for line in lines[:10]:
                print(f"  {line}")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_leave_workflow():
    """Test leave request workflow matching."""
    print("\n" + "=" * 80)
    print("TEST: Leave Request Workflow")
    print("=" * 80)

    user_message = "I want to request time off"
    session_id = "test-session-002"

    print(f"\nUser: {user_message}")
    print("\nRunning chatbot pipeline...\n")

    try:
        result = await run_chatbot(
            user_message=user_message,
            session_id=session_id,
            user_id="test-user",
            access_level="employee"
        )

        print("✓ Pipeline completed successfully!\n")
        print(f"Status: {result.get('execution_status')}")
        print(f"Matched Workflow: {result.get('matched_workflow_name')}")
        print(f"Confidence: {result.get('confidence_score', 0):.2%}")

        # Show assistant response
        messages = result.get("messages", [])
        if len(messages) > 1:
            last_message = messages[-1]
            print(f"\nAssistant: {last_message.content[:200]}...")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_it_ticket_workflow():
    """Test IT ticket workflow matching."""
    print("\n" + "=" * 80)
    print("TEST: IT Ticket Submission Workflow")
    print("=" * 80)

    user_message = "My laptop is not working, I need tech support"
    session_id = "test-session-003"

    print(f"\nUser: {user_message}")
    print("\nRunning chatbot pipeline...\n")

    try:
        result = await run_chatbot(
            user_message=user_message,
            session_id=session_id,
            user_id="test-user",
            access_level="employee"
        )

        print("✓ Pipeline completed successfully!\n")
        print(f"Status: {result.get('execution_status')}")
        print(f"Matched Workflow: {result.get('matched_workflow_name')}")
        print(f"Confidence: {result.get('confidence_score', 0):.2%}")

        # Show assistant response
        messages = result.get("messages", [])
        if len(messages) > 1:
            last_message = messages[-1]
            print(f"\nAssistant: {last_message.content[:200]}...")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    print("\n🤖 Chatbot End-to-End Test Suite\n")

    await test_expense_workflow()
    await test_leave_workflow()
    await test_it_ticket_workflow()

    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
