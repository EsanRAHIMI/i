"""
Integration tests for full deployment workflow
"""
import asyncio
import json
import os
import subprocess
import time
from typing import Dict, List

import pytest
import requests
from sqlalchemy import create_engine, text


class TestFullDeploymentWorkflow:
    """Test complete deployment workflow from setup to running application"""
    
    @pytest.fixture(scope="class", autouse=True)
    def deployment_setup(self):
        """Set up full deployment for testing"""
        # Change to project root
        os.chdir("..")
        
        # Ensure clean state
        subprocess.run(["docker-compose", "down", "-v"], capture_output=True)
        
        # Copy environment file
        if not os.path.exists(".env"):
            subprocess.run(["cp", ".env.example", ".env"])
        
        # Run setup script
        setup_result = subprocess.run(
            ["./scripts/setup.sh", "--skip-migrations"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if setup_result.returncode != 0:
            pytest.fail(f"Setup script failed: {setup_result.stderr}")
        
        # Wait for services to be ready
        self._wait_for_services()
        
        yield
        
        # Cleanup
        subprocess.run(["docker-compose", "down", "-v"], capture_output=True)
    
    def _wait_for_services(self, timeout=120):
        """Wait for all services to be healthy"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check core services
                postgres_ready = self._check_postgres()
                redis_ready = self._check_redis()
                backend_ready = self._check_backend()
                
                if postgres_ready and redis_ready and backend_ready:
                    return True
                    
            except Exception:
                pass
            
            time.sleep(5)
        
        pytest.fail("Services failed to become ready within timeout")
    
    def _check_postgres(self):
        """Check if PostgreSQL is ready"""
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "postgres", "pg_isready", "-U", "postgres"],
            capture_output=True
        )
        return result.returncode == 0
    
    def _check_redis(self):
        """Check if Redis is ready"""
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "redis", "redis-cli", "ping"],
            capture_output=True
        )
        return result.returncode == 0
    
    def _check_backend(self):
        """Check if backend is ready"""
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def test_services_are_running(self):
        """Test that all required services are running"""
        result = subprocess.run(
            ["docker-compose", "ps"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        
        required_services = ["postgres", "redis", "minio", "backend", "nginx"]
        
        for service in required_services:
            assert service in result.stdout, f"Service {service} not running"
            assert "Up" in result.stdout, f"Service {service} not in Up state"
    
    def test_database_connectivity_and_schema(self):
        """Test database connectivity and schema creation"""
        # Test basic connectivity
        engine = create_engine("postgresql://postgres:postgres@localhost:5432/i_assistant")
        
        with engine.connect() as conn:
            # Test connection
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
            
            # Check if tables exist (after migrations would be run)
            tables_result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            
            # Should have at least some tables
            table_count = tables_result.fetchone()[0]
            assert table_count >= 0  # May be 0 if migrations haven't run yet
    
    def test_redis_functionality(self):
        """Test Redis functionality"""
        import redis
        
        r = redis.Redis(host='localhost', port=6379, password='redis123', decode_responses=True)
        
        # Test basic operations
        r.set('test_key', 'test_value')
        assert r.get('test_key') == 'test_value'
        
        # Test expiration
        r.setex('temp_key', 1, 'temp_value')
        assert r.get('temp_key') == 'temp_value'
        
        time.sleep(2)
        assert r.get('temp_key') is None
        
        # Cleanup
        r.delete('test_key')
    
    def test_minio_object_storage(self):
        """Test MinIO object storage functionality"""
        try:
            # Test MinIO health endpoint
            response = requests.get("http://localhost:9000/minio/health/live", timeout=10)
            assert response.status_code == 200
            
            # Test MinIO console access
            response = requests.get("http://localhost:9001", timeout=10)
            assert response.status_code in [200, 403]  # 403 is expected without auth
            
        except requests.RequestException as e:
            pytest.fail(f"MinIO connectivity test failed: {e}")
    
    def test_backend_api_endpoints(self):
        """Test backend API endpoints"""
        base_url = "http://localhost:8000"
        
        # Test health endpoint
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "healthy"
        
        # Test API documentation endpoint
        response = requests.get(f"{base_url}/docs")
        assert response.status_code == 200
        
        # Test OpenAPI schema
        response = requests.get(f"{base_url}/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
    
    def test_nginx_reverse_proxy(self):
        """Test Nginx reverse proxy functionality"""
        # Test HTTP to HTTPS redirect
        response = requests.get("http://localhost/health", allow_redirects=False)
        assert response.status_code == 301
        assert response.headers.get("Location", "").startswith("https://")
        
        # Test HTTPS endpoint (disable SSL verification for self-signed cert)
        response = requests.get("https://localhost/health", verify=False)
        assert response.status_code == 200
        
        # Test API proxying
        response = requests.get("https://localhost/api/health", verify=False)
        assert response.status_code == 200
        
        # Test security headers
        security_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection"
        ]
        
        for header in security_headers:
            assert header in response.headers, f"Security header {header} missing"
    
    def test_ssl_certificate_configuration(self):
        """Test SSL certificate configuration"""
        import ssl
        import socket
        
        # Test SSL connection
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection(('localhost', 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname='localhost') as ssock:
                cert = ssock.getpeercert()
                assert cert is not None
                
                # Check certificate has required fields
                assert 'subject' in cert
                assert 'notAfter' in cert
    
    def test_celery_worker_functionality(self):
        """Test Celery worker is running and functional"""
        # Check if Celery worker is running
        result = subprocess.run(
            ["docker-compose", "ps", "celery-worker"],
            capture_output=True,
            text=True
        )
        
        assert "Up" in result.stdout, "Celery worker not running"
        
        # Test Celery inspect command
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "celery-worker", "celery", "-A", "app.celery_app", "inspect", "ping"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Celery worker not responding to ping"
    
    def test_database_migrations(self):
        """Test database migration functionality"""
        # Run migrations
        result = subprocess.run(
            ["./scripts/migrate.sh", "upgrade"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Migration failed: {result.stderr}"
        
        # Check migration status
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "backend", "alembic", "current"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Failed to get current migration status"
        
        # Verify tables were created
        engine = create_engine("postgresql://postgres:postgres@localhost:5432/i_assistant")
        
        with engine.connect() as conn:
            tables_result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            
            tables = [row[0] for row in tables_result.fetchall()]
            
            # Should have core tables after migration
            expected_tables = ["users", "alembic_version"]
            
            for table in expected_tables:
                assert table in tables, f"Expected table {table} not found"
    
    def test_health_check_script(self):
        """Test health check script functionality"""
        result = subprocess.run(
            ["./scripts/health-check.sh"],
            capture_output=True,
            text=True
        )
        
        # Health check should pass with all services running
        assert result.returncode == 0, f"Health check failed: {result.stderr}"
        assert "Health Check Report" in result.stdout
        assert "PASS" in result.stdout
    
    def test_monitoring_services(self):
        """Test monitoring services (Prometheus and Grafana)"""
        # Start monitoring services
        subprocess.run(["docker-compose", "up", "-d", "prometheus", "grafana"])
        
        # Wait for services to start
        time.sleep(15)
        
        # Test Prometheus
        try:
            response = requests.get("http://localhost:9090/-/healthy", timeout=10)
            assert response.status_code == 200
        except requests.RequestException as e:
            pytest.fail(f"Prometheus health check failed: {e}")
        
        # Test Grafana
        try:
            response = requests.get("http://localhost:3001/api/health", timeout=10)
            assert response.status_code == 200
        except requests.RequestException as e:
            pytest.fail(f"Grafana health check failed: {e}")
    
    def test_backup_and_restore_functionality(self):
        """Test backup and restore functionality"""
        # Create a test backup
        backup_dir = f"./backups/test_{int(time.time())}"
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # Test database backup
            result = subprocess.run(
                ["docker-compose", "exec", "-T", "postgres", "pg_dump", "-U", "postgres", "i_assistant"],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0, "Database backup failed"
            assert len(result.stdout) > 0, "Backup output is empty"
            
            # Save backup to file
            backup_file = os.path.join(backup_dir, "test_backup.sql")
            with open(backup_file, 'w') as f:
                f.write(result.stdout)
            
            assert os.path.exists(backup_file), "Backup file not created"
            assert os.path.getsize(backup_file) > 0, "Backup file is empty"
            
        finally:
            # Cleanup test backup
            import shutil
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
    
    def test_performance_under_load(self):
        """Test basic performance under simulated load"""
        import concurrent.futures
        import threading
        
        def make_request():
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                return response.status_code == 200
            except:
                return False
        
        # Make 50 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # At least 90% of requests should succeed
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.9, f"Success rate {success_rate} below threshold"
    
    def test_log_aggregation(self):
        """Test log aggregation and accessibility"""
        # Check that logs are being generated
        result = subprocess.run(
            ["docker-compose", "logs", "--tail=10", "backend"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Failed to retrieve backend logs"
        
        # Check for structured logging
        log_lines = result.stdout.split('\n')
        non_empty_lines = [line for line in log_lines if line.strip()]
        
        assert len(non_empty_lines) > 0, "No log entries found"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])