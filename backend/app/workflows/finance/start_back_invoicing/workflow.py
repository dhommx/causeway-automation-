"""02 Start Back Invoicing (Proposal 02). Planned: shown on the home screen, not runnable yet."""

from app.workflows.base import Workflow


class StartBackInvoicing(Workflow):
    key = "start-back-invoicing"
    name = "Start Back Invoicing"
    department = "finance"
    number = 2
    status = "planned"
    icon = "banknote"
    summary = "Compare each salesman's cash sales in Focus with the deposits recorded in IBL."
    current_time = "15 min / day"
    target_time = "3 min / day"
    frequency = "Daily, Sun-Thu"
