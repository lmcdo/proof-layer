"""The README's how-to runs the example script, so the example is run as a test."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("pdfplumber")
ROOT = Path(__file__).resolve().parent.parent


def test_example_script_gives_the_documented_output():
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    done = subprocess.run(
        [sys.executable, "examples/check_figures.py", "examples/sample_report.pdf", "examples/figures.csv"],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    out = done.stdout
    assert done.returncode == 1
    assert "PASSED   Scope 1 emissions = 5,845   (p1)" in out
    assert "STOPPED  Scope 1 emissions = 19,691   (p1)" in out
    assert "page says: Scope 1 emissions (tCO2-e) 5,845 6,102" in out
    assert "19,000 is not on the page" in out
    assert "fits 2 places on the page:" in out
    assert "nothing on the page is about this" in out
    assert "5 figure(s) need attention" in out
