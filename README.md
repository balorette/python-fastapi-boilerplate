# IAC API

A modern, production-ready FastAPI REST API for Infrastructure as Code operations.

## 🚀 Features

- **FastAPI Framework**: High-performance, modern Python ### 🗄️ Additional Database Management

```bash
# Switch between databases
./scripts/setup-db.sh sqlite      # Switch to SQLite
./scripts/setup-db.sh postgresql  # Switch to PostgreSQL

# View current database configuration
grep "DATABASE_URL" .env
```

### ⚡ uv Quick Reference

```bash
# Fast setup (recommended)
./scripts/setup-dev-uv.sh

# Daily commands
uv run uvicorn main:app --reload    # Start server
uv run pytest                      # Run tests
uv pip install package-name        # Install packages

# Why uv?
# • 10-100x faster than pip
# • Better dependency resolution
# • Modern Python tooling
# Learn more: https://docs.astral.sh/uv/
```

## 🔧 Developmentork
- **Async Support**: Full asynchronous support with SQLAlchemy and PostgreSQL/SQLite
- **Flexible Database**: SQLite for development (default), PostgreSQL for production
- **Authentication**: JWT-based authentication with OAuth2
- **Database**: SQLite (dev) or PostgreSQL (prod) with SQLAlchemy ORM and Alembic migrations
- **Caching**: Redis for session management and caching
- **Testing**: Comprehensive test suite with pytest
- **Code Quality**: Pre-commit hooks, Black, isort, flake8, and mypy
- **Docker**: Multi-stage Docker builds and docker-compose for development
- **Documentation**: Automatic API documentation with Swagger/OpenAPI
- **Monitoring**: Structured logging with configurable levels
- **Security**: Built-in security best practices and CORS handling

## 📋 Requirements

- Python 3.11+
- Package Manager: **uv** (recommended) or pip + venv
- SQLite (included with Python) OR PostgreSQL 13+
- Redis 6+ (optional, for caching)
- Docker & Docker Compose (optional)

### 📦 Package Manager Options

**Option 1: uv (Recommended - Fast & Modern)**
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
# or
pip install uv
```

**Option 2: Traditional pip + venv**
Standard Python tooling (already installed with Python)

## 🛠️ Quick Start

### Option 1: Using Scripts (Recommended)

**With uv (fastest):**
```bash
git clone <repository-url>
cd iac-api
./scripts/setup-dev-uv.sh    # New uv-based setup script
```

**With traditional tools:**
```bash
git clone <repository-url>
cd iac-api
./scripts/setup-dev.sh       # Traditional pip + venv setup
```

**Continue with either method:**
```bash
# Configure environment (if needed)
cp .env.example .env
# Edit .env with your configuration

# Start the development server
./scripts/run-dev.sh
```

### Option 2: Using Docker Compose

**SQLite version (simpler, faster start):**
```bash
docker-compose -f docker-compose.sqlite.yml up -d
```

**PostgreSQL version (full features):**
```bash
docker-compose up -d
```

**View logs:**
```bash
docker-compose logs -f api
```

### Option 3: Manual Setup

**With uv (recommended):**
```bash
# Create project and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# Setup environment and database
cp .env.example .env
./scripts/setup-db.sh sqlite

# Start the server
uv run uvicorn main:app --reload
```

**With traditional tools:**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment and database
cp .env.example .env
./scripts/setup-db.sh sqlite

# Start the server
uvicorn main:app --reload
```

## 📚 API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## 🗄️ Database Setup

### Quick Start with SQLite (Recommended for Development)

The project uses **SQLite by default** for development - no additional setup required!

1. **Automatic setup** (SQLite is configured by default):
   ```bash
   ./scripts/setup-dev.sh  # SQLite is set up automatically
   ```

2. **Start developing immediately:**
   ```bash
   ./scripts/run-dev.sh
   ```

### Using PostgreSQL (Production or Advanced Development)

