#!/usr/bin/env python3
"""
Platform Operations CLI (ops_cli.py)
Unified CLI for Site Reliability & Kubernetes Platform Operations.
Developed for enterprise microservices management.
"""

import sys
import json
import argparse
from datetime import datetime, timezone

from cluster_health import check_nodes
from pod_health import inspect_pods
from deployment_check import check_deployments
from rollout_validator import validate_deployment_rollout
from resource_monitor import audit_pod_resources
from rollback_validator import validate_rollback
from generate_report import generate_platform_report


def get_k8s_clients():
    """Initializes and returns Kubernetes CoreV1Api and AppsV1Api clients."""
    try:
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        return client.CoreV1Api(), client.AppsV1Api()
    except Exception as e:
        print(f"[ERROR] Could not connect to Kubernetes API server: {e}", file=sys.stderr)
        return None, None


def cmd_cluster(args):
    v1, _ = get_k8s_clients()
    if not v1:
        sys.exit(1)
    res = check_nodes(v1)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["status"] == "HEALTHY" else 1)


def cmd_pods(args):
    v1, _ = get_k8s_clients()
    if not v1:
        sys.exit(1)
    res = inspect_pods(v1, namespace=args.namespace)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["status"] == "HEALTHY" else 1)


def cmd_deployments(args):
    _, apps_v1 = get_k8s_clients()
    if not apps_v1:
        sys.exit(1)
    res = check_deployments(apps_v1, namespace=args.namespace)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["status"] == "HEALTHY" else 1)


def cmd_rollout(args):
    _, apps_v1 = get_k8s_clients()
    if not apps_v1:
        sys.exit(1)
    res = validate_deployment_rollout(apps_v1, args.deployment, namespace=args.namespace)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["rollout_complete"] else 1)


def cmd_rollback(args):
    _, apps_v1 = get_k8s_clients()
    if not apps_v1:
        sys.exit(1)
    res = validate_rollback(apps_v1, args.deployment, namespace=args.namespace, expected_image=args.expected_image)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["rollback_healthy"] else 1)


def cmd_resources(args):
    v1, _ = get_k8s_clients()
    if not v1:
        sys.exit(1)
    res = audit_pod_resources(v1, namespace=args.namespace)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["status"] == "COMPLIANT" else 1)


def cmd_report(args):
    v1, apps_v1 = get_k8s_clients()
    if not v1 or not apps_v1:
        sys.exit(1)
    rep = generate_platform_report(v1, apps_v1, namespace=args.namespace)
    output_str = json.dumps(rep, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_str)
        print(f"[SUCCESS] Diagnostic report written to {args.output}")
    else:
        print(output_str)

    sys.exit(0 if rep["overall_status"] == "HEALTHY" else 1)


def main():
    parser = argparse.ArgumentParser(
        prog="ops_cli",
        description="Platform Operations Automation Engine for Kubernetes & Microservices"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: cluster
    subparsers.add_parser("cluster", help="Check Kubernetes cluster connectivity and node readiness")

    # Subcommand: pods
    p_pods = subparsers.add_parser("pods", help="Audit pod health, detect CrashLoopBackOff & restart counts")
    p_pods.add_argument("--namespace", "-n", default="retail-store", help="Kubernetes namespace")

    # Subcommand: deployments
    p_dep = subparsers.add_parser("deployments", help="Verify deployment replica availability")
    p_dep.add_argument("--namespace", "-n", default="retail-store", help="Kubernetes namespace")

    # Subcommand: rollout
    p_roll = subparsers.add_parser("validate-rollout", help="Validate zero-downtime rolling update status")
    p_roll.add_argument("--deployment", "-d", required=True, help="Deployment name")
    p_roll.add_argument("--namespace", "-n", default="retail-store", help="Kubernetes namespace")

    # Subcommand: rollback
    p_back = subparsers.add_parser("validate-rollback", help="Verify rollback completion and traffic recovery")
    p_back.add_argument("--deployment", "-d", required=True, help="Deployment name")
    p_back.add_argument("--namespace", "-n", default="retail-store", help="Kubernetes namespace")
    p_back.add_argument("--expected-image", "-i", default=None, help="Expected image tag after rollback")

    # Subcommand: resources
    p_res = subparsers.add_parser("audit-resources", help="Audit container CPU/Memory requests & limits")
    p_res.add_argument("--namespace", "-n", default="retail-store", help="Kubernetes namespace")

    # Subcommand: report
    p_rep = subparsers.add_parser("report", help="Generate full platform diagnostic operational report")
    p_rep.add_argument("--namespace", "-n", default="retail-store", help="Kubernetes namespace")
    p_rep.add_argument("--output", "-o", default=None, help="Save report to file path")

    args = parser.parse_args()

    commands = {
        "cluster": cmd_cluster,
        "pods": cmd_pods,
        "deployments": cmd_deployments,
        "validate-rollout": cmd_rollout,
        "validate-rollback": cmd_rollback,
        "audit-resources": cmd_resources,
        "report": cmd_report,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
