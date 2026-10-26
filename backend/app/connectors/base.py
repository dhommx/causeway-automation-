"""Connectors move data in and out of the portal.

A Source brings input files or values in (upload, email inbox, Zoho API, shared folder...).
A Destination sends results out (download, shared folder, PACT, email, webhook...).

Workflows never talk to outside systems directly; they get files through RunContext. That is
what lets a workflow switch from "user uploads the Zoho export" to "portal pulls it from the
Zoho API" by changing the connector, not the workflow.

To add a connector: subclass Source or Destination, give it a unique `kind`, decorate it with
@register, and keep its credentials in a Connection row (encrypted with app.core.secrets).
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from app.workflows.base import InputFile, OutputFile


class Source(ABC):
    kind: ClassVar[str]
    label: ClassVar[str]

    def __init__(self, config: dict[str, Any] | None = None, secret: dict[str, Any] | None = None):
        self.config = config or {}
        self.secret = secret or {}

    @abstractmethod
    def fetch(self, slot: str, request: dict[str, Any]) -> list[InputFile]:
        """Return the files for one input slot of a run."""


class Destination(ABC):
    kind: ClassVar[str]
    label: ClassVar[str]

    def __init__(self, config: dict[str, Any] | None = None, secret: dict[str, Any] | None = None):
        self.config = config or {}
        self.secret = secret or {}

    @abstractmethod
    def send(self, run_id: str, outputs: list[OutputFile]) -> dict[str, Any]:
        """Deliver a run's outputs. Returns details recorded in the audit log."""


SOURCES: dict[str, type[Source]] = {}
DESTINATIONS: dict[str, type[Destination]] = {}


def register(cls):
    if issubclass(cls, Source):
        SOURCES[cls.kind] = cls
    elif issubclass(cls, Destination):
        DESTINATIONS[cls.kind] = cls
    return cls
