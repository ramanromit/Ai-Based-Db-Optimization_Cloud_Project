import asyncio
import json
import time
from typing import Any, Dict, Set

from fastapi import WebSocket, WebSocketDisconnect

from api.live_runtime import live_runtime


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        dead = set()
        data = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                dead.add(connection)
        for connection in dead:
            self.active_connections.discard(connection)


manager = ConnectionManager()


def build_stream_message(query, result, action, metrics, active, multiplier, source="stream"):
    return {
        "type": "QUERY_PROCESSED",
        "query_id": result.query_id,
        "timestamp": round(time.time(), 3),
        "service_name": query.service_name,
        "tier": result.tier.value,
        "query_type": query.query_type.value,
        "latency_ms": round(result.latency_ms, 2),
        "sla_budget_ms": query.latency_budget_ms,
        "sla_violated": result.violated_sla,
        "is_cache_hit": result.is_cache_hit,
        "target_route": result.target_route,
        "active_variant": live_runtime.variant,
        "spike_active": active,
        "payload_meta": query.payload_meta,
        "action": action,
        "rolling_metrics": metrics,
        "source": source,
        "risk_score": round(result.risk_score, 3),
        "is_quarantined": result.is_quarantined,
        "risk_flags": result.risk_flags,
    }


async def websocket_stream_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    async def receive_controls():
        try:
            while True:
                message = json.loads(await websocket.receive_text())
                command = message.get("command")
                if command == "set_variant":
                    try:
                        live_runtime.set_variant(message.get("variant", "constrained"))
                        await websocket.send_text(json.dumps({
                            "type": "SYSTEM_NOTIFICATION",
                            "message": f"Switched active allocator variant to {live_runtime.variant.upper()}",
                        }))
                    except ValueError as exc:
                        await websocket.send_text(json.dumps({
                            "type": "SYSTEM_NOTIFICATION",
                            "message": f"Could not switch allocator variant: {exc}",
                        }))
                elif command == "trigger_spike":
                    multiplier = float(message.get("multiplier", 5.0))
                    duration = float(message.get("duration", 10.0))
                    live_runtime.trigger_spike(multiplier, duration)
                    await websocket.send_text(json.dumps({
                        "type": "SYSTEM_NOTIFICATION",
                        "message": f"Triggered {multiplier}x load spike for {duration}s",
                    }))
                elif command == "clear_spike":
                    live_runtime.clear_spike()
                    await websocket.send_text(json.dumps({
                        "type": "SYSTEM_NOTIFICATION",
                        "message": "Traffic spike cleared",
                    }))
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            print(f"[WebSocket Control Loop Error]: {exc}")

    control_task = asyncio.create_task(receive_controls())
    try:
        while True:
            query = live_runtime.generator.generate_single_query()
            result, action, metrics, active, multiplier = live_runtime.execute(query)
            await websocket.send_text(json.dumps(
                build_stream_message(query, result, action, metrics, active, multiplier)
            ))
            await asyncio.sleep(0.08)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
    finally:
        control_task.cancel()
