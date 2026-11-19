# proof-layer

Checks that a number an AI took from a document is really in that document, on the right row.

**Status: early. Tested on two public reports. Not independently reviewed.**

## The problem

An AI reads a report and writes down "Scope 1 emissions = 19,691". That number is on the page. But it belongs to Scope 2. A check that only asks "is this number on the page?" says fine, and the wrong number goes through.

## What it does

You give it a label ("Scope 1 emissions"), a number, and the page text. It finds the row that carries the label, then checks the number against that row only. It never guesses.

| Answer | Meaning | Passes? |
|---|---|---|
| `FOUND_IN_ROW` | One row matches the label and the number is written in it | Yes |
| `AMBIGUOUS_LABEL` | Several rows match the label, so it cannot tell which one you mean | No, a person checks |
| `WRONG_FOR_LABEL` | The number is on the page, but not on that label's row | No |
| `ABSENT` | The number is not on the page at all | No |
| `UNKNOWN` | It cannot judge: no text, no number, or no row matches the label | No |

Only the first answer passes. "I can't tell" is never treated as fine.

## Install and quickstart

```
pip install .            # from a clone; the library itself has no dependencies
pip install ".[benchmarks]"   # adds pdfplumber, needed only to run the benchmarks
```

```python
from proof_layer.locate import check_claim

page = "Scope 1 emissions 5,845 6,102\nScope 2 emissions 19,691 18,400"

# right number on its own row: the only answer that passes
assert check_claim("Scope 1 emissions", 5845, page)["verdict"] == "FOUND_IN_ROW"
# 19,691 is on the page, but it belongs to Scope 2
assert check_claim("Scope 1 emissions", 19691, page)["verdict"] == "WRONG_FOR_LABEL"
# not on the page at all
assert check_claim("Scope 1 emissions", 5846, page)["verdict"] == "ABSENT"
# no row carries this label, so it cannot judge, and it does not pass
assert check_claim("Scope 3 emissions", 5845, page)["verdict"] == "UNKNOWN"
```

## Results

Test: 553 true claims taken from two public reports (Alinta Energy FY25, Geelong Port 2025). Each was turned into wrong claims in five ways: one digit changed, two digits swapped, times ten, sign flipped, a number taken from another row. 2,392 wrong claims in total. The random seed is fixed.

| Check | Wrong numbers caught | True numbers held back |
|---|---|---|
| Number anywhere on the page | 68.7% | 0.0% |
| **Label row (this tool)**, label as printed | **99.9%** | 12.1% |
| Label row, with two extra words | 99.9% | 17.0% |

3 of 2,392 wrong numbers still passed. Most of the held-back true claims are labels that match more than one row, such as "GRI" in an index table.

Reproduce: `python -I benchmarks/located_wrong_numbers.py out.json <report1.pdf> <report2.pdf>` Two separate runs gave identical output.

## Limits

- **It proves a number is written in a row. It does not prove what the number means.** A year such as 2024 can pass as a setback. This is recorded as a known failing test.
- **12–17% of correct numbers are held back** for a person to check. That is the price of not guessing.
- **The label test was easy.** Labels came from the same line, with filler words added or the order shuffled. A separate hand-written test of 9 realistic label pairs found the right row for 4 and held 5 back as UNKNOWN: "Energy use" for "Total energy consumption", "Water withdrawal" for "Water withdrawn", the abbreviation "LTIFR", and "Female representation" for "Women". Every wrong number under those labels was still held back.
- **Pass the unit when you know it.** Without one, "100%" can explain a claimed 1.0. That is correct for a fraction, and wrong if the number was months.
- **It cannot tell which column of a row a number belongs to.** A number from the other year's column on the same row passes.
- **Tested on Python 3.11 only.** `pyproject.toml` says 3.10 or newer; that is untested.
- **Two documents only**, both climate-style reports. Scanned pages and tables whose labels sit apart from their numbers are untested.
- **Number checks use the page text as the PDF reader gives it.** A bad reading of a page gives bad results.

## Layout

- `proof_layer/integrity.py`: checks one number against one piece of text. 10 named rules explain why a stored number can differ from its source (35% stored as 0.35, 900 mm as 0.9 m, "3m x 3m" as 9). If none fits, it says UNEXPLAINED.
- `proof_layer/locate.py`: finds the label's row, then calls the check above.
- `tests/`: 66 passing tests and 6 expected failures. Breaking the checker on purpose in 6 ways was caught every time.
- `benchmarks/`: the two benchmark scripts and their saved results.

## Tests

`python -m pytest`. The README quickstart above is run as a test, so it cannot go stale.
