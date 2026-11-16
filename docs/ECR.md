# Phase 5: Amazon Elastic Container Registry (ECR) Management

This guide details the creation, authentication, multi-architecture image building, tagging strategy, and lifecycle management for Amazon ECR repositories.

---

## 1. Registry Tagging Strategy & Immutability

1. **Tag Immutability:** Enabled on production repositories to prevent tag overwriting.
2. **Immutable Identifier:** Every release is tagged with the Git commit SHA (e.g. `sha-90d8ab2`), ensuring complete traceability between Git commits and deployed containers.
3. **Semantic Versioning:** Release candidates are tagged with SemVer tags (e.g. `v1.0.0`).

---

## 2. Authentication Runbook

Authenticate Docker CLI with Amazon ECR:

```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
```

---

## 3. Building, Tagging & Pushing Multi-Arch Images

```bash
# Set variables
ACCOUNT_ID="123456789012"
REGION="us-east-1"
REPO_PREFIX="dev-retail-store"
COMMIT_SHA=$(git rev-parse --short HEAD)

# Build and Push Storefront UI image
docker buildx build \
  --platform linux/arm64,linux/amd64 \
  -t ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_PREFIX}/ui:${COMMIT_SHA} \
  -t ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_PREFIX}/ui:latest \
  --push \
  application/src/ui/
```

---

## 4. Image Lifecycle Management & Cost Optimization

Every repository is managed with an ECR Lifecycle Policy expiring untagged images or images older than 30 days, keeping cloud storage costs under \$1.00/month.
