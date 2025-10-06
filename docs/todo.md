# Task Tracking - FastAPI Enterprise Baseline

**Document Version**: 2.5.0
**Last Updated**: 2025-10-10

> **Status Snapshot (2025-10-10)**
> - `pytest` → **210 passed / 0 failed / 210 total** (coverage report generated via `uv run pytest`).
> - Coverage: **75%** — biggest gaps remain in `app/api/v1/endpoints/auth.py`, `app/core/database.py`, and CLI utilities (`app/cli.py`).
> - Deprecation warnings surfaced (`pythonjsonlogger`, `crypt`, Starlette 422 constant) alongside an SAWarning during repository flushes — track remediation alongside coverage and CI work.

The following backlog keeps the boilerplate modular, production-ready, and easy for new teams to adopt. Each section calls out the concrete steps required for completion.

## 1. Stabilize Core Observability (Completed)
- [x] Confirm structured logging end-to-end: add regression tests that exercise middleware, request IDs, and safety/audit helpers without relying on file handlers.
- [x] Finish health/metrics rollout: expose optional Prometheus endpoint, document payload contract, and add coverage for failure scenarios (DB outages, disabled audit flags).
- [x] Harden middleware defaults: ensure rate limiting, security headers, and correlation IDs are configurable via settings with sensible production defaults.
- [x] Document liveness/readiness/health payloads and logging metadata in `docs/deployment.md` (ties to Phase 1 success criteria).

## 2. Align Repository & Service Layers (Completed)
- [x] Remove legacy helpers (`count_records`, session attributes) replaced by the unified `BaseRepository`; update feature repositories accordingly.
- [x] Standardize dependency injection: services should receive `AsyncSession` via FastAPI `Depends`, avoiding mixed constructor/session patterns.
- [x] Add focused unit tests for new repository features (soft delete, relationship eager-loading, range filters) to protect the shared base abstraction.
- [x] Backfill CLI coverage to verify repository bootstrap commands (identified coverage gap).

## 3. Authentication & Authorization Hardening (Completed)
- [x] Fix OAuth login regression tests by seeding SQLite tables in debug fixtures (unblocks `tests/test_debug_oauth.py` and `tests/test_oauth_jwt_validation.py`).
- [x] Ensure inactive-user flows return consistent 403/401 responses and adjust expectations in OAuth suites once fixtures are stabilised.
- [x] Consolidate OAuth/JWT validation paths to reuse the provider factory and emit structured errors; align “real” and mock test suites.
- [x] Introduce role/permission scaffolding (schema model, token claims, reusable role guard) and cover key admin routes with RBAC tests.
- [x] Add RBAC dependency guard unit tests to prevent regressions in `require_roles`/`require_permissions`.
- [x] Expand RBAC regression coverage for high-traffic admin endpoints and document smoke scenarios.
- [x] Document RBAC defaults and seeding expectations in contributor and operations guides.

## 4. Testing & Tooling Refinement (In Progress)
- [x] Restore `uv run pytest` to green by addressing remaining OAuth/auth integration failures and flaky fixtures.
- [ ] Enforce linting/formatting in CI: wire `uv run ruff check` and `ruff format --check`, update pre-commit hooks, and document workflow (CI workflow in progress).
- [ ] Replace brittle mocks with shared pytest fixtures/factories for services, repositories, and OAuth providers to improve readability and reuse.
- [x] Resolve pytest warning noise (Pydantic serializers, `datetime.utcnow()`) to keep future upgrades low-risk.
- [ ] Eliminate remaining warnings by migrating to `pythonjsonlogger.json`, replacing Python `crypt` usage, and updating Starlette 422 constant references; investigate SQLAlchemy `Session.add` warning seen during flush events.
  - [x] Migrate structured logging to use `pythonjsonlogger.jsonlogger.JsonFormatter` to remove import deprecation warnings.

## 5. Documentation & Developer Experience (Completed)
- [x] Update docs (`README`, `docs/ai/*`, `docs/features/`) to reflect the unified repository/service patterns and observability stack.
- [x] Refresh quickstart / setup scripts so a fresh clone yields working logs, health probes, and passing smoke tests.
- [x] Capture learnings and next actions in `docs/ai/actions.md` / `docs/ai/lessons.md` after each milestone to keep the knowledge base current.
- [x] Publish CI setup guide outlining uv environment bootstrap + pytest execution for contributors.

## Future and to come
### 6. Add Strawberry GraphQL API ⚠️ PENDING
- [ ] Install Strawberry + serializers
- [ ] Model initial schema (users/auth metadata)
- [ ] Wire `/graphql` endpoint with FastAPI + dependency overrides
- [ ] Add token-aware auth directives
- [ ] Document queries/mutations in `docs/features/`


## Backlog / Deferred
- Secrets hardening for OAuth credentials (pending introduction of secrets manager in Phase 2 rollout).

*Completed work is archived in `docs/todo-completed.md` for historical reference.*
