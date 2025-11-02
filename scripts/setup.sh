#!/bin/bash

# =============================================================================
# i Assistant - Setup Script
# =============================================================================
# This script sets up the entire i Assistant system for development

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed and running
check_docker() {
    log_info "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    log_success "Docker is installed and running"
}

# Check if Node.js is installed
check_node() {
    log_info "Checking Node.js installation..."
    
    if ! command -v node &> /dev/null; then
        log_warning "Node.js is not installed. Some development features may not work."
        return 1
    fi
    
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    REQUIRED_VERSION="18.0.0"
    
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$NODE_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        log_warning "Node.js version $NODE_VERSION is below required version $REQUIRED_VERSION"
        return 1
    fi
    
    log_success "Node.js $NODE_VERSION is installed"
    return 0
}

# Check if Python is installed
check_python() {
    log_info "Checking Python installation..."
    
    if ! command -v python3 &> /dev/null; then
        log_warning "Python 3 is not installed. Some development features may not work."
        return 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_success "Python $PYTHON_VERSION is installed"
    return 0
}

# Create environment file from template
setup_environment() {
    log_info "Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        cp .env.example .env
        log_success "Created .env file from template"
        log_warning "Please update .env file with your specific configuration"
    else
        log_info ".env file already exists, skipping creation"
    fi
    
    # Create service-specific env files
    for service in backend frontend ai; do
        if [ ! -f "$service/.env" ] && [ -f "$service/.env.example" ]; then
            cp "$service/.env.example" "$service/.env"
            log_success "Created $service/.env file"
        fi
    done
}

# Generate SSL certificates for development
generate_ssl_certs() {
    log_info "Generating SSL certificates for development..."
    
    mkdir -p infra/ssl
    
    if [ ! -f infra/ssl/nginx-selfsigned.crt ]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout infra/ssl/nginx-selfsigned.key \
            -out infra/ssl/nginx-selfsigned.crt \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" \
            2>/dev/null || {
                log_warning "OpenSSL not found. SSL certificates not generated."
                log_warning "HTTPS will not work until certificates are provided."
                return 1
            }
        log_success "Generated self-signed SSL certificates"
    else
        log_info "SSL certificates already exist"
    fi
}

# Setup Let's Encrypt certificates for production
setup_letsencrypt() {
    if [ "$ENVIRONMENT" = "production" ] && [ -n "$DOMAIN" ] && [ -n "$CERTBOT_EMAIL" ]; then
        log_info "Setting up Let's Encrypt certificates for production..."
        
        # Start nginx first for HTTP challenge
        docker-compose up -d nginx
        sleep 5
        
        # Request certificate
        docker-compose run --rm certbot certonly \
            --webroot \
            --webroot-path=/var/www/certbot \
            --email "$CERTBOT_EMAIL" \
            --agree-tos \
            --no-eff-email \
            -d "$DOMAIN"
        
        if [ $? -eq 0 ]; then
            log_success "Let's Encrypt certificates obtained successfully"
            # Reload nginx with new certificates
            docker-compose exec nginx nginx -s reload
        else
            log_warning "Failed to obtain Let's Encrypt certificates, using self-signed"
        fi
    fi
}

