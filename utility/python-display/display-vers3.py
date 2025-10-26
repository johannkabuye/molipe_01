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
SMALL_FONT_PT = 25
BIG_FONT_PT   = 28
HEAD_ROW_BONUS_PT = -8

POLL_INTERVAL_MS = 10
MAX_APPLIES_PER_TICK = 512

def is_linux():
    return sys.platform.startswith("linux")

# ---------------- Dual Ring Widget ----------------
class DualRing(tk.Frame):
    """
    Two concentric arcs starting at 7 o'clock (210°) sweeping CLOCKWISE up to ~4 o'clock (330°).
    The CENTER shows the inner arc's current value (1..127).
    """
    def __init__(self, master, size=200, fg_outer="#606060", fg_inner="#ffffff",
                 bg="#000000", w_outer=15, w_inner=40, text_color="#ffffff", **kw):
        super().__init__(master, bg=bg, **kw)
        self._size = int(size)
        self._bg = bg
        self._fg_outer = fg_outer
        self._fg_inner = fg_inner
        self._w_outer = int(w_outer)
        self._w_inner = int(w_inner)
        self._text_color = text_color
        self._outer_val = 0
        self._inner_val = 0

        self.canvas = tk.Canvas(self, width=self._size, height=self._size,
                                bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        self._outer_arc_id = None
        self._inner_arc_id = None
        self._label_id = None

        self.canvas.bind("<Configure>", lambda e: self._redraw())
        self._redraw()

    @staticmethod
    def _clip01(v):
        try:
            v = int(v)
        except Exception:
            v = 0
        return 0 if v < 0 else 127 if v > 127 else v

    def set_values(self, outer_v, inner_v):
        self._outer_val = self._clip01(outer_v)
        self._inner_val = self._clip01(inner_v)
        self._update_extents()
        self._update_label()

    def set_outer(self, v):
        self._outer_val = self._clip01(v)
        self._update_extents()

    def set_inner(self, v):
        self._inner_val = self._clip01(v)
        self._update_extents()
        self._update_label()

    def restyle(self, fg_outer=None, fg_inner=None, bg=None, w_outer=None, w_inner=None, text_color=None):
        if fg_outer is not None: self._fg_outer = fg_outer
        if fg_inner is not None: self._fg_inner = fg_inner
        if w_outer is not None:  self._w_outer = int(w_outer)
        if w_inner is not None:  self._w_inner = int(w_inner)
        if text_color is not None: self._text_color = text_color
        if bg is not None:
            self._bg = bg
            try:
                self.configure(bg=bg); self.canvas.configure(bg=bg)
            except tk.TclError:
                pass
        self._redraw()

    def resize(self, size_px):
        self._size = int(size_px)
        self.canvas.config(width=self._size, height=self._size)
        self._redraw()

    def _bbox_for(self, pad):
        w = max(2, self.canvas.winfo_width())
        h = max(2, self.canvas.winfo_height())
        s = min(w, h)
        cx, cy = w//2, h//2
        r = s//2 - pad
        return (cx - r, cy - r, cx + r, cy + r)

    def _redraw(self):
        self.canvas.delete("all")

        outer_pad = max(self._w_outer//2 + 2, 4)
        inner_pad = max(self._w_inner//2 + 2, 4) + self._w_outer

        outer_bbox = self._bbox_for(outer_pad)
        inner_bbox = self._bbox_for(inner_pad)

        # background "tracks" (pure black)
        self.canvas.create_oval(*outer_bbox, outline="#000", width=self._w_outer)
        self.canvas.create_oval(*inner_bbox, outline="#000", width=self._w_inner)

        # value arcs: start at 210° (7 o'clock)
        self._outer_arc_id = self.canvas.create_arc(
            *outer_bbox, start=210, extent=0, style="arc",
            outline=self._fg_outer, width=self._w_outer
        )
        self._inner_arc_id = self.canvas.create_arc(
            *inner_bbox, start=210, extent=0, style="arc",
            outline=self._fg_inner, width=self._w_inner
        )

        # center value label (inner value)
        cx, cy = self.canvas.winfo_width()//2, self.canvas.winfo_height()//2
        font_px = 30
        font = ("DejaVu Sans", font_px, "bold")
        display_val = max(1, int(self._inner_val))
        self._label_id = self.canvas.create_text(
            cx, cy, text=str(display_val), fill=self._text_color, font=font
        )

        self._update_extents()

    def _update_extents(self):
        SWEEP_MAX = 240.0  # 7 → 4 o'clock
        ext_outer = -SWEEP_MAX * (self._outer_val / 127.0)  # negative = clockwise
        ext_inner = -SWEEP_MAX * (self._inner_val / 127.0)
        if self._outer_arc_id is not None:
            self.canvas.itemconfig(self._outer_arc_id, extent=ext_outer, outline=self._fg_outer)
        if self._inner_arc_id is not None:
            self.canvas.itemconfig(self._inner_arc_id, extent=ext_inner, outline=self._fg_inner)

    def _update_label(self):
        if self._label_id is None: return
        cx, cy = self.canvas.winfo_width()//2, self.canvas.winfo_height()//2
        font_px = 30
        font = ("DejaVu Sans", font_px, "bold")
        display_val = max(1, int(self._inner_val))
        self.canvas.itemconfig(self._label_id, text=str(display_val), fill=self._text_color, font=font)
        self.canvas.coords(self._label_id, cx, cy)

# ---------------- UDP Listener ----------------
def start_udp_listener(out_queue: Queue):
    """
    Enqueued messages:
      ("SET", r, c, fg, bg, align, text)
      ("BG_CELL", r, c, bg)
      ("ALIGN_CELL", r, c, align)

      ("RING_STYLE", r, c, fg_out, fg_in, bg, size_px, w_out, w_in)
      ("RING_VALUE", r, c, outer, inner)
      ("RING_SET",   r, c, outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in)

    NOTE: For rings, we use column THEN row (c r) just like SET.
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
                if line.endswith(";"):
                    line = line[:-1].rstrip()

                parts = line.split()
                if not parts:
                    continue

                head = parts[0].upper()

                # ALIGN r c align
                if head == "ALIGN" and len(parts) >= 4:
                    try:
                        r = int(parts[1]); c = int(parts[2]); align = parts[3]
                        out_queue.put(("ALIGN_CELL", r, c, align))
                    except ValueError:
                        pass
                    continue

                # BG r c bg
                if head == "BG" and len(parts) >= 4:
                    try:
                        r = int(parts[1]); c = int(parts[2]); bg = parts[3]
                        out_queue.put(("BG_CELL", r, c, bg))
                    except ValueError:
                        pass
                    continue

                # RING c r fg_out fg_in bg size w_out w_in
                if head == "RING" and len(parts) >= 9:
                    try:
                        c = int(parts[1]); r = int(parts[2])
                        fg_out, fg_in, bg = parts[3], parts[4], parts[5]
                        size_px, w_out, w_in = int(parts[6]), int(parts[7]), int(parts[8])
                        out_queue.put(("RING_STYLE", r, c, fg_out, fg_in, bg, size_px, w_out, w_in))
                    except ValueError:
                        pass
                    continue

                # RINGVAL c r outer inner
                if head == "RINGVAL" and len(parts) >= 5:
                    try:
                        c = int(parts[1]); r = int(parts[2]); outer = int(parts[3]); inner = int(parts[4])
                        out_queue.put(("RING_VALUE", r, c, outer, inner))
                    except ValueError:
                        pass
                    continue

                # RINGSET c r outer inner fg_out fg_in bg size w_out w_in
                if head == "RINGSET" and len(parts) >= 11:
                    try:
                        c = int(parts[1]); r = int(parts[2]); outer = int(parts[3]); inner = int(parts[4])
                        fg_out, fg_in, bg = parts[5], parts[6], parts[7]
                        size_px, w_out, w_in = int(parts[8]), int(parts[9]), int(parts[10])
                        out_queue.put(("RING_SET", r, c, outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in))
                    except ValueError:
                        pass
                    continue

                # ---- SET (text cells) ----
                # SET c r fg bg align text...
                if len(parts) >= 5:
                    try:
                        c = int(parts[0]); r = int(parts[1])
                    except ValueError:
                        continue

                    if len(parts) >= 6:
                        fg = parts[2]; bg = parts[3]; align = parts[4]
                        text = " ".join(parts[5:]).rstrip(";")
                    else:
                        fg = parts[2]; bg = parts[3]; align = None
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

        # rings per cell
        self.ring_holders = [ [None]*self.cols_per_row[r] for r in range(self.rows) ]
        self.rings        = [ [None]*self.cols_per_row[r] for r in range(self.rows) ]

    def _init_caches(self):
        self.last_text  = [ [None]*self.cols_per_row[r] for r in range(self.rows) ]
        self.last_fg    = [ [None]*self.cols_per_row[r] for r in range(self.rows) ]
        self.last_bg    = [ [None]*self.cols_per_row[r] for r in range(self.rows) ]
        self.last_anchor= [ [None]*self.cols_per_row[r] for r in range(self.rows) ]

    def _build_ui(self):
        if is_linux():
            self.root.geometry("1280x720+0+0")
        else:
            self.root.geometry("1280x720+100+100")

        self.root.configure(bg="black")

        self.container = tk.Frame(self.root, bg="black", bd=0, highlightthickness=0)
        self.container.pack(expand=True, fill="both")

        self.container.columnconfigure(0, weight=1, uniform="outer_col")
        for r in range(self.rows):
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

                if r == 0:
                    fnt = self.head_font
                elif r in BIG_FONT_ROWS:
                    fnt = self.big_font
                else:
                    fnt = self.small_font

                lbl = tk.Label(cell, textvariable=var,
                               bg="black", fg="white",
                               anchor="w", padx=0, pady=0, bd=0, highlightthickness=0)
                lbl.configure(font=fnt)
                lbl.pack(fill="both", expand=True)
                row_labels.append(lbl)

            self.vars.append(row_vars)
            self.labels.append(row_labels)
            self.cell_frames.append(row_cells)

        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(300, lambda: self.root.attributes("-topmost", False))

    # ---- RING helpers ----
    def _ensure_ring(self, r, c, fg_out, fg_in, bg, size_px, w_out, w_in):
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]): return

        # hide label if present
        lbl = self.labels[r][c]
        if lbl.winfo_manager():
            lbl.forget()

        holder = self.ring_holders[r][c]
        if holder is None:
            holder = tk.Frame(self.cell_frames[r][c], bg="black", bd=0, highlightthickness=0)
            holder.place(relx=0.5, rely=0.5, anchor="center", width=size_px, height=size_px)
            self.ring_holders[r][c] = holder
        else:
            holder.place_configure(width=size_px, height=size_px)

        ring = self.rings[r][c]
        if ring is None:
            ring = DualRing(holder, size=size_px, fg_outer=fg_out, fg_inner=fg_in,
                            bg=bg, w_outer=w_out, w_inner=w_in, text_color="#ffffff")
            ring.pack(fill="both", expand=True)
            self.rings[r][c] = ring
        else:
            ring.restyle(fg_outer=fg_out, fg_inner=fg_in, bg=bg, w_outer=w_out, w_inner=w_in)
            ring.resize(size_px)

    def set_ring_style(self, r, c, fg_out, fg_in, bg, size_px, w_out, w_in):
        self._ensure_ring(r, c, fg_out, fg_in, bg, size_px, w_out, w_in)

    def set_ring_value(self, r, c, outer, inner):
        if not (0 <= r < self.rows) or not (0 <= c < self.cols_per_row[r]): return
        ring = self.rings[r][c]
        if ring is None:
            # create with sensible defaults if not present yet
            self._ensure_ring(r, c, "#606060", "#ffffff", "#000000", 200, 15, 40)
            ring = self.rings[r][c]
        ring.set_values(outer, inner)

    def set_ring_all(self, r, c, outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in):
        self._ensure_ring(r, c, fg_out, fg_in, bg, size_px, w_out, w_in)
        self.set_ring_value(r, c, outer, inner)

    # ---- Text cells ----
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

        # if a ring is present and text arrives, remove ring and show label again
        if text is not None and text != "":
            ring = self.rings[r][c]
            if ring is not None:
                holder = self.ring_holders[r][c]
                if holder is not None:
                    holder.place_forget()
                self.rings[r][c] = None
                self.ring_holders[r][c] = None
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
    root.title("")
    root.overrideredirect(True)
    root.attributes("-fullscreen", True)
    root.config(cursor="none")
    root.configure(bg="black")

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

            # rings
            if kind == "RING_STYLE":
                _, r, c, fg_out, fg_in, bg, size_px, w_out, w_in = msg
                pending_latest[("RING_STYLE", r, c)] = (fg_out, fg_in, bg, size_px, w_out, w_in)
                continue

            if kind == "RING_VALUE":
                _, r, c, outer, inner = msg
                pending_latest[("RING_VALUE", r, c)] = (outer, inner)
                continue

            if kind == "RING_SET":
                _, r, c, outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in = msg
                pending_latest[("RING_SET", r, c)] = (outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in)
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

        # RING_SET next (style + value)
        for key, payload in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK: break
            if key[0] == "RING_SET":
                _, r, c = key
                outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in = payload
                ui.set_ring_all(r, c, outer, inner, fg_out, fg_in, bg, size_px, w_out, w_in)
                del pending_latest[key]
                applied += 1

        # RING_STYLE then RING_VALUE
        for key, payload in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK: break
            if key[0] == "RING_STYLE":
                _, r, c = key
                fg_out, fg_in, bg, size_px, w_out, w_in = payload
                ui.set_ring_style(r, c, fg_out, fg_in, bg, size_px, w_out, w_in)
                del pending_latest[key]
                applied += 1

        for key, payload in list(pending_latest.items()):
            if applied >= MAX_APPLIES_PER_TICK: break
            if key[0] == "RING_VALUE":
                _, r, c = key
                outer, inner = payload
                ui.set_ring_value(r, c, outer, inner)
                del pending_latest[key]
                applied += 1

        # SET last
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
