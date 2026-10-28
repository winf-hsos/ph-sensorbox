# pH Sensor Box

An open-source device for professional pH measurement in the lab. A 3D-printed enclosure holds a Tinkerforge ESP32 Brick with an Analog In Bricklet that reads a pH probe. The box measures, stores and serves its data over the network without a computer running next to it.

Commercial lab pH meters are expensive and give only limited access to their data, usually through vendor software or fixed export formats. This project aims for an alternative that can be rebuilt from standard parts and gives open access to every measurement and its metadata.

## Status

Planning. Nothing is built yet; the open questions (probe and amplifier, resolution, temperature compensation, calibration, data access) are worked out in `docs/`.

## Layout

| Folder | Content |
|---|---|
| `docs/` | Concept, component choices, architecture |

Firmware, software and enclosure files follow once the design is settled.

## License

Not decided yet.
