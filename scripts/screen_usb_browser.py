"""
USB Browser Screen - Browse and import projects from USB stick
Exact match to project browser look and feel
"""
import tkinter as tk
import os
import shutil
from datetime import datetime

# Grid configuration (same as project browser)
DEFAULT_ROWS = 11
COLS_PER_ROW = [4, 4, 4, 8, 4, 4, 4, 8, 4, 8, 8]
ROW_HEIGHTS = [60, 210, 50, 0, 0, 210, 50, 5, 20, 50, 50]
PROJECTS_PER_PAGE = 8

class USBBrowserScreen(tk.Frame):
    """Browse and import projects from USB stick (exact match to project browser)"""
    
    def __init__(self, parent, app):
        super().__init__(parent, bg="#000000")
        self.app = app
        
        self.rows = DEFAULT_ROWS
        self.cols_per_row = list(COLS_PER_ROW)
        
        # State
        self.usb_path = None
        self.projects = []
        self.current_page = 0
        self.total_pages = 0
        self.selected_project_index = None  # None = nothing selected
        
        # UI references
        self.cell_frames = []
        self.project_labels = []  # Will store tuples of (name_label, meta_label)
        self.page_label = None
        self.status_label = None
        self.import_button = None
        self.prev_button = None
        self.next_button = None
        
        self._build_ui()
    
    def _build_ui(self):
        """Build grid-based USB browser UI (matches project browser exactly)"""
        
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
                
                # Row 0, Cell 0: MENU button (exact match to project browser)
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
                        text="IMPORT FROM USB",
                        bg="black", fg="#606060",
                        anchor="e", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small
                    )
                    self.status_label.pack(fill="both", expand=True)
                
                # Row 1: Project cells 0-3 (exact match to project browser)
                elif r == 1:
                    # Create a container frame for name + metadata
                    proj_container = tk.Frame(cell, bg="black", bd=0, highlightthickness=0)
                    proj_container.pack(fill="both", expand=True, padx=5, pady=5)
                    proj_container.bind("<Button-1>", lambda e, idx=c: self.select_project(idx))
                    
                    # Project name label (big font, left-aligned)
                    proj_name = tk.Label(
                        proj_container, text="",
                        bg="black", fg="#ffffff",
                        anchor="w", padx=10, pady=5, bd=0, highlightthickness=0,
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
                        anchor="w", padx=10, pady=5, bd=0, highlightthickness=0,
                        font=self.app.fonts.metadata,
                        cursor="hand2",
                        wraplength=250,
                        justify="left"
                    )
                    proj_meta.pack(fill="x", anchor="nw")
                    proj_meta.bind("<Button-1>", lambda e, idx=c: self.select_project(idx))
                    
                    # Store both labels as a tuple (same as project browser)
                    self.project_labels.append((proj_name, proj_meta))
                
                # Row 5: Project cells 4-7 (exact match to project browser)
                elif r == 5:
                    # Create a container frame for name + metadata
                    proj_container = tk.Frame(cell, bg="black", bd=0, highlightthickness=0)
                    proj_container.pack(fill="both", expand=True, padx=5, pady=5)
                    proj_container.bind("<Button-1>", lambda e, idx=c+4: self.select_project(idx+4))
                    
                    # Project name label (big font, left-aligned)
                    proj_name = tk.Label(
                        proj_container, text="",
                        bg="black", fg="#ffffff",
                        anchor="w", padx=10, pady=5, bd=0, highlightthickness=0,
                        font=self.app.fonts.big,
                        cursor="hand2",
                        wraplength=270,
                        justify="left"
                    )
                    proj_name.pack(fill="x", anchor="nw")
                    proj_name.bind("<Button-1>", lambda e, idx=c+4: self.select_project(idx+4))
                    
                    # Metadata label (metadata font, grey, left-aligned)
                    proj_meta = tk.Label(
                        proj_container, text="",
                        bg="black", fg="#606060",
                        anchor="w", padx=10, pady=5, bd=0, highlightthickness=0,
                        font=self.app.fonts.metadata,
                        cursor="hand2",
                        wraplength=250,
                        justify="left"
                    )
                    proj_meta.pack(fill="x", anchor="nw")
                    proj_meta.bind("<Button-1>", lambda e, idx=c+4: self.select_project(idx+4))
                    
                    # Store both labels as a tuple (same as project browser)
                    self.project_labels.append((proj_name, proj_meta))
                
                # Row 8: Page indicator (matches project browser)
                elif r == 8:
                    if c == 0:
                        self.page_label = tk.Label(
                            row_frame,
                            text="0/0",
                            font=self.app.fonts.small,
                            bg="black", fg="#606060",
                            anchor="center"
                        )
                        self.page_label.grid(row=0, column=0, columnspan=8, sticky="nsew")
                
                # Row 9: Navigation buttons (PREV/NEXT like project browser)
                elif r == 9:
                    if c == 0:
                        # PREV button
                        self.prev_button = tk.Label(
                            cell, text="PREV",
                            font=self.app.fonts.button,
                            bg="black", fg="#ffffff",
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.prev_button.bind("<Button-1>", lambda e: self.prev_page())
                        self.prev_button.pack(fill="both", expand=True, padx=20, pady=10)
                    
                    elif c == 1:
                        # NEXT button
                        self.next_button = tk.Label(
                            cell, text="NEXT",
                            font=self.app.fonts.button,
                            bg="black", fg="#ffffff",
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.next_button.bind("<Button-1>", lambda e: self.next_page())
                        self.next_button.pack(fill="both", expand=True, padx=20, pady=10)
                
                # Row 10: Action button (IMPORT)
                elif r == 10:
                    if c == 0:
                        # IMPORT button
                        self.import_button = tk.Label(
                            cell, text="IMPORT",
                            font=self.app.fonts.button,
                            bg="black", fg="#303030",  # Disabled by default
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.import_button.bind("<Button-1>", lambda e: self.import_project())
                        self.import_button.pack(fill="both", expand=True, padx=20, pady=10)
            
            self.cell_frames.append(row_cells)
    
    def go_home(self):
        """Return to control panel"""
        self.app.show_screen('control')
    
    def on_show(self):
        """Called when screen becomes visible - scan USB"""
        self.scan_usb()
        self.update_display()
    
    def scan_usb(self):
        """Scan USB mount points for projects (EXACTLY like preset browser scans presets)"""
        self.usb_path = None
        self.projects = []
        self.selected_project_index = None
        
        # On Patchbox OS, USB sticks mount at /media/patch/[USB-NAME]/
        # Check /media/patch/ for subdirectories (each is a mount)
        media_patch = "/media/patch"
        
        if os.path.exists(media_patch):
            try:
                # List all mounts under /media/patch/
                mounts = [d for d in os.listdir(media_patch) 
                         if os.path.isdir(os.path.join(media_patch, d))]
                
                if mounts:
                    # Use first mount found
                    self.usb_path = os.path.join(media_patch, mounts[0])
                    print(f"Found USB mount: {self.usb_path}")
            except PermissionError:
                pass
        
        # Fallback: check other common mount points
        if not self.usb_path:
            for mount_point in ["/media/usb", "/mnt/usb"]:
                if os.path.exists(mount_point) and os.path.isdir(mount_point):
                    try:
                        # Check if it has content
                        if os.listdir(mount_point):
                            self.usb_path = mount_point
                            print(f"Found USB at: {self.usb_path}")
                            break
                    except PermissionError:
                        continue
        
        if not self.usb_path:
            self.update_status("NO USB DETECTED", error=True)
            self.current_page = 0
            self.total_pages = 0
            return
        
        print(f"Scanning USB: {self.usb_path}")
        
        # Scan USB for project folders (EXACTLY like preset browser)
        try:
            # Look for my_projects folder first (preferred structure)
            projects_dir = os.path.join(self.usb_path, "my_projects")
            
            # If no my_projects folder, scan USB root
            if not os.path.exists(projects_dir):
                projects_dir = self.usb_path
                print(f"No my_projects folder, scanning root: {projects_dir}")
            else:
                print(f"Found my_projects folder: {projects_dir}")
            
            # Scan for folders with main.pd (EXACTLY like preset browser lines 281-305)
            items = sorted(os.listdir(projects_dir))
            print(f"Found {len(items)} items in {projects_dir}")
            
            for item in items:
                item_path = os.path.join(projects_dir, item)
                
                # Skip hidden items
                if item.startswith('.'):
                    continue
                
                # Only check directories
                if os.path.isdir(item_path):
                    # Check if main.pd exists (EXACTLY like preset browser line 291)
                    main_pd = os.path.join(item_path, "main.pd")
                    
                    print(f"Checking folder: {item}")
                    
                    if os.path.exists(main_pd):
                        print(f"  ✓ Found main.pd in {item}")
                        self.projects.append({
                            'name': item,           # folder name = project name
                            'path': item_path,      # path to folder (not main.pd)
                            'has_main': True
                        })
                    else:
                        print(f"  ✗ No main.pd in {item}")
                        # Folder exists but no main.pd - show with warning
                        self.projects.append({
                            'name': item + " (!)",  # Add warning suffix
                            'path': item_path,
                            'has_main': False
                        })
            
            # Calculate pages (like project browser)
            if self.projects:
                valid_count = sum(1 for p in self.projects if p['has_main'])
                self.total_pages = (len(self.projects) + PROJECTS_PER_PAGE - 1) // PROJECTS_PER_PAGE
                self.update_status(f"FOUND {valid_count} PROJECT(S)")
                print(f"Found {valid_count} valid projects (with main.pd)")
            else:
                self.total_pages = 0
                self.update_status("NO PROJECTS ON USB", error=True)
                print("No project folders found on USB")
            
            # Reset to first page
            self.current_page = 0
        
        except Exception as e:
            print(f"Error scanning USB: {e}")
            import traceback
            traceback.print_exc()
            self.update_status("USB READ ERROR", error=True)
            self.projects = []
            self.current_page = 0
            self.total_pages = 0
    
    def update_display(self):
        """Update project list display (EXACT match to project browser)"""
        # Calculate start and end indices for current page
        start_idx = self.current_page * PROJECTS_PER_PAGE
        end_idx = min(start_idx + PROJECTS_PER_PAGE, len(self.projects))
        
        # Update page label
        if self.page_label:
            page_display = f"{self.current_page + 1}/{self.total_pages}" if self.total_pages > 0 else "0/0"
            self.page_label.config(text=page_display)
        
        # Update each project label (8 projects per page)
        for i in range(PROJECTS_PER_PAGE):
            project_idx = start_idx + i
            
            # Get the label tuple (name_label, meta_label)
            name_label, meta_label = self.project_labels[i]
            
            # Get parent container for background styling
            container = name_label.master
            
            if project_idx < end_idx:
                # Show project
                project = self.projects[project_idx]
                display_name = project['name']
                
                # Metadata: show "from USB" indicator
                meta_text = "from USB"
                
                # Determine if selected
                is_selected = (self.selected_project_index == project_idx)
                
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
        """Update IMPORT button based on selection (matches project browser)"""
        if self.selected_project_index is not None:
            project = self.projects[self.selected_project_index]
            if project['has_main']:
                # Valid project - IMPORT enabled (white)
                if self.import_button:
                    self.import_button.config(fg="#ffffff")
            else:
                # Missing main.pd - IMPORT disabled (dark grey)
                if self.import_button:
                    self.import_button.config(fg="#303030")
        else:
            # Nothing selected - IMPORT disabled (dark grey)
            if self.import_button:
                self.import_button.config(fg="#303030")
    
    def select_project(self, display_idx):
        """Select a project by clicking on it (display_idx is 0-7 on current page)"""
        start_idx = self.current_page * PROJECTS_PER_PAGE
        project_idx = start_idx + display_idx
        
        if project_idx < len(self.projects):
            # Toggle selection (exactly like project browser)
            if self.selected_project_index == project_idx:
                self.selected_project_index = None  # Deselect
            else:
                self.selected_project_index = project_idx  # Select
            
            self.update_display()
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.selected_project_index = None  # Clear selection when changing pages
            self.update_display()
    
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.selected_project_index = None  # Clear selection when changing pages
            self.update_display()
    
    def import_project(self):
        """Import selected project from USB"""
        if self.selected_project_index is None:
            return
        
        project = self.projects[self.selected_project_index]
        
        if not project['has_main']:
            self.update_status("CANNOT IMPORT - NO MAIN.PD", error=True)
            return
        
        project_name = project['name']
        # Remove " (!)" suffix if present
        if project_name.endswith(" (!)"):
            project_name = project_name[:-4]
        
        source_path = project['path']
        
        # Show confirmation
        def on_confirm_import():
            self.do_import(project_name, source_path)
        
        self.app.show_confirmation(
            message=f"Import '{project_name}'\nfrom USB?",
            on_yes=on_confirm_import,
            return_screen='usb_browser',
            timeout=10
        )
    
    def do_import(self, project_name, source_path):
        """Actually perform the import (copies entire folder)"""
        try:
            # Target directory
            target_dir = os.path.join(self.app.molipe_root, "my_projects")
            target_path = os.path.join(target_dir, project_name)
            
            # Check if project already exists
            if os.path.exists(target_path):
                # Generate new name with timestamp
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                new_name = f"{project_name}-{timestamp}"
                target_path = os.path.join(target_dir, new_name)
                
                print(f"Project exists, renaming to: {new_name}")
                self.update_status(f"IMPORTING AS '{new_name}'...")
            else:
                self.update_status(f"IMPORTING '{project_name}'...")
            
            # Copy entire project folder (all files and subdirectories)
            shutil.copytree(source_path, target_path)
            
            print(f"Import successful: {project_name}")
            self.update_status("✓ IMPORTED")
            
            # Return to control panel after brief delay
            self.after(1500, lambda: self.app.show_screen('control'))
        
        except Exception as e:
            print(f"Import error: {e}")
            import traceback
            traceback.print_exc()
            self.update_status("IMPORT FAILED", error=True)
    
    def update_status(self, message, error=False):
        """Update status message (matches project browser)"""
        if self.status_label:
            # Choose color based on status (like project browser)
            if error:
                color = "#e74c3c"  # Red for errors
            elif message.startswith("✓"):
                color = "#27ae60"  # Green for success
            else:
                color = "#606060"  # Grey for normal
            
            self.status_label.config(text=message.upper(), fg=color)
        print(f"USB Browser: {message}")