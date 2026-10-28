# Box protocol

Status: version 1, implemented by the server in `server/` and by the bench box `tools/bench_box.py`, which serves as the reference for the ESP32 firmware. All bodies are JSON, all times UTC in ISO 8601 with `Z`.

## 1. Registration

On every start the box calls

```
POST /api/v1/register
{"box": "227Z", "secret": "<64 hex characters>", "firmware": "0.1.0"}
```

`box` is the Brick's UID (letters, digits, `-` and `_`, at most 32 characters). The box creates the secret once with a random generator and keeps it in its flash; the server stores only a SHA-256 hash. A new box id is stored as `pending` and shows up for the administrator, who compares the id with the one on the box's display before approving it. A known id with a different secret is refused with 409, so nobody can take over a box by knowing its id.

The answer is the box configuration (see section 3).

## 2. Upload

```
POST /api/v1/readings
Authorization: Bearer <secret>
{"box": "227Z", "firmware": "0.1.0",
 "records": [{"t": "2026-10-28T09:26:30Z", "mv": 1165.7, "temp_c": 22.19, "n": 10}, ...]}
```

| Field | Meaning |
|---|---|
| `t` | end of the sample interval, UTC |
| `mv` | board voltage in mV, the median of the samples in the interval |
| `temp_c` | thermocouple temperature in °C, or `null` when the thermocouple reports an error |
| `n` | number of samples in the record |

At most 10,000 records per request. The server ignores records it already has (same box and time), so the box can repeat a batch after a lost answer without creating duplicates. Records with a time before 2020 or more than an hour in the future are rejected, because they mean the box clock is not set.

| Answer | Meaning | What the box does |
|---|---|---|
| 200 with `accepted`, `duplicates`, `rejected` and the configuration | stored | deletes the batch from its buffer |
| 401 | unknown box or wrong secret | registers again, keeps the buffer |
| 403 with `pending` or `blocked` | not approved | keeps the buffer and tries again later |
| network error or 5xx | – | keeps the buffer and tries again later |

## 3. Configuration in every answer

```json
{"status": "approved", "sample_interval_s": 10, "upload_interval_s": 60,
 "calibration": {"id": 3, "offset_mv": 1621.3, "slope_mv_per_ph": -193.3, "temp_c": 22.0}}
```

The intervals are set per box in the dashboard. The calibration is the newest one for the box, or the nominal curve of the Atlas board with `id: null`; the box uses it only for its display, with `pH = 7 + (mv − offset_mv) / (slope_mv_per_ph · (T + 273.15) / (temp_c + 273.15))`. The server keeps the raw voltages and computes the pH of every reading with the calibration that was valid at that time.

## 4. Reading the data

| Request | Content |
|---|---|
| `GET /api/v1/boxes` | approved boxes with their last reading |
| `GET /api/v1/boxes/{id}` | one box with its calibrations |
| `GET /api/v1/boxes/{id}/readings?start=…&end=…&format=csv` | readings with pH as JSON or CSV; without a range the newest 8,640 records |
| `GET /api/v1/stream` | server-sent events `reading` and `box` for live views |
