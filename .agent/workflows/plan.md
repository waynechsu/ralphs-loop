---
description: Generate TASKS.json from a high-level project goal
---
# Plan Workflow

> Use `/plan` to bootstrap a new project with an auto-generated task list.

## Steps

### 1. Define Your Goal
Describe your project in plain English. Be specific about:
- **Technology stack** (React, FastAPI, SQLite, etc.)
- **Core features** (authentication, CRUD, dashboard, etc.)
- **Constraints** (mobile-first, offline support, etc.)

Example:
```
Build a flight price tracker with React frontend and FastAPI backend.
It should scrape prices daily and send email alerts.
```

### 2. Generate Tasks
Run the orchestrator:
```bash
python orchestrator.py "Your goal description here"
```

This will:
- Parse your goal for keywords (backend, frontend, fullstack)
- Generate appropriate task templates
- Set dependencies between tasks
- Output `TASKS.json` and `task.md`

### 3. Review & Customize
Open `.agent/TASKS.json` and adjust:
- **Task order** — Reorder based on priority
- **Field requirements** — Add specific model fields from CONTEXT.json
- **Verification steps** — Add test commands

### 4. Define Context (Optional but Recommended)
Create `.agent/CONTEXT.json` with:
```json
{
  "models": {
    "YourModel": {
      "field1": "string",
      "field2": "int"
    }
  },
  "architecture": {
    "backend": "FastAPI + SQLite",
    "frontend": "React + Vite"
  },
  "testing_strategy": {
    "framework": "pytest",
    "coverage": "80%"
  }
}
```

The orchestrator will inject these field requirements into relevant tasks.

### 5. Start the Loop
```bash
python wiggum_driver.py
```

The driver will now execute tasks from your generated TASKS.json.

---

## Quick Start

```bash
# One-liner to bootstrap a new project
python orchestrator.py "Build a todo app with React and FastAPI"
python wiggum_driver.py
```
