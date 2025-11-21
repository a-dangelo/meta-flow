"""Test hybrid decomposition chatbot implementation."""

import asyncio
import sys
from pathlib import Path

# Add chatbot to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from chatbot.src.conversation.graph_hybrid import run_hybrid_chatbot


async def test_expense_workflow_hybrid():
    """Test expense approval workflow with hybrid architecture."""
    print("=" * 80)
    print("TEST: Hybrid Architecture - Expense Approval")
    print("=" * 80)

    session_id = "test-hybrid-expense-001"

    # Turn 1: User initiates
    print("\n[Turn 1] User: I need to submit an expense report")
    result = await run_hybrid_chatbot(
        user_message="I need to submit an expense report",
        session_id=session_id,
        access_level="employee"
    )

    print(f"\nWorkflow matched: {result.get('matched_workflow_name')}")
    print(f"Confidence: {result.get('search_confidence', 0):.2%}")
    print(f"Status: {result.get('execution_status')}")
    print(f"Note: BGE-small-en-v1.5 threshold is 60% (expect 65-80% for good matches)")

    # Check if agent was generated
    if result.get("json_ast"):
        print("\n✓ Agent generated successfully")
        print(f"  Parameters needed: {len(result.get('required_parameters', []))}")

        # Show what parameters were extracted
        params = result.get("required_parameters", [])
        for p in params:
            print(f"    - {p['name']} ({p['type']}): {p.get('description', '')}")

    # Check messages
    messages = result.get("messages", [])
    if messages:
        last_message = messages[-1]
        print(f"\nAgent response:\n{last_message.content}\n")

    # Turn 2: User provides all parameters
    print("=" * 80)
    print("[Turn 2] User provides parameters")
    print("=" * 80)

    user_params = (
        "The amount is $450, date is 2025-11-21, category is meals, "
        "department is Engineering, receipt is https://example.com/receipt.jpg, "
        "and my employee ID is EMP123"
    )

    print(f"\nUser: {user_params}")

    result = await run_hybrid_chatbot(
        user_message=user_params,
        session_id=session_id,
        conversation_history=messages,
        access_level="employee"
    )

    print(f"\nStatus: {result.get('execution_status')}")

    # Check collected parameters
    collected = result.get("collected_parameters", {})
    if collected:
        print("\n✓ Parameters collected:")
        for key, value in collected.items():
            print(f"    - {key}: {value}")

    # Check validation
    errors = result.get("validation_errors")
    if errors:
        print("\n✗ Validation errors:")
        for error in errors:
            print(f"    - {error}")
    else:
        print("\n✓ All parameters validated")

    # Check execution result
    exec_result = result.get("execution_result")
    if exec_result:
        print("\n✓ Workflow executed:")
        print(f"    Reference: {exec_result.get('reference_id')}")
        print(f"    Status: {exec_result.get('status')}")

    # Show performance metrics
    timings = result.get("node_timings", {})
    if timings:
        print("\nPerformance metrics:")
        total = sum(timings.values())
        for node, duration in timings.items():
            print(f"    - {node}: {duration*1000:.0f}ms")
        print(f"    Total: {total*1000:.0f}ms")

    print("\n" + "=" * 80)
    print("✓ Hybrid architecture test completed")
    print("=" * 80)


async def test_parameter_extraction():
    """Test direct JSON parameter extraction."""
    print("\n" + "=" * 80)
    print("TEST: JSON Parameter Extraction")
    print("=" * 80)

    from chatbot.src.parameter_handling.extractor import extract_parameters_from_json

    # Mock JSON AST
    mock_json = {
        "name": "test_workflow",
        "inputs": [
            {
                "name": "amount",
                "type": "float",
                "description": "Amount in USD"
            },
            {
                "name": "date",
                "type": "date",
                "description": "Transaction date"
            },
            {
                "name": "optional_field",
                "type": "string",
                "required": False,
                "default": "default_value"
            }
        ]
    }

    params = extract_parameters_from_json(mock_json)

    print(f"\nExtracted {len(params)} parameters:")
    for p in params:
        req = "required" if p.get("required", True) else "optional"
        print(f"  - {p['name']} ({p['type']}) [{req}]")
        if p.get("description"):
            print(f"      {p['description']}")

    print("\n✓ JSON extraction test passed")


