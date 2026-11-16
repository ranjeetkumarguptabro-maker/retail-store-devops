"""Unit tests for ResourceAnomalyAnalyzer and DeploymentAnalyzer."""

from unittest.mock import MagicMock, patch
from automation.analyzers.resource_analyzer import ResourceAnomalyAnalyzer
from automation.analyzers.deployment_analyzer import DeploymentAnalyzer


def test_resource_analyzer_healthy():
    analyzer = ResourceAnomalyAnalyzer()
    resource_data = {
        "namespace": "retail-store",
        "total_requested_cpu_cores": 1.0,
        "total_requested_memory_mb": 1024.0,
        "services": {
            "ui": {
                "containers": [
                    {
                        "pod": "ui-123",
                        "container": "ui",
                        "cpu_request": 0.5,
                        "cpu_limit": 1.0,
                        "memory_request_bytes": 536870912,
                        "memory_limit_bytes": 1073741824,
                    }
                ]
            }
        },
    }
    nodes_data = [
        {
            "name": "node-1",
            "ready": True,
            "conditions": {"Ready": True, "MemoryPressure": False, "DiskPressure": False},
            "allocatable": {"cpu": "4", "memory": "8Gi"},
        }
    ]

    res = analyzer.analyze(resource_data, nodes_data)
    assert res["status"] == "HEALTHY"
    assert res["anomaly_count"] == 0
    assert res["cpu_allocation_percent"] == 25.0


def test_resource_analyzer_missing_limits_and_pressure():
    analyzer = ResourceAnomalyAnalyzer()
    resource_data = {
        "namespace": "retail-store",
        "total_requested_cpu_cores": 3.8,
        "total_requested_memory_mb": 7500.0,
        "services": {
            "cart": {
                "containers": [
                    {
                        "pod": "cart-123",
                        "container": "cart",
                        "cpu_request": 0.0,
                        "cpu_limit": 0.0,
                        "memory_request_bytes": 0,
                        "memory_limit_bytes": 0,
                    }
                ]
            }
        },
    }
    nodes_data = [
        {
            "name": "node-1",
            "ready": True,
            "conditions": {"Ready": True, "MemoryPressure": True, "DiskPressure": False},
            "allocatable": {"cpu": "4", "memory": "8Gi"},
        }
    ]

    res = analyzer.analyze(resource_data, nodes_data)
    assert res["status"] == "CRITICAL"
    types = [a["type"] for a in res["anomalies"]]
    assert "MissingResourceRequests" in types
    assert "MissingResourceLimits" in types
    assert "NodeMemoryPressure" in types
    assert len(res["recommendations"]) > 0


def test_deployment_analyzer_rollout_status():
    mock_apps = MagicMock()
    mock_dep = MagicMock()
    mock_dep.metadata.name = "retail-store-ui"
    mock_dep.spec.replicas = 2
    mock_dep.status.available_replicas = 2
    mock_dep.status.updated_replicas = 2
    mock_dep.status.ready_replicas = 2

    cond = MagicMock()
    cond.type = "Progressing"
    cond.status = "True"
    mock_dep.status.conditions = [cond]

    mock_apps.list_namespaced_deployment.return_value.items = [mock_dep]

    analyzer = DeploymentAnalyzer(apps_api=mock_apps, namespace="retail-store")
    res = analyzer.analyze_deployments()

    assert res["all_deployments_ready"] is True
    assert res["deployment_count"] == 1
    assert res["deployments"]["retail-store-ui"]["rollout_complete"] is True


def test_deployment_analyzer_endpoint_probing():
    analyzer = DeploymentAnalyzer(namespace="retail-store")

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.elapsed.total_seconds.return_value = 0.045
        mock_get.return_value = mock_resp

        probe_res = analyzer.verify_endpoint_health({
            "ui": "http://localhost:8888",
            "catalog": "http://localhost:8081/catalog/products",
        })

        assert probe_res["all_endpoints_healthy"] is True
        assert probe_res["probed_endpoints"] == 2
        assert probe_res["results"]["ui"]["status_code"] == 200
        assert probe_res["results"]["ui"]["response_time_ms"] == 45.0
