"""
Orchestrator Module
===================
Generates TASKS.json from high-level goals for the Ralph Wiggum Loop.

Responsibilities:
- Parse user goals into actionable tasks
- Detect task dependencies
- Generate structured TASKS.json output
- Integrate with CONTEXT.json for project constraints
"""

import json
import os
import re
from typing import Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Task:
    """Represents a single task in the plan."""
    id: str
    action: str
    outcome: str
    tags: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    field_requirements: dict = field(default_factory=dict)
    verification: Optional[dict] = None
    context_scope: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "action": self.action,
            "outcome": self.outcome,
            "tags": self.tags,
        }
        if self.depends_on:
            result["depends_on"] = self.depends_on
        if self.field_requirements:
            result["field_requirements"] = self.field_requirements
        if self.verification:
            result["verification"] = self.verification
        if self.context_scope:
            result["context_scope"] = self.context_scope
        return result


# Common task templates by category
TASK_TEMPLATES = {
    "spec": [
        Task(
            id="TASK-SPEC-001",
            action="Define project context and constraints",
            outcome="CONTEXT.json with models, architecture, and testing strategy",
            tags=["planning", "spec"],
        ),
        Task(
            id="TASK-SPEC-002", 
            action="Create task breakdown",
            outcome="TASKS.json with actionable items and dependencies",
            tags=["planning", "spec"],
            depends_on=["TASK-SPEC-001"],
        ),
    ],
    "backend": [
        Task(
            id="TASK-BACK-001",
            action="Define database models",
            outcome="SQLModel/Pydantic classes matching CONTEXT.json spec",
            tags=["backend", "database"],
        ),
        Task(
            id="TASK-BACK-002",
            action="Implement API endpoints",
            outcome="FastAPI routes for CRUD operations",
            tags=["backend", "api"],
            depends_on=["TASK-BACK-001"],
        ),
        Task(
            id="TASK-BACK-003",
            action="Write backend tests",
            outcome="pytest tests with >80% coverage",
            tags=["backend", "testing"],
            depends_on=["TASK-BACK-002"],
        ),
    ],
    "frontend": [
        Task(
            id="TASK-FRONT-001",
            action="Create UI component library",
            outcome="Reusable components following design tokens",
            tags=["frontend", "ui", "component"],
        ),
        Task(
            id="TASK-FRONT-002",
            action="Implement main views/pages",
            outcome="Page components with routing",
            tags=["frontend", "ui"],
            depends_on=["TASK-FRONT-001"],
        ),
        Task(
            id="TASK-FRONT-003",
            action="Connect frontend to API",
            outcome="API integration with state management",
            tags=["frontend", "integration"],
            depends_on=["TASK-FRONT-002"],
        ),
        Task(
            id="TASK-FRONT-004",
            action="Write frontend tests",
            outcome="Component and integration tests",
            tags=["frontend", "testing"],
            depends_on=["TASK-FRONT-003"],
        ),
    ],
    "fullstack": [
        Task(
            id="TASK-INT-001",
            action="End-to-end integration testing",
            outcome="E2E tests covering critical user flows",
            tags=["testing", "e2e"],
        ),
        Task(
            id="TASK-DEPLOY-001",
            action="Configure deployment",
            outcome="Deployment scripts and documentation",
            tags=["devops", "deployment"],
        ),
    ],
}


