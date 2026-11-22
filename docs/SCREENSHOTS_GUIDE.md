# 📸 Visual Proof & Screenshot Guide for AWS DevOps Portfolio

This guide details how to capture, organize, and push visual verification screenshots of your AWS Cloud infrastructure, Kubernetes cluster, CI/CD pipelines, and SRE automation engine to this repository and showcase them in the [`README.md`](../README.md).

---

## 1. Why Visual Proof Matters to Recruiters

Recruiters, hiring managers, and Staff DevOps/Platform engineers look for **tangible proof** that an applicant actually deployed and validated infrastructure on live AWS rather than simply cloning a repository or running syntax checks.

Having clear, high-resolution screenshots embedded in your README and documentation provides immediate verification of:
1. **Real Cloud Infrastructure:** Live Amazon EKS clusters, Managed Node Groups, and VPC subnets.
2. **Container Security:** Trivy vulnerability scan passes and CycloneDX SBOM artifact generation.
3. **Cluster Health & Scaling:** Kubernetes pods running across multiple Availability Zones with HPAs and PDBs.
4. **Production Observability:** Grafana dashboards tracking real requests, p95 latencies, and 99% SLO error budgets.
5. **Self-Healing Automation:** Terminal execution of the automated Python incident lifecycle engine.

---

## 2. Recommended Screenshot Checklist

| Category | File Path | What to Capture in the Screenshot |
| :--- | :--- | :--- |
| **Project Architecture** | `docs/images/architecture/retail-store-devops-architecture.png` | End-to-end DevOps architecture linking developer workstation, GitHub Actions, Terraform IaC, EKS workloads, S3 backup, and SRE observability. |
| **AWS Architecture & VPC** | `docs/images/aws/retail-devops-aws-architecture.png` | Multi-account AWS architecture blueprint showing DevOps platform account, VPC peering, Multi-AZ subnets, ALB, EKS, and SRE account. |
| **DevOps Infinity Loop** | `docs/images/cicd/devops-infinity-loop.png` | Complete continuous DevOps lifecycle blueprint mapping VS Code, GitHub, Pytest, Docker, Terraform, Helm, AWS OIDC, EKS, and Prometheus/Grafana. |
| **Storefront App** | `docs/images/application/retail-storefront-ui.png` | Storefront web UI in browser (`http://localhost:8888` or AWS ALB endpoint) showing catalog products and active cart. |
| **AWS EKS Console** | `docs/images/aws/eks-cluster-console.png` | AWS Management Console ➔ EKS ➔ Clusters ➔ `dev-retail-store` showing `Active` status, Kubernetes v1.29, and subnets. |
| **AWS Node Groups** | `docs/images/aws/eks-nodegroups.png` | AWS EKS Console ➔ Compute tab showing Managed Node Group (`m5.large`), desired/min/max capacity, and instances. |
| **AWS ECR** | `docs/images/aws/ecr-repositories.png` | AWS Console ➔ Amazon ECR ➔ Repositories showing all 5 container images (`ui`, `catalog`, `cart`, `checkout`, `orders`). |
| **Kubernetes CLI** | `docs/images/kubernetes/kubectl-cluster-workloads.png` | Terminal running `kubectl get nodes,pods,svc,hpa,pdb -n retail-store -o wide` showing healthy Running pods. |
| **CI/CD Pipeline** | `docs/images/cicd/github-actions-all-green.png` | GitHub Actions tab showing all 3 workflows (`CI`, `Security`, `CD`) passing with green checkmarks. |
| **Trivy & SBOM** | `docs/images/cicd/trivy-sbom-artifact.png` | GitHub Actions run summary showing Trivy security scan pass and `software-bill-of-materials` artifact. |
| **Grafana Dashboard** | `docs/images/observability/grafana-overview.png` | Grafana dashboard showing 30-day rolling SLO gauge (99.0%), request throughput, and p95 latency. |
| **Prometheus Targets** | `docs/images/observability/prometheus-targets.png` | Prometheus web UI (`/targets`) showing all microservice scrape endpoints (`/actuator/prometheus`) in state `UP`. |
| **SRE Self-Healing** | `docs/images/sre-automation/incident-lifecycle-terminal.png` | Terminal running `python3 automation/ops_cli.py incident-lifecycle --service cart --auto-approve`. |

