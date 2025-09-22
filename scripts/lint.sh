#!/bin/bash

# Lint and format code
set -e

echo "🔍 Running code formatting and linting..."

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

# Format code with black
echo "🎨 Formatting code with black..."
$RUNNER black .

# Sort imports with isort
echo "📋 Sorting imports with isort..."
$RUNNER isort .

# Lint with flake8
echo "🔍 Linting with flake8..."
$RUNNER flake8 .

# Type check with mypy
echo "🔎 Type checking with mypy..."
$RUNNER mypy app/

echo "✅ Code formatting and linting complete!"