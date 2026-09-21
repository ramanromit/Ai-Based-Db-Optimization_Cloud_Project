import json
import os
import time
from typing import List, Dict, Optional, Any
from filelock import FileLock

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "checkpoints", "registry.json")


def _get_lock_path(registry_path: str = None) -> str:
    return (registry_path or REGISTRY_PATH) + ".lock"


def _read_registry(registry_path: str = None) -> List[Dict[str, Any]]:
    path = registry_path or REGISTRY_PATH
    lock = FileLock(_get_lock_path(path))
    with lock:
        if not os.path.exists(path):
            return []
        with open(path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []


def _atomic_write(path: str, data: List[Dict[str, Any]]):
    tmp_path = path + f".{os.getpid()}.{int(time.time() * 1_000_000)}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def _write_registry(data: List[Dict[str, Any]], registry_path: str = None):
    path = registry_path or REGISTRY_PATH
    lock = FileLock(_get_lock_path(path))
    with lock:
        _atomic_write(path, data)


def _append_policy(entry: Dict[str, Any], registry_path: str = None):
    path = registry_path or REGISTRY_PATH
    lock = FileLock(_get_lock_path(path))
    with lock:
        if not os.path.exists(path):
            data = []
        else:
            with open(path, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        data.append(entry)
        _atomic_write(path, data)


def initialize_registry(initial_checkpoint: str, auth_p99_ms: Optional[float] = None, compliance_pct: Optional[float] = None):
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    if not os.path.exists(REGISTRY_PATH):
        _write_registry([{
            "version": "v1.0.0_initial",
            "checkpoint_path": initial_checkpoint,
            "trained_at": time.time(),
            "auth_p99_ms": auth_p99_ms,
            "compliance_pct": compliance_pct,
            "metrics_source": "unmeasured_initialization" if auth_p99_ms is None or compliance_pct is None else "measured",
            "is_live": True,
            "trigger_reason": "SYSTEM_INIT"
        }])


def get_active_policy() -> Optional[Dict[str, Any]]:
    registry = _read_registry()
    for entry in registry:
        if entry.get("is_live"):
            return entry
    return registry[-1] if registry else None


def get_history() -> List[Dict[str, Any]]:
    return _read_registry()


def register_policy(version: str, checkpoint_path: str, auth_p99_ms: float, compliance_pct: float, trigger_reason: str) -> str:
    path = REGISTRY_PATH
    lock = FileLock(_get_lock_path(path))
    with lock:
        if not os.path.exists(path):
            data = []
        else:
            with open(path, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        for entry in data:
            entry["is_live"] = False
        data.append({
            "version": version,
            "checkpoint_path": checkpoint_path,
            "trained_at": time.time(),
            "auth_p99_ms": auth_p99_ms,
            "compliance_pct": compliance_pct,
            "is_live": True,
            "trigger_reason": trigger_reason
        })
        _atomic_write(path, data)
    return version


def rollback_policy(version: str) -> bool:
    path = REGISTRY_PATH
    lock = FileLock(_get_lock_path(path))
    with lock:
        if not os.path.exists(path):
            return False
        with open(path, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return False
        target = next((e for e in data if e["version"] == version), None)
        if not target:
            return False
        for entry in data:
            entry["is_live"] = (entry["version"] == version)
        _atomic_write(path, data)
    return True
