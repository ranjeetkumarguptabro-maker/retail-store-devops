output "vpc_id" {
  value       = module.networking.vpc_id
  description = "VPC ID"
}

output "eks_cluster_name" {
  value       = module.eks.cluster_name
  description = "EKS Cluster Name"
}

output "eks_cluster_endpoint" {
  value       = module.eks.cluster_endpoint
  description = "EKS API Server Endpoint"
}

output "ecr_repository_urls" {
  value       = module.ecr.repository_urls
  description = "Microservice ECR Repository URLs"
}
