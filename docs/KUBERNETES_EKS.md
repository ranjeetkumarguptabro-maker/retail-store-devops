# Phase 3 & 5: Kubernetes & Amazon EKS Architecture Guide

This guide details the Kubernetes orchestration architecture, resource configuration, health probing, autoscaling, and deployment operations for the **AWS Retail Store Sample Application** across both local Minikube and Amazon EKS.

---

## 1. Kubernetes Architecture Overview

The application deploys into an isolated namespace (`retail-store`):

```
                        +----------------------------+
                        |   Kubernetes Ingress (ALB) |
                        +--------------+-------------+
                                       |
                                       v
                        +----------------------------+
                        |  UI Service (LoadBalancer) |
                        +--------------+-------------+
                                       |
                                       v
         +-----------------------------+-----------------------------+
         |                             |                             |
         v                             v                             v
+------------------+          +------------------+          +------------------+
| Catalog Service  |          |   Cart Service   |          | Checkout Service |
| (ClusterIP:8080) |          | (ClusterIP:8080) |          | (ClusterIP:8080) |
+------------------+          +------------------+          +--------+---------+
                                                                     |
                                                                     v
                                                            +------------------+
                                                            |  Orders Service  |
                                                            | (ClusterIP:8080) |
                                                            +------------------+
```

---

## 2. Resource Specifications & Health Probes

| Component | Replicas | CPU Req / Limit | Memory Req / Limit | Readiness Probe | Liveness Probe |
|---|---|---|---|---|---|
| **UI** | 2 | 250m / 1000m | 512Mi / 1024Mi | `/actuator/health` | `/actuator/health` |
| **Catalog** | 2 | 100m / 500m | 64Mi / 256Mi | `/health` | `/health` |
| **Cart** | 2 | 150m / 500m | 256Mi / 512Mi | `/actuator/health` | `/actuator/health` |
| **Checkout** | 2 | 100m / 500m | 128Mi / 384Mi | `/health` | `/health` |
| **Orders** | 2 | 150m / 500m | 256Mi / 512Mi | `/actuator/health` | `/actuator/health` |

---

## 3. High Availability & Rolling Updates

Every Deployment is configured with zero-downtime rolling update parameters:
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```
This guarantees that Kubernetes starts and validates a new Pod before terminating any existing Pod.

### Horizontal Pod Autoscaling (HPA)
The UI service includes an HPA (`ui-hpa`) that automatically scales replicas between 2 and 5 when target CPU utilization exceeds 70%.

---

## 4. Local Deployment Runbook (Minikube / Kind)

```bash
# 1. Apply namespace
kubectl apply -f kubernetes/namespace.yaml

# 2. Apply configuration and secrets
kubectl apply -f kubernetes/config/configmap.yaml
kubectl apply -f kubernetes/config/secrets.example.yaml

# 3. Apply microservices deployments
kubectl apply -f kubernetes/catalog/deployment.yaml
kubectl apply -f kubernetes/cart/deployment.yaml
kubectl apply -f kubernetes/checkout/deployment.yaml
kubectl apply -f kubernetes/orders/deployment.yaml
kubectl apply -f kubernetes/ui/deployment.yaml

# 4. Watch rollout status
kubectl rollout status deployment/ui -n retail-store
kubectl get pods -n retail-store
kubectl get svc -n retail-store
```

---

## 5. Amazon EKS Connection & Deployment

When provisioning on AWS EKS:
```bash
# 1. Update local kubeconfig from AWS
aws eks update-kubeconfig --name retail-store-cluster --region us-east-1

# 2. Verify cluster nodes
kubectl get nodes -o wide

# 3. Apply manifests with Ingress
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/config/
kubectl apply -f kubernetes/catalog/
kubectl apply -f kubernetes/cart/
kubectl apply -f kubernetes/checkout/
kubectl apply -f kubernetes/orders/
kubectl apply -f kubernetes/ui/
kubectl apply -f kubernetes/ingress/
```
