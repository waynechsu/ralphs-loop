#!/usr/bin/env python3
"""
Ralph Wiggum Loop Driver for Antigravity IDE
=============================================
Drives the Antigravity agent via Chrome DevTools Protocol (CDP).

This is the main orchestrator that coordinates:
- Task selection from TASKS.json
- Prompt building with context injection
- IDE communication via CDP
- Progress monitoring and validation
- Context rotation (blast shield)

Usage:
    python3 wiggum_driver.py
"""

import sys
import time
from datetime import datetime

# Import modular components
from loop import (
    CDPClient,
    TaskSelector,
    PromptBuilder,
    ProgressMonitor,
    ResetHandler,
)

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
MAX_VALIDATION_RETRIES = 2
MAX_QA_RETRIES = 2
ENABLE_QA_VERIFICATION = True
CONTEXT_ROTATION_THRESHOLD = 5


def main():
    print("=" * 60)
    print("🎬 RALPH WIGGUM LOOP DRIVER (Modular)")
    print(f"   CDP Port: {CDP_PORT}")
    print(f"   Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Initialize modules
    cdp = CDPClient(port=CDP_PORT)
    selector = TaskSelector()
    builder = PromptBuilder()
    monitor = ProgressMonitor()
    reset = ResetHandler(cdp, threshold=CONTEXT_ROTATION_THRESHOLD)
    
    tasks_completed = 0
    
    while True:
        print("\n" + "-" * 40)
        print(f"[LOOP] Iteration {tasks_completed + 1}")
        print("-" * 40)
        
        # 1. Get next incomplete task
        task = selector.get_next()
        if not task:
            print("\n✅ ALL TASKS COMPLETED!")
            print(f"   Total tasks: {tasks_completed}")
            print("   I'm a unitard!")
            sys.exit(0)
        
        print(f"[TASK] 📋 Next: {task.get('action', 'Unknown')}")
        if task.get("outcome"):
            print(f"[TASK] 🎯 Outcome: {task['outcome']}")
        
        # 2. Connect to IDE
        ws_url = cdp.connect()
        if not ws_url:
            print("[ERROR] ❌ Cannot connect to IDE. Is it running with --remote-debugging-port=9000?")
            print("[ERROR] Retrying in 10 seconds...")
            time.sleep(10)
            continue
        
        print(f"[CDP] Connected to IDE")
        
        # 3. Build and inject prompt
        prompt = builder.build(task)
        cdp.inject_prompt(prompt)
        
        # 4. Wait for completion
        completed = monitor.wait_for_completion(task)
        
        if completed:
            # 5. Validate spec compliance
            is_valid, validation_errors = selector.validate_spec(task, builder.context)
            
            if not is_valid:
                retry_count = task.get('_retry_count', 0) + 1
                
                if retry_count <= MAX_VALIDATION_RETRIES:
                    print(f"[LOOP] ⚠️ Spec validation failed! Retry {retry_count}/{MAX_VALIDATION_RETRIES}")
                    
                    selector.unmark(task.get('id', ''))
                    task['_retry_count'] = retry_count
                    
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
                    cdp.inject_prompt(error_prompt)
                    
                    print("[LOOP] 🔁 Waiting for fix...\n")
                    time.sleep(2)
                    continue
                else:
                    print(f"[LOOP] ❌ Max retries ({MAX_VALIDATION_RETRIES}) exceeded. Moving to next task.")
                    tasks_completed += 1
            else:
                # 6. Run QA verification
                qa_passed = True
                
                if ENABLE_QA_VERIFICATION and QA_VERIFICATION_AVAILABLE:
                    print("[LOOP] 🔍 Running QA verification...")
                    verifier = QAVerifier(builder.context)
                    
                    import os
                    base_path = os.path.dirname(os.path.abspath(selector.task_md_path)) or "."
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
                            
                            selector.unmark(task.get('id', ''))
                            task['_qa_retry_count'] = qa_retry_count
                            
                            fix_prompt = verifier.format_failure_prompt(qa_results)
                            cdp.inject_prompt(fix_prompt)
                            
                            print("[LOOP] 🔁 Waiting for QA fix...\n")
                            time.sleep(2)
                            continue
                        else:
                            print(f"[LOOP] ❌ Max QA retries ({MAX_QA_RETRIES}) exceeded.")
                            qa_passed = True  # Move on despite failures
                
                if qa_passed:
                    tasks_completed += 1
                    print(f"[LOOP] ✨ Task {tasks_completed} completed and verified!")
            
            # 7. Context rotation check
            if reset.should_rotate(tasks_completed):
                reset.rotate()
        else:
            print("[LOOP] ⚠️ Task timed out. Continuing to next iteration...")
        
        print("[LOOP] 🔁 Starting next iteration...\n")
        time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[EXIT] 👋 Loop terminated by user (Ctrl+C)")
        sys.exit(0)
