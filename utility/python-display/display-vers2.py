#!/usr/bin/env python3
import os, sys, socket, threading
from queue import Queue, Empty
os.environ["TK_SILENCE_DEPRECATION"] = "1"

import tkinter as tk
from tkinter import font as tkfont

# ---------------- Configuration ----------------
HOST, PORT = "0.0.0.0", 9001

# --- FIXED GRID (13 rows) ---
# 1:8s, 2:4B, 3:4s, 4:8s, 5:4s, 6:1s, 7:4B, 8:4s, 9:8s, 10:4s, 11:1s, 12:8B, 13:8B
DEFAULT_ROWS = 13
COLS_PER_ROW = [8, 4, 4, 4, 4, 1, 4, 4, 4, 4, 1, 8, 8]
BIG_FONT_ROWS = {1, 6, 11, 12}  # (0-based) rows 2,7,12,13 are BIG

# --- FONT SIZE CONTROL ---
SMALL_FONT_PT = 20
BIG_FONT_PT   = 28
HEAD_ROW_BONUS_PT = 0

POLL_INTERVAL_MS = 10
MAX_APPLIES_PER_TICK = 512

# --- PRE-CREATE BARS CONFIG ---
# User wants bars preloaded in row "3" (1-based). Convert to 0-based:
PRECREATE_BAR_ROW_IDX = 3 - 1    # -> 2
# Neutral placeholder look (can be overridden by BAR/BARSET commands from PD):
PRE_BAR_FG     = "#404040"       # frame + fill (placeholder)
PRE_BAR_BG     = "#101010"       # cell/bg behind the bar
PRE_BAR_WIDTH  = 300
PRE_BAR_HEIGHT = 28
PRE_BAR_FRAME  = 2
PRE_BAR_VALUE  = 1               # initial position

def is_linux():
    return sys.platform.startswith("linux")

# ---------------- Lightweight Loading Bar ----------------
class LoadingBar(tk.Frame):
    """
    A lightweight loading bar for values 1..127.
    set_value(v) with v in [1,127]
    Colors: bar_color (fill) and frame_color (outline).
    """
    def __init__(self, master, width=300, height=28,
                 bar_color="#00D084", bg="#101010",
                 frame_color="#555555", frame_width=2, **kw):
        super().__init__(master, bg=bg, **kw)
        self._bar_color = bar_color
        self._frame_color = frame_color
        self._frame_width = int(frame_width)
        self._value = 1

        self.canvas = tk.Canvas(self, width=int(width), height=int(height),
                                highlightthickness=0, bd=0, bg=bg)
        self.canvas.pack(fill="both", expand=True)

        self._outline_id = None
        self._fill_id = None

        self.canvas.bind("<Configure>", lambda e: self._redraw())
        self._redraw()

    # ---- public API ----
    def restyle(self, bar_color=None, bg=None, frame_color=None, frame_width=None):
        if bar_color is not None: self._bar_color = bar_color
        if frame_color is not None: self._frame_color = frame_color
        if frame_width is not None: self._frame_width = int(frame_width)
        if bg is not None:
            try:
                self.configure(bg=bg)
                self.canvas.configure(bg=bg)
            except tk.TclError:
                pass
        self._redraw()

    def set_value(self, v: int):
        v = int(v)
        if v < 1: v = 1
        if v > 127: v = 127
        if v == self._value:
            return
        self._value = v
        self._redraw_fill()

    # ---- internals ----
    def _geom(self):
        w = max(2, self.canvas.winfo_width())
        h = max(2, self.canvas.winfo_height())
        pad = self._frame_width
        return pad, pad, w - pad, h - pad

    def _redraw(self):
        self.canvas.delete("all")
        self._outline_id = None
        self._fill_id = None
        x0, y0, x1, y1 = self._geom()

        # outline
        self._outline_id = self.canvas.create_rectangle(
            x0, y0, x1, y1, outline=self._frame_color, width=self._frame_width
        )
        # fill
        self._fill_id = self.canvas.create_rectangle(
            x0, y0, x0, y1, outline="", fill=self._bar_color
        )
        self._redraw_fill()

    def _redraw_fill(self):
        if self._fill_id is None:
            return
        x0, y0, x1, y1 = self._geom()
        ratio = (self._value - 1) / 126.0  # 1..127 -> 0..1
        fill_x = x0 + ratio * (x1 - x0)
        self.canvas.itemconfig(self._fill_id, fill=self._bar_color)
        self.canvas.coords(self._fill_id, x0, y0, fill_x, y1)

