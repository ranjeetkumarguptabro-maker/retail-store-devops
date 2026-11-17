#!/usr/bin/env python3
"""Platform Operations CLI (ops_cli.py)

Unified SRE and Site Reliability CLI for Kubernetes Platform Operations.
Detects pod failures, audits cluster resources, verifies deployments,
manages safe rollbacks, and exports Prometheus metrics.
"""

import argparse
import json
import logging
import os
import sys

# Ensure repository root and automation directory are in sys.path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
_AUTO_DIR = os.path.dirname(os.path.abspath(__file__))
if _AUTO_DIR not in sys.path:
    sys.path.insert(0, _AUTO_DIR)

from automation.collectors import (
    PodCollector,
    NodeCollector,
    ResourceCollector,
    EventCollector,
)
from automation.analyzers import (
    PodFailureDetector,
    ResourceAnomalyAnalyzer,
    DeploymentAnalyzer,
)
from automation.remediation import (
    RollbackManager,
    IncidentLifecycleOrchestrator,
)
from automation.reporting import (
    IncidentReportGenerator,
    get_metrics_exporter,
)

# Backwards compatibility imports for legacy script interfaces
try:
    from cluster_health import check_nodes
    from pod_health import inspect_pods
    from deployment_check import check_deployments
    from rollout_validator import validate_deployment_rollout
    from resource_monitor import audit_pod_resources
    from rollback_validator import validate_rollback
    from generate_report import generate_platform_report
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ops_cli")


def get_k8s_clients():
    """Initializes and returns Kubernetes CoreV1Api and AppsV1Api clients."""
    try:
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()
        return client.CoreV1Api(), client.AppsV1Api()
    except Exception as e:
        logger.warning(f"Could not connect to Kubernetes API server: {e}")
        return None, None


# ---------------------------------------------------------------------------
# SRE Automation Engine Subcommands
# ---------------------------------------------------------------------------

def cmd_diagnose(args):
    """Diagnoses cluster failures, isolates root causes, prints CLI overview, and saves JSON report."""
    core_api, _ = get_k8s_clients()
    metrics = get_metrics_exporter()
    namespace = args.namespace
    output_file = args.output or "reports/cluster-diagnostics.json"

    with metrics.track_duration("diagnose"):
        pod_collector = PodCollector(core_api=core_api, namespace=namespace)
        event_collector = EventCollector(core_api=core_api, namespace=namespace)
        detector = PodFailureDetector()

        pods_data = pod_collector.collect()
        events = event_collector.collect(warning_only=True)

        diagnosis = detector.diagnose_services(pods_data, events=events)

        # Collect optional resource and node info
        res_collector = ResourceCollector(core_api=core_api, namespace=namespace)
        resource_data = res_collector.collect()

        # Generate and save report
        reporter = IncidentReportGenerator(output_path=output_file)
        full_report = reporter.generate(
            diagnosis=diagnosis,
            resource_data=resource_data,
            events=events,
            namespace=namespace,
        )
        saved_path = reporter.save_report(full_report, file_path=output_file)

        # Update metrics
        for svc_name, svc_info in diagnosis.get("services", {}).items():
            st = svc_info.get("status")
            if st != "HEALTHY":
                metrics.record_failure(service=svc_name, failure_type=st)
        metrics.record_check("diagnostics", success=diagnosis.get("cluster_healthy", False))

    if args.format == "json":
        print(json.dumps(full_report, indent=2))
    else:
        cli_text = detector.format_cli_output(diagnosis, namespace=namespace)
        print(cli_text)
        print(f"\n[INFO] Comprehensive diagnostic report written to: {saved_path}")

    sys.exit(0 if diagnosis.get("cluster_healthy") else 1)


