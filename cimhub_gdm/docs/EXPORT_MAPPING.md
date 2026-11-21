# CIM → GDM export mapping

**Status:**
- X1 (framework, shell, buses, source) built 2026-11-09, for review.
- X2 (switches, matrix and sequence lines, loads, capacitors) built 2026-11-09. At the user's request ("implement X2
  so that ditto gets what it needs"), its code went in before this section was approved. Two X1 decisions changed
  because ditto needs them:
  - buses are now rated line to ground (X6);
  - the switch matrices are OpenDSS's 1 mΩ switch, not zero.
- X3 (transformers, center taps, regulators and their controllers) built 2026-11-09, at the user's "continue to next
  phase", for review. ditto drove four of its rules:
  - taps go on the catalog winding;
  - a 1-phase wye coil lists no N;
  - each regulator unit is its own GDM regulator;
  - unset line drop R and X are 0 V.
- X4, part one (geometry lines with bare and concentric wire; solar and batteries) built 2026-11-09, at the user's
  "continue to next phase", after rc_1 (S6d) was merged. ditto drove one rule: a PV's irradiance is its output's
  share of the panel's rating, not a neutral fill.
- X4, part two (reactors; a connection of several units, one GDM DER per unit) built 2026-11-09, at the user's "go
  for the next phase", after rc_1 (S6e: `get_series_compensator`, `get_inverter_units`) was merged. X4 is complete.

One section per phase ([`EXPORT_PLAN.md`](EXPORT_PLAN.md) §2). The slot tables are generated from each module's
`SLOTS` (`exporter/slots.py` `slots_table`), and a test fails on a GDM field with no slot.

## Layout

- `exporter/cim_to_gdm.py`: `GdmExporter.to_model`, `EXPORT_ORDER`, the system name (X1) and the coverage check: a
  ConductingEquipment class that no module exports raises `no GDM export yet for {...}`.
- One module per family. Each has `CIM_CLASSES`, `SLOTS` (GDM class → field → `Slot(kind, note)`) and
  `export(obj, context)`, which returns one GDM component. The orchestrator adds it to the system and records it under
  the CIM object's `uri()`, so a later module finds it with `context.gdm(obj)`. Asking for one not yet exported raises.
- `ExportContext` carries the network, the `Names`, the exported components (`made`), the shared catalogs
  (`catalogs`, X3) and the fill counts (`filled`, X4).
- `shared.shared_equipment(context, catalog, equipment)` is the X3 catalog rule for every family: one GDM equipment
  per (CIM catalog, the equipment's values, uuids and name aside). The first is named `<catalog>`, each later one
  `<catalog>_<n>`, in export order.
- Slot kinds:
  - `written`: from a getter or the CIM structure;
  - `rule`: a CIM `None` or shape GDM needs, by the rule in the note;
  - `fill`: a required field CIM cannot hold (X4), a named constant in `exporter/fills.py` written through
    `context.fill`;
  - `unset`: left at GDM's default.
- `fills.warn` logs one WARNING per export, naming each filled field and its count. When the fuse or recloser
  protection is a placeholder, the WARNING says so.
- `gdm_writer.write_gdm(system, path)` (`DistributionSystem.to_json`, overwriting) and `gdm_reader.read_gdm` are the
  only modules that touch the filesystem. `cim_to_gdm(network, destination, **opts)` is the convenience function.
- GDM is imported from `gdm.systems.distribution` (2.4's path). The importer and the tests were moved to it on this
  branch.

## Names

Decision X2: `exporter/naming.py` `Names`, on the shared switch `cimhub_core.names.export_name` (`name`, `mrid`,
`uri`; default `mrid`). GDM names are free text, so nothing is sanitized, and two components may share one (revised
2026-11-09, user). GDM allows it: `get_component(cls, name)` then raises, and `list_components_by_name` finds them
all. IEEE13_CDPSM needs it (`PVSystem.House` and `Storage.House`).
- **Identity is the uuid.** A component made from a CIM object takes that object's `Identity.identifier`, its
  `uri()` (`Names.own`). A part with no CIM object of its own takes a uuid5 of its owner's identifier, on its GDM
  class and suffix (`Names.part`). That covers inline equipment, per-phase children, a catalog's n-th variant, a
  controller named after its equipment, and placeholder protection with its curves. infrasys holds one component per
  uuid, so a part can't reuse its owner's. Every export of one CIM model gives the same uuids.
- Inline equipment, controllers included, take their instance's name (`VoltageSourceEquipment src`,
  `CapacitorEquipment vc`).
- A per-phase child takes `<instance>_<phase>` (`src_A`).
- An unnamed InverterInfo under name source `name` takes GDM's default inverter name, `''`, which the importer reads
  as unnamed.
- A DER of a connection with several units takes its unit's name and `uri()` (DER).
- Placeholder protection takes `<fuse>_tcc_placeholder` or `<recloser>_ctrl_placeholder` (X5).
- A shared catalog takes the catalog's name, or `<catalog>_<n>` for its n-th instance value (X3).
- A transformer with no TankConfiguration, and a regulator with no TapChangerInfo, has its own equipment, named after
  it.
- The system's name is `system_name=`, else the one Feeder's exported name. Several Feeders raise.

## Shell

`Feeder` → `DistributionFeeder`, `Substation` → `DistributionSubstation`, whose `feeders` are its
`NormalEnergizedFeeder`s, sorted by name. Feeders are exported first.

**DistributionFeeder**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |

**DistributionSubstation**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |
| feeders | written | the Feeders whose NormalEnergizingSubstation it is, by name |

## Containers

`shared.containers` writes a component's container as CIM holds it, with no inference:
- a Feeder gives `feeder`;
- a Substation gives `substation`;
- a VoltageLevel gives its Substation;
- no container gives neither;
- any other container class raises.

CIM holds one container, so a GDM component that named both a feeder and a substation comes back with the feeder
only (a listed difference).

## Buses

Decision X6, revised in X2. `ConnectivityNode` → `DistributionBus`:
- **Rating.** `rated_voltage` is line to ground, with `voltage_type` line-to-ground: the BaseVoltage / √3
  (`get_base_voltage(form='LN')`), or / 2 on a split-phase bus (a terminal on S1 or S2), the 120 V leg. This is how
  ditto's DSS reader writes buses. ditto 0.1.8's capacitor and solar writers read a bus rating as line to ground
  whatever its `voltage_type`, so a line-to-line bus put a 3-phase capacitor at 7.2 kV on a 4.16 kV system. A GDM
  line-to-line rating therefore comes back as its line-to-ground equivalent (a listed difference). The importer's
  `system_voltage` maps both forms to the same BaseVoltage.
- **Phases.** `phases` are the union of the conductors on the node's terminals, in A B C S1 S2 N order (a balanced
  terminal is ABC). A node with no terminals has `[]`, which GDM accepts, and is rated LL / √3.

