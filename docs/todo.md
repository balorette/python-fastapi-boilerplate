# Task Tracking - FastAPI Enterprise Baseline

**Document Version**: 1.0.0  
**Last Updated**: 2025-09-29

## Phase 1 – Critical Fixes (In Progress)

### 1. Fix Test Suite Configuration and Imports ✅ COMPLETE
- [x] Analyze failing tests and clean up deprecated fixtures (`uv run pytest` now green)
- [x] Update pytest async settings and ensure DB isolation (per-test SQLite `.venv`-backed fixtures)
- [x] Restore 100% pass rate across unit/integration suites (`uv run pytest`)

### 2. Complete Core Service Implementations ✅ COMPLETE
- [x] Finish gaps in `UserService` coverage (>80% target)
- [x] Create dedicated auth service once repositories are stable
- [x] Add docstrings/validation for new service methods

### 3. Migrate to Ruff Tooling 🔄 IN PROGRESS
- [x] Configure Ruff in `pyproject.toml`
- [x] Update lint scripts/docs
- [ ] Align pre-commit/CI to Ruff (pending)

### 4. Update Project Configuration 🔄 IN PROGRESS
- [x] Python 3.12 across docs, docker, tooling
- [x] Dependency refresh (`bcrypt>=4.0.1`, etc.)
- [ ] Modernize type hints to PEP 604/PEP 563 patterns
- [ ] Verify pytest async settings align with new fixtures

### 5. Add Strawberry GraphQL API ⚠️ PENDING
- [ ] Install Strawberry + serializers
- [ ] Model initial schema (users/auth metadata)
- [ ] Wire `/graphql` endpoint with FastAPI + dependency overrides
- [ ] Add token-aware auth directives
- [ ] Document queries/mutations in `docs/features/`

### 6. Implement Endpoint RBAC ⚠️ PENDING
- [ ] Define role model/enum in schema + DB
- [ ] Issue role claims in access/refresh tokens
- [ ] Create reusable `Depends` guard for roles
- [ ] Protect admin-sensitive routes
- [ ] Add test coverage for allowed/blocked paths

## Phase 2 – Enterprise Enhancements (Upcoming)

### Rate Limiting & Abuse Protection
- [ ] Integrate `slowapi` with Redis backend
- [ ] Define per-endpoint quotas (login, auth, general API)
- [ ] Bubble up standardized 429 responses

### Caching Layer
- [ ] Introduce FastAPI-cache backed by Redis
- [ ] Cache read-heavy repository queries with invalidation rules
- [ ] Observe hit/miss metrics

### Monitoring & Observability
- [x] Adopt structured JSON logging with compliance metadata
- [x] Upgrade health endpoints with detailed telemetry & probes
- [ ] Add Prometheus exporters & basic Grafana dashboard
- [ ] Instrument OpenTelemetry traces for auth flows
- [ ] Track critical business metrics (logins/day, provider mix)

## Phase 3 – Advanced Features (Backlog)

### Multi-Provider OAuth Expansion
- [ ] Extend provider factory to support Microsoft Entra ID and Okta
- [ ] Add provider-specific configuration blocks in settings
- [ ] Write migrations for new provider metadata fields
- [ ] Cover new providers with integration tests & docs

### Security Hardening
- [ ] Optional MFA (TOTP/SMS) for local accounts
- [ ] Redis-backed session management & invalidation
- [ ] Comprehensive audit/event logging

### UX & Admin Tooling
- [ ] UI/endpoint support for linking/unlinking providers
- [ ] CLI commands for managing OAuth apps/providers
- [ ] Dynamic provider availability endpoint for frontends

## Blocked / Deferred
- OAuth credential secrets hardening (to follow Phase 2 when secrets manager is introduced)

---

*Historical todo files (`docs/ai/todo.md`, `docs/TODO.md`) have been consolidated into this single source of truth.*