def cmd_monitor_resources(args):
    """Audits CPU and Memory requests, limits, node allocatable capacity, and anomalies."""
    core_api, _ = get_k8s_clients()
    metrics = get_metrics_exporter()
    namespace = args.namespace

    with metrics.track_duration("monitor_resources"):
        res_collector = ResourceCollector(core_api=core_api, namespace=namespace)
        node_collector = NodeCollector(core_api=core_api)
        analyzer = ResourceAnomalyAnalyzer()

        res_data = res_collector.collect()
        nodes_data = node_collector.collect()
        analysis = analyzer.analyze(res_data, nodes_data)

        metrics.record_check("resource_audit", success=(analysis["status"] == "HEALTHY"))

    if args.format == "json":
        print(json.dumps(analysis, indent=2))
    else:
        print("============================================================")
        print("          RETAIL STORE RESOURCE ANOMALY AUDIT              ")
        print("============================================================")
        print(f"Namespace:              {namespace}")
        print(f"Status:                 {analysis['status']}")
        print(f"Total CPU Requested:    {analysis['total_requested_cpu_cores']} cores")
        print(f"Total Memory Requested: {analysis['total_requested_memory_mb']} MB")
        if analysis["cpu_allocation_percent"] > 0:
            print(f"Cluster CPU Allocation: {analysis['cpu_allocation_percent']}%")
        if analysis["memory_allocation_percent"] > 0:
            print(f"Cluster Mem Allocation: {analysis['memory_allocation_percent']}%")
        print(f"Anomalies Detected:     {analysis['anomaly_count']}")
        print("------------------------------------------------------------")
        if analysis["anomalies"]:
            print("ANOMALIES:")
            for a in analysis["anomalies"]:
                print(f"  [{a['severity']}] {a['target']}: {a['message']}")
        if analysis["recommendations"]:
            print("\nRECOMMENDATIONS:")
            for r in analysis["recommendations"]:
                print(f"  * {r}")
        if not analysis["anomalies"]:
            print("All microservices and worker nodes comply with resource allocation policies.")
        print("============================================================")

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(analysis, f, indent=2)
        print(f"[INFO] Resource audit report written to: {args.output}")

    sys.exit(0 if analysis["status"] in ("HEALTHY", "WARNING") else 1)


def cmd_verify_deployment(args):
    """Verifies deployment rollout progression, replica counts, and synthetic endpoint health."""
    _, apps_api = get_k8s_clients()
    metrics = get_metrics_exporter()
    namespace = args.namespace

    with metrics.track_duration("verify_deployment"):
        analyzer = DeploymentAnalyzer(apps_api=apps_api, namespace=namespace)
        dep_res = analyzer.analyze_deployments()

        endpoints = {}
        if args.service_urls:
            try:
                endpoints = json.loads(args.service_urls)
            except Exception:
                logger.warning("Could not parse --service-urls JSON; skipping HTTP probing.")

        probe_res = analyzer.verify_endpoint_health(endpoints) if endpoints else {"all_endpoints_healthy": True, "results": {}}
        all_ok = dep_res.get("all_deployments_ready", False) and probe_res.get("all_endpoints_healthy", True)
        metrics.record_check("deployment_verification", success=all_ok)

    result_payload = {
        "deployments": dep_res,
        "endpoint_probes": probe_res,
        "overall_healthy": all_ok,
    }

    if args.format == "json":
        print(json.dumps(result_payload, indent=2))
    else:
        print("============================================================")
        print("        RETAIL STORE DEPLOYMENT VERIFICATION               ")
        print("============================================================")
        print(f"Namespace:         {namespace}")
        print(f"Overall Status:    {'READY' if all_ok else 'NOT READY'}")
        print(f"Deployments Ready: {dep_res.get('ready_count', 0)}/{dep_res.get('deployment_count', 0)}")
        print("------------------------------------------------------------")
        for d_name, d_info in dep_res.get("deployments", {}).items():
            st = "READY" if d_info.get("is_ready") else "PENDING"
            print(f"  {d_name:<26} [{st}] replicas: {d_info.get('available_replicas')}/{d_info.get('replicas')}")
        if endpoints:
            print("\nENDPOINT HEALTH PROBES:")
            for ep_name, ep_info in probe_res.get("results", {}).items():
                st = "HEALTHY" if ep_info.get("healthy") else "FAILED"
                print(f"  {ep_name:<14} [{st}] HTTP {ep_info.get('status_code')} ({ep_info.get('response_time_ms')} ms)")
        print("============================================================")

    sys.exit(0 if all_ok else 1)


def cmd_rollback(args):
    """Executes safe deployment rollback with preflight checks and dry-run safety gates."""
    _, apps_api = get_k8s_clients()
    metrics = get_metrics_exporter()
    mgr = RollbackManager(apps_api=apps_api, namespace=args.namespace, dry_run=args.dry_run)

    res = mgr.execute_rollback(
        deployment_name=args.deployment,
        to_revision=args.to_revision,
        confirm=args.confirm,
    )

    metrics.record_rollback(
        deployment=args.deployment,
        status="simulated" if args.dry_run else ("success" if res.get("success") else "failure"),
    )

    print(json.dumps(res, indent=2))
    sys.exit(0 if res.get("success") else 1)


