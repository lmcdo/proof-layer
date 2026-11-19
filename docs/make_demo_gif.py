"""Make docs/demo.gif from a REAL run of examples/check_figures.py.

The script runs the example, captures its output, and draws it as a terminal recording: the
command is typed, then each figure appears with what the AI said and, for anything that did
not pass, the page line it was checked against and why. Nothing is scripted by hand, so if
the tool's output changes, re-running this changes the GIF.

usage: python docs/make_demo_gif.py        (needs Pillow and the Consolas font on Windows)
"""
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "demo.gif"
COMMAND = "python examples/check_figures.py examples/sample_report.pdf examples/figures.csv"

BG, FG, DIM = (13, 17, 23), (201, 209, 217), (125, 133, 144)
GREEN, RED, AMBER = (63, 185, 80), (248, 81, 73), (210, 153, 34)
WORDS = (("PASSED", GREEN), ("STOPPED", RED), ("CONFIRM", AMBER))
W, PAD, FONT_SIZE, LINE = 940, 24, 16, 25


def real_output() -> list[str]:
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
    done = subprocess.run([sys.executable, *COMMAND.split()[1:]], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding="utf-8")
    return done.stdout.splitlines()


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
            blocks[-1].append(ln)
    return blocks


def draw_frame(font, height, command_shown, shown_blocks, summary, cursor):
    img = Image.new("RGB", (W, height), BG)
    d = ImageDraw.Draw(img)
    d.text((PAD, PAD - 6), "proof-layer: 8 figures an AI took from a report, checked against the PDF", font=font, fill=DIM)
    y = PAD + 30
    d.text((PAD, y), "$ " + command_shown + ("_" if cursor else ""), font=font, fill=FG)
    y += LINE + 8
    for block in shown_blocks:
        for i, line in enumerate(block):
            word, rgb = word_of(line) if i == 0 else (None, None)
            if word:
                d.text((PAD, y), word, font=font, fill=rgb)
                d.text((PAD + font.getlength(word), y), line[len(word):], font=font, fill=FG)
            else:
                d.text((PAD, y), line, font=font, fill=DIM)
            y += LINE
    if summary:
        y += 8
        d.text((PAD, y), summary, font=font, fill=FG)
    return img


def main() -> None:
    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", FONT_SIZE)
    lines = [ln for ln in real_output() if ln.strip()]
    blocks = blocks_of(lines)
    assert len(blocks) == 8, f"expected 8 figures, got {len(blocks)}"
    assert "need attention" in lines[-1], "unexpected output"
    counts = {w: sum(1 for b in blocks if b[0].startswith(w)) for w, _ in WORDS}
    summary = f"{counts['PASSED']} passed   {counts['STOPPED']} stopped   {counts['CONFIRM']} to confirm"
    height = PAD * 2 + 30 + LINE + 8 + LINE * sum(len(b) for b in blocks) + 8 + LINE + 6

    frames, durations = [], []
    step = 6
    for i in range(0, len(COMMAND) + step, step):
        frames.append(draw_frame(font, height, COMMAND[:i], [], None, True)); durations.append(60)
    frames.append(draw_frame(font, height, COMMAND, [], None, False)); durations.append(500)
    for n in range(1, len(blocks) + 1):
        frames.append(draw_frame(font, height, COMMAND, blocks[:n], None, False))
        durations.append(700 if len(blocks[n - 1]) == 1 else 1700)   # more to read on a stopped or confirm
    frames.append(draw_frame(font, height, COMMAND, blocks, summary, False)); durations.append(5000)

    pal = [f.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    pal[0].save(OUT, save_all=True, append_images=pal[1:], duration=durations, loop=0, optimize=True, disposal=2)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB, {len(frames)} frames, {W}x{height})")
    print(summary)


if __name__ == "__main__":
    main()
