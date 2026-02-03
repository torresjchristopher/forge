"""Performance benchmarking for Forge vs Podman."""

import time
import subprocess
import json
from pathlib import Path
from typing import Dict
from forge.runtime.executor import ContainerExecutor, ContainerConfig


class ForgeBenchmark:
    """Benchmark Forge performance."""
    
    def __init__(self):
        self.executor = ContainerExecutor()
        self.results = {}
    
    def benchmark_container_startup(self, iterations: int = 10) -> Dict[str, float]:
        """Measure container startup time."""
        times = []
        
        for i in range(iterations):
            config = ContainerConfig(
                image="test:latest",
                command=["echo", "hello"],
                name=f"bench-{i}",
            )
            
            start = time.time()
            exit_code = self.executor.run_container(config)
            elapsed = time.time() - start
            
            if exit_code == 0:
                times.append(elapsed)
        
        return {
            "min_ms": min(times) * 1000,
            "max_ms": max(times) * 1000,
            "avg_ms": sum(times) / len(times) * 1000,
            "iterations": iterations,
        }
    
    def benchmark_image_extraction(self, iterations: int = 5) -> Dict[str, float]:
        """Measure image extraction time."""
        times = []
        
        from forge.runtime.filesystem import ImageSnapshot, ImageStore
        
        image_store = ImageStore()
        images = image_store.list_images()
        
        if not images:
            return {"error": "No images available for benchmarking"}
        
        test_image = images[0]
        
        for i in range(iterations):
            image_path = Path.home() / ".forge" / "images" / f"{test_image['name']}.tar.gz"
            
            if image_path.exists():
                snapshot = ImageSnapshot(image_path)
                target_dir = Path("/tmp") / f"bench-extract-{i}"
                
                start = time.time()
                elapsed_extraction = snapshot.extract_to(target_dir)
                elapsed = time.time() - start
                
                times.append(elapsed)
        
        return {
            "min_ms": min(times) * 1000,
            "max_ms": max(times) * 1000,
            "avg_ms": sum(times) / len(times) * 1000,
            "iterations": iterations,
        }
    
    def benchmark_deletion(self, iterations: int = 10) -> Dict[str, float]:
        """Measure container deletion speed."""
        times = []
        
        # Create containers first
        containers = []
        for i in range(iterations):
            config = ContainerConfig(
                image="test:latest",
                command=["sleep", "1"],
                name=f"bench-delete-{i}",
            )
            container = self.executor.create_container(config)
            containers.append(container)
        
        # Measure deletion time
        for container in containers:
            start = time.time()
            cleanup_time = self.executor.delete_container(container.container_id)
            elapsed = time.time() - start
            times.append(elapsed)
        
        return {
            "min_ms": min(times) * 1000,
            "max_ms": max(times) * 1000,
            "avg_ms": sum(times) / len(times) * 1000,
            "iterations": iterations,
        }
    
    def run_all_benchmarks(self):
        """Run all benchmarks."""
        print("Running Forge performance benchmarks...\n")
        
        print("1. Container startup (10 iterations)")
        self.results["container_startup"] = self.benchmark_container_startup(10)
        print(f"   Average: {self.results['container_startup']['avg_ms']:.1f}ms")
        
        print("\n2. Image extraction (5 iterations)")
        self.results["image_extraction"] = self.benchmark_image_extraction(5)
        if "error" not in self.results["image_extraction"]:
            print(f"   Average: {self.results['image_extraction']['avg_ms']:.1f}ms")
        else:
            print(f"   {self.results['image_extraction']['error']}")
        
        print("\n3. Container deletion (10 iterations)")
        self.results["deletion"] = self.benchmark_deletion(10)
        print(f"   Average: {self.results['deletion']['avg_ms']:.1f}ms")
        
        return self.results


if __name__ == "__main__":
    import sys
    
    benchmark = ForgeBenchmark()
    results = benchmark.run_all_benchmarks()
    
    print("\n" + "="*60)
    print("BENCHMARK RESULTS")
    print("="*60)
    print(json.dumps(results, indent=2))
