"""Check a list of figures against the PDF they came from.

usage: python examples/check_figures.py report.pdf figures.csv

figures.csv has three columns: what the figure is about, the number, and the page it came
from (as the AI reported it). An optional fourth column, unit, can hold m, m2, hours, % or
storeys. See examples/figures.csv.

Prints one line per figure in plain words. Exit code 0 if every figure passed, 1 if any
needs attention, so it can sit in a pipeline.
"""
import csv
import sys

import pdfplumber

from proof_layer.locate import check_claim

PLAIN = {
    "FOUND_IN_ROW": ("PASSED", ""),
    "WRONG_FOR_LABEL": ("STOPPED", "the number is on the page, but it belongs to something else"),
    "ABSENT": ("STOPPED", "the number is not on the page"),
    "AMBIGUOUS_LABEL": ("CONFIRM", "several places on the page fit this description"),
    "UNKNOWN": ("CONFIRM", "could not find where the page discusses this"),
}


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
            word, why = PLAIN[result["verdict"]]
            if word != "PASSED":
                needs_attention += 1
            print(f"{word:8s} p{page_no}  {label}: {row['number']}" + (f"   ({why})" if why else ""))
    total_note = "all figures passed" if not needs_attention else f"{needs_attention} figure(s) need attention"
    print(f"\n{total_note}")
    return 1 if needs_attention else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
