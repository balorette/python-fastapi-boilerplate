#!/usr/bin/env bash

set -euo pipefail

MODE="full"
if [[ $# -gt 0 ]]; then
    case "$1" in
        --smoke)
            MODE="smoke"
            ;;
        --full)
            MODE="full"
            ;;
        *)
            echo "Usage: $0 [--smoke|--full]" >&2
            exit 1
            ;;
    esac
fi

echo "🧪 Running ${MODE} tests..."

if [[ -d ".venv" ]]; then
    echo "📦 Using uv virtual environment (.venv)"
    # shellcheck disable=SC1091
    source .venv/bin/activate
elif [[ -d "venv" ]]; then
    echo "📦 Using traditional virtual environment (venv)"
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

if command -v uv >/dev/null 2>&1 && [[ -d ".venv" ]]; then
    if [[ "${MODE}" == "smoke" ]]; then
        echo "🏃 Running smoke tests with uv..."
        uv run pytest -m smoke --maxfail=1
    else
        echo "🏃 Running full test suite with uv..."
        uv run pytest
    fi
else
    if [[ "${MODE}" == "smoke" ]]; then
        echo "🏃 Running smoke tests with pytest..."
        pytest -m smoke --maxfail=1
    else
        echo "🏃 Running full test suite with pytest..."
        pytest
    fi
fi
