"""
Manual test script for chatbot API endpoints.

Tests REST endpoints and provides examples for WebSocket testing.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timezone


BASE_URL = "http://localhost:8000"


async def test_health():
    """Test health endpoint."""
    print("\n" + "=" * 80)
    print("TEST: Health Check")
    print("=" * 80)

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/health") as response:
            print(f"Status: {response.status}")
            data = await response.json()
            print(f"Response: {json.dumps(data, indent=2)}")

            assert response.status == 200
            assert data["status"] in ["healthy", "degraded"]

    print("✓ Health check passed")


async def test_list_workflows():
    """Test workflow listing."""
    print("\n" + "=" * 80)
    print("TEST: List Workflows")
    print("=" * 80)

    async with aiohttp.ClientSession() as session:
        # Test with employee access
        async with session.get(
            f"{BASE_URL}/workflows/list",
            params={"access_level": "employee"}
        ) as response:
            print(f"Status: {response.status}")
            data = await response.json()
            print(f"Found {data['total']} workflows")

            for wf in data.get("workflows", []):
                print(f"  - {wf['name']}: {wf['description']}")

            assert response.status == 200
            assert data["total"] >= 0

    print("✓ Workflow listing passed")


async def test_get_workflow():
    """Test getting specific workflow."""
    print("\n" + "=" * 80)
    print("TEST: Get Workflow Details")
    print("=" * 80)

    workflow_name = "expense_approval"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/workflows/{workflow_name}",
            params={"access_level": "employee"}
        ) as response:
            print(f"Status: {response.status}")

            if response.status == 200:
                data = await response.json()
                print(f"Workflow: {data['name']}")
                print(f"Category: {data['category']}")
                print(f"Description: {data['description']}")
                print(f"Spec length: {len(data.get('specification', ''))} chars")

                assert "specification" in data
            else:
                print(f"Workflow not found (expected if no workflows loaded)")

    print("✓ Get workflow passed")


async def test_chat_flow():
    """Test complete chat flow."""
    print("\n" + "=" * 80)
    print("TEST: Chat Flow")
    print("=" * 80)

    session_id = f"test-{datetime.now(timezone.utc).timestamp()}"

    async with aiohttp.ClientSession() as session:
        # Turn 1: Send initial message
        print("\n[Turn 1] Sending: 'I need to submit an expense report'")

        payload = {
            "session_id": session_id,
            "message": "I need to submit an expense report",
            "user_id": "test-user",
            "access_level": "employee"
        }

        async with session.post(
            f"{BASE_URL}/chat/message",
            json=payload
        ) as response:
            print(f"Status: {response.status}")
            data = await response.json()

            print(f"Status: {data['status']}")
            print(f"Workflow: {data.get('matched_workflow')}")
            print(f"Confidence: {data.get('search_confidence', 0):.2%}")

            if data.get("error_message"):
                print(f"ERROR: {data['error_message']}")

            if data.get("message"):
                print(f"Agent: {data['message'][:200]}...")

            # Check parameters
            if data.get("required_parameters"):
                print(f"\nRequired parameters:")
                for param in data["required_parameters"]:
                    print(f"  - {param['name']} ({param['type']})")

        # Turn 2: Provide parameters
        if data.get("required_parameters"):
            print("\n[Turn 2] Providing parameters")

            payload = {
                "session_id": session_id,
                "message": "Amount is $450, date is 2025-11-21, category is meals, department is Engineering, receipt_url is https://example.com/receipt.pdf, employee_id is EMP123",
                "user_id": "test-user",
                "access_level": "employee"
            }

            async with session.post(
                f"{BASE_URL}/chat/message",
                json=payload
            ) as response:
                print(f"Status: {response.status}")
                data = await response.json()

                print(f"Status: {data['status']}")

                if data.get("collected_parameters"):
                    print(f"Collected parameters:")
                    for key, value in data["collected_parameters"].items():
                        print(f"  - {key}: {value}")

                if data.get("execution_result"):
                    print(f"\nExecution completed:")
                    result = data["execution_result"]
                    print(f"  Reference: {result.get('reference_id')}")
                    print(f"  Status: {result.get('status')}")

        # Get session state
        print("\n[Get Session State]")
        async with session.get(f"{BASE_URL}/chat/session/{session_id}") as response:
            print(f"Status: {response.status}")
            data = await response.json()

            print(f"Session: {data['session_id']}")
            print(f"Status: {data['status']}")
            print(f"Messages: {data['message_count']}")

        # Clean up session
        print("\n[Delete Session]")
        async with session.delete(f"{BASE_URL}/chat/session/{session_id}") as response:
            print(f"Status: {response.status}")
            data = await response.json()
            print(f"Deleted: {data.get('success')}")

    print("\n✓ Chat flow test completed")


async def test_websocket():
    """Test WebSocket connection (example)."""
    print("\n" + "=" * 80)
    print("TEST: WebSocket (Manual)")
    print("=" * 80)

    print("WebSocket URL: ws://localhost:8000/ws/chat/{session_id}")
    print("\nTo test WebSocket, use a WebSocket client like wscat:")
    print("  npm install -g wscat")
    print("  wscat -c ws://localhost:8000/ws/chat/test-session")
    print("\nOr use the browser console:")
    print("  const ws = new WebSocket('ws://localhost:8000/ws/chat/test-session');")
    print("  ws.onmessage = (event) => console.log(JSON.parse(event.data));")
    print("  ws.send(JSON.stringify({type: 'ping'}));")

    print("\n✓ WebSocket info provided")


async def main():
    """Run all API tests."""
    print("\n🚀 Chatbot API Test Suite\n")

    try:
        await test_health()
        await test_list_workflows()
        await test_get_workflow()
        await test_chat_flow()
        await test_websocket()

    except aiohttp.ClientError as e:
        print(f"\n✗ Connection error: {e}")
        print("\nMake sure the API server is running:")
        print("  cd /workspaces/meta-flow")
        print("  python -m chatbot.api.main")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("API tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
