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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables and seed data exist
    try:
        init_database()
    except Exception as e:
        print(f"[Lifespan DB Init Notice]: {e}")
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

app.include_router(router)
app.add_api_websocket_route("/ws/stream", websocket_stream_endpoint)

@app.get("/")
def root():
    return {
        "system": "CAQI Backend Engine",
        "status": "ONLINE",
        "docs": "/docs",
        "stream_endpoint": "/ws/stream"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)

