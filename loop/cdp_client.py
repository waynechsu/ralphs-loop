"""
CDP Client Module
=================
Handles Chrome DevTools Protocol communication for the Ralph Wiggum Loop.

Responsibilities:
- WebSocket connection management
- CDP command execution
- Target page discovery
"""

import json
import time
import urllib.request
import urllib.error
from typing import Optional


class CDPClient:
    """Chrome DevTools Protocol client for IDE automation."""
    
    def __init__(self, port: int = 9000):
        """
        Initialize CDP client.
        
        Args:
            port: CDP debugging port (default: 9000)
        """
        self.port = port
        self.ws_url: Optional[str] = None
        self._ws = None
    
    def connect(self, max_retries: int = 3, retry_delay: int = 2) -> Optional[str]:
        """
        Connect to the IDE via CDP with retries.
        
        Args:
            max_retries: Number of connection attempts
            retry_delay: Seconds between attempts
            
        Returns:
            WebSocket debugger URL if successful, None otherwise
        """
        for attempt in range(max_retries):
            try:
                pages = self._get_json(f"http://localhost:{self.port}/json")
                if pages:
                    target_page = self._find_chat_page(pages)
                    if target_page:
                        self.ws_url = target_page.get("webSocketDebuggerUrl")
                        print(f"[CDP] ✅ Connected to IDE on attempt {attempt + 1}")
                        return self.ws_url
            except Exception as e:
                print(f"[CDP] ⚠️ Connection attempt {attempt + 1}/{max_retries} failed: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                
        print(f"[CDP] ❌ Failed to connect after {max_retries} attempts")
        return None
    
    def send_command(self, method: str, params: Optional[dict] = None) -> Optional[dict]:
        """
        Send a CDP command via WebSocket.
        
        Args:
            method: CDP method name (e.g., "Runtime.evaluate")
            params: Optional parameters dict
            
        Returns:
            Response dict if successful, None otherwise
        """
        if not self.ws_url:
            print("[CDP] ⚠️ Not connected. Call connect() first.")
            return None
        
        try:
            import websocket  # type: ignore
        except ImportError:
            print("[ERROR] Missing 'websocket-client'. Run: pip install websocket-client")
            return None
        
        message = {
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        try:
            ws = websocket.create_connection(self.ws_url, timeout=10, suppress_origin=True)
            ws.send(json.dumps(message))
            result = json.loads(ws.recv())
            ws.close()
            return result
        except Exception as e:
            print(f"[CDP] ❌ WebSocket command failed: {e}")
            return None
    
    def inject_prompt(self, prompt: str) -> bool:
        """
        Inject a prompt into the Antigravity chat UI.
        
        Args:
            prompt: Text to inject into the chat input
            
        Returns:
            True if successful
        """
        print("[CDP] 💉 Injecting prompt...")
        
        # JavaScript to focus the chat input
        js_code = """
        (function() {
            const logs = [];
            function log(msg) { logs.push(msg); }

            const selectors = [
                'div.bg-ide-input-background[contenteditable="true"]',
                'div.cursor-text[contenteditable="true"]',
                'textarea[aria-label="Chat Input"]',
                '.chat-input textarea',
                '[data-testid="chat-input"]',
                '.lexical-editor [contenteditable="true"]',
                'div[contenteditable="true"]'
            ];
            
            let input = null;
            
            function findInputInDoc(root) {
                if (!root) return null;
                
                if (root.querySelector) {
                    for (const sel of selectors) {
                        const found = root.querySelector(sel);
                        if (found) return found;
                    }
                }
                
                if (root.querySelectorAll) {
                    const all = root.querySelectorAll('*');
                    for (const el of all) {
                        if (el.shadowRoot) {
                            const found = findInputInDoc(el.shadowRoot);
                            if (found) return found;
                        }
                    }
                }
                return null;
            }

            input = findInputInDoc(document);

            if (!input) {
                const frames = document.querySelectorAll('iframe');
                log("Found " + frames.length + " frames");
                for (const frame of frames) {
                    try {
                        const doc = frame.contentDocument;
                        if (doc) {
                            input = findInputInDoc(doc);
                            if (input) {
                                log("✅ Found input in iframe " + frame.id);
                                break;
                            }
                        }
                    } catch (e) {
                        log("Cross-origin iframe blocked: " + e.message);
                    }
                }
            }
            
            if (!input) {
                return { success: false, error: 'Input not found', logs: logs };
            }
            
            input.focus();
            log("✅ Input focused: " + (input.tagName || "unknown"));
            return { success: true, logs: logs };
        })();
        """
        
        result = self.send_command("Runtime.evaluate", {"expression": js_code, "returnByValue": True})
        
        if not result:
            return False
        
        value = result.get("result", {}).get("result", {}).get("value", {})
        
        if value.get("logs"):
            print("[CDP] 📝 Remote Logs:")
            for log in value["logs"]:
                print(f"      > {log}")
        
        if not value.get("success"):
            print(f"[CDP] ⚠️ Focus failed: {value.get('error')}")
            return True  # Continue anyway
        
        print("[CDP] ✅ Input element focused")
        
        # Insert text via CDP
        print("[CDP] ⌨️ Typing via CDP Input.insertText...")
        type_result = self.send_command("Input.insertText", {"text": prompt})
        if type_result:
            print("[CDP] ✅ Text inserted via CDP")
        else:
            print("[CDP] ⚠️ Input.insertText failed")
            return True
        
        # Press Enter
        time.sleep(0.2)
        print("[CDP] ⏎ Pressing Enter via CDP...")
        self.send_command("Input.dispatchKeyEvent", {
            "type": "keyDown",
            "key": "Enter",
            "code": "Enter",
            "windowsVirtualKeyCode": 13,
            "nativeVirtualKeyCode": 13
        })
        self.send_command("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "key": "Enter",
            "code": "Enter",
            "windowsVirtualKeyCode": 13,
            "nativeVirtualKeyCode": 13
        })
        print("[CDP] ✅ Enter key sent")
        return True
    
    def reload_page(self) -> bool:
        """
        Reload the page to rotate context.
        
        Returns:
            True if successful
        """
        print("[CDP] 🔄 Rotating context (Page.reload)...")
        result = self.send_command("Page.reload", {"ignoreCache": True})
        if result:
            print("[CDP] ✅ Page reloaded. Waiting for re-initialization...")
            time.sleep(5)
            return True
        return False
    
    def _get_json(self, url: str) -> Optional[list]:
        """Fetch JSON from a URL."""
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                return json.loads(response.read().decode())
        except urllib.error.URLError as e:
            print(f"[ERROR] CDP connection failed: {e}")
            return None
    
    def _find_chat_page(self, pages: list) -> Optional[dict]:
        """Heuristically find the Antigravity chat page from CDP targets."""
        for page in pages:
            title = page.get("title", "")
            if "Antigravity" in title:
                return page
        
        # Fallback to first available page
        return pages[0] if pages else None
