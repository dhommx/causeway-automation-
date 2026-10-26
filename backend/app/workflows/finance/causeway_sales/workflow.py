"""01 Causeway Sales Reconciliation (Proposal 01, process notes: neasi_organised.txt).

Processing rules are not written yet. Until they are, a run copies the input to the output so
the whole path (upload, preview, run, history, download) can be used and checked.
"""

from app.workflows.base import IMAGE_ACCEPT, FileSlot, RunContext, RunResult, Workflow
from app.workflows.common import passthrough


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
            key="source",
            label="Source files",
            help="Excel or CSV files for this run.",
            multiple=True,
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

    def run(self, ctx: RunContext) -> RunResult:
        return passthrough(ctx)
