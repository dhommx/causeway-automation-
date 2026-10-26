"""Finds every workflow at startup. A new workflow only needs its module under app/workflows/<dept>/;
nothing else in the portal has to change."""

import importlib
import inspect
import pkgutil
from functools import lru_cache

from app.workflows.base import Workflow

DEPARTMENTS = {
    "finance": {
        "name": "Finance",
        "summary": "Daily reconciliation, invoicing and collection work.",
    },
}


def _discover() -> dict[str, Workflow]:
    import app.workflows as root

    found: dict[str, Workflow] = {}
    for mod in pkgutil.walk_packages(root.__path__, prefix="app.workflows."):
        module = importlib.import_module(mod.name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(cls, Workflow)
                and cls is not Workflow
                and cls.__module__ == module.__name__
            ):
                if cls.key in found:
                    raise RuntimeError(f"Two workflows use the key {cls.key!r}")
                if cls.department not in DEPARTMENTS:
                    raise RuntimeError(f"{cls.key}: unknown department {cls.department!r}")
                found[cls.key] = cls()
    return found


@lru_cache
def workflows() -> dict[str, Workflow]:
    return dict(sorted(_discover().items(), key=lambda kv: (kv[1].department, kv[1].number)))


def get_workflow(key: str) -> Workflow | None:
    return workflows().get(key)
