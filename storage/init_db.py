import logging
from storage.db import engine, SessionLocal
from storage.models import Base, Account, Merchant, FraudCheckpoint, Transaction
from data.generator import generate_database_seed_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("caqi.storage.init")

def init_database():
    """Initializes tables and populates seed data."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    try:
        existing_accounts = session.query(Account).count()
        if existing_accounts == 0:
            logger.info("Populating database seed records...")
            seed_data = generate_database_seed_data(num_accounts=1000, num_merchants=200)
            
            for acc in seed_data["accounts"]:
                session.add(Account(**acc))
                session.add(FraudCheckpoint(
                    account_id=acc["account_id"],
                    risk_score=0.02,
                    velocity_1h=0,
                    dist1=12.5,
                    flagged=False
                ))
                
            for m in seed_data["merchants"]:
                session.add(Merchant(**m))
                
            session.commit()
            logger.info("Seeded 1,000 accounts, 1,000 fraud checkpoints, and 200 merchants successfully.")
        else:
            logger.info(f"Database already contains {existing_accounts} accounts. Skipping seeding.")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to seed database: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    init_database()
