from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_actor, workflow_or_404
from app.api.schemas import RulesOut, RulesSave
from app.db import get_db
from app.services import rules as rule_service
from app.workflows.base import Workflow

router = APIRouter(prefix="/workflows/{key}/rules", tags=["rules"])


@router.get("", response_model=RulesOut)
def read_rules(wf: Workflow = Depends(workflow_or_404), db: Session = Depends(get_db)):
    current = rule_service.current(db, wf)
    db.commit()
    return RulesOut(current=current, versions=rule_service.versions(db, wf.key))


@router.put("", response_model=RulesOut)
def save_rules(
    body: RulesSave,
    wf: Workflow = Depends(workflow_or_404),
    db: Session = Depends(get_db),
    actor: str = Depends(current_actor),
):
    current = rule_service.save(db, wf, body.values, body.note, actor)
    db.commit()
    return RulesOut(current=current, versions=rule_service.versions(db, wf.key))
