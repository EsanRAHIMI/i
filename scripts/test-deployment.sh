#!/bin/bash

# =============================================================================
# i Assistant - Deployment Testing Script
# =============================================================================
# Comprehensive testing of deployment and infrastructure

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

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Add test result
add_test_result() {
    local test_name=$1
    local result=$2
    
    if [ "$result" = "PASS" ]; then
        ((TESTS_PASSED++))
        log_success "$test_name: PASSED"
    else
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
        log_error "$test_name: FAILED"
    fi
}

# Test Docker installation and configuration
test_docker_setup() {
    log_info "Testing Docker setup..."
    
    # Test Docker is installed
    if command -v docker &> /dev/null; then
        add_test_result "Docker Installation" "PASS"
    else
        add_test_result "Docker Installation" "FAIL"
        return 1
    fi
    
    # Test Docker is running
    if docker info &> /dev/null; then
        add_test_result "Docker Service" "PASS"
    else
        add_test_result "Docker Service" "FAIL"
        return 1
    fi
    
    # Test Docker Compose is available
    if docker compose version &> /dev/null || docker-compose version &> /dev/null; then
        add_test_result "Docker Compose" "PASS"
    else
        add_test_result "Docker Compose" "FAIL"
        return 1
    fi
}

# Test configuration files
test_configuration_files() {
    log_info "Testing configuration files..."
    
    # Test Docker Compose configuration
    if docker-compose config &> /dev/null; then
        add_test_result "Docker Compose Config" "PASS"
    else
        add_test_result "Docker Compose Config" "FAIL"
    fi
    
    # Test production compose override
    if [ -f "docker-compose.prod.yml" ]; then
        if docker-compose -f docker-compose.yml -f docker-compose.prod.yml config &> /dev/null; then
            add_test_result "Production Compose Config" "PASS"
        else
            add_test_result "Production Compose Config" "FAIL"
        fi
    else
        add_test_result "Production Compose File" "FAIL"
    fi
    
    # Test environment files
    if [ -f ".env.example" ]; then
        add_test_result "Environment Template" "PASS"
    else
        add_test_result "Environment Template" "FAIL"
    fi
    
    # Test SSL certificates
    if [ -f "infra/ssl/nginx-selfsigned.crt" ] && [ -f "infra/ssl/nginx-selfsigned.key" ]; then
        add_test_result "SSL Certificates" "PASS"
    else
        add_test_result "SSL Certificates" "FAIL"
    fi
}

# Test Docker image builds
test_docker_builds() {
    log_info "Testing Docker image builds..."
    
    # Test backend image build
    if docker build -t i-assistant-backend:test ./backend &> /dev/null; then
        add_test_result "Backend Image Build" "PASS"
        docker rmi i-assistant-backend:test &> /dev/null || true
    else
        add_test_result "Backend Image Build" "FAIL"
    fi
    
    # Test frontend image build
    if docker build -t i-assistant-frontend:test ./frontend &> /dev/null; then
        add_test_result "Frontend Image Build" "PASS"
        docker rmi i-assistant-frontend:test &> /dev/null || true
    else
        add_test_result "Frontend Image Build" "FAIL"
    fi
}

# Test deployment scripts
test_deployment_scripts() {
    log_info "Testing deployment scripts..."
    
    scripts=("setup.sh" "deploy.sh" "health-check.sh" "migrate.sh")
    
    for script in "${scripts[@]}"; do
        script_path="scripts/$script"
        
        if [ -f "$script_path" ] && [ -x "$script_path" ]; then
            add_test_result "Script $script" "PASS"
            
            # Test script help functionality
            if "$script_path" --help &> /dev/null; then
                add_test_result "Script $script Help" "PASS"
            else
                add_test_result "Script $script Help" "FAIL"
            fi
        else
            add_test_result "Script $script" "FAIL"
        fi
    done
}

