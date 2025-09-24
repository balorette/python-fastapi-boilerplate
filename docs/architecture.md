# API Architecture

## Overview

The IAC API follows a layered architecture pattern that promotes separation of concerns, maintainability, and scalability.

## Architecture Layers

### 1. Presentation Layer (`app/api/`)
- **Endpoints**: HTTP request handlers
- **Routers**: Group related endpoints
- **Dependencies**: Request-scoped dependencies
- **Middleware**: Cross-cutting concerns

### 2. Business Logic Layer (`app/services/`)
- **Services**: Core business logic
- **Validators**: Business rule validation
- **Transformers**: Data transformation logic

### 3. Data Access Layer (`app/models/`, `app/core/database.py`)
- **Models**: SQLAlchemy ORM models
- **Repositories**: Data access patterns
- **Database**: Connection management

### 4. External Integration Layer (`app/utils/`)
- **Clients**: External API clients
- **Adapters**: Third-party service integration
- **Utilities**: Helper functions

## Design Patterns

### Dependency Injection
FastAPI's dependency injection system is used throughout:
- Database sessions
- Authentication
- Configuration
- Shared utilities

### Repository Pattern
Data access is abstracted through repository classes:
```python
class UserRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> User:
        return self.db.query(User).filter(User.id == user_id).first()
```

### Service Layer Pattern
Business logic is encapsulated in service classes:
```python
class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    def create_user(self, user_data: UserCreate) -> User:
        # Business logic here
        pass
```

## Configuration Management

### Environment-based Configuration
- Development: `.env`
- Production: Environment variables
- Testing: Override in test configuration

### Settings Hierarchy
1. Environment variables
2. `.env` file
3. Default values in `app/core/config.py`

## Database Strategy

### ORM Choice: SQLAlchemy
- **Pros**: Mature, flexible, async support
- **Cons**: Learning curve, complexity

### Migration Strategy
- Alembic for schema migrations
- Version-controlled database changes
- Rollback capabilities

### Connection Management
- Connection pooling
- Async/sync session handling
- Health checks

## Authentication & Authorization

### Dual Authentication Strategy
- **Local JWT Authentication**: Username/password with JWT tokens
- **Google OAuth 2.0**: OAuth-based authentication with ID token validation
- **Unified Token Validation**: Both token types work seamlessly

### JWT Strategy
- Stateless authentication
- Configurable expiration  
- Local user token generation

### OAuth Integration
- Google OAuth 2.0 implementation
- Auto-linking accounts by email
- OAuth-only users (no password required)
- Refresh token storage for offline access
- CSRF protection with session state

### Security Measures
- Password hashing (bcrypt) for local users
- Google ID token validation using Google's public keys
- CORS configuration
- Session middleware for OAuth state management
- Email verification tracking
- Rate limiting (future)
- Input validation

## Testing Strategy

### Test Types
1. **Unit Tests**: Individual components
2. **Integration Tests**: Multiple components
3. **End-to-End Tests**: Full request cycle

### Test Database
- SQLite for testing (fast, isolated)
- Test fixtures and factories
- Database rollback between tests

## Monitoring & Observability

### Logging Strategy
- Structured logging (JSON in production)
- Configurable log levels
- Request correlation IDs

### Health Checks
- Basic service health
- Database connectivity
- External service dependencies

### Metrics (Future)
- Request/response metrics
- Performance monitoring
- Error rates

## Scalability Considerations

### Horizontal Scaling
- Stateless application design
- Database connection pooling
- Shared cache (Redis)

### Performance Optimization
- Async request handling
- Database query optimization
- Response caching

### Resource Management
- Connection limits
- Memory usage monitoring
- CPU utilization tracking