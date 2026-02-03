"""Forge TUI Dashboard

Real-time terminal user interface for monitoring and controlling:
- Workflows (execution status, DAG visualization)
- Containers (running, stopped, resources)
- Scheduler (scheduled jobs, next run times)
- System metrics (CPU, memory, disk usage)
"""

from forge.tui.dashboard import Dashboard
from forge.tui.widgets import StatusTable, MetricsPanel, WorkflowGraph

__all__ = ["Dashboard", "StatusTable", "MetricsPanel", "WorkflowGraph"]
