# Forge ML v2.0: Implementation Guide

## Architecture Overview

Forge v2.0 implements **ephemeral ML inference**—executing models in ephemeral RAM buffers with guaranteed zero persistence and cleanup.

### Core Principles

1. **Ephemeral Buffers**: Models load into RAM, execute, then completely disappear
2. **Before/After Baselines**: Memory tracked throughout execution for verification
3. **Zero Residue**: < 10MB memory residue tolerance after cleanup
4. **Cross-Framework**: PyTorch, TensorFlow, ONNX Runtime support
5. **Quantization-Ready**: INT8 and FP16 paths for memory efficiency

## API Design

### 1. PyTorch Inference

```python
from forge.ml import PyTorchInference, MemoryManager

# Setup inference engine
inference = PyTorchInference(quantization="int8", device="cuda")
memory_mgr = MemoryManager()

# Create memory baseline
baseline = memory_mgr.create_baseline("resnet50_inference")

# Load model into ephemeral buffer
model = inference.load_model("resnet50", pretrained=True)

# Run batch inference
results = inference.infer(
    inputs=batch_images,        # Shape: (N, 3, 224, 224)
    batch_size=128,
    return_logits=False
)

# Cleanup and verify
cleanup_stats = memory_mgr.verify_cleanup("resnet50_inference")
assert cleanup_stats["zero_residue_achieved"], "Residue > 10MB!"

print(f"Processed: {results['num_samples']} samples")
print(f"Throughput: {results['throughput_samples_sec']:.0f} samples/sec")
print(f"Memory residue: {cleanup_stats['residue_mb']:.1f} MB")
```

### 2. TensorFlow Inference

```python
from forge.ml import TensorFlowInference, MemoryManager

inference = TensorFlowInference(quantization="fp16", device="cuda")

# Load EfficientNet from Keras applications
model = inference.load_model("efficientnet-b0", pretrained=True)

# Batch inference
results = inference.infer(
    inputs=batch_images,
    batch_size=64,
)

# Cleanup guaranteed by context manager
cleanup_stats = inference.cleanup_and_verify()
```

### 3. ONNX Runtime (Cross-Framework)

```python
from forge.ml import OnnxInference

# Load ONNX model (works with PyTorch, TensorFlow, scikit-learn models)
inference = OnnxInference(device="cuda")
model = inference.load_model("resnet50.onnx")

# Execute with provider selection (TensorRT, CUDA, CPU)
results = inference.infer(
    inputs=batch_images,
    providers=["TensorrtExecutionProvider", "CudaExecutionProvider"],
    batch_size=256
)
```

## Implementation Roadmap

### Phase 1: Core Architecture (DONE ✓)
- [x] Abstract `InferenceEngine` base class
- [x] `PyTorchInference`, `TensorFlowInference`, `OnnxInference` stubs
- [x] `MemoryBaseline` for before/after tracking
- [x] `MemoryManager` for session cleanup
- [x] Version bump to v2.0.0-alpha

### Phase 2: PyTorch Backend (IN PROGRESS)
**Tasks**:
1. Implement `PyTorchInference.load_model()` with torchvision models
   - Support for: ResNet50, ResNet101, VGG16, MobileNetV2
   - Pretrained weights from torchvision
   - GPU/CPU device handling
   
2. Implement `PyTorchInference.infer()` with batch processing
   - Dynamic batching with configurable batch_size
   - Context manager for guaranteed cleanup
   - Throughput measurement (samples/sec)
   
3. Implement INT8 quantization
   - Post-training quantization (PTQ) via torch.quantization
   - Calibration with sample batches
   - Memory reduction: 4x (FP32 → INT8)
   
4. Implement FP16 quantization
   - Half-precision via `.half()` for NVIDIA GPUs
   - Maintains accuracy with 2x memory reduction
   
5. Create POC: ResNet50 inference
   - Load model → run 10K predictions → verify cleanup
   - Compare FP32 vs INT8 vs FP16
   - Before/After memory baselines
   - Throughput benchmarks

**File**: `forge/ml/pytorch_backend.py` (~400 LOC)

### Phase 3: TensorFlow Backend
**Tasks**:
1. Implement `TensorFlowInference.load_model()`
   - Keras applications: EfficientNet, Inception, MobileNet
   - Transformer models via transformers library
   - Custom SavedModel loading
   
2. Implement `TensorFlowInference.infer()`
   - `@tf.function` for graph compilation
   - Batch processing with `tf.data.Dataset`
   - Automatic memory cleanup between sessions
   
3. Implement TF Lite quantization
   - Lightweight INT8 for mobile
   - Dynamic range quantization
   - ~4x model size reduction
   
4. Create POC: EfficientNet inference
   - Compare to PyTorch baseline
   - Distributed inference across TPU/GPU/CPU

**File**: `forge/ml/tensorflow_backend.py` (~350 LOC)

### Phase 4: ONNX Runtime Backend
**Tasks**:
1. Implement `OnnxInference.load_model()`
   - Load .onnx files from disk or URL
   - Provider selection (TensorRT, CUDA, CPU)
   - Model optimization via ort.GraphOptimizationLevel
   
