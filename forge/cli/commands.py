"""CLI interface for Forge."""

import click
from pathlib import Path
import sys
import time
import json

from forge.runtime.executor import ContainerExecutor, ContainerConfig
from forge.runtime.filesystem import ImageStore
from forge.orchestration.engine import OrchestrationEngine
from forge.orchestration.executor import WorkflowExecutor
from forge.scheduler.scheduler import WorkflowScheduler
from rich.console import Console
from rich.table import Table

console = Console()
executor = ContainerExecutor()
image_store = ImageStore()
orchestration = OrchestrationEngine()
workflow_executor = WorkflowExecutor()
scheduler = WorkflowScheduler()


@click.group()
@click.version_option()
def cli():
    """Forge: Lightning-fast container orchestration + embedded workflows."""
    pass


# ─── Container Commands ───


@cli.group()
def container():
    """Manage containers."""
    pass


@container.command()
@click.argument("image")
@click.argument("command", nargs=-1, required=True)
@click.option("--memory", type=int, help="Memory limit in MB")
@click.option("--cpu", type=int, help="CPU limit as percentage")
@click.option("-p", "--port", multiple=True, help="Port mapping (e.g., 8080:80)")
@click.option("-v", "--volume", multiple=True, help="Volume mount (e.g., /host:/container)")
@click.option("--timeout", type=int, help="Timeout in seconds")
def run(image: str, command: tuple, memory: int, cpu: int, port: tuple, volume: tuple, timeout: int):
    """Run a container.
    
    Example:
        forge container run python:3.11 python app.py --port 8080:5000 --volume /data:/data
    """
    start = time.time()
    
    # Parse port mappings
    ports = {}
    for p in port:
        parts = p.split(":")
        if len(parts) == 2:
            host_port, container_port = int(parts[0]), int(parts[1])
            ports[container_port] = host_port
    
    # Parse volumes
    volumes = {}
    for v in volume:
        parts = v.split(":")
        if len(parts) == 2:
            host_path, container_path = parts
            volumes[host_path] = container_path
    
    config = ContainerConfig(
        image=image,
        command=list(command),
        ports=ports if ports else None,
        volumes=volumes if volumes else None,
        memory_limit=memory,
        cpu_limit=cpu,
        timeout=timeout,
    )
    
    console.print(f"[cyan]Running container: {image}[/cyan]")
    if ports:
        console.print(f"[dim]Port mappings: {ports}[/dim]")
    if volumes:
        console.print(f"[dim]Volumes: {volumes}[/dim]")
    
    exit_code = executor.run_container(config)
    elapsed = time.time() - start
    
    if exit_code == 0:
        console.print(f"[green]✓ Completed in {elapsed:.2f}s[/green]")
    else:
        console.print(f"[red]✗ Failed with exit code {exit_code}[/red]")
    
    sys.exit(exit_code)


