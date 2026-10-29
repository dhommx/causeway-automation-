from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import workflow_or_404
from app.api.schemas import DepartmentOut, FileCheckIn, FileCheckOut, NoticeOut, WorkflowOut
from app.core.excel import SpreadsheetError
from app.db import get_db
from app.services import files as file_service
from app.workflows.base import InputFile, Workflow, WorkflowInputError
from app.workflows.registry import DEPARTMENTS, workflows

router = APIRouter(tags=["workflows"])


def to_out(wf: Workflow) -> WorkflowOut:
    return WorkflowOut(
        key=wf.key,
        name=wf.name,
        department=wf.department,
        number=wf.number,
        summary=wf.summary,
        status=wf.status,
        version=wf.version,
        icon=wf.icon,
        current_time=wf.current_time,
        target_time=wf.target_time,
        frequency=wf.frequency,
        file_slots=[asdict(s) for s in wf.file_slots],
        manual_fields=[asdict(f) for f in wf.manual_fields],
    )


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments():
    return [
        DepartmentOut(
            key=key,
            name=d["name"],
            summary=d["summary"],
            workflows=[to_out(w) for w in workflows().values() if w.department == key],
        )
        for key, d in DEPARTMENTS.items()
    ]


@router.get("/workflows", response_model=list[WorkflowOut])
def list_workflows():
    return [to_out(w) for w in workflows().values()]


@router.get("/workflows/{key}", response_model=WorkflowOut)
def read_workflow(wf: Workflow = Depends(workflow_or_404)):
    return to_out(wf)


@router.post("/workflows/{key}/check-file", response_model=FileCheckOut)
def check_file(
    body: FileCheckIn, wf: Workflow = Depends(workflow_or_404), db: Session = Depends(get_db)
):
    """Run the workflow's check on one uploaded file before Run (e.g. the AFS totals add up).
    A file that can't be read or checked comes back as ok=false with the reason."""
    slot = next((s for s in wf.file_slots if s.key == body.slot and s.checked), None)
    if slot is None:
        raise HTTPException(404, f"{wf.name} has no check for {body.slot!r}.")
    row = file_service.get(db, body.id)
    if row is None:
        raise HTTPException(404, "File not found")
    try:
        data = file_service.read(row)
    except file_service.FileGoneError as exc:
        raise HTTPException(410, str(exc)) from exc
    params = {k: v for k, v in body.params.items() if k in slot.check_params}
    try:
        result = wf.check_file(InputFile(slot.key, row.original_name, data, body.password), params)
    except (WorkflowInputError, SpreadsheetError) as exc:
        return FileCheckOut(ok=False, message=str(exc))
    notice = None
    if result.notice:
        table = result.notice.table
        notice = NoticeOut(
            title=result.notice.title,
            message=result.notice.message,
            columns=table.columns if table else [],
            rows=table.rows if table else [],
        )
    return FileCheckOut(ok=result.ok, message=result.message, fills=result.fills, notice=notice)
