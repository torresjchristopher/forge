"""Tests for orchestration engine."""

import pytest
from pathlib import Path
from forge.orchestration.engine import OrchestrationEngine, Workflow, Task, Service


@pytest.fixture
def engine():
    return OrchestrationEngine()


def test_create_service(engine):
    """Test creating a service."""
    service = Service(
        name="postgres",
        image="postgres:15",
        ports=[5432],
    )
    engine.services["postgres"] = service
    
    assert engine.get_service("postgres") == service


def test_create_workflow(engine):
    """Test creating a workflow."""
    workflow = Workflow(
        name="etl_pipeline",
        schedule="0 2 * * *",
    )
    engine.workflows["etl_pipeline"] = workflow
    
    assert engine.get_workflow("etl_pipeline") == workflow


def test_add_task_to_workflow(engine):
    """Test adding tasks to a workflow."""
    workflow = Workflow(name="test", schedule="0 * * * *")
    
    task = Task(
        name="extract",
        image="python:latest",
        command="python extract.py",
    )
    workflow.tasks["extract"] = task
    
    assert "extract" in workflow.tasks


def test_record_execution(engine):
    """Test recording workflow execution."""
    execution_data = {
        "run_id": "test-run-1",
        "status": "SUCCESS",
        "duration": 120,
        "tasks_completed": 3,
        "tasks_failed": 0,
    }
    
    engine.record_execution("test_workflow", execution_data)
    assert len(engine.execution_history) == 1
