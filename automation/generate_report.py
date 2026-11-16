#!/usr/bin/env python3
"""
Platform Operations Automation Engine — Master Health & Diagnostic Reporter
Aggregates node readiness, pod statuses, and deployment health into a structured JSON report.
"""

import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from cluster_health import check_nodes
from pod_health import inspect_pods
from deployment_check import check_deployments

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("platform_ops_report")


def generate_platform_report(v1_client, apps_v1_client, namespace: str = "retail-store") -> Dict[str, Any]:
    """Generates an end-to-end operational diagnostic report for the platform."""
    timestamp = datetime.now(timezone.utc).isoformat()

    nodes_report = check_nodes(v1_client)
    pods_report = inspect_pods(v1_client, namespace=namespace)
    deployments_report = check_deployments(apps_v1_client, namespace=namespace)

    overall_health = "HEALTHY"
    if (nodes_report["status"] in ["ERROR", "DEGRADED"] or
        pods_report["status"] in ["ERROR", "DEGRADED"] or
        deployments_report["status"] in ["ERROR", "DEGRADED"]):
        overall_health = "DEGRADED"

    report = {
        "report_id": f"platform-ops-{int(datetime.now(timezone.utc).timestamp())}",
        "timestamp": timestamp,
        "overall_status": overall_health,
        "target_namespace": namespace,
        "nodes_summary": {
            "status": nodes_report["status"],
            "total": nodes_report["total_nodes"],
            "ready": nodes_report["ready_nodes"]
        },
        "pods_summary": {
            "status": pods_report["status"],
            "total": pods_report["total_pods"],
            "healthy": pods_report["healthy_pods"],
            "issues_count": pods_report["issues_detected"],
            "unhealthy_pods": pods_report.get("unhealthy_pods", [])
        },
        "deployments_summary": {
            "status": deployments_report["status"],
            "total": deployments_report["total_deployments"],
            "deployments": deployments_report.get("deployments", [])
        }
    }

    return report


def main():
    namespace = sys.argv[1] if len(sys.argv) > 1 else "retail-store"

    try:
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()

        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        report = generate_platform_report(v1, apps_v1, namespace)
    except Exception as e:
        logger.warning(f"Kubernetes cluster connection offline ({e}). Generating fallback diagnostic report.")
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "OFFLINE",
            "message": "Kubernetes cluster not currently connected",
            "target_namespace": namespace
        }

    print(json.dumps(report, indent=2))
    sys.exit(0 if report["overall_status"] in ["HEALTHY", "OFFLINE"] else 1)


if __name__ == "__main__":
    main()
