# proof-layer

I've used AI every day for about two years. It kept making up figures, telling me what I wanted to hear, and reporting work as done when it wasn't, most often when I asked it to work with data. So I built proof-layer: instead of trusting the AI's word, it checks each number against the source. It's useful wherever knowing where a number came from matters most.

**Checks every number an AI pulls from your PDFs against the PDF itself.** Wrong ones are caught before you rely on them.

![proof-layer checking 6 figures an AI took from a report: 4 correct, 2 wrong](docs/demo.gif)

## Why use it

- **It catches wrong numbers.** In tests on 5 real reports (climate, finance, government), it stopped all 888 and all 1,247 deliberately wrong numbers (1,244 of 1,247 with padded wording).
- **It runs by itself.** Code checks each number against the PDF. Your own AI settles the unclear ones. Only the real exceptions reach you: 5 of 35 figures on the Reserve Bank's annual report, 2 of 43 on two climate reports.
- **It works on any PDF with text,** with any AI. You don't change your workflow, you add one command at the end.

## How to use it

**1. Ask your AI for figures with their source.** Paste [PROMPT.md](PROMPT.md) into the AI you already use, with your PDF and your question. Save the reply as `answer.json` (each figure comes with its page and the exact quote).

**2. Install, once.**

```
git clone https://github.com/lmcdo/proof-layer
cd proof-layer
pip install ".[pdf]"
```

**3. Run.**

```
proof-layer report.pdf answer.json --judge claude
```

You get CORRECT, WRONG or CHECK for each figure, with the page. Add `--sheet check.html` for a picture of the page, number highlighted, for anything left. The command exits with 1 if anything needs attention, so it can stop a pipeline.

Try it now: `proof-layer examples/sample_report.pdf examples/answer.json --judge claude`.

## Good to know

- **Needs a PDF with a text layer.** Scans and photos aren't read.
- **Figures your AI worked out itself** (a sum, a share) and figures written as "5.2 million" are always shown to you.
- **`--judge` sends each unclear figure, with the text around it, to the AI command you name.** `claude` means Claude Code with tools turned off. Any command that reads a prompt and prints the answer works, or use `--ask-ai` and `--answers` to do the AI step by hand.
- **It checks the number is in the document and belongs to the right item.** It doesn't judge whether the document itself is right.
- **These are small tests** on a handful of documents, with answers written by an AI. Details, limits and results: [docs/DETAILS.md](docs/DETAILS.md).

## For developers

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

Apache-2.0. Copyright 2026 Lawrence McDonell.
