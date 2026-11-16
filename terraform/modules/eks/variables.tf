variable "environment" {
  type        = string
  description = "Deployment environment"
}

variable "cluster_name" {
  type        = string
  description = "EKS cluster name"
}

variable "kubernetes_version" {
  type        = string
  default     = "1.31"
  description = "Kubernetes version"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID"
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnet IDs"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs"
}

variable "cluster_role_arn" {
  type        = string
  description = "Cluster IAM role ARN"
}

variable "node_role_arn" {
  type        = string
  description = "Node IAM role ARN"
}

variable "desired_capacity" {
  type        = number
  default     = 2
  description = "Desired number of worker nodes"
}

variable "min_capacity" {
  type        = number
  default     = 1
  description = "Minimum number of worker nodes"
}

variable "max_capacity" {
  type        = number
  default     = 4
  description = "Maximum number of worker nodes"
}

variable "instance_types" {
  type        = list(string)
  default     = ["t3.medium"]
  description = "EC2 instance types for nodes"
}

variable "capacity_type" {
  type        = string
  default     = "ON_DEMAND"
  description = "Capacity type (ON_DEMAND or SPOT)"
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Resource tags"
}
