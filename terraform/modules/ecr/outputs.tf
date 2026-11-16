output "repository_urls" {
  value       = { for k, v in aws_ecr_repository.services : k => v.repository_url }
  description = "Map of microservice names to their ECR repository URLs"
}
