import os, subprocess, sys
from pathlib import Path
import pytest
pytest.importorskip("pdfplumber")
ROOT = Path(__file__).resolve().parent.parent


def test_cli_output_matches_the_readme():
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
    done = subprocess.run([sys.executable, "-m", "proof_layer.cli", "examples/sample_report.pdf", "examples/results.json"],
                          cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    assert done.returncode == 1
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for line in done.stdout.strip().splitlines():
        if line.strip():
            assert line.rstrip() in readme, line


def test_a_written_answer_is_checked_figure_by_figure():
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
    done = subprocess.run([sys.executable, "-m", "proof_layer.cli", "examples/sample_report.pdf", "examples/ai_answer.txt"],
                          cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    out = done.stdout
    assert done.returncode == 1
    assert "CORRECT  Scope 1 emissions = 5,845, page 1" in out
    assert "WRONG    Scope 1 emissions = 19,691, page 1" in out
    assert "1 need attention" in out


def test_stored_figures_are_checked_against_their_saved_text_and_the_pdf():
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
    done = subprocess.run([sys.executable, "-m", "proof_layer.cli", "examples/sample_report.pdf", "examples/stored_rows.json"],
                          cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    out = done.stdout
    assert done.returncode == 1
    assert "CORRECT  Scope 1 emissions = 5,845, page 1" in out
    assert "the stored number is not in the text it was taken from" in out
    assert "the stored text is not in the PDF" in out
    assert "the text is in the PDF on page 1, not page 3" in out
    assert "3 need attention" in out
