"""01 Causeway Sales Reconciliation (Proposal 01, process notes: neasi_organised.txt).

Step 1 (reconcile): marketing fund = Zoho total - (Cash + AFS + PIE) for the sales date.
The ERP posting steps (sales invoice, credit notes, receipts) are not written yet.
"""

from datetime import date, datetime

import polars as pl

from app.core import excel
from app.core.money import fmt, money
from app.workflows.base import (
    IMAGE_ACCEPT,
    FileSlot,
    ManualField,
    Metric,
    ResultTable,
    RunContext,
    RunResult,
    Workflow,
    WorkflowInputError,
)

from .credit_note import (
    CALC_COLUMNS,
    DEFAULT_CREDIT_NOTE_RULES,
    JV_COLUMNS,
    calc_rows,
    credit_note,
    jv_rows,
)
from .invoice import (
    DEFAULT_INVOICE_RULES,
    DEFAULT_ITEM_TYPES,
    TABLE_COLUMNS,
    day_lines,
    direct_sales_invoice,
    table_rows,
)
from .logic import (
    ZOHO_COLUMNS,
    ZOHO_SHEET,
    format_zoho,
    read_afs,
    read_zoho_day,
    zoho_with_formatted_sheet,
)
from .receipts import COLUMNS as RECEIPT_COLUMNS
from .receipts import DEFAULT_RECEIPT_RULES, receipts


