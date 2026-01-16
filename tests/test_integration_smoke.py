"""
Integration Smoke Tests
=======================
Verifies integration of refactored components with real files.
Run with: python -m pytest tests/test_integration_smoke.py
"""

import sys
import os
import shlex
import pytest
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.append(os.getcwd())

from loop import TaskSelector
from qa import run_tests, QAConfig

def test_task_selector_real_files():
    """Test TaskSelector integration with real .agent files."""
    if not os.path.exists(".agent/TASKS.json"):
        pytest.skip("No .agent/TASKS.json found")
        
    selector = TaskSelector(
        tasks_json_path=".agent/TASKS.json",
        task_md_path=".agent/task.md"
    )
    
    tasks = selector.parse_tasks()
    assert isinstance(tasks, list)
    assert len(tasks) > 0, "Should have parsed at least one task"
    
    # Check validation delegation
    is_valid, errors = selector.validate_spec(tasks[0], None)
    assert isinstance(is_valid, bool)
    assert isinstance(errors, list)

def test_subprocess_command_splitting():
    """Test that commands are correctly split for shell=False."""
    mock_task = {"tags": ["backend"], "action": "test"}
    config = QAConfig()
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")
        
        run_tests(mock_task, config)
        
        # Verify call args
        args, kwargs = mock_run.call_args
        command_arg = args[0]
        
        assert isinstance(command_arg, list), "Command must be a list"
        assert kwargs.get("shell") is False, "shell must be False"
        
        expected_cmd = shlex.split("python -m pytest --tb=short -q")
        assert command_arg == expected_cmd, "Command list mismatch"

def test_driver_import():
    """Test that wiggum_driver can be imported."""
    try:
        import wiggum_driver
        assert True
    except ImportError as e:
        pytest.fail(f"Could not import wiggum_driver: {e}")
