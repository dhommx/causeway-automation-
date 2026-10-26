import polars as pl
import pytest

from app.core.conditions import ConditionError, apply_filter, classify

DF = pl.DataFrame(
    {
        "Item Name": [
            "Preconfigured Starter",
            "Blank 9.5(kunooz)",
            "Blank 12(EVD 2)",
            "EVD - KFC 2 - 0561",
            None,
        ],
        "Quantity": [17.0, 6.0, 4.0, 78.5, 1.0],
    }
)


def test_contains_ignores_case_and_nulls():
    assert apply_filter(DF, {"field": "Item Name", "op": "contains", "value": "KUNOOZ"}).height == 1


def test_groups():
    cond = {
        "all": [
            {"field": "Item Name", "op": "contains", "value": "evd"},
            {"field": "Quantity", "op": "lt", "value": 10},
        ]
    }
    assert apply_filter(DF, cond)["Quantity"].to_list() == [4.0]
    assert apply_filter(DF, {"not": cond}).height == 4
    assert (
        apply_filter(
            DF,
            {
                "any": [
                    {"field": "Quantity", "op": "gt", "value": 50},
                    {"field": "Item Name", "op": "is_empty"},
                ]
            },
        ).height
        == 2
    )


def test_between_and_in():
    assert apply_filter(DF, {"field": "Quantity", "op": "between", "value": [4, 17]}).height == 3
    assert (
        apply_filter(DF, {"field": "Item Name", "op": "in", "value": ["BLANK 12(EVD 2)"]}).height
        == 1
    )


def test_classify_first_match_wins():
    cases = [
        {"label": "KFC", "when": {"field": "Item Name", "op": "contains", "value": "KFC"}},
        {"label": "EVD", "when": {"field": "Item Name", "op": "contains", "value": "EVD"}},
    ]
    out = classify(DF, "Type", cases, default="Normal")
    assert out["Type"].to_list() == ["Normal", "Normal", "EVD", "KFC", "Normal"]


def test_unknown_operator():
    with pytest.raises(ConditionError):
        apply_filter(DF, {"field": "Quantity", "op": "approx", "value": 1})
