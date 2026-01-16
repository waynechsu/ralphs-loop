#!/usr/bin/env python3
"""
QA Verification Module for Ralph Wiggum Loop
=============================================
Orchestrates 3-layer verification using modular qa/ package.

Layers:
1. Test Existence Check (qa.schema_checker)
2. Test Execution & Output Parsing (qa.test_runner)
3. LLM-as-Judge Visual/Semantic Check (qa.visual_checker)
"""

from typing import Optional

# Import from modular qa package
from qa import (
    verify_test_existence,
    run_tests,
    visual_semantic_check,
    capture_screenshot_cdp,
    QAConfig,
    VerificationResult,
)


class QAVerifier:
    """Orchestrates 3-layer QA verification."""
    
    def __init__(self, context_data: Optional[dict] = None):
        """
        Initialize verifier with optional context configuration.
        
        Args:
            context_data: CONTEXT.json data with qa_verification settings
        """
        self.config = QAConfig.from_context(context_data)
    
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
                    success = False
            else:
                print("[QA]    Skipped (screenshot capture failed)")
                
        # Aggregate and save report
        success = all(r.passed for r in results)
        self.save_report(task, results, success, base_path)
        
        return success, results
    
    def save_report(
        self, 
        task: dict, 
        results: list[VerificationResult], 
        success: bool,
        base_path: str
    ) -> None:
        """Save QA report to JSON."""
        import json
        import os
        from datetime import datetime
        
        report_path = os.path.join(base_path, ".agent", "qa_report.json")
        
        report_entry = {
            "task_id": task.get("id"),
            "timestamp": datetime.now().isoformat(),
            "overall_status": "passed" if success else "failed",
            "layers": [
                {
                    "layer": r.layer,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details
                }
                for r in results
            ]
        }
        
        try:
            reports = []
            if os.path.exists(report_path):
                with open(report_path, 'r') as f:
                    try:
                        reports = json.load(f)
                        if not isinstance(reports, list):
                            reports = []
                    except json.JSONDecodeError:
                        pass
            
            # Append new report
            reports.append(report_entry)
            
            with open(report_path, 'w') as f:
                json.dump(reports, f, indent=2)
                
        except Exception as e:
            print(f"[QA] ⚠️ Failed to save report: {e}")
    
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


# CLI for standalone testing
if __name__ == "__main__":
    import sys
    
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
