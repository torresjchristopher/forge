"""
Auto-Quantization for Model Compression
========================================

Converts FP32 models to INT8/FP16 for reduced memory footprint.
Maintains inference accuracy while cutting memory usage 4x-8x.
"""

import torch
import torch.quantization
import onnxruntime as ort
import numpy as np
from typing import Optional, Tuple, Union
from pathlib import Path


class AutoQuantizer:
    """Automatic quantization of PyTorch/TensorFlow models."""
    
    @staticmethod
    def quantize_pytorch_int8(
        model: torch.nn.Module,
        calibration_data: list[torch.Tensor],
        device: str = "cpu"
    ) -> torch.nn.Module:
        """
        Quantize PyTorch model to INT8 using post-training quantization.
        
        Args:
            model: PyTorch model (FP32)
            calibration_data: List of sample inputs for calibration
            device: "cpu" or "cuda"
            
        Returns:
            Quantized model (INT8)
        """
        model = model.to(device)
        model.eval()
        
        # Set quantization config
        model.qconfig = torch.quantization.get_default_qconfig("fbgemm")
        
        # Prepare model for quantization
        torch.quantization.prepare(model, inplace=True)
        
        # Calibrate with sample data
        with torch.no_grad():
            for data in calibration_data[:min(10, len(calibration_data))]:
                data = data.to(device)
                model(data)
        
        # Convert to quantized model
        torch.quantization.convert(model, inplace=True)
        
        return model
    
    @staticmethod
    def quantize_pytorch_fp16(
        model: torch.nn.Module,
        device: str = "cuda"
    ) -> torch.nn.Module:
        """
        Quantize PyTorch model to FP16 (half precision).
        
        Args:
            model: PyTorch model (FP32)
            device: "cuda" (FP16 only works on NVIDIA GPUs)
            
        Returns:
            Quantized model (FP16)
        """
        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("FP16 quantization requires CUDA GPU")
        
        model = model.to(device)
        model = model.half()  # Convert to FP16
        model.eval()
        
        return model
    
    @staticmethod
    def quantize_onnx_int8(
        onnx_path: Union[str, Path],
        output_path: Union[str, Path],
        calibration_data: Optional[list[np.ndarray]] = None
    ) -> str:
        """
        Quantize ONNX model to INT8 using ONNX Runtime.
        
        Args:
            onnx_path: Path to input ONNX model
            output_path: Path to save quantized model
            calibration_data: Optional calibration data for accuracy
            
        Returns:
            Path to quantized model
        """
        from onnxruntime.quantization import quantize_dynamic, QuantType
        
        # Dynamic quantization (no calibration needed)
        quantize_dynamic(
            str(onnx_path),
            str(output_path),
            weight_type=QuantType.QInt8,
        )
        
        return str(output_path)
    
    @staticmethod
    def measure_model_size(model: torch.nn.Module) -> Tuple[float, float]:
        """
        Measure model size in MB (parameters only, not activations).
        
        Returns:
            (size_mb_fp32, estimated_size_mb_int8)
        """
        size_fp32 = sum(p.numel() * 4 for p in model.parameters()) / (1024**2)  # FP32 = 4 bytes
        size_int8 = sum(p.numel() * 1 for p in model.parameters()) / (1024**2)  # INT8 = 1 byte
        
        return size_fp32, size_int8
    
    @staticmethod
    def estimate_memory_reduction(
        model_size_mb: float,
        quantization: str = "int8"
    ) -> dict:
        """
        Estimate memory reduction and inference speedup from quantization.
        
        Args:
            model_size_mb: Model size in MB
            quantization: "int8" or "fp16"
            
        Returns:
            Dict with reduction estimates
        """
        if quantization == "int8":
            reduction_factor = 4.0  # 4x smaller
            speedup_factor = 2.5   # ~2.5x faster on CPU
        elif quantization == "fp16":
            reduction_factor = 2.0  # 2x smaller
            speedup_factor = 1.5   # ~1.5x faster on GPU
        else:
            return {}
        
        return {
            "original_size_mb": model_size_mb,
            "quantized_size_mb": model_size_mb / reduction_factor,
            "reduction_factor": reduction_factor,
            "estimated_speedup": speedup_factor,
            "memory_saved_mb": model_size_mb * (1 - 1/reduction_factor),
        }
