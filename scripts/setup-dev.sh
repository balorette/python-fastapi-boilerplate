#!/usr/bin/env bash

set -euo pipefail

if [[ ! -f "pyproject.toml" ]]; then
    echo "❌ Please run this script from the repository root." >&2
    exit 1
fi

echo "🚀 Setting up IAC API development environment..."

required_version="3.12"
python_version=$(python3 --version 2>/dev/null | awk '{print $2}')

if [[ -z "${python_version}" ]]; then
    echo "❌ python3 not found on PATH." >&2
    exit 1
fi

if [[ "$(printf '%s\n' "${required_version}" "${python_version}" | sort -V | head -n1)" != "${required_version}" ]]; then
    echo "❌ Python ${required_version}+ is required. Found: ${python_version}" >&2
    exit 1
fi

echo "📦 Creating virtual environment with python3 (${python_version})..."
python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate

python -m pip install --upgrade pip

echo "📚 Installing project and development dependencies..."
pip install -e ".[dev]"

echo "🔗 Setting up pre-commit hooks..."
pre-commit install

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

if command -v pytest >/dev/null 2>&1; then
    echo "🧪 Running smoke checks (pytest -m smoke)..."
    pytest -m smoke --maxfail=1
else
    echo "⚠️ pytest not found on PATH; skipping smoke checks." >&2
fi

cat <<'MSG'
✅ Development environment setup complete!

🎯 Activate the environment with:
   source venv/bin/activate

🚀 Start the development server with:
   ./scripts/run-dev.sh

📚 Run the full test suite with:
   ./scripts/run-tests.sh
MSG
