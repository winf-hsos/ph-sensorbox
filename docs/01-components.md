# Component choices

Status: proposal, 2026-10-28. Nothing here is decided. The vendor facts come from the manufacturers' pages and datasheets as read on that date, partly through page summaries, so every number that drives an order should be checked against the original datasheet first. Statements marked **(inference)** or **(calculation)** are ours and not taken from a source.

## 1. What the probe demands

A pH glass electrode follows the Nernst equation with a slope of 59.16 mV per pH unit at 25 °C, so a full range of pH 0 to 14 spans about ±414 mV around 0 V. The source impedance of the glass membrane lies between 10 MΩ and 1 GΩ (the datasheet of one lab electrode names a membrane resistance below 250 MΩ), and the measurement circuit therefore has to draw almost no current from it.

| Target accuracy | Allowed error at the probe | Step size needed (≤ ⅓ of the tolerance) | Effective resolution over 828 mV |
|---|---|---|---|
| ±0.02 pH | 1.18 mV | about 0.36 mV | about 11 bit |
| ±0.01 pH | 0.59 mV | about 0.18 mV | about 12 bit |

All rows in this table are a **calculation**. Two further effects belong to the same budget: the slope changes by 0.198 mV per kelvin and pH unit away from pH 7, so one kelvin of temperature error costs about 0.010 pH at pH 4 (calculation), and a standard buffer with a tolerance of ±0.01 pH already uses up the entire budget of a ±0.01 pH claim.

## 2. Why the electrode cannot go straight into a Bricklet