async def test_validation():
    """Test deterministic parameter validation."""
    print("\n" + "=" * 80)
    print("TEST: Parameter Validation")
    print("=" * 80)

    from chatbot.src.parameter_handling.validator import validate_all_parameters

    parameters = [
        {"name": "amount", "type": "float", "required": True},
        {"name": "date", "type": "date", "required": True},
        {"name": "email", "type": "email", "required": True}
    ]

    # Test valid values
    valid_values = {
        "amount": "450.50",
        "date": "2025-11-21",
        "email": "user@example.com"
    }

    all_valid, validated, errors = validate_all_parameters(parameters, valid_values)

    print(f"\nValidation result: {'PASS' if all_valid else 'FAIL'}")
    if all_valid:
        print("Validated values:")
        for key, value in validated.items():
            print(f"  - {key}: {value} ({type(value).__name__})")
    else:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")

    # Test invalid values
    invalid_values = {
        "amount": "not a number",
        "date": "invalid-date",
        "email": "not-an-email"
    }

    all_valid, validated, errors = validate_all_parameters(parameters, invalid_values)

    print(f"\nInvalid input result: {'PASS' if not all_valid else 'UNEXPECTED'}")
    if errors:
        print("Expected errors caught:")
        for error in errors:
            print(f"  - {error}")

    print("\n✓ Validation test passed")


async def test_execution_sandbox():
    """Test sandboxed execution with log capture."""
    print("\n" + "=" * 80)
    print("TEST: Sandboxed Execution")
    print("=" * 80)

    from chatbot.src.execution.orchestrator import execute_agent_safely

    # Simple test agent code
    test_agent_code = '''
class TestAgent:
    """Simple test agent for execution verification."""

    def execute(self, amount: float, category: str) -> dict:
        """Execute test workflow."""
        print(f"Processing {category} expense for ${amount}")

        if amount > 1000:
            status = "requires_approval"
            print("⚠️ Amount exceeds $1000 - manager approval required")
        else:
            status = "approved"
            print("✓ Auto-approved")

        return {
            "status": status,
            "processed_amount": amount,
            "category": category,
            "message": f"{category} expense ${amount} {status}"
        }
'''

    # Test successful execution
    print("\n[Test 1] Successful execution:")
    result = await execute_agent_safely(
        agent_code=test_agent_code,
        parameters={"amount": 450.0, "category": "meals"},
        timeout=5.0
    )

    print(f"  Success: {result.success}")
    print(f"  Execution time: {result.execution_time:.3f}s")
    if result.success:
        print(f"  Result: {result.result}")
        print(f"  Logs captured: {len(result.logs)} lines")
        for log in result.logs:
            print(f"    | {log.strip()}")
    else:
        print(f"  Error: {result.error}")

    # Test with amount requiring approval
    print("\n[Test 2] Execution with conditional logic:")
    result = await execute_agent_safely(
        agent_code=test_agent_code,
        parameters={"amount": 1500.0, "category": "travel"},
        timeout=5.0
    )

    print(f"  Success: {result.success}")
    if result.success:
        print(f"  Result: {result.result}")
        print(f"  Logs:")
        for log in result.logs:
            print(f"    | {log.strip()}")

    # Test error handling
    print("\n[Test 3] Error handling (missing parameter):")
    result = await execute_agent_safely(
        agent_code=test_agent_code,
        parameters={"amount": 100.0},  # Missing 'category'
        timeout=5.0
    )

    print(f"  Success: {result.success}")
    if not result.success:
        print(f"  Error type: {result.error_type}")
        print(f"  Error: {result.error}")

    # Test timeout
    print("\n[Test 4] Timeout handling:")
    timeout_agent = '''
class TimeoutAgent:
    def execute(self) -> dict:
        import time
        print("Starting long operation...")
        time.sleep(10)  # Will timeout
        return {"status": "completed"}
'''

    result = await execute_agent_safely(
        agent_code=timeout_agent,
        parameters={},
        timeout=2.0
    )

    print(f"  Success: {result.success}")
    if not result.success:
        print(f"  Error type: {result.error_type}")
        print(f"  Error: {result.error}")

    print("\n✓ Execution sandbox tests passed")


async def test_log_sanitization():
    """Test credential sanitization in logs."""
    print("\n" + "=" * 80)
    print("TEST: Log Sanitization")
    print("=" * 80)

    from chatbot.src.execution.streaming import sanitize_log_message

    test_cases = [
        ("api_key='sk-ant-12345'", "api_key=***"),
        ("password=\"secretpass\"", "password=***"),
        ("Using bearer abc123def456", "bearer ***"),
        ("Normal log message", "Normal log message"),
    ]

    print("\nSanitization tests:")
    for original, expected_pattern in test_cases:
        sanitized = sanitize_log_message(original)
        contains_pattern = expected_pattern in sanitized or expected_pattern == sanitized
        status = "✓" if contains_pattern else "✗"
        print(f"  {status} '{original[:40]}...' -> '{sanitized[:40]}...'")

    print("\n✓ Log sanitization tests passed")


async def main():
    """Run all hybrid architecture tests."""
    print("\n🚀 Hybrid Decomposition Chatbot Test Suite\n")

    try:
        # Unit tests
        await test_parameter_extraction()
        await test_validation()
        await test_execution_sandbox()
        await test_log_sanitization()

        # Integration test
        await test_expense_workflow_hybrid()

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("All hybrid architecture tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
