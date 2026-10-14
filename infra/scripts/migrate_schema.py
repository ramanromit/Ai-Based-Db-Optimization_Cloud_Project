"""
infra/scripts/migrate_schema.py

Migrates the CAQI schema from local SQLite/SQLAlchemy models to Aurora PostgreSQL.
Uses SQLAlchemy metadata (same models the app uses) — no pg_dump/psql required.

Usage (from project root):
    python infra/scripts/migrate_schema.py \\
        --host <aurora-writer-endpoint> \\
        --password <db_master_password> \\
        [--username caqi_admin] \\
        [--dbname caqi] \\
        [--port 5432] \\
        [--seed]

⚠️  Run this only ONCE (first session), pointing at the WRITER endpoint directly.
    After migration, all app traffic should go via the RDS Proxy endpoint.
"""
import sys
import os
import argparse
import logging

# Make sure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("caqi.migrate")


def parse_args():
    p = argparse.ArgumentParser(description="Migrate CAQI schema to Aurora PostgreSQL")
    p.add_argument("--host",     required=True,  help="Aurora writer endpoint hostname")
    p.add_argument("--password", required=True,  help="Master password")
    p.add_argument("--username", default="caqi_admin")
    p.add_argument("--dbname",   default="caqi")
    p.add_argument("--port",     default="5432")
    p.add_argument("--seed",     action="store_true",
                   help="Also seed reference data (accounts, merchants) after migration")
    return p.parse_args()


def main():
    args = parse_args()

    url = f"postgresql://{args.username}:{args.password}@{args.host}:{args.port}/{args.dbname}"
    logger.info(f"Connecting to Aurora: {args.host}:{args.port}/{args.dbname}")

    engine = create_engine(
        url,
        connect_args={"connect_timeout": 10},
        echo=False,
    )

    # Verify connectivity
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Connection successful.")
    except Exception as e:
        logger.error(f"❌ Cannot connect to Aurora: {e}")
        logger.error("   → Check that your local IP is allowed by the data-sg security group.")
        logger.error("   → Temporary rule: add your IP to the data-sg for port 5432, run migration, then remove it.")
        sys.exit(1)

    # Import and create all tables via SQLAlchemy metadata
    logger.info("Creating tables from SQLAlchemy models...")
    try:
        from storage.models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables created successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        sys.exit(1)

    # Optional seeding
    if args.seed:
        logger.info("Seeding reference data (accounts, merchants, fraud checkpoints)...")
        try:
            from storage.init_db import init_database as _init
            # Temporarily override the engine used by init_db
            import storage.db as db_module
            original_engine = db_module.engine
            db_module.engine = engine
            db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            _init()
            db_module.engine = original_engine
            logger.info("✅ Seed data applied.")
        except Exception as e:
            logger.error(f"❌ Seeding failed: {e}")
            sys.exit(1)

    logger.info("")
    logger.info("═══════════════════════════════════════════════════")
    logger.info("Migration complete. Next steps:")
    logger.info("  1. Remove the temporary security group rule (your local IP → port 5432)")
    logger.info("  2. Set USE_AWS=true in .env (or use phase2_start.ps1 which does it)")
    logger.info("  3. Set RDS_PROXY_ENDPOINT in .env to the proxy endpoint")
    logger.info("  4. Restart the backend: uvicorn api.main:app --port 8000 --reload")
    logger.info("═══════════════════════════════════════════════════")


if __name__ == "__main__":
    main()
