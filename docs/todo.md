# Task Tracking - FastAPI Enterprise Baseline

**Document Version**: 2.0.0  
**Last Updated**: 2025-10-05

The following backlog keeps the boilerplate modular, production-ready, and easy for new teams to adopt. Each section calls out the concrete steps required for completion.

## 1. Stabilize Core Observability (In Progress)
- [ ] Confirm structured logging end-to-end: add regression tests that exercise middleware, request IDs, and safety/audit helpers without relying on file handlers.
- [ ] Finish health/metrics rollout: expose optional Prometheus endpoint, document payload contract, and add coverage for failure scenarios (DB outages, disabled audit flags).
- [ ] Harden middleware defaults: ensure rate limiting, security headers, and correlation IDs are configurable via settings with sensible production defaults.

## 2. Align Repository & Service Layers (In Progress)
- [ ] Remove legacy helpers (`count_records`, session attributes) replaced by the unified `BaseRepository`; update feature repositories accordingly.
- [ ] Standardize dependency injection: services should receive `AsyncSession` via FastAPI `Depends`, avoiding mixed constructor/session patterns.
- [ ] Add focused unit tests for new repository features (soft delete, relationship eager-loading, range filters) to protect the shared base abstraction.

## 3. Authentication & Authorization Hardening (In Progress)
- [ ] Fix inactive-user flows so auth endpoints return consistent 403/401 responses and update failing tests (`tests/test_auth.py`, OAuth suites).
- [ ] Consolidate OAuth/JWT validation paths to reuse the provider factory and emit structured errors; align “real” and mock test suites.
- [ ] Introduce role/permission scaffolding (schema model, token claims, reusable role guard) and cover key admin routes with RBAC tests.

## 4. Testing & Tooling Refinement (In Progress)
- [ ] Restore `uv run pytest` to green by addressing remaining OAuth/auth integration failures and flaky fixtures.
- [ ] Enforce linting/formatting in CI: wire `uv run ruff check` and `ruff format --check`, update pre-commit hooks, and document workflow.
- [ ] Replace brittle mocks with shared pytest fixtures/factories for services, repositories, and OAuth providers to improve readability and reuse.

## 5. Documentation & Developer Experience (In Progress)
- [ ] Update docs (`README`, `docs/ai/*`, `docs/features/`) to reflect the unified repository/service patterns and observability stack.
- [ ] Refresh quickstart / setup scripts so a fresh clone yields working logs, health probes, and passing smoke tests.
- [ ] Capture learnings and next actions in `docs/ai/actions.md` / `docs/ai/lessons.md` after each milestone to keep the knowledge base current.

## Backlog / Deferred
- Secrets hardening for OAuth credentials (pending introduction of secrets manager in Phase 2 rollout).

*Completed work is archived in `docs/todo-completed.md` for historical reference.*
