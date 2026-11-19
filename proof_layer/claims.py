"""Pull the figures out of an AI's answer, in the AI's own words.

Input is the text an AI wrote: sentences, bullet points, markdown tables. Output is one Claim
per figure: what it is about (the words around the number) and the number itself.

Rules, all deterministic:
- A year (1900-2100, written without a comma or point) is not a figure.
- A number straight after a word like "Scope", "Section", "Table", "Page" names something;
  it is not a figure ("Scope 1" stays part of the description).
- Numbers glued to letters (FY25, CO2, Q3) are not figures.
- A number followed by million / billion / thousand / k is flagged as scaled: it cannot be
  matched digit for digit, so it is reported for a person to check.
- Several numbers in one sentence share the description unless new words come between them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_NUMBER = re.compile(r"(?<![\w.])[-−]?\$?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")
_BULLET = re.compile(r"^\s*(?:[-*•]|\d{1,2}[.)])\s+")
_SENTENCE_END = re.compile(r"(?<=[.!?;])\s+(?=[A-Z(\"'*])|;\s+")
_SCALE = re.compile(r"^\s?(million|billion|trillion|thousand|bn|k)\b", re.I)

#: units the checker understands, in the order they are tried
_UNITS = (
    (re.compile(r"^\s?(?:%|per\s?cent\b)", re.I), "%"),
    (re.compile(r"^\s?(?:sqm|m2|m²|square\s+met(?:re|er)s?)\b", re.I), "m2"),
    (re.compile(r"^\s?(?:metres?|meters?|m)(?!\w)", re.I), "m"),
    (re.compile(r"^\s?(?:hours?|hrs?)\b", re.I), "hours"),
    (re.compile(r"^\s?(?:storeys?|stories)\b", re.I), "storeys"),
)

#: a number right after one of these words names something instead of measuring it
_NAMING_WORDS = frozenset({
    "scope", "category", "categories", "section", "sections", "table", "figure", "fig", "page",
    "pages", "p", "pp", "chapter", "appendix", "step", "item", "no", "number", "q", "quarter",
    "fy", "gri", "tier", "level", "phase", "part", "version", "v", "clause", "rule", "control",
})

#: words that do not help find the right place in the document
_FILLER = frozenset({
    "a", "an", "the", "and", "or", "of", "in", "to", "by", "for", "at", "on", "from", "with",
    "was", "were", "is", "are", "be", "been", "being", "had", "has", "have", "that", "which",
    "this", "these", "those", "it", "its", "their", "about", "approximately", "around", "roughly",
    "over", "under", "just", "only", "also", "some", "up", "down", "than", "as", "per", "into",
    "reported", "increased", "decreased", "fell", "rose", "reached", "totalled", "totaled",
    "stood", "came", "amounted", "equal", "equals", "equalled", "grew", "dropped", "declined",
    "rising", "falling", "key", "figures", "figure", "report", "here", "following",
    "shows", "show", "showed", "states", "stated", "says", "said", "according", "notes", "noted",
    "indicates", "indicated", "highlights", "includes", "included",
})


#: "Table 3", "page 12", "section 4.2": pointers into the document, not part of what a figure is about
_REFERENCE = re.compile(r"\b(?:tables?|figures?|fig|pages?|pp?|sections?|chapters?|appendix|clauses?|steps?)\.?\s+\d+(?:\.\d+)*\b", re.I)


@dataclass(frozen=True)
class Claim:
    description: str      # what the figure is about, in the AI's words, filler removed
    number_text: str      # the number as the AI wrote it
    value: float
    unit: str | None      # one of m, m2, %, hours, storeys, or None
    scaled: bool          # written with million / billion / thousand / k
    sentence: str         # the sentence or line it came from


def _clean_words(text: str) -> str:
    text = re.sub(r"[*_`#>|]", " ", text)
    text = _REFERENCE.sub(" ", text)
    words = []
    for raw in re.split(r"[\s:,()\[\]\"'/]+", text):
        w = raw.strip(".-–—")
        low = w.lower()
        if not w or low in _FILLER:
            continue
        if re.fullmatch(r"fy\d{2,4}|(?:19|20)\d{2}|\$?\d[\d,]*(?:\.\d+)?%?", low) and not re.fullmatch(r"\d{1,2}", low):
            continue                      # years, FY tags and figures are not description words
        words.append(w)
    return " ".join(words)


def _parse(token: str) -> float | None:
    try:
        return float(token.replace(",", "").replace("$", "").replace("−", "-"))
    except ValueError:
        return None


def _is_figure(sentence: str, match: re.Match, token: str, value: float) -> bool:
    if re.fullmatch(r"(?:19|20)\d{2}", token.lstrip("-−$")):
        return False                       # a year
    before = re.findall(r"[A-Za-z]+", sentence[: match.start()])
    if before and before[-1].lower() in _NAMING_WORDS and re.fullmatch(r"[\d.]+", token):
        return False                       # "Scope 1", "Table 3", "page 12"
    return True


def _figures_in(sentence: str) -> list[tuple[re.Match, str, float]]:
    out = []
    for m in _NUMBER.finditer(sentence):
        value = _parse(m.group(0))
        if value is not None and _is_figure(sentence, m, m.group(0), value):
            out.append((m, m.group(0), value))
    return out


def _unit_and_scale(sentence: str, end: int) -> tuple[str | None, bool]:
    rest = sentence[end:]
    if _SCALE.match(rest):
        return None, True
    for pattern, unit in _UNITS:
        if pattern.match(rest):
            return unit, False
    return None, False


def _from_sentence(sentence: str) -> list[Claim]:
    figures = _figures_in(sentence)
    claims: list[Claim] = []
    last_description = ""
    prev_end = 0
    for k, (m, token, value) in enumerate(figures):
        between = sentence[prev_end: m.start()]
        description = _clean_words(between)
        if k > 0 and len(description.split()) < 2:
            description = last_description               # "... from 6,102 to 5,845": same item
        if not description:                              # "19,691 tCO2-e of Scope 1 emissions"
            next_start = figures[k + 1][0].start() if k + 1 < len(figures) else len(sentence)
            description = _clean_words(sentence[m.end(): next_start])
        unit, scaled = _unit_and_scale(sentence, m.end())
        if description:
            claims.append(Claim(description, token, value, unit, scaled, sentence.strip()))
            last_description = description
        prev_end = m.end()
    return claims


def _from_table_row(line: str) -> list[Claim]:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if not cells or all(re.fullmatch(r":?-{2,}:?", c) or not c for c in cells):
        return []
    label = _clean_words(cells[0])
    if not label or not re.search(r"[A-Za-z]{3,}", label):
        return []
    claims = []
    for cell in cells[1:]:
        for m, token, value in _figures_in(cell):
            unit, scaled = _unit_and_scale(cell, m.end())
            claims.append(Claim(label, token, value, unit, scaled, line.strip()))
            break                                        # one figure per cell
    return claims


def extract_claims(answer: str) -> list[Claim]:
    """Every figure in the AI's answer, with what it is about. Repeats are dropped."""
    claims: list[Claim] = []
    for raw in (answer or "").splitlines():
        if not raw.strip():
            continue
        if "|" in raw:
            claims += _from_table_row(raw)
            continue
        line = _BULLET.sub("", raw)
        for sentence in _SENTENCE_END.split(line):
            claims += _from_sentence(sentence)
    seen, unique = set(), []
    for c in claims:
        key = (c.description.lower(), c.value)
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique
