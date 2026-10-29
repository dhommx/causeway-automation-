"""Causeway step 5: the three receipts to type into the ERP (procedure page 5).

  5a Cash Receipt   CAUSEWAY = cash amount
  5b Bank Receipt   CAUSEWAY = AFS total, AFS   = -(AFS total x 2.2%)
  5c Bank Receipt   CAUSEWAY = PIE total, PAYME = -(PIE total x 1.65%)

Account codes, names and the commission rates are rules (`receipts`).

ERP upload file for 5a (RECEIPTS.xlsx, sheet RECEIPTS), from the user's PACT template
(templates/RECEIPTS.xlsx). Every condition is in docs/causeway/erp-files.md with the reason.
  Doc Date       the cash deposit date entered for the run
  DocPrefix      "YQ-<yy>-<mm>-" from the cash deposit date (trailing dash as in the template)
  Doc No         left empty: the accountant types it in PACT
  Cash/Bank GL   101001004021 / AUB BHD Account 0016-525530-001 (the bank the cash goes into)
  Account        101001001001 / Cash in Hand - Bahraini Dinars
  Property, Unit, Terminal ID  "-"
  Amount         the cash amount
  Reference      CASH DEPOSIT
  Description    "Causeway Cash sales dd/mm/yyyy" with the sales date
  CHEQUE DATE    formula =A<row> (the Doc Date), as in the template
  CHEQUE NUMBER  formula joining Description, CHEQUE DATE and Doc No, as in the template, so it
                 fills in once the accountant types the Doc No
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.core import excel
from app.core.money import fmt, money, percent_of
from app.workflows.base import OutputFile

DEFAULT_RECEIPT_RULES: dict[str, Any] = {
    "customer_code": "CAUSEWAY",
    "customer_name": "Causeway Cash Sales",
    "cash_receipt_mode": "Cash in Hand - Bahraini Dinars",
    "bank_debit_account": "AUB BHD Account 0016-525530-001",
    "afs_account_code": "AFS",
    "afs_account_name": "ARAB FINANCIAL SERVICES CO. B.S.C.(CLOSED)",
    "afs_commission_percent": "2.2",
    "pie_account_code": "PAYME",
    "pie_account_name": "PAYMENT INTERNATIONAL ENTERPRISE-QR Charges",
    "pie_commission_percent": "1.65",
    # ERP upload file for the cash receipt (RECEIPTS.xlsx).
    "cash_erp_file_name": "RECEIPTS.xlsx",
    "cash_erp_doc_prefix": "YQ-{day:%y}-{day:%m}-",
    "cash_erp_business_unit": "YQ",
    "cash_erp_bank_gl_code": "101001004021",
    "cash_erp_bank_gl_name": "AUB BHD Account 0016-525530-001",
    "cash_erp_account_code": "101001001001",
    "cash_erp_account_name": "Cash in Hand - Bahraini Dinars",
    "cash_erp_reference": "CASH DEPOSIT",
    "cash_erp_description": "Causeway Cash sales {sales_day:%d/%m/%Y}",
}

RECEIPTS_TEMPLATE = Path(__file__).parent / "templates" / "RECEIPTS.xlsx"

COLUMNS = [
    "Account code",
    "Account name",
    "Amount",
    "Cheque number",
    "Receipt mode / Debit account",
]


@dataclass
class Receipt:
    title: str  # tab name, e.g. "Receipt (Cash)"
    mode_or_account: str
    cheque: str
    lines: list[tuple[str, str, Decimal]]  # (account code, account name, amount)
    commission_note: str = ""

    @property
    def net(self) -> Decimal:
        return money(sum((amt for _, _, amt in self.lines), Decimal(0)))

    def rows(self) -> list[list[Any]]:
        """Its lines as typed into the ERP."""
        return [
            [code, name, fmt(amt), self.cheque, self.mode_or_account]
            for code, name, amt in self.lines
        ]


def receipts(
    day: date,
    cash: Decimal,
    afs: Decimal,
    pie: Decimal,
    afs_batches: list[str],
    rules: dict[str, Any],
) -> list[Receipt]:
    code, name = rules["customer_code"], rules["customer_name"]
    afs_rate, pie_rate = rules["afs_commission_percent"], rules["pie_commission_percent"]
    afs_commission = percent_of(afs, afs_rate)
    pie_commission = percent_of(pie, pie_rate)
    return [
        Receipt(
            "Receipt (Cash)",
            rules["cash_receipt_mode"],
            "",
            [(code, name, money(cash))],
        ),
        Receipt(
            "Receipt (AFS)",
            rules["bank_debit_account"],
            " ".join(["AFS", *afs_batches]),
            [
                (code, name, money(afs)),
                (rules["afs_account_code"], rules["afs_account_name"], -afs_commission),
            ],
            f"{fmt(afs)} x {afs_rate}% = {fmt(afs_commission)}",
        ),
        Receipt(
            "Receipt (PIE)",
            rules["bank_debit_account"],
            f"MSWIPE {day:%d/%m/%Y}",
            [
                (code, name, money(pie)),
                (rules["pie_account_code"], rules["pie_account_name"], -pie_commission),
            ],
            f"{fmt(pie)} x {pie_rate}% = {fmt(pie_commission)}",
        ),
    ]


def cash_erp_rows(
    sales_day: date, deposit_day: date, cash: Decimal, rules: dict[str, Any]
) -> list[list[Any]]:
    """The RECEIPTS upload row for the cash, in the template's column order (A-P)."""
    return [
        [
            datetime(deposit_day.year, deposit_day.month, deposit_day.day),
            rules["cash_erp_doc_prefix"].format(day=deposit_day),
            None,  # Doc No: typed in PACT by the accountant
            rules["cash_erp_business_unit"],
            rules["cash_erp_bank_gl_code"],
            rules["cash_erp_bank_gl_name"],
            rules["cash_erp_account_code"],
            rules["cash_erp_account_name"],
            "-",
            "-",
            "-",
            money(cash),
            rules["cash_erp_reference"],
            rules["cash_erp_description"].format(sales_day=sales_day),
            lambda r: f"=A{r}",
            lambda r: f'=CONCATENATE(N{r}," ",TEXT(O{r},"DD/MM/YYYY")," ",C{r})',
        ]
    ]


def cash_erp_file(
    sales_day: date, deposit_day: date, cash: Decimal, rules: dict[str, Any]
) -> OutputFile:
    data = excel.fill_template(
        RECEIPTS_TEMPLATE, cash_erp_rows(sales_day, deposit_day, cash, rules)
    )
    return OutputFile(rules["cash_erp_file_name"], data)
