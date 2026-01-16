"""
Task Parser Module
==================
Handles parsing tasks from JSON and Markdown files.

Responsibilities:
- Parse tasks from TASKS.json
- Parse tasks from task.md (legacy format)
- Track completion status
"""

import json
import os
import re
from typing import Optional


def parse_json_tasks(
    tasks_json_path: str,
    task_md_path: str
) -> list[dict]:
    """
    Parse tasks from TASKS.json.
    
    Args:
        tasks_json_path: Path to TASKS.json file
        task_md_path: Path to task.md for completion status
        
    Returns:
        List of task dicts
    """
    tasks = []
    
    try:
        with open(tasks_json_path, 'r') as f:
            data = json.load(f)
        
        # Check completion status from task.md
        completed_ids = get_completed_ids(task_md_path)
        
        for i, item in enumerate(data):
            tid = item.get("id", f"TASK-{i}")
            tasks.append({
                "line_num": i,
                "complete": tid in completed_ids,
                "action": item.get("action"),
                "outcome": item.get("outcome"),
                "verification": item.get("verification"),
                "context_scope": item.get("context_scope"),
                "field_requirements": item.get("field_requirements", {}),
                "tags": item.get("tags", []),
                "id": tid,
                "raw": json.dumps(item)
            })
    except Exception as e:
        print(f"[TASK] ⚠️ Failed to parse JSON tasks: {e}")
    
    return tasks


def parse_markdown_tasks(task_md_path: str) -> list[dict]:
    """
    Parse tasks from task.md (legacy format).
    
    Args:
        task_md_path: Path to task.md file
        
    Returns:
        List of task dicts
    """
    tasks = []
    
    try:
        with open(task_md_path, 'r') as f:
            lines = f.read().splitlines()
        
        pattern_full = re.compile(
            r'^- \[([ x])\]\s*\*\*Action\*\*:\s*(.+?)\s*→\s*\*\*Outcome\*\*:\s*(.+)$'
        )
        pattern_id = re.compile(r'<!-- id: (.*?) -->')
        pattern_simple = re.compile(r'^- \[([ x])\]\s*(.+)$')
        
        for i, line in enumerate(lines):
            match_full = pattern_full.match(line.strip())
            match_simple = pattern_simple.match(line.strip())
            match_id = pattern_id.search(line)
            tid = match_id.group(1) if match_id else f"MD-{i}"
            
            if match_full:
                tasks.append({
                    "line_num": i,
                    "complete": match_full.group(1).lower() == 'x',
                    "action": match_full.group(2).strip(),
                    "outcome": match_full.group(3).strip(),
                    "id": tid,
                    "raw": line
                })
            elif match_simple:
                tasks.append({
                    "line_num": i,
                    "complete": match_simple.group(1).lower() == 'x',
                    "action": match_simple.group(2).strip(),
                    "outcome": None,
                    "id": tid,
                    "raw": line
                })
    except Exception as e:
        print(f"[TASK] ⚠️ Failed to parse Markdown tasks: {e}")
    
    return tasks


def get_completed_ids(task_md_path: str) -> set:
    """
    Get set of completed task IDs from task.md.
    
    Args:
        task_md_path: Path to task.md file
        
    Returns:
        Set of completed task ID strings
    """
    completed_ids: set = set()
    
    if os.path.exists(task_md_path):
        with open(task_md_path, 'r') as f:
            content = f.read()
        
        matches = re.findall(
            r'^\s*-\s*\[x\]\s*.*<!-- id:\s*(.*?)\s*-->',
            content, re.MULTILINE | re.IGNORECASE
        )
        completed_ids = set(matches)
    
    return completed_ids
