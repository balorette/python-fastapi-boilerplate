#!/bin/bash

# Run development server
set -e

echo "🚀 Starting IAC API development server..."

# Activate virtual environment if it exists (supports both venv and .venv)
if [ -d ".venv" ]; then
    echo "📦 Using uv virtual environment (.venv)"
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "📦 Using traditional virtual environment (venv)"
    source venv/bin/activate
else
    echo "⚠️ No virtual environment found. Using system Python."
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Start the development server with hot reload
# Use uv run if available and in uv environment, otherwise use uvicorn directly
if command -v uv &> /dev/null && [ -d ".venv" ]; then
    echo "🏃 Running with uv..."
    uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "🏃 Running with uvicorn..."
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi
