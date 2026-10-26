"""Background jobs (Procrastinate, queue kept in Postgres).

Start the worker with:  uv run python -m procrastinate --app=app.jobs.app worker
Scheduled runs (e.g. pull from Zoho every morning) go here later as @app.periodic tasks.
"""

import uuid

from procrastinate import App, PsycopgConnector

from app.config import get_settings

app = App(connector=PsycopgConnector(conninfo=get_settings().libpq_url))


@app.task(name="run_workflow", queue="workflows")
def run_workflow(run_id: str, sealed_passwords: str | None = None) -> None:
    from app.services.runs import execute

    execute(uuid.UUID(run_id), sealed_passwords)
