"""
Deployment-specific tests for i Assistant
"""
import json
import os
import subprocess
import time
from typing import Dict, List

import pytest
import requests
import yaml


class TestCIConfiguration:
    """Test CI/CD pipeline configuration"""
    
    def test_github_workflows_exist(self):
        """Test GitHub Actions workflow files exist"""
        workflows_dir = "../.github/workflows"
        assert os.path.exists(workflows_dir), "GitHub workflows directory not found"
        
        required_workflows = [
            "ci.yml",
            "cd-staging.yml",
            "cd-production.yml",
            "security-scan.yml"
        ]
        
        for workflow in required_workflows:
            workflow_path = os.path.join(workflows_dir, workflow)
            assert os.path.exists(workflow_path), f"Workflow {workflow} not found"
    
    def test_ci_workflow_syntax(self):
        """Test CI workflow YAML syntax is valid"""
        workflow_path = "../.github/workflows/ci.yml"
        
        with open(workflow_path, 'r') as f:
            try:
                workflow_data = yaml.safe_load(f)
                assert "name" in workflow_data
                assert "on" in workflow_data
                assert "jobs" in workflow_data
            except yaml.YAMLError as e:
                pytest.fail(f"CI workflow YAML syntax error: {e}")
    
    def test_dependabot_config_exists(self):
        """Test Dependabot configuration exists"""
        config_path = "../.github/dependabot.yml"
        assert os.path.exists(config_path), "Dependabot config not found"
        
        with open(config_path, 'r') as f:
            try:
                config_data = yaml.safe_load(f)
                assert "version" in config_data
                assert "updates" in config_data
                assert len(config_data["updates"]) > 0
            except yaml.YAMLError as e:
                pytest.fail(f"Dependabot config YAML syntax error: {e}")
    
    def test_sonar_config_exists(self):
        """Test SonarCloud configuration exists"""
        config_path = "../sonar-project.properties"
        assert os.path.exists(config_path), "SonarCloud config not found"
        
        with open(config_path, 'r') as f:
            content = f.read()
            required_props = [
                "sonar.projectKey",
                "sonar.sources",
                "sonar.tests"
            ]
            
            for prop in required_props:
                assert prop in content, f"Required SonarCloud property {prop} not found"


class TestDockerComposeProduction:
    """Test production Docker Compose configuration"""
    
    def test_production_compose_exists(self):
        """Test production Docker Compose override exists"""
        compose_path = "../docker-compose.prod.yml"
        assert os.path.exists(compose_path), "Production compose file not found"
    
    def test_production_compose_syntax(self):
        """Test production compose file syntax"""
        compose_path = "../docker-compose.prod.yml"
        
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.yml", "-f", compose_path, "config"],
            capture_output=True,
            text=True,
            cwd=".."
        )
        assert result.returncode == 0, f"Production compose syntax error: {result.stderr}"
    
    def test_production_optimizations(self):
        """Test production-specific optimizations are configured"""
        compose_path = "../docker-compose.prod.yml"
        
        with open(compose_path, 'r') as f:
            try:
                compose_data = yaml.safe_load(f)
                services = compose_data.get("services", {})
                
                # Check restart policies
                for service_name, service_config in services.items():
                    if "restart" in service_config:
                        assert service_config["restart"] == "unless-stopped"
                
                # Check logging configuration
                postgres_config = services.get("postgres", {})
                if "logging" in postgres_config:
                    logging_config = postgres_config["logging"]
                    assert logging_config.get("driver") == "json-file"
                    assert "max-size" in logging_config.get("options", {})
                
            except yaml.YAMLError as e:
                pytest.fail(f"Production compose YAML syntax error: {e}")


