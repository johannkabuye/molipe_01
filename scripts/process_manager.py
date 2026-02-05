"""
Process manager for Pure Data - Patchbox Method
Replicates exactly what Patchbox PureData module does
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
    """Manages Pure Data using Patchbox method"""
    
    def __init__(self):
        self.pd_process = None
        self.current_patch = None
        self.status = PDStatus.STOPPED
        self.status_message = ""
        self.startup_thread = None
        self.midi_connector_thread = None
    
    def get_status(self):
        """Get current status for GUI display"""
        return (self.status, self.status_message)
    
    def disconnect_all_midi(self):
        """
        Disconnect all MIDI connections
        Critical step from Patchbox scripts
        """
        try:
            print("Disconnecting all MIDI connections...")
            subprocess.run(
                ['aconnect', '-x'],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                timeout=2
            )
            time.sleep(0.2)
            print("✓ All MIDI connections cleared")
        except Exception as e:
            print(f"Warning: Could not disconnect MIDI: {e}")
    
    def connect_midi_to_puredata(self):
        """
        Connect all MIDI input ports to Pure Data
        This is what Patchbox does after PD starts
        """
        try:
            print("Connecting MIDI inputs to Pure Data...")
            
            # Get list of MIDI input ports (excluding Pure Data itself)
            result = subprocess.run(
                ['aconnect', '-i'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            # Parse port numbers (exclude Through, Pure Data, System)
            import re
            ports = []
            for line in result.stdout.split('\n'):
                # Look for lines like "client 20: 'USB MIDI' [type=kernel]"
                if 'client' in line.lower() and 'pure data' not in line.lower() and 'through' not in line.lower() and 'system' not in line.lower():
                    match = re.search(r'client\s+(\d+):', line)
                    if match:
                        ports.append(match.group(1))
            
            # Connect each port to Pure Data
            connections_made = 0
            for port in ports:
                for subport in range(16):  # Try subports 0-15
                    try:
                        # Connect TO Pure Data (for MIDI IN)
                        subprocess.run(
                            ['aconnect', f'{port}:{subport}', 'Pure Data'],
                            stderr=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            timeout=1
                        )
                        connections_made += 1
                    except:
                        pass  # Connection failed, try next
            
            if connections_made > 0:
                print(f"✓ Made {connections_made} MIDI input connections")
            else:
                print("⚠ No MIDI input connections made")
            
            return connections_made > 0
            
        except Exception as e:
            print(f"Error connecting MIDI: {e}")
            return False
    
    def _startup_worker(self, patch_path):
        """Background worker for PD startup using Patchbox method"""
        try:
            # Step 1: Clear state
            self.status = PDStatus.INITIALIZING_MIDI
            self.status_message = "Stopping previous instance..."
            print("\n=== Starting Pure Data (Patchbox Method) ===")
            
            # Step 2: Disconnect all MIDI (Patchbox does this!)
            self.disconnect_all_midi()
            
            # Step 3: Kill Pure Data
            print("Killing existing Pure Data instances...")
            subprocess.run(['killall', 'puredata'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            time.sleep(0.5)
            
            # Step 4: Verify patch exists
            if not os.path.exists(patch_path):
                print(f"ERROR: Patch not found: {patch_path}")
                self.status = PDStatus.ERROR
                self.status_message = "Patch file not found"
                return
            
            project_dir = os.path.dirname(patch_path)
            project_patch = os.path.basename(patch_path)
            
            print(f"Loading: {project_patch}")
            
            # Step 5: Start Pure Data using Patchbox method
            self.status = PDStatus.STARTING
            self.status_message = "Starting Pure Data..."
            
            if sys.platform.startswith("linux"):
                # Use ALSA MIDI like Patchbox (not JACK MIDI!)
                cmd = [
                    'puredata',
                    '-stderr',           # Show errors
                    ##'-nogui',            # No GUI
                    '-alsamidi',         # Use ALSA MIDI (like Patchbox)
                    '-mididev', '1',     # MIDI device 1 (like Patchbox)
                    '-channels', '2',    # 2 audio channels
                    '-r', '48000',       # 48kHz sample rate
                    '-outchannels', '8', # 8 audio outputs (HiFiBerry HAT)
                    '-send', ';pd dsp 1',# Enable audio DSP
                    patch_path           # Patch to load
                ]
                
                print(f"Command: {' '.join(cmd)}")
                
                # Change to patch directory (like Patchbox does)
                self.pd_process = subprocess.Popen(
                    cmd,
                    cwd=project_dir,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                # Step 6: Wait for Pure Data to initialize
                # Patchbox uses 3 seconds
                self.status_message = "Waiting for Pure Data MIDI..."
                print("Waiting 3 seconds for Pure Data to initialize...")
                time.sleep(3.0)
                
                # Check if still running
                if self.pd_process.poll() is not None:
                    print("ERROR: Pure Data died immediately!")
                    stderr_output = self.pd_process.stderr.read()
                    print(f"Error: {stderr_output}")
                    self.status = PDStatus.ERROR
                    self.status_message = "Pure Data crashed"
                    return
                
                print(f"✓ Pure Data started (PID: {self.pd_process.pid})")
                
                # Step 7: Connect MIDI inputs to Pure Data
                # This is THE CRITICAL STEP Patchbox does!
                self.status_message = "Connecting MIDI inputs..."
                self.connect_midi_to_puredata()
                
                # Step 8: Wait for patch to fully initialize
                # The patch itself takes time to load (create objects, load samples, etc.)
                # This is when CPU spikes to 350%+
                self.status_message = "Initializing patch..."
                print("Waiting for patch to fully initialize (5 seconds)...")
                time.sleep(5.0)
                
                # Step 9: Success!
                self.current_patch = patch_path
                self.status = PDStatus.RUNNING
                self.status_message = "Connected"
                print("✓ Patch fully loaded and ready!\n")
                
            else:
                # macOS mock
                print(f"[MOCK PD] Would start: {patch_path}")
                self.pd_process = subprocess.Popen(['sleep', '9999'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                self.current_patch = patch_path
                self.status = PDStatus.RUNNING
                self.status_message = "Connected"
            
        except FileNotFoundError:
            print("ERROR: puredata command not found!")
            self.status = PDStatus.ERROR
            self.status_message = "Pure Data not installed"
        except Exception as e:
            print(f"Error starting PD: {e}")
            import traceback
            traceback.print_exc()
            self.status = PDStatus.ERROR
            self.status_message = f"Error: {str(e)}"
    
    def start_pd_async(self, patch_path):
        """Start Pure Data asynchronously (non-blocking)"""
        if self.status == PDStatus.INITIALIZING_MIDI or self.status == PDStatus.STARTING:
            print("Startup already in progress")
            return True
        
        self.startup_thread = threading.Thread(
            target=self._startup_worker,
            args=(patch_path,),
            daemon=True
        )
        self.startup_thread.start()
        return True
    
    def start_pd(self, patch_path):
        """DEPRECATED: Blocking version"""
        print("WARNING: Using blocking start_pd()")
        self._startup_worker(patch_path)
        return self.status == PDStatus.RUNNING
    
    def stop_pd(self):
        """Stop Pure Data (Patchbox method)"""
        try:
            # Disconnect all MIDI first (Patchbox does this!)
            self.disconnect_all_midi()
            
            # Kill Pure Data
            subprocess.run(['killall', 'puredata'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            time.sleep(0.5)
            
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
            return False
        
        return True
    
    def restart_pd(self):
        """Restart Pure Data with current patch"""
        if self.current_patch:
            return self.start_pd_async(self.current_patch)
        return False
    
    def cleanup(self):
        """Clean shutdown"""
        print("Cleaning up Pure Data...")
        self.stop_pd()