@container.command()
def list():
    """List all containers with details."""
    containers = executor.list_containers()
    
    if not containers:
        console.print("[yellow]No containers[/yellow]")
        return
    
    table = Table(title="Containers")
    table.add_column("ID", style="cyan")
    table.add_column("Image", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Memory (MB)", justify="right")
    table.add_column("Filesystem (MB)", justify="right")
    table.add_column("Ports", style="dim")
    
    for container in containers:
        stats = container.get_stats()
        port_info = ", ".join([f"{k}→{v}" for k, v in stats.get("port_mappings", {}).items()]) or "—"
        table.add_row(
            container.container_id,
            container.config.image,
            container.status,
            f"{stats['memory_mb']:.1f}",
            f"{stats['filesystem_mb']:.1f}",
            port_info,
        )
    
    console.print(table)


@container.command()
@click.argument("container_id")
def delete(container_id: str):
    """Delete a container instantly."""
    start = time.time()
    cleanup_time = executor.delete_container(container_id)
    elapsed = time.time() - start
    
    console.print(f"[green]✓ Deleted {container_id} in {elapsed*1000:.0f}ms[/green]")


@container.command()
def prune():
    """Delete all stopped containers instantly."""
    executor.cleanup_all()
    console.print("[green]✓ Pruned all containers[/green]")


# ─── Image Commands ───


@cli.group()
def image():
    """Manage images."""
    pass


@image.command()
def list():
    """List all images."""
    images = image_store.list_images()
    
    if not images:
        console.print("[yellow]No images[/yellow]")
        return
    
    table = Table(title="Images")
    table.add_column("Name", style="cyan")
    table.add_column("Size (MB)", justify="right")
    table.add_column("Created", style="dim")
    
    for img in images:
        table.add_row(
            img["name"],
            f"{img['size_mb']:.1f}",
            img.get("created", "unknown")[:10],
        )
    
    console.print(table)


@image.command()
@click.argument("image_name")
def delete(image_name: str):
    """Delete an image instantly."""
    start = time.time()
    delete_time = image_store.delete_image(image_name)
    elapsed = time.time() - start
    
    console.print(f"[green]✓ Deleted {image_name} in {elapsed*1000:.0f}ms[/green]")


# ─── Service Commands ───


@cli.group()
def service():
    """Manage services."""
    pass


@service.command()
@click.argument("name")
def start(name: str):
    """Start a service."""
    console.print(f"[cyan]Starting service: {name}[/cyan]")


@service.command()
@click.argument("name")
def stop(name: str):
    """Stop a service."""
    console.print(f"[cyan]Stopping service: {name}[/cyan]")


@service.command()
def list():
    """List all services."""
    console.print("[yellow]Services:[/yellow]")


# ─── Workflow Commands ───


@cli.group()
def workflow():
    """Manage workflows."""
    pass


@workflow.command()
@click.argument("name")
@click.option("--config", type=click.Path(exists=True), help="Path to workflow config file")
def run(name: str, config: str):
    """Run a workflow.
    
    Example:
        forge workflow run daily_etl --config forge.yml
    """
    try:
        if config:
            with open(config) as f:
                import yaml
                config_data = yaml.safe_load(f)
                workflow_config = config_data.get("workflows", {}).get(name)
        else:
            # Load from default forge.yml
            with open("forge.yml") as f:
                import yaml
                config_data = yaml.safe_load(f)
                workflow_config = config_data.get("workflows", {}).get(name)
        
        if not workflow_config:
            console.print(f"[red]Workflow '{name}' not found[/red]")
            return
        
        workflow_config["name"] = name
        
        console.print(f"[cyan]Running workflow: {name}[/cyan]")
        start = time.time()
        
        result = workflow_executor.execute_workflow(workflow_config)
        elapsed = time.time() - start
        
        # Display results
        console.print("")
        console.print(f"[bold]Workflow Execution Report[/bold]")
        console.print(f"Status: {result.get('status').upper()}")
        console.print(f"Duration: {result.get('duration_seconds', 0):.1f}s")
        console.print(f"Tasks Completed: {result.get('tasks_completed', 0)}")
        console.print(f"Tasks Failed: {result.get('tasks_failed', 0)}")
        
        if result.get("task_results"):
            console.print("\n[bold]Task Details[/bold]")
            table = Table()
            table.add_column("Task ID", style="cyan")
            table.add_column("Status", style="yellow")
            table.add_column("Duration (s)", justify="right")
            table.add_column("Exit Code", justify="right")
            
            for task_id, task_result in result["task_results"].items():
                status_color = "green" if task_result.get("status") == "success" else "red"
                table.add_row(
                    task_id,
                    f"[{status_color}]{task_result.get('status')}[/{status_color}]",
                    f"{task_result.get('duration_seconds', 0):.1f}",
                    str(task_result.get("exit_code", "—")),
                )
            
            console.print(table)
    
    except FileNotFoundError:
        console.print("[red]Could not find forge.yml or specified config file[/red]")
    except Exception as e:
        console.print(f"[red]Error running workflow: {e}[/red]")


@workflow.command()
def list():
    """List all workflows."""
    try:
        with open("forge.yml") as f:
            import yaml
            config = yaml.safe_load(f)
            workflows = config.get("workflows", {})
        
        if not workflows:
            console.print("[yellow]No workflows defined[/yellow]")
            return
        
        table = Table(title="Workflows")
        table.add_column("Name", style="cyan")
        table.add_column("Schedule", style="green")
        table.add_column("Tasks", justify="right")
        table.add_column("Description", style="dim")
        
        for name, wf in workflows.items():
            task_count = len(wf.get("tasks", []))
            description = wf.get("description", "")
            table.add_row(
                name,
                wf.get("schedule", "—"),
                str(task_count),
                description[:40],
            )
        
        console.print(table)
    
    except FileNotFoundError:
        console.print("[red]No forge.yml found[/red]")
    except Exception as e:
        console.print(f"[red]Error listing workflows: {e}[/red]")


# ─── System Commands ───


@cli.group()
def system():
    """System commands."""
    pass


@system.command()
def prune():
    """Auto-prune unused images and logs."""
    console.print("[cyan]Pruning unused data...[/cyan]")
    
    start = time.time()
    result = image_store.cleanup_unused([])
    elapsed = time.time() - start
    
    console.print(f"[green]✓ Deleted {result['deleted_count']} images, freed {result['freed_mb']} MB in {elapsed:.2f}s[/green]")


@system.command()
def usage():
    """Show system usage and storage."""
    images = image_store.list_images()
    containers = executor.list_containers()
    
    total_image_size = sum(img["size_mb"] for img in images)
    total_container_size = sum(c.stats.filesystem_mb for c in containers)
    
    table = Table(title="System Usage")
    table.add_column("Component", style="cyan")
    table.add_column("Size (MB)", justify="right")
    table.add_column("Count", justify="right")
    
    table.add_row("Images", f"{total_image_size:.1f}", str(len(images)))
    table.add_row("Containers", f"{total_container_size:.1f}", str(len(containers)))
    table.add_row("Total", f"{total_image_size + total_container_size:.1f}", "")
    
    console.print(table)


@cli.command()
def tui():
    """Launch TUI dashboard."""
    console.print("[cyan]Launching Forge TUI...[/cyan]")


def main():
    """Entry point."""
    try:
        cli()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
