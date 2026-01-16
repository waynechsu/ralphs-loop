"""
Unit Tests for Prompt Builder Module
=====================================
Tests for loop/prompt_builder.py class.
"""

import json
import pytest
from unittest.mock import patch, mock_open

from loop.prompt_builder import PromptBuilder


class TestPromptBuilderInit:
    """Tests for PromptBuilder initialization."""
    
    def test_init_without_files(self, tmp_path):
        """Test initialization when no context files exist."""
        builder = PromptBuilder(
            context_path=str(tmp_path / "missing.json"),
            brand_path=str(tmp_path / "missing_brand.json")
        )
        
        assert builder.context is None
        assert builder.brand_tokens is None
    
    def test_init_with_context_file(self, tmp_path):
        """Test initialization loads CONTEXT.json."""
        context_file = tmp_path / "CONTEXT.json"
        context_file.write_text(json.dumps({
            "models": {"User": {"name": "string"}}
        }))
        
        builder = PromptBuilder(
            context_path=str(context_file),
            brand_path=str(tmp_path / "missing.json")
        )
        
        assert builder.context is not None
        assert "models" in builder.context
    
    def test_init_with_brand_tokens(self, tmp_path):
        """Test initialization loads design tokens."""
        brand_file = tmp_path / "tokens.json"
        brand_file.write_text(json.dumps({
            "colors": {"primary": "#FF0000"}
        }))
        
        builder = PromptBuilder(
            context_path=str(tmp_path / "missing.json"),
            brand_path=str(brand_file)
        )
        
        assert builder.brand_tokens is not None
        assert "colors" in builder.brand_tokens


class TestBuildBasePrompt:
    """Tests for base prompt building."""
    
    def test_minimal_task(self, tmp_path):
        """Test building prompt with minimal task data."""
        builder = PromptBuilder(
            context_path=str(tmp_path / "missing.json"),
            brand_path=str(tmp_path / "missing.json")
        )
        
        task = {"action": "Create a button"}
        prompt = builder.build(task)
        
        assert "Create a button" in prompt
        assert "Execute the following task" in prompt
    
    def test_task_with_outcome(self, tmp_path):
        """Test that outcome gets included."""
        builder = PromptBuilder(
            context_path=str(tmp_path / "missing.json"),
            brand_path=str(tmp_path / "missing.json")
        )
        
        task = {
            "action": "Create button",
            "outcome": "Button displays correctly"
        }
        prompt = builder.build(task)
        
        assert "Success Criteria" in prompt
        assert "Button displays correctly" in prompt
    
    def test_task_with_verification(self, tmp_path):
        """Test that verification gets JSON-serialized."""
        builder = PromptBuilder(
            context_path=str(tmp_path / "missing.json"),
            brand_path=str(tmp_path / "missing.json")
        )
        
        task = {
            "action": "Create API",
            "verification": {"test": "pytest", "coverage": 80}
        }
        prompt = builder.build(task)
        
        assert "Verification" in prompt
        assert "pytest" in prompt


class TestContextInjection:
    """Tests for CONTEXT.json injection."""
    
    def test_model_requirements_injected(self, tmp_path):
        """Test that model fields are injected with CAUTION."""
        context_file = tmp_path / "CONTEXT.json"
        context_file.write_text(json.dumps({
            "models": {"Flight": {"origin": "str", "destination": "str"}}
        }))
        
        builder = PromptBuilder(
            context_path=str(context_file),
            brand_path=str(tmp_path / "missing.json")
        )
        
        task = {"action": "Create model", "tags": ["backend"]}
        prompt = builder.build(task)
        
        assert "CAUTION" in prompt
        assert "MANDATORY" in prompt
        assert "Flight" in prompt
    
    def test_architecture_injected_for_backend(self, tmp_path):
        """Test architecture standards for backend tasks."""
        context_file = tmp_path / "CONTEXT.json"
        context_file.write_text(json.dumps({
            "architecture": {"pattern": "MVC"}
        }))
        
        builder = PromptBuilder(
            context_path=str(context_file),
            brand_path=str(tmp_path / "missing.json")
        )
        
        task = {"action": "Create service", "tags": ["backend"]}
        prompt = builder.build(task)
        
        assert "Architecture Standards" in prompt
        assert "MVC" in prompt
    
    def test_qa_rigour_injected(self, tmp_path):
        """Test QA rigour message for all_interactive_elements."""
        context_file = tmp_path / "CONTEXT.json"
        context_file.write_text(json.dumps({
            "testing_strategy": {"interaction_coverage": "all_interactive_elements"}
        }))
        
        builder = PromptBuilder(
            context_path=str(context_file),
            brand_path=str(tmp_path / "missing.json")
        )
        
        task = {"action": "Create form", "tags": ["frontend"]}
        prompt = builder.build(task)
        
        assert "QA RIGOUR LEVEL: MAXIMUM" in prompt


class TestBrandInjection:
    """Tests for brand/design token injection."""
    
    def test_brand_tokens_for_frontend_tasks(self, tmp_path):
        """Test brand tokens injected for frontend tasks."""
        brand_file = tmp_path / "tokens.json"
        brand_file.write_text(json.dumps({
            "colors": {"primary": "#3B82F6"}
        }))
        
        builder = PromptBuilder(
            context_path=str(tmp_path / "missing.json"),
            brand_path=str(brand_file)
        )
        
        task = {"action": "Create component", "tags": ["frontend"]}
        prompt = builder.build(task)
        
        assert "BRAND GUIDELINES" in prompt
        assert "#3B82F6" in prompt
    
    def test_brand_tokens_skipped_for_backend(self, tmp_path):
        """Test brand tokens NOT injected for backend tasks."""
        brand_file = tmp_path / "tokens.json"
        brand_file.write_text(json.dumps({
            "colors": {"primary": "#3B82F6"}
        }))
        
        builder = PromptBuilder(
            context_path=str(tmp_path / "missing.json"),
            brand_path=str(brand_file)
        )
        
        task = {"action": "Create API", "tags": ["backend"]}
        prompt = builder.build(task)
        
        assert "BRAND GUIDELINES" not in prompt


class TestInstructions:
    """Tests for standard instructions."""
    
    def test_instructions_always_present(self, tmp_path):
        """Test that instructions are always appended."""
        builder = PromptBuilder(
            context_path=str(tmp_path / "missing.json"),
            brand_path=str(tmp_path / "missing.json")
        )
        
        task = {"action": "Any task"}
        prompt = builder.build(task)
        
        assert "Instructions:" in prompt
        assert "Complete ONLY this single task" in prompt
        assert "RUN TESTS" in prompt
        assert "ralph_mode.md" in prompt


class TestReloadContext:
    """Tests for context reloading."""
    
    def test_reload_clears_and_reloads(self, tmp_path):
        """Test that reload_context refreshes data."""
        context_file = tmp_path / "CONTEXT.json"
        context_file.write_text(json.dumps({"version": 1}))
        
        builder = PromptBuilder(
            context_path=str(context_file),
            brand_path=str(tmp_path / "missing.json")
        )
        
        assert builder.context["version"] == 1
        
        # Update file
        context_file.write_text(json.dumps({"version": 2}))
        builder.reload_context()
        
        assert builder.context["version"] == 2
