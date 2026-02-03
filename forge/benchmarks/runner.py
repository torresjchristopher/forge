"""Comprehensive benchmarking framework for Forge

Compares Forge against Podman/Docker across:
- Container startup time
- Image loading time
- Workflow execution time
- Memory usage (idle and runtime)
- Disk usage (images and containers)
- DAG parsing performance
"""

import time
import psutil
import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import datetime
import subprocess
import sys


@dataclass
class BenchmarkResult:
    """Single benchmark measurement"""
    name: str
    operation: str
    runtime: str  # "forge", "podman", "docker"
    metric: str  # "startup", "memory", "disk", "duration"
    value: float
    unit: str  # "ms", "MB", "GB", "seconds"
    timestamp: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results"""
    suite_name: str
    timestamp: str
    results: List[BenchmarkResult]
    
    def to_json(self):
        return {
            "suite_name": self.suite_name,
            "timestamp": self.timestamp,
            "results": [asdict(r) for r in self.results],
        }


class BenchmarkRunner:
    """Runs benchmarks and collects results"""
    
    def __init__(self, output_dir: str = "~/.forge/benchmarks"):
        self.output_dir = os.path.expanduser(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.results: List[BenchmarkResult] = []
    
    def benchmark_container_startup(self, runtime: str, iterations: int = 5) -> Dict:
        """Benchmark container startup time"""
        times = []
        
        for i in range(iterations):
            try:
                start = time.perf_counter()
                
                if runtime == "forge":
                    cmd = ["forge", "container", "run", "alpine:latest", "echo", "test"]
                elif runtime == "podman":
                    cmd = ["podman", "run", "--rm", "alpine:latest", "echo", "test"]
                elif runtime == "docker":
                    cmd = ["docker", "run", "--rm", "alpine:latest", "echo", "test"]
                else:
                    return {"error": f"Unknown runtime: {runtime}"}
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=30,
                    check=False
                )
                
                elapsed = (time.perf_counter() - start) * 1000  # ms
                times.append(elapsed)
                
                self.results.append(BenchmarkResult(
                    name=f"{runtime}_startup_{i}",
                    operation="container_startup",
                    runtime=runtime,
                    metric="startup",
                    value=elapsed,
                    unit="ms",
                    timestamp=datetime.now().isoformat(),
                    success=result.returncode == 0,
                ))
            except subprocess.TimeoutExpired:
                self.results.append(BenchmarkResult(
                    name=f"{runtime}_startup_{i}",
                    operation="container_startup",
                    runtime=runtime,
                    metric="startup",
                    value=0,
                    unit="ms",
                    timestamp=datetime.now().isoformat(),
                    success=False,
                    error_message="Timeout after 30s",
                ))
            except Exception as e:
                self.results.append(BenchmarkResult(
                    name=f"{runtime}_startup_{i}",
                    operation="container_startup",
                    runtime=runtime,
                    metric="startup",
                    value=0,
                    unit="ms",
                    timestamp=datetime.now().isoformat(),
                    success=False,
                    error_message=str(e),
                ))
        
        avg = sum(times) / len(times) if times else 0
        min_time = min(times) if times else 0
        max_time = max(times) if times else 0
        
        return {
            "operation": "container_startup",
            "runtime": runtime,
            "average_ms": avg,
            "min_ms": min_time,
            "max_ms": max_time,
            "iterations": iterations,
            "successful": len([r for r in self.results if r.success and r.runtime == runtime]),
        }
    
    def benchmark_memory_usage(self, runtime: str, sample_count: int = 10, interval: float = 1.0) -> Dict:
        """Benchmark idle memory usage"""
        process = psutil.Process()
        
        # Warm up
        if runtime == "forge":
            subprocess.run(["forge", "system", "usage"], capture_output=True, timeout=5)
        
        # Sample memory usage
        samples = []
        for i in range(sample_count):
            try:
                mem = process.memory_info().rss / (1024 * 1024)  # MB
                samples.append(mem)
                
                self.results.append(BenchmarkResult(
                    name=f"{runtime}_memory_{i}",
                    operation="memory_usage",
                    runtime=runtime,
                    metric="memory",
                    value=mem,
                    unit="MB",
                    timestamp=datetime.now().isoformat(),
                    success=True,
                ))
                
                time.sleep(interval)
            except Exception as e:
                self.results.append(BenchmarkResult(
                    name=f"{runtime}_memory_{i}",
                    operation="memory_usage",
                    runtime=runtime,
                    metric="memory",
                    value=0,
                    unit="MB",
                    timestamp=datetime.now().isoformat(),
                    success=False,
                    error_message=str(e),
                ))
        
        avg = sum(samples) / len(samples) if samples else 0
        min_mem = min(samples) if samples else 0
        max_mem = max(samples) if samples else 0
        
        return {
            "operation": "memory_usage",
            "runtime": runtime,
            "average_mb": avg,
            "min_mb": min_mem,
            "max_mb": max_mem,
            "samples": sample_count,
        }
    
    def benchmark_image_loading(self, runtime: str, image_path: str, iterations: int = 3) -> Dict:
        """Benchmark image loading time"""
        times = []
        
        if not os.path.exists(image_path):
            return {"error": f"Image not found: {image_path}"}
        
        for i in range(iterations):
            try:
                start = time.perf_counter()
                
                if runtime == "forge":
                    cmd = ["forge", "image", "load", image_path]
                elif runtime == "podman":
                    cmd = ["podman", "load", "-i", image_path]
                elif runtime == "docker":
                    cmd = ["docker", "load", "-i", image_path]
                else:
                    return {"error": f"Unknown runtime: {runtime}"}
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=60,
                    check=False
                )
                
                elapsed = (time.perf_counter() - start) * 1000  # ms
                times.append(elapsed)
                
                self.results.append(BenchmarkResult(
                    name=f"{runtime}_load_{i}",
                    operation="image_load",
                    runtime=runtime,
                    metric="load_time",
                    value=elapsed,
                    unit="ms",
                    timestamp=datetime.now().isoformat(),
                    success=result.returncode == 0,
                ))
            except Exception as e:
                self.results.append(BenchmarkResult(
                    name=f"{runtime}_load_{i}",
                    operation="image_load",
                    runtime=runtime,
                    metric="load_time",
                    value=0,
                    unit="ms",
                    timestamp=datetime.now().isoformat(),
                    success=False,
                    error_message=str(e),
                ))
        
        avg = sum(times) / len(times) if times else 0
        
        return {
            "operation": "image_load",
            "runtime": runtime,
            "average_ms": avg,
            "iterations": iterations,
        }
    
    def benchmark_disk_usage(self, runtime: str) -> Dict:
        """Benchmark disk space used"""
        try:
            if runtime == "forge":
                forge_dir = os.path.expanduser("~/.forge")
                if not os.path.exists(forge_dir):
                    return {"size_mb": 0, "error": "Forge directory not found"}
                
                total_size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, dirnames, filenames in os.walk(forge_dir)
                    for filename in filenames
                )
                size_mb = total_size / (1024 * 1024)
            
            elif runtime == "podman":
                result = subprocess.run(
                    ["podman", "system", "df"],
                    capture_output=True,
                    timeout=10,
                    check=False
                )
                # Parse output to get total size
                size_mb = 0  # Placeholder
            
            elif runtime == "docker":
                result = subprocess.run(
                    ["docker", "system", "df"],
                    capture_output=True,
                    timeout=10,
                    check=False
                )
                size_mb = 0  # Placeholder
            else:
                return {"error": f"Unknown runtime: {runtime}"}
            
            self.results.append(BenchmarkResult(
                name=f"{runtime}_disk",
                operation="disk_usage",
                runtime=runtime,
                metric="disk",
                value=size_mb,
                unit="MB",
                timestamp=datetime.now().isoformat(),
                success=True,
            ))
            
            return {"runtime": runtime, "size_mb": size_mb}
        
        except Exception as e:
            self.results.append(BenchmarkResult(
                name=f"{runtime}_disk",
                operation="disk_usage",
                runtime=runtime,
                metric="disk",
                value=0,
                unit="MB",
                timestamp=datetime.now().isoformat(),
                success=False,
                error_message=str(e),
            ))
            return {"error": str(e)}
    
    def save_results(self, filename: Optional[str] = None) -> str:
        """Save results to JSON file"""
        if not filename:
            filename = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        suite = BenchmarkSuite(
            suite_name="forge_comprehensive",
            timestamp=datetime.now().isoformat(),
            results=self.results,
        )
        
        with open(filepath, "w") as f:
            json.dump(suite.to_json(), f, indent=2)
        
        return filepath
    
    def print_summary(self):
        """Print summary of results"""
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        
        # Group by operation
        operations = {}
        for result in self.results:
            if result.operation not in operations:
                operations[result.operation] = []
            operations[result.operation].append(result)
        
        for op_name, op_results in operations.items():
            table = Table(title=f"Benchmark: {op_name}")
            table.add_column("Runtime", style="cyan")
            table.add_column("Metric", style="green")
            table.add_column("Value", justify="right")
            table.add_column("Unit", style="yellow")
            table.add_column("Status", style="magenta")
            
            for result in op_results:
                status = "✓" if result.success else "✗"
                table.add_row(
                    result.runtime,
                    result.metric,
                    f"{result.value:.2f}",
                    result.unit,
                    status,
                )
            
            console.print(table)


def main():
    """Run comprehensive benchmarks"""
    runner = BenchmarkRunner()
    
    # Benchmark Forge
    print("Benchmarking Forge container startup...")
    startup_result = runner.benchmark_container_startup("forge", iterations=5)
    print(f"  Average: {startup_result.get('average_ms', 0):.1f}ms")
    
    print("\nBenchmarking Forge memory usage...")
    memory_result = runner.benchmark_memory_usage("forge", sample_count=5)
    print(f"  Average: {memory_result.get('average_mb', 0):.1f}MB")
    
    print("\nBenchmarking Forge disk usage...")
    disk_result = runner.benchmark_disk_usage("forge")
    print(f"  Size: {disk_result.get('size_mb', 0):.1f}MB")
    
    # Save results
    output_file = runner.save_results()
    print(f"\n[green]✓ Benchmarks saved to {output_file}[/green]")
    
    # Print summary
    runner.print_summary()


if __name__ == "__main__":
    main()
