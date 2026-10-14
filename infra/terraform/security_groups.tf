# 1.2 Security Groups

# App-tier SG (FastAPI backend / client instances)
resource "aws_security_group" "app_sg" {
  name        = "caqi-app-sg"
  description = "Security group for CAQI App tier"
  vpc_id      = aws_vpc.caqi_vpc.id

  ingress {
    description = "FastAPI HTTP API port"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "caqi-app-sg"
  }
}

# Data-tier SG (Aurora, RDS Proxy, Redis)
resource "aws_security_group" "data_sg" {
  name        = "caqi-data-sg"
  description = "Security group for CAQI Aurora DB, Proxy, and Redis"
  vpc_id      = aws_vpc.caqi_vpc.id

  ingress {
    description     = "PostgreSQL port from App tier"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
  }

  ingress {
    description     = "Redis port from App tier"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "caqi-data-sg"
  }
}

