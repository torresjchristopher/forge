"""
Core Inference Engine for Ephemeral Compute
===========================================

Loads models into ephemeral RAM buffers, executes inference,
cleans up completely. Zero model/data persistence.
"""

import numpy as np
from typing import Dict, List, Union, Optional, Any
from contextlib import contextmanager
import gc
import time

from .memory import MemoryManager, MemoryBaseline

# Import ML libraries with graceful fallback for testing
try:
    import torch
    import torch.nn.functional as F
    import torchvision.models as models
    import torchvision.transforms as transforms
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


class EphemeralBuffer:
    """Ephemeral in-memory buffer for models and data."""
    
    def __init__(self, max_size_mb: int = 2048):
        self.max_size_mb = max_size_mb
        self.model: Optional[Any] = None
        self.data: Dict[str, Any] = {}
        self.created_at = time.time()
    
    def load_model(self, model: Any, device: str = "cpu"):
        """Load model into ephemeral buffer."""
        if TORCH_AVAILABLE and torch is not None:
            self.model = model.to(device) if hasattr(model, 'to') else model
            if hasattr(self.model, 'eval'):
                self.model.eval()
        else:
            self.model = model
    
    def store_tensor(self, name: str, tensor: Any):
        """Store tensor in buffer."""
        if len(self.data) > 100:  # Prevent unbounded growth
            self.clear()
        self.data[name] = tensor
    
    def get_tensor(self, name: str) -> Optional[Any]:
        """Retrieve tensor from buffer."""
        return self.data.get(name)
    
    def clear(self):
        """Clear all data from buffer."""
        self.data.clear()
        gc.collect()
        if TORCH_AVAILABLE and torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()


class ModelInference:
    """
    Ephemeral inference engine with zero-residue guarantees.
    
    Example:
        inference = ModelInference(quantization="int8")
        results = inference.infer_pytorch(
            model_name="resnet50",
            inputs=batch_images,
            device="cuda"
        )
        stats = inference.cleanup_and_verify()  # < 10MB residue
    """
    
    PYTORCH_MODELS = {
        "resnet50": models.resnet50,
        "resnet101": models.resnet101,
        "vgg16": models.vgg16,
        "mobilenet_v2": models.mobilenet_v2,
    }
    
    def __init__(self, quantization: Optional[str] = None, device: str = "cpu"):
        """
        Initialize inference engine.
        
        Args:
            quantization: None, "int8", or "fp16"
            device: "cpu" or "cuda"
        """
        self.quantization = quantization
        self.device = device
        self.memory_manager = MemoryManager()
        self.buffer = EphemeralBuffer()
        self.baseline: Optional[MemoryBaseline] = None
        
        if quantization == "fp16" and device == "cpu":
            raise ValueError("FP16 quantization requires CUDA GPU")
    
    @contextmanager
    def ephemeral_session(self, session_name: str = "inference"):
        """
        Context manager for ephemeral inference sessions.
        
        Guarantees complete cleanup on exit, even if errors occur.
        """
        self.baseline = self.memory_manager.create_baseline(session_name)
        
        try:
            yield self
        finally:
            # Force cleanup
            self.buffer.clear()
            self.baseline = None
            cleanup_stats = self.memory_manager.verify_cleanup(session_name)
            print(f"[CLEANUP] {session_name}: {cleanup_stats}")
    
    def load_pytorch_model(
        self,
        model_name: str,
        pretrained: bool = True,
        device: Optional[str] = None
    ) -> Any:
        """Load PyTorch model from torchvision."""
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available. Install with: pip install torch torchvision")
        
        if model_name not in self.PYTORCH_MODELS:
            raise ValueError(f"Unknown model: {model_name}")
        
        device = device or self.device
        
        # Load model
        model_fn = self.PYTORCH_MODELS[model_name]
        model = model_fn(pretrained=pretrained)
        
        # Apply quantization if requested
        if self.quantization == "int8":
            from .quantizer import AutoQuantizer
            model = AutoQuantizer.quantize_pytorch_int8(model, [], device)
        elif self.quantization == "fp16":
            from .quantizer import AutoQuantizer
            model = AutoQuantizer.quantize_pytorch_fp16(model, device)
        
        # Move to device and eval mode
        model = model.to(device)
        model.eval()
        
        self.buffer.load_model(model, device)
        return model
    
    def infer_pytorch(
        self,
        model_name: str,
        inputs: Union[np.ndarray, Any],
        batch_size: int = 32,
        device: Optional[str] = None,
        return_logits: bool = False
    ) -> Dict[str, Any]:
        """
        Run batch inference with PyTorch model.
        
        Args:
            model_name: "resnet50", "vgg16", etc.
            inputs: Numpy array or tensor
            batch_size: Batch size for processing
            device: "cpu" or "cuda"
            return_logits: If True, return raw logits; else return probabilities
            
        Returns:
            Dict with predictions, logits/probabilities, timing
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available")
        
        device = device or self.device
        start_time = time.time()
        
        # Load model
        model = self.load_pytorch_model(model_name, device=device)
        
        # Convert to tensor if needed
        if isinstance(inputs, np.ndarray):
            inputs = torch.from_numpy(inputs).float()
        elif not isinstance(inputs, torch.Tensor):
            inputs = torch.tensor(inputs, dtype=torch.float32)
        
        inputs = inputs.to(device)
        
        # Batch processing
        all_outputs = []
        num_batches = (len(inputs) + batch_size - 1) // batch_size
        
        with torch.no_grad():
            for i in range(num_batches):
                batch = inputs[i*batch_size:(i+1)*batch_size]
                output = model(batch)
                all_outputs.append(output.cpu())
        
        # Concatenate outputs
        logits = torch.cat(all_outputs, dim=0)
        
        # Get probabilities and predictions
        if hasattr(model, 'fc'):  # Classification model
            probs = F.softmax(logits, dim=1)
            predictions = torch.argmax(probs, dim=1)
            
            return {
                "predictions": predictions.numpy(),
                "probabilities": probs.numpy() if not return_logits else None,
                "logits": logits.numpy() if return_logits else None,
                "num_samples": len(inputs),
                "num_batches": num_batches,
                "inference_time_sec": time.time() - start_time,
                "throughput_samples_per_sec": len(inputs) / (time.time() - start_time),
                "device": device,
                "quantization": self.quantization,
            }
        else:
            return {
                "output": logits.numpy(),
                "num_samples": len(inputs),
                "inference_time_sec": time.time() - start_time,
                "throughput_samples_per_sec": len(inputs) / (time.time() - start_time),
            }
    
    def cleanup_and_verify(self) -> Dict[str, Any]:
        """
        Force cleanup and verify zero residue (< 10MB).
        
        Returns:
            Cleanup statistics including residue_mb and zero_residue_achieved
        """
        if not self.baseline:
            raise RuntimeError("No baseline created - use ephemeral_session context")
        
        return self.baseline.cleanup_and_verify()
    
    def get_memory_stats(self) -> Dict[str, float]:
        """Get current system memory statistics."""
        return self.memory_manager.get_system_memory()
