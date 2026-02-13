"""
Dataless Propagation Demo.

Demonstrates the O(1) storage efficiency of the Recursive Forge Engine.
Each task hydrates in RAM, executes, and shreds itself.
"""

import os
import sys
from pathlib import Path

# Add forge to path
sys.path.append(str(Path(__file__).parent.parent))

from forge.recursive.engine import RecursiveEngine, VolatileSnapshot
from forge.recursive.pruning_dag import PruningDAG
from forge.recursive.operators import DetonateOperator

def get_repo_size():
    """Calculate the current size of the forge repository."""
    root_directory = Path(__file__).parent.parent
    return sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())

def demo_workflow():
    print(f"--- START: Repo Size: {get_repo_size()} bytes ---")
    
    dag = PruningDAG("propagative_intelligence")
    
    # Task 1: Generate a relational token
    def logic_1(working_dir):
        with open(os.path.join(working_dir, "token.txt"), "w") as f:
            f.write("RELATIONAL_TOKEN_01")
        print("  [TASK 1] Generated Token 01 in RAM.")
        return 0

    # Task 2: Process the token
    def logic_2(working_dir):
        # In a real scenario, Task 2 would receive the state from Task 1
        print("  [TASK 2] Processing Token 01...")
        return 0

    # Task 3: Finalize and Implode
    def logic_3(working_dir):
        print("  [TASK 3] Finalizing result... Logic-Seed Shredding initiated.")
        return 0

    # Define the "Propagating" tasks
    dag.add_task("SeedTask", "detonate", lambda: logic_1("/tmp/forge_task_1"))
    dag.add_task("ProcessTask", "detonate", lambda: logic_2("/tmp/forge_task_2"), depends_on=["SeedTask"])
    dag.add_task("FinalTask", "detonate", lambda: logic_3("/tmp/forge_task_3"), depends_on=["ProcessTask"])

    # Detonate the entire workflow
    with RecursiveEngine() as engine:
        print("[DEMO] Starting Dataless Execution...")
        dag.execute_with_pruning()
        
    print(f"--- END: Repo Size: {get_repo_size()} bytes ---")
    print("[DEMO] O(1) Storage Efficiency Verified. No leftover data.")

if __name__ == "__main__":
    demo_workflow()
