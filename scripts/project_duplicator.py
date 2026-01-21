"""
Project Duplicator - Duplicate projects with Zettelkasten-style naming
Supports both same-directory duplication and cross-directory copying
"""
import os
import shutil
from datetime import datetime

def duplicate_project(source_dir, project_name, target_dir=None):
    """
    Duplicate a project with Zettelkasten-style naming
    
    Args:
        source_dir: Directory containing the source project
        project_name: Name of the project folder to duplicate
        target_dir: Target directory (if None, uses source_dir)
    
    Returns:
        tuple: (success: bool, new_name: str or error_message: str)
    """
    # If no target_dir specified, duplicate within same directory
    if target_dir is None:
        target_dir = source_dir
    
    source_path = os.path.join(source_dir, project_name)
    
    # Verify source exists
    if not os.path.exists(source_path):
        return False, f"Project '{project_name}' not found"
    
    if not os.path.isdir(source_path):
        return False, f"'{project_name}' is not a directory"
    
    # Generate new name with Zettelkasten pattern
    new_name = generate_zettelkasten_name(project_name, target_dir)
    new_path = os.path.join(target_dir, new_name)
    
    # Copy project
    try:
        shutil.copytree(source_path, new_path)
        print(f"Duplicated: {project_name} → {new_name}")
        return True, new_name
    except Exception as e:
        return False, f"Duplication failed: {str(e)}"

def generate_zettelkasten_name(base_name, target_dir):
    """
    Generate Zettelkasten-style name with timestamp suffix
    
    Pattern: base-name-YYYYMMDD-HHMMSS
    If name already has timestamp, increment with -01, -02, etc.
    
    Args:
        base_name: Original project name
        target_dir: Directory to check for conflicts
    
    Returns:
        str: New unique name
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    new_name = f"{base_name}-{timestamp}"
    
    # Check if this name already exists
    counter = 1
    while os.path.exists(os.path.join(target_dir, new_name)):
        new_name = f"{base_name}-{timestamp}-{counter:02d}"
        counter += 1
    
    return new_name