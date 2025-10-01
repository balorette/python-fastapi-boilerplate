# FastAPI Enterprise Baseline - Improvement Plan

**Document Version**: 1.1.1
**Last Updated**: 2025-10-08
**Status**: Active Development

## Executive Summary

This plan guides the ongoing evolution of the FastAPI enterprise baseline. The codebase now ships with a unified authentication stack, structured observability, and modern tooling. The remaining work focuses on closing the last test regressions, raising coverage, and layering on enterprise amenities such as rate limiting, caching, and production-ready automation.

### Current State Assessment

**Strengths** ✅
- Mature authentication stack that supports both local JWT and Google OAuth flows.
- Repository/service abstractions in place with strong coverage around the user domain.
- Structured logging, health probes, and middleware aligned with enterprise baselines.
- Modern Python 3.12 target, Ruff-first tooling, and uv-backed workflows already standardised.

**Current Gaps** ⚠️
- `uv run pytest` is green (**185 passed / 0 failed / 185 total**), but the harness still depends on ad-hoc SQLite bootstrap logic that should be hardened before parallelisation.
- Coverage sits at **72%** (goal ≥80%); low-coverage zones include `app/api/v1/endpoints/auth.py`, `app/core/database.py`, and the CLI helpers.
- SQLite bootstrap in ad-hoc scripts (for example `test_debug_oauth.py`) still assumes pre-created tables, leading to portability concerns when swapping databases.

## Implementation Roadmap

### Phase 1: Test & Observability Stabilisation (Current Phase)
**Status**: In Progress — objective is a green build and ≥80% coverage.

#### Remaining Tasks
- [ ] Patch OAuth login flows to provision SQLite tables during debug/regression runs.
- [ ] Backfill integration tests around `/api/v1/auth/login` and `/api/v1/auth/token` to lift coverage in `auth.py` and `database.py`.
- [x] Replace deprecated `datetime.utcnow()` usage with timezone-aware alternatives and modern Pydantic serializers.
- [ ] Document structured logging rollout and health-check payloads in README/deployment guides.

#### Completed Highlights
- [x] Consolidated documentation under `docs/` with living backlog and action logs.
- [x] Unified repository/service abstractions and restored the majority of integration suites.
- [x] Migrated to Ruff-only linting with uv-based workflows.
- [x] Elevated the Python target to 3.12 across Docker, scripts, and developer docs.

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
- **OAuth Debug Harness**: Seed temporary SQLite databases within regression fixtures before hitting auth endpoints.
- **Coverage Push**: Target low-coverage modules surfaced by pytest-cov, especially `auth.py`, `database.py`, and CLI utilities.
- **Deprecation Remediation**: ✅ Completed — timezone-aware timestamps and Pydantic V2 serializers now ship in production code.
- **Telemetry Documentation**: Publish structured logging payload examples and health probe contracts in `docs/deployment.md`.

## Success Metrics

### Phase 1 Success Criteria
- 🟡 `uv run pytest` returns green (0 failures).
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
1. Implement lightweight DB bootstrap in OAuth debug/integration tests.
2. Add regression coverage for auth endpoint success/failure responses.
3. Capture logging/health contract details in deployment docs.

### Near-Term (This Sprint)
1. Push coverage above 80% by focusing on the uncovered modules.
2. Update CI guidance with Ruff + pytest commands and environment setup steps.
3. Document structured logging payloads and health check contracts once the observability docs are refreshed.

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
**Next Review**: Weekly during active development
