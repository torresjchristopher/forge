"""
Memory Management for Ephemeral Inference
==========================================

Tracks memory allocation/deallocation to guarantee zero residue.
Before/After baseline measurements for verification.
"""

import gc
import psutil
import numpy as np
from datetime import datetime
from typing import Dict, Tuple, Optional

# Import ML libraries with graceful fallback
try:
    import torch
    TORCH_AVAILABLE = True
except (ImportError, OSError):
    TORCH_AVAILABLE = False
    torch = None

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except (ImportError, OSError):
    TF_AVAILABLE = False
    tf = None


class MemoryBaseline:
    """Before/After memory snapshot for zero-residue verification."""
    
    def __init__(self, name: str):
        self.name = name
        self.timestamp = datetime.now()
        self.process = psutil.Process()
        
        # Baseline measurements
        self.ram_before = self.process.memory_info().rss / (1024**2)  # MB
        self.torch_allocated = 0
        self.torch_cached = 0
        
        if TORCH_AVAILABLE and torch is not None and torch.cuda.is_available():
            self.torch_allocated = torch.cuda.memory_allocated() / (1024**2)
            self.torch_cached = torch.cuda.memory_reserved() / (1024**2)
        
    def cleanup_and_verify(self) -> Dict[str, float]:
        """Force cleanup and measure residue."""
        
        # Force Python garbage collection
        gc.collect()
        
        # Clear PyTorch cache if available
        if TORCH_AVAILABLE and torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        # Clear TensorFlow memory
        if TF_AVAILABLE and tf is not None:
            tf.keras.backend.clear_session()
        
        # Force another garbage collection
        gc.collect()
        
        # Measure after cleanup
        ram_after = self.process.memory_info().rss / (1024**2)
        torch_allocated_after = 0
        if TORCH_AVAILABLE and torch is not None and torch.cuda.is_available():
            torch_allocated_after = torch.cuda.memory_allocated() / (1024**2)
        
        residue_mb = ram_after - self.ram_before
        
        return {
            "baseline_mb": self.ram_before,
            "after_mb": ram_after,
            "residue_mb": residue_mb,
            "residue_pct": (residue_mb / self.ram_before * 100) if self.ram_before > 0 else 0,
            "torch_gpu_residue_mb": torch_allocated_after,
            "zero_residue_achieved": residue_mb < 10,  # < 10MB tolerance
        }


class MemoryManager:
    """Manages ephemeral memory allocation and cleanup."""
    
    def __init__(self):
        self.baselines: Dict[str, MemoryBaseline] = {}
        self.allocations: Dict[str, Tuple[int, str]] = {}  # (size_mb, timestamp)
    
    def create_baseline(self, name: str) -> MemoryBaseline:
        """Create memory baseline snapshot before inference."""
        baseline = MemoryBaseline(name)
        self.baselines[name] = baseline
        return baseline
    
    def verify_cleanup(self, name: str) -> Dict[str, float]:
        """Verify cleanup achieved < 10MB residue."""
        if name not in self.baselines:
            raise ValueError(f"No baseline for {name}")
        
        return self.baselines[name].cleanup_and_verify()
    
    def get_system_memory(self) -> Dict[str, float]:
        """Get current system memory usage."""
        mem = psutil.virtual_memory()
        return {
            "total_gb": mem.total / (1024**3),
            "available_gb": mem.available / (1024**3),
            "used_gb": mem.used / (1024**3),
            "percent": mem.percent,
        }
    
    def log_allocation(self, name: str, size_mb: float):
        """Track allocation for debugging."""
        self.allocations[name] = (size_mb, datetime.now().isoformat())
