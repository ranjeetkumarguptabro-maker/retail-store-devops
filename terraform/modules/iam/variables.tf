variable "environment" {
  type        = string
  description = "Deployment environment"
}

variable "cluster_name" {
  type        = string
  description = "EKS cluster name"
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Resource tags"
}