class TestSecurityConfiguration:
    """Test security-related configuration"""
    
    def test_dependency_check_suppressions_exist(self):
        """Test OWASP dependency check suppressions file exists"""
        suppressions_path = "../dependency-check-suppressions.xml"
        assert os.path.exists(suppressions_path), "Dependency check suppressions not found"
        
        with open(suppressions_path, 'r') as f:
            content = f.read()
            assert "<?xml version" in content
            assert "suppressions" in content
    
    def test_nginx_security_headers(self):
        """Test Nginx security headers configuration"""
        nginx_config_path = "../infra/nginx/conf.d/ssl-params.conf"
        
        if os.path.exists(nginx_config_path):
            with open(nginx_config_path, 'r') as f:
                content = f.read()
                security_headers = [
                    "X-Frame-Options",
                    "X-Content-Type-Options",
                    "X-XSS-Protection",
                    "Strict-Transport-Security",
                    "Content-Security-Policy"
                ]
                
                for header in security_headers:
                    assert header in content, f"Security header {header} not configured"
    
    def test_ssl_configuration(self):
        """Test SSL/TLS configuration"""
        ssl_config_path = "../infra/nginx/conf.d/ssl-params.conf"
        
        if os.path.exists(ssl_config_path):
            with open(ssl_config_path, 'r') as f:
                content = f.read()
                
                # Check for secure SSL protocols
                assert "TLSv1.2" in content or "TLSv1.3" in content
                
                # Check for secure ciphers
                assert "ECDHE" in content
                
                # Check for HSTS
                assert "Strict-Transport-Security" in content


class TestBackupAndRecovery:
    """Test backup and recovery functionality"""
    
    def test_backup_directories_created(self):
        """Test backup directories are created by deployment scripts"""
        # This would be tested after running deployment scripts
        pass
    
    def test_database_backup_functionality(self):
        """Test database backup can be created"""
        # Start postgres service for testing
        subprocess.run(["docker-compose", "up", "-d", "postgres"], cwd="..")
        time.sleep(10)
        
        try:
            # Test pg_dump command
            result = subprocess.run(
                ["docker-compose", "exec", "-T", "postgres", "pg_dump", "--version"],
                capture_output=True,
                text=True,
                cwd=".."
            )
            assert result.returncode == 0, "pg_dump not available"
            assert "pg_dump" in result.stdout
            
        finally:
            subprocess.run(["docker-compose", "down"], cwd="..")


class TestLoadBalancingAndScaling:
    """Test load balancing and scaling configuration"""
    
    def test_nginx_upstream_configuration(self):
        """Test Nginx upstream configuration for load balancing"""
        nginx_config_path = "../infra/nginx/conf.d/default.conf"
        
        with open(nginx_config_path, 'r') as f:
            content = f.read()
            
            # Check for upstream blocks
            assert "upstream backend" in content
            assert "upstream frontend" in content
            
            # Check for proxy_pass directives
            assert "proxy_pass http://backend" in content
            assert "proxy_pass http://frontend" in content
    
    def test_docker_compose_scaling_ready(self):
        """Test Docker Compose configuration supports scaling"""
        # Check that services don't have conflicting port mappings that would prevent scaling
        result = subprocess.run(
            ["docker-compose", "config"],
            capture_output=True,
            text=True,
            cwd=".."
        )
        assert result.returncode == 0
        
        # Parse the composed configuration
        try:
            config_data = yaml.safe_load(result.stdout)
            services = config_data.get("services", {})
            
            # Services that should be scalable shouldn't expose ports directly
            scalable_services = ["backend", "frontend", "celery-worker"]
            
            for service_name in scalable_services:
                if service_name in services:
                    service_config = services[service_name]
                    # In production, these services shouldn't expose ports directly
                    # (they should go through nginx)
                    pass  # This test would be more specific in a real deployment
                    
        except yaml.YAMLError as e:
            pytest.fail(f"Composed configuration YAML error: {e}")


