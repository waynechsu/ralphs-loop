# Ralph's Loop Template Gap Analysis

Based on the Flight & Hotel Tracker implementation drift, this document identifies improvement areas in the Ralph Wiggum Loop templates.

---

## Summary of Issues Found

| Gap | Impact | Location(s) |
|-----|--------|-------------|
| No field-level traceability | Spec fields get skipped/renamed | `TASKS.json`, `CONTEXT.json` |
| No spec validation before verification | Agent doesn't check if all fields implemented | `wiggum_driver.py` |
| Bidirectional sync missing | Spec never updated after implementation | Manual process |
| Glossary underutilized | Naming drift (`TripRequest` → `Route`) | `system_architect.md` |
| Workflow lacks spec-checking step | Agent skips straight to marking [x] | `ralph_mode.md` |

---

## Detailed Gap Analysis

### 1. TASKS.json — Missing Field-Level Granularity

**Current State:**
```json
{
  "action": "Define Database Models",
  "outcome": "SQLModel classes for Route, PricePoint, and Settings."
}
```

**Problem:** The task says "create models" but doesn't list *which fields* from `CONTEXT.json` must be present. The agent can complete this by creating models with *any* fields.

**Proposed Fix:**
```json
{
  "action": "Define Database Models",
  "outcome": "SQLModel classes for Route, PricePoint, and Settings.",
  "field_requirements": {
    "TripRequest": ["origin", "destination", "date_range_start", "date_range_end", "max_price_threshold", "cooldown_hours", "flexibility"]
  },
  "verification": {
    "type": "schema_check",
    "command": "python -c \"from backend.models import Route; print([f.name for f in Route.__fields__.values()])\"",
    "expected_fields": ["origin", "destination", "max_price_threshold", "cooldown_hours"]
  }
}
```

---

### 2. wiggum_driver.py — No Pre-Flight Spec Validation

**Current State (line 439-480):**
```python
prompt = f"""Execute the following task from the Ralph Wiggum workflow:

**Task**: {task['action']}
...
```

**Problem:** The driver injects the task but does NOT inject the required field list from `CONTEXT.json`. The agent has no way to know what fields are expected.

**Proposed Fix:** Add a new injection step:
```python
# NEW: Inject required model fields from CONTEXT.json
if "models" in context_data and task.get("field_requirements"):
    model_spec = context_data["models"]
    prompt += f"""
**Required Model Fields (from CONTEXT.json):**
{json.dumps(model_spec, indent=2)}

You MUST implement ALL fields listed above. Missing fields = task failure.
"""
```

---

### 3. system_architect.md — Weak Glossary → Code Binding

**Current State (line 177-192):**
```json
{
  "primary": "invoice",
  "synonyms": ["bill", "statement"],
  "aliases_in_code": ["INV", "inv_id"]
}
```

**Problem:** The glossary defines `aliases_in_code` but this is NOT enforced. The agent named the model `Route` when the spec said `TripRequest`.

**Proposed Fix:** Add to `CONTEXT.json`:
```json
"naming_enforcement": {
  "model_names": {
    "TripRequest": "Route",  // Explicit mapping OR enforcement
    "PricePoint": "PricePoint"
  },
  "enforcement": "warn"  // warn | block
}
```

And add to the validation phase:
```markdown
### Naming Validation
- [ ] All model names match CONTEXT.json `naming_enforcement.model_names`
- [ ] Divergence is logged in changelog with justification
```

---

### 4. ralph_mode.md — Missing Spec Comparison Step

**Current State:**
```markdown
1. Read the Task List
2. Execute Task
3. Update Task List
4. Report Completion
```

**Problem:** No step to **compare implementation against spec** before marking complete.

**Proposed Fix:**
```markdown
---
description: Ralph Wiggum Loop Workflow
---
# Ralph Wiggum Workflow

1.  **Read the Task List**
    - Open `.agent/task.md` and find the first unchecked item.

2.  **Check Spec Requirements** ← NEW
    - Open `.agent/CONTEXT.json` and identify the relevant models/fields
    - If `field_requirements` exist in TASKS.json, list them explicitly

3.  **Execute Task**
    - Perform the necessary code changes
    - **Crucial**: Implement ALL fields from the spec, not just "enough to work"

4.  **Validate Against Spec** ← NEW
    - Compare implemented fields to CONTEXT.json requirements
    - If mismatch: DO NOT mark as complete; report discrepancy

5.  **Update Task List**
    - Mark the item as `[x]` in `.agent/task.md`

6.  **Report Completion**
    - State clearly "I have completed the task: [Task Name]"
```

