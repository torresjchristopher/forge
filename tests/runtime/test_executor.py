"""Tests for container executor."""

import pytest
from pathlib import Path
from forge.runtime.executor import ContainerExecutor, ContainerConfig


@pytest.fixture
def executor():
    return ContainerExecutor()


def test_container_creation(executor):
    """Test creating a container."""
    config = ContainerConfig(
        image="test:latest",
        command=["echo", "hello"],
    )
    container = executor.create_container(config)
    assert container.container_id
    assert container.config == config
    assert container.status == "created"


def test_list_containers(executor):
    """Test listing containers."""
    config1 = ContainerConfig(image="test:latest", command=["echo", "1"])
    config2 = ContainerConfig(image="test:latest", command=["echo", "2"])
    
    executor.create_container(config1)
    executor.create_container(config2)
    
    containers = executor.list_containers()
    assert len(containers) == 2


def test_get_container(executor):
    """Test retrieving a container."""
    config = ContainerConfig(image="test:latest", command=["echo", "hello"])
    container = executor.create_container(config)
    
    retrieved = executor.get_container(container.container_id)
    assert retrieved == container


def test_container_cleanup(executor):
    """Test container cleanup."""
    config = ContainerConfig(image="test:latest", command=["echo", "hello"])
    container = executor.create_container(config)
    
    container.cleanup()
    assert container.status == "cleaned"
