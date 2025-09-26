# FastAPI OAuth Integration - TODO & Roadmap

## 🎯 Current Status

### ✅ Completed Features
- [x] Local JWT authentication system
- [x] Google OAuth integration with auto-linking
- [x] Database schema for OAuth providers
- [x] Unified authentication dependencies
- [x] Admin CLI initialization
- [x] Comprehensive test coverage (78%)

### 🏗️ Architecture Foundation
- [x] Repository + Service + DTO pattern
- [x] Async SQLAlchemy with PostgreSQL/SQLite
- [x] Pydantic v2 schemas with validation
- [x] Custom exception hierarchy
- [x] Security middleware and CSRF protection

---

## 🎯 Phase 1: Code Quality & Standards (High Priority)

### **Immediate Tasks (1-2 days)**
- [ ] **Add Ruff Configuration**
  ```toml
  # Add to pyproject.toml
  [tool.ruff]
  target-version = "py312"
  line-length = 88
  select = ["E", "W", "F", "I", "B", "C4", "UP"]
  ```
- [ ] **Modernize Type Hints**
  - [ ] Replace `List[str]` → `list[str]`
  - [ ] Replace `Dict[str, Any]` → `dict[str, Any]`  
  - [ ] Replace `Optional[str]` → `str | None`
  - [ ] Add return type annotations to all functions
- [ ] **Reorganize Test Structure**
  ```
  tests/
  ├── unit/           # Pure unit tests
  ├── integration/    # Service integration tests  
  ├── api/           # API endpoint tests
  └── conftest.py
  ```
- [ ] **Add GitHub Actions CI**
  ```yaml
  # .github/workflows/ci.yml
  - name: Run tests
    run: uv run pytest --cov=app --cov-report=xml
  - name: Run linting
    run: uv run ruff check .
  ```

### **Code Quality Improvements**
- [ ] **Standardize API Response Format**
  ```python
  class APIResponse[T](BaseModel):
      success: bool
      data: T | None = None
      message: str | None = None
      errors: list[str] | None = None
  ```
- [ ] **Improve Test Coverage** (Target: >90%)
  - [ ] Add unit tests for all service methods
  - [ ] Add integration tests for OAuth flows
  - [ ] Add API tests for all endpoints
- [ ] **Add Rate Limiting**
  - [ ] OAuth endpoints: 10 requests/hour per IP
  - [ ] Auth endpoints: 5 login attempts/minute
  - [ ] API endpoints: 100 requests/minute per user

---

## 🔐 Phase 2: Multi-Provider OAuth (Medium Priority)

### **Microsoft Entra ID Integration (3-4 days)**

#### **Planning & Research**
- [ ] **Study Microsoft Identity Platform**
  - [ ] Research Entra ID OAuth 2.0 flow
  - [ ] Understand Microsoft Graph API scopes
  - [ ] Review tenant-specific vs multi-tenant apps
  - [ ] Document required Azure app registration steps

#### **Implementation Tasks**
- [ ] **Extend OAuth Service**
  ```python
  # app/services/oauth.py
  class EntraIDOAuthService:
      async def get_authorization_url(self) -> tuple[str, str]
      async def exchange_code_for_tokens(self, code: str) -> dict[str, Any]
      async def validate_id_token(self, id_token: str) -> dict[str, Any]
      async def get_user_info(self, access_token: str) -> dict[str, Any]
  ```

- [ ] **Add Configuration**
  ```python
  # app/core/config.py
  ENTRA_CLIENT_ID: str = Field(..., description="Microsoft Entra client ID")
  ENTRA_CLIENT_SECRET: str = Field(..., description="Microsoft Entra client secret")  
  ENTRA_TENANT_ID: str = Field(..., description="Microsoft Entra tenant ID")
  ENTRA_REDIRECT_URI: str = Field(..., description="Entra redirect URI")
  ```

- [ ] **Create OAuth Endpoints**
  ```python
  # app/api/v1/endpoints/auth.py
  @router.get("/oauth/entra/authorize")
  async def entra_authorize()
  
  @router.post("/oauth/entra/callback")  
  async def entra_callback()
  ```

- [ ] **Update Database Schema**
  ```sql
  -- Migration: Add Entra ID support
  ALTER TABLE users ADD COLUMN entra_tenant_id VARCHAR(255);
  UPDATE users SET oauth_provider = 'entra' WHERE oauth_provider = 'microsoft';
  ```

