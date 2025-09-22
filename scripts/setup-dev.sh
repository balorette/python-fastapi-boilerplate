#!/bin/bash

# Development setup script
set -e

echo "🚀 Setting up IAC API development environment..."

# Check if Python 3.11+ is installed
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ is required. Found: $python_version"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Install development dependencies
echo "🛠️ Installing development dependencies..."
pip install -e ".[dev]"

# Setup pre-commit hooks
echo "🔗 Setting up pre-commit hooks..."
pre-commit install

# Copy environment file and setup database
if [ ! -f .env ]; then
    echo "📄 Creating .env file..."
    cp .env.example .env
    echo "✅ Using SQLite for development (default)"
    echo "⚠️ Please review .env file and update if needed"
else
    echo "📄 .env file already exists"
fi

# Setup database (defaults to SQLite)
echo "🗄️ Setting up database..."
./scripts/setup-db.sh sqlite

echo "✅ Development environment setup complete!"
echo ""
echo "To activate the environment, run:"
echo "source venv/bin/activate"
echo ""
echo "To start the development server, run:"
echo "./scripts/run-dev.sh"