def cmd_incident_lifecycle(args):
    """Executes the complete 7-stage incident lifecycle: Detect -> Collect -> Analyze -> Recommend -> Gate -> Verify -> Report."""
    core_api, apps_api = get_k8s_clients()
    metrics = get_metrics_exporter()

    orchestrator = IncidentLifecycleOrchestrator(
        core_api=core_api,
        apps_api=apps_api,
        namespace=args.namespace,
        output_dir=args.output_dir,
    )

    with metrics.track_duration("incident_lifecycle"):
        report = orchestrator.run_lifecycle(
            target_service=args.service,
            auto_approve=args.auto_approve,
            dry_run=args.dry_run,
            service_url=args.service_url,
        )

    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print("============================================================")
        print("         AUTOMATED INCIDENT LIFECYCLE ORCHESTRATION         ")
        print("============================================================")
        print(f"Incident ID:        {report.get('incident_id')}")
        print(f"Target Service:     {str(report.get('target_service', 'all')).capitalize()}")
        print(f"Namespace:          {report.get('namespace')}")
        print(f"Lifecycle Status:   {report.get('status')}")
        print(f"Duration:           {report.get('duration_seconds')}s")
        print("------------------------------------------------------------")
        print("LIFECYCLE AUDIT TRAIL:")
        for t in report.get("timeline", []):
            st = t.get("status", "OK")
            stage = t.get("stage", "")
            print(f"  [{st:<14}] {stage:<20} {t.get('message')}")

        diag = report.get("diagnosis")
        if diag:
            print("\nROOT CAUSE DIAGNOSIS:")
            print(f"  Failure Mode:     {diag.get('failure_type')}")
            print(f"  Root Cause:       {diag.get('root_cause')}")
            print(f"  Action Plan:      {report.get('remediation_plan', {}).get('action')}")

        if report.get("report_files"):
            print("\nPOST-MORTEM ARTIFACTS:")
            print(f"  JSON Record:      {report['report_files']['json']}")
            print(f"  Markdown Report:  {report['report_files']['markdown']}")
        print("============================================================")

    # Exit code: 0 if resolved, dry-run completed, or clean; 1 if remediation failed or waiting for approval
    success_states = ("RESOLVED", "DRY_RUN_COMPLETED", "NO_INCIDENT")
    sys.exit(0 if report.get("status") in success_states else 1)


def cmd_export_metrics(args):
    """Starts Prometheus metrics exporter HTTP daemon on specified port with live background audits."""
    metrics = get_metrics_exporter()
    port = args.port
    interval = getattr(args, "interval", 15)
    namespace = getattr(args, "namespace", "retail-store")
    run_once = getattr(args, "once", False)

    print(f"[INFO] Starting Prometheus metrics server on port {port}...")
    metrics.start_server(port=port)
    print(f"[SUCCESS] Scrape endpoint live at: http://localhost:{port}/metrics")

    core_api, _ = get_k8s_clients()

    def run_cycle():
        with metrics.track_duration("daemon_audit_cycle"):
            metrics.update_scrape_timestamp()
            if not core_api:
                metrics.record_check("daemon_cycle", success=True)
                return

            try:
                collector = PodCollector(core_api=core_api, namespace=namespace)
                detector = PodFailureDetector()
                pods = collector.collect()

                services = {"ui", "cart", "catalog", "checkout", "orders"}
                service_failures = {s: False for s in services}

                for p in pods:
                    svc = p.get("labels", {}).get("app.kubernetes.io/name") or p.get("pod_name", "").split("-")[0]
                    restarts = p.get("restart_count", 0)
                    metrics.set_pod_restarts(service=svc, pod_name=p.get("pod_name"), namespace=namespace, restarts=restarts)

                    diag = detector.analyze_pod(p)
                    if diag.get("status") in ("CRITICAL", "WARNING"):
                        ftype = diag.get("failure_type", "Unknown")
                        metrics.record_failure(service=svc, failure_type=ftype)
                        if svc in service_failures:
                            service_failures[svc] = True

                for svc, failed in service_failures.items():
                    metrics.set_service_health(service=svc, namespace=namespace, healthy=not failed)

                metrics.record_check("daemon_cycle", success=True)
            except Exception as e:
                logger.error(f"Error during daemon audit cycle: {e}")
                metrics.record_check("daemon_cycle", success=False)

    run_cycle()
    if run_once:
        print("[INFO] Single evaluation cycle complete (--once).")
        return

    print(f"[INFO] Running continuous cluster monitor every {interval}s (Press Ctrl+C to exit)...")
    try:
        import time
        while True:
            time.sleep(interval)
            run_cycle()
    except KeyboardInterrupt:
        print("\n[INFO] Metrics exporter stopped gracefully.")
        sys.exit(0)


