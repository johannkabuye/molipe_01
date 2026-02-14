"""
MIDI Setup Screen - Select USB MIDI device for Pure Data MIDI-Out 2
Integrated into Preferences screen workflow
"""
import tkinter as tk
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from midi_device_manager import MIDIDeviceManager

# Grid configuration (same as other screens)
DEFAULT_ROWS = 11
COLS_PER_ROW = [4, 4, 4, 8, 4, 4, 4, 8, 4, 8, 8]
ROW_HEIGHTS = [60, 210, 50, 0, 0, 210, 50, 5, 20, 50, 50]

class MIDISetupScreen(tk.Frame):
    """MIDI device selection screen"""
    
    def __init__(self, parent, app):
        super().__init__(parent, bg="#000000")
        self.app = app
        
        self.rows = DEFAULT_ROWS
        self.cols_per_row = list(COLS_PER_ROW)
        
        # State
        self.devices = []  # List of (device_name, port_name, full_id)
        self.selected_index = None
        self.current_device = None
        
        # UI references
        self.cell_frames = []
        self.device_list_frame = None
        self.device_labels = []
        self.current_label = None
        self.select_button_cell = None
        self.clear_button_cell = None
        self.status_label = None
        
        self._build_ui()
    
    def _build_ui(self):
        """Build grid-based MIDI setup UI"""
        
        # Main grid container
        container = tk.Frame(self, bg="black", bd=0, highlightthickness=0)
        container.pack(expand=True, fill="both")
        
        container.columnconfigure(0, weight=1, uniform="outer_col")
        
        self.cell_frames.clear()
        
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
                
                # Row 0, Cell 0: MENU button
                if r == 0 and c == 0:
                    menu_button = tk.Label(
                        cell,
                        text="////MENU",
                        bg="black", fg="white",
                        anchor="w", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small,
                        cursor="hand2"
                    )
                    menu_button.bind("<Button-1>", lambda e: self.on_menu_clicked())
                    menu_button.pack(fill="both", expand=True)
                
                # Row 0, Cell 3: Status label
                elif r == 0 and c == 3:
                    self.status_label = tk.Label(
                        cell,
                        text="MIDI SETUP",
                        bg="black", fg="#606060",
                        anchor="e", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.status
                    )
                    self.status_label.pack(fill="both", expand=True)
                
                # Row 1: Current device display
                elif r == 1:
                    if c == 0:
                        # Label
                        lbl = tk.Label(
                            cell, text="CURRENT:",
                            font=self.app.fonts.small,
                            bg="black", fg="#606060",
                            anchor="w", padx=40
                        )
                        lbl.pack(fill="both", expand=True)
                    elif c == 1:
                        # Current device name
                        self.current_label = tk.Label(
                            cell, text="(none)",
                            font=self.app.fonts.small,
                            bg="black", fg="white",
                            anchor="w", padx=20
                        )
                        self.current_label.pack(fill="both", expand=True)
                
                # Row 2: "AVAILABLE DEVICES" label
                elif r == 2 and c == 0:
                    lbl = tk.Label(
                        cell, text="AVAILABLE DEVICES:",
                        font=self.app.fonts.status,
                        bg="black", fg="#606060",
                        anchor="w", padx=40
                    )
                    lbl.pack(fill="both", expand=True)
                
                # Rows 3-4: Device list (scrollable area)
                elif r == 3 and c == 0:
                    # Create scrollable device list frame (spans 2 rows visually)
                    self.device_list_frame = tk.Frame(cell, bg="black")
                    self.device_list_frame.pack(fill="both", expand=True, padx=40)
                
                # Row 5: Action buttons
                elif r == 5:
                    if c == 0:
                        # UP button
                        btn = self._create_big_button(cell, "UP", self.on_up_clicked)
                        btn.pack(fill="both", expand=True)
                    elif c == 1:
                        # DOWN button
                        btn = self._create_big_button(cell, "DOWN", self.on_down_clicked)
                        btn.pack(fill="both", expand=True)
                    elif c == 2:
                        # SELECT button (dynamic)
                        self.select_button_cell = cell
                    elif c == 3:
                        # CLEAR button (dynamic)
                        self.clear_button_cell = cell
            
            self.cell_frames.append(row_cells)
    
    def _create_big_button(self, parent, text, command):
        """Create a big button using BIG font (29pt)"""
        btn = tk.Label(
            parent, text=text,
            font=self.app.fonts.big,
            bg="#000000", fg="#ffffff",
            cursor="hand2", bd=0, relief="flat", padx=20, pady=20
        )
        
        def on_click(e):
            print(f"Button clicked: {text}")
            command()
        
        btn.bind("<Button-1>", on_click)
        return btn
    
    def on_show(self):
        """Called when screen becomes visible - refresh device list"""
        self.refresh_devices()
    
    def refresh_devices(self):
        """Scan for MIDI devices and update display"""
        print("Scanning for MIDI devices...")
        
        # Get available devices
        self.devices = get_available_midi_devices()
        
        # Get current device
        self.current_device = get_current_midi_device()
        
        # Update current device label
        if self.current_label:
            if self.current_device:
                # Extract device name from full ID (e.g., "CRAVE:CRAVE MIDI 1" → "CRAVE")
                device_name = self.current_device.split(':')[0] if ':' in self.current_device else self.current_device
                self.current_label.config(text=device_name, fg="white")
            else:
                self.current_label.config(text="(none)", fg="#606060")
        
        # Rebuild device list
        self._rebuild_device_list()
        
        # Update action buttons
        self._update_action_buttons()
        
        # Update status
        if self.devices:
            self.update_status(f"{len(self.devices)} DEVICE(S) FOUND")
        else:
            self.update_status("NO DEVICES FOUND")
    
    def _rebuild_device_list(self):
        """Rebuild the device list display"""
        if not self.device_list_frame:
            return
        
        # Clear existing labels
        for widget in self.device_list_frame.winfo_children():
            widget.destroy()
        
        self.device_labels = []
        
        if not self.devices:
            # Show "no devices" message
            lbl = tk.Label(
                self.device_list_frame,
                text="(plug in a USB MIDI device)",
                font=self.app.fonts.status,
                bg="black", fg="#404040",
                anchor="w"
            )
            lbl.pack(fill="x", pady=5)
            self.selected_index = None
            return
        
        # Show device list
        for i, (device_name, port_name, full_id) in enumerate(self.devices):
            lbl = tk.Label(
                self.device_list_frame,
                text=f"  {device_name}",
                font=self.app.fonts.small,
                bg="black", fg="white",
                anchor="w"
            )
            lbl.pack(fill="x", pady=2)
            self.device_labels.append(lbl)
        
        # Select first device by default
        if self.selected_index is None and self.devices:
            self.selected_index = 0
        
        # Ensure selected_index is valid
        if self.selected_index is not None and self.selected_index >= len(self.devices):
            self.selected_index = len(self.devices) - 1
        
        # Highlight selected
        self._update_selection_highlight()
    
    def _update_selection_highlight(self):
        """Update visual highlight of selected device"""
        for i, lbl in enumerate(self.device_labels):
            if i == self.selected_index:
                lbl.config(bg="#2c2c2c", fg="white", text=f"▶ {self.devices[i][0]}")
            else:
                lbl.config(bg="black", fg="white", text=f"  {self.devices[i][0]}")
    
    def _update_action_buttons(self):
        """Update SELECT and CLEAR buttons based on state"""
        # SELECT button
        if self.select_button_cell:
            for widget in self.select_button_cell.winfo_children():
                widget.destroy()
            
            if self.devices and self.selected_index is not None:
                btn = self._create_big_button(self.select_button_cell, "SELECT", self.on_select_clicked)
                btn.pack(fill="both", expand=True)
        
        # CLEAR button
        if self.clear_button_cell:
            for widget in self.clear_button_cell.winfo_children():
                widget.destroy()
            
            if self.current_device:
                btn = self._create_big_button(self.clear_button_cell, "CLEAR", self.on_clear_clicked)
                btn.pack(fill="both", expand=True)
    
    def on_menu_clicked(self):
        """Return to preferences"""
        self.app.show_screen('preferences')
    
    def on_up_clicked(self):
        """Move selection up"""
        if not self.devices or self.selected_index is None:
            return
        
        self.selected_index = (self.selected_index - 1) % len(self.devices)
        self._update_selection_highlight()
    
    def on_down_clicked(self):
        """Move selection down"""
        if not self.devices or self.selected_index is None:
            return
        
        self.selected_index = (self.selected_index + 1) % len(self.devices)
        self._update_selection_highlight()
    
    def on_select_clicked(self):
        """Select current device"""
        if not self.devices or self.selected_index is None:
            return
        
        device_name, port_name, full_id = self.devices[self.selected_index]
        
        def on_confirm():
            self.update_status("CONFIGURING...")
            
            # Set MIDI device (in background thread)
            import threading
            def do_config():
                success, message = set_midi_device(full_id)
                
                if success:
                    self.after(0, lambda: self.update_status(f"SET: {device_name}"))
                    self.after(0, self.refresh_devices)
                else:
                    self.after(0, lambda: self.update_status(f"ERROR: {message}", error=True))
                    self.after(3000, lambda: self.update_status("MIDI SETUP"))
            
            threading.Thread(target=do_config, daemon=True).start()
            
            # Return to this screen
            self.app.show_screen('midi_setup')
        
        self.app.show_confirmation(
            message=f"Set MIDI output to:\n\n{device_name}?",
            on_yes=on_confirm,
            return_screen='midi_setup',
            timeout=10
        )
    
    def on_clear_clicked(self):
        """Clear current MIDI device"""
        def on_confirm():
            self.update_status("CLEARING...")
            
            # Clear MIDI device (in background thread)
            import threading
            def do_clear():
                success, message = clear_midi_device()
                
                if success:
                    self.after(0, lambda: self.update_status("CLEARED"))
                    self.after(0, self.refresh_devices)
                else:
                    self.after(0, lambda: self.update_status(f"ERROR: {message}", error=True))
                    self.after(3000, lambda: self.update_status("MIDI SETUP"))
            
            threading.Thread(target=do_clear, daemon=True).start()
            
            # Return to this screen
            self.app.show_screen('midi_setup')
        
        self.app.show_confirmation(
            message="Clear MIDI output device?",
            on_yes=on_confirm,
            return_screen='midi_setup',
            timeout=10
        )
    
    def update_status(self, message, error=False):
        """Update status message"""
        if self.status_label:
            color = "#e74c3c" if error else "#606060"
            self.status_label.config(text=message.upper(), fg=color)
        print(f"MIDI Setup: {message}")
