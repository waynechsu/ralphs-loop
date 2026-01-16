"""
Unit Tests for QA Config Module
================================
Tests for qa/config.py classes.
"""

import pytest

from qa.config import QAConfig, VerificationResult, DEFAULT_TEST_PATTERNS


class TestQAConfig:
    """Tests for QAConfig class."""
    
    def test_default_values(self):
        """Test that defaults are sensible."""
        config = QAConfig()
        
        assert config.test_existence == True
        assert config.test_execution == True
        assert config.visual_semantic == True
        assert config.max_self_heal_attempts == 2
        assert config.visual_check_model == "gemini-2.0-flash"
    
    def test_from_context_empty(self):
        """Test creating from empty context."""
        config = QAConfig.from_context(None)
        
        assert config.test_existence == True
        assert config.max_self_heal_attempts == 2
    
    def test_from_context_with_data(self):
        """Test creating from full context data."""
        context = {
            "qa_verification": {
                "layers": {
                    "test_existence": False,
                    "test_execution": True,
                    "visual_semantic": False
                },
                "max_self_heal_attempts": 5,
                "visual_check_model": "gemini-1.5-pro"
            }
        }
        
        config = QAConfig.from_context(context)
        
        assert config.test_existence == False
        assert config.test_execution == True
        assert config.visual_semantic == False
        assert config.max_self_heal_attempts == 5
        assert config.visual_check_model == "gemini-1.5-pro"
    
    def test_from_context_partial(self):
        """Test creating from partial context."""
        context = {
            "qa_verification": {
                "max_self_heal_attempts": 3
            }
        }
        
        config = QAConfig.from_context(context)
        
        # Should use defaults for missing values
        assert config.test_existence == True
        assert config.max_self_heal_attempts == 3


class TestVerificationResult:
    """Tests for VerificationResult class."""
    
    def test_create_passing(self):
        """Test creating a passing result."""
        result = VerificationResult(
            passed=True,
            layer="test_execution",
            message="All tests passed",
            details=["5 tests ran"]
        )
        
        assert result.passed == True
        assert result.layer == "test_execution"
        assert result.suggested_fix is None
    
    def test_create_failing(self):
        """Test creating a failing result with fix suggestion."""
        result = VerificationResult(
            passed=False,
            layer="visual_semantic",
            message="UI has issues",
            details=["Missing label", "Wrong color"],
            suggested_fix="Add proper labels to form fields"
        )
        
        assert result.passed == False
        assert len(result.details) == 2
        assert result.suggested_fix == "Add proper labels to form fields"


class TestDefaultPatterns:
    """Tests for default test patterns."""
    
    def test_frontend_patterns_exist(self):
        """Test that frontend patterns are defined."""
        assert "frontend" in DEFAULT_TEST_PATTERNS
        assert "*.test.ts" in DEFAULT_TEST_PATTERNS["frontend"]
    
    def test_backend_patterns_exist(self):
        """Test that backend patterns are defined."""
        assert "backend" in DEFAULT_TEST_PATTERNS
        assert "test_*.py" in DEFAULT_TEST_PATTERNS["backend"]
