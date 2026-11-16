terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend configuration (Configured when remote S3 + DynamoDB locking is enabled)
  # backend "s3" {
  #   bucket         = "retail-store-tfstate-unique-id"
  #   key            = "dev/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "retail-store-tflocks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "RetailStoreDevOps"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
