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
            match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
            
            if match:
                # Add timestamp if enabled and not present
                self._ensure_timestamp(task_id, content, match)
                
                # Log metrics
                self._log_metrics(task_id)
                return True
                
            return False
        except Exception:
            return False

    def _log_metrics(self, task_id: str) -> None:
        """Log task duration metrics."""
        import json
        
        duration = self.get_elapsed_time()
        metrics_path = os.path.join(os.path.dirname(self.task_md_path), "metrics.json")
        
        entry = {
            "task_id": task_id,
            "duration_seconds": duration,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            metrics = []
            if os.path.exists(metrics_path):
                # Check if we already logged this task recently to avoid dupes from polling
                # A simple way is to check if TTA < 60s
                with open(metrics_path, 'r') as f:
                    try:
                        metrics = json.load(f)
                    except json.JSONDecodeError:
                        pass
                        
            # Prevent duplicate logs for same task completion event (simple de-dupe)
            if not any(m["task_id"] == task_id and m["duration_seconds"] == duration for m in metrics):
                metrics.append(entry)
                with open(metrics_path, 'w') as f:
                    json.dump(metrics, f, indent=2)
        except Exception as e:
            print(f"[POLL] ⚠️ Failed to log metrics: {e}")

    def _ensure_timestamp(self, task_id: str, content: str, match: re.Match) -> None:
        """Add timestamp to completed task if missing."""
        line = match.group(0)
        # Check if already has date-like string (simple heuristic)
        if re.search(r'\d{4}-\d{2}-\d{2}', line):
            return
            
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        # Insert timestamp after [x]
        new_line = re.sub(r'(\[x\])', f'\\1 *{timestamp}*', line)
        
        new_content = content.replace(line, new_line)
        
        try:
            with open(self.task_md_path, 'w') as f:
                f.write(new_content)
            print(f"[POLL] 🕒 Added timestamp to task {task_id}")
        except Exception as e:
            print(f"[POLL] ⚠️ Failed to add timestamp: {e}")
