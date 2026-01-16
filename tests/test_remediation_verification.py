"""
Verification Script for Remediation Changes
===========================================
Verifies that:
1. LoopConfig loads correctly.
2. Logging is setup.
3. TaskSelector uses TASKS.json as source of truth.
4. Markdown is synced from JSON.
"""

import sys
import os
import json
import logging
import pytest
from loop.config import LoopConfig
from loop.utils import setup_logging
from loop.task_selector import TaskSelector

def test_config_and_logging(tmp_path):
    """Verify config loading and logging setup."""
    log_file = tmp_path / "test.log"
    os.environ["LOG_FILE"] = str(log_file)
    os.environ["CDP_PORT"] = "1234"
    
    # Test Config
    config = LoopConfig.from_env()
    assert config.cdp_port == 1234
    assert config.log_file == str(log_file)
    
    # Test Logging
    logger = setup_logging(config.log_file)
    assert logger.name == "ralphs_loop"
    logger.info("Test log message")
    
    assert log_file.exists()
    assert "Test log message" in log_file.read_text()

def test_state_management(tmp_path):
    """Verify JSON <-> Markdown sync."""
    json_path = tmp_path / "TASKS.json"
    md_path = tmp_path / "task.md"
    
    # 1. Create initial JSON
    initial_tasks = [
        {"id": "T1", "action": "Task 1", "status": "pending", "tags": ["backend"]},
        {"id": "T2", "action": "Task 2", "status": "pending", "tags": ["frontend"]}
    ]
    json_path.write_text(json.dumps(initial_tasks))
    
    config = LoopConfig(
        tasks_json_path=str(json_path),
        task_md_path=str(md_path)
    )
    
    selector = TaskSelector(config=config)
    
    # 2. Verify loaded
    assert len(selector._tasks) == 2
    
    # 3. Mark Complete (Should update JSON and MD)
    selector.mark_complete("T1")
    
    # Check JSON
    data = json.loads(json_path.read_text())
    t1 = next(t for t in data if t["id"] == "T1")
    assert t1["status"] == "complete"
    assert "completed_at" in t1
    
    # Check MD Sync
    assert md_path.exists()
    md_content = md_path.read_text()
    assert "- [x] Task 1" in md_content
    assert "- [ ] Task 2" in md_content
    
    # 4. Mark Failed
    selector.mark_failed("T2", "Syntax Error")
    
    # Check JSON
    data = json.loads(json_path.read_text())
    t2 = next(t for t in data if t["id"] == "T2")
    assert t2["status"] == "failed"
    assert t2["failure_reason"] == "Syntax Error"
    
    # Check MD Sync
    md_content = md_path.read_text()
    assert "- [!] Task 2" in md_content
    assert "reason: Syntax Error" in md_content
    
    # 5. Verify Unmark
    selector.unmark("T2")
    data = json.loads(json_path.read_text())
    t2 = next(t for t in data if t["id"] == "T2")
    assert t2["status"] == "pending"
    assert "failure_reason" not in t2
    
    md_content = md_path.read_text()
    assert "- [ ] Task 2" in md_content

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