# Test service startup
test_service_startup() {
    log_info "Testing service startup..."
    
    # Create environment file if it doesn't exist
    if [ ! -f ".env" ]; then
        cp .env.example .env
    fi
    
    # Start core services
    log_info "Starting core services..."
    if docker-compose up -d postgres redis minio &> /dev/null; then
        add_test_result "Core Services Startup" "PASS"
        
        # Wait for services to be ready
        sleep 15
        
        # Test service health
        if docker-compose ps postgres | grep -q "Up (healthy)"; then
            add_test_result "PostgreSQL Health" "PASS"
        else
            add_test_result "PostgreSQL Health" "FAIL"
        fi
        
        if docker-compose ps redis | grep -q "Up (healthy)"; then
            add_test_result "Redis Health" "PASS"
        else
            add_test_result "Redis Health" "FAIL"
        fi
        
        if docker-compose ps minio | grep -q "Up (healthy)"; then
            add_test_result "MinIO Health" "PASS"
        else
            add_test_result "MinIO Health" "FAIL"
        fi
        
    else
        add_test_result "Core Services Startup" "FAIL"
    fi
}

# Test application services
test_application_services() {
    log_info "Testing application services..."
    
    # Start application services
    if docker-compose up -d backend frontend nginx &> /dev/null; then
        add_test_result "Application Services Startup" "PASS"
        
        # Wait for services to be ready
        sleep 30
        
        # Test backend health
        max_retries=10
        for ((i=1; i<=max_retries; i++)); do
            if curl -f -s http://localhost:8000/health &> /dev/null; then
                add_test_result "Backend Health Endpoint" "PASS"
                break
            elif [ $i -eq $max_retries ]; then
                add_test_result "Backend Health Endpoint" "FAIL"
            else
                sleep 3
            fi
        done
        
        # Test frontend health
        for ((i=1; i<=max_retries; i++)); do
            if curl -f -s http://localhost:3000/api/health &> /dev/null; then
                add_test_result "Frontend Health Endpoint" "PASS"
                break
            elif [ $i -eq $max_retries ]; then
                add_test_result "Frontend Health Endpoint" "FAIL"
            else
                sleep 3
            fi
        done
        
        # Test nginx proxy
        if curl -f -s -k https://localhost/health &> /dev/null; then
            add_test_result "Nginx HTTPS Proxy" "PASS"
        else
            add_test_result "Nginx HTTPS Proxy" "FAIL"
        fi
        
    else
        add_test_result "Application Services Startup" "FAIL"
    fi
}

# Test database migrations
test_database_migrations() {
    log_info "Testing database migrations..."
    
    # Test Alembic is available
    if docker-compose exec -T backend alembic --version &> /dev/null; then
        add_test_result "Alembic Available" "PASS"
        
        # Test migration status
        if docker-compose exec -T backend alembic current &> /dev/null; then
            add_test_result "Migration Status Check" "PASS"
        else
            add_test_result "Migration Status Check" "FAIL"
        fi
        
        # Test migration history
        if docker-compose exec -T backend alembic history &> /dev/null; then
            add_test_result "Migration History" "PASS"
        else
            add_test_result "Migration History" "FAIL"
        fi
        
    else
        add_test_result "Alembic Available" "FAIL"
    fi
}

# Test monitoring setup
test_monitoring_setup() {
    log_info "Testing monitoring setup..."
    
    # Test Prometheus configuration
    if [ -f "infra/prometheus/prometheus.yml" ]; then
        add_test_result "Prometheus Config" "PASS"
    else
        add_test_result "Prometheus Config" "FAIL"
    fi
    
    # Test Grafana provisioning
    if [ -f "infra/grafana/provisioning/datasources/prometheus.yml" ]; then
        add_test_result "Grafana Datasource Config" "PASS"
    else
        add_test_result "Grafana Datasource Config" "FAIL"
    fi
    
    # Start monitoring services
    if docker-compose up -d prometheus grafana &> /dev/null; then
        add_test_result "Monitoring Services Startup" "PASS"
        
        sleep 10
        
        # Test Prometheus endpoint
        if curl -f -s http://localhost:9090/-/healthy &> /dev/null; then
            add_test_result "Prometheus Health" "PASS"
        else
            add_test_result "Prometheus Health" "FAIL"
        fi
        
        # Test Grafana endpoint
        if curl -f -s http://localhost:3001/api/health &> /dev/null; then
            add_test_result "Grafana Health" "PASS"
        else
            add_test_result "Grafana Health" "FAIL"
        fi
        
    else
        add_test_result "Monitoring Services Startup" "FAIL"
    fi
}

