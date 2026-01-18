"""
Project Deleter - Safe deletion with trash/recovery system
Moves projects to .trash folder instead of permanent deletion
"""
import os
import shutil
from datetime import datetime

class ProjectDeleter:
    """
    Safely deletes projects by moving them to a trash folder
    
    Features:
    - Moves to .trash instead of permanent deletion
    - Adds timestamp to avoid name conflicts
    - Allows future recovery/restoration
    - Hidden trash folder (.trash) to keep projects dir clean
    """
    
    def __init__(self, projects_dir):
        self.projects_dir = projects_dir
        self.trash_dir = os.path.join(projects_dir, "trash")
        
        # Create trash directory if it doesn't exist
        if not os.path.exists(self.trash_dir):
            try:
                os.makedirs(self.trash_dir)
                print(f"Created trash directory: {self.trash_dir}")
            except Exception as e:
                print(f"Error creating trash directory: {e}")
    
    def delete_project(self, project_name):
        """
        Delete a project by moving it to trash folder
        
        Args:
            project_name: Name of the project folder to delete
        
        Returns:
            tuple: (success: bool, message: str)
        """
        source_path = os.path.join(self.projects_dir, project_name)
        
        # Verify source exists
        if not os.path.exists(source_path):
            return False, f"Project '{project_name}' not found"
        
        if not os.path.isdir(source_path):
            return False, f"'{project_name}' is not a directory"
        
        # Generate trash name with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trash_name = f"{project_name}_{timestamp}"
        trash_path = os.path.join(self.trash_dir, trash_name)
        
        # Move to trash
        try:
            shutil.move(source_path, trash_path)
            print(f"Moved to trash: {project_name} → {trash_name}")
            return True, trash_name
        except Exception as e:
            return False, f"Delete failed: {str(e)}"
    
    def list_trash(self):
        """
        List all projects in trash folder
        
        Returns:
            list: List of project names in trash (with timestamps)
        """
        if not os.path.exists(self.trash_dir):
            return []
        
        try:
            items = os.listdir(self.trash_dir)
            # Only return directories
            return [item for item in items 
                   if os.path.isdir(os.path.join(self.trash_dir, item))]
        except Exception as e:
            print(f"Error listing trash: {e}")
            return []
    
    def restore_project(self, trash_name):
        """
        Restore a project from trash (future feature)
        
        Args:
            trash_name: Name of project in trash (with timestamp)
        
        Returns:
            tuple: (success: bool, restored_name: str or error_message: str)
        """
        trash_path = os.path.join(self.trash_dir, trash_name)
        
        # Verify trash item exists
        if not os.path.exists(trash_path):
            return False, f"Trash item '{trash_name}' not found"
        
        # Extract original name (remove timestamp suffix)
        # Format: "project-name_YYYYMMDD_HHMMSS"
        parts = trash_name.rsplit('_', 2)
        if len(parts) >= 3:
            original_name = parts[0]
        else:
            original_name = trash_name  # Fallback if no timestamp
        
        # Check if original name already exists
        restore_path = os.path.join(self.projects_dir, original_name)
        if os.path.exists(restore_path):
            # Add suffix if name conflict
            counter = 1
            while os.path.exists(os.path.join(self.projects_dir, f"{original_name}-restored-{counter}")):
                counter += 1
            original_name = f"{original_name}-restored-{counter}"
            restore_path = os.path.join(self.projects_dir, original_name)
        
        # Move back from trash
        try:
            shutil.move(trash_path, restore_path)
            print(f"Restored from trash: {trash_name} → {original_name}")
            return True, original_name
        except Exception as e:
            return False, f"Restore failed: {str(e)}"
    
    def empty_trash(self):
        """
        Permanently delete all items in trash (future feature)
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if not os.path.exists(self.trash_dir):
            return True, "Trash is already empty"
        
        try:
            # Count items before deletion
            items = self.list_trash()
            count = len(items)
            
            # Delete all items
            for item in items:
                item_path = os.path.join(self.trash_dir, item)
                shutil.rmtree(item_path)
            
            print(f"Emptied trash: {count} items permanently deleted")
            return True, f"Deleted {count} items"
        except Exception as e:
            return False, f"Empty trash failed: {str(e)}"


def delete_project(projects_dir, project_name):
    """
    Convenience function for deleting a project
    
    Args:
        projects_dir: Path to projects directory
        project_name: Name of project to delete
    
    Returns:
        tuple: (success: bool, trash_name: str or error_message: str)
    """
    deleter = ProjectDeleter(projects_dir)
    return deleter.delete_project(project_name)


def list_trash(projects_dir):
    """
    Convenience function for listing trash
    
    Args:
        projects_dir: Path to projects directory
    
    Returns:
        list: List of trashed project names
    """
    deleter = ProjectDeleter(projects_dir)
    return deleter.list_trash()


# Test function
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Delete:  python project_deleter.py <projects_dir> <project_name>")
        print("  List:    python project_deleter.py <projects_dir> --list")
        print("  Restore: python project_deleter.py <projects_dir> --restore <trash_name>")
        sys.exit(1)
    
    projects_dir = sys.argv[1]
    
    if len(sys.argv) > 2 and sys.argv[2] == "--list":
        # List trash
        items = list_trash(projects_dir)
        if items:
            print(f"Trash contains {len(items)} items:")
            for item in items:
                print(f"  - {item}")
        else:
            print("Trash is empty")
    
    elif len(sys.argv) > 3 and sys.argv[2] == "--restore":
        # Restore from trash
        trash_name = sys.argv[3]
        deleter = ProjectDeleter(projects_dir)
        success, result = deleter.restore_project(trash_name)
        
        if success:
            print(f"✓ Restored: {result}")
        else:
            print(f"✗ Error: {result}")
            sys.exit(1)
    
    elif len(sys.argv) >= 3:
        # Delete project
        project_name = sys.argv[2]
        success, result = delete_project(projects_dir, project_name)
        
        if success:
            print(f"✓ Moved to trash: {result}")
        else:
            print(f"✗ Error: {result}")
            sys.exit(1)