#### **Testing Strategy**
- [ ] **Unit Tests**
  - [ ] Test Entra ID token validation
  - [ ] Test user profile mapping
  - [ ] Test tenant ID handling
- [ ] **Integration Tests**  
  - [ ] Test complete Entra OAuth flow
  - [ ] Test account linking with existing users
  - [ ] Test multi-tenant scenarios
- [ ] **API Tests**
  - [ ] Test authorization URL generation
  - [ ] Test callback handling
  - [ ] Test error scenarios

### **Okta Integration (3-4 days)**

#### **Planning & Research**
- [ ] **Study Okta OAuth Implementation**
  - [ ] Research Okta OAuth 2.0 flow and OIDC
  - [ ] Understand Okta domain configuration
  - [ ] Review custom authorization servers
  - [ ] Document Okta app integration setup

#### **Implementation Tasks**
- [ ] **Extend OAuth Service**
  ```python
  # app/services/oauth.py
  class OktaOAuthService:
      async def get_authorization_url(self) -> tuple[str, str]
      async def exchange_code_for_tokens(self, code: str) -> dict[str, Any]
      async def validate_id_token(self, id_token: str) -> dict[str, Any]
      async def get_user_info(self, access_token: str) -> dict[str, Any]
  ```

- [ ] **Add Configuration**
  ```python
  # app/core/config.py
  OKTA_CLIENT_ID: str = Field(..., description="Okta client ID")
  OKTA_CLIENT_SECRET: str = Field(..., description="Okta client secret")
  OKTA_DOMAIN: str = Field(..., description="Okta domain (e.g., dev-123456.okta.com)")
  OKTA_AUTHORIZATION_SERVER_ID: str = Field(default="default", description="Okta auth server")
  ```

- [ ] **Create OAuth Endpoints**
  ```python
  # app/api/v1/endpoints/auth.py  
  @router.get("/oauth/okta/authorize")
  async def okta_authorize()
  
  @router.post("/oauth/okta/callback")
  async def okta_callback()
  ```

- [ ] **Update Database Schema**
  ```sql
  -- Migration: Add Okta organization support
  ALTER TABLE users ADD COLUMN okta_org_url VARCHAR(500);
  ```

#### **Testing Strategy**
- [ ] **Unit Tests**
  - [ ] Test Okta token validation with custom auth servers
  - [ ] Test organization domain handling
  - [ ] Test user profile mapping
- [ ] **Integration Tests**
  - [ ] Test complete Okta OAuth flow
  - [ ] Test custom authorization server integration
  - [ ] Test organization-specific routing
- [ ] **API Tests**
  - [ ] Test authorization URL with custom domains
  - [ ] Test callback with organization context
  - [ ] Test error handling for invalid domains

### **Unified OAuth Architecture**

#### **Provider Abstraction Layer**
- [ ] **Create Base OAuth Provider**
  ```python
  # app/services/oauth/base.py
  class BaseOAuthProvider(ABC):
      @abstractmethod
      async def get_authorization_url(self) -> tuple[str, str]
      @abstractmethod
      async def exchange_code_for_tokens(self, code: str) -> dict[str, Any]
      @abstractmethod
      async def validate_id_token(self, id_token: str) -> dict[str, Any]
      @abstractmethod
      async def get_user_info(self, access_token: str) -> dict[str, Any]
  ```

- [ ] **Provider Factory**
  ```python
  # app/services/oauth/factory.py
  class OAuthProviderFactory:
      _providers: dict[str, type[BaseOAuthProvider]] = {
          "google": GoogleOAuthProvider,
          "entra": EntraIDOAuthProvider,
          "okta": OktaOAuthProvider,
      }

      @classmethod
      def create_provider(cls, provider_name: str) -> BaseOAuthProvider:
          try:
              return cls._providers[provider_name]()
          except KeyError as exc:
              raise ValidationError("Unsupported provider") from exc
  ```

- [ ] **Enhanced User Service**
  ```python
  # app/services/user.py
  async def authenticate_oauth_user(
      self,
      provider: str,
      id_token: str,
      access_token: str
  ) -> User:
      oauth_service = OAuthProviderFactory.create_provider(provider)
      # Unified OAuth authentication logic
  ```

