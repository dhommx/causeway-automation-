"""Background jobs (Procrastinate, queue kept in Postgres).

Start the worker with:  uv run python -m procrastinate --app=app.jobs.app worker
Scheduled runs (e.g. pull from Zoho every morning) go here later as @app.periodic tasks,
like clear_old_uploads below.
"""

import uuid

from procrastinate import App, PsycopgConnector

from app.config import get_settings

app = App(connector=PsycopgConnector(conninfo=get_settings().libpq_url))


@app.periodic(cron="0 3 * * *")
@app.task(name="clear_old_uploads", queue="workflows")
def clear_old_uploads(timestamp: int) -> None:
    """Every night at 03:00: delete uploads that were never used in a run (see guide.md)."""
    from app.core import audit, storage
    from app.db import SessionLocal
    from app.services import settings

    with SessionLocal() as db:
        removed = storage.clear_old_uploads(
            settings.data_folder(db), get_settings().upload_keep_days, storage.local_now().date()
        )
        if removed:
            audit.record(
                db,
                "files.uploads_cleared",
                "folder",
                "_uploads",
                {"removed": removed},
                audit.SYSTEM,
            )
            db.commit()


@app.task(name="run_workflow", queue="workflows")
def run_workflow(run_id: str, sealed_passwords: str | None = None) -> None:
    from app.services.runs import execute

    execute(uuid.UUID(run_id), sealed_passwords)
