# Phase 4: AWS Infrastructure & Terraform Architecture Guide

This document details the cloud architecture, modular Terraform design, cost management, and safe operational procedures for deploying the **AWS Retail Store Sample Application** to AWS.

---

## 1. AWS Resource Architecture

```
                                  AWS Cloud
  +-------------------------------------------------------------------------+
  |  Virtual Private Cloud (VPC) 10.0.0.0/16                                |
  |                                                                         |
  |  +---------------------------+       +-------------------------------+  |
  |  | Public Subnets (AZ1, AZ2) |       | Private Subnets (AZ1, AZ2)    |  |
  |  | - Internet Gateway (IGW)  |       | - EKS Managed Worker Nodes    |  |
  |  | - NAT Gateway (0.0.0.0/0) | ----> | - Internal Pod Communication  |  |
  |  | - Public Load Balancers   |       | - Private Endpoints           |  |
  |  +---------------------------+       +-------------------------------+  |
  |                                                                         |
  |  +-------------------------------------------------------------------+  |
  |  | EKS Control Plane (Kubernetes 1.31) - Managed by AWS              |  |
  |  +-------------------------------------------------------------------+  |
  |                                                                         |
  |  +-------------------------------------------------------------------+  |
  |  | Amazon ECR Repositories (ui, catalog, cart, checkout, orders)     |  |
  |  +-------------------------------------------------------------------+  |
  +-------------------------------------------------------------------------+
```

---

## 2. Cost Analysis & Budget Safeguards

| Resource | Hourly Rate (Est.) | Monthly Cost (Est.) | Optimization & Cost Control |
|---|---|---|---|
| **EKS Control Plane** | \$0.10 / hr | \$72.00 | Single cluster, tear down when not in use |
| **Worker Nodes (2x `t3.medium`)** | \$0.0416 / node / hr | \$60.00 | Scale to 1 node or Spot instances in dev |
| **NAT Gateway** | \$0.045 / hr + data | \$32.40 | Disable NAT in local testing; single NAT in dev |
| **EBS Storage (20 GB / node)** | \$0.08 / GB / month | \$3.20 | Standard gp3 storage |
| **ECR Storage** | \$0.10 / GB / month | < \$1.00 | Lifecycle policy expires images > 30 days |
| **Estimated Total:** | | **~\$168.00 / month** | **~\$0.23 / hr during active testing** |

> [!CAUTION]
> Always execute `terraform destroy` after testing sessions to prevent ongoing hourly charges.

---

## 3. Pre-Deployment Validation & Plan Review

Before any `terraform apply`:
1. Verify code formatting and linting: `terraform fmt -check`
2. Validate module configurations: `terraform validate`
3. Generate detailed execution plan: `terraform plan -out=tfplan`
4. Review resource additions, changes, and deletions with project lead before applying.