class CausewaySalesReconciliation(Workflow):
    key = "causeway-sales-reconciliation"
    name = "Causeway Sales Reconciliation"
    department = "finance"
    number = 1
    icon = "receipt"
    summary = "Collect, calculate, review and record daily Causeway sales from AFS and PIE POS."
    current_time = "15 min / day"
    target_time = "5 min / day"
    frequency = "Daily, Sun-Thu"

    file_slots = (
        FileSlot(
            key="afs",
            label="AFS settlement report",
            help="The AFS Excel from the email. Its Total row gives the AFS amount.",
            password_protected=True,
        ),
        FileSlot(
            key="zoho",
            label="Zoho invoice export",
            help="Zoho > Invoices > export. The total is taken for the sales date.",
        ),
        FileSlot(
            key="images",
            label="Images (for reference)",
            help="Screenshots to read amounts from. Shown on screen, not processed.",
            required=False,
            multiple=True,
            accept=IMAGE_ACCEPT,
            kind="reference",
        ),
    )

    manual_fields = (
        ManualField(key="sales_date", label="Sales date", type="date"),
        ManualField(
            key="cash", label="Cash amount (BHD)", type="money", help="From the email report."
        ),
        ManualField(
            key="pie", label="PIE / MSwipe amount (BHD)", type="money", help="From the email image."
        ),
    )

    default_rules = {
        # Columns kept on the new sheet of the downloaded Zoho file, in this order.
        "zoho_columns": ZOHO_COLUMNS,
        # How each Zoho item line is typed (first match wins); anything else is a normal product.
        "item_types": DEFAULT_ITEM_TYPES,
        # Direct Sales Invoice codes and the Kunooz commission (procedure page 3).
        "direct_sales_invoice": DEFAULT_INVOICE_RULES,
        # Credit Note (JV Type) accounts for the EVD + KFC amounts (procedure page 4).
        "credit_note": DEFAULT_CREDIT_NOTE_RULES,
        # Cash and bank receipts: accounts and commission rates (procedure page 5).
        "receipts": DEFAULT_RECEIPT_RULES,
    }

    def run(self, ctx: RunContext) -> RunResult:
        day = _sales_date(ctx.params.get("sales_date"))
        cash = _amount(ctx.params.get("cash"), "Cash amount")
        pie = _amount(ctx.params.get("pie"), "PIE amount")
        afs_file = ctx.files_for("afs")[0]
        zoho_file = ctx.files_for("zoho")[0]

        afs = read_afs(afs_file.sheets())
        afs_amount = afs.total("tran_amt")
        ctx.note(f"{afs_file.name}: {afs.transactions} transactions, Total row {fmt(afs_amount)}")
        zoho_sheets = zoho_file.sheets()
        zoho = read_zoho_day(zoho_sheets, day)
        ctx.note(
            f"{zoho_file.name}: {zoho.lines} item lines dated {day:%d/%m/%Y}, "
            f"{len(zoho.invoices)} invoice(s), total {fmt(zoho.total)}"
        )

        payments = cash + afs_amount + pie
        fund = zoho.total - payments
        ctx.note(f"Marketing fund {fmt(zoho.total)} - {fmt(payments)} = {fmt(fund)}")

        warnings = []
        if afs.dates and afs.dates != [day]:
            shown = ", ".join(f"{d:%d/%m/%Y}" for d in afs.dates)
            warnings.append(
                f"The AFS file has transactions dated {shown}, not {day:%d/%m/%Y}. "
                "Check that the right day's report was uploaded."
            )
        if fund < 0:
            warnings.append(
                "Payments are more than the Zoho total. The marketing fund cannot be negative, "
                "so check the amounts before posting."
            )

        reconciliation = ResultTable(
            title="Reconciliation",
            columns=["Value", "Source", "BHD"],
            rows=[
                ["Cash", "Entered", fmt(cash)],
                ["AFS (card machine)", "AFS file, Total row, Tran Amt", fmt(afs_amount)],
                ["PIE (MSwipe)", "Entered", fmt(pie)],
                ["Sum of payments", "Cash + AFS + PIE", fmt(payments)],
                ["Zoho total", f"Zoho invoices dated {day:%d/%m/%Y}", fmt(zoho.total)],
                ["Marketing fund", "Zoho total - Sum of payments", fmt(fund)],
            ],
        )
        steps = ResultTable(
            title="How it was worked out",
            columns=["Step", "Detail"],
            rows=[
                [
                    1,
                    f"Opened {afs_file.name} with its password and read the Total row: "
                    f"{afs.transactions} transactions totalling {fmt(afs_amount)}.",
                ],
                [
                    2,
                    f"Kept the Zoho rows dated {day:%d/%m/%Y} ({zoho.lines} item lines) and took each "
                    f"invoice's Total once: {fmt(zoho.total)}.",
                ],
                [3, f"Payments: {fmt(cash)} + {fmt(afs_amount)} + {fmt(pie)} = {fmt(payments)}."],
                [
                    4,
                    f"Marketing fund: {fmt(zoho.total)} - {fmt(payments)} = {fmt(fund)}. "
                    "Posted in step 6 as the Batelco marketing fund credit note.",
                ],
            ],
        )
        terminals = ResultTable(
            title="AFS terminals",
            columns=["Terminal", "Tran Amt", "Commission", "VAT", "Net"],
            rows=[
                [t.terminal, fmt(t.tran_amt), fmt(t.commission), fmt(t.vat), fmt(t.net)]
                for t in afs.terminals
            ],
        )
        invoices = ResultTable(
            title="Zoho invoices",
            columns=["Invoice", "Status", "Total"],
            rows=[[i.number, i.status, fmt(i.total)] for i in zoho.invoices],
        )
        # Rules saved before a setting existed fall back to its default.
        rules = {**self.default_rules, **ctx.rules}
        dsi_rules = {**DEFAULT_INVOICE_RULES, **(rules.get("direct_sales_invoice") or {})}
        lines = day_lines(zoho_sheets, day, rules["item_types"])
        dsi = direct_sales_invoice(lines, dsi_rules)
        ctx.note(
            f"Direct Sales Invoice: {len(dsi)} line(s): "
            + ", ".join(f"{ln.code} x {ln.qty.normalize():f}" for ln in dsi)
        )
        sales_invoice = ResultTable(
            title="Direct Sales Invoice",
            columns=TABLE_COLUMNS,
            rows=table_rows(dsi),
        )

        cn_rules = {**DEFAULT_CREDIT_NOTE_RULES, **(rules.get("credit_note") or {})}
        note = credit_note(lines)
        warnings.extend(note.warnings)
        ctx.note(f"Credit Note: {len(note.items)} EVD/KFC item(s), total {fmt(note.total)}")
        credit_calc = ResultTable(
            title="Credit Note EVD + KFC", columns=CALC_COLUMNS, rows=calc_rows(note)
        )
        credit_jv = ResultTable(
            title="Credit Note (JV)", columns=JV_COLUMNS, rows=jv_rows(note, cn_rules)
        )
        tables = [reconciliation, steps, terminals, invoices, sales_invoice]
        if note.items:
            tables += [credit_calc, credit_jv]

        rc_rules = {**DEFAULT_RECEIPT_RULES, **(rules.get("receipts") or {})}
        rcs = receipts(day, cash, afs_amount, pie, afs.batches, rc_rules)
        afs_receipt = rcs[1]
        afs_file_commission = -(afs.total("commission") + afs.total("vat"))
        if afs_file_commission != -afs_receipt.lines[1][2]:
            warnings.append(
                f"AFS commission: {afs_receipt.commission_note}, but the AFS file's Commission + "
                f"VAT is {fmt(afs_file_commission)}. Check the rate before posting."
            )
        ctx.note(
            "Receipts: "
            + "; ".join(f"{r.title} net {fmt(r.net)}" for r in rcs)
            + f" (AFS file Commission + VAT {fmt(afs_file_commission)})"
        )
        tables += [ResultTable(title=r.title, columns=RECEIPT_COLUMNS, rows=r.rows()) for r in rcs]

        ctx.add_output(
            f"causeway_reconciliation_{day:%Y%m%d}.xlsx",
            excel.write_workbook(
                {t.title: pl.DataFrame(t.rows, schema=t.columns, orient="row") for t in tables}
            ),
        )

        # The Zoho file again, same name, with a cleaned copy of its sheet added.
        zoho_columns = rules.get("zoho_columns") or ZOHO_COLUMNS
        formatted = format_zoho(zoho_sheets, zoho_columns)
        data, name = zoho_with_formatted_sheet(
            zoho_file.data, zoho_file.name, zoho_file.password, formatted
        )
        ctx.add_output(name, data)
        ctx.note(
            f"{name}: added sheet '{ZOHO_SHEET}' with {len(zoho_columns)} columns and an empty "
            f"row between dates ({formatted.height} rows); the original sheet is unchanged"
        )
        return RunResult(
            metrics=[
                Metric("Zoho total", fmt(zoho.total)),
                Metric("Cash + AFS + PIE", fmt(payments)),
                Metric("Marketing fund", fmt(fund), "bad" if fund < 0 else "good"),
            ],
            tables=tables,
            warnings=warnings,
        )


def _sales_date(value: object) -> date:
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except ValueError as exc:
        raise WorkflowInputError("Enter the sales date.") from exc


def _amount(value: object, label: str):
    try:
        result = money(value)
    except ArithmeticError as exc:
        raise WorkflowInputError(f"{label}: enter an amount, e.g. 100.500") from exc
    if result < 0:
        raise WorkflowInputError(f"{label} cannot be negative.")
    return result
