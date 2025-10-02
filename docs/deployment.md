# Deployment Guide

## Production Deployment

### Prerequisites

- Docker & Docker Compose
- PostgreSQL database
- Redis instance
- Domain name (optional)
- SSL certificate (recommended)

### Environment Setup

1. **Create production environment file:**
   ```bash
   cp .env.example .env.production
   ```

2. **Update production settings:**
   ```env
   ENVIRONMENT=production
   DEBUG=False
   SECRET_KEY=your-super-secret-production-key
   DATABASE_URL=postgresql://user:password@db-host:5432/database
   REDIS_URL=redis://redis-host:6379/0
   CORS_ALLOW_ORIGINS=["https://yourdomain.com"]
   LOG_LEVEL=INFO
   
   # Google OAuth Configuration (required for OAuth features)
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   GOOGLE_REDIRECT_URI=https://yourdomain.com/api/v1/auth/callback/google
   ```

## Observability & Health Endpoints

The boilerplate exposes a comprehensive set of probes and headers that operators can rely on during rollouts:

### Health Endpoints

#### Aggregate Health Check: `GET /api/v1/health`

Returns comprehensive health information including database latency, system metrics, and configuration status.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-02T12:00:00.000Z",
  "version": "0.1.0",
  "uptime_seconds": 3600,
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5.42,
      "dialect": "postgresql",
      "driver": "asyncpg"
    },
    "system": {
      "status": "healthy",
      "cpu_percent": 25.3,
      "memory_percent": 45.2,
      "disk_percent": 62.1,
      "warnings": []
    },
    "configuration": {
      "status": "healthy",
      "environment": "production",
      "debug": false,
      "audit_log_enabled": true,
      "safety_checks_enabled": true,
      "prometheus_metrics_enabled": true,
      "warnings": []
    },
    "module": {
      "status": "healthy",
      "components": {...},
      "metrics": {...},
      "alerts": []
    }
  }
}
```

**Degraded Response:**
When subsystems are degraded (e.g., audit logging disabled):
```json
{
  "status": "degraded",
  "checks": {
    "configuration": {
      "status": "degraded",
      "warnings": ["Audit logging disabled - compliance risk"]
    }
  }
}
```

#### Liveness Probe: `GET /api/v1/health/liveness`

Simple endpoint to verify the API process is running. Use for Kubernetes liveness probes.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-02T12:00:00.000Z"
}
```

#### Readiness Probe: `GET /api/v1/health/readiness`

Validates database connectivity. Use for Kubernetes readiness probes.

**Success Response (200 OK):**
```json
{
  "status": "ready",
  "timestamp": "2025-10-02T12:00:00.000Z"
}
```

**Failure Response (503 Service Unavailable):**
```json
{
  "detail": {
    "status": "unhealthy",
    "error": "database connection failed",
    "timestamp": "2025-10-02T12:00:00.000Z"
  }
}
```

### Metrics Endpoint

#### Prometheus Metrics: `GET /metrics`

When `PROMETHEUS_METRICS_ENABLED=true`, exposes Prometheus-formatted metrics for scraping.

**Example Response:**
```
# HELP python_info Python platform information
# TYPE python_info gauge
python_info{implementation="CPython",major="3",minor="12",patchlevel="11",version="3.12.11"} 1.0
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 45.23
```

### Response Headers

Every HTTP response includes observability headers when `REQUEST_LOGGING_ENABLED=true`:

**Headers:**
```
X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
X-Process-Time: 12.34
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

- **`X-Correlation-ID`**: Unique request identifier (also appears in structured logs)
- **`X-Process-Time`**: Request processing time in milliseconds
- Security headers (CSP, frame options, etc.) when `SECURITY_HEADERS_ENABLED=true`

### Structured Logging

All logs are emitted as JSON in UTC timezone (`timestamp` ends with `Z`):

**Example Log Entry:**
```json
{
  "timestamp": "2025-10-02T12:00:00.000Z",
  "level": "INFO",
  "logger": "app.middleware",
  "message": "Request completed",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "GET",
  "url": "http://localhost:8000/api/v1/users",
  "status_code": 200,
  "process_time_ms": 12.34
}
```

### Configuration

Adjust observability settings in `.env.production`:

```env
# Middleware toggles
SECURITY_HEADERS_ENABLED=true
SECURITY_CSP_ENABLED=true
PERFORMANCE_MONITORING_ENABLED=true
REQUEST_LOGGING_ENABLED=true

