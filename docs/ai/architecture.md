# System Architecture - FastAPI Enterprise Baseline

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-25  
**Status**: Living Document

## Architecture Overview

```mermaid
graph TB
    Client[Client Application]
    API[FastAPI Application]
    Auth[Authentication Layer]
    Service[Service Layer]
    Repo[Repository Layer]
    DB[(Database)]
    Cache[(Redis Cache)]
    
    Client -->|HTTP/HTTPS| API
    API --> Auth
    API --> Service
    Service --> Repo
    Repo --> DB
    Service -.->|Phase 2| Cache
    Auth -.->|Phase 2| Cache
```

## Architectural Principles

### 1. Separation of Concerns
Each layer has a single, well-defined responsibility:
- **API Layer**: HTTP handling, request/response transformation
- **Service Layer**: Business logic, orchestration
- **Repository Layer**: Data access, query building
- **Model Layer**: Data structure definitions

### 2. Dependency Inversion
- Higher layers depend on abstractions, not concrete implementations
- Dependency injection for loose coupling
- Testability through interface design

### 3. Async-First Design
- Async/await throughout the stack
- Non-blocking I/O operations
- Efficient resource utilization

### 4. Domain-Driven Design
- Business logic in service layer
- Domain models separate from database models
- Rich domain objects with behavior

## Layer Architecture

### API Layer (Presentation)

**Responsibilities:**
- HTTP request handling
- Input validation
- Response formatting
- Authentication/authorization
- Error handling
- API documentation

**Key Components:**
```python
app/api/
├── dependencies.py  # Shared dependencies
├── v1/
│   ├── api.py      # Router aggregation
│   └── endpoints/  # Endpoint modules
│       ├── auth.py
│       ├── health.py
│       └── users.py
```

**Design Patterns:**
- Router pattern for endpoint organization
- Dependency injection for services
- Middleware pipeline for cross-cutting concerns

### Service Layer (Business Logic)

**Responsibilities:**
- Business rule implementation
- Transaction coordination
- External service integration
- Complex validations
- Business event handling

**Key Components:**
```python
app/services/
├── __init__.py
├── base.py      # Base service class
├── auth.py      # Authentication service
├── user.py      # User management service
└── oauth/       # OAuth provider services
    ├── base.py
    ├── google.py
    └── factory.py
```

**Design Patterns:**
- Service pattern for business logic
- Factory pattern for OAuth providers
- Strategy pattern for authentication methods

### Repository Layer (Data Access)

**Responsibilities:**
- Database queries
- Data persistence
- Query optimization
- Transaction management
- Cache integration (Phase 2)

**Key Components:**
```python
app/repositories/
├── __init__.py
├── base.py      # Generic repository
└── user.py      # User repository
```

**Design Patterns:**
- Repository pattern for data access
- Generic repository for CRUD operations
- Unit of Work via SQLAlchemy sessions

### Model Layer (Domain & Data)

**Responsibilities:**
- Domain entity definitions
- Data validation rules
- Database schema mapping
- Serialization/deserialization

**Key Components:**
```python
app/models/      # SQLAlchemy models
├── __init__.py
├── base.py      # Base model class
└── user.py      # User model

app/schemas/     # Pydantic schemas
├── __init__.py
├── user.py      # User schemas
├── oauth.py     # OAuth schemas
└── pagination.py # Pagination schemas
```

**Design Patterns:**
- Active Record pattern (SQLAlchemy)
- Data Transfer Objects (Pydantic)
- Schema versioning for API evolution

## Core Design Patterns

### 1. Repository Pattern

```python
class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: Any) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
```

**Benefits:**
- Abstracts data access logic
- Enables easy testing with mocks
- Supports multiple data sources
- Centralizes query logic
- Reusable generic operations

### 2. Service Pattern

```python
class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserRepository(session)

    async def create_user(self, user_data: UserCreate) -> User:
        # Business validation
        existing_user = await self.repository.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # Password hashing
        hashed_password = get_password_hash(user_data.password)

        # Create user
        user_dict = user_data.dict(exclude={'password'})
        user_dict['hashed_password'] = hashed_password

        # Repository call with transaction
        async with self.session.begin():
            user = await self.repository.create(user_dict)
            # Emit events, send emails, etc.

        return user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = await self.repository.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
```

**Benefits:**
- Encapsulates business logic
- Coordinates multiple repositories
- Handles complex transactions
- Provides high-level API
- Centralizes business rules and validations

### 3. Dependency Injection

```python
async def get_user_service(
    session: AsyncSession = Depends(get_async_db)
) -> UserService:
    return UserService(session)

@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service)
):
    return await service.get_user(user_id)
```

**Benefits:**
- Loose coupling between components
- Easy testing with mock dependencies
- Configuration flexibility
- Lifecycle management

### 4. Factory Pattern (OAuth)

```python
class OAuthProviderFactory:
    @staticmethod
    def create_provider(provider_name: str) -> BaseOAuthProvider:
        if provider_name == "google":
            return GoogleOAuthProvider()
        # Add more providers
        raise ValueError(f"Unknown provider: {provider_name}")
```

**Benefits:**
- Extensible provider system
- Consistent interface
- Easy to add new providers
- Runtime provider selection

## Database Architecture

### Connection Management

```python
# Async engine with connection pooling
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### Session Lifecycle

```python
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Migration Strategy
- Alembic for schema migrations
- Auto-generation from models
- Rollback capability
- Version control for schemas

## Security Architecture

### Authentication Architecture

