# Meta-Agent Frontend

React + TypeScript web interface for the Meta-Agent workflow generator. Provides a visual editor for creating workflow specifications and viewing generated Python agents.

## Overview

The frontend is a single-page application built with:
- **React 18**: Component-based UI framework
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool and dev server
- **Chakra UI**: Component library with dark mode support
- **Monaco Editor**: VS Code-style code editor with syntax highlighting
- **React Router**: Client-side routing

## Architecture

```
src/
├── components/          # Reusable UI components
│   ├── Editor/         # Monaco-based code editor
│   ├── GenerationResult/ # Output display panels
│   └── StatusIndicator/ # Connection status
├── features/           # Feature modules
│   ├── editor/        # Workflow editor feature
│   └── generator/     # Agent generation feature
├── hooks/             # Custom React hooks
│   ├── useGeneration.ts  # Agent generation logic
│   └── useBackendStatus.ts # Health check polling
├── services/          # API client
│   └── api.ts        # Backend communication
├── theme/            # Chakra UI theme customization
└── App.tsx           # Main application component
```

## Key Features

### Three-Panel Layout
- **Editor Panel**: Write workflow specifications with syntax highlighting and validation
- **Visualizer Panel**: Preview workflow structure (planned feature)
- **Output Panel**: View generated Python code, JSON AST, and metadata

### Example Templates
Pre-built workflow templates accessible via dropdown:
- Sequential workflows (data processing)
- Conditional workflows (expense approval)
- Parallel workflows (compliance checks)
- Orchestrator workflows (ticket routing)
- Nested workflows (order fulfillment)

### Real-Time Generation
- Progress tracking during agent generation
- Streaming feedback from backend
- Error handling with detailed messages

### Dark Mode
- Professional dark theme using Chakra UI
- Persistent preference in localStorage
- Optimized for extended use

## Running the Frontend

### Docker (Production)

The frontend is automatically built and served via Nginx in Docker:

```bash
# Start with interactive menu
./scripts/start.sh

# Or directly
./scripts/meta-agent-start.sh

# Access at http://localhost:3001
```

The Docker build:
1. Builds static assets with Vite
2. Serves via Nginx on port 80 (mapped to host 3001)
3. Proxies `/api/*` requests to backend service
4. Includes health check endpoint at `/health`

### Local Development

For frontend development with hot module replacement:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Access at http://localhost:5173
```

**Environment Variables:**

Create `frontend/.env` for local development:
```bash
# Leave empty to use Vite proxy (recommended)
VITE_API_URL=

# Or specify backend directly (requires CORS)
VITE_API_URL=http://localhost:8000
```

The Vite proxy forwards `/api/*` requests to `http://localhost:8000` automatically, avoiding CORS issues.

## API Integration

The frontend communicates with the backend via REST API:

### Health Check
```typescript
GET /api/health
```
Polled every 10 seconds to display connection status.

### Generate Agent
```typescript
POST /api/generate
Content-Type: application/json

{
  "spec": "Workflow: ...",
  "provider": "claude",
  "model_version": "claude-haiku-4-5"
}
```

See [API README](../api/README.md) for complete endpoint documentation.

## Building for Production

```bash
# Build optimized static assets
npm run build

# Preview production build locally
npm run preview

# Output: dist/ directory with static files
```

The production build:
- Minifies JavaScript and CSS
- Optimizes bundle size with code splitting
- Generates source maps for debugging
- Creates static assets ready for CDN deployment

## Configuration

### Vite Configuration

Key settings in `vite.config.ts`:
- **Proxy**: Forwards `/api/*` to backend during development
- **Build Target**: ES2020 for modern browser support
- **Chunk Splitting**: Separate vendor bundles for better caching
- **Source Maps**: Enabled in development, optional in production

### Environment Variables

All environment variables must be prefixed with `VITE_` to be exposed to the frontend:

- `VITE_API_URL`: Backend API base URL (default: empty, uses proxy)

In Docker, these are set at build time via `ARG` in Dockerfile and baked into the static bundle.

## Development Guidelines

### Component Structure

Components follow a consistent pattern:
```typescript
// MyComponent.tsx
import { FC } from 'react';
import { Box, Text } from '@chakra-ui/react';

interface MyComponentProps {
  title: string;
  onAction: () => void;
}

export const MyComponent: FC<MyComponentProps> = ({ title, onAction }) => {
  return (
    <Box>
      <Text>{title}</Text>
      {/* ... */}
    </Box>
  );
};
```

### State Management

- **Local State**: `useState` for component-specific state
- **Shared State**: React Context for cross-component state (theme, user settings)
- **Server State**: Custom hooks (`useGeneration`, `useBackendStatus`) for API data

### Type Safety

All components and functions are fully typed with TypeScript:
- Props interfaces for all components
- API response types in `services/api.ts`
- Strict mode enabled in `tsconfig.json`

### Code Style

- ESLint configuration included for consistency
- Prettier for automatic formatting
- Run `npm run lint` before committing

## Testing

```bash
# Run tests (when implemented)
npm run test

# Type checking
npm run type-check

# Lint code
npm run lint
```

## Troubleshooting

**Build fails with "Module not found":**
- Delete `node_modules` and `package-lock.json`
- Run `npm install` again
- Ensure Node.js version is 18 or higher

**API requests fail with CORS errors:**
- In development: Ensure `VITE_API_URL` is empty to use proxy
- In Docker: Verify both services are on same network
- Check backend CORS configuration in `api/main.py`

**Hot reload not working:**
- Check Vite dev server is running: `npm run dev`
- Verify file watchers aren't hitting system limits
- Try `npm run dev -- --force` to clear cache

**Monaco Editor not loading:**
- Monaco requires web workers and blob: URLs
- Ensure Content Security Policy allows `worker-src blob:`
- Check browser console for CSP violations

## Deployment

### Docker Deployment

The included Dockerfile uses a multi-stage build:

**Stage 1: Build**
- Node 20 Alpine
- Installs dependencies and builds static assets

**Stage 2: Serve**
- Nginx Alpine
- Copies built assets to `/usr/share/nginx/html`
- Custom nginx config for SPA routing and API proxying

**Nginx Configuration:**
- Serves static files from `/usr/share/nginx/html`
- Proxies `/api/*` to `backend:8000`
- Fallback to `index.html` for SPA routing
- Health check endpoint at `/health`

### Alternative Deployment

The built `dist/` directory can be served by any static file server:
- Vercel, Netlify, Cloudflare Pages
- S3 + CloudFront
- Any HTTP server (Apache, Nginx, Caddy)

Ensure SPA routing is configured (all routes serve `index.html`).

## License

AGPL-3.0 - See root [LICENSE](../LICENSE) file for details.
