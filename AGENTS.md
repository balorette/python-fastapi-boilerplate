# Repository Guidelines

## Project Structure & Module Organization
- The FastAPI service lives in `app/`; `api/v1/endpoints` holds route handlers and `main.py` wires the router and middleware.
- Configuration, database bootstrap, and security utilities sit in `app/core`; ORM models in `app/models`; Pydantic contracts in `app/schemas`.
- Business logic lives in `app/services`; persistence in `app/repositories`; utilities in `app/utils`.
- Tests reside in `tests/` with fixtures in `tests/conftest.py`, unit coverage under `tests/unit/`, and flow tests under `tests/integration/`.
- Documentation lives in `docs/` and `docs/ai/` for spec, architecture, actions, lessons, and todo.

## Build, Test, and Development Commands
- Bootstrap with `./scripts/setup-dev-uv.sh` (uv) or `./scripts/setup-dev.sh` (pip); both seed SQLite.
- Run the API via `./scripts/run-dev.sh` or `uv run uvicorn main:app --reload`.
- Apply migrations using `alembic upgrade head`; scaffold new ones with `alembic revision --autogenerate -m "add_users_table"`.
- Use `./scripts/migrate-oauth.sh` when upgrading existing deployments to the Google OAuth stack.

## Coding Style & Naming Conventions
- Follow Ruff defaults: 88-char lines, double quotes, 4-space indentation, and full type hints for new functions.
- Python modules stay snake_case (`user_service.py`); Pydantic schemas and enums use PascalCase (`UserRead`); async mirrors append `_async`.
- Run `ruff check` before commits; `ruff format` and `ruff check --fix` keep style and imports aligned with `pyproject.toml`.

## Testing Guidelines
- Tests rely on `pytest` with async fixtures; favor explicit names like `test_auth_login_returns_token`.
- Execute `./scripts/run-tests.sh` or `pytest --cov=app --cov-report=html` (HTML lives in `htmlcov/`) before pushing.
- Mock outbound HTTP calls with helpers in `tests/conftest.py`.

## Documentation & AI Collaboration
- Before coding, review relevant sections in `docs/ai/spec.md` and `docs/ai/architecture.md`; log significant work in `docs/ai/actions.md` and update `docs/ai/todo.md`.
- Reflect requirement or design shifts in `docs/ai/improvement-plan.md` and `docs/features/`; keep README aligned with public APIs.
- Capture follow-up learnings in `docs/ai/lessons.md`; document new endpoints or flows in `OAUTH_IMPLEMENTATION.md` and `DOCUMENTATION_UPDATES.md` when applicable.

## Commit & Pull Request Guidelines
- Write present-tense commits (`feat: add oauth authorize endpoint`); mention Alembic revision IDs or scripts touched in bodies.
- PRs should link issues, describe testing, and include screenshots or curl output for user-visible changes.
- Confirm linting and tests locally before review; call out breaking changes, new env vars, or ops steps in the PR description.

## Security & Configuration Tips
- Copy `.env.example` to `.env` and set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, and `SECRET_KEY` before running OAuth paths.
- Use `./scripts/setup-db.sh postgresql` when mirroring production; keep secrets out of source control and rotate OAuth credentials.
