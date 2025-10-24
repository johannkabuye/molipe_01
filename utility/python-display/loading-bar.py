#!/usr/bin/env python3
import tkinter as tk

class LoadingBar(tk.Frame):
    """
    A lightweight loading bar for values 1..127.
    - Call set_value(v) with v in [1,127].
    - Renders a framed bar, no text.
    """
    def __init__(self, master, width=300, height=28,
                 bar_color="#00D084", bg="#101010",
                 frame_color="#555555", frame_width=2, **kw):
        super().__init__(master, bg=bg, **kw)
        self.width  = int(width)
        self.height = int(height)
        self.bg = bg
        self.bar_color = bar_color
        self.frame_color = frame_color
        self.frame_width = int(frame_width)

        # canvas fills the frame; we'll draw outline + fill
        self.canvas = tk.Canvas(self, width=self.width, height=self.height,
                                highlightthickness=0, bd=0, bg=self.bg)
        self.canvas.pack(fill="both", expand=True)

        # IDs for reuse on redraw
        self._outline_id = None
        self._fill_id = None

        # current value (clamped to [1,127])
        self._value = 1

        # redraw when resized (keeps crisp border)
        self.canvas.bind("<Configure>", lambda e: self._redraw())

        self._redraw()

    def set_value(self, v: int):
        """Set the bar fill with v in [1..127]."""
        v = int(v)
        if v < 1: v = 1
        if v > 127: v = 127
        if v == self._value:
            return
        self._value = v
        self._redraw_fill()

    # ---------- internal drawing ----------
    def _geom(self):
        """Compute inner rect geometry considering frame width."""
        w = max(2, self.canvas.winfo_width())
        h = max(2, self.canvas.winfo_height())
        pad = self.frame_width
        x0, y0 = pad, pad
        x1, y1 = w - pad, h - pad
        return x0, y0, x1, y1

    def _redraw(self):
        """Redraw outline and fill."""
        self.canvas.delete("all")
        self._outline_id = None
        self._fill_id = None

        x0, y0, x1, y1 = self._geom()

        # outline (frame)
        self._outline_id = self.canvas.create_rectangle(
            x0, y0, x1, y1,
            outline=self.frame_color,
            width=self.frame_width
        )

        # fill (initial)
        self._fill_id = self.canvas.create_rectangle(
            x0, y0, x0, y1,  # will be resized in _redraw_fill
            outline="", fill=self.bar_color
        )
        self._redraw_fill()

    def _redraw_fill(self):
        """Resize the fill rectangle based on current value."""
        if self._fill_id is None:
            return

        x0, y0, x1, y1 = self._geom()

        # Map 1..127 to 0..1 (1 should not look empty → start slightly above 0)
        # exact linear mapping: ratio = (v - 1) / 126
        ratio = (self._value - 1) / 126.0

        # Compute new fill width
        fill_x = x0 + ratio * (x1 - x0)

        # Update the rectangle without recreating
        self.canvas.coords(self._fill_id, x0, y0, fill_x, y1)


# ---------------- Demo ----------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Loading Bar 1..127")

    # Optional: clean dark background window
    root.configure(bg="#101010")

    # Fullscreen toggles for development
    def toggle_fullscreen(event=None):
        root.attributes("-fullscreen", not root.attributes("-fullscreen"))
    def end_fullscreen(event=None):
        root.attributes("-fullscreen", False)
    root.bind("<F11>", toggle_fullscreen)
    root.bind("<Escape>", end_fullscreen)

    bar = LoadingBar(root, width=500, height=40,
                     bar_color="#00D084", bg="#101010",
                     frame_color="#888888", frame_width=2)
    bar.pack(padx=20, pady=20, fill="x")

    # Simple keyboard control for testing: Left/Right to change value
    current = {"v": 1}
    bar.set_value(current["v"])

    def inc(_e=None):
        current["v"] = min(127, current["v"] + 1)
        bar.set_value(current["v"])
    def dec(_e=None):
        current["v"] = max(1, current["v"] - 1)
        bar.set_value(current["v"])

    root.bind("<Right>", inc)
    root.bind("<Left>",  dec)

    # Example: auto-animate to show it works
    def animate():
        current["v"] += 1
        if current["v"] > 127:
            current["v"] = 1
        bar.set_value(current["v"])
        root.after(30, animate)  # ~33 FPS
    # Comment out next line if you don't want auto-animation
    # animate()

    root.mainloop()