# ---------------- UDP Listener ----------------
def start_udp_listener(out_queue: Queue):
    """
    Enqueued messages:
      ("SET", r, c, fg, bg, align, text)
      ("BG_CELL", r, c, bg)
      ("ALIGN_CELL", r, c, align)
      ("BAR_STYLE", r, c, fg, bg, width_px, height_px, frame_px_or_none)
      ("BAR_VALUE", r, c, value)
      ("BAR_SET", r, c, value, fg, bg, width_px, height_px, frame_px_or_none)
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
    except Exception:
        pass
    sock.bind((HOST, PORT))
    sock.setblocking(True)

    def loop():
        while True:
            try:
                data, _addr = sock.recvfrom(16384)
                line = data.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                # Normalize Pd flavor: optional trailing ';' and leading 'send'
                if line.endswith(";"):
                    line = line[:-1].rstrip()
                parts = line.split()
                if not parts:
                    continue
                if parts[0].lower() == "send":
                    parts = parts[1:]
                    if not parts:  # just "send" with nothing else
                        continue

                head = parts[0].upper()

                # ALIGN row col align
                if head == "ALIGN" and len(parts) >= 4:
                    try:
                        r = int(parts[1]); c = int(parts[2]); align = parts[3]
                        out_queue.put(("ALIGN_CELL", r, c, align))
                    except ValueError:
                        pass
                    continue

                # BG row col color
                if head == "BG" and len(parts) >= 4:
                    try:
                        r = int(parts[1]); c = int(parts[2]); bg = parts[3]
                        out_queue.put(("BG_CELL", r, c, bg))
                    except ValueError:
                        pass
                    continue

                # BARSET <c> <r> <val> <fg> <bg> <w> <h> [frame]
                if head == "BARSET" and len(parts) >= 8:
                    try:
                        c = int(parts[1]); r = int(parts[2]); val = int(parts[3])
                        fg = parts[4]; bg = parts[5]
                        w = int(parts[6]); h = int(parts[7])
                        frame_px = int(parts[8]) if len(parts) >= 9 else None
                        out_queue.put(("BAR_SET", r, c, val, fg, bg, w, h, frame_px))
                    except ValueError:
                        pass
                    continue

                # (legacy) BAR <c> <r> <fg> <bg> <w> <h> [frame]
                if head == "BAR" and len(parts) >= 7:
                    try:
                        c = int(parts[1]); r = int(parts[2])
                        fg = parts[3]; bg = parts[4]
                        w = int(parts[5]); h = int(parts[6])
                        frame_px = int(parts[7]) if len(parts) >= 8 else None
                        out_queue.put(("BAR_STYLE", r, c, fg, bg, w, h, frame_px))
                    except ValueError:
                        pass
                    continue

                # (legacy) BARVAL <c> <r> <value>
                if head == "BARVAL" and len(parts) >= 4:
                    try:
                        c = int(parts[1]); r = int(parts[2]); val = int(parts[3])
                        out_queue.put(("BAR_VALUE", r, c, val))
                    except ValueError:
                        pass
                    continue

                # ---- SET (text cells) ----
                if len(parts) >= 5:
                    try:
                        c = int(parts[0]); r = int(parts[1])
                    except ValueError:
                        continue

                    if len(parts) >= 6:
                        fg = parts[2]
                        bg = parts[3]
                        align = parts[4]
                        text = " ".join(parts[5:]).rstrip(";")
                    else:
                        fg = parts[2]
                        bg = parts[3]
                        align = None
                        text = " ".join(parts[4:]).rstrip(";")

                    out_queue.put(("SET", r, c, fg, bg, align, text))
                    continue

            except Exception:
                continue

    threading.Thread(target=loop, daemon=True).start()

# ---------------- UI Class ----------------
class Display:
    def __init__(self, root, rows=DEFAULT_ROWS, cols_per_row=None):
        self.root = root
        self.rows = rows
        self.cols_per_row = list(cols_per_row or COLS_PER_ROW)

        # Fonts
        self.small_font = tkfont.Font(family="DejaVu Sans", size=SMALL_FONT_PT, weight="bold")
        self.big_font   = tkfont.Font(family="DejaVu Sans", size=BIG_FONT_PT,   weight="bold")
        self.head_font  = tkfont.Font(family="DejaVu Sans",
                                      size=SMALL_FONT_PT + HEAD_ROW_BONUS_PT,
                                      weight="bold")

        self.vars, self.labels, self.cell_frames, self.row_frames = [], [], [], []
        self.bar_holders, self.bars = [], []

        # ---- IMPORTANT: init caches BEFORE building UI (pre-create bars uses caches)
        self._init_caches()

        # build widgets (this also pre-creates bars in row 3)
        self._build_ui()

    def _init_caches(self):
        self.last_text   = [ [None]*self.cols_per_row[r] for r in range(self.rows) ]
        self.last_fg     = [ [None]*self.cols_per_row[r] for r in range(self.rows) ]
        self.last_bg     = [ [None]*self.cols_per_row[r] for r in range(self.rows) ]
        self.last_anchor = [ [None]*self.cols_per_row[r] for r in range(self.rows) ]

    def _build_ui(self):
        if is_linux():
            self.root.geometry("800x480+0+0")  # 5" RPi display typical mode
        else:
            self.root.geometry("800x480+100+100")

        self.root.configure(bg="black")

        self.container = tk.Frame(self.root, bg="black", bd=0, highlightthickness=0)
        self.container.pack(expand=True, fill="both")

        self.container.columnconfigure(0, weight=1, uniform="outer_col")
        for r in range(self.rows):
            self.container.rowconfigure(r, weight=1, uniform="outer_row")

        self.vars.clear(); self.labels.clear(); self.cell_frames.clear()
        self.row_frames.clear(); self.bar_holders.clear(); self.bars.clear()

        for r in range(self.rows):
            row_frame = tk.Frame(self.container, bg="black", bd=0, highlightthickness=0)
            row_frame.grid(row=r, column=0, sticky="nsew", padx=0, pady=0)
            row_frame.grid_propagate(False)
            self.row_frames.append(row_frame)

            cols = self.cols_per_row[r]
            for c in range(cols):
                row_frame.columnconfigure(c, weight=1, uniform=f"row{r}_col")
            row_frame.rowconfigure(0, weight=1)

            row_vars, row_labels, row_cells = [], [], []
            row_bar_holders, row_bars = [], []

            for c in range(cols):
                cell = tk.Frame(row_frame, bg="black", bd=0, highlightthickness=0)
                cell.grid(row=0, column=c, sticky="nsew", padx=0, pady=0)
                cell.grid_propagate(False)
                row_cells.append(cell)

                var = tk.StringVar(value="")
                row_vars.append(var)

                # font choice
                if r == 0: fnt = self.head_font
                elif r in BIG_FONT_ROWS: fnt = self.big_font
                else: fnt = self.small_font

                lbl = tk.Label(cell, textvariable=var,
                               bg="black", fg="white",
                               anchor="w", padx=0, pady=0, bd=0, highlightthickness=0)
                lbl.configure(font=fnt)
                lbl.pack(fill="both", expand=True)
                row_labels.append(lbl)

                # bar placeholders
                row_bar_holders.append(None)
                row_bars.append(None)

            self.vars.append(row_vars)
            self.labels.append(row_labels)
            self.cell_frames.append(row_cells)
            self.bar_holders.append(row_bar_holders)
            self.bars.append(row_bars)

        # ---- PRE-CREATE BARS in row index PRECREATE_BAR_ROW_IDX ----
        pre_r = PRECREATE_BAR_ROW_IDX
        if 0 <= pre_r < self.rows:
            for c in range(self.cols_per_row[pre_r]):
                self._ensure_bar(pre_r, c,
                                 fg=PRE_BAR_FG, bg=PRE_BAR_BG,
                                 width_px=PRE_BAR_WIDTH, height_px=PRE_BAR_HEIGHT,
                                 frame_px=PRE_BAR_FRAME)
                self.set_bar_value(pre_r, c, PRE_BAR_VALUE)

        # Fullscreen toggle + exit
        self.root.bind("<F11>", lambda e: self.root.attributes(
            "-fullscreen", not self.root.attributes("-fullscreen")))
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(300, lambda: self.root.attributes("-topmost", False))

    # ------- Bars: create / style / size / value -------
    def _ensure_bar(self, r, c, fg, bg, width_px, height_px, frame_px):
        """Create a bar in cell (r,c), replacing the label visually (label kept for later reuse)."""
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            return

        cell = self.cell_frames[r][c]
        # hide text label if present
        lbl = self.labels[r][c]
        if lbl.winfo_manager():
            lbl.forget()

        # create or reuse holder centered in cell with fixed size
        holder = self.bar_holders[r][c]
        if holder is None:
            holder = tk.Frame(cell, bg=bg, bd=0, highlightthickness=0)
            # absolute size inside the flexible grid cell:
            holder.place(relx=0.5, rely=0.5, anchor="center", width=width_px, height=height_px)
            self.bar_holders[r][c] = holder
        else:
            holder.configure(bg=bg)
            holder.place_configure(width=width_px, height=height_px)

        # create or restyle bar
        frame_px = PRE_BAR_FRAME if frame_px is None else int(frame_px)
        bar = self.bars[r][c]
        if bar is None:
            bar = LoadingBar(holder, width=width_px, height=height_px,
                             bar_color=fg, bg=bg, frame_color=fg, frame_width=frame_px)
            bar.pack(fill="both", expand=True)
            self.bars[r][c] = bar
        else:
            bar.restyle(bar_color=fg, frame_color=fg, bg=bg, frame_width=frame_px)

        # remember bg in caches for this cell
        self.last_bg[r][c] = bg

    def set_bar_style(self, r, c, fg, bg, width_px, height_px, frame_px):
        self._ensure_bar(r, c, fg, bg, width_px, height_px, frame_px)

    def set_bar_value(self, r, c, value):
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]):
            return
        bar = self.bars[r][c]
        if bar is None:
            self._ensure_bar(r, c, fg=PRE_BAR_FG, bg=PRE_BAR_BG,
                             width_px=PRE_BAR_WIDTH, height_px=PRE_BAR_HEIGHT,
                             frame_px=PRE_BAR_FRAME)
            bar = self.bars[r][c]
        bar.set_value(value)

    def set_bar_all(self, r, c, value, fg, bg, width_px, height_px, frame_px):
        self._ensure_bar(r, c, fg, bg, width_px, height_px, frame_px)
        self.set_bar_value(r, c, value)

    # -------- Text/Color/Align for normal cells --------
    @staticmethod
    def _map_anchor(align: str | None):
        if not align: return "w"
        a = align.strip().lower()
        if a in ("l", "left"):   return "w"
        if a in ("c", "center", "centre", "mid", "middle"): return "center"
        if a in ("r", "right"):  return "e"
        return "w"

    def set_cell(self, r: int, c: int, text: str = None, fg: str = None, bg: str = None, align: str | None = None):
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]): return

        # If a bar lives here and text is sent, show text again (bar hidden).
        bar = self.bars[r][c]
        if text is not None and text != "":
            if bar is not None:
                # hide bar holder and show label
                holder = self.bar_holders[r][c]
                if holder is not None:
                    holder.place_forget()
                self.bars[r][c] = None
                self.bar_holders[r][c] = None
                # re-pack the label
                lbl = self.labels[r][c]
                if not lbl.winfo_manager():
                    lbl.pack(fill="both", expand=True)

        lbl = self.labels[r][c]

        if text is not None and text != self.last_text[r][c]:
            self.vars[r][c].set(text)
            self.last_text[r][c] = text

        if fg and fg != self.last_fg[r][c]:
            try:
                lbl.configure(fg=fg)
                self.last_fg[r][c] = fg
            except tk.TclError:
                pass

        if bg and bg != self.last_bg[r][c]:
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

# ---------------- Main ----------------
def main():
    root = tk.Tk()
    root.title("Molipe Display Grid (PD-UDP) + BARSET (Row 3 preloaded)")

    ui = Display(root, DEFAULT_ROWS, COLS_PER_ROW)

    q: Queue = Queue()
    start_udp_listener(q)

    pending_latest = {}

    def drain_and_apply():
        while True:
            try:
                msg = q.get_nowait()
            except Empty:
                break

            kind = msg[0]

            if kind == "BG_CELL":
                _, r, c, bg = msg
                pending_latest[("BG", r, c)] = bg
                continue

            if kind == "ALIGN_CELL":
                _, r, c, align = msg
                pending_latest[("ALIGN", r, c)] = align
                continue

            if kind == "SET":
                _, r, c, fg, bg, align, text = msg
                pending_latest[("SET", r, c)] = (text, fg, bg, align)
                continue

            if kind == "BAR_STYLE":
                _, r, c, fg, bg, w, h, frame_px = msg
                pending_latest[("BAR_STYLE", r, c)] = (fg, bg, w, h, frame_px)
                continue

            if kind == "BAR_VALUE":
                _, r, c, val = msg
                pending_latest[("BAR_VALUE", r, c)] = val
                continue

            if kind == "BAR_SET":
                _, r, c, val, fg, bg, w, h, frame_px = msg
                pending_latest[("BAR_SET", r, c)] = (val, fg, bg, w, h, frame_px)
                continue

        applied = 0
        # BG first
        for key, bg in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK: break
            if key[0] == "BG":
                _, r, c = key
                ui.set_cell(r, c, None, None, bg, None)
                del pending_latest[key]
                applied += 1

        # ALIGN second
        for key, align in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK: break
            if key[0] == "ALIGN":
                _, r, c = key
                ui.set_cell(r, c, None, None, None, align)
                del pending_latest[key]
                applied += 1

        # BAR_SET next (does style + value in one go)
        for key, payload in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK: break
            if key[0] == "BAR_SET":
                _, r, c = key
                val, fg, bg, w, h, frame_px = payload
                ui.set_bar_all(r, c, val, fg, bg, w, h, frame_px)
                del pending_latest[key]
                applied += 1

        # legacy bar style/value
        for key, payload in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK: break
            if key[0] == "BAR_STYLE":
                _, r, c = key
                fg, bg, w, h, frame_px = payload
                ui.set_bar_style(r, c, fg, bg, w, h, frame_px)
                del pending_latest[key]
                applied += 1

        for key, val in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK: break
            if key[0] == "BAR_VALUE":
                _, r, c = key
                ui.set_bar_value(r, c, val)
                del pending_latest[key]
                applied += 1

        # text last
        for key, payload in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK: break
            if key[0] == "SET":
                _, r, c = key
                text, fg, bg, align = payload
                ui.set_cell(r, c, text, fg, bg, align)
                del pending_latest[key]
                applied += 1

        root.after(POLL_INTERVAL_MS, drain_and_apply)

    root.after(POLL_INTERVAL_MS, drain_and_apply)
    root.mainloop()

if __name__ == "__main__":
    main()
