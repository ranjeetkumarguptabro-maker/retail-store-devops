"""Pytest fixtures for Kubernetes cluster integration tests.

Automatically detects whether the python 'kubernetes' client is installed
and whether an active cluster (Minikube, kind, or remote EKS) is reachable.
If either is unavailable, gracefully skips tests marked with @pytest.mark.integration.
"""

import os
import sys
import pytest


def get_k8s_client_config():
    """Safely loads pip 'kubernetes' library bypassing local directory collision."""
    orig_path = sys.path[:]
    try:
        sys.path = [p for p in sys.path if p not in ("", ".", os.getcwd())]
        from kubernetes import client, config
        return client, config
    except (ImportError, AttributeError):
        return None, None
    finally:
        sys.path = orig_path


def is_cluster_reachable() -> bool:
    """Attempts to connect to Kubernetes API server and list namespaces."""
    client, config = get_k8s_client_config()
    if not client or not config:
        return False
    try:
        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()
        v1 = client.CoreV1Api()
        v1.list_namespace(limit=1, timeout_seconds=2)
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def k8s_clients():
    """Provides CoreV1Api and AppsV1Api if cluster is accessible; otherwise skips."""
    client, config = get_k8s_client_config()
    if not client or not config:
        pytest.skip(
            "Python 'kubernetes' package is not installed. Install via 'pip install -r automation/requirements.txt'."
        )
    if not is_cluster_reachable():
        pytest.skip(
            "Kubernetes cluster is not reachable. Launch Minikube or kind, or execute via 'scripts/run_integration_tests.sh'."
        )
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()
    return client.CoreV1Api(), client.AppsV1Api()


@pytest.fixture(scope="module")
def test_namespace(k8s_clients):
    """Creates a temporary test namespace and tears it down after tests complete."""
    client, _ = get_k8s_client_config()
    core_api, _ = k8s_clients
    ns_name = "retail-store-itest"

    try:
        core_api.create_namespace(
            body=client.V1Namespace(
                metadata=client.V1ObjectMeta(
                    name=ns_name,
                    labels={"environment": "integration-test", "managed-by": "pytest"},
                )
            )
        )
    except Exception:
        pass

    yield ns_name

    try:
        core_api.delete_namespace(name=ns_name, grace_period_seconds=0)
    except Exception:
        pass
