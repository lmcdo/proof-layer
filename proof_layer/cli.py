"""proof-layer report.pdf results.json  ->  checks every figure your code returned.

results.json is a list of figures: [{"name": "Scope 1 emissions", "value": 5845}, ...].
Field names are found automatically (name/label/about/item, value/number/amount, unit).
If the second file is plain text (.txt/.md), it is an AI's written answer instead: every figure
in it is found and checked. Figures written as "5.2 million" are always passed to you to check.
If a figure also carries the text it was taken from ("source_text", plus "page" if known), as it
does when it is stored in a database, two things are checked: that the stored number really is in
that text, and that the text really is in the PDF (on that page, if you gave one).
Exit code 0 if every figure is correct, 1 if any needs attention.
"""
import json
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


QUOTE = ("source_text", "quote", "evidence", "source")


def _norm(text: str) -> str:
    return " ".join(str(text).lower().split())


def check_stored(name, value, quote, page, doc, unit):
    """A stored figure with the text it came from: is the number in the text, is the text in the PDF?"""
    from .integrity import FAILING_STATES, MISSING_SOURCE_TEXT, explain_value
    state, _ = explain_value(value, quote, unit)
    if state == MISSING_SOURCE_TEXT:
        return {"verdict": "UNKNOWN", "reason": "no source text was stored with this number"}
    if state in FAILING_STATES:
        return {"verdict": "WRONG_FOR_LABEL", "lines": [f"the stored text: {str(quote)[:140]}"],
                "reason": "the stored number is not in the text it was taken from"}
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
        text = open(path, encoding="utf-8").read()
        return [{"name": c.description, "value": c.value, "unit": c.unit, "scaled": c.scaled}
                for c in extract_claims(text)]
    return json.load(open(path, encoding="utf-8"))


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__)
        return 2
    doc = load_pages(argv[0])
    rows = load_rows(argv[1])
    bad = 0
    for row in rows:
        name, value = _pick(row, NAME), _pick(row, VALUE)
        quote = _pick(row, QUOTE)
        if quote is not None:
            r = check_stored(name, value, quote, row.get("page"), doc, row.get("unit"))
        elif row.get("scaled"):
            r = {"verdict": "UNKNOWN", "reason": "written with a scale (million, billion, k); check it by eye"}
        else:
            r = check_in_document(str(name or ""), value, doc, unit=row.get("unit"))
        word = SAYS[r["verdict"]]
        pages = r.get("pages")
        where = f", page {pages[0]}" if pages and len(pages) == 1 else (f", pages {pages}" if pages else "")
        shown = f"{int(value):,}" if isinstance(value, (int, float)) and float(value).is_integer() else value
        print(f"{word:8s} {name} = {shown}{where}")
        if word == "WRONG" and r.get("lines"):
            print(f"         {r['reason']}" if quote is not None else f"         the report says: {r['lines'][0]}")
        if word == "CHECK":
            print(f"         {r['reason']}")
        bad += word != "CORRECT"
    print("\nall correct" if not bad else f"\n{bad} need attention")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
