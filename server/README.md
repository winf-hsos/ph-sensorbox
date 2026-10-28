# pH Sensor Box server

The central server of the pH Sensor Box: boxes register here and upload their raw readings, an administrator approves them and enters calibrations, and everyone with access sees a live dashboard and can export the data. The design is described in `../docs/02-architecture.md`, the box protocol in `../docs/06-box-protocol.md`.

Python, FastAPI and SQLite; the dashboard is plain HTML, CSS and JavaScript without a build step or external requests, in German and English, with light and dark themes. The charts (`static/plot.js`) are drawn on canvas without a chart library: crosshair with tooltip, drag to zoom, double-click to reset, arrow keys to step. The typeface Instrument Sans is served from `static/fonts/` under the SIL Open Font License (`OFL-instrument-sans.txt`), so no font service is contacted.

## Run locally

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # on Linux: .venv/bin/python
PHBOX_ADMIN_PASSWORD=choose-one .venv/Scripts/python -m uvicorn phbox_server.main:create_app --factory --port 8000
```

| Setting | Meaning | Default |
|---|---|---|
| `PHBOX_DB` | path of the SQLite file | `phbox.sqlite3` in the working directory |
| `PHBOX_ADMIN_PASSWORD` | password of the user `admin` for `/admin` and the admin API | none; admin functions are disabled without it |
| `PHBOX_ADMIN_PASSWORD_FILE` | file holding that password, used when `PHBOX_ADMIN_PASSWORD` is not set | none |

Deployment on Uberspace 8 is described in `../docs/07-deployment-uberspace.md`.

Pages: `/` overview of all approved boxes, `/box?id=…` history and calibrations of one box, `/admin` approval, names, intervals and calibration entry (HTTP basic auth, user `admin`). The API is listed at `/docs`.

To feed it with real data from the bench, run `../tools/bench_box.py`, which reads the Bricklets through a Brick Daemon and behaves like a box; approve the box `bench` under `/admin` afterwards.

## Tests

```bash
.venv/Scripts/python -m pytest
```

## Access rules

Reading is open: the overview, the history and the export of approved boxes need no login, in line with the open-data goal of the project. Writing needs either the box secret (uploads) or the admin password (approval, names, intervals, calibrations). Boxes that are pending or blocked are visible only to the administrator. Reading stays open on the public host as well (decided by Nicolas on 2026-10-28).

## Not done yet

The actual deployment on Uberspace (the guide is written but untested), a consistent daily copy of the database, several administrator accounts, deleting data, and a guided calibration workflow that waits for a stable reading.