#### **Database Schema Updates**
- [ ] **Enhanced OAuth Fields**
  ```python
  # app/models/user.py
  class User(Base):
      # Existing fields...
      oauth_provider: Mapped[str | None] = mapped_column(String(50))  # google, entra, okta
      oauth_id: Mapped[str | None] = mapped_column(String(255))
      oauth_email_verified: Mapped[bool | None] = mapped_column(Boolean)
      oauth_refresh_token: Mapped[str | None] = mapped_column(Text)
      
      # Provider-specific fields
      entra_tenant_id: Mapped[str | None] = mapped_column(String(255))
      okta_org_url: Mapped[str | None] = mapped_column(String(500))
      
      # OAuth metadata
      oauth_created_at: Mapped[datetime | None] = mapped_column(DateTime)
      oauth_last_login: Mapped[datetime | None] = mapped_column(DateTime)
  ```

#### **Configuration Management**
- [ ] **Provider-Specific Config Sections**
  ```python
  # app/core/config.py
  class OAuthSettings(BaseModel):
      # Google OAuth
      google_client_id: str = Field(..., description="Google OAuth client ID")
      google_client_secret: str = Field(..., description="Google OAuth client secret")
      
      # Microsoft Entra ID
      entra_client_id: str = Field(..., description="Microsoft Entra client ID")  
      entra_client_secret: str = Field(..., description="Microsoft Entra client secret")
      entra_tenant_id: str = Field(..., description="Microsoft Entra tenant ID")
      
      # Okta
      okta_client_id: str = Field(..., description="Okta client ID")
      okta_client_secret: str = Field(..., description="Okta client secret") 
      okta_domain: str = Field(..., description="Okta domain")
      
      # Common settings
      oauth_redirect_base_url: str = Field(..., description="Base URL for OAuth redirects")
  ```

---

## 🚀 Phase 3: Advanced Features (Lower Priority)

### **Enhanced Security (2-3 days)**
- [ ] **Multi-Factor Authentication**
  - [ ] TOTP support for local accounts
  - [ ] SMS verification integration
  - [ ] Backup codes generation
- [ ] **Advanced Session Management**
  - [ ] Redis-backed sessions for OAuth state
  - [ ] Session invalidation across devices
  - [ ] Concurrent session limits
- [ ] **Audit Logging**
  - [ ] Authentication events logging
  - [ ] Failed login attempt tracking
  - [ ] OAuth provider usage analytics

### **User Experience Improvements (1-2 days)**
- [ ] **Account Management**
  - [ ] Link/unlink OAuth providers
  - [ ] Convert OAuth-only to local account
  - [ ] Account deletion with OAuth cleanup
- [ ] **Provider Selection UI Support**
  - [ ] Dynamic provider availability endpoint
  - [ ] Provider-specific branding data
  - [ ] User preference storage

### **Admin & Monitoring (2-3 days)**
- [ ] **Enhanced CLI Tools**
  ```bash
  uv run python -m app.cli create-oauth-app --provider google
  uv run python -m app.cli list-oauth-providers
  uv run python -m app.cli migrate-oauth-users --from google --to entra
  ```
- [ ] **OAuth Analytics Dashboard**
  - [ ] Provider usage statistics
  - [ ] Authentication success rates
  - [ ] User registration sources
- [ ] **Health Checks**
  - [ ] OAuth provider connectivity checks
  - [ ] Token validation endpoint health
  - [ ] Provider-specific health endpoints

### **Performance Optimization (1-2 days)**
- [ ] **Caching Strategy**
  - [ ] Cache OAuth provider public keys
  - [ ] Cache user profile data from providers
  - [ ] Implement token validation caching
- [ ] **Background Tasks**
  - [ ] Async token refresh for long-lived sessions
  - [ ] Periodic OAuth provider health checks
  - [ ] User data synchronization with providers

---

## 🧪 Testing Strategy

### **Comprehensive Test Coverage Goals**
- [ ] **Unit Tests (Target: 95%)**
  - [ ] OAuth service provider implementations
  - [ ] Token validation logic
  - [ ] User profile mapping functions
  - [ ] Configuration validation
- [ ] **Integration Tests (Target: 90%)**  
  - [ ] Complete OAuth flows for each provider
  - [ ] Account linking/unlinking scenarios
  - [ ] Cross-provider user migration
  - [ ] Error handling and edge cases
- [ ] **API Tests (Target: 100%)**
  - [ ] All OAuth endpoints for each provider
  - [ ] Authentication middleware with multiple token types
  - [ ] Rate limiting and security measures
  - [ ] Admin management endpoints

