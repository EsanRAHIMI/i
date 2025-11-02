#!/bin/bash

# =============================================================================
# i Assistant - Health Check Script
# =============================================================================
# Comprehensive health check for all services

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

# Health check results
HEALTH_RESULTS=()
FAILED_CHECKS=0

# Add result to array
add_result() {
    local service=$1
    local status=$2
    local message=$3
    
    HEALTH_RESULTS+=("$service:$status:$message")
    
    if [ "$status" = "FAIL" ]; then
        ((FAILED_CHECKS++))
    fi
}

# Check Docker services
check_docker_services() {
    log_info "Checking Docker services..."
    
    services=("postgres" "redis" "minio" "backend" "frontend" "nginx" "celery-worker" "celery-beat")
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            if docker-compose ps "$service" | grep -q "healthy"; then
                add_result "$service" "PASS" "Service is running and healthy"
                log_success "$service: Running and healthy"
            else
                add_result "$service" "WARN" "Service is running but not healthy"
                log_warning "$service: Running but not healthy"
            fi
        else
            add_result "$service" "FAIL" "Service is not running"
            log_error "$service: Not running"
        fi
    done
}

# Check HTTP endpoints
check_http_endpoints() {
    log_info "Checking HTTP endpoints..."
    
    endpoints=(
        "http://localhost/health:Frontend Health"
        "http://localhost/api/health:Backend Health"
        "http://localhost/api/v1/auth/health:Auth Health"
        "http://localhost:9001:MinIO Console"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        IFS=':' read -r endpoint description <<< "$endpoint_info"
        
        if curl -f -s --max-time 10 "$endpoint" > /dev/null 2>&1; then
            add_result "$description" "PASS" "Endpoint responding"
            log_success "$description: OK"
        else
            add_result "$description" "FAIL" "Endpoint not responding"
            log_error "$description: Failed"
        fi
    done
}

# Check database connectivity
check_database() {
    log_info "Checking database connectivity..."
    
    if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        add_result "PostgreSQL" "PASS" "Database is ready"
        log_success "PostgreSQL: Ready"
        
        # Check if tables exist
        table_count=$(docker-compose exec -T postgres psql -U postgres -d i_assistant -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
        
        if [ "$table_count" -gt 0 ]; then
            add_result "Database Schema" "PASS" "$table_count tables found"
            log_success "Database Schema: $table_count tables"
        else
            add_result "Database Schema" "WARN" "No tables found - may need migration"
            log_warning "Database Schema: No tables found"
        fi
    else
        add_result "PostgreSQL" "FAIL" "Database not ready"
        log_error "PostgreSQL: Not ready"
    fi
}

# Check Redis connectivity
check_redis() {
    log_info "Checking Redis connectivity..."
    
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        add_result "Redis" "PASS" "Redis is responding"
        log_success "Redis: Responding"
    else
        add_result "Redis" "FAIL" "Redis not responding"
        log_error "Redis: Not responding"
    fi
}

# Check SSL certificates
check_ssl() {
    log_info "Checking SSL certificates..."
    
    if [ -f "infra/ssl/nginx-selfsigned.crt" ]; then
        # Check certificate expiry
        expiry_date=$(openssl x509 -in infra/ssl/nginx-selfsigned.crt -noout -enddate 2>/dev/null | cut -d= -f2)
        if [ -n "$expiry_date" ]; then
            expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_date" +%s 2>/dev/null)
            current_epoch=$(date +%s)
            days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))
            
            if [ $days_until_expiry -gt 30 ]; then
                add_result "SSL Certificate" "PASS" "Certificate valid for $days_until_expiry days"
                log_success "SSL Certificate: Valid for $days_until_expiry days"
            elif [ $days_until_expiry -gt 0 ]; then
                add_result "SSL Certificate" "WARN" "Certificate expires in $days_until_expiry days"
                log_warning "SSL Certificate: Expires in $days_until_expiry days"
            else
                add_result "SSL Certificate" "FAIL" "Certificate has expired"
                log_error "SSL Certificate: Expired"
            fi
        else
            add_result "SSL Certificate" "WARN" "Could not read certificate expiry"
            log_warning "SSL Certificate: Could not read expiry date"
        fi
    else
        add_result "SSL Certificate" "FAIL" "No SSL certificate found"
        log_error "SSL Certificate: Not found"
    fi
}

# Check disk space
check_disk_space() {
    log_info "Checking disk space..."
    
    # Check available disk space (in percentage)
    disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -lt 80 ]; then
        add_result "Disk Space" "PASS" "${disk_usage}% used"
        log_success "Disk Space: ${disk_usage}% used"
    elif [ "$disk_usage" -lt 90 ]; then
        add_result "Disk Space" "WARN" "${disk_usage}% used"
        log_warning "Disk Space: ${disk_usage}% used"
    else
        add_result "Disk Space" "FAIL" "${disk_usage}% used - critically low"
        log_error "Disk Space: ${disk_usage}% used - critically low"
    fi
}

# Check memory usage
check_memory() {
    log_info "Checking memory usage..."
    
    # Get memory usage percentage
    memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [ "$memory_usage" -lt 80 ]; then
        add_result "Memory Usage" "PASS" "${memory_usage}% used"
        log_success "Memory Usage: ${memory_usage}% used"
    elif [ "$memory_usage" -lt 90 ]; then
        add_result "Memory Usage" "WARN" "${memory_usage}% used"
        log_warning "Memory Usage: ${memory_usage}% used"
    else
        add_result "Memory Usage" "FAIL" "${memory_usage}% used - critically high"
        log_error "Memory Usage: ${memory_usage}% used - critically high"
    fi
}

# Generate health report
generate_report() {
    echo
    echo "==============================================================================="
    echo -e "${BLUE}Health Check Report${NC}"
    echo "==============================================================================="
    echo
    
    printf "%-25s %-8s %s\n" "Service/Check" "Status" "Message"
    echo "-------------------------------------------------------------------------------"
    
    for result in "${HEALTH_RESULTS[@]}"; do
        IFS=':' read -r service status message <<< "$result"
        
        case $status in
            "PASS")
                status_color="${GREEN}PASS${NC}"
                ;;
            "WARN")
                status_color="${YELLOW}WARN${NC}"
                ;;
            "FAIL")
                status_color="${RED}FAIL${NC}"
                ;;
        esac
        
        printf "%-25s %-8s %s\n" "$service" "$status_color" "$message"
    done
    
    echo
    echo "==============================================================================="
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        log_success "All health checks passed!"
        exit 0
    else
        log_error "$FAILED_CHECKS health check(s) failed"
        exit 1
    fi
}

# Main function
main() {
    echo "==============================================================================="
    echo -e "${BLUE}i Assistant - Health Check${NC}"
    echo "==============================================================================="
    echo
    
    check_docker_services
    check_http_endpoints
    check_database
    check_redis
    check_ssl
    check_disk_space
    check_memory
    
    generate_report
}

# Run main function
main "$@"