"""Collects CPU and memory resource requests, limits, and consumption."""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("operations_engine.collectors.resource")


def parse_cpu(cpu_str: Optional[str]) -> float:
    """Parses Kubernetes CPU resource strings into fractional cores.
    Examples: '250m' -> 0.25, '1' -> 1.0, '500m' -> 0.5.
    """
    if not cpu_str:
        return 0.0
    cpu_str = str(cpu_str).strip()
    if cpu_str.endswith("m"):
        try:
            return float(cpu_str[:-1]) / 1000.0
        except ValueError:
            return 0.0
    if cpu_str.endswith("u"):
        try:
            return float(cpu_str[:-1]) / 1000000.0
        except ValueError:
            return 0.0
    if cpu_str.endswith("n"):
        try:
            return float(cpu_str[:-1]) / 1000000000.0
        except ValueError:
            return 0.0
    try:
        return float(cpu_str)
    except ValueError:
        return 0.0


def parse_memory_bytes(mem_str: Optional[str]) -> int:
    """Parses Kubernetes memory resource strings into bytes.
    Examples: '128Mi' -> 134217728, '1Gi' -> 1073741824, '500M' -> 500000000.
    """
    if not mem_str:
        return 0
    mem_str = str(mem_str).strip()
    units = {
        "Ki": 1024,
        "Mi": 1024**2,
        "Gi": 1024**3,
        "Ti": 1024**4,
        "Pi": 1024**5,
        "Ei": 1024**6,
        "k": 1000,
        "M": 1000**2,
        "G": 1000**3,
        "T": 1000**4,
        "P": 1000**5,
        "E": 1000**6,
    }
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?)([A-Za-z]+)?$", mem_str)
    if not match:
        return 0
    value, unit = match.groups()
    try:
        val = float(value)
    except ValueError:
        return 0

    if not unit:
        return int(val)
    multiplier = units.get(unit, 1)
    return int(val * multiplier)


class ResourceCollector:
    """Queries pod resource allocations (requests/limits) and metrics."""

    def __init__(self, core_api: Optional[Any] = None, custom_api: Optional[Any] = None, namespace: str = "retail-store"):
        self.namespace = namespace
        self._core_api = core_api
        self._custom_api = custom_api

    def _get_core_api(self):
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

    def collect(self) -> Dict[str, Any]:
        """Collects resource allocation and usage statistics across pods."""
        api = self._get_core_api()
        if not api:
            return {
                "namespace": self.namespace,
                "total_requested_cpu_cores": 0.0,
                "total_limit_cpu_cores": 0.0,
                "total_requested_memory_bytes": 0,
                "total_limit_memory_bytes": 0,
                "services": {},
            }

        try:
            pod_list = api.list_namespaced_pod(namespace=self.namespace)
        except Exception as e:
            logger.error(f"Failed to list pods for resources: {e}")
            return {"namespace": self.namespace, "error": str(e), "services": {}}

        total_cpu_req = 0.0
        total_cpu_lim = 0.0
        total_mem_req = 0
        total_mem_lim = 0
        services_data: Dict[str, Dict[str, Any]] = {}

        for pod in getattr(pod_list, "items", []):
            metadata = getattr(pod, "metadata", None)
            spec = getattr(pod, "spec", None)
            if not metadata or not spec:
                continue

            pod_name = getattr(metadata, "name", "unknown")
            labels = getattr(metadata, "labels", {}) or {}
            service = labels.get("app.kubernetes.io/name") or labels.get("app") or pod_name.split("-")[0]

            if service not in services_data:
                services_data[service] = {
                    "pod_count": 0,
                    "requested_cpu_cores": 0.0,
                    "limit_cpu_cores": 0.0,
                    "requested_memory_bytes": 0,
                    "limit_memory_bytes": 0,
                    "requested_memory_mb": 0.0,
                    "limit_memory_mb": 0.0,
                    "containers": [],
                }

            services_data[service]["pod_count"] += 1

            for container in getattr(spec, "containers", []) or []:
                c_name = getattr(container, "name", "unknown")
                resources = getattr(container, "resources", None)
                reqs = getattr(resources, "requests", {}) or {} if resources else {}
                limits = getattr(resources, "limits", {}) or {} if resources else {}

                c_cpu_req = parse_cpu(reqs.get("cpu"))
                c_cpu_lim = parse_cpu(limits.get("cpu"))
                c_mem_req = parse_memory_bytes(reqs.get("memory"))
                c_mem_lim = parse_memory_bytes(limits.get("memory"))

                services_data[service]["requested_cpu_cores"] += c_cpu_req
                services_data[service]["limit_cpu_cores"] += c_cpu_lim
                services_data[service]["requested_memory_bytes"] += c_mem_req
                services_data[service]["limit_memory_bytes"] += c_mem_lim

                total_cpu_req += c_cpu_req
                total_cpu_lim += c_cpu_lim
                total_mem_req += c_mem_req
                total_mem_lim += c_mem_lim

                services_data[service]["containers"].append({
                    "pod": pod_name,
                    "container": c_name,
                    "cpu_request": c_cpu_req,
                    "cpu_limit": c_cpu_lim,
                    "memory_request_bytes": c_mem_req,
                    "memory_limit_bytes": c_mem_lim,
                })

        for s_info in services_data.values():
            s_info["requested_cpu_cores"] = round(s_info["requested_cpu_cores"], 3)
            s_info["limit_cpu_cores"] = round(s_info["limit_cpu_cores"], 3)
            s_info["requested_memory_mb"] = round(s_info["requested_memory_bytes"] / (1024 * 1024), 2)
            s_info["limit_memory_mb"] = round(s_info["limit_memory_bytes"] / (1024 * 1024), 2)

        return {
            "namespace": self.namespace,
            "total_requested_cpu_cores": round(total_cpu_req, 3),
            "total_limit_cpu_cores": round(total_cpu_lim, 3),
            "total_requested_memory_bytes": total_mem_req,
            "total_requested_memory_mb": round(total_mem_req / (1024 * 1024), 2),
            "total_limit_memory_bytes": total_mem_lim,
            "total_limit_memory_mb": round(total_mem_lim / (1024 * 1024), 2),
            "services": services_data,
        }
