"""Collects detailed pod health, container states, restart spikes, and error logs."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("operations_engine.collectors.pod")


class PodCollector:
    """Queries the Kubernetes API for pod statuses, container states, and logs."""

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

    def collect(self) -> List[Dict[str, Any]]:
        """Collects telemetry for all pods in the target namespace."""
        api = self._get_api()
        if not api:
            return []

        try:
            pod_list = api.list_namespaced_pod(namespace=self.namespace)
        except Exception as e:
            logger.error(f"Failed to list pods in namespace {self.namespace}: {e}")
            return []

        pods_data = []
        for pod in getattr(pod_list, "items", []):
            pod_info = self._extract_pod_info(pod)
            pods_data.append(pod_info)

        return pods_data

    def _extract_pod_info(self, pod: Any) -> Dict[str, Any]:
        """Extracts structured metadata and container state details from a V1Pod object."""
        metadata = getattr(pod, "metadata", None)
        status = getattr(pod, "status", None)
        spec = getattr(pod, "spec", None)

        name = getattr(metadata, "name", "unknown")
        labels = getattr(metadata, "labels", {}) or {}
        service = labels.get("app.kubernetes.io/name") or labels.get("app") or name.split("-")[0]
        node_name = getattr(spec, "node_name", "unassigned")
        phase = getattr(status, "phase", "Unknown")

        container_statuses = []
        total_restarts = 0
        has_critical_issue = False
        all_ready = True
        error_reasons = []

        for cs in getattr(status, "container_statuses", []) or []:
            c_name = getattr(cs, "name", "")
            ready = getattr(cs, "ready", False)
            if not ready:
                all_ready = False
            restart_count = getattr(cs, "restart_count", 0)
            total_restarts += restart_count

            state_info = self._parse_container_state(cs)
            if state_info.get("is_issue"):
                has_critical_issue = True
                if state_info.get("reason"):
                    error_reasons.append(state_info["reason"])

            container_statuses.append({
                "name": c_name,
                "ready": ready,
                "restart_count": restart_count,
                "state": state_info["state"],
                "reason": state_info["reason"],
                "message": state_info["message"],
                "exit_code": state_info["exit_code"],
            })

        # Determine overall pod health status
        health_status = "HEALTHY"
        if error_reasons:
            health_status = error_reasons[0].upper()
        elif phase != "Running":
            health_status = phase.upper()
        elif not all_ready and container_statuses:
            health_status = "NOT_READY"

        pod_logs = ""
        if has_critical_issue or total_restarts > 0:
            pod_logs = self.get_container_logs(name)

        return {
            "name": name,
            "service": service,
            "namespace": self.namespace,
            "node": node_name,
            "phase": phase,
            "ready": all_ready and len(container_statuses) > 0,
            "total_restarts": total_restarts,
            "restart_count": total_restarts,
            "has_restart_spike": total_restarts >= 5,
            "has_critical_issue": has_critical_issue,
            "health_status": health_status,
            "error_reasons": error_reasons,
            "containers": container_statuses,
            "logs": pod_logs,
        }

    def _parse_container_state(self, cs: Any) -> Dict[str, Any]:
        """Inspects waiting, terminated, and running container states."""
        state = getattr(cs, "state", None)
        if not state:
            return {"state": "unknown", "reason": "", "message": "", "exit_code": None, "is_issue": False}

        # Check waiting state (e.g. CrashLoopBackOff, ImagePullBackOff, ContainerCreating)
        waiting = getattr(state, "waiting", None)
        if waiting:
            reason = getattr(waiting, "reason", "") or "Waiting"
            msg = getattr(waiting, "message", "") or ""
            is_issue = reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "CreateContainerConfigError")
            return {"state": "waiting", "reason": reason, "message": msg, "exit_code": None, "is_issue": is_issue}

        # Check terminated state (e.g. OOMKilled, Error)
        terminated = getattr(state, "terminated", None)
        if terminated:
            reason = getattr(terminated, "reason", "") or "Terminated"
            msg = getattr(terminated, "message", "") or ""
            exit_code = getattr(terminated, "exit_code", 0)
            is_issue = reason in ("OOMKilled", "Error") or exit_code != 0
            return {"state": "terminated", "reason": reason, "message": msg, "exit_code": exit_code, "is_issue": is_issue}

        # Running state
        running = getattr(state, "running", None)
        if running:
            return {"state": "running", "reason": "Running", "message": "", "exit_code": None, "is_issue": False}

        return {"state": "unknown", "reason": "", "message": "", "exit_code": None, "is_issue": False}

    def get_container_logs(self, pod_name: str, container_name: str = None, tail_lines: int = 50) -> str:
        """Fetches the tail logs of a container for root-cause analysis."""
        api = self._get_api()
        if not api:
            return "Logs unavailable: Kubernetes API client not connected."

        try:
            kwargs = {"namespace": self.namespace, "name": pod_name, "tail_lines": tail_lines}
            if container_name:
                kwargs["container"] = container_name
            logs = api.read_namespaced_pod_log(**kwargs)
            return logs or ""
        except Exception as e:
            return f"Error retrieving logs for {pod_name}: {e}"
