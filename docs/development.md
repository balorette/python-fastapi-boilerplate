# Development Guide

## Getting Started

### Prerequisites
- Python 3.11+
- Package Manager: **uv** (recommended) or pip + venv
- SQLite (included with Python) OR PostgreSQL 13+
- Redis 6+ (optional, for caching)
- Git

### Package Manager Options

**uv (Recommended - 10-100x faster than pip)**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# or
pip install uv

# Key benefits:
# • Extremely fast dependency resolution and installation
# • Better conflict resolution
# • Automatic Python version management
# • Drop-in replacement for pip
# • Built in Rust for speed
```

**Traditional pip + venv**
Standard Python tooling included with Python installations.

### Development Setup

**Option 1: Quick setup with uv (recommended)**
```bash
git clone <repository-url>
cd iac-api
./scripts/setup-dev-uv.sh
```

**Option 2: Traditional setup**
```bash
git clone <repository-url>
cd iac-api
./scripts/setup-dev.sh
```

**Option 3: Manual setup with uv**
```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -e ".[dev]"

# Setup environment
cp .env.example .env
./scripts/setup-db.sh sqlite
```

**Option 4: Manual setup with pip**
```bash
# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"

# Setup environment
cp .env.example .env
./scripts/setup-db.sh sqlite
```

### Environment Management

#### Using uv (Recommended)

```bash
# Create virtual environment
uv venv                              # Creates .venv/

# Activate environment
source .venv/bin/activate            # Linux/macOS
.venv\Scripts\activate               # Windows

# Install dependencies
uv pip install -r requirements.txt  # Install from requirements.txt
uv pip install package-name         # Install single package
uv pip install -e ".[dev]"          # Install project in editable mode

# Run commands in environment
uv run python script.py             # Run without activating
uv run pytest                       # Run tests
uv run uvicorn main:app --reload    # Start server

# List installed packages
uv pip list

# Generate requirements
uv pip freeze > requirements.txt
```

#### Using Traditional Tools

```bash
# Create virtual environment
python3 -m venv venv

# Activate environment
source venv/bin/activate             # Linux/macOS
venv\Scripts\activate                # Windows

# Install dependencies
pip install -r requirements.txt
pip install package-name
pip install -e ".[dev]"

# List installed packages
pip list

# Generate requirements
pip freeze > requirements.txt
```

#### Virtual Environment Locations

- **uv**: Creates `.venv/` directory (modern convention)
- **venv**: Creates `venv/` directory (traditional)
- Both are supported by the project scripts

## Development Workflow

### Daily Development Commands

#### With uv (Fast & Modern)

```bash
# Start development server
./scripts/run-dev.sh                # Uses uv if available
# or directly:
uv run uvicorn main:app --reload

# Run tests
./scripts/run-tests.sh              # Uses uv if available
# or directly:
uv run pytest

# Format and lint code
./scripts/lint.sh                   # Uses uv if available
# or directly:
uv run black .
uv run isort .
uv run flake8 .
uv run mypy app/

# Install new dependencies
uv pip install new-package
uv pip install new-package==1.0.0   # Specific version

# Update dependencies
uv pip install --upgrade package-name
uv pip install --upgrade-all        # Update all packages
```

#### With Traditional Tools

```bash
# Activate environment first
source venv/bin/activate             # or .venv/bin/activate

# Then run commands
uvicorn main:app --reload
pytest
black .
pip install new-package
```

### Package Management Best Practices

#### uv Advantages

- **Speed**: 10-100x faster than pip
- **Reliability**: Better dependency resolution
- **Convenience**: Can run commands without activation
- **Modern**: Active development, modern Python tooling

#### When to Use Each

**Use uv when:**
- Starting new projects
- Working in teams (faster CI/CD)
- You want the latest Python tooling
- Speed matters for your workflow

**Use pip when:**
- Working with legacy projects
- Corporate environments with restrictions
- You prefer established, stable tooling
- Team members are unfamiliar with uv

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

#### Database Configuration

The project supports both SQLite (for development) and PostgreSQL (for production):

```bash
# Use SQLite (default, no setup required)
./scripts/setup-db.sh sqlite

# Use PostgreSQL (requires PostgreSQL installation)
./scripts/setup-db.sh postgresql
```

#### Database Features by Type

**SQLite (Development)**
- ✅ No installation required
- ✅ Fast local development
- ✅ Easy testing and experimentation
- ❌ No concurrent writes
- ❌ Limited for production use

**PostgreSQL (Production)**
- ✅ Full ACID compliance
- ✅ Concurrent access
- ✅ Advanced features (JSON, arrays, etc.)
- ✅ Production ready
- ❌ Requires installation and setup

#### Database Best Practices

**Development Workflow**
1. Start with SQLite for quick prototyping
2. Test with PostgreSQL before production deployment
3. Use migrations for all schema changes
4. Keep test database separate (automatically handled)

**Model Development**
```python
# app/models/example.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.models.base import Base

class Example(Base):
    __tablename__ = "examples"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)  # Add indexes for queries
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Add constraints and indexes as needed
    __table_args__ = (
        Index('ix_example_name_active', 'name', 'is_active'),
    )
```

**Migration Best Practices**
```bash
# Always review generated migrations before applying
alembic revision --autogenerate -m "Add example table"

# Edit the generated migration file to add:
# - Proper indexes
# - Data migrations if needed
# - Rollback logic

# Test the migration
alembic upgrade head
alembic downgrade -1  # Test rollback
alembic upgrade head  # Apply again
```

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