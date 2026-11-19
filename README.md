# proof-layer

**Catches the wrong numbers an AI pulls out of your documents, so you only re-check the ones that need it.**

An AI reads a report and writes "Scope 1 emissions: 19,691". proof-layer checks that number against the document. Right numbers pass automatically. Wrong ones are stopped. Anything it can't confirm goes to a person, with the reason. It never guesses.

## A real workflow

You're preparing a client's climate disclosure. 40 company reports, and the figures need to go into a spreadsheet.

1. **The AI extracts the figures.** 500 numbers, each with what it is about ("Scope 1 emissions", "Total energy use") and the page it came from.
2. **proof-layer checks all 500 in one go.** About 440 pass. Nobody touches them.
3. **You review the rest, about 60,** starting with the stopped ones. Each comes with a one-line reason.
4. **You fix, confirm or correct each one.** Then the spreadsheet goes out, and you can say every number was checked against its source.

**Time saved.** Without proof-layer, someone checks all 500 by hand. With it, they check about 60. If a check takes 3 minutes, that is roughly 25 hours down to roughly 3. Use your own minutes per check. The 60 in 500 comes from the test below. The held-back ones are the harder ones, so allow a bit more time per number than average.

## What you get back

| Outcome | What it means | What to do |
|---|---|---|
| **Passed** | The number is written where the page talks about this item | Nothing. Use it |
| **Stopped** | The number isn't on the page, or it's on the page but belongs to something else | Look at it first. In the test, nearly all of these were real errors |
| **Needs a person** | Several places on the page fit, or none clearly does, so it won't guess | Take a quick look and decide |

Only "Passed" passes. "I can't tell" is never treated as fine.

## Handling the exceptions

Work through the held-back list from the top:

- **Stopped.** The AI most likely got it wrong. Correct it. Rarely, the description matched the wrong part of the page. A glance at the page tells you which.
- **Needs a person, "several places fit".** The most common case: "Total water" appears in three tables. Make the description more specific ("Water withdrawn in water-stressed areas") and run it again. This usually resolves it. Or just check the page.
- **Needs a person, "couldn't find where the page discusses this".** The AI described it in very different words from the page. Check the page, or use the page's wording.

Every held-back number comes with its reason, so you know which case you're in before you open the document.

**What to expect:** about 88 in 100 right numbers pass on their own. The rest need a look. When the description uses the page's own words, it is mostly the "several places fit" kind. When the wording differs a lot, more are "couldn't find". In the test, nearly every wrong number was stopped.

## How this is different

| | What it does | What it doesn't do |
|---|---|---|
| **RAG** (search the documents, then answer) | Helps the AI find the right passage | Doesn't check the answer afterwards. The AI can read the right passage and still write the wrong number |
| **"Cite your source" prompts** | Asks the AI to show where a number came from | The AI can cite a real passage and still be wrong about the number |
| **A second AI to double-check** | Gets another opinion | Another AI can be wrong too, and may give a different answer tomorrow |
| **proof-layer** | Compares each number to the document text with fixed rules. Same answer every time, no AI involved, no per-check cost | It checks the number against the text. It can't judge whether the document itself is right |

It sits after any AI, RAG system or extraction tool. You keep what you already use.

## Who it's for

Anyone who has to stand behind figures that an AI read from documents: sustainability and audit teams checking climate and annual reports, finance, procurement and compliance teams pulling numbers from contracts, invoices and filings, and anyone building a product that shows users figures taken from their documents.

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

# Nothing on the page is about Scope 3, so it can't tell. It does not pass.
assert check_claim("Scope 3 emissions", 5845, page)["verdict"] == "UNKNOWN"
```

In the code the outcomes are: `FOUND_IN_ROW` = Passed; `WRONG_FOR_LABEL` and `ABSENT` = Stopped; `AMBIGUOUS_LABEL` and `UNKNOWN` = Needs a person.

## Results

Tested on two real public company sustainability reports. I took real numbers from them, then made 2,392 deliberately wrong versions: a digit changed, two digits swapped, multiplied by ten, the sign flipped, or a number borrowed from elsewhere on the same page.

| | Wrong numbers stopped | Right numbers sent to a person |
|---|---|---|
| Only checking the number appears somewhere on the page | 69 in 100 | 0 |
| **proof-layer** | **99.9 in 100** (2,389 of 2,392) | **12 in 100** (17 if the description is worded differently from the page) |

Two separate runs of the test gave identical results.

Run it yourself: `python -I benchmarks/located_wrong_numbers.py out.json report1.pdf report2.pdf` (needs `pip install ".[benchmarks]"`).

## Know before you use it

- **Early.** Tested on two reports so far.
- **It checks the number is there, not what it means.** A year like 2024 can pass as a quantity. Give it the unit (metres, %, tonnes) when you know it.
- **It can't tell which year's column a number is from** when two numbers sit on the same line.

## What's inside

- `proof_layer/locate.py`: finds the part of the page that discusses the item, then checks the number there.
- `proof_layer/integrity.py`: the number check itself. It knows the legitimate reasons a number can differ from its text (35% written as 0.35, 900 mm as 0.9 m) and says "unexplained" when none fits.
- `tests/`: 66 passing tests and 6 expected failures that mark the known limits above. The code above is run as a test.
- `benchmarks/`: the test scripts and saved results.

Apache-2.0. Copyright 2026 Lawrence McDonell.
