"""
GitHub Manager - Handles git operations for individual Molipe projects
"""
import os
import subprocess
import configparser
from datetime import datetime


class GitHubConfig:
    """Represents a project's GitHub configuration"""
    
    def __init__(self, repo_url, username, token):
        self.repo_url = repo_url
        self.username = username
        self.token = token
        self.authenticated_url = self._build_authenticated_url()
    
    def _build_authenticated_url(self):
        """Build URL with embedded credentials for push operations"""
        # Convert: https://github.com/user/repo.git
        # To: https://username:token@github.com/user/repo.git
        
        if not self.repo_url.startswith('https://'):
            return None
        
        # Remove https:// prefix
        url_without_protocol = self.repo_url[8:]
        
        # Build authenticated URL
        return f"https://{self.username}:{self.token}@{url_without_protocol}"
    
    @classmethod
    def from_file(cls, project_path):
        """Read github_config from project folder"""
        config_file = os.path.join(project_path, 'github_config')
        
        if not os.path.exists(config_file):
            return None
        
        try:
            config = configparser.ConfigParser()
            config.read(config_file)
            
            if not config.has_section('github'):
                return None
            
            repo_url = config.get('github', 'repo_url', fallback=None)
            username = config.get('github', 'username', fallback=None)
            token = config.get('github', 'token', fallback=None)
            
            # Validate all fields are present
            if not all([repo_url, username, token]):
                return None
            
            return cls(repo_url, username, token)
        
        except Exception as e:
            print(f"Error reading github_config: {e}")
            return None


def has_github_config(project_path):
    """Check if project has a valid github_config file"""
    config = GitHubConfig.from_file(project_path)
    return config is not None


def is_git_initialized(project_path):
    """Check if project already has .git folder"""
    git_dir = os.path.join(project_path, '.git')
    return os.path.exists(git_dir)


def create_gitignore(project_path):
    """Create .gitignore file for Molipe projects"""
    gitignore_path = os.path.join(project_path, '.gitignore')
    
    gitignore_content = """# Molipe GitHub config (contains credentials!)
github_config

# Backup files
*.bak
*~
*.swp

# OS files
.DS_Store
Thumbs.db

# Temporary files
*.tmp
"""
    
    try:
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_content)
        return True
    except Exception as e:
        print(f"Error creating .gitignore: {e}")
        return False


def init_git_repo(project_path, github_config):
    """
    First-time git setup for a project
    
    Args:
        project_path: Path to project folder
        github_config: GitHubConfig object
    
    Returns:
        (success: bool, message: str)
    """
    
    if not isinstance(github_config, GitHubConfig):
        return False, "Invalid GitHub configuration"
    
    try:
        # Step 1: Initialize git repo
        result = subprocess.run(
            ['git', 'init'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return False, f"Git init failed: {result.stderr}"
        
        # Step 2: Configure git user (use GitHub noreply email)
        subprocess.run(
            ['git', 'config', 'user.name', github_config.username],
            cwd=project_path,
            check=True,
            timeout=5
        )
        
        subprocess.run(
            ['git', 'config', 'user.email', f'{github_config.username}@users.noreply.github.com'],
            cwd=project_path,
            check=True,
            timeout=5
        )
        
        # Step 3: Create .gitignore
        if not create_gitignore(project_path):
            return False, "Failed to create .gitignore"
        
        # Step 4: Set up remote with authenticated URL
        subprocess.run(
            ['git', 'remote', 'add', 'origin', github_config.authenticated_url],
            cwd=project_path,
            check=True,
            timeout=5
        )
        
        # Step 5: Create initial commit
        subprocess.run(
            ['git', 'add', '.'],
            cwd=project_path,
            check=True,
            timeout=10
        )
        
        subprocess.run(
            ['git', 'commit', '-m', 'Initial commit from Molipe'],
            cwd=project_path,
            check=True,
            timeout=10
        )
        
        # Step 6: Set branch to main
        subprocess.run(
            ['git', 'branch', '-M', 'main'],
            cwd=project_path,
            check=True,
            timeout=5
        )
        
        # Step 7: Push to GitHub (force push to overwrite any GitHub-created files)
        result = subprocess.run(
            ['git', 'push', '-u', 'origin', 'main', '--force'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return False, f"Push failed: {result.stderr}"
        
        return True, "Repository initialized and pushed successfully"
    
    except subprocess.TimeoutExpired:
        return False, "Git operation timed out"
    except subprocess.CalledProcessError as e:
        return False, f"Git command failed: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def sync_project(project_path):
    """
    Sync project to GitHub (add, commit, push)
    
    Args:
        project_path: Path to project folder
    
    Returns:
        (success: bool, message: str)
    """
    
    # Check if github_config exists
    github_config = GitHubConfig.from_file(project_path)
    if not github_config:
        return False, "No valid github_config found"
    
    # Check if git is initialized
    if not is_git_initialized(project_path):
        # First time - do full initialization
        return init_git_repo(project_path, github_config)
    
    # Already initialized - just sync
    try:
        # Step 1: Add all changes
        subprocess.run(
            ['git', 'add', '.'],
            cwd=project_path,
            check=True,
            timeout=10
        )
        
        # Step 2: Check if there's anything to commit
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if not status_result.stdout.strip():
            return True, "No changes to sync"
        
        # Step 3: Commit with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Auto-sync: {timestamp}"
        
        subprocess.run(
            ['git', 'commit', '-m', commit_message],
            cwd=project_path,
            check=True,
            timeout=10
        )
        
        # Step 4: Push to GitHub
        result = subprocess.run(
            ['git', 'push'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return False, f"Push failed: {result.stderr}"
        
        return True, "Synced successfully"
    
    except subprocess.TimeoutExpired:
        return False, "Git operation timed out"
    except subprocess.CalledProcessError as e:
        return False, f"Git command failed: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def get_git_status(project_path):
    """
    Get current git status of project
    
    Returns:
        dict with keys:
            - initialized: bool
            - has_config: bool
            - has_changes: bool
            - last_commit: str or None
    """
    
    status = {
        'initialized': is_git_initialized(project_path),
        'has_config': has_github_config(project_path),
        'has_changes': False,
        'last_commit': None
    }
    
    if not status['initialized']:
        return status
    
    try:
        # Check for uncommitted changes
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5
        )
        status['has_changes'] = bool(result.stdout.strip())
        
        # Get last commit message
        result = subprocess.run(
            ['git', 'log', '-1', '--pretty=%s'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            status['last_commit'] = result.stdout.strip()
    
    except Exception as e:
        print(f"Error getting git status: {e}")
    
    return status


# Convenience function for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python github_manager.py <project_path>")
        sys.exit(1)
    
    project_path = sys.argv[1]
    
    print(f"Checking project: {project_path}")
    print(f"Has github_config: {has_github_config(project_path)}")
    print(f"Git initialized: {is_git_initialized(project_path)}")
    
    status = get_git_status(project_path)
    print(f"\nStatus: {status}")
    
    if len(sys.argv) > 2 and sys.argv[2] == 'sync':
        print("\nSyncing project...")
        success, message = sync_project(project_path)
        print(f"Result: {message}")