---

### 5. Missing Bidirectional Sync Mechanism

**Problem:** After implementation, the spec (`CONTEXT.json`) is never updated to reflect reality. This creates permanent drift.

**Proposed Fix:** Add to `system_architect.md` Phase 5:

```markdown
**Phase 5B: Post-Implementation Sync (NEW)**
- Triggered after ALL tasks complete
- Compare CONTEXT.json models to actual implementations
- Generate changelog entry for any divergence
- Options:
  - Update CONTEXT.json to match code (preferred for organic evolution)
  - Create issue/task to fix code to match spec (preferred for strict compliance)
```

And add a new verified artifact:
```
specs/
├── ...existing files...
└── IMPLEMENTATION_DELTA.json   # Tracks spec vs reality differences
```

---

## Priority Ranking

| # | Improvement | Effort | Impact | Status |
|---|-------------|--------|--------|--------|
| 1 | Add `field_requirements` to TASKS.json schema | Low | High | ✅ Solved (task_selector.py) |
| 2 | Update `ralph_mode.md` with validation step | Low | High | ✅ Solved |
| 3 | Add spec field injection to wiggum_driver.py | Medium | High | ✅ Solved (wiggum_driver.py) |
| 4 | Add `naming_enforcement` to CONTEXT.json schema | Low | Medium | ✅ Solved (spec_validator.py) |
| 5 | Add Phase 5B post-implementation sync | Medium | Medium | 🚧 Deferred |

---

## Applied Fixes Summary

| File | Changes Made |
|------|-------------|
| `ralph_mode.md` | Added "SPEC = REQUIREMENT" caution, validation steps 2 & 4, divergence reporting |
| `wiggum_driver.py` | Automated spec validation with retry loop (see below) |
| `system_architect.md` | Added `field_requirements`, `naming_enforcement`, Phase 5B sync |
| **QA Integration** | Added mandatory `testing_strategy` and `Run Tests` steps to all templates |
| `README.md` | Documented spec enforcement features |

---

## Automated Spec Validation System (NEW)

The driver now includes **real enforcement**, not just advisory prompts:

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│ Agent marks [x] │ ───▶ │ validate_spec_  │ ───▶ │ If FAIL: Unmark │
│                 │      │ compliance()    │      │ + retry prompt  │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

### New Functions

| Function | Purpose |
|----------|--------|
| `validate_spec_compliance()` | Reads CONTEXT.json, parses `models.py`, compares fields |
| `unmark_task()` | Removes [x] from task.md so agent must retry |

### Retry Logic

- **MAX_VALIDATION_RETRIES = 2** — Agent gets 2 chances to fix missing fields
- On failure: Driver injects error prompt listing exactly which fields are missing
- After max retries: Task is marked as failed and driver moves on

---

## 6. QA Institutionalization (NEW)

To ensure all future apps have testing built-in, the following changes were made:

| Template | Change |
|----------|--------|
| `system_architect.md` | MANDATES defining a "QA Strategy" (Frameworks, Golden Path) in Phase 2 |
| `ralph_mode.md` | Added "Regression Check" (Step 1b) and "Run Tests" (Step 3b) |
| `wiggum_driver.py` | Injects "RUN TESTS" instruction in every prompt |

---

## Recommended Next Steps

1. **Update template schemas** — Add `field_requirements` and `naming_enforcement` to the spec format
2. **Patch ralph_mode.md** — Add steps 2 and 4 (spec check, validation)
3. **Enhance wiggum_driver.py** — Inject model field requirements into prompts

---

## V1 Finalization Status (2026-01-16)

The following improvements were implemented to finalize V1:

### 1. Robustness
- **Validation**: `TaskSelector` now validates `TASKS.json` schema on load.
- **Error Handling**: `wiggum_driver.py` includes robust retries for CDP connections.

### 2. QA Depth
- **Aggregation**: `qa_verification.py` aggregates all checks into `.agent/qa_report.json`.
- **Visual Checks**: `qa/visual_checker.py` now includes strict rule-based checks (PNG header, size) before LLM calls.

### 3. Testing
- **E2E**: Expanded `tests/test_e2e_flow.py` with dependency handling and context rotation scenarios.
- **CI**: Configured GitHub Actions to archive QA reports.

### 4. Metrics
- **Performance**: `ProgressMonitor` now logs task duration to `.agent/metrics.json`.

### 5. Documentation
- **Workflow**: Added Mermaid sequence diagram for triggers to `README.md`.

