"""
Unit Tests for Progress Monitor Module
=======================================
Tests for loop/progress_monitor.py class.
"""

import time
import pytest
from unittest.mock import patch, MagicMock

from loop.progress_monitor import ProgressMonitor


class TestProgressMonitorInit:
    """Tests for ProgressMonitor initialization."""
    
    def test_default_values(self):
        """Test default configuration."""
        monitor = ProgressMonitor()
        
        assert monitor.task_md_path == ".agent/task.md"
        assert monitor.poll_interval == 3
        assert monitor.timeout == 300
    
    def test_custom_values(self):
        """Test custom configuration."""
        monitor = ProgressMonitor(
            task_md_path="/custom/path.md",
            poll_interval=5,
            timeout=60
        )
        
        assert monitor.task_md_path == "/custom/path.md"
        assert monitor.poll_interval == 5
        assert monitor.timeout == 60


class TestGetElapsedTime:
    """Tests for elapsed time tracking."""
    
    def test_elapsed_zero_before_start(self):
        """Test elapsed is 0 before polling starts."""
        monitor = ProgressMonitor()
        assert monitor.get_elapsed_time() == 0
    
    def test_elapsed_after_start(self):
        """Test elapsed increases after start."""
        monitor = ProgressMonitor()
        monitor._start_time = time.time() - 10  # Simulate 10s ago
        
        elapsed = monitor.get_elapsed_time()
        assert 9 <= elapsed <= 11  # Allow 1s tolerance


class TestIsTaskComplete:
    """Tests for task completion detection."""
    
    def test_detects_complete_task(self, tmp_path):
        """Test detecting a completed task."""
        task_file = tmp_path / "task.md"
        task_file.write_text("- [x] Do something <!-- id: TASK-001 -->")
        
        monitor = ProgressMonitor(task_md_path=str(task_file))
        
        assert monitor._is_task_complete("TASK-001") == True
    
    def test_detects_incomplete_task(self, tmp_path):
        """Test detecting an incomplete task."""
        task_file = tmp_path / "task.md"
        task_file.write_text("- [ ] Do something <!-- id: TASK-001 -->")
        
        monitor = ProgressMonitor(task_md_path=str(task_file))
        
        assert monitor._is_task_complete("TASK-001") == False
    
    def test_case_insensitive_x(self, tmp_path):
        """Test both [x] and [X] are detected."""
        task_file = tmp_path / "task.md"
        task_file.write_text("- [X] Do something <!-- id: TASK-001 -->")
        
        monitor = ProgressMonitor(task_md_path=str(task_file))
        
        assert monitor._is_task_complete("TASK-001") == True
    
    def test_missing_file_returns_false(self, tmp_path):
        """Test graceful handling of missing file."""
        monitor = ProgressMonitor(task_md_path=str(tmp_path / "missing.md"))
        
        assert monitor._is_task_complete("TASK-001") == False
    
    def test_wrong_task_id_returns_false(self, tmp_path):
        """Test that wrong task ID returns False."""
        task_file = tmp_path / "task.md"
        task_file.write_text("- [x] Do something <!-- id: TASK-001 -->")
        
        monitor = ProgressMonitor(task_md_path=str(task_file))
        
        assert monitor._is_task_complete("TASK-999") == False


class TestWaitForCompletion:
    """Tests for the main polling loop."""
    
    def test_immediate_completion(self, tmp_path):
        """Test immediate return when task already complete."""
        task_file = tmp_path / "task.md"
        task_file.write_text("- [x] Done <!-- id: TASK-001 -->")
        
        monitor = ProgressMonitor(
            task_md_path=str(task_file),
            poll_interval=1,
            timeout=5
        )
        
        result = monitor.wait_for_completion({"id": "TASK-001"})
        
        assert result == True
    
    def test_timeout_when_never_completes(self, tmp_path):
        """Test timeout when task never gets marked complete."""
        task_file = tmp_path / "task.md"
        task_file.write_text("- [ ] Not done <!-- id: TASK-001 -->")
        
        monitor = ProgressMonitor(
            task_md_path=str(task_file),
            poll_interval=1,
            timeout=2  # Very short timeout for test
        )
        
        result = monitor.wait_for_completion({"id": "TASK-001"})
        
        assert result == False
    
    def test_completion_during_polling(self, tmp_path):
        """Test that completion is detected during polling."""
        task_file = tmp_path / "task.md"
        task_file.write_text("- [ ] Pending <!-- id: TASK-001 -->")
        
        monitor = ProgressMonitor(
            task_md_path=str(task_file),
            poll_interval=1,
            timeout=10
        )
        
        # Simulate completion after 1 second
        def delayed_complete():
            time.sleep(1.5)
            task_file.write_text("- [x] Done <!-- id: TASK-001 -->")
        
        import threading
        thread = threading.Thread(target=delayed_complete)
        thread.start()
        
        result = monitor.wait_for_completion({"id": "TASK-001"})
        thread.join()
        
        assert result == True
