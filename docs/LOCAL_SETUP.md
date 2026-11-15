# Phase 1: Local Application Setup & Verification Guide

This guide details how to set up, configure, start, verify, and stop the **AWS Retail Store Sample Application** locally on macOS (Apple Silicon M3).

---

## 1. Architecture Overview & Operating Modes

The application can operate in two distinct modes:

### Mode A: Lightweight Standalone Mode (Zero External Database)
The UI service (`ui`) contains built-in mock fallbacks (`MockCatalogService`, `MockCartsService`, `MockCheckoutService`, `MockRecommendationsService`). When backend service endpoint environment variables are empty or omitted, the UI serves products, shopping carts, and checkout flows completely in-memory.
- **Port:** `8888` (mapped to internal `8080`)
- **Memory Footprint:** ~350 MB
- **Start Time:** ~2.2 seconds

### Mode B: Full Microservices Distributed Mode
All 5 microservices run in concert with their respective data stores:
- **UI:** Storefront web proxy (`8888 -> 8080`)
- **Catalog:** Go Gin API (`8081 -> 8080`) + MariaDB (`3306`)
- **Cart:** Java Spring Boot API (`8082 -> 8080`) + DynamoDB-Local (`8000`)
- **Checkout:** Node.js NestJS API (`8085 -> 8080`) + Redis (`6379`)
- **Orders:** Java Spring Boot API (`8083 -> 8080`) + PostgreSQL (`5432`) + RabbitMQ (`5672`)

---

## 2. Prerequisites & Environment Configuration

Ensure Docker Desktop is active on your macOS system:

```bash
docker --version
docker info
```

### Environment Configuration
Copy the template configuration file:

```bash
cp .env.example .env
```

Key environment settings:
```ini
UI_PORT=8888
CATALOG_PORT=8081
CART_PORT=8082
CHECKOUT_PORT=8085
ORDERS_PORT=8083

SEARCH_ENABLED=false
RETAIL_UI_SEARCH_ENABLED=false
RETAIL_CATALOG_SEARCH_ENABLED=false
```

---

## 3. Starting the Application

### Option 1: Standalone Storefront UI (Instant Startup)
Run the UI container directly:

```bash
docker run -d \
  --name retail-ui \
  -p 8888:8080 \
  public.ecr.aws/aws-containers/retail-store-sample-ui:1.0.0
```

### Option 2: Full Distributed Stack (Docker Compose)
From the project root:

```bash
docker compose -f application/src/app/docker-compose.yml -f application/src/app/compose.override.yaml up -d
```

---

## 4. Verifying Functionality & Endpoints

### A. Health & Metrics Checks
Verify application readiness and Prometheus instrumentation:

```bash
# Health Check (Spring Boot Actuator)
curl -s http://localhost:8888/actuator/health
# Expected Output: {"status":"UP"}

# Prometheus Metrics Endpoint
curl -s http://localhost:8888/actuator/prometheus | head -n 20
```

### B. Core Storefront Page Verification
Run automated route checks:

```bash
for route in "" "home" "catalog" "cart" "checkout" "topology" "info"; do
  http_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8888/${route}")
  echo "Route: /${route} -> HTTP ${http_code}"
done
```

Expected Output:
```text
Route: / -> HTTP 200
Route: /home -> HTTP 200
Route: /catalog -> HTTP 200
Route: /cart -> HTTP 200
Route: /checkout -> HTTP 200
Route: /topology -> HTTP 200
Route: /info -> HTTP 200
```

### C. Browser Testing
Open the application in Google Chrome / Safari:
- **Storefront:** [http://localhost:8888](http://localhost:8888)
- **Product Catalog:** [http://localhost:8888/catalog](http://localhost:8888/catalog)
- **Shopping Cart:** [http://localhost:8888/cart](http://localhost:8888/cart)
- **Architecture & Topology Viewer:** [http://localhost:8888/topology](http://localhost:8888/topology)

---

## 5. Stopping the Application

### Stopping Standalone UI:
```bash
docker stop retail-ui
docker rm retail-ui
```

### Stopping Full Distributed Compose Stack:
```bash
docker compose -f application/src/app/docker-compose.yml -f application/src/app/compose.override.yaml down -v
```
