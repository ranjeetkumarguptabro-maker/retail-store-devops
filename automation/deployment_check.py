#!/usr/bin/env python3
"""
Deployment Availability & Replica Health Check
Verifies that all Deployments in the namespace have their expected replicas available.
"""

import sys
import json
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("deployment_check")


def check_deployments(apps_v1_client, namespace: str = "retail-store") -> Dict[str, Any]:
    """Inspects Deployments in the namespace."""
    try:
        deployments = apps_v1_client.list_namespaced_deployment(namespace=namespace).items
    except Exception as e:
        logger.error(f"Failed to query deployments in '{namespace}': {e}")
        return {"status": "ERROR", "message": str(e), "total_deployments": 0, "deployments": []}

    dep_status: List[Dict[str, Any]] = []
    all_ready = True

    for dep in deployments:
        name = dep.metadata.name
        desired = dep.spec.replicas or 0
        ready = dep.status.ready_replicas or 0
        available = dep.status.available_replicas or 0
        updated = dep.status.updated_replicas or 0

        is_healthy = (ready == desired and available == desired)
        if not is_healthy:
            all_ready = False

        dep_status.append({
            "name": name,
            "desired_replicas": desired,
            "ready_replicas": ready,
            "available_replicas": available,
            "updated_replicas": updated,
            "healthy": is_healthy
        })

    status = "HEALTHY" if all_ready and len(deployments) > 0 else ("EMPTY" if len(deployments) == 0 else "DEGRADED")

    return {
        "status": status,
        "namespace": namespace,
        "total_deployments": len(deployments),
        "deployments": dep_status,
    }


def main():
    namespace = sys.argv[1] if len(sys.argv) > 1 else "retail-store"
    try:
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        apps_v1 = client.AppsV1Api()
    except Exception as e:
        logger.warning(f"Could not load Kubernetes client config ({e}).")
        result = {"status": "OFFLINE", "namespace": namespace, "total_deployments": 0, "deployments": []}
        print(json.dumps(result, indent=2))
        sys.exit(0)

    result = check_deployments(apps_v1, namespace=namespace)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "HEALTHY" else 1)


if __name__ == "__main__":
    main()
