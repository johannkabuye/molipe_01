"""
MIDI Device Manager - Detects USB MIDI devices and configures amidiminder
Handles Pure Data MIDI OUT routing to external hardware
"""
import subprocess
import re
import os


class MIDIDeviceManager:
    """
    Manages MIDI device detection and amidiminder configuration
    
    Features:
    - Scans amidiminder output for USB MIDI devices
    - Filters out system devices (APC Key, Pure Data, etc.)
    - Writes amidiminder.rules for persistent routing
    - Routes Pure Data MIDI-Out 2 to selected device
    """
    
    # Devices to ignore (system critical or irrelevant)
    IGNORED_DEVICES = [
        "Midi Through",
        "APC Key 25 mk2",
        "RtMidiIn Client",
        "RtMidiOut Client",
        "Pure Data",
        "TouchOSC"
    ]
    
    def __init__(self):
        self.rules_file = "/etc/amidiminder.rules"
    
    def get_available_devices(self):
        """
        Get list of available USB MIDI devices (excluding system devices)
        
        Returns:
            list: List of device names that can be selected
                  e.g., ["CRAVE", "MicroFreak", "Digitone"]
        """
        try:
            # Run amidiminder to detect ports
            # Use timeout to prevent hanging
            result = subprocess.run(
                ["amidiminder"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            # Parse output for "port added" lines
            # Example: "port added CRAVE:CRAVE MIDI 1 [32:0]"
            devices = set()
            
            for line in result.stdout.split('\n'):
                if 'port added' in line:
                    # Extract device name (before colon)
                    match = re.search(r'port added ([^:]+):', line)
                    if match:
                        device_name = match.group(1).strip()
                        
                        # Filter out ignored devices
                        if not any(ignored in device_name for ignored in self.IGNORED_DEVICES):
                            devices.add(device_name)
            
            return sorted(list(devices))
        
        except subprocess.TimeoutExpired:
            print("Warning: amidiminder timeout")
            return []
        except Exception as e:
            print(f"Error detecting MIDI devices: {e}")
            return []
    
    def get_device_ports(self, device_name):
        """
        Get all MIDI ports for a specific device
        
        Args:
            device_name: Name of device (e.g., "CRAVE")
        
        Returns:
            list: List of port names
                  e.g., ["CRAVE MIDI 1", "CRAVE MIDI 2"]
        """
        try:
            result = subprocess.run(
                ["amidiminder"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            ports = []
            
            for line in result.stdout.split('\n'):
                if f'port added {device_name}:' in line:
                    # Extract port name (between colon and bracket)
                    # Example: "port added CRAVE:CRAVE MIDI 1 [32:0]"
                    match = re.search(r':([^\[]+)\[', line)
                    if match:
                        port_name = match.group(1).strip()
                        ports.append(port_name)
            
            return ports
        
        except Exception as e:
            print(f"Error getting device ports: {e}")
            return []
    
    def get_current_device(self):
        """
        Get currently configured MIDI device from amidiminder.rules
        
        Returns:
            str or None: Device name if configured, None otherwise
        """
        try:
            if not os.path.exists(self.rules_file):
                return None
            
            with open(self.rules_file, 'r') as f:
                content = f.read()
            
            # Look for Pure Data Midi-Out 2 rule
            # Example: "Pure Data:Pure Data Midi-Out 2 --> CRAVE:CRAVE MIDI 1"
            match = re.search(r'Pure Data:Pure Data Midi-Out 2 --> ([^:]+):', content)
            if match:
                return match.group(1).strip()
            
            return None
        
        except Exception as e:
            print(f"Error reading current device: {e}")
            return None
    
    def set_midi_device(self, device_name):
        """
        Configure amidiminder to route Pure Data MIDI-Out 2 to selected device
        
        Args:
            device_name: Name of device to route to (e.g., "CRAVE")
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Get device ports
            ports = self.get_device_ports(device_name)
            if not ports:
                return False, f"No ports found for {device_name}"
            
            # Use first port (typically "DEVICE MIDI 1")
            target_port = ports[0]
            
            # Read current rules file
            if os.path.exists(self.rules_file):
                with open(self.rules_file, 'r') as f:
                    lines = f.readlines()
            else:
                lines = []
            
            # Remove any existing Pure Data Midi-Out 2 rules
            new_lines = [line for line in lines 
                        if 'Pure Data Midi-Out 2' not in line]
            
            # Add new rule at the end
            # Format: Pure Data:Pure Data Midi-Out 2 --> DEVICE:PORT
            new_rule = f"Pure Data:Pure Data Midi-Out 2 --> {device_name}:{target_port}\n"
            new_lines.append(new_rule)
            
            # Write rules file (requires sudo)
            temp_file = "/tmp/amidiminder.rules.tmp"
            with open(temp_file, 'w') as f:
                f.writelines(new_lines)
            
            # Copy with sudo
            result = subprocess.run(
                ["sudo", "cp", temp_file, self.rules_file],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return False, f"Failed to write rules: {result.stderr}"
            
            # Clean up temp file
            os.remove(temp_file)
            
            # Restart amidiminder service
            restart_result = subprocess.run(
                ["sudo", "systemctl", "restart", "amidiminder"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if restart_result.returncode != 0:
                return False, f"Failed to restart amidiminder: {restart_result.stderr}"
            
            print(f"[OK] MIDI device configured: {device_name} -> Pure Data MIDI-Out 2")
            return True, target_port
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Error: {str(e)}"
    
    def clear_midi_device(self):
        """
        Remove MIDI device routing (disconnect Pure Data MIDI-Out 2)
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Read current rules file
            if not os.path.exists(self.rules_file):
                return True, "No rules file exists"
            
            with open(self.rules_file, 'r') as f:
                lines = f.readlines()
            
            # Remove Pure Data Midi-Out 2 rules
            new_lines = [line for line in lines 
                        if 'Pure Data Midi-Out 2' not in line]
            
            # Write rules file
            temp_file = "/tmp/amidiminder.rules.tmp"
            with open(temp_file, 'w') as f:
                f.writelines(new_lines)
            
            # Copy with sudo
            subprocess.run(
                ["sudo", "cp", temp_file, self.rules_file],
                capture_output=True,
                timeout=5
            )
            
            os.remove(temp_file)
            
            # Restart amidiminder
            subprocess.run(
                ["sudo", "systemctl", "restart", "amidiminder"],
                capture_output=True,
                timeout=10
            )
            
            print("[OK] MIDI device routing cleared")
            return True, "Cleared"
        
        except Exception as e:
            return False, f"Error: {str(e)}"


# Convenience functions
def get_available_devices():
    """Get list of available USB MIDI devices"""
    manager = MIDIDeviceManager()
    return manager.get_available_devices()


def get_current_device():
    """Get currently configured device"""
    manager = MIDIDeviceManager()
    return manager.get_current_device()


def set_midi_device(device_name):
    """Set MIDI device routing"""
    manager = MIDIDeviceManager()
    return manager.set_midi_device(device_name)


def clear_midi_device():
    """Clear MIDI device routing"""
    manager = MIDIDeviceManager()
    return manager.clear_midi_device()


# Test functionality
if __name__ == "__main__":
    import sys
    
    manager = MIDIDeviceManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            # List available devices
            devices = manager.get_available_devices()
            print(f"Available MIDI devices: {devices}")
        
        elif command == "current":
            # Show current device
            current = manager.get_current_device()
            print(f"Current device: {current or 'None'}")
        
        elif command == "set" and len(sys.argv) > 2:
            # Set device
            device = sys.argv[2]
            success, msg = manager.set_midi_device(device)
            print(f"{'[OK]' if success else '[ERROR]'} {msg}")
        
        elif command == "clear":
            # Clear device
            success, msg = manager.clear_midi_device()
            print(f"{'[OK]' if success else '[ERROR]'} {msg}")
        
        else:
            print("Usage:")
            print("  python midi_device_manager.py list")
            print("  python midi_device_manager.py current")
            print("  python midi_device_manager.py set DEVICE_NAME")
            print("  python midi_device_manager.py clear")
    
    else:
        # Default: show available devices
        devices = manager.get_available_devices()
        current = manager.get_current_device()
        
        print(f"Available MIDI devices: {devices}")
        print(f"Current device: {current or 'None'}")
