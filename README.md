# proof-layer

**Every number your AI pulls from a document, checked against that document.**

An AI reads a report and writes "Scope 1 emissions: 19,691". proof-layer confirms that number is in the document, and that it belongs to Scope 1. Right numbers pass straight through. Wrong ones are stopped. If it can't tell, it asks you instead of guessing.

- **Right numbers pass on their own.** In testing, 88 in 100 right numbers needed no one.
- **Wrong numbers are stopped.** 99.9 in 100 in testing (2,389 of 2,392 deliberately wrong numbers).
- **Same answer every time.** Fixed rules, no second AI, no cost per check.
- **Works with what you already use.** Any AI, any extraction tool, any RAG setup.

## How it fits into your work

You're preparing a client's climate disclosure from 40 company reports.

1. **Your AI extracts the figures.** 500 numbers, each with what it is about ("Scope 1 emissions", "Total energy use").
2. **proof-layer checks all 500.** Most pass straight through, already confirmed against the source.
3. **The few it asks about come back with a one-line reason,** such as "the same wording appears in two tables". You confirm them.
4. **You send the spreadsheet knowing every figure was checked against its source.**

**Time saved.** Instead of checking all 500 by hand, you confirm the handful it asks about. At 3 minutes a check, 500 numbers is about 25 hours by hand. At the test's rate of 12 in 100 that need confirming, it is about 3 hours. Use your own minutes per check. (The held-back numbers may take a little longer than average.)

## What you get back

| Outcome | What it means | What to do |
|---|---|---|
| **Passed** | The number is written where the page talks about this item | Nothing. Use it |
| **Stopped** | The number isn't on the page, or it belongs to something else | Correct it. In testing, nearly all of these were real errors |
| **Confirm** | The page has several places that fit, or none that clearly does, so it asks you instead of guessing | A quick look, or give a more specific description and run it again |

Only "Passed" passes. A "can't tell" is never treated as fine.

In the code: `FOUND_IN_ROW` = Passed; `WRONG_FOR_LABEL` and `ABSENT` = Stopped; `AMBIGUOUS_LABEL` and `UNKNOWN` = Confirm.

## Works alongside RAG and cite-your-source prompts

| | What it gives you | Where proof-layer comes in |
|---|---|---|
| **RAG** (search the documents, then answer) | Finds the right passage for the AI | Checks the number the AI wrote from that passage |
| **"Cite your source" prompts** | Shows where the AI says a number came from | Checks the number is really there |
| **A second AI as reviewer** | Another opinion | A fixed check that gives the same answer every time and costs nothing per number |

Keep what you have. proof-layer is the last step before the numbers go out.

## Who it's for

Anyone who stands behind figures that an AI read from documents: sustainability and audit teams, finance, procurement and compliance teams working from contracts, invoices and filings, and products that show users figures from their own documents.

## How to use it

You need two things: the PDF, and the list of figures your AI pulled from it (what each is about, the number, the page).

1. **Install it** (needs Python): `pip install ".[pdf]"`
2. **Put your figures in a spreadsheet saved as CSV,** with three columns: `about`, `number`, `page`. See `examples/figures.csv`.
3. **Run it:**

```
python examples/check_figures.py examples/sample_report.pdf examples/figures.csv
```

4. **Read the result.** One line per figure:

```
PASSED   p1  Scope 1 emissions: 5845
PASSED   p1  Scope 2 emissions: 19691
STOPPED  p1  Scope 1 emissions: 19691   (the number is on the page, but it belongs to something else)
STOPPED  p1  Scope 2 emissions: 19000   (the number is not on the page)
PASSED   p1  Total energy consumption: 1074807
CONFIRM  p1  Water withdrawn: 22.975   (several places on the page fit this description)
CONFIRM  p1  Water withdrawn: 3.8   (several places on the page fit this description)
CONFIRM  p1  Scope 3 emissions: 5845   (could not find where the page discusses this)

5 figure(s) need attention
```

`PASSED` figures are done. `STOPPED` ones are errors to correct. `CONFIRM` ones need a quick look at the page, or a more specific description in the `about` column and a re-run. The script exits with 1 if anything needs attention, so it can run as a step in a pipeline.

Building this into your own tool? The one function is in the next section.

## Install and quickstart

```
pip install .
```

```python
from proof_layer.locate import check_claim

page = """Scope 1 emissions 5,845 6,102
Scope 2 emissions 19,691 18,400"""

# The right number, where the page discusses Scope 1: passes.
assert check_claim("Scope 1 emissions", 5845, page)["verdict"] == "FOUND_IN_ROW"

# 19,691 is on the page, but it is the Scope 2 figure: stopped.
assert check_claim("Scope 1 emissions", 19691, page)["verdict"] == "WRONG_FOR_LABEL"

# A number that isn't on the page at all: stopped.
assert check_claim("Scope 1 emissions", 5846, page)["verdict"] == "ABSENT"

# Nothing on the page is about Scope 3, so it asks instead of guessing.
assert check_claim("Scope 3 emissions", 5845, page)["verdict"] == "UNKNOWN"
```

## Results

Version 0.1.0, tested on two real public company sustainability reports. I took real numbers from them, then made 2,392 deliberately wrong versions: a digit changed, two digits swapped, multiplied by ten, the sign flipped, or a number borrowed from elsewhere on the same page.

| | Wrong numbers stopped | Right numbers it asks you to confirm |
|---|---|---|
| Only checking the number appears somewhere on the page | 69 in 100 | 0 |
| **proof-layer** | **99.9 in 100** (2,389 of 2,392) | **12 in 100** |

The 12 in 100 are not errors. They are numbers it wouldn't guess at, mostly because the same wording appears in several tables of one report, like "Total water". The test used a random sample of all the numbers in both reports, including index tables and chart labels. Two separate runs gave identical results.

Run it yourself: `python -I benchmarks/located_wrong_numbers.py out.json report1.pdf report2.pdf` (needs `pip install ".[benchmarks]"`).

## Tips for the best results

- **Be specific.** "Water withdrawn in water-stressed areas" passes where "Total water" would ask you to confirm.
- **Give the unit** (metres, %, tonnes) when you know it.
- **Two years side by side on one line:** it confirms the number is on the line but doesn't pick the year.

## What's inside

- `proof_layer/locate.py`: finds the part of the page that discusses the item, then checks the number there.
- `proof_layer/integrity.py`: the number check itself. It recognises the legitimate ways a number can be written differently (35% as 0.35, 900 mm as 0.9 m).
- `tests/`: 67 passing tests, plus 6 marked expected failures that record the cases above. The code above is run as a test.
- `benchmarks/`: the test scripts and saved results.

Apache-2.0. Copyright 2026 Lawrence McDonell.
