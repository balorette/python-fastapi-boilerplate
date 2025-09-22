#!/bin/bash

# Development setup script using uv (fast Python package installer)
set -e

echo "🚀 Setting up API development environment with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    
    # Check if installation was successful
    if ! command -v uv &> /dev/null; then
        echo "❌ Failed to install uv. Please install manually:"
        echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "   or visit: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
fi

echo "✅ uv found: $(uv --version)"

# Check if Python 3.11+ is available
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ is required. Found: $python_version"
    echo "💡 Try: uv python install 3.11"
    exit 1
fi

# Create virtual environment with uv
echo "📦 Creating virtual environment with uv..."
uv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies with uv (much faster than pip)
echo "📚 Installing dependencies with uv..."
uv pip install -r requirements.txt

# Install development dependencies
echo "🛠️ Installing development dependencies..."
uv pip install -e ".[dev]"

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
echo "🎯 To activate the environment in the future:"
echo "   source .venv/bin/activate"
echo ""
echo "🚀 To start the development server:"
echo "   ./scripts/run-dev.sh"
echo "   or: uv run uvicorn main:app --reload"
echo ""
echo "🧪 To run tests:"
echo "   ./scripts/run-tests.sh"
echo "   or: uv run pytest"
echo ""
echo "💡 uv benefits:"
echo "   • 10-100x faster than pip"
echo "   • Better dependency resolution"
echo "   • Automatic Python version management"
echo "   • Learn more: https://docs.astral.sh/uv/"