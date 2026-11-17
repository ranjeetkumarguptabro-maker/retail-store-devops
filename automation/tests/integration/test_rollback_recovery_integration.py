"""Real cluster integration test for safe deployment rollback and post-recovery validation.

Deploys Revision 1 (healthy), upgrades to Revision 2 (broken), observes regression,
executes automated rollback via RollbackManager, and verifies stabilization via RecoveryValidator.
"""

import time
import pytest
from automation.remediation.rollback import RollbackManager
from automation.remediation.recovery_validator import RecoveryValidator
from automation.tests.integration.conftest import get_k8s_client_config


@pytest.mark.integration
def test_real_rollback_and_recovery(k8s_clients, test_namespace):
    core_api, apps_api = k8s_clients
    client, _ = get_k8s_client_config()
    dep_name = "integration-ui-rollback-test"

    # Revision 1: Healthy deployment
    dep_v1 = client.V1Deployment(
        metadata=client.V1ObjectMeta(
            name=dep_name,
            namespace=test_namespace,
            labels={"app.kubernetes.io/name": "ui"},
        ),
        spec=client.V1DeploymentSpec(
            replicas=1,
            revision_history_limit=10,
            selector=client.V1LabelSelector(match_labels={"app": "ui-rollback"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "ui-rollback"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="ui",
                            image="busybox:1.36",
                            command=["sleep", "3600"],
                        )
                    ]
                ),
            ),
        ),
    )

    apps_api.create_namespaced_deployment(namespace=test_namespace, body=dep_v1)

    try:
        # Wait for Revision 1 to become ready
        validator = RecoveryValidator(apps_api=apps_api, core_api=core_api, namespace=test_namespace)
        stab_v1 = validator.verify_service_stabilization(deployment_name=dep_name, timeout_seconds=20)
        assert stab_v1["stabilized"] is True, "Revision 1 failed to reach ready state"

        # Revision 2: Update with crashing container command
        dep_v2 = apps_api.read_namespaced_deployment(name=dep_name, namespace=test_namespace)
        dep_v2.spec.template.spec.containers[0].command = ["/bin/sh", "-c"]
        dep_v2.spec.template.spec.containers[0].args = ["echo 'regression fault' >&2; exit 1"]
        apps_api.patch_namespaced_deployment(name=dep_name, namespace=test_namespace, body=dep_v2)

        time.sleep(4)

        # Execute safe rollback using RollbackManager
        rollback_mgr = RollbackManager(apps_api=apps_api, namespace=test_namespace, dry_run=False)
        preflight = rollback_mgr.validate_preflight(dep_name)
        assert preflight["can_rollback"] is True

        rollback_res = rollback_mgr.execute_rollback(deployment_name=dep_name, confirm=True)
        assert rollback_res["success"] is True

        # Verify post-recovery stabilization
        recovery = validator.verify_service_stabilization(deployment_name=dep_name, timeout_seconds=30)
        assert recovery["stabilized"] is True, "Deployment failed to stabilize after rollback"
        assert recovery["replicas_available"] >= 1

    finally:
        try:
            apps_api.delete_namespaced_deployment(name=dep_name, namespace=test_namespace)
        except Exception:
            pass
