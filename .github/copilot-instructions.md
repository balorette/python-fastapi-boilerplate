# GitHub Copilot Instructions for AI-Lab

## 0) Repository Facts

* **Project name:** fastAPI 
* **Primary stack:** Python 3.12+, FastAPI, SQLAlchemy (async), PostgreSQL
* **Package manager:** UV (required)
* **CI:** GitHub Actions
* **Testing:** pytest
* **Code quality:** Ruff (linting + formatting)

### Key Configuration and Information

This project is a FastAPI + Postgres solution with support for SQLLite for Dev. This serves as a starting point for building out robust enterprise grade APIs in Python FastAPI and PostgreSQL for data persistence (SQLLite enabled in dev).

Environment variables should be configured in `.env` (copy from `.env.example`).

**Architecture Pattern:** Repository + Service + DTO pattern with separate API schemas and database models.

---

## 1) How I Want Copilot to Work Here

1. **Start with a plan.** Before writing code, generate a brief **task plan**:
   * Context summary (1–2 lines)
   * **TODO checklist** of concrete steps
   * Affected files/modules (models, schemas, repositories, services, routes)
   * Database migration considerations
   * Acceptance criteria / test cases

2. **Ask if unsure.** If requirements are ambiguous, ask up to 3 clarifying questions.

3. **Prefer async patterns** where they make sense, but ensure ACID compliance for data operations.

4. **Follow repo standards** (async/await, repository pattern, separate models/schemas, RESTful design).

5. **Cite references** (files, lines) in PR descriptions when relevant.

> When I say *"do X"*, produce the plan + checklist first. After I confirm (or after 1 minute with no reply), implement.

---

## 2) Code Style & Quality

* **Package Management:** Always use UV commands (`uv add`, `uv run`, `uv sync`) - never pip
* **Formatting & Linting:** Use Ruff for both linting and formatting
* **Async Patterns:** Prefer async/await for I/O operations, database queries, and API calls
* **Naming:** 
  * Snake_case for functions, variables, file names
  * PascalCase for classes, schemas, models
  * UPPER_CASE for constants and environment variables
* **Type Hints:** 
  * Required on all function signatures and class attributes
  * Use modern Python typing (`list[str]` not `List[str]`)
  * Prefer Pydantic models for data validation

**Import Organization:**
```python
# Standard library
import asyncio
from datetime import datetime

# Third party
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

# Local imports
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.repositories.user_repository import UserRepository
```
## 3) Testing Standards

* **Framework:** pytest with pytest-asyncio
* **Coverage:** Aim for >90% test coverage
* **Test Structure:**
  * Unit tests: `tests/unit/`
  * Integration tests: `tests/integration/`
  * API tests: `tests/api/`
* **Database Testing:** Use test database with transaction rollback
* **AI Agent Testing:** Mock external AI API calls, test logic separately
* **Async Testing:** Use `@pytest.mark.asyncio` for async test functions

**Test Naming Convention:**
```python
async def test_create_user_returns_created_user():
    # Given
    # When  
    # Then
```

---

## 4) Security & Privacy

* **Never hardcode secrets** - use environment variables and Pydantic settings
* **Input validation:** All request data through Pydantic schemas
* **SQL Injection:** Always use SQLAlchemy ORM, never raw queries
* **Authentication:** Follow FastAPI security best practices (OAuth2, JWT)
* **AI API Keys:** Store securely, implement rate limiting and usage tracking
* **Database:** Use connection pooling, prepared statements
* **CORS:** Configure appropriately for frontend integration

---

## 5) FastAPI Architecture Patterns

### Project Structure
```
app/
├── api/              # API route handlers
│   ├── v1/
│   │   ├── routes/   # Route definitions
│   │   └── deps.py   # Dependencies
├── core/             # Core functionality
│   ├── config.py     # Settings/configuration
│   ├── database.py   # Database connection
│   └── security.py   # Auth/security
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic models (request/response)
├── repositories/     # Data access layer
├── services/         # Business logic
├── agents/           # AI agent implementations
└── utils/            # Shared utilities
```

### Repository Pattern
```python
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user_data: UserCreate) -> User:
        # Implementation
        
    async def get_by_id(self, user_id: int) -> User | None:
        # Implementation
```

### Service Layer
```python
class UserService:
    def __init__(self, user_repo: UserRepository, ai_agent: UserAIAgent):
        self.user_repo = user_repo
        self.ai_agent = ai_agent
    
    async def create_user_with_ai_profile(self, user_data: UserCreate) -> UserResponse:
        # Business logic combining repository and AI agent
```

### API Routes
```python
@router.post("/users/", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.create_user_with_ai_profile(user_data)
```
---

## 6) Database Patterns

