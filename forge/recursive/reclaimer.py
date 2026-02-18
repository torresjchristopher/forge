"""
Inertia Reclaimer - The Sovereign System Janitor.

Scans the Nexus directory for non-coded files (Inertia)
and flags them for reclamation (Ingest -> Shred).
"""

import os
import shutil
from rich.console import Console
from rich.table import Table

console = Console()

class InertiaReclaimer:
    def __init__(self, root_path: str):
        self.root = root_path
        self.reclaimable = []

    def scan(self):
        """Find files that do not follow the NX- Protocol."""
        self.reclaimable = []
        for item in os.listdir(self.root):
            # Exclude known internal Nexus folders/files
            if item.startswith(".") or item in ["venv", "__pycache__", "quarantine"]:
                continue
                
            # If it doesn't start with NX-, it's legacy inertia
            if not item.startswith("NX-"):
                path = os.path.join(self.root, item)
                size = self._get_size(path)
                self.reclaimable.append({"name": item, "path": path, "size": size})
        
        return self.reclaimable

    def _get_size(self, start_path='.'):
        total_size = 0
        if os.path.isfile(start_path):
            return os.path.getsize(start_path)
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    def report(self):
        table = Table(title="Inertia Reclamation Audit", border_style="red")
        table.add_column("Legacy Target", style="white")
        table.add_column("Size", justify="right", style="yellow")
        table.add_column("Status", style="red")

        total = 0
        for item in self.reclaimable:
            size_mb = item['size'] / (1024 * 1024)
            table.add_row(item['name'], f"{size_mb:.2f} MB", "INERTIA")
            total += item['size']

        console.print(table)
        console.print(f"
[bold red]TOTAL RECLAIMABLE:[/bold red] {total / (1024*1024):.2f} MB")
        console.print("[dim]Run 'forge reclaim --all' to ingest logic and shred bloat.[/dim]")

if __name__ == "__main__":
    # Test on the current directory
    reclaimer = InertiaReclaimer(".")
    reclaimer.scan()
    reclaimer.report()
