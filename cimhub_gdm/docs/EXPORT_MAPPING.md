# CIM → GDM export mapping

**Status:**
- X1 (framework, shell, buses, source) built 2026-11-09, for review.
- X2 (switches, matrix and sequence lines, loads, capacitors) built 2026-11-09. At the user's request ("implement X2
  so that ditto gets what it needs"), its code went in before this section was approved. Two X1 decisions changed
  because ditto needs them:
  - buses are now rated line to ground (X6);
  - the switch matrices are OpenDSS's 1 mΩ switch, not zero.

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
`uri`; default `mrid`). GDM names are free text, so nothing is sanitized. Two objects on one name in one GDM class
raise, naming both mRIDs.
- Inline equipment, controllers included, take their instance's name (`VoltageSourceEquipment src`,
  `CapacitorEquipment vc`).
- A per-phase child takes `<instance>_<phase>` (`src_A`).
- Placeholder protection takes `<fuse>_tcc_placeholder` or `<recloser>_ctrl_placeholder` (X5).
- A shared catalog takes the catalog's name, or `<catalog>_<n>` for its n-th instance value (X3).
- The system's name is `system_name=`, else the one Feeder's exported name. Several Feeders raise.

## Shell

`Feeder` → `DistributionFeeder`, `Substation` → `DistributionSubstation`, whose `feeders` are its
`NormalEnergizedFeeder`s, sorted by name. Feeders are exported first.

**DistributionFeeder**

| GDM field | kind | from / why |
|---|---|---|
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
| name | written | Names (X2) |

**DistributionSubstation**

| GDM field | kind | from / why |
|---|---|---|
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
| name | written | the source's name (X2) |
| sources | written | one PhaseVoltageSourceEquipment per phase, all with the source's values |

**PhaseVoltageSourceEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
| name | written | the switch's name (X2) |
| construction | unset | untranscribed on import: no home on a CIM switch; GDM's default, overhead |
| r_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal: a CIM switch is ideal, and a zero matrix is singular in OpenDSS |
| x_matrix | fill | fills.switch_matrices, 1 ohm/km diagonal |
| c_matrix | fill | fills.switch_matrices, zero |
| ampacity | written | required_qty(ratedCurrent, 'A') |

**MatrixImpedanceFuseEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
| name | written | the switch's name (X2) |
| delay | fill | fills.SWITCH_CONTROLLER_DELAY, 0 s: no CIM home |
| normal_state | written | get_switch_state(which='normal'): open → 'open', closed → 'close' |
| is_locked | fill | fills.SWITCH_CONTROLLER_LOCKED, False: no CIM home |

**TimeCurrentCurve**

| GDM field | kind | from / why |
|---|---|---|
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
| name | written | <fuse>_tcc_placeholder (X5) |
| curve_x | fill | TimeCurrentCurve.example() |
| curve_y | fill | TimeCurrentCurve.example() |

**DistributionRecloserController**

| GDM field | kind | from / why |
|---|---|---|
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
- **Not here.** A line with a WireConfiguration raises `no GDM export yet for geometry lines`: X4 exports it as
  native geometry, never a computed matrix. A line with no PerLengthImpedance (lumped r, x only) raises.
- `length` is `length` in m.

The importer's OperationalLimitTypes have no `durationKind`, because `add_limit_type` has no keyword for it (B22 b,
`GDM_MAPPING.md` §14). `get_current_limits` needs it, so GDM-origin CIM can't export its lines yet. The tests set it
(`gdm_atoms.type_limit_durations`) until the builder has it. DSS-origin CIM writes it (the core `common` shape).

**MatrixImpedanceBranch**

| GDM field | kind | from / why |
|---|---|---|
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
| name | written | Names (X2) |
| substation | written | the EquipmentContainer when it is a Substation or VoltageLevel (containers) |
| feeder | written | the EquipmentContainer when it is a Feeder (containers) |
| in_service | rule | get_in_service(which='actual'); unset is in service, GDM's default |
| buses | written | get_terminal_nodes |
| length | written | required_qty(length, 'm') |
| phases | written | get_conductor_phases: ACLineSegmentPhase order, the matrix's row order |
| equipment | written | the SequenceImpedanceBranchEquipment for (PerLengthSequenceImpedance, ampacity) |

**MatrixImpedanceBranchEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
| name | written | the catalog's name; <catalog>_<n> for its n-th ampacity (X3) |
| construction | unset | untranscribed on import: no home on PerLengthImpedance; GDM's default |
| r_matrix | written | get_line_phase_impedance_matrix.r (ohm/km), the lower triangle mirrored |
| x_matrix | written | get_line_phase_impedance_matrix.x (ohm/km) |
| c_matrix | rule | get_line_phase_impedance_matrix.b (S/km) / 2πf; unset b is zero; a non-zero g raises: GDM has no shunt conductance |
| ampacity | written | get_current_limits(line).normal (A) of the lines on it; unset raises |

**SequenceImpedanceBranchEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
| name | written | the catalog's name; <catalog>_<n> for its n-th ampacity (X3) |
| pos_seq_resistance | written | get_line_sequence_impedance_per_length.r (ohm/km) |
| zero_seq_resistance | written | get_line_sequence_impedance_per_length.r0; unset raises |
| pos_seq_reactance | written | get_line_sequence_impedance_per_length.x |
| zero_seq_reactance | written | get_line_sequence_impedance_per_length.x0; unset raises |
| pos_seq_capacitance | rule | b (S/km) / 2πf; unset is zero; a non-zero g raises |
| zero_seq_capacitance | rule | b0 (S/km) / 2πf; unset is zero; a non-zero g0 raises |
| ampacity | written | get_current_limits(line).normal (A) of the lines on it; unset raises |

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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
| name | written | the load's name (X2) |
| phase_loads | written | one PhaseLoadEquipment per phase conductor |
| connection_type | written | phaseConnection: Y and Yn → STAR, D → DELTA; others raise |

**PhaseLoadEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
| name | written | the capacitor's name (X2) |
| phase_capacitors | written | one PhaseCapacitorEquipment per phase conductor |
| connection_type | written | phaseConnection: Y and Yn → STAR, D → DELTA; others raise |
| rated_voltage | written | get_shunt_reactive_power(voltage='nominal').voltage: nomU (kV) |
| voltage_type | rule | line-to-line on balanced ABC and for delta (nomU across a branch), else line-to-ground: the importer's nominal_voltage inverse |

**PhaseCapacitorEquipment**

| GDM field | kind | from / why |
|---|---|---|
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
| name | written | <capacitor>_<phase> (X2) |
| resistance | unset | untranscribed on import: no home on LinearShuntCompensator; GDM's default 0 |
| reactance | unset | untranscribed on import: no home on LinearShuntCompensator; GDM's default 0 |
| rated_reactive_power | written | get_shunt_reactive_power(sections='maximum', voltage='nominal').per_phase (kVAr) |
| num_banks_on | written | get_shunt_reactive_power(sections='actual').sections; a fraction raises |
| num_banks | written | get_shunt_reactive_power(sections='maximum').sections |

**VoltageCapacitorController**

| GDM field | kind | from / why |
|---|---|---|
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
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
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
| name | written | the capacitor's name (X2) |
| delay_on | written | get_equipment_control.delay (aVRDelay, s); unset is None |
| delay_off | unset | untranscribed on import: CIM has one delay, aVRDelay |
| dead_time | unset | untranscribed on import: no CIM home |
| on_power | rule | (target − deadband / 2) (W) |
| off_power | rule | (target + deadband / 2) (W) |

**ReactivePowerCapacitorController**

| GDM field | kind | from / why |
|---|---|---|
| uuid | unset | GDM makes a fresh one; the importer never copies it either |
| name | written | the capacitor's name (X2) |
| delay_on | written | get_equipment_control.delay (aVRDelay, s); unset is None |
| delay_off | unset | untranscribed on import: CIM has one delay, aVRDelay |
| dead_time | unset | untranscribed on import: no CIM home |
| on_power | rule | (target − deadband / 2) (VAr) |
| off_power | rule | (target + deadband / 2) (VAr) |

## Tests

- `test_export_round_trip.py`: every importer golden is loaded, exported with CIM names, imported again, and must
  match itself (`assert_import_matches`). Families not exported yet must raise `no GDM export yet`. The line golden
  still raises, because it holds geometry lines (X4). The `EXPORTED` set grows phase by phase.
- `test_export_gdm_level.py`: the export against the atom system it came from (`gdm_compare.gdm_differences`), one
  test per family, every difference listed with its reason. The X2 tests drop the geometry lines and catalogs
  (`gdm_atoms.without_geometry`). It also checks:
  - the matrix and sequence lines' CIM fixed point;
  - a split of a catalog by ampacity;
  - that a second export changes nothing;
  - the JSON round trip;
  - that the loaded golden and the built model export alike.
- `test_export_framework.py`:
  - slot coverage, the naming switch, a name clash, the system name, unset source impedance, `phase_angle`;
  - the fills WARNING, the placeholder names, the switch controller rule;
  - fail-fast: a fuse's differing normal state, a Sectionaliser, a geometry line, a control on another terminal;
  - a disabled control, and the capacitor targets.
- `test_export_ditto.py`: the export through ditto's OpenDSS writer and the OpenDSS engine.
  - It writes, compiles and solves.
  - Without capacitors, it solves to the original's node voltages within 1e-4 pu. ditto misrates the original's
    capacitors, whose buses are line to line.
  - With capacitors, it still solves.
  - A strict xfail pins ditto 0.1.8's missing CircuitBreaker and Disconnector equipment writers. ditto writes their
    lines with no LineCode, and OpenDSS stops.
