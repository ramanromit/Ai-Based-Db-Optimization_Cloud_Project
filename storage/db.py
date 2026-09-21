"""
storage/db.py — Database engine factory for CAQI backend.

Dual-endpoint design (Phase 2):
  - writer_engine  → RDS Proxy endpoint (auth-critical writes, settlement writes)
                     Falls back to local PostgreSQL → SQLite
  - reader_engine  → Aurora reader endpoint (analytical queries, settlement reads)
                     Falls back to same engine as writer when running locally

The allocator's routing decision picks which engine to use per query type,
implementing the "priority encoded into DB resource allocation" claim via
the RDS Proxy connection pool protecting the writer capacity.

Environment variables:
  USE_AWS=true         → use AWS endpoints below
  RDS_PROXY_ENDPOINT   → RDS Proxy host (writer path)
  AURORA_READER_ENDPOINT → Aurora reader host (analytical offload)
  DB_PORT              → default 5432
  DB_NAME              → default "caqi"
  DB_USERNAME          → default "caqi_admin"
  DB_PASSWORD          → master password (sensitive)
  DATABASE_URL         → override entire writer URL (local dev)
"""
import os
import logging
from sqlalchemy import create_engine, text, pool
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("caqi.storage.db")

# ── Configuration ────────────────────────────────────────────────────
USE_AWS = os.getenv("USE_AWS", "false").lower() == "true"

DB_PORT     = os.getenv("DB_PORT", "5432")
DB_NAME     = os.getenv("DB_NAME", "caqi")
DB_USERNAME = os.getenv("DB_USERNAME", os.getenv("DB_MASTER_USERNAME", "caqi_admin"))
DB_PASSWORD = os.getenv("DB_PASSWORD", os.getenv("DB_MASTER_PASSWORD", "caqi_secret"))

RDS_PROXY_ENDPOINT    = os.getenv("RDS_PROXY_ENDPOINT", "")
AURORA_READER_ENDPOINT = os.getenv("AURORA_READER_ENDPOINT", "")

# Local fallback URL (Docker Postgres → SQLite)
LOCAL_DATABASE_URL  = os.getenv(
    "DATABASE_URL",
    f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@localhost:{DB_PORT}/{DB_NAME}"
)
FALLBACK_SQLITE_URL = "sqlite:///caqi_local.sqlite"


# ── Engine factory ───────────────────────────────────────────────────
def _make_postgres_engine(host: str, label: str):
    """Creates a PostgreSQL engine with connection pooling appropriate for Aurora + RDS Proxy."""
    url = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{host}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(
        url,
        # NullPool is recommended when behind RDS Proxy — the proxy manages
        # connection pooling; SQLAlchemy's own pool would double-pool.
        poolclass=pool.QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,   # validates connections before use (important for proxy)
        connect_args={"connect_timeout": 5},
    )
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info(f"[{label}] Connected to PostgreSQL at {host}")
    return engine


def _make_sqlite_engine():
    return create_engine(
        FALLBACK_SQLITE_URL,
        connect_args={"check_same_thread": False},
    )


def _build_writer_engine():
    """
    Writer engine path:
      USE_AWS=true  → RDS Proxy endpoint (connection-pooled, priority-protected)
      USE_AWS=false → local PostgreSQL → SQLite fallback
    """
    if USE_AWS and RDS_PROXY_ENDPOINT:
        try:
            return _make_postgres_engine(RDS_PROXY_ENDPOINT, "WRITER/PROXY")
        except Exception as e:
            logger.error(f"[WRITER/PROXY] Failed to connect to RDS Proxy ({e}). "
                         "Check USE_AWS, RDS_PROXY_ENDPOINT, and VPC connectivity.")
            raise  # Do NOT silently fall back in AWS mode — the error must be visible
    else:
        # Local mode
        try:
            return _make_postgres_engine("localhost", "WRITER/LOCAL")
        except Exception as e:
            logger.warning(f"[WRITER/LOCAL] PostgreSQL unreachable ({e}). "
                           f"Falling back to SQLite: {FALLBACK_SQLITE_URL}")
            return _make_sqlite_engine()


def _build_reader_engine(writer_engine):
    """
    Reader engine path:
      USE_AWS=true  → Aurora reader endpoint (separate read replica)
      USE_AWS=false → same engine as writer (no replica locally)
    """
    if USE_AWS and AURORA_READER_ENDPOINT:
        try:
            return _make_postgres_engine(AURORA_READER_ENDPOINT, "READER/REPLICA")
        except Exception as e:
            logger.warning(f"[READER/REPLICA] Failed to connect to Aurora reader ({e}). "
                           "Falling back to writer engine for reads.")
            return writer_engine
    # Locally: reader == writer (no replica)
    logger.info("[READER] No reader endpoint configured — using writer engine for reads.")
    return writer_engine


# ── Module-level engine instances ────────────────────────────────────
engine        = _build_writer_engine()   # Default writer (used by ORM models, init_db)
reader_engine = _build_reader_engine(engine)

SessionLocal  = sessionmaker(autocommit=False, autoflush=False, bind=engine)
ReaderSession = sessionmaker(autocommit=False, autoflush=False, bind=reader_engine)


# ── FastAPI dependency generators ────────────────────────────────────
def get_db():
    """Writer session — auth-critical reads/writes, settlement writes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_reader_db():
    """
    Reader session — analytical queries and settlement reads.
    Routes to Aurora read replica in AWS mode; falls back to writer locally.
    Use this in API routes handling non-critical analytical traffic.
    """
    db = ReaderSession()
    try:
        yield db
    finally:
        db.close()
