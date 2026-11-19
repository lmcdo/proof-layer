"""Find a claim's own row by its label, then check the number against that row only.

Why: checking a number against a whole page lets a wrong number pass whenever that
number appears anywhere else on the page. Checking against the claim's own row does not.

Five verdicts. Only FOUND_IN_ROW passes. Everything else is HELD_BACK, with a reason:

  FOUND_IN_ROW     exactly one row matches the label and the number is written in it
  AMBIGUOUS_LABEL  several rows match the label and the number is in at least one: the
                   checker cannot tell which row the claim means, so a human should
  WRONG_FOR_LABEL  the label's row was found, the number is NOT in it, but it is
                   elsewhere on the page (the lifted-number case)
  ABSENT           the number is not on the page at all
  UNKNOWN          the checker cannot judge: no source text, no number, or no row
                   matches the label. Never treated as fine.

Label matching tolerates paraphrase (extra words, different order) but never a
different digit: "Scope 3" cannot match the "Scope 1" row.
"""
from __future__ import annotations

import re
from typing import Optional

from .integrity import FAILING_STATES, explain_value

FOUND_IN_ROW = "FOUND_IN_ROW"
AMBIGUOUS_LABEL = "AMBIGUOUS_LABEL"
WRONG_FOR_LABEL = "WRONG_FOR_LABEL"
ABSENT = "ABSENT"
UNKNOWN = "UNKNOWN"
HELD_BACK = frozenset({AMBIGUOUS_LABEL, WRONG_FOR_LABEL, ABSENT, UNKNOWN})

#: Share of a long label's words that must appear on a row. Labels of 1-2 words need all of them.
LONG_LABEL_MATCH = 0.5

# Words of 3+ characters, PLUS stand-alone 1-2 digit numbers: "Scope 1" and "Scope 2" differ only by
# that digit. A digit that is part of a longer number ("19,691", "5.5") is a value, not a label part;
# a comma or full stop AFTER the digit ("Scope 2, market-based") is just punctuation.
_WORD = re.compile(r"[a-z][a-z0-9\-]{2,}|(?<![\d.])(?<!\d,)\d{1,2}(?!\d|[.,]\d)")
_STOP = frozenset({"the", "and", "for", "with", "from", "that", "this", "total", "per", "are", "was"})


def _tokens(text: str) -> list[str]:
    return [w for w in _WORD.findall((text or "").lower()) if w not in _STOP]


def _result(verdict: str, reason: str, **extra) -> dict:
    return {"verdict": verdict, "reason": reason, **extra}


def _found(value, text: str, unit) -> bool:
    return explain_value(value, text, unit)[0] not in FAILING_STATES


def _candidate_rows(want: list[str], lines: list[str], line_tokens: Optional[list] = None) -> list[int]:
    """Rows that best match the label. Digits in the label must all be on the row.

    ``line_tokens`` lets a caller that checks many claims against one page prepare the
    page's words once instead of on every call."""
    digits = {t for t in want if t.isdigit()}
    words = [t for t in want if not t.isdigit()]
    if not words:
        return []
    need = 1.0 if len(words) <= 2 else LONG_LABEL_MATCH
    scored = []
    for i, ln in enumerate(lines):
        have = line_tokens[i] if line_tokens is not None else set(_tokens(ln))
        if not digits <= have:
            continue
        share = sum(1 for w in words if w in have) / len(words)
        if share >= need:
            scored.append((share, i))
    if not scored:
        return []
    best = max(s for s, _ in scored)
    return [i for s, i in scored if s == best]


def check_claim(label: str, value, page_text: Optional[str], unit=None) -> dict:
    """Check that ``value`` is written on the row of ``page_text`` that carries ``label``."""
    if not str(page_text or "").strip():
        return _result(UNKNOWN, "no source text to check against")
    if value is None or isinstance(value, bool):
        return _result(UNKNOWN, "no numeric value was claimed")
    try:
        float(value)
    except (TypeError, ValueError):
        return _result(UNKNOWN, "the claimed value is not a number")
    want = _tokens(label)
    if not [t for t in want if not t.isdigit()]:
        return _result(UNKNOWN, "the label is too short to locate a row")

    lines = page_text.split("\n")
    rows = _candidate_rows(want, lines)
    if not rows:
        verdict = UNKNOWN if _found(value, page_text, unit) else ABSENT
        why = "no row matches the label; number is on the page" if verdict == UNKNOWN else "number is not on the page"
        return _result(verdict, why, candidates=0)

    hits, windows = [], []
    for i in rows:
        window = lines[i]
        # A wrapped row: the numbers sit on the next line when that line has no words of its own.
        if i + 1 < len(lines) and not _tokens(lines[i + 1]):
            window += " " + lines[i + 1]
        windows.append(window)
        if _found(value, window, unit):
            hits.append(window)
    shown = [w[:140] for w in windows[:3]]   # the line(s) the claim was checked against
    if hits and len(rows) == 1:
        return _result(FOUND_IN_ROW, "number is written in the label's only matching row",
                       candidates=1, row=hits[0][:200], lines=shown)
    if hits:
        return _result(AMBIGUOUS_LABEL,
                       f"{len(rows)} rows match the label; the number is in {len(hits)} of them",
                       candidates=len(rows), rows_with_number=len(hits), lines=shown)
    if _found(value, page_text, unit):
        return _result(WRONG_FOR_LABEL, "number is on the page but not in the label's row",
                       candidates=len(rows), lines=shown)
    return _result(ABSENT, "number is not on the page", candidates=len(rows), lines=shown)
