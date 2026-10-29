"""Request and response shapes of the public API (/api/v1). The frontend's types are generated
from these through OpenAPI, so a change here is followed by `pnpm gen:api` in frontend/."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class FileSlotOut(BaseModel):
    key: str
    label: str
    help: str
    required: bool
    multiple: bool
    accept: list[str]
    password_protected: bool
    kind: Literal["data", "reference"]
    checked: bool
    check_params: list[str]


class ManualFieldOut(BaseModel):
    key: str
    label: str
    type: str
    help: str
    required: bool
    options: list[str]


class WorkflowOut(BaseModel):
    key: str
    name: str
    department: str
    number: int
    summary: str
    status: Literal["live", "planned"]
    version: str
    icon: str
    current_time: str
    target_time: str
    frequency: str
    file_slots: list[FileSlotOut]
    manual_fields: list[ManualFieldOut]


class DepartmentOut(BaseModel):
    key: str
    name: str
    summary: str
    workflows: list[WorkflowOut]


class StoredFileOut(BaseModel):
    id: uuid.UUID
    original_name: str
    content_type: str
    size_bytes: int
    sha256: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PreviewOut(BaseModel):
    file_id: uuid.UUID
    name: str
    sheets: list[str]
    sheet: str
    columns: list[str]
    rows: list[list[Any]]
    total_rows: int


class FileCheckIn(BaseModel):
    slot: str
    id: uuid.UUID
    password: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)  # the slot's check_params values


class NoticeOut(BaseModel):
    title: str
    message: str
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)


class FileCheckOut(BaseModel):
    ok: bool
    message: str
    fills: dict[str, str] = Field(default_factory=dict)
    notice: NoticeOut | None = None


class RunInputFile(BaseModel):
    id: uuid.UUID
    password: str | None = None


class RunCreate(BaseModel):
    workflow_key: str
    inputs: dict[str, list[RunInputFile]] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)


class RunSplit(BaseModel):
    amounts: dict[str, str]


class RunFileOut(BaseModel):
    role: str
    slot: str
    file: StoredFileOut

    model_config = {"from_attributes": True}


class RunOut(BaseModel):
    id: uuid.UUID
    workflow_key: str
    workflow_version: str
    status: Literal["queued", "running", "succeeded", "failed"]
    params: dict[str, Any]
    rule_version: int | None
    result: dict[str, Any] | None
    error: str | None
    trigger: str
    actor: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    folder: str | None
    files: list[RunFileOut]


class RuleSetOut(BaseModel):
    id: int
    workflow_key: str
    version: int
    values: dict[str, Any]
    note: str
    actor: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RulesOut(BaseModel):
    current: RuleSetOut
    versions: list[RuleSetOut]


class RulesSave(BaseModel):
    values: dict[str, Any]
    note: str = ""


class AuditEventOut(BaseModel):
    id: int
    at: datetime
    actor: str
    action: str
    entity_type: str
    entity_id: str
    details: dict[str, Any]

    model_config = {"from_attributes": True}


class SettingsOut(BaseModel):
    data_folder: str
    default_data_folder: str
    upload_keep_days: int


class SettingsSave(BaseModel):
    data_folder: str | None = None  # None goes back to the default


class HealthOut(BaseModel):
    status: str
    database: bool
    workflows: int
