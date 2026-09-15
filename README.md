# CAQI — Criticality-Aware Autonomous Query Intelligence

AI-based database performance optimization for online payment systems, using a Constrained Reinforcement Learning allocator to guarantee latency SLAs for auth-critical queries while letting lower-priority queries degrade gracefully under load.

> BCSE355L — Cloud Architecture Design | Project Phase-I & II
> VIT Vellore

---

## Team

| Member | Reg. No. | Role |
|---|---|---|
| **Pranit Mathur** | 24BIT0497 | 
| **Aniket Agrawal** | 24BIT0533 | 
| **Romit Raman** | 24BIT0558 | 

---

## Work Division

### Pranit Mathur
- CAQI Dashboard: live view of query mix by tier (auth-critical / settlement-critical / analytical)
- Real-time latency vs. SLA budget visualization per tier
- Explainability panel — human-readable justification feed pulled from CloudWatch/S3 logs
- Constraint-violation view — highlights auth-critical p99 latency breaches, with baseline (Aurora Auto Scaling) comparison chart
- Admin controls: trigger load-spike simulation, view retraining status/history
- **Stack:** React, Recharts/Chart.js, REST calls to backend API

###   Aniket Agrawal
- Criticality tagging service — classifies incoming requests as auth/settlement/analytical based on calling service
- Constrained RL Resource Allocator — CMDP logic (state, action, reward, constraint) and policy inference endpoint
- API layer consumed by the frontend — query mix stats, latency stats, explainability logs, constraint-violation events
- Explainability Logger — generates justification text for each routing/index/cache decision
- Retraining pipeline logic (invoked by Step Functions)
- **Stack:** Python (FastAPI/Flask), stable-baselines3 / custom CMDP implementation

###  Romit Raman
- Provisioning: RDS Proxy, Aurora, DynamoDB, ElastiCache
- Backend deployment via ECS Fargate / Lambda, exposed through API Gateway / ALB
- SageMaker (training/hosting the RL policy) and Step Functions (orchestrates the retraining loop)
- CloudWatch (logs/alarms/Performance Insights), S3 (explainability log archive), SNS (violation alerts)
- IAM roles / Cognito access control, deployment scripts (CDK/Terraform/CloudFormation)
- Load-testing setup: synthetic TPC-style workload generator + IEEE-CIS Fraud Detection dataset feed for evaluation runs

### 🤝 Shared
- Backend API contract definition (agreed early so frontend/infra aren't blocked)
- End-to-end integration and demo run
- Final benchmarking against all six AWS Well-Architected Framework pillars

---

## Architecture

CAQI tags every incoming query/connection at the RDS Proxy layer, routes it through a Constrained Markov Decision Process-based RL allocator, and logs a human-readable justification for every autonomous decision:

```
Incoming Payment Request
        ↓
Edge / Security (WAF, Shield, CloudFront)
        ↓
Application Tier (API Gateway, Payment Microservices)
        ↓
CAQI Tier (RDS Proxy tagging → RL Allocator → SageMaker)
        ↓
Data Tier (Aurora, DynamoDB, ElastiCache)
        ↓
Observability & Reliability (CloudWatch, SNS, Step Functions)
```

---

## Datasets

| Dataset | Purpose |
|---|---|
| [IEEE-CIS Fraud Detection](https://www.kaggle.com/c/ieee-fraud-detection) | Realistic fraud-relevant feature distribution for auth-critical query simulation |
| Synthetic TPC-style payment workload | Simulates auth/settlement/analytical query mix for training and evaluating the RL allocator |

---

## Repository

[github.com/ramanromit/Ai-Based-Db-Optimization](https://github.com/ramanromit/Ai-Based-Db-Optimization)
