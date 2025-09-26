#!/bin/bash

# Lint and format code
set -e

echo "🔍 Running Ruff formatting and linting..."

# Activate virtual environment if it exists (supports both venv and .venv)
if [ -d ".venv" ]; then
    echo "📦 Using uv virtual environment (.venv)"
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "📦 Using traditional virtual environment (venv)"
    source venv/bin/activate
fi

# Choose runner based on available tools
if command -v uv &> /dev/null && [ -d ".venv" ]; then
    RUNNER="uv run"
    echo "🏃 Using uv to run tools..."
else
    RUNNER=""
    echo "🏃 Using direct tool execution..."
fi

# Format code with Ruff
echo "🎨 Formatting code with Ruff..."
$RUNNER ruff format .

# Lint and auto-fix with Ruff
echo "🔧 Linting with Ruff (auto-fix)..."
$RUNNER ruff check --fix .

echo "✅ Ruff formatting and linting complete!"
