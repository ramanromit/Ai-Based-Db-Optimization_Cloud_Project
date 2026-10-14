# ═══════════════════════════════════════════════════════════════════
# Phase 2 — Aurora Serverless v2, PostgreSQL-compatible
# Gated behind enable_expensive_core = true (default: false)
# DESTROY at end of every session — Aurora bills continuously.
# ═══════════════════════════════════════════════════════════════════

# ── Aurora Cluster ──────────────────────────────────────────────────
resource "aws_rds_cluster" "aurora_cluster" {
  count = var.enable_expensive_core ? 1 : 0

  cluster_identifier     = "caqi-aurora-cluster"
  engine                 = "aurora-postgresql"
  engine_mode            = "provisioned"
  engine_version         = "15.4"
  database_name          = "caqi"
  master_username        = var.db_master_username
  master_password        = var.db_master_password
  db_subnet_group_name   = aws_db_subnet_group.aurora_subnet_group.name
  vpc_security_group_ids = [aws_security_group.data_sg.id]
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.caqi_cmk.arn
  skip_final_snapshot    = true

  # Serverless v2 — cap at 2 ACUs to stay inside Learner Lab budget.
  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 2.0
  }

  # Ignore object-lock attributes blocked by the Learner Lab SCP.
  lifecycle {
    ignore_changes = [
      master_password, # managed outside Terraform after first apply
    ]
  }

  tags = {
    Name = "caqi-aurora-cluster"
    Role = "Primary writer (payment auth, settlement)"
  }
}

# ── Writer Instance ─────────────────────────────────────────────────
resource "aws_rds_cluster_instance" "writer_instance" {
  count = var.enable_expensive_core ? 1 : 0

  identifier         = "caqi-aurora-writer"
  cluster_identifier = aws_rds_cluster.aurora_cluster[0].id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.aurora_cluster[0].engine
  engine_version     = aws_rds_cluster.aurora_cluster[0].engine_version
  promotion_tier     = 0

  tags = {
    Name = "caqi-aurora-writer"
    Role = "Writer — auth-critical & settlement writes via RDS Proxy"
  }
}

# ── Reader Instance (Read Replica) ──────────────────────────────────
# Aurora automatically replicates from the writer.
# The allocator routes analytical/settlement queries here to protect
# the writer's connection quota for auth-critical traffic.
resource "aws_rds_cluster_instance" "reader_instance" {
  count = var.enable_expensive_core ? 1 : 0

  identifier         = "caqi-aurora-reader-1"
  cluster_identifier = aws_rds_cluster.aurora_cluster[0].id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.aurora_cluster[0].engine
  engine_version     = aws_rds_cluster.aurora_cluster[0].engine_version
  promotion_tier     = 1

  tags = {
    Name = "caqi-aurora-reader-1"
    Role = "Reader — analytical/settlement offload, lower priority"
  }
}
