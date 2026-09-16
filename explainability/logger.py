import os
import time
import json
import sqlite3
import queue
import threading
from typing import Dict, Any, List, Optional
from explainability.templates import generate_justification

DEFAULT_DB_PATH = os.getenv("EXPLAINABILITY_DB_PATH", "caqi_explainability.sqlite")
DEFAULT_JSONL_PATH = "explainability_audit.jsonl"

class ExplainabilityLogger:
    """
    Asynchronous, off-hot-path audit logger for autonomous DB resource decisions.
    Buffers events in memory and writes concurrently to SQLite and JSONL to avoid
    introducing latency on the critical query processing path.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ExplainabilityLogger, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: str = DEFAULT_DB_PATH, jsonl_path: str = DEFAULT_JSONL_PATH):
        if self._initialized:
            return
            
        self.db_path = db_path
        self.jsonl_path = jsonl_path
        self.queue = queue.Queue(maxsize=10000)
        self.stop_event = threading.Event()
        
        self._init_sqlite()
        
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        self._initialized = True

    def _init_sqlite(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS explainability_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    variant TEXT NOT NULL,
                    load_multiplier REAL NOT NULL,
                    auth_p99_ms REAL NOT NULL,
                    sla_budget_ms REAL NOT NULL,
                    pool_priority INTEGER NOT NULL,
                    replica_routing INTEGER NOT NULL,
                    cache_ttl INTEGER NOT NULL,
                    analytical_throttle INTEGER NOT NULL,
                    sla_violated INTEGER NOT NULL,
                    justification_text TEXT NOT NULL
                )
            """)
            conn.commit()

    def _worker(self):
        """Background thread consumer processing queued log events."""
        while not self.stop_event.is_set() or not self.queue.empty():
            try:
                record = self.queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                # 1. Write to SQLite
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO explainability_logs (
                            timestamp, variant, load_multiplier, auth_p99_ms, sla_budget_ms,
                            pool_priority, replica_routing, cache_ttl, analytical_throttle,
                            sla_violated, justification_text
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record["timestamp"],
                        record["variant"],
                        record["load_multiplier"],
                        record["auth_p99_ms"],
                        record["sla_budget_ms"],
                        record["action"]["pool_priority"],
                        record["action"]["replica_routing"],
                        record["action"]["cache_ttl"],
                        record["action"]["analytical_throttle"],
                        1 if record["sla_violated"] else 0,
                        record["justification_text"]
                    ))
                    conn.commit()

                # 2. Append to JSONL audit file
                with open(self.jsonl_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")

            except Exception as e:
                print(f"[ExplainabilityLogger Worker Error]: {e}")
            finally:
                self.queue.task_done()

    def log_decision(
        self,
        variant: str,
        action: Dict[str, Any],
        auth_p99_ms: float,
        sla_budget_ms: float = 10.0,
        load_multiplier: float = 1.0,
        queue_saturation: float = 0.1
    ) -> Dict[str, Any]:
        """Queues an autonomous decision record for async persistence."""
        now = time.time()
        justification = generate_justification(
            variant=variant,
            action=action,
            auth_p99=auth_p99_ms,
            budget_ms=sla_budget_ms,
            spike_factor=load_multiplier,
            queue_saturation=queue_saturation
        )
        
        record = {
            "timestamp": now,
            "variant": variant,
            "load_multiplier": load_multiplier,
            "auth_p99_ms": round(auth_p99_ms, 2),
            "sla_budget_ms": sla_budget_ms,
            "action": action,
            "sla_violated": auth_p99_ms > sla_budget_ms,
            "justification_text": justification
        }
        
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            print("[ExplainabilityLogger Warning]: Log queue is full, dropping event to protect hot path.")
            
        return record

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Reads the most recent decisions from SQLite for UI presentation."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, variant, load_multiplier, auth_p99_ms, sla_budget_ms,
                       pool_priority, replica_routing, cache_ttl, analytical_throttle,
                       sla_violated, justification_text
                FROM explainability_logs
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            
            results = []
            for r in rows:
                results.append({
                    "timestamp": r["timestamp"],
                    "variant": r["variant"],
                    "load_multiplier": r["load_multiplier"],
                    "auth_p99_ms": r["auth_p99_ms"],
                    "sla_budget_ms": r["sla_budget_ms"],
                    "action": {
                        "pool_priority": r["pool_priority"],
                        "replica_routing": r["replica_routing"],
                        "cache_ttl": r["cache_ttl"],
                        "analytical_throttle": r["analytical_throttle"],
                    },
                    "sla_violated": bool(r["sla_violated"]),
                    "justification_text": r["justification_text"]
                })
            return results

    def close(self):
        """Flushes queue and terminates worker thread."""
        self.queue.join()
        self.stop_event.set()
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)

# Global singleton logger
explainability_logger = ExplainabilityLogger()

