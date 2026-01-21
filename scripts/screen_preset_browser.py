"""
Preset Browser Screen - Browse and start from factory preset projects
Simplified version without filter functionality
"""
import tkinter as tk
import os
import sys
import threading
from project_duplicator import duplicate_project

# Grid configuration (same as other screens)
DEFAULT_ROWS = 11
COLS_PER_ROW = [4, 4, 4, 8, 4, 4, 4, 8, 4, 8, 8]
ROW_HEIGHTS = [60, 210, 50, 0, 0, 210, 50, 5, 20, 50, 50]
PRESETS_PER_PAGE = 8

class PresetBrowserScreen(tk.Frame):
    """
    Browse factory preset projects and start new projects from them
    
    Features:
    - Display presets from preset_projects/ directory
    - Show metadata (title, level, style, description)
    - 8 presets per page with pagination
    - START button duplicates preset to my_projects/ and loads it
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
        
        # UI references
        self.cell_frames = []
        self.preset_labels = []
        self.page_label = None
        self.status_label = None
        self.start_button = None
        self.prev_button = None
        self.next_button = None
        
        self._build_ui()
    
    def _build_ui(self):
        """Build grid-based preset browser UI"""
        
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
                
                # Row 0: Navigation and status
                if r == 0:
                    if c == 0:
                        # HOME button
                        home_button = tk.Label(
                            cell, text="HOME",
                            font=self.app.fonts.small,
                            bg="black", fg="white",
                            cursor="hand2", bd=0, relief="flat"
                        )
                        home_button.bind("<Button-1>", lambda e: self.go_home())
                        home_button.pack(fill="both", expand=True)
                    
                    elif c == 3:
                        # Status label (upper right)
                        self.status_label = tk.Label(
                            cell,
                            text="PRESETS",
                            bg="black", fg="#606060",
                            anchor="e", padx=10, pady=0, bd=0, highlightthickness=0,
                            font=self.app.fonts.status
                        )
                        self.status_label.pack(fill="both", expand=True)
                
                # Rows 1-8: Preset list (8 slots)
                elif 1 <= r <= 8:
                    preset_idx = r - 1  # 0-7
                    
                    # Create label for preset
                    preset_label = tk.Label(
                        cell,
                        text="",
                        font=self.app.fonts.big,
                        bg="black", fg="#606060",
                        anchor="w", padx=10, bd=0, relief="flat",
                        cursor="hand2"
                    )
                    preset_label.bind("<Button-1>", lambda e, idx=preset_idx: self.select_preset(idx))
                    preset_label.grid(row=0, column=0, columnspan=4, sticky="nsew")
                    self.preset_labels.append(preset_label)
                
                # Row 9: Pagination and action buttons
                elif r == 9:
                    if c == 0:
                        # PREVIOUS PAGE button
                        self.prev_button = tk.Label(
                            cell, text="PREV",
                            font=self.app.fonts.small,
                            bg="#000000", fg="#ffffff",
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.prev_button.bind("<Button-1>", lambda e: self.prev_page())
                        self.prev_button.pack(fill="both", expand=True)
                    elif c == 1:
                        # NEXT PAGE button
                        self.next_button = tk.Label(
                            cell, text="NEXT",
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
                        # START button (last column)
                        self.start_button = tk.Label(
                            cell, text="START",
                            font=self.app.fonts.small,
                            bg="#000000", fg="#303030",  # Start dark grey (disabled)
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.start_button.bind("<Button-1>", lambda e: self.start_selected_preset())
                        self.start_button.pack(fill="both", expand=True)
            
            self.cell_frames.append(row_cells)
    
    def refresh_presets(self):
        """Scan preset_projects directory for presets"""
        self.presets = []
        self.selected_preset_index = None
        
        # Scan preset_projects directory (inside molipe_root, same level as my_projects)
        presets_dir = os.path.join(self.app.molipe_root, "preset_projects")
        
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
        """Update preset list display for current page"""
        # Calculate start and end indices for current page
        start_idx = self.current_page * PRESETS_PER_PAGE
        end_idx = min(start_idx + PRESETS_PER_PAGE, len(self.presets))
        
        # Update each preset label
        for i, label in enumerate(self.preset_labels):
            preset_idx = start_idx + i
            
            if preset_idx < end_idx:
                # Show preset
                preset = self.presets[preset_idx]
                
                # Display format: "Title (level, style)"
                display_text = preset['title']
                if preset['level'] or preset['style']:
                    tags = []
                    if preset['level']:
                        tags.append(preset['level'])
                    if preset['style']:
                        tags.append(preset['style'])
                    display_text += f" ({', '.join(tags)})"
                
                label.config(text=display_text, fg="#ffffff" if i == (self.selected_preset_index or -1) - start_idx else "#606060")
            else:
                # Empty slot
                label.config(text="", fg="#606060")
        
        # Update page indicator
        if self.page_label:
            if self.total_pages > 0:
                self.page_label.config(text=f"{self.current_page + 1}/{self.total_pages}")
            else:
                self.page_label.config(text="0/0")
        
        # Update navigation buttons
        self.update_nav_buttons()
        
        # Update action button
        self.update_action_button()
    
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
    
    def update_action_button(self):
        """Update START button based on selection"""
        if self.selected_preset_index is not None:
            # Something selected - START enabled
            if self.start_button:
                self.start_button.config(fg="#ffffff")
        else:
            # Nothing selected - START disabled
            if self.start_button:
                self.start_button.config(fg="#303030")
    
    def select_preset(self, display_idx):
        """Select a preset by clicking on it (display_idx is 0-7 on current page)"""
        start_idx = self.current_page * PRESETS_PER_PAGE
        preset_idx = start_idx + display_idx
        
        if preset_idx < len(self.presets):
            # Toggle selection
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
        self.update_status("STARTING...")
        
        # Duplicate preset to my_projects
        presets_dir = os.path.join(self.app.molipe_root, "preset_projects")
        my_projects_dir = os.path.join(self.app.molipe_root, "my_projects")
        
        def do_start():
            # Use duplicate_project to copy preset to my_projects
            # Note: We need to modify duplicate_project to accept target_dir
            success, new_name = duplicate_project(presets_dir, preset_name, target_dir=my_projects_dir)
            
            if success:
                print(f"✓ Created new project: {new_name}")
                self.after(0, lambda: self.update_status("✓ CREATED"))
                
                # Load the new project
                new_project_path = os.path.join(my_projects_dir, new_name, "main.pd")
                
                if os.path.exists(new_project_path):
                    if self.app.pd_manager.start_pd(new_project_path):
                        # Switch to patch display
                        self.after(500, lambda: self.app.show_screen('patch'))
                    else:
                        print("Failed to load new project")
                        self.after(0, lambda: self.update_status("LOAD FAILED"))
            else:
                print(f"✗ Start failed: {new_name}")
                self.after(0, lambda: self.update_status("START FAILED"))
        
        threading.Thread(target=do_start, daemon=True).start()
    
    def update_status(self, message, duration=3000):
        """Update status label with message"""
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
