"""Tests for workflow scheduler."""

import pytest
from forge.scheduler.scheduler import WorkflowScheduler


@pytest.fixture
def scheduler():
    return WorkflowScheduler()


def test_scheduler_creation(scheduler):
    """Test scheduler initialization."""
    assert scheduler.scheduler is not None
    assert len(scheduler.jobs) == 0


def test_add_workflow(scheduler):
    """Test adding a workflow to scheduler."""
    def dummy_callback():
        pass
    
    scheduler.add_workflow(
        "test_workflow",
        "0 * * * *",  # Every hour
        dummy_callback,
    )
    
    assert "test_workflow" in scheduler.jobs


def test_list_jobs(scheduler):
    """Test listing scheduled jobs."""
    def dummy_callback():
        pass
    
    scheduler.add_workflow("workflow1", "0 * * * *", dummy_callback)
    scheduler.add_workflow("workflow2", "0 0 * * *", dummy_callback)
    
    jobs = scheduler.list_jobs()
    assert len(jobs) == 2


def test_remove_workflow(scheduler):
    """Test removing a workflow."""
    def dummy_callback():
        pass
    
    scheduler.add_workflow("test_workflow", "0 * * * *", dummy_callback)
    assert "test_workflow" in scheduler.jobs
    
    scheduler.remove_workflow("test_workflow")
    assert "test_workflow" not in scheduler.jobs
