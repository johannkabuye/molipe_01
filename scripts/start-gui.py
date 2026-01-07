#!/usr/bin/env python3
"""
Molipe Control Panel
System control interface matching main GUI design
"""

import tkinter as tk
from tkinter import font as tkfont
import subprocess
import sys
import os
import socket
import shutil
from pathlib import Path
import threading

# Font configuration (matching main GUI)
FONT_FAMILY_PRIMARY = "Sunflower"
FONT_FAMILY_FALLBACK = "TkDefaultFont"
TITLE_FONT_SIZE = 48
BUTTON_FONT_SIZE = 20
STATUS_FONT_SIZE = 14

# Connectivity check interval (milliseconds)
INTERNET_CHECK_INTERVAL = 10000  # 10 seconds

class MolipeControl:
    def __init__(self, root):
        self.root = root
        self.root.title("")
        
        # Track processes
        self.pd_process = None
        self.gui_process = None
        self.pd_running = False
        self.updating = False  # Track if update is in progress
        
        # Paths - adjust these
        self.pd_patch = "/home/patch/molipe_01/main.pd"
        self.gui_script = "/home/patch/molipe_01/molipe_gui.py"
        self.repo_path = str(Path.home() / "molipe_01")  # ~/molipe_01
        self.backup_path = str(Path.home() / "molipe_01.backup")
        
        # Check internet connectivity
        self.has_internet = self.check_internet()
        
        # Initialize fonts with fallback
        self._init_fonts()
        
        # Store reference to container for dynamic UI updates
        self.container = None
        self.update_button = None
        self.no_internet_label = None
        
        # Build UI (includes geometry setup)
        self._build_ui()
        
        # Fullscreen setup (matching main GUI) - after geometry is set
        self.root.overrideredirect(True)
        self.root.attributes("-fullscreen", True)
        self.root.config(cursor="none")
        self.root.configure(bg="#000000")
        
        # Keyboard bindings
        self.root.bind("<Escape>", lambda e: self.exit_app())
        
        # Start periodic internet connectivity check
        self.check_connectivity_periodically()
    
    def check_internet(self, host="8.8.8.8", port=53, timeout=3):
        """
        Check if internet connection is available.
        Tries to connect to Google's DNS server.
        """
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except socket.error:
            return False
    
    def check_connectivity_periodically(self):
        """Periodically check internet connectivity and update UI"""
        old_status = self.has_internet
        self.has_internet = self.check_internet()
        
        # If status changed, update UI
        if old_status != self.has_internet:
            self._update_connectivity_ui()
        
        # Schedule next check
        self.root.after(INTERNET_CHECK_INTERVAL, self.check_connectivity_periodically)
    
    def _update_connectivity_ui(self):
        """Update UI based on connectivity status change"""
        if self.has_internet:
            # Internet connected - show update button
            if self.no_internet_label:
                self.no_internet_label.grid_forget()
                self.no_internet_label.destroy()
                self.no_internet_label = None
            
            if not self.update_button:
                self.update_button = self._create_button(
                    self.container,
                    "↻ UPDATE\nPROJECTS",
                    self.update_projects
                )
                self.update_button.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
            
            # Update status if not currently doing something
            if not self.updating and not self.pd_running:
                self.update_status("ONLINE")
        else:
            # Internet disconnected - show no internet label
            if self.update_button:
                self.update_button.grid_forget()
                self.update_button.destroy()
                self.update_button = None
            
            if not self.no_internet_label:
                self.no_internet_label = tk.Label(
                    self.container,
                    text="NO\nINTERNET",
                    font=self.button_font,
                    bg="#000000",
                    fg="#303030",
                    cursor="none",
                    bd=0,
                    relief="flat",
                    padx=20,
                    pady=20
                )
                self.no_internet_label.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
            
            # Update status if not currently doing something
            if not self.updating and not self.pd_running:
                self.update_status("OFFLINE MODE")
    
    def _init_fonts(self):
        """Initialize fonts with fallback handling."""
        try:
            self.title_font = tkfont.Font(
                family=FONT_FAMILY_PRIMARY,
                size=TITLE_FONT_SIZE,
                weight="bold"
            )
            self.button_font = tkfont.Font(
                family=FONT_FAMILY_PRIMARY,
                size=BUTTON_FONT_SIZE,
                weight="bold"
            )
            self.status_font = tkfont.Font(
                family=FONT_FAMILY_PRIMARY,
                size=STATUS_FONT_SIZE,
                weight="normal"
            )
        except Exception:
            self.title_font = tkfont.Font(
                family=FONT_FAMILY_FALLBACK,
                size=TITLE_FONT_SIZE,
                weight="bold"
            )
            self.button_font = tkfont.Font(
                family=FONT_FAMILY_FALLBACK,
                size=BUTTON_FONT_SIZE,
                weight="bold"
            )
            self.status_font = tkfont.Font(
                family=FONT_FAMILY_FALLBACK,
                size=STATUS_FONT_SIZE,
                weight="normal"
            )
    
    def _create_button(self, parent, text, command):
        """Create a custom button using Label (works on macOS)"""
        btn = tk.Label(
            parent,
            text=text,
            font=self.button_font,
            bg="#000000",
            fg="#ffffff",
            cursor="none",
            bd=0,
            relief="flat",
            padx=20,
            pady=20
        )
        btn.bind("<Button-1>", lambda e: command())
        return btn
    
    def _build_ui(self):
        """Build the control panel UI."""
        # Set geometry to match main GUI
        if sys.platform.startswith("linux"):
            self.root.geometry("1280x720+0+0")
        else:
            self.root.geometry("1280x720+100+100")  # MacBook positioning
        
        # Main container
        self.container = tk.Frame(self.root, bg="#000000")
        self.container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Title
        title = tk.Label(
            self.container,
            text="MOLIPE",
            font=self.title_font,
            bg="#000000",
            fg="#ffffff"
        )
        title.grid(row=0, column=0, columnspan=4, pady=(0, 60))
        
        # Configure grid columns (4 columns, equal width)
        for i in range(4):
            self.container.columnconfigure(i, weight=1, uniform="button_col")
        
        # Row 1: Start/Restart button always shown
        self.start_button = self._create_button(
            self.container,
            "▶ START",
            self.start_restart_molipe
        )
        self.start_button.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        # Update button only if internet is available
        if self.has_internet:
            self.update_button = self._create_button(
                self.container,
                "↻ UPDATE\nPROJECTS",
                self.update_projects
            )
            self.update_button.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        else:
            # Show "no internet" placeholder
            self.no_internet_label = tk.Label(
                self.container,
                text="NO\nINTERNET",
                font=self.button_font,
                bg="#000000",
                fg="#303030",
                cursor="none",
                bd=0,
                relief="flat",
                padx=20,
                pady=20
            )
            self.no_internet_label.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        
        # Empty cells
        for col in range(2, 4):
            empty_frame = tk.Frame(self.container, bg="#000000", width=150, height=80)
            empty_frame.grid(row=1, column=col, padx=10, pady=10)
        
        # Row 2: Shutdown and 3 empty cells
        self._create_button(
            self.container,
            "⏻ SHUTDOWN",
            self.shutdown
        ).grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        
        # Empty cells (placeholders for future buttons)
        for col in range(1, 4):
            empty_frame = tk.Frame(self.container, bg="#000000", width=150, height=80)
            empty_frame.grid(row=2, column=col, padx=10, pady=10)
        
        # Status label (spans all 4 columns)
        status_text = "READY"
        if not self.has_internet:
            status_text = "OFFLINE MODE"
        
        self.status = tk.Label(
            self.container,
            text=status_text,
            font=self.status_font,
            bg="#000000",
            fg="#606060"
        )
        self.status.grid(row=3, column=0, columnspan=4, pady=(40, 0))
    
    def start_restart_molipe(self):
        """Start or restart Pure Data and GUI"""
        if self.pd_running:
            # Restart
            self.restart_pd()
        else:
            # Start
            self.launch_molipe()
    
    def launch_molipe(self):
        """Launch Pure Data AND GUI together"""
        # Start Pure Data
        try:
            # Kill any existing PD
            subprocess.run(['pkill', '-9', 'puredata'], stderr=subprocess.DEVNULL)
            
            # Start PD
            self.pd_process = subprocess.Popen([
                'puredata',
                '-nogui',
                '-open', self.pd_patch,
                '-audiobuf', '10',
                '-alsa'
            ])
            self.pd_running = True
            self.start_button.config(text="↻ RESTART")
            self.update_status(f"PD STARTED (PID: {self.pd_process.pid})")
        except Exception as e:
            self.update_status(f"ERROR: {e}", error=True)
            return
        
        # Start GUI
        try:
            self.gui_process = subprocess.Popen([
                'python3',
                self.gui_script
            ])
            self.update_status("MOLIPE RUNNING")
            
            # Hide control panel
            self.root.withdraw()
            
            # Monitor GUI to restore control panel when closed
            self.check_gui_status()
            
        except Exception as e:
            self.update_status(f"ERROR: {e}", error=True)
    
    def check_gui_status(self):
        """Monitor GUI and restore control panel when it closes"""
        if self.gui_process and self.gui_process.poll() is None:
            # GUI still running, check again in 500ms
            self.root.after(500, self.check_gui_status)
        else:
            # GUI closed, restore control panel
            self.root.deiconify()
            self.update_status("CONTROL PANEL")
    
    def show_control_panel(self):
        """Bring control panel to front (called from GUI via wmctrl)"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.update_status("CONTROL PANEL")
    
    def restart_pd(self):
        """Restart Pure Data"""
        try:
            # Kill old process
            if self.pd_process:
                self.pd_process.terminate()
                self.pd_process.wait(timeout=3)
            
            # Kill any stray processes
            subprocess.run(['pkill', '-9', 'puredata'], stderr=subprocess.DEVNULL)
            
            # Start fresh
            self.pd_process = subprocess.Popen([
                'puredata',
                '-nogui',
                '-open', self.pd_patch,
                '-audiobuf', '10',
                '-alsa'
            ])
            self.pd_running = True
            self.start_button.config(text="↻ RESTART")
            self.update_status(f"PD RESTARTED (PID: {self.pd_process.pid})")
        except Exception as e:
            self.update_status(f"ERROR: {e}", error=True)
    
    def create_backup(self):
        """Create backup of project before updating"""
        try:
            # Remove old backup if exists
            if os.path.exists(self.backup_path):
                shutil.rmtree(self.backup_path)
            
            # Create new backup
            shutil.copytree(self.repo_path, self.backup_path)
            return True
        except Exception as e:
            print(f"Backup failed: {e}")
            return False
    
    def update_projects(self):
        """Update projects from GitHub with backup"""
        if self.updating:
            return  # Already updating
        
        if not self.has_internet:
            self.update_status("NO INTERNET", error=True)
            return
        
        # Disable button during update
        self.updating = True
        if self.update_button:
            self.update_button.config(fg="#606060")  # Dim button
        
        self.update_status("CREATING BACKUP...")
        self.root.update()
        
        # Create backup in separate thread to not block UI
        def do_update():
            # Create backup
            backup_success = self.create_backup()
            if not backup_success:
                self.root.after(0, lambda: self.update_status("BACKUP FAILED", error=True))
                self.root.after(0, self._finish_update)
                return
            
            self.root.after(0, lambda: self.update_status("PULLING FROM GITHUB..."))
            
            # Pull from GitHub
            try:
                result = subprocess.run(
                    ['git', 'pull', 'origin', 'main'],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    if "Already up to date" in result.stdout or "Already up-to-date" in result.stdout:
                        self.root.after(0, lambda: self.update_status("✓ ALREADY UP TO DATE"))
                    else:
                        self.root.after(0, lambda: self.update_status("✓ UPDATED SUCCESSFULLY"))
                        # Auto restart PD after successful update
                        if self.pd_running:
                            self.root.after(2000, self.restart_pd)
                else:
                    error_msg = result.stderr.strip() if result.stderr else "UPDATE FAILED"
                    self.root.after(0, lambda: self.update_status(f"✗ {error_msg}", error=True))
            
            except subprocess.TimeoutExpired:
                self.root.after(0, lambda: self.update_status("✗ UPDATE TIMEOUT", error=True))
            except Exception as e:
                self.root.after(0, lambda: self.update_status(f"✗ ERROR: {str(e)}", error=True))
            
            self.root.after(0, self._finish_update)
        
        # Run update in thread
        thread = threading.Thread(target=do_update, daemon=True)
        thread.start()
    
    def _finish_update(self):
        """Re-enable button after update completes"""
        self.updating = False
        if self.update_button:
            self.update_button.config(fg="#ffffff")  # Restore button
    
    def shutdown(self):
        """Shutdown the system - NO CONFIRMATION"""
        self.update_status("SHUTTING DOWN...")
        self.cleanup()
        self.root.after(500, lambda: subprocess.run(['sudo', 'shutdown', '-h', 'now']))
    
    def exit_app(self):
        """Exit the control panel (ESC key)"""
        self.cleanup()
        self.root.destroy()
    
    def cleanup(self):
        """Clean shutdown of processes"""
        if self.pd_process:
            try:
                self.pd_process.terminate()
                self.pd_process.wait(timeout=3)
            except:
                try:
                    self.pd_process.kill()
                except:
                    pass
    
    def update_status(self, message, error=False):
        """Update status label"""
        color = "#e74c3c" if error else "#606060"
        self.status.config(text=message.upper(), fg=color)
        self.root.update()

def main():
    root = tk.Tk()
    app = MolipeControl(root)
    
    # Handle window close (shouldn't happen with overrideredirect, but just in case)
    def on_closing():
        app.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()