# Test CI/CD configuration
test_cicd_configuration() {
    log_info "Testing CI/CD configuration..."
    
    # Test GitHub Actions workflows
    workflows=("ci.yml" "cd-staging.yml" "cd-production.yml" "security-scan.yml")
    
    for workflow in "${workflows[@]}"; do
        workflow_path=".github/workflows/$workflow"
        
        if [ -f "$workflow_path" ]; then
            add_test_result "Workflow $workflow" "PASS"
        else
            add_test_result "Workflow $workflow" "FAIL"
        fi
    done
    
    # Test Dependabot configuration
    if [ -f ".github/dependabot.yml" ]; then
        add_test_result "Dependabot Config" "PASS"
    else
        add_test_result "Dependabot Config" "FAIL"
    fi
    
    # Test SonarCloud configuration
    if [ -f "sonar-project.properties" ]; then
        add_test_result "SonarCloud Config" "PASS"
    else
        add_test_result "SonarCloud Config" "FAIL"
    fi
}

# Test security configuration
test_security_configuration() {
    log_info "Testing security configuration..."
    
    # Test dependency check suppressions
    if [ -f "dependency-check-suppressions.xml" ]; then
        add_test_result "Dependency Check Suppressions" "PASS"
    else
        add_test_result "Dependency Check Suppressions" "FAIL"
    fi
    
    # Test Nginx security configuration
    if [ -f "infra/nginx/conf.d/ssl-params.conf" ]; then
        security_headers=("X-Frame-Options" "X-Content-Type-Options" "Strict-Transport-Security")
        
        for header in "${security_headers[@]}"; do
            if grep -q "$header" infra/nginx/conf.d/ssl-params.conf; then
                add_test_result "Security Header $header" "PASS"
            else
                add_test_result "Security Header $header" "FAIL"
            fi
        done
    else
        add_test_result "Nginx Security Config" "FAIL"
    fi
}

# Cleanup after tests
cleanup() {
    log_info "Cleaning up test environment..."
    
    # Stop all services
    docker-compose down -v &> /dev/null || true
    
    # Remove test images
    docker rmi i-assistant-backend:test i-assistant-frontend:test &> /dev/null || true
    
    log_success "Cleanup completed"
}

# Generate test report
generate_report() {
    echo
    echo "==============================================================================="
    echo -e "${BLUE}Deployment Test Report${NC}"
    echo "==============================================================================="
    echo
    echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    echo
    
    if [ $TESTS_FAILED -gt 0 ]; then
        echo "Failed Tests:"
        for test in "${FAILED_TESTS[@]}"; do
            echo -e "  ${RED}✗${NC} $test"
        done
        echo
    fi
    
    echo "==============================================================================="
    
    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "All deployment tests passed!"
        exit 0
    else
        log_error "$TESTS_FAILED test(s) failed"
        exit 1
    fi
}

# Main function
main() {
    echo "==============================================================================="
    echo -e "${BLUE}i Assistant - Deployment Testing${NC}"
    echo "==============================================================================="
    echo
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Run all tests
    test_docker_setup
    test_configuration_files
    test_docker_builds
    test_deployment_scripts
    test_service_startup
    test_application_services
    test_database_migrations
    test_monitoring_setup
    test_cicd_configuration
    test_security_configuration
    
    # Generate final report
    generate_report
}

# Run main function
main "$@"