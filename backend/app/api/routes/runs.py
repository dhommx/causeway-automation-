import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_actor, workflow_or_404
from app.api.schemas import RunCreate, RunOut
from app.config import get_settings
from app.db import get_db
from app.models import Run
from app.services import runs as run_service

router = APIRouter(prefix="/runs", tags=["runs"])


def to_out(run: Run) -> RunOut:
    return RunOut(
        id=run.id,
        workflow_key=run.workflow_key,
        workflow_version=run.workflow_version,
        status=run.status,
        params=run.params,
        rule_version=run.rule_set.version if run.rule_set else None,
        result=run.result,
        error=run.error,
        trigger=run.trigger,
        actor=run.actor,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        files=run.files,
    )


@router.post("", response_model=RunOut, status_code=202)
def create_run(
    body: RunCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    actor: str = Depends(current_actor),
):
    wf = workflow_or_404(body.workflow_key)
    inputs = {slot: [f.model_dump() for f in items] for slot, items in body.inputs.items()}
    try:
        run = run_service.create(db, wf, inputs, body.params, actor)
    except run_service.RunRequestError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()

    passwords = {
        str(f.id): f.password for items in body.inputs.values() for f in items if f.password
    }
    sealed = run_service.seal_passwords(passwords)
    if get_settings().run_inline:
        background.add_task(run_service.execute, run.id, sealed)
    else:
        from app.jobs import run_workflow

        run_workflow.defer(run_id=str(run.id), sealed_passwords=sealed)
    return to_out(run_service.get(db, run.id))


@router.get("", response_model=list[RunOut])
def list_runs(workflow_key: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    return [to_out(r) for r in run_service.list_runs(db, workflow_key, min(limit, 500))]


@router.get("/{run_id}", response_model=RunOut)
def read_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = run_service.get(db, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    return to_out(run)
