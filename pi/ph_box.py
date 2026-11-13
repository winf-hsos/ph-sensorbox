#!/usr/bin/env python3
"""pH Sensor Box service for a Raspberry Pi: read the Bricklets and upload to the server.

The Master Brick hangs on the Pi's USB port, brickd talks to it, and this service
does what tools/bench_box.py does on a laptop, made for unattended operation:

- it finds the Analog In 3.0 and the Thermocouple 2.0 by enumeration, so a box
  works with any set of Bricklets without editing UIDs;
- it waits until the clock is synchronised, because the Pi has no real-time clock
  and the server rejects records with a wrong time;
- it keeps the backlog in a file, so records survive a restart or a power cut;
- it keeps running when the Brick or the network is gone and catches up later;
- it writes its state to a small JSON file that `ph-box status` and the updater read.

Usage: ph_box.py [--config /etc/ph-box/config.toml] [--no-time-check]
"""
import argparse
import datetime
import json
import os
import secrets
import signal
import socket
import statistics
import subprocess
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

from tinkerforge.bricklet_analog_in_v3 import BrickletAnalogInV3
from tinkerforge.bricklet_thermocouple_v2 import BrickletThermocoupleV2
from tinkerforge.ip_connection import Error as TinkerforgeError
from tinkerforge.ip_connection import IPConnection

MAX_BACKLOG = 100_000
MAX_BATCH = 1000

DEFAULTS = {
    "server": "https://ph.hsos.uber.space",
    "box": socket.gethostname(),
    "brickd_host": "localhost",
    "brickd_port": 4223,
    "analog_uid": "",   # empty: find by enumeration
    "tc_uid": "",       # empty: find by enumeration
    "state_dir": "/var/lib/ph-box",
    "run_dir": "/run/ph-box",
}

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--config", default="/etc/ph-box/config.toml")
parser.add_argument("--no-time-check", action="store_true",
                    help="do not wait for NTP (for machines without timedatectl)")
args = parser.parse_args()

settings = dict(DEFAULTS)
config_path = Path(args.config)
if config_path.exists():
    settings.update(tomllib.loads(config_path.read_text()))

state_dir = Path(settings["state_dir"])
run_dir = Path(settings["run_dir"])
state_dir.mkdir(parents=True, exist_ok=True)
run_dir.mkdir(parents=True, exist_ok=True)

version_file = state_dir / "version"
VERSION = version_file.read_text().strip() if version_file.exists() else "dev"
FIRMWARE = f"ph-box {VERSION}"[:64]
BOX = settings["box"]

secret_file = state_dir / "secret"
if not secret_file.exists():
    secret_file.write_text(secrets.token_hex(32))
    secret_file.chmod(0o600)
secret = secret_file.read_text().strip()

backlog_file = state_dir / "backlog.jsonl"
state_file = run_dir / "state.json"


def log(text):
    print(text, flush=True)  # journald adds the time


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


state = {"version": VERSION, "box": BOX, "server": settings["server"], "pid": os.getpid(),
         "started": utc_now(), "phase": "starting", "status": "unknown", "brick": "unknown",
         "backlog": 0, "last_record": None, "last_upload": None, "last_error": None}


def save_state(**changes):
    state.update(changes)
    tmp = state_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1))
    os.replace(tmp, state_file)


def stop(signum, frame):
    raise SystemExit(0)


signal.signal(signal.SIGTERM, stop)
save_state()
log(f"{FIRMWARE} starting as box {BOX}, server {settings['server']}")


# ---- backlog that survives restarts --------------------------------------------------

def load_backlog():
    if not backlog_file.exists():
        return []
    records = []
    for line in backlog_file.read_text().splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            pass  # a line cut off by a power loss
    return records[-MAX_BACKLOG:]


def append_backlog(record):
    with backlog_file.open("a") as f:
        f.write(json.dumps(record) + "\n")


def rewrite_backlog(records):
    if not records:
        backlog_file.unlink(missing_ok=True)
        return
    tmp = backlog_file.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in records))
    os.replace(tmp, backlog_file)


backlog = load_backlog()
if backlog:
    log(f"{len(backlog)} records from before the restart still to upload")
    rewrite_backlog(backlog)  # drop cut-off lines and the overflow


# ---- clock ---------------------------------------------------------------------------

def clock_synchronised():
    try:
        out = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return out == "yes"
    except (OSError, subprocess.SubprocessError):
        return False


if not args.no_time_check and not clock_synchronised():
    log("waiting for the clock to be synchronised (NTP)")
    save_state(phase="waiting for clock")
    while not clock_synchronised():
        time.sleep(10)
    log("clock synchronised")


# ---- server --------------------------------------------------------------------------

def post(path, payload, auth=False):
    request = urllib.request.Request(
        settings["server"].rstrip("/") + path, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", "User-Agent": FIRMWARE,
                 **({"Authorization": f"Bearer {secret}"} if auth else {})})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


config = {"status": "unknown", "sample_interval_s": 10, "upload_interval_s": 60}


def register():
    global config
    try:
        config = post("/api/v1/register", {"box": BOX, "secret": secret, "firmware": FIRMWARE})
        log(f"registered as {BOX}: {config['status']}")
        save_state(status=config["status"], last_error=None)
    except urllib.error.HTTPError as error:
        log(f"registration refused ({error.code}): {error.read().decode()[:100]}")
        save_state(last_error=f"registration refused ({error.code})")
    except (urllib.error.URLError, OSError) as error:
        log(f"registration failed, measuring anyway: {error}")
        save_state(last_error=f"server not reachable: {error}")


