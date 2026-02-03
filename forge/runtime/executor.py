"""Lightweight container execution engine.

Philosophy: Speed-first, minimal overhead, instant cleanup.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List
from pathlib import Path
import subprocess
import uuid
import time
import json
from datetime import datetime

from forge.runtime.filesystem import ContainerFilesystem, ImageSnapshot, ImageStore
from forge.runtime.resources import ResourceLimiter


@dataclass
class ContainerConfig:
    """Container configuration."""
    image: str
    command: List[str]
    ports: Optional[Dict[int, int]] = None
    volumes: Optional[Dict[str, str]] = None
    env: Optional[Dict[str, str]] = None
    memory_limit: Optional[int] = None  # MB
    cpu_limit: Optional[int] = None     # percentage
    timeout: Optional[int] = None
    name: Optional[str] = None


@dataclass
class ContainerStats:
    """Container runtime statistics."""
    container_id: str
    image: str
    status: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    exit_code: Optional[int] = None
    memory_mb: float = 0.0
    filesystem_mb: float = 0.0
    extraction_time_ms: float = 0.0


class Container:
    """Represents a running container with lightweight isolation."""
    
    def __init__(self, container_id: str, config: ContainerConfig, base_dir: Path):
        self.container_id = container_id
        self.config = config
        self.base_dir = base_dir
        self.process = None
        self.status = "created"
        
        # Lightweight components
        self.filesystem = ContainerFilesystem(container_id, base_dir / "containers")
        self.resources = ResourceLimiter(container_id, base_dir / "resources")
        self.stats = ContainerStats(
            container_id=container_id,
            image=config.image,
            status=self.status,
        )
    
    def prepare(self, image_snapshot: ImageSnapshot) -> bool:
        """Prepare container filesystem and resources."""
        try:
            # Extract image (critical path - measure this)
            extraction_time = self.filesystem.prepare(image_snapshot)
            self.stats.extraction_time_ms = extraction_time * 1000
            
            # Mount volumes
            if self.config.volumes:
                for src, dest in self.config.volumes.items():
                    self.filesystem.mount_volume(src, dest)
            
            # Set resource limits
            if self.config.memory_limit:
                self.resources.set_memory_limit(self.config.memory_limit)
            if self.config.cpu_limit:
                self.resources.set_cpu_limit(self.config.cpu_limit)
            
            return True
        except Exception as e:
            self.status = "error"
            print(f"Error preparing container: {e}")
            return False
    
    def run(self) -> int:
        """Execute the container."""
        start_time = time.time()
        self.status = "running"
        self.stats.status = "running"
        self.stats.start_time = datetime.now().isoformat()
        
        try:
            # Set up environment
            env = dict(os.environ) if hasattr(os, 'environ') else {}
            if self.config.env:
                env.update(self.config.env)
            
            # Run the command
            import os
            self.process = subprocess.run(
                self.config.command,
                timeout=self.config.timeout,
                capture_output=False,
                env=env,
            )
            
            exit_code = self.process.returncode
            self.status = "completed" if exit_code == 0 else "failed"
            self.stats.exit_code = exit_code
            
            return exit_code
        except subprocess.TimeoutExpired:
            self.status = "timeout"
            self.stats.exit_code = 124
            if self.process:
                self.process.kill()
            return 124
        except Exception as e:
            self.status = "error"
            self.stats.exit_code = 1
            print(f"Error running container: {e}")
            return 1
        finally:
            elapsed = time.time() - start_time
            self.stats.duration_seconds = elapsed
            self.stats.status = self.status
            self.stats.end_time = datetime.now().isoformat()
            self.stats.memory_mb = self.resources.get_current_usage().get("memory_mb", 0)
            self.stats.filesystem_mb = self.filesystem.get_size_mb()
    
    def stop(self):
        """Stop the container."""
        if self.process:
            self.process.terminate()
            self.status = "stopped"
    
    def cleanup(self) -> float:
        """Delete container filesystem instantly."""
        import time
        start = time.time()
        
        self.stop()
        cleanup_time = self.filesystem.cleanup()
        self.resources.cleanup()
        self.status = "cleaned"
        
        elapsed = time.time() - start
        return elapsed
    
    def get_stats(self) -> dict:
        """Get container statistics."""
        return {
            "container_id": self.container_id,
            "image": self.config.image,
            "status": self.status,
            "duration_seconds": self.stats.duration_seconds,
            "exit_code": self.stats.exit_code,
            "memory_mb": self.stats.memory_mb,
            "filesystem_mb": self.stats.filesystem_mb,
            "extraction_time_ms": self.stats.extraction_time_ms,
        }


class ContainerExecutor:
    """Main container execution engine - speed-first design."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.home() / ".forge"
        self.base_dir.mkdir(exist_ok=True)
        self.containers: Dict[str, Container] = {}
        self.image_store = ImageStore(self.base_dir / "images")
        self.stats_file = self.base_dir / "container_stats.json"
    
    def create_container(self, config: ContainerConfig) -> Container:
        """Create a new lightweight container."""
        container_id = config.name or str(uuid.uuid4())[:12]
        container = Container(container_id, config, self.base_dir)
        self.containers[container_id] = container
        return container
    
    def run_container(self, config: ContainerConfig) -> int:
        """Run a container with automatic cleanup."""
        container = self.create_container(config)
        
        # Prepare filesystem and resources
        try:
            image_path = self.base_dir / "images" / f"{config.image}.tar.gz"
            image_snapshot = ImageSnapshot(image_path)
            
            if not container.prepare(image_snapshot):
                container.cleanup()
                return 1
        except Exception as e:
            print(f"Error preparing image: {e}")
            container.cleanup()
            return 1
        
        # Execute
        exit_code = container.run()
        
        # Record stats
        self._record_stats(container)
        
        # Instant cleanup
        container.cleanup()
        del self.containers[container.container_id]
        
        return exit_code
    
    def get_container(self, container_id: str) -> Optional[Container]:
        """Get a container by ID."""
        return self.containers.get(container_id)
    
    def list_containers(self) -> List[Container]:
        """List all containers."""
        return list(self.containers.values())
    
    def delete_container(self, container_id: str) -> float:
        """Delete a container instantly."""
        container = self.get_container(container_id)
        if not container:
            return 0.0
        
        cleanup_time = container.cleanup()
        del self.containers[container_id]
        return cleanup_time
    
    def delete_image(self, image_name: str) -> float:
        """Delete an image instantly."""
        return self.image_store.delete_image(image_name)
    
    def cleanup_all(self):
        """Clean up all containers and images."""
        for container in list(self.containers.values()):
            container.cleanup()
        self.containers.clear()
    
    def _record_stats(self, container: Container):
        """Record container execution statistics."""
        try:
            stats = []
            if self.stats_file.exists():
                with open(self.stats_file) as f:
                    stats = json.load(f)
            
            stats.append(container.get_stats())
            
            # Keep only last 100 executions
            if len(stats) > 100:
                stats = stats[-100:]
            
            with open(self.stats_file, "w") as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            print(f"Warning: could not record stats: {e}")


# Import os for use in Container.run()
import os
