"""
Recursive Pruning DAG.

A DAG that actively consumes itself during execution to maintain
Zero-Inertia efficiency.
"""

from typing import Dict, List, Any, Optional
import gc
from forge.orchestration.dag import DAG, DAGTask, TaskStatus

class PruningDAG(DAG):
    """
    A DAG that deletes its own nodes upon completion.
    """
    
    def __init__(self, dag_id: str):
        super().__init__(dag_id)
        # Track original structure for reporting, but runtime graph will shrink
        self.completion_log = []
        
    def execute_with_pruning(self) -> Dict[str, Any]:
        """
        Execute tasks and immediately prune them from memory.
        """
        if not self._validate():
            raise ValueError("Invalid DAG structure")
            
        execution_order = self._get_execution_order()
        
        for layer in execution_order:
            for task_id in layer:
                # 1. Execute the task
                task = self.tasks[task_id]
                print(f"[RECURSIVE] Executing {task_id}...")
                result = task.execute()
                
                # 2. Log minimal result (encrypted/hashed in full version)
                self.completion_log.append({
                    "id": task_id,
                    "status": result.status.value,
                    "exit": result.exit_code
                })
                
                # 3. SELF-PRUNING: Delete the node from the graph
                self._prune_node(task_id)
                
                # 4. RE-ENGINEERING: Opportunity to optimize remaining graph
                self._reengineer_graph(task_id, result)
                
        return {"status": "success", "history_hash": hash(str(self.completion_log))}
        
    def _prune_node(self, task_id: str):
        """
        Destroy the node and force memory reclamation.
        """
        if task_id in self.tasks:
            # Remove dependency links from other tasks to allow GC
            for t in self.tasks.values():
                if task_id in t.depends_on:
                    t.depends_on.remove(task_id)
            
            # Delete the task object
            del self.tasks[task_id]
            print(f"[RECURSIVE] Pruned {task_id} from runtime graph.")
            
            # Force GC to reclaim memory immediately
            gc.collect()
            
    def _reengineer_graph(self, completed_task_id: str, result: Any):
        """
        Recursive Logic: Analyze result and potentially modify remaining graph.
        """
        # Example logic: If a critical task fails, prune the entire branch immediately
        if result.status != TaskStatus.SUCCESS:
            print(f"[RECURSIVE] Task {completed_task_id} failed. Analyzing impact...")
            # In a real implementation, we would traverse downstream nodes and
            # delete them before they even run, saving compute.
            pass
