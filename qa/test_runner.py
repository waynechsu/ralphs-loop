"""
Test Runner Module
==================
Layer 2: Test execution and output parsing.

Runs tests and parses output for pass/fail status.
"""

import re
import shlex
import subprocess
import os
from .config import QAConfig, VerificationResult, DEFAULT_TEST_COMMANDS


def run_tests(
    task: dict,
    config: QAConfig,
    cwd: str = "."
) -> VerificationResult:
    """
    Layer 2: Execute tests and parse output for pass/fail.
    
    Args:
        task: Task dictionary
        config: QA configuration  
        cwd: Working directory for test execution
        
    Returns:
        VerificationResult with test output and failures
    """
    if not config.test_execution:
        return VerificationResult(True, "test_execution", "Skipped (disabled)", [])
    
    tags = task.get("tags", [])
    
    # Determine test command
    if "backend" in tags:
        cmd = DEFAULT_TEST_COMMANDS["backend"]
    elif "frontend" in tags:
        cmd = DEFAULT_TEST_COMMANDS["frontend"]
    else:
        cmd = DEFAULT_TEST_COMMANDS["default"]
    
    print(f"[QA] 🧪 Running tests: {cmd}")
    
    # Inject mock environment variables
    env = os.environ.copy()
    if config.mock_dependencies:
        env["MOCK_EXTERNAL_DEPENDENCIES"] = "true"
        print("[QA]    Mocking enabled (MOCK_EXTERNAL_DEPENDENCIES=true)")
    
    try:
        result = subprocess.run(
            shlex.split(cmd),
            shell=False,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
            cwd=cwd,
            env=env
        )
        
        output = result.stdout + result.stderr
        
        # Parse for failures
        failures = []
        
        failure_patterns = [
            r"FAIL\s+(.+)",
            r"AssertionError:\s*(.+)",
            r"Error:\s*(.+)",
            r"✕\s+(.+)",  # Vitest failure marker
            r"FAILED\s+(.+)",  # Pytest
        ]
        
        for pattern in failure_patterns:
            matches = re.findall(pattern, output)
            failures.extend(matches)
        
        passed = result.returncode == 0
        
        if passed:
            return VerificationResult(
                passed=True,
                layer="test_execution",
                message="All tests passed ✅",
                details=[f"Exit code: {result.returncode}"]
            )
        else:
            return VerificationResult(
                passed=False,
                layer="test_execution",
                message=f"Tests failed ({len(failures)} failure(s))",
                details=failures[:10],  # Show first 10 failures
                suggested_fix=f"Fix failing tests:\n" + "\n".join(f"  - {f}" for f in failures[:5])
            )
            
    except subprocess.TimeoutExpired:
        return VerificationResult(
            passed=False,
            layer="test_execution",
            message="Test execution timed out (>120s)",
            details=["Tests took too long to complete"],
            suggested_fix="Check for infinite loops or hanging tests"
        )
    except Exception as e:
        return VerificationResult(
            passed=False,
            layer="test_execution",
            message=f"Test execution error: {str(e)}",
            details=[str(e)],
            suggested_fix="Ensure test framework is installed and configured"
        )
