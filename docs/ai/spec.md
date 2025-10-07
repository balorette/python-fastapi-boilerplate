# Technical Specification - FastAPI Enterprise Baseline

**Document Version**: 1.1.0
**Last Updated**: 2025-10-10
**Status**: Living Document

## 1. System Overview

### 1.1 Purpose
Provide a production-ready, batteries-included FastAPI baseline for building enterprise APIs with authentication, database integration, and modern Python patterns.

### 1.2 Scope
- REST API development framework
- OAuth2/OIDC authentication
- Database operations (CRUD + advanced queries)
- User management system
- Extensible architecture for additional features

### 1.3 Non-Functional Requirements
- **Performance**: <100ms response time for CRUD operations
- **Scalability**: Support 1000+ concurrent users
- **Reliability**: 99.9% uptime target
- **Security**: OAuth2 compliance, JWT tokens, password hashing
- **Maintainability**: Clean architecture, >80% test coverage

## 2. Technical Architecture

### 2.1 Core Components

#### API Layer (FastAPI)
- RESTful endpoints with OpenAPI documentation
- Request/response validation with Pydantic
- Async request handling
- Middleware for cross-cutting concerns

#### Service Layer
- Business logic encapsulation
- Transaction management
- Validation and authorization
- External service integration

#### Repository Layer
- Data access abstraction
- CRUD operations
- Advanced filtering and pagination
- Query optimization

#### Database Layer
- SQLAlchemy 2.0 ORM with async support
- Alembic for migrations
- Connection pooling
- Multi-database support (SQLite/PostgreSQL)

### 2.2 Technology Stack

```yaml
Core:
  Language: Python 3.12+
  Framework: FastAPI 0.117+
  ORM: SQLAlchemy 2.0+
  Validation: Pydantic 2.0+

Database:
  Development: SQLite
  Production: PostgreSQL 13+
  Migrations: Alembic

Authentication:
  Local: JWT tokens with bcrypt
  OAuth: Google OAuth2 with PKCE
  Session: Redis-backed sessions

Testing:
  Framework: pytest
  Coverage: pytest-cov
  Async: pytest-asyncio

Tooling:
  Package Manager: uv
  Linting/Formatting: ruff
  Pre-commit: pre-commit hooks
```

## 3. API Specification

### 3.1 Endpoint Structure

```
/api/v1/
├── /health           # System health checks
│   ├── GET /        # Basic health
│   └── GET /detailed # Detailed health with dependencies
├── /auth            # Unified OAuth2 authentication endpoints
│   ├── POST /authorize # Start OAuth flow (any provider)
│   ├── POST /token    # Exchange authorization code for tokens
│   ├── POST /login    # Local username/password login
│   ├── POST /refresh  # Refresh access token
│   ├── GET /callback/{provider} # OAuth provider callbacks
│   ├── POST /revoke   # Revoke tokens
│   └── GET /providers # List available OAuth providers
└── /users           # User management
    ├── GET /        # List users (paginated)
    ├── POST /       # Create user
    ├── GET /{id}    # Get user
    ├── PUT /{id}    # Update user
    └── DELETE /{id} # Delete user
```

### 3.2 Authentication Flow

#### Local Authentication
1. User submits credentials to `/auth/login`
2. System validates credentials
3. System generates JWT access token (30 min)
4. System generates refresh token (7 days)
5. Client includes token in Authorization header

#### OAuth2 Flow (with PKCE)
1. Client requests `/api/v1/auth/authorize` with provider
2. System generates state for CSRF protection
3. User redirected to provider (e.g., Google)
4. Provider redirects to `/api/v1/auth/callback/{provider}` with code
5. Client exchanges code at `/api/v1/auth/token`
6. System validates and creates/links user by email
7. System returns JWT tokens

### 3.3 Data Models

#### User Model
```python
class User:
    id: int (primary key)
    email: str (unique, indexed)
    username: str (optional, unique)
    full_name: str (optional)
    hashed_password: str (optional for OAuth users)
    is_active: bool (default: true)
    is_superuser: bool (default: false)
    oauth_provider: str (optional)
    oauth_provider_user_id: str (optional)
    created_at: datetime
    updated_at: datetime
```

