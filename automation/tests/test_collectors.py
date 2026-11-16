"""Unit tests for Kubernetes telemetry collectors."""

from unittest.mock import MagicMock
from automation.collectors.pod_collector import PodCollector
from automation.collectors.node_collector import NodeCollector
from automation.collectors.resource_collector import ResourceCollector, parse_cpu, parse_memory_bytes
from automation.collectors.event_collector import EventCollector


def test_parse_cpu():
    assert parse_cpu("250m") == 0.25
    assert parse_cpu("1") == 1.0
    assert parse_cpu("500m") == 0.5
    assert parse_cpu("1000000u") == 1.0
    assert parse_cpu("1000000000n") == 1.0
    assert parse_cpu(None) == 0.0
    assert parse_cpu("invalid") == 0.0


def test_parse_memory_bytes():
    assert parse_memory_bytes("128Mi") == 128 * 1024 * 1024
    assert parse_memory_bytes("1Gi") == 1024 * 1024 * 1024
    assert parse_memory_bytes("500M") == 500 * 1000 * 1000
    assert parse_memory_bytes("1024") == 1024
    assert parse_memory_bytes(None) == 0
    assert parse_memory_bytes("invalid") == 0


def test_pod_collector_normal():
    mock_api = MagicMock()

    # Mock pod item
    mock_pod = MagicMock()
    mock_pod.metadata.name = "retail-store-ui-6789-xyz"
    mock_pod.metadata.labels = {"app.kubernetes.io/name": "ui"}
    mock_pod.spec.node_name = "node-1"
    mock_pod.status.phase = "Running"
    mock_pod.status.pod_ip = "10.0.0.5"
    mock_pod.status.start_time = "2026-11-16T12:00:00Z"

    # Container status
    c_status = MagicMock()
    c_status.name = "ui"
    c_status.ready = True
    c_status.restart_count = 0
    c_status.state.running = MagicMock()
    c_status.state.waiting = None
    c_status.state.terminated = None
    mock_pod.status.container_statuses = [c_status]

    mock_api.list_namespaced_pod.return_value.items = [mock_pod]

    collector = PodCollector(core_api=mock_api, namespace="retail-store")
    data = collector.collect()

    assert len(data) == 1
    assert data[0]["name"] == "retail-store-ui-6789-xyz"
    assert data[0]["service"] == "ui"
    assert data[0]["phase"] == "Running"
    assert data[0]["ready"] is True
    assert data[0]["restart_count"] == 0
    assert data[0]["health_status"] == "HEALTHY"


def test_pod_collector_crashloop():
    mock_api = MagicMock()

    mock_pod = MagicMock()
    mock_pod.metadata.name = "retail-store-cart-999-abc"
    mock_pod.metadata.labels = {"app": "cart"}
    mock_pod.spec.node_name = "node-2"
    mock_pod.status.phase = "Running"
    mock_pod.status.pod_ip = "10.0.0.6"
    mock_pod.status.start_time = "2026-11-16T12:00:00Z"

    c_status = MagicMock()
    c_status.name = "cart"
    c_status.ready = False
    c_status.restart_count = 8
    c_status.state.running = None
    c_status.state.waiting = MagicMock(reason="CrashLoopBackOff", message="Back-off 5m restarting failed container")
    c_status.state.terminated = None
    mock_pod.status.container_statuses = [c_status]

    mock_api.list_namespaced_pod.return_value.items = [mock_pod]
    mock_api.read_namespaced_pod_log.return_value = "java.lang.NullPointerException: DB connection failed"

    collector = PodCollector(core_api=mock_api, namespace="retail-store")
    data = collector.collect()

    assert len(data) == 1
    assert data[0]["health_status"] == "CRASHLOOPBACKOFF"
    assert data[0]["restart_count"] == 8
    assert data[0]["has_restart_spike"] is True
    assert "CrashLoopBackOff" in data[0]["error_reasons"]
    assert "DB connection failed" in data[0]["logs"]


def test_node_collector():
    mock_api = MagicMock()

    mock_node = MagicMock()
    mock_node.metadata.name = "ip-10-0-1-50.ec2.internal"
    ready_cond = MagicMock(type="Ready", status="True")
    disk_cond = MagicMock(type="DiskPressure", status="False")
    mock_node.status.conditions = [ready_cond, disk_cond]
    mock_node.status.capacity = {"cpu": "4", "memory": "16Gi", "pods": "110"}
    mock_node.status.allocatable = {"cpu": "3.8", "memory": "15Gi", "pods": "110"}

    mock_api.list_node.return_value.items = [mock_node]

    collector = NodeCollector(core_api=mock_api)
    nodes = collector.collect()

    assert len(nodes) == 1
    assert nodes[0]["name"] == "ip-10-0-1-50.ec2.internal"
    assert nodes[0]["ready"] is True
    assert nodes[0]["capacity"]["cpu"] == "4"


def test_resource_collector():
    mock_api = MagicMock()

    mock_pod = MagicMock()
    mock_pod.metadata.name = "retail-store-catalog-abc"
    mock_pod.metadata.labels = {"app.kubernetes.io/name": "catalog"}

    container = MagicMock()
    container.name = "catalog"
    container.resources.requests = {"cpu": "200m", "memory": "256Mi"}
    container.resources.limits = {"cpu": "500m", "memory": "512Mi"}
    mock_pod.spec.containers = [container]

    mock_api.list_namespaced_pod.return_value.items = [mock_pod]

    collector = ResourceCollector(core_api=mock_api, namespace="retail-store")
    res = collector.collect()

    assert res["namespace"] == "retail-store"
    assert res["total_requested_cpu_cores"] == 0.2
    assert res["total_limit_cpu_cores"] == 0.5
    assert res["total_requested_memory_mb"] == 256.0
    assert "catalog" in res["services"]
    assert res["services"]["catalog"]["pod_count"] == 1


def test_event_collector():
    mock_api = MagicMock()

    ev1 = MagicMock(type="Warning", reason="FailedScheduling", message="0/3 nodes available: insufficient cpu.")
    ev1.involved_object.kind = "Pod"
    ev1.involved_object.name = "retail-store-orders-xyz"
    ev1.count = 3
    ev1.last_timestamp = "2026-11-16T13:00:00Z"

    ev2 = MagicMock(type="Normal", reason="Scheduled", message="Successfully assigned to node-1")
    ev2.involved_object.kind = "Pod"
    ev2.involved_object.name = "retail-store-ui-123"
    ev2.count = 1
    ev2.last_timestamp = "2026-11-16T13:00:00Z"

    mock_api.list_namespaced_event.return_value.items = [ev1, ev2]

    collector = EventCollector(core_api=mock_api, namespace="retail-store")
    warning_events = collector.collect(warning_only=True)
    all_events = collector.collect(warning_only=False)

    assert len(warning_events) == 1
    assert warning_events[0]["reason"] == "FailedScheduling"
    assert len(all_events) == 2

    pod_events = collector.get_events_for_pod("retail-store-orders-xyz")
    assert len(pod_events) == 1
