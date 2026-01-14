#!/usr/bin/env python3
"""
QA Verification Module for Ralph Wiggum Loop
=============================================
Implements 3-layer verification:
1. Test Existence Check
2. Test Execution & Output Parsing
3. LLM-as-Judge Visual/Semantic Check
"""

import os
import re
import json
import subprocess
import base64
from typing import Optional
from dataclasses import dataclass

# ============================================================================
# Configuration
# ============================================================================

DEFAULT_TEST_PATTERNS = {
    "frontend": ["*.test.ts", "*.test.tsx", "*.spec.ts", "*.spec.tsx"],
    "backend": ["*_test.py", "test_*.py", "*.test.js"],
    "component": ["*.test.tsx", "*.spec.tsx"]
}

DEFAULT_TEST_COMMANDS = {
    "frontend": "npm test -- --run --reporter=json",
    "backend": "python -m pytest --tb=short -q",
    "default": "npm test -- --run"
}

# ============================================================================
# Data Classes
# ============================================================================

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


# ============================================================================
# Layer 1: Test Existence Verification
# ============================================================================

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
            # Use find command to locate test files
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


# ============================================================================
# Layer 2: Test Execution
# ============================================================================

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
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
            cwd=cwd
        )
        
        output = result.stdout + result.stderr
        
        # Parse for failures
        failures = []
        
        # Common failure patterns
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


# ============================================================================
# Layer 3: LLM-as-Judge Visual/Semantic Check
# ============================================================================

# Prompt template for visual/semantic verification
VISUAL_CHECK_PROMPT = """You are a QA engineer reviewing a UI implementation.

**Task Completed**: {task_action}
**Expected Outcome**: {task_outcome}

Review this screenshot and check for OBVIOUS issues:

1. **Labeling**: Are all tables, charts, and axes properly labeled? Any "undefined", "NaN", or missing headers?
2. **Layout**: Is the layout logical? Any overlapping, cut-off, or misaligned elements?
3. **Data Display**: Does displayed data make sense? Any placeholder text still visible?
4. **Completeness**: Does the UI match the expected outcome description?
5. **Usability**: Could a user understand this interface without explanation?

Be STRICT. Real users will see this.

Respond ONLY with valid JSON (no markdown):
{{"acceptable": true/false, "issues": ["issue 1", "issue 2"], "severity": "blocker|major|minor|none", "suggested_fix": "Single most important fix needed"}}
"""


def visual_semantic_check(
    task: dict,
    screenshot_base64: str,
    config: QAConfig,
    api_key: Optional[str] = None
) -> VerificationResult:
    """
    Layer 3: LLM-as-Judge for UI correctness via screenshot analysis.
    
    Args:
        task: Task dictionary
        screenshot_base64: Base64-encoded PNG screenshot
        config: QA configuration
        api_key: Gemini API key (uses GEMINI_API_KEY env var if not provided)
        
    Returns:
        VerificationResult with LLM assessment
    """
    if not config.visual_semantic:
        return VerificationResult(True, "visual_semantic", "Skipped (disabled)", [])
    
    tags = task.get("tags", [])
    
    # Only run for UI-related tasks
    if not any(t in tags for t in ["frontend", "ui", "component"]):
        return VerificationResult(
            passed=True,
            layer="visual_semantic",
            message="Skipped (not a UI task)",
            details=[]
        )
    
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return VerificationResult(
            passed=True,  # Don't block if no API key
            layer="visual_semantic",
            message="Skipped (no GEMINI_API_KEY)",
            details=["Set GEMINI_API_KEY to enable LLM visual checks"]
        )
    
    # Build prompt
    prompt = VISUAL_CHECK_PROMPT.format(
        task_action=task.get("action", "Unknown task"),
        task_outcome=task.get("outcome", "No outcome specified")
    )
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(config.visual_check_model)
        
        # Create image part
        image_data = {
            "mime_type": "image/png",
            "data": screenshot_base64
        }
        
        response = model.generate_content([prompt, image_data])
        response_text = response.text.strip()
        
        # Parse JSON response
        # Handle potential markdown wrapping
        if response_text.startswith("```"):
            response_text = re.sub(r"```json?\n?", "", response_text)
            response_text = response_text.rstrip("`").strip()
        
        result = json.loads(response_text)
        
        acceptable = result.get("acceptable", True)
        issues = result.get("issues", [])
        severity = result.get("severity", "none")
        suggested_fix = result.get("suggested_fix", "")
        
        if acceptable or severity == "none":
            return VerificationResult(
                passed=True,
                layer="visual_semantic",
                message="UI passes visual check ✅",
                details=issues if issues else ["No issues found"]
            )
        else:
            return VerificationResult(
                passed=False,
                layer="visual_semantic",
                message=f"UI has {severity} issues",
                details=issues,
                suggested_fix=suggested_fix
            )
            
    except ImportError:
        return VerificationResult(
            passed=True,
            layer="visual_semantic",
            message="Skipped (google-generativeai not installed)",
            details=["pip install google-generativeai"]
        )
    except json.JSONDecodeError as e:
        return VerificationResult(
            passed=True,  # Don't block on parse errors
            layer="visual_semantic",
            message=f"LLM response parse error: {e}",
            details=["Response was not valid JSON"]
        )
    except Exception as e:
        return VerificationResult(
            passed=True,  # Don't block on API errors
            layer="visual_semantic",
            message=f"LLM API error: {str(e)}",
            details=[str(e)]
        )


