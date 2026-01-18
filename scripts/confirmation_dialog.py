"""
Confirmation Dialog - Reusable YES/NO confirmation with auto-timeout
Prevents unintentional touches with clear buttons and countdown
"""
import tkinter as tk
from tkinter import font as tkfont
from fonts import BIG_FONT_PT, FONT_FAMILY_PRIMARY, FONT_FAMILY_FALLBACK


class ConfirmationDialog:
    """
    Modal confirmation dialog with YES/NO buttons and auto-timeout
    
    Features:
    - Large, touchscreen-friendly buttons
    - 10-second auto-timeout (defaults to NO)
    - Visual countdown timer
    - Modal (blocks other UI interaction)
    - Centered on screen
    - Matches Molipe visual style
    """
    
    def __init__(self, parent, message, timeout=10, title="Confirm"):
        """
        Create confirmation dialog
        
        Args:
            parent: Parent widget (usually root window or frame)
            message: Message to display (can be multi-line)
            timeout: Seconds before auto-close (default 10)
            title: Dialog title (default "Confirm")
        """
        self.result = False  # Default to NO/cancel
        self.timeout = timeout
        self.remaining = timeout
        
        # Create modal dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        
        # Modal setup
        self.dialog.transient(parent)
        
        # Dialog styling
        self.dialog.configure(bg="#000000")
        
        # Dialog size (touchscreen-friendly)
        dialog_width = 800
        dialog_height = 400
        
        # Force window update before positioning (helps with RPi)
        self.dialog.update_idletasks()
        
        # Center on screen
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # Setup fonts
        self._setup_fonts()
        
        # Build UI
        self._build_ui(message)
        
        # Hide cursor on dialog too
        self.dialog.config(cursor="none")
        
        # CRITICAL FOR RPI: Force dialog to front and grab focus
        self.dialog.attributes("-topmost", True)  # Always on top
        self.dialog.lift()  # Raise to top
        self.dialog.focus_force()  # Force keyboard focus
        self.dialog.grab_set()  # Modal grab (after UI is built)
        
        # Force another update to ensure visibility on RPi
        self.dialog.update_idletasks()
        
        # Start countdown
        self._update_countdown()
        
        # Make dialog modal and wait for result
        self.dialog.wait_window()
    
    def _setup_fonts(self):
        """Setup fonts with fallback - all using BIG_FONT_PT from fonts.py"""
        try:
            # Message text - same size as big buttons
            self.message_font = tkfont.Font(
                family=FONT_FAMILY_PRIMARY, size=BIG_FONT_PT, weight="normal"
            )
            # Button text - same size as big buttons
            self.button_font = tkfont.Font(
                family=FONT_FAMILY_PRIMARY, size=BIG_FONT_PT, weight="bold"
            )
        except:
            # Fallback to default fonts
            self.message_font = tkfont.Font(
                family=FONT_FAMILY_FALLBACK, size=BIG_FONT_PT, weight="normal"
            )
            self.button_font = tkfont.Font(
                family=FONT_FAMILY_FALLBACK, size=BIG_FONT_PT, weight="bold"
            )
    
    def _build_ui(self, message):
        """Build dialog UI"""
        
        # Main container with border
        main_frame = tk.Frame(
            self.dialog,
            bg="#1a1a1a",
            bd=0,
            highlightthickness=2,
            highlightbackground="#ffffff"
        )
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Message area
        message_frame = tk.Frame(main_frame, bg="#1a1a1a")
        message_frame.pack(fill="both", expand=True, padx=40, pady=(40, 20))
        
        message_label = tk.Label(
            message_frame,
            text=message,
            font=self.message_font,
            bg="#1a1a1a",
            fg="#ffffff",
            wraplength=700,  # Wrap long messages
            justify="center"
        )
        message_label.pack(expand=True)
        
        # Button area
        button_frame = tk.Frame(main_frame, bg="#1a1a1a")
        button_frame.pack(fill="x", padx=40, pady=(0, 40))
        
        # Configure button columns
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=0, minsize=20)  # Spacer
        button_frame.columnconfigure(2, weight=1)
        
        # NO button (left) - Red background for danger
        no_button = tk.Label(
            button_frame,
            text="NO",
            font=self.button_font,
            bg="#2c2c2c",
            fg="#ffffff",
            cursor="hand2",
            bd=0,
            relief="flat",
            padx=40,
            pady=20
        )
        no_button.grid(row=0, column=0, sticky="ew")
        no_button.bind("<Button-1>", lambda e: self._on_no())
        
        # Hover effect for NO button
        def no_enter(e):
            no_button.config(bg="#3c3c3c")
        def no_leave(e):
            no_button.config(bg="#2c2c2c")
        no_button.bind("<Enter>", no_enter)
        no_button.bind("<Leave>", no_leave)
        
        # YES button (right) - Orange background for confirmation
        yes_button = tk.Label(
            button_frame,
            text="YES",
            font=self.button_font,
            bg="#cc5500",  # Dark orange
            fg="#ffffff",
            cursor="hand2",
            bd=0,
            relief="flat",
            padx=40,
            pady=20
        )
        yes_button.grid(row=0, column=2, sticky="ew")
        yes_button.bind("<Button-1>", lambda e: self._on_yes())
        
        # Hover effect for YES button
        def yes_enter(e):
            yes_button.config(bg="#ff6600")  # Lighter orange on hover
        def yes_leave(e):
            yes_button.config(bg="#cc5500")
        yes_button.bind("<Enter>", yes_enter)
        yes_button.bind("<Leave>", yes_leave)
        
        # ESC key closes with NO
        self.dialog.bind("<Escape>", lambda e: self._on_no())
    
    def _update_countdown(self):
        """Update countdown timer (silent - no visual feedback)"""
        if self.remaining > 0:
            self.remaining -= 1
            # Schedule next update
            self.dialog.after(1000, self._update_countdown)
        else:
            # Timeout reached - auto-close with NO
            self._on_timeout()
    
    def _on_yes(self):
        """User clicked YES"""
        self.result = True
        self.dialog.destroy()
    
    def _on_no(self):
        """User clicked NO"""
        self.result = False
        self.dialog.destroy()
    
    def _on_timeout(self):
        """Timeout reached - default to NO"""
        self.result = False
        self.dialog.destroy()
    
    def get_result(self):
        """Get the dialog result (True=YES, False=NO/timeout)"""
        return self.result


