# 1.1 VPC & Networking (Phase 1 Foundation - No cost for VPC itself)

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "caqi_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "caqi-vpc"
  }
}

# Public Subnets (AZ-a and AZ-b)
resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.caqi_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "caqi-public-subnet-1"
  }
}

resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.caqi_vpc.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true

  tags = {
    Name = "caqi-public-subnet-2"
  }
}

# Private Subnets (AZ-a and AZ-b) for Aurora, RDS Proxy, ElastiCache
resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.caqi_vpc.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "caqi-private-subnet-1"
  }
}

resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.caqi_vpc.id
  cidr_block        = "10.0.12.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "caqi-private-subnet-2"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "caqi_igw" {
  vpc_id = aws_vpc.caqi_vpc.id

  tags = {
    Name = "caqi-igw"
  }
}

# Public Route Table
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.caqi_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.caqi_igw.id
  }

  tags = {
    Name = "caqi-public-rt"
  }
}

resource "aws_route_table_association" "public_1" {
  subnet_id      = aws_subnet.public_1.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "public_2" {
  subnet_id      = aws_subnet.public_2.id
  route_table_id = aws_route_table.public_rt.id
}

# DB Subnet Group for Aurora / RDS Proxy
resource "aws_db_subnet_group" "aurora_subnet_group" {
  name       = "caqi-aurora-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]

  tags = {
    Name = "caqi-aurora-subnet-group"
  }
}

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "redis_subnet_group" {
  name       = "caqi-redis-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]
}

