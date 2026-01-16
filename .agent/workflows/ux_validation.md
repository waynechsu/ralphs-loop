---
description: Run the UX Validation agent to verify UI implementation against specs
---

# UX Validation Agent (v1.2)

**Role:** Verify implemented UI matches `UI_SPEC.json`. Audit and report only.

---

## Invocation Parameters

```json
{
  "pages_to_validate": ["PAGE-001"],
  "thresholds": {
    "visual_diff_percent": 5,
    "max_load_time_ms": 2000,
    "min_contrast_ratio": 4.5
  }
}
```

---

## Phase 0: Input Validation

Verify `UI_SPEC.json`, presets, features exist. On failure → `DIAGNOSTICS.md` + HALT.

---

## Phase 1: Spec Ingestion

Load specs, `validation_hooks.test_data_source` if defined.

---

## Phase 2: Automated Audits

| Audit | Primary Tool | Python Fallback |
|-------|--------------|-----------------|
| Accessibility | axe-core | BeautifulSoup |
| Visual Regression | Playwright | PIL/Pillow |
| Performance | Lighthouse | requests + timing |

Includes: Contrast, Focus, ARIA, States, Responsive, Analytics, **Performance (NEW)**.

---

## Phase 3–4: Components & Traceability

Data binding, variants, interactions. Feature coverage vs CONTEXT.json.

---

## Phase 5: Reports

### Executive Summary (NEW)
Quick overview: pages validated, critical/warning counts, estimated fix time.

### Outputs
| Artifact | Required |
|----------|----------|
| `UX_VALIDATION_REPORT.md` | Yes |
| `REMEDIATION_PLAN.md` | If issues |
| `DIAGNOSTICS.md` | On error |

### Severity: 🔴 Critical (blocks) | 🟡 Warning (fix soon) | 🟢 Info
