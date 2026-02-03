"""Container execution engine."""

from dataclasses import dataclass
from typing import Dict, Optional, List
from pathlib import Path
import subprocess
import uuid


@dataclass
class ContainerConfig:
    """Container configuration."""
    image: str
    command: List[str]
    ports: Optional[Dict[int, int]] = None
    volumes: Optional[Dict[str, str]] = None
    env: Optional[Dict[str, str]] = None
    memory_limit: Optional[str] = None
    cpu_limit: Optional[str] = None
    timeout: Optional[int] = None


class Container:
    """Represents a running container."""
    
    def __init__(self, container_id: str, config: ContainerConfig):
        self.container_id = container_id
        self.config = config
        self.process = None
        self.status = "created"
    
    def run(self) -> int:
        """Execute the container."""
        self.status = "running"
        try:
            self.process = subprocess.run(
                self.config.command,
                timeout=self.config.timeout,
                capture_output=False,
            )
            self.status = "completed" if self.process.returncode == 0 else "failed"
            return self.process.returncode
        except subprocess.TimeoutExpired:
            self.status = "timeout"
            if self.process:
                self.process.kill()
            return 124
        except Exception as e:
            self.status = "error"
            raise e
    
    def stop(self):
        """Stop the container."""
        if self.process:
            self.process.terminate()
            self.status = "stopped"
    
    def cleanup(self):
        """Clean up container resources."""
        self.stop()
        self.status = "cleaned"


class ContainerExecutor:
    """Main container execution engine."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.home() / ".forge"
        self.base_dir.mkdir(exist_ok=True)
        self.containers: Dict[str, Container] = {}
    
    def create_container(self, config: ContainerConfig) -> Container:
        """Create a new container."""
        container_id = str(uuid.uuid4())[:12]
        container = Container(container_id, config)
        self.containers[container_id] = container
        return container
    
    def run_container(self, config: ContainerConfig) -> int:
        """Run a container and wait for completion."""
        container = self.create_container(config)
        return container.run()
    
    def get_container(self, container_id: str) -> Optional[Container]:
        """Get a container by ID."""
        return self.containers.get(container_id)
    
    def list_containers(self) -> List[Container]:
        """List all containers."""
        return list(self.containers.values())
    
    def cleanup_all(self):
        """Clean up all containers."""
        for container in self.containers.values():
            container.cleanup()
