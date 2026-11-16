"""
Unit Tests for Platform Operations Automation Engine
Uses unittest.mock to test failure detection, node readiness, resource auditing, and rollback validation.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

# Add parent directory to path so automation modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cluster_health import check_nodes
from pod_health import inspect_pods
from deployment_check import check_deployments
from rollout_validator import validate_deployment_rollout
from resource_monitor import audit_pod_resources
from rollback_validator import validate_rollback
from generate_report import generate_platform_report


class TestPlatformOperations(unittest.TestCase):

    def test_cluster_health_all_ready(self):
        mock_v1 = MagicMock()
        mock_node = MagicMock()
        mock_node.metadata.name = "node-1"
        mock_cond = MagicMock()
        mock_cond.type = "Ready"
        mock_cond.status = "True"
        mock_node.status.conditions = [mock_cond]
        mock_node.status.node_info.kubelet_version = "v1.31.0"
        mock_node.status.node_info.os_image = "Amazon Linux 2023"
        mock_node.status.node_info.architecture = "arm64"
        mock_v1.list_node.return_value.items = [mock_node]

        result = check_nodes(mock_v1)
        self.assertEqual(result["status"], "HEALTHY")
        self.assertEqual(result["total_nodes"], 1)
        self.assertEqual(result["ready_nodes"], 1)

    def test_pod_health_detects_crashloop(self):
        mock_v1 = MagicMock()
        mock_pod = MagicMock()
        mock_pod.metadata.name = "catalog-pod-crash"
        mock_pod.status.phase = "Running"
        mock_c_status = MagicMock()
        mock_c_status.name = "catalog"
        mock_c_status.restart_count = 8
        mock_c_status.state.waiting.reason = "CrashLoopBackOff"
        mock_c_status.state.terminated = None
        mock_pod.status.container_statuses = [mock_c_status]
        mock_v1.list_namespaced_pod.return_value.items = [mock_pod]

        result = inspect_pods(mock_v1, "retail-store")
        self.assertEqual(result["status"], "DEGRADED")
        self.assertEqual(result["issues_detected"], 1)
        self.assertIn("CrashLoopBackOff", result["unhealthy_pods"][0]["diagnostics"][0])

    def test_deployment_check_all_healthy(self):
        mock_apps = MagicMock()
        mock_dep = MagicMock()
        mock_dep.metadata.name = "ui"
        mock_dep.spec.replicas = 2
        mock_dep.status.ready_replicas = 2
        mock_dep.status.available_replicas = 2
        mock_dep.status.updated_replicas = 2
        mock_apps.list_namespaced_deployment.return_value.items = [mock_dep]

        result = check_deployments(mock_apps, "retail-store")
        self.assertEqual(result["status"], "HEALTHY")
        self.assertEqual(result["total_deployments"], 1)
        self.assertTrue(result["deployments"][0]["healthy"])

    def test_rollout_validator_completed(self):
        mock_apps = MagicMock()
        mock_dep = MagicMock()
        mock_dep.metadata.generation = 2
        mock_dep.spec.replicas = 2
        mock_dep.status.observed_generation = 2
        mock_dep.status.updated_replicas = 2
        mock_dep.status.available_replicas = 2
        mock_dep.status.unavailable_replicas = 0
        mock_apps.read_namespaced_deployment.return_value = mock_dep

        result = validate_deployment_rollout(mock_apps, "ui", "retail-store")
        self.assertTrue(result["rollout_complete"])
        self.assertEqual(result["status"], "COMPLETED")

    def test_resource_monitor_audit(self):
        mock_v1 = MagicMock()
        mock_pod = MagicMock()
        mock_pod.metadata.name = "cart-pod"
        mock_container = MagicMock()
        mock_container.name = "cart"
        mock_container.resources.requests = {"cpu": "150m", "memory": "256Mi"}
        mock_container.resources.limits = {"cpu": "500m", "memory": "512Mi"}
        mock_pod.spec.containers = [mock_container]
        mock_v1.list_namespaced_pod.return_value.items = [mock_pod]

        result = audit_pod_resources(mock_v1, "retail-store")
        self.assertEqual(result["status"], "COMPLIANT")
        self.assertEqual(result["total_containers"], 1)
        self.assertEqual(result["compliant_containers"], 1)

    def test_rollback_validator_success(self):
        mock_apps = MagicMock()
        mock_dep = MagicMock()
        mock_dep.spec.replicas = 2
        mock_dep.status.available_replicas = 2
        mock_dep.status.updated_replicas = 2
        mock_dep.spec.template.spec.containers = [MagicMock(image="public.ecr.aws/aws-containers/retail-store-sample-ui:1.0.0")]
        mock_apps.read_namespaced_deployment.return_value = mock_dep

        result = validate_rollback(mock_apps, "ui", "retail-store", "public.ecr.aws/aws-containers/retail-store-sample-ui:1.0.0")
        self.assertEqual(result["status"], "HEALTHY")
        self.assertTrue(result["rollback_healthy"])

    def test_generate_platform_report(self):
        mock_v1 = MagicMock()
        mock_apps = MagicMock()

        mock_v1.list_node.return_value.items = []
        mock_v1.list_namespaced_pod.return_value.items = []
        mock_apps.list_namespaced_deployment.return_value.items = []

        report = generate_platform_report(mock_v1, mock_apps, "retail-store")
        self.assertIn("report_id", report)
        self.assertEqual(report["target_namespace"], "retail-store")


if __name__ == "__main__":
    unittest.main()