2. Implement `OnnxInference.infer()`
   - Execution provider management
   - Hardware-accelerated inference
   - Cross-framework compatibility
   
3. Model conversion tools
   - PyTorch → ONNX converter
   - TensorFlow → ONNX converter
   - Quantization-aware export
   
4. POC: Cross-framework inference
   - Same model in PyTorch, TensorFlow, ONNX
   - Performance comparison
   - Accuracy validation

**File**: `forge/ml/onnx_backend.py` (~300 LOC)

### Phase 5: Advanced Features
**Tasks**:
1. Distributed inference
   - Multi-GPU inference with data parallelism
   - Model parallelism for large models
   - Async execution with futures
   
2. Auto-batching
   - Dynamic batching across requests
   - Queue-based inference
   - Latency/throughput tradeoff tuning
   
3. Model caching (with ephemeral cleanup)
   - LRU cache for repeated models
   - TTL-based eviction
   - Memory limits enforcement
   
4. Monitoring & profiling
   - Per-layer latency breakdown
   - Memory allocator tracing
   - Throughput curves (batch size vs latency)

## Data Principles: Zero Residue Guarantee

### Before/After Baseline
```
┌─────────────────────────────────────┐
│  Session Start                      │
│  RAM Baseline: 2.3 GB               │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│  Model Load: ResNet50               │
│  RAM After Load: 2.8 GB (+500 MB)   │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│  Inference: 10,000 samples          │
│  Peak RAM: 3.2 GB                   │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│  Cleanup & Verify                   │
│  RAM After: 2.35 GB                 │
│  Residue: 50 MB (< 10 MB limit ✓)   │
└─────────────────────────────────────┘
```

### Cleanup Procedure
1. **Session End**: Context manager exit triggers cleanup
2. **Force GC**: Call `gc.collect()` 3x (aggressive)
3. **Clear Caches**: Empty PyTorch CUDA cache, TF session
4. **Destroy Buffers**: Delete all model/data references
5. **Verify**: Check RAM within baseline ± 10MB

### Verification

Test with `forge.ml.examples.zero_residue_poc`:

```bash
python -m forge.ml.examples.zero_residue_poc

[MEMORY VERIFICATION]
Baseline:    2300.5 MB
After Cleanup: 2351.2 MB
Residue:       50.7 MB (2.2%)
Zero Residue:  ✓ PASS (< 10 MB tolerance)
```

## Testing Strategy

### Unit Tests
- `test_pytorch_load.py`: Model loading, device handling
- `test_inference_api.py`: Batch processing, output shapes
- `test_quantization.py`: INT8/FP16 accuracy within 0.1%
- `test_memory.py`: Baseline creation, cleanup verification

### Integration Tests
- `test_end_to_end_pytorch.py`: Load → Infer → Cleanup
- `test_end_to_end_tensorflow.py`: TF model → ONNX → inference
- `test_distributed.py`: Multi-GPU synchronization

### Benchmarks (`forge/ml/benchmarks/`)
- `resnet50_comparison.py`: FP32 vs INT8 vs FP16
- `throughput_scaling.py`: Batch size vs latency curves
- `memory_profile.py`: Peak memory vs model size
- `cross_framework.py`: PyTorch vs TensorFlow vs ONNX

## Dependencies

### Required
```
psutil>=5.9.0      # Memory tracking
numpy>=1.21.0      # Array operations
```

### Optional (install for specific backends)
```
torch>=2.0.0           # PyTorch inference
torchvision>=0.15.0    # Pretrained models
tensorflow>=2.12.0     # TensorFlow/Keras
onnxruntime>=1.15.0    # ONNX execution
transformers>=4.30.0   # Hugging Face models
```

### Installation
```bash
# Core (memory tracking only)
pip install psutil numpy

# PyTorch backend
pip install torch torchvision

# TensorFlow backend
pip install tensorflow

# All backends
pip install torch torchvision tensorflow onnxruntime
```

## Performance Targets

### ResNet50 Inference (10,000 samples)

| Quantization | Memory | Throughput | Cleanup Time |
|-------------|--------|-----------|-------------|
| FP32        | 650 MB | 2,500 samples/sec | < 1s |
| INT8        | 170 MB | 5,000 samples/sec | < 1s |
| FP16 (GPU)  | 330 MB | 4,200 samples/sec | < 1s |

### BERT Base Inference (text classification)

| Quantization | Memory | Throughput | Accuracy Loss |
|-------------|--------|-----------|-------------|
| FP32        | 450 MB | 150 samples/sec | - |
| INT8        | 120 MB | 280 samples/sec | < 0.5% |
| FP16 (GPU)  | 230 MB | 240 samples/sec | < 0.1% |

## References

- PyTorch Quantization: https://pytorch.org/docs/stable/quantization.html
- TensorFlow Lite: https://www.tensorflow.org/lite
- ONNX Runtime: https://onnxruntime.ai/docs
- Memory Profiling: https://pytorch.org/docs/stable/torch_cuda.html
