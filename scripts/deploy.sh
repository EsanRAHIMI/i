#!/bin/bash

# =============================================================================
# i Assistant - Production Deployment Script
# =============================================================================
# This script handles production deployment with zero-downtime updates

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
COMPOSE_FILE="docker-compose.yml"
COMPOSE_PROD_FILE="docker-compose.prod.yml"

# Parse arguments
parse_args() {
    ROLLBACK=false
    BACKUP_ONLY=false
    SKIP_BACKUP=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --rollback)
                ROLLBACK=true
                shift
                ;;
            --backup-only)
                BACKUP_ONLY=true
                shift
                ;;
            --skip-backup)
                SKIP_BACKUP=true
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

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --rollback      Rollback to previous deployment"
    echo "  --backup-only   Only create backup, don't deploy"
    echo "  --skip-backup   Skip backup creation"
    echo "  --help         Show this help message"
}

# Create backup
create_backup() {
    if [ "$SKIP_BACKUP" = true ]; then
        log_info "Skipping backup creation"
        return 0
    fi
    
    log_info "Creating backup..."
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    log_info "Backing up database..."
    docker-compose exec -T postgres pg_dump -U postgres i_assistant > "$BACKUP_DIR/database.sql"
    
    # Backup volumes
    log_info "Backing up volumes..."
    docker run --rm -v i-assistant_postgres_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/postgres_data.tar.gz -C /data .
    docker run --rm -v i-assistant_redis_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/redis_data.tar.gz -C /data .
    docker run --rm -v i-assistant_minio_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/minio_data.tar.gz -C /data .
    
    # Backup configuration
    cp -r infra "$BACKUP_DIR/"
    cp .env "$BACKUP_DIR/" 2>/dev/null || true
    cp docker-compose.yml "$BACKUP_DIR/"
    
    log_success "Backup created at $BACKUP_DIR"
}

# Rollback to previous version
rollback() {
    log_info "Rolling back to previous deployment..."
    
    # Find latest backup
    LATEST_BACKUP=$(ls -1 backups/ | sort -r | head -n1)
    if [ -z "$LATEST_BACKUP" ]; then
        log_error "No backup found for rollback"
        exit 1
    fi
    
    BACKUP_PATH="backups/$LATEST_BACKUP"
    log_info "Rolling back to backup: $BACKUP_PATH"
    
    # Stop services
    docker-compose down
    
    # Restore database
    log_info "Restoring database..."
    docker-compose up -d postgres
    sleep 10
    docker-compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS i_assistant;"
    docker-compose exec -T postgres psql -U postgres -c "CREATE DATABASE i_assistant;"
    docker-compose exec -T postgres psql -U postgres i_assistant < "$BACKUP_PATH/database.sql"
    
    # Restore volumes
    log_info "Restoring volumes..."
    docker run --rm -v i-assistant_postgres_data:/data -v "$(pwd)/$BACKUP_PATH":/backup alpine tar xzf /backup/postgres_data.tar.gz -C /data
    docker run --rm -v i-assistant_redis_data:/data -v "$(pwd)/$BACKUP_PATH":/backup alpine tar xzf /backup/redis_data.tar.gz -C /data
    docker run --rm -v i-assistant_minio_data:/data -v "$(pwd)/$BACKUP_PATH":/backup alpine tar xzf /backup/minio_data.tar.gz -C /data
    
    # Restore configuration
    cp -r "$BACKUP_PATH/infra" ./
    cp "$BACKUP_PATH/.env" ./ 2>/dev/null || true
    cp "$BACKUP_PATH/docker-compose.yml" ./
    
    # Start services
    docker-compose up -d
    
    log_success "Rollback completed successfully"
}

# Deploy new version
deploy() {
    log_info "Starting deployment..."
    
    # Pull latest images
    log_info "Pulling latest images..."
    docker-compose pull
    
    # Build new images
    log_info "Building new images..."
    docker-compose build --no-cache
    
    # Run database migrations
    log_info "Running database migrations..."
    docker-compose run --rm backend alembic upgrade head
    
    # Rolling update - update services one by one
    services=("backend" "frontend" "celery-worker" "celery-beat")
    
    for service in "${services[@]}"; do
        log_info "Updating $service..."
        docker-compose up -d --no-deps "$service"
        
        # Wait for service to be healthy
        max_retries=30
        for ((i=1; i<=max_retries; i++)); do
            if docker-compose ps "$service" | grep -q "Up (healthy)"; then
                log_success "$service updated successfully"
                break
            elif [ $i -eq $max_retries ]; then
                log_error "$service failed to start properly"
                exit 1
            else
                sleep 10
            fi
        done
    done
    
    # Update nginx last to avoid downtime
    log_info "Updating nginx..."
    docker-compose up -d --no-deps nginx
    
    log_success "Deployment completed successfully"
}

# Health check after deployment
health_check() {
    log_info "Performing health check..."
    
    endpoints=(
        "http://localhost/health"
        "http://localhost/api/health"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "$endpoint" > /dev/null; then
            log_success "Health check passed: $endpoint"
        else
            log_error "Health check failed: $endpoint"
            return 1
        fi
    done
    
    log_success "All health checks passed"
}

# Main function
main() {
    echo "==============================================================================="
    echo -e "${BLUE}i Assistant - Production Deployment${NC}"
    echo "==============================================================================="
    echo
    
    parse_args "$@"
    
    if [ "$ROLLBACK" = true ]; then
        rollback
        health_check
        exit 0
    fi
    
    create_backup
    
    if [ "$BACKUP_ONLY" = true ]; then
        log_success "Backup completed"
        exit 0
    fi
    
    deploy
    health_check
    
    log_success "Deployment completed successfully!"
    echo
    echo "Backup location: $BACKUP_DIR"
    echo "To rollback: $0 --rollback"
}

# Run main function
main "$@"