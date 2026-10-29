import json
import os
from datetime import date
from pathlib import Path

from app.core import storage
from tests.test_api import KEY, PARAMS, causeway_inputs
from tests.test_causeway_sales import AFS_PASSWORD


def run_causeway(client) -> dict:
    body = {"workflow_key": KEY, "inputs": causeway_inputs(client), "params": PARAMS}
    run_id = client.post("/api/v1/runs", json=body).json()["id"]
    return client.get(f"/api/v1/runs/{run_id}").json()


def test_run_saves_inputs_entries_and_outputs_in_its_folder(client):
    run = run_causeway(client)
    assert run["status"] == "succeeded", run["error"]

    folder = Path(run["folder"])
    root = Path(os.environ["AP_DATA_ROOT"])
    assert folder.parent.parent == root  # <data folder>/<date>/<automation - time>
    date.fromisoformat(folder.parent.name)
    assert folder.name.startswith("Causeway Sales Reconciliation - ")

    assert sorted(p.name for p in (folder / "input").iterdir()) == [
        "afs.xlsx",
        "entries.json",
        "zoho.xlsx",
    ]
    assert json.loads((folder / "input" / "entries.json").read_text()) == PARAMS
    outputs = [f for f in run["files"] if f["role"] == "output"]
    assert {p.name for p in (folder / "output").iterdir()} == {
        f["file"]["original_name"] for f in outputs
    }

    summary = json.loads((folder / "run.json").read_text())
    assert summary["status"] == "succeeded"
    assert summary["entries"] == PARAMS
    assert {i["saved_as"] for i in summary["inputs"]} == {"input/afs.xlsx", "input/zoho.xlsx"}
    assert AFS_PASSWORD not in json.dumps(summary)  # file passwords are never written to disk


def test_two_runs_in_the_same_second_get_separate_folders(tmp_path):
    at = storage.local_now()
    first = storage.new_run_folder(tmp_path, "Causeway", at)
    second = storage.new_run_folder(tmp_path, "Causeway", at)
    assert first != second and second.name.endswith("(2)")


def test_files_are_never_overwritten(tmp_path):
    a, _ = storage.write_new(tmp_path, "zoho.xlsx", b"one")
    b, _ = storage.write_new(tmp_path, "zoho.xlsx", b"two")
    assert (a.name, b.name) == ("zoho.xlsx", "zoho (2).xlsx")
    assert a.read_bytes() == b"one"


def test_data_folder_can_be_changed_and_reset(client, tmp_path):
    url = "/api/v1/settings"
    default = client.get(url).json()["default_data_folder"]

    chosen = tmp_path / "Audit Data"
    saved = client.put(url, json={"data_folder": str(chosen)}).json()
    assert saved["data_folder"] == str(chosen)
    run = run_causeway(client)
    assert Path(run["folder"]).is_relative_to(chosen)

    assert client.put(url, json={"data_folder": "relative/path"}).status_code == 422
    assert client.put(url, json={"data_folder": None}).json()["data_folder"] == default
    # The older run still opens from where it was saved.
    out = next(f for f in run["files"] if f["role"] == "output")
    assert client.get(f"/api/v1/files/{out['file']['id']}/download").status_code == 200


def test_old_unused_uploads_are_cleared(tmp_path):
    old = tmp_path / storage.UPLOADS / "2026-10-01"
    recent = tmp_path / storage.UPLOADS / "2026-10-25"
    for d in (old, recent):
        storage.write_new(d, "zoho.xlsx", b"x")
    removed = storage.clear_old_uploads(tmp_path, 7, date(2026, 10, 27))
    assert removed == [str(old)] and recent.exists() and not old.exists()
