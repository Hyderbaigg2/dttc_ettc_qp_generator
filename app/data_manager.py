"""Loads, saves and mutates the single JSON data store.

Every write goes through save(), which writes atomically (temp file +
replace) so a crash or power cut mid-write can't corrupt the store.
"""
import json
import os
import shutil
import tempfile
from datetime import datetime

from app.paths import data_file_path

LEVELS = ["Easy", "Medium", "Hard"]
QUESTION_TYPES = ["mcq", "fill_blank", "descriptive"]
ID_PREFIX = {"mcq": "MCQ", "fill_blank": "BLA", "descriptive": "DES"}


class DataManager:
    def __init__(self, path: str = None):
        self.path = path or data_file_path()
        self.data = {}
        self.load()

    # ---------- persistence ----------

    def load(self):
        if not os.path.exists(self.path):
            self.data = {
                "meta": {
                    "institute": "Diesel Traction Training Centre, Kazipet (DTTC/KZJ)",
                    "zone": "South Central Railway",
                    "schema_version": 1,
                },
                "courses": [],
                "topics": [],
                "levels": LEVELS,
                "formats": [],
                "questions": {"mcq": [], "fill_blank": [], "descriptive": []},
            }
            self.save()
            return
        with open(self.path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.data.setdefault("questions", {})
        for t in QUESTION_TYPES:
            self.data["questions"].setdefault(t, [])
        self.data.setdefault("courses", [])
        self.data.setdefault("topics", [])
        self.data.setdefault("formats", [])
        self.data.setdefault("levels", LEVELS)

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(self.path), prefix=".dttc_", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            shutil.move(tmp_path, self.path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def backup(self) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(
            os.path.dirname(self.path), f"dttc_data_backup_{stamp}.json"
        )
        shutil.copy2(self.path, backup_path)
        return backup_path

    # ---------- courses ----------

    def courses(self):
        return self.data["courses"]

    def next_course_id(self) -> str:
        nums = [int(c["id"][1:]) for c in self.data["courses"] if c["id"][1:].isdigit()]
        return f"C{(max(nums) + 1) if nums else 1:03d}"

    def add_course(self, name: str):
        course = {"id": self.next_course_id(), "name": name.strip()}
        self.data["courses"].append(course)
        self.save()
        return course

    def update_course(self, course_id: str, name: str):
        for c in self.data["courses"]:
            if c["id"] == course_id:
                c["name"] = name.strip()
        self.save()

    def delete_course(self, course_id: str):
        self.data["courses"] = [c for c in self.data["courses"] if c["id"] != course_id]
        self.save()

    # ---------- topics ----------

    def topics(self):
        return self.data["topics"]

    def topic_names(self):
        return [t["name"] for t in self.data["topics"]]

    def next_topic_id(self) -> str:
        nums = [int(t["id"][1:]) for t in self.data["topics"] if t["id"][1:].isdigit()]
        return f"T{(max(nums) + 1) if nums else 1:03d}"

    def add_topic(self, name: str):
        topic = {"id": self.next_topic_id(), "name": name.strip()}
        self.data["topics"].append(topic)
        self.save()
        return topic

    def update_topic(self, topic_id: str, name: str):
        old_name = None
        for t in self.data["topics"]:
            if t["id"] == topic_id:
                old_name = t["name"]
                t["name"] = name.strip()
        if old_name and old_name != name.strip():
            for qtype in QUESTION_TYPES:
                for q in self.data["questions"][qtype]:
                    if q.get("topic") == old_name:
                        q["topic"] = name.strip()
        self.save()

    def delete_topic(self, topic_id: str):
        self.data["topics"] = [t for t in self.data["topics"] if t["id"] != topic_id]
        self.save()

    def topic_in_use(self, name: str) -> int:
        count = 0
        for qtype in QUESTION_TYPES:
            count += sum(1 for q in self.data["questions"][qtype] if q.get("topic") == name)
        return count

    # ---------- formats ----------

    def formats(self):
        return self.data["formats"]

    def get_format(self, fmt_id: str):
        for f in self.data["formats"]:
            if f["id"] == fmt_id:
                return f
        return None

    def upsert_format(self, fmt: dict):
        existing = self.get_format(fmt["id"])
        if existing:
            existing.update(fmt)
        else:
            self.data["formats"].append(fmt)
        self.save()

    def delete_format(self, fmt_id: str):
        self.data["formats"] = [f for f in self.data["formats"] if f["id"] != fmt_id]
        self.save()

    @staticmethod
    def format_total_marks(fmt: dict) -> int:
        total = 0
        for sec in fmt.get("sections", []):
            answer_count = sec["display_count"] - sec.get("choice_leave", 0)
            total += answer_count * sec["marks_each"]
        return total

    # ---------- questions ----------

    def questions(self, qtype: str):
        return self.data["questions"][qtype]

    def next_question_id(self, qtype: str) -> str:
        prefix = ID_PREFIX[qtype]
        nums = [
            int(q["id"][len(prefix):])
            for q in self.data["questions"][qtype]
            if q["id"].startswith(prefix) and q["id"][len(prefix):].isdigit()
        ]
        return f"{prefix}{(max(nums) + 1) if nums else 1:04d}"

    def add_question(self, qtype: str, fields: dict):
        q = dict(fields)
        q["id"] = self.next_question_id(qtype)
        self.data["questions"][qtype].append(q)
        self.save()
        return q

    def update_question(self, qtype: str, qid: str, fields: dict):
        for q in self.data["questions"][qtype]:
            if q["id"] == qid:
                q.update(fields)
        self.save()

    def delete_question(self, qtype: str, qid: str):
        self.data["questions"][qtype] = [
            q for q in self.data["questions"][qtype] if q["id"] != qid
        ]
        self.save()

    def find_question(self, qtype: str, qid: str):
        for q in self.data["questions"][qtype]:
            if q["id"] == qid:
                return q
        return None
