#!/usr/bin/env python3
"""
Pod Lifecycle & Failure Detection Script
Identifies unhealthy pods, excessive restarts, CrashLoopBackOff, and ImagePullBackOff.
"""

import sys
import json
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pod_health")


def inspect_pods(v1_client, namespace: str = "retail-store") -> Dict[str, Any]:
    """Inspects all Pods in the specified namespace for errors and restart counts."""
    try:
        pods = v1_client.list_namespaced_pod(namespace=namespace).items
    except Exception as e:
        logger.error(f"Failed to query pods in namespace '{namespace}': {e}")
        return {"status": "ERROR", "message": str(e), "total_pods": 0, "healthy_pods": 0, "issues": []}

    issues: List[Dict[str, Any]] = []
    healthy_count = 0

    for pod in pods:
        name = pod.metadata.name
        phase = pod.status.phase
        pod_issues: List[str] = []
        total_restarts = 0

        if pod.status.container_statuses:
            for c_status in pod.status.container_statuses:
                total_restarts += c_status.restart_count

                # Detect waiting state errors (CrashLoopBackOff, ImagePullBackOff, ErrImagePull)
                if c_status.state and c_status.state.waiting:
                    reason = c_status.state.waiting.reason
                    if reason in ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "CreateContainerConfigError"]:
                        pod_issues.append(f"Container '{c_status.name}' in {reason}")

                # Detect terminated with error
                if c_status.state and c_status.state.terminated:
                    if c_status.state.terminated.exit_code != 0:
                        pod_issues.append(f"Container '{c_status.name}' exited with code {c_status.state.terminated.exit_code}")

                # Check excessive restarts threshold (> 5)
                if c_status.restart_count > 5:
                    pod_issues.append(f"High restart count: {c_status.restart_count} restarts")

        if phase not in ["Running", "Succeeded"] or pod_issues:
            issues.append({
                "pod_name": name,
                "phase": phase,
                "restarts": total_restarts,
                "diagnostics": pod_issues if pod_issues else [f"Pod in phase {phase}"]
            })
        else:
            healthy_count += 1

    status = "HEALTHY" if not issues and len(pods) > 0 else ("EMPTY" if len(pods) == 0 else "DEGRADED")

    return {
        "status": status,
        "namespace": namespace,
        "total_pods": len(pods),
        "healthy_pods": healthy_count,
        "issues_detected": len(issues),
        "unhealthy_pods": issues,
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
        result = {"status": "OFFLINE", "namespace": namespace, "total_pods": 0, "healthy_pods": 0, "issues_detected": 0, "unhealthy_pods": []}
        print(json.dumps(result, indent=2))
        sys.exit(0)

    result = inspect_pods(v1, namespace=namespace)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "HEALTHY" else 1)


if __name__ == "__main__":
    main()
