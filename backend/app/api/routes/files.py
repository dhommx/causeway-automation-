import mimetypes
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import current_actor
from app.api.schemas import PreviewOut, StoredFileOut
from app.config import get_settings
from app.core.excel import IMAGE_SUFFIXES, READABLE_SUFFIXES, SpreadsheetError, suffix_of
from app.db import get_db
from app.services import files as file_service

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", response_model=list[StoredFileOut], status_code=201)
def upload_files(
    files: list[UploadFile],
    db: Session = Depends(get_db),
    actor: str = Depends(current_actor),
):
    limit = get_settings().max_upload_mb * 1024 * 1024
    saved = []
    for upload in files:
        name = upload.filename or "file"
        if suffix_of(name) not in READABLE_SUFFIXES | IMAGE_SUFFIXES:
            raise HTTPException(422, f"{name}: only Excel, CSV or image files are accepted.")
        data = upload.file.read()
        if len(data) > limit:
            raise HTTPException(413, f"{name} is larger than {get_settings().max_upload_mb} MB.")
        content_type = upload.content_type or mimetypes.guess_type(name)[0] or ""
        saved.append(file_service.save(db, name, data, content_type, "upload", actor))
    db.commit()
    return saved


@router.get("/{file_id}", response_model=StoredFileOut)
def read_file(file_id: uuid.UUID, db: Session = Depends(get_db)):
    row = file_service.get(db, file_id)
    if row is None:
        raise HTTPException(404, "File not found")
    return row


@router.get("/{file_id}/preview", response_model=PreviewOut)
def preview_file(
    file_id: uuid.UUID,
    sheet: str | None = None,
    password: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
):
    row = file_service.get(db, file_id)
    if row is None:
        raise HTTPException(404, "File not found")
    try:
        return file_service.preview(row, sheet, password, get_settings().preview_row_limit)
    except SpreadsheetError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/{file_id}/download")
def download_file(file_id: uuid.UUID, inline: bool = False, db: Session = Depends(get_db)):
    """The file itself. inline=true lets the browser show it (used for images) instead of saving it."""
    row = file_service.get(db, file_id)
    if row is None:
        raise HTTPException(404, "File not found")
    return Response(
        file_service.read(row),
        media_type=row.content_type,
        headers={
            "Content-Disposition": f'{"inline" if inline else "attachment"}; filename="{row.original_name}"'
        },
    )
