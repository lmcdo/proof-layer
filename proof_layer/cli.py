"""proof-layer report.pdf results.json  ->  checks every figure your code returned.

results.json is a list of figures: [{"name": "Scope 1 emissions", "value": 5845}, ...].
Field names are found automatically (name/label/about/item, value/number/amount, unit).
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


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__)
        return 2
    doc = load_pages(argv[0])
    rows = json.load(open(argv[1], encoding="utf-8"))
    bad = 0
    for row in rows:
        name, value = _pick(row, NAME), _pick(row, VALUE)
        r = check_in_document(str(name or ""), value, doc, unit=row.get("unit"))
        word = SAYS[r["verdict"]]
        pages = r.get("pages")
        where = f", page {pages[0]}" if pages and len(pages) == 1 else (f", pages {pages}" if pages else "")
        shown = f"{value:,}" if isinstance(value, (int, float)) and float(value).is_integer() else value
        print(f"{word:8s} {name} = {shown}{where}")
        if word == "WRONG" and r.get("lines"):
            print(f"         the report says: {r['lines'][0]}")
        if word == "CHECK":
            print(f"         {r['reason']}")
        bad += word != "CORRECT"
    print("\nall correct" if not bad else f"\n{bad} need attention")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
