# Forge Engine Changelog

## [1.0.0] - 2026-02-19 (Stable Release)

### What is Forge 1.0?
Forge Engine is the execution component of the Ethereal Compute Platform. It runs tasks in isolated memory buffers with zero infrastructure footprint.

### Features
- **Task Execution**: Run workflows in ephemeral memory buffers
- **Container Runtime**: Lightweight alternative to Docker
- **Workflow Orchestration**: DAG-based scheduling (Airflow alternative)
- **CLI Interface**: Simple command-line control
- **Zero Persistence**: All data cleaned up post-execution

### Dependencies
- Python 3.11+
- Click, PyYAML, APScheduler, Pydantic, Rich

### Known Limitations
- Single-machine execution (no distributed compute yet)
- No ML inference capabilities (coming in v2.0)
- No federated learning support (Pidgeon v2.0 integration needed)

### Next Release
**Forge v2.0.0** (Q1 2026) will add:
- PyTorch/TensorFlow model inference
- Auto-quantization for lightweight models
- Distributed inference support via Pidgeon v2.0
- MLflow integration for experiment tracking

### Installation
```bash
pip install forge-runtime
forge --help
```

### Getting Started
See README.md for examples and documentation.
