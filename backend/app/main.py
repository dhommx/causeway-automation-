import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import files, rules, runs, settings, system, workflows
from app.config import get_settings
from app.workflows.registry import workflows as registered

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    registered()  # load every workflow now, so a broken one stops startup instead of a request
    settings = get_settings()
    if settings.run_inline:
        yield
        return
    from app.jobs import app as jobs_app

    jobs_app.open()
    try:
        yield
    finally:
        jobs_app.close()


app = FastAPI(title="PIE Automation Portal API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
for module in (system, workflows, files, runs, rules, settings):
    app.include_router(module.router, prefix=API_PREFIX)