class Orchestrator:
    """
    Generates TASKS.json from high-level goals.
    
    Usage:
        orch = Orchestrator()
        tasks = orch.generate_tasks("Build a todo app with React frontend and FastAPI backend")
        orch.save_tasks(tasks, ".agent/TASKS.json")
    """
    
    def __init__(self, context_path: str = ".agent/CONTEXT.json"):
        """
        Initialize orchestrator.
        
        Args:
            context_path: Path to CONTEXT.json for project constraints
        """
        self.context_path = context_path
        self.context: Optional[dict] = None
        self._load_context()
    
    def generate_tasks(self, goal: str) -> list[Task]:
        """
        Generate task list from a high-level goal.
        
        Args:
            goal: Natural language description of the project goal
            
        Returns:
            List of Task objects
        """
        print(f"[ORCH] 🎯 Parsing goal: {goal[:50]}...")
        
        # Detect project type from goal keywords
        goal_lower = goal.lower()
        tasks: list[Task] = []
        task_counter = 0
        
        # Always start with spec tasks
        for template in TASK_TEMPLATES["spec"]:
            task_counter += 1
            tasks.append(self._customize_task(template, task_counter, goal))
        
        # Detect backend keywords
        backend_keywords = ["backend", "api", "fastapi", "flask", "django", "database", "server", "rest"]
        if any(kw in goal_lower for kw in backend_keywords):
            print("[ORCH] 📦 Detected: Backend component")
            for template in TASK_TEMPLATES["backend"]:
                task_counter += 1
                tasks.append(self._customize_task(template, task_counter, goal))
        
        # Detect frontend keywords  
        frontend_keywords = ["frontend", "ui", "react", "vue", "angular", "nextjs", "vite", "web app", "dashboard"]
        if any(kw in goal_lower for kw in frontend_keywords):
            print("[ORCH] 🎨 Detected: Frontend component")
            for template in TASK_TEMPLATES["frontend"]:
                task_counter += 1
                tasks.append(self._customize_task(template, task_counter, goal))
        
        # Detect fullstack patterns
        if any(kw in goal_lower for kw in backend_keywords) and any(kw in goal_lower for kw in frontend_keywords):
            print("[ORCH] 🔗 Detected: Fullstack integration")
            for template in TASK_TEMPLATES["fullstack"]:
                task_counter += 1
                tasks.append(self._customize_task(template, task_counter, goal))
        
        # If no specific patterns detected, add generic tasks
        if len(tasks) == 2:  # Only spec tasks
            print("[ORCH] 📝 No specific patterns detected, adding generic tasks")
            tasks.append(Task(
                id=f"TASK-{task_counter + 1:03d}",
                action="Analyze requirements and create implementation",
                outcome=f"Working implementation for: {goal[:100]}",
                tags=["implementation"],
            ))
            tasks.append(Task(
                id=f"TASK-{task_counter + 2:03d}",
                action="Write tests and documentation",
                outcome="Tests and README documentation",
                tags=["testing", "documentation"],
            ))
        
        # Inject field requirements from CONTEXT.json
        tasks = self._inject_field_requirements(tasks)
        
        # Resolve dependencies
        tasks = self.detect_dependencies(tasks)
        
        print(f"[ORCH] ✅ Generated {len(tasks)} tasks")
        return tasks
    
    def detect_dependencies(self, tasks: list[Task]) -> list[Task]:
        """
        Analyze and set task dependencies based on tags and order.
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            Tasks with updated depends_on fields
        """
        # Build tag index
        tag_to_tasks: dict[str, list[str]] = {}
        for task in tasks:
            for tag in task.tags:
                if tag not in tag_to_tasks:
                    tag_to_tasks[tag] = []
                tag_to_tasks[tag].append(task.id)
        
        # Common dependency rules
        dependency_rules = [
            # Testing depends on implementation
            (["testing"], ["backend", "frontend", "implementation"]),
            # Integration depends on both backend and frontend
            (["integration", "e2e"], ["backend", "api"]),
            # Deployment depends on testing
            (["deployment", "devops"], ["testing"]),
        ]
        
        for task in tasks:
            for dependent_tags, provider_tags in dependency_rules:
                if any(tag in task.tags for tag in dependent_tags):
                    for provider_tag in provider_tags:
                        if provider_tag in tag_to_tasks:
                            for provider_id in tag_to_tasks[provider_tag]:
                                if provider_id != task.id and provider_id not in task.depends_on:
                                    # Only add if provider comes before this task
                                    provider_idx = next((i for i, t in enumerate(tasks) if t.id == provider_id), -1)
                                    task_idx = next((i for i, t in enumerate(tasks) if t.id == task.id), -1)
                                    if provider_idx < task_idx:
                                        task.depends_on.append(provider_id)
        
        return tasks
    
    def save_tasks(self, tasks: list[Task], output_path: str = ".agent/TASKS.json") -> bool:
        """
        Save tasks to TASKS.json file.
        
        Args:
            tasks: List of Task objects
            output_path: Output file path
            
        Returns:
            True if successful
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Convert to JSON-serializable format
            tasks_data = [task.to_dict() for task in tasks]
            
            with open(output_path, 'w') as f:
                json.dump(tasks_data, f, indent=2)
            
            print(f"[ORCH] 💾 Saved {len(tasks)} tasks to {output_path}")
            return True
        except Exception as e:
            print(f"[ORCH] ❌ Failed to save tasks: {e}")
            return False
    
    def generate_task_md(self, tasks: list[Task], output_path: str = ".agent/task.md") -> bool:
        """
        Generate task.md file for status tracking.
        
        Args:
            tasks: List of Task objects
            output_path: Output file path
            
        Returns:
            True if successful
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            lines = [
                "# Task List",
                "",
                f"> Generated: {datetime.now().isoformat()}",
                "",
            ]
            
            # Group by phase/category
            current_category = None
            for task in tasks:
                category = task.tags[0] if task.tags else "general"
                if category != current_category:
                    lines.append(f"\n## {category.title()}")
                    current_category = category
                
                lines.append(f"- [ ] {task.action} <!-- id: {task.id} -->")
            
            with open(output_path, 'w') as f:
                f.write("\n".join(lines))
            
            print(f"[ORCH] 📝 Generated task.md at {output_path}")
            return True
        except Exception as e:
            print(f"[ORCH] ❌ Failed to generate task.md: {e}")
            return False
    
    def _load_context(self) -> None:
        """Load CONTEXT.json if available."""
        if os.path.exists(self.context_path):
            try:
                with open(self.context_path, 'r') as f:
                    self.context = json.load(f)
                print(f"[ORCH] 📄 Loaded context from {self.context_path}")
            except Exception as e:
                print(f"[ORCH] ⚠️ Failed to load context: {e}")
    
    def _customize_task(self, template: Task, counter: int, goal: str) -> Task:
        """Create a customized copy of a task template."""
        return Task(
            id=f"TASK-{counter:03d}",
            action=template.action,
            outcome=template.outcome,
            tags=template.tags.copy(),
            depends_on=template.depends_on.copy() if template.depends_on else [],
            field_requirements=template.field_requirements.copy(),
            verification=template.verification,
            context_scope=template.context_scope,
        )
    
    def _inject_field_requirements(self, tasks: list[Task]) -> list[Task]:
        """Inject field requirements from CONTEXT.json into relevant tasks."""
        if not self.context or "models" not in self.context:
            return tasks
        
        models = self.context["models"]
        
        for task in tasks:
            # Add field requirements to database/backend tasks
            if any(tag in task.tags for tag in ["database", "backend"]):
                for model_name, model_def in models.items():
                    if isinstance(model_def, dict):
                        task.field_requirements[model_name] = list(model_def.keys())
        
        return tasks


# CLI interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py '<goal description>'")
        print("Example: python orchestrator.py 'Build a todo app with React and FastAPI'")
        sys.exit(1)
    
    goal = " ".join(sys.argv[1:])
    
    orch = Orchestrator()
    tasks = orch.generate_tasks(goal)
    
    print("\n" + "=" * 50)
    print("Generated Tasks:")
    print("=" * 50)
    for task in tasks:
        deps = f" (depends: {', '.join(task.depends_on)})" if task.depends_on else ""
        print(f"  [{task.id}] {task.action}{deps}")
    
    # Save to files
    orch.save_tasks(tasks)
    orch.generate_task_md(tasks)