# Header names (customize if needed)
REQUEST_ID_HEADER_NAME=X-Correlation-ID
PROCESS_TIME_HEADER_NAME=X-Process-Time

# Performance thresholds
PERFORMANCE_SLOW_REQUEST_THRESHOLD_MS=1000.0

# Metrics
PROMETHEUS_METRICS_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_DIRECTORY=logs
AUDIT_LOG_ENABLED=true
SAFETY_CHECKS_ENABLED=true

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100
```

**Production Recommendations:**
- Keep all middleware enabled (`*_ENABLED=true`) for maximum observability
- Set `PROMETHEUS_METRICS_ENABLED=true` for Prometheus/Grafana integration
- Use `LOG_LEVEL=INFO` in production (avoid `DEBUG` for performance)
- Ensure `AUDIT_LOG_ENABLED=true` and `SAFETY_CHECKS_ENABLED=true` for compliance
- Adjust rate limits based on your traffic patterns

**Development/Local:**
- Can disable CSP (`SECURITY_CSP_ENABLED=false`) if it interferes with local frontend
- Set `DEBUG=true` and `LOG_LEVEL=DEBUG` for detailed troubleshooting
- Lower rate limits acceptable for local testing

### Docker Deployment

#### Option 1: Docker Compose (Recommended)

1. **Deploy with production compose file:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Check service status:**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   ```

3. **View logs:**
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f api
   ```

#### Option 2: Standalone Docker

1. **Build the image:**
   ```bash
   docker build -t iac-api:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name iac-api \
     -p 8000:8000 \
     --env-file .env.production \
     iac-api:latest
   ```

### Cloud Deployment

#### AWS ECS

1. **Build and push to ECR:**
   ```bash
   # Authenticate Docker to ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   
   # Build and tag image
   docker build -t iac-api .
   docker tag iac-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/iac-api:latest
   
   # Push image
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/iac-api:latest
   ```

2. **Create ECS task definition and service**

#### Google Cloud Run

1. **Build and deploy:**
   ```bash
   gcloud run deploy iac-api \
     --image gcr.io/PROJECT-ID/iac-api \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

#### Azure Container Instances

1. **Deploy to ACI:**
   ```bash
   az container create \
     --resource-group myResourceGroup \
     --name iac-api \
     --image myregistry.azurecr.io/iac-api:latest \
     --ports 8000
   ```

### Kubernetes Deployment

#### Basic Deployment

1. **Create deployment manifest:**
   ```yaml
   # k8s/deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: iac-api
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: iac-api
     template:
       metadata:
         labels:
           app: iac-api
       spec:
         containers:
         - name: iac-api
           image: iac-api:latest
           ports:
           - containerPort: 8000
           env:
           - name: DATABASE_URL
             valueFrom:
               secretKeyRef:
                 name: iac-api-secrets
                 key: database-url
   ```

2. **Create service manifest:**
   ```yaml
   # k8s/service.yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: iac-api-service
   spec:
     selector:
       app: iac-api
     ports:
     - port: 80
       targetPort: 8000
     type: LoadBalancer
   ```

3. **Deploy to cluster:**
   ```bash
   kubectl apply -f k8s/
   ```

### Database Setup

#### PostgreSQL

1. **Create database and user:**
   ```sql
   CREATE DATABASE iac_api_production;
   CREATE USER api_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE iac_api_production TO api_user;
   ```

2. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

#### Managed Database Services

- **AWS RDS**: Use PostgreSQL RDS instance
- **Google Cloud SQL**: PostgreSQL instance
- **Azure Database**: PostgreSQL service

### SSL/TLS Configuration

#### Using Nginx Reverse Proxy

