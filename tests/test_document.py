"""Checking a figure against a whole document, with no page numbers. Answers written first."""
import pytest
from proof_layer.document import Document, check_in_document
from proof_layer.locate import ABSENT, AMBIGUOUS_LABEL, FOUND_IN_ROW, HELD_BACK, UNKNOWN, WRONG_FOR_LABEL

P1 = "Scope 1 emissions (tCO2-e) 5,845 6,102"
P2 = "Scope 2 emissions (tCO2-e) 19,691 18,400"
P3 = "Highlights\nScope 1 emissions 5,845"
P4 = "Restated figures\nScope 1 emissions (restated) 5,900 6,102"


def v(label, value, *pages):
    return check_in_document(label, value, Document.from_texts(list(pages)))


def test_number_in_every_place_that_fits_passes_and_names_the_pages():
    r = check_in_document("Scope 1 emissions", 5845, Document.from_texts([P1, P2, P3]))
    assert r["verdict"] == FOUND_IN_ROW and r["pages"] == [1, 3]


def test_number_belonging_to_another_item_is_stopped():
    assert check_in_document("Scope 1 emissions", 19691, Document.from_texts([P1, P2, P3]))["verdict"] == WRONG_FOR_LABEL


def test_number_nowhere_in_the_document_is_absent():
    assert check_in_document("Scope 1 emissions", 7777, Document.from_texts([P1, P2]))["verdict"] == ABSENT


def test_description_found_nowhere_is_unknown_when_the_number_exists_and_absent_when_it_does_not():
    doc = Document.from_texts([P1, P2])
    assert check_in_document("Scope 3 emissions", 5845, doc)["verdict"] == UNKNOWN
    assert check_in_document("Scope 3 emissions", 7777, doc)["verdict"] == ABSENT


def test_description_fitting_places_that_disagree_is_ambiguous_not_a_pass():
    r = check_in_document("Scope 1 emissions", 5845, Document.from_texts([P1, P3, P4]))
    assert r["verdict"] == AMBIGUOUS_LABEL and r["candidates"] == 3 and r["verdict"] in HELD_BACK


def test_the_right_number_for_the_other_place_that_fits_is_also_held_back_if_not_in_all():
    r = check_in_document("Scope 1 emissions", 5900, Document.from_texts([P1, P3, P4]))
    assert r["verdict"] == AMBIGUOUS_LABEL


def test_results_say_which_page_each_line_is_from():
    r = check_in_document("Scope 2 emissions", 19000, Document.from_texts([P1, P2]))
    assert r["verdict"] == ABSENT and r["lines"] == ["p2: " + P2] and r["pages"] == [2]


@pytest.mark.parametrize("label,value,pages", [
    ("Scope 1 emissions", None, [P1]),
    ("Scope 1 emissions", "abc", [P1]),
    ("Scope 1 emissions", True, [P1]),
    ("a b", 5845, [P1]),
    ("Scope 1 emissions", 5845, [""]),
    ("Scope 1 emissions", 5845, []),
])
def test_nothing_to_judge_is_unknown(label, value, pages):
    assert check_in_document(label, value, Document.from_texts(pages))["verdict"] == UNKNOWN


def test_wrapped_row_numbers_on_the_next_line_are_found():
    doc = Document.from_texts(["Total energy consumption (GJ)\n1,074,807 998,100"])
    assert check_in_document("Total energy consumption", 1074807, doc)["verdict"] == FOUND_IN_ROW


def test_unit_still_stops_the_wrong_kind_of_quantity():
    doc = Document.from_texts(["Minimum setback 3 hours of sunlight is required on site"])
    assert check_in_document("Minimum setback", 3, doc)["verdict"] == FOUND_IN_ROW
    assert check_in_document("Minimum setback", 3, doc, unit="m")["verdict"] == ABSENT


def test_a_confirm_names_the_pages_where_the_number_was_found():
    r = check_in_document("Scope 1 emissions", 5845, Document.from_texts([P1, P3, P4]))
    assert r["verdict"] == AMBIGUOUS_LABEL and r["found_pages"] == [1, 2] and "5,845" in r["found_line"]
