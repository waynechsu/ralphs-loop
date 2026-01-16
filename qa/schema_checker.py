"""
Schema Checker Module
=====================
Layer 1: Test existence verification.

Checks if test files exist for the task scope.
"""

import subprocess
from .config import QAConfig, VerificationResult, DEFAULT_TEST_PATTERNS


def verify_test_existence(
    task: dict, 
    config: QAConfig,
    base_path: str = "."
) -> VerificationResult:
    """
    Layer 1: Check if test files exist for the task scope.
    
    Args:
        task: Task dictionary with 'tags', 'action', 'id'
        config: QA configuration
        base_path: Root directory to search
        
    Returns:
        VerificationResult with pass/fail and details
    """
    if not config.test_existence:
        return VerificationResult(True, "test_existence", "Skipped (disabled)", [])
    
    tags = task.get("tags", [])
    action = task.get("action", "").lower()
    task_id = task.get("id", "unknown")
    
    # Determine what type of tests we're looking for
    test_types = []
    if "frontend" in tags or "ui" in tags or "component" in action:
        test_types.append("frontend")
    if "backend" in tags or "api" in tags or "database" in action:
        test_types.append("backend")
    if not test_types:
        test_types = ["frontend"]  # Default assumption
    
    # Search for test files
    found_tests = []
    missing_areas = []
    
    for test_type in test_types:
        patterns = DEFAULT_TEST_PATTERNS.get(test_type, DEFAULT_TEST_PATTERNS["frontend"])
        type_tests = []
        
        for pattern in patterns:
            try:
                result = subprocess.run(
                    ["find", base_path, "-name", pattern, "-type", "f"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.stdout.strip():
                    type_tests.extend(result.stdout.strip().split("\n"))
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        
        if type_tests:
            found_tests.extend(type_tests)
        else:
            missing_areas.append(test_type)
    
    if missing_areas:
        return VerificationResult(
            passed=False,
            layer="test_existence",
            message=f"No test files found for: {', '.join(missing_areas)}",
            details=[f"Task {task_id} requires tests for {missing_areas}"],
            suggested_fix=f"Create test files for {missing_areas}. Example: {task_id.lower()}.test.ts"
        )
    
    return VerificationResult(
        passed=True,
        layer="test_existence",
        message=f"Found {len(found_tests)} test file(s)",
        details=found_tests[:5]  # Show first 5
    )
