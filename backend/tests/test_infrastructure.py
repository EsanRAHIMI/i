"""
Infrastructure and deployment tests for i Assistant
"""
import asyncio
import json
import os
import subprocess
import time
from typing import Dict, List

import docker
import pytest
import requests
from sqlalchemy import create_engine, text


class TestDockerInfrastructure:
    """Test Docker container builds and connectivity"""
    
    @pytest.fixture(scope="class")
    def docker_client(self):
        """Docker client fixture"""
        return docker.from_env()
    
    def test_backend_dockerfile_exists(self):
        """Test that backend Dockerfile exists and is valid"""
        dockerfile_path = "backend/Dockerfile"
        assert os.path.exists(dockerfile_path), "Backend Dockerfile not found"
        
        with open(dockerfile_path, 'r') as f:
            content = f.read()
            assert "FROM python:" in content
            assert "WORKDIR /app" in content
            assert "EXPOSE 8000" in content
    
    def test_frontend_dockerfile_exists(self):
        """Test that frontend Dockerfile exists and is valid"""
        dockerfile_path = "frontend/Dockerfile"
        assert os.path.exists(dockerfile_path), "Frontend Dockerfile not found"
        
        with open(dockerfile_path, 'r') as f:
            content = f.read()
            assert "FROM node:" in content
            assert "WORKDIR /app" in content
            assert "EXPOSE 3000" in content
    
    def test_docker_compose_config(self):
        """Test Docker Compose configuration is valid"""
        result = subprocess.run(
            ["docker-compose", "config"],
            capture_output=True,
            text=True,
            cwd=".."
        )
        assert result.returncode == 0, f"Docker Compose config invalid: {result.stderr}"
    
    def test_backend_image_build(self, docker_client):
        """Test backend Docker image builds successfully"""
        try:
            image, logs = docker_client.images.build(
                path="../backend",
                tag="i-assistant-backend:test",
                rm=True
            )
            assert image is not None
            assert "i-assistant-backend:test" in [tag for tag in image.tags]
        except Exception as e:
            pytest.fail(f"Backend image build failed: {e}")
    
    def test_frontend_image_build(self, docker_client):
        """Test frontend Docker image builds successfully"""
        try:
            image, logs = docker_client.images.build(
                path="../frontend",
                tag="i-assistant-frontend:test",
                rm=True
            )
            assert image is not None
            assert "i-assistant-frontend:test" in [tag for tag in image.tags]
        except Exception as e:
            pytest.fail(f"Frontend image build failed: {e}")


class TestServiceConnectivity:
    """Test service connectivity and health checks"""
    
    @pytest.fixture(scope="class")
    def services_running(self):
        """Ensure services are running for tests"""
        # Start services if not running
        subprocess.run(["docker-compose", "up", "-d"], cwd="..")
        
        # Wait for services to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    break
            except requests.RequestException:
                pass
            
            if i == max_retries - 1:
                pytest.fail("Services failed to start within timeout")
            
            time.sleep(2)
        
        yield
        
        # Cleanup after tests
        subprocess.run(["docker-compose", "down"], cwd="..")
    
    def test_postgres_connectivity(self, services_running):
        """Test PostgreSQL database connectivity"""
        try:
            engine = create_engine("postgresql://postgres:postgres@localhost:5432/i_assistant")
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1
        except Exception as e:
            pytest.fail(f"PostgreSQL connectivity failed: {e}")
    
    def test_redis_connectivity(self, services_running):
        """Test Redis connectivity"""
        import redis
        
        try:
            r = redis.Redis(host='localhost', port=6379, password='redis123', decode_responses=True)
            r.ping()
            
            # Test basic operations
            r.set('test_key', 'test_value')
            assert r.get('test_key') == 'test_value'
            r.delete('test_key')
        except Exception as e:
            pytest.fail(f"Redis connectivity failed: {e}")
    
    def test_minio_connectivity(self, services_running):
        """Test MinIO object storage connectivity"""
        try:
            response = requests.get("http://localhost:9000/minio/health/live", timeout=10)
            assert response.status_code == 200
        except Exception as e:
            pytest.fail(f"MinIO connectivity failed: {e}")
    
    def test_backend_health_endpoint(self, services_running):
        """Test backend health endpoint"""
        try:
            response = requests.get("http://localhost:8000/health", timeout=10)
            assert response.status_code == 200
            
            data = response.json()
            assert data.get("status") == "healthy"
        except Exception as e:
            pytest.fail(f"Backend health check failed: {e}")
    
    def test_frontend_health_endpoint(self, services_running):
        """Test frontend health endpoint"""
        try:
            response = requests.get("http://localhost:3000/api/health", timeout=10)
            assert response.status_code == 200
        except Exception as e:
            pytest.fail(f"Frontend health check failed: {e}")
    
    def test_nginx_proxy(self, services_running):
        """Test Nginx reverse proxy"""
        try:
            # Test HTTP to HTTPS redirect
            response = requests.get("http://localhost/health", allow_redirects=False, timeout=10)
            assert response.status_code == 301
            
            # Test HTTPS endpoint (with SSL verification disabled for self-signed cert)
            response = requests.get("https://localhost/health", verify=False, timeout=10)
            assert response.status_code == 200
        except Exception as e:
            pytest.fail(f"Nginx proxy test failed: {e}")


