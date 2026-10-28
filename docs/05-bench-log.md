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

## 2026-10-28: does the thermocouple disturb the pH reading? (water test)

Question: when the K probe and the pH electrode sit in the same liquid, both are connected to the same Brick ground, so a current could flow through the liquid and shift the high-impedance pH signal (`01-components.md`, section 5).

Setup as above, one glass of tap water. Raw data: `data/bench/2026-10-28-water-test.csv` (600 samples, one per second, 09:50:44 to 10:00:47 UTC). Procedure, times from Nicolas' messages and the temperature curve:

| Time (UTC) | Step |
|---|---|
| about 09:52:00 | pH electrode taken from its storage tube, rinsed, put into the water; the K probe was briefly dipped in and taken out again at the same time |
| 09:55:30 | K probe into the same glass, not touching the electrode |
| 09:58:03 | K probe out again, electrode stays in |

Evaluation with `python tools/step_analysis.py data/bench/2026-10-28-water-test.csv 09:55:30 09:58:03`, which fits a straight line to 60 s before and after each event and compares both lines at the event:

| Event | Step | Drift before / after | Residual sd |
|---|---|---|---|
| probe in, 09:55:30 | −0.2 mV (−0.001 pH) | 14.7 / 10.3 mV/min | 0.67 / 0.65 mV |
| probe out, 09:58:03 | −0.2 mV (−0.001 pH) | 7.4 / 6.0 mV/min | 0.55 / 0.64 mV |

Findings:

- **No interference measurable.** Inserting and removing the K probe shifted the voltage by 0.2 mV in both cases, which is below the noise of about 0.6 mV; at 195 mV per pH this is 0.001 pH (calculation). The probe used here does not disturb the pH reading in tap water.
- During handling single samples jumped by about 10 mV for one second (09:55:29: 1320 mV between 1331 values; 09:58:00: 1359 mV between 1355 values), probably from touching the setup. A median filter over a few samples would remove such spikes.
- **The electrode settles slowly.** After the change from storage solution to water the voltage rose from about 1260 to 1366 mV within nine minutes, and the drift fell from 19 to 9 to 4 mV per minute, so it had not settled by the end. Readings taken in the first minutes after moving the electrode are not usable, and a calibration has to wait for a stable value (for example less than 1 mV per minute).
- Temperature: the water read about 20.6 °C with the probe in it.

Limits: tap water conducts far less than a buffer or many lab samples, so the test should be repeated in a buffer or salt solution; only one of the three K probes was used; and the final 1366 mV would correspond to pH 8.4 with the nominal mapping (calculation), which means nothing without calibration.
