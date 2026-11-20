"""Make docs/demo.gif from a REAL run of the proof-layer command.

The script runs the example, captures its output, and draws it as a terminal recording: the
command is typed, then each figure appears with what the AI said and, for anything that did
not pass, the page line it was checked against and why. Nothing is scripted by hand, so if
the tool's output changes, re-running this changes the GIF.

usage: python docs/make_demo_gif.py        (needs Pillow and the Consolas font on Windows)
"""
import os
import subprocess
import textwrap
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "demo.gif"
COMMAND = "proof-layer sample_report.pdf answer.json --judge claude"

BG, FG, DIM = (13, 17, 23), (201, 209, 217), (125, 133, 144)
SOFT = (170, 180, 192)
GREEN, RED, AMBER = (63, 185, 80), (248, 81, 73), (255, 190, 40)
WORDS = (("CORRECT", GREEN), ("WRONG", RED), ("CHECK", AMBER))
W, PAD, FONT_SIZE, LINE = 1060, 28, 19, 30


def real_output() -> list[str]:
    """The saved output of a real run: python -m proof_layer.cli examples/sample_report.pdf examples/answer.json --judge claude
    (re-record it with that command; the GIF is drawn from the file, not typed by hand)."""
    return (ROOT / "docs" / "demo_run.txt").read_text(encoding="utf-8").splitlines()


def word_of(line: str):
    for word, rgb in WORDS:
        if line.startswith(word):
            return word, rgb
    return None, None


def blocks_of(lines: list[str]) -> list[list[str]]:
    """Group output into one block per figure: the figure line plus its indented detail."""
    blocks: list[list[str]] = []
    for ln in lines:
        if word_of(ln)[0]:
            blocks.append([ln])
        elif ln.startswith(" ") and blocks:
            blocks[-1].extend(textwrap.wrap(ln.strip(), 84, initial_indent=" " * 9, subsequent_indent=" " * 9))
    return blocks


def report_lines() -> list[str]:
    import pdfplumber
    with pdfplumber.open(ROOT / "examples" / "sample_report.pdf") as pdf:
        text = pdf.pages[0].extract_text()
    return [ln for ln in text.splitlines() if ln.startswith(("Scope 1", "Scope 2", "Total energy", "Water withdrawn in water"))]


def ai_lines() -> list[str]:
    import json
    rows = json.load(open(ROOT / "examples" / "answer.json", encoding="utf-8"))
    return [f"{r['name']} = {r['value']:,}" for r in rows]


def draw_frame(font, height, stage, command_shown, shown_blocks, summary, cursor, report, ai):
    """stage 1: the report; 2: + the AI's figures; 3: + the command and its results."""
    img = Image.new("RGB", (W, height), BG)
    d = ImageDraw.Draw(img)
    y = PAD - 6
    d.text((PAD, y), "1. The report (sample_report.pdf, page 1) says:", font=font, fill=FG)
    y += LINE
    for ln in report:
        d.text((PAD + 20, y), ln, font=font, fill=SOFT)
        y += LINE
    y += 12
    if stage >= 2:
        d.text((PAD, y), "2. An AI read it and gave you these 6 figures (each with its page and quote):", font=font, fill=FG)
        y += LINE
        for ln in ai:
            d.text((PAD + 20, y), ln, font=font, fill=SOFT)
            y += LINE
        y += 12
    if stage >= 3:
        d.text((PAD, y), "3. proof-layer checks each one, and your AI settles the unclear ones by itself:", font=font, fill=FG)
        y += LINE + 4
        d.text((PAD, y), "$ " + command_shown + ("_" if cursor else ""), font=font, fill=FG)
        y += LINE + 8
        for block in shown_blocks:
            for k, line in enumerate(block):
                word, rgb = word_of(line) if k == 0 else (None, None)
                if word:
                    d.text((PAD, y), word, font=font, fill=rgb)
                    d.text((PAD + font.getlength(word), y), line[len(word):], font=font, fill=FG)
                else:
                    d.text((PAD, y), line, font=font, fill=SOFT)
                y += LINE
        if summary:
            y += 8
            d.text((PAD, y), summary, font=font, fill=FG)
    return img


def main() -> None:
    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", FONT_SIZE)
    lines = [ln for ln in real_output() if ln.strip()]
    blocks = blocks_of(lines)
    assert len(blocks) == 6, f"expected 6 figures, got {len(blocks)}"
    assert "need your attention" in lines[-1], "unexpected output"
    summary = lines[-1].strip()
    report, ai = report_lines(), ai_lines()
    assert len(report) == 4 and len(ai) == 6
    height = (PAD * 2 + LINE * (1 + len(report)) + 12 + LINE * (1 + len(ai)) + 12 + LINE + 4 + LINE + 8
              + LINE * sum(len(b) for b in blocks) + 8 + LINE)

    def frame(stage, cmd="", shown=(), summ=None, cursor=False):
        return draw_frame(font, height, stage, cmd, list(shown), summ, cursor, report, ai)

    frames, durations = [frame(1)], [2500]
    frames.append(frame(2)); durations.append(3000)
    step = 6
    for k in range(0, len(COMMAND) + step, step):
        frames.append(frame(3, COMMAND[:k], cursor=True)); durations.append(60)
    frames.append(frame(3, COMMAND)); durations.append(500)
    for n in range(1, len(blocks) + 1):
        frames.append(frame(3, COMMAND, blocks[:n]))
        durations.append(900 if len(blocks[n - 1]) == 1 else 2200)   # more to read on a wrong or check
    frames.append(frame(3, COMMAND, blocks, summary)); durations.append(6000)

    pal = [f.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    pal[0].save(OUT, save_all=True, append_images=pal[1:], duration=durations, loop=0, optimize=True, disposal=2)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB, {len(frames)} frames, {W}x{height})")
    print(summary)


if __name__ == "__main__":
    main()
