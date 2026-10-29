"""What a workflow is. Every automation in the portal is a subclass of Workflow.

A workflow declares:
  - who it is (key, name, department, summary, status)
  - its inputs: file slots to upload and manual fields to type in
  - its default rules (values and conditions the user can change later, versioned)
and implements run(ctx), which reads the inputs, applies the rules and adds outputs.
It can also implement check_file(file, params) for slots marked `checked`, which runs as soon as
the file is added, before Run, and can fill manual fields and show a notice.

The portal does the rest: upload, preview, queueing, history, rule versions, audit, downloads.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, ClassVar, Literal

import polars as pl

from app.core import excel

Status = Literal["live", "planned"]


IMAGE_ACCEPT = (".png", ".jpg", ".jpeg", ".webp")


@dataclass(frozen=True)
class FileSlot:
    """A named file input, e.g. the Zoho export or the AFS sheet."""

    key: str
    label: str
    help: str = ""
    required: bool = True
    multiple: bool = False
    accept: tuple[str, ...] = (".xlsx", ".xls", ".xlsm", ".csv")
    password_protected: bool = False  # shows a password box next to the file
    # "data" files are processed; "reference" files (images) are only shown to the user and kept
    # with the run for audit.
    kind: Literal["data", "reference"] = "data"
    # The workflow's check_file() runs on this file once it is added (and its password typed);
    # Run stays disabled until it passes.
    checked: bool = False
    # Manual fields whose values the check also needs (e.g. the sales date).
    check_params: tuple[str, ...] = ()


@dataclass(frozen=True)
class ManualField:
    """A value the user types in, e.g. an amount read from an image."""

    key: str
    label: str
    type: Literal["text", "number", "money", "date", "select"] = "text"
    help: str = ""
    required: bool = True
    options: tuple[str, ...] = ()


@dataclass
class InputFile:
    slot: str
    name: str
    data: bytes
    password: str | None = None

    @property
    def is_image(self) -> bool:
        return excel.is_image(self.name)

    def sheets(self) -> dict[str, pl.DataFrame]:
        return excel.read_sheets(self.data, self.name, self.password)


@dataclass
class OutputFile:
    name: str
    data: bytes
    content_type: str = excel.XLSX_MIME
    slot: str = "output"


@dataclass
class RunContext:
    """Everything a workflow's run() gets, and where it puts its results."""

    files: list[InputFile]
    params: dict[str, Any]
    rules: dict[str, Any]
    outputs: list[OutputFile] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def files_for(self, slot: str) -> list[InputFile]:
        return [f for f in self.files if f.slot == slot]

    def add_output(self, name: str, data: bytes, content_type: str = excel.XLSX_MIME) -> None:
        self.outputs.append(OutputFile(name=name, data=data, content_type=content_type))

    def note(self, message: str) -> None:
        self.log.append(message)


@dataclass
class Metric:
    label: str
    value: str
    tone: Literal["neutral", "good", "warn", "bad"] = "neutral"


@dataclass
class ResultTable:
    """A table shown on the result screen (columns + rows of plain values)."""

    title: str
    columns: list[str]
    rows: list[list[Any]]
    # A line shown in bold above the table, e.g. the cash deposit date; "warn" highlights it.
    note: str = ""
    note_tone: Literal["neutral", "warn"] = "neutral"
    # An output file that belongs to this tab (e.g. its ERP upload file): its download button shows
    # on the tab instead of with the run's other outputs.
    file: str = ""


@dataclass
class SplitPart:
    key: str
    label: str
    code: str = ""  # account code shown next to the label


@dataclass
class Split:
    """An amount the user splits between parts after the run, in a popup (e.g. the variance
    between two accounts). The parts must add up to the total exactly. Confirming calls the
    workflow's apply_split(), which rebuilds the affected tables and outputs."""

    title: str
    message: str
    total: str
    parts: list[SplitPart]
    default_part: str  # the "all to ..." button
    amounts: dict[str, str]  # current amount per part key
    confirmed: bool = False


@dataclass
class RunResult:
    metrics: list[Metric] = field(default_factory=list)
    tables: list[ResultTable] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    split: Split | None = None


@dataclass
class Notice:
    """A popup shown once before Run, e.g. the AFS transactions that belong to the next day."""

    title: str
    message: str
    table: ResultTable | None = None


@dataclass
class FileCheck:
    """The result of check_file(), shown under the file before Run."""

    ok: bool
    message: str
    # Values written into manual fields; the user can still change them (with a warning).
    fills: dict[str, str] = field(default_factory=dict)
    notice: Notice | None = None


class WorkflowInputError(ValueError):
    """Bad input from the user. The message is shown as is, so write it for the user."""


class Workflow:
    key: ClassVar[str]
    name: ClassVar[str]
    department: ClassVar[str]
    summary: ClassVar[str]
    number: ClassVar[int]  # order on the department screen
    version: ClassVar[str] = "0.1.0"
    status: ClassVar[Status] = "live"
    icon: ClassVar[str] = "workflow"  # a lucide icon name used by the frontend
    # Facts from the proposal, shown on the card.
    current_time: ClassVar[str] = ""
    target_time: ClassVar[str] = ""
    frequency: ClassVar[str] = ""

    file_slots: ClassVar[tuple[FileSlot, ...]] = ()
    manual_fields: ClassVar[tuple[ManualField, ...]] = ()
    default_rules: ClassVar[dict[str, Any]] = {}

    def run(self, ctx: RunContext) -> RunResult:
        raise NotImplementedError(f"{self.key} has no processing yet.")

    def apply_split(
        self,
        result: dict[str, Any],
        amounts: dict[str, Decimal],
        params: dict[str, Any],
        rules: dict[str, Any],
    ) -> list[OutputFile]:
        """Apply a confirmed split to a finished run's result (changed in place) and return the
        outputs that must be replaced, matched by name. Amounts are already checked."""
        raise NotImplementedError(f"{self.key} has no split.")

    def check_file(self, file: InputFile, params: dict[str, Any]) -> FileCheck:
        """Check one file of a `checked` slot before Run. Raise WorkflowInputError for bad input."""
        raise NotImplementedError(f"{self.key} has no check for {file.slot}.")
