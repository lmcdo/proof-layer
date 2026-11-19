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
