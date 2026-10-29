import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core import audit, excel, storage
from app.models import StoredFile
from app.services import settings


class FileGoneError(LookupError):
    """The file's record exists but the file is no longer on disk (e.g. an old unused upload)."""


def save(
    db: Session,
    name: str,
    data: bytes,
    content_type: str,
    source: str,
    actor: str,
    folder: Path,
) -> StoredFile:
    """Write the file into folder (never over another file) and record it."""
    path, sha = storage.write_new(folder, name, data)
    row = StoredFile(
        sha256=sha,
        path=str(path),
        original_name=name,
        content_type=content_type or "application/octet-stream",
        size_bytes=len(data),
        source=source,
        actor=actor,
    )
    db.add(row)
    db.flush()
    audit.record(
        db,
        f"file.{source}",
        "file",
        row.id,
        {"name": name, "sha256": sha, "path": str(path)},
        actor,
    )
    return row


def save_upload(db: Session, name: str, data: bytes, content_type: str, actor: str) -> StoredFile:
    """An upload waits in <data folder>/_uploads/<date>/ until a run copies it into its folder."""
    folder = settings.data_folder(db) / storage.UPLOADS / storage.local_now().strftime("%Y-%m-%d")
    return save(db, name, data, content_type, "upload", actor, folder)


def get(db: Session, file_id: uuid.UUID) -> StoredFile | None:
    return db.get(StoredFile, file_id)


def read(row: StoredFile) -> bytes:
    try:
        return storage.read(row.path)
    except FileNotFoundError as exc:
        raise FileGoneError(f"{row.original_name} is no longer kept. Upload it again.") from exc


def preview(row: StoredFile, sheet: str | None, password: str | None, limit: int) -> dict:
    """First `limit` rows of one sheet, plus the sheet list and full row count."""
    if excel.is_image(row.original_name):
        raise excel.SpreadsheetError("Images have no table preview; open the image itself.")
    sheets = excel.read_sheets(read(row), row.original_name, password)
    names = list(sheets)
    chosen = sheet if sheet in sheets else names[0]
    df = sheets[chosen]
    head = df.head(limit)
    return {
        "file_id": str(row.id),
        "name": row.original_name,
        "sheets": names,
        "sheet": chosen,
        "columns": head.columns,
        "rows": [[_plain(v) for v in r] for r in head.iter_rows()],
        "total_rows": df.height,
    }


def _plain(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
