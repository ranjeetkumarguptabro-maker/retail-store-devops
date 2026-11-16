# Phase 9: Python Platform Operations Automation Engine

This guide details the Python-based platform operations automation engine developed to monitor cluster health, audit container resource requests/limits, detect pod crash loops, validate rolling updates and rollbacks, and generate structured diagnostic reports.

---

## 1. Engine Architecture & Tool Suite

Located in [`automation/`](../automation/):

```
automation/
├── ops_cli.py               # Master CLI entrypoint for platform SRE operations
├── cluster_health.py        # Inspects API connectivity and node Ready conditions
├── pod_health.py            # Identifies CrashLoopBackOff, ImagePullBackOff, high restarts
├── deployment_check.py      # Validates deployment replicas (desired vs ready vs available)
├── resource_monitor.py      # Audits container CPU/Memory requests & limits to prevent OOMKills
├── rollout_validator.py     # Verifies rolling update progress and zero-downtime completion
├── rollback_validator.py    # Tracks rollback execution and validates traffic recovery
├── generate_report.py       # Master diagnostic reporter outputting structured JSON
└── tests/
    └── test_automation.py   # Full unit test suite using unittest & mocks (7/7 tests passing)
```

---

## 2. Unified CLI Usage Runbook (`ops_cli.py`)

```bash
# Display CLI commands
python3 automation/ops_cli.py --help

# 1. Inspect Node Readiness
python3 automation/ops_cli.py cluster

# 2. Audit Pod Health & Crash Detection
python3 automation/ops_cli.py pods --namespace retail-store

# 3. Check Deployment Replicas
python3 automation/ops_cli.py deployments --namespace retail-store

# 4. Audit Container Resource Limits
python3 automation/ops_cli.py audit-resources --namespace retail-store

# 5. Validate Zero-Downtime Rollout
python3 automation/ops_cli.py validate-rollout --deployment ui --namespace retail-store

# 6. Validate Rollback Recovery
python3 automation/ops_cli.py validate-rollback --deployment ui --namespace retail-store

# 7. Generate & Export Master Diagnostic JSON Report
python3 automation/ops_cli.py report --namespace retail-store --output report.json
```

---

## 3. Automated Test Suite

Run unit tests:
```bash
python3 -m unittest automation/tests/test_automation.py -v
```
Output:
```text
test_cluster_health_all_ready ... ok
test_deployment_check_all_healthy ... ok
test_generate_platform_report ... ok
test_pod_health_detects_crashloop ... ok
test_resource_monitor_audit ... ok
test_rollback_validator_success ... ok
test_rollout_validator_completed ... ok
----------------------------------------------------------------------
Ran 7 tests in 0.003s - OK
```
