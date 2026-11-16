# Terraform AWS Infrastructure Modules

This directory contains modular Infrastructure as Code (IaC) for provisioning the cloud foundation on AWS for the **AWS Retail Store Sample Application**.

---

## 1. Directory Structure

```text
terraform/
├── modules/
│   ├── networking/   # VPC, Public & Private Subnets, IGW, NAT Gateway, Route Tables
│   ├── iam/          # EKS Cluster & Node IAM Roles (Least Privilege)
│   ├── ecr/          # ECR Repositories for UI, Catalog, Cart, Checkout, Orders
│   └── eks/          # Managed EKS Cluster & Node Groups
│
└── environments/
    └── dev/          # Development environment composition & tfvars
```

---

## 2. Infrastructure Operations Runbook

### Formatting & Validation:
```bash
cd terraform/environments/dev
terraform fmt -recursive
terraform init
terraform validate
```

### Execution Planning (Dry-Run):
```bash
terraform plan -var-file="terraform.tfvars"
```

### Resource Destruction & Cleanup:
```bash
terraform destroy -var-file="terraform.tfvars"
```
