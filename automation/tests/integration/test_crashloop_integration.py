"""Real cluster integration test for CrashLoopBackOff detection and incident lifecycle.

Deploys a container configured to fail on startup, observes Kubernetes transition
it into CrashLoopBackOff, extracts actual container stderr logs via the Kubernetes API,
and validates that the failure detector isolates the root cause.
"""

import time
import pytest
from automation.collectors.pod_collector import PodCollector
from automation.analyzers.failure_detector import PodFailureDetector
from automation.remediation.incident_lifecycle import IncidentLifecycleOrchestrator
from automation.tests.integration.conftest import get_k8s_client_config


@pytest.mark.integration
def test_real_crashloop_detection_and_lifecycle(k8s_clients, test_namespace, tmp_path):
    core_api, apps_api = k8s_clients
    client, _ = get_k8s_client_config()
    dep_name = "integration-cart-crashing"

    # Define a deployment that immediately exits with error code 1
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(
            name=dep_name,
            namespace=test_namespace,
            labels={"app.kubernetes.io/name": "cart", "test": "crashloop"},
        ),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels={"app": "cart-crash"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "cart-crash"}),
                spec=client.V1PodSpec(
                    restart_policy="Always",
                    containers=[
                        client.V1Container(
                            name="cart",
                            image="busybox:1.36",
                            command=["/bin/sh", "-c"],
                            args=["echo 'FATAL: database connection refused to redis-cart:6379' >&2; exit 1"],
                        )
                    ],
                ),
            ),
        ),
    )

    # 1. Create failing deployment in cluster
    apps_api.create_namespaced_deployment(namespace=test_namespace, body=deployment)

    try:
        # Wait up to 30 seconds for pod to crash and restart
        pod_collector = PodCollector(core_api=core_api, namespace=test_namespace)
        detector = PodFailureDetector()

        observed_crashloop = False
        captured_logs = ""

        for _ in range(15):
            time.sleep(2)
            pods = pod_collector.collect()
            matching = [p for p in pods if dep_name in p.get("name", "")]
            if matching:
                p = matching[0]
                diag = detector.analyze_pod(p)
                if diag.get("status") in ("CRASHLOOPBACKOFF", "ERROR") or p.get("total_restarts", 0) > 0:
                    observed_crashloop = True
                    captured_logs = p.get("logs", "")
                    break

        assert observed_crashloop is True, "Pod did not enter CrashLoopBackOff or restart within timeout"
        assert "FATAL: database connection refused" in captured_logs, "Failed to capture stderr logs from crashing pod"

        # 2. Test Incident Lifecycle Orchestrator against this real failure
        orchestrator = IncidentLifecycleOrchestrator(
            core_api=core_api,
            apps_api=apps_api,
            namespace=test_namespace,
            output_dir=str(tmp_path),
        )

        report = orchestrator.run_lifecycle(
            target_service="cart",
            auto_approve=False,
            dry_run=True,
        )

        assert report["status"] == "DRY_RUN_COMPLETED"
        assert report["target_service"] == "cart"
        assert "CrashLoop" in report["diagnosis"]["root_cause"] or "CRASHLOOPBACKOFF" in report["diagnosis"]["failure_type"]
        assert "database" in report["diagnosis"]["root_cause"].lower() or "database" in str(report["evidence"]).lower()

    finally:
        # Cleanup deployment
        try:
            apps_api.delete_namespaced_deployment(name=dep_name, namespace=test_namespace)
        except Exception:
            pass
