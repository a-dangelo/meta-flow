# Meta-Flow Chatbot Automation Layer

Enterprise chatbot automation platform that transforms natural language requests into executable workflow agents.

## Overview

The chatbot layer sits on top of the existing meta-flow infrastructure, providing conversational orchestration for internal business processes. Employees interact naturally with the system: "I need to submit an expense report" → chatbot generates and executes the appropriate workflow agent.

## Architecture

```
Employee → Chatbot Interface → Intent Matcher → Workflow Repository
                                        ↓
                                Meta-Agent Pipeline (existing)
                                        ↓
                         Parameter Extraction → Collection → Execution
                                        ↓
                            Results → Employee Notification
```

## Key Components

### 1. Conversation Management (`src/conversation/`)
- LangGraph-based state machine for conversation flow
- State tracking across multiple turns
- Session management and persistence

### 2. Workflow Matching (`src/workflow_matching/`)
- Semantic search using sentence-transformers
- Intent classification and confidence scoring
- Workflow repository interface

### 3. Parameter Handling (`src/parameter_handling/`)
- AST-based parameter extraction from generated agents
- Conversational parameter collection
- Type validation and business rules

### 4. Execution (`src/execution/`)
- Sandboxed agent execution
- Real-time log streaming
- Error handling and recovery

### 5. Integration (`src/integration/`)
- Meta-agent client for workflow generation
- Agent loader and code injection

## Setup

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Download sentence-transformers model (first run)
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"
```

### Environment Variables

```bash
# Required for meta-agent integration
export ANTHROPIC_API_KEY=your_api_key_here

# Optional: Redis for state persistence (default: in-memory)
export REDIS_URL=redis://localhost:6379
```

## Running the Chatbot

### Docker (Recommended)

```bash
# Start with interactive menu
./scripts/start.sh

# Or directly
./scripts/chatbot-start.sh

# Access:
# - Frontend: http://localhost:3002
# - Backend API: http://localhost:8001
# - API Docs: http://localhost:8001/api/docs
```

### Local Development

```bash
# Start chatbot API
cd chatbot
uvicorn api.main:app --reload --port 8001

# API available at http://localhost:8001
```

## Usage Example

### REST API

```python
import requests

# Send message
response = requests.post(
    "http://localhost:8001/chat/message",
    json={
        "session_id": "user-123",
        "message": "I need to submit an expense report",
        "user_id": "employee@company.com"
    }
)

# Response
{
    "response": "I can help with that. Please provide:\n• Expense amount (USD)\n• Date of expense\n• Category (travel/meals/office/other)",
    "status": "collecting_parameters",
    "parameters_needed": ["amount", "date", "category", "department", "receipt_url"]
}
```

### WebSocket (Real-time)

```javascript
const ws = new WebSocket('ws://localhost:8001/ws/chat/user-123');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "log") {
        console.log("Execution log:", data.payload);
    } else if (data.type === "result") {
        console.log("Final result:", data.payload);
    }
};

ws.send(JSON.stringify({
    message: "I need to submit an expense",
    user_id: "employee@company.com"
}));
```

## Workflow Repository

Workflows are stored as `.txt` specifications in `workflows/`:

```
workflows/
├── hr/
│   ├── expense_approval.txt
│   └── leave_request.txt
├── it/
│   └── ticket_submission.txt
└── finance/
    └── invoice_processing.txt
```

### Adding a New Workflow

1. Create workflow specification in appropriate directory
2. Follow standard format (Workflow, Description, Inputs, Steps, Outputs)
3. System automatically indexes on startup
4. No code changes required

## Testing

```bash
# Run all tests
pytest chatbot/tests/ -v

# Run specific test
pytest chatbot/tests/test_conversation.py -v

# With coverage
pytest chatbot/tests/ --cov=chatbot/src --cov-report=html
```

## API Endpoints

### Chat

- `POST /chat/message` - Send message, get response
- `GET /chat/session/{session_id}` - Retrieve session state
- `DELETE /chat/session/{session_id}` - Clear session
- `WS /ws/chat/{session_id}` - WebSocket for real-time updates

### Workflows

- `GET /workflows/list` - List all available workflows
- `GET /workflows/{workflow_id}` - Get workflow details
- `GET /workflows/search?q=query` - Search workflows

### Health

- `GET /health` - Service health check

## Configuration

### Semantic Search

Adjust matching threshold in `src/workflow_matching/repository.py`:

```python
# Default: 0.75 (75% confidence)
# Lower = more permissive, Higher = more strict
CONFIDENCE_THRESHOLD = 0.75
```

### Execution Timeout

Configure agent execution timeout in `src/execution/orchestrator.py`:

```python
# Default: 30 seconds
EXECUTION_TIMEOUT = 30
```

## Troubleshooting

### Low Intent Matching Accuracy

- Check workflow descriptions are clear and descriptive
- Rebuild embeddings cache: `rm -rf .embeddings_cache`
- Tune confidence threshold (see Configuration)

### Execution Timeouts

- Check agent complexity (tool count, parallel branches)
- Increase timeout for complex workflows
- Review execution logs for bottlenecks

### State Loss

- MVP uses in-memory state (lost on restart)
- Production: Configure Redis via `REDIS_URL`
- Add session persistence middleware

## Architecture Decisions

### Why AST-based Parameter Extraction?

- **Deterministic**: No LLM hallucination risk
- **Fast**: Millisecond parsing vs. seconds for LLM
- **Reliable**: Works even when generated code format changes slightly
- **Trade-off**: Requires well-formed Python code (meta-agent already guarantees this)

### Why Semantic Search?

- **Fast**: Sub-100ms query time with cached embeddings
- **Flexible**: Works with synonyms and paraphrasing
- **Scalable**: O(n) search with pre-computed embeddings
- **Trade-off**: Requires model download (~90MB for BAAI/bge-small-en-v1.5)

### Why LangGraph?

- **Stateful**: Built-in state management and checkpointing
- **Composable**: Easy to add/remove nodes without refactoring
- **Debuggable**: Visual graph representation and step-by-step execution
- **Trade-off**: Learning curve for graph-based thinking

## MVP Limitations

1. **State Persistence**: In-memory only (Redis for production)
2. **Authentication**: No user auth (add middleware for production)
3. **Tool Execution**: Simulated stubs (implement real integrations)
4. **Error Recovery**: Basic retry only (add ML-based classification)
5. **Multi-language**: English only (add i18n for global deployment)

## Contributing

1. Follow supercode principles (see project plan)
2. Add tests for all new functionality
3. Update progress tracker with changes
4. Keep functions <20 lines, single responsibility

## License

AGPL-3.0 - If you use this in a web service, you must open-source your service.
