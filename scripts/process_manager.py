"""
Process manager for Pure Data - Following Patchbox OS pattern
"""
import subprocess
import os
import sys
import time

class ProcessManager:
    """Manages Pure Data process lifecycle"""
    
    def __init__(self):
        self.pd_process = None
        self.current_patch = None
    
    def start_pd(self, patch_path):
        """
        Start Pure Data with mother.pd + project's main.pd
        Both patches open in the same PD instance
        
        Args:
            patch_path: Full path to project's main.pd file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Kill any existing PD processes first
            print(f"Killing existing Pure Data instances...")
            self.stop_pd()
            
            # Get project patch info
            project_dir = os.path.dirname(patch_path)
            project_patch = os.path.basename(patch_path)
            
            # Mother.pd location (in molipe root)
            molipe_root = os.path.dirname(os.path.dirname(project_dir))  # Go up from projects/project-name/ to molipe root
            mother_path = os.path.join(molipe_root, "mother.pd")
            
            if not os.path.exists(mother_path):
                print(f"ERROR: mother.pd not found at: {mother_path}")
                return False
            
            print(f"Starting Pure Data with:")
            print(f"  - mother.pd: {mother_path}")
            print(f"  - project: {project_patch}")
            print(f"  - project directory: {project_dir}")
            
            # Build command based on platform
            if sys.platform.startswith("linux"):
                # Linux - Open BOTH patches in same PD instance with 8 audio outputs
                # puredata -nogui -send ";pd dsp 1" -outchannels 8 mother.pd /path/to/project/main.pd
                cmd = [
                    'puredata',
                    '-stderr',              # Show errors
                    '-nogui',               # No GUI
                    '-send', ';pd dsp 1',   # Enable audio DSP
                    '-outchannels', '8',    # 8 audio outputs (HiFiBerry HAT)
                    mother_path,            # First patch: mother.pd (full path)
                    patch_path              # Second patch: project's main.pd (full path)
                ]
                
                print(f"Command: {' '.join(cmd)}")
                
                # Start PD (no need to change directory - using full paths)
                self.pd_process = subprocess.Popen(
                    cmd,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                # Give it a moment to start
                time.sleep(0.5)
                
                # Check if it's still running
                if self.pd_process.poll() is not None:
                    # Process died immediately
                    print("ERROR: Pure Data process died immediately!")
                    stderr_output = self.pd_process.stderr.read()
                    print(f"Error output: {stderr_output}")
                    return False
                
                print(f"Pure Data started! PID: {self.pd_process.pid}")
                print(f"  - mother.pd loaded")
                print(f"  - {project_patch} loaded")
                
            else:
                # macOS - mock for testing
                print(f"[MOCK PD] Would start Pure Data with:")
                print(f"  - mother.pd: {mother_path}")
                print(f"  - project: {patch_path}")
                self.pd_process = subprocess.Popen(
                    ['sleep', '9999'],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL
                )
            
            self.current_patch = patch_path
            return True
            
        except FileNotFoundError as e:
            print(f"ERROR: puredata command not found! Is Pure Data installed?")
            print(f"Install with: sudo apt-get install puredata")
            return False
        except Exception as e:
            print(f"Error starting PD: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop_pd(self):
        """Stop Pure Data process"""
        try:
            # Kill all Pure Data instances (Patchbox style: killall puredata)
            subprocess.run(
                ['killall', 'puredata'],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL
            )
            
            # Give it a moment
            time.sleep(0.2)
            
            self.pd_process = None
            self.current_patch = None
            
        except Exception as e:
            print(f"Error stopping PD: {e}")
    
    def is_running(self):
        """Check if PD is currently running"""
        if self.pd_process is None:
            return False
        
        # Check if process is still alive
        poll = self.pd_process.poll()
        
        if poll is not None:
            # Process died - print any error output
            try:
                stderr_output = self.pd_process.stderr.read()
                if stderr_output:
                    print(f"Pure Data error output: {stderr_output}")
            except:
                pass
            return False
        
        return True
    
    def restart_pd(self):
        """Restart Pure Data with current patch"""
        if self.current_patch:
            return self.start_pd(self.current_patch)
        return False
    
    def cleanup(self):
        """Clean shutdown of all processes"""
        print("Cleaning up Pure Data...")
        self.stop_pd()