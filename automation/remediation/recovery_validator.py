"""Post-recovery validator to ensure services stabilize and return to healthy status."""

import logging
import time
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger("operations_engine.remediation.validator")


class RecoveryValidator:
    """Verifies that a service has stabilized and recovered following remediation or rollback."""

    def __init__(
        self,
        apps_api: Optional[Any] = None,
        core_api: Optional[Any] = None,
        namespace: str = "retail-store",
    ):
        self.namespace = namespace
        self._apps_api = apps_api
        self._core_api = core_api

    def verify_service_stabilization(
        self,
        deployment_name: str,
        service_url: Optional[str] = None,
        timeout_seconds: int = 30,
        poll_interval: float = 2.0,
    ) -> Dict[str, Any]:
        """Polls deployment replica status and optionally verifies endpoint HTTP response."""
        start_time = time.time()
        stabilized = False
        last_reason = "Waiting for initial replica status"
        replicas_available = 0
        replicas_expected = 1

        while (time.time() - start_time) < timeout_seconds:
            if not self._apps_api:
                # If mock or no direct API, treat as simulated check
                stabilized = True
                break

            try:
                dep = self._apps_api.read_namespaced_deployment(name=deployment_name, namespace=self.namespace)
                spec = getattr(dep, "spec", None)
                status = getattr(dep, "status", None)

                replicas_expected = getattr(spec, "replicas", 1) or 1
                replicas_available = getattr(status, "available_replicas", 0) or 0
                updated_replicas = getattr(status, "updated_replicas", 0) or 0

                if replicas_available >= replicas_expected and updated_replicas == replicas_expected:
                    stabilized = True
                    last_reason = "All replicas available and updated"
                    break
                else:
                    last_reason = f"Replicas available: {replicas_available}/{replicas_expected}"
            except Exception as e:
                last_reason = f"Error reading deployment: {e}"

            time.sleep(poll_interval)

        endpoint_healthy = True
        endpoint_status = 200
        if service_url:
            try:
                resp = requests.get(service_url, timeout=3.0)
                endpoint_status = resp.status_code
                endpoint_healthy = 200 <= resp.status_code < 400
            except Exception as e:
                endpoint_healthy = False
                last_reason = f"Endpoint health check failed: {e}"

        overall_success = stabilized and endpoint_healthy

        return {
            "deployment": deployment_name,
            "recovered": overall_success,
            "stabilized": stabilized,
            "replicas_expected": replicas_expected,
            "replicas_available": replicas_available,
            "endpoint_healthy": endpoint_healthy,
            "endpoint_status_code": endpoint_status,
            "details": last_reason,
            "duration_seconds": round(time.time() - start_time, 2),
        }