def show_confirmation(parent, message, timeout=10, title="Confirm"):
    """
    Show confirmation dialog with YES/NO buttons and auto-timeout
    
    Args:
        parent: Parent widget (usually root window or frame)
        message: Message to display
        timeout: Seconds before auto-close (default 10)
        title: Dialog title (default "Confirm")
    
    Returns:
        bool: True if user clicked YES, False if NO or timeout
    
    Example:
        result = show_confirmation(
            parent=self,
            message="Are you sure you want to duplicate 'drum-beat'?",
            timeout=10
        )
        if result:
            # User confirmed
            duplicate_project()
        else:
            # User cancelled or timeout
            return
    """
    dialog = ConfirmationDialog(parent, message, timeout, title)
    return dialog.get_result()


# Test function for standalone testing
if __name__ == "__main__":
    def test_dialog():
        """Test the confirmation dialog"""
        root = tk.Tk()
        root.geometry("1280x720")
        root.configure(bg="#000000")
        
        def show_test():
            result = show_confirmation(
                parent=root,
                message="Are you sure you want to test this confirmation dialog?\n\nThis is a multi-line message.",
                timeout=10,
                title="Test Confirmation"
            )
            print(f"Dialog result: {result}")
            if result:
                test_label.config(text="User clicked YES ✓", fg="#00ff00")
            else:
                test_label.config(text="User clicked NO or timeout ✗", fg="#ff0000")
        
        # Test button
        test_button = tk.Button(
            root,
            text="SHOW CONFIRMATION DIALOG",
            command=show_test,
            font=(FONT_FAMILY_PRIMARY, BIG_FONT_PT, "bold"),
            bg="#cc5500",
            fg="#ffffff",
            padx=20,
            pady=20
        )
        test_button.pack(expand=True)
        
        test_label = tk.Label(
            root,
            text="Click button to test dialog",
            font=(FONT_FAMILY_PRIMARY, BIG_FONT_PT),
            bg="#000000",
            fg="#ffffff"
        )
        test_label.pack(pady=20)
        
        root.mainloop()
    
    test_dialog()