"""
Project Duplicator - Zettelkasten-style naming system
Handles smart duplication of project folders with intelligent naming
"""
import os
import shutil
import re

class ProjectDuplicator:
    """
    Duplicates project folders with Zettelkasten-style naming:
    - my-patch → my-patch-1 (first duplicate)
    - my-patch-1 → my-patch-1a (duplicate of numbered version)
    - my-patch-1a → my-patch-1b (duplicate of lettered version)
    """
    
    def __init__(self, projects_dir):
        self.projects_dir = projects_dir
    
    def duplicate_project(self, source_name):
        """
        Duplicate a project with smart naming
        
        Args:
            source_name: Name of the project folder to duplicate
        
        Returns:
            tuple: (success: bool, new_name: str or error_message: str)
        """
        source_path = os.path.join(self.projects_dir, source_name)
        
        # Verify source exists
        if not os.path.exists(source_path):
            return False, f"Source project '{source_name}' not found"
        
        if not os.path.isdir(source_path):
            return False, f"'{source_name}' is not a directory"
        
        # Get all existing project names
        existing_names = self._get_existing_projects()
        
        # Generate new name
        new_name = self._generate_next_name(source_name, existing_names)
        new_path = os.path.join(self.projects_dir, new_name)
        
        # Copy the project folder
        try:
            shutil.copytree(source_path, new_path)
            print(f"Duplicated: {source_name} → {new_name}")
            return True, new_name
        except Exception as e:
            return False, f"Copy failed: {str(e)}"
    
    def _get_existing_projects(self):
        """Get list of all existing project folder names"""
        if not os.path.exists(self.projects_dir):
            return []
        
        try:
            return [item for item in os.listdir(self.projects_dir)
                   if os.path.isdir(os.path.join(self.projects_dir, item))]
        except Exception as e:
            print(f"Error scanning projects: {e}")
            return []
    
    def _generate_next_name(self, source_name, existing_names):
        """
        Generate next available name using Zettelkasten system
        
        Examples:
            "my-patch" → "my-patch-1"
            "my-patch-1" → "my-patch-1a"
            "my-patch-1a" → "my-patch-1b"
            "my-patch-2" → "my-patch-2a"
        """
        # Parse the source name
        base, suffix_type, number, letter = self._parse_name(source_name)
        
        if suffix_type == "none":
            # Original has no suffix: add number
            # Find next available number
            return self._find_next_number(base, existing_names)
        
        elif suffix_type == "number":
            # Has number suffix: add letter
            # my-patch-1 → my-patch-1a
            return self._find_next_letter(base, number, existing_names)
        
        elif suffix_type == "letter":
            # Has number+letter suffix: increment letter
            # my-patch-1a → my-patch-1b
            return self._find_next_letter(base, number, existing_names, start_letter=letter)
        
        else:
            # Fallback: just add -copy
            return f"{source_name}-copy"
    
    def _parse_name(self, name):
        """
        Parse project name into components
        
        Returns:
            tuple: (base, suffix_type, number, letter)
            
        Examples:
            "my-patch" → ("my-patch", "none", None, None)
            "my-patch-1" → ("my-patch", "number", 1, None)
            "my-patch-1a" → ("my-patch", "letter", 1, "a")
            "my-patch-2b" → ("my-patch", "letter", 2, "b")
        """
        # Pattern: name-NUMBER or name-NUMBERletter
        pattern_letter = r'^(.+)-(\d+)([a-z])$'
        pattern_number = r'^(.+)-(\d+)$'
        
        # Try to match number+letter first
        match = re.match(pattern_letter, name)
        if match:
            base = match.group(1)
            number = int(match.group(2))
            letter = match.group(3)
            return (base, "letter", number, letter)
        
        # Try to match just number
        match = re.match(pattern_number, name)
        if match:
            base = match.group(1)
            number = int(match.group(2))
            return (base, "number", number, None)
        
        # No suffix
        return (name, "none", None, None)
    
    def _find_next_number(self, base, existing_names):
        """
        Find next available number for base name
        
        Example:
            base="my-patch", existing=["my-patch-1", "my-patch-2"]
            → returns "my-patch-3"
        """
        used_numbers = []
        
        for name in existing_names:
            parsed_base, suffix_type, number, letter = self._parse_name(name)
            
            # Only consider names with same base
            if parsed_base == base and suffix_type in ["number", "letter"]:
                used_numbers.append(number)
        
        # Find next available number
        next_num = 1
        while next_num in used_numbers:
            next_num += 1
        
        return f"{base}-{next_num}"
    
    def _find_next_letter(self, base, number, existing_names, start_letter=None):
        """
        Find next available letter for base-number combination
        
        Example:
            base="my-patch", number=1, existing=["my-patch-1a", "my-patch-1b"]
            → returns "my-patch-1c"
        """
        used_letters = []
        
        for name in existing_names:
            parsed_base, suffix_type, parsed_num, letter = self._parse_name(name)
            
            # Only consider names with same base and number
            if parsed_base == base and parsed_num == number and suffix_type == "letter":
                used_letters.append(letter)
        
        # Start from 'a' or from the letter after start_letter
        if start_letter:
            # Increment the current letter
            start_ord = ord(start_letter) + 1
        else:
            # Start from 'a'
            start_ord = ord('a')
        
        # Find next available letter
        for letter_ord in range(start_ord, ord('z') + 1):
            letter = chr(letter_ord)
            if letter not in used_letters:
                return f"{base}-{number}{letter}"
        
        # If we've exhausted a-z, fall back to adding timestamp
        import time
        timestamp = int(time.time() * 1000) % 10000
        return f"{base}-{number}z{timestamp}"


def duplicate_project(projects_dir, source_name):
    """
    Convenience function for duplicating a project
    
    Args:
        projects_dir: Path to projects directory
        source_name: Name of project to duplicate
    
    Returns:
        tuple: (success: bool, new_name: str or error_message: str)
    """
    duplicator = ProjectDuplicator(projects_dir)
    return duplicator.duplicate_project(source_name)


# Test function
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python project_duplicator.py <projects_dir> <project_name>")
        sys.exit(1)
    
    projects_dir = sys.argv[1]
    project_name = sys.argv[2]
    
    success, result = duplicate_project(projects_dir, project_name)
    
    if success:
        print(f"✓ Success! New project: {result}")
    else:
        print(f"✗ Error: {result}")
        sys.exit(1)
