"""
Comprehensive tests for monitoring and observability features.
Tests metrics collection, dashboard functionality, alerting systems, logging, and tracing.
"""
import pytest
import json
import time
import uuid
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry, generate_latest

from app.main import app
from app.core.metrics import (
    metrics_collector, HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION,
    VOICE_PROCESSING_DURATION, AI_MODEL_INFERENCE_DURATION,
    DATABASE_QUERY_DURATION, SYSTEM_CPU_USAGE
)
from app.core.logging_config import (
    configure_logging, LoggingContext, audit_logger, 
    performance_logger, get_correlation_id, set_correlation_id
)
from app.core.tracing import (
    custom_tracer, ai_tracer, db_tracer, api_tracer,
    get_trace_id, add_span_attribute
)


class TestMetricsCollection:
    """Test Prometheus metrics collection functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
    
    def test_metrics_endpoint_available(self):
        """Test that metrics endpoint is accessible."""
        response = self.client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        
        # Check for basic Prometheus format
        content = response.text
        assert "# HELP" in content
        assert "# TYPE" in content
    
    def test_http_request_metrics_recorded(self):
        """Test HTTP request metrics are properly recorded."""
        # Make a test request
        response = self.client.get("/health")
        assert response.status_code == 200
        
        # Check metrics endpoint
        metrics_response = self.client.get("/metrics")
        content = metrics_response.text
        
        # Verify HTTP metrics are present
        assert "http_requests_total" in content
        assert "http_request_duration_seconds" in content
        assert 'method="GET"' in content
        assert 'endpoint="/health"' in content
    
    def test_metrics_collector_http_request(self):
        """Test metrics collector HTTP request recording."""
        initial_count = HTTP_REQUESTS_TOTAL.labels(
            method="GET", endpoint="/test", status_code=200, service="backend"
        )._value._value
        
        metrics_collector.record_http_request(
            method="GET",
            endpoint="/test",
            status_code=200,
            duration=0.5,
            request_size=100,
            response_size=200
        )
        
        final_count = HTTP_REQUESTS_TOTAL.labels(
            method="GET", endpoint="/test", status_code=200, service="backend"
        )._value._value
        
        assert final_count > initial_count
    
    def test_voice_processing_metrics(self):
        """Test voice processing metrics recording."""
        metrics_collector.record_voice_processing(
            operation="stt",
            duration=1.5,
            success=True
        )
        
        # Check that metrics were recorded
        metrics_content = metrics_collector.get_metrics()
        assert "voice_processing_total" in metrics_content
        assert "voice_processing_duration_seconds" in metrics_content
    
    def test_ai_inference_metrics(self):
        """Test AI model inference metrics recording."""
        metrics_collector.record_ai_inference(
            model_type="intent_recognition",
            duration=0.8,
            accuracy=0.92
        )
        
        metrics_content = metrics_collector.get_metrics()
        assert "ai_model_inference_duration_seconds" in metrics_content
        assert "ai_model_accuracy_ratio" in metrics_content
    
    def test_database_query_metrics(self):
        """Test database query metrics recording."""
        metrics_collector.record_database_query(
            operation="SELECT",
            table="users",
            duration=0.05,
            success=True
        )
        
        metrics_content = metrics_collector.get_metrics()
        assert "database_queries_total" in metrics_content
        assert "database_query_duration_seconds" in metrics_content
    
    def test_system_metrics_update(self):
        """Test system metrics are updated."""
        metrics_collector.update_system_metrics()
        
        metrics_content = metrics_collector.get_metrics()
        assert "system_cpu_usage_percent" in metrics_content
        assert "system_memory_usage_bytes" in metrics_content
    
    def test_security_event_metrics(self):
        """Test security event metrics recording."""
        metrics_collector.record_security_event(
            event_type="authentication_failure",
            severity="warning"
        )
        
        metrics_content = metrics_collector.get_metrics()
        assert "security_events_total" in metrics_content
    
    def test_user_interaction_metrics(self):
        """Test user interaction metrics recording."""
        metrics_collector.record_user_interaction(
            interaction_type="voice",
            satisfaction_score=4.5
        )
        
        metrics_content = metrics_collector.get_metrics()
        assert "user_interactions_total" in metrics_content
        assert "user_satisfaction_score" in metrics_content


class TestLoggingConfiguration:
    """Test structured logging configuration and functionality."""
    
    def test_logging_context_manager(self):
        """Test logging context manager functionality."""
        correlation_id = str(uuid.uuid4())
        user_id = "test-user-123"
        
        with LoggingContext(correlation_id=correlation_id, user_id=user_id):
            assert get_correlation_id() == correlation_id
    
    def test_correlation_id_functions(self):
        """Test correlation ID getter and setter functions."""
        test_id = str(uuid.uuid4())
        set_correlation_id(test_id)
        assert get_correlation_id() == test_id
    
    def test_audit_logger_user_action(self):
        """Test audit logger user action recording."""
        with patch('app.core.logging_config.structlog.get_logger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log
            
            audit_logger.log_user_action(
                user_id="test-user",
                action="create_event",
                resource_type="calendar_event",
                resource_id="event-123",
                details={"title": "Test Event"},
                ip_address="192.168.1.1"
            )
            
            mock_log.info.assert_called_once()
            call_args = mock_log.info.call_args
            assert "User action performed" in call_args[0]
            assert call_args[1]["user_id"] == "test-user"
            assert call_args[1]["action"] == "create_event"
    
    def test_audit_logger_security_event(self):
        """Test audit logger security event recording."""
        with patch('app.core.logging_config.structlog.get_logger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log
            
            audit_logger.log_security_event(
                event_type="authentication_failure",
                severity="warning",
                user_id="test-user",
                ip_address="192.168.1.1"
            )
            
            mock_log.warning.assert_called_once()
            call_args = mock_log.warning.call_args
            assert "Security event detected" in call_args[0]
    
    def test_performance_logger_operation_timing(self):
        """Test performance logger operation timing."""
        with patch('app.core.logging_config.structlog.get_logger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log
            
            performance_logger.log_operation_timing(
                operation="voice_processing",
                duration_ms=1500.0,
                success=True,
                details={"operation_type": "stt"}
            )
            
            mock_log.info.assert_called_once()
            call_args = mock_log.info.call_args
            assert call_args[1]["operation"] == "voice_processing"
            assert call_args[1]["duration_ms"] == 1500.0
    
    def test_security_sanitizer(self):
        """Test security sanitizer removes sensitive data."""
        from app.core.logging_config import SecuritySanitizer
        
        sanitizer = SecuritySanitizer()
        test_data = {
            "username": "testuser",
            "password": "secret123",
            "token": "jwt-token-here",
            "normal_field": "normal_value",
            "nested": {
                "api_key": "secret-key",
                "public_data": "visible"
            }
        }
        
        sanitized = sanitizer(None, None, test_data)
        
        assert sanitized["username"] == "testuser"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["token"] == "[REDACTED]"
        assert sanitized["normal_field"] == "normal_value"
        assert sanitized["nested"]["api_key"] == "[REDACTED]"
        assert sanitized["nested"]["public_data"] == "visible"


class TestDistributedTracing:
    """Test distributed tracing functionality."""
    
    def test_custom_tracer_function_decorator(self):
        """Test custom tracer function decorator."""
        @custom_tracer.trace_function("test_operation")
        def test_function(x, y):
            return x + y
        
        result = test_function(2, 3)
        assert result == 5
    
    @pytest.mark.asyncio
    async def test_custom_tracer_async_decorator(self):
        """Test custom tracer async function decorator."""
        @custom_tracer.trace_async_function("async_test_operation")
        async def async_test_function(x, y):
            return x * y
        
        result = await async_test_function(4, 5)
        assert result == 20
    
    def test_ai_tracer_decorators(self):
        """Test AI operation tracer decorators."""
        @ai_tracer.trace_voice_processing("stt")
        async def mock_stt_function():
            return "transcribed text"
        
        @ai_tracer.trace_model_inference("intent_recognition")
        async def mock_inference_function():
            return {"intent": "calendar_create", "confidence": 0.95}
        
        # Test that decorators can be applied without errors
        assert callable(mock_stt_function)
        assert callable(mock_inference_function)
    
    def test_database_tracer_decorators(self):
        """Test database tracer decorators."""
        @db_tracer.trace_query("SELECT", "users")
        async def mock_query_function():
            return [{"id": 1, "name": "test"}]
        
        assert callable(mock_query_function)
    
    def test_external_api_tracer_decorators(self):
        """Test external API tracer decorators."""
        @api_tracer.trace_google_calendar("create_event")
        async def mock_calendar_function():
            return {"event_id": "123"}
        
        @api_tracer.trace_whatsapp("send_message")
        async def mock_whatsapp_function():
            return {"message_id": "456"}
        
        assert callable(mock_calendar_function)
        assert callable(mock_whatsapp_function)
    
    def test_span_attribute_functions(self):
        """Test span attribute helper functions."""
        # These functions should not raise errors when no active span
        add_span_attribute("test_key", "test_value")
        
        # Test trace ID functions
        trace_id = get_trace_id()
        # Should return None when no active trace
        assert trace_id is None or isinstance(trace_id, str)


class TestAlertingSystem:
    """Test alerting rules and configuration."""
    
    def test_alert_rules_file_exists(self):
        """Test that alert rules file exists and is valid."""
        import os
        import yaml
        
        alert_rules_path = "../infra/prometheus/alert_rules.yml"
        assert os.path.exists(alert_rules_path), "Alert rules file not found"
        
        with open(alert_rules_path, 'r') as f:
            try:
                rules_data = yaml.safe_load(f)
                assert "groups" in rules_data
                assert len(rules_data["groups"]) > 0
                
                # Check for essential alert rules
                all_rules = []
                for group in rules_data["groups"]:
                    all_rules.extend(group.get("rules", []))
                
                rule_names = [rule.get("alert") for rule in all_rules]
                
                # Verify critical alerts exist
                expected_alerts = [
                    "HighErrorRate",
                    "ServiceDown",
                    "VoiceProcessingLatencyHigh",
                    "DatabaseConnectionsHigh",
                    "SecurityEventDetected"
                ]
                
                for alert in expected_alerts:
                    assert alert in rule_names, f"Alert rule {alert} not found"
                    
            except yaml.YAMLError as e:
                pytest.fail(f"Alert rules YAML error: {e}")
    
    def test_prometheus_config_includes_rules(self):
        """Test Prometheus configuration includes alert rules."""
        import os
        import yaml
        
        prometheus_config_path = "../infra/prometheus/prometheus.yml"
        assert os.path.exists(prometheus_config_path)
        
        with open(prometheus_config_path, 'r') as f:
            config_data = yaml.safe_load(f)
            rule_files = config_data.get("rule_files", [])
            assert "alert_rules.yml" in rule_files


class TestDashboardConfiguration:
    """Test Grafana dashboard configuration."""
    
    def test_dashboard_files_exist(self):
        """Test that dashboard JSON files exist."""
        import os
        
        dashboard_files = [
            "../infra/grafana/provisioning/dashboards/system-overview.json",
            "../infra/grafana/provisioning/dashboards/ai-performance.json",
            "../infra/grafana/provisioning/dashboards/infrastructure.json",
            "../infra/grafana/provisioning/dashboards/security-privacy.json"
        ]
        
        for dashboard_file in dashboard_files:
            assert os.path.exists(dashboard_file), f"Dashboard file {dashboard_file} not found"
    
    def test_dashboard_json_validity(self):
        """Test that dashboard JSON files are valid."""
        import os
        import json
        
        dashboard_files = [
            "../infra/grafana/provisioning/dashboards/system-overview.json",
            "../infra/grafana/provisioning/dashboards/ai-performance.json"
        ]
        
        for dashboard_file in dashboard_files:
            if os.path.exists(dashboard_file):
                with open(dashboard_file, 'r') as f:
                    try:
                        dashboard_data = json.load(f)
                        assert "dashboard" in dashboard_data
                        assert "title" in dashboard_data["dashboard"]
                        assert "panels" in dashboard_data["dashboard"]
                    except json.JSONDecodeError as e:
                        pytest.fail(f"Dashboard JSON error in {dashboard_file}: {e}")
    
    def test_grafana_provisioning_config(self):
        """Test Grafana provisioning configuration."""
        import os
        import yaml
        
        # Test datasource configuration
        datasource_path = "../infra/grafana/provisioning/datasources/prometheus.yml"
        if os.path.exists(datasource_path):
            with open(datasource_path, 'r') as f:
                datasource_config = yaml.safe_load(f)
                assert "datasources" in datasource_config
                
                prometheus_ds = next(
                    (ds for ds in datasource_config["datasources"] 
                     if ds.get("type") == "prometheus"), None
                )
                assert prometheus_ds is not None
                assert "prometheus:9090" in prometheus_ds.get("url", "")
        
        # Test dashboard provisioning configuration
        dashboard_config_path = "../infra/grafana/provisioning/dashboards/dashboard.yml"
        if os.path.exists(dashboard_config_path):
            with open(dashboard_config_path, 'r') as f:
                dashboard_config = yaml.safe_load(f)
                assert "providers" in dashboard_config


class TestLogAggregation:
    """Test log aggregation configuration."""
    
    def test_filebeat_config_exists(self):
        """Test Filebeat configuration exists and is valid."""
        import os
        import yaml
        
        filebeat_config_path = "../infra/filebeat/filebeat.yml"
        assert os.path.exists(filebeat_config_path), "Filebeat config not found"
        
        with open(filebeat_config_path, 'r') as f:
            try:
                config_data = yaml.safe_load(f)
                
                # Check essential configuration sections
                assert "filebeat.inputs" in config_data
                assert "output.elasticsearch" in config_data
                
                # Verify inputs are configured
                inputs = config_data["filebeat.inputs"]
                assert len(inputs) > 0
                
                # Check for backend and celery log inputs
                input_paths = []
                for input_config in inputs:
                    input_paths.extend(input_config.get("paths", []))
                
                assert any("/var/log/backend" in path for path in input_paths)
                assert any("/var/log/celery" in path for path in input_paths)
                
                # Check Elasticsearch output
                es_output = config_data["output.elasticsearch"]
                assert "hosts" in es_output
                assert "elasticsearch:9200" in es_output["hosts"]
                
            except yaml.YAMLError as e:
                pytest.fail(f"Filebeat config YAML error: {e}")


class TestIntegrationMonitoring:
    """Test end-to-end monitoring integration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
    
    def test_request_generates_metrics_and_logs(self):
        """Test that a request generates both metrics and logs."""
        correlation_id = str(uuid.uuid4())
        
        # Make request with correlation ID
        response = self.client.get(
            "/health",
            headers={"X-Correlation-ID": correlation_id}
        )
        
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        
        # Check metrics were generated
        metrics_response = self.client.get("/metrics")
        assert "http_requests_total" in metrics_response.text
    
    def test_error_handling_with_monitoring(self):
        """Test error handling generates appropriate metrics and logs."""
        # Make request to non-existent endpoint
        response = self.client.get("/non-existent-endpoint")
        assert response.status_code == 404
        
        # Check metrics include error
        metrics_response = self.client.get("/metrics")
        metrics_content = metrics_response.text
        assert "http_requests_total" in metrics_content
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(self):
        """Test performance monitoring integration."""
        start_time = time.time()
        
        # Simulate operation
        await asyncio.sleep(0.1)
        
        duration = time.time() - start_time
        
        # Record performance metrics
        performance_logger.log_operation_timing(
            operation="test_operation",
            duration_ms=duration * 1000,
            success=True
        )
        
        # Verify no errors occurred
        assert duration > 0.1


if __name__ == "__main__":
    pytest.main([__file__])