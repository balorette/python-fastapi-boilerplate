# Onboarding Guide

## Project at a Glance
- The repository packages a production-ready FastAPI REST API with async SQLAlchemy, OAuth2 authentication, Redis caching, and extensive tooling for tests, linting, and Dockerized deployments.【F:README.md†L1-L18】
- The README walks through prerequisites, environment setup scripts, Docker Compose options, and manual commands so you can bring the stack up locally before diving into code.【F:README.md†L20-L118】

## How a Request Moves Through the Stack
1. **Application startup** – `main.create_application()` configures the FastAPI app, wires middleware, mounts the versioned router, and registers global error handlers.【F:main.py†L39-L93】
2. **Routing** – the API router at `app/api/v1/api.py` aggregates feature routers (health, auth, users) under `/api/v1` to keep versioned endpoints organized.【F:app/api/v1/api.py†L1-L12】
3. **Endpoint layer** – route modules such as `app/api/v1/endpoints/users.py` enforce request validation, inject dependencies, and translate domain exceptions into HTTP responses.【F:app/api/v1/endpoints/users.py†L1-L136】
4. **Dependencies & auth** – shared dependencies in `app/api/dependencies.py` resolve authenticated users, wire services, and support both internal JWT and Google OAuth tokens.【F:app/api/dependencies.py†L1-L83】
5. **Services** – business logic lives in service classes such as `UserService`, which orchestrates validation, password hashing, pagination, and OAuth-aware workflows on top of repositories.【F:app/services/user.py†L1-L200】
6. **Repositories & models** – repositories provide reusable SQLAlchemy query helpers, backed by declarative models (`app/models/base.py`, `app/models/user.py`) with timestamped audit columns and OAuth-friendly fields.【F:app/repositories/user.py†L1-L152】【F:app/models/base.py†L1-L28】【F:app/models/user.py†L1-L25】
7. **Schemas** – Pydantic models in `app/schemas/` (for example `user.py`) encode validation rules and response shapes shared across the stack.【F:app/schemas/user.py†L1-L195】

## Supporting Infrastructure
- **Configuration** – `app/core/config.py` centralizes environment-driven settings (API metadata, DB URLs, OAuth keys, CORS origins, etc.) via `pydantic-settings` for easy override per environment.【F:app/core/config.py†L1-L96】
- **Database layer** – `app/core/database.py` bootstraps synchronous and async SQLAlchemy engines, tunes pooling for SQLite/PostgreSQL, and exposes request-scoped session dependencies with retry-aware async helpers.【F:app/core/database.py†L1-L130】【F:app/core/database.py†L168-L213】
- **Security utilities** – `app/core/security.py` issues and validates OAuth2-compliant JWTs, manages password hashing, and supports PKCE and password reset flows.【F:app/core/security.py†L1-L165】
- **Error handling** – `app/core/error_handlers.py` installs consistent JSON responses for custom API exceptions, SQLAlchemy errors, and uncaught failures, keeping clients insulated from stack traces.【F:app/core/error_handlers.py†L1-L105】
- **Migrations** – Alembic is configured for async migrations; `alembic/env.py` wires project metadata and runs migrations online/offline against the configured database URL.【F:alembic/env.py†L1-L104】

## Developer Tooling & Tests
- `tests/` ships pytest fixtures that spin up an async SQLite database, override dependencies, and provide sample users so feature tests can exercise the full stack.【F:tests/conftest.py†L1-L200】
- High-level smoke tests cover the public root and health endpoints, ensuring the app boots and basic responses remain stable.【F:tests/test_main.py†L1-L22】
- Additional suites (`tests/test_auth.py`, `tests/test_users.py`, `tests/test_repositories.py`, etc.) probe authentication flows, repository queries, and service logic. Explore them to see real usage patterns of the abstractions above.【F:tests/test_users.py†L1-L20】【F:tests/test_repositories.py†L1-L20】
- Project scripts and docs outline how to run servers, tests, and linting; start with the README or `docs/development.md` for command snippets using either `uv` or traditional tooling.【F:README.md†L41-L118】【F:docs/development.md†L32-L177】

## Suggested Next Steps for New Contributors
1. **Run the API locally** following the README quick-start to become familiar with the environment variables and startup scripts.【F:README.md†L41-L118】
2. **Trace a feature end-to-end** by setting breakpoints or adding logs through the router → dependency → service → repository path for a user endpoint.【F:app/api/v1/endpoints/users.py†L25-L136】【F:app/services/user.py†L59-L200】【F:app/repositories/user.py†L16-L152】
3. **Review domain models and schemas** to understand validation expectations and database shape before extending features.【F:app/models/user.py†L9-L25】【F:app/schemas/user.py†L9-L195】
4. **Explore the docs folder** for deeper dives into deployment, best practices, and architecture to align with existing conventions.【F:docs/development.md†L1-L177】
5. **Experiment with tests**—run them, inspect fixtures, and add a small assertion to get comfortable with the async testing utilities.【F:tests/conftest.py†L1-L200】

Welcome aboard! With these pointers you should be able to navigate the codebase confidently and spot where to plug in new features or fixes.
