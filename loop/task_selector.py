"""
Task Selector Module
====================
Manages task selection and status tracking for the Ralph Wiggum Loop.

This is the simplified orchestrator that delegates:
- Parsing to task_parser module
- Validation to spec_validator module
"""

import os
import re
from typing import Optional

from .task_parser import parse_json_tasks, parse_markdown_tasks
from .spec_validator import validate_spec


class TaskSelector:
    """Manages task selection and status tracking."""
    
    def __init__(
        self,
        tasks_json_path: str = ".agent/TASKS.json",
        task_md_path: str = ".agent/task.md"
    ):
        """
        Initialize task selector.
        
        Args:
            tasks_json_path: Path to TASKS.json file
            task_md_path: Path to task.md for status tracking
        """
        self.tasks_json_path = tasks_json_path
        self.task_md_path = task_md_path
        self._tasks: list[dict] = []
    
    def parse_tasks(self) -> list[dict]:
        """
        Parse tasks from JSON (preferred) or Markdown (legacy).
        
        Returns:
            List of task dicts with keys: id, action, outcome, complete, etc.
        """
        self._tasks = []
        
        # Try JSON source first
        if os.path.exists(self.tasks_json_path):
            self._tasks = parse_json_tasks(self.tasks_json_path, self.task_md_path)
        elif os.path.exists(self.task_md_path):
            self._tasks = parse_markdown_tasks(self.task_md_path)
        else:
            print(f"[TASK] ⚠️ No task file found at {self.tasks_json_path} or {self.task_md_path}")
        
        return self._tasks
    
    def get_next(self) -> Optional[dict]:
        """
        Get the first incomplete task.
        
        Returns:
            Task dict if found, None if all complete
        """
        tasks = self.parse_tasks()
        for task in tasks:
            if not task.get("complete"):
                return task
        return None
    
    def mark_complete(self, task_id: str) -> bool:
        """
        Mark a task as complete in task.md.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if successfully marked
        """
        if not os.path.exists(self.task_md_path):
            return False
        
        with open(self.task_md_path, 'r') as f:
            content = f.read()
        
        # Pattern to match unchecked task with this ID
        pattern = rf'(- \[) (\].*<!-- id: {re.escape(task_id)} -->)'
        new_content = re.sub(pattern, r'\1x\2', content)
        
        if new_content != content:
            with open(self.task_md_path, 'w') as f:
                f.write(new_content)
            print(f"[TASK] ✅ Marked task {task_id} complete")
            return True
        
        return False
    
    def unmark(self, task_id: str) -> bool:
        """
        Remove [x] from a task, reverting to [ ].
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if successfully unmarked
        """
        if not os.path.exists(self.task_md_path):
            return False
        
        with open(self.task_md_path, 'r') as f:
            content = f.read()
        
        pattern = rf'(- \[)[xX](\].*<!-- id: {re.escape(task_id)} -->)'
        new_content = re.sub(pattern, r'\1 \2', content)
        
        if new_content != content:
            with open(self.task_md_path, 'w') as f:
                f.write(new_content)
            print(f"[TASK] 🔄 Unmarked task {task_id} for retry")
            return True
        
        return False
    
    def validate_spec(self, task: dict, context_data: Optional[dict]) -> tuple[bool, list[str]]:
        """
        Validate that implementation matches spec requirements.
        
        Delegates to spec_validator module.
        
        Args:
            task: Task dict with field_requirements
            context_data: CONTEXT.json data with models
            
        Returns:
            (is_valid, list_of_errors)
        """
        return validate_spec(task, context_data)
