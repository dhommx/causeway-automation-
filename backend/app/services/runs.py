"""Creating and executing runs. The API creates a run; the worker (or the API, when
AP_RUN_INLINE is true) executes it with execute()."""

import logging
import traceback
import uuid
from dataclasses import asdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.connectors.builtin import DownloadDestination, UploadSource
from app.core import audit, secrets
from app.core.excel import SpreadsheetError, suffix_of
from app.db import SessionLocal
from app.models import Run, RunFile
from app.services import files as file_service
from app.services import rules as rule_service
from app.workflows.base import RunContext, Workflow, WorkflowInputError
from app.workflows.registry import get_workflow

log = logging.getLogger(__name__)


class RunRequestError(ValueError):
    pass


def create(
    db: Session,
    workflow: Workflow,
    inputs: dict[str, list[dict]],
    params: dict,
    actor: str,
    trigger: str = "manual",
) -> Run:
    """Check the request against the workflow's inputs and save a queued run."""
    if workflow.status != "live":
        raise RunRequestError(f"{workflow.name} is not available yet.")

    slots = {s.key: s for s in workflow.file_slots}
    for key in inputs:
        if key not in slots:
            raise RunRequestError(f"Unknown input {key!r}.")
    for slot in workflow.file_slots:
        given = inputs.get(slot.key, [])
        if slot.required and not given:
            raise RunRequestError(f"{slot.label} is required.")
        if not slot.multiple and len(given) > 1:
            raise RunRequestError(f"{slot.label} takes one file.")
    for f in workflow.manual_fields:
        if f.required and params.get(f.key) in (None, ""):
            raise RunRequestError(f"{f.label} is required.")

    rule_set = rule_service.current(db, workflow)
    run = Run(
        workflow_key=workflow.key,
        workflow_version=workflow.version,
        params=params,
        rule_set_id=rule_set.id,
        trigger=trigger,
        actor=actor,
        status="queued",
    )
    for slot_key, items in inputs.items():
        for item in items:
            file_id = uuid.UUID(str(item["id"]))
            stored = file_service.get(db, file_id)
            if stored is None:
                raise RunRequestError(f"File {file_id} was not found. Upload it again.")
            if suffix_of(stored.original_name) not in slots[slot_key].accept:
                raise RunRequestError(
                    f"{stored.original_name} can't be used as {slots[slot_key].label}. "
                    f"Allowed: {' '.join(slots[slot_key].accept)}"
                )
            run.files.append(RunFile(file_id=file_id, role="input", slot=slot_key))
    db.add(run)
    db.flush()
    audit.record(
        db,
        "run.created",
        "run",
        run.id,
        {"workflow": workflow.key, "rule_version": rule_set.version, "params": params},
        actor,
    )
    return run


def seal_passwords(passwords: dict[str, str]) -> str | None:
    """File passwords travel to the worker encrypted, so the job queue never holds them in clear."""
    return secrets.encrypt(passwords).decode() if passwords else None


def execute(run_id: uuid.UUID, sealed_passwords: str | None = None) -> None:
    """Run a queued run to the end. Never raises: failures are stored on the run."""
    passwords = secrets.decrypt(sealed_passwords.encode()) if sealed_passwords else {}
    with SessionLocal() as db:
        run = db.get(Run, run_id, options=[selectinload(Run.files)])
        if run is None or run.status not in ("queued", "running"):
            return
        workflow = get_workflow(run.workflow_key)
        run.status, run.started_at = "running", datetime.now(UTC)
        db.commit()

        try:
            if workflow is None:
                raise WorkflowInputError(f"Workflow {run.workflow_key} no longer exists.")
            source = UploadSource(db=db)
            files = []
            for rf in run.files:
                if rf.role == "input":
                    request = {
                        "files": [{"id": rf.file_id, "password": passwords.get(str(rf.file_id))}]
                    }
                    files.extend(source.fetch(rf.slot, request))
            ctx = RunContext(
                files=files, params=run.params, rules=run.rule_set.values if run.rule_set else {}
            )
            result = workflow.run(ctx)

            for out in ctx.outputs:
                stored = file_service.save(
                    db, out.name, out.data, out.content_type, "output", audit.SYSTEM
                )
                run.files.append(RunFile(file_id=stored.id, role="output", slot=out.slot))
            DownloadDestination().send(str(run.id), ctx.outputs)

            run.result = {**asdict(result), "log": ctx.log}
            run.status = "succeeded"
        except (WorkflowInputError, SpreadsheetError) as exc:
            db.rollback()
            run = db.get(Run, run_id)
            run.status, run.error = "failed", str(exc)
        except Exception:
            log.exception("Run %s failed", run_id)
            db.rollback()
            run = db.get(Run, run_id)
            run.status = "failed"
            run.error = "Unexpected error while processing. Details are in the server log."
            run.result = {"trace": traceback.format_exc(limit=5)}

        run.finished_at = datetime.now(UTC)
        audit.record(db, f"run.{run.status}", "run", run.id, {"error": run.error}, audit.SYSTEM)
        db.commit()


def list_runs(db: Session, workflow_key: str | None, limit: int) -> list[Run]:
    stmt = select(Run).options(
        selectinload(Run.files).selectinload(RunFile.file), selectinload(Run.rule_set)
    )
    if workflow_key:
        stmt = stmt.where(Run.workflow_key == workflow_key)
    return list(db.scalars(stmt.order_by(Run.created_at.desc()).limit(limit)))


def get(db: Session, run_id: uuid.UUID) -> Run | None:
    return db.get(
        Run,
        run_id,
        options=[selectinload(Run.files).selectinload(RunFile.file), selectinload(Run.rule_set)],
    )
