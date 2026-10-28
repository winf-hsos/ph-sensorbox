# Architecture

Status: proposal, 2026-10-28. It follows the bench setup in `01-components.md` (Atlas Surveyor analog pH board on the Analog In Bricklet 3.0, Thermocouple Bricklet for temperature). In this setup the Brick reads two voltages and the software computes the pH, whereas an EZO-pH upgrade would move that computation into the EZO and add the RS232 Bricklet; the design has to be revisited if the front end changes.

## 1. What the ESP32 Brick can do

According to the [ESP32 Brick page](https://www.tinkerforge.com/en/doc/Hardware/Bricks/ESP32_Brick.html), the Brick has six Bricklet ports, 16 MB of flash and Wi-Fi, and its standard firmware is a network gateway for the Bricklets with a web interface that manages only the network settings. The same page states that custom code can run directly on the Brick, alongside the standard firmware if desired. The standard firmware contains no data logging; it keeps its configuration in a small LittleFS partition of about 3.4 MiB (partition table in the [firmware repository](https://github.com/Tinkerforge/esp32-firmware)).

The firmware is open source under the LGPL 2.1 (`software/LICENSE` in that repository), built with PlatformIO and, for the web frontend, Node.js and `uv`. It can be extended with its own modules, as the [tutorial](https://www.tinkerforge.com/en/doc/Tutorials/Tutorial_ESP32_Firmware/Tutorial.html) shows with a polled Bricklet. For standalone code there are also the [microcontroller bindings](https://www.tinkerforge.com/en/doc/Software/API_Bindings_uC.html) for Arduino. The licence of those bindings and of the Brick hardware files was not found and has to be looked up before a licence is chosen for this project.

## 2. Proposed approach in three phases

**Phase 0, bench test without own firmware.** The bench host is a Master Brick on USB, which the Brick Daemon on the laptop serves on `localhost:4223`, so a Python script reads the Bricklets without any network setup. An ESP32 Brick with its standard firmware would serve the same bindings over Wi-Fi or Ethernet, but a first attempt on 2026-10-28 found no way to reach it over USB: `brickd` did not list it and its serial port was silent. The source code of the firmware opens TCP port 4223 for this (`proxy.cpp`), whereas no documentation page was found that confirms it, so this is the first thing to try. The phase answers the open hardware questions: how large the noise and drift of the analog pH voltage are, what the thermocouple delivers, whether the thermocouple disturbs the pH signal, and how well a two- or three-point calibration with buffers holds. The calibration and compensation code is first written in Python here and later ported to the firmware. The old prototype in `ph-sensor-dashboard` took the same route, but only read a voltage.

**Phase 1, own module on the Brick.** The measurement runs on the Brick without a computer. A module in the Tinkerforge firmware reads the EZO and the thermocouple, sends the temperature to the EZO for compensation, stores the readings and serves them. The module route gives Wi-Fi setup, firmware update over the network and NTP time for free, at the price of the large build chain and the LGPL; the lighter alternative is an Arduino sketch, which would require writing the network setup, update and web server ourselves. We propose the module route and flag the licence consequence in the open questions.

**Phase 2, open front end and polish.** Option B of the component proposal (own electrometer stage) as an alternative board, the enclosure design and documentation for rebuilders.

## 3. Software on the Brick (phase 1)

| Part | Task |
|---|---|
| Sampling loop | Read the voltage of the pH board from the Analog In Bricklet and the temperature from the thermocouple once per second, average, and compute the pH. With an EZO upgrade, read the pH from the EZO instead and send it the temperature. |
| Calibration | Two- or three-point calibration controlled from the web interface (a linear fit of voltage against pH, slope scaled with the absolute temperature), with each event written to the log. |
| Log | Records of time (UTC from NTP), pH, temperature, plus metadata of the active probe and calibration. |
| Web interface | Live value, short history, calibration, download. German and English. |
| API | Read-only JSON endpoints for the current reading, a time range of the log (JSON or CSV) and the metadata; optional push to an MQTT broker or an HTTP address in the lab. |

The endpoints are a proposal and do not exist yet. The MQTT modules in the Tinkerforge repository belong to the charger products, and whether they can be reused for the Brick was not checked.

### Storage

The standard partition for files is about 3.4 MiB. With a compact record of 32 bytes this holds roughly 110,000 readings, which means about 31 hours at one reading per second or about 13 days at one reading per ten seconds (calculation, ignoring filesystem overhead and wear). Three ways to extend this are possible, none of them verified: a custom partition table that gives the file system more of the 16 MB flash, a SD card if the Brick can drive one, and a push of the data to a lab server. The design should therefore keep the box usable on its own for days and make the long-term archive a task of whatever receives the push.

## 4. Data access

The central promise of the project is open access, so the record format is part of the architecture. Proposed fields per reading: UTC time, pH, raw electrode-board voltage, temperature in °C, identifier of the active probe, identifier of the active calibration; and per calibration event: time, buffer values, buffer temperature, slope and offset. The same schema serves the CSV download and the JSON API, and the web interface only reads what the API serves. Authentication follows the firmware's own options (the proxy module accepts a secret); an unauthenticated port on a lab network is acceptable for tests only.

## 5. Enclosure requirements (3D printed)

- Space for the ESP32 Brick, the RS232 Bricklet, the Thermocouple Bricklet, the EZO with its carrier board and a short cable run; the dimensions still have to be taken from the data sheets or measured.
- A BNC socket in the wall for the electrode, with the wire to the EZO as short as possible. The input is extremely sensitive to moisture and dirt, so the enclosure should be closed and drip-protected, and the electrode leakage paths should be kept clean **(inference)**.
- A panel connector for the thermocouple probe, USB power inlet and a cut-out for status LEDs; plastic around the Wi-Fi antenna.
- Printable without supports on a standard printer, with the source files in a parametric format.

## 6. Why not other designs

A Raspberry Pi or server running the logger next to the Brick would be the quickest solution and is used in phase 0, but it contradicts the goal of a box that needs no computer. A pure ESP32 build without Tinkerforge parts (for example an ADS1115) was not examined; it would lose the tested Bricklets and drivers and is kept as a fallback.
