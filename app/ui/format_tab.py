import tkinter as tk
from tkinter import ttk

from app.data_manager import DataManager
from app.ui import dialogs, theme

SECTION_TYPE_LABELS = {"descriptive": "Descriptive", "fill_blank": "Fill in the Blanks", "mcq": "MCQ"}
SECTION_TYPE_BY_LABEL = {v: k for k, v in SECTION_TYPE_LABELS.items()}


class SectionRowDialog(tk.Toplevel):
    def __init__(self, parent, existing: dict = None):
        super().__init__(parent)
        self.title("Edit Section" if existing else "Add Section")
        self.configure(bg=theme.CARD_BG)
        self.resizable(False, False)
        self.result = None
        self.transient(parent)

        frm = ttk.Frame(self, padding=18, style="Card.TFrame")
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Question Type:", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=6)
        self.type_var = tk.StringVar(
            value=SECTION_TYPE_LABELS[existing["type"]] if existing else "MCQ"
        )
        ttk.Combobox(
            frm, textvariable=self.type_var, values=list(SECTION_TYPE_LABELS.values()), state="readonly", width=22
        ).grid(row=0, column=1, sticky="w", padx=(10, 0))

        ttk.Label(frm, text="Number of Questions:", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=6)
        self.count_var = tk.IntVar(value=existing["display_count"] if existing else 10)
        ttk.Spinbox(frm, from_=1, to=200, textvariable=self.count_var, width=8).grid(
            row=1, column=1, sticky="w", padx=(10, 0)
        )

        ttk.Label(frm, text="Marks per Question:", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        self.marks_var = tk.DoubleVar(value=existing["marks_each"] if existing else 1)
        ttk.Spinbox(frm, from_=0.5, to=50, increment=0.5, textvariable=self.marks_var, width=8).grid(
            row=2, column=1, sticky="w", padx=(10, 0)
        )

        ttk.Label(frm, text="Choice to Leave (optional):", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=6)
        self.leave_var = tk.IntVar(value=existing.get("choice_leave", 0) if existing else 0)
        ttk.Spinbox(frm, from_=0, to=100, textvariable=self.leave_var, width=8).grid(
            row=3, column=1, sticky="w", padx=(10, 0)
        )
        ttk.Label(
            frm,
            text="e.g. show 6, answer any 4 -> Choice to Leave = 2",
            style="CardMuted.TLabel",
        ).grid(row=4, column=0, columnspan=2, sticky="w")

        btns = ttk.Frame(frm, style="Card.TFrame")
        btns.grid(row=5, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="right")
        ttk.Button(btns, text="Save", style="Accent.TButton", command=self._save).pack(side="right", padx=(0, 8))

        self.grab_set()
        self.wait_window(self)

    def _cancel(self):
        self.result = None
        self.destroy()

    def _save(self):
        if self.leave_var.get() >= self.count_var.get():
            dialogs.error(self, "Invalid Choice", "Choice to leave must be less than the number of questions shown.")
            return
        self.result = {
            "type": SECTION_TYPE_BY_LABEL[self.type_var.get()],
            "display_count": int(self.count_var.get()),
            "marks_each": float(self.marks_var.get()),
            "choice_leave": int(self.leave_var.get()),
        }
        self.destroy()


class FormatEditorDialog(tk.Toplevel):
    def __init__(self, parent, dm, existing: dict = None):
        super().__init__(parent)
        self.dm = dm
        self.existing = existing
        self.title("Edit Exam Format" if existing else "New Exam Format")
        self.configure(bg=theme.CARD_BG)
        self.resizable(False, False)
        self.result = None
        self.transient(parent)
        self.sections = [dict(s) for s in existing["sections"]] if existing else []

        frm = ttk.Frame(self, padding=18, style="Card.TFrame")
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Format Name:", style="Card.TLabel").pack(anchor="w")
        self.name_var = tk.StringVar(value=existing["name"] if existing else "")
        ttk.Entry(frm, textvariable=self.name_var, width=60).pack(fill="x", pady=(4, 10))

        ttk.Label(frm, text="Description (shown on the paper header, optional):", style="Card.TLabel").pack(anchor="w")
        self.desc_var = tk.StringVar(value=existing.get("description", "") if existing else "")
        ttk.Entry(frm, textvariable=self.desc_var, width=60).pack(fill="x", pady=(4, 10))

        ttk.Label(frm, text="Sections:", style="Card.TLabel").pack(anchor="w", pady=(4, 4))
        table_frame = ttk.Frame(frm, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True)
        cols = ("type", "count", "marks_each", "leave", "answer_count", "section_marks")
        headings = {
            "type": "Type", "count": "Shown", "marks_each": "Marks Each",
            "leave": "Choice to Leave", "answer_count": "Answered", "section_marks": "Section Marks",
        }
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=6)
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=110, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", lambda e: self._edit_section())

        sec_btns = ttk.Frame(frm, style="Card.TFrame")
        sec_btns.pack(fill="x", pady=(8, 0))
        ttk.Button(sec_btns, text="+ Add Section", command=self._add_section).pack(side="left")
        ttk.Button(sec_btns, text="Edit Section", command=self._edit_section).pack(side="left", padx=6)
        ttk.Button(sec_btns, text="Remove Section", command=self._remove_section).pack(side="left")

        self.total_label = ttk.Label(frm, text="", style="Card.TLabel", font=(theme.FONT_FAMILY, 11, "bold"))
        self.total_label.pack(anchor="e", pady=(10, 0))

        btns = ttk.Frame(frm, style="Card.TFrame")
        btns.pack(fill="x", pady=(14, 0))
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="right")
        ttk.Button(btns, text="Save Format", style="Accent.TButton", command=self._save).pack(side="right", padx=(0, 8))

        self._refresh_sections()
        self.grab_set()
        self.wait_window(self)

    def _refresh_sections(self):
        self.tree.delete(*self.tree.get_children())
        total = 0
        for i, sec in enumerate(self.sections):
            answer_count = sec["display_count"] - sec.get("choice_leave", 0)
            section_marks = answer_count * sec["marks_each"]
            total += section_marks
            self.tree.insert(
                "", "end", iid=str(i),
                values=(
                    SECTION_TYPE_LABELS[sec["type"]], sec["display_count"], sec["marks_each"],
                    sec.get("choice_leave", 0), answer_count, section_marks,
                ),
            )
        self.total_label.configure(text=f"Total Marks: {total:g}")

    def _add_section(self):
        dlg = SectionRowDialog(self)
        if dlg.result:
            self.sections.append(dlg.result)
            self._refresh_sections()

    def _edit_section(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        dlg = SectionRowDialog(self, self.sections[idx])
        if dlg.result:
            self.sections[idx] = dlg.result
            self._refresh_sections()

    def _remove_section(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        del self.sections[idx]
        self._refresh_sections()

    def _cancel(self):
        self.result = None
        self.destroy()

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            dialogs.error(self, "Missing Name", "Please enter a format name.")
            return
        if not self.sections:
            dialogs.error(self, "No Sections", "Please add at least one section.")
            return
        fmt_id = self.existing["id"] if self.existing else self._next_id()
        self.result = {
            "id": fmt_id,
            "name": name,
            "description": self.desc_var.get().strip(),
            "sections": self.sections,
        }
        self.destroy()

    def _next_id(self):
        existing_ids = {f["id"] for f in self.dm.formats()}
        n = 1
        while f"F{n:02d}" in existing_ids:
            n += 1
        return f"F{n:02d}"


class FormatTab(ttk.Frame):
    def __init__(self, parent, dm: DataManager, on_change=None):
        super().__init__(parent, padding=16)
        self.dm = dm
        self.on_change = on_change
        self._build()
        self.refresh()

    def _build(self):
        ttk.Label(self, text="Exam Format Types", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            self,
            text="Define question-paper formats: how many descriptive / fill-in-the-blank / MCQ questions, "
                 "their marks, and any 'answer any N of M' choice. These appear in the Randomizer's Exam Format dropdown.",
            style="Muted.TLabel",
            wraplength=780,
        ).pack(anchor="w", pady=(2, 12))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="+ New Format", style="Accent.TButton", command=self._add).pack(side="left")
        ttk.Button(toolbar, text="Edit", command=self._edit).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Delete", command=self._delete).pack(side="left")

        table_frame = ttk.Frame(self, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True)
        cols = ("id", "name", "breakdown", "total")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=14)
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Format Name")
        self.tree.heading("breakdown", text="Sections")
        self.tree.heading("total", text="Total Marks")
        self.tree.column("id", width=60, anchor="w")
        self.tree.column("name", width=260, anchor="w")
        self.tree.column("breakdown", width=420, anchor="w")
        self.tree.column("total", width=100, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", lambda e: self._edit())

    def _breakdown_text(self, fmt):
        parts = []
        for sec in fmt["sections"]:
            label = SECTION_TYPE_LABELS[sec["type"]]
            if sec.get("choice_leave"):
                answer_n = sec["display_count"] - sec["choice_leave"]
                parts.append(f"{sec['display_count']} {label} (answer {answer_n}) @ {sec['marks_each']:g}m")
            else:
                parts.append(f"{sec['display_count']} {label} @ {sec['marks_each']:g}m")
        return "; ".join(parts)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for fmt in self.dm.formats():
            total = DataManager.format_total_marks(fmt)
            self.tree.insert(
                "", "end", iid=fmt["id"],
                values=(fmt["id"], fmt["name"], self._breakdown_text(fmt), f"{total:g}"),
            )
        if self.on_change:
            self.on_change()

    def _selected_id(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _add(self):
        dlg = FormatEditorDialog(self, self.dm)
        if dlg.result:
            self.dm.upsert_format(dlg.result)
            self.refresh()

    def _edit(self):
        fid = self._selected_id()
        if not fid:
            return
        fmt = self.dm.get_format(fid)
        dlg = FormatEditorDialog(self, self.dm, fmt)
        if dlg.result:
            self.dm.upsert_format(dlg.result)
            self.refresh()

    def _delete(self):
        fid = self._selected_id()
        if not fid:
            return
        fmt = self.dm.get_format(fid)
        if dialogs.confirm(self, "Delete Format", f"Delete exam format '{fmt['name']}'?"):
            self.dm.delete_format(fid)
            self.refresh()
