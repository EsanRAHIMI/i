#!/bin/bash

# =============================================================================
# i Assistant - Database Migration Script
# =============================================================================
# Handle database migrations and schema updates

set -e

# Colors
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

# Parse arguments
parse_args() {
    ACTION="upgrade"
    TARGET="head"
    CREATE_MIGRATION=false
    MIGRATION_MESSAGE=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            upgrade|downgrade|current|history|show)
                ACTION=$1
                shift
                ;;
            --target)
                TARGET=$2
                shift 2
                ;;
            --create)
                CREATE_MIGRATION=true
                shift
                ;;
            --message)
                MIGRATION_MESSAGE=$2
                shift 2
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
    echo "Usage: $0 [ACTION] [OPTIONS]"
    echo
    echo "Actions:"
    echo "  upgrade     Upgrade database to latest migration (default)"
    echo "  downgrade   Downgrade database to previous migration"
    echo "  current     Show current migration"
    echo "  history     Show migration history"
    echo "  show        Show migration details"
    echo
    echo "Options:"
    echo "  --target REV    Target migration revision (default: head)"
    echo "  --create        Create new migration"
    echo "  --message MSG   Migration message (required with --create)"
    echo "  --help         Show this help message"
}

# Check if backend service is running
check_backend() {
    log_info "Checking backend service..."
    
    if ! docker-compose ps backend | grep -q "Up"; then
        log_error "Backend service is not running. Please start it first:"
        log_info "docker-compose up -d backend"
        exit 1
    fi
    
    # Wait for backend to be ready
    max_retries=30
    for ((i=1; i<=max_retries; i++)); do
        if docker-compose exec -T backend python -c "import sys; sys.exit(0)" 2>/dev/null; then
            log_success "Backend service is ready"
            break
        elif [ $i -eq $max_retries ]; then
            log_error "Backend service not ready after waiting"
            exit 1
        else
            log_info "Waiting for backend service... (attempt $i/$max_retries)"
            sleep 2
        fi
    done
}

# Create backup before migration
create_backup() {
    log_info "Creating database backup before migration..."
    
    backup_dir="./backups/migrations/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    if docker-compose exec -T postgres pg_dump -U postgres i_assistant > "$backup_dir/pre_migration_backup.sql"; then
        log_success "Database backup created: $backup_dir/pre_migration_backup.sql"
        echo "$backup_dir" > .last_migration_backup
    else
        log_error "Failed to create database backup"
        exit 1
    fi
}

# Run migration upgrade
run_upgrade() {
    log_info "Running database upgrade to: $TARGET"
    
    create_backup
    
    if docker-compose exec -T backend alembic upgrade "$TARGET"; then
        log_success "Database upgrade completed successfully"
        
        # Show current revision
        current_rev=$(docker-compose exec -T backend alembic current --verbose 2>/dev/null | head -1 || echo "Unknown")
        log_info "Current database revision: $current_rev"
    else
        log_error "Database upgrade failed"
        
        # Offer to restore backup
        if [ -f .last_migration_backup ]; then
            backup_path=$(cat .last_migration_backup)
            log_warning "Backup available at: $backup_path"
            log_info "To restore: docker-compose exec -T postgres psql -U postgres i_assistant < $backup_path/pre_migration_backup.sql"
        fi
        
        exit 1
    fi
}

# Run migration downgrade
run_downgrade() {
    log_warning "Running database downgrade to: $TARGET"
    log_warning "This operation may result in data loss!"
    
    read -p "Are you sure you want to proceed? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Downgrade cancelled"
        exit 0
    fi
    
    create_backup
    
    if docker-compose exec -T backend alembic downgrade "$TARGET"; then
        log_success "Database downgrade completed"
    else
        log_error "Database downgrade failed"
        exit 1
    fi
}

# Show current migration
show_current() {
    log_info "Current database migration:"
    docker-compose exec -T backend alembic current --verbose
}

# Show migration history
show_history() {
    log_info "Migration history:"
    docker-compose exec -T backend alembic history --verbose
}

# Show migration details
show_migration() {
    log_info "Migration details for: $TARGET"
    docker-compose exec -T backend alembic show "$TARGET"
}

# Create new migration
create_migration() {
    if [ -z "$MIGRATION_MESSAGE" ]; then
        log_error "Migration message is required. Use --message 'Your message'"
        exit 1
    fi
    
    log_info "Creating new migration: $MIGRATION_MESSAGE"
    
    if docker-compose exec -T backend alembic revision --autogenerate -m "$MIGRATION_MESSAGE"; then
        log_success "Migration created successfully"
        
        # Show the new migration file
        log_info "New migration files:"
        docker-compose exec -T backend find alembic/versions -name "*.py" -newer alembic/versions/001_initial_schema.py 2>/dev/null | tail -1 || true
    else
        log_error "Failed to create migration"
        exit 1
    fi
}

# Validate migration
validate_migration() {
    log_info "Validating migration state..."
    
    # Check if database is in sync with models
    if docker-compose exec -T backend alembic check 2>/dev/null; then
        log_success "Database is in sync with models"
    else
        log_warning "Database may be out of sync with models"
        log_info "Consider creating a new migration with: $0 --create --message 'Description'"
    fi
}

# Main function
main() {
    echo "==============================================================================="
    echo -e "${BLUE}i Assistant - Database Migration${NC}"
    echo "==============================================================================="
    echo
    
    parse_args "$@"
    
    check_backend
    
    case $ACTION in
        "upgrade")
            run_upgrade
            validate_migration
            ;;
        "downgrade")
            run_downgrade
            ;;
        "current")
            show_current
            ;;
        "history")
            show_history
            ;;
        "show")
            show_migration
            ;;
    esac
    
    if [ "$CREATE_MIGRATION" = true ]; then
        create_migration
    fi
    
    log_success "Migration operation completed"
}

# Run main function
main "$@"