### **Test Data & Mocking Strategy**
- [ ] **Mock OAuth Providers**
  - [ ] Create test OAuth servers for each provider
  - [ ] Generate test ID tokens and access tokens
  - [ ] Simulate provider-specific error conditions
- [ ] **Test User Scenarios**
  - [ ] New users registering via each provider
  - [ ] Existing users linking additional providers
  - [ ] Account conflicts and resolution
  - [ ] Provider account deletions

---

## 📚 Documentation Updates

### **Technical Documentation**
- [ ] **API Documentation**
  - [ ] OAuth endpoints for each provider
  - [ ] Authentication flow diagrams
  - [ ] Error response examples
- [ ] **Architecture Documentation**
  - [ ] Multi-provider OAuth architecture
  - [ ] Security considerations for each provider
  - [ ] Database schema documentation
- [ ] **Deployment Documentation**
  - [ ] OAuth app registration guides for each provider
  - [ ] Environment variable configuration
  - [ ] Production security checklist

### **User-Facing Documentation**
- [ ] **Setup Guides**
  - [ ] Google OAuth setup guide
  - [ ] Microsoft Entra ID setup guide  
  - [ ] Okta integration setup guide
- [ ] **Migration Guides**
  - [ ] Upgrading from single-provider OAuth
  - [ ] Data migration procedures
  - [ ] Rollback procedures

---

## 🎯 Acceptance Criteria

### **Phase 1: Code Quality**
- [ ] Ruff linting passes with zero warnings
- [ ] Test coverage >90% across all modules
- [ ] GitHub Actions CI pipeline passes
- [ ] Modern Python type hints throughout codebase
- [ ] Consistent API response format

### **Phase 2: Multi-Provider OAuth**  
- [ ] Support for Google, Entra ID, and Okta OAuth
- [ ] Unified authentication experience
- [ ] Account auto-linking by email across providers
- [ ] Provider-specific configuration management
- [ ] Comprehensive error handling for all providers

### **Phase 3: Advanced Features**
- [ ] Admin tools for OAuth provider management
- [ ] Performance metrics and monitoring
- [ ] Advanced security features (MFA, audit logs)
- [ ] Complete documentation for all providers
- [ ] Production-ready deployment guides

---

## 🚨 Risk Mitigation

### **Security Considerations**
- [ ] **Token Security**
  - [ ] Secure storage of refresh tokens
  - [ ] Token rotation and expiration policies
  - [ ] Protection against token leakage
- [ ] **Provider Trust**
  - [ ] Validation of OAuth provider certificates
  - [ ] Monitoring for provider API changes
  - [ ] Fallback authentication methods

### **Operational Risks**  
- [ ] **Provider Outages**
  - [ ] Graceful degradation when providers are unavailable
  - [ ] Local authentication fallback options
  - [ ] User notification systems
- [ ] **Data Migration**
  - [ ] Backup strategies for user OAuth data
  - [ ] Rollback procedures for failed migrations
  - [ ] Data consistency validation

---

## 📅 Timeline Estimates

| Phase | Estimated Duration | Dependencies |
|-------|-------------------|--------------|
| **Phase 1: Code Quality** | 3-4 days | None |
| **Phase 2A: Entra ID** | 4-5 days | Phase 1 complete |
| **Phase 2B: Okta** | 4-5 days | Phase 2A complete |
| **Phase 2C: Unified Architecture** | 2-3 days | Phase 2A & 2B complete |
| **Phase 3: Advanced Features** | 5-7 days | Phase 2 complete |
| **Documentation & Polish** | 2-3 days | All phases complete |

**Total Estimated Duration: 20-27 days**

---

## 🎯 Success Metrics

### **Technical Metrics**
- [ ] Test coverage >90% maintained
- [ ] API response time <200ms for OAuth flows
- [ ] Zero critical security vulnerabilities
- [ ] 99.9% OAuth flow success rate

### **User Experience Metrics**
- [ ] <3 clicks for OAuth registration
- [ ] <10 seconds for complete OAuth flow
- [ ] <1% user-reported authentication issues
- [ ] Support for 3+ major OAuth providers

### **Operational Metrics**  
- [ ] Zero deployment issues with OAuth changes
- [ ] <1 hour mean time to recovery for OAuth issues
- [ ] 100% backward compatibility maintained
- [ ] Comprehensive monitoring and alerting in place

---

*Last Updated: September 2025*
*Next Review: After Phase 1 completion*
