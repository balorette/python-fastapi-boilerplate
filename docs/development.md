# Development Guide

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- Git

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd iac-api
   ```

2. **Run the setup script:**
   ```bash
   ./scripts/setup-dev.sh
   ```

3. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

4. **Start development server:**
   ```bash
   ./scripts/run-dev.sh
   ```

## Development Workflow

### Code Style

We use several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Code linting
- **mypy**: Type checking

Run all quality checks:
```bash
./scripts/lint.sh
```

### Pre-commit Hooks

Pre-commit hooks automatically run quality checks:

```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

### Testing

#### Running Tests

```bash
# All tests
./scripts/run-tests.sh

# Specific test file
pytest tests/test_users.py -v

# With coverage
pytest --cov=app --cov-report=html
```

#### Writing Tests

Test structure:
```python
def test_function_name(client: TestClient, auth_headers: dict):
    """Test description."""
    # Arrange
    data = {"key": "value"}
    
    # Act
    response = client.post("/api/v1/endpoint/", json=data, headers=auth_headers)
    
    # Assert
    assert response.status_code == 201
    assert response.json()["key"] == "value"
```

#### Test Fixtures

Common fixtures in `tests/conftest.py`:
- `client`: TestClient instance
- `auth_headers`: Authentication headers
- `db_session`: Database session

### Database Development

#### Creating Models

```python
# app/models/example.py
from sqlalchemy import Column, Integer, String, DateTime
from app.models.base import Base

class Example(Base):
    __tablename__ = "examples"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### Creating Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Add example table"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### API Development

#### Creating Endpoints

1. **Define Schema** (`app/schemas/`):
```python
from pydantic import BaseModel

class ExampleCreate(BaseModel):
    name: str

class ExampleResponse(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes = True
```

2. **Create Endpoint** (`app/api/v1/endpoints/`):
```python
from fastapi import APIRouter, Depends
from app.schemas.example import ExampleCreate, ExampleResponse

router = APIRouter()

@router.post("/", response_model=ExampleResponse)
async def create_example(example: ExampleCreate):
    # Implementation
    pass
```

3. **Register Router** (`app/api/v1/api.py`):
```python
from app.api.v1.endpoints import examples

api_router.include_router(examples.router, prefix="/examples", tags=["examples"])
```

#### Error Handling

```python
from fastapi import HTTPException, status

# Standard error response
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Resource not found"
)
```

#### Authentication

Protected endpoints:
```python
from app.api.dependencies import get_current_user

@router.get("/protected")
async def protected_endpoint(current_user = Depends(get_current_user)):
    return {"user": current_user}
```

### Configuration

#### Environment Variables

Add new settings to `app/core/config.py`:
```python
class Settings(BaseSettings):
    new_setting: str = "default_value"
    
    class Config:
        env_file = ".env"
```

#### Feature Flags

Use environment variables for feature flags:
```python
# In config.py
FEATURE_ENABLED: bool = False

# In code
if settings.FEATURE_ENABLED:
    # Feature implementation
    pass
```

### Logging

#### Using Structured Logging

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Log with context
logger.info("User created", user_id=user.id, username=user.username)

# Error logging
logger.error("Database error", error=str(e), user_id=user_id)
```

#### Log Levels

- `DEBUG`: Detailed information for debugging
- `INFO`: General information about program execution
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical error messages

### Performance Optimization

#### Database Queries

```python
# Use select_related for N+1 query prevention
users = db.query(User).options(selectinload(User.posts)).all()

# Use pagination
users = db.query(User).offset(skip).limit(limit).all()

# Use async queries when possible
async def get_users_async(db: AsyncSession):
    result = await db.execute(select(User))
    return result.scalars().all()
```

#### Caching

```python
from app.core.cache import cache

@cache.cached(timeout=300)  # 5 minutes
async def expensive_operation(param: str):
    # Expensive computation
    return result
```

### Debugging

#### Local Debugging

1. Set breakpoints in your IDE
2. Start server in debug mode
3. Make requests to trigger breakpoints

#### Docker Debugging

```bash
# Run with debugger port exposed
docker-compose -f docker-compose.debug.yml up

# Attach debugger to port 5678
```

#### Logging Debug Information

```python
logger.debug("Processing request", request_data=data)
```

### Common Issues

#### Import Errors

- Ensure `__init__.py` files exist in all packages
- Check Python path and virtual environment
- Verify all dependencies are installed

#### Database Connection Issues

- Check database URL format
- Verify database server is running
- Check network connectivity and credentials

#### Authentication Issues

- Verify JWT secret key is set
- Check token expiration
- Ensure proper headers are sent

### Best Practices

1. **Code Organization**
   - Keep functions small and focused
   - Use meaningful variable names
   - Add docstrings to functions and classes

2. **Error Handling**
   - Use specific exception types
   - Provide meaningful error messages
   - Log errors with context

3. **Testing**
   - Write tests for all new features
   - Test edge cases and error conditions
   - Keep tests independent and isolated

4. **Documentation**
   - Update README for new features
   - Document API changes
   - Add inline code comments for complex logic

5. **Security**
   - Validate all input data
   - Use parameterized queries
   - Keep dependencies updated
   - Never commit secrets to version control