"""
End-to-end tests for meta-agent v2 with LangGraph.

Tests the complete pipeline:
    Parser → Reasoner → Validator → Generator
"""

import pytest
import os
from langgraph.checkpoint.sqlite import SqliteSaver

from src.agents_v2 import (
    run_meta_agent,
    create_meta_agent_graph,
    parser_node,
    MetaAgentState,
    create_initial_state,
)


# ===== Test Specifications =====

SIMPLE_SPEC = """Workflow: customer_lookup
Description: Look up customer information by ID

Inputs:
- customer_id (string): Unique customer identifier
- database_url (string): Database connection string

Steps:
1. Fetch customer data from database using customer_id
2. Validate customer data format
3. Extract customer email and name
4. Format response as JSON

Outputs:
- customer_info (object): Customer information object
"""


CONDITIONAL_SPEC = """Workflow: expense_approval
Description: Approve or reject expense based on amount

Inputs:
- expense_amount (number): Expense amount in dollars
- expense_type (string): Type of expense

Steps:
1. Validate expense amount is positive
2. If expense_amount > 1000, then escalate to manager
3. Otherwise, auto-approve expense
4. Send notification email

Outputs:
- approval_status (string): Approved or rejected
- notification_sent (boolean): Whether notification was sent
"""


# ===== Unit Tests for Individual Nodes =====

def test_parser_node_valid_spec():
    """Test parser node with valid specification."""
    state = create_initial_state(SIMPLE_SPEC)
    result = parser_node(state)

    assert result['execution_status'] == 'reasoning'
    assert len(result['parsing_errors']) == 0
    assert result['parsed_sections']['workflow'] == 'customer_lookup'
    assert result['parsed_sections']['description'] == 'Look up customer information by ID'
    assert len(result['parsed_sections']['inputs']) == 2
    assert len(result['parsed_sections']['steps']) == 4
    assert len(result['parsed_sections']['outputs']) == 1


def test_parser_node_missing_sections():
    """Test parser node with missing sections."""
    incomplete_spec = """Workflow: test
Description: Test workflow

Inputs:
- x (int): Test input
"""
    # Missing Steps and Outputs sections

    state = create_initial_state(incomplete_spec)
    result = parser_node(state)

    assert result['execution_status'] == 'error'
    assert len(result['parsing_errors']) > 0
    assert any('Steps' in error for error in result['parsing_errors'])


def test_parser_extracts_numbered_steps():
    """Test that parser correctly extracts numbered steps."""
    state = create_initial_state(SIMPLE_SPEC)
    result = parser_node(state)

    steps = result['parsed_sections']['steps']
    assert len(steps) == 4
    assert steps[0] == 'Fetch customer data from database using customer_id'
    assert steps[1] == 'Validate customer data format'
    assert steps[2] == 'Extract customer email and name'
    assert steps[3] == 'Format response as JSON'


# ===== Integration Tests =====

@pytest.mark.skipif(
    not os.getenv('AIMLAPI_API_KEY'),
    reason="AIMLAPI_API_KEY not set"
)
def test_end_to_end_simple_workflow():
    """Test complete pipeline with simple sequential workflow."""
    # Create checkpointer (in-memory)
    checkpointer = SqliteSaver.from_conn_string(":memory:")

    # Run meta-agent
    result = run_meta_agent(
        raw_spec=SIMPLE_SPEC,
        checkpointer=checkpointer
    )

    # Check final state
    assert result['execution_status'] == 'complete'
    assert result['generated_json'] is not None
    assert len(result['validation_errors']) == 0

    # Verify JSON contains expected fields
    import json
    workflow = json.loads(result['generated_json'])
    assert workflow['name'] == 'customer_lookup'
    assert workflow['description'] == 'Look up customer information by ID'
    assert len(workflow['inputs']) == 2
    assert len(workflow['outputs']) == 1


@pytest.mark.skipif(
    not os.getenv('AIMLAPI_API_KEY'),
    reason="AIMLAPI_API_KEY not set"
)
def test_end_to_end_conditional_workflow():
    """Test complete pipeline with conditional workflow."""
    checkpointer = SqliteSaver.from_conn_string(":memory:")

    result = run_meta_agent(
        raw_spec=CONDITIONAL_SPEC,
        checkpointer=checkpointer
    )

    # Check final state
    assert result['execution_status'] in ['complete', 'escalated']

    if result['execution_status'] == 'complete':
        # Verify generated JSON
        import json
        workflow = json.loads(result['generated_json'])
        assert workflow['name'] == 'expense_approval'
        assert 'workflow' in workflow


def test_graph_structure():
    """Test that LangGraph graph is properly constructed."""
    graph = create_meta_agent_graph()

    # Graph should be compiled
    assert graph is not None

    # Should have entry point
    # Note: LangGraph doesn't expose internal structure easily,
    # so we just verify it compiled without errors


def test_checkpointing():
    """Test that checkpointing works."""
    checkpointer = SqliteSaver.from_conn_string(":memory:")

    # Create graph with checkpointing
    graph = create_meta_agent_graph(checkpointer=checkpointer)
    assert graph is not None


def test_retry_logic_with_validation_errors():
    """Test that validation errors trigger retry."""
    # This would require mocking the LLM to return invalid JSON,
    # which is complex. For now, we verify the logic exists.
    from src.agents_v2.state import should_retry

    # State with validation errors, low retry count
    state = {
        'execution_status': 'error',
        'validation_errors': ['field: error'],
        'retry_count': 0,
        'should_escalate': False
    }
    assert should_retry(state) is True

    # State with retry limit reached
    state['retry_count'] = 3
    assert should_retry(state) is False

    # State marked for escalation
    state['retry_count'] = 0
    state['should_escalate'] = True
    assert should_retry(state) is False


def test_confidence_scoring():
    """Test confidence score calculation."""
    from src.agents_v2.nodes import _calculate_confidence

    # Complete structure
    complete = {
        'name': 'test',
        'description': 'Test workflow',
        'workflow': {
            'type': 'sequential',
            'steps': [
                {'type': 'tool_call', 'tool_name': 'test'}
            ]
        }
    }
    sections = {'steps': ['Step 1']}
    confidence = _calculate_confidence(complete, sections)
    assert confidence == 1.0

    # Missing name
    incomplete = {
        'description': 'Test',
        'workflow': {'type': 'sequential', 'steps': []}
    }
    confidence = _calculate_confidence(incomplete, sections)
    assert confidence < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
