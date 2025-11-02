# Run in 5 Minutes - Quick Start Guide

Get the AI Assistant system running locally in under 5 minutes with this streamlined setup guide.

## Prerequisites

- **Docker** and **Docker Compose** installed
- **Git** for cloning the repository
- **8GB RAM** minimum (16GB recommended)
- **10GB free disk space**

## Quick Setup

### Step 1: Clone and Configure (1 minute)

```bash
# Clone the repository
git clone https://github.com/your-org/ai-assistant.git
cd ai-assistant

# Copy environment template
cp .env.example .env

# Generate JWT keys
mkdir -p backend/keys
openssl genrsa -out backend/keys/jwt_private_key.pem 2048
openssl rsa -in backend/keys/jwt_private_key.pem -pubout -out backend/keys/jwt_public_key.pem
```

### Step 2: Start Core Services (2 minutes)

```bash
# Start infrastructure services
docker compose up -d postgres redis minio

# Wait for services to be ready
sleep 30

# Run database migrations
docker compose run --rm backend python -m alembic upgrade head
```

### Step 3: Start Application Services (2 minutes)

```bash
# Start all application services
docker compose up -d

# Check service health
docker compose ps
```

You should see all services running:
- ✅ **postgres** - Database
- ✅ **redis** - Cache and message broker
- ✅ **minio** - Object storage
- ✅ **backend** - FastAPI application
- ✅ **frontend** - Next.js application
- ✅ **celery** - Background task worker
- ✅ **nginx** - Reverse proxy

### Step 4: Verify Installation (30 seconds)

```bash
# Check API health
curl http://localhost/health

# Expected response:
# {"status":"healthy","timestamp":1640995200.0,"version":"1.0.0"}

# Access the application
open http://localhost
```

## Default Access

- **Frontend**: http://localhost
- **API Documentation**: http://localhost/api/v1/docs
- **API Base URL**: http://localhost/api/v1
- **Admin Panel**: http://localhost/admin (if enabled)

## Test the System

### 1. Create a User Account

```bash
curl -X POST "http://localhost/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "timezone": "UTC",
    "language_preference": "en-US"
  }'
```

### 2. Test Voice Processing

```bash
# Get access token from registration response
TOKEN="your_access_token_here"

# Test text-to-speech
curl -X POST "http://localhost/api/v1/voice/tts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is your AI assistant!",
    "language": "en"
  }'
```

### 3. Test Calendar Integration

```bash
# Initiate Google Calendar connection
curl -X POST "http://localhost/api/v1/calendar/connect" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Configuration Options

### Environment Variables

Key variables you can modify in `.env`:

```bash
# Database
POSTGRES_DB=ai_assistant
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password

# Security
JWT_SECRET_KEY=your_jwt_secret_key
ENCRYPTION_KEY=your_32_byte_encryption_key

# External APIs (optional for basic testing)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
WHATSAPP_ACCESS_TOKEN=your_whatsapp_token
OPENAI_API_KEY=your_openai_key
```

### Service Scaling

Scale services based on your needs:

```bash
# Scale backend workers
docker compose up -d --scale backend=3

# Scale Celery workers
docker compose up -d --scale celery=2

# Check scaled services
docker compose ps
```

## Development Mode

For development with hot reloading:

```bash
# Stop production containers
docker compose down

# Start in development mode
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs
docker compose logs -f backend frontend
```

## Troubleshooting Quick Fixes

### Services Won't Start

```bash
# Check Docker resources
docker system df
docker system prune -f

# Restart with fresh containers
docker compose down -v
docker compose up -d
```

### Database Connection Issues

```bash
# Reset database
docker compose down postgres
docker volume rm ai-assistant_postgres_data
docker compose up -d postgres
sleep 30
docker compose run --rm backend python -m alembic upgrade head
```

### Port Conflicts

```bash
# Check what's using port 80
sudo lsof -i :80

# Use different ports
export NGINX_PORT=8080
docker compose up -d
```

### Memory Issues

```bash
# Check Docker memory usage
docker stats

# Reduce service replicas
docker compose up -d --scale celery=1 --scale backend=1
```

## Next Steps

Once the system is running:

1. **Configure External Integrations**
   - [Google Calendar Setup](../integrations/google-calendar-setup.md)
   - [WhatsApp Setup](../integrations/whatsapp-setup.md)

2. **Enable Production Features**
   - [SSL/TLS Configuration](./ssl-setup.md)
   - [Monitoring Setup](./monitoring.md)
   - [Backup Configuration](./backup.md)

3. **Customize the System**
   - [Configuration Guide](./configuration.md)
   - [Security Hardening](./security.md)
   - [Performance Tuning](./performance.md)

## Support

If you encounter issues:

1. Check the [Troubleshooting Guide](./troubleshooting.md)
2. Review service logs: `docker compose logs [service_name]`
3. Join our [Discord Community](https://discord.gg/ai-assistant)
4. Open an issue on [GitHub](https://github.com/your-org/ai-assistant/issues)

## Clean Up

To completely remove the system:

```bash
# Stop all services
docker compose down

# Remove all data (WARNING: This deletes everything!)
docker compose down -v
docker system prune -f
```

---

**🎉 Congratulations!** Your AI Assistant is now running. Visit http://localhost to start using your personal AI assistant.