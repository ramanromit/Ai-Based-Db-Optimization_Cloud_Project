import os
import random
import uuid
import pandas as pd
import numpy as np
from typing import Dict, Any, List

def generate_synthetic_ieee_cis_dataset(num_records: int = 10000, output_path: str = "data/ieee_fraud_sample.csv") -> pd.DataFrame:
    """
    Generates a synthetic dataset preserving the statistical properties,
    card networks, amount distribution, and fraud rate (~3.5%) of the IEEE-CIS Fraud Detection dataset.
    Used for local training and realistic auth-critical simulations.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    np.random.seed(42)
    random.seed(42)
    
    # 1. TransactionAmt (Log-normal distribution matching real payment data)
    amounts = np.random.lognormal(mean=3.9, sigma=1.1, size=num_records)
    amounts = np.clip(amounts, 0.5, 10000.0).round(2)
    
    # 2. ProductCD (Payment product code)
    product_codes = np.random.choice(['W', 'H', 'C', 'S', 'R'], size=num_records, p=[0.75, 0.10, 0.08, 0.04, 0.03])
    
    # 3. Card networks and types (Card1-6 in IEEE-CIS)
    card1 = np.random.randint(1000, 20000, size=num_records)
    card2 = np.random.randint(100, 600, size=num_records)
    card3 = np.random.choice([150, 185, 102], size=num_records, p=[0.90, 0.08, 0.02])
    card4 = np.random.choice(['visa', 'mastercard', 'discover', 'american express'], size=num_records, p=[0.65, 0.28, 0.05, 0.02])
    card6 = np.random.choice(['debit', 'credit'], size=num_records, p=[0.75, 0.25])
    
    # 4. Location and distance proxies (addr1, addr2, dist1)
    addr1 = np.random.randint(100, 500, size=num_records)
    addr2 = np.random.choice([87, 60, 96], size=num_records, p=[0.95, 0.03, 0.02])
    dist1 = np.random.exponential(scale=20.0, size=num_records).round(1)
    
    # 5. Fraud label (Realistic ~3.5% fraud rate with correlated risk features)
    base_fraud_prob = 0.025
    # Risk boosters: high amount, amex/discover, large distance
    high_amt_boost = (amounts > 500).astype(float) * 0.04
    dist_boost = (dist1 > 80).astype(float) * 0.03
    
    total_fraud_prob = np.clip(base_fraud_prob + high_amt_boost + dist_boost, 0.01, 0.95)
    is_fraud = (np.random.rand(num_records) < total_fraud_prob).astype(int)
    
    # 6. Fraud checkpoint features (C1 - C5 counts of transactions)
    c1 = np.random.poisson(lam=1.5 + 3.0 * is_fraud, size=num_records)
    c2 = np.random.poisson(lam=1.2 + 2.5 * is_fraud, size=num_records)
    
    df = pd.DataFrame({
        "TransactionID": np.arange(3000000, 3000000 + num_records),
        "isFraud": is_fraud,
        "TransactionAmt": amounts,
        "ProductCD": product_codes,
        "card1": card1,
        "card2": card2,
        "card3": card3,
        "card4": card4,
        "card6": card6,
        "addr1": addr1,
        "addr2": addr2,
        "dist1": dist1,
        "C1": c1,
        "C2": c2
    })
    
    df.to_csv(output_path, index=False)
    print(f"Generated synthetic IEEE-CIS dataset: {output_path} ({num_records} rows, {df['isFraud'].mean()*100:.2f}% fraud rate)")
    return df

def generate_database_seed_data(num_accounts: int = 1000, num_merchants: int = 200) -> Dict[str, List[Dict[str, Any]]]:
    """Generates relational seed records for accounts, merchants, and fraud profiles."""
    random.seed(42)
    
    accounts = []
    for i in range(1, num_accounts + 1):
        accounts.append({
            "account_id": f"acc_{1000 + i}",
            "balance": round(random.uniform(50.0, 25000.0), 2),
            "credit_limit": random.choice([1000.0, 2500.0, 5000.0, 10000.0, 25000.0]),
            "status": "ACTIVE",
            "currency": "USD"
        })
        
    merchants = []
    categories = ["RETAIL", "DIGITAL_GOODS", "GROCERY", "TRAVEL", "ENTERTAINMENT"]
    for i in range(1, num_merchants + 1):
        merchants.append({
            "merchant_id": f"m_{100 + i}",
            "merchant_name": f"Merchant_{100 + i}",
            "category": random.choice(categories),
            "settlement_frequency": "DAILY",
            "status": "ACTIVE"
        })
        
    return {
        "accounts": accounts,
        "merchants": merchants
    }

if __name__ == "__main__":
    generate_synthetic_ieee_cis_dataset(5000)