#### Unified OAuth2 Authentication System
The system uses a single OAuth2-based authentication approach that supports both local username/password and external OAuth providers (Google, etc.).

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant AS as AuthService
    participant OS as OAuthService
    participant DB as Database
    participant G as Google OAuth

    alt Local Authentication
        C->>A: POST /api/v1/auth/login
        A->>AS: authenticate_user(email, password)
        AS->>DB: get_user_by_email()
        AS->>AS: verify_password()
        AS->>AS: create_jwt_tokens()
        AS-->>A: TokenResponse
        A-->>C: JWT tokens
    else OAuth Authentication
        C->>A: POST /api/v1/auth/authorize
        A->>OS: get_authorization_url()
        OS-->>C: auth_url + state
        C->>G: User authorizes
        G-->>C: redirect with code
        C->>A: POST /api/v1/auth/token
        A->>OS: exchange_code(code)
        OS->>G: validate token
        G-->>OS: user info
        OS->>DB: create_or_update_user()
        OS->>AS: create_jwt_tokens()
        OS-->>A: TokenResponse
        A-->>C: JWT tokens
    end
```

### Token Architecture
- **Access Token**: Short-lived (30 min), contains user claims
- **Refresh Token**: Long-lived (7 days), for token renewal
- **JWT Structure**: Header.Payload.Signature
- **Claims**: sub (user_id), email, exp, iat, iss, aud
- **Token Validation**: Both local JWT and OAuth provider tokens work seamlessly

### OAuth Provider Integration
- **Google OAuth 2.0**: Complete implementation with refresh token support
- **Auto-linking**: Users automatically linked by email address
- **OAuth-only Users**: No password required for external auth users
- **CSRF Protection**: State parameter with session middleware
- **Email Verification**: Tracks OAuth provider email verification status

### Security Measures
- **Password Hashing**: bcrypt for local users (cost factor: 12)
- **OAuth Token Validation**: Provider-specific validation (Google ID tokens)
- **JWT Security**: HS256 algorithm with configurable secret
- **Session Management**: Secure session cookies for OAuth state
- **CORS Configuration**: Environment-specific CORS settings
- **Input Validation**: Pydantic schemas for all inputs

### Security Layers
1. **Transport**: HTTPS enforcement in production
2. **Authentication**: Unified OAuth2 with JWT tokens
3. **Authorization**: Role-based access control (future)
4. **Validation**: Input sanitization via Pydantic
5. **Database**: Parameterized queries via SQLAlchemy

## Caching Architecture (Phase 2)

### Cache Layers
1. **Application Cache**: FastAPI response caching
2. **Query Cache**: Database query results
3. **Session Cache**: User session data
4. **Token Cache**: JWT token validation

### Cache Strategy
```python
# Decorator-based caching
@cache(expire=300)
async def get_user(user_id: int):
    # Expensive operation cached for 5 minutes
```

## Error Handling Architecture

### Exception Hierarchy
```python
APIException
├── ValidationError (400)
├── AuthenticationError (401)
├── AuthorizationError (403)
├── NotFoundError (404)
├── ConflictError (409)
└── InternalError (500)
```

### Global Error Handler
```python
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
            "request_id": request.state.request_id
        }
    )
```

## Monitoring Architecture (Phase 2)

### Metrics Collection
- **Prometheus**: Time-series metrics
- **OpenTelemetry**: Distributed tracing
- **Custom Metrics**: Business KPIs

### Logging Strategy
- **Structured Logging**: JSON format
- **Correlation IDs**: Request tracking
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Aggregation**: Centralized log management

## Deployment Architecture

### Container Strategy
```dockerfile
# Multi-stage build
FROM python:3.12-slim as builder
# Build dependencies

FROM python:3.12-slim
# Runtime only
```

### Environment Configuration
- **Development**: Local SQLite, debug enabled
- **Staging**: PostgreSQL, production-like
- **Production**: PostgreSQL, optimized, monitoring

### Scaling Strategy
- **Horizontal**: Multiple API instances
- **Load Balancing**: Nginx/HAProxy
- **Database**: Read replicas (future)
- **Caching**: Redis cluster (future)

## Scalability Considerations

### Horizontal Scaling
- **Stateless Design**: All state in database or cache
- **Session Affinity**: Not required due to JWT tokens
- **Load Distribution**: Round-robin or least-connections
- **Health Checks**: `/health` endpoint for load balancer

### Performance Optimization
- **Async Operations**: Full async/await support
- **Connection Pooling**: Database connection reuse
- **Query Optimization**: Indexed queries, eager loading
- **Response Caching**: Cache frequently accessed data (Phase 2)
- **Compression**: gzip compression for responses

### Resource Management
- **Connection Limits**: Configurable pool size (default: 20)
- **Request Timeouts**: Configurable per endpoint
- **Memory Management**: Lazy loading, pagination
- **CPU Utilization**: Async I/O to maximize throughput

## Technology Decisions

### Why FastAPI?
- Modern async framework
- Automatic OpenAPI documentation
- Type safety with Pydantic
- High performance
- Great developer experience

### Why SQLAlchemy 2.0?
- Mature ORM with async support
- Type hints support
- Powerful query capabilities
- Migration support via Alembic
- Multiple database support

### Why Pydantic?
- Runtime type validation
- Serialization/deserialization
- OpenAPI schema generation
- Custom validators
- Performance optimizations

### Why Repository Pattern?
- Testability
- Abstraction of data access
- Centralized query logic
- Easy to switch data sources
- Query optimization

## Future Architecture Enhancements

### Phase 2: Enterprise Features
- Redis caching layer
- Rate limiting middleware
- Monitoring integration
- Background job processing

### Phase 3: Advanced Features
- WebSocket support
- GraphQL endpoint
- Event-driven architecture
- Microservices ready

### Phase 4: Scale & Performance
- Database sharding
- Read/write splitting
- CDN integration
- Auto-scaling

---

**Document Status**: Living Document  
**Review Schedule**: Updated with each architectural decision  
**Next Update**: After Phase 1 implementation