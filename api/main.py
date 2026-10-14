import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.routes import router
from api.websocket import websocket_stream_endpoint
from storage.init_db import init_database
from explainability.logger import explainability_logger

load_dotenv()

def _bootstrap_registry():
    """Ensure the policy registry has an initial entry so retrain can run."""
    try:
        from rl_allocator.registry import initialize_registry
        checkpoint = os.path.join("rl_allocator", "checkpoints", "constrained_seed_42.zip")
        if os.path.exists(checkpoint):
            initialize_registry(
                initial_checkpoint=checkpoint,
                auth_p99_ms=8.5,
                compliance_pct=97.2,
            )
            print("[Registry] Bootstrapped with constrained_seed_42 checkpoint.")
        else:
            print("[Registry] Warning: constrained_seed_42.zip not found — retrain may fail.")
    except Exception as e:
        print(f"[Registry Bootstrap Error]: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables and seed data exist
    # Startup: DB tables + registry bootstrap
    try:
        init_database()
    except Exception as e:
        print(f"[Lifespan DB Init Notice]: {e}")
    _bootstrap_registry()
    yield
    # Shutdown: flush and close background logger
    explainability_logger.close()

app = FastAPI(
    title="CAQI — Criticality-Aware Autonomous Query Intelligence",
    description="Autonomous database resource allocation for online payment systems using Constrained RL",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router at both /api prefix and root level
app.include_router(router, prefix="/api", tags=["api"])
app.include_router(router, prefix="", tags=["root"])

# WebSocket routes for both /ws/stream and /stream
app.add_api_websocket_route("/ws/stream", websocket_stream_endpoint)
app.add_api_websocket_route("/stream", websocket_stream_endpoint)

@app.get("/")
@app.get("/status")
def status_info():
    return {
        "system": "CAQI Backend Engine",
        "status": "ONLINE",
        "docs": "/docs",
        "stream_endpoint": "/ws/stream",
        "endpoints": {
            "websocket_stream": "/ws/stream",
            "stream_endpoint": "/ws/stream",
            "metrics": "/metrics",
            "explainability": "/explainability",
            "trigger_spike": "/trigger-spike",
            "compare": "/compare"
        }
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)
