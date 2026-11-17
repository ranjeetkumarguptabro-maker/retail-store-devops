"""Unit tests for Platform Operations unified ops_cli."""

from unittest.mock import MagicMock, patch
import pytest
from automation.ops_cli import (
    build_parser,
    cmd_diagnose,
    cmd_monitor_resources,
    cmd_verify_deployment,
    cmd_rollback,
    cmd_incident_lifecycle,
)


def test_cli_parser_subcommands():
    parser = build_parser()

    # Test diagnose args
    args = parser.parse_args(["diagnose", "--namespace", "test-ns", "--format", "json"])
    assert args.command == "diagnose"
    assert args.namespace == "test-ns"
    assert args.format == "json"

    # Test rollback args
    args = parser.parse_args(["rollback", "-d", "retail-store-cart", "--dry-run"])
    assert args.command == "rollback"
    assert args.deployment == "retail-store-cart"
    assert args.dry_run is True

    # Test monitor-resources args
    args = parser.parse_args(["monitor-resources", "-n", "retail-store"])
    assert args.command == "monitor-resources"
    assert args.namespace == "retail-store"


def test_cmd_diagnose_execution(tmp_path):
    report_file = tmp_path / "diag.json"
    parser = build_parser()
    args = parser.parse_args(["diagnose", "-n", "retail-store", "-o", str(report_file)])

    with patch("automation.ops_cli.get_k8s_clients") as mock_clients, \
         patch("automation.ops_cli.PodCollector.collect") as mock_pod_col, \
         patch("automation.ops_cli.EventCollector.collect") as mock_event_col:

        mock_clients.return_value = (MagicMock(), MagicMock())
        mock_pod_col.return_value = [
            {
                "name": "retail-store-ui-123",
                "service": "ui",
                "phase": "Running",
                "total_restarts": 0,
                "containers": [{"name": "ui", "state": "running", "reason": "Running", "ready": True}],
            }
        ]
        mock_event_col.return_value = []

        with pytest.raises(SystemExit) as exc_info:
            cmd_diagnose(args)
        assert exc_info.value.code == 0
        assert report_file.exists()


def test_cmd_monitor_resources_execution(tmp_path):
    report_file = tmp_path / "res.json"
    parser = build_parser()
    args = parser.parse_args(["monitor-resources", "-n", "retail-store", "-o", str(report_file)])

    with patch("automation.ops_cli.get_k8s_clients") as mock_clients, \
         patch("automation.ops_cli.ResourceCollector.collect") as mock_res_col, \
         patch("automation.ops_cli.NodeCollector.collect") as mock_node_col:

        mock_clients.return_value = (MagicMock(), MagicMock())
        mock_res_col.return_value = {
            "total_requested_cpu_cores": 0.5,
            "total_requested_memory_mb": 512,
            "services": {},
        }
        mock_node_col.return_value = []

        with pytest.raises(SystemExit) as exc_info:
            cmd_monitor_resources(args)
        assert exc_info.value.code == 0


def test_cmd_verify_deployment_execution():
    parser = build_parser()
    args = parser.parse_args(["verify-deployment", "-n", "retail-store"])

    with patch("automation.ops_cli.get_k8s_clients") as mock_clients, \
         patch("automation.ops_cli.DeploymentAnalyzer.analyze_deployments") as mock_analyze:

        mock_clients.return_value = (MagicMock(), MagicMock())
        mock_analyze.return_value = {
            "all_deployments_ready": True,
            "ready_count": 5,
            "deployment_count": 5,
            "deployments": {},
        }

        with pytest.raises(SystemExit) as exc_info:
            cmd_verify_deployment(args)
        assert exc_info.value.code == 0


def test_cmd_rollback_dry_run():
    parser = build_parser()
    args = parser.parse_args(["rollback", "-d", "retail-store-ui", "--dry-run"])

    with patch("automation.ops_cli.get_k8s_clients") as mock_clients, \
         patch("automation.ops_cli.RollbackManager.execute_rollback") as mock_rb:

        mock_clients.return_value = (MagicMock(), MagicMock())
        mock_rb.return_value = {
            "success": True,
            "dry_run": True,
            "message": "DRY-RUN simulated",
        }

        with pytest.raises(SystemExit) as exc_info:
            cmd_rollback(args)
        assert exc_info.value.code == 0


def test_cmd_incident_lifecycle_execution(tmp_path):
    parser = build_parser()
    args = parser.parse_args(["incident-lifecycle", "-s", "cart", "--dry-run", "--output-dir", str(tmp_path)])

    with patch("automation.ops_cli.get_k8s_clients") as mock_clients, \
         patch("automation.ops_cli.IncidentLifecycleOrchestrator.run_lifecycle") as mock_run:

        mock_clients.return_value = (MagicMock(), MagicMock())
        mock_run.return_value = {
            "incident_id": "INC-TEST-cart",
            "status": "DRY_RUN_COMPLETED",
            "target_service": "cart",
            "namespace": "retail-store",
            "duration_seconds": 1.23,
            "timeline": [{"stage": "DETECT", "message": "CrashLoopBackOff detected", "status": "FAILURE"}],
            "diagnosis": {"failure_type": "CrashLoopBackOff", "root_cause": "NPE", "action": "Rollback"},
            "remediation_plan": {"action": "Rollback deployment"},
            "report_files": {"json": str(tmp_path / "inc.json"), "markdown": str(tmp_path / "inc.md")},
        }

        with pytest.raises(SystemExit) as exc_info:
            cmd_incident_lifecycle(args)
        assert exc_info.value.code == 0
