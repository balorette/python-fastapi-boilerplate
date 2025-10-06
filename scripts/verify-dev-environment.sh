#!/usr/bin/env bash

set -euo pipefail

if [[ ! -f "pyproject.toml" ]]; then
    echo "❌ Please run this script from the repository root." >&2
    exit 1
fi

PYTHON_CMD=("python")
if command -v uv >/dev/null 2>&1 && [[ -d ".venv" ]]; then
    PYTHON_CMD=("uv" "run" "python")
fi

if [[ -d "venv" && "${VIRTUAL_ENV:-}" != "$(pwd)/venv" && "${#PYTHON_CMD[@]}" -eq 1 ]]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

echo "🩺 Validating health probes and structured logging..."
"${PYTHON_CMD[@]}" <<'PY'
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from main import app

client = TestClient(app)
response = client.get("/health")
response.raise_for_status()
payload = response.json()
if payload.get("status") != "healthy":
    raise SystemExit(f"Health endpoint returned unexpected payload: {payload}")

log_dir = Path(settings.LOG_DIRECTORY)
if not log_dir.exists():
    raise SystemExit(f"Log directory {log_dir} was not created")

app_log = log_dir / "application.log"
if not app_log.exists() or app_log.stat().st_size == 0:
    raise SystemExit(
        "Structured logging did not produce an application.log entry; "
        "check logging configuration."
    )

print("Health payload:", payload)
print("Application log located at:", app_log)
PY

echo "✅ Health probes responded and structured logs are available."