| Bricklet | Range and resolution | Input impedance | Verdict |
|---|---|---|---|
| [Analog In 3.0](https://www.tinkerforge.com/en/doc/Hardware/Bricklets/Analog_In_V3.html) | 0 to 42 V, 12 bit, "~10mV" | not stated | The range is unipolar and one step equals about 0.17 pH at the probe (calculation). |
| [Industrial Dual Analog In](https://www.tinkerforge.com/en/doc/Hardware/Bricklets/Industrial_Dual_Analog_In_V2.html) | ±35 V, 24 bit, accuracy "0.1% / ±4mV full scale" | not stated | The range fits, but an unstated impedance on a ±35 V input is very unlikely to suffice for a gigaohm source **(inference)**. |

Tinkerforge sells no pH or potentiostat Bricklet; the shop list of 75 Bricklets was checked for this. A high-impedance buffer between the electrode and the Bricklet is therefore mandatory, and the question is only whose buffer to use.

## 3. Options for the pH front end

| Option | Output | Accuracy by the vendor | Open | Fit with Tinkerforge |
|---|---|---|---|---|
| **A. Atlas EZO-pH circuit** on an isolated carrier board ([circuit](https://www.atlas-scientific.com/circuits/ezo-ph-circuit/), [carrier](https://atlas-scientific.com/carrier-boards/electrically-isolated-ezo-carrier-board/)) | UART or I2C, ASCII | ±0.002 pH for the circuit alone, electrode not included | no, the datasheet is marked "patent protected"; only the host libraries are on GitHub | UART via the RS232 Bricklet 2.0 is compatible on paper; no practical report found |
| **B. Own electrometer stage** (LMP7721, ADA4530-1 or the pH front end LMP91200) read by the Industrial Dual Analog In | bipolar analog voltage | depends on our design | yes, if we publish the board | works, but needs a PCB design and an amplification stage |
| C. Gravity analog modules (DFRobot SEN0161-V2, Atlas Gravity) | 0 to 3 V, about 195 mV per pH | ±0.1 pH (DFRobot), ±0.2 pH (Atlas) | no | Usable for ±0.1 to ±0.2 pH and in use as the bench setup since 2026-10-28 (see below). Not suited for ±0.02 pH, because even a ±4 mV reading gives only ±0.023 pH at best (calculation) and the vendor tolerance is larger still. |
| D. Electrode directly at a Bricklet | | | | Rejected, see section 2. |

Option A details that matter for the box:

- The EZO takes 3.3 to 5.5 V and draws about 14.5 mA at 3.3 V (source: Atlas datasheet V4.5, a 2018 copy, so re-check).
- The default is UART at 9600 baud with one reading per second; I2C at address 0x63 is also available. There is no I2C Bricklet, so UART through the [RS232 Bricklet 2.0](https://www.tinkerforge.com/en/doc/Hardware/Bricklets/RS232_V2.html) is the only way to attach it without custom firmware.
- That Bricklet offers a 3.3 V TTL pin header (RX, TX, 3.3 V, GND) next to the RS232-level connectors; only the pin header may be used, and the jumper between RX1 and RX2 has to be removed. The current the 3.3 V pin can supply is not documented, so the EZO and its carrier may need their own supply.
- Temperature compensation is set by a command, so the temperature has to come from outside, which suits the thermocouple (section 5).
- The circuit does one-, two- and three-point calibration (vendor page); where the calibration is stored is still to be verified.
- The EZO is not isolated by itself. Atlas recommends isolation near pumps and valves, and the carrier board provides isolated power and data. The Tinkerforge Isolator Bricklet (19.99 EUR) isolates a Bricklet from the Brick and would be an alternative **(inference: one of the two is enough)**.

### Bench setup in use (since 2026-10-28)

Nicolas builds the first prototype with an Atlas Scientific Surveyor pH Meter V3.0 (analog board with an SMA input and three pins marked −, + and A) wired to the Analog In Bricklet 3.0 on the ESP32 Brick, with the Thermocouple Bricklet for temperature; this follows a photo of the setup. The facts below come from the datasheet V2.4 of the Atlas analog pH circuit, as found for the Gravity/Surveyor analog family, and whether it covers this V3.0 board revision is **not verified**:

- The output falls from 3.00 V at pH 0 to 0.265 V at pH 14, which is about 195 mV per pH unit (calculated from the two end points; the first research report gave 177 mV per pH, which does not fit its own end points) with a tolerance of ±15 mV in the datasheet table, so the voltage decreases when the pH rises. A calibration with buffers will measure the real slope.
- The supply is 3.3 to 5.5 V at 3 mA, the accuracy is stated as ±0.2 pH, there is no isolation and no temperature compensation, and the output is unpredictable while no probe is connected.

Consequences (calculation): one Bricklet step of about 10 mV corresponds to about 0.05 pH, which is below the vendor's ±0.2 pH, so the Bricklet is not the limiting part at this accuracy and the setup is a sensible way to start. The conversion from voltage to pH, the calibration and the temperature compensation then have to be done in our own software: a linear fit of voltage against pH from two or three buffers, and a slope that is scaled with the absolute temperature taken from the thermocouple (Nernst). This suits the open-data goal, because the raw voltage stays available next to the pH value. The Analog In Bricklet has a built-in oversampling setting from 32x to 16384x (moving average, confirmed in the Python bindings), and a first bench measurement at 4096x gave a standard deviation of 0.8 mV, which is about 0.004 pH.

Points to settle with this setup: the supply pin used on the Bricklet (5 V or 3.3 V) and the common ground, which the photo does not show clearly; the missing isolation, which makes the thermocouple coupling test of section 5 more important (Atlas sells a separate analog isolator for this case); and the electrode, which has to match the SMA input.

Upgrade paths, in order of effort: reading the same Atlas board with the Industrial Dual Analog In (40 EUR, 24 bit) for a finer reading, replacing the board by the EZO-pH on the RS232 Bricklet (option A) for the vendor's ±0.002 pH at the circuit, or an own electrometer stage (option B).

**Proposed route:** continue with the bench setup, develop the software side (calibration, temperature compensation, record format) against it, and decide on an upgrade once the target accuracy is fixed. Which accuracy the project aims at, and whether the closed Atlas circuits are open enough for the project, are questions for Nicolas (see `04-open-questions.md`).

## 4. Electrode

An electrode with a BNC plug fits all options. Prices found on 2026-10-28:

| Electrode | Temperature sensor | Price |
|---|---|---|
| Atlas Lab Grade pH probe, BNC with adapter ([RobotShop](https://www.robotshop.com/products/atlas-scientific-lab-grade-ph-probe-includes-sma-to-bnc-adapter)) | not mentioned | 86.99 USD or 95.69 EUR (on order) |
| Hanna HI-1131B, glass body ([Hanna UK](https://www.hannainstruments.co.uk/electrodes-and-probes/57-ph-electrode-glass-body-general-purpose-for-laboratory)) | no | 232.68 GBP gross |
| Mettler Toledo InLab Expert Pro, 120 mm ([Buddeberg](https://shop.buddeberg.de/analytical-measurement-and-testing/ph-measurement/ph-electrodes/ph-electrode-inlab-expert/info9523_lang_uk.htm)) | NTC 30 kΩ with separate RCA plug | 433.16 EUR gross |
| Sentek P11 with Pt100 ([Deploy UK](https://shopping.deploy.co.uk/product/sentek-ph-electrode-pi11pt1005mcfe-yEzgJZgc)) | Pt100 | 237.50 GBP |

Pt1000/Pt100 or NTC electrodes are not needed when the temperature comes from the thermocouple. The electrode is the largest single cost of the box and the choice between a lab-grade and a budget electrode is tied to the accuracy target.

## 5. Temperature: Thermocouple Bricklet 2.0 (already owned)

Nicolas already has a [Thermocouple Bricklet 2.0](https://www.tinkerforge.com/en/doc/Hardware/Bricklets/Thermocouple_V2.html) in a clear case and three probes from B+B Thermo-Technik with the article number K-M625 0100-30 (seen on a photo from 2026-10-28). The Bricklet covers the types B, E, J, K, N, R, S and T with a resolution of 0.01 °C, and its accuracy is stated as "±0.15% (full-scale), ±0.7°C (cold-junction)" (the Industrial PTC Bricklet, 27.99 EUR, is therefore not needed).

Points to verify before relying on it:

- **Probe type.** The "K" in the article number suggests type K **(inference)**; the type has to be set on the Bricklet to match.
- **Accuracy.** If the ±0.15 % of full scale is meant over the whole type K span of roughly 1580 K, the absolute error would be about 2.4 K, which equals about 0.024 pH at pH 4 **(calculation under that assumption)**. That is irrelevant for ±0.1 pH and relevant for ±0.01 pH, so the first test is a comparison against a reference thermometer, with a software offset if needed.
- **Electrical coupling.** A conductive probe sheath in the same solution as the electrode can inject noise into the high-impedance pH signal when the thermocouple junction is grounded **(inference)**. The isolated carrier board should break the loop, and a measurement in buffer solution with and without the thermocouple will show it.
- **Chemistry.** The sheath material is unknown; for acidic or salty samples it has to be checked, and a coated or glass-sheathed probe may be necessary.
- **Cold junction.** The Bricklet's cold-junction sensor sits on its board, so the Bricklet should be kept away from heat sources inside the box.

## 6. Calibration and buffers

Calibration with two or three buffers (pH 4.01, 7.00 and 10.01) is proposed, and the box should record every calibration event as data (time, buffers, temperature, slope, offset) next to the measurements so that the history stays traceable. Whoever wants to claim ±0.01 pH needs certified buffers that are traceable to NIST or PTB with a batch certificate; the Merck set 1.99006 is advertised this way ([Merck](https://www.merckmillipore.com/IL/en/product/mm/199006), summary only, price not retrieved). The Hanna HI-7010 buffer at pH 10.01 costs 41.19 EUR gross per litre ([RS](https://de.rs-online.com/web/p/pufferlosungen/2384524)).

## 7. Not verified

- Input impedance and accuracy of the Analog In 3.0, and the input impedance of the Industrial Dual Analog In (could be asked of Tinkerforge).
- Whether the EZO works on the RS232 Bricklet in practice, including the current on its 3.3 V pin and the logic level of the carrier board.
- Where the EZO stores its calibration, and whether it can output the raw electrode voltage.
- Whether the Industrial Dual Analog In versions 2.0 (documentation) and 2.1 (shop) are technically identical.
- The ADA4177 and the Mikroe pH 2 Click were not examined.
