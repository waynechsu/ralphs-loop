"""
Reset Handler Module
====================
Manages context rotation (blast shield) for the Ralph Wiggum Loop.

Responsibilities:
- Determine when to rotate context
- Execute page reload via CDP
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cdp_client import CDPClient


class ResetHandler:
    """Handles context rotation to prevent agent degradation."""
    
    def __init__(self, cdp_client: "CDPClient", threshold: int = 5):
        """
        Initialize reset handler.
        
        Args:
            cdp_client: CDPClient instance for page reload
            threshold: Number of tasks before context rotation
        """
        self.cdp_client = cdp_client
        self.threshold = threshold
    
    def should_rotate(self, tasks_completed: int) -> bool:
        """
        Check if context rotation is needed.
        
        Args:
            tasks_completed: Number of tasks completed in this session
            
        Returns:
            True if rotation is due
        """
        return tasks_completed > 0 and tasks_completed % self.threshold == 0
    
    def rotate(self) -> bool:
        """
        Execute context rotation by reloading the page.
        
        Returns:
            True if successful
        """
        print(f"[RESET] 🧹 Context rotation threshold reached ({self.threshold} tasks)")
        return self.cdp_client.reload_page()
