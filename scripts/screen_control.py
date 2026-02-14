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
        
        # Start background connectivity monitoring (runs continuously)
        self.start_background_connectivity_monitoring()
    
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
                
                # Row 0, Cell 3: Empty (status removed - only needed in preferences)
                elif r == 0 and c == 3:
                    pass  # Empty cell
                
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
                    elif c == 2:
                        # IMPORT button (from USB) - moved from row 5
                        btn = self._create_big_button(cell, "IMPORT", self.on_import_clicked)
                        btn.pack(fill="both", expand=True)
                    elif c == 3:
                        # SHUTDOWN button
                        btn = self._create_big_button(cell, "SHUTDOWN", self.shutdown)
                        btn.pack(fill="both", expand=True)
                
                # Row 5 (big font row): PREFERENCES only
                elif r == 5:
                    if c == 3:
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
    
    def on_import_clicked(self):
        """Handle IMPORT button click - go to USB browser"""
        self.app.show_screen('usb_browser')
    
    def on_show(self):
        """Called when this screen becomes visible"""
        # Update PATCH button visibility
        self.refresh_button_state()
    
    def update_status(self, message, error=False):
        """Update status message"""
        if self.status_label:
            color = "#e74c3c" if error else "#606060"
            self.status_label.config(text=message.upper(), fg=color)
        print(f"Control Panel: {message}")
    
    def check_internet(self):
        """
        Check if GitHub is reachable (not just generic internet)
        Used at startup to determine initial connectivity state
        """
        try:
            import socket
            # Force a new socket connection each time (no caching)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("github.com", 443))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def start_background_connectivity_monitoring(self):
        """
        Start background thread that continuously monitors GitHub connectivity
        Updates all screens when connectivity changes
        """
        def monitor():
            import time
            while True:
                time.sleep(2)  # Check every 2 seconds (faster than old 10 seconds)
                
                has_internet = self.check_internet()
                
                if has_internet != self.app.has_internet:
                    self.app.has_internet = has_internet
                    print(f"⚡ GitHub connectivity CHANGED: {'ONLINE' if has_internet else 'OFFLINE'}")
                    
                    # Update preferences screen UPDATE button AND status label
                    if 'preferences' in self.app.screens:
                        prefs = self.app.screens['preferences']
                        # Update UPDATE button (grey out when offline)
                        if hasattr(prefs, '_update_button_display'):
                            prefs.after(0, prefs._update_button_display)
                        # Update status label (show READY/OFFLINE MODE)
                        if hasattr(prefs, 'update_status'):
                            status_text = "READY" if has_internet else "OFFLINE MODE"
                            prefs.after(0, lambda t=status_text: prefs.update_status(t))
                    
                    # Update browser screen buttons (if something is selected)
                    if 'browser' in self.app.screens:
                        browser = self.app.screens['browser']
                        if hasattr(browser, 'selected_project_index') and browser.selected_project_index is not None:
                            if hasattr(browser, 'update_action_buttons'):
                                browser.after(0, browser.update_action_buttons)
        
        # Start background thread
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        print("Background connectivity monitoring started")
    
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