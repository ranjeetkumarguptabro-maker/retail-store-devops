"""Unit tests for the Intelligent Pod Failure Detector."""

from automation.analyzers.failure_detector import PodFailureDetector


def test_failure_detector_healthy_pod():
    detector = PodFailureDetector()
    pod = {
        "name": "retail-store-ui-6789-xyz",
        "service": "ui",
        "phase": "Running",
        "total_restarts": 0,
        "containers": [{"name": "ui", "state": "running", "reason": "Running", "exit_code": None, "ready": True}],
    }
    diag = detector.analyze_pod(pod)
    assert diag["is_healthy"] is True
    assert diag["status"] == "HEALTHY"
    assert "healthy and running" in diag["root_cause"]


def test_failure_detector_crashloop():
    detector = PodFailureDetector()
    pod = {
        "name": "retail-store-cart-999-abc",
        "service": "cart",
        "phase": "Running",
        "total_restarts": 4,
        "containers": [
            {
                "name": "cart",
                "state": "waiting",
                "reason": "CrashLoopBackOff",
                "message": "Back-off 5m restarting failed container",
                "exit_code": None,
                "ready": False,
            }
        ],
        "logs": "Exception in thread 'main' java.lang.NullPointerException: DB connection failed",
    }
    diag = detector.analyze_pod(pod)
    assert diag["is_healthy"] is False
    assert diag["status"] == "CRASHLOOPBACKOFF"
    assert "CrashLoop" in diag["root_cause"]
    assert "database connection" in diag["remediation"].lower()
    assert "DB connection failed" in diag["logs_sample"]


def test_failure_detector_image_pull_backoff():
    detector = PodFailureDetector()
    pod = {
        "name": "retail-store-orders-111-xyz",
        "service": "orders",
        "phase": "Running",
        "total_restarts": 0,
        "containers": [
            {
                "name": "orders",
                "state": "waiting",
                "reason": "ImagePullBackOff",
                "message": "Back-off pulling image 'invalid-repo/orders:v99'",
                "exit_code": None,
                "ready": False,
            }
        ],
    }
    diag = detector.analyze_pod(pod)
    assert diag["is_healthy"] is False
    assert diag["status"] == "IMAGEPULLBACKOFF"
    assert "image" in diag["remediation"].lower()


def test_failure_detector_oom_killed():
    detector = PodFailureDetector()
    pod = {
        "name": "retail-store-catalog-222-xyz",
        "service": "catalog",
        "phase": "Running",
        "total_restarts": 2,
        "containers": [
            {
                "name": "catalog",
                "state": "terminated",
                "reason": "OOMKilled",
                "message": "Container killed by OOM killer",
                "exit_code": 137,
                "ready": False,
            }
        ],
    }
    diag = detector.analyze_pod(pod)
    assert diag["is_healthy"] is False
    assert diag["status"] == "OOMKILLED"
    assert "resources.limits.memory" in diag["remediation"]


def test_failure_detector_pending_pod():
    detector = PodFailureDetector()
    pod = {
        "name": "retail-store-checkout-333-xyz",
        "service": "checkout",
        "phase": "Pending",
        "total_restarts": 0,
        "containers": [],
    }
    events = [
        {
            "object_name": "retail-store-checkout-333-xyz",
            "reason": "FailedScheduling",
            "message": "0/3 nodes available: 3 Insufficient memory.",
        }
    ]
    diag = detector.analyze_pod(pod, events=events)
    assert diag["is_healthy"] is False
    assert diag["status"] == "PENDING"
    assert "Insufficient memory" in diag["root_cause"]


def test_failure_detector_restart_spike():
    detector = PodFailureDetector(restart_spike_threshold=5)
    pod = {
        "name": "retail-store-ui-flapping",
        "service": "ui",
        "phase": "Running",
        "total_restarts": 7,
        "containers": [{"name": "ui", "state": "running", "reason": "Running", "exit_code": None, "ready": True}],
    }
    diag = detector.analyze_pod(pod)
    assert diag["is_healthy"] is False
    assert diag["status"] == "RESTARTSPIKE"
    assert "restarts" in diag["remediation"].lower()


def test_diagnose_services_aggregate_and_cli():
    detector = PodFailureDetector()
    pods = [
        {
            "name": "retail-store-ui-123",
            "service": "ui",
            "phase": "Running",
            "total_restarts": 0,
            "containers": [{"name": "ui", "state": "running", "reason": "Running", "ready": True}],
        },
        {
            "name": "retail-store-catalog-123",
            "service": "catalog",
            "phase": "Running",
            "total_restarts": 0,
            "containers": [{"name": "catalog", "state": "running", "reason": "Running", "ready": True}],
        },
        {
            "name": "retail-store-cart-123",
            "service": "cart",
            "phase": "Running",
            "total_restarts": 8,
            "containers": [
                {"name": "cart", "state": "waiting", "reason": "CrashLoopBackOff", "ready": False, "message": "Crash"}
            ],
            "logs": "Fatal DB Error",
        },
        {
            "name": "retail-store-orders-123",
            "service": "orders",
            "phase": "Running",
            "total_restarts": 0,
            "containers": [{"name": "orders", "state": "running", "reason": "Running", "ready": True}],
        },
        {
            "name": "retail-store-checkout-123",
            "service": "checkout",
            "phase": "Running",
            "total_restarts": 0,
            "containers": [{"name": "checkout", "state": "running", "reason": "Running", "ready": True}],
        },
    ]

    report = detector.diagnose_services(pods)
    assert report["cluster_healthy"] is False
    assert report["services"]["ui"]["status"] == "HEALTHY"
    assert report["services"]["catalog"]["status"] == "HEALTHY"
    assert report["services"]["cart"]["status"] == "CRASHLOOPBACKOFF"
    assert report["services"]["orders"]["status"] == "HEALTHY"
    assert report["services"]["checkout"]["status"] == "HEALTHY"

    cli_text = detector.format_cli_output(report, namespace="retail-store")
    assert "RETAIL STORE CLUSTER DIAGNOSTICS" in cli_text
    assert "Namespace: retail-store" in cli_text
    assert "Ui           HEALTHY" in cli_text
    assert "Cart         CRASHLOOPBACKOFF" in cli_text
    assert "Service: Cart" in cli_text
    assert "Fatal DB Error" in cli_text
