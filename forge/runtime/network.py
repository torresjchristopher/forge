"""Network management for containers.

Port mapping and network namespace support.
Focus on speed and simplicity.
"""

import sys
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import subprocess


@dataclass
class PortMapping:
    """Represents a port mapping: container_port -> host_port"""
    container_port: int
    host_port: Optional[int] = None  # None = auto-assign
    protocol: str = "tcp"


class LinuxNetworking:
    """Network management using Linux namespaces."""
    
    def __init__(self, container_id: str):
        self.container_id = container_id
        self.port_mappings: Dict[int, int] = {}
        self.veth_pair = (f"veth{container_id[:8]}", f"eth0")
    
    def create_network_namespace(self) -> bool:
        """Create a network namespace for the container."""
        try:
            # Create network namespace
            subprocess.run(
                ["ip", "netns", "add", self.container_id],
                capture_output=True,
                check=False,
            )
            return True
        except Exception as e:
            print(f"Warning: could not create network namespace: {e}")
            return False
    
    def map_port(self, container_port: int, host_port: Optional[int] = None) -> int:
        """
        Map a container port to host port.
        
        Args:
            container_port: Port inside container
            host_port: Port on host (None = auto-assign from ephemeral range)
        
        Returns:
            Actual host port used
        """
        if host_port is None:
            # Auto-assign from ephemeral range (49152-65535)
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', 0))
                host_port = s.getsockname()[1]
        
        self.port_mappings[container_port] = host_port
        
        # Set up port forwarding (simplified)
        # Real implementation would use iptables or nftables
        try:
            subprocess.run(
                ["iptables", "-t", "nat", "-A", "DOCKER",
                 "-p", "tcp", "-d", "127.0.0.1",
                 "--dport", str(host_port),
                 "-j", "DNAT", "--to-destination", f"127.0.0.1:{container_port}"],
                capture_output=True,
                check=False,
            )
        except Exception as e:
            print(f"Warning: port mapping setup incomplete: {e}")
        
        return host_port
    
    def cleanup_network(self):
        """Clean up network namespace and port mappings."""
        try:
            subprocess.run(
                ["ip", "netns", "delete", self.container_id],
                capture_output=True,
                check=False,
            )
        except Exception:
            pass


class WindowsNetworking:
    """Network management for Windows (simplified)."""
    
    def __init__(self, container_id: str):
        self.container_id = container_id
        self.port_mappings: Dict[int, int] = {}
    
    def create_network_namespace(self) -> bool:
        """Windows doesn't have namespaces, just use port forwarding."""
        return True
    
    def map_port(self, container_port: int, host_port: Optional[int] = None) -> int:
        """
        Map a container port to host port using netsh (Windows).
        
        On Windows, this is simplified to use loopback forwarding.
        """
        if host_port is None:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', 0))
                host_port = s.getsockname()[1]
        
        self.port_mappings[container_port] = host_port
        
        # Simplified: would use netsh portproxy
        try:
            subprocess.run(
                ["netsh", "interface", "portproxy", "add", "v4tov4",
                 "listenport=" + str(host_port),
                 "connectaddress=127.0.0.1",
                 "connectport=" + str(container_port)],
                capture_output=True,
                check=False,
            )
        except Exception as e:
            print(f"Warning: port mapping setup incomplete: {e}")
        
        return host_port
    
    def cleanup_network(self):
        """Clean up port mappings."""
        for container_port, host_port in self.port_mappings.items():
            try:
                subprocess.run(
                    ["netsh", "interface", "portproxy", "delete", "v4tov4",
                     "listenport=" + str(host_port)],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass


class ContainerNetworking:
    """Platform-agnostic container networking."""
    
    def __init__(self, container_id: str):
        self.container_id = container_id
        
        if sys.platform.startswith("linux"):
            self.networking = LinuxNetworking(container_id)
        elif sys.platform == "win32":
            self.networking = WindowsNetworking(container_id)
        else:
            self.networking = WindowsNetworking(container_id)  # Fallback
    
    def create_network_namespace(self) -> bool:
        """Create network namespace."""
        return self.networking.create_network_namespace()
    
    def map_port(self, container_port: int, host_port: Optional[int] = None) -> int:
        """Map container port to host port."""
        return self.networking.map_port(container_port, host_port)
    
    def cleanup_network(self):
        """Clean up networking."""
        self.networking.cleanup_network()
    
    def get_port_mappings(self) -> Dict[int, int]:
        """Get all port mappings."""
        return self.networking.port_mappings.copy()
