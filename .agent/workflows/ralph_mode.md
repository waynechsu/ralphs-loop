---
description: Ralph Wiggum Loop Workflow
---
# Ralph Wiggum Workflow

This workflow is designed to be run repeatedly by the external driver loop.

> [!CAUTION]
> **SPEC = REQUIREMENT, NOT INSPIRATION**
> The fields and models in `.agent/CONTEXT.json` are mandatory contracts.
> Skipping or renaming fields without updating the spec is a **TASK FAILURE**.

---

## Workflow Steps

### 1. Read the Task List
- Open `.agent/task.md` and find the first unchecked item.
- Note the task ID (e.g., `TASK-002`).

### 1b. Regression Check (If applicable)
- Run `npm test` or `pytest` to ensure clean state.
- If existing tests fail, **STOP** and fix them before starting the task.

### 2. Load Spec Requirements ⚠️ CRITICAL
- Open `.agent/CONTEXT.json` and identify relevant `models` for this task.
- If `.agent/TASKS.json` contains `field_requirements` for this task, **you MUST implement ALL listed fields**.
- List out the required fields before writing code.

### 3a. Execute Task
- Perform the necessary code changes for *that single item*.
- **Crucial**: Do not attempt multiple items. Focus is key.
- **Crucial**: Implement ALL fields from the spec—not just "enough to work".

### 3b. Run Tests ⚠️ CRITICAL
- Run unit/integration tests for the modified component.
- Ensure ALL tests pass (`npm test` / `pytest`).
- **Required Coverage**: Check `interaction_coverage` in CONTEXT.json.
  - If `all_interactive_elements`: You MUST test every button click and input.
  - If `critical_path`: Test the happy-path flow.

### 4. Validate Against Spec ⚠️ CRITICAL
Before marking complete, verify:
- [ ] ALL Tests pass (Green build)
- [ ] Coverage meets `interaction_coverage` standard (e.g. all buttons tested)
- [ ] All required model fields from `CONTEXT.json` are implemented
- [ ] Naming matches spec (or divergence is documented in changelog)
- [ ] If `field_requirements` exist in TASKS.json, ALL are present

**If validation fails**: DO NOT mark as complete. Report the discrepancy.

### 5. Update Task List
- Mark the item as `[x]` in `.agent/task.md`.

### 6. Report Completion
- State clearly: "I have completed the task: [Task Name]".
- If any spec divergence occurred, note it: "Divergence: [field] renamed to [new_name]"
- This signal allows the external driver to reset the loop.
