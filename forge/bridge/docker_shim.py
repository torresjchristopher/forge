"""
Docker-to-Forge Bridge.

Converts legacy Docker/OCI images into Forge "Detonation Seeds".
"""

import subprocess
import tarfile
import os
from pathlib import Path

class DockerShim:
    """
    Utility to ingest Docker images and flatten them into 
    Sovereign Forge seeds.
    """
    
    def __init__(self, export_dir: str = "/tmp/forge_seeds"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def ingest_image(self, image_tag: str) -> str:
        """
        Takes a local Docker image and flattens it into a Forge Seed.
        """
        seed_name = image_tag.replace(":", "_").replace("/", "-") + ".tar.gz"
        seed_path = self.export_dir / seed_name
        
        print(f"[BRIDGE] Ingesting legacy image: {image_tag}...")
        
        # 1. Create a temporary container to export the filesystem
        container_id = subprocess.check_output(
            ["docker", "create", image_tag]
        ).decode().strip()
        
        try:
            # 2. Export the flattened filesystem
            print(f"[BRIDGE] Flattening layers into O(1) seed...")
            with open(seed_path, "wb") as f:
                subprocess.run(["docker", "export", container_id], stdout=f)
                
            print(f"[BRIDGE] Successfully created Seed: {seed_path}")
            return str(seed_path)
            
        finally:
            # 3. Cleanup the legacy container
            subprocess.run(["docker", "rm", container_id], capture_output=True)

    def detonate_legacy(self, image_tag: str, command: list):
        """
        One-command bridge: Ingest -> Detonate -> Execute -> Implode.
        """
        seed = self.ingest_image(image_tag)
        # Here we would hand off to the RecursiveEngine
        print(f"[BRIDGE] Ready to detonate {image_tag} in Recursive RAM-mode.")
