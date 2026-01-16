#!/usr/bin/env python3
"""
Molipe Application
Modular audio production system with Pure Data integration

Main orchestrator that manages screens and navigation
"""
import tkinter as tk
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from screen_control import ControlScreen
from screen_browser import BrowserScreen
from screen_patch_display import PatchDisplayScreen
from fonts import FontManager
from process_manager import ProcessManager


class MolipeApp:
    """Main application - orchestrates screens and navigation"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("")
        
        # Paths - detect platform
        if sys.platform.startswith("linux"):
            # On Linux/RPi: /home/patch/Desktop/molipe_01
            self.molipe_root = "/home/patch/Desktop/molipe_01"
        else:
            # On macOS: go up one level from scripts/ to molipe_01/
            scripts_dir = os.path.dirname(os.path.abspath(__file__))
            self.molipe_root = os.path.dirname(scripts_dir)
        
        # Initialize utilities
        self.fonts = FontManager()
        self.pd_manager = ProcessManager()
        
        # Setup window
        self._setup_window()
        
        # Create all screens
        self.screens = {}
        self._create_screens()
        
        # Show initial screen
        self.current_screen = None
        self.show_screen('control')
        
        # Keyboard bindings
        self.root.bind("<Escape>", lambda e: self.on_escape())
        
        # Enforce cursor hiding periodically (some systems re-enable it)
        self._enforce_cursor_hiding()
    
    def _setup_window(self):
        """Setup main window properties"""
        # Set geometry
        if sys.platform.startswith("linux"):
            self.root.geometry("1280x720+0+0")
        else:
            self.root.geometry("1280x720+100+100")
        
        # Fullscreen setup
        self.root.overrideredirect(True)
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)  # Always on top
        
        # Create blank cursor (more reliable than cursor="none" on touchscreens)
        self._create_blank_cursor()
        
        self.root.configure(bg="#000000")
    
    def _create_blank_cursor(self):
        """Create a blank cursor (more reliable than cursor='none' on touchscreens)"""
        try:
            if sys.platform.startswith("linux"):
                # On Linux: Create a truly blank cursor using X11
                # This is more reliable than cursor="none" for touchscreens
                blank_cursor = "none"
                self.root.config(cursor=blank_cursor)
                
                # Additional X11 approach - set blank cursor via bind
                # This catches cursor re-appearances from touch events
                def hide_cursor(event=None):
                    self.root.config(cursor="none")
                    return "break"
                
                # Bind to all possible cursor-showing events
                self.root.bind("<Motion>", hide_cursor)
                self.root.bind("<Button-1>", hide_cursor)
                self.root.bind("<ButtonRelease-1>", hide_cursor)
            else:
                # On macOS/other
                self.root.config(cursor="none")
        except Exception as e:
            print(f"Cursor hiding setup failed: {e}")
            # Fallback
            self.root.config(cursor="none")
    
    def _enforce_cursor_hiding(self):
        """Periodically enforce cursor hiding (touchscreens can re-enable it)"""
        try:
            self.root.config(cursor="none")
            # Also set on all screens
            for screen in self.screens.values():
                screen.config(cursor="none")
        except:
            pass  # Ignore errors during startup
        # Re-check every 100ms (more aggressive)
        self.root.after(100, self._enforce_cursor_hiding)
    
    def _create_screens(self):
        """Create all screen instances"""
        self.screens['control'] = ControlScreen(self.root, self)
        self.screens['browser'] = BrowserScreen(self.root, self)
        self.screens['patch'] = PatchDisplayScreen(self.root, self)
    
    def show_screen(self, name):
        """
        Show a screen by name
        
        Args:
            name: 'control', 'browser', or 'patch'
        """
        if name not in self.screens:
            print(f"Warning: Unknown screen '{name}'")
            return
        
        new_screen = self.screens[name]
        
        # Strategy: Pack new screen FIRST (on top of old one)
        # Then prepare content, then hide old screens
        # This prevents grey flicker
        
        # Pack the new screen immediately
        new_screen.pack(fill="both", expand=True)
        
        # Prepare content (now that it's packed, widgets exist in the layout)
        if hasattr(new_screen, 'on_show'):
            new_screen.on_show()
        
        # Force rendering to complete
        new_screen.update_idletasks()
        
        # Now hide all OTHER screens (new screen is already visible)
        for screen_name, screen in self.screens.items():
            if screen_name != name:
                screen.pack_forget()
        
        self.current_screen = name
        
        # Update control panel button state
        if name != 'control' and 'control' in self.screens:
            self.screens['control'].refresh_button_state()
    
    def on_escape(self):
        """Handle ESC key press"""
        # ESC always goes home (control panel)
        if self.current_screen != 'control':
            self.show_screen('control')
        else:
            # ESC on control panel exits app
            self.cleanup()
            self.root.destroy()
    
    def cleanup(self):
        """Clean shutdown of all resources"""
        self.pd_manager.cleanup()
    
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.cleanup()


def main():
    """Application entry point"""
    root = tk.Tk()
    app = MolipeApp(root)
    
    # Handle window close
    def on_closing():
        app.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Run application
    app.run()


if __name__ == "__main__":
    main()