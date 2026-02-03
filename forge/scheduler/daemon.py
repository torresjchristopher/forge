"""Workflow scheduler daemon.

Manages scheduled workflow execution with automatic triggering.
"""

import threading
import time
from pathlib import Path
from typing import Dict, Optional, Callable, List
from datetime import datetime
import json
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


logger = logging.getLogger(__name__)


class SchedulerDaemon:
    """Background daemon for workflow scheduling."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.home() / ".forge"
        self.base_dir.mkdir(exist_ok=True)
        
        self.scheduler = BackgroundScheduler()
        self.workflows: Dict[str, Dict] = {}
        self.running = False
        self.execution_queue: List[Dict] = []
        self.queue_file = self.base_dir / "execution_queue.json"
        self.scheduler_state_file = self.base_dir / "scheduler_state.json"
        
        # Load any previously scheduled workflows
        self._load_state()
    
    def start(self) -> bool:
        """Start the scheduler daemon."""
        if self.running:
            logger.warning("Scheduler already running")
            return False
        
        try:
            if not self.scheduler.running:
                self.scheduler.start()
            self.running = True
            logger.info("Scheduler daemon started")
            self._save_state()
            return True
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the scheduler daemon."""
        if not self.running:
            logger.warning("Scheduler not running")
            return False
        
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
            self.running = False
            logger.info("Scheduler daemon stopped")
            self._save_state()
            return True
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            return False
    
    def schedule_workflow(
        self,
        workflow_id: str,
        workflow_config: Dict,
        cron_expression: str,
        callback: Callable,
    ) -> bool:
        """Schedule a workflow for automatic execution.
        
        Args:
            workflow_id: Unique workflow identifier
            workflow_config: Workflow configuration dict
            cron_expression: Cron schedule (e.g., "0 2 * * *" for 2 AM daily)
            callback: Function to call when workflow executes
        
        Returns:
            True if successfully scheduled
        """
        try:
            trigger = CronTrigger.from_crontab(cron_expression)
            
            job = self.scheduler.add_job(
                self._execute_workflow_wrapper,
                trigger=trigger,
                args=(workflow_id, workflow_config, callback),
                id=workflow_id,
                name=workflow_id,
                replace_existing=True,
                misfire_grace_time=60,  # Allow 60s grace for missed executions
            )
            
            self.workflows[workflow_id] = {
                "config": workflow_config,
                "cron": cron_expression,
                "job_id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "enabled": True,
            }
            
            logger.info(f"Scheduled workflow: {workflow_id} ({cron_expression})")
            self._save_state()
            
            return True
        except Exception as e:
            logger.error(f"Failed to schedule workflow {workflow_id}: {e}")
            return False
    
    def unschedule_workflow(self, workflow_id: str) -> bool:
        """Remove a scheduled workflow.
        
        Args:
            workflow_id: Workflow to remove
        
        Returns:
            True if successfully unscheduled
        """
        try:
            self.scheduler.remove_job(workflow_id)
            if workflow_id in self.workflows:
                del self.workflows[workflow_id]
            
            logger.info(f"Unscheduled workflow: {workflow_id}")
            self._save_state()
            
            return True
        except Exception as e:
            logger.error(f"Failed to unschedule workflow {workflow_id}: {e}")
            return False
    
    def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a scheduled workflow."""
        try:
            job = self.scheduler.get_job(workflow_id)
            if job:
                job.pause()
                self.workflows[workflow_id]["enabled"] = False
                logger.info(f"Paused workflow: {workflow_id}")
                self._save_state()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to pause workflow {workflow_id}: {e}")
            return False
    
    def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow."""
        try:
            job = self.scheduler.get_job(workflow_id)
            if job:
                job.resume()
                self.workflows[workflow_id]["enabled"] = True
                logger.info(f"Resumed workflow: {workflow_id}")
                self._save_state()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to resume workflow {workflow_id}: {e}")
            return False
    
    def trigger_now(self, workflow_id: str) -> bool:
        """Manually trigger a workflow execution immediately.
        
        Args:
            workflow_id: Workflow to trigger
        
        Returns:
            True if successfully triggered
        """
        try:
            if workflow_id in self.workflows:
                job = self.scheduler.get_job(workflow_id)
                if job:
                    # Get the function and args from job
                    job.func(*job.args, **job.kwargs)
                    logger.info(f"Manually triggered workflow: {workflow_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to trigger workflow {workflow_id}: {e}")
            return False
    
    def backfill(self, workflow_id: str, start_date: str, end_date: str) -> int:
        """Execute a workflow for a date range (backfill).
        
        Args:
            workflow_id: Workflow to backfill
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Number of executions triggered
        """
        try:
            from datetime import datetime, timedelta
            
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            
            if workflow_id not in self.workflows:
                logger.error(f"Workflow not found: {workflow_id}")
                return 0
            
            job = self.scheduler.get_job(workflow_id)
            if not job:
                logger.error(f"Job not found: {workflow_id}")
                return 0
            
            count = 0
            current = start
            
            while current <= end:
                # Check if this date matches the cron schedule
                if self._matches_cron_schedule(current, self.workflows[workflow_id]["cron"]):
                    # Queue the execution
                    self.execution_queue.append({
                        "workflow_id": workflow_id,
                        "scheduled_date": current.isoformat(),
                        "status": "queued",
                        "created_at": datetime.now().isoformat(),
                    })
                    count += 1
                
                current += timedelta(days=1)
            
            logger.info(f"Backfilled {count} executions for {workflow_id}")
            self._save_queue()
            
            return count
        except Exception as e:
            logger.error(f"Failed to backfill workflow {workflow_id}: {e}")
            return 0
    
    def get_scheduled_workflows(self) -> List[Dict]:
        """Get all scheduled workflows."""
        result = []
        for workflow_id, config in self.workflows.items():
            job = self.scheduler.get_job(workflow_id)
            result.append({
                "workflow_id": workflow_id,
                "schedule": config.get("cron"),
                "enabled": config.get("enabled", True),
                "next_run": config.get("next_run"),
            })
        return result
    
    def get_execution_queue(self) -> List[Dict]:
        """Get pending executions in queue."""
        return self.execution_queue.copy()
    
    def process_queue(self, executor_callback: Callable) -> int:
        """Process pending executions from queue.
        
        Args:
            executor_callback: Function to execute workflows
        
        Returns:
            Number of executions processed
        """
        processed = 0
        remaining = []
        
        for execution in self.execution_queue:
            try:
                if execution["status"] == "queued":
                    # Execute the workflow
                    executor_callback(
                        execution["workflow_id"],
                        execution.get("scheduled_date"),
                    )
                    execution["status"] = "completed"
                    execution["completed_at"] = datetime.now().isoformat()
                    processed += 1
                
                remaining.append(execution)
            except Exception as e:
                logger.error(f"Failed to process execution: {e}")
                execution["status"] = "failed"
                execution["error"] = str(e)
                remaining.append(execution)
        
        self.execution_queue = remaining
        self._save_queue()
        
        return processed
    
    def _execute_workflow_wrapper(self, workflow_id: str, config: Dict, callback: Callable):
        """Wrapper for workflow execution (called by scheduler)."""
        try:
            callback(workflow_id, config)
        except Exception as e:
            logger.error(f"Error executing workflow {workflow_id}: {e}")
    
    @staticmethod
    def _matches_cron_schedule(dt: "datetime", cron_expr: str) -> bool:
        """Check if a datetime matches a cron expression."""
        try:
            trigger = CronTrigger.from_crontab(cron_expr)
            # APScheduler trigger.get_next_fire_time returns next execution
            # We check if dt is within the same window
            from datetime import timedelta
            next_fire = trigger.get_next_fire_time(None, dt - timedelta(minutes=1))
            
            # If next fire is within 1 minute of dt, it matches
            return abs((next_fire - dt).total_seconds()) < 60
        except Exception:
            return False
    
    def _save_state(self):
        """Save scheduler state to disk."""
        try:
            state = {
                "running": self.running,
                "workflows": self.workflows,
                "updated_at": datetime.now().isoformat(),
            }
            
            with open(self.scheduler_state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save scheduler state: {e}")
    
    def _load_state(self):
        """Load scheduler state from disk."""
        try:
            if self.scheduler_state_file.exists():
                with open(self.scheduler_state_file) as f:
                    state = json.load(f)
                    self.workflows = state.get("workflows", {})
                    logger.info(f"Loaded {len(self.workflows)} scheduled workflows")
        except Exception as e:
            logger.error(f"Failed to load scheduler state: {e}")
    
    def _save_queue(self):
        """Save execution queue to disk."""
        try:
            with open(self.queue_file, "w") as f:
                json.dump(self.execution_queue, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save execution queue: {e}")
    
    def _load_queue(self):
        """Load execution queue from disk."""
        try:
            if self.queue_file.exists():
                with open(self.queue_file) as f:
                    self.execution_queue = json.load(f)
                    logger.info(f"Loaded {len(self.execution_queue)} queued executions")
        except Exception as e:
            logger.error(f"Failed to load execution queue: {e}")
