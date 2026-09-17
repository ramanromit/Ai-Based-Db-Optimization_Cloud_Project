# CAQI — Criticality-Aware Autonomous Query Intelligence

**Course**: BCSE355L — Cloud Architecture Design  
**Title**: AI-Based Database Performance Optimization for Online Payment Systems Using Autonomous Query Intelligence

---

## 📌 Executive Summary

Online payment databases handle two fundamentally contrasting workloads:
1. **Auth-Critical Operations (P0)**: Single-digit millisecond latency budgets for payment authorizations, balance checks, idempotency lookups, and fraud screening.
2. **Settlement & Analytical Queries (P1/P2)**: High-volume batch settlement, ledger reconciliation, and heavy BI aggregations that can tolerate delay.

Existing database auto-tuning systems optimize workload-wide averages, treating every query as equally important. Under load spikes, this causes severe SLA breaches on the payment path.

**CAQI** addresses this problem by:
- Structurally tagging incoming queries into criticality tiers (`AUTH_CRITICAL`, `SETTLEMENT_CRITICAL`, `ANALYTICAL`) without inspecting sensitive transaction payloads.
- Formulating database resource management (dedicated connection pool reservation, read-replica routing, cache TTL, query throttling) as a **Constrained Markov Decision Process (CMDP)**.
- Enforcing a hard probabilistic constraint on auth-critical p99 latency (`P(auth_p99 <= 10.0ms) >= 1 - delta`) via dual Lagrangian relaxation in PPO.
- Generating off-hot-path human-readable decision justifications in real time.
- Providing an interactive, Datadog-style React 18 dashboard displaying live telemetry, load spike controls, policy variant switching, and IEEE-CIS payment transaction inspection.

---

## 🏗 System Architecture

```
CloudProject/
├── api/                    # FastAPI REST & WebSocket streaming server
│   ├── main.py             # App entrypoint & CORS setup
│   ├── routes.py           # /metrics, /explainability, /trigger-spike, /compare, /health
│   └── websocket.py        # /ws/stream live query telemetry broadcasting
├── tagger/                 # Structural criticality tagger (zero payload parsing)
├── workload_gen/           # TPC-C payment & IEEE-CIS workload generator
├── storage/                # Database proxy simulator, Postgres/SQLite, Redis stand-in
├── rl_allocator/           # Gymnasium CMDP environment & Constrained PPO agent
│   ├── env.py              # 9-dim state, MultiDiscrete action, Lagrangian reward
│   └── train.py            # Model training runner
├── baseline/               # Criticality-agnostic Aurora baseline allocator
├── explainability/         # Asynchronous off-hot-path audit logger & justification templates
├── evaluation/             # Standardized 3-way ablation study harness & plot generator
└── caqi-dashboard/         # React 18 + TypeScript + Vite + Tailwind CSS dashboard
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** (Python 3.12 verified)
- **Node.js 20+** & **npm**

---

### 1. Start the Backend API & Telemetry Server

```powershell
# Open Terminal 1
cd C:\Users\HP\Desktop\CloudProject

# Run database seed initialization (if needed)
python -m storage.init_db

# Start FastAPI Uvicorn Server on port 8000
python -m uvicorn api.main:app --reload --port 8000
```
- Interactive API Documentation: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/api/health`

---

### 2. Start the React Frontend Dashboard

```powershell
# Open Terminal 2
cd C:\Users\HP\Desktop\CloudProject\caqi-dashboard

# Start Vite Development Server
npm.cmd run dev
```
- Access Dashboard: `http://localhost:5173`

---

## 📊 Standardized Ablation Benchmark Results

Evaluated across matched random seeds (42, 100, 2024) under an identical 5.0x traffic burst:

| Allocator Variant | Auth P99 Latency | Auth SLA Compliance (≤10ms) | SLA Violations Count | Throughput (QPS) |
|-------------------|:----------------:|:---------------------------:|:--------------------:|:----------------:|
| **Aurora Baseline (Agnostic)** | **148.76 ms** | **79.18%** | 20.5 | 7,037 QPS |
| **Unconstrained RL** | **108.46 ms** (burst) | 88.40% | 5.2 | 1,484 QPS |
| **Constrained CAQI (Ours)** | **4.40 ms** | **100.00%** | **0.0** | 1,344 QPS |

---

## 🧪 Running Tests & Evaluation

```powershell
# 1. Run all 25 backend & API unit tests
python -m pytest tests/ -v

# 2. Run the standardized 3-way ablation study harness
python -m evaluation.harness --queries 1200 --seeds 42 100 2024

# 3. Generate benchmark charts
python -m evaluation.visualize

# 4. Verify Frontend Production Build
cd caqi-dashboard
npm.cmd run build
```

---

## 📜 AWS Well-Architected Framework Alignment

- **Operational Excellence**: Non-blocking async explainability logging off the hot path.
- **Security**: Structural caller metadata tagging; zero inspection of sensitive raw SQL payloads.
- **Reliability**: CMDP Lagrangian formulation bounding P99 SLA breaches ($\le 10$ms).
- **Performance Efficiency**: Dedicated priority pools, read-replica offloading, and Redis TTL tuning.
- **Cost Optimization**: Sheds non-critical analytical compute under peak load instead of expensive DB cluster auto-scaling.
- **Sustainability**: Prevents over-provisioning compute resources during short-lived traffic spikes.

