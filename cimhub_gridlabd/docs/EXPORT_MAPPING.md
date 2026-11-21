# cim18v17 → GridLAB-D export spec

Plan and decisions: `.development/GLM_REWRITE_PLAN.md` §8 (X1-X9 and §8.5, the user's 2026-11-21). The exporter
reads values only through the core getters (skill `export-getters`) and asks each for the GLM slot's own unit
(`exporter/units.py`, X8). The `GlmModel` it returns has the shape `GlmReader.read_all()` returns, so `GlmWriter`'s
deck reads back through the reader and the importer, and GridLAB-D 6.0 solves it.

## Layout

```
cimhub_gridlabd/src/cimhub_gridlabd/
    glm_writer.py             GlmWriter: clock, #set, modules, then objects in WRITE_ORDER; values a+bj, TRUE/FALSE, "text"
    exporter/
        cim_to_glm.py         GlmExporter(FormatExporter).to_model(network, *, name_source, switch_state), EXPORT_ORDER,
                              cim_to_glm(network, destination, **opts); raises on equipment no module exports
        naming.py             Names: the shared name switch (X1) + glm_safe_name, one namespace per deck
        units.py              glm_unit(class, slot): the schema's unit as a pint unit; from_percent
        buses.py              node / triplex_node / substation, each bus's system and nominal_voltage
        line.py, line_catalog.py   lines and the conductors, spacings and configurations they name
        switch.py             switch, fuse, recloser, sectionalizer
        transformer.py        transformer + transformer_configuration: native, centre tap, wye-wye, star split, banks
        regulator.py          regulator + regulator_configuration
        load.py, capacitor.py, inverter.py
```

Each module has `CIM_CLASSES`, `SLOTS` (`{GLM class: {slot: Slot}}`, `cimhub_core.export_slots`) and
`export(context) -> list[record]`. `test_export_framework.py` checks that `SLOTS` names every schema slot and that the
tables at the end of this file are the generated ones.

## X0: framework, writer, buses and the swing

- **Deck header:** one power flow, a `clock` that starts and stops at one instant; `#set relax_naming_rules=1`;
  `module powerflow { solver_method NR; nominal_frequency f; line_capacitance TRUE; }`, f the network's base
  frequency (`line_capacitance`: CIM's line b is part of the model, and GridLAB-D ignores every `c` without it);
  `module generators` when the deck holds DER.
- **Names (X1):** `cimhub_core.names.export_name` (`name`, `mrid`, `uri`; default `mrid`), `glm_safe_name` (a `.`
  is GridLAB-D's `object.property`, `:` its `class:id`; whitespace, quotes, `;`, braces and `$` end a token), one
  namespace, a collision raises. GLM-origin models round-trip under `name_source="name"`.
- **Buses:** a ConnectivityNode is a `node`, a `triplex_node` on a split-phase bus, the swing's a `substation`. Its
  system is read per voltage zone (`cimtopology.core.Topology.voltage_zones`): s1/s2 split phase (the service letter
  from its centre taps' primary); the EnergySource, a polyphase transformer end, or one-phase ends on different phases
  (a bank) three phase; one-phase ends on one phase single phase. `nominal_voltage` is the BaseVoltage over √3, as
  is, or over 2. Phases: every terminal's A, B, C, then N (S for a triplex bus).
- **The swing (X6):** one EnergySource, `bustype SWING`, `nominal_voltage` its nominalVoltage/√3 (the importer's
  `line_voltage` inverted, so the deck's own figure comes back), `positive_sequence_voltage` voltageMagnitude/√3 at
  voltageAngle, `base_power` the graph's BasePower when it holds one (`network.base_power`'s 100 MVA default is not
  CIM's). GLM's swing is ideal: the source impedance is not written. Two EnergySources raise (NR takes one).

## X1: lines and switches

- A line is geometry when its WireConfiguration names a WireSpacing (`get_line_geometry`; skill
  `conductor-geometry`), whatever else it has. The WireConfiguration is the equivalence route: an XYSpacing and a
  ConductorDistanceSpacing may both lead to one configuration, and it may also carry the PerLengthImpedance its
  geometry equals. A geometry line is a `line_configuration` with `conductor_X` the wire at phase X's sequence number
  and a `line_spacing` with the distances and heights the spacing holds (`get_stored_distances`; a pair or height left out is GridLAB-D's 0). No
  impedance is computed from geometry. A split-phase line is a `triplex_line` whose configuration's `diameter` and
  `insulation_thickness` come from its spacing (S2-8 inverted). A geometry line with a cable is an `underground_line`.
- Otherwise its code (`get_line_code`: its own PerLengthImpedance, else its WireConfiguration's, a template LineCode;
  both set and different raise) is a matrix configuration by phase letter, a neutral Kron-reduced out, b as
  `c` = `c_from_b` at the base frequency (b unset: c unset, GridLAB-D's 0); a sequence code is expanded by the getter.
- A template used on different phases is one GLM object per use, `<template>_<letters>`.
- Conductors: `rAC50` (the GLM importer's), else `rAC25` (the DSS importer's). A bare wire buried in an underground
  configuration gets `outer_diameter` = 1.2 × its diameter (the Java exporter's rule; GridLAB-D needs one). A tape
  shield's `shield_gmr` = diameterOverScreen / 2 and `shield_resistance` = 18.826 / (d_s[in] × T[mil]) Ω/mile
  (Kersting eq. 4.89, the Java exporter's): GridLAB-D tells a tape-shield cable by `shield_gmr` > 0.
- Switches: Fuse `fuse` (`current_limit` = ratedCurrent), Recloser `recloser`, Sectionaliser `sectionalizer`, every
  other Switch `switch`; `status` from `switch_state` (`actual`: `open`, `normal`: `normalOpen`).
- Ratings: each link's own normal and emergency limits on its phases (D9); a triplex line's on its service
  letter, which GridLAB-D and the importer read.

## X2: transformers and regulators

Per unit (`get_transformer_units`), the model in pu on winding 1's ratedS:

| form | written as |
|---|---|
| Y/Yn/I to Y/Yn/I on one phase set | `WYE_WYE` (one coil `SINGLE_PHASE`) |
| D-D on three phases | `DELTA_DELTA` |
| D-Yn on three phases, phaseShift unset or -30 (Dyn1) | `DELTA_GWYE` |
| three windings on s1, s2, N | `SINGLE_PHASE_CENTER_TAPPED`, the star whole (`impedance`, `impedance1`, `impedance2`) |
| any other two windings (X3, the user's rule) | `WYE_WYE` on both windings' phases, logged |
| three windings, not a centre tap (X4, the user's rule) | three legs to a 1 kV star bus `<unit>_star`; a D leg `DELTA_GWYE`, else `WYE_WYE` |
| single-phase cans with a phase-to-phase coil on the same buses (the user's rule) | one bank, then the rows above |
| one PowerTransformer's lugged cans under a TransformerBankConfiguration (the importer's bank, S3b-9) | one `WYE_WYE`, `powerX_rating` each can's, named by the bank configuration |

- GridLAB-D's base is `secondary_voltage²/power_rating` as written: polyphase units line to line on their whole kVA,
  a coil on its own; a two-phase wye's coil base is n/3 of GridLAB-D's. A bank's cans all get GridLAB-D's one
  impedance in the same ohms, so each can's own pu × S_total / (3 S_can) (the importer's k inverted) must agree.
- R ≤ 0 or X ≤ 0 is written at 1e-6 pu and logged (§8.5 Q2); a star's middle branch is often negative.
- An LTC is folded into its winding's voltage at the actual step; its control is not written (X5).
- Regulators: one per VoltageRegulator (GridLAB-D takes one-phase regulators side by side). Units the GLM importer
  split (`<base>_<phase>` on the same buses, S3c) are `<base>` again. A delta bank (coils between phases) is
  `WYE_WYE`, each coil's tap on its own phase: GridLAB-D 6.0 solves no delta regulator under NR. `Type` B on a
  `construction` typeB, else A (CIM's 1 + step × increment). `Control` MANUAL when disabled, else LINE_DROP_COMP or
  OUTPUT_VOLTAGE; a disabled control may have no target (core getter change, 2026-11-21). The compensator settings
  are written wherever CIM holds a line drop (GridLAB-D reads them on LINE_DROP_COMP only, the importer on any
  Control). Several units are `control_level` INDIVIDUAL; one VoltageRegulator alone (a gang on ABC, or one phase
  not named as the importer's split) is BANK, sensing `PT_phase`/`CT_phase` = the control's monitored phase (its
  first phase under MANUAL), which GridLAB-D and the importer read as one unit (GLM-7, S6).

## X3: loads and capacitors

- A load per EnergyConsumer, parented to its bus, in GLM's base_power form per phase (each ZIP part's |S|, fraction
  and power factor, negative when its Q is). Delta: A, B, C are the branches AB, BC, CA (as cimtables' branch
  children). A voltage-exponent model with exponents 0, 1 or 2 is constant power, current or impedance; another
  raises. On a split-phase bus a wye consumer is the legs `_1`/`_2`, a delta one the 240 V part `_12`; the
  importer's `<base>_12` consumer is its base's `_12` again (S4a-6).
- A capacitor per LinearShuntCompensator: `capacitor_X` at nomU with every section in, `switchX` from the actual
  sections, VOLT from an enabled voltage control (the target ± half the deadband, `pt_phase` the monitored phases,
  else the unit's own: a BANK capacitor senses one phase). A control of another mode is MANUAL at the actual state,
  logged. The importer's per-phase units `<base>_<phase>` are `<base>` again (S4a-8).

## X4: DER

- Each PowerElectronicsUnit is an inverter (several share their connection by maxP, `get_inverter_units`):
  `FOUR_QUADRANT`, `rated_power` per phase.
- A battery: `CONSTANT_PQ` at CIM's set point, `soc_reserve` minimumE / ratedE, `max_charge_rate` its
  StorageInverterInfo's chargeRateActiveMax (`get_inverter_datasheet`; `max_discharge_rate` has no CIM home, and both
  are read by LOAD_FOLLOWING only). Its `battery` is the internal model: capacity, state of charge, round-trip
  efficiency, `battery_type` from BatteryInfo (none: unset, GridLAB-D's UNKNOWN, as the deck it came from),
  `nominal_voltage` unset (the DCConductingAssetInfo TODO, plan §7).
- A PV: `CONSTANT_PF` at CIM's power factor, GridLAB-D's own PV logic (S4b-1). Its `solar` carries the datasheets
  (`get_photovoltaic_datasheet`: tilt, azimuth and shading from the SolarArrayInfo, efficiency and `Rated_Insolation`
  from the SolarPanelInfo), `rated_power` maxP, `soiling` and the inverter's efficiency 1, and `derating` the whole
  loss: CIM's p over GridLAB-D's lossless static-weather output at its defaults for what CIM does not hold (panel
  type, NOCT; the importer's `static_dc_output`). So GridLAB-D's output, and the re-import's p, is CIM's p, from any
  origin. A p above the lossless output raises (GridLAB-D's factors are at most 1).

## X5: tests

- `test_glm_writer.py`: value formats, one object's text, the deck order, a read-back round trip.
- `test_export_framework.py`: SLOTS cover the schema and are these tables; names; the transformer forms, the bank
  model, the star; regulator bank letters; the tape-shield formulas.
- `test_export_atoms.py` (tier 2): each importer atom deck (but the bare catalog, which `line.glm` includes) through
  the exporter and the importer again; the two CIM models equal (`cimtables.diff_models`, SI) under the X1 names,
  except the differences listed below by name; each exported deck is the golden `<atom>.exported.glm` beside it.
- `test_export_decks.py` (GridLAB-D 6.0): the Java exports (IEEE 13 cdpsm and assets, IEEE 123) solve to the
  original's voltages within 1e-4, the original run as the importer reads it (a second swing a plain bus, S1-2; a
  CONSTANT_PF battery at its CONSTANT_PQ set point, S4b-2); the PNNL exports solve; a second pass is the same text
  on all five; the IEEE 13 export is the committed golden `goldens/IEEE13_cdpsm/IEEE13_cdpsm.exported.glm`.
- `tests/cross_format/test_dss_to_glm.py`: DSS decks through CIM to GLM, against OpenDSS's own solution of one
  frozen state (controls off, CIM's taps, loads' models at any voltage), line to line on three-phase buses, each
  deck's tolerance the difference listed below.
- `gridlabd_engine.py` notes the wheel's quirks: no CLI; load errors only from `DirectGridLabD`; polar text misread
  unless `complex_output_format` is `RECT`; the Java exports need GridAPPS-D's `ieeezipload` player.

## Expected differences

| what | why | measured (worst, line to line unless noted) |
|---|---|---|
| a source's impedance is not written | GLM's swing is ideal (X6) | IEEE 13 original 3e-4 |
| a VoltageRegulator's own impedance | GLM's regulator is ideal | (in the row above) |
| a winding's grounding impedance (`rground`/`xground`) | GLM grounds a wye solidly | IEEE13_CDPSM's Sub3: 3e-3 (3 % line to neutral) |
| a non-native two-winding model's phase shift and zero sequence | the wye-wye replacement (X3) | YD, GrdYD 1.4e-3 |
| an open-delta bank as a full bank | the wye-wye replacement (X3) | OYOD 11 % (balanced), 16 % (unbalanced); solve only |
| a delta regulator bank as wye | GridLAB-D 6.0 has no delta regulator under NR | IEEE37 1.75 % |
| geometry lines' impedances | each engine computes its own line constants | IEEE13_Assets 2 % |
| an LTC's control, a capacitor's non-voltage control | GLM has no form for them | — |
| a battery's DC voltage | no CIM home yet (TODO, DCConductingAssetInfo) | tier 2: numberOfCells 11 → 28 (GridLAB-D's 115 V) |
| a template no equipment uses | GLM's configurations are written per use | tier 2: the atoms' `cn_250`, `xc_unused` |
| a bus's `nominal_voltage` as the deck rounded it | it is the BaseVoltage's: the deck's 2401.78 V is 4160 V / √3 | tier 2: a regulator end's baseU, neutralU, 1.2e-6 |
| `rated_power`, ratings and every slot CIM cannot hold | GridLAB-D's defaults | — |

## Slot tables

Generated from `SLOTS` (`test_export_framework.spec_tables`); every slot not listed is left unset, GridLAB-D's
default.

### node

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| phases | written | the A, B, C of every terminal on the node, then N |
| nominal_voltage | written | the BaseVoltage, LL / sqrt 3 on a three-phase system, LL on a single-phase one (module docstring) |
| bustype | written | SWING on the substation only |

102 other slots: unset

### triplex_node

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| phases | written | the service's letter, then S |
| nominal_voltage | written | the BaseVoltage (s1 to s2) / 2: one leg |

80 other slots: unset

### substation

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| phases | written | the A, B, C of every terminal on the node, then N |
| nominal_voltage | written | get_source: nominalVoltage / sqrt 3 (the importer's line_voltage inverted) |
| bustype | written | SWING on the substation only |
| positive_sequence_voltage | written | get_source: voltageMagnitude / sqrt 3 at voltageAngle |
| base_power | written | the graph's BasePower, when it holds one (network.base_power's 100 MVA default is not CIM's) |

123 other slots: unset

### overhead_line_conductor

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names; <wire>_<class> when one WireInfo is two GLM classes |
| geometric_mean_radius | written | get_wire_info.gmr; unset raises |
| resistance | written | get_wire_info: rAC50 (GridLAB-D's 50 C value, the GLM importer's), else rAC25 (the DSS importer's); neither raises |
| diameter | written | 2 x get_wire_info.radius; unset: unset (GridLAB-D reads it only for line capacitance) |
| rating_summer_continuous | written | the wire's normal limit, else ratedCurrent |
| rating_summer_emergency | written | the wire's emergency limit |

10 other slots: unset

### triplex_line_conductor

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names; <wire>_<class> when one WireInfo is two GLM classes |
| resistance | written | get_wire_info: rAC50 (GridLAB-D's 50 C value, the GLM importer's), else rAC25 (the DSS importer's); neither raises |
| geometric_mean_radius | written | get_wire_info.gmr; unset raises |
| rating_summer_continuous | written | the wire's normal limit, else ratedCurrent |
| rating_summer_emergency | written | the wire's emergency limit |

10 other slots: unset

### underground_line_conductor

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names; <wire>_<class> when one WireInfo is two GLM classes |
| outer_diameter | written | a cable's diameterOverJacket; a bare wire's BARE_BURIED_OUTER x its diameter (rule: CIM has no jacket, GridLAB-D needs one) |
| conductor_gmr | written | get_wire_info.gmr; unset raises |
| conductor_diameter | written | 2 x get_wire_info.radius; unset: unset (GridLAB-D reads it only for line capacitance) |
| conductor_resistance | written | get_wire_info: rAC50 (GridLAB-D's 50 C value, the GLM importer's), else rAC25 (the DSS importer's); neither raises |
| neutral_gmr | written | neutralStrandGmr (ConcentricNeutralCableInfo) |
| neutral_diameter | written | 2 x neutralStrandRadius |
| neutral_resistance | written | neutralStrandRDC20 |
| neutral_strands | written | neutralStrandCount |
| shield_thickness | written | tapeThickness (TapeShieldCableInfo) |
| shield_diameter | written | diameterOverScreen (TapeShieldCableInfo) |
| shield_gmr | written | tape_shield_gmr: diameterOverScreen / 2, the Java exporter's (GridLAB-D tells a tape-shield cable by shield_gmr > 0) |
| shield_resistance | written | tape_shield_resistance: Kersting eq. 4.89, the Java exporter's |
| rating_summer_continuous | written | the wire's normal limit, else ratedCurrent |
| rating_summer_emergency | written | the wire's emergency limit |

11 other slots: unset

### line_spacing

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names; <spacing>_<letters> when lines use it on different phases |
| distance_AB | written | get_stored_distances between the two phases' sequence numbers; absent: unset (GridLAB-D's 0, no coupling) |
| distance_BC | written | get_stored_distances between the two phases' sequence numbers; absent: unset (GridLAB-D's 0, no coupling) |
| distance_AC | written | get_stored_distances between the two phases' sequence numbers; absent: unset (GridLAB-D's 0, no coupling) |
| distance_AN | written | get_stored_distances between the two phases' sequence numbers; absent: unset (GridLAB-D's 0, no coupling) |
| distance_BN | written | get_stored_distances between the two phases' sequence numbers; absent: unset (GridLAB-D's 0, no coupling) |
| distance_CN | written | get_stored_distances between the two phases' sequence numbers; absent: unset (GridLAB-D's 0, no coupling) |
| distance_AE | written | the stored height; an XYSpacing's y (a line with a ySpacingOffset raises) |
| distance_BE | written | the stored height; an XYSpacing's y (a line with a ySpacingOffset raises) |
| distance_CE | written | the stored height; an XYSpacing's y (a line with a ySpacingOffset raises) |
| distance_NE | written | the stored height; an XYSpacing's y (a line with a ySpacingOffset raises) |

8 other slots: unset

### line_configuration

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names; <template>_<letters> when lines use it on different phases |
| conductor_A | written | geometry: the wire at the phase's sequence number |
| conductor_B | written | geometry: the wire at the phase's sequence number |
| conductor_C | written | geometry: the wire at the phase's sequence number |
| conductor_N | written | geometry: the wire at the phase's sequence number |
| spacing | written | geometry: the line_spacing |
| z11 | written | matrix: r + jx (ohm/mile) by phase letter, neutrals Kron-reduced |
| z12 | written | matrix: r + jx (ohm/mile) by phase letter, neutrals Kron-reduced |
| z13 | written | matrix: r + jx (ohm/mile) by phase letter, neutrals Kron-reduced |
| z21 | written | matrix: r + jx (ohm/mile) by phase letter, neutrals Kron-reduced |
| z22 | written | matrix: r + jx (ohm/mile) by phase letter, neutrals Kron-reduced |
| z23 | written | matrix: r + jx (ohm/mile) by phase letter, neutrals Kron-reduced |
| z31 | written | matrix: r + jx (ohm/mile) by phase letter, neutrals Kron-reduced |
| z32 | written | matrix: r + jx (ohm/mile) by phase letter, neutrals Kron-reduced |
| z33 | written | matrix: r + jx (ohm/mile) by phase letter, neutrals Kron-reduced |
| c11 | written | matrix: c_from_b(b) (nF/mile) at the base frequency; b unset: unset (0) |
| c12 | written | matrix: c_from_b(b) (nF/mile) at the base frequency; b unset: unset (0) |
| c13 | written | matrix: c_from_b(b) (nF/mile) at the base frequency; b unset: unset (0) |
| c21 | written | matrix: c_from_b(b) (nF/mile) at the base frequency; b unset: unset (0) |
| c22 | written | matrix: c_from_b(b) (nF/mile) at the base frequency; b unset: unset (0) |
| c23 | written | matrix: c_from_b(b) (nF/mile) at the base frequency; b unset: unset (0) |
| c31 | written | matrix: c_from_b(b) (nF/mile) at the base frequency; b unset: unset (0) |
| c32 | written | matrix: c_from_b(b) (nF/mile) at the base frequency; b unset: unset (0) |
| c33 | written | matrix: c_from_b(b) (nF/mile) at the base frequency; b unset: unset (0) |

12 other slots: unset

### triplex_line_configuration

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names, as line_configuration |
| conductor_N | written | geometry: the wire at s1, s2, N |
| z11 | written | matrix: r + jx (ohm/mile) on s1, s2, N Kron-reduced |
| z12 | written | matrix: r + jx (ohm/mile) on s1, s2, N Kron-reduced |
| z21 | written | matrix: r + jx (ohm/mile) on s1, s2, N Kron-reduced |
| z22 | written | matrix: r + jx (ohm/mile) on s1, s2, N Kron-reduced |
| conductor_1 | written | geometry: the wire at s1, s2, N |
| conductor_2 | written | geometry: the wire at s1, s2, N |
| insulation_thickness | written | t = D12 - D1N of the spacing (S2-8 inverted) |
| diameter | written | d = 2 D1N - D12 |

30 other slots: unset

### overhead_line

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| phases | written | the line's A, B, C, then N when it has a neutral conductor; a triplex line its buses' service letter, then S |
| from_node | written | terminal 1's bus |
| to | written | terminal 2's bus |
| continuous_rating_A | written | get_current_limits normal, on each of the line's phases (a triplex line's service letter) |
| continuous_rating_B | written | get_current_limits normal, on each of the line's phases (a triplex line's service letter) |
| continuous_rating_C | written | get_current_limits normal, on each of the line's phases (a triplex line's service letter) |
| emergency_rating_A | written | get_current_limits emergency |
| emergency_rating_B | written | get_current_limits emergency |
| emergency_rating_C | written | get_current_limits emergency |
| configuration | written | line_catalog: the configuration of the line's key |
| length | written | ACLineSegment.length (ft); unset raises |

52 other slots: unset

### underground_line

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| phases | written | the line's A, B, C, then N when it has a neutral conductor; a triplex line its buses' service letter, then S |
| from_node | written | terminal 1's bus |
| to | written | terminal 2's bus |
| continuous_rating_A | written | get_current_limits normal, on each of the line's phases (a triplex line's service letter) |
| continuous_rating_B | written | get_current_limits normal, on each of the line's phases (a triplex line's service letter) |
| continuous_rating_C | written | get_current_limits normal, on each of the line's phases (a triplex line's service letter) |
| emergency_rating_A | written | get_current_limits emergency |
| emergency_rating_B | written | get_current_limits emergency |
| emergency_rating_C | written | get_current_limits emergency |
| configuration | written | line_catalog: the configuration of the line's key |
| length | written | ACLineSegment.length (ft); unset raises |

52 other slots: unset

### triplex_line

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| phases | written | the line's A, B, C, then N when it has a neutral conductor; a triplex line its buses' service letter, then S |
| from_node | written | terminal 1's bus |
| to | written | terminal 2's bus |
| continuous_rating_A | written | get_current_limits normal, on each of the line's phases (a triplex line's service letter) |
| continuous_rating_B | written | get_current_limits normal, on each of the line's phases (a triplex line's service letter) |
| continuous_rating_C | written | get_current_limits normal, on each of the line's phases (a triplex line's service letter) |
| emergency_rating_A | written | get_current_limits emergency |
| emergency_rating_B | written | get_current_limits emergency |
| emergency_rating_C | written | get_current_limits emergency |
| configuration | written | line_catalog: the configuration of the line's key |
| length | written | ACLineSegment.length (ft); unset raises |

52 other slots: unset

### switch

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| phases | written | side 1's A, B, C |
| status | written | get_switch_state(which=switch_state): OPEN or CLOSED |
| from_node | written | terminal 1's bus |
| to | written | terminal 2's bus |
| continuous_rating_A | written | get_current_limits normal |
| continuous_rating_B | written | get_current_limits normal |
| continuous_rating_C | written | get_current_limits normal |
| emergency_rating_A | written | get_current_limits emergency |
| emergency_rating_B | written | get_current_limits emergency |
| emergency_rating_C | written | get_current_limits emergency |

58 other slots: unset

### fuse

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| phases | written | side 1's A, B, C |
| status | written | get_switch_state(which=switch_state): OPEN or CLOSED |
| from_node | written | terminal 1's bus |
| to | written | terminal 2's bus |
| continuous_rating_A | written | get_current_limits normal |
| continuous_rating_B | written | get_current_limits normal |
| continuous_rating_C | written | get_current_limits normal |
| emergency_rating_A | written | get_current_limits emergency |
| emergency_rating_B | written | get_current_limits emergency |
| emergency_rating_C | written | get_current_limits emergency |
| current_limit | written | Fuse.ratedCurrent (A) |

57 other slots: unset

### recloser

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| phases | written | side 1's A, B, C |
| status | written | get_switch_state(which=switch_state): OPEN or CLOSED |
| from_node | written | terminal 1's bus |
| to | written | terminal 2's bus |
| continuous_rating_A | written | get_current_limits normal |
| continuous_rating_B | written | get_current_limits normal |
| continuous_rating_C | written | get_current_limits normal |
| emergency_rating_A | written | get_current_limits emergency |
| emergency_rating_B | written | get_current_limits emergency |
| emergency_rating_C | written | get_current_limits emergency |

61 other slots: unset

### sectionalizer

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| phases | written | side 1's A, B, C |
| status | written | get_switch_state(which=switch_state): OPEN or CLOSED |
| from_node | written | terminal 1's bus |
| to | written | terminal 2's bus |
| continuous_rating_A | written | get_current_limits normal |
| continuous_rating_B | written | get_current_limits normal |
| continuous_rating_C | written | get_current_limits normal |
| emergency_rating_A | written | get_current_limits emergency |
| emergency_rating_B | written | get_current_limits emergency |
| emergency_rating_C | written | get_current_limits emergency |

58 other slots: unset

### transformer_configuration

| GLM slot | kind | from / why |
|---|---|---|
| name | written | the TankConfiguration's name when every instance wires it alike, else <unit>_config |
| connect_type | written | WYE_WYE, SINGLE_PHASE, DELTA_DELTA, DELTA_GWYE, SINGLE_PHASE_CENTER_TAPPED (module docstring) |
| primary_voltage | written | winding 1's ratedU (V), a coil's baseU; an LTC's actual ratio folded in |
| secondary_voltage | written | winding 2's, likewise; a centre tap's half; a star leg's 1000 V |
| power_rating | written | winding 1's ratedS (kVA); a star leg's own winding's |
| powerA_rating | written | a coil's or a centre tap's kVA on its phase |
| powerB_rating | written | a coil's or a centre tap's kVA on its phase |
| powerC_rating | written | a coil's or a centre tap's kVA on its phase |
| impedance | written | the (1, 2) R + jX in pu (R the windings' r and the mesh r); a centre tap's or a star leg's star branch; not positive: FLOOR |
| impedance1 | written | a centre tap's s1 half of the star |
| impedance2 | written | a centre tap's s2 half of the star |
| shunt_resistance | written | 1 / the core g (pu); unset: not written (GridLAB-D's lossless core) |
| shunt_reactance | written | 1 / the core b (pu); unset: not written |

35 other slots: unset

### transformer

| GLM slot | kind | from / why |
|---|---|---|
| name | written | the transformer's; a tank of several <transformer>_<n>; a star leg <unit>_<winding> |
| phases | written | winding 1's A, B, C, then N; a centre tap's letter, then S |
| from_node | written | winding 1's bus |
| to | written | winding 2's bus; a star leg's star bus |
| continuous_rating_A | written | get_current_limits normal |
| continuous_rating_B | written | get_current_limits normal |
| continuous_rating_C | written | get_current_limits normal |
| emergency_rating_A | written | get_current_limits emergency |
| emergency_rating_B | written | get_current_limits emergency |
| emergency_rating_C | written | get_current_limits emergency |
| configuration | written | its transformer_configuration |

67 other slots: unset

### regulator_configuration

| GLM slot | kind | from / why |
|---|---|---|
| name | written | <regulator>_config |
| connect_type | written | WYE_WYE: CIM's AutoTransformerEnds are grounded wye coils |
| band_center | written | the target (V); over ptRatio on LINE_DROP_COMP; unset on a disabled control |
| band_width | written | the deadband (V), likewise |
| dwell_time | written | TapChanger.initialDelay (s) |
| raise_taps | written | highStep - neutralStep |
| lower_taps | written | neutralStep - lowStep |
| current_transducer_ratio | written | ctRatio |
| power_transducer_ratio | written | ptRatio |
| compensator_r_setting_A | written | lineDropR x ctRatio / ptRatio |
| compensator_r_setting_B | written | lineDropR x ctRatio / ptRatio |
| compensator_r_setting_C | written | lineDropR x ctRatio / ptRatio |
| compensator_x_setting_A | written | lineDropX x ctRatio / ptRatio |
| compensator_x_setting_B | written | lineDropX x ctRatio / ptRatio |
| compensator_x_setting_C | written | lineDropX x ctRatio / ptRatio |
| CT_phase | written | BANK: as PT_phase |
| PT_phase | written | BANK: the monitored phase, else its first |
| regulation | written | stepVoltageIncrement x raise_taps (per unit) |
| control_level | written | BANK for one VoltageRegulator alone, else unset (INDIVIDUAL) |
| Control | written | MANUAL, LINE_DROP_COMP or OUTPUT_VOLTAGE from the TapChangerControl |
| Type | written | B on a construction typeB, else A (module docstring) |
| tap_pos_A | written | step - neutralStep on each phase |
| tap_pos_B | written | step - neutralStep on each phase |
| tap_pos_C | written | step - neutralStep on each phase |

10 other slots: unset

### regulator

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| phases | written | the A, B, C of its end 1 |
| from_node | written | end 1's bus |
| to | written | end 2's bus |
| continuous_rating_A | written | get_current_limits normal |
| continuous_rating_B | written | get_current_limits normal |
| continuous_rating_C | written | get_current_limits normal |
| emergency_rating_A | written | get_current_limits emergency |
| emergency_rating_B | written | get_current_limits emergency |
| emergency_rating_C | written | get_current_limits emergency |
| configuration | written | its regulator_configuration |

64 other slots: unset

### load

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| parent | written | its bus |
| phases | written | the letters then N (wye) or D (delta); a split-phase bus's letter then S |
| nominal_voltage | written | its bus's |
| base_power_A | written | base_power form: module docstring |
| base_power_B | written | base_power form: module docstring |
| base_power_C | written | base_power form: module docstring |
| power_pf_A | written | base_power form: module docstring |
| current_pf_A | written | base_power form: module docstring |
| impedance_pf_A | written | base_power form: module docstring |
| power_pf_B | written | base_power form: module docstring |
| current_pf_B | written | base_power form: module docstring |
| impedance_pf_B | written | base_power form: module docstring |
| power_pf_C | written | base_power form: module docstring |
| current_pf_C | written | base_power form: module docstring |
| impedance_pf_C | written | base_power form: module docstring |
| power_fraction_A | written | base_power form: module docstring |
| current_fraction_A | written | base_power form: module docstring |
| impedance_fraction_A | written | base_power form: module docstring |
| power_fraction_B | written | base_power form: module docstring |
| current_fraction_B | written | base_power form: module docstring |
| impedance_fraction_B | written | base_power form: module docstring |
| power_fraction_C | written | base_power form: module docstring |
| current_fraction_C | written | base_power form: module docstring |
| impedance_fraction_C | written | base_power form: module docstring |

198 other slots: unset

### triplex_load

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| parent | written | its bus |
| phases | written | the letters then N (wye) or D (delta); a split-phase bus's letter then S |
| nominal_voltage | written | its bus's |
| base_power_1 | written | base_power form: module docstring |
| base_power_2 | written | base_power form: module docstring |
| base_power_12 | written | base_power form: module docstring |
| power_pf_1 | written | base_power form: module docstring |
| current_pf_1 | written | base_power form: module docstring |
| impedance_pf_1 | written | base_power form: module docstring |
| power_pf_2 | written | base_power form: module docstring |
| current_pf_2 | written | base_power form: module docstring |
| impedance_pf_2 | written | base_power form: module docstring |
| power_pf_12 | written | base_power form: module docstring |
| current_pf_12 | written | base_power form: module docstring |
| impedance_pf_12 | written | base_power form: module docstring |
| power_fraction_1 | written | base_power form: module docstring |
| current_fraction_1 | written | base_power form: module docstring |
| impedance_fraction_1 | written | base_power form: module docstring |
| power_fraction_2 | written | base_power form: module docstring |
| current_fraction_2 | written | base_power form: module docstring |
| impedance_fraction_2 | written | base_power form: module docstring |
| power_fraction_12 | written | base_power form: module docstring |
| current_fraction_12 | written | base_power form: module docstring |
| impedance_fraction_12 | written | base_power form: module docstring |

115 other slots: unset

### capacitor

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (X1) |
| parent | written | its bus |
| phases | written | its letters then N |
| nominal_voltage | written | its bus's |
| pt_phase | written | VOLT: the monitored phases |
| phases_connected | written | as phases |
| switchA | written | CLOSED when the actual sections are in |
| switchB | written | CLOSED when the actual sections are in |
| switchC | written | CLOSED when the actual sections are in |
| control | written | VOLT for an enabled voltage RegulatingControl, else MANUAL |
| voltage_set_high | written | VOLT: target + deadband / 2 |
| voltage_set_low | written | VOLT: target - deadband / 2 |
| capacitor_A | written | get_shunt_reactive_power per phase, every section in |
| capacitor_B | written | get_shunt_reactive_power per phase, every section in |
| capacitor_C | written | get_shunt_reactive_power per phase, every section in |
| cap_nominal_voltage | written | nomU line to neutral (module docstring) |
| dwell_time | written | VOLT: aVRDelay |
| control_level | written | VOLT: INDIVIDUAL on one phase, BANK on more |

119 other slots: unset

### inverter

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names; <connection>_<n> for each of several units |
| parent | written | its bus |
| inverter_type | written | FOUR_QUADRANT |
| four_quadrant_control_mode | written | a battery's CONSTANT_PQ (CIM's set point), a PV's CONSTANT_PF (GridLAB-D's PV logic, S4b-1) |
| generator_status | written | OFFLINE when normallyInService is false, else ONLINE |
| P_Out | written | a battery's get_inverter_units p, generation sign |
| Q_Out | written | a battery's get_inverter_units q, generation sign |
| rated_power | written | ratedS x share / phases (GLM's is per phase) |
| inverter_efficiency | rule | a PV's 1: its losses are in CIM's p (module docstring) |
| soc_reserve | written | a battery's minimumE / ratedE |
| power_factor | written | a PV's p / |p + jq|, negative when q is |
| phases | written | its letters then N; a split-phase bus's letter then S |
| max_charge_rate | written | a battery's StorageInverterInfo.chargeRateActiveMax x share |

243 other slots: unset

### battery

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (the BatteryUnit) |
| parent | written | its inverter |
| use_internal_battery_model | written | TRUE |
| battery_type | written | BatteryInfo.batteryType; none: unset (GridLAB-D's UNKNOWN) |
| rated_power | written | maxP (W) |
| battery_capacity | written | ratedE (Wh) |
| round_trip_efficiency | written | chargingEfficiency x dischargingEfficiency |
| state_of_charge | written | storedE / ratedE |

70 other slots: unset

### solar

| GLM slot | kind | from / why |
|---|---|---|
| name | written | Names (the PhotoVoltaicUnit) |
| parent | written | its inverter |
| Rated_Insolation | written | SolarPanelInfo.referenceIrradiation |
| efficiency | written | SolarPanelInfo.efficiency |
| soiling | rule | 1: in CIM's p (module docstring) |
| derating | rule | p / GridLAB-D's lossless output: the whole loss (module docstring) |
| rated_power | written | maxP (W); unset raises |
| shading_factor | written | SolarArrayInfo.shadingFactor |
| tilt_angle | written | SolarArrayInfo.tiltAngle |
| orientation_azimuth | written | SolarArrayInfo.orientationAzimuth |

54 other slots: unset
