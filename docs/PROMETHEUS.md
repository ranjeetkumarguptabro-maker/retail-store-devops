# Phase 7: Prometheus Monitoring Architecture

This guide details the Prometheus metrics scraping configuration, service annotations, and metric targets for the **AWS Retail Store Sample Application**.

---

## 1. Scrape Architecture

Prometheus is installed via the official Helm chart (`prometheus-community/prometheus`) with custom values located in [`monitoring/prometheus/values.yaml`](../monitoring/prometheus/values.yaml).

```
+------------------------------------+
|  Prometheus Server                 |
+------------------+-----------------+
                   |
     +-------------+-------------+---------------------+
     | (Every 15s)               | (Every 15s)         | (Every 15s)
     v                           v                     v
+------------------+     +------------------+   +----------------------+
| UI / Cart /      |     | Catalog /        |   | Kube-State-Metrics   |
| Orders           |     | Checkout         |   |                      |
| (Spring Actuator)|     | (Gin / NestJS)   |   | Pod phases, restarts,|
| /actuator/prom   |     | /metrics         |   | deployments, nodes   |
+------------------+     +------------------+   +----------------------+
```

---

## 2. Pod Relabeling & Discovery Rules

The Prometheus scrape configuration discovers Pods dynamically using Kubernetes annotations:
- `prometheus.io/scrape: "true"`: Opts the Pod into automatic scraping.
- `prometheus.io/path`: Defaults to `/actuator/prometheus` (Spring Boot) or `/metrics` (Go / Node.js).
- `prometheus.io/port`: Defaults to port `8080`.

---

## 3. Helm Installation Runbook

```bash
# 1. Add Prometheus Helm Repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# 2. Install Prometheus into 'monitoring' namespace
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install prometheus prometheus-community/prometheus \
  --namespace monitoring \
  -f monitoring/prometheus/values.yaml

# 3. Port-Forward Prometheus Web UI
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
```
Then visit `http://localhost:9090` to explore metrics.
