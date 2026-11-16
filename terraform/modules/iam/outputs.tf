output "cluster_role_arn" {
  value       = aws_iam_role.cluster.arn
  description = "IAM role ARN for EKS control plane"
}

output "node_role_arn" {
  value       = aws_iam_role.nodes.arn
  description = "IAM role ARN for EKS worker nodes"
}
