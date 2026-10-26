"""Causeway step 4a: the Direct Sales Invoice lines to type into the ERP for one date.

Procedure page 3 (Finance > Direct Sales Invoice, warehouse Causeway Cash Sales). The ERP holds
each product's price, so what matters is the product code and the quantity; unit price and value
are shown for checking.

  Normal products  one line per Zoho SKU, Zoho quantity
  Vanilla SIM      VANILASIM, quantity = all EVD + Kunooz quantities (not KFC), price 0
  Kunooz commission 0108002, Kunooz quantity, 2 per unit incl. VAT -> 2 / 1.1 = 1.818
  Kunooz eSIM      ESIM9.5 (Zoho VANILASIM9.5), Kunooz quantity, price from the ERP

Item types come from the rules (`item_types`, conditions on the Zoho columns), so Finance can change
them. EVD and KFC amounts are not on this invoice; they go on the credit note (4b).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import polars as pl

from app.core import conditions
from app.core.money import fmt, money, to_decimal
from app.workflows.base import WorkflowInputError

from .logic import parse_date

NORMAL = "Normal"

DEFAULT_ITEM_TYPES: list[dict[str, Any]] = [
    # First match wins: "EVD - KFC 2" is KFC, not EVD.
    {"label": "KFC", "when": {"field": "Item Name", "op": "contains", "value": "KFC"}},
    {"label": "Kunooz", "when": {"field": "Item Name", "op": "contains", "value": "kunooz"}},
    {"label": "EVD", "when": {"field": "Item Name", "op": "contains", "value": "EVD"}},
]

DEFAULT_INVOICE_RULES: dict[str, Any] = {
    "vanilla_sim_code": "VANILASIM",
    "vanilla_sim_name": "Batelco Vanilla Sim",
    "vanilla_sim_types": ["EVD", "Kunooz"],
    "kunooz_commission_code": "0108002",
    "kunooz_commission_name": "Commission Income - Batelco Starter Pack",
    "kunooz_commission_per_unit_incl_vat": "2",
    "vat_rate_percent": "10",
    "kunooz_esim_code": "ESIM9.5",
    "kunooz_esim_name": "eSIM 9.5(Kunooz)",
}

LINE_COLUMNS = ("Item Name", "SKU", "Quantity", "Item Price")


@dataclass
class ZohoLine:
    item: str
    sku: str
    qty: Decimal
    price: Decimal
    kind: str


@dataclass
class InvoiceLine:
    line: str  # Normal product, Vanilla SIM, Kunooz commission, Kunooz eSIM
    code: str
    name: str
    qty: Decimal
    unit_price: Decimal | None  # None: the ERP fills it in
    value: Decimal | None
    source: list[ZohoLine] = field(default_factory=list)


def qty_text(q: Decimal) -> str:
    """17 -> '17', 431.50 -> '431.5'."""
    return f"{q.normalize():f}"


def day_lines(
    sheets: dict[str, pl.DataFrame], day: date, item_types: list[dict[str, Any]]
) -> list[ZohoLine]:
    """The Zoho item lines dated `day`, each with its type (Normal, KFC, Kunooz, EVD)."""
    df = next(iter(sheets.values()))
    by_lower: dict[str, str] = {}
    for c in df.columns:
        by_lower.setdefault(c.strip().lower(), c)
    missing = [c for c in ("Invoice Date", *LINE_COLUMNS) if c.lower() not in by_lower]
    if missing:
        raise WorkflowInputError(
            f"The Zoho file has no {', '.join(repr(c) for c in missing)} column."
        )
    df = df.select(
        pl.col(by_lower[c.lower()]).alias(c) for c in ("Invoice Date", *LINE_COLUMNS)
    ).with_columns(pl.col(c).cast(pl.String) for c in ("Item Name", "SKU"))
    df = df.filter(pl.Series([parse_date(v) == day for v in df["Invoice Date"]]))
    try:
        typed = conditions.classify(df, "Type", item_types, NORMAL)
    except (conditions.ConditionError, pl.exceptions.PolarsError) as exc:
        raise WorkflowInputError(f"The item_types rule could not be applied: {exc}") from exc
    return [
        ZohoLine(
            item=(r["Item Name"] or "").strip(),
            sku=(r["SKU"] or "").strip(),
            qty=to_decimal(r["Quantity"]),
            price=to_decimal(r["Item Price"]),
            kind=r["Type"],
        )
        for r in typed.iter_rows(named=True)
    ]


def direct_sales_invoice(lines: list[ZohoLine], rules: dict[str, Any]) -> list[InvoiceLine]:
    out: list[InvoiceLine] = []

    # Normal products: one line per SKU, quantities added up across that day's invoices.
    normal: dict[str, InvoiceLine] = {}
    for z in lines:
        if z.kind != NORMAL:
            continue
        code = z.sku or z.item
        if code not in normal:
            normal[code] = InvoiceLine("Normal product", code, "", Decimal(0), z.price, None)
        normal[code].qty += z.qty
        normal[code].source.append(z)
    for ln in normal.values():
        ln.value = money(ln.qty * ln.unit_price) if ln.unit_price is not None else None
    out.extend(normal.values())

    vanilla = [z for z in lines if z.kind in rules["vanilla_sim_types"]]
    if vanilla:
        out.append(
            InvoiceLine(
                "Vanilla SIM",
                rules["vanilla_sim_code"],
                rules["vanilla_sim_name"],
                sum((z.qty for z in vanilla), Decimal(0)),
                money(0),
                money(0),
                vanilla,
            )
        )

    kunooz = [z for z in lines if z.kind == "Kunooz"]
    if kunooz:
        qty = sum((z.qty for z in kunooz), Decimal(0))
        vat = Decimal(1) + to_decimal(rules["vat_rate_percent"]) / Decimal(100)
        per_unit = to_decimal(rules["kunooz_commission_per_unit_incl_vat"]) / vat
        out.append(
            InvoiceLine(
                "Kunooz commission",
                rules["kunooz_commission_code"],
                rules["kunooz_commission_name"],
                qty,
                money(per_unit),
                money(qty * per_unit),
                kunooz,
            )
        )
        out.append(
            InvoiceLine(
                "Kunooz eSIM",
                rules["kunooz_esim_code"],
                rules["kunooz_esim_name"],
                qty,
                None,
                None,
                kunooz,
            )
        )
    return out


def reference(ln: InvoiceLine) -> str:
    """The Zoho items behind a line, with their SKU and quantity, for checking."""
    return "; ".join(f"{z.item} [{z.sku}] x {qty_text(z.qty)}" for z in ln.source)


def table_rows(invoice: list[InvoiceLine]) -> list[list[Any]]:
    return [
        [
            i,
            ln.line,
            ln.code,
            ln.name,
            qty_text(ln.qty),
            fmt(ln.unit_price) if ln.unit_price is not None else "From ERP",
            fmt(ln.value) if ln.value is not None else "From ERP",
            reference(ln),
        ]
        for i, ln in enumerate(invoice, start=1)
    ]


TABLE_COLUMNS = [
    "#",
    "Line",
    "Product code",
    "ERP name",
    "Qty",
    "Unit price",
    "Value",
    "Zoho items (reference)",
]
