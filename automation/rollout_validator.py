#!/usr/bin/env python3
"""
Deployment Rollout Validator & Automated Verification Engine
Validates rolling update status, monitors progress, and determines success/failure.
"""

import sys
import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rollout_validator")


def validate_deployment_rollout(apps_v1_client, deployment_name: str, namespace: str = "retail-store") -> Dict[str, Any]:
    """Validates whether a specific deployment has completed its rollout successfully."""
    try:
        dep = apps_v1_client.read_namespaced_deployment(name=deployment_name, namespace=namespace)
    except Exception as e:
        logger.error(f"Deployment '{deployment_name}' not found in '{namespace}': {e}")
        return {"deployment": deployment_name, "status": "NOT_FOUND", "message": str(e), "rollout_complete": False}

    spec_replicas = dep.spec.replicas or 1
    status = dep.status
    generation = dep.metadata.generation
    observed_generation = status.observed_generation or 0
    updated_replicas = status.updated_replicas or 0
    available_replicas = status.available_replicas or 0
    unavailable_replicas = status.unavailable_replicas or 0

    is_complete = (
        observed_generation >= generation
        and updated_replicas == spec_replicas
        and available_replicas == spec_replicas
        and unavailable_replicas == 0
    )

    return {
        "deployment": deployment_name,
        "namespace": namespace,
        "spec_replicas": spec_replicas,
        "updated_replicas": updated_replicas,
        "available_replicas": available_replicas,
        "unavailable_replicas": unavailable_replicas,
        "rollout_complete": is_complete,
        "status": "COMPLETED" if is_complete else "IN_PROGRESS"
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 rollout_validator.py <deployment_name> [namespace]")
        sys.exit(1)

    deployment_name = sys.argv[1]
    namespace = sys.argv[2] if len(sys.argv) > 2 else "retail-store"

    try:
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        apps_v1 = client.AppsV1Api()
    except Exception as e:
        logger.warning(f"Could not load Kubernetes client config ({e}).")
        result = {"deployment": deployment_name, "status": "OFFLINE", "rollout_complete": False}
        print(json.dumps(result, indent=2))
        sys.exit(0)

    result = validate_deployment_rollout(apps_v1, deployment_name, namespace)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["rollout_complete"] else 1)


if __name__ == "__main__":
    main()
