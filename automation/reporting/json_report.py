"""Generates structured JSON incident and cluster diagnostic reports."""

from datetime import datetime, timezone
import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("operations_engine.reporting.json")


class IncidentReportGenerator:
    """Consolidates diagnostics, resource metrics, and deployment statuses into JSON reports."""

    def __init__(self, output_path: str = "reports/cluster-diagnostics.json"):
        self.output_path = output_path

    def generate(
        self,
        diagnosis: Dict[str, Any],
        resource_data: Optional[Dict[str, Any]] = None,
        deployment_data: Optional[Dict[str, Any]] = None,
        events: Optional[list] = None,
        namespace: str = "retail-store",
        cluster_name: str = "retail-store-cluster",
    ) -> Dict[str, Any]:
        """Builds the comprehensive diagnostics report object."""
        now_iso = datetime.now(timezone.utc).isoformat()

        services = diagnosis.get("services", {})
        summary = diagnosis.get("summary", {})

        total_svc = summary.get("total_services", len(services))
        healthy_svc = summary.get("healthy_services", sum(1 for s in services.values() if s.get("status") == "HEALTHY"))
        failing_svc = summary.get("failing_services", sum(1 for s in services.values() if s.get("status") not in ("HEALTHY", "MISSING")))

        report = {
            "metadata": {
                "generated_at": now_iso,
                "cluster": cluster_name,
                "namespace": namespace,
                "engine_version": "2.0.0",
                "overall_status": "HEALTHY" if failing_svc == 0 else "DEGRADED",
            },
            "summary": {
                "total_services": total_svc,
                "healthy_services": healthy_svc,
                "failing_services": failing_svc,
                "cluster_healthy": diagnosis.get("cluster_healthy", failing_svc == 0),
            },
            "services": services,
            "pod_diagnostics": diagnosis.get("pod_diagnostics", []),
            "resources": resource_data or {},
            "deployments": deployment_data or {},
            "recent_events": events or [],
        }

        return report

    def save_report(
        self,
        report_data: Dict[str, Any],
        file_path: Optional[str] = None,
    ) -> str:
        """Serializes report to the specified file path (defaulting to self.output_path)."""
        target = file_path or self.output_path
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)

        try:
            with open(target, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)
            logger.info(f"Diagnostics report saved to {target}")
            return target
        except Exception as e:
            logger.error(f"Failed to write report to {target}: {e}")
            raise
