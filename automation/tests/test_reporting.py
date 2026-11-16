"""Unit tests for IncidentReportGenerator and MetricsExporter."""

import json
import os
from prometheus_client import CollectorRegistry
from automation.reporting.json_report import IncidentReportGenerator
from automation.reporting.metrics import MetricsExporter


def test_incident_report_generation(tmp_path):
    report_file = tmp_path / "test-diagnostics.json"
    generator = IncidentReportGenerator(output_path=str(report_file))

    diagnosis = {
        "cluster_healthy": False,
        "services": {
            "ui": {"service": "ui", "status": "HEALTHY", "pod_count": 1, "healthy_pods": 1},
            "cart": {
                "service": "cart",
                "status": "CRASHLOOPBACKOFF",
                "pod_count": 1,
                "healthy_pods": 0,
                "primary_issue": "CrashLoopBackOff on container 'cart'",
                "suggested_action": "Inspect DB credentials",
            },
        },
        "pod_diagnostics": [
            {
                "pod_name": "retail-store-cart-xyz",
                "service": "cart",
                "status": "CRASHLOOPBACKOFF",
                "is_healthy": False,
                "root_cause": "CrashLoopBackOff",
                "remediation": "Inspect DB credentials",
            }
        ],
        "summary": {"total_services": 2, "healthy_services": 1, "failing_services": 1},
    }

    report_data = generator.generate(
        diagnosis=diagnosis,
        namespace="retail-store",
        cluster_name="test-cluster",
    )

    assert report_data["metadata"]["cluster"] == "test-cluster"
    assert report_data["metadata"]["namespace"] == "retail-store"
    assert report_data["metadata"]["overall_status"] == "DEGRADED"
    assert report_data["summary"]["failing_services"] == 1
    assert "cart" in report_data["services"]

    saved_path = generator.save_report(report_data, file_path=str(report_file))
    assert os.path.exists(saved_path)

    with open(saved_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["metadata"]["namespace"] == "retail-store"
    assert loaded["services"]["cart"]["status"] == "CRASHLOOPBACKOFF"


def test_metrics_exporter():
    registry = CollectorRegistry()
    exporter = MetricsExporter(registry=registry)

    exporter.record_check("diagnostics", success=True)
    exporter.record_check("diagnostics", success=False)
    exporter.record_failure("cart", "CrashLoopBackOff")
    exporter.record_rollback("retail-store-cart", status="success")

    with exporter.track_duration("diagnose"):
        pass

    text = exporter.get_metrics_text()
    assert "automation_checks_total" in text
    assert 'check_type="diagnostics",status="success"' in text
    assert 'check_type="diagnostics",status="failure"' in text
    assert 'automation_failures_total{failure_type="CrashLoopBackOff",service="cart"}' in text
    assert 'deployment_rollbacks_total{deployment="retail-store-cart",status="success"}' in text
    assert "automation_execution_seconds" in text
