#!/usr/bin/env python3
"""
UDP Display Server - Improved Version
Displays text, ring widgets, and horizontal bars in a grid layout via UDP commands.
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

os.environ["TK_SILENCE_DEPRECATION"] = "1"

import tkinter as tk
from tkinter import font as tkfont

# ---------------- Configuration ----------------
# Protocol version
PROTOCOL_VERSION = "1.0"

# Network settings
HOST = "0.0.0.0"
PORT = 9001
SOCKET_TIMEOUT_SEC = 1.0
SOCKET_BUFFER_SIZE = 1 << 20  # 1MB

# Grid layout (11 rows)
DEFAULT_ROWS = 11
COLS_PER_ROW = [4, 4, 4, 8, 4, 4, 4, 8, 4, 8, 8]

# 0-based indices of rows that use BIG font
BIG_FONT_ROWS = {1, 5, 9}

# Rows that contain bar widgets - DISABLED (set to 0px height)
BAR_ROWS = {3, 7}  # Rows 4 and 8 (kept for message compatibility, but 0px height)

# Font configuration
SMALL_FONT_PT = 27
BIG_FONT_PT = 35
HEAD_ROW_BONUS_PT = 0
FONT_FAMILY_PRIMARY = "DejaVu Sans"
FONT_FAMILY_FALLBACK = "TkDefaultFont"

# Row heights (pixels) - 11 rows total
# Rows 4, 5, 8, 9 are set to 0px (invisible but keep message order)
ROW_HEIGHTS = [60, 260, 30, 0, 0, 260, 30, 0, 0, 30, 30]

# Ring widget configuration
RING_START_ANGLE = 210  # 7 o'clock position
RING_END_ANGLE = 330    # 4 o'clock position
RING_SWEEP_MAX = 240    # Total sweep angle
RING_CENTER_FONT_SIZE = 35
RING_EXTRA_ARC_WIDTH = 4  # Width of the two extra thin arcs
RING_EXTRA_ARC_GAP = 6  # Gap between arcs (same for all)
RING_EXTRA_DOT_SIZE = 8  # Diameter of the dot at arc peak
RING_OUTER_ARC_WIDTH = 10  # Reduced from 15
RING_INNER_ARC_WIDTH = 30  # Reduced from 40

# Bar widget configuration
BAR_BORDER_COLOR = "#303030"  # Darker grey
BAR_FILL_COLOR = "#606060"    # Light grey (matches outer circle)
BAR_BG_COLOR = "#000000"
BAR_GAP_PIXELS = 2  # Gap between border and fill
BAR_BORDER_WIDTH = 2
BARS_PER_CELL = 1  # One bar per cell

# Performance tuning
POLL_INTERVAL_MS = 10
MAX_APPLIES_PER_TICK = 512
HEARTBEAT_TIMEOUT_SEC = 30.0

# Logging configuration
LOG_LEVEL = logging.WARNING
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ---------------- Logging Setup ----------------
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


# ---------------- Utility Functions ----------------
def is_linux() -> bool:
    """Check if running on Linux."""
    return sys.platform.startswith("linux")


def validate_color(color: str) -> bool:
    """Validate color string format."""
    if not color:
        return False
    if color.startswith('#'):
        return len(color) in (4, 7, 9) and all(c in '0123456789abcdefABCDEF' for c in color[1:])
    return True  # Named colors


def lighten_color(hex_color: str, factor: float) -> str:
    """
    Lighten a hex color by a factor (0.0 to 1.0).
    Factor of 0.5 means 50% lighter towards white.
    """
    if not hex_color.startswith('#'):
        return hex_color
    
    # Remove '#' and parse RGB
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Lighten towards white (255, 255, 255)
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        
        # Clamp values
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        
        return f'#{r:02x}{g:02x}{b:02x}'
    except (ValueError, IndexError):
        return hex_color


@dataclass
class PerformanceMetrics:
    """Track performance metrics."""
    messages_received: int = 0
    messages_processed: int = 0
    messages_dropped: int = 0
    last_message_time: float = 0.0
    
    def update_received(self):
        self.messages_received += 1
        self.last_message_time = time.time()
    
    def update_processed(self):
        self.messages_processed += 1
    
    def update_dropped(self):
        self.messages_dropped += 1
    
    def is_alive(self, timeout: float = HEARTBEAT_TIMEOUT_SEC) -> bool:
        if self.last_message_time == 0.0:
            return True
        return (time.time() - self.last_message_time) < timeout


# ---------------- Horizontal Bar Widget ----------------
class HorizontalBar(tk.Canvas):
    """
    A horizontal bar that fills from left to right based on value (1-127).
    Has a border with a gap between the border and the fill.
    """
    
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
        self._value = 0  # 0-127
        
        self._border_rect = None
        self._fill_rect = None
        
        self.bind("<Configure>", lambda e: self._redraw())
        self._redraw()
    
    @staticmethod
    def _clip_value(v: Any) -> int:
        """Clip value to valid range [0, 127]."""
        try:
            v = int(v)
        except (ValueError, TypeError):
            logger.warning(f"Invalid bar value: {v}, defaulting to 0")
            v = 0
        return max(0, min(127, v))
    
    def set_value(self, value: int) -> None:
        """Set bar value (0-127)."""
        self._value = self._clip_value(value)
        self._update_fill()
    
    def _redraw(self) -> None:
        """Redraw the bar."""
        self.delete("all")
        
        w = self.winfo_width()
        h = self.winfo_height()
        
        if w < 4 or h < 4:
            return
        
        # Draw border
        self._border_rect = self.create_rectangle(
            0, 0, w, h,
            outline=self._border_color,
            width=self._border_width,
            fill=self._bg_color
        )
        
        # Draw fill (will be updated by _update_fill)
        gap = self._gap + self._border_width
        self._fill_rect = self.create_rectangle(
            gap, gap, gap, h - gap,
            outline="",
            fill=self._fill_color
        )
        
        self._update_fill()
    
    def _update_fill(self) -> None:
        """Update the fill rectangle based on current value."""
        if self._fill_rect is None:
            return
        
        w = self.winfo_width()
        h = self.winfo_height()
        
        if w < 4 or h < 4:
            return
        
        gap = self._gap + self._border_width
        
        # Calculate fill width based on value
        available_width = w - (2 * gap)
        fill_width = (available_width * self._value) / 127.0
        
        # Update fill rectangle coordinates
        x1 = gap
        y1 = gap
        x2 = gap + fill_width
        y2 = h - gap
        
        try:
            self.coords(self._fill_rect, x1, y1, x2, y2)
        except tk.TclError as e:
            logger.error(f"Failed to update bar fill: {e}")


# ---------------- Dual Ring Widget ----------------
class DualRing(tk.Frame):
    """
    Two concentric arcs (outer thin, inner thick) plus two additional thin outer arcs.
    All arcs start at 7 o'clock (210°) sweeping CLOCKWISE up to ~4 o'clock (330°).
    The CENTER shows the inner arc's current value (1..127) or an override text if set.
    """
    
    def __init__(self, master, size: int = 200, fg_outer: str = "#606060", 
                 fg_inner: str = "#ffffff", bg: str = "#000000", 
                 w_outer: int = None, w_inner: int = None, 
                 text_color: str = "#ffffff", **kw):
        super().__init__(master, bg=bg, **kw)
        
        self._display_size = int(size)  # Canvas display size (larger)
        self._arc_size = 180  # Actual arc drawing size (smaller, fixed)
        self._bg = bg
        self._fg_outer = fg_outer
        self._fg_inner = fg_inner
        self._w_outer = int(w_outer) if w_outer is not None else RING_OUTER_ARC_WIDTH
        self._w_inner = int(w_inner) if w_inner is not None else RING_INNER_ARC_WIDTH
        self._text_color = text_color
        self._outer_val = 0
        self._inner_val = 0
        self._extra_arc1_val = 0  # NEW: First extra arc value
        self._extra_arc2_val = 0  # NEW: Second extra arc value
        self._center_override: Optional[str] = None
        
        # Create canvas with anti-aliasing hint
        self.canvas = tk.Canvas(
            self, width=self._display_size, height=self._display_size,
            bg=bg, highlightthickness=0, bd=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        self._outer_arc_id: Optional[int] = None
        self._inner_arc_id: Optional[int] = None
        self._extra_arc1_id: Optional[int] = None  # NEW
        self._extra_arc2_id: Optional[int] = None  # NEW
        self._extra_dot1_id: Optional[int] = None  # NEW: Dot for arc 1
        self._extra_dot2_id: Optional[int] = None  # NEW: Dot for arc 2
        self._label_id: Optional[int] = None
        
        self.canvas.bind("<Configure>", lambda e: self._redraw())
        self._redraw()
    
    @staticmethod
    def _clip_value(v: Any) -> int:
        """Clip value to valid range [0, 127]."""
        try:
            v = int(v)
        except (ValueError, TypeError):
            logger.warning(f"Invalid ring value: {v}, defaulting to 0")
            v = 0
        return max(0, min(127, v))
    
    def set_values(self, outer_v: int, inner_v: int) -> None:
        """Set both outer and inner ring values."""
        self._outer_val = self._clip_value(outer_v)
        self._inner_val = self._clip_value(inner_v)
        self._update_extents()
        self._update_label()
    
    def set_outer(self, v: int) -> None:
        """Set outer ring value."""
        self._outer_val = self._clip_value(v)
        self._update_extents()
    
    def set_inner(self, v: int) -> None:
        """Set inner ring value."""
        self._inner_val = self._clip_value(v)
        self._update_extents()
        self._update_label()
    
    def set_extra_arcs(self, val1: int, val2: int) -> None:
        """Set the two extra outer arc values."""
        # val1 controls extra_arc1 (closer to grey arc)
        # val2 controls extra_arc2 (outermost)
        self._extra_arc1_val = self._clip_value(val1)
        self._extra_arc2_val = self._clip_value(val2)
        self._update_extents()
    
    def set_center_text(self, text: Optional[str]) -> None:
        """Override the center text display."""
        self._center_override = text if text else None
        self._update_label()
    
    def restyle(self, fg_outer: Optional[str] = None, fg_inner: Optional[str] = None,
                bg: Optional[str] = None, w_outer: Optional[int] = None,
                w_inner: Optional[int] = None, text_color: Optional[str] = None) -> None:
        """Update ring styling."""
        if fg_outer is not None and validate_color(fg_outer):
            self._fg_outer = fg_outer
        if fg_inner is not None and validate_color(fg_inner):
            self._fg_inner = fg_inner
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
            except tk.TclError as e:
                logger.error(f"Failed to set background: {e}")
        self._redraw()
    
    def resize(self, size_px: int) -> None:
        """Resize the ring widget display (not the arcs themselves)."""
        self._display_size = int(size_px)
        self.canvas.config(width=self._display_size, height=self._display_size)
        self._redraw()
    
    def _bbox_for(self, pad: int) -> Tuple[int, int, int, int]:
        """Calculate bounding box for arc with padding.
        Uses fixed arc_size, not display_size.
        Smaller pad = larger circle (further from center)
        Larger pad = smaller circle (closer to center)
        """
        # Use arc_size for calculations, but center in display canvas
        w = max(2, self.canvas.winfo_width())
        h = max(2, self.canvas.winfo_height())
        cx, cy = w // 2, h // 2
        
        # Calculate radius based on fixed arc size
        r = self._arc_size // 2 - pad
        return (cx - r, cy - r, cx + r, cy + r)
    
    def _redraw(self) -> None:
        """Redraw all ring elements."""
        self.canvas.delete("all")
        
        # Calculate padding - SMALLER pad = LARGER circle (further from center)
        # Start from innermost (largest pad value)
        
        # Inner arc is the thickest and innermost (largest pad)
        inner_pad = max(self._w_inner // 2 + 2, 4)
        
        # Outer arc (grey, thinner) - LARGER circle, so SMALLER pad
        outer_pad = inner_pad - self._w_inner // 2 - self._w_outer // 2 - RING_EXTRA_ARC_GAP
        
        # Extra arcs go OUTSIDE (even LARGER circles, even SMALLER pad values)
        gap = RING_EXTRA_ARC_GAP
        extra_arc_width = RING_EXTRA_ARC_WIDTH
        
        # Extra arc 2 (closer to grey) - just outside grey arc
        extra_arc2_pad = outer_pad - self._w_outer // 2 - gap - extra_arc_width // 2
        
        # Extra arc 1 (outermost) - furthest from center, smallest pad
        extra_arc1_pad = extra_arc2_pad - gap - extra_arc_width
        
        outer_bbox = self._bbox_for(outer_pad)
        inner_bbox = self._bbox_for(inner_pad)
        extra_arc1_bbox = self._bbox_for(extra_arc1_pad)
        extra_arc2_bbox = self._bbox_for(extra_arc2_pad)
        
        # Calculate lighter colors based on inner arc color
        light_color1 = lighten_color(self._fg_inner, 0.3)  # 30% lighter
        light_color2 = lighten_color(self._fg_inner, 0.5)  # 50% lighter
        
        # Background tracks (pure black)
        self.canvas.create_oval(*inner_bbox, outline="#000", width=self._w_inner)
        self.canvas.create_oval(*outer_bbox, outline="#000", width=self._w_outer)
        self.canvas.create_oval(*extra_arc1_bbox, outline="#000", width=extra_arc_width)
        self.canvas.create_oval(*extra_arc2_bbox, outline="#000", width=extra_arc_width)
        
        # Value arcs: start at 210° (7 o'clock)
        # Draw from innermost to outermost
        
        # Inner arc (colored, thick) - innermost
        self._inner_arc_id = self.canvas.create_arc(
            *inner_bbox, start=RING_START_ANGLE, extent=0, style="arc",
            outline=self._fg_inner, width=self._w_inner
        )
        
        # Outer arc (grey, thinner) - outside inner
        self._outer_arc_id = self.canvas.create_arc(
            *outer_bbox, start=RING_START_ANGLE, extent=0, style="arc",
            outline=self._fg_outer, width=self._w_outer
        )
        
        # Extra arc 2 (light colored, outside grey arc - closer)
        self._extra_arc2_id = self.canvas.create_arc(
            *extra_arc2_bbox, start=RING_START_ANGLE, extent=0, style="arc",
            outline=light_color2, width=extra_arc_width
        )
        
        # Extra arc 1 (lighter colored, outermost)
        self._extra_arc1_id = self.canvas.create_arc(
            *extra_arc1_bbox, start=RING_START_ANGLE, extent=0, style="arc",
            outline=light_color1, width=extra_arc_width
        )
        
        # Create dots for extra arcs (initially at 0 position)
        dot_radius = RING_EXTRA_DOT_SIZE // 2
        self._extra_dot1_id = self.canvas.create_oval(
            0, 0, RING_EXTRA_DOT_SIZE, RING_EXTRA_DOT_SIZE,
            fill=light_color1, outline=""
        )
        self._extra_dot2_id = self.canvas.create_oval(
            0, 0, RING_EXTRA_DOT_SIZE, RING_EXTRA_DOT_SIZE,
            fill=light_color2, outline=""
        )
        
        # Center value label
        cx, cy = self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2
        font = (FONT_FAMILY_PRIMARY, RING_CENTER_FONT_SIZE, "bold")
        display_val = max(1, int(self._inner_val))
        self._label_id = self.canvas.create_text(
            cx, cy, text=str(display_val), fill=self._text_color, font=font
        )
        
        self._update_extents()
    
    def _update_extents(self) -> None:
        """Update arc extents based on current values."""
        import math
        
        ext_outer = -RING_SWEEP_MAX * (self._outer_val / 127.0)  # negative = clockwise
        ext_inner = -RING_SWEEP_MAX * (self._inner_val / 127.0)
        ext_extra1 = -RING_SWEEP_MAX * (self._extra_arc1_val / 127.0)
        ext_extra2 = -RING_SWEEP_MAX * (self._extra_arc2_val / 127.0)
        
        if self._outer_arc_id is not None:
            try:
                self.canvas.itemconfig(self._outer_arc_id, extent=ext_outer, outline=self._fg_outer, width=self._w_outer)
            except tk.TclError as e:
                logger.error(f"Failed to update outer arc: {e}")
        
        if self._inner_arc_id is not None:
            try:
                self.canvas.itemconfig(self._inner_arc_id, extent=ext_inner, outline=self._fg_inner, width=self._w_inner)
            except tk.TclError as e:
                logger.error(f"Failed to update inner arc: {e}")
        
        # Update extra arcs with lighter colors
        light_color1 = lighten_color(self._fg_inner, 0.3)
        light_color2 = lighten_color(self._fg_inner, 0.5)
        
        if self._extra_arc1_id is not None:
            try:
                self.canvas.itemconfig(self._extra_arc1_id, extent=ext_extra1, outline=light_color1, width=RING_EXTRA_ARC_WIDTH)
            except tk.TclError as e:
                logger.error(f"Failed to update extra arc 1: {e}")
        
        if self._extra_arc2_id is not None:
            try:
                self.canvas.itemconfig(self._extra_arc2_id, extent=ext_extra2, outline=light_color2, width=RING_EXTRA_ARC_WIDTH)
            except tk.TclError as e:
                logger.error(f"Failed to update extra arc 2: {e}")
        
        # Update dot positions at the peak of each arc
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        cx, cy = w // 2, h // 2
        
        # Calculate padding same way as in _redraw
        # SMALLER pad = LARGER circle (further from center)
        # Use fixed arc_size for radius calculations
        inner_pad = max(self._w_inner // 2 + 2, 4)
        outer_pad = inner_pad - self._w_inner // 2 - self._w_outer // 2 - RING_EXTRA_ARC_GAP
        gap = RING_EXTRA_ARC_GAP
        extra_arc_width = RING_EXTRA_ARC_WIDTH
        extra_arc2_pad = outer_pad - self._w_outer // 2 - gap - extra_arc_width // 2
        extra_arc1_pad = extra_arc2_pad - gap - extra_arc_width
        
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        cx, cy = w // 2, h // 2
        
        radius1 = self._arc_size // 2 - extra_arc1_pad
        radius2 = self._arc_size // 2 - extra_arc2_pad
        
        # Calculate angle at peak (start_angle + extent)
        # Canvas coordinates: 0° = 3 o'clock (east), 90° = 6 o'clock (south)
        # Our arcs go clockwise from 210° (7 o'clock)
        peak_angle1_deg = RING_START_ANGLE + ext_extra1
        peak_angle2_deg = RING_START_ANGLE + ext_extra2
        
        # Convert to standard math radians (counter-clockwise from east)
        # Canvas Y-axis is inverted, so we negate the sine component
        peak_angle1_rad = math.radians(-peak_angle1_deg)
        peak_angle2_rad = math.radians(-peak_angle2_deg)
        
        # Calculate dot positions
        dot_radius = RING_EXTRA_DOT_SIZE // 2
        dot1_x = cx + radius1 * math.cos(peak_angle1_rad)
        dot1_y = cy + radius1 * math.sin(peak_angle1_rad)
        dot2_x = cx + radius2 * math.cos(peak_angle2_rad)
        dot2_y = cy + radius2 * math.sin(peak_angle2_rad)
        
        # Update dot positions and colors
        if self._extra_dot1_id is not None:
            try:
                self.canvas.coords(
                    self._extra_dot1_id,
                    dot1_x - dot_radius, dot1_y - dot_radius,
                    dot1_x + dot_radius, dot1_y + dot_radius
                )
                self.canvas.itemconfig(self._extra_dot1_id, fill=light_color1)
            except tk.TclError as e:
                logger.error(f"Failed to update dot 1: {e}")
        
        if self._extra_dot2_id is not None:
            try:
                self.canvas.coords(
                    self._extra_dot2_id,
                    dot2_x - dot_radius, dot2_y - dot_radius,
                    dot2_x + dot_radius, dot2_y + dot_radius
                )
                self.canvas.itemconfig(self._extra_dot2_id, fill=light_color2)
            except tk.TclError as e:
                logger.error(f"Failed to update dot 2: {e}")
    
    def _update_label(self) -> None:
        """Update center label text."""
        if self._label_id is None:
            return
        
        cx, cy = self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2
        font = (FONT_FAMILY_PRIMARY, RING_CENTER_FONT_SIZE, "bold")
        
        # Prefer override text if present
        if self._center_override is not None:
            display_text = str(self._center_override)
        else:
            display_text = str(max(1, int(self._inner_val)))
        
        try:
            self.canvas.itemconfig(self._label_id, text=display_text, fill=self._text_color, font=font)
            self.canvas.coords(self._label_id, cx, cy)
        except tk.TclError as e:
            logger.error(f"Failed to update label: {e}")


# ---------------- UDP Listener ----------------
def start_udp_listener(out_queue: Queue, metrics: PerformanceMetrics) -> None:
    """
    Start UDP listener thread.
    
    Enqueued message formats:
      ("SET", r, c, fg, bg, align, text)
      ("BG_CELL", r, c, bg)
      ("ALIGN_CELL", r, c, align)
      ("RING_STYLE", r, c, fg_out, fg_in, bg, size_px, w_out, w_in)
      ("RING_VALUE", r, c, outer, inner, text)
      ("RING_SET", r, c, outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in)
      ("ARC_VALUE", r, c, val1, val2)
      ("BAR_VALUE", r, c, value)
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE)
    except OSError as e:
        logger.warning(f"Failed to set socket buffer size: {e}")
    
    try:
        sock.bind((HOST, PORT))
        sock.settimeout(SOCKET_TIMEOUT_SEC)
        logger.info(f"UDP listener bound to {HOST}:{PORT}")
    except OSError as e:
        logger.error(f"Failed to bind socket: {e}")
        return
    
    def parse_message(line: str) -> Optional[Tuple]:
        """Parse incoming UDP message."""
        if not line:
            return None
        
        if line.endswith(";"):
            line = line[:-1].rstrip()
        
        parts = line.split()
        if not parts:
            return None
        
        head = parts[0].upper()
        
        try:
            # ARC c r val1 val2
            if head == "ARC" and len(parts) >= 5:
                c, r = int(parts[1]), int(parts[2])
                val1, val2 = int(parts[3]), int(parts[4])
                return ("ARC_VALUE", r, c, val1, val2)
            
            # BAR r c value
            if head == "BAR" and len(parts) >= 4:
                r, c = int(parts[1]), int(parts[2])
                value = int(parts[3])
                return ("BAR_VALUE", r, c, value)
            
            # ALIGN r c align
            if head == "ALIGN" and len(parts) >= 4:
                r, c, align = int(parts[1]), int(parts[2]), parts[3]
                return ("ALIGN_CELL", r, c, align)
            
            # BG r c bg
            if head == "BG" and len(parts) >= 4:
                r, c, bg = int(parts[1]), int(parts[2]), parts[3]
                return ("BG_CELL", r, c, bg)
            
            # RING c r fg_out fg_in bg size w_out w_in
            if head == "RING" and len(parts) >= 9:
                c, r = int(parts[1]), int(parts[2])
                fg_out, fg_in, bg = parts[3], parts[4], parts[5]
                size_px, w_out, w_in = int(parts[6]), int(parts[7]), int(parts[8])
                return ("RING_STYLE", r, c, fg_out, fg_in, bg, size_px, w_out, w_in)
            
            # RINGVAL c r outer inner [text...]
            if head == "RINGVAL" and len(parts) >= 5:
                c, r = int(parts[1]), int(parts[2])
                outer, inner = int(parts[3]), int(parts[4])
                text = " ".join(parts[5:]).rstrip(";") if len(parts) > 5 else None
                return ("RING_VALUE", r, c, outer, inner, text)
            
            # RINGSET c r outer inner fg_out fg_in bg size w_out w_in
            if head == "RINGSET" and len(parts) >= 11:
                c, r = int(parts[1]), int(parts[2])
                outer, inner = int(parts[3]), int(parts[4])
                fg_out, fg_in, bg = parts[5], parts[6], parts[7]
                size_px, w_out, w_in = int(parts[8]), int(parts[9]), int(parts[10])
                return ("RING_SET", r, c, outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in)
            
            # SET c r fg bg [align] text...
            if len(parts) >= 5:
                c, r = int(parts[0]), int(parts[1])
                
                if len(parts) >= 6:
                    fg, bg, align = parts[2], parts[3], parts[4]
                    text = " ".join(parts[5:]).rstrip(";")
                else:
                    fg, bg, align = parts[2], parts[3], None
                    text = " ".join(parts[4:]).rstrip(";")
                
                return ("SET", r, c, fg, bg, align, text)
        
        except (ValueError, IndexError) as e:
            logger.debug(f"Failed to parse message '{line}': {e}")
            return None
        
        return None
    
    def loop():
        """Main listener loop."""
        while True:
            try:
                data, addr = sock.recvfrom(16384)
                metrics.update_received()
                
                line = data.decode("utf-8", errors="replace").strip()
                msg = parse_message(line)
                
                if msg:
                    out_queue.put(msg)
                    metrics.update_processed()
                else:
                    metrics.update_dropped()
            
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"UDP listener error: {e}")
                continue
    
    threading.Thread(target=loop, daemon=True, name="UDPListener").start()


