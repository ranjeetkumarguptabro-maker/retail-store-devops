variable "repository_prefix" {
  type        = string
  default     = "retail-store"
  description = "Prefix for ECR repository names"
}

variable "service_names" {
  type        = list(string)
  default     = ["ui", "catalog", "cart", "checkout", "orders"]
  description = "List of microservices to create ECR repositories for"
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Resource tags"
}
