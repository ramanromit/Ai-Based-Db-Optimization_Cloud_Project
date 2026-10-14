from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ThreatTier(str, Enum):
    NORMAL = "NORMAL"
    SUSPICIOUS = "SUSPICIOUS"
    THREAT = "THREAT"


class AnomalyVerdict(BaseModel):
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Anomaly risk index (0.0 clean to 1.0 malicious)")
    is_quarantined: bool = Field(default=False, description="True if query is routed to security quarantine")
    threat_tier: ThreatTier = Field(default=ThreatTier.NORMAL, description="Categorical threat severity")
    flagged_reasons: List[str] = Field(default_factory=list, description="Specific triggers flagged by detector")
    client_ip: Optional[str] = None
    account_id: Optional[str] = None