# ---------------------------------------------------------------------------
# Legacy Commands Bridge (for backwards compatibility)
# ---------------------------------------------------------------------------

def cmd_legacy_cluster(args):
    v1, _ = get_k8s_clients()
    if not v1:
        sys.exit(1)
    res = check_nodes(v1)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["status"] == "HEALTHY" else 1)


def cmd_legacy_pods(args):
    v1, _ = get_k8s_clients()
    if not v1:
        sys.exit(1)
    res = inspect_pods(v1, namespace=args.namespace)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["status"] == "HEALTHY" else 1)


def cmd_legacy_deployments(args):
    _, apps_v1 = get_k8s_clients()
    if not apps_v1:
        sys.exit(1)
    res = check_deployments(apps_v1, namespace=args.namespace)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["status"] == "HEALTHY" else 1)


def cmd_legacy_rollout(args):
    _, apps_v1 = get_k8s_clients()
    if not apps_v1:
        sys.exit(1)
    res = validate_deployment_rollout(apps_v1, args.deployment, namespace=args.namespace)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["rollout_complete"] else 1)


def cmd_legacy_rollback(args):
    _, apps_v1 = get_k8s_clients()
    if not apps_v1:
        sys.exit(1)
    res = validate_rollback(apps_v1, args.deployment, namespace=args.namespace, expected_image=args.expected_image)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["rollback_healthy"] else 1)


def cmd_legacy_resources(args):
    v1, _ = get_k8s_clients()
    if not v1:
        sys.exit(1)
    res = audit_pod_resources(v1, namespace=args.namespace)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["status"] == "COMPLIANT" else 1)


def cmd_legacy_report(args):
    v1, apps_v1 = get_k8s_clients()
    if not v1 or not apps_v1:
        sys.exit(1)
    rep = generate_platform_report(v1, apps_v1, namespace=args.namespace)
    output_str = json.dumps(rep, indent=2)
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output_str)
        print(f"[SUCCESS] Diagnostic report written to {args.output}")
    else:
        print(output_str)
    sys.exit(0 if rep["overall_status"] == "HEALTHY" else 1)


