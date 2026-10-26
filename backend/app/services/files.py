import uuid

from sqlalchemy.orm import Session

from app.core import audit, excel
from app.core.storage import get_storage
from app.models import StoredFile


def save(
    db: Session,
    name: str,
    data: bytes,
    content_type: str,
    source: str = "upload",
    actor: str = audit.ANONYMOUS,
) -> StoredFile:
    sha = get_storage().put(data)
    row = StoredFile(
        sha256=sha,
        original_name=name,
        content_type=content_type or "application/octet-stream",
        size_bytes=len(data),
        source=source,
        actor=actor,
    )
    db.add(row)
    db.flush()
    audit.record(db, f"file.{source}", "file", row.id, {"name": name, "sha256": sha}, actor)
    return row


def get(db: Session, file_id: uuid.UUID) -> StoredFile | None:
    return db.get(StoredFile, file_id)


def read(row: StoredFile) -> bytes:
    return get_storage().get(row.sha256)


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
