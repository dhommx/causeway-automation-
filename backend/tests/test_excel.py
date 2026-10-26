import io

import msoffcrypto
import openpyxl
import polars as pl
import pytest

from app.core import excel


def make_xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Invoices"
    ws.append(["Invoice Number", "Total"])
    ws.append([None, None])  # spacer row, as in the Zoho export
    ws.append(["INV-1", 376.493])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def test_read_drops_empty_rows():
    sheets = excel.read_sheets(make_xlsx(), "zoho.xlsx")
    assert list(sheets) == ["Invoices"]
    assert sheets["Invoices"].height == 1


def test_write_then_read_round_trip():
    data = excel.write_workbook({"Out": pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})})
    assert excel.read_sheets(data, "out.xlsx")["Out"].to_dict(as_series=False) == {
        "a": [1, 2],
        "b": ["x", "y"],
    }


def test_edit_keeps_original_sheet():
    with excel.edit_workbook(make_xlsx(), "zoho.xlsx") as wb:
        excel.add_sheet(wb, "Cleaned", pl.DataFrame({"Total": [376.493]}))
    sheets = excel.read_sheets(wb.saved, "zoho.xlsx")
    assert list(sheets) == ["Invoices", "Cleaned"]


def test_csv_and_unsupported():
    assert excel.read_sheets(b"a,b\n1,2\n", "x.csv")["x"].height == 1
    with pytest.raises(excel.SpreadsheetError):
        excel.read_sheets(b"hello", "notes.txt")


def test_password_protected():
    plain = make_xlsx()
    office = msoffcrypto.format.ooxml.OOXMLFile(io.BytesIO(plain))
    locked = io.BytesIO()
    office.encrypt("secret", locked)
    data = locked.getvalue()
    with pytest.raises(excel.SpreadsheetError, match="password"):
        excel.read_sheets(data, "afs.xlsx")
    assert excel.read_sheets(data, "afs.xlsx", "secret")["Invoices"].height == 1
