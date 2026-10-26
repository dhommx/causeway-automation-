"""The condition engine: rules saved as JSON, turned into Polars filter expressions.

A condition is either a single check
    {"field": "Item Name", "op": "contains", "value": "KFC"}
or a group
    {"all": [cond, cond, ...]}   every one must match
    {"any": [cond, cond, ...]}   at least one must match
    {"not": cond}

Text checks ignore upper/lower case. Workflows store their conditions in their rule set,
so users can change them without a code change, and each run records the version it used.
"""

from typing import Any

import polars as pl

OPERATORS = {
    "eq": "equals",
    "ne": "does not equal",
    "gt": "greater than",
    "gte": "greater than or equal",
    "lt": "less than",
    "lte": "less than or equal",
    "between": "between (inclusive)",
    "in": "is one of",
    "not_in": "is not one of",
    "contains": "contains",
    "not_contains": "does not contain",
    "starts_with": "starts with",
    "ends_with": "ends with",
    "is_empty": "is empty",
    "not_empty": "is not empty",
}


class ConditionError(ValueError):
    pass


def _text(col: pl.Expr) -> pl.Expr:
    return col.cast(pl.String).str.to_lowercase()


def _lower(value: Any) -> Any:
    return value.lower() if isinstance(value, str) else value


def to_expr(cond: dict[str, Any]) -> pl.Expr:
    """Turn a condition (or group) into a Polars boolean expression."""
    if "all" in cond:
        parts = [to_expr(c) for c in cond["all"]]
        return pl.all_horizontal(parts) if parts else pl.lit(True)
    if "any" in cond:
        parts = [to_expr(c) for c in cond["any"]]
        return pl.any_horizontal(parts) if parts else pl.lit(False)
    if "not" in cond:
        return ~to_expr(cond["not"])

    try:
        field, op = cond["field"], cond["op"]
    except KeyError as exc:
        raise ConditionError(f"Condition is missing {exc.args[0]!r}: {cond}") from exc
    if op not in OPERATORS:
        raise ConditionError(f"Unknown operator {op!r}. Allowed: {', '.join(OPERATORS)}")

    col = pl.col(field)
    value = cond.get("value")
    match op:
        case "eq":
            return _text(col) == _lower(value) if isinstance(value, str) else col == value
        case "ne":
            return _text(col) != _lower(value) if isinstance(value, str) else col != value
        case "gt":
            return col > value
        case "gte":
            return col >= value
        case "lt":
            return col < value
        case "lte":
            return col <= value
        case "between":
            low, high = value
            return col.is_between(low, high, closed="both")
        case "in":
            return _text(col).is_in([_lower(v) for v in value])
        case "not_in":
            return ~_text(col).is_in([_lower(v) for v in value])
        case "contains":
            return _text(col).str.contains(str(value).lower(), literal=True).fill_null(False)
        case "not_contains":
            return ~_text(col).str.contains(str(value).lower(), literal=True).fill_null(False)
        case "starts_with":
            return _text(col).str.starts_with(str(value).lower()).fill_null(False)
        case "ends_with":
            return _text(col).str.ends_with(str(value).lower()).fill_null(False)
        case "is_empty":
            return col.is_null() | (col.cast(pl.String).str.strip_chars() == "")
        case "not_empty":
            return col.is_not_null() & (col.cast(pl.String).str.strip_chars() != "")
    raise ConditionError(op)  # unreachable


def apply_filter(df: pl.DataFrame, cond: dict[str, Any]) -> pl.DataFrame:
    """Rows that match the condition."""
    return df.filter(to_expr(cond))


def classify(
    df: pl.DataFrame, column: str, cases: list[dict[str, Any]], default: str
) -> pl.DataFrame:
    """Add a label column. The first case that matches wins, so order cases from most specific.

    cases = [{"label": "KFC", "when": {...}}, {"label": "EVD", "when": {...}}]
    """
    expr = pl.lit(default)
    for case in reversed(cases):
        expr = pl.when(to_expr(case["when"])).then(pl.lit(case["label"])).otherwise(expr)
    return df.with_columns(expr.alias(column))
