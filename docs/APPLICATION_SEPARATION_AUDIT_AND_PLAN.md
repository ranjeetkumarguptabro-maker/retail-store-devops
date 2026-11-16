# Application Separation Audit & Final Migration Plan

> **Date:** November 16, 2026  
> **Repository:** `ranjeetkumarguptabro-maker/retail-store-devops`  
> **Dedicated Branch:** `restructure/application-devops-separation`  
> **Rollback Baseline Commit:** `7c6a055` (`Separate application source code from platform engineering implementation`)  
> **Status:** Pending User Approval for Final Cleanup

---

## 1. Executive Classification (Step 1)

Every directory and file in `application/` has been inspected and classified according to the three requested criteria:
* **Category A:** Required application source code, build configuration, or runtime dependency.
* **Category B:** DevOps, infrastructure, containerization, or CI/CD implementation.
* **Category C:** Documentation, linters, or development tooling not required at runtime.

### Comprehensive Classification Matrix

| Directory / File | Category | Original Purpose | Proposed / Executed Action |
|---|:---:|---|---|
| **`.github/`** | **B** | AWS-internal GitHub Actions workflows (release-please, PRs, kind e2e) | **Moved** to `.github/upstream/` to prevent interference with root CI/CD. |
| **`terraform/`** | **B** | AWS workshop blueprints (ECS, EKS, App Runner, ADOT, Istio) | **Moved** to `terraform/upstream-blueprints/` without conflicting with custom `terraform/modules/`. |
| **`docs/`** | **C** | Upstream architecture PNGs, drawio diagrams, features spec | **Moved** to `docs/upstream-app/`. |
| **`README.md`** | **C** | Upstream repository README | **Removed** from `application/`; attribution and license preserved in root `README.md`. |
| **`DEVELOPER_GUIDE.md`**| **C** | Upstream development environment setup instructions | **Moved** to `docs/upstream-app/DEVELOPER_GUIDE.md`. |
| **`scripts/`** | **B** | Manifest generation (`create-manifest.sh`), Kind e2e, security scanning | **Moved** to `scripts/upstream/`. |
| **`src/app/`** | **B** | Upstream umbrella Helm chart, Helmfiles, compose files, Tiltfile, OTel config | **Moved** to `kubernetes/upstream-helm/`, `docker/upstream/`, and `monitoring/upstream/`. |
| **`src/*/chart/`** | **B** | Individual microservice Helm charts | **Moved** to `kubernetes/upstream-helm/services/{ui,catalog,cart,checkout,orders}/`. |
| **`src/*/docker-compose.yml`** | **B** | Individual microservice local compose overrides | **Moved** to `docker/upstream/services/{ui,catalog,cart,checkout,orders}/`. |
| **`src/*/Dockerfile*`**| **B** | Multi-stage Docker container build specifications | **Moved** to `docker/dockerfiles/Dockerfile.{ui,catalog,cart,checkout,orders,...}`. |
| **`src/ui/`** | **A** | Storefront UI source code (Java 21 / Spring Boot 3.5, `pom.xml`, `mvnw`, `.mvn/`) | **RETAINED** in `application/src/ui/`. Genuine application source. |
| **`src/catalog/`** | **A** | Product Catalog source code (Go Gin REST API, `main.go`, `go.mod`, `go.sum`, `api/`, `model/`, `test/`) | **RETAINED** in `application/src/catalog/`. Genuine application source. |
| **`src/cart/`** | **A** | Cart service source code (Java 21 / Spring Boot 3.5, `pom.xml`, `mvnw`, `.mvn/`) | **RETAINED** in `application/src/cart/`. Genuine application source. |
| **`src/checkout/`** | **A** | Checkout service source code (Node.js 20 / NestJS 11 + TS, `package.json`, `tsconfig.json`) | **RETAINED** in `application/src/checkout/`. Genuine application source. |
| **`src/orders/`** | **A** | Orders service source code (Java 21 / Spring Boot 3.5, `events/`, `pom.xml`, `mvnw`, `.mvn/`) | **RETAINED** in `application/src/orders/`. Genuine application source. |
| **`src/recommendations/`**| **A** | Component OpenAPI specification (`openapi.yml`) | **RETAINED** in `application/src/recommendations/`. |
| **`src/load-generator/`**| **A** | Artillery / Node.js test traffic suite (`package.json`, `scenario.yml`) | **RETAINED** in `application/src/load-generator/`. |
| **`src/e2e/`** | **A** | Cypress end-to-end integration browser test suite | **RETAINED** in `application/src/e2e/`. |
| **`samples/`** | **A** | Mock catalog JSON datasets (`products.json`, `tags.json`) & product images | **RETAINED** in `application/samples/`. Required by Catalog & UI. |
| **`LICENSE`** | **A** | Original AWS MIT-0 License document | **RETAINED** in `application/LICENSE` for open-source license compliance. |
| **`package.json`** | **B/C** | Upstream monorepo root package file (contains `compose:up`, Nx devDependencies) | **Candidate for Removal/Relocation** (see Section 3). |
| **`yarn.lock`** | **C** | Monorepo root yarn lockfile | **Candidate for Removal/Relocation** (see Section 3). |
| **`nx.json`** | **B** | Upstream Nx monorepo container build & Helm packaging graph | **Candidate for Removal/Relocation** (see Section 3). |
| **`.yarn/` & `.yarnrc.yml`** | **C** | Monorepo Yarn 4 release binaries & yarn configuration | **Candidate for Removal/Relocation** (see Section 3). |
| **`lefthook.yml`** | **C** | Git pre-commit hook runner | **Candidate for Removal/Relocation** (see Section 3). |
| **`.prettierrc`, `.prettierignore`** | **C** | Prettier code formatter configs | **Candidate for Removal/Relocation** (see Section 3). |
| **`.mergify.yml`** | **B** | GitHub automated pull request merge queue rules | **Candidate for Removal/Relocation** (see Section 3). |
| **`release-please-config.json`** | **B** | Google Release Please bot configuration | **Candidate for Removal/Relocation** (see Section 3). |
| **`.release-please-manifest.json`** | **B** | Release Please state manifest | **Candidate for Removal/Relocation** (see Section 3). |
| **`renovate.json`** | **B** | Renovate automated dependency bot configuration | **Candidate for Removal/Relocation** (see Section 3). |
| **`.mise.toml`** | **C** | Mise runtime tool version manager | **Candidate for Removal/Relocation** (see Section 3). |
| **`CHANGELOG.md`** | **C** | Upstream historical release changelog | **Candidate for Relocation** to `docs/upstream-app/`. |
| **`CODE_OF_CONDUCT.md`** | **C** | Amazon Open Source Code of Conduct | **Candidate for Relocation** to `docs/upstream-app/`. |
| **`CONTRIBUTING.md`** | **C** | Guidelines for contributing to upstream AWS repository | **Candidate for Relocation** to `docs/upstream-app/`. |
| **`oss/`** | **C** | Open Source Review Toolkit (ORT) compliance configurations | **Candidate for Relocation** to `docs/upstream-app/oss/`. |

