"""Core randomisation logic: turns a format + filters into 1-3 question sets.

Kept independent of the GUI and of docx so it can be unit-tested and
reused (e.g. from a future CLI) on its own.

A generated set is a dict keyed by the section's position in the format
({0: [questions...], 1: [...]}), so formats with several sections, even of
the same question type, each get their own questions.
"""
import random
from collections import Counter


class InsufficientQuestionsError(Exception):
    def __init__(self, shortfalls):
        self.shortfalls = shortfalls  # list of (section_type, needed, available)
        msg = "; ".join(
            f"{t}: need {n}, only {a} available after filters" for t, n, a in shortfalls
        )
        super().__init__(f"Not enough questions to generate this paper — {msg}")


class TopicShortageError(Exception):
    """A topic was given more questions of a type than the bank has for it."""

    def __init__(self, shortfalls):
        self.shortfalls = shortfalls  # list of (section_type, topic, needed, available)
        msg = "; ".join(
            f"{t} / {topic}: need {n}, only {a}" for t, topic, n, a in shortfalls
        )
        super().__init__(f"Not enough questions for the topic allocation — {msg}")


def _filter_pool(all_questions, level_filter, topic_filter):
    pool = all_questions
    if level_filter and level_filter != "Mixed (All Levels)":
        pool = [q for q in pool if q.get("level") == level_filter]
    if topic_filter:
        pool = [q for q in pool if q.get("topic") in topic_filter]
    return pool


def _type_groups(fmt: dict) -> dict:
    """{question_type: [section indexes]} in format order."""
    groups = {}
    for idx, sec in enumerate(fmt["sections"]):
        groups.setdefault(sec["type"], []).append(idx)
    return groups


def available_by_topic(question_bank: dict, qtype: str, level_filter) -> dict:
    """{topic: number of questions of this type at this hardness level}."""
    return dict(Counter(q.get("topic") for q in _filter_pool(question_bank[qtype], level_filter, None)))


def check_availability(fmt: dict, question_bank: dict, level_filter, topic_filter):
    """Returns a list of (section_type, needed, available) shortfalls, empty if OK.

    Sections of the same type draw from one pool, so their counts are added up.
    """
    shortfalls = []
    for qtype, idxs in _type_groups(fmt).items():
        pool = _filter_pool(question_bank[qtype], level_filter, topic_filter)
        needed = sum(fmt["sections"][i]["display_count"] for i in idxs)
        if len(pool) < needed:
            shortfalls.append((qtype, needed, len(pool)))
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
                spare = [q for q in pool if q not in keep and q not in fresh]
                fresh += random.sample(spare, need - len(fresh))
            new_set = keep + fresh
            random.shuffle(new_set)
            sets.append(new_set)
            prev = new_set
        return sets

    queue = list(pool)
    random.shuffle(queue)
    sets = []
    for _ in range(num_sets):
        chunk = []
        while len(chunk) < count:
            if not queue:
                queue = [q for q in pool if q not in chunk]
                random.shuffle(queue)
            chunk.append(queue.pop())
        sets.append(chunk)
    return sets


def apportion(count: int, weights: dict, capacities: dict) -> dict:
    """Split `count` across topics in proportion to `weights`, never exceeding
    a topic's `capacities` (questions available). Leftover seats go one at a
    time to whichever topic is furthest below its ideal share, so a topic that
    runs out of questions has its shortfall absorbed by the others.
    """
    total_w = sum(w for w in weights.values() if w > 0)
    ideal = {t: count * w / total_w for t, w in weights.items() if w > 0}
    alloc = {t: min(int(ideal[t]), capacities.get(t, 0)) for t in ideal}
    remaining = count - sum(alloc.values())
    while remaining > 0:
        open_topics = [t for t in ideal if alloc[t] < capacities.get(t, 0)]
        if not open_topics:
            break
        best = max(open_topics, key=lambda t: ideal[t] - alloc[t])
        alloc[best] += 1
        remaining -= 1
    return alloc


def plan_percent_allocations(fmt: dict, question_bank: dict, level_filter, topic_weights: dict):
    """For each section, compare the topic split the percentages ask for with
    what the question bank can actually supply.

    Returns a list (one entry per section) of (wanted, got), each {topic: count}.
    `got` differs from `wanted` when a topic has fewer questions than its share,
    in which case the other topics make up the difference. Sections of the same
    type draw from the same stock, so earlier sections use it up first.
    """
    weights = {t: w for t, w in topic_weights.items() if w > 0}
    stock = {}
    plan = []
    for sec in fmt["sections"]:
        qtype, count = sec["type"], sec["display_count"]
        if qtype not in stock:
            stock[qtype] = {t: 0 for t in weights}
            for q in _filter_pool(question_bank[qtype], level_filter, list(weights)):
                stock[qtype][q["topic"]] += 1
        wanted = apportion(count, weights, {t: count for t in weights})
        got = apportion(count, weights, stock[qtype])
        for t, n in got.items():
            stock[qtype][t] -= n
        plan.append((wanted, got))
    return plan


