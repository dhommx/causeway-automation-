"""03 Cash Collection (Proposal 03). Planned: shown on the home screen, not runnable yet."""

from app.workflows.base import Workflow


class CashCollection(Workflow):
    key = "cash-collection"
    name = "Cash Collection"
    department = "finance"
    number = 3
    status = "planned"
    icon = "wallet"
    summary = "Calculate and record the daily Benefit QR and cash totals for each salesman."
    current_time = "1 hour / day"
    target_time = "10 min / day"
    frequency = "Daily, Sun-Thu"
