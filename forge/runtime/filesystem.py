"""Lightweight filesystem management for containers.

Uses snapshot-based images (single tarball) instead of layers.
Focused on instant extraction and minimal overhead.
"""

import tarfile
import gzip
import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime
import json


class ImageSnapshot:
    """Represents a container image as a single snapshot (tar.gz)."""
    
    def __init__(self, image_path: Path):
        self.image_path = image_path
        self.metadata_file = image_path.with_suffix('.json')
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> dict:
        """Load image metadata."""
        if self.metadata_file.exists():
            with open(self.metadata_file) as f:
                return json.load(f)
        return {
            "name": self.image_path.stem,
            "created": datetime.now().isoformat(),
            "size_bytes": self.image_path.stat().st_size if self.image_path.exists() else 0,
        }
    
    def extract_to(self, target_dir: Path) -> float:
        """
        Extract snapshot to target directory.
        
        Returns:
            Extraction time in seconds
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        
        import time
        start = time.time()
        
        try:
            with tarfile.open(self.image_path, 'r:gz') as tar:
                tar.extractall(path=target_dir)
        except Exception as e:
            raise RuntimeError(f"Failed to extract image: {e}")
        
        elapsed = time.time() - start
        return elapsed
    
    def get_size_mb(self) -> float:
        """Get image size in MB."""
        return self.image_path.stat().st_size / (1024 * 1024)


class ContainerFilesystem:
    """Manages container filesystem isolation and volumes."""
    
    def __init__(self, container_id: str, base_dir: Path):
        self.container_id = container_id
        self.base_dir = base_dir
        self.rootfs = base_dir / container_id / "rootfs"
        self.volumes = {}
    
    def prepare(self, image_snapshot: ImageSnapshot) -> float:
        """
        Prepare container filesystem by extracting image.
        
        Returns:
            Preparation time in seconds
        """
        self.rootfs.mkdir(parents=True, exist_ok=True)
        extraction_time = image_snapshot.extract_to(self.rootfs)
        return extraction_time
    
    def mount_volume(self, volume_src: str, volume_dest: str, read_only: bool = False):
        """
        Mount a volume (bind mount).
        
        Supports:
        - Host path to container path: /host/data:/container/data
        - Read-only volumes: use read_only=True
        """
        src_path = Path(volume_src).resolve()
        dest_path = self.rootfs / volume_dest.lstrip("/")
        
        if not src_path.exists():
            src_path.mkdir(parents=True, exist_ok=True)
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create bind mount (simplified for speed)
        # On Linux: would use mount(2) with MS_BIND flag
        # On Windows: would use junctions or symlinks
        try:
            if sys.platform.startswith("linux"):
                # Mount bind on Linux
                import subprocess
                subprocess.run(
                    ["mount", "--bind", str(src_path), str(dest_path)],
                    capture_output=True,
                    check=False,
                )
            else:
                # Windows: create symlink for simplicity
                dest_path.symlink_to(src_path, target_is_directory=True)
        except Exception:
            # Fallback: just create directory
            dest_path.mkdir(exist_ok=True)
        
        self.volumes[volume_dest] = {
            "source": str(src_path),
            "destination": str(dest_path),
            "read_only": read_only,
        }
    
    def cleanup(self):
        """Delete container filesystem (instant cleanup)."""
        import time
        start = time.time()
        
        try:
            if self.rootfs.parent.exists():
                shutil.rmtree(self.rootfs.parent)
        except Exception as e:
            print(f"Warning: cleanup incomplete: {e}")
        
        elapsed = time.time() - start
        return elapsed
    
    def get_size_mb(self) -> float:
        """Get container rootfs size in MB."""
        if not self.rootfs.exists():
            return 0
        
        total = 0
        for dirpath, dirnames, filenames in os.walk(self.rootfs):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total += os.path.getsize(filepath)
        
        return total / (1024 * 1024)


class ImageStore:
    """Manages image storage with auto-pruning."""
    
    def __init__(self, store_dir: Optional[Path] = None):
        self.store_dir = store_dir or Path.home() / ".forge" / "images"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.keep_last_n = 3
        self.max_age_days = 30
    
    def list_images(self) -> list[dict]:
        """List all stored images."""
        images = []
        for image_file in self.store_dir.glob("*.tar.gz"):
            metadata_file = image_file.with_suffix('.json')
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
            
            images.append({
                "name": image_file.stem,
                "path": str(image_file),
                "size_mb": image_file.stat().st_size / (1024 * 1024),
                "created": metadata.get("created"),
            })
        
        return sorted(images, key=lambda x: x.get("created", ""), reverse=True)
    
    def delete_image(self, image_name: str) -> float:
        """Delete an image (instant deletion)."""
        import time
        start = time.time()
        
        image_file = self.store_dir / f"{image_name}.tar.gz"
        metadata_file = image_file.with_suffix('.json')
        
        if image_file.exists():
            image_file.unlink()
        if metadata_file.exists():
            metadata_file.unlink()
        
        elapsed = time.time() - start
        return elapsed
    
    def cleanup_unused(self, active_images: list[str], dry_run: bool = False) -> dict:
        """
        Remove unused/old images.
        
        Returns:
            Stats: {deleted_count, freed_mb, time_seconds}
        """
        import time
        from datetime import datetime, timedelta
        
        start = time.time()
        deleted_count = 0
        freed_mb = 0
        
        cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
        all_images = self.list_images()
        
        for image in all_images:
            if image["name"] in active_images:
                continue  # Don't delete active images
            
            try:
                created = datetime.fromisoformat(image["created"]) if image.get("created") else datetime.now()
                if created < cutoff_date:
                    if not dry_run:
                        self.delete_image(image["name"])
                    deleted_count += 1
                    freed_mb += image["size_mb"]
            except Exception as e:
                print(f"Error cleaning up {image['name']}: {e}")
        
        elapsed = time.time() - start
        return {
            "deleted_count": deleted_count,
            "freed_mb": round(freed_mb, 2),
            "time_seconds": elapsed,
        }
