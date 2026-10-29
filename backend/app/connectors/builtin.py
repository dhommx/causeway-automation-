"""Built-in connectors: files uploaded in the portal in, files kept for download out."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.connectors.base import Destination, Source, register
from app.models import StoredFile
from app.services import files as file_service
from app.workflows.base import InputFile, OutputFile


@register
class UploadSource(Source):
    """Files the user uploaded through the portal. request = {"files": [{"id", "password"?}]}."""

    kind = "upload"
    label = "Upload in the portal"

    def __init__(self, db: Session, **kwargs: Any):
        super().__init__(**kwargs)
        self.db = db

    def fetch(self, slot: str, request: dict[str, Any]) -> list[InputFile]:
        files = []
        for item in request.get("files", []):
            row = self.db.get(StoredFile, uuid.UUID(str(item["id"])))
            if row is None:
                raise LookupError(f"File {item['id']} not found")
            files.append(
                InputFile(
                    slot=slot,
                    name=row.original_name,
                    data=file_service.read(row),
                    password=item.get("password") or None,
                )
            )
        return files


@register
class DownloadDestination(Destination):
    """Keeps outputs in the run's output folder, downloadable from its page (the default)."""

    kind = "download"
    label = "Download from the portal"

    def send(self, run_id: str, outputs: list[OutputFile]) -> dict[str, Any]:
        # Storing and linking the files is done by the run service; nothing else to deliver.
        return {"files": [o.name for o in outputs]}
