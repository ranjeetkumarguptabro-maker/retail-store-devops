# Phase 8: Grafana Operational Dashboards

This document details the operational dashboards created for visualizing microservices traffic, error rates, Kubernetes pod lifecycles, and cluster health for the **AWS Retail Store Sample Application**.

---

## 1. Dashboard Catalog

Exported dashboard JSON definitions are stored under [`monitoring/grafana/dashboards/`](../monitoring/grafana/dashboards/):

1. **Application Overview (`application-overview.json`):**
   - **Throughput:** `sum(rate(http_server_requests_seconds_count[1m])) by (uri)`
   - **HTTP Error Rate:** `sum(rate(http_server_requests_seconds_count{status=~"5.."}[1m])) by (app)`
   - **P95 Latency:** `histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket[5m])) by (le))`
2. **Kubernetes Overview (`kubernetes-overview.json`):**
   - Running pods vs Failed / Pending pods (`kube_pod_status_phase`)
   - Pod restart rate and crash backoffs (`increase(kube_pod_container_status_restarts_total[1h])`)
   - Container CPU and Memory working set usage.
3. **Infrastructure Overview (`infrastructure-overview.json`):**
   - Node readiness (`kube_node_status_condition{condition="Ready"}`)
   - Allocatable CPU cores and memory limits across worker nodes.

---

## 2. Helm Installation & Dashboard Import

```bash
# 1. Add Grafana Helm Repository
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# 2. Install Grafana
helm upgrade --install grafana grafana/grafana \
  --namespace monitoring \
  --set adminPassword="admin" \
  --set service.type=ClusterIP

# 3. Port-Forward Grafana UI
kubectl port-forward -n monitoring svc/grafana 3000:80
```
- Open `http://localhost:3000` (User: `admin`, Password: `admin`).
- Add Prometheus Data Source (`http://prometheus-server.monitoring.svc.cluster.local`).
- Import JSON files from `monitoring/grafana/dashboards/`.
