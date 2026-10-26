import io
from datetime import datetime

import msoffcrypto.format.ooxml
import openpyxl
import pytest

from app.workflows.base import InputFile, RunContext, WorkflowInputError
from app.workflows.finance.causeway_sales.workflow import CausewaySalesReconciliation

AFS_PASSWORD = "4651"


def make_afs(day: str = "18-OCT-2026", password: str = AFS_PASSWORD) -> bytes:
    """Same layout as the AFS settlement report: 10 sales totalling 91.000 on one terminal."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "MerchantAUBTerminalWise"
    ws.append(["Terminal ID:03221330"])
    ws.append(
        [
            "Tran Date",
            None,
            "Batch",
            "RRN",
            "Card No",
            "Tran Type",
            "Auth Code",
            "Track  Id",
            "Tran Amt",
            "Commission",
            "VAT",
            "Net",
        ]
    )
    sales = [("8.500", "-0.170", "-0.017", "8.313")] * 7 + [
        ("9.500", "-0.190", "-0.019", "9.291"),
        ("11.000", "-0.220", "-0.022", "10.758"),
        ("11.000", "-0.220", "-0.022", "10.758"),
    ]
    for amt, com, vat, net in sales:
        ws.append(
            [
                day,
                None,
                "999",
                "629113075038",
                "440227******1751",
                "Purchase",
                "580740",
                "",
                f"{amt} BHD",
                com,
                vat,
                net,
            ]
        )
    ws.append([None, "Total", None, None, None, None, None, None, 91, -1.82, -0.182, 88.998])
    plain = io.BytesIO()
    wb.save(plain)
    locked = io.BytesIO()
    msoffcrypto.format.ooxml.OOXMLFile(io.BytesIO(plain.getvalue())).encrypt(password, locked)
    return locked.getvalue()


def make_zoho() -> bytes:
    """Two days of the Zoho export; each item line repeats the invoice Total."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Invoice"
    ws.append(
        ["Invoice Date", "Invoice Number", "Invoice Status", "Total", "Item Name", "Quantity"]
    )
    for item, qty in [("Preconfigured- Batelco BD 9.5 Starter Pack", 17), ("EVD - KFC 1", 230.5)]:
        ws.append([datetime(2026, 10, 18), "INV-001071", "Draft", 450.493, item, qty])
    ws.append([datetime(2026, 10, 19), "INV-001072", "Draft", 438.992, "eSIM 9.5(Kunooz)", 12])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def run(params=None, afs=None, password=AFS_PASSWORD):
    ctx = RunContext(
        files=[
            InputFile("afs", "afs.xlsx", afs or make_afs(), password),
            InputFile("zoho", "zoho.xlsx", make_zoho()),
        ],
        params={"sales_date": "2026-10-18", "cash": "100.500", "pie": "215.000", **(params or {})},
        rules={},
    )
    return ctx, CausewaySalesReconciliation().run(ctx)


def test_marketing_fund_matches_the_worked_example():
    ctx, result = run()
    assert [(m.label, m.value, m.tone) for m in result.metrics] == [
        ("Zoho total", "450.493", "neutral"),
        ("Cash + AFS + PIE", "406.500", "neutral"),
        ("Marketing fund", "43.993", "good"),
    ]
    assert result.warnings == []
    assert result.tables[2].rows == [["03221330", "91.000", "-1.820", "-0.182", "88.998"]]
    assert result.tables[3].rows == [["INV-001071", "Draft", "450.493"]]
    assert len(ctx.outputs) == 1 and ctx.outputs[0].name == "causeway_reconciliation_20261018.xlsx"


def test_wrong_afs_date_and_negative_fund_warn():
    _, result = run(params={"cash": "200"}, afs=make_afs(day="17-OCT-2026"))
    assert result.metrics[2].value == "-55.507" and result.metrics[2].tone == "bad"
    assert len(result.warnings) == 2


def test_date_missing_from_zoho():
    with pytest.raises(WorkflowInputError, match="No Zoho invoices for 02/11/2026"):
        run(params={"sales_date": "2026-11-02"})


def test_bad_amount():
    with pytest.raises(WorkflowInputError, match="Cash amount"):
        run(params={"cash": "abc"})


def test_wrong_password():
    from app.core.excel import SpreadsheetError

    with pytest.raises(SpreadsheetError, match="password"):
        run(password="1111")
