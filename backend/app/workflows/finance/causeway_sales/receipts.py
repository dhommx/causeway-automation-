"""Causeway step 5: the three receipts to type into the ERP (procedure page 5).

  5a Cash Receipt   CAUSEWAY = cash amount
  5b Bank Receipt   CAUSEWAY = AFS total, AFS   = -(AFS total x 2.2%)
  5c Bank Receipt   CAUSEWAY = PIE total, PAYME = -(PIE total x 1.65%)

Account codes, names and the commission rates are rules (`receipts`).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.core.money import fmt, money, percent_of

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
}

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
