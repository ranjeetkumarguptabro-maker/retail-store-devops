# Python Platform Operations Automation Engine

The Retail Store DevOps platform includes an enterprise-grade Site Reliability Engineering (SRE) automation engine written in Python. It detects microservice failures, audits resource quotas and anomalies, verifies zero-downtime rolling updates, gates and executes safe rollbacks, exports real-time Prometheus telemetry, and generates structured incident reports.

---

## 1. Engine Architecture & Component Layout

```text
automation/
├── ops_cli.py                 # Unified SRE CLI entrypoint for platform operations
├── config/
│   ├── settings.yaml          # Operational thresholds, failure rules, remediation gates
│   └── __init__.py            # ConfigManager with environment variable overrides
├── collectors/                # Kubernetes API telemetry ingestion
│   ├── pod_collector.py       # Container states, exit codes, restart spikes, crash logs
│   ├── node_collector.py      # Node Ready conditions, disk/memory pressure, allocatable
│   ├── resource_collector.py  # CPU & Memory requests/limits normalization and parsing
│   └── event_collector.py     # Cluster and pod warning/error event correlation
├── analyzers/                 # Diagnostic and anomaly detection engines
│   ├── failure_detector.py    # PodFailureDetector: CrashLoop, ImagePull, OOM, Pending
│   ├── resource_analyzer.py   # Capacity exhaustion, missing limit audits, right-sizing
│   └── deployment_analyzer.py # Rollout progression and synthetic HTTP endpoint probing
├── remediation/               # Automated recovery and safety gates
│   ├── rollback.py            # RollbackManager with preflight checks and dry-run safety
│   └── recovery_validator.py  # Post-rollback replica stabilization and HTTP verification
├── reporting/                 # Operational reporting & telemetry
│   ├── json_report.py         # IncidentReportGenerator producing reports/cluster-diagnostics.json
│   └── metrics.py             # Prometheus metrics exporter (port 9102)
└── tests/                     # Automated unit test suite with 100% mocked Kubernetes API
    ├── test_collectors.py
    ├── test_failure_detector.py
    ├── test_analyzers.py
    ├── test_remediation.py
    ├── test_reporting.py
    ├── test_ops_cli.py
    ├── test_config.py
    └── test_automation.py
```

---

## 2. Six Core Operational Capabilities

### 1. Intelligent Pod Failure Detection
Identifies complex Kubernetes container failure modes:
- **CrashLoopBackOff**: Analyzes non-zero exit codes, retrieves the last 50 lines of container stderr, and recommends database or configuration checks.
- **ImagePullBackOff / ErrImagePull**: Flags missing image tags or ECR credentials.
- **OOMKilled**: Detects exit code 137 container terminations and generates memory limit increase recommendations.
- **Pending Pods**: Correlates pod scheduling failures with node CPU/memory exhaustion events.
- **Restart Spikes**: Alerts on flapping containers exceeding restart thresholds.

### 2. Resource Monitoring & Anomaly Detection
Audits cluster capacity against pod consumption:
- Enforces best-practice CPU and memory requests to prevent scheduler starvation.
- Detects missing memory limits to prevent noisy-neighbor OOM events.
- Flags worker nodes reporting `MemoryPressure` or `DiskPressure`.
- Calculates cluster-wide CPU and memory reservation percentages.

### 3. Automated Deployment Verification
- Tracks `updated_replicas` and `available_replicas` across rolling deployments.
- Verifies zero-downtime rollout progression without dropped connections.
- Executes synthetic HTTP health checks against service endpoints (`/`, `/health`, `/catalog/products`).

### 4. Safe Automated Rollback & Recovery
- **Pre-flight safety validation**: Verifies deployment history and confirms prior revisions exist before triggering rollbacks.
- **Dry-run simulation mode (`--dry-run`)**: Audits and outputs the exact recovery actions without modifying cluster state.
- **Authorization confirmation gate (`--confirm`)**: Protects production environments from unintended mutations.
- **Post-recovery validation**: Polls deployment stabilization and runs synthetic probes to confirm traffic recovery.

### 5. Prometheus Telemetry & Metrics Exporter
Exposes real-time SRE metrics on port 9102:
- `automation_checks_total{check_type="...", status="..."}`
- `automation_failures_total{service="...", failure_type="..."}`
- `deployment_rollbacks_total{deployment="...", status="..."}`
- `automation_execution_seconds{operation="..."}`
- Pre-configured Grafana dashboard located at [`monitoring/grafana/dashboards/platform-operations-automation.json`](../monitoring/grafana/dashboards/platform-operations-automation.json).

### 6. Incident Reporting
Consolidates diagnostic telemetry into structured JSON:
- Default output path: [`reports/cluster-diagnostics.json`](../reports/cluster-diagnostics.json).
- Includes ISO 8601 timestamps, service health matrices, root-cause statements, and suggested remediation steps.

---

## 3. Unified SRE CLI Commands Runbook

```bash
# 1. Diagnose cluster health and detect pod failures
python3 automation/ops_cli.py diagnose --namespace retail-store

# 2. Output diagnosis in raw JSON format
python3 automation/ops_cli.py diagnose --namespace retail-store --format json

# 3. Audit resource requests, limits, and cluster capacity
python3 automation/ops_cli.py monitor-resources --namespace retail-store

# 4. Verify deployment rollouts and test service endpoints
python3 automation/ops_cli.py verify-deployment --namespace retail-store \
  --service-urls '{"ui":"http://localhost:8888","catalog":"http://localhost:8081/catalog/products"}'

# 5. Simulate a deployment rollback (dry-run mode)
python3 automation/ops_cli.py rollback --deployment retail-store-cart --dry-run

# 6. Execute an authorized live deployment rollback
python3 automation/ops_cli.py rollback --deployment retail-store-cart --confirm

# 7. Start the Prometheus metrics scrape daemon
python3 automation/ops_cli.py export-metrics --port 9102
```

Sample CLI output for `diagnose`:
```text
============================================================
             RETAIL STORE CLUSTER DIAGNOSTICS               
============================================================
Namespace: retail-store

SERVICE HEALTH OVERVIEW:
  Ui           HEALTHY
  Catalog      HEALTHY
  Cart         CRASHLOOPBACKOFF
  Orders       HEALTHY
  Checkout     HEALTHY

INCIDENT ROOT CAUSE & REMEDIATION:
------------------------------------------------------------
Service: Cart
  Issue:       CrashLoopBackOff on container 'cart': Back-off 5m restarting failed container
  Remediation: Inspect application configuration, database connection strings, and fatal stack traces in pod logs. Verify liveness probes are not timing out.
  Pod Log Extract (retail-store-cart-999-abc):
    | Exception in thread 'main' java.lang.NullPointerException: DB connection failed
    |     at com.amazonaws.retailstore.cart.CartService.connect(CartService.java:42)

============================================================
[INFO] Comprehensive diagnostic report written to: reports/cluster-diagnostics.json
```

---

## 4. Automated CI/CD Testing & Quality Gates

The engine is integrated into GitHub Actions ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)):

```bash
# 1. Ruff linting
ruff check automation/

# 2. Unit testing with coverage analysis
pytest automation/tests --cov=automation --cov-report=term-missing
```
All unit tests mock the Kubernetes API client, ensuring fast, deterministic, and sandboxed test execution without requiring live cloud cluster connectivity.
