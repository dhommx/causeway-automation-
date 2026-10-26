from fastapi import HTTPException

from app.core import audit
from app.workflows.base import Workflow
from app.workflows.registry import get_workflow


def current_actor() -> str:
    """Who is acting. Fixed until login is added; then this reads the session or API token."""
    return audit.ANONYMOUS


def workflow_or_404(key: str) -> Workflow:
    wf = get_workflow(key)
    if wf is None:
        raise HTTPException(404, f"No workflow named {key!r}")
    return wf
