"""Small reusable modal dialogs."""
import tkinter as tk
from tkinter import ttk

from app.ui import theme


class SimpleTextDialog(tk.Toplevel):
    """Single-line text entry dialog. Sets self.result on OK, None on cancel."""

    def __init__(self, parent, title, label, initial=""):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=theme.CARD_BG)
        self.resizable(False, False)
        self.result = None
        self.transient(parent)

        frm = ttk.Frame(self, padding=16, style="Card.TFrame")
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=label, style="Card.TLabel").pack(anchor="w", pady=(0, 6))
        self.var = tk.StringVar(value=initial)
        entry = ttk.Entry(frm, textvariable=self.var, width=42)
        entry.pack(fill="x")
        entry.focus_set()
        entry.select_range(0, tk.END)

        btns = ttk.Frame(frm, style="Card.TFrame")
        btns.pack(fill="x", pady=(14, 0))
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="right")
        ttk.Button(btns, text="Save", style="Accent.TButton", command=self._ok).pack(
            side="right", padx=(0, 8)
        )

        entry.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())
        self.grab_set()
        self.wait_window(self)

    def _ok(self):
        val = self.var.get().strip()
        if val:
            self.result = val
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


def confirm(parent, title, message) -> bool:
    from tkinter import messagebox
    return messagebox.askyesno(title, message, parent=parent)


def info(parent, title, message):
    from tkinter import messagebox
    messagebox.showinfo(title, message, parent=parent)


def error(parent, title, message):
    from tkinter import messagebox
    messagebox.showerror(title, message, parent=parent)


def warn(parent, title, message):
    from tkinter import messagebox
    return messagebox.askyesno(title, message, parent=parent, icon="warning")
