import io

import openpyxl

from tests.test_causeway_sales import AFS_PASSWORD, make_afs, make_zoho
from tests.test_excel import make_xlsx

KEY = "causeway-sales-reconciliation"
PARAMS = {
    "sales_date": "2026-10-18",
    "cash": "100.500",
    "cash_deposit_date": "2026-10-18",
    "pie": "215.000",
}


def upload(client, name: str, data: bytes) -> str:
    return client.post("/api/v1/files", files={"files": (name, data)}).json()[0]["id"]


def causeway_inputs(client) -> dict:
    return {
        "afs": [{"id": upload(client, "afs.xlsx", make_afs()), "password": AFS_PASSWORD}],
        "zoho": [{"id": upload(client, "zoho.xlsx", make_zoho())}],
    }


def test_health(client):
    body = client.get("/api/v1/health").json()
    assert body == {"status": "ok", "database": True, "workflows": 4}


def test_departments(client):
    finance = client.get("/api/v1/departments").json()[0]
    assert finance["key"] == "finance"
    assert len(finance["workflows"]) == 4


def test_upload_preview_run_download(client):
    up = client.post("/api/v1/files", files={"files": ("zoho.xlsx", make_xlsx())})
    assert up.status_code == 201
    file_id = up.json()[0]["id"]

    preview = client.get(f"/api/v1/files/{file_id}/preview").json()
    assert preview["columns"] == ["Invoice Number", "Total"]
    assert preview["total_rows"] == 1

    run = client.post(
        "/api/v1/runs",
        json={"workflow_key": KEY, "inputs": causeway_inputs(client), "params": PARAMS},
    )
    assert run.status_code == 202
    run = client.get(f"/api/v1/runs/{run.json()['id']}").json()
    assert run["status"] == "succeeded", run["error"]
    assert run["rule_version"] == 1
    assert run["result"]["metrics"][2]["value"] == "43.993"
    outputs = [f for f in run["files"] if f["role"] == "output"]
    # RECEIPTS and CreditNoteJV upload files, the reconciliation workbook, the Zoho file.
    assert len(outputs) == 4
    for out in outputs:
        download = client.get(f"/api/v1/files/{out['file']['id']}/download")
        assert download.status_code == 200 and download.content[:2] == b"PK"

    actions = [
        e["action"] for e in client.get("/api/v1/audit", params={"entity_id": run["id"]}).json()
    ]
    assert actions == ["run.succeeded", "run.created"]


