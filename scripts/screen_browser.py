"""
Browser Screen - Page-based navigation with GitHub integration and sorting
"""
import tkinter as tk
import os
import sys
import threading
import json
from datetime import datetime

# Import project duplicator and deleter
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
from project_duplicator import duplicate_project
from project_deleter import delete_project

# Grid configuration (same as patch display and control panel)
DEFAULT_ROWS = 11
COLS_PER_ROW = [4, 4, 4, 8, 4, 4, 4, 8, 4, 8, 8]
ROW_HEIGHTS = [60, 210, 50, 0, 0, 210, 50, 5, 20, 50, 50]
PATCHES_PER_PAGE = 8

class BrowserScreen(tk.Frame):
    """Project browser with page-based navigation and sorting"""
    
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
        
        # Sorting state
        self.sort_mode = "recent"  # "name" or "recent"
        self.sort_direction = "desc"  # "desc" or "asc"
        
        # Metadata file path (will be set in refresh_projects)
        self.metadata_file = None
        
        # UI references
        self.cell_frames = []
        self.project_labels = []
        self.page_label = None
        self.sync_status_label = None
        self.sort_mode_button = None  # NAME/RECENT button
        self.sort_dir_button = None   # Sort direction button
        self.load_button = None
        self.duplicate_button = None
        self.delete_button = None
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
                        text="////MENU",
                        bg="black", fg="white",
                        anchor="w", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small,
                        cursor="hand2"
                    )
                    menu_btn.bind("<Button-1>", lambda e: self.go_home())
                    menu_btn.pack(fill="both", expand=True)
                
                # Row 0, Cell 1: NAME/RECENT toggle button
                elif r == 0 and c == 1:
                    self.sort_mode_button = tk.Label(
                        cell,
                        text="RECENT",  # Default
                        bg="black", fg="white",
                        anchor="center", padx=5, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small,
                        cursor="hand2"
                    )
                    self.sort_mode_button.bind("<Button-1>", lambda e: self.toggle_sort_mode())
                    self.sort_mode_button.pack(fill="both", expand=True)
                
                # Row 0, Cell 2: DESC/ASC direction button
                elif r == 0 and c == 2:
                    self.sort_dir_button = tk.Label(
                        cell,
                        text="DESC",  # Default descending
                        bg="black", fg="white",
                        anchor="center", padx=5, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small,
                        cursor="hand2"
                    )
                    self.sort_dir_button.bind("<Button-1>", lambda e: self.toggle_sort_direction())
                    self.sort_dir_button.pack(fill="both", expand=True)
                
                # Row 0, Cell 3: Sync status indicator
                elif r == 0 and c == 3:
                    self.sync_status_label = tk.Label(
                        cell,
                        text="",  # Empty by default
                        bg="black", fg="#606060",
                        anchor="e", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small
                    )
                    self.sync_status_label.pack(fill="both", expand=True)
                
                # Row 1: Project cells 0-3 (left-aligned with metadata)
                elif r == 1:
                    # Create a container frame for name + metadata
                    proj_container = tk.Frame(cell, bg="black", bd=0, highlightthickness=0)
                    proj_container.pack(fill="both", expand=True, padx=5, pady=5)
                    proj_container.bind("<Button-1>", lambda e, idx=c: self.select_project(idx))
                    
                    # Project name label (big font, left-aligned)
                    proj_name = tk.Label(
                        proj_container, text="",
                        bg="black", fg="#ffffff",
                        anchor="w", padx=10, pady=5, bd=0, highlightthickness=0,  # Internal padding
                        font=self.app.fonts.big,
                        cursor="hand2",
                        wraplength=270,
                        justify="left"
                    )
                    proj_name.pack(fill="x", anchor="nw")
                    proj_name.bind("<Button-1>", lambda e, idx=c: self.select_project(idx))
                    
                    # Metadata label (metadata font, grey, left-aligned)
                    proj_meta = tk.Label(
                        proj_container, text="",
                        bg="black", fg="#606060",
                        anchor="w", padx=10, pady=5, bd=0, highlightthickness=0,  # Single value for pady
                        font=self.app.fonts.metadata,
                        cursor="hand2",
                        wraplength=250,  # Wrap text if too long
                        justify="left"   # Left-align wrapped text
                    )
                    proj_meta.pack(fill="x", anchor="nw")
                    proj_meta.bind("<Button-1>", lambda e, idx=c: self.select_project(idx))
                    
                    # Store both labels as a tuple
                    self.project_labels.append((proj_name, proj_meta))
                
                # Row 5: Project cells 4-7 (left-aligned with metadata)
                elif r == 5:
                    # Create a container frame for name + metadata
                    proj_container = tk.Frame(cell, bg="black", bd=0, highlightthickness=0)
                    proj_container.pack(fill="both", expand=True, padx=5, pady=5)
                    proj_container.bind("<Button-1>", lambda e, idx=c+4: self.select_project(idx))
                    
                    # Project name label (big font, left-aligned)
                    proj_name = tk.Label(
                        proj_container, text="",
                        bg="black", fg="#ffffff",
                        anchor="w", padx=10, pady=5, bd=0, highlightthickness=0,  # Internal padding
                        font=self.app.fonts.big,
                        cursor="hand2",
                        wraplength=270,
                        justify="left"
                    )
                    proj_name.pack(fill="x", anchor="nw")
                    proj_name.bind("<Button-1>", lambda e, idx=c+4: self.select_project(idx))
                    
                    # Metadata label (metadata font, grey, left-aligned)
                    proj_meta = tk.Label(
                        proj_container, text="",
                        bg="black", fg="#606060",
                        anchor="w", padx=10, pady=5, bd=0, highlightthickness=0,  # Single value for pady
                        font=self.app.fonts.metadata,
                        cursor="hand2",
                        wraplength=250,  # Wrap text if too long
                        justify="left"   # Left-align wrapped text
                    )
                    proj_meta.pack(fill="x", anchor="nw")
                    proj_meta.bind("<Button-1>", lambda e, idx=c+4: self.select_project(idx))
                    
                    # Store both labels as a tuple
                    self.project_labels.append((proj_name, proj_meta))
                
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
                    elif c == 2:
                        # Page indicator (moved from Row 0)
                        self.page_label = tk.Label(
                            cell,
                            text="1/1",
                            bg="black", fg="#606060",
                            anchor="center", padx=5, pady=0, bd=0, highlightthickness=0,
                            font=self.app.fonts.small
                        )
                        self.page_label.pack(fill="both", expand=True)
                    elif c == 5:
                        # DELETE button
                        self.delete_button = tk.Label(
                            cell, text="DELETE",
                            font=self.app.fonts.small,
                            bg="#000000", fg="#303030",  # Start dark grey (disabled)
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.delete_button.bind("<Button-1>", lambda e: self.delete_selected_project())
                        self.delete_button.pack(fill="both", expand=True)
                    elif c == 6:
                        # COPY button (was DUPLICATE - shorter text)
                        self.duplicate_button = tk.Label(
                            cell, text="COPY",
                            font=self.app.fonts.small,
                            bg="#000000", fg="#303030",  # Start dark grey (disabled)
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.duplicate_button.bind("<Button-1>", lambda e: self.duplicate_selected_project())
                        self.duplicate_button.pack(fill="both", expand=True)
                    elif c == 7:
                        # LOAD button (last column)
                        self.load_button = tk.Label(
                            cell, text="LOAD",
                            font=self.app.fonts.small,
                            bg="#000000", fg="#303030",  # Start dark grey (disabled)
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.load_button.bind("<Button-1>", lambda e: self.load_selected_project())
                        self.load_button.pack(fill="both", expand=True)
            
            self.cell_frames.append(row_cells)
    
    def toggle_sort_mode(self):
        """Toggle between NAME and RECENT sorting"""
        if self.sort_mode == "name":
            self.sort_mode = "recent"
            self.sort_mode_button.config(text="RECENT")
        else:
            self.sort_mode = "name"
            self.sort_mode_button.config(text="NAME")
        
        # Re-sort and refresh display
        self.sort_projects()
        self.update_display()
    
    def format_timestamp(self, timestamp_str):
        """Format timestamp as human-readable relative time"""
        if not timestamp_str:
            return "never opened"
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            diff = now - timestamp
            
            # Calculate time differences
            seconds = diff.total_seconds()
            minutes = seconds / 60
            hours = minutes / 60
            days = diff.days
            
            # Format based on time ago
            if seconds < 60:
                return "just now"
            elif minutes < 60:
                m = int(minutes)
                return f"{m} min ago" if m == 1 else f"{m} mins ago"
            elif hours < 24:
                h = int(hours)
                return f"{h} hour ago" if h == 1 else f"{h} hours ago"
            elif days < 7:
                return f"{days} day ago" if days == 1 else f"{days} days ago"
            elif days < 30:
                weeks = days // 7
                return f"{weeks} week ago" if weeks == 1 else f"{weeks} weeks ago"
            else:
                # For older items, show the date
                return timestamp.strftime("%b %d, %Y")
        except:
            return "unknown"
    
    def read_patch_data(self, project_folder_path):
        """Read musical metadata from patch_data.txt in statesave folder"""
        patch_data_file = os.path.join(project_folder_path, "statesave", "patch_data.txt")
        
        if not os.path.exists(patch_data_file):
            return []
        
        try:
            metadata_lines = []
            with open(patch_data_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines
                    if line:
                        metadata_lines.append(line)
            
            return metadata_lines
        except Exception as e:
            print(f"Error reading patch_data.txt: {e}")
            return []
    
    def toggle_sort_direction(self):
        """Toggle between descending (DESC) and ascending (ASC)"""
        if self.sort_direction == "desc":
            self.sort_direction = "asc"
            self.sort_dir_button.config(text="ASC")
        else:
            self.sort_direction = "desc"
            self.sort_dir_button.config(text="DESC")
        
        # Re-sort and refresh display
        self.sort_projects()
        self.update_display()
    
    def load_metadata(self):
        """Load metadata from .molipe_meta file"""
        if not self.metadata_file or not os.path.exists(self.metadata_file):
            return {}
        
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata: {e}")
            return {}
    
    def save_metadata(self, metadata):
        """Save metadata to .molipe_meta file"""
        if not self.metadata_file:
            return
        
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def update_project_timestamp(self, project_name):
        """Update timestamp for a project when it's opened"""
        metadata = self.load_metadata()
        metadata[project_name] = datetime.now().isoformat()
        self.save_metadata(metadata)
    
    def sort_projects(self):
        """Sort projects based on current sort mode and direction"""
        if not self.projects:
            return
        
        if self.sort_mode == "name":
            # Sort by name
            self.projects.sort(key=lambda p: p['name'].lower())
        else:
            # Sort by recent (timestamp)
            metadata = self.load_metadata()
            
            def get_timestamp(project):
                project_name = project['name']
                # Remove " (!)" suffix if present
                if project_name.endswith(" (!)"):
                    project_name = project_name[:-4]
                
                timestamp_str = metadata.get(project_name, "1970-01-01T00:00:00")
                try:
                    return datetime.fromisoformat(timestamp_str)
                except:
                    return datetime(1970, 1, 1)  # Default to epoch for projects never opened
            
            self.projects.sort(key=get_timestamp)
        
        # Reverse if descending
        if self.sort_direction == "desc":
            self.projects.reverse()
    
    def refresh_projects(self):
        """Scan my_projects directory for project folders"""
        self.projects = []
        self.selected_project_index = None
        
        # Scan my_projects directory (inside molipe_root, same level as scripts)
        projects_dir = os.path.join(self.app.molipe_root, "my_projects")
        
        # Set metadata file path
        self.metadata_file = os.path.join(projects_dir, ".molipe_meta")
        
        # Check if projects directory exists
        if not os.path.exists(projects_dir):
            self.projects = []
            self.current_page = 0
            self.total_pages = 0
            self.update_display()
            return
        
        # Scan for project folders (must have both main.pd and patch-gui.py)
        try:
            for item in sorted(os.listdir(projects_dir)):
                item_path = os.path.join(projects_dir, item)
                
                # Skip hidden folders and files (starting with .)
                if item.startswith('.'):
                    continue
                
                # Skip trash folder
                if item == 'trash':
                    continue
                
                # Only include directories
                if os.path.isdir(item_path):
                    # Check if main.pd exists
                    main_pd = os.path.join(item_path, "main.pd")
                    patch_gui = os.path.join(item_path, "patch-gui.py")
                    
                    # Valid project needs BOTH main.pd AND patch-gui.py
                    has_pd = os.path.exists(main_pd)
                    has_gui = os.path.exists(patch_gui)
                    
                    if has_pd and has_gui:
                        # Valid project
                        self.projects.append({
                            'name': item,
                            'path': main_pd,
                            'gui_path': patch_gui,
                            'folder_path': item_path
                        })
                    else:
                        # Show folder but mark as incomplete
                        missing = []
                        if not has_pd:
                            missing.append("main.pd")
                        if not has_gui:
                            missing.append("patch-gui.py")
                        
                        self.projects.append({
                            'name': f"{item} (missing: {', '.join(missing)})",
                            'path': None,
                            'gui_path': None,
                            'folder_path': item_path
                        })
        except Exception as e:
            print(f"Error scanning projects: {e}")
        
        # Sort projects after loading
        self.sort_projects()
        
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
        
        # Load metadata for timestamp display
        metadata = self.load_metadata()
        
        # Update project labels
        for i in range(PATCHES_PER_PAGE):
            project_idx = start_idx + i
            
            # Get the label tuple (name_label, meta_label)
            name_label, meta_label = self.project_labels[i]
            
            # Get parent container for border
            container = name_label.master
            
            if project_idx < len(self.projects):
                project = self.projects[project_idx]
                project_name = project['name']
                display_name = project_name
                
                # Get clean name for metadata lookup (without "(!)" suffix)
                clean_name = project_name[:-4] if project_name.endswith(" (!)") else project_name
                
                # Get timestamp metadata
                timestamp_str = metadata.get(clean_name, None)
                time_text = self.format_timestamp(timestamp_str)
                
                # Get musical metadata from patch_data.txt (list of lines)
                folder_path = project.get('folder_path')
                patch_data_lines = self.read_patch_data(folder_path) if folder_path else []
                
                # Build metadata text (combine time + all patch data lines)
                meta_parts = [time_text]
                meta_parts.extend(patch_data_lines)  # Add all lines from file
                
                meta_text = " • ".join(meta_parts)
                
                # Determine if selected
                is_selected = (self.selected_project_index == project_idx)
                
                # Update name label and container background
                if is_selected:
                    # Selected: yellow text, dark grey background
                    name_label.config(
                        text=display_name, 
                        fg="#ffff00",  # Yellow
                        bg="#1a1a1a",  # Darker grey background
                        font=self.app.fonts.big
                    )
                    # Dark grey background on container and metadata
                    container.config(bg="#1a1a1a", highlightthickness=0)
                    meta_label.config(bg="#1a1a1a")  # Match container background
                else:
                    # Unselected: white text, black background
                    name_label.config(
                        text=display_name, 
                        fg="#ffffff",  # White
                        bg="black",
                        font=self.app.fonts.big
                    )
                    # Black background
                    container.config(bg="black", highlightthickness=0)
                    meta_label.config(bg="black")
                
                # Update metadata text (always grey text)
                meta_label.config(text=meta_text, fg="#606060")
                
            else:
                # Empty cell
                name_label.config(text="", fg="#606060", bg="black", font=self.app.fonts.big)
                meta_label.config(text="", fg="#606060", bg="black")
                container.config(bg="black", highlightthickness=0)
        
        # Update action buttons
        self.update_action_buttons()
        
        # Update navigation button states
        self.update_nav_buttons()
    
    def update_action_buttons(self):
        """Update LOAD, DUPLICATE, and DELETE button colors based on selection"""
        if self.selected_project_index is not None:
            # Something selected - all buttons enabled
            if self.load_button:
                self.load_button.config(fg="#ffffff")
            if self.duplicate_button:
                self.duplicate_button.config(fg="#ffffff")
            if self.delete_button:
                self.delete_button.config(fg="#ffffff")
        else:
            # Nothing selected - all buttons disabled
            if self.load_button:
                self.load_button.config(fg="#303030")
            if self.duplicate_button:
                self.duplicate_button.config(fg="#303030")
            if self.delete_button:
                self.delete_button.config(fg="#303030")
    
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
        
        # Define the actual load action
        def do_load():
            # Update timestamp for this project
            project_name = selected_project['name']
            # Remove " (!)" suffix if present (though this shouldn't happen anymore)
            if " (missing:" in project_name:
                project_name = project_name.split(" (missing:")[0]
            self.update_project_timestamp(project_name)
            
            # Start Pure Data (async - returns immediately)
            print(f"Loading: {selected_project['name']}")
            self.app.pd_manager.start_pd_async(main_pd_path)
            
            # Dynamically load GUI from project folder
            gui_path = selected_project['gui_path']
            if gui_path and os.path.exists(gui_path):
                try:
                    # Import the GUI module from project folder
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("project_gui", gui_path)
                    gui_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(gui_module)
                    
                    # Destroy old patch screen if it exists
                    if 'patch' in self.app.screens:
                        old_screen = self.app.screens['patch']
                        old_screen.destroy()
                    
                    # Create new GUI instance (assumes class is named PatchDisplayScreen)
                    new_gui = gui_module.PatchDisplayScreen(self.app.root, self.app)
                    self.app.screens['patch'] = new_gui
                    
                    print(f"Loaded custom GUI from: {gui_path}")
                    
                except Exception as e:
                    print(f"Error loading custom GUI: {e}")
                    import traceback
                    traceback.print_exc()
                    # Fallback to default if custom GUI fails
                    # (but this shouldn't happen if patch-gui.py is required)
            
            # Switch to patch display immediately (will show loading state)
            self.app.show_screen('patch')
        
        # CHECK IF PATCH IS ALREADY RUNNING
        if self.app.pd_manager.is_running():
            # Get current patch name
            current_patch = self.app.pd_manager.current_patch
            if current_patch:
                current_name = os.path.basename(os.path.dirname(current_patch))
            else:
                current_name = "current patch"
            
            new_name = selected_project['name']
            # Remove " (!)" suffix if present
            if new_name.endswith(" (!)"):
                new_name = new_name[:-4]
            
            # Show confirmation screen
            self.app.show_confirmation(
                message=f"Close '{current_name}' and load\n'{new_name}'?",
                on_yes=do_load,
                return_screen='browser',
                timeout=10
            )
        else:
            # No patch running, just load directly
            do_load()
    
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
        
        # Define what happens when user confirms
        def on_confirm_duplicate():
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
                    error_msg = result[:20] if len(result) > 20 else result
                    self.after(0, lambda: self.show_sync_status(f"FAILED", error=True, duration=5000))
            
            threading.Thread(target=do_duplicate, daemon=True).start()
            
            # Return to browser
            self.app.show_screen('browser')
        
        # Show confirmation screen
        self.app.show_confirmation(
            message=f"Duplicate '{source_name}'?",
            on_yes=on_confirm_duplicate,
            on_no=None,  # Default: return to browser
            return_screen='browser',
            timeout=10
        )
    
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
    
    def delete_selected_project(self):
        """Delete the selected project (move to trash) with confirmation screen"""
        # Only delete if something is selected
        if self.selected_project_index is None:
            print("No project selected")
            self.show_sync_status("NO PROJECT", error=True, duration=3000)
            return
        
        if not self.projects:
            return
        
        selected_project = self.projects[self.selected_project_index]
        project_name = selected_project['name']
        
        # Remove the " (!)" suffix if present
        if project_name.endswith(" (!)"):
            project_name = project_name[:-4]
        
        # Define what happens when user confirms
        def on_confirm_delete():
            print(f"Deleting: {project_name}")
            self.show_sync_status("DELETING...", syncing=True)
            
            # Call deleter in background thread
            projects_dir = os.path.join(self.app.molipe_root, "my_projects")
            
            def do_delete():
                success, result = delete_project(projects_dir, project_name)
                
                # Update UI from main thread
                if success:
                    print(f"✓ Moved to trash: {result}")
                    self.after(0, lambda: self.show_sync_status("✓ DELETED", error=False, duration=3000))
                    
                    # Refresh the browser to remove deleted project
                    self.after(100, lambda: self.refresh_projects())
                else:
                    print(f"✗ Deletion failed: {result}")
                    error_msg = result[:20] if len(result) > 20 else result
                    self.after(0, lambda: self.show_sync_status(f"DELETE FAILED", error=True, duration=5000))
            
            threading.Thread(target=do_delete, daemon=True).start()
            
            # Return to browser
            self.app.show_screen('browser')
        
        # Show confirmation screen
        self.app.show_confirmation(
            message=f"Delete '{project_name}'?\n\nIt will be moved to trash.",
            on_yes=on_confirm_delete,
            on_no=None,  # Default: return to browser
            return_screen='browser',
            timeout=10
        )
        
        threading.Thread(target=do_delete, daemon=True).start()
    
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