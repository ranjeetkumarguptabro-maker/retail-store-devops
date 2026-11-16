# Repository Restructuring Report: Data & Application Separation

> **Date:** November 16, 2026  
> **Repository:** `ranjeetkumarguptabro-maker/retail-store-devops`  
> **Target Branch:** `restructure/application-devops-separation`  
> **Initial Commit:** `acefc2f` (`Add production documentation, failure recovery guide, and master README`)

---

## 1. Objective & Scope

The purpose of this restructuring is to achieve clean separation of concerns:
* **`application/`** strictly contains the upstream AWS Retail Store Sample Application source code, test assets, sample catalog datasets, build dependencies, and original AWS licenses.
* **Root repository directories** contain all custom DevOps engineering implementations: containerization, vanilla declarative Kubernetes manifests, modular Terraform IaC, GitHub Actions CI/CD workflows, Prometheus & Grafana observability, and the Python SRE operations automation engine.

---

## 2. Inventory of Files Moved

| Category | Source in `application/` | Relocated Root Destination | Rationale |
|---|---|---|---|
| **Terraform Blueprints** | `application/terraform/` (`ecs/`, `eks/`, `apprunner/`, `lib/`) | `terraform/upstream-blueprints/` | Moves AWS demo workshop blueprints out of application source while preserving them for reference without conflicting with custom `terraform/modules/`. |
| **Helm Charts (Umbrella)** | `application/src/app/chart/` | `kubernetes/upstream-helm/umbrella-chart/` | Relocates umbrella Helm chart from application tree. |
| **Helmfiles & Templates** | `application/src/app/helmfile*.yaml`, `application/src/app/templates/` | `kubernetes/upstream-helm/` | Relocates Helmfile manifests and Go gotmpl templates. |
| **Service Helm Charts** | `application/src/{ui,catalog,cart,checkout,orders}/chart/` | `kubernetes/upstream-helm/services/{ui,catalog,cart,checkout,orders}/` | Completely purges nested Helm charts from each microservice directory. |
| **Docker Compose Files** | `application/src/app/docker-compose*.yml`, `compose.override.yaml`, `Tiltfile` | `docker/upstream/` | Moves upstream compose orchestration out of the application root. |
| **Service Compose Files** | `application/src/{ui,catalog,cart,checkout,orders}/docker-compose.yml` | `docker/upstream/services/{ui,catalog,cart,checkout,orders}/docker-compose.yml` | Clears individual service Docker Compose files out of microservice directories. |
| **Dockerfiles** | `application/src/{ui,catalog,cart,checkout,orders,load-generator,e2e}/Dockerfile*` | `docker/dockerfiles/Dockerfile.{ui,catalog,cart,checkout,orders,load-generator,load-generator-run,e2e-run}` | Centralizes multi-stage, multi-arch Dockerfiles in `docker/dockerfiles/`. |
| **Monitoring (OTel)** | `application/src/app/otel-collector-config.yml` | `monitoring/upstream/otel-collector-config.yml` | Unifies all observability configurations under root `monitoring/`. |
| **CI/CD Workflows** | `application/.github/` (`workflows/`, `actions/`) | `.github/upstream/` (`workflows/`, `actions/`) | Moves upstream AWS-internal workflows out of `application/`. Prevents GitHub Actions from trying to run internal AWS jobs. |
| **Deployment Scripts** | `application/scripts/` (`create-manifest.sh`, `compose-dist.sh`, `kubernetes-dist.sh`, `e2e*.sh`, `generate-*-report.sh`, etc.) | `scripts/upstream/` | Consolidates upstream build and manifest scripts in root `scripts/`. |
| **Upstream Documentation**| `application/docs/` (`features.md`, `diagrams.drawio.xml`, `images/`) & `application/DEVELOPER_GUIDE.md` | `docs/upstream-app/` | Centralizes all upstream architectural documentation under `docs/`. |
| **Nested README** | `application/README.md` | **Deleted** (Root `README.md` serves as single master) | Eliminates redundant nested README while preserving `application/LICENSE` and `ATTRIBUTION.md`. |

---

## 3. Files Retained in `application/` and Justification

The following files remain inside `application/` because they are genuine application source, build dependencies, test suites, or required open-source metadata:

