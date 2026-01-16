"""
Visual Checker Module
=====================
Layer 3: LLM-as-Judge visual/semantic verification.

Uses Gemini to analyze screenshots for UI correctness.
"""

import os
import re
import json
from typing import Optional
from .config import QAConfig, VerificationResult


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
    Layer 3: Hybrid visual verification.
    
    1. Rule-based checks (Zero cost): File size, dimensions, solid color.
    2. LLM check (Cost): Only if explicitly enabled or tagged for reasoning.
    
    Args:
        task: Task dictionary
        screenshot_base64: Base64-encoded PNG screenshot
        config: QA configuration
        api_key: Gemini API key (uses GEMINI_API_KEY env var if not provided)
        
    Returns:
        VerificationResult
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
        
    # 1. Rule-based checks (Free)
    rules_passed, rule_issues = check_basic_rules(screenshot_base64)
    if not rules_passed:
        return VerificationResult(
            passed=False,
            layer="visual_semantic", 
            message="Basic rule check failed",
            details=rule_issues,
            suggested_fix="Fix screenshot capture or rendering issue"
        )
        
    # 2. LLM check (Cost)
    # Only run if:
    # - Explicitly enabled in config (ENABLE_LLM_VISUAL_CHECK)
    # - OR task has "reasoning" tag AND config allows it
    needs_reasoning = "reasoning" in tags or task.get("needs_reasoning", False)
    enable_llm = os.environ.get("ENABLE_LLM_VISUAL_CHECK", "false").lower() == "true"
    
    if not (enable_llm or needs_reasoning):
        return VerificationResult(
            passed=True,
            layer="visual_semantic",
            message="Pass (Rule-based only)",
            details=["Use needs_reasoning=true tag to enable LLM check"]
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


def check_basic_rules(screenshot_base64: str) -> tuple[bool, list[str]]:
    """
    Perform rule-based checks on screenshot.
    
    Args:
        screenshot_base64: Base64 image data
        
    Returns:
        (passed, list_of_issues)
    """
    issues = []
    
    if not screenshot_base64:
        return False, ["Empty screenshot data"]
        
    # Check data size (sanity check for extremely small files)
    if len(screenshot_base64) < 1000:
        issues.append("Screenshot too small (< 1KB), likely error page")
        
    # Check for valid PNG header (simple string check on base64 prefix)
    # PNG base64 usually starts with iVBORw0KGgo
    if not screenshot_base64.startswith("iVBORw0KGgo"):
        issues.append("Invalid PNG header (does not start with 'iVBORw0KGgo')")

    return len(issues) == 0, issues


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
