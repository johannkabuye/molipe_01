#!/usr/bin/env python3
"""
Molipe Control Panel
System control interface matching main GUI design
"""

import tkinter as tk
from tkinter import messagebox, font as tkfont
import subprocess
import os

# Font configuration (matching main GUI)
FONT_FAMILY_PRIMARY = "Sunflower"
FONT_FAMILY_FALLBACK = "TkDefaultFont"
TITLE_FONT_SIZE = 48
BUTTON_FONT_SIZE = 20
STATUS_FONT_SIZE = 14

class MolipeControl:
    def __init__(self, root):
        self.root = root
        self.root.title("")
        
        # Fullscreen setup (matching main GUI)
        self.root.overrideredirect(True)
        self.root.attributes("-fullscreen", True)
        self.root.config(cursor="none")
        self.root.configure(bg="#000000")
        
        # Track processes
        self.pd_process = None
        self.gui_process = None
        
        # Paths - adjust these
        self.pd_patch = "/home/patch/molipe/main.pd"
        self.gui_script = "/home/patch/molipe/molipe_gui.py"
        self.repo_path = "/home/patch/molipe"
        
        # Initialize fonts with fallback
        self._init_fonts()
        
        # Build UI
        self._build_ui()
        
        # Keyboard bindings
        self.root.bind("<Escape>", lambda e: self.exit_app())
    
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
    
    def _build_ui(self):
        """Build the control panel UI."""
        # Main container
        container = tk.Frame(self.root, bg="#000000")
        container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Title
        title = tk.Label(
            container,
            text="MOLIPE",
            font=self.title_font,
            bg="#000000",
            fg="#ffffff"
        )
        title.pack(pady=(0, 60))
        
        # Button configuration
        button_config = {
            'font': self.button_font,
            'width': 20,
            'height': 2,
            'bd': 0,
            'relief': 'flat',
            'cursor': 'none'
        }
        
        # Launch Molipe button
        self.launch_btn = tk.Button(
            container,
            text="▶ LAUNCH",
            command=self.launch_molipe,
            bg="#27ae60",
            fg="#ffffff",
            activebackground="#229954",
            activeforeground="#ffffff",
            **button_config
        )
        self.launch_btn.pack(pady=10)
        
        # Restart Pure Data button
        tk.Button(
            container,
            text="↻ RESTART PD",
            command=self.restart_pd,
            bg="#f39c12",
            fg="#ffffff",
            activebackground="#e67e22",
            activeforeground="#ffffff",
            **button_config
        ).pack(pady=10)
        
        # Git Pull button
        tk.Button(
            container,
            text="↻ GIT PULL",
            command=self.git_pull,
            bg="#3498db",
            fg="#ffffff",
            activebackground="#2980b9",
            activeforeground="#ffffff",
            **button_config
        ).pack(pady=10)
        
        # Reboot button
        tk.Button(
            container,
            text="⟲ REBOOT",
            command=self.reboot,
            bg="#e67e22",
            fg="#ffffff",
            activebackground="#d35400",
            activeforeground="#ffffff",
            **button_config
        ).pack(pady=10)
        
        # Shutdown button
        tk.Button(
            container,
            text="⏻ SHUTDOWN",
            command=self.shutdown,
            bg="#e74c3c",
            fg="#ffffff",
            activebackground="#c0392b",
            activeforeground="#ffffff",
            **button_config
        ).pack(pady=10)
        
        # Status label
        self.status = tk.Label(
            container,
            text="READY",
            font=self.status_font,
            bg="#000000",
            fg="#606060"
        )
        self.status.pack(pady=(40, 0))
    
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
            self.update_status(f"PD RESTARTED (PID: {self.pd_process.pid})")
        except Exception as e:
            self.update_status(f"ERROR: {e}", error=True)
    
    def git_pull(self):
        """Update from git repository"""
        self.update_status("GIT PULLING...")
        
        try:
            result = subprocess.run(
                ['git', 'pull'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                if "Already up to date" in result.stdout:
                    self.update_status("UP TO DATE")
                else:
                    self.update_status("UPDATED")
                    # Auto restart PD after successful update
                    self.root.after(1000, self.restart_pd)
            else:
                self.update_status("GIT FAILED", error=True)
                
        except Exception as e:
            self.update_status(f"ERROR: {e}", error=True)
    
    def shutdown(self):
        """Shutdown the system"""
        self.update_status("SHUTTING DOWN...")
        self.cleanup()
        self.root.after(500, lambda: subprocess.run(['sudo', 'shutdown', '-h', 'now']))
    
    def reboot(self):
        """Reboot the system"""
        self.update_status("REBOOTING...")
        self.cleanup()
        self.root.after(500, lambda: subprocess.run(['sudo', 'reboot']))
    
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