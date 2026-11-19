"""Break-it tests: each case is a way the checker could give a silently wrong answer.

Wrong values must NOT be explained; right values must be. Every case has a known
right answer written before the checker is run.
"""
import pytest
from proof_layer.integrity import explain_value, FAILING_STATES


def flagged(value, source, unit=None):
    state, _ = explain_value(value, source, unit)
    return state in FAILING_STATES


@pytest.mark.parametrize("value,source,unit", [
    (5, "setback of 15 metres", "m"),            # 5 is not inside 15
    (3.5, "width of 13.5 m", "m"),               # 3.5 is not inside 13.5
    (50, "area 1500 sqm", "m2"),                 # 50 is not inside 1500
    (150, "area 1,500 sqm", "m2"),
    (9, "", "m"),                                # no source: never fine
    (9, None, "m"),
    (4.5, "minimum 4.55 m", "m"),                # near miss
    (7, "max 7 storeys and 12 metres", "m"),     # right digits, wrong thing
    (0.8, "minimum 900mm", "m"),
    (0.53, "coverage 35%", None),                # digits swapped
    (5, "temperature -5 C", None),               # SIGN FLIPPED
    (-5, "temperature 5 C", None),               # SIGN INVENTED
])
def test_wrong_values_are_flagged(value, source, unit):
    assert flagged(value, source, unit)


@pytest.mark.parametrize("value,source,unit", [
    (4.5, "minimum 4.5 m", "m"),
    (1500, "area 1,500 sqm", "m2"),
    (0.9, "minimum 900mm", "m"),
    (0.35, "coverage 35%", None),
    (-5, "temperature -5 C", None),              # a negative must be readable
    (-5, "change of \u22125 percent", None),     # unicode minus
    (6, "setback 4-6 m", "m"),                   # a range dash is not a sign
    (4, "setback 4-6 m", "m"),
])
def test_right_values_are_not_flagged(value, source, unit):
    assert not flagged(value, source, unit)


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN LIMIT: text alone cannot tell that 2024 is a year, not a setback. "
    "The check proves the digits are present, not what they measure."))
def test_year_is_not_a_setback():
    assert flagged(2024, "adopted in 2024, setback 4 m", "m")


def test_list_item_number_is_not_a_quantity():
    # "2." is the second list item, not a 2 m setback.
    quote = "1. Fences are to be open.\n2. Front fences must not impede sight lines."
    assert flagged(2.0, quote, "m")


def test_clause_citation_is_not_a_quantity():
    # "Clause 4.3" names a clause; it must not explain a stored 4.3.
    assert flagged(4.3, "Clause 4.3: the minimum setback is 6 m", "m")
    assert not flagged(6, "Clause 4.3: the minimum setback is 6 m", "m")
