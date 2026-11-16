# ==============================================================================
# Terraform Module: Networking (VPC, Subnets, Gateways, Route Tables)
# ==============================================================================

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(
    var.tags,
    {
      Name                                           = "${var.environment}-retail-vpc"
      "kubernetes.io/cluster/${var.cluster_name}"     = "shared"
    }
  )
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-retail-igw"
    }
  )
}

resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(
    var.tags,
    {
      Name                                           = "${var.environment}-public-${var.availability_zones[count.index]}"
      "kubernetes.io/cluster/${var.cluster_name}"     = "shared"
      "kubernetes.io/role/elb"                       = "1"
    }
  )
}

resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(
    var.tags,
    {
      Name                                           = "${var.environment}-private-${var.availability_zones[count.index]}"
      "kubernetes.io/cluster/${var.cluster_name}"     = "shared"
      "kubernetes.io/role/internal-elb"              = "1"
    }
  )
}

resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? 1 : 0
  domain = "vpc"

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-nat-eip"
    }
  )
}

resource "aws_nat_gateway" "nat" {
  count         = var.enable_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-nat-gw"
    }
  )

  depends_on = [aws_internet_gateway.gw]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-public-rt"
    }
  )
}

resource "aws_route_table_association" "public" {
  count          = length(var.public_subnet_cidrs)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.nat[0].id
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-private-rt"
    }
  )
}

resource "aws_route_table_association" "private" {
  count          = length(var.private_subnet_cidrs)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}
