---
description: Brand Design: Define visual identity and design system for your product
---
# Brand Design Workflow

> Use this to create a cohesive brand identity before or during development.

---

## When to Use
- Starting a new product and want a polished visual identity
- Existing product needs design consistency
- Before major UI work to establish design tokens

---

## Workflow Steps

### 1. Invoke Brand Designer Persona
Load the brand designer system prompt:
```
I want to define the brand identity for this project.
Follow the protocol in system_brand_designer.md
```

### 2. Phase 1: Soul Search
Provide these inputs when asked:
- **Product Name**: What is this called?
- **Target User**: Who uses this?
- **Core Emotions**: How should it feel? (e.g., "trustworthy", "exciting", "calm")

Agent will propose 3 "Vibe Directions". **Select one**.

### 3. Phase 2: Visual Anchor
Agent will deliver:
- Typography pairing (Header + Body fonts)
- Color palette (Primary, Secondary, Accent, Surface)
- Moodboard descriptors

### 4. Phase 3: Identity Architecture
Agent will create:
- Logo concept (CSS-based or SVG description)
- Voice/tone guidelines

### 5. Phase 4: System Implementation
Agent will generate:

**Required Output:**
```
.agent/BRAND_BOOK.md       # Human-readable brand guide
.agent/design_tokens.json  # Machine-readable design tokens
```

---

## Output Files

### BRAND_BOOK.md (Human Readable)
```markdown
# [Product Name] Brand Guide

## Brand Archetype
[Selected direction]

## Typography
- Primary: [Font]
- Secondary: [Font]

## Color Palette
| Role | Hex | Usage |
|------|-----|-------|
| Primary | #xxx | Buttons, links |
| Background | #xxx | Page bg |
...

## Voice & Tone
[Guidelines]
```

### design_tokens.json (Machine Readable)
```json
{
  "colors": {
    "primary": "#4F46E5",
    "secondary": "#10B981",
    "background": "#0F172A",
    "surface": "#1E293B",
    "text": "#F8FAFC",
    "textMuted": "#94A3B8"
  },
  "typography": {
    "fontPrimary": "Inter",
    "fontSecondary": "JetBrains Mono"
  },
  "spacing": {
    "unit": 4
  },
  "borderRadius": {
    "sm": "4px",
    "md": "8px",
    "lg": "16px"
  }
}
```

---

## Integration with Ralph Wiggum Loop

The driver automatically detects `.agent/design_tokens.json`:
- **If present**: Injects brand context into UI task prompts
- **If absent**: Proceeds without brand constraints

> [!TIP]
> Run `/brand` before starting UI tasks to ensure visual consistency!

---

## Example Usage

```bash
# In the IDE chat:
/brand

# Follow the 4-phase process
# Output: .agent/BRAND_BOOK.md and .agent/design_tokens.json

# Later, when running the loop:
python3 wiggum_driver.py
# Driver will detect and inject brand tokens into UI prompts
```
