#!/usr/bin/env python3
"""
Resource Utilization & Configuration Auditor
Inspects Kubernetes Pod resource requests and limits to prevent noisy neighbors and OOMKills.
"""

import sys
import json
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("resource_monitor")


def audit_pod_resources(v1_client, namespace: str = "retail-store") -> Dict[str, Any]:
    """Audits CPU and Memory requests and limits for all Pods in the namespace."""
    try:
        pods = v1_client.list_namespaced_pod(namespace=namespace).items
    except Exception as e:
        logger.error(f"Failed to query pods in namespace '{namespace}': {e}")
        return {"status": "ERROR", "message": str(e), "pods_audited": 0, "findings": []}

    findings: List[Dict[str, Any]] = []
    compliant_containers = 0
    total_containers = 0

    for pod in pods:
        pod_name = pod.metadata.name
        for container in pod.spec.containers:
            total_containers += 1
            c_name = container.name
            resources = container.resources

            has_cpu_req = bool(resources and resources.requests and "cpu" in resources.requests)
            has_mem_req = bool(resources and resources.requests and "memory" in resources.requests)
            has_cpu_limit = bool(resources and resources.limits and "cpu" in resources.limits)
            has_mem_limit = bool(resources and resources.limits and "memory" in resources.limits)

            missing: List[str] = []
            if not has_cpu_req:
                missing.append("Missing CPU Request")
            if not has_mem_req:
                missing.append("Missing Memory Request")
            if not has_cpu_limit:
                missing.append("Missing CPU Limit")
            if not has_mem_limit:
                missing.append("Missing Memory Limit (OOMKill risk)")

            if missing:
                findings.append({
                    "pod": pod_name,
                    "container": c_name,
                    "compliance": "NON_COMPLIANT",
                    "issues": missing
                })
            else:
                compliant_containers += 1

    status = "COMPLIANT" if not findings and total_containers > 0 else ("EMPTY" if total_containers == 0 else "WARNING")

    return {
        "status": status,
        "namespace": namespace,
        "total_containers": total_containers,
        "compliant_containers": compliant_containers,
        "non_compliant_findings": len(findings),
        "findings": findings
    }


def main():
    namespace = sys.argv[1] if len(sys.argv) > 1 else "retail-store"
    try:
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        v1 = client.CoreV1Api()
    except Exception as e:
        logger.warning(f"Could not load Kubernetes client config ({e}). Running in standalone mock mode.")
        result = {"status": "OFFLINE", "namespace": namespace, "total_containers": 0, "findings": []}
        print(json.dumps(result, indent=2))
        sys.exit(0)

    result = audit_pod_resources(v1, namespace=namespace)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "COMPLIANT" else 1)


if __name__ == "__main__":
    main()