# Create required directories
create_directories() {
    log_info "Creating required directories..."
    
    directories=(
        "backend/logs"
        "infra/ssl"
        "infra/prometheus"
        "infra/grafana/provisioning/datasources"
        "infra/grafana/provisioning/dashboards"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
    done
    
    log_success "Required directories created"
}

# Install dependencies if Node.js is available
install_dependencies() {
    if check_node; then
        log_info "Installing Node.js dependencies..."
        npm install
        log_success "Node.js dependencies installed"
    fi
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    
    # Create basic Dockerfiles if they don't exist
    create_dockerfiles
    
    docker-compose build --no-cache
    log_success "Docker images built successfully"
}

# Create basic Dockerfiles
create_dockerfiles() {
    # Backend Dockerfile
    if [ ! -f backend/Dockerfile ]; then
        cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EOF
        log_success "Created backend/Dockerfile"
    fi

    # Frontend Dockerfile
    if [ ! -f frontend/Dockerfile ]; then
        cat > frontend/Dockerfile << 'EOF'
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps --only=production

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

# Run the application
CMD ["npm", "start"]
EOF
        log_success "Created frontend/Dockerfile"
    fi
}

# Start services
start_services() {
    log_info "Starting services..."
    
    docker-compose up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    check_service_health
}

# Check service health with retries
check_service_health() {
    log_info "Checking service health..."
    
    services=("postgres" "redis" "minio" "backend" "frontend")
    max_retries=30
    retry_interval=10
    
    for service in "${services[@]}"; do
        log_info "Waiting for $service to be healthy..."
        
        for ((i=1; i<=max_retries; i++)); do
            if docker-compose ps "$service" | grep -q "Up (healthy)"; then
                log_success "$service is healthy"
                break
            elif [ $i -eq $max_retries ]; then
                log_error "$service failed to become healthy after $((max_retries * retry_interval)) seconds"
                docker-compose logs "$service" | tail -20
                return 1
            else
                log_info "Waiting for $service... (attempt $i/$max_retries)"
                sleep $retry_interval
            fi
        done
    done
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Wait for backend to be ready
    max_retries=10
    for ((i=1; i<=max_retries; i++)); do
        if docker-compose exec -T backend python -c "import sys; sys.exit(0)" 2>/dev/null; then
            break
        elif [ $i -eq $max_retries ]; then
            log_error "Backend service not ready for migrations"
            return 1
        else
            log_info "Waiting for backend service... (attempt $i/$max_retries)"
            sleep 5
        fi
    done
    
    # Run Alembic migrations
    if docker-compose exec -T backend alembic upgrade head; then
        log_success "Database migrations completed successfully"
    else
        log_error "Database migrations failed"
        return 1
    fi
}

# Seed initial data
seed_database() {
    log_info "Seeding initial database data..."
    
    # Create seed script if it doesn't exist
    if [ ! -f backend/seed_data.py ]; then
        log_info "Creating database seed script..."
        create_seed_script
    fi
    
    if docker-compose exec -T backend python seed_data.py; then
        log_success "Database seeded successfully"
    else
        log_warning "Database seeding failed or skipped"
    fi
}

# Create database seed script
create_seed_script() {
    cat > backend/seed_data.py << 'EOF'
#!/usr/bin/env python3
"""
Database seeding script for i Assistant
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from app.database.models import Base
from app.config import get_settings

async def seed_database():
    """Seed the database with initial data"""
    settings = get_settings()
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
    try:
        # Create tables if they don't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("Database seeded successfully")
        return True
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(seed_database())
    sys.exit(0 if success else 1)
EOF
    chmod +x backend/seed_data.py
}

# Display setup completion message
display_completion() {
    log_success "Setup completed successfully!"
    echo
    echo "==============================================================================="
    echo -e "${GREEN}i Assistant is now running!${NC}"
    echo "==============================================================================="
    echo
    echo "Services:"
    echo "  • Frontend:  http://localhost:3000"
    echo "  • Backend:   http://localhost:8000"
    echo "  • MinIO:     http://localhost:9001 (admin: minioadmin/minioadmin123)"
    echo
    echo "Next steps:"
    echo "  1. Update .env files with your API keys and configuration"
    echo "  2. Run database migrations: docker-compose exec backend alembic upgrade head"
    echo "  3. Access the application at http://localhost:3000"
    echo
    echo "Useful commands:"
    echo "  • View logs:     docker-compose logs -f"
    echo "  • Stop services: docker-compose down"
    echo "  • Restart:       docker-compose restart"
    echo
    echo "==============================================================================="
}

# Parse command line arguments
parse_args() {
    ENVIRONMENT="development"
    SKIP_BUILD=false
    SKIP_MIGRATIONS=false
    PRODUCTION_MODE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --production)
                ENVIRONMENT="production"
                PRODUCTION_MODE=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-migrations)
                SKIP_MIGRATIONS=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Show help message
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --production      Set up for production environment"
    echo "  --skip-build      Skip Docker image building"
    echo "  --skip-migrations Skip database migrations"
    echo "  --help           Show this help message"
    echo
    echo "Environment Variables:"
    echo "  DOMAIN           Domain name for Let's Encrypt (production only)"
    echo "  CERTBOT_EMAIL    Email for Let's Encrypt registration"
}

# Main setup function
main() {
    echo "==============================================================================="
    echo -e "${BLUE}i Assistant - Intelligent AI Life Assistant${NC}"
    echo -e "${BLUE}Setup Script${NC}"
    echo "==============================================================================="
    echo
    
    parse_args "$@"
    
    log_info "Environment: $ENVIRONMENT"
    
    check_docker
    create_directories
    setup_environment
    generate_ssl_certs
    
    if [ "$PRODUCTION_MODE" = true ]; then
        setup_letsencrypt
    fi
    
    install_dependencies
    
    if [ "$SKIP_BUILD" = false ]; then
        build_images
    fi
    
    start_services
    check_service_health
    
    if [ "$SKIP_MIGRATIONS" = false ]; then
        run_migrations
        seed_database
    fi
    
    display_completion
}

# Run main function
main "$@"