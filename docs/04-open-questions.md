# Open questions

Status: 2026-10-28.

## Decisions that only the project owner can make

1. **Target accuracy.** The choice between ±0.1 pH, ±0.02 pH and ±0.01 pH decides the front end, the electrode and above all the buffers, because ±0.01 pH needs certified, traceable buffers and a temperature error below about 0.5 K. Proposal: aim at ±0.02 pH and test how far the prototype gets.
2. **How open the components must be.** The recommended front end, the Atlas EZO-pH, is a closed circuit (its datasheet is marked "patent protected") that is sold as a standard component with a documented command set. If this is not acceptable, the open electrometer stage has to be designed, which costs time. Proposal: prototype with the EZO, develop the open board afterwards.
3. **Pilot laboratory.** Which laboratory or course serves as the first user decides the required accuracy, the sample types (which affect the thermocouple sheath) and the network (Wi-Fi or Ethernet).
4. **Licences.** Hardware and enclosure (for example CERN-OHL, which the reef-pi board uses), software, and documentation. A module inside the Tinkerforge firmware inherits the LGPL 2.1 for that code, and the licence of the Tinkerforge microcontroller bindings is still unknown.
5. **Budget and ordering.** The first bill of materials is in `03-bill-of-materials.md`; the electrode choice spans 96 to 433 EUR. No cost centre exists yet for the project.
6. **Electrode.** Which electrode is available already, and whether a lab-grade electrode may be bought for the prototype.

## Technical points to settle by experiment

1. Does the EZO work on the RS232 Bricklet, including the 3.3 V supply from the pin header and the logic level of the isolated carrier board?
2. Is the thermocouple accurate enough (comparison with a reference thermometer), and does a grounded thermocouple tip disturb the pH reading?
3. Can the Python bindings talk to the ESP32 Brick on TCP port 4223, and does that port need authentication?
4. Where does the EZO keep its calibration, and can it report raw electrode voltage?
5. How many readings fit into the Brick's file system in practice, and can the partition table be changed?

## Facts to look up

- Input impedance of the Tinkerforge analog Bricklets (a question to Tinkerforge).
- Licences of the Tinkerforge microcontroller bindings and of the Brick hardware files.
- Type, insulation and sheath material of the B+B K-M625 0100-30 probe (manufacturer data).
