"""SQLite storage for boxes, raw readings and calibrations."""
import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS boxes (
    id TEXT PRIMARY KEY,
    secret_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',   -- pending, approved, blocked
    name TEXT,
    location TEXT,
    firmware TEXT,
    created_at TEXT NOT NULL,
    last_seen TEXT,
    sample_interval_s INTEGER NOT NULL DEFAULT 10,
    upload_interval_s INTEGER NOT NULL DEFAULT 60
);
CREATE TABLE IF NOT EXISTS readings (
    box_id TEXT NOT NULL REFERENCES boxes(id),
    t TEXT NOT NULL,              -- UTC, ISO 8601 with Z
    mv REAL NOT NULL,             -- board voltage
    temp_c REAL,
    n INTEGER,                    -- samples averaged into this record
    received_at TEXT NOT NULL,
    PRIMARY KEY (box_id, t)
);
CREATE TABLE IF NOT EXISTS calibrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    box_id TEXT NOT NULL REFERENCES boxes(id),
    t TEXT NOT NULL,              -- valid for readings from this time on
    probe TEXT,
    points_json TEXT NOT NULL,    -- [[pH, mV, °C], ...]
    offset_mv REAL NOT NULL,
    slope_mv_per_ph REAL NOT NULL,
    temp_c REAL NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS calibration_drafts (
    box_id TEXT PRIMARY KEY REFERENCES boxes(id),
    draft_json TEXT NOT NULL,     -- {"probe": ..., "points": [{"ph", "mv", "temp_c", "t"}, ...]}
    updated_at TEXT NOT NULL
);
"""


def now_utc() -> str:
    return iso(datetime.now(timezone.utc))


def iso(dt: datetime) -> str:
    """Normalise a datetime to the stored form, UTC with second precision and Z."""
    if dt.tzinfo is None:
        raise ValueError("timestamps must carry a time zone")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    return con


def get_box(con, box_id):
    return con.execute("SELECT * FROM boxes WHERE id = ?", (box_id,)).fetchone()


def list_boxes(con):
    return con.execute("SELECT * FROM boxes ORDER BY status, COALESCE(name, id)").fetchall()


def create_box(con, box_id, secret_hash, firmware):
    con.execute(
        "INSERT INTO boxes (id, secret_hash, firmware, created_at) VALUES (?, ?, ?, ?)",
        (box_id, secret_hash, firmware, now_utc()),
    )
    con.commit()


def update_box(con, box_id, **fields):
    allowed = {"status", "name", "location", "firmware", "last_seen",
               "sample_interval_s", "upload_interval_s"}
    fields = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not fields:
        return
    assignments = ", ".join(f"{k} = ?" for k in fields)
    con.execute(f"UPDATE boxes SET {assignments} WHERE id = ?", (*fields.values(), box_id))
    con.commit()


def insert_readings(con, box_id, records) -> list[dict]:
    """Insert records and return those that were new; repeats of a batch are ignored."""
    received = now_utc()
    new = []
    for r in records:
        cur = con.execute(
            "INSERT OR IGNORE INTO readings (box_id, t, mv, temp_c, n, received_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (box_id, r["t"], r["mv"], r.get("temp_c"), r.get("n"), received),
        )
        if cur.rowcount:
            new.append(r)
    con.commit()
    return new


def readings(con, box_id, start=None, end=None, limit=None):
    where = "box_id = ?"
    args = [box_id]
    if start:
        where += " AND t >= ?"
        args.append(start)
    if end:
        where += " AND t <= ?"
        args.append(end)
    if limit:
        # the newest `limit` records, returned in chronological order
        sql = (f"SELECT * FROM (SELECT t, mv, temp_c, n FROM readings WHERE {where} "
               "ORDER BY t DESC LIMIT ?) ORDER BY t")
        args.append(limit)
    else:
        sql = f"SELECT t, mv, temp_c, n FROM readings WHERE {where} ORDER BY t"
    return con.execute(sql, args).fetchall()


def last_reading(con, box_id):
    return con.execute(
        "SELECT t, mv, temp_c, n FROM readings WHERE box_id = ? ORDER BY t DESC LIMIT 1",
        (box_id,),
    ).fetchone()


def add_calibration(con, box_id, t, probe, points, cal):
    cur = con.execute(
        "INSERT INTO calibrations (box_id, t, probe, points_json, offset_mv, slope_mv_per_ph, "
        "temp_c, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (box_id, t, probe, json.dumps(points), cal.offset_mv, cal.slope_mv_per_ph,
         cal.temp_c, now_utc()),
    )
    con.commit()
    return cur.lastrowid


def calibrations(con, box_id):
    return con.execute(
        "SELECT * FROM calibrations WHERE box_id = ? ORDER BY t", (box_id,)
    ).fetchall()


def get_draft(con, box_id):
    return con.execute(
        "SELECT draft_json, updated_at FROM calibration_drafts WHERE box_id = ?", (box_id,)
    ).fetchone()


def set_draft(con, box_id, draft) -> str:
    updated = now_utc()
    con.execute(
        "INSERT INTO calibration_drafts (box_id, draft_json, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT (box_id) DO UPDATE SET draft_json = excluded.draft_json, "
        "updated_at = excluded.updated_at",
        (box_id, json.dumps(draft), updated),
    )
    con.commit()
    return updated


def delete_draft(con, box_id):
    con.execute("DELETE FROM calibration_drafts WHERE box_id = ?", (box_id,))
    con.commit()
