"""Break-it tests for the label-row check. Right answers are written before the code runs."""
import pytest
from proof_layer.locate import (ABSENT, AMBIGUOUS_LABEL, FOUND_IN_ROW, HELD_BACK, UNKNOWN, WRONG_FOR_LABEL, check_claim)

PAGE = "\n".join([
    "Scope 1 emissions 5,845 6,102",
    "Scope 2 emissions 19,691 18,400",
    "Total energy consumption (GJ)",
    "1,074,807 998,100",
    "Water withdrawn 22.975 26.511",
])


def v(label, value, page=PAGE):
    return check_claim(label, value, page)["verdict"]


def test_right_number_on_its_own_row_passes():
    assert v("Scope 1 emissions", 5845) == FOUND_IN_ROW
    assert v("Scope 2 emissions", 18400) == FOUND_IN_ROW   # second column


def test_number_lifted_from_another_row_is_caught():
    # 19,691 IS on the page, but it belongs to Scope 2.
    assert v("Scope 1 emissions", 19691) == WRONG_FOR_LABEL


def test_number_not_on_page_is_absent():
    assert v("Scope 1 emissions", 5846) == ABSENT


def test_wrapped_row_numbers_on_next_line_are_found():
    assert v("Total energy consumption", 1074807) == FOUND_IN_ROW


def test_wrapped_row_does_not_borrow_the_next_rows_numbers():
    # Water row has words of its own, so Scope 2's line must not leak into Scope 1.
    assert v("Scope 2 emissions", 22.975) == WRONG_FOR_LABEL


def test_label_not_found_is_unknown_not_fine():
    r = check_claim("Scope 3 emissions", 5845, PAGE)
    assert r["verdict"] == UNKNOWN and r["verdict"] in HELD_BACK


def test_label_not_found_and_number_absent_is_absent():
    assert v("Scope 3 emissions", 7777) == ABSENT


@pytest.mark.parametrize("label,value,page", [
    ("Scope 1 emissions", 5845, ""),
    ("Scope 1 emissions", 5845, None),
    ("Scope 1 emissions", None, PAGE),
    ("Scope 1 emissions", "abc", PAGE),
    ("Scope 1 emissions", True, PAGE),
    ("", 5845, PAGE),
    ("a b", 5845, PAGE),          # no word long enough to locate a row
])
def test_nothing_to_judge_is_unknown(label, value, page):
    assert check_claim(label, value, page)["verdict"] == UNKNOWN


def test_only_found_in_row_passes():
    for lab, val in [("Scope 1 emissions", 19691), ("Scope 1 emissions", 5846), ("Scope 9", 5845)]:
        assert check_claim(lab, val, PAGE)["verdict"] in HELD_BACK


def test_ambiguous_label_is_held_back_not_passed():
    page = "Emissions 5,845\nEmissions 99"
    r = check_claim("Emissions", 99, page)
    assert r["verdict"] == AMBIGUOUS_LABEL and r["candidates"] == 2 and r["verdict"] in HELD_BACK


def test_ambiguous_label_with_number_in_neither_row_is_absent():
    assert check_claim("Emissions", 7, "Emissions 5,845\nEmissions 99")["verdict"] == ABSENT


def test_extra_words_in_the_label_still_find_the_row():
    assert v("Total Scope 1 GHG emissions reported", 5845) == FOUND_IN_ROW


def test_reordered_label_still_finds_the_row():
    assert v("emissions Scope 1", 5845) == FOUND_IN_ROW


def test_a_different_digit_never_matches_the_wrong_row():
    # "Scope 3" must not fall back on the Scope 1 or Scope 2 row.
    assert v("Total Scope 3 GHG emissions reported", 5845) == UNKNOWN


def test_label_with_no_matching_words_is_unknown():
    assert v("Biodiversity offsets purchased", 5845) == UNKNOWN


def test_unit_stops_a_figure_matching_the_wrong_kind_of_quantity():
    page = "Minimum setback 3 hours of sunlight is required on site\nFront setback to street 6 m"
    assert check_claim("Minimum setback", 3, page)["verdict"] == FOUND_IN_ROW           # no unit: the digits are there
    assert check_claim("Minimum setback", 3, page, unit="m")["verdict"] == ABSENT       # metres: "3 hours" does not count


def test_held_back_results_show_the_line_they_were_checked_against():
    wrong = check_claim("Scope 1 emissions", 19691, PAGE)
    assert wrong["verdict"] == WRONG_FOR_LABEL
    assert wrong["lines"] == ["Scope 1 emissions 5,845 6,102"]
    two = check_claim("Emissions", 99, "Emissions 5,845\nEmissions 99")
    assert two["verdict"] == AMBIGUOUS_LABEL and len(two["lines"]) == 2
    assert check_claim("Scope 1 emissions", 5845, PAGE)["lines"] == ["Scope 1 emissions 5,845 6,102"]
    assert "lines" not in check_claim("Scope 3 emissions", 5845, PAGE)   # no matching line to show
