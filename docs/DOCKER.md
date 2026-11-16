# Phase 2: Docker Containerization & Multi-Service Orchestration

This document outlines the container architecture, multi-stage build strategy, non-root security principles, and local multi-service orchestration for the **AWS Retail Store Sample Application**.

---

## 1. Container Strategy & Principles

### A. Multi-Stage Builds
Each microservice utilizes a multi-stage Dockerfile:
1. **Build Stage:** Full compilation toolchain (`maven` / `golang` / `yarn`). Dependencies are pre-cached before source code injection to maximize Docker build layer caching.
2. **Runtime Stage:** Minimal, secure base image (`amazonlinux:2023` or `alpine`), discarding compilers, source files, and temporary artifacts.

### B. Security & Least Privilege
- **Non-Root Execution:** All application containers drop privileges to user `appuser` (UID `1000`, GID `1000`).
- **Capability Dropping:** Unnecessary Linux kernel capabilities are removed.
- **Read-Only Root Filesystems:** Supported with ephemeral `/tmp` volume mounts.

### C. Multi-Architecture Support
Docker Buildx builds native images for:
- `linux/arm64` (Apple Silicon M-series developer workstations)
- `linux/amd64` (Standard AWS EC2 / EKS worker nodes)

---

## 2. Service Container Breakdown

| Service | Base Runtime Image | Memory Reservation | Memory Limit | Health Check |
|---|---|---|---|---|
| **UI** | `amazonlinux:2023` (Java 21) | 512 MB | 1024 MB | HTTP GET `/actuator/health` |
| **Catalog** | `amazonlinux:2023` (Go static binary) | 64 MB | 256 MB | HTTP GET `/health` |
| **Cart** | `amazonlinux:2023` (Java 21) | 256 MB | 512 MB | HTTP GET `/actuator/health` |
| **Checkout** | `amazonlinux:2023` (Node.js 20) | 128 MB | 384 MB | HTTP GET `/health` |
| **Orders** | `amazonlinux:2023` (Java 21) | 256 MB | 512 MB | HTTP GET `/actuator/health` |

---

## 3. Local Multi-Service Orchestration (`docker-compose.yml`)

The unified stack is located in [`docker/docker-compose.yml`](../docker/docker-compose.yml).

### Starting the Multi-Service Mesh:
```bash
docker compose -f docker/docker-compose.yml up -d
```

### Inspecting Running Services:
```bash
docker compose -f docker/docker-compose.yml ps
```

### Viewing Logs:
```bash
# All logs
docker compose -f docker/docker-compose.yml logs -f

# Specific service log
docker compose -f docker/docker-compose.yml logs -f ui
```

### Stopping the Stack:
```bash
docker compose -f docker/docker-compose.yml down -v
```