def build_parser() -> argparse.ArgumentParser:
    """Builds and returns the argument parser."""
    parser = argparse.ArgumentParser(
        prog="ops_cli",
        description="Retail Store Platform Operations Automation Engine & SRE CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. diagnose
    p_diag = subparsers.add_parser("diagnose", help="Intelligent pod failure detection and incident diagnosis")
    p_diag.add_argument("--namespace", "-n", default="retail-store", help="Kubernetes namespace (default: retail-store)")
    p_diag.add_argument("--output", "-o", default="reports/cluster-diagnostics.json", help="Path to save JSON diagnostics")
    p_diag.add_argument("--format", choices=["table", "json"], default="table", help="Terminal output layout")

    # 2. monitor-resources
    p_mon = subparsers.add_parser("monitor-resources", help="Audit CPU/memory consumption, requests/limits, and node capacity")
    p_mon.add_argument("--namespace", "-n", default="retail-store", help="Kubernetes namespace")
    p_mon.add_argument("--output", "-o", default=None, help="Save JSON audit report to path")
    p_mon.add_argument("--format", choices=["table", "json"], default="table", help="Output format")

    # 3. verify-deployment
    p_ver = subparsers.add_parser("verify-deployment", help="Automated rollout status check and synthetic endpoint probes")
    p_ver.add_argument("--namespace", "-n", default="retail-store", help="Kubernetes namespace")
    p_ver.add_argument("--service-urls", default=None, help="JSON dictionary of service names to endpoint URLs")
    p_ver.add_argument("--format", choices=["table", "json"], default="table", help="Output format")

    # 4. rollback
    p_rb = subparsers.add_parser("rollback", help="Safely trigger or simulate deployment rollback with safety gates")
    p_rb.add_argument("--deployment", "-d", required=True, help="Target deployment name")
    p_rb.add_argument("--namespace", "-n", default="retail-store", help="Kubernetes namespace")
    p_rb.add_argument("--dry-run", action="store_true", help="Simulate rollback without cluster mutation")
    p_rb.add_argument("--confirm", action="store_true", help="Confirm authorization for live rollback execution")
    p_rb.add_argument("--to-revision", type=int, default=None, help="Specific revision number to roll back to")

    # 5. incident-lifecycle (end-to-end 7-stage incident response)
    p_life = subparsers.add_parser(
        "incident-lifecycle",
        aliases=["remediate-incident", "lifecycle"],
        help="Execute automated 7-stage incident response (Detect->Collect->Analyze->Recommend->Gate->Verify->Report)",
    )
    p_life.add_argument("--service", "-s", default=None, help="Target service (e.g. cart, ui, catalog)")
    p_life.add_argument("--namespace", "-n", default="retail-store", help="Kubernetes namespace")
    p_life.add_argument("--auto-approve", action="store_true", help="Authorize automated rollback execution without interactive gate")
    p_life.add_argument("--dry-run", action="store_true", help="Simulate rollback and verification without modifying cluster")
    p_life.add_argument("--service-url", default=None, help="Service URL to probe for post-recovery verification")
    p_life.add_argument("--output-dir", default="reports/incidents", help="Directory to save JSON & Markdown incident post-mortems")
    p_life.add_argument("--format", choices=["table", "json"], default="table", help="Terminal output layout")

    # 6. export-metrics
    p_met = subparsers.add_parser("export-metrics", help="Run background Prometheus metrics HTTP exporter")
    p_met.add_argument("--port", "-p", type=int, default=9102, help="Port to expose Prometheus metrics (default: 9102)")
    p_met.add_argument("--interval", "-i", type=int, default=15, help="Cluster evaluation poll interval in seconds (default: 15)")
    p_met.add_argument("--namespace", "-n", default="retail-store", help="Kubernetes namespace to evaluate (default: retail-store)")
    p_met.add_argument("--once", action="store_true", help="Run a single evaluation cycle and exit (useful for testing and cron)")

    # Legacy Subcommands
    subparsers.add_parser("cluster", help="Check cluster connectivity and node readiness (legacy)")
    p_pods = subparsers.add_parser("pods", help="Audit pod health (legacy)")
    p_pods.add_argument("--namespace", "-n", default="retail-store")
    p_dep = subparsers.add_parser("deployments", help="Verify deployment replica availability (legacy)")
    p_dep.add_argument("--namespace", "-n", default="retail-store")
    p_roll = subparsers.add_parser("validate-rollout", help="Validate rolling update status (legacy)")
    p_roll.add_argument("--deployment", "-d", required=True)
    p_roll.add_argument("--namespace", "-n", default="retail-store")
    p_back = subparsers.add_parser("validate-rollback", help="Verify rollback completion (legacy)")
    p_back.add_argument("--deployment", "-d", required=True)
    p_back.add_argument("--namespace", "-n", default="retail-store")
    p_back.add_argument("--expected-image", "-i", default=None)
    p_res = subparsers.add_parser("audit-resources", help="Audit container CPU/Memory requests & limits (legacy)")
    p_res.add_argument("--namespace", "-n", default="retail-store")
    p_rep = subparsers.add_parser("report", help="Generate full platform diagnostic operational report (legacy)")
    p_rep.add_argument("--namespace", "-n", default="retail-store")
    p_rep.add_argument("--output", "-o", default=None)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "diagnose": cmd_diagnose,
        "monitor-resources": cmd_monitor_resources,
        "verify-deployment": cmd_verify_deployment,
        "rollback": cmd_rollback,
        "incident-lifecycle": cmd_incident_lifecycle,
        "remediate-incident": cmd_incident_lifecycle,
        "lifecycle": cmd_incident_lifecycle,
        "export-metrics": cmd_export_metrics,
        "cluster": cmd_legacy_cluster,
        "pods": cmd_legacy_pods,
        "deployments": cmd_legacy_deployments,
        "validate-rollout": cmd_legacy_rollout,
        "validate-rollback": cmd_legacy_rollback,
        "audit-resources": cmd_legacy_resources,
        "report": cmd_legacy_report,
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn:
        cmd_fn(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
