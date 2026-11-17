"""Unit tests for the complete 7-stage IncidentLifecycleOrchestrator."""

import os
from unittest.mock import MagicMock, patch
from automation.remediation.incident_lifecycle import IncidentLifecycleOrchestrator


def test_incident_lifecycle_full_resolved(tmp_path):
    mock_core = MagicMock()
    mock_apps = MagicMock()

    # 1. Pod data representing failing Cart pod
    mock_pod = MagicMock()
    mock_pod.metadata.name = "retail-store-cart-999-abc"
    mock_pod.metadata.labels = {"app": "cart"}
    mock_pod.spec.node_name = "node-1"
    mock_pod.status.phase = "Running"
    mock_pod.status.start_time = "2026-11-17T12:00:00Z"

    c_status = MagicMock()
    c_status.name = "cart"
    c_status.ready = False
    c_status.restart_count = 6
    c_status.state.running = None
    c_status.state.waiting = MagicMock(reason="CrashLoopBackOff", message="Back-off 5m restarting failed container")
    c_status.state.terminated = None
    mock_pod.status.container_statuses = [c_status]

    mock_core.list_namespaced_pod.return_value.items = [mock_pod]
    mock_core.read_namespaced_pod_log.return_value = "java.lang.NullPointerException: Connection refused to redis-cart:6379"

    # Events
    mock_event = MagicMock()
    mock_event.type = "Warning"
    mock_event.reason = "BackOff"
    mock_event.message = "Back-off restarting failed container"
    mock_event.involved_object.name = "retail-store-cart-999-abc"
    mock_event.involved_object.kind = "Pod"
    mock_event.count = 5
    mock_event.last_timestamp = "2026-11-17T12:05:00Z"
    mock_core.list_namespaced_event.return_value.items = [mock_event]

    # Deployment for rollback & recovery
    mock_dep = MagicMock()
    mock_dep.spec.replicas = 1
    mock_dep.spec.revision_history_limit = 10
    mock_dep.status.available_replicas = 1
    mock_dep.status.updated_replicas = 1
    mock_apps.read_namespaced_deployment.return_value = mock_dep

    orchestrator = IncidentLifecycleOrchestrator(
        core_api=mock_core,
        apps_api=mock_apps,
        namespace="retail-store",
        output_dir=str(tmp_path),
    )

    with patch("subprocess.run") as mock_subproc, patch("requests.get") as mock_http:
        mock_subproc.return_value.stdout = "deployment.apps/retail-store-cart rolled back"
        mock_http.return_value.status_code = 200

        report = orchestrator.run_lifecycle(
            target_service="cart",
            auto_approve=True,
            dry_run=False,
            service_url="http://localhost:8082/carts/status",
        )

        assert report["status"] == "RESOLVED"
        assert report["target_service"] == "cart"
        assert report["diagnosis"]["failure_type"] == "CRASHLOOPBACKOFF"
        assert "CrashLoopBackOff" in report["diagnosis"]["root_cause"]
        assert report["rollback_execution"]["executed"] is True
        assert report["verification"]["recovered"] is True
        assert report["verification"]["endpoint_healthy"] is True
        assert len(report["timeline"]) >= 7

        # Check artifact files created
        assert os.path.exists(report["report_files"]["json"])
        assert os.path.exists(report["report_files"]["markdown"])


def test_incident_lifecycle_approval_gate(tmp_path):
    mock_core = MagicMock()
    mock_apps = MagicMock()

    mock_pod = MagicMock()
    mock_pod.metadata.name = "retail-store-cart-999-abc"
    mock_pod.metadata.labels = {"app": "cart"}
    mock_pod.spec.node_name = "node-1"
    mock_pod.status.phase = "Running"

    c_status = MagicMock()
    c_status.name = "cart"
    c_status.ready = False
    c_status.restart_count = 6
    c_status.state.running = None
    c_status.state.waiting = MagicMock(reason="CrashLoopBackOff", message="Back-off")
    c_status.state.terminated = None
    mock_pod.status.container_statuses = [c_status]

    mock_core.list_namespaced_pod.return_value.items = [mock_pod]
    mock_core.list_namespaced_event.return_value.items = []

    mock_dep = MagicMock()
    mock_dep.spec.replicas = 1
    mock_dep.spec.revision_history_limit = 10
    mock_apps.read_namespaced_deployment.return_value = mock_dep

    orchestrator = IncidentLifecycleOrchestrator(
        core_api=mock_core,
        apps_api=mock_apps,
        namespace="retail-store",
        output_dir=str(tmp_path),
    )

    report = orchestrator.run_lifecycle(
        target_service="cart",
        auto_approve=False,
        dry_run=False,
    )

    assert report["status"] == "AWAITING_APPROVAL"
    assert report["rollback_execution"]["executed"] is False
    assert report["rollback_execution"]["awaiting_approval"] is True


def test_incident_lifecycle_dry_run(tmp_path):
    mock_core = MagicMock()
    mock_apps = MagicMock()

    mock_pod = MagicMock()
    mock_pod.metadata.name = "retail-store-cart-999-abc"
    mock_pod.metadata.labels = {"app": "cart"}
    mock_pod.status.phase = "Running"

    c_status = MagicMock()
    c_status.name = "cart"
    c_status.ready = False
    c_status.restart_count = 4
    c_status.state.running = None
    c_status.state.waiting = MagicMock(reason="CrashLoopBackOff", message="Back-off")
    c_status.state.terminated = None
    mock_pod.status.container_statuses = [c_status]

    mock_core.list_namespaced_pod.return_value.items = [mock_pod]
    mock_core.list_namespaced_event.return_value.items = []

    mock_dep = MagicMock()
    mock_dep.spec.replicas = 1
    mock_dep.spec.revision_history_limit = 10
    mock_apps.read_namespaced_deployment.return_value = mock_dep

    orchestrator = IncidentLifecycleOrchestrator(
        core_api=mock_core,
        apps_api=mock_apps,
        namespace="retail-store",
        output_dir=str(tmp_path),
    )

    report = orchestrator.run_lifecycle(
        target_service="cart",
        auto_approve=False,
        dry_run=True,
    )

    assert report["status"] == "DRY_RUN_COMPLETED"
    assert report["rollback_execution"]["dry_run"] is True


def test_incident_lifecycle_clean_cluster(tmp_path):
    mock_core = MagicMock()
    mock_apps = MagicMock()

    mock_pod = MagicMock()
    mock_pod.metadata.name = "retail-store-ui-123"
    mock_pod.metadata.labels = {"app": "ui"}
    mock_pod.status.phase = "Running"

    c_status = MagicMock()
    c_status.name = "ui"
    c_status.ready = True
    c_status.restart_count = 0
    c_status.state.running = MagicMock()
    c_status.state.waiting = None
    c_status.state.terminated = None
    mock_pod.status.container_statuses = [c_status]

    mock_core.list_namespaced_pod.return_value.items = [mock_pod]

    orchestrator = IncidentLifecycleOrchestrator(
        core_api=mock_core,
        apps_api=mock_apps,
        namespace="retail-store",
        output_dir=str(tmp_path),
    )

    report = orchestrator.run_lifecycle(target_service="ui")
    assert report["status"] == "NO_INCIDENT"
