#!/bin/bash

# Lint and format code
set -e

echo "🔍 Running code formatting and linting..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Format code with black
echo "🎨 Formatting code with black..."
black .

# Sort imports with isort
echo "📋 Sorting imports with isort..."
isort .

# Lint with flake8
echo "🔍 Linting with flake8..."
flake8 .

# Type check with mypy
echo "🔎 Type checking with mypy..."
mypy app/

echo "✅ Code formatting and linting complete!"