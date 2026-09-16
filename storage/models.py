import time
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"
    
    account_id = Column(String(64), primary_key=True, index=True)
    balance = Column(Float, nullable=False, default=0.0)
    credit_limit = Column(Float, nullable=False, default=1000.0)
    currency = Column(String(3), default="USD")
    status = Column(String(16), default="ACTIVE")

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    
    key = Column(String(128), primary_key=True, index=True)
    transaction_id = Column(String(64), nullable=True)
    status = Column(String(16), default="IN_FLIGHT") # IN_FLIGHT, COMPLETED, FAILED
    created_at = Column(Float, default=time.time)
    expires_at = Column(Float, nullable=False)

class FraudCheckpoint(Base):
    __tablename__ = "fraud_checkpoints"
    
    account_id = Column(String(64), primary_key=True, index=True)
    risk_score = Column(Float, default=0.01)
    velocity_1h = Column(Integer, default=0)
    dist1 = Column(Float, default=0.0)
    flagged = Column(Boolean, default=False)
    updated_at = Column(Float, default=time.time)

class Transaction(Base):
    __tablename__ = "transactions"
    
    transaction_id = Column(String(64), primary_key=True, index=True)
    account_id = Column(String(64), index=True)
    merchant_id = Column(String(64), index=True)
    amount = Column(Float, nullable=False)
    card_network = Column(String(32), default="visa")
    card_type = Column(String(16), default="debit")
    status = Column(String(16), default="AUTHORIZED") # AUTHORIZED, SETTLED, DECLINED
    timestamp = Column(Float, default=time.time)

class SettlementBatch(Base):
    __tablename__ = "settlement_batches"
    
    batch_id = Column(String(64), primary_key=True, index=True)
    merchant_id = Column(String(64), index=True)
    record_count = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)
    status = Column(String(16), default="PENDING") # PENDING, PROCESSING, SETTLED
    timestamp = Column(Float, default=time.time)

class Merchant(Base):
    __tablename__ = "merchants"
    
    merchant_id = Column(String(64), primary_key=True, index=True)
    merchant_name = Column(String(128), nullable=False)
    category = Column(String(32), default="RETAIL")
    settlement_frequency = Column(String(16), default="DAILY")
    status = Column(String(16), default="ACTIVE")

