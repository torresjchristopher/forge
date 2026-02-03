# Forge Quick Reference Guide

## Installation

```bash
git clone https://github.com/torresjchristopher/forge.git
cd forge
pip install -e .
```

## Quick Start

### 1. Launch Dashboard

```bash
forge tui
```

### 2. Run a Container

```bash
forge container run python-image:latest python script.py
```

### 3. Define a Workflow

Create `forge.yml`:

```yaml
workflows:
  my_etl:
    schedule: "0 2 * * *"  # Daily at 2 AM
    tasks:
      - name: extract
        image: etl:latest
        command: python extract.py
      - name: transform
        image: etl:latest
        command: python transform.py
        depends_on: [extract]
      - name: load
        image: etl:latest
        command: python load.py
        depends_on: [transform]
```

### 4. Schedule Workflow

```bash
forge scheduler schedule my_etl --cron "0 2 * * *"
forge scheduler start
```

## Command Reference

### Container Commands

```bash
# Run container
forge container run IMAGE COMMAND [OPTIONS]
  -m, --memory INT      Memory limit (MB)
  -p, --port PORT:PORT  Port mapping
  -v, --volume PATH:PATH Volume mount
  --timeout INT         Timeout (seconds)

# List containers
forge container ps

# View logs
forge container logs CONTAINER_ID

# Stop/remove container
forge container stop CONTAINER_ID
forge container rm CONTAINER_ID
```

### Image Commands

```bash
# Load image
forge image load PATH/TO/IMAGE.tar

# List images
forge image ls

# Remove image
forge image rm IMAGE_ID

# Get image info
forge image inspect IMAGE_ID
```

### Workflow Commands

```bash
# Run workflow immediately
forge workflow run WORKFLOW_ID

# List workflows
forge workflow list

# View execution history
forge workflow history WORKFLOW_ID
```

### Scheduler Commands

```bash
# Schedule workflow
forge scheduler schedule WORKFLOW_ID --cron "CRON_EXPR"

# Pause/resume
forge scheduler pause WORKFLOW_ID
forge scheduler resume WORKFLOW_ID

# Manual trigger
forge scheduler trigger WORKFLOW_ID

# View status
forge scheduler status

# Backfill dates
forge scheduler backfill WORKFLOW_ID --start 2024-01-01 --end 2024-01-31

# Daemon control
forge scheduler start
forge scheduler stop
```

### System Commands

```bash
# Prune unused data
forge system prune

# Show usage
forge system usage

# Launch TUI
forge tui
```

## Dashboard Navigation

| Key | Action |
|-----|--------|
| `1` | Overview |
| `2` | Workflows |
| `3` | Containers |
| `4` | Scheduler |
| `5` | Logs |
| `q` | Quit |
| `r` | Refresh |

## Cron Expression Examples

```
"0 2 * * *"     # Daily at 2 AM
"0 * * * *"     # Every hour
"*/15 * * * *"  # Every 15 minutes
"0 0 * * 0"     # Weekly Sunday midnight
"0 0 1 * *"     # Monthly 1st at midnight
```

## Configuration Files

```
~/.forge/
├── containers/              # Container state
├── execution_history/       # Workflow executions (500 max)
├── workflows/               # Workflow definitions
├── logs/                    # Task logs
├── scheduler_state.json     # Scheduled workflows
├── execution_queue.json     # Pending executions
└── scheduled_executions.json # Execution history
```

## Performance Targets

| Operation | Target |
|-----------|--------|
| Container startup | <500ms |
| Image extraction | <1s |
| Dashboard refresh | <50ms |
| Workflow trigger | <50ms |
| Container cleanup | <10ms |

## Troubleshooting

### Dashboard won't start

```bash
# Check Rich installation
python -c "import rich; print('OK')"

# Try explicit terminal
TERM=xterm-256color forge tui
```

### Container won't run

```bash
# Check image exists
forge image ls

# Check logs
forge container logs CONTAINER_ID

# Check resource limits
forge system usage
```

### Scheduler not executing

```bash
# Check daemon status
forge scheduler status

# Start daemon
forge scheduler start

# Check scheduled workflows
cat ~/.forge/scheduler_state.json
```

## Architecture Overview

```
Forge = Container Runtime + Orchestration + Scheduler + TUI

┌─────────────────────────────────────────────┐
│         Forge CLI (Click)                   │
├─────────────────────────────────────────────┤
│  Container  │  Workflow  │  Scheduler  │ TUI │
│  Runtime    │ Executor   │ Daemon      │     │
├─────────────────────────────────────────────┤
│        File-Based State (~/.forge/)         │
├─────────────────────────────────────────────┤
│  Linux Namespaces | Windows Job Objects     │
└─────────────────────────────────────────────┘
```

## What Makes Forge Different?

| Feature | Docker | Podman | Forge |
|---------|--------|--------|-------|
| **Daemon required** | Yes | No | No |
| **Memory per container** | ~50MB | ~30MB | ~10MB |
| **Startup time** | 1-2s | 0.5-1s | <500ms |
| **Built-in scheduling** | No | No | Yes (APScheduler) |
| **Built-in workflow** | No | No | Yes (DAG engine) |
| **Unified TUI** | No | No | Yes |
| **Auto-pruning** | Manual | Manual | Automatic |
| **State format** | Graph DB | Containers db | JSON files |

## Quick Examples

### Example 1: Run Python Script

```bash
forge container run python:3.11 python -c "print('Hello Forge')"
```

### Example 2: Mount Volume

```bash
forge container run python:3.11 python script.py \
  -v /host/data:/container/data
```

### Example 3: Map Port

```bash
forge container run nginx:latest \
  -p 8080:80
```

### Example 4: Set Resource Limits

```bash
forge container run heavy-workload:latest script.py \
  -m 512 \
  --cpu 50 \
  --timeout 3600
```

### Example 5: Run Workflow

```bash
# Create workflow config
cat > forge.yml << 'EOF'
workflows:
  test:
    tasks:
      - name: task1
        image: python:3.11
        command: echo "Task 1"
      - name: task2
        image: python:3.11
        command: echo "Task 2"
        depends_on: [task1]
EOF

# Execute
forge workflow run test
```

### Example 6: Schedule Daily Task

```bash
# Schedule
forge scheduler schedule daily_backup --cron "0 3 * * *"

# Start daemon
forge scheduler start

# Verify
forge scheduler status
```

## Getting Help

```bash
# General help
forge --help

# Command help
forge container --help
forge workflow --help
forge scheduler --help

# TUI built-in help
forge tui          # Press 'h' for help in dashboard
```

## Resources

- **Documentation**: See docs/ directory
- **Examples**: See examples/forge.yml
- **Architecture**: See IMPLEMENTATION.md
- **Scheduler Guide**: See SCHEDULER.md
- **TUI Guide**: See TUI.md
- **GitHub**: https://github.com/torresjchristopher/forge

---

**Forge v0.1.0** - Lightning-fast container orchestration + embedded workflows
