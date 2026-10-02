import tkinter as tk
from tkinter import filedialog, ttk

from app import csv_io
from app.data_manager import LEVELS
from app.ui import dialogs, theme
from app.ui.question_form import QuestionFormDialog

TYPE_LABELS = {"mcq": "MCQs", "fill_blank": "Fill in the Blanks", "descriptive": "Descriptive"}


class QuestionListPanel(ttk.Frame):
    def __init__(self, parent, dm, qtype, on_change=None):
        super().__init__(parent, padding=16)
        self.dm = dm
        self.qtype = qtype
        self.on_change = on_change
        self._build()
        self.refresh()

    def _build(self):
        filt = ttk.Frame(self)
        filt.pack(fill="x", pady=(0, 8))
        ttk.Label(filt, text="Topic:").pack(side="left")
        self.topic_filter = tk.StringVar(value="All")
        self.topic_combo = ttk.Combobox(filt, textvariable=self.topic_filter, state="readonly", width=22)
        self.topic_combo.pack(side="left", padx=(4, 14))
        self.topic_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(filt, text="Level:").pack(side="left")
        self.level_filter = tk.StringVar(value="All")
        level_combo = ttk.Combobox(
            filt, textvariable=self.level_filter, values=["All"] + LEVELS, state="readonly", width=12
        )
        level_combo.pack(side="left", padx=(4, 14))
        level_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(filt, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(filt, textvariable=self.search_var, width=28)
        search_entry.pack(side="left", padx=(4, 0))
        search_entry.bind("<KeyRelease>", lambda e: self.refresh())

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="+ Add Question", style="Accent.TButton", command=self._add).pack(side="left")
        ttk.Button(toolbar, text="Edit", command=self._edit).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Delete Selected", command=self._delete).pack(side="left")
        ttk.Button(toolbar, text="Import CSV/Excel", command=self._import).pack(side="right")
        ttk.Button(toolbar, text="Export CSV/Excel", command=self._export).pack(side="right", padx=6)
        self.count_label = ttk.Label(toolbar, text="", style="Muted.TLabel")
        self.count_label.pack(side="right", padx=12)

        table_frame = ttk.Frame(self, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True)

        if self.qtype == "mcq":
            cols = ("id", "text", "correct", "topic", "level")
            headings = {"id": "ID", "text": "Question", "correct": "Correct Option", "topic": "Topic", "level": "Level"}
            widths = {"id": 80, "text": 420, "correct": 140, "topic": 140, "level": 80}
        elif self.qtype == "fill_blank":
            cols = ("id", "text", "answer", "topic", "level")
            headings = {"id": "ID", "text": "Question", "answer": "Answer", "topic": "Topic", "level": "Level"}
            widths = {"id": 80, "text": 440, "answer": 160, "topic": 140, "level": 80}
        else:
            cols = ("id", "text", "topic", "level")
            headings = {"id": "ID", "text": "Question", "topic": "Topic", "level": "Level"}
            widths = {"id": 80, "text": 560, "topic": 160, "level": 80}

        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=16)
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", lambda e: self._edit())
        self.tree.bind("<Control-a>", self._select_all)

    def _filtered(self):
        qs = self.dm.questions(self.qtype)
        topic = self.topic_filter.get()
        level = self.level_filter.get()
        search = self.search_var.get().strip().lower()
        out = []
        for q in qs:
            if topic != "All" and q.get("topic") != topic:
                continue
            if level != "All" and q.get("level") != level:
                continue
            if search and search not in q["text"].lower() and search not in q["id"].lower():
                continue
            out.append(q)
        return out

    def refresh(self):
        self.topic_combo["values"] = ["All"] + self.dm.topic_names()
        self.tree.delete(*self.tree.get_children())
        for q in self._filtered():
            text_preview = q["text"] if len(q["text"]) <= 90 else q["text"][:87] + "..."
            if self.qtype == "mcq":
                vals = (q["id"], text_preview, q.get("correct_option", ""), q.get("topic", ""), q.get("level", ""))
            elif self.qtype == "fill_blank":
                vals = (q["id"], text_preview, q.get("answer", ""), q.get("topic", ""), q.get("level", ""))
            else:
                vals = (q["id"], text_preview, q.get("topic", ""), q.get("level", ""))
            self.tree.insert("", "end", iid=q["id"], values=vals)
        total = len(self.dm.questions(self.qtype))
        self.count_label.configure(text=f"{len(self._filtered())} shown / {total} total")
        if self.on_change:
            self.on_change()

    def _selected_id(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _add(self):
        if not self.dm.topic_names():
            dialogs.error(self, "No topics yet", "Please add at least one Question Topic first (Question Bank > Topics tab).")
            return
        dlg = QuestionFormDialog(self, self.dm, self.qtype)
        if dlg.result:
            self.dm.add_question(self.qtype, dlg.result)
            self.refresh()

    def _edit(self):
        qid = self._selected_id()
        if not qid:
            return
        existing = self.dm.find_question(self.qtype, qid)
        dlg = QuestionFormDialog(self, self.dm, self.qtype, existing)
        if dlg.result:
            self.dm.update_question(self.qtype, qid, dlg.result)
            self.refresh()

    def _delete(self):
        qids = list(self.tree.selection())
        if not qids:
            dialogs.info(self, "Nothing Selected", "Select one or more questions first (Ctrl/Shift+click, or Ctrl+A for all shown).")
            return
        if len(qids) == 1:
            msg = f"Delete question {qids[0]}? This cannot be undone."
        else:
            msg = f"Delete {len(qids)} selected questions? This cannot be undone."
        if dialogs.confirm(self, "Delete Questions", msg):
            self.dm.delete_questions(self.qtype, qids)
            self.refresh()

    def _select_all(self, event=None):
        self.tree.selection_set(self.tree.get_children())
        return "break"

    def _export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")],
            initialfile=f"{self.qtype}_questions.xlsx",
        )
        if not path:
            return
        csv_io.export_questions(self.qtype, self.dm.questions(self.qtype), path)
        dialogs.info(self, "Export Complete", f"Exported to:\n{path}")

    def _import(self):
        path = filedialog.askopenfilename(filetypes=[("Excel/CSV", "*.xlsx *.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            rows = csv_io.import_questions(self.qtype, path)
        except Exception as e:
            dialogs.error(self, "Import Failed", str(e))
            return
        added, skipped = 0, 0
        known_topics = set(self.dm.topic_names())
        for fields in rows:
            if not fields.get("text") or not fields.get("topic"):
                skipped += 1
                continue
            if fields["topic"] not in known_topics:
                self.dm.add_topic(fields["topic"])
                known_topics.add(fields["topic"])
            self.dm.add_question(self.qtype, fields)
            added += 1
        self.refresh()
        msg = f"Imported {added} question(s)."
        if skipped:
            msg += f" Skipped {skipped} row(s) missing text/topic."
        dialogs.info(self, "Import Complete", msg)


class TopicsPanel(ttk.Frame):
    def __init__(self, parent, dm, on_change=None):
        super().__init__(parent, padding=16)
        self.dm = dm
        self.on_change = on_change
        self._build()
        self.refresh()

    def _build(self):
        ttk.Label(
            self,
            text="Question Topics used to tag and filter MCQ / Fill-in-the-Blank / Descriptive questions.",
            style="Muted.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(0, 12))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="+ Add Topic", style="Accent.TButton", command=self._add).pack(side="left")
        ttk.Button(toolbar, text="Rename", command=self._edit).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Delete", command=self._delete).pack(side="left")
        ttk.Button(toolbar, text="Import CSV/Excel", command=self._import).pack(side="right")
        ttk.Button(toolbar, text="Export CSV/Excel", command=self._export).pack(side="right", padx=6)

        table_frame = ttk.Frame(self, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table_frame, columns=("id", "name", "usage"), show="headings", height=14)
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Topic Name")
        self.tree.heading("usage", text="Questions Using It")
        self.tree.column("id", width=80)
        self.tree.column("name", width=400, anchor="w")
        self.tree.column("usage", width=160, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", lambda e: self._edit())

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for t in self.dm.topics():
            usage = self.dm.topic_in_use(t["name"])
            self.tree.insert("", "end", iid=t["id"], values=(t["id"], t["name"], usage))
        if self.on_change:
            self.on_change()

    def _selected_id(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _add(self):
        dlg = dialogs.SimpleTextDialog(self, "Add Topic", "Topic name:")
        if dlg.result:
            self.dm.add_topic(dlg.result)
            self.refresh()

    def _edit(self):
        tid = self._selected_id()
        if not tid:
            return
        topic = next(t for t in self.dm.topics() if t["id"] == tid)
        dlg = dialogs.SimpleTextDialog(self, "Rename Topic", "Topic name:", topic["name"])
        if dlg.result:
            self.dm.update_topic(tid, dlg.result)
            self.refresh()

    def _delete(self):
        tid = self._selected_id()
        if not tid:
            return
        topic = next(t for t in self.dm.topics() if t["id"] == tid)
        usage = self.dm.topic_in_use(topic["name"])
        msg = f"Delete topic '{topic['name']}'?"
        if usage:
            msg += f"\n\n{usage} question(s) currently use this topic and will keep the old topic name as free text."
        if dialogs.confirm(self, "Delete Topic", msg):
            self.dm.delete_topic(tid)
            self.refresh()

    def _export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")], initialfile="topics.xlsx"
        )
        if not path:
            return
        csv_io.export_topics(self.dm.topics(), path)
        dialogs.info(self, "Export Complete", f"Topics exported to:\n{path}")

    def _import(self):
        path = filedialog.askopenfilename(filetypes=[("Excel/CSV", "*.xlsx *.csv"), ("All files", "*.*")])
        if not path:
            return
        names = csv_io.import_topics(path)
        for n in names:
            self.dm.add_topic(n)
        self.refresh()
        dialogs.info(self, "Import Complete", f"Imported {len(names)} topic(s).")


class QuestionBankTab(ttk.Frame):
    def __init__(self, parent, dm, on_change=None):
        super().__init__(parent, padding=16)
        self.dm = dm
        self.on_change = on_change

        ttk.Label(self, text="Question Bank", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            self,
            text="Manage descriptive, fill-in-the-blank and MCQ questions, and the topics used to tag them.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 12))

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.mcq_panel = QuestionListPanel(nb, dm, "mcq", on_change=self._changed)
        self.fib_panel = QuestionListPanel(nb, dm, "fill_blank", on_change=self._changed)
        self.des_panel = QuestionListPanel(nb, dm, "descriptive", on_change=self._changed)
        self.topics_panel = TopicsPanel(nb, dm, on_change=self._topics_changed)

        nb.add(self.mcq_panel, text="MCQs")
        nb.add(self.fib_panel, text="Fill in the Blanks")
        nb.add(self.des_panel, text="Descriptive")
        nb.add(self.topics_panel, text="Topics")

    def _changed(self):
        if self.on_change:
            self.on_change()

    def _topics_changed(self):
        self.mcq_panel.refresh()
        self.fib_panel.refresh()
        self.des_panel.refresh()
        if self.on_change:
            self.on_change()

    def refresh_all(self):
        self.mcq_panel.refresh()
        self.fib_panel.refresh()
        self.des_panel.refresh()
        self.topics_panel.refresh()
