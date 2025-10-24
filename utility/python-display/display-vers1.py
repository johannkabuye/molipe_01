#!/usr/bin/env python3
import os, sys, socket, threading
from queue import Queue, Empty
os.environ["TK_SILENCE_DEPRECATION"] = "1"

import tkinter as tk
from tkinter import font as tkfont

# ---------------- Configuration ----------------
HOST, PORT = "0.0.0.0", 9001

# --- FIXED GRID (13 rows) ---
# Row indices are 0-based here; comments show your 1-based plan.
# 1:8s, 2:4B, 3:4s, 4:8s, 5:4s, 6:1s, 7:4B, 8:4s, 9:8s, 10:4s, 11:1s, 12:8B, 13:8B
DEFAULT_ROWS = 13
COLS_PER_ROW = [8, 4, 4, 4, 4, 1, 4, 4, 4, 4, 1, 8, 8]
BIG_FONT_ROWS = {1, 6, 11, 12}  # (0-based) rows 2,7,12,13 are BIG

# --- FONT SIZE CONTROL (edit these) ---
SMALL_FONT_PT = 25      # base small font size
BIG_FONT_PT   = 28      # base big font size
HEAD_ROW_BONUS_PT = -8   # +2 pt for the first row (row 0) as requested

POLL_INTERVAL_MS = 10             # drain + paint every 10 ms (~100 Hz)
MAX_APPLIES_PER_TICK = 512        # safety cap per frame

def is_linux():
    return sys.platform.startswith("linux")

# ---------------- UDP Listener ----------------
def start_udp_listener(out_queue: Queue):
    """
    Enqueue parsed messages:
      ("SET", r, c, fg_color, bg_color, align, text)  # align may be None if omitted
      ("BG_CELL", r, c, bg_color)
      ("ALIGN_CELL", r, c, align)                     # 'left' | 'center' | 'right'

    Colors can be any Tk color string, e.g. "#000000", "#ff00ff", "white".

    NOTE: Flexible grid commands (GRID/RCFG) were removed by request.
    """
    import socket
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
                parts = line.split()
                if not parts:
                    continue

                head = parts[0].upper()

                # ---- ALIGN only ----
                # ALIGN row col align
                if head == "ALIGN" and len(parts) >= 4:
                    try:
                        r = int(parts[1]); c = int(parts[2])
                        align = parts[3]
                        out_queue.put(("ALIGN_CELL", r, c, align))
                    except ValueError:
                        pass
                    continue

                # ---- BG only ----
                # BG row col <bg_color>
                if head == "BG" and len(parts) >= 4:
                    try:
                        r = int(parts[1]); c = int(parts[2])
                        bg = parts[3]
                        out_queue.put(("BG_CELL", r, c, bg))
                    except ValueError:
                        pass
                    continue

                # ---- SET (cell content) ----
                # New format (with alignment):
                # SET col row <fg_color> <bg_color> <align> text...
                # Old format (no alignment): defaults to 'left'
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
                        # legacy: SET col row fg bg text...
                        fg = parts[2]
                        bg = parts[3]
                        align = None  # default later
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
        # FIXED: use provided cols_per_row exactly
        self.cols_per_row = list(cols_per_row or COLS_PER_ROW)

        # Fonts: small, big, and header (small + bonus)
        self.small_font = tkfont.Font(family="DejaVu Sans", size=SMALL_FONT_PT, weight="bold")
        self.big_font   = tkfont.Font(family="DejaVu Sans", size=BIG_FONT_PT,   weight="bold")
        self.head_font  = tkfont.Font(family="DejaVu Sans",
                                      size=SMALL_FONT_PT + HEAD_ROW_BONUS_PT,
                                      weight="bold")

        self.vars, self.labels, self.cell_frames, self.row_frames = [], [], [], []
        self._build_ui()

        # caches
        self.last_text, self.last_fg, self.last_bg, self.last_anchor = [], [], [], []
        self._init_caches()

    def _init_caches(self):
        self.last_text  = [ [None]*self.cols_per_row[r] for r in range(self.rows) ]
        self.last_fg    = [ [None]*self.cols_per_row[r] for r in range(self.rows) ]
        self.last_bg    = [ [None]*self.cols_per_row[r] for r in range(self.rows) ]
        self.last_anchor= [ [None]*self.cols_per_row[r] for r in range(self.rows) ]

    def _build_ui(self):
        if is_linux():
            self.root.geometry("800x480+0+0")  # typical for the 5" RPi display
        else:
            self.root.geometry("800x480+100+100")

        self.root.configure(bg="black")

        self.container = tk.Frame(self.root, bg="black", bd=0, highlightthickness=0)
        self.container.pack(expand=True, fill="both")

        self.container.columnconfigure(0, weight=1, uniform="outer_col")
        for r in range(self.rows):
            # Let Tk auto-distribute; weights can be tuned if you want different heights
            self.container.rowconfigure(r, weight=1, uniform="outer_row")

        self.vars.clear(); self.labels.clear(); self.cell_frames.clear(); self.row_frames.clear()

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

            for c in range(cols):
                cell = tk.Frame(row_frame, bg="black", bd=0, highlightthickness=0)
                cell.grid(row=0, column=c, sticky="nsew", padx=0, pady=0)
                cell.grid_propagate(False)
                row_cells.append(cell)

                var = tk.StringVar(value="")
                row_vars.append(var)

                # Choose font for this row:
                if r == 0:
                    fnt = self.head_font               # small + bonus (+2pt)
                elif r in BIG_FONT_ROWS:
                    fnt = self.big_font                # BIG rows
                else:
                    fnt = self.small_font              # small rows

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

        # Fullscreen toggle + exit
        self.root.bind("<F11>", lambda e: self.root.attributes(
            "-fullscreen", not self.root.attributes("-fullscreen")))
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(300, lambda: self.root.attributes("-topmost", False))

    @staticmethod
    def _map_anchor(align: str | None):
        if not align: return "w"  # default left
        a = align.strip().lower()
        if a in ("l", "left"):   return "w"
        if a in ("c", "center", "centre", "mid", "middle"): return "center"
        if a in ("r", "right"):  return "e"
        return "w"

    # ---- Per-cell operations ----
    def set_cell(self, r: int, c: int, text: str = None, fg: str = None, bg: str = None, align: str | None = None):
        if not (0 <= r < self.rows): return
        if not (0 <= c < self.cols_per_row[r]): return
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
    root.title("Molipe Display Grid (PD-UDP)")

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

        # SET last (can override fg/bg/align/text)
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