---

## 2. Completed Migrations & Preservations (Step 2)

All major standalone DevOps implementations have already been relocated to the root repository without overwriting any custom work:

1. **Terraform**:
   * Upstream AWS workshop blueprints (`application/terraform/`) → `terraform/upstream-blueprints/`
   * Your custom production Terraform → untouched in `terraform/modules/` and `terraform/environments/dev/`
2. **Kubernetes & Helm**:
   * Upstream Helm charts (`application/src/app/chart/`, `helmfile*.yaml`, `application/src/*/chart/`) → `kubernetes/upstream-helm/`
   * Your pure declarative vanilla Kubernetes manifests → untouched in `kubernetes/` (`ui`, `catalog`, `cart`, `checkout`, `orders`, `config`, `ingress`)
3. **Docker**:
   * Upstream compose files & Tiltfile → `docker/upstream/`
   * Upstream Dockerfiles → centralized in `docker/dockerfiles/`
   * Your custom multi-service compose mesh → untouched in `docker/docker-compose.yml`
4. **Monitoring**:
   * Upstream OpenTelemetry collector config → `monitoring/upstream/otel-collector-config.yml`
   * Your Prometheus values & Grafana dashboards → untouched in `monitoring/prometheus/` and `monitoring/grafana/`
5. **CI/CD**:
   * Upstream AWS internal workflows → `.github/upstream/`
   * Your custom GitHub Actions pipelines → untouched in `.github/workflows/` (`ci.yml`, `security.yml`, `deploy.yml`)
6. **Documentation**:
   * Upstream diagrams & docs → `docs/upstream-app/`
   * Nested `application/README.md` → removed; root `README.md` updated with comprehensive Attribution & Separation Matrix

---

## 3. Proposed Final Cleanup for `application/` Root (Step 3)

Currently, the `application/` root directory still contains 15 non-runtime tooling and bot configuration files left over from the original monorepo setup:

