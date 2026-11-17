#!/usr/bin/env bash
# ==============================================================================
# run_integration_tests.sh
# Executes live Kubernetes cluster integration tests against kind or Minikube.
# ==============================================================================

set -euo pipefail

CLUSTER_NAME="retail-store-itest"
KIND_CONFIG_TEMP="/tmp/kind-itest-config.yaml"

echo "============================================================"
echo "    RETAIL STORE SRE AUTOMATION: CLUSTER INTEGRATION TESTS   "
echo "============================================================"

# Check if an existing cluster is reachable
if kubectl cluster-info >/dev/null 2>&1; then
    echo "[INFO] Existing Kubernetes cluster detected: $(kubectl config current-context)"
else
    echo "[INFO] No active cluster detected. Checking for 'kind' to launch a local test cluster..."
    if command -v kind >/dev/null 2>&1; then
        echo "[INFO] Provisioning local kind cluster '${CLUSTER_NAME}'..."
        cat <<EOF > "${KIND_CONFIG_TEMP}"
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
EOF
        kind create cluster --name "${CLUSTER_NAME}" --config "${KIND_CONFIG_TEMP}"
        trap 'kind delete cluster --name "${CLUSTER_NAME}"; rm -f "${KIND_CONFIG_TEMP}"' EXIT
    else
        echo "[ERROR] No Kubernetes cluster is reachable and 'kind' is not installed."
        echo "Please launch Minikube ('minikube start') or install kind ('brew install kind')."
        exit 1
    fi
fi

# Run pytest on integration test suite
echo "[INFO] Executing cluster integration tests with Pytest..."
python3 -m pytest automation/tests/integration/ -m integration -v

echo "============================================================"
echo "[SUCCESS] All Kubernetes cluster integration tests passed!"
echo "============================================================"
