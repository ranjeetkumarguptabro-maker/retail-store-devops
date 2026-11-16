"""Intelligent Pod Failure Detector and Root Cause Diagnostic Engine."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("operations_engine.analyzers.failure")

KNOWN_SERVICES = ["ui", "catalog", "cart", "orders", "checkout"]

FAILURE_REMEDIATIONS = {
    "CrashLoopBackOff": "Inspect application configuration, database connection strings, and fatal stack traces in pod logs. Verify liveness probes are not timing out.",
    "ImagePullBackOff": "Verify Docker image repository, tag existence, and AWS ECR / ImagePullSecrets credentials in namespace.",
    "ErrImagePull": "Check image tag spelling and network access to container registry from worker nodes.",
    "OOMKilled": "Container exceeded cgroup memory limit (exit code 137). Increase container resources.limits.memory in Kubernetes deployment manifest.",
    "Pending": "Pod cannot be scheduled. Check node capacity (CPU/memory requests), node taints/tolerations, or PersistentVolumeClaim bindings.",
    "RestartSpike": "Frequent container restarts detected. Check application memory leaks, intermittent unhandled exceptions, or flapping readiness/liveness probes.",
    "CreateContainerConfigError": "Missing ConfigMap, Secret, or environment variable reference required by container specification.",
}


class PodFailureDetector:
    """Analyzes pod telemetry and events to detect failure modes and isolate root causes."""

    def __init__(self, restart_spike_threshold: int = 5):
        self.restart_spike_threshold = restart_spike_threshold

    def analyze_pod(self, pod_data: Dict[str, Any], events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Performs in-depth root cause diagnostics on a single pod."""
        pod_name = pod_data.get("name", "unknown")
        service = pod_data.get("service", "unknown")
        phase = pod_data.get("phase", "Unknown")
        total_restarts = pod_data.get("total_restarts", 0)
        containers = pod_data.get("containers", [])
        pod_logs = pod_data.get("logs", "")

        detected_failures: List[Dict[str, Any]] = []

        # 1. Check phase level issues (e.g. Pending)
        if phase == "Pending":
            related_events = [e for e in (events or []) if e.get("object_name") == pod_name or pod_name in e.get("message", "")]
            scheduling_msg = related_events[0]["message"] if related_events else "Pod unscheduled in Pending phase."
            detected_failures.append({
                "type": "Pending",
                "severity": "CRITICAL",
                "message": scheduling_msg,
                "remediation": FAILURE_REMEDIATIONS.get("Pending"),
            })

        # 2. Check each container state for CrashLoopBackOff, ImagePullBackOff, OOMKilled, etc.
        for c in containers:
            c_name = c.get("name", "")
            state = c.get("state")
            reason = c.get("reason", "")
            message = c.get("message", "")
            exit_code = c.get("exit_code")

            if reason == "CrashLoopBackOff" or (state == "waiting" and "CrashLoop" in reason):
                detected_failures.append({
                    "type": "CrashLoopBackOff",
                    "container": c_name,
                    "severity": "CRITICAL",
                    "message": f"CrashLoopBackOff on container '{c_name}': {message or 'Application continuously failing on startup'}",
                    "remediation": FAILURE_REMEDIATIONS.get("CrashLoopBackOff"),
                })
            elif reason in ("ImagePullBackOff", "ErrImagePull"):
                detected_failures.append({
                    "type": reason,
                    "container": c_name,
                    "severity": "HIGH",
                    "message": f"{reason} on container '{c_name}': {message or 'Image pull failed'}",
                    "remediation": FAILURE_REMEDIATIONS.get(reason, FAILURE_REMEDIATIONS.get("ImagePullBackOff")),
                })
            elif reason == "OOMKilled" or exit_code == 137:
                detected_failures.append({
                    "type": "OOMKilled",
                    "container": c_name,
                    "severity": "CRITICAL",
                    "message": f"Container {c_name} terminated with exit code 137 (Out Of Memory).",
                    "remediation": FAILURE_REMEDIATIONS.get("OOMKilled"),
                })
            elif reason == "CreateContainerConfigError":
                detected_failures.append({
                    "type": "CreateContainerConfigError",
                    "container": c_name,
                    "severity": "HIGH",
                    "message": message or f"Missing ConfigMap or Secret for {c_name}.",
                    "remediation": FAILURE_REMEDIATIONS.get("CreateContainerConfigError"),
                })

        # 3. Check for restart spikes
        if total_restarts >= self.restart_spike_threshold and not any(f["type"] == "CrashLoopBackOff" for f in detected_failures):
            detected_failures.append({
                "type": "RestartSpike",
                "severity": "WARNING",
                "message": f"Pod restart count ({total_restarts}) exceeded threshold ({self.restart_spike_threshold}).",
                "remediation": FAILURE_REMEDIATIONS.get("RestartSpike"),
            })

        # Determine diagnostic status
        if not detected_failures:
            status = "HEALTHY"
            root_cause = "Pod and all containers are healthy and running."
            remediation = "None"
        else:
            primary_failure = detected_failures[0]
            status = primary_failure["type"].upper()
            root_cause = primary_failure["message"]
            remediation = primary_failure["remediation"]

        return {
            "pod_name": pod_name,
            "service": service,
            "phase": phase,
            "status": status,
            "is_healthy": len(detected_failures) == 0,
            "failures": detected_failures,
            "root_cause": root_cause,
            "remediation": remediation,
            "total_restarts": total_restarts,
            "logs_sample": pod_logs[:500] if pod_logs else "No recent crash logs found.",
        }

    def diagnose_services(
        self,
        pods_data: List[Dict[str, Any]],
        events: Optional[List[Dict[str, Any]]] = None,
        expected_services: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Aggregates pod diagnostics into service-level health and actionable incident reports."""
        services = expected_services or KNOWN_SERVICES
        service_reports: Dict[str, Dict[str, Any]] = {}
        all_pod_diagnostics: List[Dict[str, Any]] = []

        # Initialize expected services
        for svc in services:
            service_reports[svc] = {
                "service": svc,
                "status": "MISSING",
                "pod_count": 0,
                "healthy_pods": 0,
                "diagnostics": [],
                "primary_issue": None,
                "suggested_action": "Deploy service manifests to cluster.",
            }

        # Analyze each pod
        for pod in pods_data:
            diag = self.analyze_pod(pod, events=events)
            all_pod_diagnostics.append(diag)
            svc = pod.get("service", "unknown")

            if svc not in service_reports:
                service_reports[svc] = {
                    "service": svc,
                    "status": "HEALTHY" if diag["is_healthy"] else diag["status"],
                    "pod_count": 0,
                    "healthy_pods": 0,
                    "diagnostics": [],
                    "primary_issue": None,
                    "suggested_action": "None",
                }

            s_entry = service_reports[svc]
            s_entry["pod_count"] += 1
            if diag["is_healthy"]:
                s_entry["healthy_pods"] += 1
            s_entry["diagnostics"].append(diag)

            if not diag["is_healthy"]:
                s_entry["status"] = diag["status"]
                s_entry["primary_issue"] = diag["root_cause"]
                s_entry["suggested_action"] = diag["remediation"]

        # Finalize overall service statuses
        for svc, data in service_reports.items():
            if data["pod_count"] > 0 and data["healthy_pods"] == data["pod_count"]:
                data["status"] = "HEALTHY"
                data["suggested_action"] = "Service operating normally."

        cluster_healthy = all(s["status"] == "HEALTHY" for s in service_reports.values() if s["pod_count"] > 0)

        return {
            "cluster_healthy": cluster_healthy,
            "services": service_reports,
            "pod_diagnostics": all_pod_diagnostics,
            "summary": {
                "total_services": len(service_reports),
                "healthy_services": sum(1 for s in service_reports.values() if s["status"] == "HEALTHY"),
                "failing_services": sum(1 for s in service_reports.values() if s["status"] not in ("HEALTHY", "MISSING")),
            },
        }

    def format_cli_output(self, diagnosis: Dict[str, Any], namespace: str = "retail-store") -> str:
        """Formats the diagnosis into the required terminal output layout."""
        lines = [
            "============================================================",
            "             RETAIL STORE CLUSTER DIAGNOSTICS               ",
            "============================================================",
            f"Namespace: {namespace}",
            "",
            "SERVICE HEALTH OVERVIEW:",
        ]

        failing_services = []
        for svc_name, s_data in diagnosis.get("services", {}).items():
            status = s_data["status"]
            status_display = status
            lines.append(f"  {svc_name.capitalize():<12} {status_display}")
            if status != "HEALTHY":
                failing_services.append(s_data)

        if failing_services:
            lines.append("")
            lines.append("INCIDENT ROOT CAUSE & REMEDIATION:")
            lines.append("------------------------------------------------------------")
            for fs in failing_services:
                svc = fs["service"].capitalize()
                issue = fs.get("primary_issue") or "Service degraded or pods failing"
                action = fs.get("suggested_action") or "Investigate pod logs"
                lines.append(f"Service: {svc}")
                lines.append(f"  Issue:       {issue}")
                lines.append(f"  Remediation: {action}")
                for d in fs.get("diagnostics", []):
                    if not d.get("is_healthy") and d.get("logs_sample"):
                        lines.append(f"  Pod Log Extract ({d['pod_name']}):")
                        for log_line in d["logs_sample"].strip().split("\n")[:4]:
                            lines.append(f"    | {log_line}")
                lines.append("")
        else:
            lines.append("")
            lines.append("All Retail Store microservices are healthy and operating normally.")

        lines.append("============================================================")
        return "\n".join(lines)
