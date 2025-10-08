# FastAPI Enterprise Baseline - Improvement Plan

**Document Version**: 1.5.0
**Last Updated**: 2025-10-07
**Status**: Active Development (At Risk)

## Executive Summary

This plan guides the ongoing evolution of the FastAPI enterprise baseline. The codebase now ships with a unified authentication stack, structured observability, and modern tooling. The remaining work focuses on closing the last test regressions, raising coverage, and layering on enterprise amenities such as rate limiting, caching, and production-ready automation.

### Current State Assessment

**Strengths** ✅
- Mature authentication stack that supports both local JWT and Google OAuth flows.
- Repository/service abstractions in place with strong coverage around the user domain.
- Structured logging, health probes, and middleware aligned with enterprise baselines.
- Modern Python 3.12 target, Ruff-first tooling, and uv-backed workflows already standardised.

**Current Gaps** ⚠️
- Latest regression run (`uv run pytest`) surfaces one failure (`TestUserService::test_update_user_success`) because the uniqueness guard only checks the email field. CI automation is still missing, so the breakage was caught manually.
- Coverage now sits at **82%** (goal ≥80% achieved); remaining low-coverage zones include `app/api/v1/endpoints/health.py`, the CLI helpers, and select database utilities earmarked for follow-up.
- Runtime warnings persist: deprecated `crypt` usage, Starlette 422 constant references, and an SQLAlchemy `Session.add()` warning emitted during flushes. The `pythonjsonlogger` import warning has been addressed, but the remaining clean-up is pending.
- RBAC regression coverage should broaden to high-sensitivity admin endpoints now that dependency guard behaviour is locked in.

## Implementation Roadmap

### Phase 1: Test & Observability Stabilisation (Current Phase)
**Status**: At Risk — regression introduced in `UserService.update_user`; objective remains a green build and ≥80% coverage.

#### Remaining Tasks
- [ ] Resolve the `UserService.update_user` uniqueness regression so the service double-checks conflicting identifiers (or updates the contract/tests accordingly) and the suite returns to green.
- [ ] Backfill integration tests around `/api/v1/auth/login`, `/api/v1/auth/token`, and OAuth provider error paths to lift coverage in `auth.py`, `database.py`, and `app/services/oauth/`.
- [ ] Expand RBAC test coverage for admin-only endpoints and document the smoke scenarios alongside seeded defaults.
- [ ] Stand up CI with lint + test automation so regressions surface automatically.
- [ ] Replace deprecated Python `crypt` usage, update Starlette 422 constant references, and address the SQLAlchemy `Session.add()` warning seen during flush operations.
- [x] Update structured logging to import `JsonFormatter` from `pythonjsonlogger.json` to resolve the deprecation warning.
- [x] Replace deprecated `datetime.utcnow()` usage with timezone-aware alternatives and modern Pydantic serializers.
- [x] Document structured logging rollout and health-check payloads in README/deployment guides.

#### Completed Highlights
- [x] Consolidated documentation under `docs/` with living backlog and action logs.
- [x] Unified repository/service abstractions and restored the majority of integration suites.
- [x] Migrated to Ruff-only linting with uv-based workflows.
- [x] Elevated the Python target to 3.12 across Docker, scripts, and developer docs.
- [x] Delivered role- and permission-based access controls with seeded defaults and token claims integration.

### Phase 2: Enterprise Features
**Status**: Planned — starts once Phase 1 is closed out.

**Key Deliverables**
- Expand rate limiting and security header defaults, backed by configuration toggles.
- Introduce Redis caching and queue-friendly adapters for background work.
- Wire Prometheus/OpenTelemetry exporters and document scrape targets.
- Harden the OAuth provider factory to support additional providers (Okta, Azure AD, etc.).

### Phase 3: Developer Experience
**Status**: Planned (tentative sequencing).

