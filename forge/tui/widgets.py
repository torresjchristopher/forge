"""Reusable TUI components for Forge dashboard"""

import json
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.console import Console
from rich.text import Text
from rich import box


@dataclass
class ContainerStatus:
    """Container status snapshot"""
    id: str
    name: str
    image: str
    status: str  # running, stopped, failed
    memory_mb: float
    cpu_percent: float
    ports: List[str]
    uptime_seconds: int


@dataclass
class WorkflowStatus:
    """Workflow execution status"""
    workflow_id: str
    execution_id: str
    status: str  # running, success, failed, scheduled
    tasks_total: int
    tasks_completed: int
    tasks_failed: int
    started_at: str
    duration_seconds: Optional[int]


@dataclass
class SystemMetrics:
    """System resource metrics"""
    cpu_percent: float
    memory_percent: float
    memory_mb_used: float
    memory_mb_total: float
    disk_percent: float
    active_containers: int
    total_containers: int


class StatusTable:
    """Renders status tables for containers, workflows, etc."""

    @staticmethod
    def containers_table(containers: List[ContainerStatus]) -> Table:
        """Create a table of container statuses"""
        table = Table(title="Containers", box=box.ROUNDED, show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Image", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Memory", justify="right")
        table.add_column("CPU", justify="right")
        table.add_column("Uptime", justify="right")

        for container in containers:
            status_style = "green" if container.status == "running" else "red"
            table.add_row(
                container.name,
                container.image,
                Text(container.status, style=status_style),
                f"{container.memory_mb:.1f} MB",
                f"{container.cpu_percent:.1f}%",
                format_uptime(container.uptime_seconds),
            )

        return table

    @staticmethod
    def workflows_table(workflows: List[WorkflowStatus]) -> Table:
        """Create a table of workflow statuses"""
        table = Table(title="Workflows", box=box.ROUNDED, show_header=True)
        table.add_column("Workflow", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Progress", justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("Failed", justify="right")

        for workflow in workflows:
            status_style = "green" if workflow.status == "success" else (
                "yellow" if workflow.status == "running" else "red"
            )
            progress = f"{workflow.tasks_completed}/{workflow.tasks_total}"
            duration = (
                format_duration(workflow.duration_seconds)
                if workflow.duration_seconds
                else "—"
            )

            table.add_row(
                workflow.workflow_id,
                Text(workflow.status, style=status_style),
                progress,
                duration,
                str(workflow.tasks_failed),
            )

        return table

    @staticmethod
    def schedulers_table(schedules: List[Dict[str, Any]]) -> Table:
        """Create a table of scheduled workflows"""
        table = Table(title="Scheduled Workflows", box=box.ROUNDED, show_header=True)
        table.add_column("Workflow", style="cyan")
        table.add_column("Schedule", style="yellow")
        table.add_column("Next Run", style="magenta")
        table.add_column("Status", style="green")

        for schedule in schedules:
            enabled_style = "green" if schedule.get("enabled", True) else "red"
            enabled_text = "✓" if schedule.get("enabled", True) else "✗"

            table.add_row(
                schedule.get("workflow_id", "N/A"),
                schedule.get("cron_expression", "N/A"),
                schedule.get("next_run", "N/A"),
                Text(enabled_text, style=enabled_style),
            )

        return table


class MetricsPanel:
    """Renders system metrics and summaries"""

    @staticmethod
    def system_metrics_panel(metrics: SystemMetrics) -> Panel:
        """Create a panel showing system metrics"""
        lines = [
            f"[cyan]CPU Usage:[/cyan] {metrics.cpu_percent:.1f}%",
            f"[magenta]Memory:[/magenta] {metrics.memory_percent:.1f}% "
            f"({metrics.memory_mb_used:.0f}MB / {metrics.memory_mb_total:.0f}MB)",
            f"[yellow]Disk:[/yellow] {metrics.disk_percent:.1f}%",
            f"[green]Containers:[/green] {metrics.active_containers}/{metrics.total_containers} active",
        ]

        content = "\n".join(lines)
        return Panel(
            content,
            title="[bold]System Metrics[/bold]",
            box=box.ROUNDED,
            expand=False,
        )

    @staticmethod
    def workflow_summary_panel(workflows: List[WorkflowStatus]) -> Panel:
        """Create a panel with workflow summary"""
        running = sum(1 for w in workflows if w.status == "running")
        success = sum(1 for w in workflows if w.status == "success")
        failed = sum(1 for w in workflows if w.status == "failed")
        scheduled = sum(1 for w in workflows if w.status == "scheduled")

        lines = [
            f"[green]Success:[/green] {success}",
            f"[yellow]Running:[/yellow] {running}",
            f"[red]Failed:[/red] {failed}",
            f"[cyan]Scheduled:[/cyan] {scheduled}",
        ]

        content = "\n".join(lines)
        return Panel(
            content,
            title="[bold]Workflow Summary[/bold]",
            box=box.ROUNDED,
            expand=False,
        )


class WorkflowGraph:
    """Renders workflow DAG visualization"""

    @staticmethod
    def ascii_dag(dag_dict: Dict[str, Any]) -> str:
        """Create ASCII DAG visualization from workflow tasks"""
        tasks = dag_dict.get("tasks", {})
        if not tasks:
            return "[yellow]No tasks[/yellow]"

        lines = []

        for task_name, task_info in tasks.items():
            status = task_info.get("status", "unknown")
            depends_on = task_info.get("depends_on", [])

            status_marker = {
                "running": "▶",
                "success": "✓",
                "failed": "✗",
                "scheduled": "○",
            }.get(status, "?")

            prefix = f"  [{status_marker}] {task_name}"

            if depends_on:
                deps_str = " ← " + ", ".join(depends_on)
                lines.append(prefix + deps_str)
            else:
                lines.append(prefix + " (start)")

        return "\n".join(lines)

    @staticmethod
    def workflow_graph_panel(workflow_id: str, dag_dict: Dict[str, Any]) -> Panel:
        """Create a panel with workflow DAG"""
        graph = WorkflowGraph.ascii_dag(dag_dict)
        return Panel(
            graph,
            title=f"[bold]Workflow: {workflow_id}[/bold]",
            box=box.ROUNDED,
            expand=False,
        )


class LogViewer:
    """Renders task logs with filtering"""

    @staticmethod
    def task_logs_panel(
        task_name: str, logs: str, tail_lines: int = 20
    ) -> Panel:
        """Create a panel with task logs"""
        log_lines = logs.split("\n")
        if len(log_lines) > tail_lines:
            log_lines = ["..."] + log_lines[-tail_lines:]

        content = "\n".join(log_lines)
        return Panel(
            content,
            title=f"[bold]Logs: {task_name}[/bold]",
            box=box.ROUNDED,
            expand=False,
        )

    @staticmethod
    def search_logs(logs: str, search_term: str) -> List[str]:
        """Search logs for a term"""
        return [line for line in logs.split("\n") if search_term.lower() in line.lower()]


def format_duration(seconds: Optional[int]) -> str:
    """Format duration in human-readable form"""
    if not seconds:
        return "—"
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def format_uptime(seconds: int) -> str:
    """Format uptime in human-readable form"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h"
    else:
        days = seconds // 86400
        return f"{days}d"


def load_workflow_status(workflow_id: str) -> Optional[WorkflowStatus]:
    """Load workflow status from execution history"""
    history_file = os.path.expanduser(f"~/.forge/execution_history/{workflow_id}.json")
    if not os.path.exists(history_file):
        return None

    try:
        with open(history_file, "r") as f:
            data = json.load(f)
            if data:
                latest = data[0]  # Most recent execution
                return WorkflowStatus(
                    workflow_id=workflow_id,
                    execution_id=latest.get("execution_id", "N/A"),
                    status=latest.get("status", "unknown"),
                    tasks_total=len(latest.get("tasks", {})),
                    tasks_completed=sum(
                        1
                        for t in latest.get("tasks", {}).values()
                        if t.get("status") == "success"
                    ),
                    tasks_failed=sum(
                        1
                        for t in latest.get("tasks", {}).values()
                        if t.get("status") == "failed"
                    ),
                    started_at=latest.get("started_at", "N/A"),
                    duration_seconds=latest.get("duration_seconds"),
                )
    except Exception as e:
        print(f"Error loading workflow status: {e}")

    return None
