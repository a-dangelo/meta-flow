# Meta-Agent v2: LangGraph Production Implementation

Production-grade meta-agent system using LangGraph for workflow generation from natural language specifications.

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
export AIMLAPI_API_KEY=your_api_key_here
```

### Basic Usage

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from src.agents import run_meta_agent

# Create checkpointer for state persistence
checkpointer = SqliteSaver.from_conn_string(":memory:")

# Define your workflow specification
spec = """
Workflow: customer_lookup
Description: Look up customer information by ID

Inputs:
- customer_id (string): Unique customer identifier

Steps:
1. Fetch customer data from database using customer_id
2. Validate customer data format
3. Return customer profile

Outputs:
- customer_data (object): Customer information
"""

# Run the meta-agent
result = run_meta_agent(
    raw_spec=spec,
    checkpointer=checkpointer
)

# Check results
if result['execution_status'] == 'complete':
    print("✓ Success!")
    print(result['generated_json'])
else:
    print(f"✗ Status: {result['execution_status']}")
    if result.get('validation_errors'):
        for error in result['validation_errors']:
            print(f"  - {error}")
```

## Architecture

### State Machine Flow

```
START → Parser → Reasoner → Validator → Generator → END
          ↓         ↓          ↓           ↓
      [Error]  [Escalate] [Retry]     [Success]
```

### Nodes

1. **Parser** - Deterministic regex extraction of sections
2. **Reasoner** - LLM inference with confidence scoring
3. **Validator** - Pydantic schema validation
4. **Generator** - JSON serialization with round-trip check
5. **Escalation** - Human-in-loop for low confidence cases

## Features

### ✅ Comprehensive Validation
- **Field validators**: Parameter names, types, tool names
- **Model validators**: DAG validation, variable references
- **Credential detection**: Auto-detects api_key, token, password patterns
- **Safe conditions**: Prevents exec, eval, import in conditions

### ✅ Error Recovery
- **Smart retry**: Up to 3 attempts with feedback
- **Confidence scoring**: 0.0-1.0 quality assessment
- **Escalation**: Human review for <0.8 confidence
- **Error tracking**: Full history in state

### ✅ State Management
- **Checkpointing**: SQLite persistence for recovery
- **Execution tracing**: Unique IDs for each run
- **Feedback loop**: Validation errors fed back to LLM

## Models

### WorkflowSpec (Top-level)
```python
{
    "name": "workflow_name",           # Snake_case identifier
    "description": "Description",      # Human-readable
    "version": "1.0.0",               # Semantic version
    "inputs": [WorkflowInput],        # Input parameters
    "outputs": [WorkflowOutput],      # Output parameters
    "workflow": Union[...],           # Root workflow node
    "metadata": {}                    # Additional metadata
}
```

### Workflow Node Types

#### ToolCall
```python
{
    "type": "tool_call",
    "tool_name": "fetch_data",                    # Snake_case
    "parameters": {"id": "{{customer_id}}"},      # Variable refs
    "assigns_to": "customer_data"                 # Output binding
}
```

#### SequentialWorkflow
```python
{
    "type": "sequential",
    "steps": [ToolCall | Conditional | Parallel],
    "description": "Linear workflow"
}
```

#### ConditionalWorkflow
```python
{
    "type": "conditional",
    "condition": "{{amount}} > 1000",             # Safe expression
    "if_branch": Workflow,
    "else_branch": Workflow | None
}
```

#### ParallelWorkflow
```python
{
    "type": "parallel",
    "branches": [Workflow, Workflow, ...],        # 2-10 branches
    "wait_for_all": true
}
```

#### OrchestratorWorkflow
```python
{
    "type": "orchestrator",
    "sub_workflows": {"route_a": Workflow, ...},
    "routing_rules": [
        {"condition": "{{type}} == 'A'", "workflow_name": "route_a"}
    ],
    "default_workflow": "route_a"
}
```

## Validation Rules

### Parameter Names
- Must be snake_case: `[a-z_][a-z0-9_]*`
- Max 64 characters
- Examples: `customer_id`, `api_key`, `total_amount`

### Variable References
- Format: `{{variable_name}}`
- Must reference inputs or previous assigns_to
- Validated at workflow level

### Conditions
- **Allowed operators**: `>`, `<`, `==`, `!=`, `>=`, `<=`, `and`, `or`, `not`, `in`, `is`
- **Forbidden**: `import`, `exec`, `eval`, `__`, `lambda`, `open`, `file`
- **Example**: `{{status}} == 'approved' and {{amount}} < 1000`

