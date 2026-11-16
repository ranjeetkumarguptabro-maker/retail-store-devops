"""Collects Kubernetes cluster and namespace events with error and warning filtering."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("operations_engine.collectors.event")


class EventCollector:
    """Queries cluster events, filtering warnings, failures, and correlated pod events."""

    def __init__(self, core_api: Optional[Any] = None, namespace: str = "retail-store"):
        self.namespace = namespace
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

    def collect(self, warning_only: bool = True) -> List[Dict[str, Any]]:
        """Collects events for the target namespace."""
        api = self._get_api()
        if not api:
            return []

        try:
            event_list = api.list_namespaced_event(namespace=self.namespace)
        except Exception as e:
            logger.error(f"Failed to list events in namespace {self.namespace}: {e}")
            return []

        events = []
        for item in getattr(event_list, "items", []):
            event_type = getattr(item, "type", "Normal")
            if warning_only and event_type == "Normal":
                continue

            involved_object = getattr(item, "involved_object", None)
            obj_kind = getattr(involved_object, "kind", "Unknown") if involved_object else "Unknown"
            obj_name = getattr(involved_object, "name", "Unknown") if involved_object else "Unknown"

            reason = getattr(item, "reason", "Unknown")
            message = getattr(item, "message", "")
            count = getattr(item, "count", 1) or 1
            last_timestamp = getattr(item, "last_timestamp", None)
            time_str = str(last_timestamp) if last_timestamp else "recent"

            events.append({
                "type": event_type,
                "reason": reason,
                "message": message,
                "object_kind": obj_kind,
                "object_name": obj_name,
                "count": count,
                "timestamp": time_str,
            })

        return events

    def get_events_for_pod(self, pod_name: str) -> List[Dict[str, Any]]:
        """Filters events associated specifically with a given pod name."""
        all_events = self.collect(warning_only=False)
        return [e for e in all_events if e["object_name"] == pod_name or pod_name in e["message"]]
