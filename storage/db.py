import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("caqi.storage.db")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://caqi_admin:caqi_secret@localhost:5432/caqi_db")
FALLBACK_SQLITE_URL = "sqlite:///caqi_local.sqlite"

def get_engine():
    """Attempts PostgreSQL connection; falls back to local SQLite if PG is unreachable."""
    try:
        # Short timeout test for Postgres
        pg_engine = create_engine(
            DATABASE_URL,
            pool_size=20,
            max_overflow=10,
            connect_args={"connect_timeout": 2}
        )
        with pg_engine.connect() as conn:
            conn.execute(create_engine("select 1").connect().connection.cursor())
        logger.info(f"Connected to PostgreSQL at {DATABASE_URL}")
        return pg_engine
    except Exception as e:
        logger.warning(f"PostgreSQL unreachable ({e}). Using local SQLite database: {FALLBACK_SQLITE_URL}")
        return create_engine(
            FALLBACK_SQLITE_URL,
            connect_args={"check_same_thread": False}
        )

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency / generator for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
