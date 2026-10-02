import os
import subprocess
import sys

import tkinter as tk
from tkinter import filedialog, ttk

from app import docx_export, pdf_export
from app.generator import InsufficientQuestionsError, generate_sets
from app.paths import output_dir
from app.ui import dialogs, theme
from app.ui.widgets import DatePicker, DurationPicker, ScrollableFrame

SET_LABELS = ["A", "B", "C"]
RANDOMNESS_HELP = {
    "Low": "All sets use the same questions, reshuffled in order (and MCQ options reshuffled). Good for controlled retests.",
    "Medium": "Each set keeps roughly half of the previous set's questions and swaps in fresh ones where the bank allows.",
    "High": "The sets try to use different questions from each other as much as the question bank allows.",
}


class RandomizerTab(ttk.Frame):
    def __init__(self, parent, dm):
        super().__init__(parent, padding=16)
        self.dm = dm
        self.topic_vars = {}
        self.last_output_dir = None
        self._build()
        self.refresh_choices()

    def _build(self):
        ttk.Label(self, text="Randomizer — Generate Question Papers", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            self,
            text="Choose the parameters below, then generate 1, 2 or 3 randomised sets of the selected exam format.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 14))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left_scroll = ScrollableFrame(body)
        left_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left = ttk.Frame(left_scroll.body, style="Card.TFrame", padding=18)
        left.pack(fill="both", expand=True)

        right = ttk.Frame(body, style="Card.TFrame", padding=18)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._build_form(left)
        self._build_output_panel(right)

    def _field(self, parent, label):
        ttk.Label(parent, text=label, style="Card.TLabel", font=(theme.FONT_FAMILY, 10, "bold")).pack(
            anchor="w", pady=(12, 2)
        )

    def _build_form(self, parent):
        when_row = ttk.Frame(parent, style="Card.TFrame")
        when_row.pack(fill="x")
        date_col = ttk.Frame(when_row, style="Card.TFrame")
        date_col.pack(side="left")
        ttk.Label(date_col, text="Date", style="Card.TLabel", font=(theme.FONT_FAMILY, 10, "bold")).pack(anchor="w", pady=(12, 2))
        self.date_picker = DatePicker(date_col)
        self.date_picker.pack(anchor="w")
        dur_col = ttk.Frame(when_row, style="Card.TFrame")
        dur_col.pack(side="left", padx=(28, 0))
        ttk.Label(dur_col, text="Exam Duration", style="Card.TLabel", font=(theme.FONT_FAMILY, 10, "bold")).pack(anchor="w", pady=(12, 2))
        self.duration_picker = DurationPicker(dur_col)
        self.duration_picker.pack(anchor="w")

        self._field(parent, "Course Name")
        self.course_var = tk.StringVar()
        self.course_combo = ttk.Combobox(parent, textvariable=self.course_var, state="readonly", width=48)
        self.course_combo.pack(anchor="w", fill="x")

        self._field(parent, "Exam Format")
        self.format_var = tk.StringVar()
        self.format_combo = ttk.Combobox(parent, textvariable=self.format_var, state="readonly", width=48)
        self.format_combo.pack(anchor="w", fill="x")
        self.format_combo.bind("<<ComboboxSelected>>", lambda e: self._update_format_desc())
        self.format_desc_label = ttk.Label(parent, text="", style="CardMuted.TLabel", wraplength=380)
        self.format_desc_label.pack(anchor="w", pady=(4, 0))

        two_col = ttk.Frame(parent, style="Card.TFrame")
        two_col.pack(fill="x", pady=(12, 0))

        left = ttk.Frame(two_col, style="Card.TFrame")
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="Hardness Level", style="Card.TLabel", font=(theme.FONT_FAMILY, 10, "bold")).pack(anchor="w")
        self.level_var = tk.StringVar(value="Mixed (All Levels)")
        ttk.Combobox(
            left, textvariable=self.level_var,
            values=["Mixed (All Levels)", "Easy", "Medium", "Hard"], state="readonly", width=22,
        ).pack(anchor="w", pady=(2, 0))

        right = ttk.Frame(two_col, style="Card.TFrame")
        right.pack(side="left", fill="x", expand=True, padx=(20, 0))
        ttk.Label(right, text="Randomness Level", style="Card.TLabel", font=(theme.FONT_FAMILY, 10, "bold")).pack(anchor="w")
        self.randomness_var = tk.StringVar(value="High")
        rand_combo = ttk.Combobox(
            right, textvariable=self.randomness_var, values=["Low", "Medium", "High"], state="readonly", width=22
        )
        rand_combo.pack(anchor="w", pady=(2, 0))
        rand_combo.bind("<<ComboboxSelected>>", lambda e: self._update_randomness_help())
        self.randomness_help = ttk.Label(parent, text="", style="CardMuted.TLabel", wraplength=380)
        self.randomness_help.pack(anchor="w", pady=(4, 0))

        self._field(parent, "Question Topics to Include")
        topics_outer = ttk.Frame(parent, style="Card.TFrame")
        topics_outer.pack(fill="x")
        btn_row = ttk.Frame(topics_outer, style="Card.TFrame")
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Select All", command=lambda: self._set_all_topics(True)).pack(side="left")
        ttk.Button(btn_row, text="Clear All", command=lambda: self._set_all_topics(False)).pack(side="left", padx=6)

        self.topics_frame = ttk.Frame(topics_outer, style="Card.TFrame")
        self.topics_frame.pack(fill="x", pady=(6, 0))

        self._field(parent, "Sets Required")
        sets_row = ttk.Frame(parent, style="Card.TFrame")
        sets_row.pack(anchor="w")
        self.num_sets_var = tk.IntVar(value=3)
        for n in (1, 2, 3):
            ttk.Radiobutton(
                sets_row, text=str(n), value=n, variable=self.num_sets_var, style="Card.TRadiobutton"
            ).pack(side="left", padx=(0, 16))

        self._field(parent, "Output File Format")
        fmt_row = ttk.Frame(parent, style="Card.TFrame")
        fmt_row.pack(anchor="w")
        self.output_word_var = tk.BooleanVar(value=True)
        self.output_pdf_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            fmt_row, text="Word (.docx)", variable=self.output_word_var, style="Card.TCheckbutton"
        ).pack(side="left")
        ttk.Checkbutton(
            fmt_row, text="PDF (.pdf)", variable=self.output_pdf_var, style="Card.TCheckbutton"
        ).pack(side="left", padx=(16, 0))

        self.answer_key_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            parent, text="Also generate an answer key for each set", variable=self.answer_key_var,
            style="Card.TCheckbutton",
        ).pack(anchor="w", pady=(16, 0))

        ttk.Button(
            parent, text="Generate Question Papers", style="Accent.TButton", command=self._generate
        ).pack(anchor="w", pady=(20, 0), fill="x")

    def _build_output_panel(self, parent):
        ttk.Label(parent, text="Output", style="Card.TLabel", font=(theme.FONT_FAMILY, 11, "bold")).pack(anchor="w")
        self.log = tk.Text(parent, height=22, wrap="word", state="disabled", font=(theme.FONT_FAMILY, 9), bg="#fbfcfd")
        self.log.pack(fill="both", expand=True, pady=(8, 8))

        btn_row = ttk.Frame(parent, style="Card.TFrame")
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Open Output Folder", command=self._open_output_folder).pack(side="left")

    def refresh_choices(self):
        self.course_combo["values"] = [c["name"] for c in self.dm.courses()]
        if self.dm.courses() and not self.course_var.get():
            self.course_var.set(self.dm.courses()[0]["name"])

        fmt_names = [f"{f['id']} — {f['name']}" for f in self.dm.formats()]
        self.format_combo["values"] = fmt_names
        if fmt_names and self.format_var.get() not in fmt_names:
            self.format_var.set(fmt_names[0])
        self._update_format_desc()
        self._update_randomness_help()
        self._rebuild_topic_checkboxes()

    def _rebuild_topic_checkboxes(self):
        for w in self.topics_frame.winfo_children():
            w.destroy()
        self.topic_vars = {}
        names = self.dm.topic_names()
        for i, name in enumerate(names):
            var = tk.BooleanVar(value=True)
            self.topic_vars[name] = var
            cb = ttk.Checkbutton(self.topics_frame, text=name, variable=var, style="Card.TCheckbutton")
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 16), pady=2)

    def _set_all_topics(self, value):
        for v in self.topic_vars.values():
            v.set(value)

    def _selected_format(self):
        val = self.format_var.get()
        if not val:
            return None
        fmt_id = val.split(" — ")[0]
        return self.dm.get_format(fmt_id)

    def _update_format_desc(self):
        fmt = self._selected_format()
        self.format_desc_label.configure(text=fmt["description"] if fmt else "")

    def _update_randomness_help(self):
        self.randomness_help.configure(text=RANDOMNESS_HELP.get(self.randomness_var.get(), ""))

    def _log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.configure(state="disabled")
        self.log.see("end")

    def _generate(self):
        course = self.course_var.get()
        fmt = self._selected_format()
        if not course:
            dialogs.error(self, "Missing Course", "Please select a course (add one in the Course List tab if empty).")
            return
        if not fmt:
            dialogs.error(self, "Missing Format", "Please select an exam format (add one in the Exam Format Types tab if empty).")
            return
        topics = [name for name, v in self.topic_vars.items() if v.get()]
        if not topics:
            dialogs.error(self, "No Topics Selected", "Please select at least one Question Topic to include.")
            return
        want_word = self.output_word_var.get()
        want_pdf = self.output_pdf_var.get()
        if not want_word and not want_pdf:
            dialogs.error(self, "No Output Format Selected", "Please select Word, PDF, or both.")
            return

        level_filter = self.level_var.get()
        randomness = self.randomness_var.get()
        date_str = self.date_picker.get()
        duration_str = self.duration_picker.text()

        try:
            sets = generate_sets(
                fmt, self.dm.data["questions"], level_filter, topics, randomness, self.num_sets_var.get()
            )
        except InsufficientQuestionsError as e:
            details = "\n".join(
                f"  • {docx_export.SECTION_TITLES[t]}: need {n}, only {a} available with current filters"
                for t, n, a in e.shortfalls
            )
            dialogs.error(
                self, "Not Enough Questions",
                "The current filters don't provide enough questions for this format:\n\n" + details +
                "\n\nTry widening the Hardness Level, selecting more Topics, or adding more questions in the Question Bank.",
            )
            return

        out_dir = output_dir()
        self.last_output_dir = out_dir
        meta = self.dm.data.get("meta", {})
        self._log(f"--- Generating papers: {course} | {fmt['name']} | {date_str} ---")

        written = []
        for i, set_data in enumerate(sets):
            label = SET_LABELS[i]
            base = docx_export.safe_filename(course, fmt["id"], date_str, f"Set{label}")

            if want_word:
                paper_path = os.path.join(out_dir, f"{base}.docx")
                docx_export.build_paper(fmt, meta, course, date_str, label, set_data, paper_path, duration_str)
                written.append(paper_path)
                self._log(f"Set {label}: {os.path.basename(paper_path)}")
            if want_pdf:
                paper_path = os.path.join(out_dir, f"{base}.pdf")
                pdf_export.build_paper(fmt, meta, course, date_str, label, set_data, paper_path, duration_str)
                written.append(paper_path)
                self._log(f"Set {label}: {os.path.basename(paper_path)}")

            if self.answer_key_var.get():
                if want_word:
                    key_path = os.path.join(out_dir, f"{base}_AnswerKey.docx")
                    docx_export.build_answer_key(fmt, meta, course, date_str, label, set_data, key_path)
                    written.append(key_path)
                    self._log(f"Set {label} Answer Key: {os.path.basename(key_path)}")
                if want_pdf:
                    key_path = os.path.join(out_dir, f"{base}_AnswerKey.pdf")
                    pdf_export.build_answer_key(fmt, meta, course, date_str, label, set_data, key_path)
                    written.append(key_path)
                    self._log(f"Set {label} Answer Key: {os.path.basename(key_path)}")

        self._log(f"Done. {len(written)} file(s) saved to:\n{out_dir}\n")
        dialogs.info(self, "Papers Generated", f"{len(sets)} question paper set(s) generated successfully in:\n{out_dir}")

    def _open_output_folder(self):
        folder = self.last_output_dir or output_dir()
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
