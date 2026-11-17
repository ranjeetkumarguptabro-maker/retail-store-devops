"""Complete End-to-End Incident Lifecycle Orchestrator for Kubernetes Microservices.

Executes the 7-stage SRE incident lifecycle:
1. Detect: Identify failing pod or service anomaly (e.g. CrashLoopBackOff on Cart)
2. Collect: Ingest logs, exit codes, and Kubernetes warning events as evidence
3. Analyze: Classify failure root cause, severity, and error stack traces
4. Recommend: Formulate explicit remediation action and rollback target
5. Gate & Execute: Enforce operator approval gate before rolling back deployment
6. Verify: Poll deployment stabilization, replica readiness, and HTTP health probes
7. Report: Generate structured JSON incident record and Markdown post-mortem
"""

from datetime import datetime, timezone
import json
import logging
import os
from typing import Any, Dict, List, Optional

from automation.collectors.pod_collector import PodCollector
from automation.collectors.event_collector import EventCollector
from automation.analyzers.failure_detector import PodFailureDetector
from automation.remediation.rollback import RollbackManager
from automation.remediation.recovery_validator import RecoveryValidator
from automation.reporting.metrics import get_metrics_exporter

logger = logging.getLogger("operations_engine.remediation.lifecycle")


class IncidentLifecycleOrchestrator:
    """Coordinates detection, forensics, root-cause analysis, gated rollback, verification, and reporting."""

    def __init__(
        self,
        core_api: Optional[Any] = None,
        apps_api: Optional[Any] = None,
        namespace: str = "retail-store",
        output_dir: str = "reports/incidents",
    ):
        self.namespace = namespace
        self.output_dir = output_dir
        self.core_api = core_api
        self.apps_api = apps_api
        self.metrics = get_metrics_exporter()

    def run_lifecycle(
        self,
        target_service: Optional[str] = None,
        auto_approve: bool = False,
        dry_run: bool = False,
        service_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes the complete 7-stage incident response lifecycle."""
        start_time = datetime.now(timezone.utc)
        incident_id = f"INC-{start_time.strftime('%Y%m%d-%H%M%S')}-{target_service or 'cluster'}"
        timeline: List[Dict[str, Any]] = []

        def log_event(stage: str, message: str, status: str = "COMPLETED"):
            now = datetime.now(timezone.utc).isoformat()
            timeline.append({"timestamp": now, "stage": stage, "message": message, "status": status})
            logger.info(f"[{stage}] {message}")

        log_event("INITIALIZATION", f"Starting incident lifecycle inspection for incident {incident_id}")

        # -------------------------------------------------------------------
        # Stage 1: Detection
        # -------------------------------------------------------------------
        log_event("STAGE_1_DETECTION", f"Scanning namespace '{self.namespace}' for pod and service failures...")
        pod_collector = PodCollector(core_api=self.core_api, namespace=self.namespace)
        detector = PodFailureDetector()

        pods_data = pod_collector.collect()
        if target_service:
            pods_data = [p for p in pods_data if p.get("service") == target_service or target_service in p.get("name", "")]

        failing_pods = [p for p in pods_data if not p.get("ready") or p.get("has_critical_issue") or p.get("phase") != "Running"]

        if not failing_pods:
            log_event("STAGE_1_DETECTION", f"No active pod failures detected in target scope ({target_service or 'all'}).", "CLEAN")
            report = {
                "incident_id": incident_id,
                "status": "NO_INCIDENT",
                "target_service": target_service or "all",
                "namespace": self.namespace,
                "timestamp_detected": start_time.isoformat(),
                "timestamp_resolved": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": round((datetime.now(timezone.utc) - start_time).total_seconds(), 2),
                "summary": "Cluster and target services operating normally; no remediation required.",
                "timeline": timeline,
                "evidence": {},
                "remediation": None,
                "verification": None,
            }
            self._save_incident_report(report)
            return report

        primary_pod = failing_pods[0]
        failing_service = primary_pod.get("service") or (target_service or "unknown")
        deployment_name = f"retail-store-{failing_service}" if not failing_service.startswith("retail-store-") else failing_service

        log_event("STAGE_1_DETECTION", f"Detected failing pod '{primary_pod.get('name')}' for service '{failing_service}'.", "FAILURE_CONFIRMED")
        self.metrics.record_failure(failing_service, primary_pod.get("health_status", "UNKNOWN"))

        # -------------------------------------------------------------------
        # Stage 2: Evidence Collection
        # -------------------------------------------------------------------
        log_event("STAGE_2_COLLECTION", f"Extracting forensic container logs and Kubernetes events for {primary_pod.get('name')}...")
        event_collector = EventCollector(core_api=self.core_api, namespace=self.namespace)
        pod_events = event_collector.get_events_for_pod(primary_pod.get("name", ""))
        pod_logs = primary_pod.get("logs") or pod_collector.get_container_logs(primary_pod.get("name", ""), tail_lines=100)

        evidence = {
            "pod_name": primary_pod.get("name"),
            "service": failing_service,
            "phase": primary_pod.get("phase"),
            "restart_count": primary_pod.get("total_restarts", 0),
            "containers": primary_pod.get("containers", []),
            "events": pod_events,
            "raw_logs_sample": pod_logs[:2000] if pod_logs else "No standard output captured",
        }
        log_event("STAGE_2_COLLECTION", f"Collected {len(pod_events)} events and {len(pod_logs)} bytes of log evidence.")

        # -------------------------------------------------------------------
        # Stage 3: Root Cause Isolation & Diagnosis
        # -------------------------------------------------------------------
        log_event("STAGE_3_ANALYSIS", "Running diagnostic classification on container states and log traces...")
        diagnosis = detector.analyze_pod(primary_pod, events=pod_events)
        failure_type = diagnosis.get("status", "UNKNOWN")
        root_cause = diagnosis.get("root_cause") or "Undetermined application runtime error"
        suggested_remediation = diagnosis.get("remediation")

        log_event("STAGE_3_ANALYSIS", f"Diagnosed failure: [{failure_type}] {root_cause}", "ROOT_CAUSE_ISOLATED")

        # -------------------------------------------------------------------
        # Stage 4: Remediation Recommendation
        # -------------------------------------------------------------------
        log_event("STAGE_4_RECOMMENDATION", f"Formulating automated recovery strategy for deployment '{deployment_name}'...")
        planned_strategy = "ROLLBACK_DEPLOYMENT"
        remediation_plan = {
            "strategy": planned_strategy,
            "target_deployment": deployment_name,
            "action": f"Roll back deployment '{deployment_name}' to previous healthy revision",
            "justification": f"Mitigates {failure_type} regression: {suggested_remediation}",
            "requires_approval": not auto_approve and not dry_run,
        }
        log_event("STAGE_4_RECOMMENDATION", f"Recommended Action: {remediation_plan['action']}")

        # -------------------------------------------------------------------
        # Stage 5: Gated Execution (Approval & Rollback)
        # -------------------------------------------------------------------
        rollback_mgr = RollbackManager(apps_api=self.apps_api, namespace=self.namespace, dry_run=dry_run)
        rollback_result: Dict[str, Any] = {}

        if dry_run:
            log_event("STAGE_5_EXECUTION", f"[DRY-RUN] Simulating rollback on deployment '{deployment_name}'", "SIMULATED")
            rollback_result = rollback_mgr.execute_rollback(deployment_name, confirm=True)
            lifecycle_status = "DRY_RUN_COMPLETED"
        elif not auto_approve:
            log_event("STAGE_5_EXECUTION", f"Rollback requires human authorization. Halting at approval gate for '{deployment_name}'.", "AWAITING_APPROVAL")
            rollback_result = {
                "success": False,
                "executed": False,
                "awaiting_approval": True,
                "message": f"Deployment '{deployment_name}' requires approval. Run with --auto-approve to execute.",
            }
            lifecycle_status = "AWAITING_APPROVAL"
        else:
            log_event("STAGE_5_EXECUTION", f"Approval granted. Executing automated rollback on '{deployment_name}'...", "EXECUTING")
            rollback_result = rollback_mgr.execute_rollback(deployment_name, confirm=True)
            if rollback_result.get("success"):
                log_event("STAGE_5_EXECUTION", f"Rollback trigger succeeded: {rollback_result.get('output', 'OK')}", "ROLLBACK_APPLIED")
                lifecycle_status = "REMEDIATION_APPLIED"
            else:
                log_event("STAGE_5_EXECUTION", f"Rollback failed: {rollback_result.get('error')}", "ROLLBACK_FAILED")
                lifecycle_status = "REMEDIATION_FAILED"

        # -------------------------------------------------------------------
        # Stage 6: Post-Recovery Verification
        # -------------------------------------------------------------------
        verification_result: Dict[str, Any] = {}
        if rollback_result.get("success") and not dry_run:
            log_event("STAGE_6_VERIFICATION", f"Verifying stabilization of deployment '{deployment_name}'...")
            validator = RecoveryValidator(apps_api=self.apps_api, core_api=self.core_api, namespace=self.namespace)
            verification_result = validator.verify_service_stabilization(
                deployment_name=deployment_name,
                service_url=service_url,
                timeout_seconds=30,
                poll_interval=2.0,
            )
            if verification_result.get("recovered"):
                log_event("STAGE_6_VERIFICATION", f"Service '{failing_service}' stabilized and healthy! (HTTP {verification_result.get('endpoint_status_code')})", "RECOVERED")
                lifecycle_status = "RESOLVED"
            else:
                log_event("STAGE_6_VERIFICATION", f"Recovery validation incomplete: {verification_result.get('details')}", "UNSTABLE")
                lifecycle_status = "UNSTABLE"
        elif dry_run:
            verification_result = {"simulated": True, "expected_health": "RECOVERED"}

        # -------------------------------------------------------------------
        # Stage 7: Reporting & Post-Mortem
        # -------------------------------------------------------------------
        end_time = datetime.now(timezone.utc)
        duration_sec = round((end_time - start_time).total_seconds(), 2)
        log_event("STAGE_7_REPORTING", f"Compiling structured incident post-mortem {incident_id} (Duration: {duration_sec}s)...")

        final_report = {
            "incident_id": incident_id,
            "status": lifecycle_status,
            "target_service": failing_service,
            "namespace": self.namespace,
            "timestamp_detected": start_time.isoformat(),
            "timestamp_resolved": end_time.isoformat() if lifecycle_status == "RESOLVED" else None,
            "duration_seconds": duration_sec,
            "diagnosis": {
                "failure_type": failure_type,
                "root_cause": root_cause,
                "remediation_guidance": suggested_remediation,
            },
            "evidence": evidence,
            "remediation_plan": remediation_plan,
            "rollback_execution": rollback_result,
            "verification": verification_result,
            "timeline": timeline,
            "post_mortem": {
                "impact": f"Service '{failing_service}' experienced {failure_type} disrupting availability.",
                "root_cause_summary": root_cause,
                "remediation_summary": f"Executed rollback of deployment '{deployment_name}'.",
                "preventative_actions": [
                    "Verify container configuration and DB credentials in CI staging before rolling update.",
                    "Ensure readiness probe initialDelaySeconds accommodates application startup time.",
                    "Enforce strict memory limits to avert OOMKilled events.",
                ],
            },
        }

        json_path, md_path = self._save_incident_report(final_report)
        final_report["report_files"] = {"json": json_path, "markdown": md_path}
        log_event("STAGE_7_REPORTING", f"Incident reports generated: {json_path} and {md_path}", "REPORT_SAVED")

        # Telemetry updates
        self.metrics.record_check("incident_lifecycle", success=(lifecycle_status in ("RESOLVED", "DRY_RUN_COMPLETED")))
        if rollback_result.get("executed"):
            self.metrics.record_rollback(deployment_name, "success" if lifecycle_status == "RESOLVED" else "failure")

        return final_report

    def _save_incident_report(self, report: Dict[str, Any]) -> tuple[str, str]:
        """Saves both JSON telemetry and human-readable Markdown post-mortem."""
        os.makedirs(self.output_dir, exist_ok=True)
        incident_id = report.get("incident_id", "incident")

        json_file = os.path.join(self.output_dir, f"{incident_id}.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

        md_file = os.path.join(self.output_dir, f"{incident_id}.md")
        md_content = self.format_markdown_report(report)
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_content)

        return json_file, md_file

    def format_markdown_report(self, report: Dict[str, Any]) -> str:
        """Renders an incident report as a GitHub-flavored Markdown post-mortem."""
        inc_id = report.get("incident_id")
        status = report.get("status")
        svc = str(report.get("target_service", "Unknown")).upper()
        diag = report.get("diagnosis") or {}
        post_mortem = report.get("post_mortem") or {}
        verification = report.get("verification") or {}
        evidence = report.get("evidence") or {}

        md = [
            f"# SRE Incident Post-Mortem: {inc_id}",
            "",
            f"**Service:** `{svc}` | **Status:** `{status}` | **Namespace:** `{report.get('namespace')}`",
            f"**Detected At:** `{report.get('timestamp_detected')}` | **Duration:** `{report.get('duration_seconds')}s`",
            "",
            "## 1. Executive Summary",
            f"- **Failure Mode:** `{diag.get('failure_type', 'N/A')}`",
            f"- **Root Cause:** {diag.get('root_cause', 'N/A')}",
            f"- **Remediation Action:** {report.get('remediation_plan', {}).get('action', 'N/A') if report.get('remediation_plan') else 'None'}",
            "",
            "## 2. Incident Timeline",
            "| Timestamp (UTC) | Lifecycle Stage | Status | Details |",
            "|---|---|:---:|---|",
        ]

        for item in report.get("timeline", []):
            md.append(f"| {item.get('timestamp')} | `{item.get('stage')}` | {item.get('status')} | {item.get('message')} |")

        md.extend([
            "",
            "## 3. Forensic Evidence",
            "```text",
            str(evidence.get("raw_logs_sample", "No logs"))[:800],
            "```",
            "",
            "## 4. Verification & Health Probes",
            f"- **Deployment Stabilized:** `{verification.get('stabilized', False)}`",
            f"- **Replicas Available:** `{verification.get('replicas_available', 0)} / {verification.get('replicas_expected', 1)}`",
            f"- **HTTP Status Code:** `{verification.get('endpoint_status_code', 'N/A')}`",
            "",
            "## 5. Preventative Action Items",
        ])

        for action in post_mortem.get("preventative_actions", []):
            md.append(f"- [x] {action}")

        md.append("")
        return "\n".join(md)
