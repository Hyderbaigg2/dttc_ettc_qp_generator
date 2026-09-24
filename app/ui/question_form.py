import tkinter as tk
from tkinter import ttk

from app.data_manager import LEVELS
from app.ui import theme


class QuestionFormDialog(tk.Toplevel):
    """Add/Edit dialog whose fields depend on qtype. Sets self.result dict or None."""

    def __init__(self, parent, dm, qtype: str, existing: dict = None):
        super().__init__(parent)
        self.dm = dm
        self.qtype = qtype
        self.existing = existing
        self.result = None

        titles = {"mcq": "MCQ Question", "fill_blank": "Fill in the Blanks Question", "descriptive": "Descriptive Question"}
        self.title(("Edit " if existing else "Add ") + titles[qtype])
        self.configure(bg=theme.CARD_BG)
        self.resizable(False, False)
        self.transient(parent)

        self.frm = ttk.Frame(self, padding=18, style="Card.TFrame")
        self.frm.pack(fill="both", expand=True)

        self._build_common_top()
        if qtype == "mcq":
            self._build_mcq_fields()
        elif qtype == "fill_blank":
            self._build_fib_fields()
        else:
            self._build_descriptive_fields()
        self._build_topic_level_row()
        self._build_buttons()

        self.grab_set()
        self.wait_window(self)

    def _row(self, label_text):
        row = ttk.Frame(self.frm, style="Card.TFrame")
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text=label_text, style="Card.TLabel").pack(anchor="w")
        return row

    def _build_common_top(self):
        row = self._row("Question text:")
        self.text_widget = tk.Text(row, width=70, height=4, wrap="word", font=(theme.FONT_FAMILY, 10))
        self.text_widget.pack(fill="x", pady=(4, 0))
        if self.existing:
            self.text_widget.insert("1.0", self.existing.get("text", ""))

    def _build_mcq_fields(self):
        self.option_vars = []
        opts_row = ttk.Frame(self.frm, style="Card.TFrame")
        opts_row.pack(fill="x", pady=(0, 10))
        ttk.Label(opts_row, text="Options:", style="Card.TLabel").grid(row=0, column=0, sticky="w", columnspan=2)
        existing_opts = self.existing.get("options", ["", "", "", ""]) if self.existing else ["", "", "", ""]
        existing_opts = (existing_opts + ["", "", "", ""])[:4]
        for i in range(4):
            var = tk.StringVar(value=existing_opts[i])
            self.option_vars.append(var)
            ttk.Label(opts_row, text=f"Option {chr(65+i)}:", style="Card.TLabel").grid(
                row=i + 1, column=0, sticky="w", pady=3
            )
            ttk.Entry(opts_row, textvariable=var, width=55).grid(row=i + 1, column=1, sticky="w", padx=(8, 0))

        row = self._row("Correct option:")
        self.correct_var = tk.StringVar(value=self.existing.get("correct_option", "") if self.existing else "")
        self.correct_combo = ttk.Combobox(row, textvariable=self.correct_var, state="readonly", width=54)
        self.correct_combo.pack(fill="x", pady=(4, 0))
        self._refresh_correct_options()
        for v in self.option_vars:
            v.trace_add("write", lambda *a: self._refresh_correct_options())

    def _refresh_correct_options(self):
        opts = [v.get() for v in self.option_vars if v.get().strip()]
        current = self.correct_var.get()
        self.correct_combo["values"] = opts
        if current not in opts:
            self.correct_var.set(opts[0] if opts else "")

    def _build_fib_fields(self):
        row = self._row("Answer:")
        self.answer_var = tk.StringVar(value=self.existing.get("answer", "") if self.existing else "")
        ttk.Entry(row, textvariable=self.answer_var, width=70).pack(fill="x", pady=(4, 0))

    def _build_descriptive_fields(self):
        pass

    def _build_topic_level_row(self):
        row = ttk.Frame(self.frm, style="Card.TFrame")
        row.pack(fill="x", pady=(0, 10))

        left = ttk.Frame(row, style="Card.TFrame")
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="Topic:", style="Card.TLabel").pack(anchor="w")
        self.topic_var = tk.StringVar(value=self.existing.get("topic", "") if self.existing else "")
        topics = self.dm.topic_names()
        combo = ttk.Combobox(left, textvariable=self.topic_var, values=topics, state="readonly", width=30)
        combo.pack(anchor="w", pady=(4, 0))
        if not self.topic_var.get() and topics:
            self.topic_var.set(topics[0])

        right = ttk.Frame(row, style="Card.TFrame")
        right.pack(side="left", fill="x", expand=True, padx=(20, 0))
        ttk.Label(right, text="Hardness Level:", style="Card.TLabel").pack(anchor="w")
        self.level_var = tk.StringVar(value=self.existing.get("level", "") if self.existing else LEVELS[0])
        ttk.Combobox(right, textvariable=self.level_var, values=LEVELS, state="readonly", width=20).pack(
            anchor="w", pady=(4, 0)
        )

    def _build_buttons(self):
        btns = ttk.Frame(self.frm, style="Card.TFrame")
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="right")
        ttk.Button(btns, text="Save", style="Accent.TButton", command=self._save).pack(side="right", padx=(0, 8))

    def _cancel(self):
        self.result = None
        self.destroy()

    def _save(self):
        from app.ui import dialogs

        text = self.text_widget.get("1.0", "end").strip()
        if not text:
            dialogs.error(self, "Missing text", "Question text is required.")
            return
        if not self.topic_var.get():
            dialogs.error(self, "Missing topic", "Please select a topic (add one in the Topics tab first).")
            return

        fields = {"text": text, "topic": self.topic_var.get(), "level": self.level_var.get()}

        if self.qtype == "mcq":
            opts = [v.get().strip() for v in self.option_vars if v.get().strip()]
            if len(opts) < 2:
                dialogs.error(self, "Missing options", "Please enter at least 2 options.")
                return
            if not self.correct_var.get():
                dialogs.error(self, "Missing answer", "Please choose the correct option.")
                return
            fields["options"] = opts
            fields["correct_option"] = self.correct_var.get()
        elif self.qtype == "fill_blank":
            if not self.answer_var.get().strip():
                dialogs.error(self, "Missing answer", "Please enter the answer.")
                return
            fields["answer"] = self.answer_var.get().strip()

        self.result = fields
        self.destroy()
