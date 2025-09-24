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
   BACKEND_CORS_ORIGINS=["https://yourdomain.com"]
   LOG_LEVEL=INFO
   
   # Google OAuth Configuration (required for OAuth features)
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   GOOGLE_REDIRECT_URI=https://yourdomain.com/api/v1/auth/oauth/google/callback
   ```

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