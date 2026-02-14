"""
MIDI Setup Screen - Select USB MIDI device for Pure Data MIDI-Out 2
Full-screen navigation following browser pattern
"""
import tkinter as tk
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from midi_device_manager import MIDIDeviceManager

# Grid configuration (same as browser)
DEFAULT_ROWS = 11
COLS_PER_ROW = [4, 4, 4, 8, 4, 4, 4, 8, 4, 8, 8]
ROW_HEIGHTS = [60, 210, 50, 0, 0, 210, 50, 5, 20, 50, 50]

class MIDISetupScreen(tk.Frame):
    """MIDI device selection screen - follows browser pattern"""
    
    def __init__(self, parent, app):
        super().__init__(parent, bg="#000000")
        self.app = app
        
        self.rows = DEFAULT_ROWS
        self.cols_per_row = list(COLS_PER_ROW)
        
        # MIDI manager
        self.midi_manager = MIDIDeviceManager()
        
        # State
        self.devices = []  # List of device names ["CRAVE", "MicroFreak", etc.]
        self.current_device = None  # Currently configured device
        self.selected_index = None  # Currently selected in UI (0-3 for 4 slots)
        
        # UI references
        self.cell_frames = []
        self.device_labels = []  # 4 device labels (rows 1, 3, 5, 7)
        self.status_label = None
        
        self._build_ui()
    
    def _build_ui(self):
        """Build grid-based MIDI setup UI"""
        
        # Main grid container
        container = tk.Frame(self, bg="black", bd=0, highlightthickness=0)
        container.pack(expand=True, fill="both")
        
        container.columnconfigure(0, weight=1, uniform="outer_col")
        
        self.cell_frames.clear()
        self.device_labels.clear()
        
        # Build 11-row grid
        for r in range(self.rows):
            fixed_h = ROW_HEIGHTS[r] if r < len(ROW_HEIGHTS) else 0
            container.rowconfigure(r, minsize=fixed_h, weight=0)
            
            row_frame = tk.Frame(container, bg="black", bd=0, highlightthickness=0)
            row_frame.grid(row=r, column=0, sticky="nsew", padx=0, pady=0)
            row_frame.grid_propagate(False)
            
            if fixed_h:
                row_frame.configure(height=fixed_h)
            
            cols = self.cols_per_row[r]
            for c in range(cols):
                row_frame.columnconfigure(c, weight=1, uniform=f"row{r}_col")
            row_frame.rowconfigure(0, weight=1)
            
            row_cells = []
            
            for c in range(cols):
                cell = tk.Frame(row_frame, bg="black", bd=0, highlightthickness=0)
                cell.grid(row=0, column=c, sticky="nsew", padx=0, pady=0)
                cell.grid_propagate(False)
                row_cells.append(cell)
                
                # Row 0, Cell 0: BACK button (like browser's MENU button)
                if r == 0 and c == 0:
                    back_btn = tk.Label(
                        cell,
                        text="////BACK",
                        bg="black", fg="white",
                        anchor="w", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small,
                        cursor="hand2"
                    )
                    back_btn.bind("<Button-1>", lambda e: self.go_back())
                    back_btn.pack(fill="both", expand=True)
                
                # Row 0, Cell 3: Status label
                elif r == 0 and c == 3:
                    self.status_label = tk.Label(
                        cell,
                        text="SCANNING...",
                        bg="black", fg="#606060",
                        anchor="e", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.status
                    )
                    self.status_label.pack(fill="both", expand=True)
                
                # Rows 1, 3, 5, 7: Device slots (4 total)
                elif r in [1, 3, 5, 7] and c == 0:
                    device_index = [1, 3, 5, 7].index(r)
                    device_label = tk.Label(
                        cell,
                        text="",
                        font=self.app.fonts.big,
                        bg="#1a1a1a", fg="#606060",
                        anchor="w", padx=40,
                        cursor="hand2", bd=0, relief="flat"
                    )
                    device_label.bind("<Button-1>", lambda e, idx=device_index: self.select_device(idx))
                    device_label.pack(fill="both", expand=True, padx=40, pady=20)
                    self.device_labels.append(device_label)
                
                # Row 9: Action buttons (CLEAR and SET)
                elif r == 9:
                    if c == 6:
                        # CLEAR button
                        clear_btn = tk.Label(
                            cell,
                            text="CLEAR",
                            font=self.app.fonts.medium,
                            bg="#2c2c2c", fg="#ffffff",
                            cursor="hand2", bd=0, relief="flat"
                        )
                        clear_btn.bind("<Button-1>", lambda e: self.clear_device())
                        clear_btn.pack(fill="both", expand=True, padx=20, pady=10)
                    
                    elif c == 7:
                        # SET button
                        set_btn = tk.Label(
                            cell,
                            text="SET",
                            font=self.app.fonts.medium,
                            bg="#cc5500", fg="#ffffff",
                            cursor="hand2", bd=0, relief="flat"
                        )
                        set_btn.bind("<Button-1>", lambda e: self.set_device())
                        set_btn.pack(fill="both", expand=True, padx=20, pady=10)
            
            self.cell_frames.append(row_cells)
    
    def go_back(self):
        """Return to preferences screen"""
        self.app.show_screen('preferences')
    
    def on_show(self):
        """Called when screen becomes visible"""
        print("=== MIDI Setup Screen: on_show called ===")
        self.scan_devices()
    
    def scan_devices(self):
        """Scan for available MIDI devices"""
        print("Scanning for MIDI devices...")
        self.update_status("SCANNING...")
        
        try:
            # Get available devices
            self.devices = self.midi_manager.get_available_devices()
            print(f"Found devices: {self.devices}")
            
            # Get current device
            self.current_device = self.midi_manager.get_current_device()
            print(f"Current device: {self.current_device}")
            
            # Auto-select current device if it exists
            if self.current_device and self.current_device in self.devices:
                self.selected_index = self.devices.index(self.current_device)
            else:
                self.selected_index = None
            
            # Update display
            self.update_device_list()
            
            # Update status
            if not self.devices:
                self.update_status("NO DEVICES FOUND")
            elif self.current_device:
                self.update_status(f"ACTIVE: {self.current_device}")
            else:
                self.update_status("SELECT DEVICE")
        
        except Exception as e:
            print(f"Error scanning devices: {e}")
            import traceback
            traceback.print_exc()
            self.update_status("ERROR SCANNING", error=True)
    
    def update_device_list(self):
        """Update device list display"""
        for i, label in enumerate(self.device_labels):
            if i < len(self.devices):
                device = self.devices[i]
                label.config(text=device)
                
                # Highlight current device (green)
                if device == self.current_device:
                    label.config(bg="#1a4d1a", fg="#00ff00")
                # Highlight selected device (yellow)
                elif i == self.selected_index:
                    label.config(bg="#4d4d1a", fg="#ffff00")
                # Normal
                else:
                    label.config(bg="#1a1a1a", fg="#ffffff")
            else:
                # Empty slot
                label.config(text="", bg="#0a0a0a", fg="#606060")
    
    def select_device(self, index):
        """Select a device from the list"""
        if index < len(self.devices):
            self.selected_index = index
            self.update_device_list()
            print(f"Selected device {index}: {self.devices[index]}")
    
    def set_device(self):
        """Set the selected device"""
        if self.selected_index is None or self.selected_index >= len(self.devices):
            self.update_status("SELECT A DEVICE FIRST", error=True)
            return
        
        device = self.devices[self.selected_index]
        
        # Show confirmation
        def on_confirm():
            self.update_status("CONFIGURING...")
            
            # Set device
            success, msg = self.midi_manager.set_midi_device(device)
            
            if success:
                self.current_device = device
                self.update_status(f"ACTIVE: {device}")
                self.update_device_list()
                
                # Return to preferences after 1.5 seconds
                self.after(1500, self.go_back)
            else:
                self.update_status(f"ERROR: {msg}", error=True)
                self.after(3000, self.scan_devices)
        
        self.app.show_confirmation(
            message=f"Set MIDI device to:\n\n{device}?",
            on_yes=on_confirm,
            return_screen='midi_setup',
            timeout=10
        )
    
    def clear_device(self):
        """Clear the current MIDI device"""
        if not self.current_device:
            self.update_status("NO DEVICE ACTIVE", error=True)
            return
        
        # Show confirmation
        def on_confirm():
            self.update_status("CLEARING...")
            
            # Clear device
            success, msg = self.midi_manager.clear_midi_device()
            
            if success:
                self.current_device = None
                self.selected_index = None
                self.update_status("CLEARED")
                self.update_device_list()
                
                # Return to preferences after 1.5 seconds
                self.after(1500, self.go_back)
            else:
                self.update_status(f"ERROR: {msg}", error=True)
                self.after(3000, self.scan_devices)
        
        self.app.show_confirmation(
            message=f"Disconnect MIDI device:\n\n{self.current_device}?",
            on_yes=on_confirm,
            return_screen='midi_setup',
            timeout=10
        )
    
    def update_status(self, message, error=False):
        """Update status label"""
        if self.status_label:
            color = "#e74c3c" if error else "#606060"
            self.status_label.config(text=message.upper(), fg=color)
        print(f"MIDI Setup: {message}")
