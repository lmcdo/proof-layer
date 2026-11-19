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
    assert "PASSED   p1  Scope 1 emissions: 5845" in out
    assert "STOPPED  p1  Scope 1 emissions: 19691" in out
    assert "STOPPED  p1  Scope 2 emissions: 19000" in out
    assert "CONFIRM  p1  Water withdrawn: 22.975" in out
    assert "CONFIRM  p1  Scope 3 emissions: 5845" in out
    assert "5 figure(s) need attention" in out
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for line in out.strip().splitlines():
        if line.strip():
            assert line.strip() in readme, f"README output block is out of date: {line}"
