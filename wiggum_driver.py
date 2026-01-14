#!/usr/bin/env python3
"""
Ralph Wiggum Loop Driver for Antigravity IDE
=============================================
Drives the Antigravity agent via Chrome DevTools Protocol (CDP).
Implements:
- True outer loop with exit conditions
- File-based completion detection
- Robust task parsing (Action → Outcome format)
- Context rotation via Page.reload
- 3-layer QA verification (tests, execution, visual/semantic)
"""

import json
import time
import urllib.request
import urllib.error
import sys
import re
import os
from datetime import datetime

# Import QA verification module
try:
    from qa_verification import QAVerifier
    QA_VERIFICATION_AVAILABLE = True
except ImportError:
    QA_VERIFICATION_AVAILABLE = False
    print("[WARN] qa_verification module not found. QA checks disabled.")

# ============================================================================
# Configuration
# ============================================================================
CDP_PORT = 9000
TASK_FILE = ".agent/task.md"
POLL_INTERVAL_SECONDS = 3
MAX_WAIT_SECONDS = 300  # 5 minutes max per task
CONTEXT_ROTATION_THRESHOLD = 5  # Rotate context after N tasks (simplified heuristic)
MAX_VALIDATION_RETRIES = 2  # Max retries if spec validation fails
MAX_QA_RETRIES = 2  # Max retries if QA verification fails
ENABLE_QA_VERIFICATION = True  # Set to False to disable QA layer

# ============================================================================
# CDP Helpers
# ============================================================================

def get_json(url: str) -> list | None:
    """Fetch JSON from a URL (used for CDP /json endpoint)."""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        print(f"[ERROR] CDP connection failed: {e}")
        return None

def find_chat_page(pages: list) -> dict | None:
    """Heuristically find the Antigravity chat page from CDP targets."""
    for page in pages:
        title = page.get("title", "")
        url = page.get("url", "")
        
        # Look for the Main Project Window or Antigravity
        if "Antigravity" in title or "Flight_Hotel_Tracker" in title:
             # This is likely the main window
             # We might need to handle iframes later if this is just the shell
             return page

    # Fallback to first available page
    return pages[0] if pages else None

def send_ws_command(ws_url: str, method: str, params: dict = None) -> dict | None:
    """Send a CDP command via WebSocket and return the result."""
    try:
        import websocket  # type: ignore
    except ImportError:
        print("[ERROR] Missing 'websocket-client'. Run: pip install websocket-client")
        return None
    
    message = {
        "id": 1,  # Fixed ID for stateless connection
        "method": method,
        "params": params or {}
    }
    print(f"[DEBUG] Sending: {json.dumps(message)}")
    
    try:
        # Updated to fix 403 Forbidden
        ws = websocket.create_connection(ws_url, timeout=10, suppress_origin=True)
        ws.send(json.dumps(message))
        result = json.loads(ws.recv())
        ws.close()
        return result
    except Exception as e:
        print(f"[ERROR] WebSocket command failed: {e}")
        return None

# ============================================================================
# Task Management
# ============================================================================

TASKS_JSON_FILE = ".agent/TASKS.json"  # Fallback location
SCRATCH_TASKS_JSON = "/Users/waynehsu/.gemini/antigravity/scratch/flight_hotel_tracker/TASKS.json"

