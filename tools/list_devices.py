#!/usr/bin/env python3
"""List all Tinkerforge devices reachable through a Brick Daemon or an ESP32 Brick."""
import sys
import time

from tinkerforge.bricklet_analog_in_v3 import BrickletAnalogInV3
from tinkerforge.bricklet_thermocouple_v2 import BrickletThermocoupleV2
from tinkerforge.ip_connection import IPConnection

HOST = sys.argv[1] if len(sys.argv) > 1 else "localhost"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 4223

# Device identifiers come from the bindings; the ESP32 Brick has none there.
NAMES = {
    BrickletAnalogInV3.DEVICE_IDENTIFIER: "Analog In Bricklet 3.0",
    BrickletThermocoupleV2.DEVICE_IDENTIFIER: "Thermocouple Bricklet 2.0",
}

devices = []


def on_enumerate(uid, connected_uid, position, hw, fw, device_id, enum_type):
    if enum_type == IPConnection.ENUMERATION_TYPE_DISCONNECTED:
        return
    devices.append((uid, connected_uid, position, fw, device_id))


ipcon = IPConnection()
ipcon.register_callback(IPConnection.CALLBACK_ENUMERATE, on_enumerate)
ipcon.connect(HOST, PORT)
ipcon.enumerate()
time.sleep(2)
ipcon.disconnect()

if not devices:
    print(f"No devices found at {HOST}:{PORT}")
    sys.exit(1)

for uid, connected_uid, position, fw, device_id in devices:
    name = NAMES.get(device_id, f"unknown device {device_id}")
    print(f"{uid:>8}  {name:<28} connected to {connected_uid or '-':>8} "
          f"position {position}  firmware {'.'.join(map(str, fw))}")
