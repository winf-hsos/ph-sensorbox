# Architecture

Status: the direction was agreed with Nicolas on 2026-10-28; the details below are proposals. Statements marked **(calculation)** or **(inference)** are ours and not taken from a source.

## Requirements (Nicolas, 2026-10-28)

- Many boxes run in parallel. Each box holds an ESP32 Brick, the Analog In Bricklet 3.0 with the Atlas analog pH board, the Thermocouple Bricklet 2.0 and an OLED 128x64 Bricklet as a display that only shows values.
- The enclosure is 3D printed and fitted to these parts.
- No cables except the pH probe and the thermocouple probe. The box has a single USB-C port for power, fed by a USB power supply or a power bank, and it has to run for several days in a row.
- The boxes connect to an IoT Wi-Fi in the lab, which will be set up.
- A central web dashboard in the cloud (for example on Uberspace) where the boxes register, with live monitoring and all data recorded and available for analysis.

## Overview

```
 Box (one of many)                         Server (Uberspace)                 Users
 ┌───────────────────────────┐   HTTPS    ┌──────────────────────────┐      ┌───────────┐
 │ ESP32 Brick, own firmware │  batches   │ ingest API               │      │ dashboard │
 │  Analog In ← Atlas board  │ ─────────► │ registration + approval  │ ◄──► │ live view │
 │  Thermocouple ← K probe   │  of raw    │ database (raw readings)  │      │ export    │
 │  OLED 128x64 (display)    │  readings  │ calibration, pH compute  │      │ API       │
 │  flash buffer when offline│ ◄───────── │ config for each box      │      └───────────┘
 └───────────────────────────┘ calibration└──────────────────────────┘
         ▲ USB-C power (supply or power bank)
```

The box is a measuring node and the server holds the data, the dashboard and the calibration. The box serves no monitoring web page of its own, because a central dashboard covers all boxes and a box that does not have to keep a web server ready can save power.

## 1. The box

### Hardware

| Part | Port | Note |
|---|---|---|
| ESP32 Brick | – | six Bricklet ports, three in use |
| Analog In Bricklet 3.0 | 1 | reads the Atlas analog pH board |
| Thermocouple Bricklet 2.0 | 1 | type K probe |
| OLED 128x64 Bricklet | 1 | display only; Nicolas has several |
| USB-C port in the enclosure wall | – | panel-mount extension to the Brick's own USB-C jack |

