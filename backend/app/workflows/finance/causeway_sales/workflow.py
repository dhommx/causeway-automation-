"""01 Causeway Sales Reconciliation (Proposal 01, process notes: neasi_organised.txt).

Step 1 (reconcile): variance = Zoho total - (Cash + AFS for the sales date + PIE), where
AFS for the sales date = AFS file total - AFS for the next day + AFS from the previous day.
The AFS receipt still uses the full AFS file total.
The ERP posting steps (sales invoice, credit notes, receipts) are not written yet.
"""

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal

import polars as pl

from app.core import excel
from app.core.money import fmt, money
from app.workflows.base import (
    IMAGE_ACCEPT,
    FileCheck,
    FileSlot,
    InputFile,
    ManualField,
    Metric,
    Notice,
    OutputFile,
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
    AfsTransaction,
    format_zoho,
    read_afs,
    read_zoho_day,
    zoho_with_formatted_sheet,
)
from .receipts import COLUMNS as RECEIPT_COLUMNS
from .receipts import DEFAULT_RECEIPT_RULES, cash_erp_file, receipts
from .variance_note import DEFAULT_VARIANCE_RULES, erp_file, split_for
from .variance_note import TITLE as VARIANCE_TITLE
from .variance_note import table as variance_table


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
            checked=True,
            check_params=("sales_date",),
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
        ManualField(
            key="afs_previous_day",
            label="AFS amount from the previous day (BHD)",
            type="money",
            help="AFS transactions for this sales date that came in yesterday's report. Added to "
            "the variance; not in today's receipt.",
            required=False,
        ),
        ManualField(key="sales_date", label="Sales date", type="date"),
        ManualField(
            key="afs_next_day",
            label="AFS amount for the next day (BHD)",
            type="money",
            help="Filled in from AFS transactions dated after the sales date. Left out of the "
            "variance; still in today's AFS receipt.",
            required=False,
        ),
        ManualField(
            key="cash", label="Cash amount (BHD)", type="money", help="From the email report."
        ),
        ManualField(
            key="cash_deposit_date",
            label="Cash deposit date",
            type="date",
            help="The day the cash was deposited: the sales date or later. Shown on Receipt (Cash).",
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
        # Credit Note (JV Type) for the variance: Causeway credited, split between the Batelco
        # marketing fund and Business Promotion after the run.
        "variance_credit_note": DEFAULT_VARIANCE_RULES,
        # Cash and bank receipts: accounts and commission rates (procedure page 5).
        "receipts": DEFAULT_RECEIPT_RULES,
    }

    def run(self, ctx: RunContext) -> RunResult:
        day = _sales_date(ctx.params.get("sales_date"))
        cash = _amount(ctx.params.get("cash"), "Cash amount")
        deposit_day = _date(ctx.params.get("cash_deposit_date"), "Enter the cash deposit date.")
        if deposit_day < day:
            raise WorkflowInputError(
                f"The cash deposit date ({deposit_day:%d/%m/%Y}) is before the sales date "
                f"({day:%d/%m/%Y}). It must be the same day or later."
            )
        pie = _amount(ctx.params.get("pie"), "PIE amount")
        afs_file = ctx.files_for("afs")[0]
        zoho_file = ctx.files_for("zoho")[0]

        afs = read_afs(afs_file.sheets())
        if problems := afs.mismatches():
            raise WorkflowInputError(" ".join(["The AFS file does not add up.", *problems]))
        afs_amount = afs.total("tran_amt")
        ctx.note(f"{afs_file.name}: {afs.transactions} transactions, Total row {fmt(afs_amount)}")
        previous_day = _amount(
            ctx.params.get("afs_previous_day") or "0", "AFS amount from the previous day"
        )
        next_day = _amount(ctx.params.get("afs_next_day") or "0", "AFS amount for the next day")
        later = afs.after(day)
        found_next_day = _sum(later)
        afs_for_day = afs_amount - next_day + previous_day
        ctx.note(
            f"AFS for the sales date {fmt(afs_amount)} - {fmt(next_day)} (next day; the file has "
            f"{fmt(found_next_day)} in {len(later)} transaction(s) dated after {day:%d/%m/%Y}) "
            f"+ {fmt(previous_day)} (previous day) = {fmt(afs_for_day)}"
        )
        zoho_sheets = zoho_file.sheets()
        zoho = read_zoho_day(zoho_sheets, day)
        ctx.note(
            f"{zoho_file.name}: {zoho.lines} item lines dated {day:%d/%m/%Y}, "
            f"{len(zoho.invoices)} invoice(s), total {fmt(zoho.total)}"
        )

        payments = cash + afs_for_day + pie
        fund = zoho.total - payments
        ctx.note(f"Variance {fmt(zoho.total)} - {fmt(payments)} = {fmt(fund)}")

        warnings = []
        if earlier := [d for d in afs.dates if d < day]:
            shown = ", ".join(f"{d:%d/%m/%Y}" for d in earlier)
            warnings.append(
                f"The AFS file has transactions dated {shown}, before {day:%d/%m/%Y}. "
                "Check that the right day's report was uploaded."
            )
        if next_day != found_next_day:
            warnings.append(
                f"AFS amount for the next day was entered as {fmt(next_day)}, but the AFS file has "
                f"{fmt(found_next_day)} dated after {day:%d/%m/%Y}. The variance uses the entered "
                "amount; this was the user's choice."
            )
        if len({r.day for r in later}) > 1:
            warnings.append(
                "The AFS transactions after the sales date fall on more than one day: "
                f"{_days(later)}. Check them before posting."
            )
        if fund < 0:
            warnings.append(
                "Payments are more than the Zoho total. The variance cannot be negative, "
                "so check the amounts before posting."
            )

        reconciliation = ResultTable(
            title="Reconciliation",
            columns=["Value", "Source", "BHD"],
            rows=[
                ["Cash", "Entered", fmt(cash)],
                ["AFS (card machine)", "AFS file, Total row, Tran Amt", fmt(afs_amount)],
                [
                    "Less AFS for the next day",
                    f"Entered (the AFS file has {fmt(found_next_day)} dated after {day:%d/%m/%Y})",
                    fmt(-next_day),
                ],
                ["Add AFS from the previous day", "Entered", fmt(previous_day)],
                [
                    "AFS for the sales date",
                    "AFS - next day + previous day",
                    fmt(afs_for_day),
                ],
                ["PIE (MSwipe)", "Entered", fmt(pie)],
                ["Sum of payments", "Cash + AFS for the sales date + PIE", fmt(payments)],
                ["Zoho total", f"Zoho invoices dated {day:%d/%m/%Y}", fmt(zoho.total)],
                ["Variance", "Zoho total - Sum of payments", fmt(fund)],
            ],
        )
        steps = ResultTable(
            title="How it was worked out",
            columns=["Step", "Detail"],
            rows=[
                [
                    1,
                    f"Opened {afs_file.name} with its password and read the Total row: "
                    f"{afs.transactions} transactions totalling {fmt(afs_amount)}. The "
                    "transactions add up to the Total row.",
                ],
                [
                    2,
                    f"Kept the Zoho rows dated {day:%d/%m/%Y} ({zoho.lines} item lines) and took each "
                    f"invoice's Total once: {fmt(zoho.total)}.",
                ],
                [
                    3,
                    f"AFS for the sales date: {fmt(afs_amount)} - {fmt(next_day)} (next day) + "
                    f"{fmt(previous_day)} (previous day) = {fmt(afs_for_day)}. Receipt (AFS) "
                    f"still uses the full {fmt(afs_amount)}.",
                ],
                [
                    4,
                    f"Payments: {fmt(cash)} + {fmt(afs_for_day)} + {fmt(pie)} = {fmt(payments)}.",
                ],
                [
                    5,
                    f"Variance: {fmt(zoho.total)} - {fmt(payments)} = {fmt(fund)}. "
                    "Posted as the variance credit note, split between the Batelco marketing "
                    "fund and Business Promotion.",
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
        receipt_tables = [
            ResultTable(title=r.title, columns=RECEIPT_COLUMNS, rows=r.rows()) for r in rcs
        ]
        tables += receipt_tables
        # The variance credit note comes after the receipts (last tab).
        split = None
        if fund > 0:
            vn_rules = _variance_rules(rules)
            split = split_for(fund, vn_rules)
            amounts = {split.default_part: fund}
            tables.append(variance_table(day, fund, amounts, vn_rules, False))
            # The ERP upload file is rebuilt when the user confirms the split.
            ctx.outputs.append(erp_file(day, fund, amounts, vn_rules))
        # The cash may be deposited after the sales date; the Cash Receipt (first) shows that date.
        cash_table = receipt_tables[0]
        late = (deposit_day - day).days
        cash_table.note = f"Cash deposit date: {deposit_day:%d/%m/%Y}" + (
            f", {late} day{'s' if late > 1 else ''} after the sales date ({day:%d/%m/%Y})."
            if late
            else " (same day as the sales date)."
        )
        cash_table.note_tone = "warn" if late else "neutral"
        # ERP upload file for the cash deposit; no file when there was no cash.
        if cash > 0:
            cash_file = cash_erp_file(day, deposit_day, cash, rc_rules)
            ctx.outputs.append(cash_file)
            cash_table.file = cash_file.name
        ctx.note(cash_table.note)

        ctx.add_output(
            _workbook_name(day),
            _workbook([(t.title, t.columns, t.rows) for t in tables]),
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
                Metric("Variance", fmt(fund), "bad" if fund < 0 else "good"),
            ],
            tables=tables,
            warnings=warnings,
            split=split,
        )

    def apply_split(self, result, amounts, params, rules) -> list[OutputFile]:
        """Rewrite the variance credit note with the user's split and rebuild the workbook."""
        day = _sales_date(params.get("sales_date"))
        split = result["split"]
        variance = money(split["total"])
        vn_rules = _variance_rules(rules)
        new = variance_table(day, variance, amounts, vn_rules, True)
        for i, t in enumerate(result["tables"]):
            if t["title"] == VARIANCE_TITLE:
                result["tables"][i] = asdict(new)
        split["amounts"] = {k: fmt(v) for k, v in amounts.items()}
        split["confirmed"] = True
        tables = [(t["title"], t["columns"], t["rows"]) for t in result["tables"]]
        return [
            OutputFile(_workbook_name(day), _workbook(tables)),
            erp_file(day, variance, amounts, vn_rules),
        ]

    def check_file(self, file: InputFile, params: dict) -> FileCheck:
        """AFS: every terminal's transactions must add up to the Total row the file states.
        Once the sales date is in, the transactions dated after it fill 'AFS amount for the next
        day' and are listed in a notice."""
        afs = read_afs(file.sheets())
        if problems := afs.mismatches():
            return FileCheck(ok=False, message=" ".join(problems))
        check = FileCheck(
            ok=True,
            message=f"Total matches: {afs.transactions} transactions = "
            f"{fmt(afs.total('tran_amt'))} BHD",
        )
        try:
            day = _sales_date(params.get("sales_date"))
        except WorkflowInputError:
            return check  # no date yet: nothing to split
        later = afs.after(day)
        check.fills = {"afs_next_day": fmt(_sum(later))}
        if later:
            batches = sorted({r.batch for r in later if r.batch})
            message = (
                f"{len(later)} AFS transaction(s) are dated after {day:%d/%m/%Y}"
                + (f" (batch {', '.join(batches)})" if batches else "")
                + f", so they are for the next day. Their total, {fmt(_sum(later))} BHD, is "
                "filled in 'AFS amount for the next day' and left out of the variance. "
                "Receipt (AFS) still uses the full AFS total."
            )
            if len({r.day for r in later}) > 1:
                message += f" They fall on more than one day: {_days(later)}."
            check.notice = Notice(
                title="AFS transactions for the next day",
                message=message,
                table=ResultTable(
                    title="Next-day transactions",
                    columns=["Date", "Batch", "Terminal", "Tran Amt"],
                    rows=[
                        [f"{r.day:%d/%m/%Y}", r.batch, r.terminal, fmt(r.tran_amt)] for r in later
                    ],
                ),
            )
        return check


def _variance_rules(rules: dict) -> dict:
    # Rules saved before the variance credit note existed fall back to its defaults.
    return {**DEFAULT_VARIANCE_RULES, **(rules.get("variance_credit_note") or {})}


def _workbook_name(day: date) -> str:
    return f"causeway_reconciliation_{day:%Y%m%d}.xlsx"


def _workbook(tables: list[tuple[str, list[str], list[list]]]) -> bytes:
    return excel.write_workbook(
        {title: pl.DataFrame(rows, schema=columns, orient="row") for title, columns, rows in tables}
    )


def _sum(rows: list[AfsTransaction]) -> Decimal:
    return money(sum((r.tran_amt for r in rows), Decimal(0)))


def _days(rows: list[AfsTransaction]) -> str:
    return ", ".join(f"{d:%d/%m/%Y}" for d in sorted({r.day for r in rows}))


def _sales_date(value: object) -> date:
    return _date(value, "Enter the sales date.")


def _date(value: object, missing: str) -> date:
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except ValueError as exc:
        raise WorkflowInputError(missing) from exc


def _amount(value: object, label: str):
    try:
        result = money(value)
    except ArithmeticError as exc:
        raise WorkflowInputError(f"{label}: enter an amount, e.g. 100.500") from exc
    if result < 0:
        raise WorkflowInputError(f"{label} cannot be negative.")
    return result
