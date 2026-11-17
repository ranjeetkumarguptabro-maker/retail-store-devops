"""Real cluster integration test for failed deployment detection (ImagePullBackOff).

Deploys a deployment with a non-existent container image tag, verifies that the
Kubernetes API transitions it to ImagePullBackOff / ErrImagePull, and validates that
the DeploymentAnalyzer and FailureDetector classify the deployment as unready.
"""

import time
import pytest
from automation.collectors.pod_collector import PodCollector
from automation.analyzers.deployment_analyzer import DeploymentAnalyzer
from automation.analyzers.failure_detector import PodFailureDetector
from automation.tests.integration.conftest import get_k8s_client_config


@pytest.mark.integration
def test_real_failed_deployment_image_pull_backoff(k8s_clients, test_namespace):
    core_api, apps_api = k8s_clients
    client, _ = get_k8s_client_config()
    dep_name = "integration-orders-bad-image"

    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(
            name=dep_name,
            namespace=test_namespace,
            labels={"app.kubernetes.io/name": "orders", "test": "bad-image"},
        ),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels={"app": "orders-bad-img"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "orders-bad-img"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="orders",
                            image="retail-store/orders:nonexistent-tag-v9999",
                        )
                    ],
                ),
            ),
        ),
    )

    apps_api.create_namespaced_deployment(namespace=test_namespace, body=deployment)

    try:
        pod_collector = PodCollector(core_api=core_api, namespace=test_namespace)
        dep_analyzer = DeploymentAnalyzer(apps_api=apps_api, namespace=test_namespace)
        detector = PodFailureDetector()

        observed_image_error = False

        for _ in range(15):
            time.sleep(2)
            pods = pod_collector.collect()
            matching = [p for p in pods if dep_name in p.get("name", "")]
            if matching:
                p = matching[0]
                diag = detector.analyze_pod(p)
                if diag["status"] in ("IMAGEPULLBACKOFF", "ERRIMAGEPULL") or any(
                    "Image" in r for r in p.get("error_reasons", [])
                ):
                    observed_image_error = True
                    break

        assert observed_image_error is True, "Pod did not enter ImagePullBackOff within timeout"

        # Check deployment analyzer reports readiness failure
        dep_res = dep_analyzer.analyze_deployments()
        assert dep_res["all_deployments_ready"] is False
        assert dep_res["deployments"][dep_name]["is_ready"] is False

    finally:
        try:
            apps_api.delete_namespaced_deployment(name=dep_name, namespace=test_namespace)
        except Exception:
            pass
