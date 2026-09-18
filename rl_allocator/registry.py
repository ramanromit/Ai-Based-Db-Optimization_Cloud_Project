import json
import os
import time
import shutil
from typing import List, Dict, Optional, Any
from filelock import FileLock

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "checkpoints", "registry.json")
LOCK_PATH = REGISTRY_PATH + ".lock"

def _read_registry() -> List[Dict[str, Any]]:
    if not os.path.exists(REGISTRY_PATH):
        return []
    with open(REGISTRY_PATH, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
    with FileLock(LOCK_PATH):
        if not os.path.exists(REGISTRY_PATH):

def _get_lock_path(registry_path: str) -> str:
    return registry_path + ".lock"


def _read_registry(registry_path: str = None) -> List[Dict[str, Any]]:
    path = registry_path or REGISTRY_PATH
    lock = FileLock(_get_lock_path(path))
    with lock:
        if not os.path.exists(path):
            return []
        with open(REGISTRY_PATH, "r") as f:
        with open(path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

def _write_registry(data: List[Dict[str, Any]]):
    tmp_path = REGISTRY_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    # os.replace is atomic on POSIX, and practically atomic on modern Windows 
    # replacing the destination file if it exists.
    os.replace(tmp_path, REGISTRY_PATH)
    with FileLock(LOCK_PATH):
        # Write to a temporary file unique to this thread/process to avoid conflicts
        tmp_path = REGISTRY_PATH + f".{os.getpid()}.{time.time()}.tmp"

def _write_registry(data: List[Dict[str, Any]], registry_path: str = None):
    path = registry_path or REGISTRY_PATH
    lock = FileLock(_get_lock_path(path))
    with lock:
        tmp_path = path + f".{os.getpid()}.{int(time.time() * 1_000_000)}.tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, REGISTRY_PATH)
        os.replace(tmp_path, path)


def _append_policy(entry: Dict[str, Any], registry_path: str = None):
    """Atomically append a policy entry under a single lock (no TOCTOU)."""
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
        tmp_path = path + f".{os.getpid()}.{int(time.time() * 1_000_000)}.tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)


def initialize_registry(initial_checkpoint: str, auth_p99_ms: float = 4.40, compliance_pct: float = 100.0):
    """Seed the registry with the initial trained model if it doesn't exist."""
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    if not os.path.exists(REGISTRY_PATH):
        _write_registry([{
            "version": "v1.0.0_initial",
            "checkpoint_path": initial_checkpoint,
            "trained_at": time.time(),
            "auth_p99_ms": auth_p99_ms,
            "compliance_pct": compliance_pct,
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

def register_policy(version: str, checkpoint_path: str, auth_p99_ms: float, compliance_pct: float, trigger_reason: str):
    registry = _read_registry()
    
    # Demote current live policies
    for entry in registry:
        entry["is_live"] = False
        
    registry.append({
        "version": version,
        "checkpoint_path": checkpoint_path,
        "trained_at": time.time(),
        "auth_p99_ms": auth_p99_ms,
        "compliance_pct": compliance_pct,
        "is_live": True,
        "trigger_reason": trigger_reason
    })
    
    _write_registry(registry)

def register_policy(version: str, checkpoint_path: str, auth_p99_ms: float, compliance_pct: float, trigger_reason: str) -> str:
    # Read-modify-write under lock
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
        tmp_path = path + f".{os.getpid()}.{int(time.time() * 1_000_000)}.tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    return version


def rollback_policy(version: str) -> bool:
    registry = _read_registry()
    target_entry = None
    for entry in registry:
        if entry["version"] == version:
            target_entry = entry
            break
            
    if not target_entry:
        return False
        
    for entry in registry:
        entry["is_live"] = (entry["version"] == version)
        
    _write_registry(registry)
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
        tmp_path = path + f".{os.getpid()}.{int(time.time() * 1_000_000)}.tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    return True
