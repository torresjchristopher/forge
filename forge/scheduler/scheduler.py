"""Workflow scheduler using APScheduler."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Callable, Optional
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


class WorkflowScheduler:
    """Manages workflow scheduling and execution."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.jobs = {}
    
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Workflow scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Workflow scheduler stopped")
    
    def add_workflow(
        self,
        workflow_name: str,
        cron_expression: str,
        callback: Callable,
        args: Optional[tuple] = None,
    ):
        """Schedule a workflow execution."""
        try:
            trigger = CronTrigger.from_crontab(cron_expression)
            job = self.scheduler.add_job(
                callback,
                trigger=trigger,
                args=args or (),
                id=workflow_name,
                name=workflow_name,
                replace_existing=True,
            )
            self.jobs[workflow_name] = job
            logger.info(f"Scheduled workflow: {workflow_name} ({cron_expression})")
            return job
        except Exception as e:
            logger.error(f"Failed to schedule workflow {workflow_name}: {e}")
            raise
    
    def remove_workflow(self, workflow_name: str):
        """Remove a scheduled workflow."""
        try:
            self.scheduler.remove_job(workflow_name)
            del self.jobs[workflow_name]
            logger.info(f"Removed workflow: {workflow_name}")
        except Exception as e:
            logger.error(f"Failed to remove workflow {workflow_name}: {e}")
    
    def get_job(self, workflow_name: str):
        """Get a scheduled job."""
        return self.jobs.get(workflow_name)
    
    def list_jobs(self):
        """List all scheduled jobs."""
        return list(self.jobs.values())
    
    def trigger_now(self, workflow_name: str):
        """Trigger a workflow immediately."""
        job = self.get_job(workflow_name)
        if job:
            job.func(*job.args, **job.kwargs)
            logger.info(f"Triggered workflow: {workflow_name}")
        else:
            logger.warning(f"Workflow not found: {workflow_name}")
