"""
Control Panel Screen - Grid-based layout matching patch display
"""
import tkinter as tk
import socket
import subprocess
import threading
import os

# Grid configuration (same as patch display)
DEFAULT_ROWS = 11
COLS_PER_ROW = [4, 4, 4, 8, 4, 4, 4, 8, 4, 8, 8]
ROW_HEIGHTS = [60, 210, 50, 0, 0, 210, 50, 5, 20, 50, 50]
BIG_FONT_PT = 29

class ControlScreen(tk.Frame):
    """Main control panel using grid layout"""
    
    def __init__(self, parent, app):
        super().__init__(parent, bg="#000000")
        self.app = app
        
        self.rows = DEFAULT_ROWS
        self.cols_per_row = list(COLS_PER_ROW)
        
        # Internet connectivity - store at app level for other screens to access
        self.app.has_internet = self.check_internet()
        
        # UI references
        self.patch_button = None
        self.status_label = None
        self.cell_frames = []
        
        self._build_ui()
    
    def _build_ui(self):
        """Build grid-based control panel"""
        
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
                
                # Row 0, Cell 0: PATCH button (only when PD running)
                if r == 0 and c == 0:
                    self.patch_button = tk.Label(
                        cell,
                        text="////PATCH",
                        bg="black", fg="white",
                        anchor="w", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small,  # Use small font (27pt) to match ////<MENU
                        cursor="hand2"
                    )
                    self.patch_button.bind("<Button-1>", lambda e: self.on_patch_clicked())
                    # Initially hidden
                    if not self.app.pd_manager.is_running():
                        self.patch_button.pack_forget()
                    else:
                        self.patch_button.pack(fill="both", expand=True)
                
                # Row 0, Cell 3: Status label (upper right)
                elif r == 0 and c == 3:
                    status_text = "READY" if self.app.has_internet else "OFFLINE MODE"
                    self.status_label = tk.Label(
                        cell,
                        text=status_text,
                        bg="black", fg="#606060",
                        anchor="e", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.status
                    )
                    self.status_label.pack(fill="both", expand=True)
                
                # Row 1 (big font row): Main buttons
                elif r == 1:
                    if c == 0:
                        # PROJECTS button
                        btn = self._create_big_button(cell, "PROJECTS", self.on_projects_clicked)
                        btn.pack(fill="both", expand=True)
                    elif c == 1:
                        # START NEW button
                        btn = self._create_big_button(cell, "START NEW", self.on_start_new_clicked)
                        btn.pack(fill="both", expand=True)
                    elif c == 3:
                        # SHUTDOWN button
                        btn = self._create_big_button(cell, "SHUTDOWN", self.shutdown)
                        btn.pack(fill="both", expand=True)
                
                # Row 5 (big font row): SAVE, IMPORT, and PREFERENCES
                elif r == 5:
                    if c == 0:
                        # SAVE button (placeholder)
                        btn = self._create_big_button(cell, "SAVE", self.save_placeholder)
                        btn.pack(fill="both", expand=True)
                    elif c == 1:
                        # IMPORT button (from USB)
                        btn = self._create_big_button(cell, "IMPORT", self.on_import_clicked)
                        btn.pack(fill="both", expand=True)
                    elif c == 3:
                        # PREFERENCES button (below SHUTDOWN)
                        btn = self._create_big_button(cell, "PREFERENCES", self.on_preferences_clicked)
                        btn.pack(fill="both", expand=True)
            
            self.cell_frames.append(row_cells)
    
    def _create_big_button(self, parent, text, command):
        """Create a big button for rows 1 and 5 using BIG font (29pt)"""
        btn = tk.Label(
            parent, text=text,
            font=self.app.fonts.big,  # Use BIG font (29pt) - same as patch display
            bg="#000000", fg="#ffffff",
            cursor="hand2", bd=0, relief="flat", padx=20, pady=20
        )
        
        def on_click(e):
            print(f"Button clicked: {text}")
            command()
        
        btn.bind("<Button-1>", on_click)
        print(f"Created button: {text}")
        return btn
    
    def refresh_button_state(self):
        """Update PATCH button visibility based on PD state"""
        if self.patch_button:
            if self.app.pd_manager.is_running():
                # Show PATCH button
                self.patch_button.pack(fill="both", expand=True)
            else:
                # Hide PATCH button
                self.patch_button.pack_forget()
    
    def on_projects_clicked(self):
        """Handle PROJECTS button click - always go to browser"""
        self.app.show_screen('browser')
    
    def on_start_new_clicked(self):
        """Handle START NEW button click - go to preset browser"""
        self.app.show_screen('preset_browser')
    
    def on_preferences_clicked(self):
        """Handle PREFERENCES button click - go to preferences"""
        self.app.show_screen('preferences')
    
    def on_patch_clicked(self):
        """Handle PATCH button click - go back to patch display"""
        if self.app.pd_manager.is_running():
            self.app.show_screen('patch')
    
    def save_placeholder(self):
        """SAVE button - placeholder for future functionality"""
        def on_confirm_save():
            print("SAVE clicked (placeholder)")
            self.update_status("SAVE - NOT IMPLEMENTED YET")
            self.app.show_screen('control')
        
        self.app.show_confirmation(
            message="Save project?\n\nThis will cause the audio to stop\nbriefly.",
            on_yes=on_confirm_save,
            return_screen='control',
            timeout=10
        )
    
    def on_import_clicked(self):
        """Handle IMPORT button click - go to USB browser"""
        self.app.show_screen('usb_browser')
    
    def on_show(self):
        """Called when this screen becomes visible"""
        # Update PATCH button visibility
        self.refresh_button_state()
        
        # Update status
        if self.app.pd_manager.is_running():
            self.update_status("READY")
        else:
            if self.app.has_internet:
                self.update_status("READY")
            else:
                self.update_status("OFFLINE MODE")
    
    def update_status(self, message, error=False):
        """Update status message"""
        if self.status_label:
            color = "#e74c3c" if error else "#606060"
            self.status_label.config(text=message.upper(), fg=color)
        print(f"Control Panel: {message}")
    
    def check_internet(self):
        """Check if internet connection is available"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False
    
    def shutdown(self):
        """Shutdown the system"""
        print("Shutdown button clicked!")
        
        def on_confirm_shutdown():
            self.update_status("SHUTTING DOWN...")
            
            def do_shutdown():
                import time
                time.sleep(1)
                
                # Clean up Pure Data
                self.app.pd_manager.cleanup()
                
                # Shutdown system (we're on Raspberry Pi, always Linux)
                try:
                    subprocess.run(["sudo", "shutdown", "now"], check=False)
                except Exception as e:
                    print(f"Shutdown error: {e}")
            
            threading.Thread(target=do_shutdown, daemon=True).start()
        
        self.app.show_confirmation(
            message="Shut down the system?",
            on_yes=on_confirm_shutdown,
            return_screen='control',
            timeout=10
        )