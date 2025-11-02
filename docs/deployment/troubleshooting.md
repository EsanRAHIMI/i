# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the AI Assistant system.

## Quick Diagnostics

### System Health Check

Run this comprehensive health check script:

```bash
#!/bin/bash
# health-check.sh

echo "🔍 AI Assistant System Health Check"
echo "=================================="

# Check Docker
echo "📦 Docker Status:"
docker --version
docker compose version
echo ""

# Check running services
echo "🚀 Running Services:"
docker compose ps
echo ""

# Check service health
echo "🏥 Service Health:"
services=("postgres" "redis" "minio" "backend" "frontend" "celery" "nginx")

for service in "${services[@]}"; do
    if docker compose ps $service | grep -q "Up"; then
        echo "✅ $service: Running"
    else
        echo "❌ $service: Not running"
    fi
done
echo ""

# Check API health
echo "🌐 API Health:"
if curl -s http://localhost/health > /dev/null; then
    echo "✅ API: Responding"
    curl -s http://localhost/health | jq .
else
    echo "❌ API: Not responding"
fi
echo ""

# Check database connectivity
echo "🗄️ Database Connectivity:"
if docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ PostgreSQL: Connected"
else
    echo "❌ PostgreSQL: Connection failed"
fi

# Check Redis connectivity
echo "📦 Redis Connectivity:"
if docker compose exec -T redis redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis: Connected"
else
    echo "❌ Redis: Connection failed"
fi
echo ""

# Check disk space
echo "💾 Disk Space:"
df -h | grep -E "(Filesystem|/dev/)"
echo ""

# Check memory usage
echo "🧠 Memory Usage:"
free -h
echo ""

# Check Docker resources
echo "🐳 Docker Resources:"
docker system df
```

Make it executable and run:

```bash
chmod +x health-check.sh
./health-check.sh
```

## Common Issues and Solutions

### 1. Services Won't Start

#### Symptom
```bash
docker compose up -d
# Services exit immediately or fail to start
```

#### Diagnosis
```bash
# Check service logs
docker compose logs backend
docker compose logs postgres
docker compose logs redis

# Check Docker daemon
sudo systemctl status docker

# Check available resources
docker system df
free -h
```

#### Solutions

**Insufficient Resources:**
```bash
# Free up Docker resources
docker system prune -f
docker volume prune -f

# Increase Docker memory limit (Docker Desktop)
# Settings → Resources → Memory → 8GB+
```

**Port Conflicts:**
```bash
# Check what's using ports
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :5432

# Use different ports
export NGINX_PORT=8080
export POSTGRES_PORT=5433
docker compose up -d
```

