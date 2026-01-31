"""
Preferences Screen - System settings and advanced options
"""
import tkinter as tk
import subprocess
import threading
import sys
import os

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
        self.connectivity_check_id = None  # Track connectivity checking
        
        self.rows = DEFAULT_ROWS
        self.cols_per_row = list(COLS_PER_ROW)
        
        # UI references
        self.cell_frames = []
        self.status_label = None
        self.update_button_cell = None  # Track UPDATE button cell for dynamic updates
        
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
                        text="////MENU",
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
                        # UPDATE button - store cell reference for dynamic updates
                        self.update_button_cell = cell
                        self._update_button_display()
                    elif c == 1:
                        # EXIT TO DESKTOP button
                        btn = self._create_big_button(cell, "EXIT TO DESKTOP", self.exit_to_desktop)
                        btn.pack(fill="both", expand=True)
            
            self.cell_frames.append(row_cells)
    
    def _update_button_display(self):
        """Update the UPDATE button based on current internet connectivity"""
        if not self.update_button_cell:
            print("Warning: update_button_cell not initialized yet")
            return
        
        print(f"Updating UPDATE button: {'WHITE (online)' if self.app.has_internet else 'GREY (offline)'}")
        
        # Clear the cell
        for widget in self.update_button_cell.winfo_children():
            widget.destroy()
        
        # Show UPDATE button if online, OFFLINE label if not
        if self.app.has_internet:
            btn = self._create_big_button(self.update_button_cell, "UPDATE", self.update_molipe)
            btn.pack(fill="both", expand=True)
        else:
            lbl = tk.Label(
                self.update_button_cell, text="OFFLINE",
                font=self.app.fonts.big,
                bg="#000000", fg="#303030",
                bd=0, relief="flat"
            )
            lbl.pack(fill="both", expand=True)
    
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
        self.stop_connectivity_check()
        self.app.show_screen('control')
    
    def update_status(self, message, error=False):
        """Update status message"""
        if self.status_label:
            color = "#e74c3c" if error else "#606060"
            self.status_label.config(text=message.upper(), fg=color)
        print(f"Preferences: {message}")
    
    def update_molipe(self):
        """Update molipe from git and restart - ULTRA-NUCLEAR OPTION"""
        if self.updating:
            return
        
        # Final connectivity check before showing confirmation
        if not self._check_internet():
            # Update the app-level flag
            self.app.has_internet = False
            # Update button display immediately (turn grey)
            self._update_button_display()
            # Show error message
            self.update_status("GITHUB UNREACHABLE", error=True)
            self.after(3000, lambda: self.update_status("PREFERENCES"))
            return
        
        def on_confirm_update():
            self.updating = True
            self.update_status("UPDATING...")
            
            def do_update():
                try:
                    # ULTRA-NUCLEAR OPTION: Handles ANY git state, ALWAYS overwrites
                    
                    # Step 0: Get current version BEFORE update
                    print("Checking current version...")
                    current_hash_result = subprocess.run(
                        ["git", "rev-parse", "HEAD"],
                        cwd=self.app.molipe_root,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    current_hash = current_hash_result.stdout.strip() if current_hash_result.returncode == 0 else "unknown"
                    print(f"Current version: {current_hash[:8]}")
                    
                    # Step 1: Verify remote is configured correctly
                    print("Checking remote configuration...")
                    remote_result = subprocess.run(
                        ["git", "remote", "get-url", "origin"],
                        cwd=self.app.molipe_root,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if remote_result.returncode != 0 or "johannkabuye/molipe_01" not in remote_result.stdout:
                        print("Remote not configured, setting it up...")
                        # Remove old remote if exists
                        subprocess.run(
                            ["git", "remote", "remove", "origin"],
                            cwd=self.app.molipe_root,
                            capture_output=True,
                            timeout=5
                        )
                        # Add correct remote
                        subprocess.run(
                            ["git", "remote", "add", "origin", "https://github.com/johannkabuye/molipe_01.git"],
                            cwd=self.app.molipe_root,
                            check=True,
                            timeout=5
                        )
                    
                    # Step 2: Fetch all changes (longer timeout for slow connections)
                    print("Fetching from GitHub...")
                    self.after(0, lambda: self.update_status("DOWNLOADING..."))
                    fetch_result = subprocess.run(
                        ["git", "fetch", "--all", "--prune"],
                        cwd=self.app.molipe_root,
                        capture_output=True,
                        text=True,
                        timeout=60  # Increased from 30s to 60s
                    )
                    
                    if fetch_result.returncode != 0:
                        print(f"Fetch error: {fetch_result.stderr}")
                        self.after(0, lambda: self.update_status("DOWNLOAD FAILED", error=True))
                        self.updating = False
                        self.after(3000, lambda: self.app.show_screen('preferences'))
                        return
                    
                    # Step 3: Get remote version AFTER fetch
                    remote_hash_result = subprocess.run(
                        ["git", "rev-parse", "origin/main"],
                        cwd=self.app.molipe_root,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    remote_hash = remote_hash_result.stdout.strip() if remote_hash_result.returncode == 0 else "unknown"
                    print(f"Remote version: {remote_hash[:8]}")
                    
                    # Check if update is needed
                    if current_hash == remote_hash and current_hash != "unknown":
                        print("Already up to date!")
                        self.after(0, lambda: self.update_status("ALREADY UP TO DATE"))
                        self.updating = False
                        self.after(3000, lambda: self.app.show_screen('preferences'))
                        return
                    
                    print(f"Update available: {current_hash[:8]} → {remote_hash[:8]}")
                    
                    # Step 4: Checkout main branch (in case we're detached or on wrong branch)
                    print("Checking out main branch...")
                    subprocess.run(
                        ["git", "checkout", "-f", "main"],
                        cwd=self.app.molipe_root,
                        capture_output=True,
                        timeout=5
                    )
                    
                    # Step 5: HARD RESET to match GitHub exactly (discards ALL local changes)
                    print("Hard resetting to origin/main...")
                    self.after(0, lambda: self.update_status("INSTALLING..."))
                    reset_result = subprocess.run(
                        ["git", "reset", "--hard", "origin/main"],
                        cwd=self.app.molipe_root,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if reset_result.returncode != 0:
                        print(f"Reset error: {reset_result.stderr}")
                        self.after(0, lambda: self.update_status("INSTALL FAILED", error=True))
                        self.updating = False
                        self.after(3000, lambda: self.app.show_screen('preferences'))
                        return
                    
                    # Step 6: Clean ALL untracked and ignored files (most aggressive)
                    print("Cleaning untracked files...")
                    subprocess.run(
                        ["git", "clean", "-fdx"],  # -x removes ignored files too
                        cwd=self.app.molipe_root,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    # Step 7: Update complete - RESTART
                    print(f"Update complete: {current_hash[:8]} → {remote_hash[:8]}")
                    self.after(0, lambda: self.update_status("RESTARTING..."))
                    
                    import time
                    time.sleep(1.5)
                    
                    # Clean up Pure Data before restart
                    self.app.pd_manager.cleanup()
                    
                    # Restart Python process (multiple methods for reliability)
                    print("=== RESTARTING APPLICATION ===")
                    print(f"Python: {sys.executable}")
                    print(f"Args: {sys.argv}")
                    
                    # Method 1: Try execv (preferred)
                    try:
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                    except Exception as e1:
                        print(f"execv failed: {e1}")
                        # Method 2: Fallback to subprocess
                        try:
                            subprocess.Popen([sys.executable] + sys.argv)
                            self.app.root.destroy()
                        except Exception as e2:
                            print(f"Subprocess restart failed: {e2}")
                            # Give up and just show error
                            self.after(0, lambda: self.update_status("RESTART FAILED - REBOOT SYSTEM", error=True))
                
                except subprocess.TimeoutExpired as e:
                    error_msg = f"TIMEOUT: {e.cmd[0] if e.cmd else 'git'}"
                    print(f"Timeout error: {error_msg}")
                    self.after(0, lambda msg=error_msg: self.update_status(msg, error=True))
                    self.updating = False
                    self.after(3000, lambda: self.app.show_screen('preferences'))
                
                except Exception as e:
                    error_msg = str(e)[:30]  # Truncate long errors
                    print(f"Update exception: {error_msg}")
                    import traceback
                    traceback.print_exc()
                    self.after(0, lambda msg=error_msg: self.update_status(f"ERROR: {msg}", error=True))
                    self.updating = False
                    self.after(3000, lambda: self.app.show_screen('preferences'))
            
            threading.Thread(target=do_update, daemon=True).start()
        
        self.app.show_confirmation(
            message="Update Molipe from GitHub?\n\nThis will restart Molipe and stop\nany open project.",
            on_yes=on_confirm_update,
            return_screen='preferences',
            timeout=10
        )
    
    def exit_to_desktop(self):
        """Exit GUI but keep system running"""
        print("Exit to desktop clicked!")
        
        def on_confirm_exit():
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
        
        self.app.show_confirmation(
            message="Exit Molipe GUI?\n\nThis will close the interface but\nkeep the system running.",
            on_yes=on_confirm_exit,
            return_screen='preferences',
            timeout=10
        )
    
    def check_connectivity_while_visible(self):
        """
        Check GitHub connectivity every 1 second while preferences screen is visible
        Only runs when this screen is active - more efficient than constant background checking
        """
        # Only check if this screen is currently visible
        if self.app.current_screen != 'preferences':
            print("Connectivity check stopped - not on preferences screen")
            return
        
        # Perform the check
        has_internet = self._check_internet()
        print(f"Connectivity check: GitHub {'REACHABLE' if has_internet else 'UNREACHABLE'} (was: {'online' if self.app.has_internet else 'offline'})")
        
        # If connectivity changed, update the UPDATE button
        if has_internet != self.app.has_internet:
            self.app.has_internet = has_internet
            print(f"âš¡ GitHub connectivity CHANGED: {'ONLINE' if has_internet else 'OFFLINE'}")
            self._update_button_display()
        
        # Schedule next check in 1 second (faster detection)
        self.connectivity_check_id = self.after(1000, self.check_connectivity_while_visible)
    
    def stop_connectivity_check(self):
        """Stop the connectivity checking loop"""
        if self.connectivity_check_id:
            self.after_cancel(self.connectivity_check_id)
            self.connectivity_check_id = None
    
    def _check_internet(self):
        """
        Check if GitHub is reachable (not just generic internet)
        Uses shorter timeout for faster detection when cable is unplugged
        """
        try:
            import socket
            # Check GitHub specifically (not just Google DNS)
            # github.com on HTTPS port
            # Force a new socket connection each time (no caching)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("github.com", 443))
            sock.close()
            return result == 0
        except Exception as e:
            print(f"GitHub check exception: {e}")
            return False
    
    def on_show(self):
        """Called when this screen becomes visible"""
        print("Preferences screen shown - starting connectivity monitoring")
        self.update_status("PREFERENCES")
        
        # Start connectivity checking (only while this screen is visible)
        self.check_connectivity_while_visible()