* **Async SQLAlchemy:** Always use async session and queries
* **Models vs Schemas:** Keep SQLAlchemy models separate from Pydantic schemas
* **Migrations:** Use Alembic for database migrations
* **Transactions:** Ensure ACID compliance, use database transactions properly
* **Connection Management:** Use dependency injection for database sessions

**Model Definition:**
```python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

**Schema Definition:**
```python
class UserCreate(BaseModel):
    email: EmailStr
    name: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
```
## 8) RESTful API Design

* **HTTP Methods:** GET (read), POST (create), PUT (update), PATCH (partial update), DELETE
* **Status Codes:** 
  * 200 (OK), 201 (Created), 204 (No Content)
  * 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)
  * 422 (Validation Error), 500 (Server Error)
* **URL Structure:** `/api/v1/resources/{id}/sub-resources`
* **Pagination:** Use limit/offset with proper response headers
* **Filtering:** Query parameters for filtering, sorting
* **Versioning:** URL path versioning (`/api/v1/`)

**Response Format:**
```python
class APIResponse(BaseModel):
    success: bool
    data: Any | None = None
    message: str | None = None
    errors: list[str] | None = None
```

---

## 9) Error Handling

* **Custom Exceptions:** Domain-specific exception classes
* **Global Exception Handler:** Catch and format all errors consistently
* **Validation Errors:** Let Pydantic handle with proper error messages
* **AI Service Errors:** Graceful fallbacks and user-friendly messages
* **Database Errors:** Proper transaction rollback and error reporting

---

## 10) Performance Optimization

* **Database:** Use proper indexes, connection pooling, query optimization
* **Caching:** Redis for session storage and frequently accessed data
* **Async Operations:** Non-blocking I/O for external APIs and AI services  
* **Background Tasks:** Long-running AI operations in background
* **Response Compression:** Enable gzip compression
* **Database Query Optimization:** Avoid N+1 queries, use proper joins

---

## 11) Issue → Plan → Implement Loop

When assigned an issue or given a request, Copilot should:

1. **Restate** the request in 1–2 sentences
2. **Produce a task plan** with TODO checklist
3. **Identify affected components**: models, schemas, repositories, services, routes
4. **Consider database changes**: migrations, indexes
5. **Propose test cases**: unit, integration, API tests
6. **Security considerations**: auth, validation, rate limiting

**Example Task Plan:**
```
Context: Add AI-powered content generation endpoint for blog posts.

TODO
- [ ] Create ContentRequest/ContentResponse schemas
- [ ] Add Content SQLAlchemy model with migration  
- [ ] Implement ContentRepository with CRUD operations
- [ ] Create ContentGeneratorAgent service
- [ ] Add ContentService with business logic
- [ ] Create POST /api/v1/content/ endpoint
- [ ] Add rate limiting and auth middleware
- [ ] Unit tests for repository, service, agent
- [ ] Integration tests for full workflow
- [ ] API tests for endpoint

Files
- app/schemas/content.py (new)
- app/models/content.py (new)  
- alembic/versions/xxx_add_content_table.py (new)
- app/repositories/content_repository.py (new)
- app/agents/content_generator.py (new)
- app/services/content_service.py (new)
- app/api/v1/routes/content.py (new)
- tests/unit/test_content_*.py (new)
- tests/integration/test_content_workflow.py (new)
- tests/api/test_content_endpoints.py (new)

Acceptance Criteria
- Generate blog content from user prompts
- Store generation history in database
- Rate limit: 10 requests/hour per user
- Response time < 30s for generation
- Proper error handling for AI service failures
```

---

## 12) Don'ts

* **Never use pip** - always use UV commands
* **Don't mix sync/async** - prefer async throughout the stack
* **Don't put business logic in route handlers** - use service layer
* **Don't commit secrets** or `.env` files
* **Don't skip database migrations** for schema changes
* **Don't hardcode AI prompts** - make them configurable
* **Don't ignore rate limiting** for AI services
* **Don't use raw SQL queries** - use SQLAlchemy ORM

---

## 14) PR Checklist (Auto-include by Copilot)

* [ ] Plan & TODOs completed
* [ ] Database migration created (if needed)
* [ ] Models, schemas, repositories implemented
* [ ] Service layer with business logic
* [ ] API routes with proper HTTP methods/status codes
* [ ] Authentication/authorization applied
* [ ] Rate limiting configured (for AI endpoints)
* [ ] Unit tests (>90% coverage)
* [ ] Integration tests
* [ ] API tests
* [ ] Error handling implemented
* [ ] Type hints on all functions
* [ ] Ruff linting passes
* [ ] Documentation updated
* [ ] Environment variables documented

---

## 15) Maintenance

* Keep this file updated when architecture patterns change
* Review and update AI agent patterns as Pydantic-AI evolves
* Update database patterns as SQLAlchemy async patterns mature
* Maintain test patterns and coverage requirements
* Keep security practices current with FastAPI updates