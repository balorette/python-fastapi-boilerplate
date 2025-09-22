#!/bin/bash

# Run development server
set -e

echo "🚀 Starting IAC API development server..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Start the development server with hot reload
uvicorn main:app --host 0.0.0.0 --port 8000 --reload