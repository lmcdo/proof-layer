# proof-layer

I've used AI every day for about two years. It kept making up figures, telling me what I wanted to hear, and reporting work as done when it wasn't, most often when I asked it to work with data. So I built proof-layer: instead of trusting the AI's word, it checks each number against the source. It's useful wherever knowing where a number came from matters most.

**Every number your AI pulls from a document, checked against that document.**

![proof-layer checking 8 figures an AI took from a report: 3 passed, 2 stopped, 3 to confirm](docs/demo.gif)

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

## An example, start to finish

**The situation.** A sustainability consultant is preparing a client's climate disclosure. By law, companies now have to report their emissions and energy use, and an auditor will later pick figures at random and ask: *where did this number come from?* The consultant's source is the client's own 80-page sustainability report (a PDF). Copying figures out of it by hand takes days, so she has an AI read the report and fill in the disclosure table.

**The risk.** The AI is usually right, but not always. It might copy the Scope 2 figure into the Scope 1 box (they sit next to each other in the report). Or the table has a Scope 3 line and the AI fills it in even though the report never gives one. If that reaches the auditor, the consultant is the one who signed it.

**What goes in.** Two things she already has:
1. **The report**, as the PDF.
2. **The AI's filled-in table**, which says:

| Disclosure line | AI's figure |
|---|---|
| Scope 1 emissions | 5,845 |
| Scope 1 emissions (second try) | 19,691 |
| Total energy consumption | 1,074,807 |
| Scope 3 emissions | 5,845 |

**What she wants back.** Which figures are safe to submit, which are wrong, and for each one, the page and line of the report it comes from, so she can answer the auditor.

**1. Save the AI's table** as a file, `results.json`. If your software produced it, it's probably already in this form:

```
[
  {"name": "Scope 1 emissions", "value": 5845},
  {"name": "Scope 1 emissions", "value": 19691},
  {"name": "Total energy consumption", "value": 1074807},
  {"name": "Scope 3 emissions", "value": 5845}
]
```

**2. Run one command** with the PDF and that file (install first with `pip install ".[pdf]"`):

```
proof-layer sample_report.pdf results.json
```

**3. Read the answer.** It looks every number up in the PDF:

```
CORRECT  Scope 1 emissions = 5,845, page 1
WRONG    Scope 1 emissions = 19,691, page 1
         the report says: p1: Scope 1 emissions (tCO2-e) 5,845 6,102
CORRECT  Total energy consumption = 1,074,807, page 1
CHECK    Scope 3 emissions = 5,845
         nothing in the document is clearly about this; the number appears elsewhere

2 need attention
```

- **Scope 1 = 5,845:** correct, found on page 1.
- **Scope 1 = 19,691:** wrong. That number is in the report, but it belongs to Scope 2. It shows you the line the report has for Scope 1.
- **Total energy = 1,074,807:** correct.
- **Scope 3 = 5,845:** it won't guess. Nothing in the report clearly talks about Scope 3, so it says check.

So she can submit 2 figures with the page to point to, fix 1 (it caught the Scope 1/Scope 2 mix-up), and chase 1 (the report has no Scope 3 figure, so the AI made it up or took it from elsewhere). That took seconds, and she only opened the PDF for that last one.

**No table? Paste the answer instead.** If you just have the AI's written reply, save it as `answer.txt` and run `proof-layer sample_report.pdf answer.txt`. It finds every figure in the text and checks each one the same way (try `examples/ai_answer.txt`). Figures written as "5.2 million" are handed to you to check by eye.

`sample_report.pdf` is a made-up one-page report in the `examples` folder, so you can run this yourself. You don't need page numbers: it searches the whole PDF and tells you the page. It exits with 1 if anything needs attention, so it can also stop a pipeline.

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

- **Be specific in the description of each figure.** It is the one thing you control. Write it the way the report words it, and add whatever makes the item unique: the table name, "market-based", the scope number. "Water withdrawn in water-stressed areas" passes where "Total water" would ask you to confirm. A quick way: copy the words from the line in the PDF.
- **Include the unit in your results where you can.** A `unit` of `m`, `m2`, `hours`, `%` or `storeys` stops a 3 metre figure being matched to "3 hours of sunlight". Other units (tonnes, GJ, ML) are accepted but make no difference yet.
- **Two years side by side on one line:** it confirms the number is on the line but doesn't pick the year.

## What's inside

- `proof_layer/locate.py`: finds the part of the page that discusses the item, then checks the number there.
- `proof_layer/integrity.py`: the number check itself. It recognises the legitimate ways a number can be written differently (35% as 0.35, 900 mm as 0.9 m).
- `tests/`: 96 passing tests, plus 6 marked expected failures that record the cases above. The code above is run as a test.
- `benchmarks/`: the test scripts and saved results.

Apache-2.0. Copyright 2026 Lawrence McDonell.
