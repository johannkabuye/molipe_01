"""
Browser Screen - Page-based navigation with GitHub integration
"""
import tkinter as tk
import os
import sys
import threading

# Import project duplicator and github manager
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
from project_duplicator import duplicate_project
import github_manager

# Grid configuration (same as patch display and control panel)
DEFAULT_ROWS = 11
COLS_PER_ROW = [4, 4, 4, 8, 4, 4, 4, 8, 4, 8, 8]
ROW_HEIGHTS = [60, 210, 50, 0, 0, 210, 50, 5, 20, 50, 50]
PATCHES_PER_PAGE = 8

class BrowserScreen(tk.Frame):
    """Project browser with page-based navigation and GitHub sync"""
    
    def __init__(self, parent, app):
        super().__init__(parent, bg="#000000")
        self.app = app
        
        self.rows = DEFAULT_ROWS
        self.cols_per_row = list(COLS_PER_ROW)
        
        # State
        self.projects = []
        self.current_page = 0
        self.total_pages = 0
        self.selected_project_index = None  # None = nothing selected
        self.has_github_config = False  # Track if my_projects has github_config
        
        # UI references
        self.cell_frames = []
        self.project_labels = []
        self.page_label = None
        self.sync_status_label = None  # NEW: Status indicator for sync operations
        self.load_button = None
        self.duplicate_button = None
        self.sync_button = None  # NEW: GitHub sync button
        self.prev_button = None
        self.next_button = None
        
        self._build_ui()
        
        # Initialize with content
        self.refresh_projects()
    
    def _build_ui(self):
        """Build grid-based browser UI"""
        
        # Main grid container
        container = tk.Frame(self, bg="black", bd=0, highlightthickness=0)
        container.pack(expand=True, fill="both")
        
        container.columnconfigure(0, weight=1, uniform="outer_col")
        
        self.cell_frames.clear()
        self.project_labels.clear()
        
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
                
                # Row 0, Cell 0: MENU button
                if r == 0 and c == 0:
                    menu_btn = tk.Label(
                        cell,
                        text="////<MENU",
                        bg="black", fg="white",
                        anchor="w", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small,
                        cursor="hand2"
                    )
                    menu_btn.bind("<Button-1>", lambda e: self.go_home())
                    menu_btn.pack(fill="both", expand=True)
                
                # Row 0, Cell 2: Sync status indicator
                elif r == 0 and c == 2:
                    self.sync_status_label = tk.Label(
                        cell,
                        text="",  # Empty by default
                        bg="black", fg="#606060",
                        anchor="e", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small
                    )
                    self.sync_status_label.pack(fill="both", expand=True)
                
                # Row 0, Cell 3: Page indicator (e.g., "1/8")
                elif r == 0 and c == 3:
                    self.page_label = tk.Label(
                        cell,
                        text="1/1",
                        bg="black", fg="#606060",
                        anchor="e", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small
                    )
                    self.page_label.pack(fill="both", expand=True)
                
                # Row 1: Project cells 0-3 (big font)
                elif r == 1:
                    proj_label = tk.Label(
                        cell, text="",
                        bg="black", fg="#ffffff",  # White text always
                        anchor="center", padx=5, pady=5, bd=0, highlightthickness=0,
                        font=self.app.fonts.big,
                        cursor="hand2",
                        wraplength=280,  # Wrap text if too long
                        justify="center"  # Center multi-line text
                    )
                    proj_label.pack(fill="both", expand=True)
                    proj_label.bind("<Button-1>", lambda e, idx=c: self.select_project(idx))
                    self.project_labels.append(proj_label)
                
                # Row 5: Project cells 4-7 (big font)
                elif r == 5:
                    proj_label = tk.Label(
                        cell, text="",
                        bg="black", fg="#ffffff",  # White text always
                        anchor="center", padx=5, pady=5, bd=0, highlightthickness=0,
                        font=self.app.fonts.big,
                        cursor="hand2",
                        wraplength=280,  # Wrap text if too long
                        justify="center"  # Center multi-line text
                    )
                    proj_label.pack(fill="both", expand=True)
                    proj_label.bind("<Button-1>", lambda e, idx=c+4: self.select_project(idx))
                    self.project_labels.append(proj_label)
                
                # Row 9: Navigation buttons
                elif r == 9:
                    if c == 0:
                        # PREVIOUS PAGE button
                        self.prev_button = tk.Label(
                            cell, text="◀ PREV",
                            font=self.app.fonts.small,
                            bg="#000000", fg="#ffffff",
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.prev_button.bind("<Button-1>", lambda e: self.prev_page())
                        self.prev_button.pack(fill="both", expand=True)
                    elif c == 1:
                        # NEXT PAGE button
                        self.next_button = tk.Label(
                            cell, text="NEXT ▶",
                            font=self.app.fonts.small,
                            bg="#000000", fg="#ffffff",
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.next_button.bind("<Button-1>", lambda e: self.next_page())
                        self.next_button.pack(fill="both", expand=True)
                    elif c == 5:
                        # NEW: SYNC button
                        self.sync_button = tk.Label(
                            cell, text="↻ SYNC",
                            font=self.app.fonts.small,
                            bg="#000000", fg="#303030",  # Start dark grey (disabled)
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.sync_button.bind("<Button-1>", lambda e: self.sync_selected_project())
                        self.sync_button.pack(fill="both", expand=True)
                    elif c == 6:
                        # DUPLICATE button
                        self.duplicate_button = tk.Label(
                            cell, text="⊕ DUPLICATE",
                            font=self.app.fonts.small,
                            bg="#000000", fg="#303030",  # Start dark grey (disabled)
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.duplicate_button.bind("<Button-1>", lambda e: self.duplicate_selected_project())
                        self.duplicate_button.pack(fill="both", expand=True)
                    elif c == 7:
                        # LOAD button (last column)
                        self.load_button = tk.Label(
                            cell, text="▶ LOAD",
                            font=self.app.fonts.small,
                            bg="#000000", fg="#303030",  # Start dark grey (disabled)
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.load_button.bind("<Button-1>", lambda e: self.load_selected_project())
                        self.load_button.pack(fill="both", expand=True)
            
            self.cell_frames.append(row_cells)
    
    def refresh_projects(self):
        """Scan my_projects directory for project folders and check GitHub status"""
        self.projects = []
        self.selected_project_index = None
        
        # Scan my_projects directory (inside molipe_root, same level as scripts)
        projects_dir = os.path.join(self.app.molipe_root, "my_projects")
        
        # Check if projects directory exists
        if not os.path.exists(projects_dir):
            self.projects = []
            self.current_page = 0
            self.total_pages = 0
            self.update_display()
            return
        
        # Check if github_config exists at TOP level (my_projects/github_config)
        has_github_top_level = github_manager.has_github_config(projects_dir)
        self.has_github_config = has_github_top_level  # Store at browser level
        
        # Scan for project folders (subfolders with main.pd)
        try:
            for item in sorted(os.listdir(projects_dir)):
                item_path = os.path.join(projects_dir, item)
                
                # Skip hidden folders and files (starting with .)
                if item.startswith('.'):
                    continue
                
                # Skip github_config file
                if item == 'github_config':
                    continue
                
                # Only include directories
                if os.path.isdir(item_path):
                    # Check if main.pd exists
                    main_pd = os.path.join(item_path, "main.pd")
                    
                    if os.path.exists(main_pd):
                        self.projects.append({
                            'name': item,
                            'path': main_pd,
                            'folder_path': item_path
                        })
                    else:
                        # Show folder but mark as missing main.pd
                        self.projects.append({
                            'name': f"{item} (!)",
                            'path': None,
                            'folder_path': item_path
                        })
        except Exception as e:
            print(f"Error scanning projects: {e}")
        
        # Calculate total pages
        if self.projects:
            self.total_pages = (len(self.projects) + PATCHES_PER_PAGE - 1) // PATCHES_PER_PAGE
        else:
            self.total_pages = 1
        
        # Reset to first page
        self.current_page = 0
        
        self.update_display()
    
    def update_display(self):
        """Update the project display for current page"""
        # Calculate start/end indices for current page
        start_idx = self.current_page * PATCHES_PER_PAGE
        end_idx = start_idx + PATCHES_PER_PAGE
        
        # Update page label
        if self.page_label:
            page_display = f"{self.current_page + 1}/{self.total_pages}"
            self.page_label.config(text=page_display)
        
        # Update project labels
        for i in range(PATCHES_PER_PAGE):
            project_idx = start_idx + i
            
            if project_idx < len(self.projects):
                project = self.projects[project_idx]
                project_name = project['name']
                display_name = project_name  # No emoji icon
                
                # All text is white, selected gets underlined
                if self.selected_project_index == project_idx:
                    # Selected: white text with underline
                    self.project_labels[i].config(
                        text=display_name, 
                        fg="#ffffff", 
                        bg="black",
                        font=(self.app.fonts.big.actual()['family'], 
                              self.app.fonts.big.actual()['size'], 
                              "bold underline")
                    )
                else:
                    # Unselected: white text, no underline
                    self.project_labels[i].config(
                        text=display_name, 
                        fg="#ffffff", 
                        bg="black",
                        font=self.app.fonts.big
                    )
            else:
                # Empty cell
                self.project_labels[i].config(
                    text="", 
                    fg="#606060", 
                    bg="black",
                    font=self.app.fonts.big
                )
        
        # Update action buttons
        self.update_action_buttons()
        
        # Update navigation button states
        self.update_nav_buttons()
    
    def update_action_buttons(self):
        """Update LOAD, DUPLICATE, and SYNC button colors based on selection and internet"""
        # Use app-level internet status
        has_internet = getattr(self.app, 'has_internet', True)
        
        if self.selected_project_index is not None:
            # Something selected - LOAD and DUPLICATE enabled
            if self.load_button:
                self.load_button.config(fg="#ffffff")
            if self.duplicate_button:
                self.duplicate_button.config(fg="#ffffff")
        else:
            # Nothing selected - LOAD and DUPLICATE disabled
            if self.load_button:
                self.load_button.config(fg="#303030")
            if self.duplicate_button:
                self.duplicate_button.config(fg="#303030")
        
        # SYNC is independent of selection - only depends on github_config and internet
        if self.sync_button:
            if self.has_github_config and has_internet:
                self.sync_button.config(fg="#ffffff")  # Enabled (white)
            else:
                self.sync_button.config(fg="#303030")  # Disabled (dark grey)
    
    def update_nav_buttons(self):
        """Update PREV/NEXT button states"""
        if self.prev_button:
            if self.current_page > 0:
                self.prev_button.config(fg="#ffffff")  # Enabled
            else:
                self.prev_button.config(fg="#303030")  # Disabled (first page)
        
        if self.next_button:
            if self.current_page < self.total_pages - 1:
                self.next_button.config(fg="#ffffff")  # Enabled
            else:
                self.next_button.config(fg="#303030")  # Disabled (last page)
    
    def select_project(self, display_idx):
        """Select a project by clicking on it (display_idx is 0-7 on current page)"""
        start_idx = self.current_page * PATCHES_PER_PAGE
        project_idx = start_idx + display_idx
        
        # Only select if it's a valid project
        if project_idx < len(self.projects):
            self.selected_project_index = project_idx
            self.update_display()
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.selected_project_index = None  # Clear selection on page change
            self.update_display()
    
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.selected_project_index = None  # Clear selection on page change
            self.update_display()
    
    def load_selected_project(self):
        """Load the selected project"""
        # Only load if something is selected
        if self.selected_project_index is None:
            print("No project selected")
            return
        
        if not self.projects:
            return
        
        selected_project = self.projects[self.selected_project_index]
        main_pd_path = selected_project['path']
        
        if main_pd_path is None:
            print("No main.pd found for this project")
            return
        
        if not os.path.exists(main_pd_path):
            print("main.pd file not found")
            return
        
        # Start Pure Data
        print(f"Loading: {selected_project['name']}")
        
        if self.app.pd_manager.start_pd(main_pd_path):
            # Switch to patch display
            self.after(500, lambda: self.app.show_screen('patch'))
        else:
            print("Failed to load project")
    
    def duplicate_selected_project(self):
        """Duplicate the selected project with Zettelkasten-style naming and visual feedback"""
        # Only duplicate if something is selected
        if self.selected_project_index is None:
            print("No project selected")
            self.show_sync_status("NO PROJECT", error=True, duration=3000)
            return
        
        if not self.projects:
            return
        
        selected_project = self.projects[self.selected_project_index]
        source_name = selected_project['name']
        
        # Remove the " (!)" suffix if present
        if source_name.endswith(" (!)"):
            source_name = source_name[:-4]
        
        print(f"Duplicating: {source_name}")
        self.show_sync_status("DUPLICATING...", syncing=True)
        
        # Call duplicator in background thread
        projects_dir = os.path.join(self.app.molipe_root, "my_projects")
        
        def do_duplicate():
            success, result = duplicate_project(projects_dir, source_name)
            
            # Update UI from main thread
            if success:
                print(f"✓ Duplicated successfully: {result}")
                self.after(0, lambda: self.show_sync_status("✓ DUPLICATED", error=False, duration=3000))
                
                # Refresh the browser to show new project
                self.after(100, lambda: self.refresh_and_select_new_project(result))
            else:
                print(f"✗ Duplication failed: {result}")
                error_msg = result[:20] if len(result) > 20 else result  # Truncate long errors
                self.after(0, lambda: self.show_sync_status(f"FAILED", error=True, duration=5000))
        
        threading.Thread(target=do_duplicate, daemon=True).start()
    
    def refresh_and_select_new_project(self, new_project_name):
        """Refresh browser and select the newly created project"""
        self.refresh_projects()
        
        # Try to find and select the new project
        for i, proj in enumerate(self.projects):
            if proj['name'] == new_project_name:
                self.selected_project_index = i
                # Calculate which page it's on
                self.current_page = i // PATCHES_PER_PAGE
                break
        
        self.update_display()
    
    def sync_selected_project(self):
        """Sync entire my_projects folder to GitHub with visual feedback"""
        # Check internet connectivity (use app-level status)
        has_internet = getattr(self.app, 'has_internet', True)
        if not has_internet:
            print("Cannot sync: No internet connection")
            self.show_sync_status("OFFLINE", error=True, duration=3000)
            return
        
        # Check if github_config exists at my_projects level
        if not self.has_github_config:
            print("No GitHub configuration found in my_projects folder")
            self.show_sync_status("NO CONFIG", error=True, duration=3000)
            return
        
        # Show syncing status
        self.show_sync_status("SYNCING...", syncing=True)
        
        # Sync the ENTIRE my_projects folder (not individual project)
        projects_dir = os.path.join(self.app.molipe_root, "my_projects")
        
        print(f"Syncing my_projects to GitHub...")
        
        # Run sync in background thread so UI doesn't freeze
        def do_sync():
            success, message = github_manager.sync_project(projects_dir)
            
            # Update UI from main thread
            if success:
                print(f"✓ {message}")
                self.after(0, lambda: self.show_sync_status("✓ SYNCED", error=False, duration=3000))
            else:
                print(f"✗ Sync failed: {message}")
                self.after(0, lambda: self.show_sync_status("SYNC FAILED", error=True, duration=5000))
        
        threading.Thread(target=do_sync, daemon=True).start()
    
    def show_sync_status(self, message, error=False, syncing=False, duration=None):
        """Show sync status in upper right corner"""
        if not self.sync_status_label:
            return
        
        # Choose color based on status
        if error:
            color = "#e74c3c"  # Red for errors
        elif syncing:
            color = "#f39c12"  # Orange for in-progress
        else:
            color = "#27ae60"  # Green for success
        
        self.sync_status_label.config(text=message, fg=color)
        
        # Clear status after duration (if specified)
        if duration:
            self.after(duration, lambda: self.sync_status_label.config(text=""))
    
    def go_home(self):
        """Return to control panel"""
        self.app.show_screen('control')
    
    def on_show(self):
        """Called when screen becomes visible"""
        self.refresh_projects()