"""
QA Verification Package
=======================
Modular QA verification for the Ralph Wiggum Loop.

Modules:
- schema_checker: Test existence verification
- test_runner: Test execution and output parsing
- visual_checker: LLM-as-Judge visual/semantic check
"""

from .schema_checker import verify_test_existence
from .test_runner import run_tests
from .visual_checker import visual_semantic_check, capture_screenshot_cdp
from .config import QAConfig, VerificationResult

__all__ = [
    "verify_test_existence",
    "run_tests",
    "visual_semantic_check",
    "capture_screenshot_cdp",
    "QAConfig",
    "VerificationResult",
]
