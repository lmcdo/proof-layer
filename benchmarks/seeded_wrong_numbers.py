"""Seeded wrong-number benchmark on real public PDFs.

Every TRUE claim is a (label line, number) pair taken from the document itself, so
the right answer is known before any checker runs. Each true claim is then turned
into WRONG claims in five ways. A checker is scored on:

  catch rate        = share of WRONG claims it flags (higher is better)
  false-alarm rate  = share of TRUE claims it flags   (lower is better)

Two source settings are scored, because they answer different questions:
  tight : the source is the claim's own line   (can the checker tell right from wrong?)
  loose : the source is the whole page          (does it also catch a number lifted
                                                 from elsewhere on the page?)

usage: python -I seeded_wrong_numbers.py <out.json> <pdf> [<pdf> ...]
"""
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pdfplumber  # noqa: E402

from proof_layer.integrity import FAILING_STATES, explain_value, value_absent_from_source  # noqa: E402

SEED = 20261118
MAX_TRUE = 600
NUM = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")   # greedy: "22.975ML" is 22.975, never 22


def lines_with_claims(pdf_path):
    """Yield (page_no, page_text, line, token_text) for numbers on labelled lines."""
    with pdfplumber.open(pdf_path) as pdf:
        for pno, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            for line in text.split("\n"):
                if len(re.findall(r"[A-Za-z]{3,}", line)) < 2:
                    continue  # needs a label
                for m in NUM.finditer(line):
                    if m.start() == len(line) - len(line.lstrip()) and re.match(r"\d+\.\s+[A-Za-z]", line.lstrip()):
                        continue  # a numbered heading ("3. Energy efficiency"), not a quantity
                    tok = m.group(0).rstrip(".,")
                    try:
                        v = float(tok.replace(",", ""))
                    except ValueError:
                        continue
                    if 1900 <= v <= 2100 and v == int(v) and "," not in tok:
                        continue  # a year, not a quantity: keep the truth clean
                    yield pno, text, line, tok, v


def mutate(tok, v, rng, others):
    """Return {kind: wrong_value}. Only values that differ from every number on the line."""
    out = {}
    digits = [i for i, c in enumerate(tok) if c.isdigit()]
    if digits:
        i = rng.choice(digits)
        c = rng.choice([d for d in "0123456789" if d != tok[i]])
        out["digit_changed"] = float((tok[:i] + c + tok[i + 1:]).replace(",", ""))
        pairs = [j for j in range(len(tok) - 1) if tok[j].isdigit() and tok[j + 1].isdigit() and tok[j] != tok[j + 1]]
        if pairs:
            j = rng.choice(pairs)
            s = tok[:j] + tok[j + 1] + tok[j] + tok[j + 2:]
            out["digits_swapped"] = float(s.replace(",", ""))
    out["times_ten"] = v * 10
    out["sign_flipped"] = -v if v != 0 else None
    return {k: w for k, w in out.items() if w is not None and w != v and w not in others}


def main():
    out_path, pdfs = sys.argv[1], sys.argv[2:]
    rng = random.Random(SEED)
    pool = []
    for pdf in pdfs:
        for pno, text, line, tok, v in lines_with_claims(pdf):
            pool.append((Path(pdf).name, pno, text, line, tok, v))
    rng.shuffle(pool)
    pool = pool[:MAX_TRUE]
    page_nums = defaultdict(list)
    for doc, pno, text, line, tok, v in pool:
        page_nums[(doc, pno)].append(v)

    checkers = {
        "naive_substring": lambda v, s: str(int(v)) not in s if float(v).is_integer() else str(v) not in s,
        "old_value_absent_from_source": lambda v, s: bool(value_absent_from_source([{"v": v, "s": s}], value_field="v", source_field="s")),
        "explain_value": lambda v, s: explain_value(v, s, None)[0] in FAILING_STATES,
    }
    res = {setting: {c: {"true_flagged": 0, "true_n": 0, "wrong": defaultdict(lambda: [0, 0])} for c in checkers}
           for setting in ("tight", "loose")}

    for doc, pno, text, line, tok, v in pool:
        line_nums = {float(n.rstrip(".,").replace(",", "")) for n in NUM.findall(line) if n.rstrip(".,").replace(",", "").replace("-", "").replace(".", "").isdigit()}
        wrongs = mutate(tok, v, rng, line_nums)
        others = [x for x in page_nums[(doc, pno)] if x not in line_nums and x != v]
        if others:
            wrongs["lifted_from_page"] = rng.choice(others)
        for setting, src in (("tight", line), ("loose", text)):
            for cname, fn in checkers.items():
                r = res[setting][cname]
                r["true_n"] += 1
                r["true_flagged"] += fn(v, src)
                for kind, w in wrongs.items():
                    # in the loose setting a wrong value that really is elsewhere on the page is
                    # only "wrong" for the claim's own line; count it, but report it separately
                    r["wrong"][kind][1] += 1
                    r["wrong"][kind][0] += fn(w, src)

    summary = {"true_claims": len(pool), "docs": sorted({p[0] for p in pool}), "seed": SEED, "results": {}}
    for setting, byc in res.items():
        summary["results"][setting] = {}
        for cname, r in byc.items():
            tot_w = sum(n for _, n in r["wrong"].values())
            caught = sum(c for c, _ in r["wrong"].values())
            summary["results"][setting][cname] = {
                "false_alarm_rate": round(r["true_flagged"] / r["true_n"], 3),
                "catch_rate_overall": round(caught / tot_w, 3) if tot_w else None,
                "catch_rate_by_kind": {k: round(c / n, 3) for k, (c, n) in sorted(r["wrong"].items())},
                "wrong_n": tot_w,
            }
    Path(out_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