- Establish GitHub Actions CI/CD with Ruff + pytest workflows and environment bootstrap notes.
- Polish developer CLI (database seeding, admin bootstrap, smoke tests).
- Expand onboarding guides and architecture diagrams for new contributors.

### Phase 4: Production Readiness
**Status**: Planned (post Phase 2 feature drops).

- Load/performance benchmarking with locust or k6.
- Deployment automation scripts for Docker/Kubernetes targets.
- Secrets management integration and hardened OAuth credential rotation.

## Technical Specifications

### Core Stack
- **Framework**: FastAPI 0.115.x (pinned in `pyproject.toml`).
- **Python Runtime**: 3.12.x (uv-managed virtual environment).
- **ORM**: SQLAlchemy 2.x with async engine/session patterns.
- **Validation**: Pydantic 2.11.
- **Datastores**: SQLite (development/testing) and PostgreSQL (production ready).
- **Tooling**: uv package manager, Ruff lint/format, pytest + pytest-asyncio.

### Enterprise Additions (Planned)
- Rate limiting (slowapi) integrated with existing observability signals.
- Redis cache for session data and token revocation flows.
- Prometheus/OpenTelemetry exporters for metrics and tracing.
- Background job workers (arq or Celery) for long-running OAuth sync tasks.
- Hardened secrets management and CI smoke tests.

## Tactical Focus Areas
- **UserService Regression**: Align update logic and test expectations so email/username uniqueness checks run consistently and the service unit test returns to green.
- **OAuth Debug Harness**: Seed temporary SQLite databases within regression fixtures before hitting auth endpoints.
- **Coverage Push**: Target low-coverage modules surfaced by pytest-cov, especially `auth.py`, `database.py`, and CLI utilities.
- **Deprecation Remediation**: ✅ Completed — timezone-aware timestamps and Pydantic V2 serializers now ship in production code.
- **Telemetry Documentation**: Publish structured logging payload examples and health probe contracts in `docs/deployment.md`.

## Success Metrics

### Phase 1 Success Criteria
- 🔴 `uv run pytest` returns green (0 failures) and is enforced through CI.
- 🟡 Code coverage ≥80%.
- ✅ Authentication, repository, and service layers unified.
- ✅ Tooling modernised (uv + Ruff).
- 🟡 Documentation refreshed to reflect observability and auth status.

### Overall Project Goals
- Deliver an enterprise-ready but approachable baseline.
- Maintain batteries-included functionality without over-engineering.
- Keep documentation actionable and current for downstream teams.

## Next Steps

### Immediate Actions (Next 1-2 Days)
1. Fix the `UserService.update_user` regression (double identifier checks + updated tests/spec) to restore a green suite.
2. Raise auth/DB coverage by exercising refresh, error, and provider edge cases.
3. Outline RBAC regression scenarios for admin endpoints and backfill docs detailing default role/permission seeding.
4. Remediate outstanding warnings (deprecated `crypt`, Starlette 422 constant, SQLAlchemy flush behaviour) or document workarounds until fixes land.

### Near-Term (This Sprint)
1. Push coverage above 80% by focusing on the uncovered modules.
2. Add GitHub Actions (or equivalent) workflow that runs `ruff check` and `pytest` against a uv environment, with uv caching for faster iterations.
3. Publish refreshed setup docs explaining dependency pins (bcrypt, itsdangerous, typer) and the expected test baseline (include guidance on the update-user regression fix once merged).

### Longer-Term (Post Phase 1)
1. Kick off rate limiting and Redis caching work (Phase 2).
2. Introduce developer experience enhancements (CLI polish, onboarding docs).
3. Schedule load/performance testing once enterprise features stabilise.

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org)
- [Pydantic V2 Documentation](https://docs.pydantic.dev)
- [Python 3.12 Features](https://docs.python.org/3.12/whatsnew/3.12.html)

---

**Document Status**: Living Document — updated as the project progresses.
**Last Review**: 2025-10-07
**Next Review**: Weekly during active development (or after any regression is detected)