#### Token Payload
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "exp": 1234567890,
  "iat": 1234567890,
  "nbf": 1234567890,
  "iss": "api.example.com",
  "aud": "api.example.com",
  "token_type": "access_token",
  "provider": "local|google",
  "new_user": false
}
```

## 4. Service Specifications

### 4.1 UserService

#### Core Methods
- `create_user(user_data: UserCreate) -> User`
- `get_user(user_id: int) -> User`
- `update_user(user_id: int, user_data: UserUpdate) -> User`
- `delete_user(user_id: int) -> bool`
- `authenticate_user(username: str, password: str) -> User`
- `get_users_paginated(skip: int, limit: int) -> List[User]`

#### Validation Rules
- Email must remain unique across all users and is validated on both create and update flows.
- Username must remain unique across all users (including updates) and defaults to lowercase enforcement.
- Update operations run independent uniqueness checks for email and username so email-only changes still validate both fields.
- Conflicts surface as `ConflictError` (HTTP 409) responses with descriptive detail messages for API clients.
- Passwords require a minimum of 8 characters and must contain at least one letter and one number.

### 4.2 AuthService

#### Responsibilities
- Centralise credential validation, OAuth callbacks, and token lifecycle management.
- Persist refresh tokens (local + provider) and coordinate rotation/blacklisting.
- Emit structured audit logs for authentication decisions.

#### Dependencies
- `UserRepository` for identity lookups/updates.
- `TokenEncoder` utility providing JWT encode/decode helpers and key rotation awareness.
- `OAuthProviderRegistry` for provider-specific exchange/revoke flows (Google, future providers).
- `AuditLogger` wrapper exposing `log_auth_success` / `log_auth_failure` events.

#### Method Contracts
- `create_tokens(user: User, context: AuthContext) -> TokenResponse`
  - Generates access + refresh tokens with deterministic `sub`, `iss`, `aud`, and `provider` claims.
  - Binds `roles`/`permissions` arrays in custom claims for downstream guards.
  - Persists hashed refresh token fingerprint + expiry for revocation checks.
  - Emits `audit` log with correlation + user metadata; increments Prometheus counter `auth_success_total`.
- `authenticate_credentials(identifier: str, password: str) -> User`
  - Accepts either username or email; normalises case before lookup.
  - Uses direct `bcrypt` checks for timing-safe comparison, increments failure metrics on mismatch.
  - Raises `InvalidCredentialsError` (HTTP 401) after 3 failed attempts recorded in rolling window.
- `begin_oauth(provider: str, redirect_uri: str) -> OAuthRedirect`
  - Validates provider is registered, generates PKCE verifier/challenge, stores state in session cache.
- `exchange_oauth_code(provider: str, code: str, state: str) -> TokenResponse`
  - Validates state, fetches profile, links/creates local user, then delegates to `create_tokens`.
  - Stores provider refresh token encrypted via Fernet using `settings.SECRET_KEY` derived key.
- `refresh_tokens(refresh_token: str) -> TokenResponse`
  - Validates signature + fingerprint, rejects if revoked/expired, rotates refresh token atomically.
  - Issues new JWT pair and updates persisted fingerprint; logs `refresh` audit event.
- `revoke_tokens(user_id: int, *, provider: str | None = None) -> None`
  - Adds refresh token fingerprint to blacklist table with expiry.
  - Calls provider revoke API when `provider` provided and stored token exists.
- `validate_token(token: str) -> TokenData`
  - Verifies signature, expiry, issuer, and audience.
  - Checks jti/refresh fingerprint against revocation store.
  - Returns strongly typed payload including roles/permissions for guard dependencies.

#### Error Handling & Observability
- Emits structured audit log for every login success/failure with `correlation_id` and `source_ip` fields.
- Metrics:
  - `auth_success_total{provider="local|google"}`
  - `auth_failure_total{reason="invalid_credentials|revoked|expired"}`
  - `auth_refresh_total`
- Raises typed exceptions mapped to HTTP responses:
  - `InvalidCredentialsError` → 401
  - `InactiveUserError` → 403 (includes remediation hint in response detail)
  - `ProviderExchangeError` → 502 with provider error metadata.
- All error branches trigger `log_auth_failure` with reason codes for SOC ingestion.

### 4.3 RoleService

#### Responsibilities
- Manage RBAC role lifecycle (create/update/delete) and enforce uniqueness constraints.
- Coordinate assignment of roles to users and cascade permission updates.

#### Method Contracts
- `create_role(data: RoleCreate) -> Role`
  - Validates slug uniqueness, stores human-readable description, triggers audit log entry.
- `update_role(role_id: int, data: RoleUpdate) -> Role`
  - Prevents renaming of system roles (`admin`, `user`) unless `force=True` and caller is superuser.
- `delete_role(role_id: int) -> None`
  - Soft deletes by default (marks `deleted_at`), hard delete only when `force=True` and no assignments.
- `assign_role(user_id: int, role_id: int) -> None`
  - Validates user/role existence and active status, ensures idempotency, propagates permission cache bust.
- `remove_role(user_id: int, role_id: int) -> None`
  - Blocks removal of last admin role, raises `LastAdminRemovalError` with remediation instructions.
- `list_roles(include_permissions: bool = False) -> list[Role]`
  - Supports eager loading of permissions, returns deterministic ordering (name asc).

### 4.4 PermissionService

#### Responsibilities
- Define fine-grained permission slugs and manage role associations.
- Provide lookup helpers consumed by guard dependencies.

#### Method Contracts
- `create_permission(data: PermissionCreate) -> Permission`
  - Enforces slug pattern `^[a-z0-9_.:-]+$`, rejects duplicates.
- `attach_permission(role_id: int, permission_id: int) -> None`
  - Validates relationship does not exist, updates role cache, logs `permission_attached` event.
- `detach_permission(role_id: int, permission_id: int) -> None`
  - Prevents detaching permissions flagged as mandatory for role (e.g., `admin:*`).
- `list_permissions() -> list[Permission]`
  - Returns canonical ordering, supports filtering by prefix for UI search.
- `get_effective_permissions(user_id: int) -> set[str]`
  - Aggregates direct role permissions + dynamic overrides, used in JWT claim enrichment.

### 4.5 HealthService

#### Responsibilities
- Aggregate dependency checks (database, Redis, logging) for `/api/v1/health/*` endpoints.
- Provide readiness vs liveness separation with consistent payload schemas.

#### Method Contracts
- `get_liveness() -> HealthStatus`
  - Returns static healthy status plus build metadata; no external calls.
- `get_readiness() -> HealthStatus`
  - Executes async DB query (`SELECT 1`), verifies log directory writable, ensures background tasks responsive.
  - Flags `status="degraded"` when non-critical dependencies fail (e.g., Redis down) but API still functional.
- `get_detailed() -> HealthDetails`
  - Extends readiness payload with timings, last migration version, queue depths, and recent auth error counts.

### 4.6 Service Telemetry Baseline

- All services instrument structured logs with `service`, `operation`, and `correlation_id` fields.
- Emit Prometheus counters/histograms via shared `ServiceMetrics` helper:
  - `service_operation_duration_seconds{service="user",operation="create"}` (histogram)
  - `service_operation_failures_total{service,operation}` (counter)
- Propagate tracing context (W3C traceparent) via middleware; services attach span attributes for DB/cache calls.
- Guard-critical paths (auth, role mutation) trigger audit log events with `compliance_event=True` for regulator traceability.

## 5. Database Specifications

### 5.1 Connection Configuration

#### Development (SQLite)
```python
DATABASE_URL = "sqlite:///./app.db"
DATABASE_URL_ASYNC = "sqlite+aiosqlite:///./app.db"
```

#### Production (PostgreSQL)
```python
DATABASE_URL = "postgresql://user:pass@host:5432/dbname"
DATABASE_URL_ASYNC = "postgresql+asyncpg://user:pass@host:5432/dbname"

# Connection pool settings
pool_size = 20
max_overflow = 30
pool_pre_ping = True
pool_recycle = 3600
```

### 5.2 Query Patterns

#### Repository Pattern Features
- Generic CRUD operations
- Advanced filtering (range queries, IN clauses)
- Pagination with offset/limit
- Ordering (ascending/descending)
- Relationship loading (eager/lazy)
- Existence checks
- Count operations

### 5.3 Schema Definitions

All tables inherit the shared `Base` mixin which provides `id`, `created_at`, and
`updated_at` columns plus naming conventions for deterministic constraint
identifiers.

#### `users`

| Column                 | Type           | Constraints / Indexes         | Notes                             |
|------------------------|----------------|--------------------------------|-----------------------------------|
| `id`                   | `INTEGER`      | Primary key, indexed           | Auto-incrementing surrogate key   |
| `email`                | `VARCHAR(255)` | Unique, indexed                | Primary login + OAuth identifier  |
| `username`             | `VARCHAR(255)` | Unique, indexed                | Human-friendly handle             |
| `hashed_password`      | `VARCHAR(255)` | Nullable                       | Empty for OAuth-only accounts     |
| `full_name`            | `VARCHAR(255)` | Nullable                       | Display name                      |
| `is_active`            | `BOOLEAN`      | Default `TRUE`                 | Soft-disable flag                 |
| `is_superuser`         | `BOOLEAN`      | Default `FALSE`                | Grants elevated permissions       |
| `oauth_provider`       | `VARCHAR(50)`  | Nullable, indexed              | `google`, `local`, etc.           |
| `oauth_id`             | `VARCHAR(255)` | Nullable, indexed              | Provider user identifier          |
| `oauth_email_verified` | `BOOLEAN`      | Nullable                       | Mirrors provider verification flag |
| `oauth_refresh_token`  | `TEXT`         | Nullable                       | Encrypted provider refresh token  |

#### `roles`

| Column         | Type           | Constraints / Indexes               | Notes                                |
|----------------|----------------|--------------------------------------|--------------------------------------|
| `id`           | `INTEGER`      | Primary key, indexed                 |                                      |
| `name`         | `VARCHAR(64)`  | Unique, indexed                      | Machine-readable RBAC role key       |
| `description`  | `VARCHAR(255)` | Nullable                             | Human readable description           |

#### `permissions`

| Column        | Type            | Constraints / Indexes               | Notes                                |
|---------------|-----------------|--------------------------------------|--------------------------------------|
| `id`          | `INTEGER`       | Primary key, indexed                 |                                      |
| `name`        | `VARCHAR(128)`  | Unique, indexed                      | Canonical permission slug            |
| `description` | `VARCHAR(255)`  | Nullable                             | Optional documentation string        |

#### Association Tables

- `user_roles`
  - Columns: `user_id` (FK -> `users.id`, `ON DELETE CASCADE`),
    `role_id` (FK -> `roles.id`, `ON DELETE CASCADE`).
  - Composite primary key on (`user_id`, `role_id`) with
    `uq_user_role` unique constraint to prevent duplicates.
- `role_permissions`
  - Columns: `role_id` (FK -> `roles.id`, `ON DELETE CASCADE`),
    `permission_id` (FK -> `permissions.id`, `ON DELETE CASCADE`).
  - Composite primary key on (`role_id`, `permission_id`) and unique constraint
    `uq_role_permission` enforcing idempotent assignments.

### 5.4 Indexing & Performance Considerations

- Composite indexes evaluated per query plan (e.g. `users (oauth_provider,
  oauth_id)` for provider lookups) and created as needed via migrations.
- Foreign keys use `ON DELETE CASCADE` to keep join tables clean when parent
  rows are removed.
- Naming convention in metadata ensures predictable index/constraint names,
  simplifying Alembic diffs and database observability.
- All timestamp fields are stored in UTC; queries requiring ordering should use
  `created_at` indexes for pagination windows.

### 5.5 Migration & Data Management Strategy

- **Versioning**: Alembic revision IDs follow the `YYYYMMDDHHMM_<summary>`
  format to encode chronological ordering.
- **Bootstrap**: Initial migration seeds baseline roles (`admin`, `user`) and
  assigns default permissions required for the API surface.
- **Repeatability**: Seeding scripts live under `app/db/seeders/` (to be
  implemented) and are idempotent, using `ON CONFLICT DO NOTHING` semantics for
  PostgreSQL and equivalent logic for SQLite.
- **Rollback**: Every migration defines both `upgrade()` and `downgrade()` paths
  with lossless reversibility when feasible; destructive steps require explicit
  documentation and ops approval.
- **Data retention**: OAuth refresh tokens are encrypted before persistence and
  rotated whenever providers return new values; scheduled cleanup tasks purge
  inactive users (disabled for >365 days) in future phases.

## 6. Security Specifications

### 6.1 Authentication Security
- Bcrypt for password hashing (cost factor: 12)
- JWT tokens with HS256 algorithm
- Token expiration enforcement
- PKCE for OAuth2 flows
- CSRF protection via state parameter

### 6.2 API Security
- CORS configuration per environment
- Rate limiting (Phase 2)
- Input validation via Pydantic
- SQL injection protection via SQLAlchemy
- XSS protection via proper encoding

### 6.3 Secrets Management
- Environment variables for secrets
- No hardcoded credentials
- Secure token generation
- Key rotation support

## 7. Performance Specifications

### 7.1 Target Metrics
- API Response: <100ms for CRUD
- Database Query: <50ms average
- Token Generation: <10ms
- Password Hashing: <200ms
- Concurrent Users: 1000+

### 7.2 Optimization Strategies
- Database connection pooling
- Query result caching (Phase 2)
- Response compression (Phase 2)
- Async I/O throughout
- Efficient serialization

## 8. Testing Specifications

### 8.1 Test Coverage Requirements
- Unit Tests: >80% coverage
- Integration Tests: Critical paths
- End-to-End Tests: Authentication flows
- Performance Tests: Load testing (Phase 4)

### 8.2 Test Categories
- Repository layer tests
- Service layer tests
- API endpoint tests
- Authentication flow tests
- Database migration tests

## 9. Deployment Specifications

### 9.1 Container Configuration
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

### 9.2 Environment Configuration
- Development: SQLite, debug enabled
- Staging: PostgreSQL, debug disabled
- Production: PostgreSQL, optimized settings

## 10. Monitoring Specifications (Phase 2)

### 10.1 Metrics
- Request rate and latency
- Error rates and types
- Database query performance
- Token generation/validation
- Cache hit rates

### 10.2 Logging
- Structured JSON logging
- Correlation IDs for tracing
- Error aggregation
- Audit logging for sensitive operations

---

**Document Status**: Living Document  
**Review Schedule**: Updated with each implementation phase  
**Next Update**: After Phase 1 completion
