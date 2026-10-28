#!/usr/bin/env python3
"""Act like a pH Sensor Box on the bench: read the Bricklets and upload to the server.

This is the reference for the box protocol that the ESP32 firmware will implement:
register with a random secret, sample every second, store one record per sample
interval, upload batches over HTTP(S), keep everything that the server has not
confirmed, and take the intervals from the server's answer.

Each record holds the median of its samples, which drops single spikes from touching
the setup (see docs/05-bench-log.md).

If the Brick is unplugged, the script keeps running: it drops the samples of the
interrupted record, keeps uploading the backlog and resumes measuring once the Brick
answers again, so the outage shows up as a gap in the data.

Usage: bench_box.py [--server URL] [--box ID] [--host H] [--port P]
                    [--analog-uid UID] [--tc-uid UID]
"""
import argparse
import datetime
import json
import secrets
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

from tinkerforge.bricklet_analog_in_v3 import BrickletAnalogInV3
from tinkerforge.bricklet_thermocouple_v2 import BrickletThermocoupleV2
from tinkerforge.ip_connection import Error as TinkerforgeError
from tinkerforge.ip_connection import IPConnection

FIRMWARE = "bench-box 0.1"
MAX_BACKLOG = 100_000

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--server", default="http://127.0.0.1:8000")
parser.add_argument("--box", default="bench")
parser.add_argument("--host", default="localhost")
parser.add_argument("--port", type=int, default=4223)
parser.add_argument("--analog-uid", default="27eC")
parser.add_argument("--tc-uid", default="2f9u")
args = parser.parse_args()

secret_file = Path(__file__).with_name(f".{args.box}.secret")
if not secret_file.exists():
    secret_file.write_text(secrets.token_hex(32))
secret = secret_file.read_text().strip()


def post(path, payload, auth=False):
    request = urllib.request.Request(
        args.server.rstrip("/") + path, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {secret}"} if auth else {})})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def log(text):
    print(f"{datetime.datetime.now():%H:%M:%S}  {text}", flush=True)


config = {"status": "unknown", "sample_interval_s": 10, "upload_interval_s": 60}


def register():
    global config
    try:
        config = post("/api/v1/register", {"box": args.box, "secret": secret, "firmware": FIRMWARE})
        log(f"registered as {args.box}: {config['status']}")
    except (urllib.error.URLError, OSError) as error:
        log(f"registration failed, measuring anyway: {error}")


register()

ipcon = IPConnection()
ipcon.connect(args.host, args.port)
analog = BrickletAnalogInV3(args.analog_uid, ipcon)
tc = BrickletThermocoupleV2(args.tc_uid, ipcon)

backlog, voltages, temperatures = [], [], []
record_due = upload_due = time.monotonic()
brick_lost = False
try:
    while True:
        try:
            voltage = analog.get_voltage()
            over_under, open_circuit = tc.get_error_state()
            temperature = None if over_under or open_circuit else tc.get_temperature() / 100
        except TinkerforgeError as error:
            if not brick_lost:
                log(f"Brick not reachable ({error}); retrying, backlog {len(backlog)} kept")
                brick_lost = True
                voltages, temperatures = [], []  # do not let a record span the gap
        else:
            if brick_lost:
                log("Brick is back, measuring again")
                brick_lost = False
                record_due = time.monotonic()
            voltages.append(voltage)
            if temperature is not None:
                temperatures.append(temperature)

        now = time.monotonic()
        if voltages and now >= record_due + config["sample_interval_s"]:
            record_due = now
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            backlog.append({"t": stamp, "mv": statistics.median(voltages),
                            "temp_c": round(statistics.median(temperatures), 2) if temperatures else None,
                            "n": len(voltages)})
            del backlog[:-MAX_BACKLOG]
            voltages, temperatures = [], []
            last = backlog[-1]
            log(f"{last['mv']:.1f} mV, {last['temp_c']} °C, backlog {len(backlog)}")

        if backlog and now >= upload_due + config["upload_interval_s"]:
            upload_due = now
            batch = backlog[:1000]
            try:
                answer = post("/api/v1/readings", {"box": args.box, "firmware": FIRMWARE,
                                                   "records": batch}, auth=True)
                del backlog[:len(batch)]
                config = answer
                log(f"uploaded: {answer['accepted']} new, {answer['duplicates']} repeated")
            except urllib.error.HTTPError as error:
                log(f"upload refused ({error.code}): {error.read().decode()[:100]}; keeping the backlog")
                if error.code == 401:  # the server does not know this box (yet)
                    register()
            except (urllib.error.URLError, OSError) as error:
                log(f"server not reachable: {error}; keeping the backlog")

        time.sleep(1)
except KeyboardInterrupt:
    log(f"stopped with {len(backlog)} records not uploaded")
finally:
    ipcon.disconnect()
