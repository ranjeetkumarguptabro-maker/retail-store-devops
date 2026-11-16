"""Automated deployment verification, rollout progression, and endpoint health probing."""

import logging
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger("operations_engine.analyzers.deployment")


class DeploymentAnalyzer:
    """Verifies Kubernetes Deployment rollouts, replica availability, and HTTP endpoints."""

    def __init__(self, apps_api: Optional[Any] = None, namespace: str = "retail-store"):
        self.namespace = namespace
        self._apps_api = apps_api

    def _get_api(self):
        if self._apps_api:
            return self._apps_api
        try:
            from kubernetes import client, config
            try:
                config.load_incluster_config()
            except Exception:
                config.load_kube_config()
            self._apps_api = client.AppsV1Api()
            return self._apps_api
        except Exception as e:
            logger.warning(f"Could not initialize Kubernetes AppsV1 client: {e}")
            return None

    def analyze_deployments(self) -> Dict[str, Any]:
        """Queries deployments in namespace and checks rollout completion."""
        api = self._get_api()
        if not api:
            return {
                "namespace": self.namespace,
                "all_deployments_ready": False,
                "deployments": {},
                "error": "Kubernetes client unavailable",
            }

        try:
            deploy_list = api.list_namespaced_deployment(namespace=self.namespace)
        except Exception as e:
            logger.error(f"Failed to list deployments: {e}")
            return {"namespace": self.namespace, "all_deployments_ready": False, "deployments": {}, "error": str(e)}

        deployments_data: Dict[str, Dict[str, Any]] = {}
        all_ready = True

        for dep in getattr(deploy_list, "items", []):
            metadata = getattr(dep, "metadata", None)
            spec = getattr(dep, "spec", None)
            status = getattr(dep, "status", None)

            name = getattr(metadata, "name", "unknown")
            replicas = getattr(spec, "replicas", 1) or 1
            available = getattr(status, "available_replicas", 0) or 0
            updated = getattr(status, "updated_replicas", 0) or 0
            ready = getattr(status, "ready_replicas", 0) or 0

            # Conditions
            conditions = {}
            for c in getattr(status, "conditions", []) or []:
                c_type = getattr(c, "type", "")
                c_status = getattr(c, "status", "")
                conditions[c_type] = c_status

            is_progressing = conditions.get("Progressing") == "True"
            is_available = available >= replicas

            if not is_available:
                all_ready = False

            deployments_data[name] = {
                "name": name,
                "replicas": replicas,
                "available_replicas": available,
                "updated_replicas": updated,
                "ready_replicas": ready,
                "is_ready": is_available,
                "is_progressing": is_progressing,
                "rollout_complete": is_available and updated == replicas,
            }

        return {
            "namespace": self.namespace,
            "all_deployments_ready": all_ready and len(deployments_data) > 0,
            "deployment_count": len(deployments_data),
            "ready_count": sum(1 for d in deployments_data.values() if d["is_ready"]),
            "deployments": deployments_data,
        }

    def verify_endpoint_health(
        self,
        endpoint_urls: Dict[str, str],
        timeout_seconds: float = 3.0,
    ) -> Dict[str, Any]:
        """Executes synthetic HTTP health probes against service endpoints."""
        results: Dict[str, Dict[str, Any]] = {}
        all_healthy = True

        for service_name, url in endpoint_urls.items():
            try:
                resp = requests.get(url, timeout=timeout_seconds)
                is_ok = 200 <= resp.status_code < 400
                if not is_ok:
                    all_healthy = False

                results[service_name] = {
                    "url": url,
                    "status_code": resp.status_code,
                    "healthy": is_ok,
                    "response_time_ms": round(resp.elapsed.total_seconds() * 1000, 2),
                    "error": None,
                }
            except Exception as e:
                all_healthy = False
                results[service_name] = {
                    "url": url,
                    "status_code": 0,
                    "healthy": False,
                    "response_time_ms": 0.0,
                    "error": str(e),
                }

        return {
            "all_endpoints_healthy": all_healthy,
            "probed_endpoints": len(results),
            "healthy_endpoints": sum(1 for r in results.values() if r["healthy"]),
            "results": results,
        }
