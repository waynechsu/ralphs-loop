"""
Loop Configuration Module
=========================
Centralized configuration for the Ralph Wiggum Loop driver.
"""

import os
from dataclasses import dataclass

@dataclass
class LoopConfig:
    """Configuration settings for the loop driver."""
    
    # CDP Settings
    cdp_port: int = 9000
    
    # Retry Limits
    max_validation_retries: int = 2
    max_qa_retries: int = 2
    max_driver_retries: int = 3
    
    # Feature Flags
    enable_qa_verification: bool = True
    enable_llm_visual_check: bool = False
    
    # Context Management
    context_rotation_threshold: int = 5
    
    # Paths
    log_file: str = ".agent/errors.log"
    tasks_json_path: str = ".agent/TASKS.json"
    task_md_path: str = ".agent/task.md"

    @classmethod
    def from_env(cls) -> 'LoopConfig':
        """Load configuration from environment variables with defaults."""
        return cls(
            cdp_port=int(os.environ.get("CDP_PORT", 9000)),
            max_validation_retries=int(os.environ.get("MAX_VALIDATION_RETRIES", 2)),
            max_qa_retries=int(os.environ.get("MAX_QA_RETRIES", 2)),
            max_driver_retries=int(os.environ.get("MAX_DRIVER_RETRIES", 3)),
            enable_qa_verification=os.environ.get("ENABLE_QA_VERIFICATION", "true").lower() == "true",
            enable_llm_visual_check=os.environ.get("ENABLE_LLM_VISUAL_CHECK", "false").lower() == "true",
            context_rotation_threshold=int(os.environ.get("CONTEXT_ROTATION_THRESHOLD", 5)),
            log_file=os.environ.get("LOG_FILE", ".agent/errors.log"),
            tasks_json_path=os.environ.get("TASKS_JSON_PATH", ".agent/TASKS.json"),
            task_md_path=os.environ.get("TASK_MD_PATH", ".agent/task.md")
        )