### Credentials
Auto-detected patterns:
- `api_key`, `apikey`, `token`, `password`, `secret`
- `database_url`, `db_url`, `connection_string`
- `auth`, `authorization`, `bearer`, `private_key`

## State Fields

### MetaAgentState
```python
{
    # Input/Output
    'raw_spec': str,                   # Original text spec
    'generated_json': str | None,      # Final JSON output

    # Parsing
    'parsed_sections': dict,           # Extracted sections
    'parsing_errors': list[str],       # Parsing issues

    # Reasoning
    'inferred_structure': dict,        # LLM output
    'confidence_score': float,         # 0.0 to 1.0
    'reasoning_trace': list[str],      # LLM thoughts

    # Validation
    'workflow_spec': dict | None,      # Validated spec
    'validation_errors': list[str],    # Schema violations

    # Control
    'execution_status': str,           # Current state
    'retry_count': int,                # Retry attempts
    'should_escalate': bool,           # Need human review

    # Metadata
    'timestamp': str,                  # ISO timestamp
    'execution_id': str,               # Unique UUID
    'model_version': str,              # LLM model
    'prompt_version': str,             # Prompt version

    # Error tracking
    'error_history': list[dict],       # All errors
    'feedback_messages': list[str]     # For retry
}
```

## Advanced Usage

### With Persistent Checkpointing

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# Use file-based SQLite for persistence
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

result = run_meta_agent(
    raw_spec=spec,
    checkpointer=checkpointer,
    config={"configurable": {"thread_id": "workflow-123"}}
)

# Later, resume from checkpoint
# (LangGraph handles this automatically with same thread_id)
```

### Custom Model Selection

```python
result = run_meta_agent(
    raw_spec=spec,
    model_version="claude-sonnet-4-20250514",  # Use Claude instead
    prompt_version="2.0.0"
)
```

### Accessing Individual Nodes

```python
from src.agents import (
    parser_node,
    reasoner_node,
    validator_node,
    create_initial_state
)

# Run parser only
state = create_initial_state(spec)
parsed_state = parser_node(state)

print(parsed_state['parsed_sections'])
```

### Creating Custom Graph

```python
from src.agents.graph import create_meta_agent_graph

# Create graph with custom checkpointer
graph = create_meta_agent_graph(
    checkpointer=checkpointer,
    enable_tracing=True
)

# Run with custom config
result = graph.invoke(
    create_initial_state(spec),
    config={"configurable": {"thread_id": "custom-id"}}
)
```

## Error Handling

### Escalation Scenarios

Execution escalates to human review when:
- Confidence score < 0.8
- Retry limit reached (3 attempts)
- Unrecoverable parsing errors
- Critical validation failures

### Checking Status

```python
result = run_meta_agent(raw_spec=spec, checkpointer=checkpointer)

if result['execution_status'] == 'complete':
    # Success - use generated_json
    workflow = json.loads(result['generated_json'])

elif result['execution_status'] == 'escalated':
    # Needs human review
    print(f"Confidence: {result['confidence_score']:.2f}")
    print(f"Errors: {result['validation_errors']}")

elif result['execution_status'] == 'error':
    # Unrecoverable error
    print(f"Error history: {result['error_history']}")
```

## Testing

```bash
# Run all tests
pytest tests/test_models_v2.py tests/test_meta_agent_v2.py -v

# Run only model tests
pytest tests/test_models_v2.py -v

# Run with coverage
pytest tests/ --cov=src.agents --cov-report=html
```

## Performance

**Typical execution times**:
- Parser: <100ms (deterministic regex)
- Reasoner: 2-4s (LLM API call)
- Validator: <100ms (Pydantic validation)
- Generator: <50ms (JSON serialization)
- **Total**: ~2-5 seconds end-to-end

**Target**: <5s (already achieved)

## Troubleshooting

### "Missing AIMLAPI_API_KEY"
```bash
export AIMLAPI_API_KEY=your_key_here
```

### "Validation failed: undefined variable"
- Check that variable references use `{{var_name}}` syntax
- Ensure variables are defined in inputs or previous assigns_to

### "Unsafe pattern in condition"
- Don't use exec, eval, import in conditions
- Use only comparison operators: >, <, ==, !=, and, or, not

### Low confidence scores
- Add more detail to step descriptions
- Be explicit about input/output relationships
- Use clear, unambiguous language

## Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

result = run_meta_agent(spec, checkpointer)
# Will see detailed logs from each node
```

## Next Steps

- **Add LangSmith tracing** for production observability
- **Expand test suite** to 30+ comprehensive cases
- **Performance profiling** and optimization
- **Multi-agent reasoning** for ambiguity resolution

## License

AGPL-3.0 - See LICENSE file
