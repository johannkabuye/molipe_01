"""
Preset Browser Screen - Browse and start from factory preset projects
Matches project browser look and feel exactly
"""
import tkinter as tk
import os
import sys
import threading
import json
from datetime import datetime
from project_duplicator import duplicate_project

# Grid configuration (same as project browser)
DEFAULT_ROWS = 11
COLS_PER_ROW = [4, 4, 4, 8, 4, 4, 4, 8, 4, 8, 8]
ROW_HEIGHTS = [60, 210, 50, 0, 0, 210, 50, 5, 20, 50, 50]
PRESETS_PER_PAGE = 8

class PresetBrowserScreen(tk.Frame):
    """
    Browse factory preset projects and start new projects from them
    Exact match to project browser UI
    """
    
    def __init__(self, parent, app):
        super().__init__(parent, bg="#000000")
        self.app = app
        
        self.rows = DEFAULT_ROWS
        self.cols_per_row = list(COLS_PER_ROW)
        
        # State
        self.presets = []
        self.current_page = 0
        self.total_pages = 0
        self.selected_preset_index = None  # None = nothing selected
        
        # Metadata file path (for timestamp tracking in my_projects)
        self.metadata_file = None
        
        # UI references
        self.cell_frames = []
        self.preset_labels = []  # Will store tuples of (name_label, meta_label)
        self.page_label = None
        self.status_label = None
        self.start_button = None
        self.prev_button = None
        self.next_button = None
        
        self._build_ui()
    
    def _build_ui(self):
        """Build grid-based preset browser UI (matches project browser exactly)"""
        
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
                
                # Row 0, Cell 0: MENU button (same as project browser)
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
                
                # Row 0, Cell 3: Status label (matches sync status position)
                elif r == 0 and c == 3:
                    self.status_label = tk.Label(
                        cell,
                        text="PRESETS",
                        bg="black", fg="#606060",
                        anchor="e", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small
                    )
                    self.status_label.pack(fill="both", expand=True)
                
                # Row 1: Preset cells 0-3 (matches project browser exactly)
                elif r == 1:
                    # Create a container frame for name + metadata
                    preset_container = tk.Frame(cell, bg="black", bd=0, highlightthickness=0)
                    preset_container.pack(fill="both", expand=True, padx=5, pady=5)
                    preset_container.bind("<Button-1>", lambda e, idx=c: self.select_preset(idx))
                    
                    # Preset name label (big font, left-aligned)
                    preset_name = tk.Label(
                        preset_container, text="",
                        bg="black", fg="#ffffff",
                        anchor="w", padx=10, pady=5, bd=0, highlightthickness=0,
                        font=self.app.fonts.big,
                        cursor="hand2",
                        wraplength=270,
                        justify="left"
                    )
                    preset_name.pack(fill="x", anchor="nw")
                    preset_name.bind("<Button-1>", lambda e, idx=c: self.select_preset(idx))
                    
                    # Metadata label (metadata font, grey, left-aligned)
                    preset_meta = tk.Label(
                        preset_container, text="",
                        bg="black", fg="#606060",
                        anchor="w", padx=10, pady=5, bd=0, highlightthickness=0,
                        font=self.app.fonts.metadata,
                        cursor="hand2",
                        wraplength=250,
                        justify="left"
                    )
                    preset_meta.pack(fill="x", anchor="nw")
                    preset_meta.bind("<Button-1>", lambda e, idx=c: self.select_preset(idx))
                    
                    # Store both labels as a tuple (same as project browser)
                    self.preset_labels.append((preset_name, preset_meta))
                
                # Row 5: Preset cells 4-7 (matches project browser exactly)
                elif r == 5:
                    # Create a container frame for name + metadata
                    preset_container = tk.Frame(cell, bg="black", bd=0, highlightthickness=0)
                    preset_container.pack(fill="both", expand=True, padx=5, pady=5)
                    preset_container.bind("<Button-1>", lambda e, idx=c+4: self.select_preset(idx+4))
                    
                    # Preset name label (big font, left-aligned)
                    preset_name = tk.Label(
                        preset_container, text="",
                        bg="black", fg="#ffffff",
                        anchor="w", padx=10, pady=5, bd=0, highlightthickness=0,
                        font=self.app.fonts.big,
                        cursor="hand2",
                        wraplength=270,
                        justify="left"
                    )
                    preset_name.pack(fill="x", anchor="nw")
                    preset_name.bind("<Button-1>", lambda e, idx=c+4: self.select_preset(idx+4))
                    
                    # Metadata label (metadata font, grey, left-aligned)
                    preset_meta = tk.Label(
                        preset_container, text="",
                        bg="black", fg="#606060",
                        anchor="w", padx=10, pady=5, bd=0, highlightthickness=0,
                        font=self.app.fonts.metadata,
                        cursor="hand2",
                        wraplength=250,
                        justify="left"
                    )
                    preset_meta.pack(fill="x", anchor="nw")
                    preset_meta.bind("<Button-1>", lambda e, idx=c+4: self.select_preset(idx+4))
                    
                    # Store both labels as a tuple (same as project browser)
                    self.preset_labels.append((preset_name, preset_meta))
                
                # Row 9: Navigation buttons (matches project browser)
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
                        # Page indicator
                        self.page_label = tk.Label(
                            cell,
                            text="1/1",
                            bg="black", fg="#606060",
                            anchor="center", padx=5, pady=0, bd=0, highlightthickness=0,
                            font=self.app.fonts.small
                        )
                        self.page_label.pack(fill="both", expand=True)
                    elif c == 7:
                        # START button (replaces LOAD in project browser)
                        self.start_button = tk.Label(
                            cell, text="START",
                            font=self.app.fonts.small,
                            bg="#000000", fg="#303030",  # Start dark grey (disabled)
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.start_button.bind("<Button-1>", lambda e: self.start_selected_preset())
                        self.start_button.pack(fill="both", expand=True)
            
            self.cell_frames.append(row_cells)
    
    def load_metadata(self):
        """Load metadata from .molipe_meta file (same as project browser)"""
        if not self.metadata_file or not os.path.exists(self.metadata_file):
            return {}
        
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata: {e}")
            return {}
    
    def save_metadata(self, metadata):
        """Save metadata to .molipe_meta file (same as project browser)"""
        if not self.metadata_file:
            return
        
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def update_project_timestamp(self, project_name):
        """Update timestamp for a project when it's created/opened (same as project browser)"""
        metadata = self.load_metadata()
        metadata[project_name] = datetime.now().isoformat()
        self.save_metadata(metadata)
    
    def refresh_presets(self):
        """Scan preset_projects directory for presets"""
        self.presets = []
        self.selected_preset_index = None
        
        # Scan preset_projects directory (inside molipe_root, same level as my_projects)
        presets_dir = os.path.join(self.app.molipe_root, "preset_projects")
        
        # Set metadata file path (points to my_projects metadata file)
        my_projects_dir = os.path.join(self.app.molipe_root, "my_projects")
        self.metadata_file = os.path.join(my_projects_dir, ".molipe_meta")
        
        # Check if presets directory exists
        if not os.path.exists(presets_dir):
            print(f"Presets directory not found: {presets_dir}")
            self.presets = []
            self.current_page = 0
            self.total_pages = 0
            self.update_display()
            return
        
        # Scan for preset folders (subfolders with main.pd)
        try:
            for item in sorted(os.listdir(presets_dir)):
                item_path = os.path.join(presets_dir, item)
                
                # Skip hidden folders
                if item.startswith('.'):
                    continue
                
                # Only include directories
                if os.path.isdir(item_path):
                    # Check if main.pd exists
                    main_pd = os.path.join(item_path, "main.pd")
                    
                    if os.path.exists(main_pd):
                        # Parse metadata if available
                        metadata = self._parse_metadata(item_path)
                        
                        self.presets.append({
                            'folder_name': item,
                            'title': metadata.get('title', item),
                            'level': metadata.get('level', ''),
                            'style': metadata.get('style', ''),
                            'description': metadata.get('description', ''),
                            'path': main_pd,
                            'folder_path': item_path
                        })
        except Exception as e:
            print(f"Error scanning presets: {e}")
        
        # Calculate pages
        if self.presets:
            self.total_pages = (len(self.presets) + PRESETS_PER_PAGE - 1) // PRESETS_PER_PAGE
            self.current_page = min(self.current_page, self.total_pages - 1)
        else:
            self.total_pages = 0
            self.current_page = 0
        
        self.update_display()
    
    def _parse_metadata(self, preset_folder):
        """Parse metadata.txt file from preset folder"""
        metadata = {}
        metadata_file = os.path.join(preset_folder, "metadata.txt")
        
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if ':' in line:
                            key, value = line.split(':', 1)
                            metadata[key.strip().lower()] = value.strip()
            except Exception as e:
                print(f"Error parsing metadata: {e}")
        
        return metadata
    
    def update_display(self):
        """Update preset list display for current page (matches project browser exactly)"""
        # Calculate start and end indices for current page
        start_idx = self.current_page * PRESETS_PER_PAGE
        end_idx = min(start_idx + PRESETS_PER_PAGE, len(self.presets))
        
        # Update page label
        if self.page_label:
            page_display = f"{self.current_page + 1}/{self.total_pages}" if self.total_pages > 0 else "0/0"
            self.page_label.config(text=page_display)
        
        # Update each preset label (8 presets per page)
        for i in range(PRESETS_PER_PAGE):
            preset_idx = start_idx + i
            
            # Get the label tuple (name_label, meta_label)
            name_label, meta_label = self.preset_labels[i]
            
            # Get parent container for background styling
            container = name_label.master
            
            if preset_idx < end_idx:
                # Show preset
                preset = self.presets[preset_idx]
                
                # Display format: "Title"
                display_name = preset['title']
                
                # Build metadata text: "level, style"
                meta_parts = []
                if preset['level']:
                    meta_parts.append(preset['level'])
                if preset['style']:
                    meta_parts.append(preset['style'])
                meta_text = ", ".join(meta_parts) if meta_parts else ""
                
                # Determine if selected
                is_selected = (self.selected_preset_index == preset_idx)
                
                # Update name label and container background (EXACT match to project browser)
                if is_selected:
                    # Selected: yellow text, dark grey background
                    name_label.config(
                        text=display_name,
                        fg="#ffff00",  # Yellow (exactly like project browser)
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
        
        # Update action button
        self.update_action_button()
        
        # Update navigation button states
        self.update_nav_buttons()
    
    def update_nav_buttons(self):
        """Update PREV/NEXT button states (matches project browser)"""
        if self.prev_button:
            if self.current_page > 0:
                self.prev_button.config(fg="#ffffff")  # Enabled (white)
            else:
                self.prev_button.config(fg="#303030")  # Disabled (dark grey)
        
        if self.next_button:
            if self.current_page < self.total_pages - 1:
                self.next_button.config(fg="#ffffff")  # Enabled (white)
            else:
                self.next_button.config(fg="#303030")  # Disabled (dark grey)
    
    def update_action_button(self):
        """Update START button based on selection (matches project browser)"""
        if self.selected_preset_index is not None:
            # Something selected - START enabled (white)
            if self.start_button:
                self.start_button.config(fg="#ffffff")
        else:
            # Nothing selected - START disabled (dark grey)
            if self.start_button:
                self.start_button.config(fg="#303030")
    
    def select_preset(self, display_idx):
        """Select a preset by clicking on it (display_idx is 0-7 on current page)"""
        start_idx = self.current_page * PRESETS_PER_PAGE
        preset_idx = start_idx + display_idx
        
        if preset_idx < len(self.presets):
            # Toggle selection (exactly like project browser)
            if self.selected_preset_index == preset_idx:
                self.selected_preset_index = None  # Deselect
            else:
                self.selected_preset_index = preset_idx  # Select
            
            self.update_display()
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.selected_preset_index = None  # Clear selection when changing pages
            self.update_display()
    
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.selected_preset_index = None  # Clear selection when changing pages
            self.update_display()
    
    def start_selected_preset(self):
        """Start new project from selected preset (duplicate to my_projects and load)"""
        # Only start if something is selected
        if self.selected_preset_index is None:
            print("No preset selected")
            return
        
        if not self.presets:
            return
        
        selected_preset = self.presets[self.selected_preset_index]
        preset_name = selected_preset['folder_name']
        
        print(f"Starting from preset: {preset_name}")
        
        # Define the actual start logic
        def do_start():
            self.update_status("STARTING...")
            
            # Duplicate preset to my_projects
            presets_dir = os.path.join(self.app.molipe_root, "preset_projects")
            my_projects_dir = os.path.join(self.app.molipe_root, "my_projects")
            
            def do_duplicate_and_load():
                # Use duplicate_project to copy preset to my_projects
                success, new_name = duplicate_project(presets_dir, preset_name, target_dir=my_projects_dir)
                
                if success:
                    print(f"✓ Created new project: {new_name}")
                    self.after(0, lambda: self.update_status("✓ CREATED"))
                    
                    # IMPORTANT: Update timestamp for the new project
                    self.after(0, lambda: self.update_project_timestamp(new_name))
                    
                    # Load the new project (async - returns immediately)
                    new_project_path = os.path.join(my_projects_dir, new_name, "main.pd")
                    new_gui_path = os.path.join(my_projects_dir, new_name, "patch-gui.py")
                    
                    if os.path.exists(new_project_path):
                        # Start Pure Data
                        self.app.pd_manager.start_pd_async(new_project_path)
                        
                        # Dynamically load GUI from project folder
                        if os.path.exists(new_gui_path):
                            def load_gui():
                                try:
                                    # Import the GUI module from project folder
                                    import importlib.util
                                    spec = importlib.util.spec_from_file_location("project_gui", new_gui_path)
                                    gui_module = importlib.util.module_from_spec(spec)
                                    spec.loader.exec_module(gui_module)
                                    
                                    # Destroy old patch screen if it exists
                                    if 'patch' in self.app.screens:
                                        old_screen = self.app.screens['patch']
                                        old_screen.destroy()
                                    
                                    # Create new GUI instance (assumes class is named PatchDisplayScreen)
                                    new_gui = gui_module.PatchDisplayScreen(self.app.root, self.app)
                                    self.app.screens['patch'] = new_gui
                                    
                                    print(f"Loaded custom GUI from: {new_gui_path}")
                                    
                                except Exception as e:
                                    print(f"Error loading custom GUI: {e}")
                                    import traceback
                                    traceback.print_exc()
                            
                            # Load GUI on main thread
                            self.after(0, load_gui)
                        
                        # Switch to patch display immediately (will show loading screen)
                        self.after(0, lambda: self.app.show_screen('patch'))
                    else:
                        print("Failed to find new project main.pd")
                        self.after(0, lambda: self.update_status("LOAD FAILED"))
                else:
                    print(f"✗ Start failed: {new_name}")
                    self.after(0, lambda: self.update_status("START FAILED"))
            
            threading.Thread(target=do_duplicate_and_load, daemon=True).start()
        
        # CHECK IF PATCH IS ALREADY RUNNING
        if self.app.pd_manager.is_running():
            # Get current patch name
            current_patch = self.app.pd_manager.current_patch
            if current_patch:
                current_name = os.path.basename(os.path.dirname(current_patch))
            else:
                current_name = "current patch"
            
            # Show confirmation screen
            self.app.show_confirmation(
                message=f"Close '{current_name}' and start\n'{preset_name}'?",
                on_yes=do_start,
                return_screen='preset_browser',
                timeout=10
            )
        else:
            # No patch running, just start directly
            do_start()
    
    def update_status(self, message, duration=3000):
        """Update status label with message (matches project browser)"""
        if self.status_label:
            self.status_label.config(text=message)
            
            # Reset to "PRESETS" after duration
            if duration:
                self.after(duration, lambda: self.status_label.config(text="PRESETS"))
    
    def go_home(self):
        """Return to control panel"""
        self.app.show_screen('control')
    
    def on_show(self):
        """Called when screen becomes visible"""
        # Refresh presets when shown
        self.refresh_presets()