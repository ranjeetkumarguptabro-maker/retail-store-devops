variable "environment" {
  type        = string
  description = "Deployment environment name (e.g. dev, prod)"
}

variable "cluster_name" {
  type        = string
  description = "EKS cluster name to tag on subnets"
}

variable "vpc_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "CIDR block for the VPC"
}

variable "public_subnet_cidrs" {
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
  description = "Public subnet CIDR blocks"
}

variable "private_subnet_cidrs" {
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
  description = "Private subnet CIDR blocks"
}

variable "availability_zones" {
  description = "Availability zones for the networking module"
  type        = list(string)
  default     = ["eu-north-1a", "eu-north-1b"]
}

variable "enable_nat_gateway" {
  type        = bool
  default     = true
  description = "Enable NAT Gateway for private subnets"
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Resource tags"
}
