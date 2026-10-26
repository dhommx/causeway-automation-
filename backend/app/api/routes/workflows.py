from dataclasses import asdict

from fastapi import APIRouter, Depends

from app.api.deps import workflow_or_404
from app.api.schemas import DepartmentOut, WorkflowOut
from app.workflows.base import Workflow
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
