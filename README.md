# pH Sensor Box

An open-source device for professional pH measurement in the lab. A 3D-printed enclosure holds a Tinkerforge ESP32 Brick with an Analog In Bricklet that reads a pH probe. The box measures, stores and serves its data over the network without a computer running next to it.

Commercial lab pH meters are expensive and give only limited access to their data, usually through vendor software or fixed export formats. This project aims for an alternative that can be rebuilt from standard parts and gives open access to every measurement and its metadata.

## Status

Early development. The bench setup (Atlas analog pH board and thermocouple on Tinkerforge Bricklets) delivers readings, and a first version of the central server with registration, live dashboard, calibration and export runs locally. Firmware for the ESP32 Brick and the enclosure are not started yet.

## Layout

| Folder | Content |
|---|---|
| `docs/` | Concept, component choices, architecture, box protocol, bench log |
| `server/` | Central server: API, dashboard, calibration (Python, FastAPI, SQLite) |
| `tools/` | Bench scripts: list devices, read sensors, act as a box, analyse steps |
| `data/` | Raw data of bench tests |

Firmware and enclosure files follow.

## License

Not decided yet.
