"""Core randomisation logic: turns a format + filters into 1-3 question sets.

Kept independent of the GUI and of docx so it can be unit-tested and
reused (e.g. from a future CLI) on its own.
"""
import random


class InsufficientQuestionsError(Exception):
    def __init__(self, shortfalls):
        self.shortfalls = shortfalls  # list of (section_type, needed, available)
        msg = "; ".join(
            f"{t}: need {n}, only {a} available after filters" for t, n, a in shortfalls
        )
        super().__init__(f"Not enough questions to generate this paper — {msg}")


def _filter_pool(all_questions, level_filter, topic_filter):
    pool = all_questions
    if level_filter and level_filter != "Mixed (All Levels)":
        pool = [q for q in pool if q.get("level") == level_filter]
    if topic_filter:
        pool = [q for q in pool if q.get("topic") in topic_filter]
    return pool


def check_availability(fmt: dict, question_bank: dict, level_filter, topic_filter):
    """Returns a list of (section_type, needed, available) shortfalls, empty if OK."""
    shortfalls = []
    for sec in fmt["sections"]:
        pool = _filter_pool(question_bank[sec["type"]], level_filter, topic_filter)
        needed = sec["display_count"]
        if len(pool) < needed:
            shortfalls.append((sec["type"], needed, len(pool)))
    return shortfalls


def _sample_sets(pool, count, randomness, num_sets):
    """Draw `num_sets` lists of `count` questions each from `pool` per the randomness level.

    Low: one base sample reused by every set (order/options reshuffled per set).
    Medium: each set keeps ~50% of the previous set, refreshes the rest.
    High: draws without replacement across all sets to minimise repeats,
          wrapping around the pool (reshuffled) only once it's exhausted.
    """
    pool = list(pool)
    if randomness == "Low":
        base = random.sample(pool, count)
        return [list(base) for _ in range(num_sets)]

    if randomness == "Medium":
        prev = random.sample(pool, count)
        sets = [prev]
        for _ in range(num_sets - 1):
            keep_n = count // 2
            keep = random.sample(prev, keep_n) if keep_n else []
            remaining_pool = [q for q in pool if q not in keep]
            need = count - len(keep)
            if len(remaining_pool) >= need:
                fresh = random.sample(remaining_pool, need)
            else:
                fresh = list(remaining_pool)
                fresh += random.sample(pool, need - len(fresh))
            new_set = keep + fresh
            random.shuffle(new_set)
            sets.append(new_set)
            prev = new_set
        return sets

    shuffled = list(pool)
    random.shuffle(shuffled)
    sets, i = [], 0
    for _ in range(num_sets):
        chunk = []
        while len(chunk) < count:
            if i >= len(shuffled):
                random.shuffle(shuffled)
                i = 0
            chunk.append(shuffled[i])
            i += 1
        sets.append(chunk)
    return sets


def generate_sets(fmt: dict, question_bank: dict, level_filter, topic_filter, randomness, num_sets=3):
    """Returns a list of `num_sets` sets, each a dict: {section_type: [question,...]}.

    Raises InsufficientQuestionsError if the filtered pool can't satisfy the format.
    """
    shortfalls = check_availability(fmt, question_bank, level_filter, topic_filter)
    if shortfalls:
        raise InsufficientQuestionsError(shortfalls)

    sets = [{} for _ in range(num_sets)]
    for sec in fmt["sections"]:
        pool = _filter_pool(question_bank[sec["type"]], level_filter, topic_filter)
        drawn = _sample_sets(pool, sec["display_count"], randomness, num_sets)
        for i in range(num_sets):
            questions = [dict(q) for q in drawn[i]]
            random.shuffle(questions)
            if sec["type"] == "mcq":
                for q in questions:
                    opts = list(q["options"])
                    random.shuffle(opts)
                    q["_shuffled_options"] = opts
            sets[i][sec["type"]] = questions
    return sets
