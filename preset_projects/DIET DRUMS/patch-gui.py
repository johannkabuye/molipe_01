#!/usr/bin/env python3
"""
Patch Display Screen - UDP-controlled GUI integrated with molipe navigation
MENU button integrated in grid at cell (0,0) - no z-order issues
"""
import os
import sys
import socket
import threading
import logging
import time
from queue import Queue, Empty
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

import tkinter as tk
from tkinter import font as tkfont

# Import PDStatus for status polling
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from process_manager import PDStatus
except ImportError:
    # Fallback if process_manager not updated yet
    from enum import Enum
    class PDStatus(Enum):
        STOPPED = "stopped"
        INITIALIZING_MIDI = "initializing_midi"
        STARTING = "starting"
        RUNNING = "running"
        ERROR = "error"

# Configuration
PROTOCOL_VERSION = "1.0"
HOST = "0.0.0.0"
PORT = 9001
SOCKET_TIMEOUT_SEC = 1.0
SOCKET_BUFFER_SIZE = 1 << 20

DEFAULT_ROWS = 11
COLS_PER_ROW = [4, 4, 4, 8, 4, 4, 4, 8, 4, 8, 8]
BIG_FONT_ROWS = {1, 2, 5, 6, 9, 10}
BAR_ROWS = {3, 7}

SMALL_FONT_PT = 27
BIG_FONT_PT = 29
HEAD_ROW_BONUS_PT = 0
FONT_FAMILY_PRIMARY = "Sunflower"
FONT_FAMILY_FALLBACK = "TkDefaultFont"

ROW_HEIGHTS = [60, 210, 50, 0, 0, 210, 50, 5, 20, 50, 50]

RING_START_ANGLE = 210
RING_END_ANGLE = 330
RING_SWEEP_MAX = 240
RING_CENTER_FONT_SIZE = 35
RING_INNER_RADIUS = 70
RING_OUTER_RADIUS = 103
RING_EXTRA1_RADIUS = 120
RING_EXTRA2_RADIUS = 127
RING_OUTER_ARC_WIDTH = 10
RING_INNER_ARC_WIDTH = 27
RING_EXTRA_ARC_WIDTH = 4
RING_EXTRA_DOT_SIZE = 8

BAR_BORDER_COLOR = "#303030"
BAR_FILL_COLOR = "#606060"
BAR_BG_COLOR = "#000000"
BAR_GAP_PIXELS = 2
BAR_BORDER_WIDTH = 2

POLL_INTERVAL_MS = 33
MAX_APPLIES_PER_TICK = 50

LOG_LEVEL = logging.ERROR
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

def validate_color(color: str) -> bool:
    if not color:
        return False
    if color.startswith('#'):
        return len(color) in (4, 7, 9) and all(c in '0123456789abcdefABCDEF' for c in color[1:])
    return True

_color_cache: Dict[Tuple[str, float], str] = {}

def lighten_color(hex_color: str, factor: float) -> str:
    cache_key = (hex_color, factor)
    if cache_key in _color_cache:
        return _color_cache[cache_key]
    
    if not hex_color.startswith('#'):
        return hex_color
    
    hex_color_clean = hex_color.lstrip('#')
    if len(hex_color_clean) == 3:
        hex_color_clean = ''.join([c*2 for c in hex_color_clean])
    
    try:
        r = int(hex_color_clean[0:2], 16)
        g = int(hex_color_clean[2:4], 16)
        b = int(hex_color_clean[4:6], 16)
        
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        
        result = f'#{r:02x}{g:02x}{b:02x}'
        _color_cache[cache_key] = result
        return result
    except (ValueError, IndexError):
        return hex_color

@dataclass
class PerformanceMetrics:
    messages_received: int = 0
    messages_processed: int = 0
    last_message_time: float = 0.0
    
    def update_received(self):
        self.messages_received += 1
        self.last_message_time = time.time()
    
    def update_processed(self):
        self.messages_processed += 1

class HorizontalBar(tk.Canvas):
    def __init__(self, master, width: int = 200, height: int = 20,
                 fill_color: str = BAR_FILL_COLOR,
                 border_color: str = BAR_BORDER_COLOR,
                 bg_color: str = BAR_BG_COLOR,
                 gap: int = BAR_GAP_PIXELS,
                 border_width: int = BAR_BORDER_WIDTH, **kw):
        super().__init__(master, width=width, height=height, bg=bg_color,
                        highlightthickness=0, bd=0, **kw)
        
        self._fill_color = fill_color
        self._border_color = border_color
        self._bg_color = bg_color
        self._gap = gap
        self._border_width = border_width
        self._value = 0
        
        self._border_rect = None
        self._fill_rect = None
        
        self.bind("<Configure>", lambda e: self._redraw())
        self._redraw()
    
    @staticmethod
    def _clip_value(v: Any) -> int:
        try:
            v = int(v)
        except (ValueError, TypeError):
            v = 0
        return max(0, min(127, v))
    
    def set_value(self, value: int) -> None:
        self._value = self._clip_value(value)
        self._update_fill()
    
    def _redraw(self) -> None:
        self.delete("all")
        
        w = self.winfo_width()
        h = self.winfo_height()
        
        if w < 4 or h < 4:
            return
        
        self._border_rect = self.create_rectangle(
            0, 0, w, h,
            outline=self._border_color,
            width=self._border_width,
            fill=self._bg_color
        )
        
        gap = self._gap + self._border_width
        self._fill_rect = self.create_rectangle(
            gap, gap, gap, h - gap,
            outline="",
            fill=self._fill_color
        )
        
        self._update_fill()
    
    def _update_fill(self) -> None:
        if self._fill_rect is None:
            return
        
        w = self.winfo_width()
        h = self.winfo_height()
        
        if w < 4 or h < 4:
            return
        
        gap = self._gap + self._border_width
        available_width = w - (2 * gap)
        fill_width = (available_width * self._value) / 127.0
        
        x1 = gap
        y1 = gap
        x2 = gap + fill_width
        y2 = h - gap
        
        try:
            self.coords(self._fill_rect, x1, y1, x2, y2)
        except tk.TclError:
            pass

