"""
QA Configuration Module
=======================
Shared configuration and data classes for QA verification.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class VerificationResult:
    """Result of a verification layer."""
    passed: bool
    layer: str
    message: str
    details: list[str]
    suggested_fix: Optional[str] = None


@dataclass
class QAConfig:
    """QA verification configuration."""
    test_existence: bool = True
    test_execution: bool = True
    visual_semantic: bool = True
    max_self_heal_attempts: int = 2
    visual_check_model: str = "gemini-2.0-flash"
    test_directory: str = "."
    
    @classmethod
    def from_context(cls, context_data: Optional[dict] = None) -> "QAConfig":
        """Create QAConfig from CONTEXT.json data."""
        if not context_data:
            return cls()
        
        qa_config = context_data.get("qa_verification", {})
        layers = qa_config.get("layers", {})
        
        return cls(
            test_existence=layers.get("test_existence", True),
            test_execution=layers.get("test_execution", True),
            visual_semantic=layers.get("visual_semantic", True),
            max_self_heal_attempts=qa_config.get("max_self_heal_attempts", 2),
            visual_check_model=qa_config.get("visual_check_model", "gemini-2.0-flash"),
            test_directory=qa_config.get("test_directory", ".")
        )


# Default test patterns by project type
DEFAULT_TEST_PATTERNS = {
    "frontend": ["*.test.ts", "*.test.tsx", "*.spec.ts", "*.spec.tsx"],
    "backend": ["*_test.py", "test_*.py", "*.test.js"],
    "component": ["*.test.tsx", "*.spec.tsx"]
}

# Default test commands by project type
DEFAULT_TEST_COMMANDS = {
    "frontend": "npm test -- --run --reporter=json",
    "backend": "python -m pytest --tb=short -q",
    "default": "npm test -- --run"
}