**DistributionBus**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |
| substation | written | the ConnectivityNodeContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the ConnectivityNodeContainer when it is a Feeder (containers) |
| in_service | unset | a ConnectivityNode has no service state; GDM's default, True |
| voltage_type | rule | always line-to-ground, as ditto writes buses: its capacitor and solar writers read every bus rating as line to ground (X6) |
| phases | rule | the union of the conductors on the node's terminals, in A B C S1 S2 N order; [] when no terminal is on it (X6) |
| voltagelimits | unset | untranscribed on import: no OperationalLimitSet on a ConnectivityNode |
| rated_voltage | rule | get_base_voltage(form='LN') (kV); on a split-phase bus (S1 or S2) the 120 V leg, get_base_voltage(form='LL') / 2 (the importer's system_voltage inverse) |
| coordinate | unset | untranscribed on import: a ConnectivityNode is not a PowerSystemResource (X10) |

## Source

`EnergySource` → `DistributionVoltageSource` + `VoltageSourceEquipment` + one `PhaseVoltageSourceEquipment` per
phase, all with the source's values from `get_source` (kV, ohm, degrees).
- **Unset impedance.** r, x, r0 or x0 unset raises: GDM needs all four on every phase.
- **Negative sequence.** r2/x2 set and different from r/x raises, because GDM has no negative sequence.
- **Voltage.** The phase voltages are `voltageMagnitude`, line to line. ditto's source writer reads both forms.
- **Angles.** Phase k's angle is the source's angle − 120° × k, wrapped to [−180, 180): positive sequence. An unset
  angle is 0, the reference. CIM holds one angle, so ditto's +120° convention comes back as −120° steps. The
  importer accepts both (G2).

**DistributionVoltageSource**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| bus | written | the bus of get_terminal_nodes |
| phases | written | get_source.phases |
| equipment | written | a VoltageSourceEquipment made for this source |

**VoltageSourceEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the source's name (X2) |
| sources | written | one PhaseVoltageSourceEquipment per phase, all with the source's values |

**PhaseVoltageSourceEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | <source>_<phase> (X2) |
| r0 | written | get_source.impedance.r0 (ohm); unset raises |
| r1 | written | get_source.impedance.r (ohm); unset raises |
| x0 | written | get_source.impedance.x0 (ohm); unset raises |
| x1 | written | get_source.impedance.x (ohm); unset raises |
| voltage | written | get_source.magnitude (kV, line to line) |
| voltage_type | rule | always line-to-line: voltageMagnitude is line to line (X6) |
| angle | rule | get_source.angle - 120 deg x the phase's position, wrapped to [-180, 180); an unset angle is 0, the reference |

## Switches

Decision X5, the importer's decision 14 inverted:

| CIM | GDM component | GDM equipment |
|---|---|---|
| LoadBreakSwitch | MatrixImpedanceSwitch | MatrixImpedanceSwitchEquipment |
| Breaker | MatrixImpedanceSwitch | CircuitBreakerEquipment (`breakingCapacity` → `interrupting_current`, kA) |
| Disconnector | MatrixImpedanceSwitch | DisconnectorEquipment |
| GroundDisconnector | MatrixImpedanceSwitch | EarthingSwitchEquipment (the importer has no builder for it yet, B19) |
| Fuse | MatrixImpedanceFuse | MatrixImpedanceFuseEquipment |
| Recloser | MatrixImpedanceRecloser | MatrixImpedanceRecloserEquipment |
| Sectionaliser, Jumper | raise `no GDM export yet` | |

- **State.** Each phase is open when its SwitchPhase's `open` is set and true, else when the switch's `open` is.
  `get_switch_state(which='actual')` reads both; unset on both raises.
- **Normal state.** With `normalOpen` set, and the switch mixed or its normal state different from the actual one, the
  equipment gets a `DistributionSwitchController` (`normal_state` open or close). That is the importer's rule
  inverted, so a reimport gives the same `normalOpen`. Fuse and recloser equipment hold no controller, so a differing
  normal state on one raises.
- **Ampacity.** `ratedCurrent`, required.
- **Fills (X4).**
  - Matrices: r and x are 1 Ω/km on the diagonal, c is zero, n × n. This is OpenDSS's own switch impedance
    (`Switch=yes`: r1 = x1 = 1 per unit length), 1 mΩ across the 1 m length. A zero matrix is singular: OpenDSS,
    through ditto, aborts with a matrix inversion error.
  - Length: 1 m.
  - Switch controller: `delay` 0 s, `is_locked` False.
  - Fuse: `delay` 0 s, `tcc_curve` GDM's `TimeCurrentCurve.example()`.
  - Recloser: `controller` GDM's `DistributionRecloserController.example()`, renamed.

  The protection is not scaled to the device's rating, and the WARNING says it is a placeholder.
- SequenceImpedanceSwitch and GeometrySwitch are never written: a CIM switch has no impedance. A GDM
  SequenceImpedanceSwitch comes back as a MatrixImpedanceSwitch (a listed difference).

**MatrixImpedanceSwitch**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| buses | written | get_terminal_nodes |
| length | fill | fills.SWITCH_LENGTH, 1 m: a switch has no length in CIM |
| phases | written | get_conductor_phases |
| is_closed | rule | per phase, not get_switch_state(which='actual') of its SwitchPhase when that is set, else of the switch |
| equipment | written | made for this switch; its class from the CIM class (SWITCH_CLASSES) |
| conductor_phases | unset | CIM maps no parallel conductors (importer: must be unset or = phases) |

**MatrixImpedanceFuse**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| buses | written | get_terminal_nodes |
| length | fill | fills.SWITCH_LENGTH, 1 m: a switch has no length in CIM |
| phases | written | get_conductor_phases |
| is_closed | rule | per phase, not get_switch_state(which='actual') of its SwitchPhase when that is set, else of the switch |
| equipment | written | made for this switch; its class from the CIM class (SWITCH_CLASSES) |

**MatrixImpedanceRecloser**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| buses | written | get_terminal_nodes |
| length | fill | fills.SWITCH_LENGTH, 1 m: a switch has no length in CIM |
| phases | written | get_conductor_phases |
| is_closed | rule | per phase, not get_switch_state(which='actual') of its SwitchPhase when that is set, else of the switch |
| equipment | written | made for this switch; its class from the CIM class (SWITCH_CLASSES) |
| controller | fill | fills.recloser_controller, <recloser>_ctrl_placeholder: no RecloseSequence in cim18v17 (X5) |

**MatrixImpedanceSwitchEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the switch's name (X2) |
| construction | unset | untranscribed on import: no home on a CIM switch; GDM's default, overhead |
| r_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal: a CIM switch is ideal, and a zero matrix is singular in OpenDSS |
| x_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal |
| c_matrix | fill | fills.switch_matrices, zero |
| ampacity | written | required_qty(ratedCurrent, 'A') |
| controller | rule | a DistributionSwitchController when normalOpen is set and the switch is mixed or its normal state differs from the actual one; else None |

**DisconnectorEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the switch's name (X2) |
| construction | unset | untranscribed on import: no home on a CIM switch; GDM's default, overhead |
| r_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal: a CIM switch is ideal, and a zero matrix is singular in OpenDSS |
| x_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal |
| c_matrix | fill | fills.switch_matrices, zero |
| ampacity | written | required_qty(ratedCurrent, 'A') |
| controller | rule | a DistributionSwitchController when normalOpen is set and the switch is mixed or its normal state differs from the actual one; else None |

**EarthingSwitchEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the switch's name (X2) |
| construction | unset | untranscribed on import: no home on a CIM switch; GDM's default, overhead |
| r_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal: a CIM switch is ideal, and a zero matrix is singular in OpenDSS |
| x_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal |
| c_matrix | fill | fills.switch_matrices, zero |
| ampacity | written | required_qty(ratedCurrent, 'A') |
| controller | rule | a DistributionSwitchController when normalOpen is set and the switch is mixed or its normal state differs from the actual one; else None |

**CircuitBreakerEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the switch's name (X2) |
| construction | unset | untranscribed on import: no home on a CIM switch; GDM's default, overhead |
| r_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal: a CIM switch is ideal, and a zero matrix is singular in OpenDSS |
| x_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal |
| c_matrix | fill | fills.switch_matrices, zero |
| ampacity | written | required_qty(ratedCurrent, 'A') |
| controller | rule | a DistributionSwitchController when normalOpen is set and the switch is mixed or its normal state differs from the actual one; else None |
| interrupting_current | written | get_qty(breakingCapacity, 'kA'); unset is None |
| interrupting_current_unit | rule | always kiloampere, the unit interrupting_current is read in |
| trip_circuit_count | unset | untranscribed on import: no CIM home; GDM's default, 1 |

**MatrixImpedanceRecloserEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the switch's name (X2) |
| construction | unset | untranscribed on import: no home on a CIM switch; GDM's default, overhead |
| r_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal: a CIM switch is ideal, and a zero matrix is singular in OpenDSS |
| x_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal |
| c_matrix | fill | fills.switch_matrices, zero |
| ampacity | written | required_qty(ratedCurrent, 'A') |

**MatrixImpedanceFuseEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the switch's name (X2) |
| construction | unset | untranscribed on import: no home on a CIM switch; GDM's default, overhead |
| r_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal: a CIM switch is ideal, and a zero matrix is singular in OpenDSS |
| x_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal |
| c_matrix | fill | fills.switch_matrices, zero |
| ampacity | written | required_qty(ratedCurrent, 'A') |
| delay | fill | fills.FUSE_DELAY, 0 s: no FuseCharacteristicCurve in cim18v17 |
| tcc_curve | fill | fills.fuse_curve, <fuse>_tcc_placeholder: GDM's example curve (X5) |

**DistributionSwitchController**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the switch's name (X2) |
| delay | fill | fills.SWITCH_CONTROLLER_DELAY, 0 s: no CIM home |
| normal_state | written | get_switch_state(which='normal'): open → 'open', closed → 'close' |
| is_locked | fill | fills.SWITCH_CONTROLLER_LOCKED, False: no CIM home |

**TimeCurrentCurve**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | <fuse>_tcc_placeholder (X5) |
| curve_x | fill | TimeCurrentCurve.example() |
| curve_y | fill | TimeCurrentCurve.example() |

**DistributionRecloserController**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | <recloser>_ctrl_placeholder (X5) |
| delay | fill | DistributionRecloserController.example() |
| ground_delayed | fill | DistributionRecloserController.example() |
| ground_fast | fill | DistributionRecloserController.example() |
| phase_delayed | fill | DistributionRecloserController.example() |
| phase_fast | fill | DistributionRecloserController.example() |
| num_fast_ops | fill | DistributionRecloserController.example() |
| num_shots | fill | DistributionRecloserController.example() |
| reclose_intervals | fill | DistributionRecloserController.example() |
| reset_time | fill | DistributionRecloserController.example() |
| equipment | written | the example's RecloserControllerEquipment, renamed |

**RecloserControllerEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | <recloser>_ctrl_placeholder, not the example's vendor model (X5) |

## Lines

`ACLineSegment` → a branch on a shared catalog, picked by its PerLengthImpedance:
- PerLengthPhaseImpedance → MatrixImpedanceBranch on MatrixImpedanceBranchEquipment. The matrices come from
  `get_line_phase_impedance_matrix` (ohm/km, S/km), the lower triangle mirrored, in the line's ACLineSegmentPhase
  order.
- PerLengthSequenceImpedance → SequenceImpedanceBranch on SequenceImpedanceBranchEquipment, from
  `get_line_sequence_impedance_per_length`. An unset r0 or x0 raises.
- **Capacitance.** GDM holds capacitance and CIM susceptance, so C = b / (2π · 60 Hz), the inverse of the importer's
  `susceptance`. An unset b is zero, and a non-zero g raises (GDM has no shunt conductance).
- **Catalogs (X3).** GDM puts the line's `ampacity` on the catalog, so one GDM equipment is made per (catalog, the
  line's normal current limit from `get_current_limits`). The first value seen is named `<catalog>`, and each later
  one `<catalog>_2`, `_3` in export order: no pre-pass. A line with no normal limit raises.
- **Geometry (X4, `exporter/geometry.py`).** A line with geometry, a WireConfiguration that names a WireSpacing
  (`get_line_geometry`), is a GeometryBranch on a GeometryBranchEquipment: native geometry, never a computed matrix
  (`CONDUCTOR_GEOMETRY_ANTI_PATTERNS.md`), even when the configuration also holds its equivalent PerLengthImpedance.
  Otherwise the PerLengthImpedance is the line's own or its WireConfiguration's, a template LineCode
  (`get_line_code`).
  - The positions are the line's (`get_line_conductor_xy`, m): the spacing raised by the line's `ySpacingOffset`.
    So one GDM equipment is made per (configuration, positions, conductors), named `<configuration>`, then
    `<configuration>_<n>`.
  - The conductors are the configuration's wires by sequence number (`get_configuration_wires`, `get_wire_info`).
    An OverheadWireInfo becomes a BareConductorEquipment and a ConcentricNeutralCableInfo a ConcentricCableEquipment,
    each shared per (wire, values). A TapeShieldCableInfo raises: GDM has no tape-shield cable (IEEE13_Assets has
    one). A configuration that mixes bare wires and cables raises, because GDM's conductors are one kind.
  - **Ratings.** The importer puts a geometry line's first conductor's ratings on the line (the DSS engine's rule).
    So the first conductor carries the line's own normal and emergency limits where it has them, and every other
    conductor its wire's (its normal limit, else `ratedCurrent`). An unset emergency rating is 1.5 × normal,
    OpenDSS's `emergamps`. A line whose limits differ from its first wire's splits that wire's equipment.
  - A cable's `rated_voltage` is its `ratedVoltage` (read with `get_qty`: `get_wire_info` has none, and DSS has no
    such field). Unset, it is the line's BaseVoltage, line to line.
  - Every other wire value CIM can hold (radius, gmr, rAC25, rDC20, the cable's construction) raises when unset.
- A line with neither geometry nor a PerLengthImpedance (lumped r, x only) raises, and so does one whose own
  PerLengthImpedance differs from its WireConfiguration's (`get_line_code`).
- `length` is `length` in m.

The importer's OperationalLimitTypes have no `durationKind`, because `add_limit_type` has no keyword for it (B22 b,
`GDM_MAPPING.md` §14). `get_current_limits` needs it, so GDM-origin CIM can't export its lines yet. The tests set it
(`gdm_atoms.type_limit_durations`) until the builder has it. DSS-origin CIM writes it (the core `common` shape).

**MatrixImpedanceBranch**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| buses | written | get_terminal_nodes |
| length | written | required_qty(length, 'm') |
| phases | written | get_conductor_phases: ACLineSegmentPhase order, the matrix's row order |
| equipment | written | the MatrixImpedanceBranchEquipment for (PerLengthPhaseImpedance, ampacity) |

**SequenceImpedanceBranch**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| buses | written | get_terminal_nodes |
| length | written | required_qty(length, 'm') |
| phases | written | get_conductor_phases: ACLineSegmentPhase order, the matrix's row order |
| equipment | written | the SequenceImpedanceBranchEquipment for (PerLengthSequenceImpedance, ampacity) |

**GeometryBranch**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| buses | written | get_terminal_nodes |
| length | written | required_qty(length, 'm') |
| phases | written | get_conductor_phases: ACLineSegmentPhase order, the matrix's row order |
| equipment | written | the GeometryBranchEquipment for (WireConfiguration, the line's positions and ratings) (geometry.py) |

**MatrixImpedanceBranchEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the catalog's name; <catalog>_<n> for its n-th ampacity (X3) |
| construction | unset | untranscribed on import: no home on PerLengthImpedance; GDM's default |
| r_matrix | written | get_line_phase_impedance_matrix.r (ohm/km), the lower triangle mirrored |
| x_matrix | written | get_line_phase_impedance_matrix.x (ohm/km) |
| c_matrix | rule | get_line_phase_impedance_matrix.b (S/km) / 2πf; unset b is zero; a non-zero g raises: GDM has no shunt conductance |
| ampacity | written | get_current_limits(line).normal (A) of the lines on it; unset raises |

**SequenceImpedanceBranchEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the catalog's name; <catalog>_<n> for its n-th ampacity (X3) |
| pos_seq_resistance | written | get_line_sequence_impedance_per_length.r (ohm/km) |
| zero_seq_resistance | written | get_line_sequence_impedance_per_length.r0; unset raises |
| pos_seq_reactance | written | get_line_sequence_impedance_per_length.x |
| zero_seq_reactance | written | get_line_sequence_impedance_per_length.x0; unset raises |
| pos_seq_capacitance | rule | b (S/km) / 2πf; unset is zero; a non-zero g raises |
| zero_seq_capacitance | rule | b0 (S/km) / 2πf; unset is zero; a non-zero g0 raises |
| ampacity | written | get_current_limits(line).normal (A) of the lines on it; unset raises |

**GeometryBranchEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the WireConfiguration's name; <configuration>_<n> for its n-th values (X3) |
| conductors | written | get_configuration_wires, by sequence number: one kind (bare or concentric), a tape-shield cable raises |
| horizontal_positions | written | get_line_conductor_xy x (m) |
| vertical_positions | written | get_line_conductor_xy y (m): the spacing raised by the line's ySpacingOffset |
| insulation | unset | untranscribed on import: CIM has no permittivity; GDM's default (air) |

**BareConductorEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the OverheadWireInfo's name; <wire>_<n> for its n-th values (X3) |
| conductor_diameter | written | 2 × get_wire_info.radius (m); unset raises |
| conductor_gmr | written | get_wire_info.gmr (m); unset raises |
| ampacity | rule | the first conductor: the line's normal limit (get_current_limits), else its wire's; the others: the wire's normal limit, else ratedCurrent (get_wire_info); none raises |
| ac_resistance | written | get_wire_info.r_ac25 (ohm/m); unset raises |
| emergency_ampacity | rule | the first conductor: the line's emergency limit, else its wire's; the others: the wire's; unset is 1.5 × ampacity (OpenDSS's emergamps) |
| dc_resistance | written | get_wire_info.r_dc20 (ohm/m); unset raises |

**ConcentricCableEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the ConcentricNeutralCableInfo's name; <cable>_<n> for its n-th values (X3) |
| strand_diameter | written | 2 × neutral_strand_radius (m); unset raises |
| conductor_diameter | written | 2 × radius (m); unset raises |
| cable_diameter | written | diameter_over_jacket (m); unset raises |
| insulation_thickness | written | insulation_thickness (m); unset raises |
| insulation_diameter | written | diameter_over_insulation (m); unset raises |
| ampacity | rule | the first conductor: the line's normal limit (get_current_limits), else its wire's; the others: the wire's normal limit, else ratedCurrent (get_wire_info); none raises |
| conductor_gmr | written | gmr (m); unset raises |
| strand_gmr | written | neutral_strand_gmr (m); unset raises |
| phase_ac_resistance | written | r_ac25 (ohm/m); unset raises |
| strand_ac_resistance | written | neutral_strand_r_dc20 (ohm/m), CIM's one strand resistance; unset raises |
| num_neutral_strands | written | neutral_strand_count; unset raises |
| rated_voltage | rule | the cable's ratedVoltage (kV; get_wire_info has none); unset is the line's BaseVoltage, line to line |
| insulation | unset | untranscribed on import: CIM has no permittivity; GDM's default (PE) |

## Loads

Decision X7. `EnergyConsumer` → `DistributionLoad` + `LoadEquipment` + one `PhaseLoadEquipment` per phase conductor.
- **Power.** p and q come from `get_phase_loads` (kW, kVAr): the EnergyConsumerPhase values, else the total split
  evenly.
- **Connection.** Y and Yn → STAR, D → DELTA. Unset, I and G raise.
- **Load model.** Every phase gets the LoadResponseCharacteristic (`get_load_response`): the ZIP fractions as stored,
  or the voltage exponents. GDM still requires the fractions with exponents, so they are filled as constant power
  (`fills.ZIP_UNDER_EXPONENTS`); ditto then writes `Model=4`.
- `num_customers` is `customerCount` on every phase.

**DistributionLoad**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| bus | written | the bus of get_terminal_nodes |
| phases | written | get_phase_loads.phases: the phase conductors, no neutral |
| equipment | written | a LoadEquipment made for this load |

**LoadEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the load's name (X2) |
| phase_loads | written | one PhaseLoadEquipment per phase conductor |
| connection_type | written | phaseConnection: Y and Yn → STAR, D → DELTA; others raise |

**PhaseLoadEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | <load>_<phase> (X2) |
| real_power | written | get_phase_loads.per_phase p (kW): EnergyConsumerPhase, else the even split |
| reactive_power | written | get_phase_loads.per_phase q (kVAr) |
| z_real | written | pConstantImpedance (get_load_response, ZIP form; the exponent form writes fills.ZIP_UNDER_EXPONENTS (constant power)) |
| z_imag | written | qConstantImpedance |
| i_real | written | pConstantCurrent |
| i_imag | written | qConstantCurrent |
| p_real | written | pConstantPower |
| p_imag | written | qConstantPower |
| num_customers | written | EnergyConsumer.customerCount, the same on every phase; unset is None |
| min_voltage_pu | unset | untranscribed on import: no home on LoadResponseCharacteristic |
| max_voltage_pu | unset | untranscribed on import: no home on LoadResponseCharacteristic |
| cutoff_voltage_pu | unset | untranscribed on import: no home on LoadResponseCharacteristic |
| active_power_voltage_exponent | written | get_load_response.p_exponent; None in the ZIP form |
| reactive_power_voltage_exponent | written | get_load_response.q_exponent; None in the ZIP form |

## Capacitors

Decisions X7, X8. `LinearShuntCompensator` → `DistributionCapacitor` + `CapacitorEquipment` + one
`PhaseCapacitorEquipment` per phase conductor.
- **Rating.** Q comes from `get_shunt_reactive_power` on `nomU`. The rating is all sections in, split evenly by
  phase. `num_banks` is maximumSections, and `num_banks_on` the actual sections; a fraction of a section raises.
  `rated_voltage` is nomU: line to line on balanced ABC and for delta, line to ground for a wye off ABC (the
  importer's `nominal_voltage` inverted).
- **State.** One entry, as ditto writes it: on when any section is in. ditto 0.1.8 counts `True` entries as banks
  on, so one entry is right for a single-bank capacitor.
- **Controller.** From `get_equipment_control`, picked by mode:

  | mode | controller | on / off |
  |---|---|---|
  | voltage | VoltageCapacitorController | (target ∓ deadband / 2) / pt_ratio, V |
  | currentFlow | CurrentCapacitorController | (target ∓ deadband / 2) / ct_ratio, A |
  | activePower | ActivePowerCapacitorController | target ∓ deadband / 2, W |
  | reactivePower | ReactivePowerCapacitorController | target ∓ deadband / 2, VAr |

  - An unset ratio is 1, and an unset deadband is 0.
  - `delay_on` is `aVRDelay`.
  - Any other mode raises.
  - A disabled control (`enabled` or `controlEnabled` false) exports no controller, because GDM has no enabled flag.
  - A GDM capacitor controller names no monitored element, so a control on any terminal but the capacitor's own
    raises.
  - CIM holds one control per compensator, so per-phase copies come back as one controller.
  - ditto 0.1.8 writes no capacitor controllers.

**DistributionCapacitor**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| bus | written | the bus of get_terminal_nodes |
| phases | written | get_shunt_reactive_power.phases: the phase conductors, no neutral |
| controllers | rule | one controller from get_equipment_control, by mode (CONTROLLERS); none when there is no control or it is disabled (enabled or controlEnabled false) |
| equipment | written | a CapacitorEquipment made for this capacitor |
| state | rule | one entry, as ditto writes it: sections (actual) > 0 |

**CapacitorEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the capacitor's name (X2) |
| phase_capacitors | written | one PhaseCapacitorEquipment per phase conductor |
| connection_type | written | phaseConnection: Y and Yn → STAR, D → DELTA; others raise |
| rated_voltage | written | get_shunt_reactive_power(voltage='nominal').voltage: nomU (kV) |
| voltage_type | rule | line-to-line on balanced ABC and for delta (nomU across a branch), else line-to-ground: the importer's nominal_voltage inverse |

**PhaseCapacitorEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | <capacitor>_<phase> (X2) |
| resistance | unset | untranscribed on import: no home on LinearShuntCompensator; GDM's default 0 |
| reactance | unset | untranscribed on import: no home on LinearShuntCompensator; GDM's default 0 |
| rated_reactive_power | written | get_shunt_reactive_power(sections='maximum', voltage='nominal').per_phase (kVAr) |
| num_banks_on | written | get_shunt_reactive_power(sections='actual').sections; a fraction raises |
| num_banks | written | get_shunt_reactive_power(sections='maximum').sections |

**VoltageCapacitorController**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the capacitor's name (X2) |
| delay_on | written | get_equipment_control.delay (aVRDelay, s); unset is None |
| delay_off | unset | untranscribed on import: CIM has one delay, aVRDelay |
| dead_time | unset | untranscribed on import: no CIM home |
| on_voltage | rule | (target − deadband / 2) / pt_ratio (V) |
| off_voltage | rule | (target + deadband / 2) / pt_ratio (V) |
| pt_ratio | rule | ptRatio; unset is 1, the targets as stored |

**CurrentCapacitorController**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the capacitor's name (X2) |
| delay_on | written | get_equipment_control.delay (aVRDelay, s); unset is None |
| delay_off | unset | untranscribed on import: CIM has one delay, aVRDelay |
| dead_time | unset | untranscribed on import: no CIM home |
| on_current | rule | (target − deadband / 2) / ct_ratio (A) |
| off_current | rule | (target + deadband / 2) / ct_ratio (A) |
| ct_ratio | rule | ctRatio; unset is 1, the targets as stored |

**ActivePowerCapacitorController**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the capacitor's name (X2) |
| delay_on | written | get_equipment_control.delay (aVRDelay, s); unset is None |
| delay_off | unset | untranscribed on import: CIM has one delay, aVRDelay |
| dead_time | unset | untranscribed on import: no CIM home |
| on_power | rule | (target − deadband / 2) (W) |
| off_power | rule | (target + deadband / 2) (W) |

**ReactivePowerCapacitorController**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the capacitor's name (X2) |
| delay_on | written | get_equipment_control.delay (aVRDelay, s); unset is None |
| delay_off | unset | untranscribed on import: CIM has one delay, aVRDelay |
| dead_time | unset | untranscribed on import: no CIM home |
| on_power | rule | (target − deadband / 2) (VAr) |
| off_power | rule | (target + deadband / 2) (VAr) |

## Transformers

Decision X3. `PowerTransformer` → `DistributionTransformer` on a `DistributionTransformerEquipment`:
- **Model.** `get_transformer_model` reads the transformer's one unit, in kV and kVA: its tank, or the transformer
  itself by ends. It reads any CIM form (by ends, by phase ends, by template tank ends, by template lugs).
  - Each winding is a `WindingEquipment` on the bus its end lands on.
  - The mesh gives `coupling_sequences`, 0-based (as ditto writes and requires them), and `winding_reactances`, in
    % on winding 1's ratedS.
  - The core's g and b are `pct_no_load_loss` (unset 0) and `magnetizing_current_pct` (unset None).
- **Catalog.** A tank on a TransformerTankConfiguration shares one GDM equipment per (configuration, values), named
  after the configuration. Any other transformer (DSS by ends or by phase ends) gets its own, named after it.
  - A CoolingInfo AssetDatasheet makes it a `PowerTransformerEquipment`, with `cooling_class` its typeOfCooling.
  - Its `vector_group` is made from the connections, as the importer checks it, with no neutral mark: `Dyn1` comes
    back `Dy1`.
- **Winding.**
  - `rated_voltage` is the coil: baseU, else ratedU (over √3 on a wye). It is line to line on a delta and line to
    ground on a wye, as ditto's DSS reader writes it.
  - `rated_power` is ratedS, but a center-tap half is 2 × ratedS, its baseS (DSS-2).
  - `resistance` is the winding's r moved to its own rated_power.
  - `num_phases` is 3 for a winding on A, B and C, else 1 (a 1-phase delta spans two conductors).
  - `connection_type`: Y, Yn and I (a center tap's split end) are STAR, and D is DELTA; others raise.
  - `is_grounded` is `grounded`. Unset is False on a delta and raises on a wye.
- **Taps.** Each winding's actual ratio from its end's RatioTapChanger (`get_tap_ratio`) goes on the catalog winding,
  one per phase. The range is highStep − lowStep and the low and high ratios; with no tap changer it is GDM's default.
  The instance's `tap_positions` is left unset. ditto 0.1.8's OpenDSS Transformer has no `Tap_wdg`, so an instance
  tap never reaches OpenDSS; on the catalog it does. Instances on different taps therefore split the catalog
  (`ln1_2`). The importer takes either (G4).
- **Phases.** `winding_phases` are each winding's phases, but a 1-phase wye coil on A, B or C lists no N. ditto 0.1.8
  writes `Phases` as the length of winding 1's list, so `[B, N]` would be a 2-phase unit. The importer adds the N
  back. A center tap's halves keep theirs (`[S1, N]`, `[N, S2]`).
- **Center tap.** Three windings, the last two on one end (DSS-2).
- **Full-load loss.** `loadLoss` on the tank or its configuration, as % of winding 1's ratedS. Unset, it is windings 1
  and 2's r summed: OpenDSS's %loadloss, which a by-ends transformer from DSS holds as r.
- **Fail fast.**
  - A bank of several tanks raises `no GDM export yet`: GDM holds one equipment per transformer.
  - A transformer whose RatioTapChanger has a TapChangerControl (an LTC) raises `no GDM export yet`.
  - An unset ratedS or r raises.

Every tap assumption here, with why and how to revisit it, is in [`TAP_ASSUMPTIONS.md`](TAP_ASSUMPTIONS.md).

**DistributionTransformer**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| buses | written | each winding's end's ConnectivityNode, in winding order (a center tap's halves share one) |
| winding_phases | rule | each winding's phases from get_transformer_model (its end's terminal, or a coil's two phase ends), a 1-phase wye coil without its N (ditto 0.1.8 counts the list as Phases) |
| tap_positions | unset | the taps are the equipment's (ditto 0.1.8 writes no instance tap) |
| equipment | written | the DistributionTransformerEquipment (or PowerTransformerEquipment) made for it |

**DistributionTransformerEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the TankConfiguration's name, <configuration>_<n> for its n-th values (X3); else the transformer's |
| mounting | unset | untranscribed on import: no CIM home; GDM's default |
| pct_no_load_loss | rule | get_transformer_model core g (% on winding 1's ratedS); unset is 0 |
| pct_full_load_loss | rule | loadLoss on the tank or its configuration, % of winding 1's ratedS; unset is windings 1 and 2's r summed (OpenDSS's %loadloss) |
| windings | written | one WindingEquipment per get_transformer_model winding |
| coupling_sequences | written | the mesh pairs, 0-based (as ditto writes them) |
| winding_reactances | written | the mesh x, % on winding 1's ratedS |
| is_center_tapped | rule | three windings, the last two on one end (DSS-2) |
| magnetizing_current_pct | written | get_transformer_model core b (% on winding 1's ratedS); unset is None |

**PowerTransformerEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the TankConfiguration's name, <configuration>_<n> for its n-th values (X3); else the transformer's |
| mounting | unset | untranscribed on import: no CIM home; GDM's default |
| pct_no_load_loss | rule | get_transformer_model core g (% on winding 1's ratedS); unset is 0 |
| pct_full_load_loss | rule | loadLoss on the tank or its configuration, % of winding 1's ratedS; unset is windings 1 and 2's r summed (OpenDSS's %loadloss) |
| windings | written | one WindingEquipment per get_transformer_model winding |
| coupling_sequences | written | the mesh pairs, 0-based (as ditto writes them) |
| winding_reactances | written | the mesh x, % on winding 1's ratedS |
| is_center_tapped | rule | three windings, the last two on one end (DSS-2) |
| magnetizing_current_pct | written | get_transformer_model core b (% on winding 1's ratedS); unset is None |
| vector_group | rule | made from the windings' connections, ANSI phasing, no neutral marks (the importer's vector_group) |
| cooling_class | written | typeOfCooling of the unit's CoolingInfo AssetDatasheet; one is what makes it a PowerTransformerEquipment |
| fluid_type | unset | untranscribed on import: no Specification builder |

**WindingEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | unset | untranscribed on import: inline, no CIM object of its own |
| resistance | written | the winding's r, moved to its own rated_power; unset raises (a regulator: half the mesh r) |
| is_grounded | rule | grounded; unset is False on a delta and raises on a wye (a regulator: unset is False, B27) |
| rated_voltage | rule | the coil: baseU, else ratedU (/ √3 on a wye) |
| voltage_type | rule | line-to-line on a delta, line-to-ground on a wye |
| rated_power | rule | ratedS (kVA); a center tap half 2 × ratedS (its baseS) |
| num_phases | rule | 3 when the winding's phases hold A, B and C, else 1 |
| connection_type | written | connectionKind: Y, Yn and I (a center tap's split end) → STAR, D → DELTA; others raise (a regulator: STAR) |
| tap_positions | rule | get_tap_ratio(which='actual') of the end's RatioTapChanger, one per phase; none is 1.0 (a regulator's are 1.0: its tap is the instance's) |
| total_taps | rule | highStep − lowStep from the end's RatioTapChanger (get_tap_steps, get_tap_ratio); none: GDM's default |
| min_tap_pu | rule | get_tap_ratio(which='low') from the end's RatioTapChanger (get_tap_steps, get_tap_ratio); none: GDM's default |
| max_tap_pu | rule | get_tap_ratio(which='high') from the end's RatioTapChanger (get_tap_steps, get_tap_ratio); none: GDM's default |

## Regulators

Decisions X3, X8. `VoltageRegulator` → `DistributionRegulator`, one per CIM unit, with one `RegulatorController`:
- **One per unit.** ditto 0.1.8 writes a GDM regulator as one OpenDSS Transformer, whose RegControls then gang its
  phases. A bank of single-phase units exported as one 3-phase regulator would lose each unit's own tap, so each unit
  is its own GDM regulator. The importer names a bank's units `<regulator>_<phase>` (`rb_a`), so each has a name of its
  own and a reimport gives the same mRIDs. Only a single-phase unit of two ends is exported; anything else raises
  `no GDM export yet`.
- **Windings.** The two AutoTransformerEnds (`get_transformer_model`, form AUTO). Each is wye, on baseU line to ground,
  rated ratedS, ungrounded when `grounded` is unset (B27: the importer can't write it). A winding's phases have no N,
  as a transformer's 1-phase wye coil.
- **Impedance.** A mesh between the ends (DSS-origin, the engine's stand-in) gives x, r / 2 on each winding, and
  `pct_full_load_loss` r. The importer has no home for a GDM regulator's impedance (no AutoTransformer configuration in
  cim18v17), so without a mesh it is an X4 fill: r 0.01 %, x 0.01 %, the near-ideal step regulator of the IEEE test
  feeders. A zero impedance is singular in OpenDSS. There is no core.
- **Equipment.** The tap changer's TapChangerInfo, shared and named after it (B17), else the regulator's own. The taps
  on it are nominal; the tap is the instance's (`tap_positions`, `get_tap_ratio(which='actual')` on the tapped
  winding), as a controller's state.
- **Controller.** From `get_tap_changer_control`, the importer's inverse:
  - The PT-secondary settings are the primary values / ptRatio: `v_setpoint`, `bandwidth`, `min_v_limit`,
    `max_v_limit`. An unset ptRatio is 1.
  - Line drop: `ldc_R`, `ldc_X` = ohms × ctRating / ptRatio, in volts. An unset one is 0 V, because ditto 0.1.8 writes
    no RegControl without them.
  - An unset limit is the setpoint over the whole tap range (setpoint × the low and high ratios), because GDM needs a
    limit above 0 V. It never acts before the taps run out.
  - `max_step` is the X4 rule highStep − lowStep.
  - `tapped_winding` is the tapped end's number. `controlled_bus` is the monitored terminal's bus, and
    `controlled_phase` the monitored phase (unset, the regulator's).
  - GDM requires one controller per phase, so no TapChangerControl, or a disabled one, raises. A mode other than
    voltage raises.
- **ditto.** ditto 0.1.8 writes every RegControl with `Bus=<controlled bus>`, which in OpenDSS replaces line drop
  compensation, and it drops the regulator's initial tap. On IEEE13 the taps then settle at 2 instead of 9, 6 and 9
  (an upstream report).

Every tap assumption here, with why and how to revisit it, is in [`TAP_ASSUMPTIONS.md`](TAP_ASSUMPTIONS.md).

**DistributionRegulator**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2): one per VoltageRegulator unit |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| buses | written | each AutoTransformerEnd's ConnectivityNode, end 1 (S) first |
| winding_phases | rule | each end's phase conductor, without the N its coil returns to (as a transformer's 1-phase wye coil) |
| tap_positions | rule | get_tap_ratio(which='actual') on the tapped winding, 1.0 on the other |
| equipment | written | the DistributionTransformerEquipment of the tap changer's TapChangerInfo (shared, X3), else the regulator's own |
| controllers | written | one RegulatorController from get_tap_changer_control; GDM requires one per phase, so no control or a disabled one (enabled or controlEnabled false) raises |

**RegulatorController**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the regulator's name (X2) |
| tapped_winding | written | the endNumber of the end the RatioTapChanger is on |
| delay | written | initialDelay (s); unset is None |
| v_setpoint | rule | targetValue / pt_ratio (V) |
| min_v_limit | rule | minLimitVoltage / pt_ratio (V); unset (GDM needs > 0) is v_setpoint × min_tap_pu, the tap range's reach, so it never acts first |
| max_v_limit | rule | maxLimitVoltage / pt_ratio (V); unset is v_setpoint × max_tap_pu |
| pt_ratio | rule | ptRatio (tap changer and control agreed); unset is 1, the targets as stored |
| use_ldc | rule | lineDropCompensation; unset is False |
| is_reversible | rule | reversible; unset is False |
| ldc_R | rule | lineDropR × ctRating / pt_ratio (V); unset is 0 V (ditto 0.1.8 needs a value) |
| ldc_X | rule | lineDropX × ctRating / pt_ratio (V); unset is 0 V (ditto 0.1.8 needs a value) |
| ct_primary | written | ctRating (A); unset is None |
| max_step | fill | highStep − lowStep: no limit per iteration (§3.1) |
| bandwidth | rule | targetDeadband / pt_ratio (V); unset is 0 |
| controlled_bus | written | the bus of the monitored Terminal |
| controlled_phase | rule | monitoredPhase; unset is the regulator's phase |

## DER

X4, X7, X8. `PowerElectronicsConnection` → one `DistributionSolar` or `DistributionBattery` per PowerElectronicsUnit.
A PhotoVoltaicUnit gives a solar and a BatteryUnit a battery; another unit raises.
- **Units.** GDM holds one DC device per inverter. So a connection of several units (a PV array and a battery behind
  one inverter) is chopped by `get_inverter_units`, the DSS exporter's rule: each unit's share is its maxP over the
  units' total. One unit is the whole connection, and its DER takes the connection's name and uuid. Several each
  take their unit's name and uuid (`uri()`).
- **Output.** Each DER's p is its unit's own, else its share of the connection's p; its q is its share of the
  connection's q. Both are in the generation sign (kW and kVAr), on the connection's phase conductors.
- **Inverter.** `rated_apparent_power` is the unit's share of the connection's ratedS (`get_inverter_rating`). Its
  InverterInfo shares it (X3), so units of different shares split it (`<info>_2`); without one it is the DER's own,
  named after it. An unnamed InverterInfo under name source `name` keeps
  GDM's default name `''` (Names).
  Cut-in, cut-out, efficiency and the ramp limits have no InverterInfo slot: fills (0 %, 0 %, 100 %, None).
- **Rating voltage.** The equipment's `rated_voltage` is the connection's ratedU in the importer's `system_voltage`
  form, inverted. It is line to line on three phases, and otherwise line to ground: half on a split-phase leg, and
  ratedU / √3 on any other phase.
- **Solar.** `rated_power` is the PhotoVoltaicUnit's maxP; unset raises. The panel's resistance and reactance are
  fills (0 %). **Irradiance** is `PhotoVoltaicUnit.irradiance` when set (B16b). Unset, it is a rule, not a fill:
  ditto 0.1.8 writes no `active_power`, and OpenDSS makes `Pmpp × Irradiance`, so irradiance is p / maxP × 1 kW/m²,
  and the PV makes CIM's p (`test_export_ditto.py` sets the atoms' irradiance to that share).
- **Battery.** `rated_power` is the BatteryUnit's maxP, with minP unset or −maxP (GDM has one rating both ways);
  otherwise it raises. ratedE and the two efficiencies are required; idling efficiency is a fill (100 %: idlingP is
  a power). The unit's BatteryInfo shares the equipment; without one it is the DER's own. ditto 0.1.8 has no battery
  writer, so an exported battery does not reach OpenDSS.
- `controller` is None: inverter controllers are not in CIM (X8).

**DistributionSolar**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2): the connection's for one unit, else the unit's |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| bus | written | the bus of get_terminal_nodes |
| phases | written | get_der_output.phases: the phase conductors, no neutral (balanced ABC on none, G3) |
| active_power | written | get_inverter_units(sign='generation') p (kW): the unit's own, else its share of the connection's |
| reactive_power | written | get_inverter_units(sign='generation') q (kVAr): its share of the connection's |
| controller | unset | inverter controllers are not in CIM (PENDING on import, X8) |
| inverter | written | the InverterEquipment of the connection's InverterInfo (shared, X3), else the DER's own |
| irradiance | rule | PhotoVoltaicUnit.irradiance; unset, p / the panel's maxP × 1 kW/m² (standard test conditions): what OpenDSS makes of it (Pmpp × Irradiance) is CIM's p |
| equipment | written | a SolarEquipment made for this DER |

**DistributionBattery**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2): the connection's for one unit, else the unit's |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| bus | written | the bus of get_terminal_nodes |
| phases | written | get_der_output.phases: the phase conductors, no neutral (balanced ABC on none, G3) |
| active_power | written | get_inverter_units(sign='generation') p (kW): the unit's own, else its share of the connection's |
| reactive_power | written | get_inverter_units(sign='generation') q (kVAr): its share of the connection's |
| controller | unset | inverter controllers are not in CIM (PENDING on import, X8) |
| inverter | written | the InverterEquipment of the connection's InverterInfo (shared, X3), else the DER's own |
| equipment | written | the BatteryEquipment of the unit's BatteryInfo (shared, X3), else the DER's own |

**SolarEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the DER's name (X2) |
| rated_power | written | get_photovoltaic_unit(sign='generation').max_p (kW); unset raises |
| power_temp_curve | unset | untranscribed on import: until the Curve builder (B12) |
| resistance | fill | fills.SOLAR_RESISTANCE, 0 % (§3.1) |
| reactance | fill | fills.SOLAR_REACTANCE, 0 % (§3.1) |
| rated_voltage | rule | the connection's ratedU (get_inverter_rating), line to line on three phases, else line to ground: / 2 on a split-phase leg, / √3 otherwise (the importer's system_voltage inverted) |
| voltage_type | rule | line-to-line on A, B and C, else line-to-ground |

**BatteryEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the BatteryInfo's name (X2); else the DER's |
| rated_energy | written | get_battery_unit.rated_e (kWh); unset raises |
| rated_power | rule | get_battery_unit(sign='generation').max_p (kW), with min_p unset or -max_p (GDM has one rating both ways); else raises |
| charging_efficiency | written | get_battery_unit.charging_efficiency (%); unset raises |
| discharging_efficiency | written | get_battery_unit.discharging_efficiency (%); unset raises |
| idling_efficiency | fill | fills.BATTERY_IDLING_EFFICIENCY, 100 % (§3.1) |
| rated_voltage | rule | the connection's ratedU (get_inverter_rating), line to line on three phases, else line to ground: / 2 on a split-phase leg, / √3 otherwise (the importer's system_voltage inverted) |
| voltage_type | rule | line-to-line on A, B and C, else line-to-ground |

**InverterEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the InverterInfo's name (X2), '' when it has none under name source 'name' (GDM's default, which the importer reads as unnamed); else the DER's |
| rated_apparent_power | written | get_inverter_rating.rated_s × the unit's share (kVA) |
| rise_limit | fill | fills.INVERTER_RAMP_LIMIT, None (§3.1) |
| fall_limit | fill | fills.INVERTER_RAMP_LIMIT, None (§3.1) |
| cutout_percent | fill | fills.INVERTER_CUTOUT_PERCENT, 0 % (§3.1) |
| cutin_percent | fill | fills.INVERTER_CUTIN_PERCENT, 0 % (§3.1) |
| dc_to_ac_efficiency | fill | fills.INVERTER_EFFICIENCY, 100 % (§3.1) |
| eff_curve | unset | untranscribed on import: until the Curve builder (B12) |

## Reactors

X4. `SeriesCompensator` → `DistributionReactor` between its two terminals' buses, the importer's §21 inverted
(`exporter/reactor.py`).
- **Impedance.** `get_series_compensator` gives r and x per phase, lumped, which go on an inline ReactorEquipment
  named after the reactor (the importer builds no SeriesReactorInfo).
- GDM's reactor has no zero sequence: an r0 or x0 other than r or x raises (no mutual coupling, as the DSS goldens
  write r0 = r, x0 = x). It has no varistor either: `varistorPresent` raises. `compensatorType` is not read.
- `phases` are the terminals' conductors (`get_conductor_phases`; none is ABC, G3).
- `length` has no CIM home: a fill, 1 m. The impedance is lumped, and ditto writes no length for a reactor.
- GDM's reactor has no ampacity, so the compensator's current limits are not exported.

**DistributionReactor**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | Names (X2) |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| buses | written | the buses of get_terminal_nodes: Terminal 1, Terminal 2 |
| length | fill | fills.REACTOR_LENGTH, 1 m: the impedance is lumped; ditto writes no length |
| phases | written | get_conductor_phases (balanced ABC on none, G3) |
| equipment | written | a ReactorEquipment made for this reactor |

**ReactorEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | written | the uri() (Identity.identifier) of the CIM object it is made from (Names.own); a part with no CIM object of its own: a uuid5 of its owner's, on its class and suffix (Names.part) |
| name | written | the reactor's name (X2) |
| resistance | written | get_series_compensator.r (ohm); r0 other than r raises |
| reactance | written | get_series_compensator.x (ohm); x0 other than x raises |

## Tests

- `test_export_round_trip.py`: every importer golden is loaded, exported with CIM names, imported again, and must
  match itself. Every family is exported, the reference system (`e2e`) included. The exceptions:
  - Each reimport is named after its golden's `Model` header, which seeds the hashed PhaseImpedanceData
    identifiers.
  - The DER golden lists the unnamed inverter's mRID: the importer names it by the exported uuid (B18), not the
    atom's pinned one.
  - The regulator golden lists its differences (`CIM_DIFFERENCES`). Its catalog TransformerTankConfigurations, which
    no regulator links, are rebuilt from the per-unit equipment and the impedance fill.
- `test_export_gdm_level.py`: the export against the atom system it came from (`gdm_compare.gdm_differences`), one
  test per family, every difference listed with its reason. It also checks:
  - the lines' CIM fixed point, geometry included;
  - a split of a catalog by ampacity, and of a transformer catalog by tap;
  - that a second export changes nothing;
  - the JSON round trip;
  - that the loaded golden and the built model export alike.
- `test_export_framework.py`:
  - slot coverage, the naming switch, a shared name, the uuids (the CIM `uri()`, and a part's uuid5), the system
    name, unset source impedance, `phase_angle`;
  - the fills WARNING, the placeholder names, the switch controller rule;
  - fail-fast: a fuse's differing normal state, a Sectionaliser, a control on another terminal, a battery rated
    differently each way, a coupled reactor, a reactor with a varistor;
  - a hybrid inverter: one DER per unit, each its maxP share, named and identified by its unit;
  - a geometry line's first conductor carrying the line's ratings, the others their wire's;
  - a disabled control, and the capacitor targets;
  - a transformer under tap control, a bank of tanks, a 3-phase regulator and a regulator without an enabled control
    (all raise);
  - the regulator settings, and the unset limits and line drop.
- `test_export_ditto.py`: the export through ditto's OpenDSS writer and the OpenDSS engine.
  - It writes, compiles and solves.
  - Without capacitors, it solves to the original's node voltages within 1e-4 pu. ditto misrates the original's
    capacitors, whose buses are line to line.
  - The comparison includes the geometry lines, the reactors and the transformers, but not t_ln: ditto can't write the original's
    1-based couplings or its instance tap. It leaves out the DER: ditto writes the original's PV kV from its line to
    line bus as if line to ground, and the atoms' irradiance is not their output's share.
  - Each exported PV makes the p and q CIM holds, its irradiance set to its output's share of the panel.
  - Exported load series become one LoadShape per load, `UseActual=yes`, in kW and kvar (T1, T6).
  - With capacitors and t_ln, it still solves.
  - An exported regulator bank (rb alone) holds its band, 121–123 V on its PT.
  - A strict xfail pins ditto 0.1.8's missing CircuitBreaker and Disconnector equipment writers. ditto writes their
    lines with no LineCode, and OpenDSS stops.
