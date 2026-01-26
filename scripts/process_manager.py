"""
Process manager for Pure Data - Threaded version for non-blocking GUI
"""
import subprocess
import os
import sys
import time
import threading
from enum import Enum

class PDStatus(Enum):
    """Pure Data process status"""
    STOPPED = "stopped"
    INITIALIZING_MIDI = "initializing_midi"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"

class ProcessManager:
    """Manages Pure Data process lifecycle with non-blocking startup"""
    
    def __init__(self):
        self.pd_process = None
        self.current_patch = None
        self.status = PDStatus.STOPPED
        self.status_message = ""
        self.startup_thread = None
    
    def get_status(self):
        """
        Get current status for GUI display
        Returns: (PDStatus, message_string)
        """
        return (self.status, self.status_message)
    
    def ensure_jack_midi_bridge(self):
        """
        Check that JACK MIDI bridge is running
        DON'T restart it - amidiauto service manages this on Patchbox OS
        """
        try:
            # Just check if a2jmidid is running
            result = subprocess.run(
                ['pgrep', '-f', 'a2jmidid'],
                capture_output=True
            )
            
            if result.returncode == 0:
                print("✓ JACK MIDI bridge running (managed by Patchbox services)")
                return True
            else:
                print("⚠ JACK MIDI bridge not running!")
                print("⚠ Check: systemctl status amidiauto")
                print("⚠ This service should auto-manage a2jmidid")
                return False
                
        except Exception as e:
            print(f"⚠ Error checking JACK MIDI bridge: {e}")
            return False
    
    def wait_for_jack_midi_ports(self, timeout=5):
        """Wait for JACK MIDI ports to be available"""
        start_time = time.time()
        
        print("Waiting for JACK MIDI ports...")
        
        while (time.time() - start_time) < timeout:
            try:
                result = subprocess.run(
                    ['jack_lsp'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                
                if 'midi' in result.stdout.lower():
                    print("✓ JACK MIDI ports available")
                    return True
                    
            except Exception:
                pass
            
            time.sleep(0.3)
        
        print("⚠ JACK MIDI port timeout")
        return False
    
    def wait_for_midi_ready(self, timeout=3):
        """Wait for ALSA MIDI devices to be available"""
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                result = subprocess.run(
                    ['aconnect', '-l'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                
                if 'client' in result.stdout.lower():
                    print("✓ ALSA MIDI devices ready")
                    return True
                    
            except Exception:
                pass
            
            time.sleep(0.2)
        
        print("⚠ ALSA MIDI timeout (continuing anyway)")
        return False
    
    def _startup_worker(self, patch_path):
        """
        Background worker thread for PD startup
        This runs the MIDI initialization and PD startup without blocking the GUI
        """
        try:
            # Step 1: Kill existing PD
            self.status = PDStatus.INITIALIZING_MIDI
            self.status_message = "Stopping previous instance..."
            print("Killing existing Pure Data instances...")
            self.stop_pd()
            
            # Step 2: MIDI initialization sequence
            print("\n=== MIDI Initialization ===")
            
            self.status_message = "Starting MIDI bridge..."
            self.ensure_jack_midi_bridge()
            
            self.status_message = "Checking ALSA MIDI..."
            self.wait_for_midi_ready(timeout=3)
            
            self.status_message = "Waiting for JACK MIDI..."
            self.wait_for_jack_midi_ports(timeout=5)
            
            self.status_message = "MIDI stabilizing..."
            print("MIDI stabilization (4 seconds like Patchbox)...")
            time.sleep(4.0)  # Patchbox launch.sh uses 4 seconds
            
            print("=== MIDI Ready ===\n")
            
            # Step 3: Start Pure Data
            self.status = PDStatus.STARTING
            self.status_message = "Starting Pure Data..."
            
            project_dir = os.path.dirname(patch_path)
            project_patch = os.path.basename(patch_path)
            
            if not os.path.exists(patch_path):
                print(f"ERROR: Patch not found: {patch_path}")
                self.status = PDStatus.ERROR
                self.status_message = "Patch file not found"
                return
            
            print(f"Starting Pure Data with:")
            print(f"  - project: {project_patch}")
            print(f"  - directory: {project_dir}")
            
            if sys.platform.startswith("linux"):
                cmd = [
                    'puredata',
                    '-stderr',
                    '-nogui',
                    '-send', ';pd dsp 1',
                    '-outchannels', '8',
                    patch_path
                ]
                
                print(f"Command: {' '.join(cmd)}")
                
                self.pd_process = subprocess.Popen(
                    cmd,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                # Give Pure Data time to initialize MIDI
                self.status_message = "Pure Data initializing..."
                print("Waiting for Pure Data MIDI initialization...")
                time.sleep(3.0)
                
                # Check if still running
                if self.pd_process.poll() is not None:
                    print("ERROR: Pure Data process died immediately!")
                    stderr_output = self.pd_process.stderr.read()
                    print(f"Error output: {stderr_output}")
                    self.status = PDStatus.ERROR
                    self.status_message = "Pure Data crashed"
                    return
                
                print(f"Pure Data started! PID: {self.pd_process.pid}")
                print(f"  - {project_patch} loaded")
                
                # Final MIDI verification
                self.status_message = "Verifying MIDI..."
                print("\nFinal MIDI verification...")
                try:
                    result = subprocess.run(
                        ['jack_lsp'],
                        capture_output=True,
                        text=True,
                        timeout=1
                    )
                    if 'midi' in result.stdout.lower():
                        print("✓ MIDI confirmed available for Pure Data")
                    else:
                        print("⚠ WARNING: JACK MIDI ports not found after PD start!")
                except:
                    print("⚠ Could not verify MIDI")
                
            else:
                # macOS mock
                print(f"[MOCK PD] Would start Pure Data with: {patch_path}")
                self.pd_process = subprocess.Popen(
                    ['sleep', '9999'],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL
                )
            
            # Success!
            self.current_patch = patch_path
            self.status = PDStatus.RUNNING
            self.status_message = "Connected"
            print("\n✓ Pure Data ready!\n")
            
        except FileNotFoundError:
            print(f"ERROR: puredata command not found!")
            self.status = PDStatus.ERROR
            self.status_message = "Pure Data not installed"
        except Exception as e:
            print(f"Error starting PD: {e}")
            import traceback
            traceback.print_exc()
            self.status = PDStatus.ERROR
            self.status_message = f"Error: {str(e)}"
    
    def start_pd_async(self, patch_path):
        """
        Start Pure Data asynchronously (non-blocking)
        
        This returns immediately and runs the startup in a background thread.
        Check status with get_status() to see when it's ready.
        
        Args:
            patch_path: Full path to project's main.pd file
        
        Returns:
            True (always, since it's async)
        """
        # If already starting, don't start again
        if self.status == PDStatus.INITIALIZING_MIDI or self.status == PDStatus.STARTING:
            print("Startup already in progress, ignoring duplicate request")
            return True
        
        # Start background thread
        self.startup_thread = threading.Thread(
            target=self._startup_worker,
            args=(patch_path,),
            daemon=True
        )
        self.startup_thread.start()
        
        return True
    
    def start_pd(self, patch_path):
        """
        DEPRECATED: Blocking version (kept for compatibility)
        Use start_pd_async() for non-blocking startup
        """
        print("WARNING: Using blocking start_pd(). Consider start_pd_async() instead.")
        self._startup_worker(patch_path)
        return self.status == PDStatus.RUNNING
    
    def stop_pd(self):
        """Stop Pure Data process (let Patchbox services manage MIDI)"""
        try:
            # Kill Pure Data only
            subprocess.run(
                ['killall', 'puredata'],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL
            )
            
            # DON'T kill a2jmidid!
            # On Patchbox OS, amidiauto service manages a2jmidid automatically
            # Killing it causes conflicts with amidiauto
            
            time.sleep(0.5)  # Give processes time to stop
            
            self.pd_process = None
            self.current_patch = None
            
        except Exception as e:
            print(f"Error stopping PD: {e}")
    
    def is_running(self):
        """Check if PD is currently running"""
        if self.pd_process is None:
            return False
        
        poll = self.pd_process.poll()
        
        if poll is not None:
            try:
                stderr_output = self.pd_process.stderr.read()
                if stderr_output:
                    print(f"Pure Data error output: {stderr_output}")
            except:
                pass
            return False
        
        return True
    
    def restart_pd(self):
        """Restart Pure Data with current patch (async)"""
        if self.current_patch:
            return self.start_pd_async(self.current_patch)
        return False
    
    def diagnose_midi(self):
        """Print MIDI device status for debugging"""
        try:
            print("\n=== MIDI DIAGNOSTIC ===")
            
            # Check ALSA MIDI devices
            result = subprocess.run(
                ['aconnect', '-l'],
                capture_output=True,
                text=True,
                timeout=2
            )
            print("ALSA MIDI devices:")
            print(result.stdout if result.stdout else "(none)")
            
            # Check JACK MIDI ports
            try:
                result = subprocess.run(
                    ['jack_lsp', '-t'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                midi_ports = [line for line in result.stdout.split('\n') if 'midi' in line.lower()]
                if midi_ports:
                    print("\nJACK MIDI ports:")
                    for port in midi_ports:
                        print(f"  {port}")
                else:
                    print("\nJACK MIDI ports: (none)")
            except:
                print("\nJACK: (not available)")
            
            print("=== END DIAGNOSTIC ===\n")
            
        except Exception as e:
            print(f"Could not run MIDI diagnostics: {e}")
    
    def cleanup(self):
        """Clean shutdown of all processes"""
        print("Cleaning up Pure Data...")
        self.stop_pd()