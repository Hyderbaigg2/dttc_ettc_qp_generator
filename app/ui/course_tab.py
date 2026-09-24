import tkinter as tk
from tkinter import filedialog, ttk

from app import csv_io
from app.ui import dialogs, theme


class CourseTab(ttk.Frame):
    def __init__(self, parent, dm, on_change=None):
        super().__init__(parent, padding=16)
        self.dm = dm
        self.on_change = on_change
        self._build()
        self.refresh()

    def _build(self):
        ttk.Label(self, text="Course List", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            self,
            text="Add, rename or remove the courses offered by the centre. These appear in the Randomizer's Course dropdown.",
            style="Muted.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(2, 12))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="+ Add Course", style="Accent.TButton", command=self._add).pack(side="left")
        ttk.Button(toolbar, text="Edit", command=self._edit).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Delete", command=self._delete).pack(side="left")
        ttk.Button(toolbar, text="Import CSV/Excel", command=self._import).pack(side="right")
        ttk.Button(toolbar, text="Export CSV/Excel", command=self._export).pack(side="right", padx=6)

        table_frame = ttk.Frame(self, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table_frame, columns=("id", "name"), show="headings", height=16)
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Course Name")
        self.tree.column("id", width=80, anchor="w")
        self.tree.column("name", width=600, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", lambda e: self._edit())

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for c in self.dm.courses():
            self.tree.insert("", "end", iid=c["id"], values=(c["id"], c["name"]))
        if self.on_change:
            self.on_change()

    def _selected_id(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _add(self):
        dlg = dialogs.SimpleTextDialog(self, "Add Course", "Course name:")
        if dlg.result:
            self.dm.add_course(dlg.result)
            self.refresh()

    def _edit(self):
        cid = self._selected_id()
        if not cid:
            return
        course = next(c for c in self.dm.courses() if c["id"] == cid)
        dlg = dialogs.SimpleTextDialog(self, "Edit Course", "Course name:", course["name"])
        if dlg.result:
            self.dm.update_course(cid, dlg.result)
            self.refresh()

    def _delete(self):
        cid = self._selected_id()
        if not cid:
            return
        course = next(c for c in self.dm.courses() if c["id"] == cid)
        if dialogs.confirm(self, "Delete Course", f"Delete course '{course['name']}'?"):
            self.dm.delete_course(cid)
            self.refresh()

    def _export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")],
            initialfile="courses.xlsx",
        )
        if not path:
            return
        csv_io.export_courses(self.dm.courses(), path)
        dialogs.info(self, "Export Complete", f"Courses exported to:\n{path}")

    def _import(self):
        path = filedialog.askopenfilename(filetypes=[("Excel/CSV", "*.xlsx *.csv"), ("All files", "*.*")])
        if not path:
            return
        names = csv_io.import_courses(path)
        for n in names:
            self.dm.add_course(n)
        self.refresh()
        dialogs.info(self, "Import Complete", f"Imported {len(names)} course(s).")
