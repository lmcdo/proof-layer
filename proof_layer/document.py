"""Check a figure against a whole document, without being told which page it is on.

``locate.check_claim`` checks one figure against one page. Here the AI's answer carries no page
numbers, so every page is searched. The same five answers come back, now for the document:

  FOUND_IN_ROW     the description fits one or more places, and the number is in ALL of them
  AMBIGUOUS_LABEL  the description fits several places and the number is in only some of them
  WRONG_FOR_LABEL  the description was found, the number is not there, but it is elsewhere
  ABSENT           the number is nowhere in the document
  UNKNOWN          nothing in the document is about this, or there was nothing to judge

Only FOUND_IN_ROW passes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .locate import (ABSENT, AMBIGUOUS_LABEL, FOUND_IN_ROW, UNKNOWN, WRONG_FOR_LABEL, _candidate_rows,
                     _found, _result, _tokens, _without_label_digits)


@dataclass
class Page:
    number: int
    text: str
    lines: list[str] = field(init=False)
    tokens: list[set] = field(init=False)

    def __post_init__(self):
        self.lines = self.text.split("\n")
        self.tokens = [set(_tokens(ln)) for ln in self.lines]


@dataclass
class Document:
    pages: list[Page]

    @classmethod
    def from_texts(cls, texts: list[str]) -> "Document":
        """Pages are numbered from 1, in the order given."""
        return cls([Page(i, t or "") for i, t in enumerate(texts, 1)])


def _window(page: Page, i: int) -> str:
    """The row's line, plus the next line when that line holds only numbers (a wrapped row)."""
    text = page.lines[i]
    if i + 1 < len(page.lines) and not page.tokens[i + 1]:
        text += " " + page.lines[i + 1]
    return text


def _number_forms(value: float) -> list[str]:
    forms = {str(value), f"{value:g}"}
    if float(value).is_integer():
        forms |= {str(int(value)), f"{int(value):,}"}
    return list(forms)


def _number_elsewhere(value, doc: Document, unit) -> bool:
    forms = _number_forms(float(value))
    return any(any(f in p.text for f in forms) and _found(value, p.text, unit) for p in doc.pages)


def check_in_document(label: str, value, doc: Document, unit: Optional[str] = None) -> dict:
    """Check that ``value`` is written where the document discusses ``label``."""
    if value is None or isinstance(value, bool):
        return _result(UNKNOWN, "no numeric value was claimed")
    try:
        float(value)
    except (TypeError, ValueError):
        return _result(UNKNOWN, "the claimed value is not a number")
    want = _tokens(str(label))
    if not [t for t in want if not t.isdigit()]:
        return _result(UNKNOWN, "the description is too short to locate anything")
    if not any(p.text.strip() for p in doc.pages):
        return _result(UNKNOWN, "the document has no text to check against")

    seen = []                       # (page number, row text, number is in this row)
    for page in doc.pages:
        for i in _candidate_rows(want, page.lines, page.tokens):
            row = _window(page, i)
            seen.append((page.number, row, _found(value, _without_label_digits(row, want), unit)))

    pages = sorted({n for n, _, _ in seen})
    shown = [f"p{n}: {row[:140]}" for n, row, _ in seen[:3]]
    with_number = [(n, row) for n, row, has in seen if has]
    if seen and len(with_number) == len(seen):
        return _result(FOUND_IN_ROW, "the number is written where the document discusses this",
                       candidates=len(seen), pages=sorted({n for n, _ in with_number}), lines=shown)
    if with_number:
        return _result(AMBIGUOUS_LABEL,
                       f"{len(seen)} places in the document fit; the number is in {len(with_number)} of them",
                       candidates=len(seen), pages=pages, lines=shown)
    elsewhere = _number_elsewhere(value, doc, unit)
    if seen:
        verdict = WRONG_FOR_LABEL if elsewhere else ABSENT
        why = ("the number is in the document, but not where this is discussed" if elsewhere
               else "the number is not in the document")
        return _result(verdict, why, candidates=len(seen), pages=pages, lines=shown)
    if elsewhere:
        return _result(UNKNOWN, "nothing in the document is clearly about this; the number appears elsewhere",
                       candidates=0)
    return _result(ABSENT, "the number is not in the document", candidates=0)
