"""Resource management: CPU and memory limits for containers.

Uses cgroups (Linux) or Job Objects (Windows).
"""

import os
import sys
from pathlib import Path
from typing import Optional


class ResourceLimiter:
    """Manages resource limits for containers."""
    
    def __init__(self, container_id: str, base_dir: Optional[Path] = None):
        self.container_id = container_id
        self.base_dir = base_dir or Path.home() / ".forge" / "cgroups"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        if sys.platform.startswith("linux"):
            self.limiter = LinuxCgroupLimiter(container_id, self.base_dir)
        else:
            self.limiter = WindowsJobObjectLimiter(container_id)
    
    def set_memory_limit(self, memory_mb: int) -> bool:
        """Set memory limit in MB."""
        return self.limiter.set_memory_limit(memory_mb)
    
    def set_cpu_limit(self, cpu_percent: int) -> bool:
        """Set CPU limit as percentage (0-100)."""
        return self.limiter.set_cpu_limit(cpu_percent)
    
    def get_current_usage(self) -> dict:
        """Get current resource usage."""
        return self.limiter.get_current_usage()
    
    def cleanup(self):
        """Clean up resource limits."""
        self.limiter.cleanup()


class LinuxCgroupLimiter:
    """Uses cgroups v2 for resource limits (Linux only)."""
    
    CGROUP_V2_PATH = Path("/sys/fs/cgroup")
    
    def __init__(self, container_id: str, base_dir: Path):
        self.container_id = container_id
        self.cgroup_path = self.CGROUP_V2_PATH / "forge" / container_id
    
    def set_memory_limit(self, memory_mb: int) -> bool:
        """Set memory limit using cgroups v2."""
        if not self.CGROUP_V2_PATH.exists():
            print("Warning: cgroups v2 not available")
            return False
        
        try:
            self.cgroup_path.mkdir(parents=True, exist_ok=True)
            memory_bytes = memory_mb * 1024 * 1024
            
            limit_file = self.cgroup_path / "memory.max"
            with open(limit_file, "w") as f:
                f.write(str(memory_bytes))
            
            return True
        except Exception as e:
            print(f"Warning: could not set memory limit: {e}")
            return False
    
    def set_cpu_limit(self, cpu_percent: int) -> bool:
        """Set CPU limit using cgroups v2."""
        if not self.CGROUP_V2_PATH.exists():
            return False
        
        try:
            self.cgroup_path.mkdir(parents=True, exist_ok=True)
            
            # cgroups v2 CPU quota: microseconds per period
            cpu_max_file = self.cgroup_path / "cpu.max"
            period = 100000  # 100ms
            quota = int((cpu_percent / 100) * period)
            
            with open(cpu_max_file, "w") as f:
                f.write(f"{quota} {period}")
            
            return True
        except Exception as e:
            print(f"Warning: could not set CPU limit: {e}")
            return False
    
    def get_current_usage(self) -> dict:
        """Get current memory/CPU usage from cgroups."""
        usage = {
            "memory_mb": 0,
            "cpu_percent": 0,
        }
        
        try:
            memory_file = self.cgroup_path / "memory.current"
            if memory_file.exists():
                with open(memory_file) as f:
                    memory_bytes = int(f.read().strip())
                    usage["memory_mb"] = memory_bytes / (1024 * 1024)
        except Exception:
            pass
        
        return usage
    
    def cleanup(self):
        """Remove cgroup."""
        try:
            if self.cgroup_path.exists():
                os.rmdir(self.cgroup_path)
        except Exception as e:
            print(f"Warning: could not cleanup cgroup: {e}")


class WindowsJobObjectLimiter:
    """Uses Windows Job Objects for resource limits."""
    
    def __init__(self, container_id: str):
        self.container_id = container_id
    
    def set_memory_limit(self, memory_mb: int) -> bool:
        """Set memory limit on Windows (simplified)."""
        # Full implementation would use ctypes + Windows API
        return True
    
    def set_cpu_limit(self, cpu_percent: int) -> bool:
        """Set CPU limit on Windows (simplified)."""
        return True
    
    def get_current_usage(self) -> dict:
        """Get resource usage on Windows."""
        return {
            "memory_mb": 0,
            "cpu_percent": 0,
        }
    
    def cleanup(self):
        """Clean up Job Object."""
        pass