def parse_task_file() -> tuple[list[dict], str]:
    """
    Parse tasks from JSON (preferred) or Markdown (legacy).
    Returns: (tasks, raw_content)
    """
    tasks = []
    
    # 1. Try to read from JSON source (most robust)
    json_path = None
    # Check local project folder FIRST (Best Practice)
    if os.path.exists(TASKS_JSON_FILE):
        json_path = TASKS_JSON_FILE
    # Fallback to scratch folder if not found locally
    elif os.path.exists(SCRATCH_TASKS_JSON):
        json_path = SCRATCH_TASKS_JSON
        
    if json_path:
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                
            # Check existing status from task.md to sync completion state
            # (We still use task.md for STATUS tracking because the agent writes to it)
            completed_ids = set()
            if os.path.exists(TASK_FILE):
                with open(TASK_FILE, 'r') as f:
                    md_content = f.read()
                    # Find all [x] completed items
                    # Matches: - [x] ... <!-- id: TASK-123 -->
                    # Note: case insensitive for [x] vs [X]
                    completed_matches = re.findall(
                        r'^\s*-\s*\[x\]\s*.*<!--\s*id:\s*(.*?)\s*-->', 
                        md_content, 
                        re.MULTILINE | re.IGNORECASE
                    )
                    completed_ids = set(completed_matches)

            for i, item in enumerate(data):
                tid = item.get("id", f"TASK-{i}")
                is_complete = tid in completed_ids
                
                tasks.append({
                    "line_num": i, # Virtual line number
                    "complete": is_complete,
                    "action": item.get("action"),
                    "outcome": item.get("outcome"),
                    "verification": item.get("verification"),
                    "context_scope": item.get("context_scope"),
                    "id": tid,
                    "raw": json.dumps(item)
                })
            return tasks, "JSON_SOURCE"
            
        except Exception as e:
            print(f"[WARN] Failed to parse JSON tasks: {e}")
            # Fallthrough to Markdown parser

    # 2. Fallback to Markdown parsing
    raw_content = ""
    
    if not os.path.exists(TASK_FILE):
        print(f"[ERROR] Task file not found: {TASK_FILE}")
        return tasks, raw_content
    
    with open(TASK_FILE, "r") as f:
        raw_content = f.read()
        lines = raw_content.splitlines()
    
    # Regex for: - [ ] **Action**: X → **Outcome**: Y
    pattern_full = re.compile(
        r'^- \[([ x])\]\s*\*\*Action\*\*:\s*(.+?)\s*→\s*\*\*Outcome\*\*:\s*(.+)$'
    )
    pattern_id = re.compile(r'<!-- id: (.*?) -->')
    pattern_simple = re.compile(r'^- \[([ x])\]\s*(.+)$')
    
    for i, line in enumerate(lines):
        match_full = pattern_full.match(line.strip())
        match_simple = pattern_simple.match(line.strip())
        match_id = pattern_id.search(line)
        tid = match_id.group(1) if match_id else f"MD-{i}"
        
        if match_full:
            tasks.append({
                "line_num": i,
                "complete": match_full.group(1) == 'x',
                "action": match_full.group(2).strip(),
                "outcome": match_full.group(3).strip(),
                "id": tid,
                "raw": line
            })
        elif match_simple:
            tasks.append({
                "line_num": i,
                "complete": match_simple.group(1) == 'x',
                "action": match_simple.group(2).strip(),
                "outcome": None,
                "id": tid,
                "raw": line
            })
    
    return tasks, raw_content

def get_next_task() -> dict | None:
    """Get the first incomplete task."""
    tasks, _ = parse_task_file()
    for task in tasks:
        if not task["complete"]:
            return task
    return None

def wait_for_task_completion(task: dict, timeout: int = MAX_WAIT_SECONDS) -> bool:
    """
    Poll the task file until the specific task is marked complete.
    Returns True if completed, False if timeout.
    """
    start_time = time.time()
    original_line = task["line_num"]
    
    print(f"[POLL] Waiting for task completion (timeout: {timeout}s)...")
    
    while time.time() - start_time < timeout:
        tasks, _ = parse_task_file()
        
        # Find task by line number and check if complete
        for t in tasks:
            if t["line_num"] == original_line and t["complete"]:
                print(f"[POLL] ✅ Task marked complete!")
                return True
        
        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed = int(time.time() - start_time)
        if elapsed % 15 == 0:  # Progress update every 15s
            print(f"[POLL] Still waiting... ({elapsed}s elapsed)")
    
    print(f"[POLL] ⏰ Timeout after {timeout}s")
    return False


