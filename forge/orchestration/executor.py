"""Workflow executor: combines DAGs with container execution."""

from pathlib import Path
from typing import Dict, Optional, Callable
import json
from datetime import datetime

from forge.orchestration.dag import DAG, DAGTask
from forge.runtime.executor import ContainerExecutor, ContainerConfig


class WorkflowExecutor:
    """Executes workflows by converting task definitions to container executions."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.home() / ".forge"
        self.container_executor = ContainerExecutor()
        self.workflows: Dict[str, Dict] = {}
        self.execution_log = self.base_dir / "workflow_executions.json"
    
    def create_workflow_dag(self, workflow_config: Dict) -> DAG:
        """Create a DAG from workflow configuration."""
        dag = DAG(
            dag_id=workflow_config["name"],
            description=workflow_config.get("description"),
        )
        
        # Add tasks from workflow config
        for task_config in workflow_config.get("tasks", []):
            task_id = task_config["name"]
            
            # Create container config for this task
            container_config = ContainerConfig(
                image=task_config["image"],
                command=task_config["command"].split() if isinstance(task_config["command"], str) else task_config["command"],
                timeout=task_config.get("timeout"),
                memory_limit=task_config.get("memory_limit"),
                cpu_limit=task_config.get("cpu_limit"),
            )
            
            # Create handler that executes container
            def make_handler(config):
                return lambda: self.container_executor.run_container(config)
            
            dag.add_task(
                task_id=task_id,
                task_type="container",
                handler=make_handler(container_config),
                depends_on=task_config.get("depends_on", []),
                retries=task_config.get("retries", 0),
                retry_delay=task_config.get("retry_delay", 300),
                timeout=task_config.get("timeout"),
                sla=task_config.get("sla"),
            )
        
        return dag
    
    def execute_workflow(self, workflow_config: Dict) -> Dict:
        """Execute a workflow and return results."""
        dag = self.create_workflow_dag(workflow_config)
        
        # Execute the DAG
        result = dag.execute()
        
        # Log execution
        self._log_execution(result)
        
        return result
    
    def _log_execution(self, result: Dict):
        """Log workflow execution to file."""
        try:
            executions = []
            if self.execution_log.exists():
                with open(self.execution_log) as f:
                    executions = json.load(f)
            
            # Keep only last 100 executions (auto-pruning)
            if len(executions) >= 100:
                executions = executions[-99:]
            
            executions.append({
                **result,
                "timestamp": datetime.now().isoformat(),
            })
            
            with open(self.execution_log, "w") as f:
                json.dump(executions, f, indent=2)
        
        except Exception as e:
            print(f"Warning: could not log execution: {e}")
    
    def get_execution_history(self, workflow_id: str, limit: int = 10) -> list:
        """Get execution history for a workflow."""
        if not self.execution_log.exists():
            return []
        
        try:
            with open(self.execution_log) as f:
                executions = json.load(f)
            
            # Filter by workflow
            workflow_executions = [
                e for e in executions
                if e.get("dag_id") == workflow_id
            ]
            
            # Return most recent first
            return workflow_executions[-limit:][::-1]
        
        except Exception:
            return []
