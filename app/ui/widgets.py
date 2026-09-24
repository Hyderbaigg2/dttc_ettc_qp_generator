"""Small reusable widgets."""
import tkinter as tk
from tkinter import ttk


class ScrollableFrame(ttk.Frame):
    """A vertically scrollable container. Put your widgets in `.body`.

    Needed because form content (topics grow as the user adds them, etc.)
    can exceed the window height, especially at higher DPI/scaling —
    without this, controls below the fold (like the Generate button)
    become unreachable with no way to get to them.
    """

    def __init__(self, parent, style="Card.TFrame", **kwargs):
        super().__init__(parent, style=style, **kwargs)

        canvas_bg = "#ffffff"
        self.canvas = tk.Canvas(self, bg=canvas_bg, highlightthickness=0, bd=0)
        self.vscroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vscroll.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.vscroll.pack(side="right", fill="y")

        self.body = ttk.Frame(self.canvas, style=style)
        self._window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_body_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)

    def _bind_wheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_wheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
