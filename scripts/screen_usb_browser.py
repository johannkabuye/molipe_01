"""
USB Browser Screen - Browse and import projects from USB stick
Similar to project browser but scans USB mount points
"""
import tkinter as tk
import os
import shutil
from datetime import datetime

# Grid configuration (same as other screens)
DEFAULT_ROWS = 11
COLS_PER_ROW = [4, 4, 4, 8, 4, 4, 4, 8, 4, 8, 8]
ROW_HEIGHTS = [60, 210, 50, 0, 0, 210, 50, 5, 20, 50, 50]

# USB mount points to check (Patchbox OS typically uses /media/patch/)
USB_MOUNT_POINTS = [
    "/media/patch",
    "/media/usb",
    "/mnt/usb"
]

class USBBrowserScreen(tk.Frame):
    """Browse and import projects from USB stick"""
    
    def __init__(self, parent, app):
        super().__init__(parent, bg="#000000")
        self.app = app
        
        self.rows = DEFAULT_ROWS
        self.cols_per_row = list(COLS_PER_ROW)
        
        # Browser state
        self.usb_path = None
        self.projects = []
        self.selected_project_index = None
        self.page = 0
        self.projects_per_page = 4
        
        # UI references
        self.cell_frames = []
        self.status_label = None
        self.project_buttons = []
        self.import_button = None
        self.page_label = None
        
        self._build_ui()
    
    def _build_ui(self):
        """Build grid-based USB browser UI"""
        
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
                
                # Row 0, Cell 0: MENU button
                if r == 0 and c == 0:
                    menu_button = tk.Label(
                        cell,
                        text="////<MENU",
                        bg="black", fg="white",
                        anchor="w", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.small,
                        cursor="hand2"
                    )
                    menu_button.bind("<Button-1>", lambda e: self.on_menu_clicked())
                    menu_button.pack(fill="both", expand=True)
                
                # Row 0, Cell 3: Status label
                elif r == 0 and c == 3:
                    self.status_label = tk.Label(
                        cell,
                        text="IMPORT FROM USB",
                        bg="black", fg="#606060",
                        anchor="e", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.app.fonts.status
                    )
                    self.status_label.pack(fill="both", expand=True)
                
                # Row 1: Project button 0
                elif r == 1 and c == 0:
                    btn = self._create_project_button(cell, 0)
                    self.project_buttons.append(btn)
                
                # Row 1, Column 1: Project button 1
                elif r == 1 and c == 1:
                    btn = self._create_project_button(cell, 1)
                    self.project_buttons.append(btn)
                
                # Row 5: Project buttons 2 and 3
                elif r == 5 and c == 0:
                    btn = self._create_project_button(cell, 2)
                    self.project_buttons.append(btn)
                
                elif r == 5 and c == 1:
                    btn = self._create_project_button(cell, 3)
                    self.project_buttons.append(btn)
                
                # Row 8: Page indicator (centered)
                elif r == 8:
                    if c == 0:
                        # Page label spanning columns 0-7
                        self.page_label = tk.Label(
                            row_frame,
                            text="",
                            font=self.app.fonts.status,
                            bg="black", fg="#404040",
                            anchor="center"
                        )
                        self.page_label.grid(row=0, column=0, columnspan=8, sticky="nsew")
                
                # Row 9: Navigation buttons
                elif r == 9:
                    if c == 0:
                        # UP button
                        up_btn = tk.Label(
                            cell, text="UP",
                            font=self.app.fonts.button,
                            bg="#1a1a1a", fg="#ffffff",
                            cursor="hand2", bd=0, relief="flat"
                        )
                        up_btn.bind("<Button-1>", lambda e: self.page_up())
                        up_btn.pack(fill="both", expand=True, padx=20, pady=10)
                    
                    elif c == 1:
                        # DOWN button
                        down_btn = tk.Label(
                            cell, text="DOWN",
                            font=self.app.fonts.button,
                            bg="#1a1a1a", fg="#ffffff",
                            cursor="hand2", bd=0, relief="flat"
                        )
                        down_btn.bind("<Button-1>", lambda e: self.page_down())
                        down_btn.pack(fill="both", expand=True, padx=20, pady=10)
                
                # Row 10: Action buttons
                elif r == 10:
                    if c == 0:
                        # IMPORT button
                        self.import_button = tk.Label(
                            cell, text="IMPORT",
                            font=self.app.fonts.button,
                            bg="#2c2c2c", fg="#808080",
                            cursor="hand2", bd=0, relief="flat"
                        )
                        self.import_button.bind("<Button-1>", lambda e: self.import_project())
                        self.import_button.pack(fill="both", expand=True, padx=20, pady=10)
            
            self.cell_frames.append(row_cells)
    
    def _create_project_button(self, parent, index):
        """Create a project selection button"""
        btn = tk.Label(
            parent, text="",
            font=self.app.fonts.big,
            bg="#000000", fg="#606060",
            cursor="hand2", bd=0, relief="flat", padx=20, pady=20
        )
        
        def on_click(e):
            self.select_project(index)
        
        btn.bind("<Button-1>", on_click)
        btn.pack(fill="both", expand=True)
        return btn
    
    def on_menu_clicked(self):
        """Return to control panel"""
        self.app.show_screen('control')
    
    def on_show(self):
        """Called when screen becomes visible - scan USB"""
        self.scan_usb()
        self.update_display()
    
    def scan_usb(self):
        """Scan USB mount points for projects (like preset browser)"""
        self.usb_path = None
        self.projects = []
        
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
                        # Folder exists but no main.pd
                        self.projects.append({
                            'name': item,
                            'path': item_path,
                            'has_main': False
                        })
            
            if self.projects:
                valid_count = sum(1 for p in self.projects if p['has_main'])
                self.update_status(f"FOUND {valid_count} PROJECT(S)")
                print(f"Found {valid_count} valid projects (with main.pd)")
            else:
                self.update_status("NO PROJECTS ON USB", error=True)
                print("No project folders found on USB")
        
        except Exception as e:
            print(f"Error scanning USB: {e}")
            import traceback
            traceback.print_exc()
            self.update_status("USB READ ERROR", error=True)
    
    def update_display(self):
        """Update project list display"""
        start_idx = self.page * self.projects_per_page
        end_idx = start_idx + self.projects_per_page
        page_projects = self.projects[start_idx:end_idx]
        
        # Update project buttons
        for i, btn in enumerate(self.project_buttons):
            if i < len(page_projects):
                project = page_projects[i]
                name = project['name']
                
                # Show warning if no main.pd
                if not project['has_main']:
                    name += " (NO MAIN.PD)"
                
                btn.config(text=name)
                
                # Highlight if selected
                global_idx = start_idx + i
                if global_idx == self.selected_project_index:
                    btn.config(bg="#2c2c2c", fg="#ffffff")
                else:
                    btn.config(bg="#000000", fg="#606060")
            else:
                # Empty slot
                btn.config(text="", bg="#000000")
        
        # Update page indicator
        total_pages = (len(self.projects) + self.projects_per_page - 1) // self.projects_per_page
        if total_pages > 0:
            current_page = self.page + 1
            self.page_label.config(text=f"PAGE {current_page} / {total_pages}")
        else:
            self.page_label.config(text="")
        
        # Update IMPORT button state
        self.update_import_button()
    
    def select_project(self, button_index):
        """Select a project by button index"""
        global_index = self.page * self.projects_per_page + button_index
        
        if global_index < len(self.projects):
            if self.selected_project_index == global_index:
                # Deselect if clicking same project
                self.selected_project_index = None
            else:
                # Select new project
                self.selected_project_index = global_index
            
            self.update_display()
    
    def page_up(self):
        """Go to previous page"""
        if self.page > 0:
            self.page -= 1
            self.selected_project_index = None
            self.update_display()
    
    def page_down(self):
        """Go to next page"""
        total_pages = (len(self.projects) + self.projects_per_page - 1) // self.projects_per_page
        if self.page < total_pages - 1:
            self.page += 1
            self.selected_project_index = None
            self.update_display()
    
    def update_import_button(self):
        """Update IMPORT button state based on selection"""
        if self.import_button:
            if self.selected_project_index is not None:
                project = self.projects[self.selected_project_index]
                if project['has_main']:
                    # Valid project - enable import
                    self.import_button.config(bg="#cc5500", fg="#ffffff")
                else:
                    # No main.pd - disable
                    self.import_button.config(bg="#2c2c2c", fg="#808080")
            else:
                # Nothing selected - disable
                self.import_button.config(bg="#2c2c2c", fg="#808080")
    
    def import_project(self):
        """Import selected project from USB"""
        if self.selected_project_index is None:
            return
        
        project = self.projects[self.selected_project_index]
        
        if not project['has_main']:
            self.update_status("CANNOT IMPORT - NO MAIN.PD", error=True)
            return
        
        project_name = project['name']
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
        """Actually perform the import"""
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
            
            # Copy project folder
            shutil.copytree(source_path, target_path)
            
            print(f"Import successful: {project_name}")
            self.update_status("IMPORT COMPLETE")
            
            # Return to control panel after brief delay
            self.after(1500, lambda: self.app.show_screen('control'))
        
        except Exception as e:
            print(f"Import error: {e}")
            import traceback
            traceback.print_exc()
            self.update_status("IMPORT FAILED", error=True)
    
    def update_status(self, message, error=False):
        """Update status message"""
        if self.status_label:
            color = "#e74c3c" if error else "#606060"
            self.status_label.config(text=message.upper(), fg=color)
        print(f"USB Browser: {message}")