def test_split_variance_rebuilds_the_credit_note_and_workbook(client):
    run = client.post(
        "/api/v1/runs",
        json={"workflow_key": KEY, "inputs": causeway_inputs(client), "params": PARAMS},
    ).json()
    url = f"/api/v1/runs/{run['id']}/split"

    wrong = client.post(url, json={"amounts": {"marketing_fund": "40", "business_promotion": "3"}})
    assert wrong.status_code == 422 and "43.993" in wrong.json()["detail"]

    ok = client.post(
        url, json={"amounts": {"marketing_fund": "40.000", "business_promotion": "3.993"}}
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["result"]["split"]["confirmed"] is True
    note = next(t for t in body["result"]["tables"] if t["title"] == "Credit Note (Variance)")
    assert [r[3] for r in note["rows"]] == ["0.000", "40.000", "3.993", "43.993"]
    roles = sorted(f["role"] for f in body["files"])
    assert roles.count("output") == 4 and roles.count("replaced") == 2

    workbook = next(
        f
        for f in body["files"]
        if f["role"] == "output" and f["file"]["original_name"].startswith("causeway_")
    )
    data = client.get(f"/api/v1/files/{workbook['file']['id']}/download").content
    sheet = openpyxl.load_workbook(io.BytesIO(data))["Credit Note (Variance)"]
    assert [c.value for c in sheet["D"]][1:4] == ["0.000", "40.000", "3.993"]

    actions = [
        e["action"] for e in client.get("/api/v1/audit", params={"entity_id": run["id"]}).json()
    ]
    assert actions[0] == "run.split"


def test_run_needs_required_file(client):
    r = client.post("/api/v1/runs", json={"workflow_key": KEY, "inputs": {}})
    assert r.status_code == 422 and "AFS settlement report" in r.json()["detail"]


def test_wrong_afs_password_fails_the_run(client):
    inputs = causeway_inputs(client)
    inputs["afs"][0]["password"] = "1111"
    body = {"workflow_key": KEY, "inputs": inputs, "params": PARAMS}
    run = client.get(f"/api/v1/runs/{client.post('/api/v1/runs', json=body).json()['id']}").json()
    assert run["status"] == "failed" and "password" in run["error"]


def test_check_afs_file_before_run(client):
    url = f"/api/v1/workflows/{KEY}/check-file"
    good = upload(client, "afs.xlsx", make_afs())
    body = client.post(url, json={"slot": "afs", "id": good, "password": AFS_PASSWORD}).json()
    assert body == {
        "ok": True,
        "message": "Total matches: 10 transactions = 91.000 BHD",
        "fills": {},
        "notice": None,
    }

    later = upload(client, "afs.xlsx", make_afs(later=("19-OCT-2026",)))
    body = client.post(
        url,
        json={
            "slot": "afs",
            "id": later,
            "password": AFS_PASSWORD,
            "params": {"sales_date": "2026-10-18", "cash": "1"},
        },
    ).json()
    assert body["fills"] == {"afs_next_day": "11.000"}
    assert body["notice"]["columns"] == ["Date", "Batch", "Terminal", "Tran Amt"]
    assert body["notice"]["rows"] == [["19/10/2026", "999", "03221330", "11.000"]]

    bad = upload(client, "afs.xlsx", make_afs(total=92))
    body = client.post(url, json={"slot": "afs", "id": bad, "password": AFS_PASSWORD}).json()
    assert body["ok"] is False and "Total row says 92.000" in body["message"]

    body = client.post(url, json={"slot": "afs", "id": good, "password": "1111"}).json()
    assert body["ok"] is False and "password" in body["message"]

    zoho = upload(client, "zoho.xlsx", make_zoho())
    assert client.post(url, json={"slot": "zoho", "id": zoho}).status_code == 404


def test_planned_workflow_cannot_run(client):
    r = client.post("/api/v1/runs", json={"workflow_key": "cash-collection"})
    assert r.status_code == 422


def test_rules_are_versioned(client):
    url = f"/api/v1/workflows/{KEY}/rules"
    client.get(url)
    saved = client.put(url, json={"values": {"afs_rate_percent": 2.2}, "note": "test"}).json()
    assert saved["current"]["values"] == {"afs_rate_percent": 2.2}
    assert saved["current"]["version"] == saved["versions"][1]["version"] + 1
    client.put(url, json={"values": {}, "note": "reset"})


PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_images_are_kept_for_reference_not_processed(client):
    img = client.post("/api/v1/files", files={"files": ("afs amounts.png", PNG)}).json()[0]
    assert img["content_type"] == "image/png"

    view = client.get(f"/api/v1/files/{img['id']}/download", params={"inline": True})
    assert view.headers["content-disposition"].startswith("inline")
    assert client.get(f"/api/v1/files/{img['id']}/preview").status_code == 422

    body = {
        "workflow_key": KEY,
        "inputs": {**causeway_inputs(client), "images": [{"id": img["id"]}]},
        "params": PARAMS,
    }
    run = client.get(f"/api/v1/runs/{client.post('/api/v1/runs', json=body).json()['id']}").json()
    assert run["status"] == "succeeded", run["error"]
    assert {f["slot"] for f in run["files"] if f["role"] == "input"} == {"afs", "zoho", "images"}


def test_wrong_format_for_slot_is_refused(client):
    inputs = causeway_inputs(client)
    inputs["afs"] = [{"id": upload(client, "shot.png", PNG)}]
    r = client.post("/api/v1/runs", json={"workflow_key": KEY, "inputs": inputs, "params": PARAMS})
    assert r.status_code == 422 and "can't be used as AFS settlement report" in r.json()["detail"]


def test_other_formats_refused_on_upload(client):
    r = client.post("/api/v1/files", files={"files": ("notes.txt", b"hi")})
    assert r.status_code == 422