**Permission Issues:**
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
chmod +x scripts/*.sh

# Fix Docker socket permissions
sudo chmod 666 /var/run/docker.sock
```

### 2. Database Connection Errors

#### Symptom
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server
```

#### Diagnosis
```bash
# Check PostgreSQL status
docker compose logs postgres

# Test direct connection
docker compose exec postgres psql -U postgres -d ai_assistant -c "SELECT 1;"

# Check environment variables
docker compose exec backend env | grep POSTGRES
```

#### Solutions

**Database Not Ready:**
```bash
# Wait for database to be ready
docker compose up -d postgres
sleep 30
docker compose up -d backend
```

**Wrong Credentials:**
```bash
# Check .env file
cat .env | grep POSTGRES

# Reset database with correct credentials
docker compose down postgres
docker volume rm ai-assistant_postgres_data
# Update .env with correct credentials
docker compose up -d postgres
```

**Migration Issues:**
```bash
# Run migrations manually
docker compose run --rm backend python -m alembic upgrade head

# Check migration status
docker compose run --rm backend python -m alembic current
```

### 3. API Not Responding

#### Symptom
```bash
curl http://localhost/health
# Connection refused or timeout
```

#### Diagnosis
```bash
# Check backend service
docker compose logs backend

# Check nginx configuration
docker compose logs nginx

# Test backend directly
curl http://localhost:8000/health
```

#### Solutions

**Backend Service Issues:**
```bash
# Restart backend
docker compose restart backend

# Check backend logs for errors
docker compose logs -f backend

# Test backend health directly
docker compose exec backend curl http://localhost:8000/health
```

**Nginx Configuration Issues:**
```bash
# Check nginx configuration
docker compose exec nginx nginx -t

# Restart nginx
docker compose restart nginx

# Check nginx logs
docker compose logs nginx
```

**SSL/TLS Issues:**
```bash
# Disable SSL for testing
# Comment out SSL sections in nginx config
docker compose restart nginx
```

### 4. Authentication Errors

#### Symptom
```
401 Unauthorized or JWT token errors
```

#### Diagnosis
```bash
# Check JWT keys exist
ls -la backend/keys/

# Check JWT configuration
docker compose exec backend env | grep JWT

# Test token generation
curl -X POST "http://localhost/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

#### Solutions

**Missing JWT Keys:**
```bash
# Generate new JWT keys
mkdir -p backend/keys
openssl genrsa -out backend/keys/jwt_private_key.pem 2048
openssl rsa -in backend/keys/jwt_private_key.pem -pubout -out backend/keys/jwt_public_key.pem

# Restart backend
docker compose restart backend
```

**Invalid JWT Configuration:**
```bash
# Check JWT secret in .env
grep JWT_SECRET_KEY .env

# Generate new secret if needed
echo "JWT_SECRET_KEY=$(openssl rand -base64 32)" >> .env
docker compose restart backend
```

### 5. Voice Processing Issues

#### Symptom
```
Voice endpoints return 500 errors or timeout
```

#### Diagnosis
```bash
# Check Celery worker
docker compose logs celery

# Check voice service dependencies
docker compose exec backend python -c "import whisper; print('Whisper OK')"
docker compose exec backend python -c "import TTS; print('TTS OK')"

# Test voice endpoint
curl -X POST "http://localhost/api/v1/voice/tts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"test"}'
```

#### Solutions

**Missing Dependencies:**
```bash
# Rebuild backend with voice dependencies
docker compose build backend
docker compose up -d backend celery
```

**Insufficient Memory:**
```bash
# Increase Docker memory limit
# Check memory usage
docker stats

# Scale down other services
docker compose up -d --scale celery=1
```

**Model Download Issues:**
```bash
# Pre-download models
docker compose exec backend python -c "
import whisper
whisper.load_model('base')
"
```

### 6. External Integration Issues

#### Google Calendar

**OAuth Errors:**
```bash
# Check Google credentials
docker compose exec backend env | grep GOOGLE

# Verify redirect URI matches Google Console
# Check OAuth consent screen configuration
```

**API Quota Exceeded:**
```bash
# Check Google Cloud Console quotas
# Implement exponential backoff
# Monitor API usage
```

#### WhatsApp

**Webhook Verification Failed:**
```bash
# Check webhook URL is publicly accessible
curl https://your-domain.com/api/v1/whatsapp/webhook

# Verify webhook token matches Meta configuration
grep WHATSAPP_VERIFY_TOKEN .env
```

**Message Delivery Failed:**
```bash
# Check WhatsApp access token
# Verify phone number format (+country_code_number)
# Check message template approval status
```

### 7. Performance Issues

#### Symptom
```
Slow response times or high resource usage
```

#### Diagnosis
```bash
# Check resource usage
docker stats

# Check database performance
docker compose exec postgres psql -U postgres -d ai_assistant -c "
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
"

# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost/health"
```

#### Solutions

**Database Optimization:**
```bash
# Add database indexes
docker compose exec postgres psql -U postgres -d ai_assistant -c "
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY idx_events_user_start_time ON events(user_id, start_time);
"

# Analyze query performance
docker compose exec postgres psql -U postgres -d ai_assistant -c "ANALYZE;"
```

**Caching:**
```bash
# Check Redis usage
docker compose exec redis redis-cli info memory

# Clear cache if needed
docker compose exec redis redis-cli FLUSHALL
```

**Scaling:**
```bash
# Scale backend services
docker compose up -d --scale backend=3 --scale celery=2

# Use load balancer
# Configure nginx upstream
```

### 8. SSL/TLS Issues

#### Symptom
```
SSL certificate errors or HTTPS not working
```

#### Diagnosis
```bash
# Check certificate files
ls -la infra/ssl/

# Test SSL configuration
openssl s_client -connect your-domain.com:443

# Check nginx SSL configuration
docker compose exec nginx nginx -t
```

#### Solutions

**Generate Self-Signed Certificates (Development):**
```bash
# Generate certificates
mkdir -p infra/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout infra/ssl/nginx-selfsigned.key \
  -out infra/ssl/nginx-selfsigned.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Restart nginx
docker compose restart nginx
```

**Let's Encrypt (Production):**
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Monitoring and Logging

### Enable Debug Logging

```bash
# Backend debug logging
docker compose exec backend python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
"

# Database query logging
# Add to .env:
echo "SQLALCHEMY_ECHO=true" >> .env
docker compose restart backend
```

### Log Analysis

```bash
# View all logs
docker compose logs

# Follow specific service logs
docker compose logs -f backend

# Search logs for errors
docker compose logs | grep -i error

# Export logs for analysis
docker compose logs > system-logs.txt
```

### Performance Monitoring

```bash
# Monitor resource usage
watch docker stats

# Monitor API performance
# Install and configure Prometheus/Grafana
docker compose -f docker-compose.monitoring.yml up -d

# Access Grafana
open http://localhost:3000
```

## Recovery Procedures

### Database Recovery

```bash
# Backup current database
docker compose exec postgres pg_dump -U postgres ai_assistant > backup.sql

# Restore from backup
docker compose exec -T postgres psql -U postgres ai_assistant < backup.sql

# Reset to clean state
docker compose down postgres
docker volume rm ai-assistant_postgres_data
docker compose up -d postgres
sleep 30
docker compose run --rm backend python -m alembic upgrade head
```

### Complete System Reset

```bash
# Stop all services
docker compose down

# Remove all volumes (WARNING: Deletes all data)
docker compose down -v

# Remove all images
docker compose down --rmi all

# Clean Docker system
docker system prune -af

# Rebuild from scratch
docker compose build --no-cache
docker compose up -d
```

## Getting Help

### Collect System Information

```bash
#!/bin/bash
# collect-info.sh

echo "System Information for Support"
echo "============================="

echo "Date: $(date)"
echo "OS: $(uname -a)"
echo "Docker: $(docker --version)"
echo "Docker Compose: $(docker compose version)"
echo ""

echo "Service Status:"
docker compose ps
echo ""

echo "Recent Logs (last 50 lines):"
docker compose logs --tail=50
echo ""

echo "Environment Variables (sanitized):"
env | grep -E "(POSTGRES|REDIS|NGINX)" | sed 's/=.*/=***/'
echo ""

echo "Disk Usage:"
df -h
echo ""

echo "Memory Usage:"
free -h
```

### Support Channels

1. **Documentation**: Check relevant guides in `/docs`
2. **GitHub Issues**: https://github.com/your-org/ai-assistant/issues
3. **Discord Community**: https://discord.gg/ai-assistant
4. **Email Support**: support@ai-assistant.com

### When Reporting Issues

Include:
- Output from `health-check.sh`
- Relevant log snippets
- Steps to reproduce
- Expected vs actual behavior
- System specifications

## Prevention

### Regular Maintenance

```bash
# Weekly maintenance script
#!/bin/bash

# Update system
docker compose pull
docker compose up -d

# Clean up unused resources
docker system prune -f

# Backup database
docker compose exec postgres pg_dump -U postgres ai_assistant > "backup-$(date +%Y%m%d).sql"

# Check disk space
df -h

# Restart services for fresh state
docker compose restart
```

### Monitoring Setup

```bash
# Set up basic monitoring
# Add to crontab:
*/5 * * * * curl -f http://localhost/health || echo "API Down: $(date)" >> /var/log/ai-assistant-alerts.log
```

This troubleshooting guide should help you resolve most common issues. For complex problems, don't hesitate to reach out to the community or support team.