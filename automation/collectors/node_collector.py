"""Collects node statuses, conditions, and cluster capacity."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("operations_engine.collectors.node")


class NodeCollector:
    """Queries the Kubernetes API for cluster node health and capacity metrics."""

    def __init__(self, core_api: Optional[Any] = None):
        self._core_api = core_api

    def _get_api(self):
        if self._core_api:
            return self._core_api
        try:
            from kubernetes import client, config
            try:
                config.load_incluster_config()
            except Exception:
                config.load_kube_config()
            self._core_api = client.CoreV1Api()
            return self._core_api
        except Exception as e:
            logger.warning(f"Could not initialize Kubernetes client: {e}")
            return None

    def collect(self) -> List[Dict[str, Any]]:
        """Collects telemetry for all nodes in the cluster."""
        api = self._get_api()
        if not api:
            return []

        try:
            node_list = api.list_node()
        except Exception as e:
            logger.error(f"Failed to list nodes: {e}")
            return []

        nodes_data = []
        for node in getattr(node_list, "items", []):
            metadata = getattr(node, "metadata", None)
            status = getattr(node, "status", None)

            name = getattr(metadata, "name", "unknown")
            conditions = self._parse_conditions(getattr(status, "conditions", []) or [])
            capacity = getattr(status, "capacity", {}) or {}
            allocatable = getattr(status, "allocatable", {}) or {}

            is_ready = conditions.get("Ready", False)

            nodes_data.append({
                "name": name,
                "ready": is_ready,
                "conditions": conditions,
                "capacity": {
                    "cpu": capacity.get("cpu", "N/A"),
                    "memory": capacity.get("memory", "N/A"),
                    "pods": capacity.get("pods", "N/A"),
                },
                "allocatable": {
                    "cpu": allocatable.get("cpu", "N/A"),
                    "memory": allocatable.get("memory", "N/A"),
                    "pods": allocatable.get("pods", "N/A"),
                },
            })

        return nodes_data

    def _parse_conditions(self, conditions: List[Any]) -> Dict[str, bool]:
        """Translates V1NodeCondition objects into boolean status flags."""
        parsed = {}
        for cond in conditions:
            c_type = getattr(cond, "type", "")
            c_status = getattr(cond, "status", "False")
            parsed[c_type] = (c_status == "True")
        return parsed
