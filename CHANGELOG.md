# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Standardised current-user retrieval on `/api/v1/users/me` and removed the legacy `/api/v1/auth/me` alias to keep the API surface DRY.
- OAuth user provisioning now derives unique usernames from the email local-part, ensuring deterministic slugs (with numeric suffixes when needed).
- Improved error handling for unsupported auth providers and invalid logins so callers receive clear 4xx responses instead of generic 500s.
- Updated `scripts/setup-db.sh` to run Alembic migrations automatically (with fallback to `init_db.py`) and committed `alembic.ini` for CLI access.

### Fixed
- Ensured metadata imports execute before table creation so `init_db.py` and Alembic operate against the complete schema even on fresh clones.

### Added
- Regression tests that cover the `/api/v1/users/me` endpoint after local login to guarantee future compatibility.

## [0.2.0] - 2025-09-24

### Added - Google OAuth Integration

#### 🔐 Authentication Features
- **Google OAuth 2.0 Support**: Complete OAuth integration alongside existing local authentication
- **Auto-linking Accounts**: Automatically links Google accounts to existing users by email
- **OAuth-Only Users**: Support for users who authenticate only via Google (no password required)
- **Refresh Token Storage**: Stores Google refresh tokens for offline access
- **Unified Token Validation**: Both local JWT and Google ID tokens work with all protected endpoints
- **CSRF Protection**: Session-based state validation for OAuth flows

#### 🏗️ New Components
- **OAuth Provider Framework** (`app/services/oauth/`): Async provider interface, factory, and Google implementation
- **OAuth Schemas** (`app/schemas/oauth.py`): Pydantic models for OAuth flows and Google user data
- **OAuth Endpoints**: 
  - `POST /api/v1/auth/authorize` - Start OAuth flow
  - `GET /api/v1/auth/callback/{provider}` - Handle OAuth callbacks
- **OAuth Test Suite** (`test_oauth.py`): Comprehensive testing for OAuth functionality

#### 🗄️ Database Changes
- **Extended User Model**: Added OAuth fields to support Google authentication:
  - `oauth_provider` - OAuth provider name (e.g., "google")
  - `oauth_id` - Provider-specific user ID
  - `oauth_email_verified` - Email verification status from provider
  - `oauth_refresh_token` - Stored refresh token for offline access
  - `hashed_password` - Now optional for OAuth-only users

#### 📦 Dependencies
- **google-auth>=2.23.0**: Google authentication library
- **google-auth-oauthlib>=1.1.0**: Google OAuth 2.0 library

#### 🔧 Configuration
- **Environment Variables**: Added Google OAuth configuration
  - `GOOGLE_CLIENT_ID` - Google OAuth client ID
  - `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
  - `GOOGLE_REDIRECT_URI` - OAuth callback URL
- **Session Middleware**: Added for OAuth state management

#### 📚 Documentation
- **OAUTH_IMPLEMENTATION.md**: Complete OAuth implementation guide
- **IMPLEMENTATION_COMPLETE.md**: Implementation status and checklist
- Updated **README.md** with OAuth setup instructions
- Updated **docs/architecture.md** with OAuth architecture details
- Updated **docs/deployment.md** with OAuth environment variables

#### 🛠️ Development Tools
- **OAuth Migration Script** (`scripts/migrate-oauth.sh`): Upgrade existing installations
- **Demo OAuth Server** (`demo_oauth_server.py`): Quick testing server
- **Comprehensive Test Suite**: End-to-end OAuth testing

### Enhanced

#### 🔒 Security Improvements
- **Google ID Token Validation**: Uses Google's public keys for secure token verification
- **Enhanced Authentication Dependencies**: Unified authentication supporting both token types
- **Email Verification Tracking**: Monitors OAuth provider email verification status

#### 🏗️ Architecture Updates
- **Unified Authentication System**: Seamless integration of local and OAuth authentication
- **Enhanced User Service**: Added OAuth user creation and management methods
- **Extended Repository Layer**: Added OAuth-specific query methods

#### 📖 Documentation Updates
- Updated all documentation to reflect OAuth capabilities
- Added comprehensive setup guides and examples
- Enhanced API documentation with OAuth endpoints

### Fixed
- **Alembic Configuration**: Fixed interpolation syntax error in `alembic.ini`
- **Database Migration**: Resolved migration creation issues

### Technical Details

#### OAuth Flow Implementation
1. **Authorization Request**: Client requests OAuth URL with CSRF protection
2. **User Authorization**: User authorizes with Google and returns with code
3. **Token Exchange**: Server exchanges code for access/refresh tokens and user info
4. **User Creation/Login**: Server creates or updates user and returns JWT for app

#### Security Measures
- **CSRF Protection**: State parameter validates OAuth requests
- **Token Verification**: Google ID tokens verified using Google's public certificates
- **Session Management**: Secure session middleware for OAuth state
- **Email Verification**: Tracks and validates email verification from OAuth provider

#### Backward Compatibility
- **Zero Breaking Changes**: All existing authentication continues to work
- **Unified API**: All endpoints work with both local JWT and Google ID tokens
- **Progressive Enhancement**: OAuth features can be added to existing deployments

## [0.1.0] - 2025-09-23

### Added - Initial Release
- **FastAPI Framework**: High-performance, modern Python web framework
- **Local Authentication**: JWT-based authentication with user registration/login
- **Database Support**: SQLite for development, PostgreSQL for production
- **Async Support**: Full asynchronous support with SQLAlchemy
- **Testing**: Comprehensive test suite with pytest
- **Code Quality**: Pre-commit hooks, Black, isort, flake8, and mypy
- **Docker Support**: Multi-stage Docker builds and docker-compose
- **Documentation**: Automatic API documentation with Swagger/OpenAPI
- **Development Tools**: Setup scripts, development environment configuration

---

### Migration Guide (0.1.0 → 0.2.0)

#### For Existing Installations

1. **Update Dependencies**:
   ```bash
   # Using the migration script (recommended)
   ./scripts/migrate-oauth.sh
   
   # Or manually
   pip install google-auth>=2.23.0 google-auth-oauthlib>=1.1.0
   ```

2. **Update Configuration**:
   ```bash
   # Add to your .env file
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback/google
   ```

3. **Run Database Migration**:
   ```bash
   alembic upgrade head
   ```

4. **Set Up Google OAuth**:
   - Create OAuth 2.0 Client ID in Google Cloud Console
   - Enable Google+ API
   - Configure redirect URIs

#### For New Installations

Follow the standard setup procedure - OAuth support is included by default:

```bash
git clone <repository-url>
cd iac-api
./scripts/setup-dev-uv.sh  # or ./scripts/setup-dev.sh
```

Then configure your Google OAuth credentials in the `.env` file.
