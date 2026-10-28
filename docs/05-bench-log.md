# Bench log

Measurements on the bench setup, newest last. Scripts are in `tools/`.

## 2026-10-28: first readout

Setup: Master Brick (firmware 2.5.2) on USB, served by Brick Daemon 2.4.8 on `localhost:4223`; Thermocouple Bricklet 2.0 (port C, UID `2f9u`, firmware 2.0.2) with a K probe; Analog In Bricklet 3.0 (port D, UID `27eC`, firmware 2.0.3) wired to the Atlas Surveyor pH Meter V3.0 with the Atlas probe attached. The state of the probe during the run is not recorded (storage tube or buffer, to be noted from the next run on). The ESP32 Brick on USB was not reachable (see `02-architecture.md`).

Command: `python tools/read_sensors.py --count 20 --interval 1`, read-only.

| Quantity | Result |
|---|---|
| Thermocouple configuration (factory state, unchanged) | type K, averaging 16, 50 Hz filter, no open-circuit or range error |
| Analog In configuration (unchanged) | oversampling index 7, which is 4096x, calibration offset 0, multiplier 1, divisor 1 |
| Board voltage, 20 samples over 20 s | mean 1165.7 mV, standard deviation 0.81 mV, range 1165 to 1167 mV |
| Temperature, same samples | mean 22.19 °C, standard deviation 0.038 °C |

What this shows and what it does not:

- Both Bricklets and the board deliver stable values. The voltage noise of 0.8 mV corresponds to about 0.004 pH at 195 mV per pH (calculation), which is far below the vendor accuracy of ±0.2 pH.
- Applying the nominal mapping of the datasheet (3.000 V at pH 0, 0.265 V at pH 14, linear) to 1165.7 mV gives pH 9.4 (calculation). Whether that is plausible depends on what the probe was sitting in, which is not known, and the datasheet notes that the output is unpredictable without a probe. The value therefore proves nothing about the pH yet; a calibration with buffers is the next step.
- The temperature of 22.2 °C is plausible for room temperature. No comparison with a reference thermometer has been made, so the accuracy question of `01-components.md`, section 5, is still open.
- The drift over minutes or hours has not been measured.
