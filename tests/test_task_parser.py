"""
Unit Tests for Task Parser Module
==================================
Tests for loop/task_parser.py functions.
"""

import json
import os
import tempfile
import pytest

from loop.task_parser import (
    parse_json_tasks,
    parse_markdown_tasks,
    get_completed_ids,
)


class TestParseJsonTasks:
    """Tests for parse_json_tasks function."""
    
    def test_parse_empty_json(self, tmp_path):
        """Test parsing an empty JSON array."""
        tasks_file = tmp_path / "TASKS.json"
        tasks_file.write_text("[]")
        task_md = tmp_path / "task.md"
        task_md.write_text("")
        
        result = parse_json_tasks(str(tasks_file), str(task_md))
        assert result == []
    
    def test_parse_single_task(self, tmp_path):
        """Test parsing a single task."""
        tasks_file = tmp_path / "TASKS.json"
        tasks_file.write_text(json.dumps([{
            "id": "TASK-001",
            "action": "Create component",
            "outcome": "Component works",
            "tags": ["frontend"]
        }]))
        task_md = tmp_path / "task.md"
        task_md.write_text("")
        
        result = parse_json_tasks(str(tasks_file), str(task_md))
        
        assert len(result) == 1
        assert result[0]["id"] == "TASK-001"
        assert result[0]["action"] == "Create component"
        assert result[0]["complete"] == False
    
    def test_task_marked_complete(self, tmp_path):
        """Test that completed tasks are detected from task.md."""
        tasks_file = tmp_path / "TASKS.json"
        tasks_file.write_text(json.dumps([
            {"id": "TASK-001", "action": "First task"},
            {"id": "TASK-002", "action": "Second task"}
        ]))
        task_md = tmp_path / "task.md"
        task_md.write_text("- [x] First task <!-- id: TASK-001 -->\n- [ ] Second task <!-- id: TASK-002 -->")
        
        result = parse_json_tasks(str(tasks_file), str(task_md))
        
        assert result[0]["complete"] == True
        assert result[1]["complete"] == False
    
    def test_auto_generated_ids(self, tmp_path):
        """Test that tasks without IDs get auto-generated ones."""
        tasks_file = tmp_path / "TASKS.json"
        tasks_file.write_text(json.dumps([
            {"action": "No ID task"},
            {"action": "Another no ID"}
        ]))
        task_md = tmp_path / "task.md"
        task_md.write_text("")
        
        result = parse_json_tasks(str(tasks_file), str(task_md))
        
        assert result[0]["id"] == "TASK-0"
        assert result[1]["id"] == "TASK-1"


class TestParseMarkdownTasks:
    """Tests for parse_markdown_tasks function."""
    
    def test_parse_simple_tasks(self, tmp_path):
        """Test parsing simple markdown task format."""
        task_md = tmp_path / "task.md"
        task_md.write_text("""# Tasks
- [ ] First task <!-- id: MD-001 -->
- [x] Second task <!-- id: MD-002 -->
""")
        
        result = parse_markdown_tasks(str(task_md))
        
        assert len(result) == 2
        assert result[0]["action"] == "First task <!-- id: MD-001 -->"
        assert result[0]["complete"] == False
        assert result[1]["complete"] == True
    
    def test_parse_full_format(self, tmp_path):
        """Test parsing full Action->Outcome format."""
        task_md = tmp_path / "task.md"
        task_md.write_text("- [ ] **Action**: Create API → **Outcome**: API works <!-- id: T-1 -->")
        
        result = parse_markdown_tasks(str(task_md))
        
        assert len(result) == 1
        assert result[0]["action"] == "Create API"
        assert result[0]["outcome"] == "API works <!-- id: T-1 -->"


class TestGetCompletedIds:
    """Tests for get_completed_ids function."""
    
    def test_empty_file(self, tmp_path):
        """Test with empty task.md."""
        task_md = tmp_path / "task.md"
        task_md.write_text("")
        
        result = get_completed_ids(str(task_md))
        assert result == set()
    
    def test_finds_completed_ids(self, tmp_path):
        """Test that completed task IDs are found."""
        task_md = tmp_path / "task.md"
        task_md.write_text("""
- [x] Done task <!-- id: TASK-001 -->
- [ ] Not done <!-- id: TASK-002 -->
- [X] Also done <!-- id: TASK-003 -->
""")
        
        result = get_completed_ids(str(task_md))
        
        assert "TASK-001" in result
        assert "TASK-002" not in result
        assert "TASK-003" in result
    
    def test_nonexistent_file(self, tmp_path):
        """Test with a file that doesn't exist."""
        result = get_completed_ids(str(tmp_path / "nonexistent.md"))
        assert result == set()