class TestDatabaseMigrations:
    """Test database migration functionality"""
    
    def test_alembic_current(self):
        """Test Alembic current command"""
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "backend", "alembic", "current"],
            capture_output=True,
            text=True,
            cwd=".."
        )
        assert result.returncode == 0, f"Alembic current failed: {result.stderr}"
    
    def test_alembic_history(self):
        """Test Alembic history command"""
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "backend", "alembic", "history"],
            capture_output=True,
            text=True,
            cwd=".."
        )
        assert result.returncode == 0, f"Alembic history failed: {result.stderr}"
    
    def test_migration_scripts_exist(self):
        """Test that migration scripts exist"""
        migrations_dir = "../backend/alembic/versions"
        assert os.path.exists(migrations_dir), "Migrations directory not found"
        
        migration_files = [f for f in os.listdir(migrations_dir) if f.endswith('.py')]
        assert len(migration_files) > 0, "No migration files found"


class TestDeploymentScripts:
    """Test deployment scripts functionality"""
    
    def test_setup_script_exists(self):
        """Test that setup script exists and is executable"""
        script_path = "../scripts/setup.sh"
        assert os.path.exists(script_path), "Setup script not found"
        assert os.access(script_path, os.X_OK), "Setup script not executable"
    
    def test_deploy_script_exists(self):
        """Test that deploy script exists and is executable"""
        script_path = "../scripts/deploy.sh"
        assert os.path.exists(script_path), "Deploy script not found"
        assert os.access(script_path, os.X_OK), "Deploy script not executable"
    
    def test_health_check_script_exists(self):
        """Test that health check script exists and is executable"""
        script_path = "../scripts/health-check.sh"
        assert os.path.exists(script_path), "Health check script not found"
        assert os.access(script_path, os.X_OK), "Health check script not executable"
    
    def test_migrate_script_exists(self):
        """Test that migrate script exists and is executable"""
        script_path = "../scripts/migrate.sh"
        assert os.path.exists(script_path), "Migrate script not found"
        assert os.access(script_path, os.X_OK), "Migrate script not executable"
    
    def test_setup_script_help(self):
        """Test setup script help functionality"""
        result = subprocess.run(
            ["../scripts/setup.sh", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout
        assert "--production" in result.stdout
    
    def test_health_check_script_execution(self):
        """Test health check script can execute"""
        # Start minimal services for health check
        subprocess.run(["docker-compose", "up", "-d", "postgres", "redis"], cwd="..")
        time.sleep(10)
        
        try:
            result = subprocess.run(
                ["../scripts/health-check.sh"],
                capture_output=True,
                text=True,
                timeout=60
            )
            # Script may fail due to missing services, but should not crash
            assert "Health Check Report" in result.stdout
        finally:
            subprocess.run(["docker-compose", "down"], cwd="..")


class TestSSLConfiguration:
    """Test SSL certificate configuration"""
    
    def test_ssl_directory_exists(self):
        """Test SSL directory exists"""
        ssl_dir = "../infra/ssl"
        assert os.path.exists(ssl_dir), "SSL directory not found"
    
    def test_self_signed_certificates_exist(self):
        """Test self-signed certificates exist"""
        cert_file = "../infra/ssl/nginx-selfsigned.crt"
        key_file = "../infra/ssl/nginx-selfsigned.key"
        
        assert os.path.exists(cert_file), "SSL certificate not found"
        assert os.path.exists(key_file), "SSL private key not found"
    
    def test_certificate_validity(self):
        """Test SSL certificate is valid"""
        cert_file = "../infra/ssl/nginx-selfsigned.crt"
        
        if os.path.exists(cert_file):
            result = subprocess.run(
                ["openssl", "x509", "-in", cert_file, "-noout", "-text"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, "Certificate validation failed"
            assert "Certificate:" in result.stdout


class TestMonitoringConfiguration:
    """Test monitoring and observability configuration"""
    
    def test_prometheus_config_exists(self):
        """Test Prometheus configuration exists"""
        config_file = "../infra/prometheus/prometheus.yml"
        assert os.path.exists(config_file), "Prometheus config not found"
        
        with open(config_file, 'r') as f:
            content = f.read()
            assert "scrape_configs:" in content
            assert "backend" in content
            assert "frontend" in content
    
    def test_grafana_provisioning_exists(self):
        """Test Grafana provisioning configuration exists"""
        datasources_file = "../infra/grafana/provisioning/datasources/prometheus.yml"
        dashboards_file = "../infra/grafana/provisioning/dashboards/dashboard.yml"
        
        assert os.path.exists(datasources_file), "Grafana datasources config not found"
        assert os.path.exists(dashboards_file), "Grafana dashboards config not found"


class TestEnvironmentConfiguration:
    """Test environment configuration"""
    
    def test_env_example_exists(self):
        """Test .env.example file exists"""
        env_file = "../.env.example"
        assert os.path.exists(env_file), ".env.example not found"
        
        with open(env_file, 'r') as f:
            content = f.read()
            required_vars = [
                "POSTGRES_PASSWORD",
                "REDIS_PASSWORD",
                "JWT_SECRET_KEY",
                "MINIO_ROOT_PASSWORD"
            ]
            
            for var in required_vars:
                assert var in content, f"Required environment variable {var} not found"
    
    def test_service_env_files_exist(self):
        """Test service-specific .env.example files exist"""
        services = ["backend", "frontend"]
        
        for service in services:
            env_file = f"../{service}/.env.example"
            if os.path.exists(f"../{service}"):
                assert os.path.exists(env_file), f"{service}/.env.example not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])