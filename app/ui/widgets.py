"""Small reusable widgets."""
import calendar
import tkinter as tk
from datetime import date
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


class DatePicker(ttk.Frame):
    """Read-only date field with a calendar popup. get() returns DD-MM-YYYY."""

    def __init__(self, parent, initial=None):
        super().__init__(parent, style="Card.TFrame")
        self.value = initial or date.today()
        self.var = tk.StringVar(value=self._fmt(self.value))
        entry = ttk.Entry(self, textvariable=self.var, width=14, state="readonly")
        entry.pack(side="left")
        ttk.Button(self, text="Pick date", command=self._open).pack(side="left", padx=(6, 0))
        entry.bind("<Button-1>", lambda e: self._open())

    @staticmethod
    def _fmt(d):
        return d.strftime("%d-%m-%Y")

    def get(self) -> str:
        return self.var.get()

    def _open(self):
        popup = tk.Toplevel(self)
        popup.title("Select Date")
        popup.resizable(False, False)
        popup.transient(self.winfo_toplevel())
        popup.configure(bg="#ffffff")
        popup.geometry(f"+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height() + 4}")

        view = {"y": self.value.year, "m": self.value.month}
        header = ttk.Frame(popup, style="Card.TFrame", padding=(8, 8, 8, 0))
        header.pack(fill="x")
        title = ttk.Label(header, style="Card.TLabel", font=("Segoe UI", 10, "bold"), anchor="center")
        grid = ttk.Frame(popup, style="Card.TFrame", padding=8)
        grid.pack()

        def shift(delta):
            m = view["m"] - 1 + delta
            view["y"] += m // 12
            view["m"] = m % 12 + 1
            draw()

        def choose(day):
            self.value = date(view["y"], view["m"], day)
            self.var.set(self._fmt(self.value))
            popup.destroy()

        def draw():
            for w in grid.winfo_children():
                w.destroy()
            title.configure(text=f"{calendar.month_name[view['m']]} {view['y']}")
            for c, name in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
                ttk.Label(grid, text=name, style="Card.TLabel", width=4, anchor="center").grid(row=0, column=c)
            for r, week in enumerate(calendar.monthcalendar(view["y"], view["m"]), start=1):
                for c, day in enumerate(week):
                    if not day:
                        continue
                    is_sel = (view["y"], view["m"], day) == (self.value.year, self.value.month, self.value.day)
                    tk.Button(
                        grid, text=str(day), width=4, relief="flat", bd=0, pady=3,
                        bg="#1f3a5f" if is_sel else "#ffffff", fg="#ffffff" if is_sel else "#1c1c1c",
                        activebackground="#c8a951", command=lambda d=day: choose(d),
                    ).grid(row=r, column=c, padx=1, pady=1)

        ttk.Button(header, text="<<", width=3, command=lambda: shift(-12)).pack(side="left")
        ttk.Button(header, text="<", width=3, command=lambda: shift(-1)).pack(side="left", padx=(2, 0))
        ttk.Button(header, text=">>", width=3, command=lambda: shift(12)).pack(side="right")
        ttk.Button(header, text=">", width=3, command=lambda: shift(1)).pack(side="right", padx=(0, 2))
        title.pack(side="left", fill="x", expand=True)
        draw()
        popup.bind("<Escape>", lambda e: popup.destroy())
        popup.grab_set()


class DurationPicker(ttk.Frame):
    """Hours + minutes dropdowns. text() returns e.g. '1 Hr 30 Min' ('' if 0:00)."""

    def __init__(self, parent, hours=1, minutes=0):
        super().__init__(parent, style="Card.TFrame")
        self.hours_var = tk.StringVar(value=str(hours))
        self.minutes_var = tk.StringVar(value=f"{minutes:02d}")
        ttk.Combobox(self, textvariable=self.hours_var, values=[str(h) for h in range(0, 9)],
                     state="readonly", width=3).pack(side="left")
        ttk.Label(self, text="Hours", style="Card.TLabel").pack(side="left", padx=(4, 12))
        ttk.Combobox(self, textvariable=self.minutes_var, values=[f"{m:02d}" for m in range(0, 60, 5)],
                     state="readonly", width=3).pack(side="left")
        ttk.Label(self, text="Minutes", style="Card.TLabel").pack(side="left", padx=(4, 0))

    def text(self) -> str:
        h, m = int(self.hours_var.get()), int(self.minutes_var.get())
        parts = []
        if h:
            parts.append(f"{h} Hr" if h == 1 else f"{h} Hrs")
        if m:
            parts.append(f"{m} Min")
        return " ".join(parts)
