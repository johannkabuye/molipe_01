"""
Control Panel Screen - Hub for Projects, Updates, and System
"""
import tkinter as tk
import socket
import subprocess
import threading
import os

class ControlScreen(tk.Frame):
    """Main control panel / home screen"""
    
    def __init__(self, parent, app):
        super().__init__(parent, bg="#000000")
        self.app = app
        self.updating = False
        
        # Internet connectivity
        self.has_internet = self.check_internet()
        
        # UI references
        self.update_button = None
        self.no_internet_label = None
        self.projects_button = None
        
        self._build_ui()
        
        # Start connectivity monitoring
        self.check_connectivity_periodically()
    
    def _build_ui(self):
        """Build the control panel UI"""
        # Status label in upper right
        status_text = "READY" if self.has_internet else "OFFLINE MODE"
        self.status = tk.Label(
            self, text=status_text,
            font=self.app.fonts.status,
            bg="#000000", fg="#606060"
        )
        self.status.place(relx=0.98, rely=0.02, anchor="ne")
        
        # Main container
        container = tk.Frame(self, bg="#000000")
        container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Title
        title = tk.Label(
            container, text="MOLIPE",
            font=self.app.fonts.title,
            bg="#000000", fg="#ffffff"
        )
        title.grid(row=0, column=0, columnspan=3, pady=(0, 60))
        
        # Configure grid
        for i in range(3):
            container.columnconfigure(i, weight=1, uniform="button_col")
        
        # Row 1: PROJECTS, RESUME (if PD running), UPDATE/SHUTDOWN
        
        # PROJECTS button (always goes to browser)
        self.projects_button = self._create_button(
            container, "▶ PROJECTS", self.on_projects_clicked
        )
        self.projects_button.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        # RESUME button (only visible when PD is running)
        self.resume_button = self._create_button(
            container, "▶ RESUME", self.on_resume_clicked
        )
        if self.app.pd_manager.is_running():
            self.resume_button.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        else:
            self.resume_button.grid_forget()
        
        # UPDATE button (if internet available) or SHUTDOWN
        if self.has_internet:
            self.update_button = self._create_button(
                container, "↻ UPDATE", self.update_molipe
            )
            self.update_button.grid(row=1, column=2, padx=10, pady=10, sticky="nsew")
        else:
            self._create_button(
                container, "⏻ SHUTDOWN", self.shutdown
            ).grid(row=1, column=2, padx=10, pady=10, sticky="nsew")
        
        # Row 2: QUIT and SHUTDOWN (if UPDATE was shown)
        if self.has_internet:
            self._create_button(
                container, "⏻ SHUTDOWN", self.shutdown
            ).grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        
        # QUIT button (closes GUI, keeps PD running)
        self._create_button(
            container, "✕ QUIT GUI", self.quit_gui
        ).grid(row=2, column=1 if self.has_internet else 0, columnspan=2 if not self.has_internet else 1, padx=10, pady=10, sticky="nsew")
    
    def _create_button(self, parent, text, command):
        """Create a custom button using Label"""
        btn = tk.Label(
            parent, text=text,
            font=self.app.fonts.button,
            bg="#000000", fg="#ffffff",
            cursor="none", bd=0, relief="flat",
            padx=20, pady=20
        )
        btn.bind("<Button-1>", lambda e: command())
        return btn
    
    def on_projects_clicked(self):
        """Handle PROJECTS button click - always go to browser"""
        self.app.show_screen('browser')
    
    def on_resume_clicked(self):
        """Handle RESUME button click - go back to patch display"""
        if self.app.pd_manager.is_running():
            self.app.show_screen('patch')
    
    def quit_gui(self):
        """Quit GUI but leave Pure Data running"""
        self.update_status("CLOSING GUI...")
        # Do NOT call pd_manager.cleanup() - let PD keep running
        self.after(500, lambda: self.app.root.destroy())
    
    def refresh_button_state(self):
        """Update RESUME button visibility based on PD state"""
        if self.app.pd_manager.is_running():
            # Show RESUME button
            self.resume_button.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        else:
            # Hide RESUME button
            self.resume_button.grid_forget()
    
    def check_internet(self, host="8.8.8.8", port=53, timeout=3):
        """Check if internet connection is available"""
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except socket.error:
            return False
    
    def check_connectivity_periodically(self):
        """Periodically check internet connectivity"""
        old_status = self.has_internet
        self.has_internet = self.check_internet()
        
        if old_status != self.has_internet:
            self._update_connectivity_ui()
        
        # Schedule next check
        self.after(10000, self.check_connectivity_periodically)
    
    def _update_connectivity_ui(self):
        """Update UI based on connectivity change"""
        # This is a simplified version - could be expanded
        status_text = "ONLINE" if self.has_internet else "OFFLINE MODE"
        if not self.updating:
            self.update_status(status_text)
    
    def update_molipe(self):
        """Update molipe core from GitHub"""
        if self.updating or not self.has_internet:
            return
        
        repo_path = self.app.molipe_root
        
        if not os.path.exists(os.path.join(repo_path, ".git")):
            self.update_status("NOT A GIT REPO", error=True)
            return
        
        self.updating = True
        if self.update_button:
            self.update_button.config(fg="#606060")
        
        self.update_status("FETCHING...")
        
        def do_update():
            try:
                # Fetch latest
                fetch_result = subprocess.run(
                    ['git', 'fetch', 'origin', 'main'],
                    cwd=repo_path,
                    capture_output=True, text=True, timeout=30
                )
                
                if fetch_result.returncode != 0:
                    self.after(0, lambda: self.update_status("✗ FETCH FAILED", error=True))
                    self.after(0, self._finish_update)
                    return
                
                self.after(0, lambda: self.update_status("UPDATING..."))
                
                # Force reset
                reset_result = subprocess.run(
                    ['git', 'reset', '--hard', 'origin/main'],
                    cwd=repo_path,
                    capture_output=True, text=True, timeout=10
                )
                
                if reset_result.returncode == 0:
                    # Fix permissions
                    scripts_dir = os.path.join(repo_path, "scripts")
                    if os.path.exists(scripts_dir):
                        for f in os.listdir(scripts_dir):
                            if f.endswith('.py'):
                                os.chmod(os.path.join(scripts_dir, f), 0o755)
                    
                    self.after(0, lambda: self.update_status("✓ UPDATED"))
                    
                    # Restart PD if it was running
                    if self.app.pd_manager.is_running():
                        self.after(2000, self.app.pd_manager.restart_pd)
                else:
                    self.after(0, lambda: self.update_status("✗ RESET FAILED", error=True))
            
            except subprocess.TimeoutExpired:
                self.after(0, lambda: self.update_status("✗ TIMEOUT", error=True))
            except Exception as e:
                self.after(0, lambda: self.update_status("✗ ERROR", error=True))
            
            self.after(0, self._finish_update)
        
        threading.Thread(target=do_update, daemon=True).start()
    
    def _finish_update(self):
        """Re-enable button after update"""
        self.updating = False
        if self.update_button:
            self.update_button.config(fg="#ffffff")
    
    def shutdown(self):
        """Shutdown the system"""
        self.update_status("SHUTTING DOWN...")
        self.app.cleanup()
        self.after(500, lambda: subprocess.run(['sudo', 'shutdown', '-h', 'now']))
    
    def update_status(self, message, error=False):
        """Update status label"""
        color = "#e74c3c" if error else "#606060"
        self.status.config(text=message.upper(), fg=color)
        # No need to force update - will happen naturally
    
    def on_show(self):
        """Called when this screen becomes visible"""
        # Refresh button state when returning to control panel
        self.refresh_button_state()
