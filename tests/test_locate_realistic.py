"""Realistic labels on a table-style page. The page and the paraphrases are hand-written.

The right answer for each case is written BEFORE the checker is run. Cases the checker
cannot do yet are marked xfail(strict=True): they are known limits, and they fail SAFE
(held back as UNKNOWN, never passed). If a future change makes one pass, strict xfail
fails the test run so the README limit gets updated.
"""
import pytest
from proof_layer.locate import FOUND_IN_ROW, HELD_BACK, check_claim

PAGE = """Greenhouse gas emissions (Scope 1) tCO2-e 5,845 6,102
Greenhouse gas emissions (Scope 2, market-based) tCO2-e 19,691 18,400
Total energy consumption GJ 1,074,807 998,100
Water withdrawn ML 22.975 26.511
Lost time injury frequency rate 2.1 1.8
Women in leadership % 38 36
"""

SYNONYM = pytest.mark.xfail(strict=True, reason="synonym or inflection: not matched, held back as UNKNOWN (safe)")


@pytest.mark.parametrize("label,value", [
    ("Scope 1 GHG emissions", 5845),                 # abbreviation of two printed words
    ("Scope 2 market-based emissions", 19691),
    ("Lost time injury frequency rate", 2.1),        # exact words
    ("Women in leadership", 38),
    pytest.param("Energy use", 1074807, marks=SYNONYM),
    pytest.param("Total energy consumed in gigajoules", 1074807, marks=SYNONYM),
    pytest.param("Water withdrawal", 22.975, marks=SYNONYM),
    pytest.param("LTIFR", 2.1, marks=SYNONYM),
    pytest.param("Female representation in leadership", 38, marks=SYNONYM),
])
def test_paraphrased_label_finds_its_row(label, value):
    assert check_claim(label, value, PAGE)["verdict"] == FOUND_IN_ROW


@pytest.mark.parametrize("label,wrong_value", [
    ("Energy use", 1074808),
    ("Total energy consumed in gigajoules", 5845),
    ("Water withdrawal", 19691),
    ("LTIFR", 9.9),
    ("Female representation in leadership", 83),
    ("Scope 1 GHG emissions", 19691),     # the Scope 2 figure
    ("Scope 2 market-based emissions", 5845),
])
def test_wrong_number_is_held_back_whatever_the_label_style(label, wrong_value):
    assert check_claim(label, wrong_value, PAGE)["verdict"] in HELD_BACK
