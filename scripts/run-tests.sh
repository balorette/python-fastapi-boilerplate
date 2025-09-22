#!/bin/bash

# Run tests
set -e

echo "🧪 Running tests..."

# Activate virtual environment if it exists (supports both venv and .venv)
if [ -d ".venv" ]; then
    echo "📦 Using uv virtual environment (.venv)"
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "📦 Using traditional virtual environment (venv)"
    source venv/bin/activate
fi

# Run pytest with coverage using uv if available, otherwise use pytest directly
if command -v uv &> /dev/null && [ -d ".venv" ]; then
    echo "🏃 Running tests with uv..."
    uv run pytest --cov=app --cov-report=term-missing --cov-report=html
else
    echo "🏃 Running tests with pytest..."
    pytest --cov=app --cov-report=term-missing --cov-report=html
fi