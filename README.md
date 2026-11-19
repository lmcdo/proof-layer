# proof-layer

**Catches the wrong numbers an AI pulls out of your documents, before they reach a client, a regulator or a board.**

You ask an AI to read a report and list the figures. It answers "Scope 1 emissions: 19,691". Is that number really in the document? And is it the number for Scope 1, or did the AI grab the one next to it?

proof-layer checks each number against the document's own text. Right numbers pass. Anything it can't confirm is held back for a person, with the reason. It never guesses.

## The problem

AI that reads documents is usually right, and sometimes wrong in ways nobody sees: an invented figure, two digits swapped, a number lifted from a different line, a minus sign dropped. You find out after it's in the report.

Checking by hand means re-reading the document, which is the work you wanted the AI to do.

## How this is different

| | What it does | What it doesn't do |
|---|---|---|
| **RAG** (search the documents, then answer) | Helps the AI find the right passage | Doesn't check the answer afterwards. The AI can read the right passage and still write the wrong number |
| **"Cite your source" prompts** | Asks the AI to show where a number came from | The AI can cite a real passage and still be wrong about the number |
| **A second AI to double-check** | Gets another opinion | Another AI can be wrong too, and may give a different answer tomorrow |
| **proof-layer** | Compares each number to the document text with fixed rules. Same answer every time, no AI involved, no per-check cost | It checks the number against the text. It can't judge whether the document itself is right |

It sits after any AI, RAG system or extraction tool. You keep what you already use.

## Who it's for

Anyone who has to stand behind figures that an AI read from documents:

- **Sustainability and audit teams** checking figures in climate and annual reports
- **Finance, procurement and compliance teams** pulling numbers from contracts, invoices and filings
- **Anyone building a product** that shows users figures taken from their documents

**The business case:** if people now re-read documents to confirm what the AI extracted, proof-layer does the routine part. In the test below, about 88 in 100 right numbers passed automatically, and the other 12 went to a person with the reason. Nearly every wrong number was stopped. (Time saved in real workflows hasn't been measured yet. The test measured accuracy.)

## What you get back

For each number you give it the text of the page, the number, and what it is about ("Scope 1 emissions").

| Answer | What it means | Passes? |
|---|---|---|
| **Found** | The number is written where the page talks about this | Yes |
| **Wrong place** | The number is in the document, but not where this is discussed | No |
| **Not there** | The number isn't on the page at all | No |
| **Unclear which** | The description fits more than one place on the page, so it can't tell which you mean. A person should look | No |
| **Can't tell** | It couldn't find where the page discusses this, so it didn't guess | No |

Only "Found" passes. "I can't tell" is never treated as fine.

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

# 19,691 is on the page, but it is the Scope 2 figure: caught.
assert check_claim("Scope 1 emissions", 19691, page)["verdict"] == "WRONG_FOR_LABEL"

# A number that isn't on the page at all: caught.
assert check_claim("Scope 1 emissions", 5846, page)["verdict"] == "ABSENT"

# Nothing on the page is about Scope 3, so it says it can't tell. It does not pass.
assert check_claim("Scope 3 emissions", 5845, page)["verdict"] == "UNKNOWN"
```

The code names for the five answers, in table order: `FOUND_IN_ROW`, `WRONG_FOR_LABEL`, `ABSENT`, `AMBIGUOUS_LABEL`, `UNKNOWN`.

## Results

Tested on two real public company sustainability reports. I took real numbers from them, then made 2,392 deliberately wrong versions: a digit changed, two digits swapped, multiplied by ten, the sign flipped, or a number borrowed from elsewhere on the same page.

| | Wrong numbers stopped | Right numbers sent to a person |
|---|---|---|
| Only checking the number appears somewhere on the page | 69 in 100 | 0 |
| **proof-layer** | **99.9 in 100** (2,389 of 2,392) | **12 in 100** (17 if the description is worded differently from the page) |

The 12 are the price of never guessing: usually a description that fits several places on a page, such as "Total water". Two separate runs of the test gave identical results.

Run it yourself: `python -I benchmarks/located_wrong_numbers.py out.json report1.pdf report2.pdf` (needs `pip install ".[benchmarks]"`).

## Know before you use it

- **Early.** Tested on two reports so far.
- **It checks the number is there, not what it means.** A year like 2024 can pass as a quantity. Give it the unit (metres, %, tonnes) when you know it.
- **It needs words from the page to find the right spot.** If the AI describes a figure in very different words ("Energy use" for "Total energy consumption"), it says "can't tell" and a person decides. Wrong numbers were still stopped in those cases.

## What's inside

- `proof_layer/locate.py`: finds the part of the page that discusses the description, then checks the number there.
- `proof_layer/integrity.py`: the number check itself. It knows the legitimate reasons a number can differ from its text (35% written as 0.35, 900 mm as 0.9 m) and says "unexplained" when none fits.
- `tests/`: 66 passing tests and 6 expected failures that mark the known limits above. The code above is run as a test.
- `benchmarks/`: the test scripts and saved results.

Apache-2.0. Copyright 2026 Lawrence McDonell.
