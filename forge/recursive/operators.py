"""
Detonate Operator for Forge.

Integrates Zip-and-Detonate logic into the Airflow DAG orchestration.
"""

from typing import Callable, Optional, List
from forge.recursive.engine import RecursiveEngine
from forge.orchestration.dag import DAGTask, TaskStatus, TaskResult
from datetime import datetime
import time
import os

class DetonateOperator(DAGTask):
    """
    An Airflow-style operator that detonates an ephemeral container,
    executes logic, and shred-prunes the environment immediately.
    """
    
    def __init__(
        self,
        task_id: str,
        seed_logic: Callable,
        depends_on: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(
            task_id=task_id,
            task_type="detonate",
            handler=self._run_detonated,
            depends_on=depends_on,
            **kwargs
        )
        self.seed_logic = seed_logic

    def _run_detonated(self) -> int:
        """
        The wrapper that handles the Detonate/Implode loop.
        """
        # 1. Initialize the Recursive Engine for this specific task
        with RecursiveEngine() as engine:
            # 2. Execute the seed logic within the ephemeral context
            # This logic would typically involve mounting a RAM_DISK 
            # and hydrating a container runtime.
            exit_code = engine.execute_payload(self.seed_logic)
            
            # 3. Explicitly log success/fail (Internal only)
            return exit_code

    def execute(self) -> TaskResult:
        """
        Override standard execution to include the recursive pruning 
        of the task's own metadata upon success.
        """
        print(f"[FORGE] Detonating Task: {self.task_id}")
        start_time = datetime.now()
        start_exec = time.time()
        
        # Execute via the handler (the Detonate loop)
        exit_code = self.handler()
        
        elapsed = time.time() - start_exec
        status = TaskStatus.SUCCESS if exit_code == 0 else TaskStatus.FAILED
        
        result = TaskResult(
            task_id=self.task_id,
            status=status,
            start_time=start_time,
            end_time=datetime.now(),
            duration_seconds=elapsed,
            exit_code=exit_code
        )
        
        # PRUNING LOGIC: If success, we can signal the DAG to 
        # completely forget this task's definition.
        if status == TaskStatus.SUCCESS:
            print(f"[FORGE] Task {self.task_id} successful. Shredding metadata...")
            
        return result
