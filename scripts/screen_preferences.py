"""
Preferences Screen - System settings and advanced options
"""
import tkinter as tk
import subprocess
import threading
import sys
import os
from confirmation_dialog import show_confirmation

# Grid configuration (same as other screens)
DEFAULT_ROWS = 11
COLS_PER_ROW = [4, 4, 4, 8, 4, 4, 4, 8, 4, 8, 8]
ROW_HEIGHTS = [60, 210, 50, 0, 0, 210, 50, 5, 20, 50, 50]

class PreferencesScreen(tk.Frame):
    """Preferences screen with system settings"""
    
    def __init__(self, parent, app):
        super().__init__(parent, bg="#000000")
        self.app = app
        self.updating = False
        
        self.rows = DEFAULT_ROWS
        self.cols_per_row = list(COLS_PER_ROW)
        
        # UI references
        self.cell_frames = []
        self.status_label = None
        
        self._build_ui()
    
    def _build_ui(self):
        """Build grid-based preferences UI"""
        
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
                
                # Row 0, Cell 0: MENU button (back to control panel)
                if r == 0 and c == 0:
                    menu_button = tk.Label(
                        cell,
                        text="////<MENU",
                        bg="black", fg="white",
                        anchor="w", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small,
                        cursor="hand2"
                    )
                    menu_button.bind("<Button-1>", lambda e: self.on_menu_clicked())
                    menu_button.pack(fill="both", expand=True)
                
                # Row 0, Cell 3: Status label (upper right)
                elif r == 0 and c == 3:
                    self.status_label = tk.Label(
                        cell,
                        text="PREFERENCES",
                        bg="black", fg="#606060",
                        anchor="e", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.status
                    )
                    self.status_label.pack(fill="both", expand=True)
                
                # Row 1 (big font row): Main action buttons
                elif r == 1:
                    if c == 0:
                        # UPDATE button
                        if self.app.has_internet:
                            btn = self._create_big_button(cell, "UPDATE", self.update_molipe)
                            btn.pack(fill="both", expand=True)
                        else:
                            lbl = tk.Label(
                                cell, text="OFFLINE",
                                font=self.app.fonts.big,
                                bg="#000000", fg="#303030",
                                bd=0, relief="flat"
                            )
                            lbl.pack(fill="both", expand=True)
                    elif c == 1:
                        # EXIT TO DESKTOP button
                        btn = self._create_big_button(cell, "EXIT TO DESKTOP", self.exit_to_desktop)
                        btn.pack(fill="both", expand=True)
            
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
        print(f"Created button: {text}")
        return btn
    
    def on_menu_clicked(self):
        """Return to control panel"""
        self.app.show_screen('control')
    
    def update_status(self, message, error=False):
        """Update status message"""
        if self.status_label:
            color = "#e74c3c" if error else "#606060"
            self.status_label.config(text=message.upper(), fg=color)
        print(f"Preferences: {message}")
    
    def update_molipe(self):
        """Update molipe from git and restart"""
        if self.updating:
            return
        
        # SHOW CONFIRMATION DIALOG
        confirmed = show_confirmation(
            parent=self,
            message="Update Molipe from GitHub?\n\nThis will restart Molipe and stop\nany open project.",
            timeout=10,
            title="Update System"
        )
        
        if not confirmed:
            print("Update cancelled by user")
            return
        
        self.updating = True
        self.update_status("UPDATING...")
        
        def do_update():
            try:
                result = subprocess.run(
                    ["git", "pull", "--force"],
                    cwd=self.app.molipe_root,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    # Check if anything was actually updated
                    if "Already up to date" in result.stdout:
                        self.after(0, lambda: self.update_status("ALREADY UP TO DATE"))
                        self.updating = False
                    else:
                        # Files were updated - restart the app!
                        self.after(0, lambda: self.update_status("RESTARTING..."))
                        import time
                        time.sleep(1)
                        
                        # Restart Python process
                        print("UPDATE COMPLETE - RESTARTING APP...")
                        python = sys.executable
                        os.execv(python, [python] + sys.argv)
                else:
                    self.after(0, lambda: self.update_status("UPDATE FAILED", error=True))
                    self.updating = False
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self.update_status(f"ERROR: {error_msg}", error=True))
                self.updating = False
        
        threading.Thread(target=do_update, daemon=True).start()
    
    def exit_to_desktop(self):
        """Exit GUI but keep system running"""
        print("Exit to desktop clicked!")
        
        # SHOW CONFIRMATION DIALOG
        confirmed = show_confirmation(
            parent=self,
            message="Exit Molipe GUI?\n\nThis will close the interface but\nkeep the system running.",
            timeout=10,
            title="Exit to Desktop"
        )
        
        if not confirmed:
            print("Exit cancelled by user")
            return
        
        self.update_status("EXITING...")
        
        def do_exit():
            import time
            time.sleep(0.5)
            
            # Clean up Pure Data
            self.app.pd_manager.cleanup()
            
            # Exit the application (but not the system)
            print("Exiting Molipe GUI...")
            self.app.root.destroy()
        
        threading.Thread(target=do_exit, daemon=True).start()
    
    def on_show(self):
        """Called when this screen becomes visible"""
        self.update_status("PREFERENCES")