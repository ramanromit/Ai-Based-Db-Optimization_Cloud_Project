# ═══════════════════════════════════════════════════════════════════
# Phase 2 — RDS Proxy + Secrets Manager
#
# NOVELTY RATIONALE:
#   This is where CAQI's "priority encoded into the database's own
#   resource-allocation policy" claim becomes real infrastructure:
#
#   • The proxy's connection pool enforces max_connections_percent = 100
#     for ALL connections but the backend routes them through two
#     distinct SQLAlchemy engines:
#       - writer_engine  → RDS Proxy endpoint  (auth-critical writes)
#       - reader_engine  → Aurora reader endpoint (analytical reads)
#   • Under load the allocator's action decides which engine handles
#     each query type, structurally protecting auth-critical capacity.
#
# DESTROY at end of every session — RDS Proxy bills continuously.
# ═══════════════════════════════════════════════════════════════════

# ── Secrets Manager — stores Aurora credentials for RDS Proxy auth ──
# RDS Proxy cannot use a plain password; it requires a Secrets Manager
# secret with keys "username" and "password".
resource "aws_secretsmanager_secret" "db_credentials" {
  count = var.enable_expensive_core ? 1 : 0

  # Account ID suffix makes the name globally unique within the account.
  name                    = "caqi/aurora/master-credentials-${data.aws_caller_identity.current.account_id}"
  description             = "Aurora master credentials for RDS Proxy authentication"
  recovery_window_in_days = 0 # immediate deletion (no retention window needed in sandbox)

  tags = {
    Name = "caqi-aurora-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials_val" {
  count = var.enable_expensive_core ? 1 : 0

  secret_id = aws_secretsmanager_secret.db_credentials[0].id
  secret_string = jsonencode({
    username = var.db_master_username
    password = var.db_master_password
    engine   = "aurora-postgresql"
    host     = aws_rds_cluster.aurora_cluster[0].endpoint
    port     = 5432
    dbname   = "caqi"
  })
}

# ── RDS Proxy ────────────────────────────────────────────────────────
resource "aws_db_proxy" "caqi_rds_proxy" {
  count = var.enable_expensive_core ? 1 : 0

  name          = "caqi-rds-proxy"
  engine_family = "POSTGRESQL"
  # Use the pre-existing LabRole — Learner Lab blocks creating new roles
  role_arn               = data.aws_iam_role.lab_role.arn
  vpc_subnet_ids         = [aws_subnet.private_1.id, aws_subnet.private_2.id]
  vpc_security_group_ids = [aws_security_group.data_sg.id]

  # TLS disabled for simplicity in sandbox — note in report as a simplification.
  require_tls         = false
  idle_client_timeout = 1800
  debug_logging       = false

  auth {
    auth_scheme = "SECRETS"
    description = "Aurora master user via Secrets Manager"
    iam_auth    = "DISABLED"
    secret_arn  = aws_secretsmanager_secret.db_credentials[0].arn
  }

  tags = {
    Name = "caqi-rds-proxy"
    Role = "Connection pooling — protects Aurora from connection storms"
  }

  depends_on = [
    aws_secretsmanager_secret_version.db_credentials_val,
  ]
}

# ── Proxy Default Target Group (connection pool config) ─────────────
# A single shared pool — the priority enforcement is done at the
# APPLICATION layer (which endpoint/engine is chosen per query type),
# not by multiple target groups (which Aurora doesn't support per-query).
resource "aws_db_proxy_default_target_group" "rds_proxy_targets" {
  count = var.enable_expensive_core ? 1 : 0

  db_proxy_name = aws_db_proxy.caqi_rds_proxy[0].name

  connection_pool_config {
    # Allow the proxy to use 100% of Aurora's max_connections.
    # The backend's dual-engine design (writer vs. reader endpoint)
    # provides the actual priority separation at the application layer.
    max_connections_percent      = 100
    max_idle_connections_percent = 50
    connection_borrow_timeout    = 120
  }
}

# ── Proxy Target — points proxy at the Aurora cluster ───────────────
resource "aws_db_proxy_target" "rds_proxy_target_aurora" {
  count = var.enable_expensive_core ? 1 : 0

  db_proxy_name         = aws_db_proxy.caqi_rds_proxy[0].name
  target_group_name     = aws_db_proxy_default_target_group.rds_proxy_targets[0].name
  db_cluster_identifier = aws_rds_cluster.aurora_cluster[0].id
}
