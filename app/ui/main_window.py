import tkinter as tk
from tkinter import ttk

from app.data_manager import DataManager
from app.ui import theme
from app.ui.course_tab import CourseTab
from app.ui.format_tab import FormatTab
from app.ui.question_bank_tab import QuestionBankTab
from app.ui.randomizer_tab import RandomizerTab


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DTTC/KZJ Question Paper Generator")
        self.geometry("1180x760")
        self.minsize(1000, 640)

        theme.apply_theme(self)
        self.configure(bg=theme.BG)

        self.dm = DataManager()

        self._build_header()
        self._build_tabs()

    def _build_header(self):
        header = tk.Frame(self, bg=theme.NAVY)
        header.pack(fill="x")
        inner = tk.Frame(header, bg=theme.NAVY)
        inner.pack(fill="x", padx=20, pady=14)

        title = ttk.Label(
            inner, text="Diesel Traction Training Centre, Kazipet (DTTC/KZJ)", style="Header.TLabel"
        )
        title.pack(anchor="w")
        subtitle = ttk.Label(
            inner, text="South Central Railway — Question Paper Generator", style="SubHeader.TLabel"
        )
        subtitle.pack(anchor="w")

    def _build_tabs(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=14, pady=14)

        self.randomizer_tab = RandomizerTab(nb, self.dm)
        self.question_bank_tab = QuestionBankTab(nb, self.dm, on_change=self._on_bank_change)
        self.format_tab = FormatTab(nb, self.dm, on_change=self._on_format_change)
        self.course_tab = CourseTab(nb, self.dm, on_change=self._on_course_change)

        nb.add(self.randomizer_tab, text="  Randomizer  ")
        nb.add(self.question_bank_tab, text="  Question Bank  ")
        nb.add(self.format_tab, text="  Exam Format Types  ")
        nb.add(self.course_tab, text="  Course List  ")

    def _on_bank_change(self):
        self.randomizer_tab.refresh_choices()

    def _on_format_change(self):
        self.randomizer_tab.refresh_choices()

    def _on_course_change(self):
        self.randomizer_tab.refresh_choices()


def run():
    app = MainWindow()
    app.mainloop()
