"""Unit tests for RollbackManager and RecoveryValidator."""

from unittest.mock import MagicMock, patch
from automation.remediation.rollback import RollbackManager
from automation.remediation.recovery_validator import RecoveryValidator


def test_rollback_preflight_success():
    mock_apps = MagicMock()
    dep = MagicMock()
    dep.spec.replicas = 2
    dep.spec.revision_history_limit = 10
    mock_apps.read_namespaced_deployment.return_value = dep

    mgr = RollbackManager(apps_api=mock_apps, namespace="retail-store")
    check = mgr.validate_preflight("retail-store-ui")

    assert check["can_rollback"] is True
    assert check["deployment"] == "retail-store-ui"
    assert check["configured_replicas"] == 2


def test_rollback_dry_run_mode():
    mock_apps = MagicMock()
    dep = MagicMock()
    dep.spec.replicas = 1
    dep.spec.revision_history_limit = 10
    mock_apps.read_namespaced_deployment.return_value = dep

    mgr = RollbackManager(apps_api=mock_apps, namespace="retail-store", dry_run=True)
    res = mgr.execute_rollback("retail-store-cart")

    assert res["success"] is True
    assert res["dry_run"] is True
    assert res["executed"] is False
    assert "DRY-RUN" in res["message"]
    assert "kubectl rollout undo" in res["planned_action"]


def test_rollback_requires_confirmation():
    mock_apps = MagicMock()
    dep = MagicMock()
    dep.spec.replicas = 1
    dep.spec.revision_history_limit = 10
    mock_apps.read_namespaced_deployment.return_value = dep

    mgr = RollbackManager(apps_api=mock_apps, namespace="retail-store", dry_run=False)
    res = mgr.execute_rollback("retail-store-cart", confirm=False)

    assert res["success"] is False
    assert res["executed"] is False
    assert "Confirmation required" in res["error"]


def test_rollback_live_execution():
    mock_apps = MagicMock()
    dep = MagicMock()
    dep.spec.replicas = 1
    dep.spec.revision_history_limit = 10
    mock_apps.read_namespaced_deployment.return_value = dep

    mgr = RollbackManager(apps_api=mock_apps, namespace="retail-store", dry_run=False)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "deployment.apps/retail-store-cart rolled back"
        res = mgr.execute_rollback("retail-store-cart", confirm=True)

        assert res["success"] is True
        assert res["executed"] is True
        assert "rolled back" in res["output"]


def test_recovery_validator_success():
    mock_apps = MagicMock()
    dep = MagicMock()
    dep.spec.replicas = 2
    dep.status.available_replicas = 2
    dep.status.updated_replicas = 2
    mock_apps.read_namespaced_deployment.return_value = dep

    validator = RecoveryValidator(apps_api=mock_apps, namespace="retail-store")

    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        res = validator.verify_service_stabilization(
            "retail-store-ui", service_url="http://localhost:8888", timeout_seconds=5
        )

        assert res["recovered"] is True
        assert res["stabilized"] is True
        assert res["endpoint_healthy"] is True
        assert res["replicas_available"] == 2
