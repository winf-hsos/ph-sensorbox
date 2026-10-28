#!/usr/bin/env python3
"""Read the pH board voltage and the thermocouple temperature and print or log them.

The script only reads. It never changes the configuration of a Bricklet.

Usage: read_sensors.py [--host H] [--port P] [--analog-uid UID] [--tc-uid UID]
                       [--count N] [--interval S] [--csv FILE]
"""
import argparse
import csv
import datetime
import statistics
import time

from tinkerforge.bricklet_analog_in_v3 import BrickletAnalogInV3
from tinkerforge.bricklet_thermocouple_v2 import BrickletThermocoupleV2
from tinkerforge.ip_connection import IPConnection

TC_TYPES = {
    BrickletThermocoupleV2.TYPE_B: "B", BrickletThermocoupleV2.TYPE_E: "E",
    BrickletThermocoupleV2.TYPE_J: "J", BrickletThermocoupleV2.TYPE_K: "K",
    BrickletThermocoupleV2.TYPE_N: "N", BrickletThermocoupleV2.TYPE_R: "R",
    BrickletThermocoupleV2.TYPE_S: "S", BrickletThermocoupleV2.TYPE_T: "T",
    BrickletThermocoupleV2.TYPE_G8: "G8 (voltage, 1/8)",
    BrickletThermocoupleV2.TYPE_G32: "G32 (voltage, 1/32)",
}

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--host", default="localhost")
parser.add_argument("--port", type=int, default=4223)
parser.add_argument("--analog-uid", default="27eC")
parser.add_argument("--tc-uid", default="2f9u")
parser.add_argument("--count", type=int, default=20)
parser.add_argument("--interval", type=float, default=1.0)
parser.add_argument("--csv")
args = parser.parse_args()

ipcon = IPConnection()
ipcon.connect(args.host, args.port)
analog = BrickletAnalogInV3(args.analog_uid, ipcon)
tc = BrickletThermocoupleV2(args.tc_uid, ipcon)

averaging, tc_type, line_filter = tc.get_configuration()
print(f"Thermocouple: type {TC_TYPES.get(tc_type, tc_type)}, averaging {averaging}, "
      f"filter {'60 Hz' if line_filter == 1 else '50 Hz'}")
# The oversampling setting is an index: 0 means 32x, 1 means 64x, up to 9 for 16384x.
print(f"Analog In: oversampling {32 * 2 ** analog.get_oversampling()}x, "
      f"calibration {analog.get_calibration()}")

writer = None
csv_file = None
if args.csv:
    csv_file = open(args.csv, "a", newline="")
    writer = csv.writer(csv_file)
    if csv_file.tell() == 0:
        writer.writerow(["time_utc", "voltage_mv", "temperature_c", "open_circuit", "over_under"])

volts, temps = [], []
print(f"{'time (UTC)':<26}{'voltage [mV]':>14}{'temperature [C]':>17}  state")
try:
    for _ in range(args.count):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        voltage_mv = analog.get_voltage()
        temperature_c = tc.get_temperature() / 100
        over_under, open_circuit = tc.get_error_state()
        state = "ok" if not (over_under or open_circuit) else (
            "OPEN CIRCUIT" if open_circuit else "over/under voltage")
        print(f"{now:<26}{voltage_mv:>14}{temperature_c:>17.2f}  {state}")
        volts.append(voltage_mv)
        temps.append(temperature_c)
        if writer:
            writer.writerow([now, voltage_mv, f"{temperature_c:.2f}", open_circuit, over_under])
        time.sleep(args.interval)
finally:
    ipcon.disconnect()
    if csv_file:
        csv_file.close()

if len(volts) > 1:
    print(f"\nvoltage: mean {statistics.mean(volts):.1f} mV, stdev {statistics.stdev(volts):.2f} mV, "
          f"min {min(volts)}, max {max(volts)}")
    print(f"temperature: mean {statistics.mean(temps):.2f} C, stdev {statistics.stdev(temps):.3f} C")
