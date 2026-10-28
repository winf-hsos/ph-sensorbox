import pytest
from fastapi.testclient import TestClient

from phbox_server.main import create_app

SECRET = "a" * 64
ADMIN = ("admin", "test-password")


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(db_path=str(tmp_path / "test.sqlite3"), admin_password=ADMIN[1]))


def upload(client, records, secret=SECRET):
    return client.post("/api/v1/readings", headers={"Authorization": f"Bearer {secret}"},
                       json={"box": "box1", "firmware": "test", "records": records})


RECORDS = [
    {"t": "2026-10-28T09:00:00Z", "mv": 1632.5, "temp_c": 25.0, "n": 10},
    {"t": "2026-10-28T09:00:10Z", "mv": 1437.1, "temp_c": 25.0, "n": 10},
]


def test_a_new_box_waits_for_approval(client):
    r = client.post("/api/v1/register", json={"box": "box1", "secret": SECRET, "firmware": "test"})
    assert r.status_code == 200 and r.json()["status"] == "pending"
    assert upload(client, RECORDS).status_code == 403
    assert client.get("/api/v1/boxes").json() == []
    assert client.get("/api/v1/admin/boxes").status_code == 401
    assert [b["id"] for b in client.get("/api/v1/admin/boxes", auth=ADMIN).json()] == ["box1"]


def test_another_secret_cannot_take_over_a_box(client):
    client.post("/api/v1/register", json={"box": "box1", "secret": SECRET})
    r = client.post("/api/v1/register", json={"box": "box1", "secret": "b" * 64})
    assert r.status_code == 409
    client.patch("/api/v1/boxes/box1", json={"status": "approved"}, auth=ADMIN)
    assert upload(client, RECORDS, secret="b" * 64).status_code == 401


@pytest.fixture
def approved(client):
    client.post("/api/v1/register", json={"box": "box1", "secret": SECRET})
    r = client.patch("/api/v1/boxes/box1", json={"status": "approved", "name": "Bench"}, auth=ADMIN)
    assert r.status_code == 200
    return client


def test_upload_is_idempotent_and_rejects_unset_clocks(approved):
    r = upload(approved, RECORDS + [{"t": "1970-01-01T00:00:05Z", "mv": 1, "temp_c": 1}])
    assert r.json()["accepted"] == 2 and r.json()["rejected"] == 1
    r = upload(approved, RECORDS)
    assert r.json()["accepted"] == 0 and r.json()["duplicates"] == 2
    readings = approved.get("/api/v1/boxes/box1/readings").json()
    assert [x["t"] for x in readings] == ["2026-10-28T09:00:00Z", "2026-10-28T09:00:10Z"]
    assert readings[0]["ph"] == pytest.approx(7, abs=0.001)
    assert readings[0]["calibration_id"] is None


def test_calibration_applies_from_its_time_on(approved):
    upload(approved, RECORDS)
    r = approved.post("/api/v1/boxes/box1/calibrations", auth=ADMIN, json={
        "t": "2026-10-28T09:00:05Z", "probe": "test probe",
        "points": [[4.0, 2000.0, 25.0], [7.0, 1400.0, 25.0]]})
    assert r.status_code == 200 and r.json()["slope_mv_per_ph"] == pytest.approx(-200)
    first, second = approved.get("/api/v1/boxes/box1/readings").json()
    assert first["calibration_id"] is None  # before the calibration: nominal curve
    assert second["calibration_id"] == r.json()["id"]
    assert second["ph"] == pytest.approx(7 + (1437.1 - 1400) / -200, abs=0.001)
    assert upload(approved, []).json()["calibration"]["id"] == r.json()["id"]


def test_csv_export(approved):
    upload(approved, RECORDS)
    r = approved.get("/api/v1/boxes/box1/readings?format=csv&start=2026-10-28T09:00:05Z")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("time_utc,voltage_mv")
    assert len(lines) == 2 and lines[1].startswith("2026-10-28T09:00:10Z")


def test_admin_password_from_file(tmp_path, monkeypatch):
    (tmp_path / "pw").write_text("from-file\n")
    monkeypatch.delenv("PHBOX_ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("PHBOX_ADMIN_PASSWORD_FILE", str(tmp_path / "pw"))
    client = TestClient(create_app(db_path=str(tmp_path / "db.sqlite3")))
    assert client.get("/api/v1/admin/boxes", auth=("admin", "from-file")).status_code == 200
    assert client.get("/api/v1/admin/boxes", auth=("admin", "wrong")).status_code == 401


def test_pages_and_admin_protection(approved):
    assert approved.get("/").status_code == 200
    assert approved.get("/box?id=box1").status_code == 200
    assert approved.get("/admin").status_code == 401
    assert approved.get("/admin", auth=ADMIN).status_code == 200
