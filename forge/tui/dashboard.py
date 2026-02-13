"""Forge TUI Dashboard - Main orchestration interface"""

import json
import os
import psutil
import subprocess
import msvcrt
from datetime import datetime
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

from forge.tui.widgets import (
    StatusTable,
    MetricsPanel,
    WorkflowGraph,
    LogViewer,
    ContainerStatus,
    WorkflowStatus,
    SystemMetrics,
)
from forge.runtime.executor import ContainerExecutor
from forge.scheduler.manager import SchedulerManager
from forge.orchestration.executor import WorkflowExecutor
from forge.runtime.filesystem import ImageStore


class Dashboard:
    """Interactive TUI dashboard for Forge orchestration"""

    def __init__(self):
        self.console = Console()
        self.running = True
        self.current_view = "overview"  # overview, workflows, containers, scheduler, logs, images
        self.selected_workflow = None
        self.selected_container = None
        self.selected_task = None
        
        # Interactive state
        self.cursor_index = 0
        self.current_item_count = 0
        
        # Backend managers
        self.executor = ContainerExecutor()
        self.scheduler = SchedulerManager()
        self.workflow_executor = WorkflowExecutor()
        self.image_store = ImageStore()

    def run(self):
        """Start the interactive dashboard"""
        try:
            with Live(self.get_layout(), refresh_per_second=2, console=self.console) as live:
                while self.running:
                    live.update(self.get_layout())
                    
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        try:
                            # Handle special keys (arrows often start with 0xe0 or 0x00)
                            if key in (b'\x00', b'\xe0'):
                                code = msvcrt.getch()
                                if code == b'H': self.handle_input('up')
                                elif code == b'P': self.handle_input('down')
                                continue 
                            
                            char = key.decode('utf-8').lower()
                            self.handle_input(char)
                        except:
                            pass
        except KeyboardInterrupt:
            self.running = False
            self.console.print("\n[yellow]Dashboard closed[/yellow]")

    def get_layout(self) -> Layout:
        """Generate the main dashboard layout"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=2),
        )

        layout["header"].update(self.render_header())
        layout["body"].update(self.render_body())
        layout["footer"].update(self.render_footer())

        return layout

    def render_header(self) -> Panel:
        """Render top header with navigation and status"""
        views = [
            ("1", "Overview", self.current_view == "overview"),
            ("2", "Workflows", self.current_view == "workflows"),
            ("3", "Containers", self.current_view == "containers"),
            ("4", "Scheduler", self.current_view == "scheduler"),
            ("5", "Logs", self.current_view == "logs"),
            ("6", "Images", self.current_view == "images"),
        ]

        nav_items = []
        for key, label, active in views:
            style = "bold white on blue" if active else "dim"
            nav_items.append(f"[{style}]{key}: {label}[/{style}]")

        nav = "  ".join(nav_items)
        status = f"[green]✓ Ready[/green] | {datetime.now().strftime('%H:%M:%S')}"

        header_text = f"{nav}  {status}"
        return Panel(header_text, box=box.ROUNDED, expand=True)

    def render_body(self) -> Any:
        """Render main content area based on current view"""
        if self.current_view == "overview":
            return self.render_overview()
        elif self.current_view == "workflows":
            return self.render_workflows()
        elif self.current_view == "containers":
            return self.render_containers()
        elif self.current_view == "scheduler":
            return self.render_scheduler()
        elif self.current_view == "logs":
            return self.render_logs()
        elif self.current_view == "images":
            return self.render_images()
        else:
            return Panel("[yellow]Unknown view[/yellow]")

    def render_overview(self) -> Layout:
        """Render overview dashboard"""
        body = Layout()
        body.split_row(
            Layout(name="left"),
            Layout(name="right"),
        )

        # Left side: metrics + workflow summary
        left = Layout()
        left.split_column(
            Layout(name="metrics"),
            Layout(name="summary"),
        )

        metrics = self.get_system_metrics()
        workflows = self.get_workflow_statuses()
        self.current_item_count = len(workflows)

        left["metrics"].update(MetricsPanel.system_metrics_panel(metrics))
        left["summary"].update(MetricsPanel.workflow_summary_panel(workflows))

        # Right side: workflow table
        body["left"].update(left)
        body["right"].update(
            Panel(
                StatusTable.workflows_table(workflows, selected_index=self.cursor_index if self.current_view == "overview" else None),
                box=box.ROUNDED,
            )
        )

        return body

    def render_workflows(self) -> Panel:
        """Render workflows view"""
        workflows = self.get_workflow_statuses()
        self.current_item_count = len(workflows)

        if not workflows:
            return Panel("[yellow]No workflows found[/yellow]")

        table = StatusTable.workflows_table(workflows, selected_index=self.cursor_index)

        if self.selected_workflow and workflows:
            # Show detailed view of selected workflow
            workflow = next((w for w in workflows if w.workflow_id == self.selected_workflow), None)
            if workflow:
                dag_file = os.path.expanduser(f"~/.forge/workflows/{workflow.workflow_id}.json")
                if os.path.exists(dag_file):
                    try:
                        with open(dag_file, "r") as f:
                            dag = json.load(f)
                        dag_panel = WorkflowGraph.workflow_graph_panel(
                            workflow.workflow_id, dag
                        )
                        # Combine table and DAG in layout
                        layout = Layout()
                        layout.split_column(
                            Layout(Panel(table, box=box.ROUNDED)),
                            Layout(dag_panel),
                        )
                        return layout
                    except Exception as e:
                        return Panel(f"[red]Error loading DAG: {e}[/red]")

        return Panel(table, box=box.ROUNDED)

    def render_containers(self) -> Panel:
        """Render containers view"""
        containers = self.get_container_statuses()
        self.current_item_count = len(containers)

        if not containers:
            return Panel("[yellow]No containers found[/yellow]")

        table = StatusTable.containers_table(containers, selected_index=self.cursor_index)
        return Panel(table, box=box.ROUNDED)

    def render_scheduler(self) -> Panel:
        """Render scheduler view"""
        schedules = self.get_scheduled_workflows()
        self.current_item_count = len(schedules)

        if not schedules:
            return Panel("[yellow]No scheduled workflows[/yellow]")

        table = StatusTable.schedulers_table(schedules, selected_index=self.cursor_index)
        return Panel(table, box=box.ROUNDED)

    def render_logs(self) -> Panel:
        """Render logs view"""
        if not self.selected_task:
            return Panel("[yellow]Select a task to view logs[/yellow]")

        logs_file = os.path.expanduser(f"~/.forge/logs/{self.selected_task}.log")
        if not os.path.exists(logs_file):
            return Panel("[yellow]No logs available[/yellow]")

        try:
            with open(logs_file, "r") as f:
                logs = f.read()
            return LogViewer.task_logs_panel(self.selected_task, logs, tail_lines=30)
        except Exception as e:
            return Panel(f"[red]Error loading logs: {e}[/red]")

    def render_images(self) -> Panel:
        """Render images view"""
        images = self.get_image_statuses()
        self.current_item_count = len(images)

        if not images:
            return Panel("[yellow]No images found[/yellow]")

        table = StatusTable.images_table(images, selected_index=self.cursor_index)
        return Panel(table, box=box.ROUNDED)

    def render_footer(self) -> Panel:
        """Render footer with context-sensitive help text"""
        base_help = "[cyan]↑↓[/cyan] Navigate | [cyan]Enter[/cyan] Select | [cyan]q[/cyan] Quit | [cyan]r[/cyan] Refresh"
        
        ctx_help = ""
        if self.current_view == "containers":
            ctx_help = " | [cyan]d[/cyan] Delete | [cyan]p[/cyan] Prune"
        elif self.current_view == "workflows":
            ctx_help = " | [cyan]t[/cyan] Trigger | [cyan]c[/cyan] Clear Detail"
        elif self.current_view == "scheduler":
            ctx_help = " | [cyan]p[/cyan] Pause/Resume | [cyan]t[/cyan] Trigger Now"
        elif self.current_view == "images":
            ctx_help = " | [cyan]d[/cyan] Delete"

        return Panel(base_help + ctx_help, box=box.ROUNDED, expand=True)

    def get_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        # Count containers
        containers_dir = os.path.expanduser("~/.forge/containers")
        total_containers = 0
        active_containers = 0

        if os.path.exists(containers_dir):
            for item in os.listdir(containers_dir):
                container_dir = os.path.join(containers_dir, item)
                if os.path.isdir(container_dir):
                    total_containers += 1
                    status_file = os.path.join(container_dir, "status.json")
                    if os.path.exists(status_file):
                        try:
                            with open(status_file, "r") as f:
                                status = json.load(f).get("status", "unknown")
                                if status == "running":
                                    active_containers += 1
                        except Exception:
                            pass

        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_mb_used=memory.used / (1024 * 1024),
            memory_mb_total=memory.total / (1024 * 1024),
            disk_percent=psutil.disk_usage("/").percent,
            active_containers=active_containers,
            total_containers=total_containers,
        )

    def get_workflow_statuses(self) -> List[WorkflowStatus]:
        """Load workflow execution statuses"""
        workflows = []
        executions_dir = os.path.expanduser("~/.forge/execution_history")

        if not os.path.exists(executions_dir):
            return workflows

        for filename in os.listdir(executions_dir):
            if filename.endswith(".json"):
                workflow_id = filename[:-5]
                filepath = os.path.join(executions_dir, filename)

                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                        if data:
                            latest = data[0]
                            status = WorkflowStatus(
                                workflow_id=workflow_id,
                                execution_id=latest.get("execution_id", "N/A"),
                                status=latest.get("status", "unknown"),
                                tasks_total=len(latest.get("tasks", {{}})),
                                tasks_completed=sum(
                                    1
                                    for t in latest.get("tasks", {{}}).values()
                                    if t.get("status") == "success"
                                ),
                                tasks_failed=sum(
                                    1
                                    for t in latest.get("tasks", {{}}).values()
                                    if t.get("status") == "failed"
                                ),
                                started_at=latest.get("started_at", "N/A"),
                                duration_seconds=latest.get("duration_seconds"),
                            )
                            workflows.append(status)
                except Exception as e:
                    print(f"Error loading workflow status: {e}")

        return workflows

    def get_container_statuses(self) -> List[ContainerStatus]:
        """Load container statuses"""
        containers = []
        containers_dir = os.path.expanduser("~/.forge/containers")

        if not os.path.exists(containers_dir):
            return containers

        for container_name in os.listdir(containers_dir):
            container_dir = os.path.join(containers_dir, container_name)
            if os.path.isdir(container_dir):
                status_file = os.path.join(container_dir, "status.json")
                try:
                    with open(status_file, "r") as f:
                        data = json.load(f)
                        uptime = 0
                        if data.get("started_at"):
                            started = datetime.fromisoformat(data["started_at"])
                            uptime = int((datetime.now() - started).total_seconds())

                        container = ContainerStatus(
                            id=container_name[:12],
                            name=container_name,
                            image=data.get("image", "unknown"),
                            status=data.get("status", "unknown"),
                            memory_mb=data.get("memory_mb", 0.0),
                            cpu_percent=data.get("cpu_percent", 0.0),
                            ports=data.get("ports", []),
                            uptime_seconds=uptime,
                        )
                        containers.append(container)
                except Exception as e:
                    print(f"Error loading container status: {e}")

        return containers

    def get_scheduled_workflows(self) -> List[Dict[str, Any]]:
        """Load scheduled workflows"""
        schedules = []
        state_file = os.path.expanduser("~/.forge/scheduler_state.json")

        if not os.path.exists(state_file):
            return schedules

        try:
            with open(state_file, "r") as f:
                data = json.load(f)
                for workflow_id, schedule_info in data.items():
                    schedules.append(
                        {
                            "workflow_id": workflow_id,
                            "cron_expression": schedule_info.get("cron_expression", "N/A"),
                            "next_run": schedule_info.get("next_run", "N/A"),
                            "enabled": schedule_info.get("enabled", True),
                        }
                    )
        except Exception as e:
            print(f"Error loading schedules: {e}")

        return schedules

    def get_image_statuses(self) -> List[Dict[str, Any]]:
        """Load image statuses"""
        try:
            return self.image_store.list_images()
        except:
            return []

    def handle_input(self, key: str):
        """Handle keyboard input with context-aware actions"""
        if key == "q":
            self.running = False
        elif key == "1":
            self.current_view = "overview"; self.cursor_index = 0
        elif key == "2":
            self.current_view = "workflows"; self.cursor_index = 0
        elif key == "3":
            self.current_view = "containers"; self.cursor_index = 0
        elif key == "4":
            self.current_view = "scheduler"; self.cursor_index = 0
        elif key == "5":
            self.current_view = "logs"; self.cursor_index = 0
        elif key == "6":
            self.current_view = "images"; self.cursor_index = 0
        
        elif key == "up":
            self.cursor_index = max(0, self.cursor_index - 1)
        elif key == "down":
            self.cursor_index = min(self.current_item_count - 1, self.cursor_index + 1) if self.current_item_count > 0 else 0
        
        elif key == "\r" or key == "\n": # Enter
            if self.current_view == "workflows" or self.current_view == "overview":
                workflows = self.get_workflow_statuses()
                if 0 <= self.cursor_index < len(workflows):
                    self.selected_workflow = workflows[self.cursor_index].workflow_id
        
        elif key == "c":
            self.selected_workflow = None
            self.selected_task = None
            
        elif self.current_view == "containers":
            if key == "d":
                containers = self.get_container_statuses()
                if 0 <= self.cursor_index < len(containers):
                    self.executor.delete_container(containers[self.cursor_index].name)
            elif key == "p":
                self.executor.cleanup_all()
                
        elif self.current_view == "scheduler":
            schedules = self.get_scheduled_workflows()
            if 0 <= self.cursor_index < len(schedules):
                wf_id = schedules[self.cursor_index]["workflow_id"]
                if key == "p":
                    enabled = schedules[self.cursor_index].get("enabled", True)
                    if enabled: self.scheduler.pause_workflow(wf_id)
                    else: self.scheduler.resume_workflow(wf_id)
                elif key == "t":
                    self.scheduler.trigger_now(wf_id)
        
        elif self.current_view == "workflows":
            if key == "t":
                workflows = self.get_workflow_statuses()
                if 0 <= self.cursor_index < len(workflows):
                    self.scheduler.trigger_now(workflows[self.cursor_index].workflow_id)

        elif self.current_view == "images":
            if key == "d":
                images = self.get_image_statuses()
                if 0 <= self.cursor_index < len(images):
                    self.image_store.delete_image(images[self.cursor_index]["name"])