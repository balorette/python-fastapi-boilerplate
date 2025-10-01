# Task Tracking - FastAPI Enterprise Baseline

**Document Version**: 2.1.1
**Last Updated**: 2025-10-08

> **Status Snapshot (2025-10-08)**
> - `uv run pytest` → **185 passed / 0 failed / 185 total**.
> - Coverage: **72%** — focus improvements on `app/api/v1/endpoints/auth.py`, `app/core/database.py`, and CLI utilities.
> - Deprecation warnings resolved: logging now emits timezone-aware timestamps and Pydantic serializers no longer rely on deprecated `json_encoders`.

The following backlog keeps the boilerplate modular, production-ready, and easy for new teams to adopt. Each section calls out the concrete steps required for completion.

## 1. Stabilize Core Observability (In Progress)
- [x] Confirm structured logging end-to-end: add regression tests that exercise middleware, request IDs, and safety/audit helpers without relying on file handlers.
- [ ] Finish health/metrics rollout: expose optional Prometheus endpoint, document payload contract, and add coverage for failure scenarios (DB outages, disabled audit flags).
- [ ] Harden middleware defaults: ensure rate limiting, security headers, and correlation IDs are configurable via settings with sensible production defaults.
- [x] Document liveness/readiness/health payloads and logging metadata in `docs/deployment.md` (ties to Phase 1 success criteria).

## 2. Align Repository & Service Layers (In Progress)
- [x] Remove legacy helpers (`count_records`, session attributes) replaced by the unified `BaseRepository`; update feature repositories accordingly.
- [x] Standardize dependency injection: services should receive `AsyncSession` via FastAPI `Depends`, avoiding mixed constructor/session patterns.
- [x] Add focused unit tests for new repository features (soft delete, relationship eager-loading, range filters) to protect the shared base abstraction.
- [x] Backfill CLI coverage to verify repository bootstrap commands (identified coverage gap).

## 3. Authentication & Authorization Hardening (In Progress)
- [ ] Fix OAuth login regression tests by seeding SQLite tables in debug fixtures (unblocks `tests/test_debug_oauth.py` and `tests/test_oauth_jwt_validation.py`).
- [ ] Ensure inactive-user flows return consistent 403/401 responses and adjust expectations in OAuth suites once fixtures are stabilised.
- [ ] Consolidate OAuth/JWT validation paths to reuse the provider factory and emit structured errors; align “real” and mock test suites.
- [ ] Introduce role/permission scaffolding (schema model, token claims, reusable role guard) and cover key admin routes with RBAC tests.

## 4. Testing & Tooling Refinement (In Progress)
- [x] Restore `uv run pytest` to green by addressing remaining OAuth/auth integration failures and flaky fixtures.
- [ ] Enforce linting/formatting in CI: wire `uv run ruff check` and `ruff format --check`, update pre-commit hooks, and document workflow.
- [ ] Replace brittle mocks with shared pytest fixtures/factories for services, repositories, and OAuth providers to improve readability and reuse.
- [x] Resolve pytest warning noise (Pydantic serializers, `datetime.utcnow()`) to keep future upgrades low-risk.

## 5. Documentation & Developer Experience (In Progress)
- [ ] Update docs (`README`, `docs/ai/*`, `docs/features/`) to reflect the unified repository/service patterns and observability stack.
- [ ] Refresh quickstart / setup scripts so a fresh clone yields working logs, health probes, and passing smoke tests.
- [ ] Capture learnings and next actions in `docs/ai/actions.md` / `docs/ai/lessons.md` after each milestone to keep the knowledge base current.
- [ ] Publish CI setup guide outlining uv environment bootstrap + pytest execution for contributors.

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