1. **Nginx configuration:**
   ```nginx
   server {
       listen 443 ssl;
       server_name yourdomain.com;
       
       ssl_certificate /path/to/certificate.crt;
       ssl_certificate_key /path/to/private.key;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

#### Using Traefik

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  traefik:
    image: traefik:v2.9
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - acme_data:/acme.json

  api:
    build: .
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`yourdomain.com`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
```

### Monitoring and Logging

#### Application Logging

1. **Configure structured logging:**
   ```env
   LOG_LEVEL=INFO
   LOG_FORMAT=json
   ```

2. **Set up log aggregation:**
   - ELK Stack (Elasticsearch, Logstash, Kibana)
   - Fluentd
   - Cloud logging services

#### Health Monitoring

1. **Health check endpoints:**
   - Basic: `/health`
   - Detailed: `/api/v1/health/detailed`

2. **External monitoring:**
   - Uptime monitoring services
   - Application performance monitoring (APM)

#### Metrics Collection

```python
# Future: Prometheus metrics
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('requests_total', 'Total requests')
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')
```

### Backup and Recovery

#### Database Backups

1. **Automated backups:**
   ```bash
   # Daily backup script
   #!/bin/bash
   BACKUP_DIR="/backups"
   DATE=$(date +%Y%m%d_%H%M%S)
   pg_dump $DATABASE_URL > "$BACKUP_DIR/backup_$DATE.sql"
   ```

2. **Cloud backup solutions:**
   - AWS RDS automated backups
   - Google Cloud SQL backups
   - Azure Database backups

#### Application State

- Stateless application design minimizes backup needs
- Configuration managed through environment variables
- User data stored in database (covered by DB backups)

### Scaling

#### Horizontal Scaling

1. **Load balancing:**
   - Multiple application instances
   - Database connection pooling
   - Session management via Redis

2. **Auto-scaling:**
   ```yaml
   # Kubernetes HPA
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: iac-api-hpa
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: iac-api
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
   ```

#### Vertical Scaling

- Increase container resources (CPU, memory)
- Database instance scaling
- Redis instance sizing

### Security

#### Container Security

1. **Use non-root user:**
   ```dockerfile
   RUN adduser --disabled-password --gecos '' --shell /bin/bash user
   USER user
   ```

2. **Minimal base image:**
   ```dockerfile
   FROM python:3.11-slim
   ```

3. **Security scanning:**
   ```bash
   docker scan iac-api:latest
   ```

#### Network Security

- Use HTTPS/TLS
- Configure firewalls
- Network segmentation
- VPC/private networks

#### Environment Security

- Rotate secrets regularly
- Use secret management services
- Limit access permissions
- Enable audit logging

### Troubleshooting

#### Common Issues

1. **Container won't start:**
   ```bash
   docker logs iac-api
   ```

2. **Database connection errors:**
   ```bash
   # Test database connectivity
   docker exec -it iac-api python -c "from app.core.database import engine; engine.connect()"
   ```

3. **Performance issues:**
   - Check resource usage
   - Monitor database queries
   - Review application logs

#### Debugging Production Issues

1. **Enable debug logging temporarily:**
   ```env
   LOG_LEVEL=DEBUG
   ```

2. **Access container shell:**
   ```bash
   docker exec -it iac-api /bin/bash
   ```

3. **Check service dependencies:**
   ```bash
   # Health checks
   curl http://localhost:8000/health
   curl http://localhost:8000/api/v1/health/detailed
   ```

### Maintenance

#### Updates and Patches

1. **Security updates:**
   ```bash
   # Update base image
   docker pull python:3.11-slim
   
   # Rebuild application
   docker build -t iac-api:latest .
   ```

2. **Application updates:**
   ```bash
   # Rolling update in Kubernetes
   kubectl set image deployment/iac-api iac-api=iac-api:new-version
   ```

#### Database Maintenance

1. **Run migrations:**
   ```bash
   docker exec -it iac-api alembic upgrade head
   ```

2. **Database optimization:**
   - Regular VACUUM and ANALYZE
   - Index maintenance
   - Query performance monitoring
