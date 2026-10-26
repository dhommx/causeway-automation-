from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.schemas import AuditEventOut, HealthOut
from app.core.conditions import OPERATORS
from app.db import get_db
from app.models import AuditEvent
from app.workflows.registry import workflows

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("select 1"))
        ok = True
    except Exception:
        ok = False
    return HealthOut(status="ok" if ok else "degraded", database=ok, workflows=len(workflows()))


@router.get("/audit", response_model=list[AuditEventOut])
def list_audit(
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    stmt = select(AuditEvent)
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    return list(db.scalars(stmt.order_by(AuditEvent.id.desc()).limit(min(limit, 1000))))


@router.get("/conditions/operators", response_model=dict[str, str])
def condition_operators():
    """Operators the condition engine understands, for building condition editors."""
    return OPERATORS