class DualRing(tk.Frame):
    def __init__(self, master, size: int = 200, fg_outer: str = "#606060", 
                 fg_inner: str = "#ffffff", bg: str = "#000000", 
                 w_outer: int = None, w_inner: int = None, 
                 text_color: str = "#ffffff", **kw):
        super().__init__(master, bg=bg, **kw)
        
        self._display_size = int(size)
        self._bg = bg
        self._fg_outer = fg_outer
        self._fg_inner = fg_inner
        self._w_outer = int(w_outer) if w_outer is not None else RING_OUTER_ARC_WIDTH
        self._w_inner = int(w_inner) if w_inner is not None else RING_INNER_ARC_WIDTH
        self._text_color = text_color
        self._outer_val = 0
        self._inner_val = 0
        self._extra_arc1_val = 0
        self._extra_arc2_val = 0
        self._center_override: Optional[str] = None
        
        self._cached_light_color1: Optional[str] = None
        self._cached_light_color2: Optional[str] = None
        self._last_fg_inner: Optional[str] = None
        
        self._last_extra1_val = -1
        self._last_extra2_val = -1
        
        self.canvas = tk.Canvas(
            self, width=self._display_size, height=self._display_size,
            bg=bg, highlightthickness=0, bd=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        self._outer_arc_id: Optional[int] = None
        self._inner_arc_id: Optional[int] = None
        self._extra_arc1_id: Optional[int] = None
        self._extra_arc2_id: Optional[int] = None
        self._extra_dot1_id: Optional[int] = None
        self._extra_dot2_id: Optional[int] = None
        self._label_id: Optional[int] = None
        self._extra_label1_id: Optional[int] = None
        self._extra_label2_id: Optional[int] = None
        
        self.canvas.bind("<Configure>", lambda e: self._redraw())
        self._redraw()
    
    @staticmethod
    def _clip_value(v: Any) -> int:
        try:
            v = int(v)
        except (ValueError, TypeError):
            v = 0
        return max(0, min(127, v))
    
    def set_values(self, outer_v: int, inner_v: int) -> None:
        self._outer_val = self._clip_value(outer_v)
        self._inner_val = self._clip_value(inner_v)
        self._update_extents()
        self._update_label()
    
    def set_outer(self, v: int) -> None:
        self._outer_val = self._clip_value(v)
        self._update_extents()
    
    def set_inner(self, v: int) -> None:
        self._inner_val = self._clip_value(v)
        self._update_extents()
        self._update_label()
    
    def set_extra_arcs(self, val1: int, val2: int) -> None:
        self._extra_arc1_val = self._clip_value(val1)
        self._extra_arc2_val = self._clip_value(val2)
        self._update_extents()
    
    def set_center_text(self, text: Optional[str]) -> None:
        self._center_override = text if text else None
        self._update_label()
    
    def restyle(self, fg_outer: Optional[str] = None, fg_inner: Optional[str] = None,
                bg: Optional[str] = None, w_outer: Optional[int] = None,
                w_inner: Optional[int] = None, text_color: Optional[str] = None) -> None:
        if fg_outer is not None and validate_color(fg_outer):
            self._fg_outer = fg_outer
        if fg_inner is not None and validate_color(fg_inner):
            self._fg_inner = fg_inner
            self._cached_light_color1 = None
            self._cached_light_color2 = None
            self._last_fg_inner = None
        if w_outer is not None:
            self._w_outer = int(w_outer)
        if w_inner is not None:
            self._w_inner = int(w_inner)
        if text_color is not None and validate_color(text_color):
            self._text_color = text_color
        if bg is not None and validate_color(bg):
            self._bg = bg
            try:
                self.configure(bg=bg)
                self.canvas.configure(bg=bg)
            except tk.TclError:
                pass
        self._redraw()
    
    def resize(self, size_px: int) -> None:
        self._display_size = int(size_px)
        self.canvas.config(width=self._display_size, height=self._display_size)
        self._redraw()
    
    def _bbox_for_radius(self, radius: int) -> Tuple[int, int, int, int]:
        w = max(2, self.canvas.winfo_width())
        h = max(2, self.canvas.winfo_height())
        cx, cy = w // 2, h // 2
        return (cx - radius, cy - radius, cx + radius, cy + radius)
    
    def _get_light_colors(self) -> Tuple[str, str]:
        if self._cached_light_color1 is None or self._fg_inner != self._last_fg_inner:
            self._cached_light_color1 = lighten_color(self._fg_inner, 0.3)
            self._cached_light_color2 = lighten_color(self._fg_inner, 0.5)
            self._last_fg_inner = self._fg_inner
        return self._cached_light_color1, self._cached_light_color2
    
    def _redraw(self) -> None:
        self.canvas.delete("all")
        
        inner_bbox = self._bbox_for_radius(RING_INNER_RADIUS)
        outer_bbox = self._bbox_for_radius(RING_OUTER_RADIUS)
        extra_arc1_bbox = self._bbox_for_radius(RING_EXTRA1_RADIUS)
        extra_arc2_bbox = self._bbox_for_radius(RING_EXTRA2_RADIUS)
        
        light_color1, light_color2 = self._get_light_colors()
        
        self.canvas.create_oval(*inner_bbox, outline="#000", width=self._w_inner)
        self.canvas.create_oval(*outer_bbox, outline="#000", width=self._w_outer)
        self.canvas.create_oval(*extra_arc1_bbox, outline="#000", width=RING_EXTRA_ARC_WIDTH)
        self.canvas.create_oval(*extra_arc2_bbox, outline="#000", width=RING_EXTRA_ARC_WIDTH)
        
        self._inner_arc_id = self.canvas.create_arc(
            *inner_bbox, start=RING_START_ANGLE, extent=0, style="arc",
            outline=self._fg_inner, width=self._w_inner
        )
        
        self._outer_arc_id = self.canvas.create_arc(
            *outer_bbox, start=RING_START_ANGLE, extent=0, style="arc",
            outline=self._fg_outer, width=self._w_outer
        )
        
        self._extra_arc1_id = self.canvas.create_arc(
            *extra_arc1_bbox, start=RING_START_ANGLE, extent=0, style="arc",
            outline=light_color1, width=RING_EXTRA_ARC_WIDTH
        )
        
        self._extra_arc2_id = self.canvas.create_arc(
            *extra_arc2_bbox, start=RING_START_ANGLE, extent=0, style="arc",
            outline=light_color2, width=RING_EXTRA_ARC_WIDTH
        )
        
        self._extra_dot1_id = self.canvas.create_oval(
            0, 0, RING_EXTRA_DOT_SIZE, RING_EXTRA_DOT_SIZE,
            fill=light_color1, outline=""
        )
        self._extra_dot2_id = self.canvas.create_oval(
            0, 0, RING_EXTRA_DOT_SIZE, RING_EXTRA_DOT_SIZE,
            fill=light_color2, outline=""
        )
        
        cx, cy = self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2
        font = (FONT_FAMILY_PRIMARY, RING_CENTER_FONT_SIZE, "bold")
        display_val = max(1, int(self._inner_val))
        self._label_id = self.canvas.create_text(
            cx, cy, text=str(display_val), fill=self._text_color, font=font
        )
        
        extra_font = (FONT_FAMILY_PRIMARY, 24, "bold")
        self._extra_label2_id = self.canvas.create_text(
            0, 5, text="0", fill=light_color2, font=extra_font, anchor="nw"
        )
        self._extra_label1_id = self.canvas.create_text(
            self.canvas.winfo_width(), 5, text="0", fill=light_color1, font=extra_font, anchor="ne"
        )
        
        self._update_extents()
    
    def _update_extents(self) -> None:
        ext_outer = -RING_SWEEP_MAX * (self._outer_val / 127.0)
        ext_inner = -RING_SWEEP_MAX * (self._inner_val / 127.0)
        ext_extra1 = -RING_SWEEP_MAX * (self._extra_arc1_val / 127.0)
        ext_extra2 = -RING_SWEEP_MAX * (self._extra_arc2_val / 127.0)
        
        if self._outer_arc_id is not None:
            try:
                self.canvas.itemconfig(self._outer_arc_id, extent=ext_outer)
            except tk.TclError:
                pass
        
        if self._inner_arc_id is not None:
            try:
                self.canvas.itemconfig(self._inner_arc_id, extent=ext_inner)
            except tk.TclError:
                pass
        
        light_color1, light_color2 = self._get_light_colors()
        
        if self._extra_arc1_id is not None:
            try:
                self.canvas.itemconfig(self._extra_arc1_id, extent=ext_extra1, outline=light_color1)
            except tk.TclError:
                pass
        
        if self._extra_arc2_id is not None:
            try:
                self.canvas.itemconfig(self._extra_arc2_id, extent=ext_extra2, outline=light_color2)
            except tk.TclError:
                pass
        
        if (self._extra_arc1_val != self._last_extra1_val or 
            self._extra_arc2_val != self._last_extra2_val):
            self._update_dots(ext_extra1, ext_extra2, light_color1, light_color2)
            self._last_extra1_val = self._extra_arc1_val
            self._last_extra2_val = self._extra_arc2_val
    
    def _update_dots(self, ext_extra1: float, ext_extra2: float, 
                     light_color1: str, light_color2: str) -> None:
        import math
        
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        cx, cy = w // 2, h // 2
        
        radius1 = RING_EXTRA1_RADIUS
        radius2 = RING_EXTRA2_RADIUS
        
        peak_angle1_deg = RING_START_ANGLE + ext_extra1
        peak_angle2_deg = RING_START_ANGLE + ext_extra2
        
        peak_angle1_rad = math.radians(-peak_angle1_deg)
        peak_angle2_rad = math.radians(-peak_angle2_deg)
        
        dot_radius = RING_EXTRA_DOT_SIZE // 2
        dot1_x = cx + radius1 * math.cos(peak_angle1_rad)
        dot1_y = cy + radius1 * math.sin(peak_angle1_rad)
        dot2_x = cx + radius2 * math.cos(peak_angle2_rad)
        dot2_y = cy + radius2 * math.sin(peak_angle2_rad)
        
        if self._extra_dot1_id is not None:
            try:
                self.canvas.coords(
                    self._extra_dot1_id,
                    dot1_x - dot_radius, dot1_y - dot_radius,
                    dot1_x + dot_radius, dot1_y + dot_radius
                )
                self.canvas.itemconfig(self._extra_dot1_id, fill=light_color1)
            except tk.TclError:
                pass
        
        if self._extra_dot2_id is not None:
            try:
                self.canvas.coords(
                    self._extra_dot2_id,
                    dot2_x - dot_radius, dot2_y - dot_radius,
                    dot2_x + dot_radius, dot2_y + dot_radius
                )
                self.canvas.itemconfig(self._extra_dot2_id, fill=light_color2)
            except tk.TclError:
                pass
        
        if self._extra_label1_id is not None:
            try:
                self.canvas.itemconfig(
                    self._extra_label1_id, 
                    text=str(max(0, int(self._extra_arc1_val))),
                    fill=light_color1
                )
                self.canvas.coords(self._extra_label1_id, w, 5)
            except tk.TclError:
                pass
        
        if self._extra_label2_id is not None:
            try:
                self.canvas.itemconfig(
                    self._extra_label2_id, 
                    text=str(max(0, int(self._extra_arc2_val))),
                    fill=light_color2
                )
                self.canvas.coords(self._extra_label2_id, 0, 5)
            except tk.TclError:
                pass
    
    def _update_label(self) -> None:
        if self._label_id is None:
            return
        
        cx, cy = self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2
        font = (FONT_FAMILY_PRIMARY, RING_CENTER_FONT_SIZE, "bold")
        
        if self._center_override is not None:
            display_text = str(self._center_override)
        else:
            display_text = str(max(1, int(self._inner_val)))
        
        try:
            self.canvas.itemconfig(self._label_id, text=display_text, fill=self._text_color, font=font)
            self.canvas.coords(self._label_id, cx, cy)
        except tk.TclError:
            pass

class PatchDisplayScreen(tk.Frame):
    """Patch display screen with UDP control and MENU button in grid"""
    
    def __init__(self, parent, app):
        super().__init__(parent, bg="#000000")
        self.app = app
        
        self.rows = DEFAULT_ROWS
        self.cols_per_row = list(COLS_PER_ROW)
        
        self._init_fonts()
        
        self.udp_queue = Queue()
        self.metrics = PerformanceMetrics()
        self.udp_thread = None
        self.udp_stop_flag = False  # Flag to stop UDP thread
        self.udp_socket = None  # Store socket reference for cleanup
        
        self.vars: List[List[tk.StringVar]] = []
        self.labels: List[List[tk.Label]] = []
        self.cell_frames: List[List[tk.Frame]] = []
        self.row_frames: List[tk.Frame] = []
        
        self._build_ui()
        
        self.last_text: List[List[Optional[str]]] = []
        self.last_fg: List[List[Optional[str]]] = []
        self.last_bg: List[List[Optional[str]]] = []
        self.last_anchor: List[List[Optional[str]]] = []
        self._init_caches()
        
        self.ring_holders: List[List[Optional[tk.Frame]]] = [
            [None] * self.cols_per_row[r] for r in range(self.rows)
        ]
        self.rings: List[List[Optional[DualRing]]] = [
            [None] * self.cols_per_row[r] for r in range(self.rows)
        ]
        
        self.bar_holders: List[List[Optional[tk.Frame]]] = [
            [None] * self.cols_per_row[r] for r in range(self.rows)
        ]
        self.bars: List[List[Optional[HorizontalBar]]] = [
            [None] * self.cols_per_row[r] for r in range(self.rows)
        ]
        
        self.pending_latest: Dict[Tuple, Any] = {}
        
        # Loading state UI
        self._create_loading_ui()
        self.loading_visible = False
        self.status_polling_id = None  # Track scheduled status polling
        
        self._start_udp_listener()
        self.after(POLL_INTERVAL_MS, self._drain_and_apply)
        
        # Start status polling for PD startup (will be restarted by on_show)
        # Don't call it here - let on_show() handle it
        # self.check_pd_status()
    
    def _init_fonts(self) -> None:
        try:
            self.small_font = tkfont.Font(
                family=FONT_FAMILY_PRIMARY, 
                size=SMALL_FONT_PT, 
                weight="bold"
            )
            self.big_font = tkfont.Font(
                family=FONT_FAMILY_PRIMARY, 
                size=BIG_FONT_PT, 
                weight="bold"
            )
            self.head_font = tkfont.Font(
                family=FONT_FAMILY_PRIMARY,
                size=SMALL_FONT_PT + HEAD_ROW_BONUS_PT,
                weight="bold"
            )
        except Exception:
            self.small_font = tkfont.Font(
                family=FONT_FAMILY_FALLBACK, 
                size=SMALL_FONT_PT, 
                weight="bold"
            )
            self.big_font = tkfont.Font(
                family=FONT_FAMILY_FALLBACK, 
                size=BIG_FONT_PT, 
                weight="bold"
            )
            self.head_font = tkfont.Font(
                family=FONT_FAMILY_FALLBACK,
                size=SMALL_FONT_PT + HEAD_ROW_BONUS_PT,
                weight="bold"
            )
    
    def _create_loading_ui(self):
        """Create loading screen overlay"""
        # Loading overlay (shown during PD startup)
        self.loading_overlay = tk.Frame(self, bg="#000000")
        
        # Loading title
        self.loading_title = tk.Label(
            self.loading_overlay,
            text="LOADING...",
            font=("Sunflower", 36, "bold"),
            fg="#ffffff",
            bg="#000000"
        )
        self.loading_title.pack(pady=(200, 20))
        
        # Status message
        self.loading_message = tk.Label(
            self.loading_overlay,
            text="Initializing MIDI...",
            font=("Sunflower", 18),
            fg="#888888",
            bg="#000000"
        )
        self.loading_message.pack()
    
    def _init_caches(self) -> None:
        self.last_text = [[None] * self.cols_per_row[r] for r in range(self.rows)]
        self.last_fg = [[None] * self.cols_per_row[r] for r in range(self.rows)]
        self.last_bg = [[None] * self.cols_per_row[r] for r in range(self.rows)]
        self.last_anchor = [[None] * self.cols_per_row[r] for r in range(self.rows)]
    
    def _build_ui(self):
        """Build the patch display UI with MENU button in cell (0,0)"""
        
        # Main grid container
        self.container = tk.Frame(self, bg="black", bd=0, highlightthickness=0)
        self.container.pack(expand=True, fill="both")
        
        self.container.columnconfigure(0, weight=1, uniform="outer_col")
        
        self.vars.clear()
        self.labels.clear()
        self.cell_frames.clear()
        self.row_frames.clear()
        
        # Build 11-row grid
        for r in range(self.rows):
            fixed_h = ROW_HEIGHTS[r] if r < len(ROW_HEIGHTS) else 0
            self.container.rowconfigure(r, minsize=fixed_h, weight=0)
            
            row_frame = tk.Frame(self.container, bg="black", bd=0, highlightthickness=0)
            row_frame.grid(row=r, column=0, sticky="nsew", padx=0, pady=0)
            row_frame.grid_propagate(False)
            
            if fixed_h:
                row_frame.configure(height=fixed_h)
            
            self.row_frames.append(row_frame)
            
            cols = self.cols_per_row[r]
            for c in range(cols):
                row_frame.columnconfigure(c, weight=1, uniform=f"row{r}_col")
            row_frame.rowconfigure(0, weight=1)
            
            row_vars, row_labels, row_cells = [], [], []
            
            for c in range(cols):
                cell = tk.Frame(row_frame, bg="black", bd=0, highlightthickness=0)
                cell.grid(row=0, column=c, sticky="nsew", padx=0, pady=0)
                cell.grid_propagate(False)
                row_cells.append(cell)
                
                var = tk.StringVar(value="")
                row_vars.append(var)
                
                # SPECIAL: First cell (0,0) is MENU button
                if r == 0 and c == 0:
                    lbl = tk.Label(
                        cell,
                        text="////MENU",
                        bg="black", fg="white",  # Black background, white text
                        anchor="w", padx=10, pady=0, bd=0, highlightthickness=0,
                        font=self.head_font,
                        cursor="hand2"
                    )
                    lbl.bind("<Button-1>", lambda e: self.go_home())
                else:
                    # Normal cell
                    if r == 0:
                        fnt = self.head_font
                    elif r in BIG_FONT_ROWS:
                        fnt = self.big_font
                    else:
                        fnt = self.small_font
                    
                    if r in {2, 6}:
                        anchor = "n"
                    else:
                        anchor = "w"
                    
                    lbl = tk.Label(
                        cell, textvariable=var,
                        bg="black", fg="white",
                        anchor=anchor, padx=0, pady=0, bd=0, highlightthickness=0
                    )
                    lbl.configure(font=fnt)
                
                lbl.pack(fill="both", expand=True)
                row_labels.append(lbl)
            
            self.vars.append(row_vars)
            self.labels.append(row_labels)
            self.cell_frames.append(row_cells)
    
    def _start_udp_listener(self):
        """Start UDP listener thread"""
        
        def parse_message(line: str) -> Optional[Tuple]:
            if not line:
                return None
            
            if line.endswith(";"):
                line = line[:-1].rstrip()
            
            parts = line.split()
            if not parts:
                return None
            
            head = parts[0].upper()
            
            try:
                if head == "ARC" and len(parts) >= 5:
                    c, r = int(parts[1]), int(parts[2])
                    val1, val2 = int(parts[3]), int(parts[4])
                    return ("ARC_VALUE", r, c, val1, val2)
                
                if head == "BAR" and len(parts) >= 4:
                    r, c = int(parts[1]), int(parts[2])
                    value = int(parts[3])
                    return ("BAR_VALUE", r, c, value)
                
                if head == "ALIGN" and len(parts) >= 4:
                    r, c, align = int(parts[1]), int(parts[2]), parts[3]
                    return ("ALIGN_CELL", r, c, align)
                
                if head == "BG" and len(parts) >= 4:
                    r, c, bg = int(parts[1]), int(parts[2]), parts[3]
                    return ("BG_CELL", r, c, bg)
                
                if head == "RING" and len(parts) >= 9:
                    c, r = int(parts[1]), int(parts[2])
                    fg_out, fg_in, bg = parts[3], parts[4], parts[5]
                    size_px, w_out, w_in = int(parts[6]), int(parts[7]), int(parts[8])
                    return ("RING_STYLE", r, c, fg_out, fg_in, bg, size_px, w_out, w_in)
                
                if head == "RINGVAL" and len(parts) >= 5:
                    c, r = int(parts[1]), int(parts[2])
                    outer, inner = int(parts[3]), int(parts[4])
                    text = " ".join(parts[5:]).rstrip(";") if len(parts) > 5 else None
                    return ("RING_VALUE", r, c, outer, inner, text)
                
                if head == "RINGSET" and len(parts) >= 11:
                    c, r = int(parts[1]), int(parts[2])
                    outer, inner = int(parts[3]), int(parts[4])
                    fg_out, fg_in, bg = parts[5], parts[6], parts[7]
                    size_px, w_out, w_in = int(parts[8]), int(parts[9]), int(parts[10])
                    return ("RING_SET", r, c, outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in)
                
                if len(parts) >= 5:
                    c, r = int(parts[0]), int(parts[1])
                    
                    if len(parts) >= 6:
                        fg, bg, align = parts[2], parts[3], parts[4]
                        text = " ".join(parts[5:]).rstrip(";")
                    else:
                        fg, bg, align = parts[2], parts[3], None
                        text = " ".join(parts[4:]).rstrip(";")
                    
                    return ("SET", r, c, fg, bg, align, text)
            
            except (ValueError, IndexError):
                return None
            
            return None
        
        def listener_loop():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket = sock  # Store reference for cleanup
            
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE)
            except OSError:
                pass
            
            # CRITICAL: Allow port reuse when reloading projects
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except OSError:
                pass
            
            try:
                sock.bind((HOST, PORT))
                sock.settimeout(SOCKET_TIMEOUT_SEC)
                print(f"UDP listener bound to {HOST}:{PORT}")
            except OSError as e:
                print(f"ERROR: Could not bind UDP socket: {e}")
                print(f"Port {PORT} may already be in use by another patch screen")
                self.udp_socket = None
                return
            
            while not self.udp_stop_flag:  # Check stop flag
                try:
                    data, addr = sock.recvfrom(16384)
                    self.metrics.update_received()
                    
                    line = data.decode("utf-8", errors="replace").strip()
                    msg = parse_message(line)
                    
                    if msg:
                        self.udp_queue.put(msg)
                        self.metrics.update_processed()
                
                except socket.timeout:
                    continue  # Timeout is normal, keep checking stop flag
                except Exception:
                    if not self.udp_stop_flag:  # Only log if not intentionally stopped
                        continue
            
            # Clean shutdown
            print("UDP listener stopping...")
            try:
                sock.close()
            except:
                pass
            self.udp_socket = None
            print("UDP listener stopped")
        
        self.udp_thread = threading.Thread(target=listener_loop, daemon=True, name="UDPListener")
        self.udp_thread.start()
    
    def _drain_and_apply(self):
        """Process queued UDP messages"""
        
        while True:
            try:
                msg = self.udp_queue.get_nowait()
            except Empty:
                break
            
            kind = msg[0]
            
            if kind == "BAR_VALUE":
                _, r, c, value = msg
                self.pending_latest[("BAR", r, c)] = value
            
            elif kind == "BG_CELL":
                _, r, c, bg = msg
                self.pending_latest[("BG", r, c)] = bg
            
            elif kind == "ALIGN_CELL":
                _, r, c, align = msg
                self.pending_latest[("ALIGN", r, c)] = align
            
            elif kind == "SET":
                _, r, c, fg, bg, align, text = msg
                self.pending_latest[("SET", r, c)] = (text, fg, bg, align)
            
            elif kind == "RING_STYLE":
                _, r, c, fg_out, fg_in, bg, size_px, w_out, w_in = msg
                self.pending_latest[("RING_STYLE", r, c)] = (fg_out, fg_in, bg, size_px, w_out, w_in)
            
            elif kind == "RING_VALUE":
                _, r, c, outer, inner, text = msg
                self.pending_latest[("RING_VALUE", r, c)] = (outer, inner, text)
            
            elif kind == "RING_SET":
                _, r, c, outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in = msg
                self.pending_latest[("RING_SET", r, c)] = (outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in)
            
            elif kind == "ARC_VALUE":
                _, r, c, val1, val2 = msg
                self.pending_latest[("ARC", r, c)] = (val1, val2)
        
        applied = 0
        
        for key, bg in list(self.pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "BG":
                _, r, c = key
                self.set_cell(r, c, None, None, bg, None)
                del self.pending_latest[key]
                applied += 1
        
        for key, align in list(self.pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "ALIGN":
                _, r, c = key
                self.set_cell(r, c, None, None, None, align)
                del self.pending_latest[key]
                applied += 1
        
        for key, value in list(self.pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "BAR":
                _, r, c = key
                self.set_bar_value(r, c, value)
                del self.pending_latest[key]
                applied += 1
        
        for key, payload in list(self.pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "RING_SET":
                _, r, c = key
                outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in = payload
                self.set_ring_all(r, c, outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in)
                del self.pending_latest[key]
                applied += 1
        
        for key, payload in list(self.pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "RING_STYLE":
                _, r, c = key
                fg_out, fg_in, bg, size_px, w_out, w_in = payload
                self.set_ring_style(r, c, fg_out, fg_in, bg, size_px, w_out, w_in)
                del self.pending_latest[key]
                applied += 1
        
        for key, payload in list(self.pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "RING_VALUE":
                _, r, c = key
                outer, inner, text = payload
                self.set_ring_value(r, c, outer, inner)
                if text is not None:
                    self.set_ring_text(r, c, text)
                del self.pending_latest[key]
                applied += 1
        
        for key, payload in list(self.pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "ARC":
                _, r, c = key
                val1, val2 = payload
                self.set_ring_extra_arcs(r, c, val1, val2)
                del self.pending_latest[key]
                applied += 1
        
        for key, payload in list(self.pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "SET":
                _, r, c = key
                text, fg, bg, align = payload
                # Skip cell (0,0) - that's the MENU button
                if not (r == 0 and c == 0):
                    self.set_cell(r, c, text, fg, bg, align)
                del self.pending_latest[key]
                applied += 1
        
        self.after(POLL_INTERVAL_MS, self._drain_and_apply)
    
    def _ensure_bars(self, r: int, c: int) -> None:
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            return
        
        if r not in BAR_ROWS:
            return
        
        lbl = self.labels[r][c]
        if lbl.winfo_manager():
            lbl.forget()
        
        holder = self.bar_holders[r][c]
        if holder is None:
            holder = tk.Frame(self.cell_frames[r][c], bg="black", bd=0, highlightthickness=0)
            holder.pack(fill="both", expand=True, padx=2, pady=2)
            self.bar_holders[r][c] = holder
            
            bar = HorizontalBar(holder, width=200, height=30)
            bar.pack(fill="both", expand=True)
            self.bars[r][c] = bar
    
    def set_bar_value(self, r: int, c: int, value: int) -> None:
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            return
        
        if r not in BAR_ROWS:
            return
        
        self._ensure_bars(r, c)
        
        bar = self.bars[r][c]
        if bar:
            bar.set_value(value)
    
    def _ensure_ring(self, r: int, c: int, fg_out: str, fg_in: str, 
                     bg: str, size_px: int, w_out: int, w_in: int) -> None:
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            return
        
        # Don't replace MENU button
        if r == 0 and c == 0:
            return
        
        lbl = self.labels[r][c]
        if lbl.winfo_manager():
            lbl.forget()
        
        holder = self.ring_holders[r][c]
        if holder is None:
            holder = tk.Frame(self.cell_frames[r][c], bg="black", bd=0, highlightthickness=0)
            holder.place(relx=0.5, rely=0.0, anchor="n")
            self.ring_holders[r][c] = holder
        
        ring = self.rings[r][c]
        if ring is None:
            ring = DualRing(
                holder, size=260, fg_outer=fg_out, fg_inner=fg_in,
                bg=bg, w_outer=w_out, w_inner=w_in, text_color="#e3e3e3"
            )
            ring.pack(fill="both", expand=True)
            self.rings[r][c] = ring
        else:
            ring.restyle(fg_outer=fg_out, fg_inner=fg_in, bg=bg, 
                        w_outer=w_out, w_inner=w_in)
    
    def set_ring_style(self, r: int, c: int, fg_out: str, fg_in: str, 
                      bg: str, size_px: int, w_out: int, w_in: int) -> None:
        self._ensure_ring(r, c, fg_out, fg_in, bg, size_px, w_out, w_in)
    
    def set_ring_value(self, r: int, c: int, outer: int, inner: int) -> None:
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            return
        
        if r == 0 and c == 0:
            return
        
        ring = self.rings[r][c]
        if ring is None:
            self._ensure_ring(r, c, "#606060", "#ffffff", "#000000", 280, RING_OUTER_ARC_WIDTH, RING_INNER_ARC_WIDTH)
            ring = self.rings[r][c]
        
        if ring:
            ring.set_values(outer, inner)
    
    def set_ring_text(self, r: int, c: int, text: Optional[str]) -> None:
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            return
        
        if r == 0 and c == 0:
            return
        
        ring = self.rings[r][c]
        if ring is None:
            self._ensure_ring(r, c, "#606060", "#ffffff", "#000000", 280, RING_OUTER_ARC_WIDTH, RING_INNER_ARC_WIDTH)
            ring = self.rings[r][c]
        
        if ring:
            ring.set_center_text(text)
    
    def set_ring_all(self, r: int, c: int, outer: int, inner: int,
                    fg_out: str, fg_in: str, bg: str, 
                    size_px: int, w_out: int, w_in: int) -> None:
        self._ensure_ring(r, c, fg_out, fg_in, bg, size_px, w_out, w_in)
        self.set_ring_value(r, c, outer, inner)
    
    def set_ring_extra_arcs(self, r: int, c: int, val1: int, val2: int) -> None:
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            return
        
        if r == 0 and c == 0:
            return
        
        ring = self.rings[r][c]
        if ring is None:
            self._ensure_ring(r, c, "#606060", "#ffffff", "#000000", 280, RING_OUTER_ARC_WIDTH, RING_INNER_ARC_WIDTH)
            ring = self.rings[r][c]
        
        if ring:
            ring.set_extra_arcs(val1, val2)
    
    @staticmethod
    def _map_anchor(align: Optional[str]) -> str:
        if not align:
            return "w"
        
        a = align.strip().lower()
        if a in ("l", "left"):
            return "w"
        if a in ("c", "center", "centre", "mid", "middle"):
            return "center"
        if a in ("r", "right"):
            return "e"
        return "w"
    
    def set_cell(self, r: int, c: int, text: Optional[str] = None,
                fg: Optional[str] = None, bg: Optional[str] = None,
                align: Optional[str] = None) -> None:
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            return
        
        # Don't modify MENU button
        if r == 0 and c == 0:
            return
        
        if text is not None and text != "":
            ring = self.rings[r][c]
            if ring is not None:
                holder = self.ring_holders[r][c]
                if holder is not None:
                    holder.place_forget()
                    holder.destroy()
                self.rings[r][c] = None
                self.ring_holders[r][c] = None
            
            bar_holder = self.bar_holders[r][c]
            if bar_holder is not None:
                bar_holder.pack_forget()
                bar_holder.destroy()
                self.bar_holders[r][c] = None
                self.bars[r][c] = None
            
            lbl = self.labels[r][c]
            if not lbl.winfo_manager():
                lbl.pack(fill="both", expand=True)
        
        lbl = self.labels[r][c]
        
        if text is not None and text != self.last_text[r][c]:
            self.vars[r][c].set(text)
            self.last_text[r][c] = text
        
        if fg and fg != self.last_fg[r][c]:
            if validate_color(fg):
                try:
                    lbl.configure(fg=fg)
                    self.last_fg[r][c] = fg
                except tk.TclError:
                    pass
        
        if bg and bg != self.last_bg[r][c]:
            if validate_color(bg):
                try:
                    lbl.configure(bg=bg)
                    self.cell_frames[r][c].configure(bg=bg)
                    self.last_bg[r][c] = bg
                except tk.TclError:
                    pass
        
        if align is not None:
            anchor = self._map_anchor(align)
            if anchor != self.last_anchor[r][c]:
                try:
                    lbl.configure(anchor=anchor)
                    self.last_anchor[r][c] = anchor
                except tk.TclError:
                    pass
    
    def go_home(self):
        """MENU button pressed - return to control panel"""
        print("MENU clicked - returning to control panel")
        self.app.show_screen('control')
    
    def check_pd_status(self):
        """Poll Pure Data status and update UI accordingly"""
        # Cancel any existing scheduled callback first
        if self.status_polling_id:
            self.after_cancel(self.status_polling_id)
            self.status_polling_id = None
        
        try:
            status, message = self.app.pd_manager.get_status()
            
            if status == PDStatus.INITIALIZING_MIDI:
                # Still initializing MIDI
                self.show_loading_state(message)
                self.status_polling_id = self.after(200, self.check_pd_status)  # Check again in 200ms
                
            elif status == PDStatus.STARTING:
                # Pure Data is starting
                self.show_loading_state(message)
                self.status_polling_id = self.after(200, self.check_pd_status)  # Check again in 200ms
                
            elif status == PDStatus.RUNNING:
                # Pure Data ready!
                self.show_normal_gui()
                # Stop polling (don't schedule another check)
                
            elif status == PDStatus.ERROR:
                # Error occurred
                self.show_error_state(message)
                # Stop polling
                
            elif status == PDStatus.STOPPED:
                # Shouldn't happen, but handle it
                self.show_loading_state("Waiting for Pure Data...")
                self.status_polling_id = self.after(200, self.check_pd_status)
        except Exception as e:
            print(f"Error checking PD status: {e}")
            # Keep trying
            self.status_polling_id = self.after(500, self.check_pd_status)
    
    def show_loading_state(self, message):
        """Show loading overlay with status message"""
        if not self.loading_visible:
            # Hide normal UI
            self.container.pack_forget()
            # Show loading overlay
            self.loading_overlay.pack(fill="both", expand=True)
            self.loading_visible = True
        
        # Update message
        self.loading_message.config(text=message)
    
    def show_normal_gui(self):
        """Hide loading overlay, show normal patch display"""
        if self.loading_visible:
            # Hide loading overlay
            self.loading_overlay.pack_forget()
            # Show normal UI
            self.container.pack(fill="both", expand=True)
            self.loading_visible = False
            print("✓ Patch display ready - PD running!")
    
    def show_error_state(self, error_message):
        """Show error in loading overlay"""
        if not self.loading_visible:
            self.container.pack_forget()
            self.loading_overlay.pack(fill="both", expand=True)
            self.loading_visible = True
        
        self.loading_title.config(text="Connection Error", fg="#ff4444")
        self.loading_message.config(text=error_message)
    
    def on_show(self):
        """
        Called when this screen becomes visible
        
        CRITICAL: This restarts status polling every time, ensuring:
        - First load: Shows loading screen
        - Second load (via confirmation): Shows loading screen again
        - Any subsequent load: Shows loading screen
        """
        print("Patch display shown - starting/restarting status polling...")
        self.check_pd_status()  # This cancels existing polling and starts fresh
    
    def cleanup(self):
        """
        Clean up resources before destroying this screen
        CRITICAL: Must be called before creating a new patch screen
        """
        print("Cleaning up patch display...")
        
        # Stop status polling
        if self.status_polling_id:
            self.after_cancel(self.status_polling_id)
            self.status_polling_id = None
        
        # Stop UDP listener thread
        print("Stopping UDP listener...")
        self.udp_stop_flag = True  # Signal thread to stop
        
        # Close socket to unblock recvfrom
        if self.udp_socket:
            try:
                self.udp_socket.close()
                print("UDP socket closed")
            except:
                pass
        
        # Wait briefly for thread to exit
        if self.udp_thread and self.udp_thread.is_alive():
            self.udp_thread.join(timeout=2.0)
            if self.udp_thread.is_alive():
                print("Warning: UDP thread did not stop cleanly")
            else:
                print("UDP thread stopped cleanly")
        
        print("Patch display cleanup complete")
    
    def update_status(self, message, error=False):
        """Update status (for compatibility)"""
        print(f"Status: {message}")