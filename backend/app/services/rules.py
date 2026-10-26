from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import audit
from app.models import RuleSet
from app.workflows.base import Workflow


def versions(db: Session, workflow_key: str) -> list[RuleSet]:
    stmt = (
        select(RuleSet).where(RuleSet.workflow_key == workflow_key).order_by(RuleSet.version.desc())
    )
    return list(db.scalars(stmt))


def current(db: Session, workflow: Workflow) -> RuleSet:
    """The latest rule set. Version 1 is made from the workflow's defaults the first time."""
    stmt = (
        select(RuleSet)
        .where(RuleSet.workflow_key == workflow.key)
        .order_by(RuleSet.version.desc())
        .limit(1)
    )
    latest = db.scalars(stmt).first()
    if latest is None:
        latest = _add(db, workflow.key, dict(workflow.default_rules), "Defaults", audit.SYSTEM)
    return latest


def save(db: Session, workflow: Workflow, values: dict, note: str, actor: str) -> RuleSet:
    """Rules are never edited in place: every save is a new version, so old runs stay explainable."""
    current(db, workflow)
    return _add(db, workflow.key, values, note, actor)


def _add(db: Session, key: str, values: dict, note: str, actor: str) -> RuleSet:
    next_version = (
        db.scalar(
            select(func.coalesce(func.max(RuleSet.version), 0)).where(RuleSet.workflow_key == key)
        )
        + 1
    )
    row = RuleSet(workflow_key=key, version=next_version, values=values, note=note, actor=actor)
    db.add(row)
    db.flush()
    audit.record(db, "rules.saved", "workflow", key, {"version": next_version, "note": note}, actor)
    return row
