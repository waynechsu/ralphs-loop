"""
Progress Monitor Module
=======================
Handles task completion polling for the Ralph Wiggum Loop.

Responsibilities:
- Poll task file for completion status
- Handle timeouts
- Track elapsed time
"""

import os
import re
import time
from typing import Optional


class ProgressMonitor:
    """Monitors task completion via file polling."""
    
    def __init__(
        self,
        task_md_path: str = ".agent/task.md",
        poll_interval: int = 3,
        timeout: int = 300
    ):
        """
        Initialize progress monitor.
        
        Args:
            task_md_path: Path to task.md file
            poll_interval: Seconds between polls
            timeout: Maximum wait time in seconds
        """
        self.task_md_path = task_md_path
        self.poll_interval = poll_interval
        self.timeout = timeout
        self._start_time: Optional[float] = None
    
    def wait_for_completion(self, task: dict) -> bool:
        """
        Poll until task is marked complete or timeout.
        
        Args:
            task: Task dict with 'id' and 'line_num'
            
        Returns:
            True if task completed, False if timeout
        """
        self._start_time = time.time()
        task_id = task.get('id', '')
        last_update_time = 0
        
        print(f"[POLL] Waiting for task completion (timeout: {self.timeout}s)...")
        
        while self.get_elapsed_time() < self.timeout:
            if self._is_task_complete(task_id):
                print("[POLL] ✅ Task marked complete!")
                return True
            
            time.sleep(self.poll_interval)
            
            elapsed = self.get_elapsed_time()
            if elapsed - last_update_time >= 15:  # Progress update every 15s
                print(f"[POLL] Still waiting... ({elapsed}s elapsed)")
                last_update_time = elapsed
        
        print(f"[POLL] ⏰ Timeout after {self.timeout}s")
        return False
    
    def get_elapsed_time(self) -> int:
        """Get seconds elapsed since polling started."""
        if self._start_time is None:
            return 0
        return int(time.time() - self._start_time)
    
    def _is_task_complete(self, task_id: str) -> bool:
        """Check if a specific task is marked complete."""
        if not os.path.exists(self.task_md_path):
            return False
        
        try:
            with open(self.task_md_path, 'r') as f:
                content = f.read()
            
            # Check for [x] with this task ID
            pattern = rf'^\s*-\s*\[x\]\s*.*<!-- id:\s*{re.escape(task_id)}\s*-->'
            return bool(re.search(pattern, content, re.MULTILINE | re.IGNORECASE))
        except Exception:
            return False