# ---------------- UI Class ----------------
class Display:
    """Main display UI controller."""
    
    def __init__(self, root: tk.Tk, rows: int = DEFAULT_ROWS, 
                 cols_per_row: Optional[List[int]] = None):
        self.root = root
        self.rows = rows
        self.cols_per_row = list(cols_per_row or COLS_PER_ROW)
        
        # Initialize fonts with fallback
        self._init_fonts()
        
        # UI components
        self.vars: List[List[tk.StringVar]] = []
        self.labels: List[List[tk.Label]] = []
        self.cell_frames: List[List[tk.Frame]] = []
        self.row_frames: List[tk.Frame] = []
        
        # Build UI
        self._build_ui()
        
        # State caches
        self.last_text: List[List[Optional[str]]] = []
        self.last_fg: List[List[Optional[str]]] = []
        self.last_bg: List[List[Optional[str]]] = []
        self.last_anchor: List[List[Optional[str]]] = []
        self._init_caches()
        
        # Ring widget storage
        self.ring_holders: List[List[Optional[tk.Frame]]] = [
            [None] * self.cols_per_row[r] for r in range(self.rows)
        ]
        self.rings: List[List[Optional[DualRing]]] = [
            [None] * self.cols_per_row[r] for r in range(self.rows)
        ]
        
        # Bar widget storage (1 bar per cell in bar rows)
        self.bar_holders: List[List[Optional[tk.Frame]]] = [
            [None] * self.cols_per_row[r] for r in range(self.rows)
        ]
        self.bars: List[List[Optional[HorizontalBar]]] = [
            [None] * self.cols_per_row[r] for r in range(self.rows)
        ]
    
    def _init_fonts(self) -> None:
        """Initialize fonts with fallback handling."""
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
            logger.info(f"Using font family: {FONT_FAMILY_PRIMARY}")
        except Exception as e:
            logger.warning(f"Failed to load {FONT_FAMILY_PRIMARY}, using fallback: {e}")
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
    
    def _init_caches(self) -> None:
        """Initialize state caches."""
        self.last_text = [[None] * self.cols_per_row[r] for r in range(self.rows)]
        self.last_fg = [[None] * self.cols_per_row[r] for r in range(self.rows)]
        self.last_bg = [[None] * self.cols_per_row[r] for r in range(self.rows)]
        self.last_anchor = [[None] * self.cols_per_row[r] for r in range(self.rows)]
    
    def _build_ui(self) -> None:
        """Build the main UI layout."""
        if is_linux():
            self.root.geometry("1280x720+0+0")
        else:
            self.root.geometry("1280x720+100+100")
        
        self.root.configure(bg="black")
        
        self.container = tk.Frame(self.root, bg="black", bd=0, highlightthickness=0)
        self.container.pack(expand=True, fill="both")
        
        self.container.columnconfigure(0, weight=1, uniform="outer_col")
        
        self.vars.clear()
        self.labels.clear()
        self.cell_frames.clear()
        self.row_frames.clear()
        
        for r in range(self.rows):
            # Fix row to pixel height
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
                
                # Select font for this row
                if r == 0:
                    fnt = self.head_font
                elif r in BIG_FONT_ROWS:
                    fnt = self.big_font
                else:
                    fnt = self.small_font
                
                lbl = tk.Label(
                    cell, textvariable=var,
                    bg="black", fg="white",
                    anchor="w", padx=0, pady=0, bd=0, highlightthickness=0
                )
                lbl.configure(font=fnt)
                lbl.pack(fill="both", expand=True)
                row_labels.append(lbl)
            
            self.vars.append(row_vars)
            self.labels.append(row_labels)
            self.cell_frames.append(row_cells)
        
        # Keyboard controls
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(300, lambda: self.root.attributes("-topmost", False))
    
    # ---- Bar Widget Methods ----
    
    def _ensure_bars(self, r: int, c: int) -> None:
        """Ensure bar widget exists for a cell."""
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            logger.warning(f"Invalid cell coordinates: ({r}, {c})")
            return
        
        if r not in BAR_ROWS:
            logger.warning(f"Row {r} is not a bar row")
            return
        
        # Hide label if present
        lbl = self.labels[r][c]
        if lbl.winfo_manager():
            lbl.forget()
        
        holder = self.bar_holders[r][c]
        if holder is None:
            holder = tk.Frame(self.cell_frames[r][c], bg="black", bd=0, highlightthickness=0)
            holder.pack(fill="both", expand=True, padx=2, pady=2)
            self.bar_holders[r][c] = holder
            
            # Create one bar that fills the cell
            bar = HorizontalBar(holder, width=200, height=30)
            bar.pack(fill="both", expand=True)
            self.bars[r][c] = bar
    
    def set_bar_value(self, r: int, c: int, value: int) -> None:
        """Set bar value."""
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            return
        
        if r not in BAR_ROWS:
            logger.warning(f"Row {r} is not a bar row")
            return
        
        # Ensure bar exists
        self._ensure_bars(r, c)
        
        bar = self.bars[r][c]
        if bar:
            bar.set_value(value)
    
    # ---- Ring Widget Methods ----
    
    def _ensure_ring(self, r: int, c: int, fg_out: str, fg_in: str, 
                     bg: str, size_px: int, w_out: int, w_in: int) -> None:
        """Ensure ring widget exists with given parameters."""
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            logger.warning(f"Invalid cell coordinates: ({r}, {c})")
            return
        
        # Canvas display size is 260px, but arcs are drawn at 180px
        display_size = 260
        
        # Hide label if present
        lbl = self.labels[r][c]
        if lbl.winfo_manager():
            lbl.forget()
        
        holder = self.ring_holders[r][c]
        if holder is None:
            holder = tk.Frame(self.cell_frames[r][c], bg="black", bd=0, highlightthickness=0)
            # Place at fixed size in center of cell
            holder.place(relx=0.5, rely=0.5, anchor="center", width=display_size, height=display_size)
            self.ring_holders[r][c] = holder
        
        ring = self.rings[r][c]
        if ring is None:
            ring = DualRing(
                holder, size=display_size, fg_outer=fg_out, fg_inner=fg_in,
                bg=bg, w_outer=w_out, w_inner=w_in, text_color="#e3e3e3"
            )
            ring.pack(fill="both", expand=True)
            self.rings[r][c] = ring
        else:
            ring.restyle(fg_outer=fg_out, fg_inner=fg_in, bg=bg, 
                        w_outer=w_out, w_inner=w_in)
            # Ring size is fixed
    
    def set_ring_style(self, r: int, c: int, fg_out: str, fg_in: str, 
                      bg: str, size_px: int, w_out: int, w_in: int) -> None:
        """Set ring styling without changing values."""
        self._ensure_ring(r, c, fg_out, fg_in, bg, size_px, w_out, w_in)
    
    def set_ring_value(self, r: int, c: int, outer: int, inner: int) -> None:
        """Set ring values."""
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            return
        
        ring = self.rings[r][c]
        if ring is None:
            # Canvas is 260px, arcs drawn at 180px
            self._ensure_ring(r, c, "#606060", "#ffffff", "#000000", 260, RING_OUTER_ARC_WIDTH, RING_INNER_ARC_WIDTH)
            ring = self.rings[r][c]
        
        if ring:
            ring.set_values(outer, inner)
    
    def set_ring_text(self, r: int, c: int, text: Optional[str]) -> None:
        """Set ring center text override."""
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            return
        
        ring = self.rings[r][c]
        if ring is None:
            # Canvas is 260px, arcs drawn at 180px
            self._ensure_ring(r, c, "#606060", "#ffffff", "#000000", 260, RING_OUTER_ARC_WIDTH, RING_INNER_ARC_WIDTH)
            ring = self.rings[r][c]
        
        if ring:
            ring.set_center_text(text)
    
    def set_ring_all(self, r: int, c: int, outer: int, inner: int,
                    fg_out: str, fg_in: str, bg: str, 
                    size_px: int, w_out: int, w_in: int) -> None:
        """Set ring style and values together."""
        self._ensure_ring(r, c, fg_out, fg_in, bg, size_px, w_out, w_in)
        self.set_ring_value(r, c, outer, inner)
    
    def set_ring_extra_arcs(self, r: int, c: int, val1: int, val2: int) -> None:
        """Set the extra arc values."""
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            return
        
        ring = self.rings[r][c]
        if ring is None:
            # Canvas is 260px, arcs drawn at 180px
            self._ensure_ring(r, c, "#606060", "#ffffff", "#000000", 260, RING_OUTER_ARC_WIDTH, RING_INNER_ARC_WIDTH)
            ring = self.rings[r][c]
        
        if ring:
            ring.set_extra_arcs(val1, val2)
    
    # ---- Text Cell Methods ----
    
    @staticmethod
    def _map_anchor(align: Optional[str]) -> str:
        """Map alignment string to Tkinter anchor."""
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
        """Set text cell properties."""
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            logger.warning(f"Invalid cell coordinates: ({r}, {c})")
            return
        
        # If text arrives and ring exists, remove ring and show label
        if text is not None and text != "":
            ring = self.rings[r][c]
            if ring is not None:
                holder = self.ring_holders[r][c]
                if holder is not None:
                    holder.place_forget()
                    holder.destroy()
                self.rings[r][c] = None
                self.ring_holders[r][c] = None
            
            # If text arrives and bars exist, remove bars and show label
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
        
        # Update text
        if text is not None and text != self.last_text[r][c]:
            self.vars[r][c].set(text)
            self.last_text[r][c] = text
        
        # Update foreground color
        if fg and fg != self.last_fg[r][c]:
            if validate_color(fg):
                try:
                    lbl.configure(fg=fg)
                    self.last_fg[r][c] = fg
                except tk.TclError as e:
                    logger.error(f"Invalid foreground color '{fg}': {e}")
        
        # Update background color
        if bg and bg != self.last_bg[r][c]:
            if validate_color(bg):
                try:
                    lbl.configure(bg=bg)
                    self.cell_frames[r][c].configure(bg=bg)
                    self.last_bg[r][c] = bg
                except tk.TclError as e:
                    logger.error(f"Invalid background color '{bg}': {e}")
        
        # Update alignment
        if align is not None:
            anchor = self._map_anchor(align)
            if anchor != self.last_anchor[r][c]:
                try:
                    lbl.configure(anchor=anchor)
                    self.last_anchor[r][c] = anchor
                except tk.TclError as e:
                    logger.error(f"Failed to set anchor: {e}")