# ---- Bricklets -----------------------------------------------------------------------

ipcon = IPConnection()


def connect_brickd():
    while True:
        try:
            ipcon.connect(settings["brickd_host"], int(settings["brickd_port"]))
            return
        except (TinkerforgeError, OSError) as error:
            save_state(phase="waiting for brickd", brick="no brickd")
            log(f"brickd not reachable ({error}), retrying in 10 s")
            time.sleep(10)


def find_bricklets():
    """Return (analog_uid, tc_uid); configured UIDs win, the rest comes from enumeration."""
    found = {}

    def on_enumerate(uid, connected_uid, position, hardware, firmware, device_id, kind):
        if kind != IPConnection.ENUMERATION_TYPE_DISCONNECTED:
            found.setdefault(device_id, uid)

    ipcon.register_callback(IPConnection.CALLBACK_ENUMERATE, on_enumerate)
    ipcon.enumerate()
    time.sleep(1.5)
    analog_uid = settings["analog_uid"] or found.get(BrickletAnalogInV3.DEVICE_IDENTIFIER)
    tc_uid = settings["tc_uid"] or found.get(BrickletThermocoupleV2.DEVICE_IDENTIFIER)
    return analog_uid, tc_uid


register()
connect_brickd()

analog = tc = None
next_search = time.monotonic()
voltages, temperatures = [], []
record_due = upload_due = time.monotonic()
brick_lost = False
save_state(phase="running", backlog=len(backlog), last_record=backlog[-1] if backlog else None)

try:
    while True:
        now = time.monotonic()

        if analog is None and now >= next_search:
            next_search = now + 10
            analog_uid, tc_uid = find_bricklets()
            if analog_uid:
                analog = BrickletAnalogInV3(analog_uid, ipcon)
                tc = BrickletThermocoupleV2(tc_uid, ipcon) if tc_uid else None
                log(f"Analog In 3.0 {analog_uid}, Thermocouple 2.0 {tc_uid or 'not found'}")
                save_state(brick="ok", analog_uid=analog_uid, tc_uid=tc_uid)
                record_due = time.monotonic()
            elif state["brick"] != "not found":
                log("no Analog In 3.0 found, searching every 10 s")
                save_state(brick="not found")

        if analog is not None:
            try:
                voltage = analog.get_voltage()
                temperature = None
                if tc is not None:
                    over_under, open_circuit = tc.get_error_state()
                    if not (over_under or open_circuit):
                        temperature = tc.get_temperature() / 100
            except TinkerforgeError as error:
                if not brick_lost:
                    log(f"Brick not reachable ({error}); retrying, backlog {len(backlog)} kept")
                    brick_lost = True
                    voltages, temperatures = [], []  # do not let a record span the gap
                    save_state(brick="lost")
            else:
                if brick_lost:
                    log("Brick is back, measuring again")
                    brick_lost = False
                    record_due = time.monotonic()
                    save_state(brick="ok")
                voltages.append(voltage)
                if temperature is not None:
                    temperatures.append(temperature)

        now = time.monotonic()
        if voltages and now >= record_due + config["sample_interval_s"]:
            record_due = now
            record = {"t": utc_now(), "mv": statistics.median(voltages),
                      "temp_c": round(statistics.median(temperatures), 2) if temperatures else None,
                      "n": len(voltages)}
            backlog.append(record)
            append_backlog(record)
            if len(backlog) > MAX_BACKLOG:
                del backlog[:-MAX_BACKLOG]
                rewrite_backlog(backlog)
            voltages, temperatures = [], []
            save_state(last_record=record, backlog=len(backlog))

        if backlog and now >= upload_due + config["upload_interval_s"]:
            upload_due = now
            batch = backlog[:MAX_BATCH]
            try:
                answer = post("/api/v1/readings", {"box": BOX, "firmware": FIRMWARE,
                                                   "records": batch}, auth=True)
                del backlog[:len(batch)]
                rewrite_backlog(backlog)
                config = answer
                if answer["accepted"] or answer.get("rejected"):
                    log(f"uploaded: {answer['accepted']} new, {answer['duplicates']} repeated, "
                        f"{answer.get('rejected', 0)} rejected, backlog {len(backlog)}")
                save_state(status=answer.get("status", state["status"]), backlog=len(backlog),
                           last_upload=utc_now(), last_error=None)
                if len(backlog) >= MAX_BATCH:
                    upload_due = now - config["upload_interval_s"]  # catch up quickly
            except urllib.error.HTTPError as error:
                detail = error.read().decode()[:100]
                log(f"upload refused ({error.code}): {detail}; keeping the backlog")
                save_state(last_error=f"upload refused ({error.code}): {detail}")
                if error.code == 401:  # the server does not know this box (yet)
                    register()
            except (urllib.error.URLError, OSError) as error:
                log(f"server not reachable: {error}; keeping the backlog")
                save_state(last_error=f"server not reachable: {error}")

        time.sleep(1)
except (KeyboardInterrupt, SystemExit):
    log(f"stopped with {len(backlog)} records not uploaded (kept in {backlog_file})")
finally:
    save_state(phase="stopped")
    try:
        ipcon.disconnect()
    except TinkerforgeError:
        pass
