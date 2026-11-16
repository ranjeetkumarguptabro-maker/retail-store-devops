variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS deployment region"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Target environment"
}

variable "cluster_name" {
  type        = string
  default     = "retail-store"
  description = "EKS cluster base name"
}

variable "instance_types" {
  type        = list(string)
  default     = ["t3.medium"]
  description = "Node group EC2 instance types"
}

variable "desired_capacity" {
  type        = number
  default     = 2
  description = "Desired number of worker nodes"
}

variable "enable_nat_gateway" {
  type        = bool
  default     = true
  description = "Whether to provision NAT Gateway"
}
