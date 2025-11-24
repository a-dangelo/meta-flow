# Meta-Agent API

FastAPI backend service for the Meta-Agent workflow generator. Provides REST endpoints for transforming natural language workflow specifications into executable Python agents.

## Architecture

The API orchestrates the two-phase meta-agent pipeline:

```
Client Request → FastAPI → Phase 1 (LangGraph) → JSON AST → Phase 2 (Code Generator) → Python Agent
```

**Phase 1**: LLM-powered parsing and validation using LangGraph state machine
**Phase 2**: Deterministic code generation with error handling and credential management

## API Endpoints

### Health Check
```http
GET /api/health
```

Returns service health status and configuration.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-24T12:00:00",
  "version": "1.0.0",
  "providers": {
    "claude": true,
    "aimlapi": false,
    "gemini": false
  }
}
```

### Generate Agent
```http
POST /api/generate
```

Transforms a workflow specification into executable Python code.

**Request Body:**
```json
{
  "spec": "Workflow: data_processing\nDescription: ...",
  "provider": "claude",
  "model_version": "claude-haiku-4-5"
}
```

**Parameters:**
- `spec` (string, required): Natural language workflow specification
- `provider` (string, optional): LLM provider - `claude`, `aimlapi`, or `gemini` (default: `claude`)
- `model_version` (string, optional): Specific model version to override default

**Response (Success):**
```json
{
  "success": true,
  "workflow_name": "data_processing_pipeline",
  "agent_code": "#!/usr/bin/env python3\n...",
  "json_ast": {...},
  "metadata": {
    "generated_at": "2025-11-24T12:00:00",
    "code_size": 4609,
    "provider": "claude",
    "model": "claude-haiku-4-5",
    "confidence": 1.0
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Validation failed: Missing required field 'Steps'",
  "error_type": "ValidationError",
  "details": {...}
}
```

**Error Types:**
- `ValidationError`: Invalid specification format
- `ParsingError`: LLM parsing failure
- `GenerationError`: Code generation failure
- `ConfigurationError`: Missing API keys or invalid configuration

## Configuration

The API uses environment variables for configuration:

```bash
# LLM Provider Keys (at least one required)
ANTHROPIC_API_KEY=sk-ant-your-key-here
AIMLAPI_KEY=your-aimlapi-key
GEMINI_API_KEY=your-gemini-key

# Optional: Model Defaults
ANTHROPIC_MODEL=claude-haiku-4-5
AIMLAPI_MODEL=x-ai/grok-4-fast-reasoning
GEMINI_MODEL=gemini-2.5-pro
```

## Running the API

### Docker (Recommended)

```bash
# Start with docker-compose
docker compose up -d backend

# Access API
curl http://localhost:8000/api/health

# View logs
docker compose logs -f backend
```

### Local Development

```bash
# From project root
cd api
python3 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# Run server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Access API
curl http://localhost:8000/api/health
```

## API Documentation

The API provides interactive documentation at:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

These interfaces allow you to:
- Explore all available endpoints
- View request/response schemas
- Test API calls directly from the browser
- Download OpenAPI specification

## Security

The API implements multiple security layers:

- **CORS**: Restricted to localhost origins for development
- **Trusted Host Middleware**: Validates request hosts
- **Content Security Policy**: Protects against XSS attacks
- **Input Validation**: Size limits and format checks on all inputs
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, etc.

For production deployment, update CORS origins in `main.py` to match your frontend domain.

## Error Handling

All errors follow a consistent JSON structure:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_type": "ErrorClassName",
  "details": {
    "field": "Additional context"
  }
}
```

**HTTP Status Codes:**
- `200`: Success
- `400`: Client error (invalid input, validation failure)
- `500`: Server error (LLM API failure, unexpected errors)
- `503`: Service unavailable (no API keys configured)

## Dependencies

The API depends on:

- **FastAPI**: Web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Request/response validation
- **src.agents**: Phase 1 meta-agent (LangGraph + LLM)
- **src.generators**: Phase 2 code generator

All dependencies are listed in `/requirements.txt`.

## Development

### Adding New Endpoints

1. Define request/response models using Pydantic
2. Add endpoint function with proper error handling
3. Update OpenAPI metadata (title, description, tags)
4. Add tests in `/tests/api/`

### Logging

The API uses Python's standard logging module:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Processing request")
logger.error("Generation failed", exc_info=True)
```

Log level can be configured via `LOG_LEVEL` environment variable.

### Testing

```bash
# Run API tests
pytest tests/api/ -v

# Test health endpoint
curl http://localhost:8000/api/health

# Test generation (requires API key)
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"spec": "..."}'
```

## Monitoring

In Docker deployment, health checks run automatically:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
  interval: 10s
  timeout: 5s
  retries: 3
```

Check container health:
```bash
docker compose ps
```

## Troubleshooting

**API returns 503 "No API keys configured":**
- Verify `.env` file exists with at least one provider key
- Check environment variables: `docker compose exec backend env | grep API_KEY`

**CORS errors in browser console:**
- Ensure frontend origin is listed in `allow_origins` in `main.py`
- Check that frontend is accessing correct backend URL

**Slow response times:**
- Phase 1 (LLM parsing) typically takes 5-15 seconds
- Consider using faster models (e.g., `claude-haiku-4-5` instead of `claude-sonnet-4`)
- Check LLM provider API status

**Import errors:**
- Ensure `src/` is in Python path (API runs from project root)
- Verify all dependencies installed: `pip install -r requirements.txt`

## License

AGPL-3.0 - See root [LICENSE](../LICENSE) file for details.