class TestMonitoringAndObservability:
    """Test monitoring and observability setup"""
    
    def test_prometheus_targets_configured(self):
        """Test Prometheus scrape targets are properly configured"""
        prometheus_config_path = "../infra/prometheus/prometheus.yml"
        
        with open(prometheus_config_path, 'r') as f:
            try:
                config_data = yaml.safe_load(f)
                scrape_configs = config_data.get("scrape_configs", [])
                
                # Check that all services have scrape configs
                expected_jobs = ["backend", "frontend", "postgres", "redis"]
                configured_jobs = [job.get("job_name") for job in scrape_configs]
                
                for job in expected_jobs:
                    assert job in configured_jobs, f"Prometheus job {job} not configured"
                    
            except yaml.YAMLError as e:
                pytest.fail(f"Prometheus config YAML error: {e}")
    
    def test_grafana_datasource_configured(self):
        """Test Grafana datasource is properly configured"""
        datasource_path = "../infra/grafana/provisioning/datasources/prometheus.yml"
        
        with open(datasource_path, 'r') as f:
            try:
                config_data = yaml.safe_load(f)
                datasources = config_data.get("datasources", [])
                
                assert len(datasources) > 0, "No Grafana datasources configured"
                
                prometheus_ds = next((ds for ds in datasources if ds.get("type") == "prometheus"), None)
                assert prometheus_ds is not None, "Prometheus datasource not configured"
                assert "prometheus:9090" in prometheus_ds.get("url", "")
                
            except yaml.YAMLError as e:
                pytest.fail(f"Grafana datasource config YAML error: {e}")


class TestPerformanceConfiguration:
    """Test performance-related configuration"""
    
    def test_database_performance_settings(self):
        """Test database performance settings in production"""
        compose_prod_path = "../docker-compose.prod.yml"
        
        with open(compose_prod_path, 'r') as f:
            try:
                config_data = yaml.safe_load(f)
                postgres_service = config_data.get("services", {}).get("postgres", {})
                
                if "command" in postgres_service:
                    command = postgres_service["command"]
                    
                    # Check for performance-related PostgreSQL settings
                    performance_settings = [
                        "shared_buffers",
                        "effective_cache_size",
                        "max_connections"
                    ]
                    
                    for setting in performance_settings:
                        assert setting in command, f"PostgreSQL performance setting {setting} not configured"
                        
            except yaml.YAMLError as e:
                pytest.fail(f"Production compose YAML error: {e}")
    
    def test_redis_performance_settings(self):
        """Test Redis performance settings in production"""
        compose_prod_path = "../docker-compose.prod.yml"
        
        with open(compose_prod_path, 'r') as f:
            try:
                config_data = yaml.safe_load(f)
                redis_service = config_data.get("services", {}).get("redis", {})
                
                if "command" in redis_service:
                    command = redis_service["command"]
                    
                    # Check for Redis performance settings
                    assert "maxmemory" in command, "Redis maxmemory not configured"
                    assert "maxmemory-policy" in command, "Redis maxmemory-policy not configured"
                    
            except yaml.YAMLError as e:
                pytest.fail(f"Production compose YAML error: {e}")


class TestDisasterRecovery:
    """Test disaster recovery procedures"""
    
    def test_backup_script_functionality(self):
        """Test backup script can create backups"""
        # This would test the actual backup creation process
        # For now, just verify the script structure
        deploy_script_path = "../scripts/deploy.sh"
        
        with open(deploy_script_path, 'r') as f:
            content = f.read()
            
            # Check for backup-related functions
            assert "create_backup" in content, "Backup function not found in deploy script"
            assert "pg_dump" in content, "Database backup command not found"
    
    def test_rollback_functionality(self):
        """Test rollback functionality exists"""
        deploy_script_path = "../scripts/deploy.sh"
        
        with open(deploy_script_path, 'r') as f:
            content = f.read()
            
            # Check for rollback functionality
            assert "rollback" in content, "Rollback function not found"
            assert "--rollback" in content, "Rollback option not available"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])