def generate_sets(fmt: dict, question_bank: dict, level_filter, topic_filter, randomness,
                  num_sets=3, topic_weights=None, section_counts=None):
    """Returns (sets, allocations).

    sets: a list of `num_sets` sets, each a dict {section_index: [question,...]}.
    allocations: {section_index: {topic: count}} when a topic allocation was
    given (the per-topic question counts actually used), else {}.

    Topic allocation is optional and comes in two forms:
      topic_weights   {topic: percent}: each section's count is split by the
                      percentages; if a topic is short of questions the others
                      make up the difference.
      section_counts  [{topic: count}, ...], one dict per section, in format
                      order: exact question counts per topic. Each dict must add
                      up to that section's display_count.
    Without either, questions are drawn at random from all selected topics.

    Raises InsufficientQuestionsError if the filtered pool can't satisfy the
    format, TopicShortageError if an exact per-topic count exceeds what the bank
    holds, and ValueError if section_counts don't add up to the format.
    """
    sections = fmt["sections"]
    allocs = None

    if section_counts is not None:
        if len(section_counts) != len(sections):
            raise ValueError("section_counts must have one entry per section of the format.")
        allocs = [{t: n for t, n in c.items() if n > 0} for c in section_counts]
        for i, (sec, alloc) in enumerate(zip(sections, allocs), start=1):
            if sum(alloc.values()) != sec["display_count"]:
                raise ValueError(
                    f"Section {i}: topic counts add up to {sum(alloc.values())}, "
                    f"but the format needs {sec['display_count']}."
                )
        topic_filter = sorted({t for a in allocs for t in a})
        shortfalls = []
        for qtype, idxs in _type_groups(fmt).items():
            have = available_by_topic(question_bank, qtype, level_filter)
            need = Counter()
            for i in idxs:
                need.update(allocs[i])
            shortfalls += [
                (qtype, t, n, have.get(t, 0)) for t, n in need.items() if n > have.get(t, 0)
            ]
        if shortfalls:
            raise TopicShortageError(shortfalls)
    elif topic_weights:
        topic_weights = {t: w for t, w in topic_weights.items() if w > 0}
        topic_filter = list(topic_weights)
        shortfalls = check_availability(fmt, question_bank, level_filter, topic_filter)
        if shortfalls:
            raise InsufficientQuestionsError(shortfalls)
        allocs = [got for _, got in plan_percent_allocations(fmt, question_bank, level_filter, topic_weights)]
    else:
        shortfalls = check_availability(fmt, question_bank, level_filter, topic_filter)
        if shortfalls:
            raise InsufficientQuestionsError(shortfalls)

    sets = [{} for _ in range(num_sets)]
    for qtype, idxs in _type_groups(fmt).items():
        pool = _filter_pool(question_bank[qtype], level_filter, topic_filter)
        parts = [{i: [] for i in idxs} for _ in range(num_sets)]
        if allocs is not None:
            by_topic = {}
            for q in pool:
                by_topic.setdefault(q.get("topic"), []).append(q)
            totals = Counter()
            for i in idxs:
                totals.update(allocs[i])
            for topic, total in totals.items():
                drawn = _sample_sets(by_topic.get(topic, []), total, randomness, num_sets)
                for s in range(num_sets):
                    cursor = 0
                    for i in idxs:
                        n = allocs[i].get(topic, 0)
                        parts[s][i].extend(drawn[s][cursor:cursor + n])
                        cursor += n
        else:
            total = sum(sections[i]["display_count"] for i in idxs)
            drawn = _sample_sets(pool, total, randomness, num_sets)
            for s in range(num_sets):
                cursor = 0
                for i in idxs:
                    n = sections[i]["display_count"]
                    parts[s][i] = drawn[s][cursor:cursor + n]
                    cursor += n
        for s in range(num_sets):
            for i in idxs:
                questions = [dict(q) for q in parts[s][i]]
                random.shuffle(questions)
                if qtype == "mcq":
                    for q in questions:
                        opts = list(q["options"])
                        random.shuffle(opts)
                        q["_shuffled_options"] = opts
                sets[s][i] = questions

    allocations = {i: dict(a) for i, a in enumerate(allocs)} if allocs is not None else {}
    return sets, allocations
