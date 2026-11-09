# CIM → GDM exporter: plan

**Status:** plan approved by the user 2026-11-09 (X4, X5 and X11 as the user decided them). Both built 2026-11-09,
for review ([`EXPORT_MAPPING.md`](EXPORT_MAPPING.md)):
- X1;
- X2, built at the user's request so that ditto gets what it needs, without the geometry lines (X4).

ditto changed two decisions in X2: X6 (buses line to ground) and the §3.1 switch matrices (OpenDSS's 1 mΩ switch).
X3 is next. Branch `gdm-exporter`, made from `rc_1` at `7cbcf0c`, in the `~/CIMHub-gdm` worktree.

`GdmExporter(FormatExporter).to_model(network) -> DistributionSystem` is written fresh in `cimhub_gdm/exporter/`,
with one module per GDM component family. It reads every value through the core getters (`export-getters` skill)
and builds GDM pydantic objects. GDM has no file format of its own: `write_gdm(system, path)` calls
`DistributionSystem.to_json`, so `read_gdm` reads the file back. The old exporter (CIMHub_2_0, 2,374 lines,
cimhub_2026) is only the oracle. The importer's mapping (`GDM_MAPPING.md`) is the spec this inverts, and its
`FIELDS` tables say which GDM fields CIM holds.

## 1. Shape

- **Order and dispatch.** `EXPORT_ORDER` lists the modules in GDM reference order:
  1. substations and feeders;
  2. buses;
  3. catalogs (wire, geometry, matrix and sequence codes, transformer equipment);
  4. the source;
  5. switches, lines, transformers, regulators and reactors;
  6. loads and capacitors;
  7. DER.

  Each module has `CIM_CLASSES` and `export(obj, context)`, and returns GDM components. Shared catalogs are made once
  through a context cache keyed by the CIM object, plus the instance values the GDM equipment carries (§3, X3).
- **Coverage, both ways.**
  - Conducting equipment of a class no module exports raises, as DSS `_check_exported` does.
  - Every field of every GDM class the exporter writes has a slot entry. The slot says whether the field is written
    from a getter, set by a rule (with the rule), or left unset. A test fails on a GDM field with no entry, so a new
    GDM release can't add one silently.
- **Writer.** `write_gdm` sits in `gdm_writer.py`. With `gdm_reader.py`, it is the only module that touches the
  filesystem. `cim_to_gdm(network, destination, **opts)` is the convenience function.
- **Deprecation.** GDM 2.4 deprecates `gdm.distribution` in favour of `gdm.systems.distribution`. The exporter
  imports the new path. The importer moves to it in the same branch, as a mechanical change.

## 2. Phases

Each phase adds its own section to `EXPORT_MAPPING.md`, approved before its code (as the importer did): the slot
table, the rules, and the fail-fast list.

| # | content | getters (new in **bold**) |
|---|---|---|
| X0 | this plan, decisions X1-X11 (docs only) | none |
| X1 | framework: `GdmExporter`, `EXPORT_ORDER`, naming (X2), slot coverage; substations and feeders; buses (X6); the source; `write_gdm` and the JSON round trip; the test harness (§4) | `get_source`, `get_terminal_nodes`, `get_terminal_phases`, `get_base_voltage` |
| X2 | switches (X5); matrix and sequence lines; loads; capacitors and their controllers | `get_switch_state`, `get_current_limits`, `get_line_phase_impedance_matrix`, `get_line_sequence_impedance_per_length`, `get_phase_loads`, `get_load_response`, `get_shunt_reactive_power`, `get_regulating_control` |
| X3 | transformers (catalog and balanced), center taps, regulators and their controllers | `get_transformer_units`, `get_transformer_model`, `get_tap_steps`, `get_tap_ratio`, `get_tap_changer_control` |
| X4 | solar, battery, inverters; geometry lines with bare and concentric wire; reactors | `get_der_output`, `get_inverter_rating`, `get_photovoltaic_unit`, `get_battery_unit`, `get_spacing_xy`, `get_line_conductor_xy`, **`get_wire_info`**, **`get_series_compensator`** |
| X5 | the reference system round trip, the GDM-level loss list, docs, and the hand-off to `tests/cross_format/` (§4) | none |

X4's two new getters are also on DSS S6's list (`get_wire_info` in S6b, `get_series_compensator` in S6e). Who writes
them is X11.

## 3. Decisions (for approval)

| # | question | recommendation |
|---|---|---|
| X1 | API and system name | `to_model(network, *, name_source=None, system_name=None) -> DistributionSystem`, created with `auto_add_composed_components=True`. The system's name is `system_name`, else the one Feeder's export name (as DSS's circuit name, E1), else it raises, naming the feeders. The importer's `Model` header has no CIM object in the graph to read it from. |
| X2 | Names | The shared switch (`cimhub_core.names.export_name`, `name`/`mrid`/`uri`, default `mrid`, DSS E1), unchanged. There is no GDM sanitizer, since a GDM name is free text. Two objects of one GDM class on one name raise, naming both, because `get_component(cls, name)` would see only one. Inline GDM equipment (load, capacitor, source, switch, solar, inverter and battery equipment) is named after its instance, or after its AssetInfo (`inv_`, `batt_`) when it has one. Each per-phase child is named `<parent>_<phase>`. Round-trip tests run with `name_source="name"`, so a reimport gives the same mRIDs. |
| X3 | Catalogs | Keep CIM's sharing. PerLengthPhaseImpedance → MatrixImpedanceBranchEquipment. PerLengthSequenceImpedance → SequenceImpedanceBranchEquipment. WireInfo → BareConductorEquipment or ConcentricCableEquipment. WireConfiguration → GeometryBranchEquipment. TransformerTankConfiguration → DistributionTransformerEquipment. GDM puts some instance values on the shared equipment (a line's `ampacity`; GDM geometry heights carry the line's `spacingYOffset`). So one GDM equipment is made per (catalog, those values). The first values seen are named `<catalog>`, and later ones `<catalog>_2`, `_3` in export order (X2 as built: no pre-pass). A balanced transformer (PowerTransformerEnd + mesh, no TankConfiguration; DSS-origin) gets its own DistributionTransformerEquipment, named after it. |
| X4 | Required GDM fields CIM cannot hold (§3.1) | **Decided (user, 2026-11-09):** one named constant per field in `exporter/fills.py`, each with a comment saying why it is neutral. They are written only when the field is required, and each export logs one WARNING naming each filled field and its count (the importer's I8 pattern). A getter value never goes through a fill, and a fill never replaces a getter's `None` for a value CIM can hold: that raises, or follows the slot's written rule. |
| X5 | Switch class, fuses and reclosers | The importer's decision 14, inverted: LoadBreakSwitch, Breaker, Disconnector and GroundDisconnector → MatrixImpedanceSwitch with Matrix / CircuitBreaker / Disconnector / EarthingSwitch equipment. Fuse → MatrixImpedanceFuse, Recloser → MatrixImpedanceRecloser. Sectionaliser and Jumper raise until a sample needs them. **Decided (user, 2026-11-09): placeholder protection.** A fuse needs a `TimeCurrentCurve` and a recloser a full `DistributionRecloserController` (four curves, shots, intervals, reset time); CIM 18 holds none of it (`GDM_MAPPING.md` §10). They are X4 fills (§3.1): GDM's own `TimeCurrentCurve.example()` and `DistributionRecloserController.example()` values, so the numbers are GDM's and not ours. The curve is named `<fuse>_tcc_placeholder`; the controller and its equipment are named `<recloser>_ctrl_placeholder` (not the example's vendor model name). They are not scaled to the device's rating, and the X4 WARNING says the protection is a placeholder. |
| X6 | Bus phases and voltage | A bus's `phases` are the union of the phase conductors on its terminals, in A, B, C, S1, S2, N order. A balanced terminal (`phases=None`, G3) counts as ABC. **Revised in X2 for ditto:** `rated_voltage` is line to ground, with `voltage_type = line-to-ground`: the BaseVoltage / √3 (`get_base_voltage(form="LN")`), or / 2 on a split-phase bus. ditto's DSS reader writes buses this way, and its capacitor and solar writers read every bus rating as line to ground. With line-to-line buses, a 3-phase capacitor on 4.16 kV was written at 7.2 kV. A GDM line-to-line rating therefore comes back as its line-to-ground equivalent: equal in value, listed as a GDM-level difference. |
| X7 | Per-phase values | GDM is per phase everywhere (`phase_loads`, `phase_capacitors`, `sources`). Loads and DER come from `get_phase_loads` / `get_der_output` (per-phase CIM values, else the total split evenly over the phase conductors: getter rule 3). The source's equal phases come from `get_source`. A capacitor's come from `get_shunt_reactive_power` per phase. |
| X8 | Controllers | RegulatingControl → the capacitor controller class picked by mode, the exact inverse of the importer's (on and off = target ∓ deadband / 2, ÷ pt/ct ratio). TapChangerControl → RegulatorController. Inverter controllers are not in CIM (`PENDING` on import), so the DER get `controller=None`. |
| X9 | Units | Every GDM quantity is built from a getter float in the unit that getter was asked for, e.g. `Voltage(v, "kilovolt")`. There is no `* 1e3` (cim-units skill). GDM matrices are per length; the exporter asks the getter for `ohm/mi` or `ohm/m`, never scales them itself. |
| X10 | Time series and coordinates | None: CIM holds no time series, and bus coordinates are untranscribed on import (B14). Equipment `Location` coordinates are not GDM fields. |
| X11 | Scope | **Decided (user, 2026-11-09): wait for DSS S6.** This branch edits `cimhub_gdm/` only. The two getters both exporters need (`get_wire_info`, `get_series_compensator`) are written by whichever wave reaches them first, in core with their tests, and the other one consumes them. Phase X4 goes after DSS S6b and S6e have landed them on rc_1; X1-X3 don't need them. |

### 3.1 The X4 list

Required in GDM 2.4.1, untranscribed on import (found by walking the importer's `FIELDS` against
`model_fields`):

| GDM field | fill | why it is neutral |
|---|---|---|
| switch, fuse and recloser equipment `r_matrix`, `x_matrix`, `c_matrix` | r and x 1 Ω/km on the diagonal, c zero, n×n (n = conductor count; revised in X2, was zero) | a CIM switch is ideal. A zero matrix is singular, so OpenDSS (through ditto) aborts; this is OpenDSS's own switch impedance (`Switch=yes`), 1 mΩ across the 1 m length |
| `length` on MatrixImpedanceSwitch | 1 m | `length > 0` is enforced; with the switch matrices it gives 1 mΩ |
| DistributionReactor `length` | 1 m | ReactorEquipment `resistance` / `reactance` are totals, so the length scales nothing (importer 17b) |
| DistributionSwitchController `delay`, `is_locked` | 0 s, False | no CIM home |
| DistributionSolar `irradiance` | 1000 W/m² (STC) | GDM carries `active_power` itself; irradiance only scales a curve CIM doesn't have |
| SolarEquipment `resistance`, `reactance` | 0 %, 0 % | no CIM home |
| InverterEquipment `cutin_percent`, `cutout_percent`, `dc_to_ac_efficiency`; `rise_limit`, `fall_limit` | 0 %, 0 %, 100 %; None, None (the field is required but takes None) | no CIM home |
| BatteryEquipment `idling_efficiency` | 100 % | no CIM home |
| RegulatorController `max_step` (steps per control iteration) | `highStep − lowStep` from `get_tap_steps` | a rule, not a constant: the full range means no limit per iteration, which is what CIM's silence says (DSS `MaxTapChange` defaults to 16) |
| MatrixImpedanceFuseEquipment `tcc_curve`, `delay`; `length` on MatrixImpedanceFuse | GDM's `TimeCurrentCurve.example()`; 0 s; 1 m | placeholder protection (X5); `ampacity` comes from the fuse's `ratedCurrent` |
| MatrixImpedanceRecloser `controller` (+ its RecloserControllerEquipment); `length` | GDM's `DistributionRecloserController.example()` values; 1 m | placeholder protection (X5) |
| inline equipment `name` (load, capacitor, source and their phase children, reactor, solar, switch equipment) | X2 | naming |
| PhaseLoadEquipment `z_real` … `p_imag` when CIM gives voltage exponents | constant power (0, 0, 1, 0, 0, 1) | GDM requires the fractions; with exponents set they are not used (ditto writes `Model=4`) |

These GDM classes are never written: SequenceImpedanceSwitch and its equipment (a CIM switch has no impedance),
and GeometrySwitch (the same).

## 4. Tests

- **Per atom, CIM fixed point (tier 2, every phase).** For every importer atom system and its committed golden, the
  test runs `load_model(golden.cimtbl) → to_model(name_source="name") → gdm_to_cim`. It then calls the existing
  `assert_import_matches(..., golden)`: the importer's goldens are the exporter's expectations too, so no new golden
  files are needed. Exporting from the loaded golden rather than the built model proves the exporter reads only what
  CIM holds.
- **Per atom, GDM level.** `to_model` output is compared with the original atom system on every field the importer's
  `FIELDS` marks `copied`, `mapped` or `derived`, with quantities at rel 1e-9. Fields marked `untranscribed` must
  equal their X4 fill. The X6 line-to-line rating and the X3 equipment split are the listed differences.
- **JSON.** `write_gdm` → `read_gdm` → the same system, by the GDM-level comparison above.
- **Reference system (X5).** Both checks above, on the IEEE13-like `reference_system()`.
- **Not on this branch** (root `tests/cross_format/`, on rc_1 after the merge, together with the DSS/GDM parity
  item):
  - DSS-origin CIM (`dss_to_cim` on IEEE13 / IEEE123 / IEEE37) → `to_model`.
  - Idempotence: export(import(export(cim))) equals export(cim).
  - Optionally, ditto's GDM → OpenDSS writer → engine bus voltages against the original deck. ditto 0.1.8 ships an
    `opendss` writer.
