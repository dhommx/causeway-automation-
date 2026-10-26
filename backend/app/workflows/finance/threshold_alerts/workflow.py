"""04 Threshold Alert System (Proposal 04). Planned: shown on the home screen, not runnable yet."""

from app.workflows.base import Workflow


class ThresholdAlerts(Workflow):
    key = "threshold-alerts"
    name = "Threshold Alert System"
    department = "finance"
    number = 4
    status = "planned"
    icon = "bell"
    summary = "Save thresholds and conditions once, apply them to any Excel file in one click."
    current_time = "~10 min / file"
    target_time = "2-3 min / file"
    frequency = "Every file"
