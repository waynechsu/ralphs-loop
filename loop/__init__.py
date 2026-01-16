"""
Ralph Wiggum Loop - Modular Package
====================================
Provides composable modules for autonomous agent execution.

Modules:
- CDPClient: Chrome DevTools Protocol communication
- TaskSelector: Task parsing and selection
- PromptBuilder: Context injection and prompt formatting
- ProgressMonitor: Completion polling and timeout handling
- ResetHandler: Context rotation (blast shield)
- task_parser: Task file parsing utilities
- spec_validator: Spec validation utilities
"""

from .cdp_client import CDPClient
from .task_selector import TaskSelector
from .prompt_builder import PromptBuilder
from .progress_monitor import ProgressMonitor
from .reset_handler import ResetHandler
from .task_parser import parse_json_tasks, parse_markdown_tasks, get_completed_ids
from .spec_validator import validate_spec, find_implemented_models

__all__ = [
    "CDPClient",
    "TaskSelector", 
    "PromptBuilder",
    "ProgressMonitor",
    "ResetHandler",
    # New utility exports
    "parse_json_tasks",
    "parse_markdown_tasks",
    "get_completed_ids",
    "validate_spec",
    "find_implemented_models",
]

