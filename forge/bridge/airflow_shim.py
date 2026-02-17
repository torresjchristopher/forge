"""
Airflow-to-Forge Bridge.

Allows legacy Airflow DAG files to be executed by the Forge Recursive Engine.
"""

from typing import Any
from forge.recursive.pruning_dag import PruningDAG
from forge.recursive.operators import DetonateOperator

class AirflowBridge:
    """
    Shims standard Airflow classes to Forge Recursive logic.
    """
    
    @staticmethod
    def wrap_dag(legacy_dag: Any) -> PruningDAG:
        """
        Takes a legacy Airflow DAG object and converts it into a 
        Self-Pruning Forge DAG.
        """
        print(f"[BRIDGE] Wrapping legacy DAG: {legacy_dag.dag_id}")
        recursive_dag = PruningDAG(legacy_dag.dag_id)
        
        for task in legacy_dag.tasks:
            # Map legacy operators to DetonateOperators
            # This is where the magic happens: 
            # DockerOperator -> DetonateOperator
            # PythonOperator -> DetonateOperator
            recursive_dag.add_task(
                task_id=task.task_id,
                task_type="detonate",
                handler=lambda: task.execute({}), # Simplified execution
                depends_on=[t.task_id for t in task.upstream_list]
            )
            
        return recursive_dag