If you need PostgreSQL features or want to match your production environment:

1. **Install PostgreSQL** and create a database:
   ```sql
   CREATE DATABASE iac_api_db;
   CREATE USER api_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE iac_api_db TO api_user;
   ```

2. **Configure PostgreSQL:**
   ```bash
   ./scripts/setup-db.sh postgresql
   ```

3. **Or manually update .env file:**
   ```env
   # Comment out SQLite settings
   #DATABASE_URL=sqlite:///./app.db
   #DATABASE_URL_ASYNC=sqlite+aiosqlite:///./app.db
   
   # Uncomment and configure PostgreSQL
   DATABASE_URL=postgresql://api_user:your_password@localhost:5432/iac_api_db
   DATABASE_URL_ASYNC=postgresql+asyncpg://api_user:your_password@localhost:5432/iac_api_db
   ```

### Database Migrations

```bash
# Initialize migrations (run once)
alembic init alembic  # Already done in this project

# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

## 🧪 Testing

### Run all tests:
```bash
./scripts/run-tests.sh
```

### Run specific test file:
```bash
pytest tests/test_users.py -v
```

### Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

### �️ Additional Database Management

```bash
# Switch between databases
./scripts/setup-db.sh sqlite      # Switch to SQLite
./scripts/setup-db.sh postgresql  # Switch to PostgreSQL

# View current database configuration
grep "DATABASE_URL" .env
```

### Code Formatting and Linting

```bash
# Run all code quality checks
./scripts/lint.sh

# Or run individually
black .                 # Format code
isort .                 # Sort imports
flake8 .               # Lint code
mypy app/              # Type check
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

## 📁 Project Structure

```
iac-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API endpoints
│   │       └── api.py         # Router aggregation
│   ├── core/
│   │   ├── config.py          # Configuration settings
│   │   ├── database.py        # Database setup
│   │   ├── security.py        # Authentication & security
│   │   └── logging.py         # Logging configuration
│   ├── models/                # SQLAlchemy models
│   ├── schemas/               # Pydantic schemas
│   ├── services/              # Business logic
│   └── utils/                 # Utility functions
├── tests/                     # Test files
├── docs/                      # Documentation
├── scripts/                   # Development scripts
├── docker-compose.yml         # Development environment
├── docker-compose.prod.yml    # Production environment
├── Dockerfile                 # Docker image
├── requirements.txt           # Python dependencies
├── pyproject.toml            # Project configuration
└── main.py                   # Application entry point
```

## 🚀 Deployment

### Production Deployment

1. **Build and run with docker-compose:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Or build Docker image:**
   ```bash
   docker build -t iac-api .
   docker run -p 8000:8000 iac-api
   ```

### Environment Variables

Key environment variables for production:

```env
ENVIRONMENT=production
SECRET_KEY=your-super-secret-key
DATABASE_URL=postgresql://user:password@host:5432/database
REDIS_URL=redis://host:6379/0
BACKEND_CORS_ORIGINS=["https://yourdomain.com"]
```

## 🔐 Security

- JWT tokens for authentication
- Password hashing with bcrypt
- CORS configuration
- SQL injection protection via SQLAlchemy
- Input validation with Pydantic
- Security headers and middleware

## 📊 Monitoring and Logging

- Structured logging with configurable levels
- Health check endpoints
- Request/response logging
- Error tracking and reporting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:

- Check the [API Documentation](http://localhost:8000/api/v1/docs)
- Review the test files for usage examples
- Open an issue for bugs or feature requests

## 🔄 Next Steps

After setup, consider implementing:

- [ ] Database migrations with Alembic
- [ ] User authentication and authorization
- [ ] Rate limiting and request throttling
- [ ] Caching strategies
- [ ] Background tasks with Celery
- [ ] Monitoring with Prometheus/Grafana
- [ ] CI/CD pipeline
- [ ] API versioning strategy
- [ ] Comprehensive error handling
- [ ] Database backup strategies