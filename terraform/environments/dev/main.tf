# ==============================================================================
# Development Environment Root Terraform Composition
# ==============================================================================

module "networking" {
  source = "../../modules/networking"

  environment        = var.environment
  cluster_name       = "${var.environment}-${var.cluster_name}"
  enable_nat_gateway = var.enable_nat_gateway
}

module "ecr" {
  source = "../../modules/ecr"

  repository_prefix = "${var.environment}-retail-store"
  service_names     = ["ui", "catalog", "cart", "checkout", "orders"]
}

module "iam" {
  source = "../../modules/iam"

  environment  = var.environment
  cluster_name = var.cluster_name
}

module "eks" {
  source = "../../modules/eks"

  environment        = var.environment
  cluster_name       = var.cluster_name
  vpc_id             = module.networking.vpc_id
  public_subnet_ids  = module.networking.public_subnet_ids
  private_subnet_ids = module.networking.private_subnet_ids
  cluster_role_arn   = module.iam.cluster_role_arn
  node_role_arn      = module.iam.node_role_arn
  instance_types     = var.instance_types
  desired_capacity   = var.desired_capacity
}
