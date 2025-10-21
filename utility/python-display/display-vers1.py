#!/usr/bin/env python3
import os, sys, socket, threading, time, subprocess
from queue import Queue, Empty
os.environ["TK_SILENCE_DEPRECATION"] = "1"

import tkinter as tk
from tkinter import font as tkfont

# ---------------- Configuration ----------------
HOST, PORT = "0.0.0.0", 9001
DEFAULT_ROWS = 12                 # total number of rows
# Row 0: 8 cells; rows 1..7: 4 cells each; rows 8..11: 8 cells each
COLS_PER_ROW = [8] + [4]*7 + [8]*4

POLL_INTERVAL_MS = 10             # drain + paint every 10 ms (~100 Hz)
MAX_APPLIES_PER_TICK = 512        # safety cap per frame

def is_linux():
    return sys.platform.startswith("linux")

# ---------------- Shutdown helper ----------------
def request_shutdown(delay_seconds: int = 0):
    """Power off the machine after an optional delay (seconds)."""
    def _worker():
        try:
            if delay_seconds > 0:
                time.sleep(max(0, int(delay_seconds)))
            if os.geteuid() == 0:
                subprocess.run(["/bin/systemctl", "poweroff", "--no-wall"], check=False)
            else:
                subprocess.run(["sudo", "/bin/systemctl", "poweroff", "--no-wall"], check=False)
        except Exception as e:
            print(f"[shutdown] failed: {e}", flush=True)
    threading.Thread(target=_worker, daemon=True).start()

# ---------------- UDP Listener ----------------
def start_udp_listener(out_queue: Queue):
    """
    Enqueue parsed messages:
      ("SET", r, c, fg_color, bg_color, align, text)  # align may be None if omitted
      ("BG_CELL", r, c, bg_color)
      ("ALIGN_CELL", r, c, align)                     # 'left' | 'center' | 'right'
      ("GRID", rows, default_cols)
      ("RCFG", row, cols)
      ("SYS_SHUTDOWN", delay_seconds)
    Colors can be any Tk color string, e.g. "#000000", "#ff00ff", "white".
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
                parts = line.split()
                if not parts:
                    continue

                head = parts[0].upper()

                # ---- SYSTEM ----
                if head == "SYS" and len(parts) >= 2 and parts[1].upper() == "SHUTDOWN":
                    delay = 0
                    if len(parts) >= 3:
                        try:
                            delay = int(float(parts[2]))
                        except ValueError:
                            delay = 0
                    out_queue.put(("SYS_SHUTDOWN", delay))
                    continue

                # ---- PER-ROW COLUMN CONFIG ----
                if head == "RCFG" and len(parts) >= 3:
                    try:
                        row = int(parts[1]); cols = int(parts[2])
                        out_queue.put(("RCFG", row, max(1, cols)))
                    except ValueError:
                        pass
                    continue

                # ---- GRID SIZE (reinitialize) ----
                if head == "GRID" and len(parts) >= 3:
                    try:
                        rows = int(parts[1]); dcols = int(parts[2])
                        out_queue.put(("GRID", max(1, rows), max(1, dcols)))
                    except ValueError:
                        pass
                    continue

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
        self.cols_per_row = list(cols_per_row or ([8] * rows))
        self.head_font = tkfont.Font(family="DejaVu Sans", size=12, weight="bold")
        self.body_font = tkfont.Font(family="DejaVu Sans", size=12, weight="bold")

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
            self.root.geometry("640x360+50+50")
        else:
            self.root.geometry("640x360+100+100")

        self.root.configure(bg="black")

        self.container = tk.Frame(self.root, bg="black", bd=0, highlightthickness=0)
        self.container.pack(expand=True, fill="both")

        self.container.columnconfigure(0, weight=1, uniform="outer_col")
        self.container.rowconfigure(0, weight=1, uniform="outer_row")
        for r in range(1, self.rows):
            self.container.rowconfigure(r, weight=2, uniform="outer_row")

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

                lbl = tk.Label(
                    cell, textvariable=var,
                    bg="black", fg="white",
                    anchor="w", padx=0, pady=0, bd=0, highlightthickness=0
                )
                lbl.configure(font=self.head_font if r == 0 else self.body_font)
                lbl.pack(fill="both", expand=True)
                row_labels.append(lbl)

            self.vars.append(row_vars)
            self.labels.append(row_labels)
            self.cell_frames.append(row_cells)

        self.root.bind("<Configure>", lambda e: self._autosize_fonts())
        self.root.after(50, self._autosize_fonts)

        self.root.bind("<F11>", lambda e: self.root.attributes(
            "-fullscreen", not self.root.attributes("-fullscreen")))
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(300, lambda: self.root.attributes("-topmost", False))

    # --- Font autosize helpers ---
    def _fit_font_to_height(self, font_obj: tkfont.Font, target_px: int):
        if target_px <= 4:
            font_obj.configure(size=4); return
        lo, hi = 4, 512
        while lo < hi:
            mid = (lo + hi + 1) // 2
            font_obj.configure(size=mid)
            ls = font_obj.metrics("linespace")
            if ls <= target_px: lo = mid
            else: hi = mid - 1
        font_obj.configure(size=lo)

    def _autosize_fonts(self):
        if not self.row_frames: return
        try:
            h0 = self.row_frames[0].winfo_height()
            h1 = self.row_frames[min(1, self.rows-1)].winfo_height()
        except Exception:
            return
        if h0 <= 0 or h1 <= 0: return
        self._fit_font_to_height(self.head_font, max(4, h0 - 2))
        self._fit_font_to_height(self.body_font, max(4, h1 - 2))

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

    def reconfigure_row(self, row: int, cols: int):
        if row < 0: return
        if row >= self.rows:
            extra = row + 1 - self.rows
            for _ in range(extra):
                self.cols_per_row.append(self.cols_per_row[-1] if self.cols_per_row else 8)
            self.rows = row + 1
        self.cols_per_row[row] = max(1, cols)
        for w in self.root.winfo_children():
            w.destroy()
        self._build_ui()
        self._init_caches()

    def rebuild_grid(self, rows: int, default_cols: int):
        self.rows = max(1, rows)
        self.cols_per_row = [max(1, default_cols)] * self.rows
        for w in self.root.winfo_children():
            w.destroy()
        self._build_ui()
        self._init_caches()

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

            if kind == "SYS_SHUTDOWN":
                _, delay = msg
                print(f"[SYS] shutdown requested in {delay}s (euid={os.geteuid()})", flush=True)
                request_shutdown(delay)
                continue

            if kind == "GRID":
                _, rows, dcols = msg
                ui.rebuild_grid(rows, dcols)
                pending_latest.clear()
                continue

            if kind == "RCFG":
                _, row, cols = msg
                ui.reconfigure_row(row, cols)
                pending_latest.clear()
                continue

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