According to the [ESP32 Brick page](https://www.tinkerforge.com/en/doc/Hardware/Bricks/ESP32_Brick.html) the Brick can be powered through its USB-C jack, so the box needs no power electronics of its own and no built-in battery; a power bank plays that role.

### Power and runtime

Sources: the ESP32 Brick draws 740 mW with Wi-Fi and 420 mW with Wi-Fi switched off ([Tinkerforge](https://www.tinkerforge.com/en/doc/Hardware/Bricks/ESP32_Brick.html), via a search summary, to be checked on the page); the Analog In Bricklet 3.0 draws about 70 mW; the Atlas board 3 mA, about 15 mW at 5 V. The draw of the Thermocouple and OLED Bricklets was not looked up yet.

| Operating mode | Assumed total (calculation, Bricklets 0.15 to 0.25 W) | Runtime with a 20,000 mAh power bank (calculation, about 50 Wh usable at 5 V) |
|---|---|---|
| Wi-Fi always on | about 0.9 to 1.0 W | about 2 days |
| Wi-Fi only for uploads, otherwise off | about 0.6 to 0.7 W | about 3 days |

The usable energy of a power bank is lower than its printed capacity, because the capacity refers to the cell voltage of about 3.7 V and the conversion to 5 V costs further energy; the 50 Wh are an **assumption** for a typical 20,000 mAh bank. "Several days" is therefore reachable with a large power bank, but only with a firmware that keeps the radio off most of the time. Two practical risks follow **(inference)**: many power banks switch off when the current stays below a threshold, which the box must not undercut, and the real consumption has to be measured before the enclosure and the power bank are chosen.

### Firmware

A module in the Tinkerforge ESP32 firmware (LGPL 2.1), because Wi-Fi setup, network updates and NTP time already exist there and updates over the network matter for many boxes.

| Task | Proposal |
|---|---|
| Sampling | read voltage and temperature every second (Analog In oversampling on), store one averaged record every 10 s; the interval is a setting from the server |
| Display | pH, temperature, Wi-Fi state, upload backlog, box name; pH computed locally with the calibration copy received from the server |
| Buffer | records go to a ring buffer in flash first and are deleted only after the server has confirmed them, so a Wi-Fi outage leaves no gap |
| Upload | every 60 s a batch over HTTPS, radio off in between; the interval is a setting from the server |
| Identity | the Brick's UID; after approval the server issues a token that the box sends with every upload |
| Setup | Wi-Fi credentials and server address through the setup page that the firmware already has |

How much the radio can really be switched off without breaking NTP, updates and the setup page is a question for the firmware work.

## 2. Transport

HTTPS with JSON batches from the box to the server. MQTT was considered, but on Uberspace an application is reached through the web frontend, which terminates HTTPS and forwards to the application's port ([Uberspace 8 web backends](https://u8manual.uberspace.de/web_backends/)); HTTPS therefore needs no extra port and usually passes through restrictive networks, whereas a broker would need a separate port. (The Uberspace 7 manual named a quota of 20 extra TCP ports; whether Uberspace 8 offers them was not checked.)

One requirement on the lab network follows from this: the IoT Wi-Fi must allow outbound HTTPS to the internet, which has to be confirmed with the IT department, because IoT networks are sometimes isolated.

Sketch of one batch (proposal):

```json
{
  "box": "227Z",
  "firmware": "0.1.0",
  "records": [
    {"t": "2026-10-28T09:26:30Z", "mv": 1165.7, "temp_c": 22.19, "n": 10},
    {"t": "2026-10-28T09:26:40Z", "mv": 1165.5, "temp_c": 22.20, "n": 10}
  ]
}
```

## 3. The server

A web application that runs as a [web backend on Uberspace 8](https://u8manual.uberspace.de/web_backends/) on the shared Asteroid `hsos`, under its own subdomain: the application listens on a port, Uberspace terminates HTTPS and forwards the requests, and idle connections are closed after three minutes, so the live view (server-sent events) sends a keep-alive every 30 s. The setup is described in `07-deployment-uberspace.md`.

| Part | Task |
|---|---|
| Ingest API | accepts batches, checks the token, stores raw records, confirms them to the box |
| Registration | an unknown box appears as "pending"; a person approves it and gives it a name and a location |
| Calibration | records calibration events for each box and probe and computes pH from the raw values |
| Dashboard | overview of all boxes with live values, history per box, state (last contact, backlog, power) |
| Export and API | CSV and JSON for any time range, open read API |

The same application should also run outside Uberspace (a lab PC or a Raspberry Pi), so that other labs can host it themselves; this fits the open-source goal. The language and the database are still open; Python fits the earlier prototype, and the database depends on what the host offers.

## 4. Raw data are the truth

The box sends voltage and temperature, not pH. The server stores these raw values for good and computes pH with the calibration that was valid at the time. If a calibration later turns out to be wrong, a whole series can be recomputed. The box receives a copy of its current calibration only to show a pH value on its display.

Per calibration event: box, probe, time, buffer values, buffer temperatures, measured voltages, resulting slope and offset.

## 5. Enclosure requirements

- Room for the ESP32 Brick, three Bricklets, the Atlas board and short cables; dimensions from the Tinkerforge CAD data or measured.
- A window for the OLED, a panel-mount USB-C socket, a feed-through for the pH probe (SMA or BNC, to be confirmed) and one for the thermocouple plug.
- The pH input is very sensitive to moisture and dirt, so the enclosure should be closed and drip-protected **(inference)**.
- Plastic around the Wi-Fi antenna, ventilation if the electronics warm up, and the Thermocouple Bricklet away from warm parts, because its cold-junction sensor sits on its own board.
- No battery inside; the power bank stays outside or in a separate holder.
- Parametric source files, printable without supports.

## 6. Phases

| Phase | Content | State |
|---|---|---|
| 0 | Bench test with a Master Brick on USB and Python scripts: noise, calibration, temperature, interference | readout works (`05-bench-log.md`); calibration waits for buffers |
| 1 | Server skeleton (ingest, registration, simple dashboard) and a box firmware that uploads raw readings | server runs locally (`server/`, protocol in `06-box-protocol.md`), fed by `tools/bench_box.py` with real readings; firmware and Uberspace deployment not started |
| 2 | Power measurement, radio-off operation, display, enclosure | not started |
| 3 | Calibration workflow in the dashboard, export, documentation for rebuilders | not started |

## 7. Open points

- How the ESP32 Brick is reached over the network for the first firmware tests; over USB, `brickd` did not list it on 2026-10-28.
- The real power consumption of the complete box, and whether common power banks keep it powered.
- Whether the pH probe and the thermocouple disturb each other in a well-conducting solution; in tap water there was no measurable effect (`05-bench-log.md`).
- How long the electrode needs to settle after it is moved; in the water test it was still drifting by 4 mV per minute after nine minutes, which the firmware and the calibration workflow have to take into account (for example a stability criterion before a calibration point is accepted).
- Whether the IoT Wi-Fi allows outbound HTTPS.
- Access to the Uberspace Asteroid `hsos`, which Nicolas has not handed over yet.
