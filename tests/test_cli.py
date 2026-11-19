import json
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


def _run(tmp_path, rows, pdf="examples/sample_report.pdf", name="r.json", raw=None):
    f = tmp_path / name
    f.write_text(raw if raw is not None else json.dumps(rows), encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "proof_layer.cli", pdf, str(f)], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding="utf-8")


QUOTE = "Scope 1 emissions (tCO2-e) 5,845 6,102"


def test_stored_row_without_a_number_is_not_correct(tmp_path):
    for v in (None, "abc"):
        d = _run(tmp_path, [{"name": "Scope 1 emissions", "value": v, "source_text": QUOTE}])
        assert "CHECK" in d.stdout and d.returncode == 1


def test_stored_number_attached_to_the_wrong_item_is_stopped(tmp_path):
    d = _run(tmp_path, [{"name": "Scope 3 emissions", "value": 5845, "source_text": "Scope 1 emissions (tCO2-e) 5,845"}])
    assert "CORRECT" not in d.stdout and d.returncode == 1


def test_label_digit_is_not_mistaken_for_the_value():
    from proof_layer.locate import check_claim
    assert check_claim("Scope 3 emissions", 3, "Scope 3 emissions not reported")["verdict"] != "FOUND_IN_ROW"
    assert check_claim("Scope 3 emissions", 3, "Scope 3 emissions 3")["verdict"] == "FOUND_IN_ROW"


def test_bad_input_gives_a_clear_message_and_exit_2(tmp_path):
    for raw in ('{"a": 1}', '["Scope 1"]', "[null]", "{not json", "[]"):
        d = _run(tmp_path, None, raw=raw)
        assert d.returncode == 2 and "Traceback" not in d.stderr, raw
    assert _run(tmp_path, [{"name": "x", "value": 1}], pdf="nope.pdf").returncode == 2


def test_page_as_text_and_odd_unit_do_not_crash(tmp_path):
    d = _run(tmp_path, [{"name": "Scope 1 emissions", "value": 5845, "page": "1", "unit": 5, "source_text": QUOTE}])
    assert "CORRECT" in d.stdout and d.returncode == 0


def test_text_answer_with_no_figures_is_not_all_correct(tmp_path):
    f = tmp_path / "a.txt"; f.write_text("no numbers here", encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
    d = subprocess.run([sys.executable, "-m", "proof_layer.cli", "examples/sample_report.pdf", str(f)],
                       cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    assert d.returncode == 2 and "all correct" not in d.stdout


def test_dollar_millions_are_scaled_but_metres_are_not():
    from proof_layer.claims import extract_claims
    assert extract_claims("Revenue was $5m.")[0].scaled
    c = extract_claims("Minimum setback is 3 m from the boundary.")[0]
    assert not c.scaled and c.unit == "m"
    assert extract_claims("Revenue was 5.2 million and Scope 1 emissions fell to 5,845 tonnes.")[1].description == "Scope 1 emissions"


def test_sheet_pictures_the_page_for_each_figure_that_needs_a_look(tmp_path):
    pytest.importorskip("fitz")
    out = tmp_path / "check.html"
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
    done = subprocess.run([sys.executable, "-m", "proof_layer.cli", "examples/sample_report.pdf",
                           "examples/results.json", "--sheet", str(out)],
                          cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    page = out.read_text(encoding="utf-8")
    assert done.returncode == 1 and "2 figures to look at" in page
    assert page.count("<img src=\"data:image/png;base64,") >= 1
    assert "Scope 1 emissions = 19,691" in page


QROW = {"name": "Emissions from burning fuel", "value": 5845, "page": 1, "source_text": QUOTE}


def _run_flags(tmp_path, rows, *flags):
    f = tmp_path / "r.json"; f.write_text(json.dumps(rows), encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "proof_layer.cli", "examples/sample_report.pdf", str(f), *flags],
                          cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")


def test_ask_ai_writes_the_unsettled_figures_with_context(tmp_path):
    out = tmp_path / "items.json"
    d = _run_flags(tmp_path, [QROW], "--ask-ai", str(out))
    items = json.loads(out.read_text(encoding="utf-8"))
    assert d.returncode == 1 and len(items["items"]) == 1 and items["items"][0]["id"] == 0
    assert "5,845" in items["items"][0]["context"] and "instructions" in items


def test_ai_answers_settle_only_what_was_asked(tmp_path):
    def run(answer, row=QROW):
        a = tmp_path / "a.json"; a.write_text(json.dumps([{"id": 0, "answer": answer}]), encoding="utf-8")
        return _run_flags(tmp_path, [row], "--answers", str(a))
    assert run("yes").returncode == 0 and "CORRECT" in run("yes").stdout
    assert "WRONG" in run("no").stdout and run("no").returncode == 1
    assert "CHECK" in run("unsure").stdout
    # an AI "yes" can not rescue a number that is not in the text it was taken from, or a quote not in the PDF
    assert "WRONG" in run("yes", {**QROW, "value": 7777}).stdout
    assert "WRONG" in run("yes", {**QROW, "source_text": "Emissions from burning fuel 5,845 tonnes"}).stdout
