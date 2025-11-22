#!/bin/bash

# Chatbot Development Server Launcher

echo "🚀 Starting Chatbot Development Environment"
echo "==========================================="

# Function to check if port is in use
check_port() {
    lsof -i:$1 > /dev/null 2>&1
    return $?
}

# Check if backend is running
if check_port 8000; then
    echo "✅ Backend API already running on port 8000"
else
    echo "⚠️  Backend API not running. Please start it first:"
    echo "   cd /workspaces/meta-flow"
    echo "   python -m chatbot.api.main"
    echo ""
    echo "Press Enter after starting the backend..."
    read
fi

# Start frontend
echo "🎨 Starting frontend development server..."
echo ""
npm run dev -- --host --port 5173

# The frontend will be available at:
# - http://localhost:5173
# - http://[codespace-url]:5173 (if in GitHub Codespaces)