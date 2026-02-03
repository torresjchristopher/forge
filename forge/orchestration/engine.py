"""Orchestration engine for managing services and workflows."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json


@dataclass
class Task:
    """Represents a task in a workflow."""
    name: str
    image: str
    command: str
    depends_on: List[str] = field(default_factory=list)
    timeout: Optional[int] = None
    retries: int = 0
    retry_delay: int = 300
    on_failure: Optional[str] = None
    sla: Optional[int] = None
    status: str = "pending"


@dataclass
class Workflow:
    """Represents a workflow (DAG)."""
    name: str
    schedule: str
    tasks: Dict[str, Task] = field(default_factory=dict)
    description: Optional[str] = None
    enabled: bool = True


@dataclass
class Service:
    """Represents a long-running service."""
    name: str
    image: str
    ports: List[int] = field(default_factory=list)
    volumes: Dict[str, str] = field(default_factory=dict)
    env: Dict[str, str] = field(default_factory=dict)
    restart_policy: str = "always"
    status: str = "stopped"


class OrchestrationEngine:
    """Main orchestration engine for services and workflows."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.cwd() / "forge.yml"
        self.services: Dict[str, Service] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.execution_history: List[Dict] = []
    
    def load_config(self):
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        import yaml
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
        
        # Load services
        for svc_name, svc_config in config.get("services", {}).items():
            service = Service(
                name=svc_name,
                image=svc_config["image"],
                ports=svc_config.get("ports", []),
                volumes=svc_config.get("volumes", {}),
                env=svc_config.get("env", {}),
                restart_policy=svc_config.get("restart_policy", "always"),
            )
            self.services[svc_name] = service
        
        # Load workflows
        for wf_name, wf_config in config.get("workflows", {}).items():
            workflow = Workflow(
                name=wf_name,
                schedule=wf_config["schedule"],
                description=wf_config.get("description"),
                enabled=wf_config.get("enabled", True),
            )
            
            for task_config in wf_config.get("tasks", []):
                task = Task(
                    name=task_config["name"],
                    image=task_config["image"],
                    command=task_config["command"],
                    depends_on=task_config.get("depends_on", []),
                    timeout=task_config.get("timeout"),
                    retries=task_config.get("retries", 0),
                    retry_delay=task_config.get("retry_delay", 300),
                    on_failure=task_config.get("on_failure"),
                    sla=task_config.get("sla"),
                )
                workflow.tasks[task.name] = task
            
            self.workflows[wf_name] = workflow
    
    def get_workflow(self, name: str) -> Optional[Workflow]:
        """Get a workflow by name."""
        return self.workflows.get(name)
    
    def get_service(self, name: str) -> Optional[Service]:
        """Get a service by name."""
        return self.services.get(name)
    
    def list_workflows(self) -> List[Workflow]:
        """List all workflows."""
        return list(self.workflows.values())
    
    def list_services(self) -> List[Service]:
        """List all services."""
        return list(self.services.values())
    
    def record_execution(self, workflow_name: str, execution_data: Dict):
        """Record a workflow execution."""
        self.execution_history.append({
            "workflow": workflow_name,
            "data": execution_data,
        })
