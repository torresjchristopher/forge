"""
POC: Ephemeral ResNet50 Inference
=================================

Demonstrates Forge v2.0 ephemeral compute with before/after memory verification.
Run this to see:
1. Model loading into ephemeral RAM
2. Batch inference (10K samples)
3. Complete memory cleanup
4. Zero-residue verification

Usage:
    cd C:\Users\serro\Yukora\forge
    python forge/ml/examples/ephemeral_resnet50.py
"""

import sys
from pathlib import Path

# Add forge to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from forge.ml.pytorch_backend import PyTorchInference, benchmark_model, create_synthetic_image_batch


def run_single_benchmark():
    """Run single benchmark with detailed output."""
    print("\n" + "█" * 70)
    print("FORGE ML v2.0: EPHEMERAL INFERENCE POC")
    print("█" * 70)
    
    results = benchmark_model(
        model_name="resnet50",
        num_samples=5000,  # 5K for speed
        batch_size=128,
        quantization=None,  # FP32
        device="cpu"
    )
    
    return results


def run_quantization_comparison():
    """Run benchmarks comparing FP32, INT8, FP16."""
    print("\n" + "█" * 70)
    print("FORGE ML v2.0: QUANTIZATION COMPARISON")
    print("█" * 70)
    
    results = {}
    
    # FP32 Baseline
    print("\n[BENCHMARK 1/3] FP32 Baseline")
    results["fp32"] = benchmark_model(
        model_name="resnet50",
        num_samples=3000,
        batch_size=128,
        quantization=None,
        device="cpu"
    )
    
    # INT8
    print("\n[BENCHMARK 2/3] INT8 Quantized")
    results["int8"] = benchmark_model(
        model_name="resnet50",
        num_samples=3000,
        batch_size=128,
        quantization="int8",
        device="cpu"
    )
    
    # Print comparison
    print("\n" + "=" * 70)
    print("QUANTIZATION COMPARISON SUMMARY")
    print("=" * 70)
    
    if results["fp32"] and results["int8"]:
        print(f"\n{'Metric':<20} {'FP32':<20} {'INT8':<20} {'Improvement'}")
        print("-" * 70)
        
        # Throughput comparison
        fp32_tp = results["fp32"]["throughput"]
        int8_tp = results["int8"]["throughput"]
        improvement = (int8_tp / fp32_tp - 1) * 100 if fp32_tp > 0 else 0
        print(f"{'Throughput':<20} {fp32_tp:>10.0f} s/s   {int8_tp:>10.0f} s/s   {improvement:>+6.1f}%")
        
        # Memory residue comparison
        fp32_res = results["fp32"]["residue_mb"]
        int8_res = results["int8"]["residue_mb"]
        reduction = (fp32_res - int8_res) / fp32_res * 100 if fp32_res > 0 else 0
        print(f"{'Memory Residue':<20} {fp32_res:>10.1f} MB    {int8_res:>10.1f} MB    {reduction:>+6.1f}%")
        
        # Zero-residue status
        fp32_pass = "✓ PASS" if results["fp32"]["zero_residue"] else "✗ FAIL"
        int8_pass = "✓ PASS" if results["int8"]["zero_residue"] else "✗ FAIL"
        print(f"{'Zero-Residue':<20} {fp32_pass:<20} {int8_pass}")
        
        print("\n" + "=" * 70)
        if results["fp32"]["zero_residue"] and results["int8"]["zero_residue"]:
            print("✓ ALL TESTS PASSED - Ephemeral inference verified")
        else:
            print("✗ SOME TESTS FAILED - Memory residue exceeded tolerance")
        print("=" * 70 + "\n")


def run_throughput_benchmark():
    """Benchmark throughput at different batch sizes."""
    print("\n" + "█" * 70)
    print("FORGE ML v2.0: THROUGHPUT SCALING")
    print("█" * 70)
    
    batch_sizes = [32, 64, 128, 256]
    results = {}
    
    for i, batch_size in enumerate(batch_sizes, 1):
        print(f"\n[BATCH SIZE {i}/{len(batch_sizes)}] batch_size={batch_size}")
        result = benchmark_model(
            model_name="resnet50",
            num_samples=2000,
            batch_size=batch_size,
            quantization=None,
            device="cpu"
        )
        if result:
            results[batch_size] = result["throughput"]
    
    # Print scaling table
    print("\n" + "=" * 70)
    print("THROUGHPUT SCALING TABLE")
    print("=" * 70)
    print(f"{'Batch Size':<15} {'Throughput (samples/sec)':<30} {'Relative to B=32'}")
    print("-" * 70)
    
    if 32 in results:
        baseline = results[32]
        for batch_size in batch_sizes:
            if batch_size in results:
                tp = results[batch_size]
                relative = tp / baseline if baseline > 0 else 1.0
                print(f"{batch_size:<15} {tp:>15.0f} samples/sec       {relative:>+6.1f}x")
    
    print("=" * 70 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Forge ML v2.0 Ephemeral Inference POC")
    parser.add_argument(
        "--mode",
        choices=["single", "quantization", "throughput", "all"],
        default="single",
        help="Benchmark mode"
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=5000,
        help="Number of samples for single benchmark"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "single" or args.mode == "all":
            run_single_benchmark()
        
        if args.mode == "quantization" or args.mode == "all":
            run_quantization_comparison()
        
        if args.mode == "throughput" or args.mode == "all":
            run_throughput_benchmark()
        
        print("\n✓ POC execution complete!")
    
    except Exception as e:
        print(f"\n✗ POC failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
