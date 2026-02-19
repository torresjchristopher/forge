"""
Forge ML Module v2.0
=====================

PyTorch and TensorFlow inference engine for ephemeral compute.
All models load into ephemeral RAM buffers - zero persistence,
complete cleanup guarantees on session exit.

Core Features:
- Ephemeral model loading (PyTorch & TensorFlow)
- Auto-quantization (INT8, FP16)
- Batch processing with dynamic scheduling
- Zero-residue memory cleanup verification
- Model agnostic inference (ResNet, BERT, EfficientNet, etc.)

Data Principles:
- No model persistence to disk
- No training data caching
- No intermediate results retained
- Complete memory wipe on session end
- Before/After baseline comparison for verification

Installation:
    pip install torch torchvision tensorflow onnxruntime psutil
"""

from .core import (
    MemoryBaseline,
    MemoryManager,
    InferenceEngine,
    PyTorchInference,
    TensorFlowInference,
    OnnxInference,
)

__version__ = "2.0.0-alpha"
__all__ = [
    "MemoryBaseline",
    "MemoryManager",
    "InferenceEngine",
    "PyTorchInference",
    "TensorFlowInference",
    "OnnxInference",
]
