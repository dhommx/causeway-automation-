"""Creating and executing runs. The API creates a run; the worker (or the API, when
AP_RUN_INLINE is true) executes it with execute()."""

import copy
import logging
import traceback
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.connectors.builtin import DownloadDestination, UploadSource
from app.core import audit, secrets, storage
from app.core.excel import SpreadsheetError, suffix_of
from app.core.money import fmt, money
from app.db import SessionLocal
from app.models import Run, RunFile
from app.services import files as file_service
from app.services import rules as rule_service
from app.services import settings
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
) -> tuple[Run, str | None]:
    """Check the request, give the run its folder, copy the input files into input/ and save the
    entries the user typed as input/entries.json. Returns the queued run and its sealed file
    passwords (for the worker)."""
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
    chosen = []
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
            try:
                data = file_service.read(stored)
            except file_service.FileGoneError as exc:
                raise RunRequestError(str(exc)) from exc
            chosen.append((slot_key, stored, data, item.get("password")))

    folder = storage.new_run_folder(settings.data_folder(db), workflow.name, storage.local_now())
    run.folder = str(folder)
    passwords = {}
    for slot_key, stored, data, password in chosen:
        copy = file_service.save(
            db,
            stored.original_name,
            data,
            stored.content_type,
            "run-input",
            actor,
            folder / "input",
        )
        run.files.append(RunFile(file_id=copy.id, role="input", slot=slot_key))
        if password:
            passwords[str(copy.id)] = password
    storage.write_json(folder / "input" / "entries.json", params)
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
    write_summary(db, run.id)
    return run, seal_passwords(passwords)


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

            out_folder = Path(run.folder) / "output" if run.folder else _legacy_folder(db, run)
            for out in ctx.outputs:
                stored = file_service.save(
                    db, out.name, out.data, out.content_type, "output", audit.SYSTEM, out_folder
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
        try:
            write_summary(db, run_id)
        except OSError:
            log.exception("Could not write run.json for run %s", run_id)


def split(db: Session, run_id: uuid.UUID, amounts: dict[str, str], actor: str) -> Run:
    """Apply the user's split to a finished run: check that the parts add up to the total, let
    the workflow rewrite its tables, and save the rebuilt outputs as new files. The files they
    replace stay on disk and stay linked to the run as 'replaced'."""
    run = get(db, run_id)
    if run is None:
        raise RunRequestError("Run not found.")
    split_info = (run.result or {}).get("split")
    workflow = get_workflow(run.workflow_key)
    if run.status != "succeeded" or not split_info or workflow is None:
        raise RunRequestError("This run has nothing to split.")

    keys = {p["key"]: p["label"] for p in split_info["parts"]}
    if set(amounts) - set(keys):
        raise RunRequestError(f"Unknown part: {', '.join(sorted(set(amounts) - set(keys)))}.")
    parsed = {}
    for key, label in keys.items():
        try:
            parsed[key] = money(amounts.get(key) or "0")
        except ArithmeticError as exc:
            raise RunRequestError(f"{label}: enter an amount, e.g. 10.500") from exc
        if parsed[key] < 0:
            raise RunRequestError(f"{label} cannot be negative.")
    total = money(split_info["total"])
    given = sum(parsed.values(), money(0))
    if given != total:
        raise RunRequestError(
            f"The amounts add up to {fmt(given)}, but they must add up to {fmt(total)} exactly."
        )

    result = copy.deepcopy(run.result)
    rules = run.rule_set.values if run.rule_set else {}
    outputs = workflow.apply_split(result, parsed, run.params, {**workflow.default_rules, **rules})
    out_folder = Path(run.folder) / "output"
    names = {out.name for out in outputs}
    for rf in run.files:
        if rf.role == "output" and rf.file.original_name in names:
            rf.role = "replaced"
    for out in outputs:
        stored = file_service.save(
            db, out.name, out.data, out.content_type, "output", actor, out_folder
        )
        run.files.append(RunFile(file_id=stored.id, role="output", slot=out.slot))
    run.result = result
    audit.record(
        db, "run.split", "run", run.id, {"amounts": {k: fmt(v) for k, v in parsed.items()}}, actor
    )
    db.flush()
    return run


def _legacy_folder(db: Session, run: Run) -> Path:
    """A run queued before runs had folders gets one when it executes."""
    folder = storage.new_run_folder(settings.data_folder(db), run.workflow_key, storage.local_now())
    run.folder = str(folder)
    return folder / "output"


def write_summary(db: Session, run_id: uuid.UUID) -> None:
    """Write run.json in the run's folder: everything an auditor needs without the portal."""
    run = get(db, run_id)
    if run is None or not run.folder:
        return
    workflow = get_workflow(run.workflow_key)
    folder = Path(run.folder)

    def file_entry(rf: RunFile) -> dict:
        path = Path(rf.file.path)
        return {
            "slot": rf.slot,
            "name": rf.file.original_name,
            "saved_as": str(path.relative_to(folder)) if path.is_relative_to(folder) else str(path),
            "sha256": rf.file.sha256,
            "size_bytes": rf.file.size_bytes,
        }

    result = run.result or {}
    storage.write_json(
        folder / "run.json",
        {
            "run_id": run.id,
            "automation": run.workflow_key,
            "automation_name": workflow.name if workflow else run.workflow_key,
            "automation_version": run.workflow_version,
            "status": run.status,
            "started_by": run.actor,
            "trigger": run.trigger,
            "created_at": run.created_at,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "rules_version": run.rule_set.version if run.rule_set else None,
            "rules": run.rule_set.values if run.rule_set else {},
            "entries": run.params,
            "inputs": [file_entry(rf) for rf in run.files if rf.role == "input"],
            "outputs": [file_entry(rf) for rf in run.files if rf.role == "output"],
            "metrics": result.get("metrics", []),
            "warnings": result.get("warnings", []),
            "log": result.get("log", []),
            "error": run.error,
        },
    )


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
