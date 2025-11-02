# Docker Setup Guide

This is a production-ready Docker configuration for the AI Assistant application.

## Services

- **nginx** (i-nginx): Reverse proxy on port 80/443
- **frontend** (i-frontend): Node.js app on port 3000
- **backend** (i-backend): Python FastAPI app on port 8000
- **celery-worker** (i-celery-worker): Celery worker for background tasks
- **celery-beat** (i-celery-beat): Celery beat scheduler
- **postgres** (i-postgres): PostgreSQL database on port 5432
- **redis** (i-redis): Redis cache/broker on port 6379
- **minio** (i-minio): MinIO object storage on port 9000 (console: 9001)

## Quick Start

1. **Setup environment:**
   ```bash
   ./scripts/docker-setup.sh
   ```

2. **Manual setup (alternative):**
   ```bash
   # Copy environment file
   cp .env.example .env
   
   # Build and start services
   docker-compose up -d --build
   ```

## Configuration

### Environment Variables
Edit `.env` file to customize:
- Database credentials
- Redis password
- MinIO credentials
- JWT secrets
- API URLs

### Celery Configuration
The Celery app path is configured as `app.celery_app:celery_app`. To change this:
1. Update the `command` in docker-compose.yml for celery-worker and celery-beat
2. Update the healthcheck commands
3. Ensure your Celery app is properly configured in your Python code

## Health Checks

All services include health checks:
- **Backend**: `curl http://localhost:8000/health`
- **Frontend**: `curl http://localhost:3000`
- **Postgres**: `pg_isready`
- **Redis**: `redis-cli ping`
- **MinIO**: `curl http://localhost:9000/minio/health/live`
- **Celery**: `celery inspect ping`

## Volumes

Named volumes for data persistence:
- `postgres_data`: PostgreSQL data
- `redis_data`: Redis data
- `minio_data`: MinIO object storage

## Security Features

- Non-root users in containers
- Minimal base images (Alpine/slim)
- Multi-stage builds for frontend
- Comprehensive .dockerignore
- Security headers in nginx
- Rate limiting
- Health checks

## Development vs Production

This configuration is optimized for production. For development:
- Remove `restart: unless-stopped`
- Add volume mounts for live code reloading
- Use development environment variables
- Enable debug logging

## Useful Commands

```bash
# View logs
docker-compose logs -f [service-name]

# Restart a service
docker-compose restart [service-name]

# Scale workers
docker-compose up -d --scale celery-worker=3

# Execute commands in containers
docker-compose exec backend bash
docker-compose exec postgres psql -U postgres -d app_db

# Clean up
docker-compose down -v  # Removes volumes too
docker system prune -f  # Clean up unused images/containers
```

## Troubleshooting

1. **Services not starting**: Check logs with `docker-compose logs [service-name]`
2. **Port conflicts**: Modify ports in docker-compose.yml
3. **Permission issues**: Ensure proper file permissions and non-root users
4. **Memory issues**: Increase Docker Desktop memory allocation
5. **Celery not connecting**: Verify Redis is healthy and REDIS_URL is correct

## Monitoring

Access service endpoints:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/v1/docs
- MinIO Console: http://localhost:9001
- Health checks: http://localhost/health