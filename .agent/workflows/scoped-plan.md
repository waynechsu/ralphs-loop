---
description: Scoped Planning: Create a focused task list for a specific feature or branch
---
# Scoped Planning Workflow

> Use this when working on a feature branch to keep context minimal and focused.

## When to Use
- Starting work on a feature branch (`git checkout -b feature/auth`)
- Tackling a specific subsystem without full project context
- Reducing cognitive load for the agent

---

## Workflow Steps

### 1. Identify Scope
- Ask user (or infer from branch name) for the **Work Description**
  - Examples: "OAuth Integration", "Flight Matrix Display", "Price Alert System"
- This plan is **STRICTLY SCOPED** to that topic only

### 2. Orient
- Read `specs/*` and source code relevant to the scope
- Read `.agent/TASKS.json` or `.agent/task.md` for existing tasks
- **Ignore** tasks unrelated to the Work Description

### 3. Generate Scoped Plan
- Create `.agent/SCOPED_TASKS.json` (or overwrite)
- Include ONLY tasks required to achieve the Work Description
- Preserve `field_requirements` and `verification` from source tasks
- Add any NEW tasks discovered during analysis

**Format:**
```json
{
  "scope": "OAuth Integration",
  "branch": "feature/oauth",
  "parent_spec": "TASKS.json",
  "tasks": [
    {
      "id": "SCOPED-001",
      "source_id": "TASK-042",
      "action": "...",
      "outcome": "...",
      "field_requirements": {...},
      "verification": {...}
    }
  ]
}
```

### 4. Update Driver Target (Optional)
If using `wiggum_driver.py`, temporarily point it to the scoped file:
```python
TASK_FILE = ".agent/SCOPED_TASKS.json"
```

---

## Rules

> [!IMPORTANT]
> **DO NOT** include general tech debt or unrelated features.
> Keep focus on the branch goal only.

> [!TIP]
> After merging the feature branch, delete `SCOPED_TASKS.json` to avoid stale plans.

---

## Example Usage

```bash
# 1. Create feature branch
git checkout -b feature/oauth

# 2. Run scoped planning
# In IDE: /scoped-plan "OAuth Integration"

# 3. Agent generates SCOPED_TASKS.json with only OAuth tasks

# 4. Run driver on scoped tasks
python3 wiggum_driver.py  # (after updating TASK_FILE path)

# 5. Merge and cleanup
git checkout main && git merge feature/oauth
rm .agent/SCOPED_TASKS.json
```
