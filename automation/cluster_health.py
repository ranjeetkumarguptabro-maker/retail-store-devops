#!/usr/bin/env python3
"""
Cluster Connectivity & Node Readiness Checker
Inspects the Kubernetes control plane connection and reports node statuses.
"""

import sys
import json
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cluster_health")


def check_nodes(v1_client) -> Dict[str, Any]:
    """Inspects all nodes in the Kubernetes cluster."""
    try:
        nodes = v1_client.list_node().items
    except Exception as e:
        logger.error(f"Failed to communicate with Kubernetes API server: {e}")
        return {"status": "ERROR", "message": str(e), "total_nodes": 0, "ready_nodes": 0, "nodes": []}

    node_details: List[Dict[str, Any]] = []
    ready_count = 0

    for node in nodes:
        name = node.metadata.name
        is_ready = False
        for condition in node.status.conditions:
            if condition.type == "Ready" and condition.status == "True":
                is_ready = True
                break

        if is_ready:
            ready_count += 1

        node_details.append({
            "name": name,
            "ready": is_ready,
            "kubelet_version": node.status.node_info.kubelet_version,
            "os_image": node.status.node_info.os_image,
            "architecture": node.status.node_info.architecture,
        })

    status = "HEALTHY" if ready_count == len(nodes) and len(nodes) > 0 else "DEGRADED"

    return {
        "status": status,
        "total_nodes": len(nodes),
        "ready_nodes": ready_count,
        "nodes": node_details,
    }


def main():
    try:
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        v1 = client.CoreV1Api()
    except Exception as e:
        logger.warning(f"Could not load Kubernetes client config ({e}). Running in standalone mock mode.")
        result = {"status": "OFFLINE", "message": "Kubeconfig not active", "total_nodes": 0, "ready_nodes": 0, "nodes": []}
        print(json.dumps(result, indent=2))
        sys.exit(0)

    result = check_nodes(v1)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "HEALTHY" else 1)


if __name__ == "__main__":
    main()
