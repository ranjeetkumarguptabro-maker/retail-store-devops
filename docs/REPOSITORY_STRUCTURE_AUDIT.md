# Repository Structure & Boundary Audit: Upstream vs. Custom DevOps Implementation

> **Date:** November 16, 2026  
> **Repository:** `ranjeetkumarguptabro-maker/retail-store-devops`  
> **Target Upstream Application:** [AWS Retail Store Sample App (`aws-containers/retail-store-sample-app`)](https://github.com/aws-containers/retail-store-sample-app)  
> **Status:** Completed — Pending User Review

---

## 1. Executive Summary

This audit assesses the physical and logical structure of the `retail-store-devops` repository. 

A central challenge in real-world platform and DevOps engineering portfolios is handling complex multi-service applications: engineering hiring teams want to see an authentic, polyglot application running in production rather than a trivial "Hello World" container, but they must also be able to immediately distinguish **original third-party application code** from the engineer's **custom infrastructure, automation, CI/CD, and orchestration implementations**.

This repository cleanly divides into two distinct layers:
1. **Upstream Application Layer (`application/`)**: The complete upstream source tree of the AWS Retail Store Sample Application, preserved intact for authentic compilation, testing, and microservice behavior.
2. **Custom DevOps Platform Engineering Layer (Root Directory)**: The custom-designed infrastructure as code (Terraform), container orchestration (Docker Compose & Kubernetes manifests), automated CI/CD pipelines (GitHub Actions & Trivy), observability stack (Prometheus & Grafana), and SRE operations automation engine (Python).

This report catalogs all files in both layers, audits overlaps and duplications, confirms microservice integration, and outlines clear recommendations to ensure complete clarity for technical recruiters and hiring managers.

---

## 2. Upstream Artifacts Inventory (`application/`)

The `application/` directory is an exact preservation of the upstream `aws-containers/retail-store-sample-app` repository (licensed under MIT-0). It provides the polyglot microservice codebase along with AWS workshop demonstration artifacts.

```
application/
├── .github/                      # Upstream AWS repository automation (NOT used by root CI/CD)
│   ├── actions/                  # Upstream composite actions (setup-docker, setup-env)
│   └── workflows/                # Upstream release-please, e2e kind tests, PR checks
├── docs/                         # Upstream application architectural diagrams & feature docs
├── oss/                          # Upstream Open Source Review Toolkit (ORT) compliance
├── samples/                      # Sample product catalog JSON data and product images
├── scripts/                      # Upstream developer helper scripts (license headers, kind e2e)
├── src/                          # Polyglot Microservices Source Code
│   ├── ui/                       # Storefront UI (Java 21 / Spring Boot 3.5 + Thymeleaf)
│   │   ├── Dockerfile, pom.xml, chart/, docker-compose.yml, src/
│   ├── catalog/                  # Catalog Service (Go Gin REST API)
│   │   ├── Dockerfile, go.mod, chart/, docker-compose.yml, main.go, controller/, model/
│   ├── cart/                     # Cart Service (Java 21 / Spring Boot 3.5)
│   │   ├── Dockerfile, pom.xml, chart/, docker-compose.yml, src/
│   ├── checkout/                 # Checkout Service (Node.js 20 / NestJS 11 + TypeScript)
│   │   ├── Dockerfile, package.json, chart/, docker-compose.yml, src/
│   ├── orders/                   # Orders Service (Java 21 / Spring Boot 3.5)
│   │   ├── Dockerfile, pom.xml, chart/, docker-compose.yml, src/
│   ├── load-generator/           # Artillery / Node.js test traffic generation tool
│   ├── e2e/                      # Cypress end-to-end browser test suite
│   └── app/                      # Upstream aggregation module
│       ├── chart/                # Upstream umbrella Helm chart
│       ├── docker-compose.yml    # Upstream compose include file
│       ├── docker-compose.tracing.yml
│       ├── helmfile.yaml         # Upstream Helmfile definition
│       ├── helmfile.slim.yaml
│       └── Tiltfile              # Upstream local Tilt development configuration
├── terraform/                    # Upstream AWS Workshop Blueprints (NOT used by root IaC)
│   ├── ecs/                      # AWS ECS Fargate workshop blueprint
│   ├── eks/                      # AWS EKS workshop blueprints (default and minimal)
│   ├── apprunner/                # AWS App Runner workshop blueprint
│   └── lib/                      # Shared workshop modules (vpc, istio, adot, rds, dynamodb)
├── nx.json, package.json         # Upstream Nx monorepo toolchain configuration
├── yarn.lock, lefthook.yml       # Upstream git hook & package manager configurations
└── README.md, LICENSE            # Upstream repository metadata
```

---

## 3. Custom Platform Engineering Inventory (Root Repository)

All platform engineering, cloud infrastructure, container orchestration, CI/CD, observability, and operational automation authored for this project live strictly in the root repository directories:

```
retail-store-devops/
│
├── .github/workflows/            # Custom Enterprise CI/CD Pipeline
│   ├── ci.yml                    # Multi-service build, unit test & compose validation
│   ├── security.yml              # Trivy IaC config scanner & container CVE audit
│   └── deploy.yml                # PyYAML syntax validation, AWS OIDC auth & EKS rollout
│
├── automation/                   # Custom Python SRE Operations Automation Engine
│   ├── ops_cli.py                # Unified CLI entrypoint for cluster operations
│   ├── cluster_health.py         # Node readiness, condition checks, and API latency
│   ├── pod_health.py             # CrashLoopBackOff, restart spikes, and OOMKilled detection
│   ├── deployment_check.py       # Rollout progression & replica availability validator
│   ├── resource_monitor.py       # Pod/Node CPU & memory utilization threshold monitor
│   ├── rollout_validator.py      # Automated deployment revision progression validator
│   ├── rollback_validator.py     # Automated rollback triggers & post-rollback health checks
│   ├── generate_report.py        # Master structured JSON health diagnostic generator
│   ├── requirements.txt          # Python dependencies (kubernetes client, pyyaml)
│   └── tests/test_automation.py  # Comprehensive unit test suite with 100% test pass rate
│
├── docker/                       # Custom Container Orchestration
│   └── docker-compose.yml        # Unified 5-service local mesh with healthchecks & M3/ARM64 support
│
├── kubernetes/                   # Custom Production Kubernetes Manifests (Vanilla Declarative)
│   ├── namespace.yaml            # Dedicated 'retail-store' namespace
│   ├── config/                   # Decoupled ConfigMaps and Secret templates
│   │   ├── configmap.yaml
│   │   └── secrets.example.yaml
│   ├── ui/deployment.yaml        # UI Deployment, LoadBalancer Service, HorizontalPodAutoscaler
│   ├── catalog/deployment.yaml   # Catalog Go API Deployment, ClusterIP Service, HPA
│   ├── cart/deployment.yaml      # Cart Java API Deployment, ClusterIP Service, HPA
│   ├── checkout/deployment.yaml  # Checkout NestJS API Deployment, ClusterIP Service, HPA
│   ├── orders/deployment.yaml    # Orders Java API Deployment, ClusterIP Service, HPA
│   └── ingress/ingress.yaml      # Ingress definition for AWS ALB / Nginx Controller
│
├── terraform/                    # Custom Modular AWS Infrastructure as Code
│   ├── environments/dev/         # Dev environment root caller module
│   │   ├── main.tf, variables.tf, outputs.tf, terraform.tfvars.example
│   └── modules/                  # Reusable, decoupled Terraform modules
│       ├── networking/           # VPC, 3 public + 3 private subnets, NAT Gateway, IGW
│       ├── iam/                  # EKS cluster role, node role, OIDC provider, least-privilege
│       ├── ecr/                  # 5 private ECR repos with KMS encryption & lifecycle rules
│       └── eks/                  # EKS 1.29 cluster, managed node groups, KMS secrets encryption
│
├── monitoring/                   # Observability & Metrics Stack
│   ├── prometheus/values.yaml    # Production Helm values for Prometheus + KSM + Alerting
│   └── grafana/dashboards/       # Custom operational dashboards
│       ├── application-overview.json
│       ├── kubernetes-overview.json
│       └── infrastructure-overview.json
│
├── docs/                         # Technical Architecture & Operations Runbooks
│   ├── SOURCE_CODE_AUDIT.md      # Codebase audit & polyglot architecture analysis
│   ├── LOCAL_SETUP.md            # Local developer workflow and native testing guide
│   ├── DOCKER.md                 # Docker compose mesh & containerization guide
│   ├── KUBERNETES_EKS.md         # Kubernetes manifests, rolling updates, HPA & EKS runbook
│   ├── TERRAFORM_AWS.md          # Modular Terraform IaC, IAM least-privilege & cost guide
│   ├── ECR.md                    # ECR registry, KMS encryption & image management
│   ├── GITHUB_ACTIONS_CICD.md    # CI/CD, AWS OIDC federation & Trivy security scanning
│   ├── PROMETHEUS.md             # Prometheus metrics scraping & Kube-State-Metrics setup
│   ├── GRAFANA.md                # Grafana operational dashboards & alert thresholds
│   ├── PYTHON_AUTOMATION.md      # SRE operations engine design, CLI & test suite
│   ├── FAILURE_TESTING.md        # Chaos engineering, failure injection & recovery runbook
│   └── REPOSITORY_STRUCTURE_AUDIT.md # (This document)
│
├── README.md                     # Comprehensive project showcase & architecture documentation
├── .env.example                  # Environment variable configuration template
└── .gitignore                    # Git ignore file excluding build artifacts & tfstate
```

---

## 4. Duplication & Overlap Analysis

| Technology Domain | Upstream Location (`application/`) | Custom Root Implementation | Overlap / Duplication Assessment |
|---|---|---|---|
| **Docker Compose** | `application/src/app/docker-compose.yml` & `application/src/*/docker-compose.yml` | `docker/docker-compose.yml` | **Architectural Divergence:** Upstream uses nested `include:` directives and requires local DynamoDB, MySQL, and RabbitMQ container dependencies. Root `docker/docker-compose.yml` is an all-in-one unified mesh configured for standalone in-memory execution, Apple Silicon (M3/ARM64) compatibility, explicit memory limits, and inter-service healthcheck dependencies (`condition: service_healthy`). |
| **Kubernetes** | `application/src/*/chart/` & `application/src/app/helmfile.yaml` | `kubernetes/` (`ui`, `catalog`, `cart`, `checkout`, `orders`, `config`, `ingress`) | **Pure Declarative vs. Helm:** Upstream contains only Helm charts and Helmfiles requiring Helm CLI installation and variable injection. Root `kubernetes/` contains pure, production-grade vanilla declarative YAML manifests with zero external Helm dependencies, explicit RollingUpdate parameters, readiness/liveness probes, HPAs, and unified Prometheus scrape annotations. |
| **Terraform IaC** | `application/terraform/` (`ecs/`, `eks/`, `apprunner/`, `lib/`) | `terraform/` (`modules/networking`, `iam`, `ecr`, `eks`, `environments/dev`) | **Decoupled Production IaC vs. Workshop Blueprints:** Upstream Terraform consists of complex AWS demo workshop blueprints tightly coupled to AWS workshop automation scripts (provisioning OpenSearch, ADOT, Istio, App Runner, ECS). Root `terraform/` is purpose-built, modular, readable IaC implementing IAM least-privilege, KMS envelope encryption for Kubernetes secrets, and clean environment separation (`environments/dev`). |
| **CI/CD Workflows** | `application/.github/workflows/` (`pr.yaml`, `release-please.yml`, `e2e-test.yml`) | `.github/workflows/` (`ci.yml`, `security.yml`, `deploy.yml`) | **No Conflict:** GitHub Actions only executes workflows in the repository root (`.github/workflows/`). Upstream workflows inside `application/.github/` are completely dormant and ignored by GitHub. Root workflows handle linting, multi-service unit tests, Trivy security gates, OIDC AWS authentication, and EKS deployments. |

---

## 5. Deployment Pipeline Dependency Mapping

An audit of `.github/workflows/` proves exactly which configurations are active:

```mermaid
flowchart LR
    subgraph Root GitHub Actions Pipeline
        CI[ci.yml]
        SEC[security.yml]
        DEP[deploy.yml]
    end

    subgraph Active Upstream Code
        CAT_SRC[application/src/catalog]
        UI_SRC[application/src/ui]
    end

    subgraph Active Custom Root Code
        DOCKER_CFG[docker/docker-compose.yml]
        K8S_CFG[kubernetes/**/*.yaml]
        TF_CFG[terraform/**]
        AUTO_CFG[automation/tests/**]
    end

    subgraph Dormant Upstream Files [Ignored by Pipeline]
        UP_TF[application/terraform/**]
        UP_GH[application/.github/**]
        UP_HELM[application/src/**/chart/**]
        UP_APP[application/src/app/**]
    end

    CI -->|Tests Go Code| CAT_SRC
    CI -->|Tests Java Code| UI_SRC
    CI -->|Validates Compose Syntax| DOCKER_CFG
    SEC -->|Scans IaC & Manifests| K8S_CFG
    SEC -->|Scans Terraform Code| TF_CFG
    DEP -->|Validates PyYAML Syntax| K8S_CFG
    DEP -->|Applies to Amazon EKS| K8S_CFG
```

### Key Findings:
1. **Upstream Source Utilization**: The pipeline tests microservice application code directly inside `application/src/catalog` and `application/src/ui`.
2. **Upstream IaC & Helm Dormancy**: Neither `application/terraform/` nor `application/src/*/chart/` nor `application/src/app/` is referenced or executed anywhere in the root CI/CD pipeline or documentation.
3. **Pipeline Exclusivity**: 100% of deployed containers, Kubernetes objects, and cloud resources originate from the root directories (`docker/`, `kubernetes/`, `terraform/`).

---

## 6. Microservices Integration & Compatibility Verification

We audited whether root Kubernetes manifests and Terraform modules accurately integrate with the polyglot microservices:

### 1. Service Discovery & Networking
- **Namespace**: All root Kubernetes manifests target the isolated `retail-store` namespace (`metadata.namespace: retail-store`).
- **Internal DNS**: Root `kubernetes/config/configmap.yaml` configures inter-service communication using Kubernetes CoreDNS:
  - Catalog: `http://catalog.retail-store.svc.cluster.local:8080`
  - Cart: `http://cart.retail-store.svc.cluster.local:8080`
  - Checkout: `http://checkout.retail-store.svc.cluster.local:8080`
  - Orders: `http://orders.retail-store.svc.cluster.local:8080`
- **ClusterIP Ports**: In `kubernetes/*/deployment.yaml`, each backend Service (`catalog`, `cart`, `checkout`, `orders`) defines:
  - `port: 8080`
  - `targetPort: 8080`
  - `protocol: TCP`
- **Frontend Port**: The `ui` Service exposes a `LoadBalancer` on port 80 targeting container port 8080.
- **Verification**: ✅ **PASS**. Endpoints match internal Service definitions exactly.

### 2. Environment Variables & Feature Flags
- `SEARCH_ENABLED`: Set to `"false"` across all ConfigMaps and Docker Compose files. This prevents runtime errors related to missing OpenSearch/Elasticsearch clusters.
- `RETAIL_*_PERSISTENCE_PROVIDER`: Set to `"in-memory"` across all services. This allows the microservices to run seamlessly for testing and demonstrations without requiring live AWS RDS MySQL, DynamoDB, or ElastiCache clusters.
- `Verification`: ✅ **PASS**. Services initialize cleanly in standalone or clustered modes.

### 3. Health Probes
- **UI Service (Spring Boot)**: `/actuator/health` on port `8080` (HTTP GET).
- **Catalog Service (Go Gin)**: `/health` on port `8080` (HTTP GET).
- **Cart Service (Spring Boot)**: `/actuator/health` on port `8080` (HTTP GET).
- **Checkout Service (NestJS)**: `/health` on port `8080` (HTTP GET).
- **Orders Service (Spring Boot)**: `/actuator/health` on port `8080` (HTTP GET).
- **Verification`: ✅ **PASS**. Probe paths in `kubernetes/*/deployment.yaml` strictly match upstream controller route registrations.

### 4. Terraform Cloud Alignment
- Cluster Name: Defined in `terraform/environments/dev/variables.tf` as `retail-store` (resulting in `dev-retail-store`).
- CI/CD Deploy Step: `deploy.yml` connects using `aws eks update-kubeconfig --name dev-retail-store`.
- ECR Repositories: Terraform provisions 5 repositories (`dev-retail-store-ui`, `catalog`, `cart`, `checkout`, `orders`).
- **Verification**: ✅ **PASS**. Infrastructure outputs align directly with deployment scripts.

---

## 7. Conflict & Security Audit

| Check | Scope | Result | Details |
|---|---|---|---|
| **Namespace Collisions** | Kubernetes | ✅ Clean | Root uses `retail-store`. Upstream defaults to `default`. |
| **Port Conflicts (Local)** | Docker Compose | ✅ Clean | Host ports mapped distinctly: UI (8888), Catalog (8081), Cart (8082), Orders (8083), Checkout (8085). |
| **Security Contexts** | Kubernetes | ✅ Clean | Non-root enforcement: `runAsNonRoot: true`, `runAsUser: 1000`, `runAsGroup: 1000`. |
| **Resource Quotas** | Kubernetes | ✅ Clean | All pods specify CPU and memory `requests` and `limits` to prevent node starvation. |
| **GitHub Actions Run** | CI/CD | ✅ Clean | Root `.github/workflows/` has 100% green status; upstream workflows in `application/` are inert. |

---

## 8. README & Documentation Attribution Assessment

### Current State:
The root `README.md` mentions the AWS Retail Store Sample Application in the intro paragraph and lists `application/src/` in the tree diagram. However:
1. It does not explicitly catalog the rest of `application/` (`terraform/`, `docs/`, `scripts/`, `samples/`).
2. It lacks a clear, prominent architectural boundary table showing recruiters what was authored by the candidate versus what was provided by upstream AWS.

### Why This Matters for Recruiters:
Senior DevOps and Platform Engineering recruiters value authenticity. If an applicant presents a repository with two sets of Terraform and Kubernetes files without an explanation, a reviewer might assume accidental copy-pasting. Conversely, when the applicant explicitly states:
> *"Upstream application source is cloned from AWS under MIT-0. All production Kubernetes manifests, modular Terraform modules, GitHub Actions CI/CD pipelines, Prometheus monitoring, and Python SRE automation in the root directories are custom engineering implementations."*

The candidate demonstrates professional maturity, transparency, and advanced systems integration capability.

---

## 9. Recommended Improvements (For User Approval)

The following improvements are recommended to achieve complete clarity without modifying or deleting any upstream code:

1. **Retain Upstream Code Untouched**:
   - Do **not** delete `application/terraform/`, `application/.github/`, or `application/src/app/`. Keeping the upstream repository intact ensures full reproducibility and open-source license integrity.
2. **Add an Architecture Boundary Section to `README.md`**:
   - Add a dedicated section titled `## Upstream Application vs. Platform Engineering Implementation` to `README.md`.
   - Include a clear comparison matrix distinguishing upstream source from custom platform engineering.
3. **Add `application/UPSTREAM_NOTICE.md`**:
   - Add a lightweight notice inside `application/` stating that this directory contains the upstream AWS Retail Store Sample App source code, and that all active deployment, Terraform, and Kubernetes implementations reside in the root repository.
4. **Update `docs/TERRAFORM_AWS.md` and `docs/KUBERNETES_EKS.md`**:
   - Add a brief note distinguishing the custom modular implementations from upstream sample files.

---
*Report generated and validated on local workspace. Awaiting user review and authorization.*
