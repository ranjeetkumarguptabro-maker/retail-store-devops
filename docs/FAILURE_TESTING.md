# Phase 10: Operational Failure Testing & Resiliency Experiments

This guide documents 6 controlled operational failure experiments executed to validate Kubernetes self-healing, rolling updates, rollbacks, and diagnostic alerting for the **AWS Retail Store Sample Application**.

---

## Scenario 1: Pod Deletion & Self-Healing

- **Goal:** Verify that Kubernetes ReplicaSets automatically replace terminated Pods without service downtime.
- **Action:** Delete a running UI Pod:
  ```bash
  POD=$(kubectl get pod -l app.kubernetes.io/name=ui -n retail-store -o jsonpath='{.items[0].metadata.name}')
  kubectl delete pod $POD -n retail-store
  ```
- **Observed Behavior:**
  - The Pod enters `Terminating` status.
  - The Deployment immediately schedules a replacement Pod in `ContainerCreating` $\rightarrow$ `Running`.
  - Service traffic seamlessly redirects to the remaining healthy replica.
  - **Recovery Time (MTTR):** < 4 seconds.

---

## Scenario 2: Application Failure & CrashLoopBackOff Detection

- **Goal:** Verify that our Python automation tool flags crashing Pods.
- **Action:** Inject an unhandled fatal error or bad exit code:
  ```bash
  kubectl set env deployment/catalog -n retail-store RETAIL_CATALOG_PERSISTENCE_PROVIDER=invalid-db-type
  ```
- **Observed Behavior:**
  - The Catalog container fails startup and restarts.
  - Kubernetes marks the Pod in `CrashLoopBackOff`.
  - Running `python3 automation/pod_health.py retail-store` outputs:
    ```json
    {
      "status": "DEGRADED",
      "issues_detected": 1,
      "unhealthy_pods": [
        {
          "pod_name": "catalog-687f8b9d5c-x29q7",
          "diagnostics": ["Container 'catalog' in CrashLoopBackOff"]
        }
      ]
    }
    ```
- **Remediation:** Restore working environment variable:
  ```bash
  kubectl set env deployment/catalog -n retail-store RETAIL_CATALOG_PERSISTENCE_PROVIDER=in-memory
  ```

---

## Scenario 3: Invalid Image Tag & ImagePullBackOff

- **Goal:** Validate rollout stall detection when an image tag does not exist.
- **Action:**
  ```bash
  kubectl set image deployment/ui ui=public.ecr.aws/aws-containers/retail-store-sample-ui:non-existent-tag -n retail-store
  ```
- **Observed Behavior:**
  - Kubernetes attempts to pull the image and enters `ImagePullBackOff`.
  - The zero-downtime rolling update strategy (`maxUnavailable: 0`) prevents the existing 2 healthy Pods from terminating!
  - Storefront users experience **0% downtime**.
  - `python3 automation/rollout_validator.py ui retail-store` flags the rollout as incomplete.
- **Remediation:** Undo the rollout:
  ```bash
  kubectl rollout undo deployment/ui -n retail-store
  ```

---

## Scenario 4: Controlled Rolling Update

- **Goal:** Update the application version while continuously serving traffic.
- **Action:**
  ```bash
  kubectl set image deployment/ui ui=public.ecr.aws/aws-containers/retail-store-sample-ui:1.0.0 -n retail-store
  kubectl rollout status deployment/ui -n retail-store
  ```
- **Observed Behavior:**
  - A new Pod is created (`maxSurge: 1`).
  - Readiness probe (`/actuator/health`) runs for 15s until HTTP 200 is verified.
  - Only after the new Pod is Ready does Kubernetes terminate an old Pod.
  - Zero dropped connections observed.

---

## Scenario 5: Automated Rollback Verification

- **Goal:** Roll back to the last known good revision after release verification failure.
- **Action:**
  ```bash
  kubectl rollout history deployment/ui -n retail-store
  kubectl rollout undo deployment/ui -n retail-store --to-revision=1
  kubectl rollout status deployment/ui -n retail-store
  ```
- **Observed Behavior:** Kubernetes successfully rolls back to the previous deployment revision.

---

## Scenario 6: Chaos Latency Injection via Built-in `/chaos` Endpoints

- **Goal:** Test latency resilience without crashing containers.
- **Action:** Inject 500ms artificial latency into the Catalog Go service:
  ```bash
  curl -X POST http://localhost:8081/chaos/latency/500
  ```
- **Observed Behavior:**
  - Requests to `/catalog/products` take +500ms.
  - P95 latency panel in Grafana dashboard (`monitoring/grafana/dashboards/application-overview.json`) visibly spikes.
  - The UI service handles the delayed response gracefully.
- **Reset:**
  ```bash
  curl -X DELETE http://localhost:8081/chaos/latency
  ```
