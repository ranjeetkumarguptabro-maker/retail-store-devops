# ==============================================================================
# Terraform Module: EKS (Managed Kubernetes Cluster & Node Groups)
# ==============================================================================

resource "aws_security_group" "cluster" {
  name        = "${var.environment}-${var.cluster_name}-cluster-sg"
  description = "Security group for EKS control plane"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-${var.cluster_name}-cluster-sg"
    }
  )
}

resource "aws_eks_cluster" "main" {
  name     = "${var.environment}-${var.cluster_name}"
  role_arn = var.cluster_role_arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = concat(var.public_subnet_ids, var.private_subnet_ids)
    endpoint_private_access = true
    endpoint_public_access  = true
    security_group_ids      = [aws_security_group.cluster.id]
  }

  tags = merge(
    var.tags,
    {
      Environment = var.environment
    }
  )
}

resource "aws_eks_node_group" "managed" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.environment}-managed-nodes"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids

  scaling_config {
    desired_size = var.desired_capacity
    max_size     = var.max_capacity
    min_size     = var.min_capacity
  }

  instance_types = var.instance_types
  capacity_type  = var.capacity_type

  update_config {
    max_unavailable = 1
  }

  tags = merge(
    var.tags,
    {
      Environment = var.environment
    }
  )

  depends_on = [
    aws_eks_cluster.main
  ]
}
