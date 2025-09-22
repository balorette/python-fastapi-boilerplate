#!/bin/bash

# Run tests
set -e

echo "🧪 Running tests..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run pytest with coverage
pytest --cov=app --cov-report=term-missing --cov-report=html