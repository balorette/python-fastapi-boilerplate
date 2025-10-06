#!/usr/bin/env bash

set -euo pipefail

if [[ ! -f "pyproject.toml" ]]; then
    echo "❌ Please run this script from the repository root." >&2
    exit 1
fi

echo "🚀 Setting up API development environment with uv..."

if ! command -v uv >/dev/null 2>&1; then
    echo "📦 uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"

    if ! command -v uv >/dev/null 2>&1; then
        cat <<'MSG'
❌ Failed to install uv automatically.
   Install manually via:
     curl -LsSf https://astral.sh/uv/install.sh | sh
   Documentation: https://docs.astral.sh/uv/getting-started/installation/
MSG
        exit 1
    fi
fi

echo "✅ uv found: $(uv --version)"

required_python="3.12"
echo "🐍 Ensuring Python ${required_python} is available via uv..."
uv python install "${required_python}" >/dev/null 2>&1 || true

python_path=$(uv python find "${required_python}")
if [[ -z "${python_path}" ]]; then
    echo "❌ Unable to locate Python ${required_python}." >&2
    echo "   Try: uv python install ${required_python}" >&2
    exit 1
fi

echo "📦 Creating virtual environment with uv (${required_python})..."
uv venv --python "${python_path}"

echo "🔄 Activating virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

if [[ -f "uv.lock" ]]; then
    echo "📚 Installing dependencies with uv sync (including dev extras)..."
    uv sync --dev
else
    echo "📚 Installing dependencies with uv pip..."
    uv pip install -e ".[dev]"
fi

echo "🔗 Setting up pre-commit hooks..."
uv run pre-commit install

if [[ ! -f .env ]]; then
    echo "📄 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Using SQLite for development (default)"
else
    echo "📄 .env file already exists"
fi

echo "🗄️ Setting up database (SQLite default)..."
./scripts/setup-db.sh sqlite

echo "🩺 Running health/log verification..."
./scripts/verify-dev-environment.sh

echo "🧪 Running smoke checks (uv run pytest -m smoke)..."
uv run pytest -m smoke --maxfail=1

cat <<'MSG'
✅ Development environment setup complete!

🎯 Activate the environment with:
   source .venv/bin/activate

🚀 Start the development server with:
   ./scripts/run-dev.sh

📚 Run the full test suite with:
   ./scripts/run-tests.sh
MSG
