"""CLI interface for Forge."""

import click
from pathlib import Path
import sys


@click.group()
@click.version_option()
def cli():
    """Forge: Lightning-fast container orchestration + embedded workflows."""
    pass


@cli.group()
def service():
    """Manage services."""
    pass


@service.command()
@click.argument("name")
def start(name: str):
    """Start a service."""
    click.echo(f"Starting service: {name}")


@service.command()
@click.argument("name")
def stop(name: str):
    """Stop a service."""
    click.echo(f"Stopping service: {name}")


@service.command()
def list():
    """List all services."""
    click.echo("Services:")


@cli.group()
def workflow():
    """Manage workflows."""
    pass


@workflow.command()
@click.argument("name")
def run(name: str):
    """Run a workflow."""
    click.echo(f"Running workflow: {name}")


@workflow.command()
@click.argument("name")
def pause(name: str):
    """Pause a workflow."""
    click.echo(f"Pausing workflow: {name}")


@workflow.command()
def list():
    """List all workflows."""
    click.echo("Workflows:")


@cli.group()
def system():
    """System commands."""
    pass


@system.command()
def prune():
    """Auto-prune unused images and logs."""
    click.echo("Pruning unused data...")


@system.command()
def usage():
    """Show system usage and storage."""
    click.echo("System Usage:")


@cli.command()
def tui():
    """Launch TUI dashboard."""
    click.echo("Launching Forge TUI...")


def main():
    """Entry point."""
    try:
        cli()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
