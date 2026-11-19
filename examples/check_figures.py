"""Check a list of figures against the PDF they came from.

usage: python examples/check_figures.py report.pdf figures.csv

figures.csv has three columns: what the figure is about, the number, and the page it came
from (as the AI reported it). An optional fourth column, unit, can hold m, m2, hours, % or
storeys. See examples/figures.csv.

Prints one entry per figure: what the AI said, and for anything that did not pass, the line
of the page it was checked against and why. Exit code 0 if every figure passed, 1 if any
needs attention, so it can sit in a pipeline.
"""
import csv
import sys

import pdfplumber

from proof_layer.locate import check_claim

INDENT = " " * 9


def fmt(value, raw: str) -> str:
    """The number as people write it: 19691 -> 19,691."""
    if value is not None and float(value).is_integer():
        return f"{int(value):,}"
    return raw.strip()


def explain(verdict: str, number: str, result: dict) -> tuple[str, list[str]]:
    """(outcome word, lines to print under the figure)."""
    shown = result.get("lines", [])
    if verdict == "FOUND_IN_ROW":
        return "PASSED", []
    if verdict == "WRONG_FOR_LABEL":
        return "STOPPED", [f"page says: {shown[0]}", f"{number} is on this page, but for something else"]
    if verdict == "ABSENT":
        said = [f"page says: {shown[0]}"] if shown else []
        return "STOPPED", said + [f"{number} is not on the page"]
    if verdict == "AMBIGUOUS_LABEL":
        return "CONFIRM", [f"fits {result['candidates']} places on the page:"] + [f"  {s}" for s in shown]
    return "CONFIRM", ["nothing on the page is about this"]


def main(pdf_path: str, csv_path: str) -> int:
    needs_attention = 0
    with pdfplumber.open(pdf_path) as pdf, open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            label, page_no = row["about"].strip(), int(row["page"])
            try:
                value = float(row["number"].replace(",", ""))
            except ValueError:
                value = None
            text = pdf.pages[page_no - 1].extract_text() or ""
            result = check_claim(label, value, text, unit=(row.get("unit") or "").strip() or None)
            number = fmt(value, row["number"])
            word, detail = explain(result["verdict"], number, result)
            needs_attention += word != "PASSED"
            print(f"{word:8s} {label} = {number}   (p{page_no})")
            for line in detail:
                print(INDENT + line)
    print()
    print("all figures passed" if not needs_attention else f"{needs_attention} figure(s) need attention")
    return 1 if needs_attention else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
