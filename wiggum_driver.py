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
        // Try multiple selector strategies
        const selectors = [
            'textarea[aria-label="Chat Input"]',
            '.chat-input textarea',
            '[data-testid="chat-input"]',
            '.lexical-editor [contenteditable="true"]'
        ];
        
        let input = null;
        
        // Helper to find input in a document (or shadow root)
        function findInputInDoc(doc) {{
            if (!doc) return null;
            for (const sel of selectors) {{
                const found = doc.querySelector(sel);
                if (found) return found;
            }}
            return null;
        }}

        // 1. Search Main Document
        input = findInputInDoc(document);

        // 2. Search Iframes (Deep Search for Agent Panel)
        if (!input) {{
            const frames = document.querySelectorAll('iframe');
            for (const frame of frames) {{
                try {{
                    const doc = frame.contentDocument;
                    if (doc) {{
                        input = findInputInDoc(doc);
                        if (input) {{
                            console.log("Ralph Wiggum: Found input in iframe", frame.id);
                            break;
                        }}
                    }}
                }} catch (e) {{
                    console.log("Ralph Wiggum: Cross-origin iframe blocked", e);
                }}
            }}
        }}
        
        if (!input) {{
            console.error('Ralph Wiggum: Could not find chat input in Main or Iframes');
            return {{ success: false, error: 'Input not found' }};
        }}
        
        // For contenteditable (Lexical)
        if (input.contentEditable === 'true') {{
            input.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('insertText', false, "{escaped_prompt}");
        }} else {{
            // For textarea
            input.value = "{escaped_prompt}";
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
        
        // Find and click send button
        const btnSelectors = [
            'button[aria-label="Send Message"]',
            'button[type="submit"]',
            '.send-button',
            '[data-testid="send-button"]'
        ];
        
        for (const sel of btnSelectors) {{
            const btn = document.querySelector(sel);
            if (btn) {{
                btn.click();
                return {{ success: true }};
            }}
        }}
        
        // Try pressing Enter as fallback
        input.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', bubbles: true }}));
        return {{ success: true, method: 'enter-key' }};
    }})();
    """
    
    result = send_ws_command(ws_url, "Runtime.evaluate", {"expression": js_code})
    if result and result.get("result", {}).get("result", {}).get("value", {}).get("success"):
        print(f"[CDP] ✅ Prompt injected successfully")
        return True
    else:
        print(f"[CDP] ⚠️ Injection result: {result}")
        return True  # Continue anyway for demo purposes

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
