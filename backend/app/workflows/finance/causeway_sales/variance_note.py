"""Causeway: the Credit Note (JV Type) for the variance of one date.

  Line 1  Credit CAUSEWAY (Causeway Cash Sales)            = the whole variance
  Line 2  Debit  201002004001 (Batelco marketing fund)     = the part the user gives it
  Line 3  Debit  501002056 (Business Promotion)            = the rest
The user splits the variance after the run: all to one account, or between both. The two debits
must add up to the variance exactly. Until the user confirms, all of it is on the marketing fund.

ERP upload file (CreditNoteJV-.xlsx), from the user's PACT template (templates/CreditNoteJV-.xlsx).
Every condition below is in docs/causeway/erp-files.md with the reason for it.
  Doc Date       the sales date of the run (the reconciliation date)
  DocPrefix      "YQ-<yy>-<mm>" from the sales date: 21/10/2026 -> YQ-26-10
  Doc No         left empty (yellow): the accountant types it in PACT
  Account Code   line 1 is 160700-1 / CAUSEWAY in the file (on screen: CAUSEWAY / Causeway Cash
                 Sales, as PACT shows it); then 201002004001 and/or 501002056
  Lines          a debit line is left out when its amount is 0.000 (all to one account = 2 lines)
  Amounts        numbers; the other side of each line is left empty, not 0
  Narration and Remarks  "Causeway Cash Sales Marketing fund against sales date dd/mm/yyyy"
  Business Unit  YQ
"""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.core import excel
from app.core.money import fmt, money
from app.workflows.base import OutputFile, ResultTable, Split, SplitPart

DEFAULT_VARIANCE_RULES: dict[str, Any] = {
    "credit_account_code": "CAUSEWAY",
    "credit_account_name": "Causeway Cash Sales",
    "marketing_fund_code": "201002004001",
    "marketing_fund_name": "Batelco marketing fund",
    "business_promotion_code": "501002056",
    "business_promotion_name": "Business Promotion",
    # ERP upload file (CreditNoteJV-.xlsx). The credit line uses PACT's ledger code in the file.
    "erp_file_name": "CreditNoteJV-.xlsx",
    "erp_credit_account_code": "160700-1",
    "erp_credit_account_name": "CAUSEWAY",
    "erp_doc_prefix": "YQ-{day:%y}-{day:%m}",
    "erp_narration": "Causeway Cash Sales Marketing fund against sales date {day:%d/%m/%Y}",
    "erp_business_unit": "YQ",
}

TEMPLATE = Path(__file__).parent / "templates" / "CreditNoteJV-.xlsx"

TITLE = "Credit Note (Variance)"
COLUMNS = ["#", "Account code", "Account name", "Debit", "Credit"]
MARKETING_FUND = "marketing_fund"
BUSINESS_PROMOTION = "business_promotion"


def narration(day: date) -> str:
    return f"Causeway Cash Sales {day:%d/%m/%Y}"


def split_for(variance: Decimal, rules: dict[str, Any]) -> Split:
    """The popup shown after the run: the variance and the two accounts it can go to."""
    return Split(
        title="Split the variance",
        message="Give the variance to the Batelco marketing fund, to Business Promotion, or "
        "split it between them. The two amounts must add up to the variance exactly.",
        total=fmt(variance),
        parts=[
            SplitPart(MARKETING_FUND, rules["marketing_fund_name"], rules["marketing_fund_code"]),
            SplitPart(
                BUSINESS_PROMOTION,
                rules["business_promotion_name"],
                rules["business_promotion_code"],
            ),
        ],
        default_part=MARKETING_FUND,
        amounts={MARKETING_FUND: fmt(variance), BUSINESS_PROMOTION: fmt(0)},
    )


def erp_rows(
    day: date, variance: Decimal, amounts: dict[str, Decimal], rules: dict[str, Any]
) -> list[list[Any]]:
    """The CreditNoteJV upload rows, in the template's column order (A-K)."""
    doc_date = datetime(day.year, day.month, day.day)
    prefix = rules["erp_doc_prefix"].format(day=day)
    text = rules["erp_narration"].format(day=day)
    unit = rules["erp_business_unit"]

    def line(code: str, name: str, debit: Decimal | None, credit: Decimal | None) -> list[Any]:
        # Doc No (C) and Terminal ID (H) stay empty: Doc No is typed in PACT by the accountant.
        return [doc_date, prefix, None, code, name, debit, credit, None, text, text, unit]

    rows = [
        line(rules["erp_credit_account_code"], rules["erp_credit_account_name"], None, variance)
    ]
    for key, code, name in (
        (MARKETING_FUND, rules["marketing_fund_code"], rules["marketing_fund_name"]),
        (BUSINESS_PROMOTION, rules["business_promotion_code"], rules["business_promotion_name"]),
    ):
        amount = money(amounts.get(key, 0))
        if amount:  # an account with 0.000 gets no line in the upload file
            rows.append(line(code, name, amount, None))
    return rows


def erp_file(
    day: date, variance: Decimal, amounts: dict[str, Decimal], rules: dict[str, Any]
) -> OutputFile:
    data = excel.fill_template(TEMPLATE, erp_rows(day, variance, amounts, rules))
    return OutputFile(rules["erp_file_name"], data)


def table(
    day: date,
    variance: Decimal,
    amounts: dict[str, Decimal],
    rules: dict[str, Any],
    confirmed: bool,
) -> ResultTable:
    marketing = money(amounts.get(MARKETING_FUND, 0))
    promotion = money(amounts.get(BUSINESS_PROMOTION, 0))
    note = f"Narration: {narration(day)}"
    if not confirmed:
        note += ". Split not confirmed yet: all of the variance is on the Batelco marketing fund."
    return ResultTable(
        title=TITLE,
        columns=COLUMNS,
        rows=[
            [1, rules["credit_account_code"], rules["credit_account_name"], fmt(0), fmt(variance)],
            [2, rules["marketing_fund_code"], rules["marketing_fund_name"], fmt(marketing), fmt(0)],
            [
                3,
                rules["business_promotion_code"],
                rules["business_promotion_name"],
                fmt(promotion),
                fmt(0),
            ],
            ["", "", "Total", fmt(marketing + promotion), fmt(variance)],
        ],
        note=note,
        note_tone="neutral" if confirmed else "warn",
        file=rules["erp_file_name"],
    )