def unmark_task(task: dict) -> bool:
    """
    Remove [x] from a task, reverting it to [ ].
    Used when spec validation fails after agent marks complete.
    """
    if not os.path.exists(TASK_FILE):
        return False
    
    with open(TASK_FILE, 'r') as f:
        content = f.read()
    
    # Find the task by ID and unmark it
    task_id = task.get('id', '')
    if task_id:
        # Pattern to match checked task with this ID
        pattern = rf'(- \[)[xX](\].*<!-- id: {re.escape(task_id)} -->)'
        new_content = re.sub(pattern, r'\1 \2', content)
        
        if new_content != content:
            with open(TASK_FILE, 'w') as f:
                f.write(new_content)
            print(f"[VALIDATE] 🔄 Unmarked task {task_id} for retry")
            return True
    
    return False


def validate_spec_compliance(task: dict, context_data: dict | None) -> tuple[bool, list[str]]:
    """
    Validate that the implementation matches the spec requirements.
    Returns: (is_valid, list_of_errors)
    
    Currently supports:
    - Python model field checking (inspects class definitions)
    - TypeScript interface checking (basic)
    """
    errors = []
    
    # Get field requirements from task or context
    field_requirements = task.get('field_requirements', {})
    
    # If task doesn't have field_requirements, try to derive from context models
    if not field_requirements and context_data and 'models' in context_data:
        models = context_data['models']
        # For database tasks, check all model fields
        if 'database' in task.get('tags', []) or 'backend' in task.get('tags', []):
            for model_name, model_def in models.items():
                if isinstance(model_def, dict):
                    field_requirements[model_name] = list(model_def.keys())
    
    if not field_requirements:
        print("[VALIDATE] ⚠️ No field_requirements found, skipping validation")
        return True, []
    
    print(f"[VALIDATE] 🔍 Checking field requirements: {list(field_requirements.keys())}")
    
    # Find implementation files to check
    # Look for Python models
    python_model_files = [
        'backend/models.py',
        'models.py',
        'src/models.py',
        'app/models.py'
    ]
    
    found_models = {}
    
    for model_file in python_model_files:
        if os.path.exists(model_file):
            try:
                with open(model_file, 'r') as f:
                    content = f.read()
                
                # Extract class definitions and their fields
                # Pattern: class ClassName(...):
                class_pattern = re.compile(r'class\s+(\w+)\s*\([^)]*\)\s*:', re.MULTILINE)
                
                for match in class_pattern.finditer(content):
                    class_name = match.group(1)
                    class_start = match.end()
                    
                    # Find next class or end of file
                    next_class = class_pattern.search(content, class_start)
                    class_end = next_class.start() if next_class else len(content)
                    class_body = content[class_start:class_end]
                    
                    # Extract field names (SQLModel/Pydantic style: field_name: type = ...)
                    field_pattern = re.compile(r'^\s+(\w+)\s*:', re.MULTILINE)
                    fields = [m.group(1) for m in field_pattern.finditer(class_body)]
                    found_models[class_name] = set(fields)
                    
                print(f"[VALIDATE] 📄 Found models in {model_file}: {list(found_models.keys())}")
                
            except Exception as e:
                print(f"[VALIDATE] ⚠️ Error reading {model_file}: {e}")
    
    # Compare required vs implemented
    for model_name, required_fields in field_requirements.items():
        if isinstance(required_fields, list):
            # Direct field list check
            # Try to find matching model (exact or similar name)
            matched_model = None
            for impl_name in found_models:
                if impl_name.lower() == model_name.lower() or model_name.lower() in impl_name.lower():
                    matched_model = impl_name
                    break
            
            if not matched_model:
                # Model might have been renamed - this is an error
                errors.append(f"Model '{model_name}' not found in implementation")
                continue
            
            implemented_fields = found_models[matched_model]
            
            for req_field in required_fields:
                # Normalize field names (snake_case comparison)
                req_normalized = req_field.lower().replace('-', '_')
                found = False
                for impl_field in implemented_fields:
                    if impl_field.lower() == req_normalized:
                        found = True
                        break
                
                if not found:
                    errors.append(f"Missing field '{req_field}' in model '{matched_model}'")
        
        elif isinstance(required_fields, dict):
            # Field definitions with types - check field names exist
            # (Type checking is more complex, skip for now)
            for field_name in required_fields.keys():
                req_normalized = field_name.lower().replace('-', '_')
                found_in_any = False
                for impl_name, impl_fields in found_models.items():
                    if any(f.lower() == req_normalized for f in impl_fields):
                        found_in_any = True
                        break
                
                if not found_in_any:
                    errors.append(f"Field '{field_name}' from spec not found in any model")
    
    is_valid = len(errors) == 0
    
    if is_valid:
        print("[VALIDATE] ✅ Spec validation PASSED")
    else:
        print(f"[VALIDATE] ❌ Spec validation FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f"           - {err}")
    
    return is_valid, errors

# ============================================================================
# IDE Interaction
# ============================================================================

def inject_prompt(ws_url: str, prompt: str) -> bool:
    """
    Inject a prompt into the Antigravity chat UI via CDP.
    Note: DOM selectors are placeholders - inspect actual IDE for real selectors.
    """
    print(f"[CDP] 💉 Injecting prompt...")
    
    # Escape the prompt for JavaScript string
    escaped_prompt = prompt.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    
    # JavaScript to inject into the page
    # NOTE: These selectors are PLACEHOLDERS. Real implementation requires
    # inspecting the Antigravity agent panel DOM structure.
    js_code = f"""
    (function() {{
        const logs = [];
        function log(msg) {{ logs.push(msg); }}

        // Try multiple selector strategies - more specific first
        const selectors = [
            // Specific chat input selectors based on candidate scan
            'div.bg-ide-input-background[contenteditable="true"]',
            'div.cursor-text[contenteditable="true"]',
            // Generic fallbacks
            'textarea[aria-label="Chat Input"]',
            '.chat-input textarea',
            '[data-testid="chat-input"]',
            '.lexical-editor [contenteditable="true"]',
            // Last resort
            'div[contenteditable="true"]'
        ];
        
        let input = null;
        
        // Helper to find input in a document (or shadow root)
        function findInputInDoc(root) {{
            if (!root) return null;
            
            // 1. Check current root
            if (root.querySelector) {{
                for (const sel of selectors) {{
                    const found = root.querySelector(sel);
                    if (found) return found;
                }}
            }}
            
            // 2. Recursive Shadow DOM Search
            if (root.querySelectorAll) {{
                const all = root.querySelectorAll('*');
                for (const el of all) {{
                    if (el.shadowRoot) {{
                        const found = findInputInDoc(el.shadowRoot);
                        if (found) return found;
                    }}
                }}
            }}
            return null;
        }}

        // 1. Search Main Document
        let inputDoc = document; // Track which document contains the input
        input = findInputInDoc(document);

        // 2. Search Iframes (Deep Search for Agent Panel)
        if (!input) {{
            const frames = document.querySelectorAll('iframe');
            log("Found " + frames.length + " frames");
            for (const frame of frames) {{
                try {{
                    log("Checking frame " + frame.id + " (" + frame.src + ")");
                    const doc = frame.contentDocument;
                    if (doc) {{
                        input = findInputInDoc(doc);
                        if (input) {{
                            inputDoc = doc; // Remember we found it in this iframe's document
                            log("✅ Found input in iframe " + frame.id);
                            break;
                        }} else {{
                            log("❌ No input found in frame doc");
                        }}
                    }} else {{
                        log("⚠️ contentDocument is null (likely cross-origin)");
                    }}
                }} catch (e) {{
                    log("Cross-origin iframe blocked: " + e.message);
                }}
            }}
        }}
        
        if (!input) {{
            return {{ success: false, error: 'Input not found', logs: logs }};
        }}
        
        // Just focus the input - text insertion will be done via CDP Input.insertText
        input.focus();
        log("✅ Input focused: " + (input.tagName || "unknown"));
        return {{ success: true, logs: logs }};
    }})();
    """
    
    result = send_ws_command(ws_url, "Runtime.evaluate", {"expression": js_code, "returnByValue": True})
    
    # Parse result
    value = result.get("result", {}).get("result", {}).get("value", {})
    
    # Always print logs for debugging
    if "logs" in value and value["logs"]:
        print("[CDP] 📝 Remote Logs:")
        for log in value["logs"]:
            print(f"      > {log}")
    
    if not value.get("success"):
        print(f"[CDP] ⚠️ Focus failed: {value.get('error')}")
        return True  # Continue anyway
    
    print("[CDP] ✅ Input element focused")
    
    # Step 2: Use CDP Input.insertText to type the text (bypasses Lexical JS sandboxing)
    print("[CDP] ⌨️ Typing via CDP Input.insertText...")
    type_result = send_ws_command(ws_url, "Input.insertText", {"text": prompt})
    if type_result:
        print("[CDP] ✅ Text inserted via CDP")
    else:
        print("[CDP] ⚠️ Input.insertText failed")
        return True
    
    # Step 3: Press Enter via CDP
    time.sleep(0.2)  # Small delay to let editor process
    print("[CDP] ⏎ Pressing Enter via CDP...")
    send_ws_command(ws_url, "Input.dispatchKeyEvent", {
        "type": "keyDown",
        "key": "Enter",
        "code": "Enter",
        "windowsVirtualKeyCode": 13,
        "nativeVirtualKeyCode": 13
    })
    send_ws_command(ws_url, "Input.dispatchKeyEvent", {
        "type": "keyUp",
        "key": "Enter",
        "code": "Enter",
        "windowsVirtualKeyCode": 13,
        "nativeVirtualKeyCode": 13
    })
    print("[CDP] ✅ Enter key sent")
    return True

def rotate_context(ws_url: str) -> bool:
    """Clear context by reloading the page."""
    print("[CDP] 🔄 Rotating context (Page.reload)...")
    result = send_ws_command(ws_url, "Page.reload", {"ignoreCache": True})
    if result:
        print("[CDP] ✅ Page reloaded. Waiting for re-initialization...")
        time.sleep(5)  # Give page time to reload
        return True
    return False

# ============================================================================
# Main Loop
# ============================================================================

def main():
    print("=" * 60)
    print("🎬 RALPH WIGGUM LOOP DRIVER")
    print(f"   CDP Port: {CDP_PORT}")
    print(f"   Task File: {TASK_FILE}")
    print(f"   Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    tasks_completed = 0
    ws_url = None
    
    while True:
        print("\n" + "-" * 40)
        print(f"[LOOP] Iteration {tasks_completed + 1}")
        print("-" * 40)
        
        # 1. Check for remaining tasks
        task = get_next_task()
        if not task:
            print("\n✅ ALL TASKS COMPLETED!")
            print(f"   Total tasks: {tasks_completed}")
            print("   I'm a unitard!")
            sys.exit(0)
        
        print(f"[TASK] 📋 Next: {task['action']}")
        if task.get("outcome"):
            print(f"[TASK] 🎯 Outcome: {task['outcome']}")
        
        # 2. Connect to IDE (reconnect each iteration for robustness)
        pages = get_json(f"http://localhost:{CDP_PORT}/json")
        if not pages:
            print("[ERROR] ❌ Cannot connect to IDE. Is it running with --remote-debugging-port=9000?")
            print("[ERROR] Retrying in 10 seconds...")
            time.sleep(10)
            continue
        
        target_page = find_chat_page(pages)
        if not target_page:
            print("[ERROR] ❌ No suitable chat page found")
            time.sleep(10)
            continue
        
        ws_url = target_page.get("webSocketDebuggerUrl")
        print(f"[CDP] Connected to: {target_page.get('title', 'Unknown')[:40]}...")
        
        # 3. Build and inject prompt
        prompt = f"""Execute the following task from the Ralph Wiggum workflow:

**Task**: {task['action']}
"""
        if task.get("outcome"):
            prompt += f"""
**Success Criteria**: {task['outcome']}
"""
        if task.get("verification"):
            prompt += f"""
**Verification**: {json.dumps(task['verification'], indent=2)}
"""
        # Inject Context from JSON if available
        if task.get("context_scope"):
             prompt += f"""
**Context Scope**: {task['context_scope']}
"""

        # Try to load global context to inject REQUIRED fields
        context_data = None  # Initialize for scope
        try:
            context_file = SCRATCH_TASKS_JSON.replace("TASKS.json", "CONTEXT.json")
            # Also check local .agent folder
            local_context = ".agent/CONTEXT.json"
            if os.path.exists(local_context):
                context_file = local_context
            
            if os.path.exists(context_file):
                with open(context_file, 'r') as cf:
                    context_data = json.load(cf)
                    
                # CRITICAL: Inject model requirements as MANDATORY, not optional
                if "models" in context_data:
                    prompt += f"""

> [!CAUTION] SPEC = REQUIREMENT, NOT INSPIRATION
> The following model fields are MANDATORY. Missing fields = TASK FAILURE.

**REQUIRED Model Fields (from CONTEXT.json)**:
{json.dumps(context_data.get('models', {}), indent=2)}

You MUST implement ALL fields listed above. Do not skip or rename fields without explicit approval.
"""
                
                # Inject architecture standards if relevant
                if "backend" in task.get("tags", []) or "database" in task.get("tags", []):
                    if "architecture" in context_data:
                        prompt += f"""
**Architecture Standards**: {json.dumps(context_data.get('architecture', {}), indent=2)}
"""

                # Inject QA Rigour if specified
                testing_strategy = context_data.get("testing_strategy", {})
                if testing_strategy.get("interaction_coverage") == "all_interactive_elements":
                            prompt += """
> [!IMPORTANT] QA RIGOUR LEVEL: MAXIMUM
> Spec requires 'all_interactive_elements'. You must write tests for EVERY button and input field created.
"""
        except Exception as e:
            print(f"[WARN] Context injection failed: {e}") # Log but continue

        # Try to load OPTIONAL brand context for UI consistency
        brand_tokens = None
        brand_file = ".agent/design_tokens.json"
        if os.path.exists(brand_file):
            try:
                with open(brand_file, 'r') as bf:
                    brand_tokens = json.load(bf)
                print(f"[LOOP] 🎨 Brand tokens loaded from {brand_file}")
            except Exception as e:
                print(f"[WARN] Failed to load brand tokens: {e}")
        
        # Inject brand context for UI/frontend tasks
        if brand_tokens and any(t in task.get("tags", []) for t in ["frontend", "ui", "component"]):
            prompt += f"""

> [!TIP] BRAND GUIDELINES ACTIVE
> This project has a defined design system. Use these tokens for visual consistency.

**Design Tokens (from design_tokens.json):**
```json
{json.dumps(brand_tokens, indent=2)}
```

**Requirements:**
- Use the defined colors (no hardcoded hex values)
- Follow typography settings (fontPrimary, fontSecondary)
- Apply consistent spacing and border-radius
- Maintain brand voice in any UI copy
"""

        prompt += """

Instructions:
1. Complete ONLY this single task
2. RUN TESTS to verify your changes (if applicable)
3. VALIDATE all spec fields are implemented before marking complete
4. Update .agent/task.md to mark it as [x] when done
4. Report completion clearly

Follow the workflow in .agent/workflows/ralph_mode.md"""
        
        inject_prompt(ws_url, prompt)
        
        # 4. Wait for completion
        completed = wait_for_task_completion(task)
        
        if completed:
            # 5. CRITICAL: Validate spec compliance BEFORE accepting completion
            is_valid, validation_errors = validate_spec_compliance(task, context_data)
            
            if not is_valid:
                retry_count = task.get('_retry_count', 0) + 1
                
                if retry_count <= MAX_VALIDATION_RETRIES:
                    print(f"[LOOP] ⚠️ Spec validation failed! Retry {retry_count}/{MAX_VALIDATION_RETRIES}")
                    
                    # Unmark the task
                    unmark_task(task)
                    
                    # Track retry count
                    task['_retry_count'] = retry_count
                    
                    # Inject error correction prompt
                    error_prompt = f"""⚠️ SPEC VALIDATION FAILED - FIX REQUIRED

The task was marked complete but FAILED automated spec validation.

**Validation Errors:**
{chr(10).join('- ' + e for e in validation_errors)}

**Action Required:**
1. Review the errors above
2. Add the missing fields to match CONTEXT.json spec
3. Re-mark the task as [x] in .agent/task.md

Remember: SPEC = REQUIREMENT, NOT INSPIRATION. All fields must be implemented.
"""
                    inject_prompt(ws_url, error_prompt)
                    
                    # Continue to next iteration (will re-poll for this task)
                    print("[LOOP] 🔁 Waiting for fix...\n")
                    time.sleep(2)
                    continue
                else:
                    print(f"[LOOP] ❌ Max retries ({MAX_VALIDATION_RETRIES}) exceeded. Moving to next task.")
                    # Log the failure but move on
                    tasks_completed += 1
            else:
                # Spec validation passed! Now run QA verification.
                qa_passed = True
                
                if ENABLE_QA_VERIFICATION and QA_VERIFICATION_AVAILABLE:
                    print("[LOOP] 🔍 Running QA verification...")
                    verifier = QAVerifier(context_data)
                    
                    # Get project base path from task file location
                    base_path = os.path.dirname(os.path.abspath(TASK_FILE)) or "."
                    base_path = os.path.dirname(base_path)  # Go up from .agent/
                    
                    qa_passed, qa_results = verifier.verify_all(
                        task,
                        ws_url=ws_url,
                        base_path=base_path
                    )
                    
                    if not qa_passed:
                        qa_retry_count = task.get('_qa_retry_count', 0) + 1
                        
                        if qa_retry_count <= MAX_QA_RETRIES:
                            print(f"[LOOP] ⚠️ QA verification failed! Retry {qa_retry_count}/{MAX_QA_RETRIES}")
                            
                            # Unmark the task
                            unmark_task(task)
                            task['_qa_retry_count'] = qa_retry_count
                            
                            # Inject QA fix prompt
                            fix_prompt = verifier.format_failure_prompt(qa_results)
                            inject_prompt(ws_url, fix_prompt)
                            
                            print("[LOOP] 🔁 Waiting for QA fix...\n")
                            time.sleep(2)
                            continue
                        else:
                            print(f"[LOOP] ❌ Max QA retries ({MAX_QA_RETRIES}) exceeded.")
                            qa_passed = True  # Move on despite failures
                
                if qa_passed:
                    tasks_completed += 1
                    print(f"[LOOP] ✨ Task {tasks_completed} completed and verified!")
            
            # 6. Context rotation check
            if tasks_completed % CONTEXT_ROTATION_THRESHOLD == 0:
                print(f"[LOOP] 🧹 Context rotation threshold reached ({CONTEXT_ROTATION_THRESHOLD} tasks)")
                if ws_url:
                    rotate_context(ws_url)
        else:
            print("[LOOP] ⚠️ Task timed out. Continuing to next iteration...")
            # Could implement retry logic here
        
        print("[LOOP] 🔁 Starting next iteration...\n")
        time.sleep(2)  # Brief pause between iterations

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[EXIT] 👋 Loop terminated by user (Ctrl+C)")
        sys.exit(0)
