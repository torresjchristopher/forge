"""Memory and performance profiling utilities for Forge"""

import psutil
import os
import json
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime
import tracemalloc
from pathlib import Path


@dataclass
class MemorySnapshot:
    """Memory usage at a point in time"""
    timestamp: str
    process_rss_mb: float
    process_vms_mb: float
    system_memory_percent: float
    system_memory_available_mb: float
    process_percent: float
    cpu_percent: float


class MemoryProfiler:
    """Track memory usage over time"""
    
    def __init__(self, output_dir: str = "~/.forge/profiles"):
        self.output_dir = os.path.expanduser(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.snapshots: List[MemorySnapshot] = []
    
    def take_snapshot(self, label: str = "") -> MemorySnapshot:
        """Take a memory snapshot"""
        try:
            process = psutil.Process()
            mem = process.memory_info()
            vm = psutil.virtual_memory()
            
            snapshot = MemorySnapshot(
                timestamp=datetime.now().isoformat(),
                process_rss_mb=mem.rss / (1024 * 1024),
                process_vms_mb=mem.vms / (1024 * 1024),
                system_memory_percent=vm.percent,
                system_memory_available_mb=vm.available / (1024 * 1024),
                process_percent=process.memory_percent(),
                cpu_percent=process.cpu_percent(),
            )
            
            self.snapshots.append(snapshot)
            return snapshot
        except Exception as e:
            print(f"Error taking memory snapshot: {e}")
            return None
    
    def start_trace(self):
        """Start memory tracing"""
        tracemalloc.start()
    
    def stop_trace(self) -> Dict:
        """Stop tracing and get statistics"""
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return {
            "current_mb": current / (1024 * 1024),
            "peak_mb": peak / (1024 * 1024),
        }
    
    def get_top_allocations(self, limit: int = 10) -> List[Dict]:
        """Get top memory allocations"""
        try:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            
            allocations = []
            for stat in top_stats[:limit]:
                allocations.append({
                    "file": stat.traceback.format()[0] if stat.traceback else "unknown",
                    "size_mb": stat.size / (1024 * 1024),
                    "count": stat.count,
                })
            
            return allocations
        except Exception as e:
            print(f"Error getting allocations: {e}")
            return []
    
    def save_snapshots(self, filename: Optional[str] = None) -> str:
        """Save snapshots to JSON"""
        if not filename:
            filename = f"memory_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        data = {
            "snapshots": [
                {
                    "timestamp": s.timestamp,
                    "process_rss_mb": s.process_rss_mb,
                    "process_vms_mb": s.process_vms_mb,
                    "system_memory_percent": s.system_memory_percent,
                    "system_memory_available_mb": s.system_memory_available_mb,
                    "process_percent": s.process_percent,
                    "cpu_percent": s.cpu_percent,
                }
                for s in self.snapshots
            ]
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        return filepath
    
    def print_summary(self):
        """Print memory usage summary"""
        if not self.snapshots:
            print("No snapshots recorded")
            return
        
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        
        table = Table(title="Memory Profile Summary")
        table.add_column("Timestamp", style="cyan")
        table.add_column("RSS (MB)", justify="right", style="green")
        table.add_column("VMS (MB)", justify="right")
        table.add_column("System %", justify="right", style="yellow")
        table.add_column("CPU %", justify="right", style="magenta")
        
        for snapshot in self.snapshots:
            table.add_row(
                snapshot.timestamp[-8:],  # HH:MM:SS
                f"{snapshot.process_rss_mb:.1f}",
                f"{snapshot.process_vms_mb:.1f}",
                f"{snapshot.system_memory_percent:.1f}",
                f"{snapshot.cpu_percent:.1f}",
            )
        
        console.print(table)
        
        # Summary stats
        rss_values = [s.process_rss_mb for s in self.snapshots]
        print(f"\n[cyan]RSS Memory:[/cyan]")
        print(f"  Min: {min(rss_values):.1f} MB")
        print(f"  Max: {max(rss_values):.1f} MB")
        print(f"  Avg: {sum(rss_values) / len(rss_values):.1f} MB")


class PerformanceProfiler:
    """Profile operation performance"""
    
    def __init__(self, output_dir: str = "~/.forge/profiles"):
        self.output_dir = os.path.expanduser(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.measurements: List[Dict] = []
    
    def measure(self, name: str, operation, *args, **kwargs) -> Dict:
        """Measure operation performance"""
        import time
        
        start_time = time.perf_counter()
        
        try:
            result = operation(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        elapsed = time.perf_counter() - start_time
        
        measurement = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": elapsed,
            "elapsed_ms": elapsed * 1000,
            "success": success,
            "error": error,
        }
        
        self.measurements.append(measurement)
        return measurement
    
    def save_measurements(self, filename: Optional[str] = None) -> str:
        """Save measurements to JSON"""
        if not filename:
            filename = f"perf_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, "w") as f:
            json.dump(self.measurements, f, indent=2)
        
        return filepath
    
    def print_summary(self):
        """Print performance summary"""
        if not self.measurements:
            print("No measurements recorded")
            return
        
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        
        table = Table(title="Performance Profile Summary")
        table.add_column("Operation", style="cyan")
        table.add_column("Time (ms)", justify="right", style="green")
        table.add_column("Status", style="yellow")
        
        for measurement in self.measurements:
            status = "✓" if measurement["success"] else "✗"
            table.add_row(
                measurement["name"],
                f"{measurement['elapsed_ms']:.2f}",
                status,
            )
        
        console.print(table)


class SystemAnalyzer:
    """Analyze system resource usage"""
    
    @staticmethod
    def get_resource_info() -> Dict:
        """Get current system resource info"""
        try:
            vm = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            
            return {
                "memory": {
                    "total_mb": vm.total / (1024 * 1024),
                    "available_mb": vm.available / (1024 * 1024),
                    "used_mb": vm.used / (1024 * 1024),
                    "percent": vm.percent,
                },
                "disk": {
                    "total_gb": disk.total / (1024 * 1024 * 1024),
                    "used_gb": disk.used / (1024 * 1024 * 1024),
                    "free_gb": disk.free / (1024 * 1024 * 1024),
                    "percent": disk.percent,
                },
                "cpu": {
                    "count": psutil.cpu_count(),
                    "percent": psutil.cpu_percent(interval=1),
                },
            }
        except Exception as e:
            print(f"Error getting resource info: {e}")
            return {}
    
    @staticmethod
    def print_resource_info():
        """Print formatted resource info"""
        info = SystemAnalyzer.get_resource_info()
        
        from rich.console import Console
        from rich.panel import Panel
        
        console = Console()
        
        if "memory" in info:
            mem = info["memory"]
            lines = [
                f"[cyan]Total:[/cyan] {mem['total_mb']:.0f} MB",
                f"[green]Available:[/green] {mem['available_mb']:.0f} MB",
                f"[yellow]Used:[/yellow] {mem['used_mb']:.0f} MB ({mem['percent']:.1f}%)",
            ]
            console.print(Panel("\n".join(lines), title="[bold]Memory[/bold]"))
        
        if "disk" in info:
            disk = info["disk"]
            lines = [
                f"[cyan]Total:[/cyan] {disk['total_gb']:.1f} GB",
                f"[green]Free:[/green] {disk['free_gb']:.1f} GB",
                f"[yellow]Used:[/yellow] {disk['used_gb']:.1f} GB ({disk['percent']:.1f}%)",
            ]
            console.print(Panel("\n".join(lines), title="[bold]Disk[/bold]"))
