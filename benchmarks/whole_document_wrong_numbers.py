"""WHOLE-DOCUMENT version of located_wrong_numbers.py: the checker gets the whole PDF and no page number
(proof_layer.document.check_in_document). Same seed, same claims, same wrong numbers.

Original description: seeded wrong-number benchmark for the label-row check (proof_layer.locate).

Same true claims and the same five kinds of wrong number as seeded_wrong_numbers.py, but the
checker is given the WHOLE PAGE plus the claim's LABEL, and has to find the row itself.

Three label styles, because a real AI does not copy the printed words exactly:
  verbatim  : the words printed before the number, one word dropped at random when there are 3+
  extra     : verbatim, plus two qualifier words that are not on the row ("reported", "annual")
  reordered : verbatim words in a shuffled order

Reported per style:
  held_back_true      : share of TRUE claims held back (any verdict except FOUND_IN_ROW)
  true_verdicts       : which verdicts those were (UNKNOWN / AMBIGUOUS_LABEL / ...)
  catch_rate          : share of WRONG claims held back, overall and by kind
  wrong_that_passed   : WRONG claims that came back FOUND_IN_ROW (the dangerous ones)

usage: python -I located_wrong_numbers.py <out.json> <pdf> [<pdf> ...]
"""
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import seeded_wrong_numbers as sw  # noqa: E402
from proof_layer.integrity import FAILING_STATES, explain_value  # noqa: E402
from proof_layer.locate import _tokens  # noqa: E402
from proof_layer.locate import FOUND_IN_ROW  # noqa: E402
from proof_layer.document import Document, check_in_document  # noqa: E402
import pdfplumber  # noqa: E402

VALUE_LIKE = re.compile(r"(?<![\w.])\d[\d,]*\.\d+|(?<![\w.])\d{1,3}(?:,\d{3})+|(?<![\w.])\d{3,}")
QUALIFIERS = ["reported", "annual", "group", "overall", "reporting"]
STYLES = ("verbatim", "extra", "reordered")


def base_label(line, rng):
    m = VALUE_LIKE.search(line)
    words = (line[: m.start()] if m else line).split()
    if sum(1 for w in words if re.search(r"[A-Za-z]{3,}", w)) >= 3:
        droppable = [i for i, w in enumerate(words) if re.fullmatch(r"[A-Za-z]{3,}", w)]
        words.pop(rng.choice(droppable))
    return words


def style_label(words, style, rng):
    if style == "extra":
        return " ".join(words + rng.sample(QUALIFIERS, 2))
    if style == "reordered":
        w = words[:]
        rng.shuffle(w)
        return " ".join(w)
    return " ".join(words)


def main():
    out_path, pdfs = sys.argv[1], sys.argv[2:]
    rng = random.Random(sw.SEED)
    pool = []
    for pdf in pdfs:
        for pno, text, line, tok, v in sw.lines_with_claims(pdf):
            pool.append((Path(pdf).name, pno, text, line, tok, v))
    rng.shuffle(pool)
    pool = pool[: sw.MAX_TRUE]
    docs = {}
    for pdf in pdfs:
        with pdfplumber.open(pdf) as f:
            docs[Path(pdf).name] = Document.from_texts([p.extract_text() or "" for p in f.pages])
    page_nums = defaultdict(list)
    for doc, pno, text, line, tok, v in pool:
        page_nums[(doc, pno)].append(v)

    lrng = random.Random(sw.SEED + 1)
    st = {s: {"true_n": 0, "true_verdicts": Counter(), "wrong": defaultdict(lambda: [0, 0]),
              "wrong_verdicts": Counter()} for s in STYLES}
    page_only = {"true_held": 0, "true_n": 0, "wrong": defaultdict(lambda: [0, 0])}
    skipped = 0
    for doc, pno, text, line, tok, v in pool:
        words = base_label(line, lrng)
        if not re.search(r"[A-Za-z]{3,}", " ".join(words)):
            skipped += 1
            continue
        if v == int(v) and str(int(v)) in _tokens(" ".join(words)):
            skipped += 1        # the number is part of its own description ("Scope 3", "wharf 7"): no claim to check
            continue
        line_nums = {float(n.rstrip(".,").replace(",", "")) for n in sw.NUM.findall(line)
                     if n.rstrip(".,").replace(",", "").replace("-", "").replace(".", "").isdigit()}
        wrongs = sw.mutate(tok, v, rng, line_nums)
        others = [x for x in page_nums[(doc, pno)] if x not in line_nums and x != v]
        if others:
            wrongs["lifted_from_page"] = rng.choice(others)
        page_only["true_n"] += 1
        page_only["true_held"] += explain_value(v, text, None)[0] in FAILING_STATES
        for kind, w in wrongs.items():
            page_only["wrong"][kind][1] += 1
            page_only["wrong"][kind][0] += explain_value(w, text, None)[0] in FAILING_STATES
        for style in STYLES:
            label = style_label(words, style, lrng)
            s = st[style]
            s["true_n"] += 1
            s["true_verdicts"][check_in_document(label, v, docs[doc])["verdict"]] += 1
            for kind, w in wrongs.items():
                verdict = check_in_document(label, w, docs[doc])["verdict"]
                s["wrong"][kind][1] += 1
                s["wrong"][kind][0] += verdict != FOUND_IN_ROW
                s["wrong_verdicts"][verdict] += 1

    def rate(d):
        c = sum(a for a, _ in d.values()); n = sum(b for _, b in d.values())
        return round(c / n, 4), n

    summary = {"skipped_no_label": skipped, "docs": sorted({p[0] for p in pool}), "styles": {}}
    for style, s in st.items():
        caught, n = rate(s["wrong"])
        tv = s["true_verdicts"]
        summary["styles"][style] = {
            "true_claims": s["true_n"],
            "held_back_true": round(1 - tv[FOUND_IN_ROW] / s["true_n"], 4),
            "true_verdicts": dict(tv),
            "catch_rate": caught, "wrong_n": n,
            "catch_rate_by_kind": {k: round(c / m, 4) for k, (c, m) in sorted(s["wrong"].items())},
            "wrong_claim_verdicts": dict(s["wrong_verdicts"]),
            "wrong_that_passed": s["wrong_verdicts"][FOUND_IN_ROW],
        }
    pc, pn = rate(page_only["wrong"])
    summary["whole_page_without_label_for_comparison"] = {
        "held_back_true": round(page_only["true_held"] / page_only["true_n"], 4), "catch_rate": pc, "wrong_n": pn}
    Path(out_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
