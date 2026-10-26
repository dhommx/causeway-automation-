"""Causeway step 1: reconcile Cash + AFS + PIE against the Zoho total for one date.

marketing fund = Zoho total - (Cash + AFS + PIE)

The AFS amount is the 'Total' row of the AFS settlement report (sheet MerchantAUBTerminalWise),
one block per terminal: a 'Terminal ID:...' row, a header row with 'Tran Amt', 'Commission',
'VAT', 'Net', the transactions, then the 'Total' row. Amounts are text such as '8.500 BHD'.

The Zoho total comes from the invoice export: every item line repeats its invoice's Total, so
each invoice for the date is counted once.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

import polars as pl

from app.core.money import money
from app.workflows.base import WorkflowInputError

AFS_AMOUNTS = ("Tran Amt", "Commission", "VAT", "Net")


@dataclass
class AfsTerminal:
    terminal: str
    tran_amt: Decimal
    commission: Decimal
    vat: Decimal
    net: Decimal


@dataclass
class AfsReport:
    terminals: list[AfsTerminal]
    dates: list[date]
    transactions: int

    def total(self, name: str) -> Decimal:
        return sum((getattr(t, name) for t in self.terminals), Decimal(0))


@dataclass
class ZohoInvoice:
    number: str
    status: str
    total: Decimal


@dataclass
class ZohoDay:
    invoices: list[ZohoInvoice]
    lines: int
    total: Decimal = field(init=False)

    def __post_init__(self) -> None:
        self.total = sum((i.total for i in self.invoices), Decimal(0))


def amount(value: object) -> Decimal:
    """'8.500 BHD', '-0.170', 91 or None as BHD."""
    if value is None:
        return money(0)
    if isinstance(value, str):
        value = re.sub(r"[^0-9.\-]", "", value) or "0"
    return money(value)


def parse_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _cells(row: tuple) -> list[str]:
    return ["" if v is None or str(v).startswith("__UNNAMED__") else str(v).strip() for v in row]


def read_afs(sheets: dict[str, pl.DataFrame]) -> AfsReport:
    terminals: list[AfsTerminal] = []
    dates: set[date] = set()
    transactions = 0

    for sheet, df in sheets.items():
        # The first sheet row becomes the column names when read, so put it back as a row.
        rows = [tuple(df.columns), *df.rows()]
        cols: dict[str, int] | None = None
        terminal = ""
        for row in rows:
            cells = _cells(row)
            first = next((c for c in cells if c), "")
            if first.lower().startswith("terminal id"):
                terminal = first.split(":", 1)[-1].strip()
                continue
            if "Tran Amt" in cells:
                cols = {c: cells.index(c) for c in ("Tran Date", *AFS_AMOUNTS) if c in cells}
                continue
            if cols is None:
                continue
            if any(c.lower() == "total" for c in cells):
                values = {c: amount(row[cols[c]]) if c in cols else money(0) for c in AFS_AMOUNTS}
                terminals.append(
                    AfsTerminal(
                        terminal=terminal or sheet,
                        tran_amt=values["Tran Amt"],
                        commission=values["Commission"],
                        vat=values["VAT"],
                        net=values["Net"],
                    )
                )
                cols = None
                continue
            if "Tran Date" in cols and (d := parse_date(row[cols["Tran Date"]])):
                dates.add(d)
                transactions += 1

    if not terminals:
        raise WorkflowInputError(
            "No 'Total' row was found in the AFS file. Is this the AFS settlement report?"
        )
    return AfsReport(terminals=terminals, dates=sorted(dates), transactions=transactions)


def read_zoho_day(sheets: dict[str, pl.DataFrame], day: date) -> ZohoDay:
    df = next(iter(sheets.values()), None)
    if df is None:
        raise WorkflowInputError("The Zoho file has no sheets.")
    for column in ("Invoice Date", "Invoice Number", "Total"):
        if column not in df.columns:
            raise WorkflowInputError(
                f"The Zoho file has no '{column}' column. Is this the Zoho invoice export?"
            )
    has_status = "Invoice Status" in df.columns

    invoices: dict[str, ZohoInvoice] = {}
    dates_in_file: set[date] = set()
    lines = 0
    for row in df.iter_rows(named=True):
        d = parse_date(row["Invoice Date"])
        if not d:
            continue
        dates_in_file.add(d)
        if d != day:
            continue
        lines += 1
        number = str(row["Invoice Number"] or "").strip()
        if number not in invoices:
            invoices[number] = ZohoInvoice(
                number=number,
                status=str(row["Invoice Status"] or "") if has_status else "",
                total=amount(row["Total"]),
            )

    if not invoices:
        if dates_in_file:
            span = f"{min(dates_in_file):%d/%m/%Y} to {max(dates_in_file):%d/%m/%Y}"
            raise WorkflowInputError(
                f"No Zoho invoices for {day:%d/%m/%Y}. The file covers {span}."
            )
        raise WorkflowInputError("The Zoho file has no invoice rows.")
    return ZohoDay(invoices=list(invoices.values()), lines=lines)
