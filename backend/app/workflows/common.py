"""Steps shared by workflows."""

from datetime import datetime
from pathlib import Path

from app.core import excel
from app.workflows.base import Metric, ResultTable, RunContext, RunResult


def passthrough(ctx: RunContext, preview_rows: int = 50) -> RunResult:
    """Read every uploaded file and write its sheets back out unchanged as one .xlsx.

    Used by a workflow before its own processing is written: it proves upload, reading,
    output, history and download work end to end, and changes no data.
    """
    sheets = {}
    tables = []
    total_rows = 0
    data_files = [f for f in ctx.files if not f.is_image]
    images = len(ctx.files) - len(data_files)
    if images:
        ctx.note(f"Kept {images} image(s) with the run for reference; images are not processed.")
    for f in data_files:
        for sheet, df in f.sheets().items():
            label = sheet if len(data_files) == 1 else f"{Path(f.name).stem[:20]} - {sheet}"
            label = label[:31]
            sheets[label] = df
            total_rows += df.height
            head = df.head(preview_rows)
            tables.append(
                ResultTable(
                    title=f"{f.name} / {sheet}",
                    columns=head.columns,
                    rows=[[_plain(v) for v in row] for row in head.iter_rows()],
                )
            )
            ctx.note(f"Read {df.height} rows x {df.width} columns from {f.name} / {sheet}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ctx.add_output(f"output_{stamp}.xlsx", excel.write_workbook(sheets))
    return RunResult(
        metrics=[
            Metric("Files", str(len(data_files))),
            Metric("Sheets", str(len(sheets))),
            Metric("Rows", f"{total_rows:,}"),
        ],
        tables=tables,
        warnings=[
            "No processing rules are set for this automation yet. The output is a copy of the input."
        ],
    )


def _plain(value: object) -> object:
    """JSON-safe cell value."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
