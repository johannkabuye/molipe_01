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
                
                # Row 0, Cell 3: Status label (upper right) - shows connectivity status
                elif r == 0 and c == 3:
                    # Show initial connectivity status
                    status_text = "READY" if self.app.has_internet else "OFFLINE MODE"
                    self.status_label = tk.Label(
                        cell,
                        text=status_text,
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
            # Return to connectivity status after 3 seconds
            def restore_status():
                status_text = "READY" if self.app.has_internet else "OFFLINE MODE"
                self.update_status(status_text)
            self.after(3000, restore_status)
            return
        
        # Ensure Git remote uses HTTPS (not SSH) for boot reliability
        self._ensure_https_remote()
        
        def on_confirm_update():
            print("=== UPDATE CONFIRMED - Starting update process ===")
            self.updating = True
            self.update_status("UPDATING...")
            
            def do_update():
                try:
                    print("=== UPDATE THREAD STARTED ===")
                    
                    # === DIAGNOSTIC LOGGING ===
                    log_file = "/home/patch/git_update_debug.log"
                    try:
                        from datetime import datetime
                        with open(log_file, "a") as f:
                            f.write("\n" + "="*80 + "\n")
                            f.write(f"UPDATE at {datetime.now()}\n")
                            f.write("="*80 + "\n")
                            f.write(f"HOME={os.environ.get('HOME', 'NOT SET')}\n")
                            f.write(f"USER={os.environ.get('USER', 'NOT SET')}\n")
                            f.write(f"CWD={os.getcwd()}\n")
                            f.write(f"molipe_root={self.app.molipe_root}\n")
                            
                            # Quick Git test
                            test_cmd = subprocess.run(
                                ["git", "ls-remote", "--heads", "origin"],
                                cwd=self.app.molipe_root,
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            f.write(f"git ls-remote: {'OK' if test_cmd.returncode == 0 else 'FAIL'}\n")
                            if test_cmd.returncode != 0:
                                f.write(f"stderr: {test_cmd.stderr}\n")
                        print(f"[OK] Diagnostics logged to {log_file}")
                    except Exception as e:
                        print(f"Diagnostic logging failed: {e}")
                    # === END DIAGNOSTIC ===
                    
                    # ULTRA-NUCLEAR OPTION: Handles ANY git state, ALWAYS overwrites
                    
                    # Step 0a: Check if we need to fix permissions
                    # Skip sudo chown if it might hang (no password-less sudo configured)
                    print("Checking file permissions...")
                    
                    # Quick test: can we write to molipe_root?
                    test_file = os.path.join(self.app.molipe_root, ".write_test")
                    try:
                        with open(test_file, 'w') as f:
                            f.write("test")
                        os.remove(test_file)
                        print("[OK] Write access OK - no permission fix needed")
                    except PermissionError:
                        print("⚠ No write access - attempting permission fix...")
                        self.after(0, lambda: self.update_status("FIXING PERMISSIONS..."))
                        
                        # Try to fix permissions (may fail if sudo requires password)
                        import pwd
                        current_user = pwd.getpwuid(os.getuid()).pw_name
                        print(f"Attempting: sudo chown -R {current_user}:{current_user} {self.app.molipe_root}")
                        
                        try:
                            chown_result = subprocess.run(
                                ["sudo", "-n", "chown", "-R", f"{current_user}:{current_user}", self.app.molipe_root],
                                capture_output=True,
                                text=True,
                                timeout=5  # Shorter timeout
                            )
                            
                            if chown_result.returncode != 0:
                                print(f"Permission fix failed: {chown_result.stderr}")
                                print("Continuing anyway - update may fail...")
                            else:
                                print("[OK] Permissions fixed")
                        except subprocess.TimeoutExpired:
                            print("Permission fix timed out - continuing anyway")
                        except Exception as e:
                            print(f"Permission fix error: {e} - continuing anyway")
                    
                    # Step 0b: Get current version BEFORE update
                    print("Checking current version...")
                    self.after(0, lambda: self.update_status("CHECKING VERSION..."))
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
                    
                    correct_url = "https://github.com/johannkabuye/molipe_01.git"
                    
                    if remote_result.returncode != 0:
                        # Remote doesn't exist - add it
                        print("Remote 'origin' not found - adding it...")
                        try:
                            subprocess.run(
                                ["git", "remote", "add", "origin", correct_url],
                                cwd=self.app.molipe_root,
                                capture_output=True,
                                text=True,
                                check=True,
                                timeout=5
                            )
                            print("[OK] Remote added")
                        except subprocess.CalledProcessError as e:
                            print(f"Failed to add remote: {e.stderr}")
                            # Continue anyway - might still work
                    
                    elif "johannkabuye/molipe_01" not in remote_result.stdout:
                        # Remote exists but wrong URL - update it
                        print(f"Remote URL incorrect: {remote_result.stdout.strip()}")
                        print("Updating remote URL...")
                        try:
                            subprocess.run(
                                ["git", "remote", "set-url", "origin", correct_url],
                                cwd=self.app.molipe_root,
                                capture_output=True,
                                text=True,
                                check=True,
                                timeout=5
                            )
                            print("[OK] Remote URL updated")
                        except subprocess.CalledProcessError as e:
                            print(f"Failed to update remote: {e.stderr}")
                            # Continue anyway
                    
                    else:
                        print(f"[OK] Remote correctly configured: {remote_result.stdout.strip()}")
                    
                    # Set Git credential helper to cache (prevents auth prompts)
                    # This is critical for boot-time updates where there's no terminal
                    try:
                        subprocess.run(
                            ["git", "config", "--global", "credential.helper", "cache --timeout=3600"],
                            cwd=self.app.molipe_root,
                            capture_output=True,
                            timeout=2
                        )
                        # Also disable any interactive prompts
                        subprocess.run(
                            ["git", "config", "--global", "core.askPass", ""],
                            cwd=self.app.molipe_root,
                            capture_output=True,
                            timeout=2
                        )
                        print("[OK] Git credentials configured for non-interactive mode")
                    except Exception as e:
                        print(f"Warning: Could not configure Git credentials: {e}")
                        # Continue anyway
                    
                    # Step 2: Fetch all changes (longer timeout for slow connections)
                    print("Fetching from GitHub...")
                    self.after(0, lambda: self.update_status("DOWNLOADING..."))
                    
                    # Set environment to prevent any interactive prompts
                    fetch_env = os.environ.copy()
                    fetch_env['GIT_TERMINAL_PROMPT'] = '0'  # Disable credential prompts
                    fetch_env['GIT_SSH_COMMAND'] = 'ssh -o BatchMode=yes'  # Non-interactive SSH
                    
                    fetch_result = subprocess.run(
                        ["git", "fetch", "--all", "--prune"],
                        cwd=self.app.molipe_root,
                        capture_output=True,
                        text=True,
                        timeout=60,  # Increased from 30s to 60s
                        env=fetch_env  # Use non-interactive environment
                    )
                    
                    if fetch_result.returncode != 0:
                        error_msg = fetch_result.stderr.strip()
                        print(f"Fetch error: {error_msg}")
                        
                        # Show helpful error message
                        if "Permission denied" in error_msg or "permission" in error_msg.lower():
                            self.after(0, lambda: self.update_status("PERMISSION ERROR", error=True))
                            print("TIP: Try running: sudo chown -R patch:patch /home/patch/Desktop/molipe_01")
                        else:
                            self.after(0, lambda: self.update_status("DOWNLOAD FAILED", error=True))
                        
                        self.updating = False
                        self.after(5000, lambda: self.update_status("READY" if self.app.has_internet else "OFFLINE MODE"))
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
                        self.after(3000, lambda: self.update_status("READY" if self.app.has_internet else "OFFLINE MODE"))
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
                        error_msg = reset_result.stderr.strip()
                        print(f"Reset error: {error_msg}")
                        
                        # Show helpful error message
                        if "Permission denied" in error_msg or "permission" in error_msg.lower():
                            self.after(0, lambda: self.update_status("PERMISSION ERROR", error=True))
                            print("TIP: Try running: sudo chown -R patch:patch /home/patch/Desktop/molipe_01")
                        else:
                            self.after(0, lambda: self.update_status("INSTALL FAILED", error=True))
                        
                        self.updating = False
                        self.after(5000, lambda: self.update_status("READY" if self.app.has_internet else "OFFLINE MODE"))
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
                    self.after(5000, lambda: self.update_status("READY" if self.app.has_internet else "OFFLINE MODE"))
                
                except Exception as e:
                    error_msg = str(e)  # Show full error (don't truncate)
                    print(f"Update exception: {error_msg}")
                    import traceback
                    traceback.print_exc()
                    # Truncate only for display in status (but show full in console)
                    display_msg = error_msg[:50] if len(error_msg) > 50 else error_msg
                    self.after(0, lambda msg=display_msg: self.update_status(f"ERROR: {msg}", error=True))
                    self.updating = False
                    self.after(5000, lambda: self.update_status("READY" if self.app.has_internet else "OFFLINE MODE"))
            
            threading.Thread(target=do_update, daemon=True).start()
            print("=== UPDATE THREAD LAUNCHED ===")
        
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
    
    def _ensure_https_remote(self):
        """
        Ensure Git remote uses HTTPS (not SSH) for reliability at boot time
        
        SSH remotes require SSH agent to be running, which might not be
        available when app auto-starts at boot. HTTPS is more reliable.
        
        Converts: git@github.com:user/repo.git → https://github.com/user/repo.git
        """
        try:
            # Get current remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.app.molipe_root,
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode != 0:
                print("Warning: Could not get Git remote URL")
                return
            
            current_url = result.stdout.strip()
            print(f"Current Git remote: {current_url}")
            
            # Check if it's SSH format
            if current_url.startswith("git@github.com:"):
                # Convert to HTTPS
                # git@github.com:johannkabuye/molipe_01.git → https://github.com/johannkabuye/molipe_01.git
                https_url = current_url.replace("git@github.com:", "https://github.com/").replace(".git", "")
                if not https_url.endswith(".git"):
                    https_url += ".git"
                
                print(f"Converting SSH to HTTPS: {current_url} → {https_url}")
                
                # Update remote URL
                subprocess.run(
                    ["git", "remote", "set-url", "origin", https_url],
                    cwd=self.app.molipe_root,
                    capture_output=True,
                    timeout=2
                )
                
                print("Git remote converted to HTTPS for boot reliability")
            
            elif current_url.startswith("https://"):
                print("Git remote already using HTTPS")
            
            else:
                print(f"Warning: Unknown Git remote format: {current_url}")
        
        except Exception as e:
            print(f"Warning: Could not check/update Git remote: {e}")
            # Don't fail - just continue with existing remote
    
    def on_show(self):
        """Called when this screen becomes visible"""
        # Show current connectivity status
        status_text = "READY" if self.app.has_internet else "OFFLINE MODE"
        self.update_status(status_text)