---

## 3. How to Capture Screenshots

### On macOS
- **Full Window Screenshot (Crisp Drop Shadow):**  
  Press <kbd>Cmd</kbd> + <kbd>Shift</kbd> + <kbd>4</kbd>, press <kbd>Spacebar</kbd>, then click on the target browser or terminal window.
- **Selected Area Screenshot:**  
  Press <kbd>Cmd</kbd> + <kbd>Shift</kbd> + <kbd>4</kbd>, click and drag across the region of interest.
- **Mac Screenshot Utility Bar:**  
  Press <kbd>Cmd</kbd> + <kbd>Shift</kbd> + <kbd>5</kbd>.

### On Windows
- Press <kbd>Win</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> to open the Snipping Tool.

### On Linux
- Press <kbd>Shift</kbd> + <kbd>PrintScreen</kbd> or use `gnome-screenshot -a`.

---

## 4. Organizing and Moving Images to the Repository

Once you capture your screenshots, move and rename them into the organized `docs/images/` subdirectories:

```bash
# Example on macOS: Move your desktop screenshot to the AWS directory
mv ~/Desktop/Screen\ Shot*.png docs/images/aws/eks-cluster-console.png

# Move terminal capture to the SRE automation directory
mv ~/Desktop/Screen\ Shot*.png docs/images/sre-automation/incident-lifecycle-terminal.png
```

Directory structure in the repo:
```text
docs/images/
├── architecture/    # End-to-end retail store devops architecture diagram
├── aws/             # Multi-account AWS architecture & VPC topology diagrams
├── cicd/            # DevOps infinity loop blueprint & GitHub Actions pipeline passes
├── application/     # Live Storefront UI screenshots
├── kubernetes/      # Terminal captures of kubectl workloads, HPAs, NetworkPolicies
├── observability/   # Grafana executive dashboards and Prometheus targets
└── sre-automation/  # SRE incident lifecycle post-mortems and terminal runs
```

---

## 5. How to Embed Screenshots in Markdown

Use clean HTML `<img>` tags or Markdown syntax with proper captions and styling:

### Option A: Clean HTML Card (Recommended for consistent sizing)
```html
<div align="center">
  <img src="docs/images/aws/eks-cluster-console.png" alt="Amazon EKS Cluster Console" width="850px" />
  <p><b>Figure 1:</b> <i>Amazon EKS Managed Cluster (dev-retail-store) running Kubernetes v1.29 in us-east-1.</i></p>
</div>
```

### Option B: Side-by-Side Comparison Grid
```html
<table>
  <tr>
    <td width="50%">
      <img src="docs/images/application/retail-storefront-ui.png" alt="Storefront UI" />
      <p align="center"><b>Storefront Web Application</b></p>
    </td>
    <td width="50%">
      <img src="docs/images/observability/grafana-slo-dashboard.svg" alt="Grafana SLO Dashboard" />
      <p align="center"><b>30-Day Rolling SLO Dashboard</b></p>
    </td>
  </tr>
</table>
```

### Option C: Collapsible Accordion (Prevents clutter)
```html
<details>
<summary><b>🔍 Click to view Amazon EKS Console Verification Screenshot</b></summary>

<br/>
<img src="docs/images/aws/eks-cluster-console.png" alt="EKS Cluster Console" width="100%" />

</details>
```

---

## 6. Committing & Pushing to GitHub

After placing your new images and updating the README links:

```bash
# 1. Stage the new images and README updates
git add docs/images/ README.md

# 2. Commit with a descriptive message
git commit -m "Add visual verification screenshots for AWS EKS, Grafana, and CI/CD"

# 3. Push to GitHub
git push origin main
```

Your screenshots will immediately render live in GitHub on your project repository front page!
