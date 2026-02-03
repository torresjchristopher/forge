"""Storage and persistence layer."""

from pathlib import Path
from typing import Dict, List, Any, Optional
import json
from datetime import datetime, timedelta


class ExecutionStore:
    """Persistent storage for workflow executions."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.home() / ".forge"
        self.base_dir.mkdir(exist_ok=True)
        self.history_file = self.base_dir / "execution_history.json"
        self.max_history = 100
    
    def record_execution(self, workflow_name: str, execution_data: Dict[str, Any]):
        """Record a workflow execution."""
        history = self._load_history()
        
        execution = {
            "workflow_id": workflow_name,
            "run_id": execution_data.get("run_id"),
            "status": execution_data.get("status"),
            "duration": execution_data.get("duration"),
            "tasks_completed": execution_data.get("tasks_completed", 0),
            "tasks_failed": execution_data.get("tasks_failed", 0),
            "timestamp": datetime.now().isoformat(),
        }
        
        history.append(execution)
        
        # Keep only last N executions
        if len(history) > self.max_history:
            history = history[-self.max_history:]
        
        self._save_history(history)
    
    def get_execution_history(self, workflow_name: str) -> List[Dict]:
        """Get execution history for a workflow."""
        history = self._load_history()
        return [e for e in history if e["workflow_id"] == workflow_name]
    
    def _load_history(self) -> List[Dict]:
        """Load execution history from file."""
        if not self.history_file.exists():
            return []
        
        with open(self.history_file) as f:
            return json.load(f)
    
    def _save_history(self, history: List[Dict]):
        """Save execution history to file."""
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)


class LogStore:
    """Storage for execution logs."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.home() / ".forge" / "logs"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = 14
    
    def save_log(self, workflow_name: str, task_name: str, log_content: str):
        """Save task execution logs."""
        log_dir = self.base_dir / workflow_name
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"{task_name}_{datetime.now().isoformat()}.log"
        with open(log_file, "w") as f:
            f.write(log_content)
    
    def get_logs(self, workflow_name: str, task_name: str) -> List[str]:
        """Get logs for a task."""
        log_dir = self.base_dir / workflow_name
        if not log_dir.exists():
            return []
        
        logs = []
        for log_file in sorted(log_dir.glob(f"{task_name}_*.log")):
            with open(log_file) as f:
                logs.append(f.read())
        
        return logs
    
    def cleanup_old_logs(self):
        """Delete logs older than retention period."""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        for log_file in self.base_dir.rglob("*.log"):
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_time < cutoff_date:
                log_file.unlink()


class ImageStore:
    """Storage and management for container images."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.home() / ".forge" / "images"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.keep_last_n = 3
        self.max_age_days = 30
    
    def save_image(self, image_name: str, image_path: Path):
        """Save a container image."""
        dest = self.base_dir / image_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        # In real implementation, this would copy/link the image
        pass
    
    def cleanup_unused_images(self, active_images: List[str]):
        """Remove unused images older than max_age_days."""
        cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
        
        for image_file in self.base_dir.rglob("*"):
            if image_file.is_file():
                image_name = image_file.name
                if image_name not in active_images:
                    file_time = datetime.fromtimestamp(image_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        image_file.unlink()
