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
"""

import json
import time
import urllib.request
import urllib.error
import sys
import re
import os
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================
CDP_PORT = 9000
TASK_FILE = ".agent/task.md"
POLL_INTERVAL_SECONDS = 3
MAX_WAIT_SECONDS = 300  # 5 minutes max per task
CONTEXT_ROTATION_THRESHOLD = 5  # Rotate context after N tasks (simplified heuristic)

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

        # Try to load global context to inject relevant sections
        try:
            context_file = SCRATCH_TASKS_JSON.replace("TASKS.json", "CONTEXT.json")
            if os.path.exists(context_file):
                with open(context_file, 'r') as cf:
                    context_data = json.load(cf)
                    
                # Inject relevant context based on task tags/scope or just simplified global context
                # For now, we inject high-level architecture and standards if the task relates to them
                if "backend" in task.get("tags", []) or "database" in task.get("tags", []):
                    prompt += f"""
**Global Data Models**: {json.dumps(context_data.get('models', {}), indent=2)}
**Architecture Standards**: {json.dumps(context_data.get('architecture', {}), indent=2)}
"""
        except Exception as e:
            pass # Fail silently on context injection, not critical

        prompt += """
Instructions:
1. Complete ONLY this single task
2. Update .agent/task.md to mark it as [x] when done
3. Report completion clearly

Follow the workflow in .agent/workflows/ralph_mode.md"""
        
        inject_prompt(ws_url, prompt)
        
        # 4. Wait for completion
        completed = wait_for_task_completion(task)
        
        if completed:
            tasks_completed += 1
            print(f"[LOOP] ✨ Task {tasks_completed} completed!")
            
            # 5. Context rotation check
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