# ---------------- Main Application ----------------
def main():
    """Main application entry point."""
    root = tk.Tk()
    root.title("")
    root.overrideredirect(True)
    root.attributes("-fullscreen", True)
    root.config(cursor="none")
    root.configure(bg="black")
    
    # Initialize UI
    ui = Display(root, DEFAULT_ROWS, COLS_PER_ROW)
    
    # Start UDP listener
    q: Queue = Queue()
    metrics = PerformanceMetrics()
    start_udp_listener(q, metrics)
    
    # Pending updates (deduplicated)
    pending_latest: Dict[Tuple, Any] = {}
    
    # Statistics tracking
    last_stats_time = time.time()
    
    def drain_and_apply():
        """Process queued messages and apply to UI."""
        nonlocal last_stats_time
        
        # Drain queue into pending updates
        while True:
            try:
                msg = q.get_nowait()
            except Empty:
                break
            
            kind = msg[0]
            
            if kind == "BAR_VALUE":
                _, r, c, value = msg
                pending_latest[("BAR", r, c)] = value
            
            elif kind == "BG_CELL":
                _, r, c, bg = msg
                pending_latest[("BG", r, c)] = bg
            
            elif kind == "ALIGN_CELL":
                _, r, c, align = msg
                pending_latest[("ALIGN", r, c)] = align
            
            elif kind == "SET":
                _, r, c, fg, bg, align, text = msg
                pending_latest[("SET", r, c)] = (text, fg, bg, align)
            
            elif kind == "RING_STYLE":
                _, r, c, fg_out, fg_in, bg, size_px, w_out, w_in = msg
                pending_latest[("RING_STYLE", r, c)] = (fg_out, fg_in, bg, size_px, w_out, w_in)
            
            elif kind == "RING_VALUE":
                _, r, c, outer, inner, text = msg
                pending_latest[("RING_VALUE", r, c)] = (outer, inner, text)
            
            elif kind == "RING_SET":
                _, r, c, outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in = msg
                pending_latest[("RING_SET", r, c)] = (outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in)
            
            elif kind == "ARC_VALUE":
                _, r, c, val1, val2 = msg
                pending_latest[("ARC", r, c)] = (val1, val2)
        
        # Apply updates in priority order
        applied = 0
        
        # 1. Background changes
        for key, bg in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "BG":
                _, r, c = key
                ui.set_cell(r, c, None, None, bg, None)
                del pending_latest[key]
                applied += 1
        
        # 2. Alignment changes
        for key, align in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "ALIGN":
                _, r, c = key
                ui.set_cell(r, c, None, None, None, align)
                del pending_latest[key]
                applied += 1
        
        # 3. Bar values
        for key, value in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "BAR":
                _, r, c = key
                ui.set_bar_value(r, c, value)
                del pending_latest[key]
                applied += 1
        
        # 4. Ring set (style + value together)
        for key, payload in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "RING_SET":
                _, r, c = key
                outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in = payload
                ui.set_ring_all(r, c, outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in)
                del pending_latest[key]
                applied += 1
        
        # 5. Ring style
        for key, payload in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "RING_STYLE":
                _, r, c = key
                fg_out, fg_in, bg, size_px, w_out, w_in = payload
                ui.set_ring_style(r, c, fg_out, fg_in, bg, size_px, w_out, w_in)
                del pending_latest[key]
                applied += 1
        
        # 6. Ring value
        for key, payload in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "RING_VALUE":
                _, r, c = key
                outer, inner, text = payload
                ui.set_ring_value(r, c, outer, inner)
                if text is not None:
                    ui.set_ring_text(r, c, text)
                del pending_latest[key]
                applied += 1
        
        # 6b. Extra arc values
        for key, payload in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "ARC":
                _, r, c = key
                val1, val2 = payload
                ui.set_ring_extra_arcs(r, c, val1, val2)
                del pending_latest[key]
                applied += 1
        
        # 7. Text cell updates
        for key, payload in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK:
                break
            if key[0] == "SET":
                _, r, c = key
                text, fg, bg, align = payload
                ui.set_cell(r, c, text, fg, bg, align)
                del pending_latest[key]
                applied += 1
        
        # Force UI update if we applied many changes
        if applied > 100:
            root.update_idletasks()
        
        # Periodic statistics logging
        now = time.time()
        if now - last_stats_time > 10.0:
            logger.info(
                f"Stats - Received: {metrics.messages_received}, "
                f"Processed: {metrics.messages_processed}, "
                f"Dropped: {metrics.messages_dropped}, "
                f"Pending: {len(pending_latest)}, "
                f"Alive: {metrics.is_alive()}"
            )
            last_stats_time = now
        
        # Check heartbeat
        if not metrics.is_alive():
            logger.warning("No messages received in heartbeat timeout period")
        
        # Schedule next tick
        root.after(POLL_INTERVAL_MS, drain_and_apply)
    
    # Start processing loop
    root.after(POLL_INTERVAL_MS, drain_and_apply)
    
    logger.info("Display server started successfully")
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("Shutting down display server")
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}", exc_info=True)
    finally:
        logger.info("Display server stopped")


if __name__ == "__main__":
    main()