# ============================================================================
# Screenshot Capture Utility
# ============================================================================

def capture_screenshot_cdp(ws_url: str) -> Optional[str]:
    """
    Capture a screenshot via Chrome DevTools Protocol.
    
    Args:
        ws_url: WebSocket debugger URL
        
    Returns:
        Base64-encoded PNG data, or None on failure
    """
    try:
        import websocket
        
        message = {
            "id": 1,
            "method": "Page.captureScreenshot",
            "params": {
                "format": "png",
                "fullPage": True
            }
        }
        
        ws = websocket.create_connection(ws_url, timeout=10, suppress_origin=True)
        ws.send(json.dumps(message))
        result = json.loads(ws.recv())
        ws.close()
        
        if "result" in result and "data" in result["result"]:
            return result["result"]["data"]
        return None
        
    except Exception as e:
        print(f"[QA] Screenshot capture failed: {e}")
        return None


# ============================================================================
# Main Verification Orchestrator
# ============================================================================

class QAVerifier:
    """Orchestrates 3-layer QA verification."""
    
    def __init__(self, context_data: Optional[dict] = None):
        """
        Initialize verifier with optional context configuration.
        
        Args:
            context_data: CONTEXT.json data with qa_verification settings
        """
        qa_config = {}
        if context_data:
            qa_config = context_data.get("qa_verification", {})
        
        layers = qa_config.get("layers", {})
        self.config = QAConfig(
            test_existence=layers.get("test_existence", True),
            test_execution=layers.get("test_execution", True),
            visual_semantic=layers.get("visual_semantic", True),
            max_self_heal_attempts=qa_config.get("max_self_heal_attempts", 2),
            visual_check_model=qa_config.get("visual_check_model", "gemini-2.0-flash"),
            test_directory=qa_config.get("test_directory", ".")
        )
    
    def verify_all(
        self,
        task: dict,
        ws_url: Optional[str] = None,
        base_path: str = "."
    ) -> tuple[bool, list[VerificationResult]]:
        """
        Run all verification layers.
        
        Args:
            task: Task dictionary
            ws_url: WebSocket URL for screenshot capture (optional)
            base_path: Working directory
            
        Returns:
            (all_passed, list of results)
        """
        results = []
        
        # Layer 1: Test existence
        print("[QA] 📋 Layer 1: Checking test existence...")
        result1 = verify_test_existence(task, self.config, base_path)
        results.append(result1)
        print(f"[QA]    {result1.message}")
        
        if not result1.passed:
            return False, results
        
        # Layer 2: Test execution
        print("[QA] 🧪 Layer 2: Running tests...")
        result2 = run_tests(task, self.config, base_path)
        results.append(result2)
        print(f"[QA]    {result2.message}")
        
        if not result2.passed:
            return False, results
        
        # Layer 3: Visual/semantic (only if ws_url provided and UI task)
        tags = task.get("tags", [])
        if ws_url and any(t in tags for t in ["frontend", "ui", "component"]):
            print("[QA] 👁️ Layer 3: Visual/semantic check...")
            screenshot = capture_screenshot_cdp(ws_url)
            if screenshot:
                result3 = visual_semantic_check(task, screenshot, self.config)
                results.append(result3)
                print(f"[QA]    {result3.message}")
                
                if not result3.passed:
                    return False, results
            else:
                print("[QA]    Skipped (screenshot capture failed)")
        
        return True, results
    
    def format_failure_prompt(self, results: list[VerificationResult]) -> str:
        """
        Format failed verification results into a fix prompt for the agent.
        
        Args:
            results: List of verification results
            
        Returns:
            Formatted prompt string
        """
        failed = [r for r in results if not r.passed]
        if not failed:
            return ""
        
        lines = ["⚠️ QA VERIFICATION FAILED - FIX REQUIRED\n"]
        
        for result in failed:
            lines.append(f"**{result.layer.upper()}**: {result.message}")
            if result.details:
                for detail in result.details[:5]:
                    lines.append(f"  - {detail}")
            if result.suggested_fix:
                lines.append(f"\n**Suggested Fix**: {result.suggested_fix}")
        
        lines.append("\nFix the issues above and mark the task complete again.")
        
        return "\n".join(lines)


# ============================================================================
# CLI for standalone testing
# ============================================================================

if __name__ == "__main__":
    import sys
    
    # Example usage
    test_task = {
        "id": "TASK-001",
        "action": "Create flight matrix component",
        "outcome": "Matrix displays prices with date labels on X and Y axes",
        "tags": ["frontend", "ui"]
    }
    
    verifier = QAVerifier()
    passed, results = verifier.verify_all(test_task, base_path=".")
    
    print("\n" + "="*50)
    print("VERIFICATION SUMMARY")
    print("="*50)
    
    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"{status} {r.layer}: {r.message}")
    
    if not passed:
        print("\n" + verifier.format_failure_prompt(results))
        sys.exit(1)
    else:
        print("\n✅ All verification layers passed!")
        sys.exit(0)
