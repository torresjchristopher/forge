"""Scheduler manager: integrates daemon, workflows, and execution."""

from pathlib import Path
from typing import Dict, Optional
import logging
import json
from datetime import datetime

from forge.scheduler.daemon import SchedulerDaemon
from forge.orchestration.executor import WorkflowExecutor


logger = logging.getLogger(__name__)


class SchedulerManager:
    """Manages the complete scheduling system."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.home() / ".forge"
        self.daemon = SchedulerDaemon(self.base_dir)
        self.executor = WorkflowExecutor(self.base_dir)
        self.execution_log = self.base_dir / "scheduled_executions.json"
    
    def schedule_workflow(self, workflow_config: Dict, cron_expression: str) -> bool:
        """Schedule a workflow for automatic execution.
        
        Args:
            workflow_config: Workflow configuration
            cron_expression: Cron schedule (e.g., "0 2 * * *")
        
        Returns:
            True if successfully scheduled
        """
        workflow_id = workflow_config.get("name")
        if not workflow_id:
            logger.error("Workflow config missing 'name' field")
            return False
        
        # Start daemon if not running
        if not self.daemon.running:
            self.daemon.start()
        
        # Schedule the workflow
        success = self.daemon.schedule_workflow(
            workflow_id,
            workflow_config,
            cron_expression,
            self._execute_workflow,
        )
        
        return success
    
    def unschedule_workflow(self, workflow_id: str) -> bool:
        """Remove a scheduled workflow."""
        return self.daemon.unschedule_workflow(workflow_id)
    
    def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a workflow."""
        return self.daemon.pause_workflow(workflow_id)
    
    def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow."""
        return self.daemon.resume_workflow(workflow_id)
    
    def trigger_now(self, workflow_id: str) -> bool:
        """Manually trigger a workflow."""
        return self.daemon.trigger_now(workflow_id)
    
    def backfill(self, workflow_id: str, start_date: str, end_date: str) -> int:
        """Backfill workflow executions for a date range."""
        count = self.daemon.backfill(workflow_id, start_date, end_date)
        
        if count > 0:
            # Process the queue immediately
            self.daemon.process_queue(self._execute_workflow)
        
        return count
    
    def get_status(self) -> Dict:
        """Get scheduler status."""
        return {
            "running": self.daemon.running,
            "scheduled_workflows": len(self.daemon.workflows),
            "pending_executions": len(self.daemon.execution_queue),
            "workflows": self.daemon.get_scheduled_workflows(),
        }
    
    def start(self) -> bool:
        """Start the scheduler daemon."""
        return self.daemon.start()
    
    def stop(self) -> bool:
        """Stop the scheduler daemon."""
        return self.daemon.stop()
    
    def _execute_workflow(self, workflow_id: str, scheduled_date: Optional[str] = None):
        """Execute a workflow and log the result."""
        try:
            # Get workflow config
            workflow_config = self.daemon.workflows.get(workflow_id, {}).get("config")
            if not workflow_config:
                logger.error(f"Workflow config not found: {workflow_id}")
                return
            
            logger.info(f"Executing scheduled workflow: {workflow_id}")
            
            # Execute via executor
            result = self.executor.execute_workflow(workflow_config)
            
            # Log the execution
            self._log_scheduled_execution(workflow_id, scheduled_date, result)
            
            logger.info(f"Completed scheduled workflow: {workflow_id} - {result.get('status')}")
        
        except Exception as e:
            logger.error(f"Error executing scheduled workflow {workflow_id}: {e}")
            self._log_scheduled_execution(
                workflow_id,
                scheduled_date,
                {"status": "error", "error": str(e)},
            )
    
    def _log_scheduled_execution(self, workflow_id: str, scheduled_date: Optional[str], result: Dict):
        """Log a scheduled execution."""
        try:
            executions = []
            if self.execution_log.exists():
                with open(self.execution_log) as f:
                    executions = json.load(f)
            
            # Keep last 500 executions (auto-prune)
            if len(executions) >= 500:
                executions = executions[-499:]
            
            execution_record = {
                **result,
                "workflow_id": workflow_id,
                "scheduled_date": scheduled_date,
                "executed_at": datetime.now().isoformat(),
            }
            
            executions.append(execution_record)
            
            with open(self.execution_log, "w") as f:
                json.dump(executions, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to log execution: {e}")
    
    def get_execution_history(self, workflow_id: str, limit: int = 20) -> list:
        """Get execution history for a workflow."""
        try:
            if not self.execution_log.exists():
                return []
            
            with open(self.execution_log) as f:
                executions = json.load(f)
            
            # Filter by workflow
            workflow_executions = [
                e for e in executions
                if e.get("workflow_id") == workflow_id
            ]
            
            # Return most recent first
            return workflow_executions[-limit:][::-1]
        
        except Exception as e:
            logger.error(f"Failed to get execution history: {e}")
            return []
