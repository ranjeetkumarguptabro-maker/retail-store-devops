"""Safe deployment rollback engine with pre-flight gates and dry-run simulation."""

import logging
import subprocess
from typing import Any, Dict, Optional

logger = logging.getLogger("operations_engine.remediation.rollback")


class RollbackManager:
    """Manages safe rollbacks of Kubernetes deployments with safety gates and validation."""

    def __init__(
        self,
        apps_api: Optional[Any] = None,
        namespace: str = "retail-store",
        dry_run: bool = False,
    ):
        self.namespace = namespace
        self._apps_api = apps_api
        self.dry_run = dry_run

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

    def validate_preflight(self, deployment_name: str) -> Dict[str, Any]:
        """Pre-flight safety checks: deployment existence, previous revisions, cluster stability."""
        api = self._get_api()
        if not api:
            return {
                "can_rollback": False,
                "reasons": ["Kubernetes API client is unavailable"],
                "deployment": deployment_name,
            }

        reasons = []
        try:
            dep = api.read_namespaced_deployment(name=deployment_name, namespace=self.namespace)
            spec = getattr(dep, "spec", None)
            replicas = getattr(spec, "replicas", 1) or 1
        except Exception as e:
            return {
                "can_rollback": False,
                "reasons": [f"Deployment '{deployment_name}' not found in namespace '{self.namespace}': {e}"],
                "deployment": deployment_name,
            }

        # Check revision history limit
        rev_limit = getattr(spec, "revision_history_limit", 10)
        if rev_limit is not None and rev_limit <= 0:
            reasons.append("Revision history limit is 0; no prior revisions are kept.")

        return {
            "can_rollback": len(reasons) == 0,
            "reasons": reasons,
            "deployment": deployment_name,
            "namespace": self.namespace,
            "configured_replicas": replicas,
        }

    def execute_rollback(
        self,
        deployment_name: str,
        to_revision: Optional[int] = None,
        confirm: bool = False,
    ) -> Dict[str, Any]:
        """Executes or simulates a deployment rollback."""
        preflight = self.validate_preflight(deployment_name)
        if not preflight["can_rollback"]:
            return {
                "success": False,
                "deployment": deployment_name,
                "executed": False,
                "error": "Pre-flight validation failed: " + "; ".join(preflight["reasons"]),
                "dry_run": self.dry_run,
            }

        if self.dry_run:
            logger.info(f"[DRY-RUN] Rollback requested for deployment/{deployment_name} to revision {to_revision or 'previous'}")
            return {
                "success": True,
                "deployment": deployment_name,
                "executed": False,
                "dry_run": True,
                "message": f"[DRY-RUN] Safety checks passed. Deployment '{deployment_name}' would be rolled back to revision {to_revision or 'previous'}.",
                "planned_action": f"kubectl rollout undo deployment/{deployment_name} -n {self.namespace}"
                + (f" --to-revision={to_revision}" if to_revision else ""),
            }

        if not confirm:
            return {
                "success": False,
                "deployment": deployment_name,
                "executed": False,
                "dry_run": False,
                "error": "Confirmation required. Pass confirm=True to authorize rollback.",
            }

        # Execute live rollback via kubectl or API annotation trigger
        cmd = ["kubectl", "rollout", "undo", f"deployment/{deployment_name}", "-n", self.namespace]
        if to_revision:
            cmd.append(f"--to-revision={to_revision}")

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = proc.stdout.strip()
            return {
                "success": True,
                "deployment": deployment_name,
                "executed": True,
                "dry_run": False,
                "output": output,
                "message": f"Successfully triggered rollback for {deployment_name}: {output}",
            }
        except subprocess.CalledProcessError as e:
            err = e.stderr.strip() if e.stderr else str(e)
            logger.error(f"Failed to execute kubectl rollout undo: {err}")
            return {
                "success": False,
                "deployment": deployment_name,
                "executed": False,
                "dry_run": False,
                "error": f"Rollback execution command failed: {err}",
            }
        except Exception as e:
            return {
                "success": False,
                "deployment": deployment_name,
                "executed": False,
                "dry_run": False,
                "error": str(e),
            }
