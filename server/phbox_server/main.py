"""HTTP API and dashboard of the pH Sensor Box server.

Run locally:  uvicorn phbox_server.main:create_app --factory --port 8000
Settings come from the environment: PHBOX_DB (SQLite file) and PHBOX_ADMIN_PASSWORD
or PHBOX_ADMIN_PASSWORD_FILE (a file holding the password).
"""
import asyncio
import csv
import hashlib
import io
import json
import os
import secrets
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db
from .calibration import NOMINAL, Calibration, fit, slope_percent, to_ph

STATIC = Path(__file__).parent / "static"
BOX_ID = r"^[A-Za-z0-9_-]{1,32}$"
EARLIEST = datetime(2020, 1, 1, tzinfo=timezone.utc)  # older stamps mean the box clock is unset


class RegisterIn(BaseModel):
    box: str = Field(pattern=BOX_ID)
    secret: str = Field(min_length=32, max_length=128)
    firmware: str | None = Field(None, max_length=64)


class RecordIn(BaseModel):
    t: datetime
    mv: float
    temp_c: float | None = None
    n: int | None = None


class ReadingsIn(BaseModel):
    box: str = Field(pattern=BOX_ID)
    firmware: str | None = Field(None, max_length=64)
    records: list[RecordIn] = Field(max_length=10000)


class BoxUpdate(BaseModel):
    status: Literal["pending", "approved", "blocked"] | None = None
    name: str | None = Field(None, max_length=80)
    location: str | None = Field(None, max_length=120)
    sample_interval_s: int | None = Field(None, ge=1, le=3600)
    upload_interval_s: int | None = Field(None, ge=5, le=86400)


class CalibrationIn(BaseModel):
    t: datetime | None = None
    probe: str | None = Field(None, max_length=80)
    points: list[tuple[float, float, float]] = Field(min_length=2, max_length=10)


class Hub:
    """Fan-out of live events to all open dashboard streams."""

    def __init__(self):
        self.queues: set[asyncio.Queue] = set()

    def publish(self, event: str, data: dict):
        message = f"event: {event}\ndata: {json.dumps(data)}\n\n"
        for queue in list(self.queues):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass  # a stalled client misses events rather than blocking everyone


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def parse_time(value: str | None) -> str | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return db.iso(dt)


