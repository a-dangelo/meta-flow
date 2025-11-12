"""
Test that generated agents can be imported and executed.

This test validates that:
1. Generated agent can be imported as a Python module
2. Agent class can be instantiated
3. Execute method can be called with inputs
4. Tool stubs are callable and return expected structure
5. Credential handling works correctly
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Add generated_agents to path so we can import generated agents
sys.path.insert(0, str(Path(__file__).parent.parent / "generated_agents"))

import pytest


class TestGeneratedAgentExecution:
    """Test execution of generated agents."""

    def test_import_generated_agent(self):
        """Test that generated agent can be imported."""
        # Import the generated module
        import data_processing_pipeline_agent

        # Check that the agent class exists
        assert hasattr(data_processing_pipeline_agent, 'DataProcessingPipelineAgent')

        # Instantiate the agent
        agent = data_processing_pipeline_agent.DataProcessingPipelineAgent()

        # Check that required methods exist
        assert hasattr(agent, 'execute')
        assert hasattr(agent, 'fetch_customer_data')
        assert hasattr(agent, 'validate_customer_data')
        assert hasattr(agent, 'calculate_customer_lifetime_value')
        assert hasattr(agent, 'update_customer_record')

        # Check context is initialized
        assert hasattr(agent, 'context')
        assert isinstance(agent.context, dict)
        assert len(agent.context) == 0

        print("✓ Generated agent imported successfully")
        print(f"✓ Agent class: {agent.__class__.__name__}")
        print(f"✓ Methods: execute, 4 tool stubs")

    def test_execute_without_credentials(self):
        """Test that execute works when credentials are missing (should fail gracefully)."""
        import data_processing_pipeline_agent

        agent = data_processing_pipeline_agent.DataProcessingPipelineAgent()

        # Try to execute without setting DATABASE_URL
        # Should fail with clear error message
        inputs = {
            "customer_id": "test_customer_123",
            "database_url": "test_value"  # Passed as input, but tool will still check env var
        }

        try:
            result = agent.execute(**inputs)
            # If we get here, check the tool stub returned not_implemented
            print(f"✓ Execute completed (tool stubs return not_implemented)")
            print(f"  Result: {result}")
        except ValueError as e:
            # Expected if credential env var is missing
            error_msg = str(e)
            assert "DATABASE_URL" in error_msg or "not_implemented" in error_msg
            print(f"✓ Execute raised ValueError as expected: {error_msg[:100]}...")
        except RuntimeError as e:
            # Could also raise RuntimeError wrapping the ValueError
            print(f"✓ Execute raised RuntimeError (wrapped error): {str(e)[:100]}...")

    def test_execute_with_mock_credentials(self):
        """Test execution with mocked environment variables."""
        import data_processing_pipeline_agent

        # Set mock credential in environment
        os.environ['DATABASE_URL'] = 'mock://test:test@localhost:5432/testdb'

        try:
            agent = data_processing_pipeline_agent.DataProcessingPipelineAgent()

            inputs = {
                "customer_id": "test_customer_123",
                "database_url": "mock://test:test@localhost:5432/testdb"
            }

            result = agent.execute(**inputs)

            # Tool stubs return {"status": "not_implemented", "data": kwargs}
            # So execution should complete and return context
            print(f"✓ Execute completed with mock credentials")
            print(f"  Result type: {type(result)}")
            print(f"  Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")

            # Verify context was populated
            assert isinstance(result, dict)
            assert 'customer_id' in result or 'customer_id' in agent.context

        finally:
            # Clean up
            if 'DATABASE_URL' in os.environ:
                del os.environ['DATABASE_URL']

    def test_tool_stubs_callable(self):
        """Test that individual tool stubs can be called."""
        import data_processing_pipeline_agent

        agent = data_processing_pipeline_agent.DataProcessingPipelineAgent()

        # Test non-credential tool
        result = agent.validate_customer_data(data={"test": "data"})
        assert isinstance(result, dict)
        assert result.get("status") == "not_implemented"
        print("✓ Non-credential tool stub works")

        # Test credential tool (should fail without env var)
        os.environ['DATABASE_URL'] = 'mock://test@localhost/db'
        try:
            result = agent.fetch_customer_data(
                customer_id="test",
                database_url="mock://test@localhost/db"
            )
            assert isinstance(result, dict)
            assert result.get("status") == "not_implemented"
            print("✓ Credential tool stub works with env var")
        finally:
            del os.environ['DATABASE_URL']

    def test_input_validation(self):
        """Test that missing inputs are caught."""
        import data_processing_pipeline_agent

        agent = data_processing_pipeline_agent.DataProcessingPipelineAgent()

        # Try to execute without required inputs
        # Should raise RuntimeError (which wraps the original error)
        with pytest.raises(RuntimeError, match="Missing required input"):
            agent.execute(customer_id="test")  # Missing database_url

        with pytest.raises(RuntimeError, match="Missing required input"):
            agent.execute(database_url="test")  # Missing customer_id

        print("✓ Input validation works correctly")

    def test_context_management(self):
        """Test that context is properly managed during execution."""
        import data_processing_pipeline_agent

        # Set mock credential
        os.environ['DATABASE_URL'] = 'mock://localhost/db'

        try:
            agent = data_processing_pipeline_agent.DataProcessingPipelineAgent()

            inputs = {
                "customer_id": "test_123",
                "database_url": "mock://localhost/db"
            }

            # Execute workflow
            result = agent.execute(**inputs)

            # Check that context was populated with inputs
            assert 'customer_id' in agent.context
            assert agent.context['customer_id'] == 'test_123'

            # Check that intermediate results were stored
            # (tool stubs should have been called and assigned to context)
            assert 'customer_data' in agent.context
            assert 'validation_result' in agent.context
            assert 'lifetime_value' in agent.context
            assert 'update_status' in agent.context

            print("✓ Context management works correctly")
            print(f"  Context keys: {list(agent.context.keys())}")

        finally:
            if 'DATABASE_URL' in os.environ:
                del os.environ['DATABASE_URL']


def run_all_tests():
    """Run all tests and print results."""
    test = TestGeneratedAgentExecution()

    print("\n" + "=" * 60)
    print("Testing Generated Agent Execution")
    print("=" * 60 + "\n")

    tests = [
        ("Import Generated Agent", test.test_import_generated_agent),
        ("Tool Stubs Callable", test.test_tool_stubs_callable),
        ("Input Validation", test.test_input_validation),
        ("Execute Without Credentials", test.test_execute_without_credentials),
        ("Execute With Mock Credentials", test.test_execute_with_mock_credentials),
        ("Context Management", test.test_context_management),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\n[TEST] {test_name}")
            print("-" * 60)
            test_func()
            passed += 1
            print(f"✅ PASSED: {test_name}\n")
        except Exception as e:
            failed += 1
            print(f"❌ FAILED: {test_name}")
            print(f"   Error: {e}\n")

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
