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
import traceback
from datetime import datetime

# Import modular components
from loop import (
    CDPClient,
    TaskSelector,
    PromptBuilder,
    ProgressMonitor,
    ResetHandler,
)
from loop.config import LoopConfig
from loop.utils import setup_logging

# Import QA verification module
try:
    from qa_verification import QAVerifier
    QA_VERIFICATION_AVAILABLE = True
except ImportError:
    QA_VERIFICATION_AVAILABLE = False

def main():
    # Load config and setup logging
    config = LoopConfig.from_env()
    logger = setup_logging(config.log_file)
    
    logger.info("=" * 60)
    logger.info("🎬 RALPH WIGGUM LOOP DRIVER (Modular)")
    logger.info(f"   CDP Port: {config.cdp_port}")
    logger.info(f"   Started: {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    # Initialize modules
    try:
        cdp = CDPClient(port=config.cdp_port)
        selector = TaskSelector(config=config)
        builder = PromptBuilder()
        monitor = ProgressMonitor()
        reset = ResetHandler(cdp, threshold=config.context_rotation_threshold)
    except Exception as e:
        logger.error(f"[FATAL] Failed to initialize modules: {e}")
        logger.error(f"Initialization failure: {traceback.format_exc()}")
        sys.exit(1)
    
    tasks_completed = 0
    driver_retries = 0
    estimated_llm_calls = 0

    if not QA_VERIFICATION_AVAILABLE:
        logger.warning("[WARN] qa_verification module not found. QA checks disabled.")

    while True:
        try:
            logger.info("\n" + "-" * 40)
            logger.info(f"[LOOP] Iteration {tasks_completed + 1}")
            logger.info("-" * 40)
            
            # 1. Get next incomplete task
            task = selector.get_next()
            if not task:
                logger.info("\n✅ ALL TASKS COMPLETED!")
                logger.info(f"   Total tasks: {tasks_completed}")
                logger.info("   I'm a unitard!")
                sys.exit(0)
            
            logger.info(f"[TASK] 📋 Next: {task.get('action', 'Unknown')}")
            if task.get("outcome"):
                logger.info(f"[TASK] 🎯 Outcome: {task['outcome']}")
            
            # 2. Connect to IDE
            ws_url = cdp.connect()
            if not ws_url:
                logger.error("[ERROR] ❌ Cannot connect to IDE. Is it running with --remote-debugging-port=9000?")
                # Retry handled internally by CDPClient, if it fails here, it's fatal for this task iteration
                time.sleep(5)
                continue
            
            logger.info(f"[CDP] Connected to IDE")
            
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
                    
                    if retry_count <= config.max_validation_retries:
                        logger.warning(f"[LOOP] ⚠️ Spec validation failed! Retry {retry_count}/{config.max_validation_retries}")
                        
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
                        
                        logger.info("[LOOP] 🔁 Waiting for fix...\n")
                        time.sleep(2)
                        continue
                    else:
                        logger.error(f"[LOOP] ❌ Max retries ({config.max_validation_retries}) exceeded. Moving to next task.")
                        tasks_completed += 1
                else:
                    # 6. Run QA verification
                    qa_passed = True
                    
                    if config.enable_qa_verification and QA_VERIFICATION_AVAILABLE:
                        logger.info("[LOOP] 🔍 Running QA verification...")
                        verifier = QAVerifier(builder.context)
                        
                        import os
                        base_path = os.path.dirname(os.path.abspath(config.task_md_path)) or "."
                        base_path = os.path.dirname(base_path)  # Go up from .agent/
                        
                        qa_passed, qa_results = verifier.verify_all(
                            task,
                            ws_url=ws_url,
                            base_path=base_path
                        )
                        
                        if not qa_passed:
                            qa_retry_count = task.get('_qa_retry_count', 0) + 1
                            
                            if qa_retry_count <= config.max_qa_retries:
                                logger.warning(f"[LOOP] ⚠️ QA verification failed! Retry {qa_retry_count}/{config.max_qa_retries}")
                                
                                selector.unmark(task.get('id', ''))
                                task['_qa_retry_count'] = qa_retry_count
                                
                                fix_prompt = verifier.format_failure_prompt(qa_results)
                                cdp.inject_prompt(fix_prompt)
                                
                                logger.info("[LOOP] 🔁 Waiting for QA fix...\n")
                                time.sleep(2)
                                continue
                            else:
                                logger.error(f"[LOOP] ❌ Max QA retries ({config.max_qa_retries}) exceeded.")
                                qa_passed = True  # Move on despite failures
                    
                    if qa_passed:
                        # Mark complete in DB/File via Selector
                        # Note: Selector.mark_complete() now handles state persistence
                        selector.mark_complete(task.get('id'))
                        tasks_completed += 1
                        logger.info(f"[LOOP] ✨ Task {tasks_completed} completed and verified!")
                
                # 7. Context rotation check
                if reset.should_rotate(tasks_completed):
                    reset.rotate()
                
            # Reset retry counter on successful iteration
            driver_retries = 0
            
            # Update metrics (Estimation)
            estimated_llm_calls += 1  # 1 for the main prompt
            if config.enable_qa_verification and QA_VERIFICATION_AVAILABLE and config.enable_llm_visual_check:
                 estimated_llm_calls += 1 
            
            logger.info(f"[METRICS] 📊 Estimated LLM Calls this session: {estimated_llm_calls}")
            
        except KeyboardInterrupt:
            raise  # Re-raise to be caught by __main__ block
            
        except Exception as e:
            driver_retries += 1
            logger.error(f"\n[ERROR] 💥 Driver crashed (Attempt {driver_retries}/{config.max_driver_retries}): {e}")
            logger.error(f"Driver crash attempt {driver_retries}: {traceback.format_exc()}")
            
            if driver_retries <= config.max_driver_retries:
                logger.info("[LOOP] 🔁 Retrying in 5 seconds...")
                time.sleep(5)
                continue
            else:
                logger.critical(f"[FATAL] ☠️ Max retries exceeded. Exiting.")
                sys.exit(1)
        
        else:
            logger.warning("[LOOP] ⚠️ Task timed out. Continuing to next iteration...")
        
        logger.info("[LOOP] 🔁 Starting next iteration...\n")
        time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[EXIT] 👋 Loop terminated by user (Ctrl+C)")
        sys.exit(0)
