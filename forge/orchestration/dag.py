"""DAG (Directed Acyclic Graph) execution engine.

Core of the embedded Airflow functionality.
Executes tasks with dependency tracking and failure handling.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Callable
from enum import Enum
import time
from datetime import datetime
import json


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    UPSTREAM_FAILED = "upstream_failed"
    TIMEOUT = "timeout"


@dataclass
class TaskResult:
    """Result of task execution."""
    task_id: str
    status: TaskStatus
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    retries_remaining: int = 0


class DAGTask:
    """Represents a task in a DAG."""
    
    def __init__(
        self,
        task_id: str,
        task_type: str,
        handler: Callable,
        depends_on: Optional[List[str]] = None,
        retries: int = 0,
        retry_delay: int = 300,
        timeout: Optional[int] = None,
        sla: Optional[int] = None,
    ):
        self.task_id = task_id
        self.task_type = task_type  # 'container', 'python', 'shell', etc.
        self.handler = handler  # Function to execute
        self.depends_on = depends_on or []
        self.retries = retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.sla = sla
        self.status = TaskStatus.PENDING
        self.result: Optional[TaskResult] = None
    
    def execute(self) -> TaskResult:
        """Execute the task."""
        start_time = datetime.now()
        
        try:
            # Call the handler
            start_exec = time.time()
            exit_code = self.handler()
            elapsed = time.time() - start_exec
            
            status = TaskStatus.SUCCESS if exit_code == 0 else TaskStatus.FAILED
            
            self.result = TaskResult(
                task_id=self.task_id,
                status=status,
                start_time=start_time,
                end_time=datetime.now(),
                duration_seconds=elapsed,
                exit_code=exit_code,
            )
            
        except Exception as e:
            self.result = TaskResult(
                task_id=self.task_id,
                status=TaskStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(),
                duration_seconds=time.time() - start_time.timestamp(),
                error_message=str(e),
            )
        
        self.status = self.result.status
        return self.result


class DAG:
    """Directed Acyclic Graph for workflow execution."""
    
    def __init__(self, dag_id: str, description: Optional[str] = None):
        self.dag_id = dag_id
        self.description = description
        self.tasks: Dict[str, DAGTask] = {}
        self.execution_history: List[Dict] = []
    
    def add_task(
        self,
        task_id: str,
        task_type: str,
        handler: Callable,
        depends_on: Optional[List[str]] = None,
        **kwargs
    ) -> DAGTask:
        """Add a task to the DAG."""
        task = DAGTask(task_id, task_type, handler, depends_on, **kwargs)
        self.tasks[task_id] = task
        return task
    
    def _validate(self) -> bool:
        """Validate DAG structure (check for cycles)."""
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            task = self.tasks.get(node)
            if task:
                for dep in task.depends_on:
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True
            
            rec_stack.remove(node)
            return False
        
        for task_id in self.tasks:
            if task_id not in visited:
                if has_cycle(task_id):
                    return False
        
        return True
    
    def _get_execution_order(self) -> List[List[str]]:
        """Get topologically sorted task order (layers for parallel execution)."""
        in_degree = {task_id: 0 for task_id in self.tasks}
        
        # Calculate in-degrees
        for task in self.tasks.values():
            for dep in task.depends_on:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # Topological sort with layers
        layers = []
        processed = set()
        
        while len(processed) < len(self.tasks):
            current_layer = []
            
            for task_id, degree in in_degree.items():
                if task_id not in processed and degree == 0:
                    current_layer.append(task_id)
            
            if not current_layer:
                break  # Shouldn't happen if DAG is valid
            
            layers.append(current_layer)
            processed.update(current_layer)
            
            # Decrease in-degree for dependent tasks
            for task_id in current_layer:
                task = self.tasks[task_id]
                for other_task in self.tasks.values():
                    if task_id in other_task.depends_on:
                        in_degree[other_task.task_id] -= 1
        
        return layers
    
    def execute(self) -> Dict:
        """Execute the DAG and return execution result."""
        if not self._validate():
            return {
                "dag_id": self.dag_id,
                "status": "failed",
                "error": "DAG contains cycles",
            }
        
        execution_id = f"{self.dag_id}_{datetime.now().isoformat()}"
        start_time = time.time()
        
        task_results = {}
        failed_tasks = set()
        
        # Execute tasks layer by layer
        execution_order = self._get_execution_order()
        
        for layer in execution_order:
            for task_id in layer:
                task = self.tasks[task_id]
                
                # Check if upstream tasks failed
                if any(dep in failed_tasks for dep in task.depends_on):
                    task.status = TaskStatus.UPSTREAM_FAILED
                    task_results[task_id] = {
                        "task_id": task_id,
                        "status": "upstream_failed",
                    }
                    continue
                
                # Execute task
                retry_count = 0
                result = None
                
                while retry_count <= task.retries:
                    try:
                        result = task.execute()
                        
                        if result.status == TaskStatus.SUCCESS:
                            break
                        
                        retry_count += 1
                        if retry_count <= task.retries:
                            time.sleep(task.retry_delay)
                    
                    except Exception as e:
                        if retry_count < task.retries:
                            retry_count += 1
                            time.sleep(task.retry_delay)
                        else:
                            result = TaskResult(
                                task_id=task_id,
                                status=TaskStatus.FAILED,
                                start_time=datetime.now(),
                                end_time=datetime.now(),
                                duration_seconds=0,
                                error_message=str(e),
                            )
                            break
                
                if result:
                    task_results[task_id] = {
                        "task_id": task_id,
                        "status": result.status.value,
                        "duration_seconds": result.duration_seconds,
                        "exit_code": result.exit_code,
                        "retries": task.retries - result.retries_remaining,
                    }
                    
                    if result.status != TaskStatus.SUCCESS:
                        failed_tasks.add(task_id)
        
        elapsed = time.time() - start_time
        
        execution_result = {
            "execution_id": execution_id,
            "dag_id": self.dag_id,
            "status": "success" if not failed_tasks else "failed",
            "duration_seconds": elapsed,
            "tasks_completed": len([r for r in task_results.values() if r.get("status") == "success"]),
            "tasks_failed": len(failed_tasks),
            "task_results": task_results,
        }
        
        self.execution_history.append(execution_result)
        
        return execution_result
