"""proof-layer report.pdf results.json  ->  checks every figure your code returned.

results.json is a list of figures: [{"name": "Scope 1 emissions", "value": 5845}, ...].
Field names are found automatically (name/label/about/item, value/number/amount, unit).
If the second file is plain text (.txt/.md), it is an AI's written answer instead: every figure
in it is found and checked. Figures written as "5.2 million" are always passed to you to check.
If a figure also carries the text it was taken from ("source_text", plus "page" if known), as it
does when it is stored in a database, two things are checked: that the stored number really is in
that text, and that the text really is in the PDF (on that page, if you gave one).
Add --ask-ai items.json to write the figures it cannot settle, with the surrounding text, for your AI to
read; give the AI's reply back with --answers answers.json. An AI "yes" only counts where the number is
already in the stored text and that text is in the PDF, so the AI cannot approve an invented number.
Add --sheet check.html to also get one picture per figure that needs a look: the PDF page with
the number highlighted (needs PyMuPDF).
Exit code 0 if every figure is correct, 1 if any needs attention.
"""
import json
import re
import sys

from .document import Document
from .document import check_in_document

NAME = ("name", "label", "about", "item", "metric", "description")
VALUE = ("value", "number", "amount", "figure")
SAYS = {"FOUND_IN_ROW": "CORRECT", "WRONG_FOR_LABEL": "WRONG", "ABSENT": "WRONG",
        "AMBIGUOUS_LABEL": "CHECK", "UNKNOWN": "CHECK"}


def _pick(row: dict, keys):
    for k in keys:
        if k in row:
            return row[k]
    return None


def load_pages(pdf_path: str) -> Document:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return Document.from_texts([p.extract_text() or "" for p in pdf.pages])


PLAIN = {
    "nothing in the document is clearly about this; the number appears elsewhere":
        "The report doesn't clearly talk about this, though the number does appear elsewhere in it.",
    "the number is not in the document": "The number is not anywhere in the report.",
}


def _plain(reason: str) -> str:
    return PLAIN.get(reason, reason[:1].upper() + reason[1:] + ("" if reason.endswith(".") else "."))


def _report_has(line: str) -> str:
    m = re.match(r"p(\d+): (.*)", line)
    return f"The report has, on page {m.group(1)}: {m.group(2)}" if m else f"The report has: {line}"


JUDGE_INSTRUCTIONS = (
    "For each item, decide whether the quote and context support that the thing named in 'name' has exactly "
    "this 'value' (and that year or period, if the name gives one). Use only the text in the item. Answer "
    "'yes' only if the text clearly ties that number to that item. Answer 'no' if the number belongs to "
    "something else. Answer 'unsure' if you cannot tell; a number merely nearby is not 'yes'. Reply with a "
    "JSON list: [{\"id\": 0, \"answer\": \"yes\"}, ...] and save it, then run proof-layer again with "
    "--answers that-file.json")

QUOTE = ("source_text", "quote", "evidence", "source")


def _norm(text: str) -> str:
    return " ".join(str(text).lower().split())


def check_stored(name, value, quote, page, doc, unit):
    """A stored figure with the text it came from: is the number in the text, is the text in the PDF?"""
    from .integrity import FAILING_STATES, MISSING_SOURCE_TEXT, explain_value
    from .integrity import NO_VALUE_STORED
    if not any(p.text.strip() for p in doc.pages):
        return {"verdict": "UNKNOWN", "reason": "the PDF has no text to check against"}
    try:
        page = int(page) if page is not None else None
    except (TypeError, ValueError):
        page = None
    state, _ = explain_value(value, quote, unit)
    if state == NO_VALUE_STORED:
        return {"verdict": "UNKNOWN", "reason": "no numeric value was stored"}
    if state == MISSING_SOURCE_TEXT:
        return {"verdict": "UNKNOWN", "reason": "no source text was stored with this number"}
    if state in FAILING_STATES:
        return {"verdict": "WRONG_FOR_LABEL", "lines": [f"the stored text: {str(quote)[:140]}"],
                "reason": "the stored number is not in the text it was taken from"}
    from .locate import FOUND_IN_ROW, check_claim
    said = check_claim(str(name), value, str(quote), unit)["verdict"] if name else FOUND_IN_ROW
    if said == "UNKNOWN":
        want = _norm(quote)
        where = [p.number for p in doc.pages if want in _norm(p.text)]
        if not where:
            return {"verdict": "ABSENT", "lines": [f"the stored text: {str(quote)[:140]}"],
                    "reason": "the stored text is not in the PDF"}
        pg = page if page in where else where[0]
        text = doc.pages[pg - 1].text
        i = _norm(text).find(want[:40])
        flat = " ".join(text.split())
        around = flat[max(0, i - 250): i + len(want) + 250] if i >= 0 else str(quote)
        return {"verdict": "UNKNOWN", "pages": [pg], "judge": around,
                "reason": "the stored text does not mention this item; check it by eye"}
    if said != FOUND_IN_ROW:
        return {"verdict": "WRONG_FOR_LABEL", "lines": [f"the stored text: {str(quote)[:140]}"],
                "reason": "the stored text is not about this item, or the number is not where it discusses it"}
    want = _norm(quote)
    where = [p.number for p in doc.pages if want in _norm(p.text)]
    if page is not None and page in where:
        return {"verdict": "FOUND_IN_ROW", "pages": [page]}
    if where and page is not None:
        return {"verdict": "AMBIGUOUS_LABEL", "pages": where,
                "reason": f"the text is in the PDF on page {where[0]}, not page {page}"}
    if where:
        return {"verdict": "FOUND_IN_ROW", "pages": where}
    return {"verdict": "ABSENT", "lines": [f"the stored text: {str(quote)[:140]}"],
            "reason": "the stored text is not in the PDF"}


