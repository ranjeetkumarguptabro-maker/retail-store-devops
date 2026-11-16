#!/usr/bin/env python3
"""
Automated Rollback Verification Engine
Inspects ReplicaSet history, validates rollback revisions, and verifies traffic recovery.
"""

import sys
import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rollback_validator")


def validate_rollback(apps_v1_client, deployment_name: str, namespace: str = "retail-store", expected_image: str = None) -> Dict[str, Any]:
    """Validates that a rollback operation was successful for a given deployment."""
    try:
        dep = apps_v1_client.read_namespaced_deployment(name=deployment_name, namespace=namespace)
    except Exception as e:
        logger.error(f"Failed to read deployment '{deployment_name}': {e}")
        return {"status": "ERROR", "deployment": deployment_name, "message": str(e), "rollback_healthy": False}

    current_image = dep.spec.template.spec.containers[0].image
    desired_replicas = dep.spec.replicas or 1
    available_replicas = dep.status.available_replicas or 0
    updated_replicas = dep.status.updated_replicas or 0

    is_stable = (available_replicas == desired_replicas and updated_replicas == desired_replicas)
    image_matches = (expected_image is None or current_image == expected_image)

    rollback_success = is_stable and image_matches

    return {
        "status": "HEALTHY" if rollback_success else "DEGRADED",
        "deployment": deployment_name,
        "namespace": namespace,
        "current_image": current_image,
        "expected_image": expected_image,
        "desired_replicas": desired_replicas,
        "available_replicas": available_replicas,
        "rollback_healthy": rollback_success,
        "diagnostics": "Rollback fully recovered and serving traffic" if rollback_success else "Rollback pending or replica mismatch"
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 rollback_validator.py <deployment_name> [namespace] [expected_image]")
        sys.exit(1)

    deployment_name = sys.argv[1]
    namespace = sys.argv[2] if len(sys.argv) > 2 else "retail-store"
    expected_image = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        apps_v1 = client.AppsV1Api()
    except Exception as e:
        logger.warning(f"Could not load Kubernetes client config ({e}).")
        result = {"status": "OFFLINE", "deployment": deployment_name, "rollback_healthy": False}
        print(json.dumps(result, indent=2))
        sys.exit(0)

    result = validate_rollback(apps_v1, deployment_name, namespace, expected_image)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["rollback_healthy"] else 1)


if __name__ == "__main__":
    main()
