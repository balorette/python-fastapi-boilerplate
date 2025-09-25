# FastAPI Boiler Plate

A modern, production-ready FastAPI REST API.

## 🚀 Features

- **FastAPI Framework**: High-performance, modern Python web framework
- **Async Support**: Full asynchronous support with SQLAlchemy and PostgreSQL/SQLite
- **Flexible Database**: SQLite for development (default), PostgreSQL for production
- **Authentication**: JWT-based authentication with OAuth2 + Google OAuth integration
- **Database**: SQLite (dev) or PostgreSQL (prod) with SQLAlchemy ORM and Alembic migrations
- **Caching**: Redis for session management and caching
- **Testing**: Comprehensive test suite with pytest, async support, and UUID-based test isolation
- **Code Quality**: Modern tooling with Ruff (linting, formatting, import sorting) and pre-commit hooks
- **Docker**: Multi-stage Docker builds and docker-compose for development
- **Documentation**: Automatic API documentation with Swagger/OpenAPI
- **Monitoring**: Structured logging with configurable levels
- **Security**: Built-in security best practices and CORS handling

## 📋 Requirements

- Python 3.12+
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

**Pre Work Run docker container**
```bash
docker pull postgres:15.14-alpine3.22
export DB_PASSWORD="mydbpassword"
docker run --name api_postgres -e POSTGRES_PASSWORD=$DB_PASSWORD -d -p 5432:5432 -v api-pgdata:/var/lib/postgresql/data postgres:15.14-alpine3.22
```

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

This project uses **Ruff** for ultra-fast linting, formatting, and import sorting:

```bash
# Run all code quality checks (10-100x faster than legacy tools)
ruff check              # Lint code
ruff format             # Format code
ruff check --fix        # Auto-fix issues

# Run all checks together
./scripts/lint.sh
```

**Ruff Benefits:**
- 10-100x faster than Black, isort, flake8, mypy combined
- Single tool replaces multiple legacy tools
- Modern Python 3.12+ patterns and optimizations
- Automatic import sorting and unused import removal

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

## 🔐 Authentication & Security

### Local Authentication
- JWT tokens for authentication
- Password hashing with bcrypt
- User registration and login endpoints

### Google OAuth Integration
- Complete Google OAuth 2.0 implementation
- Auto-linking accounts by email
- OAuth-only users (no password required)
- Refresh token support for offline access
- CSRF protection with session state validation

### OAuth Setup
1. **Google Cloud Console Setup:**
   ```bash
   # 1. Create OAuth 2.0 Client ID in Google Cloud Console
   # 2. Enable Google+ API
   # 3. Add redirect URI: http://localhost:8000/api/v1/auth/oauth/google/callback
   ```

2. **Environment Configuration:**
   ```env
   # Add to your .env file:
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/oauth/google/callback
   ```

3. **OAuth Endpoints:**
   ```bash
   # Start OAuth flow
   GET  /api/v1/auth/oauth/google/authorize
   
   # Handle OAuth callback
   POST /api/v1/auth/oauth/google/callback
   
   # Both local JWT and Google ID tokens work with:
   GET  /api/v1/auth/me
   ```

### General Security Features
- CORS configuration
- SQL injection protection via SQLAlchemy
- Input validation with Pydantic
- Security headers and middleware
- Google ID token validation using Google's public keys

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

## 🔄 Upgrading from Previous Versions

### Migrating to OAuth Support (v0.2.0)

If you have an existing installation without OAuth support:

```bash
# Run the automated migration script
./scripts/migrate-oauth.sh

# Or follow the manual migration in CHANGELOG.md
```

This will:
- Install OAuth dependencies
- Update environment configuration
- Run database migrations
- Test OAuth functionality

## 📖 Additional Documentation

- **[OAUTH_IMPLEMENTATION.md](OAUTH_IMPLEMENTATION.md)** - Complete Google OAuth setup guide
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and migration guides
- **[docs/architecture.md](docs/architecture.md)** - System architecture and design patterns
- **[docs/deployment.md](docs/deployment.md)** - Production deployment guide
- **[docs/development.md](docs/development.md)** - Development workflow and best practices

## 🔄 Next Steps

After setup, consider implementing:

- [ ] Additional OAuth providers (GitHub, Microsoft, etc.)
- [ ] Rate limiting and request throttling
- [ ] Caching strategies with Redis
- [ ] Background tasks with Celery
- [ ] Monitoring with Prometheus/Grafana
- [ ] CI/CD pipeline
- [ ] API versioning strategy
- [ ] Comprehensive error handling
- [ ] Database backup strategies