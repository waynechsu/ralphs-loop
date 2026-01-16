"""
Prompt Builder Module
=====================
Constructs prompts with context injection for the Ralph Wiggum Loop.

Responsibilities:
- Load CONTEXT.json and design tokens
- Format task prompts with metadata
- Inject model requirements and brand guidelines
"""

import json
import os
from typing import Optional


class PromptBuilder:
    """Builds prompts with context injection for agent tasks."""
    
    def __init__(
        self,
        context_path: str = ".agent/CONTEXT.json",
        brand_path: str = ".agent/design_tokens.json"
    ):
        """
        Initialize prompt builder.
        
        Args:
            context_path: Path to CONTEXT.json
            brand_path: Path to design_tokens.json
        """
        self.context_path = context_path
        self.brand_path = brand_path
        self.context: Optional[dict] = None
        self.brand_tokens: Optional[dict] = None
        self._load_context()
    
    def build(self, task: dict) -> str:
        """
        Build a complete prompt for a task.
        
        Args:
            task: Task dict with action, outcome, verification, etc.
            
        Returns:
            Formatted prompt string
        """
        prompt = self._build_base_prompt(task)
        prompt = self._inject_context(prompt, task)
        prompt = self._inject_brand(prompt, task)
        prompt = self._inject_instructions(prompt)
        
        return prompt
    
    def _build_base_prompt(self, task: dict) -> str:
        """Build the base task prompt."""
        prompt = f"""Execute the following task from the Ralph Wiggum workflow:

**Task**: {task.get('action', 'Unknown action')}
"""
        
        if task.get("outcome"):
            prompt += f"""
**Success Criteria**: {task['outcome']}
"""
        
        if task.get("verification"):
            prompt += f"""
**Verification**: {json.dumps(task['verification'], indent=2)}
"""
        
        if task.get("context_scope"):
            prompt += f"""
**Context Scope**: {task['context_scope']}
"""
        
        return prompt
    
    def _inject_context(self, prompt: str, task: dict) -> str:
        """Inject CONTEXT.json requirements."""
        if not self.context:
            return prompt
        
        # Inject model requirements as MANDATORY
        if "models" in self.context:
            prompt += f"""

> [!CAUTION] SPEC = REQUIREMENT, NOT INSPIRATION
> The following model fields are MANDATORY. Missing fields = TASK FAILURE.

**REQUIRED Model Fields (from CONTEXT.json)**:
{json.dumps(self.context.get('models', {}), indent=2)}

You MUST implement ALL fields listed above. Do not skip or rename fields without explicit approval.
"""
        
        # Inject architecture standards for backend tasks
        tags = task.get("tags", [])
        if any(t in tags for t in ["backend", "database"]):
            if "architecture" in self.context:
                prompt += f"""
**Architecture Standards**: {json.dumps(self.context.get('architecture', {}), indent=2)}
"""
        
        # Inject QA rigour
        testing_strategy = self.context.get("testing_strategy", {})
        if testing_strategy.get("interaction_coverage") == "all_interactive_elements":
            prompt += """
> [!IMPORTANT] QA RIGOUR LEVEL: MAXIMUM
> Spec requires 'all_interactive_elements'. You must write tests for EVERY button and input field created.
"""
        
        return prompt
    
    def _inject_brand(self, prompt: str, task: dict) -> str:
        """Inject brand/design tokens for UI tasks."""
        if not self.brand_tokens:
            return prompt
        
        tags = task.get("tags", [])
        if not any(t in tags for t in ["frontend", "ui", "component"]):
            return prompt
        
        prompt += f"""

> [!TIP] BRAND GUIDELINES ACTIVE
> This project has a defined design system. Use these tokens for visual consistency.

**Design Tokens (from design_tokens.json):**
```json
{json.dumps(self.brand_tokens, indent=2)}
```

**Requirements:**
- Use the defined colors (no hardcoded hex values)
- Follow typography settings (fontPrimary, fontSecondary)
- Apply consistent spacing and border-radius
- Maintain brand voice in any UI copy
"""
        
        return prompt
    
    def _inject_instructions(self, prompt: str) -> str:
        """Add standard instructions to prompt."""
        prompt += """

Instructions:
1. Complete ONLY this single task
2. RUN TESTS to verify your changes (if applicable)
3. VALIDATE all spec fields are implemented before marking complete
4. Update .agent/task.md to mark it as [x] when done
5. Report completion clearly

Follow the workflow in .agent/workflows/ralph_mode.md"""
        
        return prompt
    
    def _load_context(self) -> None:
        """Load CONTEXT.json and design tokens."""
        # Load CONTEXT.json
        if os.path.exists(self.context_path):
            try:
                with open(self.context_path, 'r') as f:
                    self.context = json.load(f)
                print(f"[PROMPT] 📄 Context loaded from {self.context_path}")
            except Exception as e:
                print(f"[PROMPT] ⚠️ Failed to load context: {e}")
        
        # Load design tokens
        if os.path.exists(self.brand_path):
            try:
                with open(self.brand_path, 'r') as f:
                    self.brand_tokens = json.load(f)
                print(f"[PROMPT] 🎨 Brand tokens loaded from {self.brand_path}")
            except Exception as e:
                print(f"[PROMPT] ⚠️ Failed to load brand tokens: {e}")
    
    def reload_context(self) -> None:
        """Reload context files (useful for long-running sessions)."""
        self.context = None
        self.brand_tokens = None
        self._load_context()
