"""Make docs/demo.gif from a REAL run of examples/check_figures.py.

The script runs the example, captures its output, and draws it as a terminal recording: the
command is typed, then each result line appears, coloured by outcome. Nothing is scripted by
hand, so if the tool's output changes, re-running this changes the GIF.

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
W, H, PAD, FONT_SIZE, LINE = 1000, 400, 24, 16, 26


def real_output() -> list[str]:
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
    done = subprocess.run([sys.executable, *COMMAND.split()[1:]], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding="utf-8")
    return done.stdout.splitlines()


def colour(line: str):
    for word, rgb in (("PASSED", GREEN), ("STOPPED", RED), ("CONFIRM", AMBER)):
        if line.startswith(word):
            return word, rgb
    return None, FG


def draw_frame(font, command_shown: str, shown: list[str], summary: str | None, cursor: bool) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((PAD, PAD - 6), "proof-layer: checking 8 figures an AI took from a report", font=font, fill=DIM)
    y = PAD + 30
    d.text((PAD, y), "$ " + command_shown + ("_" if cursor else ""), font=font, fill=FG)
    y += LINE + 4
    for line in shown:
        word, rgb = colour(line)
        if word:
            d.text((PAD, y), word, font=font, fill=rgb)
            d.text((PAD + font.getlength(word), y), line[len(word):], font=font, fill=FG)
        else:
            d.text((PAD, y), line, font=font, fill=FG)
        y += LINE
    if summary:
        y += 6
        d.text((PAD, y), summary, font=font, fill=FG)
    return img


def main() -> None:
    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", FONT_SIZE)
    lines = [ln for ln in real_output() if ln.strip()]
    results, tail = [ln for ln in lines if colour(ln)[0]], [ln for ln in lines if not colour(ln)[0]]
    counts = {w: sum(1 for r in results if r.startswith(w)) for w in ("PASSED", "STOPPED", "CONFIRM")}
    summary = f"{counts['PASSED']} passed   {counts['STOPPED']} stopped   {counts['CONFIRM']} to confirm"
    assert len(results) == 8, f"expected 8 results, got {len(results)}"
    assert tail and "need attention" in tail[-1], "unexpected output"

    frames, durations = [], []
    step = 6
    for i in range(0, len(COMMAND) + step, step):
        frames.append(draw_frame(font, COMMAND[:i], [], None, True)); durations.append(60)
    frames.append(draw_frame(font, COMMAND, [], None, False)); durations.append(500)
    for n in range(1, len(results) + 1):
        frames.append(draw_frame(font, COMMAND, results[:n], None, False))
        durations.append(900 if colour(results[n - 1])[0] != "PASSED" else 600)
    frames.append(draw_frame(font, COMMAND, results, summary, False)); durations.append(4500)

    pal = [f.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    pal[0].save(OUT, save_all=True, append_images=pal[1:], duration=durations, loop=0, optimize=True, disposal=2)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB, {len(frames)} frames)")
    print(summary)


if __name__ == "__main__":
    main()
