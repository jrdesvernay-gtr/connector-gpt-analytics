#!/bin/bash

# Script to restart the FastAPI server

echo "🛑 Stopping server..."

# Find and kill the uvicorn process
pkill -f "uvicorn app.main:app" || echo "No server process found to kill"

# Wait a moment
sleep 2

echo "🚀 Starting server..."

# Start the server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

