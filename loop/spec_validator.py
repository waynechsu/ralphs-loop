"""
Spec Validator Module
=====================
Handles spec validation for task implementations.

Responsibilities:
- Validate field requirements against implementations
- Find and parse model files
- Match model names case-insensitively
"""

import os
import re
from typing import Optional


# Default model file locations to search
DEFAULT_MODEL_PATHS = [
    'backend/models.py',
    'models.py',
    'src/models.py',
    'app/models.py'
]


def validate_spec(
    task: dict,
    context_data: Optional[dict],
    model_paths: Optional[list[str]] = None
) -> tuple[bool, list[str]]:
    """
    Validate that implementation matches spec requirements.
    
    Args:
        task: Task dict with field_requirements
        context_data: CONTEXT.json data with models
        model_paths: List of model file paths to search (uses defaults if None)
        
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    # Get field requirements
    field_requirements = task.get('field_requirements', {})
    
    if not field_requirements and context_data and 'models' in context_data:
        models = context_data['models']
        if 'database' in task.get('tags', []) or 'backend' in task.get('tags', []):
            for model_name, model_def in models.items():
                if isinstance(model_def, dict):
                    field_requirements[model_name] = list(model_def.keys())
    
    if not field_requirements:
        print("[VALIDATE] ⚠️ No field_requirements found, skipping validation")
        return True, []
    
    print(f"[VALIDATE] 🔍 Checking field requirements: {list(field_requirements.keys())}")
    
    # Find and parse implementation files
    paths = model_paths if model_paths is not None else DEFAULT_MODEL_PATHS
    found_models = find_implemented_models(paths)
    
    # Compare required vs implemented
    for model_name, required_fields in field_requirements.items():
        if isinstance(required_fields, list):
            matched_model = find_matching_model(model_name, found_models)
            
            if not matched_model:
                errors.append(f"Model '{model_name}' not found in implementation")
                continue
            
            implemented_fields = found_models[matched_model]
            
            for req_field in required_fields:
                req_normalized = req_field.lower().replace('-', '_')
                if not any(f.lower() == req_normalized for f in implemented_fields):
                    errors.append(f"Missing field '{req_field}' in model '{matched_model}'")
    
    is_valid = len(errors) == 0
    
    if is_valid:
        print("[VALIDATE] ✅ Spec validation PASSED")
    else:
        print(f"[VALIDATE] ❌ Spec validation FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f"           - {err}")
    
    return is_valid, errors


def find_implemented_models(model_paths: list[str]) -> dict[str, set]:
    """
    Find Python models and their fields from model files.
    
    Args:
        model_paths: List of paths to search for model files
        
    Returns:
        Dict mapping class name to set of field names
    """
    found_models: dict[str, set] = {}
    
    for model_file in model_paths:
        if os.path.exists(model_file):
            try:
                with open(model_file, 'r') as f:
                    content = f.read()
                
                class_pattern = re.compile(r'class\s+(\w+)\s*\([^)]*\)\s*:', re.MULTILINE)
                
                for match in class_pattern.finditer(content):
                    class_name = match.group(1)
                    class_start = match.end()
                    
                    next_class = class_pattern.search(content, class_start)
                    class_end = next_class.start() if next_class else len(content)
                    class_body = content[class_start:class_end]
                    
                    field_pattern = re.compile(r'^\s+(\w+)\s*:', re.MULTILINE)
                    fields = [m.group(1) for m in field_pattern.finditer(class_body)]
                    found_models[class_name] = set(fields)
                
                print(f"[VALIDATE] 📄 Found models in {model_file}: {list(found_models.keys())}")
                
            except Exception as e:
                print(f"[VALIDATE] ⚠️ Error reading {model_file}: {e}")
    
    return found_models


def find_matching_model(model_name: str, found_models: dict) -> Optional[str]:
    """
    Find a model by name (case-insensitive, partial match).
    
    Args:
        model_name: Name to search for
        found_models: Dict of found model names to fields
        
    Returns:
        Matching model name or None
    """
    for impl_name in found_models:
        if impl_name.lower() == model_name.lower():
            return impl_name
        if model_name.lower() in impl_name.lower():
            return impl_name
    return None
