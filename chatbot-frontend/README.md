# Meta-Flow Chatbot Frontend

React-based conversational interface for the Meta-Flow workflow automation system.

![Chatbot Interface](artifacts/chatbot_image_1.png)

## Overview

This frontend application provides a conversational user interface for interacting with the Meta-Flow automation system. It enables employees to execute workflows through natural language conversations, with automatic parameter collection and real-time execution monitoring.

## Key Features

- **Conversational Interface**: Natural language interaction for workflow execution
- **Intelligent Workflow Matching**: Semantic search with confidence scoring (>60% threshold)
- **Dynamic Parameter Collection**: Automated form generation based on workflow requirements
- **Real-time Execution Monitoring**: Live streaming of workflow execution logs via WebSocket
- **Session Management**: Persistent conversation history with session resumption capability
- **Scandinavian Design System**: Professional, minimalist interface optimized for clarity

## Technical Architecture

### Technology Stack

- **Framework**: React 18 with TypeScript
- **UI Components**: Chakra UI v2.10
- **State Management**: Zustand v4.5
- **Data Fetching**: TanStack Query v5.18
- **WebSocket Client**: Socket.io-client v4.7
- **Build Tool**: Vite v7.2

### System Requirements

- Node.js 18.0 or higher
- npm 9.0 or higher
- Backend API running on port 8000

## Running the Application

### Docker (Production)

The chatbot frontend is automatically built and served via Nginx in Docker:

```bash
# Start with interactive menu
./scripts/start.sh

# Or directly
./scripts/chatbot-start.sh

# Access at http://localhost:3002
```

The Docker build:
1. Builds static assets with Vite
2. Serves via Nginx on port 80 (mapped to host 3002)
3. Proxies `/api/*` and `/ws/*` requests to chatbot backend
4. Includes health check endpoint at `/health`

### Local Development

For frontend development with hot module replacement:

1. Install dependencies:
   ```bash
   cd chatbot-frontend
   npm install
   ```

2. Start the backend API (separate terminal):
   ```bash
   cd /workspaces/meta-flow
   ./scripts/chatbot-start.sh  # Or start backend manually
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Access the application at http://localhost:5173

**Environment Variables:**

Create `chatbot-frontend/.env` for local development:
```bash
# Backend API URL (default: /api, uses Vite proxy)
VITE_CHATBOT_API_URL=/api

# WebSocket URL (default: /ws, uses Vite proxy)
VITE_CHATBOT_WS_URL=/ws
```

The Vite proxy forwards requests automatically during development, avoiding CORS issues.

## Project Structure

```
src/
├── features/chat/           # Core chat functionality
│   ├── ChatLayout.tsx      # Main application container
│   ├── MessageList.tsx     # Message rendering and display
│   ├── Composer.tsx        # User input component
│   ├── ParameterDrawer.tsx # Parameter collection interface
│   └── ExecutionPanel.tsx  # Execution log viewer
├── services/               # External service integration
│   ├── api.ts             # REST API client
│   ├── websocket.ts       # WebSocket connection manager
│   └── types.ts           # TypeScript type definitions
├── store/                  # Application state
│   └── chatStore.ts       # Zustand store configuration
├── hooks/                  # Custom React hooks
│   └── useChat.ts         # Chat functionality hook
└── theme/                  # Design system
    └── index.ts           # Chakra UI theme configuration
```

## API Integration

The frontend communicates with the backend through:

### REST Endpoints
- `POST /chat/message` - Process user messages
- `GET /chat/session/{id}` - Retrieve session state
- `GET /workflows/list` - List available workflows
- `DELETE /chat/session/{id}` - Clear session data

### WebSocket Connection
- `WS /ws/chat/{session_id}` - Real-time execution updates

## Performance Metrics

- Initial load time: < 2 seconds
- Message response time: < 100ms (excluding LLM processing)
- WebSocket latency: < 50ms
- Session persistence: LocalStorage with 10-session limit

## Build and Deployment

### Development Build
```bash
npm run dev
```

### Production Build
```bash
npm run build
npm run preview
```

### Build Output
- Output directory: `dist/`
- Bundle size: ~500KB (gzipped)
- Code splitting: Automatic via Vite

## License

AGPL-3.0 - Part of the Meta-Flow project
