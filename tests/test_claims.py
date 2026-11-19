"""Pulling figures out of an AI's answer. Right answers written before the code is run."""
import pytest
from proof_layer.claims import extract_claims


def got(text):
    return [(c.description, c.value) for c in extract_claims(text)]


def test_a_plain_sentence_and_a_year_is_not_a_figure():
    assert got("Scope 1 emissions were 5,845 tCO2-e in 2025.") == [("Scope 1 emissions", 5845.0)]


def test_scope_and_table_numbers_name_things_they_are_not_figures():
    # "Table 3" points into the document; it is dropped. "Scope 2" tells rows apart; it is kept.
    assert got("Table 3 shows total energy consumption was 1,074,807 GJ.") == [("total energy consumption", 1074807.0)]
    assert got("In Scope 2, emissions were 19,691.") == [("Scope 2 emissions", 19691.0)]


def test_bullets_and_bold_markdown():
    assert got("- **Total energy consumption**: 1,074,807 GJ") == [("Total energy consumption", 1074807.0)]
    assert got("1. Scope 1 emissions were 5,845") == [("Scope 1 emissions", 5845.0)]


def test_markdown_table_rows_use_the_first_cell_as_the_description():
    table = "| Item | FY24 | FY25 |\n|---|---|---|\n| Water withdrawn | 22.975 | 26.511 |"
    assert got(table) == [("Water withdrawn", 22.975), ("Water withdrawn", 26.511)]


def test_two_numbers_in_one_sentence_share_the_description():
    assert got("Scope 1 emissions fell from 6,102 to 5,845.") == [
        ("Scope 1 emissions", 6102.0), ("Scope 1 emissions", 5845.0)]


def test_a_new_item_in_the_same_sentence_gets_its_own_description():
    claims = extract_claims("Scope 1 emissions were 5,845 and total energy consumption was 1,074,807 GJ.")
    assert [c.value for c in claims] == [5845.0, 1074807.0]
    assert "energy" in claims[1].description.lower() and "energy" not in claims[0].description.lower()


def test_units_are_picked_up_when_the_checker_knows_them():
    c = extract_claims("The front setback is 6 m.")[0]
    assert c.unit == "m" and c.value == 6.0
    assert extract_claims("Landscaped area is 35%.")[0].unit == "%"
    assert extract_claims("Emissions were 5,845 tonnes.")[0].unit is None


def test_scaled_figures_are_flagged_not_guessed():
    c = extract_claims("Revenue was $1.1 billion.")[0]
    assert c.scaled is True and c.value == 1.1
    assert extract_claims("Revenue was 1,100,000.")[0].scaled is False


def test_numbers_glued_to_letters_are_not_figures():
    assert got("FY25 emissions of CO2 and Q3 results") == []


def test_no_numbers_no_claims():
    assert extract_claims("The report discusses climate risk in general terms.") == []
    assert extract_claims("") == []
    assert extract_claims(None) == []


def test_repeats_are_dropped():
    assert len(extract_claims("Scope 1 emissions were 5,845.\nScope 1 emissions were 5,845.")) == 1


def test_negative_figures_keep_their_sign():
    assert got("Net change was -5 tonnes.")[0][1] == -5.0
