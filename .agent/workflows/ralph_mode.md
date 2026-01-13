---
description: Ralph Wiggum Loop Workflow
---
# Ralph Wiggum Workflow

This workflow is designed to be run repeatedly by the external driver loop.

1.  **Read the Task List**
    - Open `.agent/task.md` and find the first unchecked item.

2.  **Execute Task**
    - Perform the necessary code changes or analysis for *that single item*.
    - **Crucial**: Do not attempt to do multiple items. Focus is key.

3.  **Update Task List**
    - Mark the item as `[x]` in `.agent/task.md`.

4.  **Report Completion**
    - State clearly "I have completed the task: [Task Name]".
    - This signal allows the external driver to reset the loop.
