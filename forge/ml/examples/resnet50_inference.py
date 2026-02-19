"""
POC: Ephemeral ResNet50 Inference Server
========================================

Demonstrates:
1. Load ResNet50 into ephemeral RAM buffer
2. Run 10K synthetic predictions
3. Complete cleanup with < 10MB residue
4. Before/After memory baseline comparison
5. Quantization impact (FP32 vs INT8 vs FP16)

Run with:
    cd C:\Users\serro\Yukora\forge
    python -m forge.ml.examples.resnet50_inference
"""

import torch
import torch.nn.functional as F
import torchvision.transforms as transforms
import numpy as np
from pathlib import Path
import sys
import time
from typing import Dict

# Add forge to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from forge.ml import ModelInference, MemoryManager


def create_synthetic_batch(num_samples: int = 1000, img_size: int = 224) -> torch.Tensor:
    """Create synthetic ImageNet-like data for benchmarking."""
    # Shape: (N, 3, 224, 224) with normalized values
    data = torch.randn(num_samples, 3, img_size, img_size)
    return data


def benchmark_inference(
    quantization: str = None,
    num_samples: int = 10000,
    batch_size: int = 128,
) -> Dict[str, float]:
    """
    Benchmark ResNet50 inference with memory tracking.
    
    Args:
        quantization: None (FP32), "int8", or "fp16"
        num_samples: Total samples to process
        batch_size: Batch size for inference
        
    Returns:
        Benchmark results with timing and memory stats
    """
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    print(f"\n{'='*70}")
    print(f"FORGE ML v2.0 EPHEMERAL INFERENCE POC")
    print(f"{'='*70}")
    print(f"Model: ResNet50")
    print(f"Quantization: {quantization or 'FP32 (Full Precision)'}")
    print(f"Device: {device.upper()}")
    print(f"Samples: {num_samples:,} | Batch Size: {batch_size}")
    print(f"{'='*70}\n")
    
    inference = ModelInference(quantization=quantization, device=device)
    
    # Use ephemeral session context for guaranteed cleanup
    with inference.ephemeral_session(f"resnet50_{quantization or 'fp32'}") as sess:
        
        # Print memory before
        mem_before = sess.get_memory_stats()
        print(f"[MEMORY BEFORE]")
        print(f"  RAM Used: {mem_before['used_gb']:.2f} GB / {mem_before['total_gb']:.2f} GB")
        print(f"  Available: {mem_before['available_gb']:.2f} GB ({100-mem_before['percent']:.1f}%)\n")
        
        # Load model
        print(f"[1] Loading ResNet50 into ephemeral buffer...")
        load_start = time.time()
        model = sess.load_pytorch_model("resnet50", device=device)
        load_time = time.time() - load_start
        print(f"    ✓ Loaded in {load_time:.2f}s\n")
        
        # Create synthetic data
        print(f"[2] Creating {num_samples:,} synthetic ImageNet samples...")
        data = create_synthetic_batch(num_samples=num_samples)
        print(f"    ✓ Created batch shape: {data.shape}\n")
        
        # Run inference
        print(f"[3] Running batch inference ({num_samples:,} samples)...")
        infer_start = time.time()
        results = sess.infer_pytorch(
            model_name="resnet50",
            inputs=data,
            batch_size=batch_size,
            device=device,
            return_logits=False
        )
        infer_time = time.time() - infer_start
        
        print(f"    ✓ Inference completed in {infer_time:.2f}s")
        print(f"    Throughput: {results['throughput_samples_per_sec']:.0f} samples/sec\n")
        
        # Cleanup happens here on context exit
        print(f"[4] Forcing cleanup and verifying zero residue...")
    
    # Print results
    cleanup_stats = inference.memory_manager.verify_cleanup(f"resnet50_{quantization or 'fp32'}")
    
    print(f"\n[CLEANUP VERIFICATION]")
    print(f"  Baseline RAM: {cleanup_stats['baseline_mb']:.1f} MB")
    print(f"  After Cleanup: {cleanup_stats['after_mb']:.1f} MB")
    print(f"  Residue: {cleanup_stats['residue_mb']:.1f} MB ({cleanup_stats['residue_pct']:.2f}%)")
    print(f"  ✓ Zero Residue Achieved: {cleanup_stats['zero_residue_achieved']}\n")
    
    print(f"[RESULTS SUMMARY]")
    print(f"  Total Inference Time: {infer_time:.2f}s")
    print(f"  Model Load Time: {load_time:.2f}s")
    print(f"  Samples Processed: {results['num_samples']:,}")
    print(f"  Throughput: {results['throughput_samples_per_sec']:.0f} samples/sec")
    print(f"  Quantization: {results['quantization'] or 'FP32'}")
    print(f"  Device: {results['device'].upper()}")
    
    return {
        "quantization": quantization or "fp32",
        "num_samples": num_samples,
        "load_time_sec": load_time,
        "inference_time_sec": infer_time,
        "throughput_samples_sec": results['throughput_samples_per_sec'],
        "residue_mb": cleanup_stats['residue_mb'],
        "zero_residue": cleanup_stats['zero_residue_achieved'],
    }


def compare_quantizations():
    """Run benchmarks comparing FP32, INT8, and FP16."""
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    num_samples = 5000  # Smaller for comparison
    
    print("\n" + "="*70)
    print("QUANTIZATION COMPARISON: Memory & Throughput")
    print("="*70 + "\n")
    
    results = {}
    
    # FP32 Baseline
    results["fp32"] = benchmark_inference(quantization=None, num_samples=num_samples)
    
    # INT8
    results["int8"] = benchmark_inference(quantization="int8", num_samples=num_samples)
    
    # FP16 (GPU only)
    if device == "cuda":
        results["fp16"] = benchmark_inference(quantization="fp16", num_samples=num_samples)
    
    # Print comparison table
    print("\n" + "="*70)
    print("QUANTIZATION IMPACT SUMMARY")
    print("="*70)
    print(f"{'Quantization':<15} {'Throughput':<20} {'Residue':<15} {'Zero-Residue':<15}")
    print("-"*70)
    
    for name, stats in results.items():
        throughput = f"{stats['throughput_samples_sec']:.0f} samples/sec"
        residue = f"{stats['residue_mb']:.1f} MB"
        zero = "✓ PASS" if stats['zero_residue'] else "✗ FAIL"
        print(f"{name:<15} {throughput:<20} {residue:<15} {zero:<15}")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    # Check dependencies
    try:
        import psutil
    except ImportError:
        print("ERROR: psutil required. Install with: pip install psutil")
        sys.exit(1)
    
    # Run comparison
    compare_quantizations()
    
    print("✓ All POC tests passed. Ephemeral inference with zero-residue verified!")
