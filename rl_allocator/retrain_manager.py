import os
import threading
from typing import Dict, Any, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from rl_allocator.registry import get_active_policy, register_policy
from rl_allocator.retrain_job import run_retrain_job, get_recent_workload_config
from rl_allocator.validation_gate import validate_new_policy
from explainability.logger import explainability_logger

class RetrainManager:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.lock = threading.Lock()
        self._is_running = False

    def start(self, interval_minutes: int = 60):
        if not self._is_running:
            self.scheduler.add_job(
                func=self.trigger_retrain,
                trigger=IntervalTrigger(minutes=interval_minutes),
                args=["SCHEDULED_TIMER"],
                id="periodic_retrain",
                replace_existing=True
            )
            self.scheduler.start()
            self._is_running = True
            
    def stop(self):
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False

    def trigger_retrain(self, trigger_reason: str, force_bad: bool = False) -> Dict[str, Any]:
        """
        Executes the full closed-loop retraining cycle:
        1. Run retrain job with dynamic snapshot
        2. Validate candidate against live policy
        3. If approved, register it and hot-swap
        """
        with self.lock:
            active_info = get_active_policy()
            if not active_info:
                return {"status": "ERROR", "message": "No active policy found in registry"}
                
            live_path = active_info["checkpoint_path"]
            
            # 1. Train candidate
            candidate_path = run_retrain_job(trigger_reason, force_bad)
            
            # 2. Validate
            snapshot = get_recent_workload_config()
            is_approved, cand_metrics, live_metrics = validate_new_policy(
                candidate_path=candidate_path,
                live_path=live_path,
                workload_config=snapshot
            )
            
            version_id = os.path.basename(candidate_path).replace(".zip", "")
            
            if is_approved:
                # 3. Promote & Register
                register_policy(
                    version=version_id,
                    checkpoint_path=candidate_path,
                    auth_p99_ms=cand_metrics["auth_p99_ms"],
                    compliance_pct=cand_metrics["compliance_pct"],
                    trigger_reason=trigger_reason
                )
                
                # Log success audit
                explainability_logger.log_decision(
                    variant="RETRAIN_MANAGER",
                    action={"action": "PROMOTED", "version": version_id},
                    auth_p99_ms=cand_metrics["auth_p99_ms"],
                    sla_budget_ms=10.0,
                    load_multiplier=snapshot.spike_multiplier
                )
                
                return {
                    "status": "PROMOTED",
                    "version": version_id,
                    "metrics": cand_metrics,
                    "live_metrics_comparison": live_metrics
                }
            else:
                # Log rejection audit
                explainability_logger.log_decision(
                    variant="RETRAIN_MANAGER",
                    action={"action": "REJECTED", "version": version_id},
                    auth_p99_ms=cand_metrics["auth_p99_ms"],
                    sla_budget_ms=10.0,
                    load_multiplier=snapshot.spike_multiplier
                )
                
                # Clean up bad candidate (optional, but good for space)
                try:
                    if os.path.exists(candidate_path):
                        os.remove(candidate_path)
                except Exception:
                    pass
                    
                return {
                    "status": "REJECTED",
                    "version": version_id,
                    "metrics": cand_metrics,
                    "live_metrics_comparison": live_metrics,
                    "reason": "Candidate degraded SLA or throughput compared to live baseline."
                }

retrain_manager = RetrainManager()
