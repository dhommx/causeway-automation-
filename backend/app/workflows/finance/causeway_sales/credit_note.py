"""Causeway step 4b: the Credit Note (JV Type) for the EVD and KFC lines of one date.

Procedure pages 3-4.
  EVD  amount = Zoho quantity x the price at the end of the SKU ("VANILASIM 10.5" -> 10.5)
  KFC  the Zoho quantity is already the amount (78.5 x 1), so it is added as it is
  Debit  CAUSEWAY (Causeway Cash Sales)  = the credit note total
  Credit the KFC terminal account (terminal number from the Zoho item), shown without an amount
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.core.money import fmt, money

from .invoice import ZohoLine, qty_text

DEFAULT_CREDIT_NOTE_RULES: dict[str, Any] = {
    "debit_account_code": "CAUSEWAY",
    "debit_account_name": "Causeway Cash Sales",
    # Credit account name per KFC terminal number. Unknown terminals are shown without a name.
    "kfc_account_names": {"056194020436028": "CAUSEWAY CASH SALES 2"},
}

TERMINAL = re.compile(r"\d{10,}")  # KFC terminal numbers are long digit runs (056194020436028)
NUMBER = re.compile(r"\d+(?:\.\d+)?")


@dataclass
class CreditItem:
    kind: str  # EVD or KFC
    item: str
    sku: str
    qty: Decimal
    price: Decimal | None  # EVD: from the SKU; KFC: none, the quantity is the amount
    amount: Decimal
    price_source: str = ""


@dataclass
class CreditNote:
    items: list[CreditItem]
    total: Decimal
    terminals: list[str]
    warnings: list[str] = field(default_factory=list)


def price_from_sku(sku: str) -> Decimal | None:
    """The number at the end of the SKU: 'VANILASIM  10.5' -> 10.5, 'VANILASIM 12' -> 12."""
    found = NUMBER.findall(sku)
    return Decimal(found[-1]) if found else None


def kfc_terminal(z: ZohoLine) -> str | None:
    """The terminal number from the SKU, or from the item name when the SKU lacks it."""
    for text in (z.sku, z.item):
        if m := TERMINAL.search(text):
            return m.group()
    return None


def credit_note(lines: list[ZohoLine]) -> CreditNote:
    items: dict[tuple[str, str, str], CreditItem] = {}
    terminals: list[str] = []
    warnings: list[str] = []

    for z in lines:
        if z.kind not in ("EVD", "KFC"):
            continue
        key = (z.kind, z.item, z.sku)
        if key not in items:
            price, source = None, ""
            if z.kind == "EVD":
                price, source = price_from_sku(z.sku), "SKU"
                if price is None:
                    price, source = z.price, "Zoho Item Price"
                    warnings.append(
                        f"{z.item}: no price at the end of SKU '{z.sku}', "
                        f"so the Zoho Item Price {fmt(z.price)} was used."
                    )
            items[key] = CreditItem(z.kind, z.item, z.sku, Decimal(0), price, Decimal(0), source)
        items[key].qty += z.qty
        if z.kind == "KFC":
            terminal = kfc_terminal(z)
            if terminal and terminal not in terminals:
                terminals.append(terminal)
            elif not terminal:
                warnings.append(f"{z.item}: no KFC terminal number in the item name or SKU.")

    for ci in items.values():
        ci.amount = money(ci.qty * ci.price) if ci.price is not None else money(ci.qty)

    ordered = sorted(items.values(), key=lambda c: c.kind == "KFC")  # EVD first, then KFC
    total = sum((c.amount for c in ordered), Decimal(0))
    if ordered and not terminals:
        warnings.append("No KFC terminal number for this date, so the credit account is not known.")
    return CreditNote(ordered, money(total), terminals, warnings)


CALC_COLUMNS = ["Type", "Zoho item", "Zoho SKU", "Calculation", "Amount"]
JV_COLUMNS = ["#", "Account code", "Account name", "Debit", "Credit"]


def calc_rows(note: CreditNote) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for c in note.items:
        if c.kind == "EVD":
            calc = f"{qty_text(c.qty)} x {qty_text(c.price)} (price from {c.price_source})"
        else:
            calc = "Already a total (quantity is the amount)"
        rows.append([c.kind, c.item, c.sku, calc, fmt(c.amount)])
    rows.append(["Total", "", "", "EVD + KFC", fmt(note.total)])
    return rows


def jv_rows(note: CreditNote, rules: dict[str, Any]) -> list[list[Any]]:
    names = rules.get("kfc_account_names") or {}
    rows: list[list[Any]] = [
        [1, rules["debit_account_code"], rules["debit_account_name"], fmt(note.total), fmt(0)]
    ]
    # The credit line is shown so it can be typed in; its amount is left for the ERP.
    for i, terminal in enumerate(note.terminals or [""], start=2):
        rows.append([i, terminal, names.get(terminal, ""), fmt(0), ""])
    return rows