def load_rows(path: str) -> list:
    if path.lower().endswith((".txt", ".md")):
        from .claims import extract_claims
        text = open(path, encoding="utf-8-sig").read()
        return [{"name": c.description, "value": c.value, "unit": c.unit, "scaled": c.scaled}
                for c in extract_claims(text)]
    return json.load(open(path, encoding="utf-8-sig"))


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    flags = {}
    for flag in ("--sheet", "--ask-ai", "--answers"):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 >= len(argv):
                print(f"{flag} needs a file name", file=sys.stderr)
                return 2
            flags[flag] = argv[i + 1]
            argv = argv[:i] + argv[i + 2:]
    sheet = flags.get("--sheet")
    if len(argv) != 2:
        print(__doc__)
        return 2
    try:
        doc = load_pages(argv[0])
        rows = load_rows(argv[1])
    except (OSError, ValueError) as e:        # missing file, not a PDF, not valid JSON
        print(f"cannot read the input: {e}", file=sys.stderr)
        return 2
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        print('results.json must be a list of figures like [{"name": "...", "value": 1}]', file=sys.stderr)
        return 2
    if not rows:
        print("no figures found to check; nothing was verified", file=sys.stderr)
        return 2
    answers = {}
    if "--answers" in flags:
        try:
            raw = json.load(open(flags["--answers"], encoding="utf-8-sig"))
            raw = raw.get("answers", raw) if isinstance(raw, dict) else raw
            answers = {int(a["id"]): str(a["answer"]).strip().lower() for a in raw}
        except (OSError, ValueError, KeyError, TypeError) as e:
            print(f"cannot read the AI's answers: {e}", file=sys.stderr)
            return 2
    ask = []
    bad = wrong = 0
    to_look_at = []
    for idx, row in enumerate(rows):
        name, value = _pick(row, NAME), _pick(row, VALUE)
        if not isinstance(row.get("unit"), str):
            row = {**row, "unit": None}
        quote = _pick(row, QUOTE)
        if quote is not None:
            r = check_stored(name, value, quote, row.get("page"), doc, row.get("unit"))
        elif row.get("scaled"):
            r = {"verdict": "UNKNOWN", "reason": "written with a scale (million, billion, k); check it by eye"}
        else:
            r = check_in_document(str(name or ""), value, doc, unit=row.get("unit"))
        if r.get("judge"):
            ask.append({"id": idx, "name": name, "value": value, "quote": quote, "context": r["judge"]})
            said = answers.get(idx)
            if said == "yes":       # only reachable when the number is in the quote and the quote is on the page
                r = {"verdict": "FOUND_IN_ROW", "pages": r["pages"]}
            elif said == "no":
                r = {"verdict": "WRONG_FOR_LABEL", "lines": [f"the stored text: {str(quote)[:140]}"],
                     "reason": "the AI read the text and says the number belongs to something else"}
            elif said == "unsure":
                r = {**r, "reason": "the AI could not tell either; check it by eye"}
        word = SAYS[r["verdict"]]
        pages = r.get("pages")
        where = f", page {pages[0]}" if pages and len(pages) == 1 else (f", pages {pages}" if pages else "")
        shown = f"{int(value):,}" if isinstance(value, (int, float)) and float(value).is_integer() else value
        print(f"{word:8s} {name} = {shown}{where}")
        if word == "WRONG" and r.get("lines"):
            print(f"         {_plain(r['reason'])}" if quote is not None else f"         {_report_has(r['lines'][0])}")
        if word == "CHECK":
            print(f"         {_plain(r['reason'])}")
            if r.get("found_pages"):
                pg = ", ".join(map(str, r["found_pages"][:5]))
                print(f"         The number is on page {pg}: {r['found_line']}")
        bad += word != "CORRECT"
        wrong += word == "WRONG"
        if word != "CORRECT":
            page = (r.get("found_pages") or r.get("pages") or [row.get("page")])[0] if (r.get("found_pages") or r.get("pages") or row.get("page")) else None
            to_look_at.append({"word": word, "name": name, "value": value, "shown": shown, "page": page,
                               "why": r.get("reason") or "the number is not where this item is discussed"})
    if "--ask-ai" in flags:
        with open(flags["--ask-ai"], "w", encoding="utf-8") as f:
            json.dump({"instructions": JUDGE_INSTRUCTIONS, "items": ask}, f, indent=1, ensure_ascii=False)
        print(f"\n{len(ask)} figures for your AI to read: {flags['--ask-ai']}")
    if sheet and to_look_at:
        from .sheet import write_sheet
        n = write_sheet(argv[0], to_look_at, sheet)
        print(f"\n{n} figures to look at, with the page pictured: {sheet}")
    print(f"\nAll {len(rows)} figures are correct." if not bad else
          f"\n{bad} of {len(rows)} need your attention: {wrong} wrong, {bad - wrong} to check.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
