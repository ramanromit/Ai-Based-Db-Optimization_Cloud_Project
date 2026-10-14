# Phase 2b - ElastiCache Redis (Gated behind enable_expensive_core)

resource "aws_elasticache_cluster" "redis" {
  count                = var.enable_expensive_core ? 1 : 0
  cluster_id           = "caqi-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.redis_subnet_group.name
  security_group_ids   = [aws_security_group.data_sg.id]

  tags = {
    Name = "caqi-redis"
  }
}