```
application/
├── .mergify.yml                  # Merge queue bot
├── .mise.toml                    # Tool version manager
├── .prettierignore, .prettierrc  # Code formatting
├── .release-please-manifest.json # Release automation
├── release-please-config.json    # Release automation
├── renovate.json                 # Dependency bot
├── lefthook.yml                  # Git pre-commit hooks
├── CHANGELOG.md                  # Upstream changelog
├── CODE_OF_CONDUCT.md            # Community doc
├── CONTRIBUTING.md               # Community doc
├── oss/                          # ORT compliance tooling
├── nx.json                       # Nx monorepo container build graph
├── package.json, yarn.lock       # Root monorepo yarn files
└── .yarn/, .yarnrc.yml           # Yarn binaries
```

### Dependency Audit for Root Tooling Files:
* Does Java UI, Cart, or Orders depend on `application/package.json`? **No.** They use Maven (`pom.xml`, `mvnw`).
* Does Go Catalog depend on `application/package.json`? **No.** It uses Go modules (`go.mod`, `go.sum`).
* Does Node.js Checkout depend on `application/package.json`? **No.** Checkout has its own isolated `package.json` and `yarn.lock` in `application/src/checkout/`.
* Does Load Generator or E2E depend on `application/package.json`? **No.** Both have their own `package.json` in their respective directories.

### Proposed Action:
1. **Relocate to `docs/upstream-app/`**:
   * Move `CHANGELOG.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, and `oss/` to `docs/upstream-app/`.
2. **Relocate Upstream Monorepo Tooling**:
   * Move `nx.json`, `application/package.json`, `application/yarn.lock`, `.yarn/`, `.yarnrc.yml`, `lefthook.yml`, `.mergify.yml`, `renovate.json`, `release-please*`, `.prettier*`, `.mise.toml` to a dedicated reference directory (e.g., `scripts/upstream-monorepo-tooling/` or remove them).
3. **Purity of `application/`**:
   * After this cleanup, `application/` will contain strictly:
     ```text
     application/
     ├── LICENSE                      # Original AWS MIT-0 License
     ├── samples/                     # Catalog datasets & product images
     └── src/                         # Pure microservice source code
         ├── ui/                      # Java Spring Boot Storefront
         ├── catalog/                 # Go Gin Catalog REST API
         ├── cart/                    # Java Spring Boot Cart Service
         ├── checkout/                # NestJS TypeScript Checkout Service
         ├── orders/                  # Java Spring Boot Orders Service
         ├── recommendations/         # OpenAPI schema
         ├── load-generator/          # Artillery load tests
         └── e2e/                     # Cypress end-to-end tests
     ```

---

## 4. Validation Results (Step 4)

| Validation Target | Verification Method | Status | Details |
|---|---|:---:|---|
| **Go Catalog API** | `go test -v ./...` | ✅ **PASS** | Tests compile and pass with TestContainers MySQL. |
| **Java UI Service** | `./mvnw test-compile` | ✅ **PASS** | Source compiles cleanly against Java 21 specification. |
| **Docker Compose Mesh** | `docker compose -f docker/docker-compose.yml config` | ✅ **PASS** | Evaluated valid with return code 0. |
| **Kubernetes Manifests**| PyYAML validation across `kubernetes/**/*.yaml` | ✅ **PASS** | Syntax validated with zero errors. |
| **Python Ops Engine** | `python3 -m unittest discover -s automation/tests -v` | ✅ **PASS** | 7/7 tests passed in 0.004s. |
| **GitHub Actions Pipeline**| Remote run on commit `7c6a055` | ✅ **PASS** | All 3 workflows (`CI`, `Security`, `CD`) are 100% Green (`✓`). |

---

## 5. Safety & Rollback Assurance (Step 5)

* **Dedicated Branch:** `restructure/application-devops-separation`
* **Rollback Commit:** `7c6a055`
* **Zero Infrastructure Changes:** No cloud resources were provisioned or modified.
* **Zero Overwrites:** All existing custom files in the root repository remain protected.

---

## 6. Awaiting User Approval

Before performing the cleanup of the 15 remaining monorepo tooling/bot configuration files listed in Section 3:
* **Option 1 (Recommended):** Relocate `nx.json`, `package.json`, `yarn.lock`, and bot configs (`renovate`, `mergify`, `release-please`, `lefthook`) to `scripts/upstream-monorepo-tooling/`, and move community docs (`CHANGELOG`, `CONTRIBUTING`, `oss/`) to `docs/upstream-app/`. This leaves `application/` containing **only** `LICENSE`, `samples/`, and `src/`.
* **Option 2:** Retain `package.json` and `nx.json` inside `application/` for monorepo reference, and remove only the bot configs and community files.

Please confirm whether you approve proceeding with **Option 1**.
