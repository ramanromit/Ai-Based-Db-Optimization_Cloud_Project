import asyncio
import json
import time
import numpy as np
from typing import Set, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

from tagger.models import CriticalityTier
from workload_gen.generator import WorkloadGenerator
from storage.executor import DatabaseProxyExecutor
from evaluation.harness import load_policy
from explainability.logger import explainability_logger

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
        for conn in self.active_connections:
            try:
                await conn.send_text(data)
            except Exception:
                dead.add(conn)
        for d in dead:
            self.active_connections.discard(d)

manager = ConnectionManager()

async def websocket_stream_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint streaming live query events and autonomous resource allocations.
    Allows real-time interaction (variant switching, spike triggers) from UI clients.
    """
    await manager.connect(websocket)
    
    current_variant = "constrained"
    policy = load_policy(current_variant)
    generator = WorkloadGenerator()
    executor = DatabaseProxyExecutor()
    
    rolling_auth = [3.5]
    rolling_settle = [20.0]
    rolling_analyt = [110.0]

    async def receive_controls():
        nonlocal current_variant, policy
        try:
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                cmd = msg.get("command")
                
                if cmd == "set_variant":
                    var = msg.get("variant", "constrained")
                    if var in ["baseline", "unconstrained", "constrained"]:
                        current_variant = var
                        policy = load_policy(var)
                        await websocket.send_text(json.dumps({
                            "type": "SYSTEM_NOTIFICATION",
                            "message": f"Switched active allocator variant to {var.upper()}"
                        }))
                        
                elif cmd == "trigger_spike":
                    mult = float(msg.get("multiplier", 5.0))
                    dur = float(msg.get("duration", 10.0))
                    generator.trigger_spike(multiplier=mult, duration_seconds=dur)
                    await websocket.send_text(json.dumps({
                        "type": "SYSTEM_NOTIFICATION",
                        "message": f"Triggered {mult}x load spike for {dur}s"
                    }))
                    
                elif cmd == "clear_spike":
                    generator.clear_spike()
                    await websocket.send_text(json.dumps({
                        "type": "SYSTEM_NOTIFICATION",
                        "message": "Traffic spike cleared"
                    }))
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"[WebSocket Control Loop Error]: {e}")

    # Launch control listener in background
    control_task = asyncio.create_task(receive_controls())

    try:
        while True:
            # Check spike state
            in_spike = generator.check_spike_status()
            spike_mult = generator.spike_multiplier if in_spike else 1.0

            # Construct state vector
            obs = np.array([
                0.15 * spike_mult,
                0.35 * spike_mult,
                0.50 * spike_mult,
                np.percentile(rolling_auth, 99) / 10.0,
                np.percentile(rolling_settle, 99) / 150.0,
                np.percentile(rolling_analyt, 99) / 1000.0,
                1.0 if in_spike else 0.0,
                0.8 if (in_spike and current_variant == "baseline") else 0.1,
                0.85 if current_variant == "constrained" else 0.5
            ], dtype=np.float32)

            # Predict action
            if current_variant == "baseline":
                action, _ = policy.predict(obs)
            else:
                action, _ = policy.predict(obs, deterministic=True)

            pool_prio, replica_route, cache_ttl, analyt_throttle = [int(a) for a in action]

            # Generate and execute query
            query = generator.generate_single_query()
            res = executor.execute_query(
                query=query,
                action_pool_priority=pool_prio,
                action_replica_routing=replica_route,
                action_cache_ttl=cache_ttl,
                action_analytical_throttle=analyt_throttle,
                active_load_multiplier=spike_mult
            )

            # Update rolling percentiles
            if res.tier == CriticalityTier.AUTH_CRITICAL:
                rolling_auth.append(res.latency_ms)
                if len(rolling_auth) > 30:
                    rolling_auth.pop(0)
            elif res.tier == CriticalityTier.SETTLEMENT_CRITICAL:
                rolling_settle.append(res.latency_ms)
                if len(rolling_settle) > 30:
                    rolling_settle.pop(0)
            else:
                rolling_analyt.append(res.latency_ms)
                if len(rolling_analyt) > 30:
                    rolling_analyt.pop(0)

            auth_p99_now = float(np.percentile(rolling_auth, 99))
            
            # Emit live stream message to UI
            # Emit live stream message to UI with enriched payment payload metadata
            stream_msg = {
                "type": "QUERY_PROCESSED",
                "query_id": res.query_id,
                "timestamp": round(time.time(), 3),
                "service_name": query.service_name,
                "tier": res.tier.value,
                "query_type": query.query_type.value,
                "latency_ms": round(res.latency_ms, 2),
                "sla_budget_ms": query.latency_budget_ms,
                "sla_violated": res.violated_sla,
                "is_cache_hit": res.is_cache_hit,
                "target_route": res.target_route,
                "active_variant": current_variant,
                "spike_active": in_spike,
                "payload_meta": query.payload_meta,
                "action": {
                    "pool_priority": pool_prio,
                    "replica_routing": replica_route,
                    "cache_ttl": cache_ttl,
                    "analytical_throttle": analyt_throttle
                },
                "rolling_metrics": {
                    "auth_p99_ms": round(auth_p99_now, 2),
                    "settle_p99_ms": round(float(np.percentile(rolling_settle, 99)), 2),
                    "analyt_p99_ms": round(float(np.percentile(rolling_analyt, 99)), 2)
                }
            }

            await websocket.send_text(json.dumps(stream_msg))
            await asyncio.sleep(0.08) # ~12 events per second for smooth UI rendering

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
    finally:
        control_task.cancel()

