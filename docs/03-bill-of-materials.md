# Bill of materials, first draft

Status: proposal, 2026-10-28. The bench setup in use is an Atlas Surveyor analog pH board on the Analog In Bricklet 3.0 with the thermocouple for temperature (parts owned according to Nicolas' photos); the table below lists that setup first and the EZO-pH route as an upgrade.

## Bench setup in use

| Item | Qty | Price | Status |
|---|---|---|---|
| Tinkerforge ESP32 Brick (assumed from the photo, to confirm) | 1 | 44.99 EUR | owned |
| Tinkerforge Analog In Bricklet 3.0 | 1 | 13.99 EUR | owned |
| Tinkerforge Thermocouple Bricklet 2.0 | 1 | 27.99 EUR | owned |
| Thermocouple probe, B+B K-M625 0100-30 | 3 | – | owned |
| Atlas Scientific Surveyor pH Meter V3.0 (analog) | 1 | not researched for V3.0; the Gravity analog module was listed at 28.99 USD and the kit with probe at 69.99 USD | owned |
| Atlas Scientific pH probe in its storage tube (photo of 2026-10-28; exact model and connector not identified) | 1 | the Atlas lab-grade probe was listed at 86.99 USD or 95.69 EUR | owned; model, membrane type and storage solution to confirm |
| Buffer solutions pH 4.01, 7.00, 10.01 | 1 set | pH 10.01, 1 L: 41.19 EUR; the other two not priced | to buy or from stock |

## Upgrade: EZO-pH route Prices are list prices of 2026-10-28 including 19 % VAT where the vendor shows it (Tinkerforge, RS, RobotShop EU) and are kept in the currency of the source. Nothing has been ordered. Shop pages carry no date of their own, so prices have to be re-checked at the time of ordering.

## Prototype

| Item | Qty | Price | Source | Status |
|---|---|---|---|---|
| Tinkerforge ESP32 Brick | 1 | 44.99 EUR | [shop](https://shop.tinkerforge.com/en/esp32-brick.html) | to buy |
| Tinkerforge RS232 Bricklet 2.0 | 1 | 21.99 EUR | [shop](https://shop.tinkerforge.com/en/bricklets/rs232-v2-bricklet.html) | to buy |
| Tinkerforge Thermocouple Bricklet 2.0 | 1 | 27.99 EUR | [shop list](https://shop.tinkerforge.com/en/bricklets.html) | owned |
| Thermocouple probe, B+B K-M625 0100-30 | 3 | – | photo of the packaging | owned |
| Bricklet cables 7p-7p | 2 to 3 | 0.69 to 3.59 EUR each | Tinkerforge product pages | to buy, length depends on the enclosure |
| Atlas EZO-pH circuit | 1 | 45.99 USD | [Atlas](https://www.atlas-scientific.com/circuits/ezo-ph-circuit/) | to buy |
| Atlas electrically isolated EZO carrier board | 1 | 41.99 USD | [Atlas](https://atlas-scientific.com/carrier-boards/electrically-isolated-ezo-carrier-board/) | to buy |
| pH electrode with BNC, lab grade | 1 | 95.69 EUR (Atlas) up to 433.16 EUR (Mettler InLab Expert Pro) | see `01-components.md`, section 4 | to decide |
| Buffer solutions pH 4.01, 7.00, 10.01 | 1 set | pH 10.01, 1 L: 41.19 EUR; the other two not priced | [RS](https://de.rs-online.com/web/p/pufferlosungen/2384524) | to buy |
| BNC bulkhead socket and short cable | 1 | not researched | | to find |
| USB cable for the Brick, USB power supply | 1 | USB cable 5.99 to 6.99 EUR as option | shop | to buy or from stock |
| 3D printed enclosure, screws | 1 | printing material | own printer | to design |

Rough sum of the priced items still to buy, with the cheapest electrode: 162.67 EUR (Brick, RS232 Bricklet, Atlas electrode) plus 87.98 USD (EZO and carrier), plus cables, buffers, BNC parts and the enclosure. Currencies are deliberately not converted.

## Optional

| Item | Price | Why |
|---|---|---|
| Tinkerforge Isolator Bricklet | 19.99 EUR | alternative or addition to the isolated carrier board |
| Tinkerforge ESP32 Ethernet Brick instead of the ESP32 Brick | 59.99 EUR | wired network in the lab |
| Tinkerforge case for Bricklets | 5.99 EUR each | protection during the bench phase |
| Tinkerforge Industrial Dual Analog In | 40.00 EUR | only for the open front end (option B) |
| Industrial PTC Bricklet | 27.99 EUR | dropped, because the thermocouple is available |

## Not covered

The open front end (option B) needs its own board with an electrometer amplifier; its parts were not priced. The same applies to a possible SD card, to panel connectors and to calibration equipment such as a reference thermometer.
