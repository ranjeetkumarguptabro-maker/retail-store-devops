# Phase 6: GitHub Actions CI/CD Pipeline & Security Scanning

This guide documents the automated Continuous Integration, Vulnerability Scanning (Trivy), and Continuous Deployment (Amazon EKS) pipeline for the **AWS Retail Store Sample Application**.

---

## 1. Pipeline Architecture

```
Push to main / PR
        |
        v
+-----------------------+
|  Job 1: CI & Testing  |  --> Test Go Catalog API & Java Maven UI
+-----------+-----------+
            |
            v
+-----------------------+
|  Job 2: Trivy Scan    |  --> Filesystem scan & Container image CVE analysis
+-----------+-----------+
            | (On Merge to main)
            v
+-----------------------+
|  Job 3: AWS OIDC Auth |  --> Zero long-lived AWS keys; assumes temporary IAM role
+-----------+-----------+
            |
            v
+-----------------------+
|  Job 4: EKS Deploy    |  --> Apply manifests & verify rollout status
+-----------------------+
```

---

## 2. Security Best Practices Implemented

1. **Zero Long-Lived AWS Keys:** Uses GitHub Actions OpenID Connect (OIDC) federation (`aws-actions/configure-aws-credentials`) to exchange a short-lived OIDC token for temporary AWS STS credentials.
2. **Container Security Auditing:** Uses Aqua Security's **Trivy** to scan containers for `CRITICAL` and `HIGH` CVEs prior to cloud deployment.
3. **Deployment Gates:** Automatic cancellation if unit tests fail or if rollout conditions timeout.
4. **Rollout Verification:** Validates that all Pods transition to the `Running` state and pass Readiness Probes (`kubectl rollout status`) before marking the deployment successful.

---

## 3. Required GitHub Secrets and Variables

Configure under **GitHub Repository $\rightarrow$ Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions**:

### Secrets:
- `AWS_ROLE_ARN`: ARN of the IAM role configured with an OIDC trust policy for this GitHub repository.

### Variables:
- `AWS_REGION`: e.g. `us-east-1`
- `EKS_CLUSTER_NAME`: e.g. `dev-retail-store`