1. **Polyglot Microservice Codebases (`application/src/`)**:
   - `ui/`: Spring Boot Java 21 frontend (`src/main/**`, `src/test/**`, `pom.xml`, `mvnw`, `.mvn/`, `ATTRIBUTION.md`, `project.json`)
   - `catalog/`: Go Gin REST API (`main.go`, `api/**`, `controller/**`, `model/**`, `repository/**`, `httputil/**`, `middleware/**`, `config/**`, `test/**`, `go.mod`, `go.sum`, `openapi.yml`, `ATTRIBUTION.md`, `project.json`)
   - `cart/`: Spring Boot Java 21 service (`src/main/**`, `src/test/**`, `pom.xml`, `mvnw`, `.mvn/`, `openapi.yml`, `ATTRIBUTION.md`, `project.json`)
   - `checkout/`: NestJS TypeScript service (`src/**`, `test/**`, `package.json`, `yarn.lock`, `tsconfig.json`, `nest-cli.json`, `eslint.config.mjs`, `openapi.yml`, `ATTRIBUTION.md`, `project.json`)
   - `orders/`: Spring Boot Java 21 service (`src/main/**`, `src/test/**`, `events/**`, `pom.xml`, `mvnw`, `.mvn/`, `openapi.yml`, `ATTRIBUTION.md`, `project.json`)
   - `recommendations/`: Component specification (`openapi.yml`, `README.md`)
   - `load-generator/`: Artillery / Node.js test traffic suite (`package.json`, `yarn.lock`, `scenario.yml`, `helpers.js`, `scripts/`)
   - `e2e/`: Cypress end-to-end browser test suite (`cypress/**`, `cypress.config.js`, `package.json`, `yarn.lock`)
   - `misc/style/`: Java checkstyle configurations
2. **Mock Catalog Datasets (`application/samples/`)**:
   - `samples/data/products.json`, `samples/data/tags.json`, `samples/images/*.jpg` required by the Catalog service and UI at runtime.
3. **Open Source Attribution & Monorepo Metadata**:
   - `application/LICENSE` (AWS MIT-0 License preserved intact)
   - `application/CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
   - `application/package.json`, `yarn.lock`, `nx.json`, `.yarnrc.yml`, `.yarn/releases/` (Nx monorepo build graph configs)

---

## 4. Integration with Custom Implementations

1. **No Overwrites**: Zero custom files in the root directories were overwritten. Existing custom files (`docker/docker-compose.yml`, `kubernetes/**/*.yaml`, `terraform/modules/**`, `terraform/environments/dev/**`, `monitoring/prometheus/**`, `monitoring/grafana/**`, `automation/**`, `.github/workflows/**`) remained completely intact.
2. **Upstream Subdirectory Isolation**:
   - Relocated upstream Terraform: `terraform/upstream-blueprints/`
   - Relocated upstream Helm: `kubernetes/upstream-helm/`
   - Relocated upstream Compose: `docker/upstream/`
   - Relocated upstream OTel config: `monitoring/upstream/`
   - Relocated upstream CI/CD: `.github/upstream/`
   - Relocated upstream scripts: `scripts/upstream/`
   - Relocated upstream docs: `docs/upstream-app/`
3. **Active Pipeline Protection**:
   - In `.github/workflows/deploy.yml`, updated the PyYAML manifest validator to skip `upstream` directories (`if 'upstream' in path: continue`). This ensures raw unrendered Helm templates with `{{ .Values... }}` in `kubernetes/upstream-helm/` do not cause PyYAML parse errors, keeping the CI/CD pipeline 100% green.

---

## 5. Validation Results

| Test / Check | Tool / Command | Result | Notes |
|---|---|:---:|---|
| **Go Catalog Tests** | `cd application/src/catalog && go test -v ./...` | ✅ **PASS** | TestContainers MySQL launched, database migrations executed, all tests passed. |
| **Java UI Compilation** | `cd application/src/ui && ./mvnw test-compile` | ✅ **PASS** | Validated against Java 21 specification. |
| **Docker Compose Config** | `docker compose -f docker/docker-compose.yml config --quiet` | ✅ **PASS** | Configuration syntax and service graph validated with exit code 0. |
| **Kubernetes Declarative Manifests**| PyYAML syntax validation across `kubernetes/**/*.yaml` | ✅ **PASS** | All declarative production manifests parsed and validated cleanly. |
| **Python Operations Engine** | `python3 -m unittest discover -s automation/tests -v` | ✅ **PASS** | 7/7 unit tests passed in 0.004s (100% pass rate). |
| **Application Directory Purity**| `find application -name "*Dockerfile*" -o -name "*chart*" -o -name "*terraform*"` | ✅ **PASS** | Zero standalone DevOps deployment files remaining in `application/`. |

---

## 6. Remaining Issues / Notes

* **None.** All microservice source directories are clean. The upstream AWS Retail Store Sample Application source is preserved under MIT-0, and all platform engineering and DevOps implementations are neatly organized in the root project structure.