def create_app(db_path: str | None = None, admin_password: str | None = None) -> FastAPI:
    db_path = db_path or os.environ.get("PHBOX_DB", "phbox.sqlite3")
    if admin_password is None:
        admin_password = os.environ.get("PHBOX_ADMIN_PASSWORD")
    if admin_password is None and os.environ.get("PHBOX_ADMIN_PASSWORD_FILE"):
        # keeps the password out of service definitions and process listings
        admin_password = Path(os.environ["PHBOX_ADMIN_PASSWORD_FILE"]).read_text().strip()
    con = db.connect(db_path)
    hub = Hub()
    app = FastAPI(title="pH Sensor Box server")
    basic = HTTPBasic(auto_error=False)

    def require_admin(credentials: HTTPBasicCredentials | None = Depends(basic)):
        if not admin_password:
            raise HTTPException(503, "admin password not configured (PHBOX_ADMIN_PASSWORD)")
        ok = credentials is not None and (
            secrets.compare_digest(credentials.username.encode(), b"admin")
            & secrets.compare_digest(credentials.password.encode(), admin_password.encode())
        )
        if not ok:
            raise HTTPException(401, headers={"WWW-Authenticate": 'Basic realm="pH Sensor Box admin"'})

    def box_or_404(box_id: str):
        box = db.get_box(con, box_id)
        if box is None:
            raise HTTPException(404, "unknown box")
        return box

    def calibrations_of(box_id: str) -> tuple[list[str], list[Calibration]]:
        rows = db.calibrations(con, box_id)
        cals = [Calibration(r["offset_mv"], r["slope_mv_per_ph"], r["temp_c"], r["id"]) for r in rows]
        return [r["t"] for r in rows], cals

    def reading_out(row, times, cals) -> dict:
        """A raw reading plus its pH, computed with the calibration valid at its time."""
        i = bisect_right(times, row["t"])
        cal = cals[i - 1] if i else NOMINAL
        return {
            "t": row["t"], "mv": row["mv"], "temp_c": row["temp_c"], "n": row["n"],
            "ph": round(to_ph(row["mv"], row["temp_c"], cal), 3),
            "calibration_id": cal.id,
        }

    def box_out(box, with_last=True) -> dict:
        out = {k: box[k] for k in ("id", "status", "name", "location", "firmware", "created_at",
                                    "last_seen", "sample_interval_s", "upload_interval_s")}
        if with_last:
            last = db.last_reading(con, box["id"])
            out["last"] = reading_out(last, *calibrations_of(box["id"])) if last else None
        return out

    def config_for(box) -> dict:
        """What a box gets back on every call: its state, intervals and current calibration."""
        times, cals = calibrations_of(box["id"])
        cal = cals[-1] if cals else NOMINAL
        return {
            "status": box["status"],
            "sample_interval_s": box["sample_interval_s"],
            "upload_interval_s": box["upload_interval_s"],
            "calibration": {"id": cal.id, "offset_mv": cal.offset_mv,
                            "slope_mv_per_ph": cal.slope_mv_per_ph, "temp_c": cal.temp_c},
        }

    def authenticate_box(box_id: str, authorization: str | None):
        box = db.get_box(con, box_id)
        token = (authorization or "").removeprefix("Bearer ").strip()
        if box is None or not secrets.compare_digest(hash_secret(token), box["secret_hash"]):
            raise HTTPException(401, "unknown box or wrong secret")
        return box

    # --- API for the boxes -------------------------------------------------------------

    @app.post("/api/v1/register")
    async def register(body: RegisterIn):
        box = db.get_box(con, body.box)
        if box is None:
            db.create_box(con, body.box, hash_secret(body.secret), body.firmware)
            box = db.get_box(con, body.box)
            hub.publish("box", box_out(box, with_last=False))
        elif not secrets.compare_digest(hash_secret(body.secret), box["secret_hash"]):
            raise HTTPException(409, "box id already registered with another secret")
        db.update_box(con, body.box, firmware=body.firmware, last_seen=db.now_utc())
        return config_for(db.get_box(con, body.box))

    @app.post("/api/v1/readings")
    async def upload(body: ReadingsIn, authorization: str | None = Header(None)):
        box = authenticate_box(body.box, authorization)
        if box["status"] != "approved":
            raise HTTPException(403, box["status"])
        latest = datetime.now(timezone.utc) + timedelta(hours=1)
        records, rejected = [], 0
        for r in body.records:
            if r.t.tzinfo is None or not (EARLIEST <= r.t <= latest):
                rejected += 1
                continue
            records.append({"t": db.iso(r.t), "mv": r.mv, "temp_c": r.temp_c, "n": r.n})
        new = db.insert_readings(con, body.box, records)
        db.update_box(con, body.box, firmware=body.firmware, last_seen=db.now_utc())
        times, cals = calibrations_of(body.box)
        for r in new:
            hub.publish("reading", {"box": body.box, **reading_out(r, times, cals)})
        return {"accepted": len(new), "duplicates": len(records) - len(new),
                "rejected": rejected, **config_for(db.get_box(con, body.box))}

    # --- public read API ---------------------------------------------------------------

    @app.get("/api/v1/boxes")
    async def boxes():
        return [box_out(b) for b in db.list_boxes(con) if b["status"] == "approved"]

    @app.get("/api/v1/boxes/{box_id}")
    async def box_detail(box_id: str):
        box = box_or_404(box_id)
        if box["status"] != "approved":
            raise HTTPException(404, "unknown box")
        out = box_out(box)
        out["calibrations"] = [
            {"id": r["id"], "t": r["t"], "probe": r["probe"], "points": json.loads(r["points_json"]),
             "offset_mv": r["offset_mv"], "slope_mv_per_ph": r["slope_mv_per_ph"],
             "temp_c": r["temp_c"],
             "slope_percent": round(slope_percent(Calibration(r["offset_mv"], r["slope_mv_per_ph"],
                                                              r["temp_c"])), 1)}
            for r in db.calibrations(con, box_id)
        ]
        return out

    @app.get("/api/v1/boxes/{box_id}/readings")
    async def box_readings(box_id: str, start: str | None = None, end: str | None = None,
                           limit: int | None = None, format: Literal["json", "csv"] = "json"):
        box = box_or_404(box_id)
        if box["status"] != "approved":
            raise HTTPException(404, "unknown box")
        try:
            start, end = parse_time(start), parse_time(end)
        except ValueError:
            raise HTTPException(422, "start and end must be ISO 8601 times")
        if not (start or end or limit):
            limit = 8640  # one day at one record every 10 s
        times, cals = calibrations_of(box_id)
        rows = [reading_out(r, times, cals) for r in db.readings(con, box_id, start, end, limit)]
        if format == "json":
            return rows
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["time_utc", "voltage_mv", "temperature_c", "samples", "ph", "calibration_id"])
        for r in rows:
            writer.writerow([r["t"], r["mv"], r["temp_c"], r["n"], r["ph"], r["calibration_id"]])
        return Response(buffer.getvalue(), media_type="text/csv", headers={
            "Content-Disposition": f'attachment; filename="{box_id}-readings.csv"'})

    @app.get("/api/v1/stream")
    async def stream(request: Request):
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        hub.queues.add(queue)

        async def events():
            try:
                yield "retry: 5000\n\n"
                while not await request.is_disconnected():
                    try:
                        # Uberspace closes idle connections after three minutes
                        yield await asyncio.wait_for(queue.get(), timeout=30)
                    except asyncio.TimeoutError:
                        yield ": keep-alive\n\n"
            finally:
                hub.queues.discard(queue)

        return StreamingResponse(events(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache"})

    # --- administration ----------------------------------------------------------------

    @app.get("/api/v1/admin/boxes", dependencies=[Depends(require_admin)])
    async def admin_boxes():
        return [box_out(b) for b in db.list_boxes(con)]

    @app.patch("/api/v1/boxes/{box_id}", dependencies=[Depends(require_admin)])
    async def update_box(box_id: str, body: BoxUpdate):
        box_or_404(box_id)
        db.update_box(con, box_id, **body.model_dump())
        box = db.get_box(con, box_id)
        hub.publish("box", box_out(box, with_last=False))
        return box_out(box)

    @app.post("/api/v1/boxes/{box_id}/calibrations", dependencies=[Depends(require_admin)])
    async def add_calibration(box_id: str, body: CalibrationIn):
        box_or_404(box_id)
        try:
            cal = fit(body.points)
        except ValueError as error:
            raise HTTPException(422, str(error))
        t = db.iso(body.t) if body.t else db.now_utc()
        cal_id = db.add_calibration(con, box_id, t, body.probe, [list(p) for p in body.points], cal)
        return {"id": cal_id, "t": t, "offset_mv": cal.offset_mv,
                "slope_mv_per_ph": cal.slope_mv_per_ph, "temp_c": cal.temp_c,
                "slope_percent": round(slope_percent(cal), 1)}

    # --- pages -------------------------------------------------------------------------

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/box", include_in_schema=False)
    async def box_page():
        return FileResponse(STATIC / "box.html")

    @app.get("/admin", include_in_schema=False, dependencies=[Depends(require_admin)])
    async def admin_page():
        return FileResponse(STATIC / "admin.html")

    @app.middleware("http")
    async def revalidate_static(request: Request, call_next):
        # without this, browsers keep an old app.js after an update
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
