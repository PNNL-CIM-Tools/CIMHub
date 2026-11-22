# OpenDSS → `.cimtbl` mapping spec

**Status:** S2 done (2026-11-07): LineCode units, base frequency and short sequence codes; wire catalogs;
LineSpacing/LineGeometry. **S3a and S3b done 2026-11-08** (lines, switches, transformers, regulators, RegControl, XfmrCode templates). **S4a done 2026-11-08** (Load, Capacitor, CapControl); **S4b done 2026-11-08** (PVSystem, Storage, Generator, Reactor); **S5 done 2026-11-08** (bus coordinates, the deck sweep test). `LineCode` (Phase 1) and the inline `Transformer` are seeded from CIMHub_2_0 with
their atoms; the master, buses and Vsource are S0/S1's. The other DSS classes follow slice by slice
([`DSS_REWRITE_PLAN.md`](../../.development/DSS_REWRITE_PLAN.md)), each section approved before its code (DSS-12).
Format: the `cimtbl-mapping-spec` skill. Contract: the `cimtbl-import-contract` skill.

The classification tables are generated from each mapper's `FIELDS` with
`cimhub_core.cimtbl.fields_table(..., fields=FIELDS)`. The samples come from `tests/decks/IEEE/IEEE13_CDPSM/` and the
IEEE8500 `LineCodes.dss`; the S2 tables' samples come from the 31 sweep decks. `{length}` in a unit is the code's
`units`; `{r_length}`, `{gmr_length}`, `{radius_length}` are a wire's `Runits`, `GMRunits`, `radunits`.

## Artifact files and order

| native class | artifact | shape | depends on |
|---|---|---|---|
| (the deck) | `<Model>.cimtbl` (master) | settings, `common` rows (Substation, Feeder, BaseFrequency, BaseVoltage), `Import`s | every part |
| (the topology walk) | `bus.cimtbl` | one `ConnectivityNode` per bus, with its `BaseVoltage` | the master |
| `Vsource` | `vsource.cimtbl` | `source` | the master, `bus.cimtbl` |
| `WireData`, `CNData`, `TSData` | `wiredata.cimtbl`, `cndata.cimtbl`, `tsdata.cimtbl` | `wire_info` | nothing |
| `LineSpacing` | `linespacing.cimtbl` | `line_by_wire_configuration` (`XYSpacing`) | nothing |
| `LineGeometry` | `linegeometry.cimtbl` | `line_by_wire_configuration` (`WireConfiguration`; inline positions get a synthesized `XYSpacing`) | the wire catalogs, `linespacing.cimtbl` |
| `LineCode` | `linecode.cimtbl` | matrix code: `PerLengthPhaseImpedance` + `PhaseImpedanceData` per lower-triangle element; sequence code: `PerLengthSequenceImpedance` | nothing |
| `Line` (+ `Fuse`, `Recloser`, `SwtControl`) | `line.cimtbl` | `line_by_impedance`, `line_by_wire_configuration`, `switch`; the line's own impedance `ln_<name>_lc` (`isTemplate=false`), synthesized `ln_<name>_wc`; ratings as `OperationalLimitSet` + `CurrentLimit` | the master (Feeder, BaseVoltage, OperationalLimitType), `bus.cimtbl`, the catalogs |
| `XfmrCode` | `xfmrcode.cimtbl` | `transformer_template` (3-phase, TankEnd), `transformer_template_1ph` (1-phase, lugs) | the instances that use it (their bus systems) |
| `Transformer` | `transformer.cimtbl` | 3-phase: `transformer_by_ends`; 1-phase: `transformer_by_phase_ends`; regulated with equal winding kV: `voltage_regulator` | the master (Feeder, BaseVoltage) and the topology walk's bus systems |
| `RegControl` | `regcontrol.cimtbl` | `voltage_regulator` / `regulator` (`RatioTapChanger` + `TapChangerControl`) | `transformer.cimtbl` |
| `LoadShape` (those a Load names as `yearly`) | `loadshape.cimtbl` | `load_schedule` (`ConformLoadGroup` + `ConformLoadSchedule`; the points in the Parquet sidecar, S8) | nothing |
| `Load` | `load.cimtbl` | `load`; `exp_<CVRwatts>_<CVRvars>` response rows; a `ConformLoad` of its yearly shape's group (S8) | the master (Feeder, BaseVoltage, `zip_fractions.cimtbl`), `bus.cimtbl`, `loadshape.cimtbl` |
| `Capacitor` | `capacitor.cimtbl` | `shunt` (`LinearShuntCompensator`) | the master, `bus.cimtbl` |
| `CapControl` | `capcontrol.cimtbl` | `shunt` (`RegulatingControl` + `Update` of the compensator) | `line.cimtbl`, `capacitor.cimtbl` |
| `PVSystem`, `Storage` | `pvsystem.cimtbl`, `storage.cimtbl` | `der` | the master, `bus.cimtbl` |
| `Generator` | `generator.cimtbl` | `synchronous_machine` | the master, `bus.cimtbl` |
| `Reactor` | `reactor.cimtbl` | `series_compensator` | the master, `bus.cimtbl` |
| `Buscoords` (BusCoords / LatLongCoords files) | `buscoords.cimtbl` (last) | `location` | every equipment part (their bound Terminals: `bound_parts`, S5-2) |

## Master

Orchestrator: `cimhub_opendss/importer/dss_to_cimtbl.py` (`DssImporter`, `map_master`, `dss_to_cim`). Golden:
`tests/goldens/IEEE13_CDPSM/IEEE13_CDPSM.cimtbl`, tested by `tests/test_dss_to_cimtbl.py`. Approved 2026-11-07 (D7 as
written); the `common` rows approved with S1.

- **File and settings (plan D7):** the caller names the model (`DssImporter("IEEE13_CDPSM")`); it is the master's
  file stem and `Model`. `Authority` is `https://github.com/PNNL-CIM-Tools/CIMHub` unless the caller passes another.
  `Profile = cim18v17`.
- **Imports:** one per non-empty part, in `MAPPING_ORDER` (catalogs before instances, plan section 2). A DSS class
  with no records writes no part and no `Import`.
- **Comment:** the deck name, this anchor, and `not mapped:` with the record count of every DSS class no mapper
  reads yet (DSS-11), so a class never disappears silently. The list shrinks as slices land.
- **`common` rows (S1).** The containers come from `New Circuit.<circuit>`, which the reader keeps
  as `Options.circuit`. A deck with no `New Circuit`, or with a second one, raises.

  ```
  Object Substation: mRID=sub_<circuit>, name=<circuit>
  Object Feeder: mRID=fdr_<circuit>, name=<circuit>, NormalEnergizingSubstation=sub_<circuit>
  Object BaseFrequency: mRID=bf_60hz, frequency (Hz)=60          # defaulted: defaultbasefreq=60.0
  # voltagebases: 115, 4.16, 13.2, 0.48, 0.208; on no bus: 0.208; not in voltagebases: 0.24
  Table BaseVoltage: mRID, nominalVoltage (kV)
      bv_115kv,  115
      bv_4p16kv, 4.16
      ...
  ```
  - `mRID`s are lowercased, like every DSS mRID.
  - `BaseFrequency` is `Set defaultbasefreq`, else the DSS default of 60 Hz (DSS-3b).
  - The BaseVoltages are the distinct bus voltages of the topology walk (DSS-1), highest first, never
    `voltagebases`. The comment lists the deck's `voltagebases` and flags any that is on no bus. A walk voltage
    missing from `voltagebases` (a bus the engine would snap, plan section 3.1) is flagged as `not in voltagebases`.
  - The Substation holds the EnergySources. The Feeder holds every other piece of equipment and every
    ConnectivityNode, so it is the `container` that mappers receive.

## Buses

Orchestrator: `importer/dss_to_cimtbl.py` (`map_buses`). Golden: `tests/goldens/IEEE13_CDPSM/bus.cimtbl`.
Approved 2026-11-07: equipment keeps its own `BaseVoltage` (mandatory).

cim18v17 adds `ConnectivityNode.BaseVoltage`. The CIM text: it "is used only if the ConnectivityNode is not
contained in a VoltageLevel", and "it is not required that the BaseVoltage of connected equipment is the same".
There are no VoltageLevels here, so the topology walk's result becomes an artifact: one row per bus it reaches.

```
# Bus voltages from the topology walk (cimtopology.core) from the source buses; 22 buses.
Table ConnectivityNode: mRID, name, BaseVoltage, ConnectivityNodeContainer=fdr_ieee13nodeckt
    sourcebus, sourcebus, bv_115kv
    650z,      650z,      bv_13p2kv
    ...
```

- `mRID` and `name` are the bus name, lowercased: the walk's key, and the cell every `node` column writes. cimtables
  binds a later `node=650` to this node instead of creating a new one.
- Rows are sorted highest voltage first, then by bus name, so the file does not depend on the walk's internals.
- A bus the walk does not reach has no row. Equipment on such a bus raises in its mapper (`no bus voltage`), as the
  transformer mapper already does.

What this solves:
- **Every bus has a voltage, written once.** A DSS Line, switch or reactor has none of its own. A bus between two
  transformers had a voltage only through the `TransformerEnd`s. An exporter that needs a per-bus base (DSS
  `setkVBase`, a GridLAB-D node's `nominal_voltage`, the MATPOWER and RAW bus tables) reads the node instead of
  inferring it from the equipment.
- **The walk is visible.** Plan section 3.1's result sits in a diffable file, not only in the mappers' `buses`
  argument.
- **A check on every equipment row.** Equipment keeps its own `BaseVoltage` column, which cimtables needs as the
  system base of a `(pu)` column and which consumers of `ConductingEquipment.BaseVoltage` read. The bind test
  asserts it equals the BaseVoltage of each of the equipment's nodes. A transformer's ends already carry their own,
  per end.

## Vsource

Mapper: `importer/cimtbl/vsource.py` (`map_vsource`). Atoms: `tests/atoms/vsource/`: `mvasc` (IEEE13_CDPSM),
`ohms` (IEEE123), `isc` (IEEE4_xfmrs `B1`), `defaults` (`New Circuit.x basekv=12.47`) and `single_phase`, with
`prereq.cimtbl`; tested by `tests/test_cimtbl_vsource.py`. Approved 2026-11-07.

One `EnergySource` per `Vsource`, `New Circuit` included (`source` shape):

```
# OpenDSS Vsource -> EnergySource on its bus; 1 Vsource.
Table EnergySource: mRID, name, node, phases, nominalVoltage (kV), voltageMagnitude (kV), voltageAngle (deg), r (ohm), x (ohm), r0 (ohm), x0 (ohm), normallyInService, BaseVoltage, EquipmentContainer=sub_ieee13nodeckt
    src_source, source, sourcebus, ABC, 115, 115, 30, 0.160376682055275, 0.641506728221101, 0.179603583012336, 0.538810749037007, true, bv_115kv  # derived from MVAsc3=20000.0, MVAsc1=21000.0; defaulted: x1r1=4.0, x0r0=3.0
```

- **Identity:** `mRID` = `src_` + `name`, lowercased.
- **Bus and phases:** `bus1` (default `sourcebus`) gives `node`. `phases` (default 3) gives `ABC` or, on a
  1-phase source, the phase of the bus's single conductor. Any other phase count raises. A `bus2` raises, because
  an ungrounded (series) source has no `source`-shape home.
- **Voltage:** `nominalVoltage` = `basekv` (default 115), copied. `voltageMagnitude` = `basekv × pu` (default
  `pu` 1), derived. `voltageAngle` = `angle` (default 0), copied, in degrees.
- **Impedance.** DSS has three ways to give a source's Thevenin impedance, and keeps the one set last
  ([Vsource properties](https://opendss.epri.com/Properties23.html), `VSource.pas` `PropertySideEffects`). The
  reader does not record the order, so, as for LineCode, a Vsource that sets two groups raises:
  1. **`R1 X1 R0 X0`** (ohms): copied. All four must be set; a partial set raises.
  2. **`MVAsc3 MVAsc1`** (with `x1r1`, `x0r0`): derived by `vsource.thevenin_from_short_circuit`, which follows
     `VSource.pas` `RecalcElementData`:
     - X1 = kV² / MVAsc3 / √(1 + 1/x1r1²) and R1 = X1 / x1r1;
     - R0 is the positive root of (1 + x0r0²)·R0² + 4(R1 + X1·x0r0)·R0 + 4(R1² + X1²) − (3·kV²/MVAsc1)² = 0, and
       X0 = R0 · x0r0;
     - a negative discriminant raises.
     A slot left unset takes its DSS default (`MVAsc3` 2000, `MVAsc1` 2100, `x1r1` 4, `x0r0` 3) under
     `# defaulted`. A Vsource that sets no group takes all four defaults, as the engine does. LineCode raises in
     that case instead, but a bare `New Circuit.x basekv=12.47` is the documented minimal deck.
  3. **`Isc3 Isc1`** (amps): converted to group 2 (MVAsc3 = √3·kV·Isc3 / 1000, MVAsc1 = f·kV·Isc1 / 1000, with
     f = √3 on 3 phases and 1 on 1 phase), then as group 2.
  - Checked against the engine (`opendssdirect`, 9 digits): IEEE13's MVAsc, all defaults, `MVAsc3` alone, `Isc`, and
    a 1-phase source.
  - `Z1 Z0 Z2 puZ1 puZ0 puZ2 baseMVA` raise when set: no deck in the sweep uses them, so a mapping waits for one.
  - Group 2 and 3 values are derived numbers, so the row comment names their inputs. The test oracle is the engine:
    `r x r0 x0` must equal `? Vsource.<name>.R1` etc. after compile, on every engine deck.
- **`enabled`** → `normallyInService`, copied.
- **Untranscribed:** `frequency` and `basefreq` (the master's BaseFrequency is the deck's), `ScanType`,
  `Sequence`, `spectrum` (harmonics), `Yearly`, `Daily`, `Duty` (time series), `Model`, `puZideal`.
- **Reader and schema changes of this slice:** the reader keeps the circuit name on `Options.circuit` and no longer
  writes `bus1=sourcebus` into a `New Circuit`'s parameters; the schema's `dss_default`s on `Vsource` carry the
  defaults, which `importer/topology.py` takes through `vsource.with_defaults`. `Clear` discards everything before
  it (the IEEE4 balanced decks build, solve and rebuild). `x1r1`, `x0r0` and `frequency` are floats, and
  `puZ1`/`puZ0`/`puZ2` are `[R, X]` arrays like `Z1`.

## LineCode

Mapper: `cimhub_opendss/importer/cimtbl/linecode.py` (`map_linecode`). Atoms: `tests/atoms/linecode/mtx601.{dss,cimtbl}`
(matrix, IEEE13_CDPSM) and `seq_3_1_0c.{dss,cimtbl}` (sequence, IEEE8500), tested by `tests/test_cimtbl_linecode.py`.

**Identity.** `mRID` = `lc_` + `name`, lowercased (DSS names are case-insensitive). `PhaseImpedanceData` has no
mRID; its `identifier` column is `<mRID>_<row><column>`.

**Template (DSS-14, the user's rule 2026-11-21).** A LineCode is a template its lines share by name: its impedance
has `isTemplate=true`, and a `WireConfiguration` `<template>_wc` (`lc_<name>_wc`, or `lc_<name>_<unit>_wc` per DSS-3)
holds it as `PerLengthImpedance`, with no `WireSpacing`. Lines reference that WireConfiguration, not the impedance.
The WireConfiguration is CIM's equivalence route: a configuration with a spacing is geometry, one with only a
`PerLengthImpedance` is a template LineCode, and one with both is geometry with its equivalent impedance. Exporters
read it through `get_line_geometry` and `get_line_code` (`cimhub_core.getters.line_impedance`). An impedance only one
line uses, the line's own values, is `ACLineSegment.PerLengthImpedance` with `isTemplate=false` (Line, below).

**Form.** A code that sets any of `r1 x1 r0 x0 C1 C0 B1 B0` is a sequence code (OpenDSS
[Line properties](https://opendss.epri.com/Properties14.html)); one that sets `rmatrix`/`xmatrix`/`cmatrix` is a
matrix code. DSS keeps whichever form was set last, and the reader does not record the order, so a code that sets
both raises. So does a code that sets neither (DSS would apply its defaults).

**Values.** The DSS reader yields floats for most slots (written as `repr()`), but `C1`, `C0`, `B1`, `B0` and
`baseFreq` as the file's text. One table per header: matrix data per length unit, sequence codes per (length unit,
`bch`/`b0ch` source), because a C-derived `bch` is in nS and a copied `B1` in uS.

| Linecode field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, LinecodeName]` | `mtx601`, `mtx602`, `mtx603` | copied | `PerLengthPhaseImpedance.name`, `PerLengthSequenceImpedance.name`, `WireConfiguration.name`; mRID = lc_ + name, lowercased; its WireConfiguration's lc_<name>_wc (DSS-14) |
| `nphases` | `Optional[int]` | `3`, `2` | copied | `PerLengthPhaseImpedance.conductorCount`; the matrix order of rmatrix/xmatrix/cmatrix; a 1- or 2-phase sequence code becomes a phase matrix as the engine builds the line (phase_matrix): 1-phase z = Z1, 2-phase Zs = (2 Z1 + Z0)/3 and Zm = (Z0 - Z1)/3 (DSS-4) |
| `r1` | `Optional[float]` | `0.769009`, `0.3489`, `0.535622` | copied | `PerLengthSequenceImpedance.r` (ohm/{length}) |
| `x1` | `Optional[float]` | `0.312115`, `0.491691`, `0.560725` | copied | `PerLengthSequenceImpedance.x` (ohm/{length}) |
| `r0` | `Optional[float]` | `1.294322`, `0.613107`, `0.608571` | copied | `PerLengthSequenceImpedance.r0` (ohm/{length}) |
| `x0` | `Optional[float]` | `0.287695`, `1.241561`, `1.19452` | copied | `PerLengthSequenceImpedance.x0` (ohm/{length}) |
| `C1` | `Optional[str]` | `154.240283543118`, `8.96939698228171`, `9.08509466816236` | derived | PerLengthSequenceImpedance bch = 2 pi baseFreq C1 (b_from_c): nF -> nS |
| `C0` | `Optional[str]` | `154.240283543118`, `4.95311934077534`, `5.10821052765362` | derived | PerLengthSequenceImpedance b0ch = 2 pi baseFreq C0 (b_from_c): nF -> nS |
| `units` | `Optional[str]` | `mi`, `km` | mapped | the length unit of every per-length header via LENGTH_UNIT; unset: the unit of the lines that use the code, else the deck's magnitude gate (DSS-3) |
| `rmatrix` | `Union[float, list[float], NoneType]` | `[0.3465, 0.1535, 0.3375, 0.158, 0.156...`, `[0.7526, 0.1535, 0.7475, 0.156, 0.158...`, `[1.3238, 0.2066, 1.3294]` | structural | PhaseImpedanceData r, one row per lower-triangle element |
| `xmatrix` | `Union[float, list[float], NoneType]` | `[1.0179, 0.3849, 1.0478, 0.4236, 0.50...`, `[1.1814, 0.3849, 1.1983, 0.5017, 0.42...`, `[1.3569, 0.4591, 1.3471]` | structural | PhaseImpedanceData x, one row per lower-triangle element |
| `cmatrix` | `Union[float, list[float], NoneType]` | `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]`, `[0.0, 0.0, 0.0]` | derived | PhaseImpedanceData b = 2 pi baseFreq C (b_from_c): nF -> nS |
| `baseFreq` | `Optional[str]` | `60` | copied | `PerLengthPhaseImpedance.calculatedFrequency` (Hz), `PerLengthSequenceImpedance.calculatedFrequency` (Hz); also the frequency of the derived b; unset with a nonzero C: the deck's base frequency, defaulted (DSS-3b) |
| `normamps` | `Optional[float]` | `730.0`, `340.0`, `230.0` | untranscribed | catalog ratings have no home on PerLengthImpedance; instance limits or untranscribed (plan D9) |
| `emergamps` | `Optional[float]` | `160.0`, `310.0`, `260.0` | untranscribed | catalog ratings have no home on PerLengthImpedance; instance limits or untranscribed (plan D9) |
| `faultrate` | `Optional[int]` | `0` | untranscribed | reliability data; no home in the network profile parts |
| `pctperm` | `Optional[float]` | `20.0` | untranscribed | reliability data; no home in the network profile parts |
| `repair` | `Optional[str]` | `3` | untranscribed | reliability data; no home in the network profile parts |
| `Kron` | `Optional[str]` |  | untranscribed | input of the matrix calculation; no CIM home |
| `Rg` | `Optional[float]` |  | untranscribed | Carson earth return per length; home PerLengthImpedance.rg/xg (ohm/<units>), not mapped until a deck sets it (none of the test decks do) |
| `Xg` | `Optional[float]` |  | untranscribed | Carson earth return per length; home PerLengthImpedance.rg/xg (ohm/<units>), not mapped until a deck sets it (none of the test decks do) |
| `rho` | `Optional[float]` |  | untranscribed | earth resistivity; home EarthResistivity.rho, an object of its own, not mapped until a deck sets it |
| `neutral` | `Optional[str]` |  | untranscribed | input of the matrix calculation; no CIM home |
| `B1` | `Optional[str]` |  | copied | `PerLengthSequenceImpedance.bch` (uS/{length}); the alternative to C1 |
| `B0` | `Optional[str]` |  | copied | `PerLengthSequenceImpedance.b0ch` (uS/{length}); the alternative to C0 |
| `Seasons` | `Optional[int]` |  | untranscribed | catalog ratings have no home on PerLengthImpedance; instance limits or untranscribed (plan D9) |
| `Ratings` | `Optional[float]` |  | untranscribed | catalog ratings have no home on PerLengthImpedance; instance limits or untranscribed (plan D9) |
| `LineType` | `Optional[float]` |  | untranscribed | no home in the network profile parts |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

**Derived.** `b_from_c(c, f)` = 2πfC: C in nF and f in Hz give b in nS. `susceptance` applies it per value; C = 0
gives b = 0 without a `baseFreq` (ACEP_PSIL `buswork` sets none).

**Fail fast.** A `units` value with no mapping; a unitless code whose lines give units on some lines only, or a gate
median in no band; both C1 and B1 (or C0 and B0); both forms or neither; B1/B0 on a 1- or 2-phase code; a matrix
whose length does not fit `nphases`.

**Deck sweep (2026-11-06).** 9 of the 24 decks with line codes map and bind. The rest stop on:

| stop | decks | open point |
|---|---|---|
| nonzero `cmatrix` without `baseFreq` | ieee9500 (both copies), IEEE8500 and K1 triplex | DSS takes the circuit's default base frequency. Take it from the deck's `Circuit`/`Set DefaultBaseFrequency`, else 60 Hz? |
| `units` unset | IEEE13_original, IEEE123_deconfliction, EPRI M1 and J1 | DSS reads the values per unit of the *line's* length, so the per-length unit belongs to the instance. Defer the code to the `Line` mapper, or require `units`? |
| 1-/2-phase sequence code | EPRI J1 (17 codes) | The engine (J1, 2026-11-06) builds a 1-phase line from Z1 alone (`oh_b13552`: R = R1, X = X1, C = C1 per length) and a 2-phase line from Zs = (2Z1 + Z0)/3, Zm = (Z0 − Z1)/3 (`oh_b41869`). The LineCode object itself reports (2Z1 + Z0)/3 for both, so the code alone does not fix the value. Proposal in [`DSS_REWRITE_PLAN.md`](DSS_REWRITE_PLAN.md) (DSS-4) |
| two mRIDs give one UUID | IEEE8500 (`lc_1p_#2acsr_#2n` vs `lc_1p_#2arv_#2n`) | CIM-Profiles bug: the mRID seed drops text up to the last `#` (CIMTABLES_REQUESTS R10) |
| `nphases=4` read as 3 | IEEE13_OCHRE | reader bug: it limits nphases to [1, 3] and substitutes 3, so the 10-value `rmatrix` no longer fits |

**Reader/schema findings** (not mapper issues): `faultrate` is typed `int`, so `0.1` reads as `0`; `LineType` is
typed `float` (DSS values are words such as `oh`); `C1`/`C0`/`B1`/`B0`/`baseFreq` are typed `str`.

**Expected differences from the hand translation** (`CIMTBL-Models/.../IEEE13_CDPSM`): it carries the 2011 corrected
off-diagonals; the import keeps the deck's values (`mtx601` r21 = 0.1535).

### LineCode: units, base frequency, short sequence codes (S2, approved 2026-11-07)

S2 lifts three of the fail-fast stops above (the sweep tables below are the pre-S2 record), as decided in [`DSS_REWRITE_PLAN.md`](../../.development/DSS_REWRITE_PLAN.md)
§6. They are the stops for 16 of the 31 sweep decks.

- **`units` unset (DSS-3).** DSS reads a unitless code per unit of the *line's* length, so:
  - (a) a code used by lines that give `units` takes the line's unit (J1: 1,382 lines, all `kft`). Lines that
    disagree give one template per unit, `lc_<name>_<unit>`.
  - (b) code and lines both unitless (M1, IEEE123_deconfliction), or a unitless code no line uses (IEEE13_original):
    a deck-level magnitude gate on the median positive `r1` (or `rmatrix` diagonal) of the deck's unitless codes.
    0.006 to 10 per unit gives `km`; 1e-5 to 0.006 gives `m`; anything else raises. `length_unit=` on the importer
    overrides the gate.

  The row comment states the unit's source: `# units from its lines: kft (...)`, `# units inferred: km (median r
  0.134 per unit over 17 codes; no units on code or line)` (M1), or `# units given: ...` for `length_unit=`.
  Inferred in the sweep: km for M1, IEEE123, IEEE123_deconfliction, IEEE13_original, IEEE37 and J1's 2 unused
  codes; J1's 4 used codes take kft from their lines.
  Code and line share the unit, so z·length is exact for any label. A wrong label only scales the physical
  length. The mapper reads the Lines (their `linecode` and `units`) for this; it maps none of them.
- **A nonzero C without `baseFreq` (DSS-3b).** `b_from_c` takes the master's base frequency (`Set
  defaultbasefreq`, else 60 Hz), and the row says `# defaulted: baseFreq=60`.
- **1- and 2-phase sequence codes (DSS-4; J1, 17 codes).** These become a derived `PerLengthPhaseImpedance` +
  `PhaseImpedanceData`, as the engine builds the line. 1-phase: z = Z1, b from C1. 2-phase: Zs = (2 Z1 + Z0)/3 and
  Zm = (Z0 − Z1)/3, the same for C. The function is `cimhub_core.derived.sequence.phase_matrix` (closed form, not
  Carson; a U4 candidate). Atom `short_sequence.dss` (two J1 codes, one line each): r, x and b equal the engine's
  line matrices. A 1-phase row lists the r0/x0/C0 the line does not use; B1/B0 on a short code raises.
- **D9:** `normamps`/`emergamps` stay untranscribed on a LineCode (no home on `PerLengthImpedance`).

## Wire catalogs

Mapper: `cimhub_opendss/importer/cimtbl/wire.py` (`map_wires(native, native_class, prefix, fields)`). Shape:
`wire_info`. Atoms: `tests/atoms/wire/assets.dss` (IEEE13_Assets: Rdc-only ACSR, Rac-only CU, `CN_250`, `TS_1/0`)
and `metric.dss` (one IEEE9500 wire, km/cm), tested by `tests/test_cimtbl_wire.py`. Approved 2026-11-07, with Rac
filled from Rdc and the TS screen diameter = DiaShield − 2 TapeLayer.

**Identity.** One file per DSS class (D4): `wiredata.cimtbl`, `cndata.cimtbl`, `tsdata.cimtbl`. mRID = `wire_`,
`cn_` or `ts_` + name, lowercased. Each DSS class is its own namespace, so the prefixes keep a WireData and a
CNData of one name apart.

**Units.** `Runits` (resistance per length), `GMRunits` and `radunits` become header units, values as written. A
cable's dimensions (`DiaIns`, `DiaCable`, `InsLayer`, `DiaStrand`, `DiaShield`, `TapeLayer`) are in `radunits`.
`GmrStrand` is in `GMRunits` and `Rstrand` in `Runits`, as DSS states. The mapper writes one table per unit
combination, as LineCode writes one per length unit. IEEE13_Assets gives two tables (kft/in/in and mi/in/in); the
IEEE9500 wires give one (km/cm/cm). An unset selector raises; every wire in the sweep sets all three.

**Values the engine fills** (DSS-6, in the row comment):
- **`Rac` unset:** rAC25 = 1.02 × Rdc, the engine's rule (`ac_from_dc`; the 9 IEEE4/IEEE13_Assets ACSR wires).
  `Rdc` unset is left unset: the engine only uses Rdc to fill Rac.
- **`diam`:** radius = diam / 2 (`radius_from_diameter`). Setting both radius and diam raises (DSS keeps the
  last, which the reader does not record); so does setting neither.
- **`GMRac` unset:** raises. The engine would take 0.7788 × radius, but no deck in the sweep omits GMRac.

**Cables** follow EPRI's ExportCIMXML wherever CIM has no exact twin:
- `Rac` → `rAC25` (DSS gives no temperature) and `Rstrand` → `neutralStrandRDC20` (DSS calls it AC; CIM has only
  the one strand resistance). Only `rAC25` is written, never the same value copied to rAC50/rAC75.
- CN `DiaCable` → both `diameterOverJacket` and `diameterOverNeutral`: the strands are outermost. CN's
  `diameterOverScreen` is not written; it is derivable and no consumer needs it.
- TS `diameterOverScreen` = DiaShield − 2 TapeLayer (`screen_diameter`). DSS measures over the tape; CIM's screen
  diameter is the shield's inside.
- `EpsR` is untranscribed: CableInfo has no permittivity. Every cable in the sweep uses the DSS default, 2.3.

**Ratings (approved 2026-11-08).** A rated wire's `normamps` is `ratedCurrent`, as before. It also becomes an
`OperationalLimitSet` `<mRID>_limits` on the new GridAPPS-D `AssetInfo.OperationalLimitSet` (the serialized side,
so the wire row names its set and the set is written first). The set has two `CurrentLimit`s:
- `<mRID>_norm` = normamps on `olt_normal`;
- `<mRID>_emerg` = emergamps on `olt_emergency`. An unset emergamps is 1.5 × normamps, the engine's rule
  (`wire_ratings`, `# defaulted: emergamps = 1.5 x normamps`).

The two limit types are the master's. An unrated wire gets no set (DSS's 400/600 A defaults are not written).
`Seasons`/`Ratings` raise when set, as on a Line. The line mapper uses the same `wire_ratings` for a geometry
line's first conductor.

Example (`wiredata.cimtbl`, IEEE13_Assets):

```
Table OperationalLimitSet: mRID
    wire_acsr_1/0_limits
    ...
Table CurrentLimit: mRID, normalValue (A), OperationalLimitType, OperationalLimitSet
    wire_acsr_1/0_norm,    230.0,  olt_normal,    wire_acsr_1/0_limits
    # defaulted: emergamps = 1.5 x normamps
    wire_acsr_1/0_emerg,   345.0,  olt_emergency, wire_acsr_1/0_limits
    ...
Table OverheadWireInfo: mRID, name, rDC20 (ohm/kft), rAC25 (ohm/kft), gmr (in), radius (in), ratedCurrent (A), OperationalLimitSet
    # defaulted: Rac = 1.02 x Rdc
    wire_acsr_1/0,   ACSR_1/0,   0.212121212, 0.21636363624000002, 0.05352, 0.199,  230.0, wire_acsr_1/0_limits
    ...
```

**Fail fast:** a unit selector unset; radius and diam both set or neither; GMRac unset; `Capradius`,
`SemiconLayer`, `Seasons` or `Ratings` set (no deck sets them).

**Oracle:** every written value equals the engine's property in the engine's units (`opendssdirect` WireData /
CNData / TSData), including the filled Rac and the normal and emergency ratings, on the vendored IEEE13_Assets and IEEE4 decks
(`test_values_match_the_engine`).

| Wiredata field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, WiredataName]` | `ACSR_1/0`, `ACSR_4/0`, `ACSR_556_5` | copied | `OverheadWireInfo.name`; mRID = prefix + name, lowercased |
| `Rdc` | `Optional[float]` | `0.212121212`, `0.112121212`, `0.035227273` | copied | `OverheadWireInfo.rDC20` (ohm/{r_length}); DC resistance (DSS gives no temperature) |
| `Rac` | `Optional[float]` | `0.607`, `1.010411`, `0.939016` | copied | `OverheadWireInfo.rAC25` (ohm/{r_length}); DSS: resistance at 60 Hz, temperature unstated; rAC25 as in EPRI's ExportCIMXML. Unset: 1.02 x Rdc, the engine's rule (ac_from_dc), with a defaulted comment |
| `Runits` | `Optional[str]` | `kft`, `mi`, `km` | mapped | the unit of Rdc, Rac in the header (LENGTH_UNIT); unset raises (every wire in the sweep sets it) |
| `GMRac` | `Optional[float]` | `0.05352`, `0.09768`, `0.3732` | copied | `OverheadWireInfo.gmr` ({gmr_length}); unset raises (the engine's 0.7788 x radius default; no deck in the sweep omits it) |
| `GMRunits` | `Optional[str]` | `in`, `cm`, `ft` | mapped | the unit of GMRac in the header (LENGTH_UNIT); unset raises (every wire in the sweep sets it) |
| `radius` | `Optional[float]` | `0.40132`, `0.39624`, `0.37084` | copied | `OverheadWireInfo.radius` ({radius_length}); one of radius and diam; both raise (DSS keeps the last, the reader does not record which), neither raises |
| `radunits` | `Optional[str]` | `in`, `cm` | mapped | the unit of radius, diam and every cable dimension in the header (LENGTH_UNIT); unset raises (every wire in the sweep sets it) |
| `normamps` | `Optional[float]` | `230.0`, `340.0`, `730.0` | copied | `OverheadWireInfo.ratedCurrent` (A); also the normal CurrentLimit of the wire's OperationalLimitSet <mRID>_limits (AssetInfo.OperationalLimitSet) |
| `emergamps` | `Optional[float]` | `200.0`, `239.0`, `172.0` | structural | the emergency CurrentLimit of the wire's OperationalLimitSet <mRID>_limits (AssetInfo.OperationalLimitSet); unset: 1.5 x normamps (wire_ratings, the engine's rule), defaulted |
| `diam` | `Optional[float]` | `0.398`, `0.563`, `0.927` | derived | radius = diam / 2 (radius_from_diameter) |
| `Seasons` | `Optional[int]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (an indexed rating array that names no calendar season; home OperationalLimitType.season) |
| `Ratings` | `Union[float, list[float], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (with Seasons) |
| `Capradius` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the radius for capacitance; not WireInfo.coreRadius) |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

| Cndata field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, CndataName]` | `CN_250`, `1/0_Al_15kV_1/3` | copied | `ConcentricNeutralCableInfo.name`; mRID = prefix + name, lowercased |
| `k` | `Optional[int]` | `13`, `6` | copied | `ConcentricNeutralCableInfo.neutralStrandCount` |
| `DiaStrand` | `Optional[float]` | `0.0641`, `0.064` | derived | neutralStrandRadius = DiaStrand / 2 (radius_from_diameter), radunits |
| `GmrStrand` | `Optional[float]` | `0.02496` | copied | `ConcentricNeutralCableInfo.neutralStrandGmr` ({gmr_length}); in GMRunits, as DSS says |
| `Rstrand` | `Optional[float]` | `14.8722`, `2.55` | copied | `ConcentricNeutralCableInfo.neutralStrandRDC20` (ohm/{r_length}); DSS calls it the strand's AC resistance; neutralStrandRDC20 as in ExportCIMXML, CIM's only strand resistance |
| `SemiconLayer` | `Union[bool, Bool, NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `EpsR` | `Optional[float]` | `2.3` | untranscribed | insulation relative permittivity; no home on CableInfo (InsulationInfo has a material, not a permittivity). DSS default 2.3, which every cable in the sweep uses |
| `InsLayer` | `Optional[float]` | `0.22`, `0.445` | copied | `ConcentricNeutralCableInfo.insulationThickness` ({radius_length}) |
| `DiaIns` | `Optional[float]` | `1.06`, `2.11` | copied | `ConcentricNeutralCableInfo.diameterOverInsulation` ({radius_length}) |
| `DiaCable` | `Optional[float]` | `1.29`, `2.74` | copied | `ConcentricNeutralCableInfo.diameterOverJacket` ({radius_length}), `ConcentricNeutralCableInfo.diameterOverNeutral` ({radius_length}); the outer diameter; a CN cable has no jacket over its strands, so it is also the diameter over the neutral (ExportCIMXML) |
| `Rdc` | `Optional[float]` |  | copied | `ConcentricNeutralCableInfo.rDC20` (ohm/{r_length}); DC resistance (DSS gives no temperature) |
| `Rac` | `Optional[float]` | `0.41`, `0.603` | copied | `ConcentricNeutralCableInfo.rAC25` (ohm/{r_length}); DSS: resistance at 60 Hz, temperature unstated; rAC25 as in EPRI's ExportCIMXML. Unset: 1.02 x Rdc, the engine's rule (ac_from_dc), with a defaulted comment |
| `Runits` | `Optional[str]` | `mi`, `km` | mapped | the unit of Rdc, Rac, Rstrand in the header (LENGTH_UNIT); unset raises (every wire in the sweep sets it) |
| `GMRac` | `Optional[float]` | `0.2052`, `0.338` | copied | `ConcentricNeutralCableInfo.gmr` ({gmr_length}); unset raises (the engine's 0.7788 x radius default; no deck in the sweep omits it) |
| `GMRunits` | `Optional[str]` | `in`, `cm` | mapped | the unit of GMRac, GmrStrand in the header (LENGTH_UNIT); unset raises (every wire in the sweep sets it) |
| `radius` | `Optional[float]` |  | copied | `ConcentricNeutralCableInfo.radius` ({radius_length}); one of radius and diam; both raise (DSS keeps the last, the reader does not record which), neither raises |
| `radunits` | `Optional[str]` | `in`, `cm` | mapped | the unit of radius, diam and every cable dimension in the header (LENGTH_UNIT); unset raises (every wire in the sweep sets it) |
| `normamps` | `Optional[float]` | `260.0` | copied | `ConcentricNeutralCableInfo.ratedCurrent` (A); also the normal CurrentLimit of the wire's OperationalLimitSet <mRID>_limits (AssetInfo.OperationalLimitSet) |
| `emergamps` | `Optional[float]` |  | structural | the emergency CurrentLimit of the wire's OperationalLimitSet <mRID>_limits (AssetInfo.OperationalLimitSet); unset: 1.5 x normamps (wire_ratings, the engine's rule), defaulted |
| `diam` | `Optional[float]` | `0.567`, `0.935` | derived | radius = diam / 2 (radius_from_diameter) |
| `Seasons` | `Optional[int]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (an indexed rating array that names no calendar season; home OperationalLimitType.season) |
| `Ratings` | `Union[float, list[float], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (with Seasons) |
| `Capradius` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the radius for capacitance; not WireInfo.coreRadius) |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

| Tsdata field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, TsdataName]` | `TS_1/0` | copied | `TapeShieldCableInfo.name`; mRID = prefix + name, lowercased |
| `DiaShield` | `Optional[float]` | `0.88` | derived | diameterOverScreen = DiaShield - 2 TapeLayer (screen_diameter): DSS measures over the tape, CIM's screen diameter is the shield's inside (ExportCIMXML) |
| `TapeLayer` | `Optional[float]` | `0.005` | copied | `TapeShieldCableInfo.tapeThickness` ({radius_length}) |
| `TapeLap` | `Optional[float]` | `20.0` | copied | `TapeShieldCableInfo.tapeLap` (percent) |
| `EpsR` | `Optional[float]` | `2.3` | untranscribed | insulation relative permittivity; no home on CableInfo (InsulationInfo has a material, not a permittivity). DSS default 2.3, which every cable in the sweep uses |
| `InsLayer` | `Optional[float]` | `0.22` | copied | `TapeShieldCableInfo.insulationThickness` ({radius_length}) |
| `DiaIns` | `Optional[float]` | `0.82` | copied | `TapeShieldCableInfo.diameterOverInsulation` ({radius_length}) |
| `DiaCable` | `Optional[float]` | `1.06` | copied | `TapeShieldCableInfo.diameterOverJacket` ({radius_length}); the outer diameter |
| `Rdc` | `Optional[float]` |  | copied | `TapeShieldCableInfo.rDC20` (ohm/{r_length}); DC resistance (DSS gives no temperature) |
| `Rac` | `Optional[float]` | `0.97` | copied | `TapeShieldCableInfo.rAC25` (ohm/{r_length}); DSS: resistance at 60 Hz, temperature unstated; rAC25 as in EPRI's ExportCIMXML. Unset: 1.02 x Rdc, the engine's rule (ac_from_dc), with a defaulted comment |
| `Runits` | `Optional[str]` | `mi` | mapped | the unit of Rdc, Rac in the header (LENGTH_UNIT); unset raises (every wire in the sweep sets it) |
| `GMRac` | `Optional[float]` | `0.1332` | copied | `TapeShieldCableInfo.gmr` ({gmr_length}); unset raises (the engine's 0.7788 x radius default; no deck in the sweep omits it) |
| `GMRunits` | `Optional[str]` | `in` | mapped | the unit of GMRac in the header (LENGTH_UNIT); unset raises (every wire in the sweep sets it) |
| `radius` | `Optional[float]` |  | copied | `TapeShieldCableInfo.radius` ({radius_length}); one of radius and diam; both raise (DSS keeps the last, the reader does not record which), neither raises |
| `radunits` | `Optional[str]` | `in` | mapped | the unit of radius, diam and every cable dimension in the header (LENGTH_UNIT); unset raises (every wire in the sweep sets it) |
| `normamps` | `Optional[float]` | `165.0` | copied | `TapeShieldCableInfo.ratedCurrent` (A); also the normal CurrentLimit of the wire's OperationalLimitSet <mRID>_limits (AssetInfo.OperationalLimitSet) |
| `emergamps` | `Optional[float]` |  | structural | the emergency CurrentLimit of the wire's OperationalLimitSet <mRID>_limits (AssetInfo.OperationalLimitSet); unset: 1.5 x normamps (wire_ratings, the engine's rule), defaulted |
| `diam` | `Optional[float]` | `0.368` | derived | radius = diam / 2 (radius_from_diameter) |
| `Seasons` | `Optional[int]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (an indexed rating array that names no calendar season; home OperationalLimitType.season) |
| `Ratings` | `Union[float, list[float], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (with Seasons) |
| `Capradius` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the radius for capacitance; not WireInfo.coreRadius) |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

## LineSpacing and LineGeometry

Mapper: `cimhub_opendss/importer/cimtbl/geometry.py` (`map_linespacing`, `map_linegeometry`). Shape:
`line_by_wire_configuration`. Geometry stays geometry: no impedance is computed (the `conductor-geometry` skill).
Atom: `tests/atoms/geometry/assets.dss` from IEEE13_Assets: spacing `500` with geometry `601` (the `spacing=`
form), `606` (inline CN positions) and `607` (inline: a TS phase and a bare CU neutral), tested by
`tests/test_cimtbl_geometry.py`. Approved 2026-11-07.

**LineSpacing → `linespacing.cimtbl`.** An `XYSpacing` `spc_<name>` (`isTemplate=true`) and one
`XYConductorPosition` per conductor: `sequenceNumber` 1..nconds, `xCoord`/`yCoord` from `x`/`h` in the
spacing's `units`, and `kind` `phase` for 1..nphases, `neutral` after (DSS's convention). The equivalent-distance
form (`detailed`, `EqDistPhPh`, ...) has no positions and raises; no deck uses it.

**LineGeometry → `linegeometry.cimtbl`.** A `WireConfiguration` `wc_<name>` (`numberOfPhases` = nphases) and one
`WireSequenceConfiguration` per conductor, naming its `WireInfo`. Its `WireSpacing` is:
- `spacing=` → `spc_<spacing>` from `linespacing.cimtbl`.
- inline positions (`cond=1 x=.. h=..`) → a synthesized `XYSpacing` `wc_<name>_spc` in `linegeometry.cimtbl`, under
  `# synthesized`, built like a LineSpacing.

**Conductor names.** The reader gives them in cond order in one of `wires`, `cncables`, `tscables`. A mixed
assembly (607) arrives whole in `wires`, so the array says nothing about the kind. Each name must therefore be in
exactly one of WireData, CNData and TSData; a name in two raises.

Example (`linegeometry.cimtbl`, 607):

```
# synthesized: the inline positions of LineGeometry 607
Object XYSpacing: mRID=wc_607_spc, name=607, isTemplate=true
Table XYConductorPosition: mRID, XYSpacing=wc_607_spc, sequenceNumber, xCoord (ft), yCoord (ft), kind
    wc_607_spc_1, 1, 0.0,  -4.0, phase
    wc_607_spc_2, 2, 0.25, -4.0, neutral

# untranscribed: reduce=true
Object WireConfiguration: mRID=wc_607, name=607, numberOfPhases=1, WireSpacing=wc_607_spc

Table WireSequenceConfiguration: mRID, WireConfiguration=wc_607, sequenceNumber, WireInfo
    wc_607_1, 1, ts_ts_1/0
    wc_607_2, 2, wire_cu_1/0
```

**Untranscribed:** `reduce` (Kron reduction is the consumer's choice from the segment's phases; 242 of 243 set
it), ratings (D9), `LineType`.

**Reader fix:** the reader kept the last `units` of the cond= blocks, so conductors in different units were
misread. It now raises when the blocks disagree; a block without `units` takes the last given, else DSS's initial
`ft`. No deck mixes units (engine-checked).

**Fail fast:** two name arrays; a name count or position count other than nconds; `spacing=` together with
inline positions; inline positions without `units`; a name in no catalog or in two; the scalar `cond`/`wire`/`x`/`h`
without the arrays.

**Oracle:** for every geometry the conductor names, coordinates and phase count equal the engine's
(`LineGeometries.Conductors/Xcoords/Ycoords/Phases`; `test_geometries_match_the_engine` on the vendored
IEEE13_Assets and IEEE4 decks). Checked by hand 2026-11-07, all match: IEEE9500 balanced 70 (both copies), YYD 3.

| Linespacing field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, LinespacingName]` | `500`, `505`, `510` | copied | `XYSpacing.name`; mRID = spc_ + name, lowercased; isTemplate = true |
| `nconds` | `Optional[int]` | `4`, `3`, `2` | structural | one XYConductorPosition per conductor, sequenceNumber 1..nconds; x and h must have nconds values |
| `nphases` | `Optional[int]` | `3`, `2`, `1` | structural | kind: phase for conductors 1..nphases, neutral after |
| `x` | `Union[float, list[float], NoneType]` | `[-4.0, -1.0, 3.0, 0.0]`, `[-4.0, 3.0, 0.0]`, `[0.5, 0.0]` | structural | XYConductorPosition.xCoord ({length}), one per conductor |
| `h` | `Union[float, list[float], NoneType]` | `[28.0, 28.0, 28.0, 24.0]`, `[28.0, 28.0, 24.0]`, `[29.0, 24.0]` | structural | XYConductorPosition.yCoord ({length}), one per conductor |
| `units` | `Optional[str]` | `ft` | mapped | the length unit of xCoord and yCoord (LENGTH_UNIT); unset raises |
| `detailed` | `Union[bool, Bool, NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the equivalent-distance form has no positions) |
| `EqDistPhPh` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the equivalent-distance form has no positions) |
| `EqDistPhN` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the equivalent-distance form has no positions) |
| `AvgPhaseHeight` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the equivalent-distance form has no positions) |
| `AvgNeutralHeight` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the equivalent-distance form has no positions) |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

| Linegeometry field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, LinegeometryName]` | `601`, `602`, `603` | copied | `WireConfiguration.name`; mRID = wc_ + name, lowercased |
| `nconds` | `Optional[int]` | `4`, `3`, `2` | structural | one WireSequenceConfiguration per conductor, sequenceNumber 1..nconds; the conductor names and (inline) positions must have nconds values |
| `nphases` | `Optional[int]` | `3`, `2`, `1` | copied | `WireConfiguration.numberOfPhases`; also the kind of an inline position: phase for 1..nphases, neutral after |
| `cond` | `Optional[int]` | `3`, `2`, `1` | structural | the reader folds the cond= blocks into the arrays; set alone (no cond=) it raises |
| `wire` | `Optional[str]` | `CU_1/0`, `2_ACSR`, `1/0_TPX` | structural | the reader folds the cond= blocks into the arrays; set alone (no cond=) it raises |
| `x` | `Optional[float]` | `0.5`, `0.25`, `0.1524` | structural | the reader folds the cond= blocks into the arrays; set alone (no cond=) it raises |
| `h` | `Optional[float]` | `-4.0`, `8.2296`, `-1.22` | structural | the reader folds the cond= blocks into the arrays; set alone (no cond=) it raises |
| `units` | `Optional[str]` | `ft`, `m` | mapped | the length unit of the inline positions (LENGTH_UNIT); unset raises. The reader raises when the cond= blocks give different units |
| `normamps` | `Optional[float]` |  | untranscribed | no home on a WireConfiguration; instance limits or untranscribed (plan D9) |
| `emergamps` | `Optional[float]` |  | untranscribed | no home on a WireConfiguration; instance limits or untranscribed (plan D9) |
| `reduce` | `Union[bool, Bool, NoneType]` | `True` | untranscribed | Kron reduction of the neutrals; a solver choice the consumer makes from the segment's phases |
| `spacing` | `Optional[str]` | `500`, `505`, `510` | structural | WireConfiguration.WireSpacing = spc_ + spacing; with inline positions it raises |
| `wires` | `Union[str, list[str], NoneType]` | `['ACSR_556_5', 'ACSR_556_5', 'ACSR_55...`, `['ACSR_4/0', 'ACSR_4/0', 'ACSR_4/0', ...`, `['ACSR_1/0', 'ACSR_1/0', 'ACSR_1/0']` | structural | the conductor names in cond order; each resolves to exactly one of WireData, CNData, TSData (a name in two raises) and is the WireSequenceConfiguration.WireInfo. A mixed assembly (607: a TS phase, a bare neutral) arrives here whole, so the array carries no kind |
| `cncable` | `Optional[str]` | `CN_250`, `1/0_Al_15kV_1/3` | structural | the reader folds the cond= blocks into the arrays; set alone (no cond=) it raises |
| `tscable` | `Optional[str]` | `TS_1/0` | structural | the reader folds the cond= blocks into the arrays; set alone (no cond=) it raises |
| `cncables` | `Union[str, list[str], NoneType]` | `['CN_250', 'CN_250', 'CN_250']`, `['1/0_Al_15kV_1/3']`, `['1/0_Al_15kV_1/3', '1/0_Al_15kV_1/3'...` | structural | as wires; only one of wires, cncables, tscables may be set |
| `tscables` | `Union[str, list[str], NoneType]` |  | structural | as wires; only one of wires, cncables, tscables may be set |
| `xs` | `Union[float, list[float], NoneType]` | `[-0.5, 0.0, 0.5]`, `[0.0, 0.25]`, `[-0.1524, 0.1524]` | structural | inline positions: a synthesized XYSpacing wc_<name>_spc, xCoord ({length}) |
| `hs` | `Union[float, list[float], NoneType]` | `[-4.0, -4.0, -4.0]`, `[-4.0, -4.0]`, `[10.5156, 8.2296]` | structural | inline positions: the synthesized XYSpacing's yCoord ({length}) |
| `Seasons` | `Optional[int]` |  | untranscribed | no home on a WireConfiguration; instance limits or untranscribed (plan D9) |
| `Ratings` | `Union[float, list[float], NoneType]` |  | untranscribed | no home on a WireConfiguration; instance limits or untranscribed (plan D9) |
| `LineType` | `Optional[str]` |  | untranscribed | no home on a WireConfiguration |
| `conductors` | `Union[str, list[str], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `like` | `Optional[str]` | `603` | untranscribed | the reader resolves like= before mapping |

## XfmrCode (S3b, approved and done 2026-11-08)

Mapper: `cimhub_opendss/importer/cimtbl/xfmrcode.py` (`map_xfmrcode(native, buses)`). Artifact `xfmrcode.cimtbl`,
after the line codes; the instances stay in `transformer.cimtbl`. Atom `tests/atoms/xfmrcode/codes.dss`:
- `ct25`: a center tap with two instances on a 3-phase system;
- `sub`: 3-phase delta-wye;
- `yyd`: 1-phase Y-Y-D, three cans;
- `unused`: no instance uses it.

Goldens `codes.cimtbl` and `codes_transformer.cimtbl`, tested by `tests/test_cimtbl_xfmrcode.py`. U2 is closed
(2026-11-08).

**Result.** 25 of 31 sweep decks bind with every S3 part (the S3a stops only). The center-tap templates are 9 in
IEEE8500 (1,177 instances), 9 in each IEEE9500 copy, 3 in IEEE123_PV and 1 in IEEE13_CDPSM (`Tpoletop`).
IEEE13_Assets has 2 TankEnd templates, IEEE4 YYD has 1. Every template's winding kV, kVA, %R and mesh x equal the
engine's for each instance, on the atom and the engine decks (IEEE13_CDPSM, IEEE13_Assets, IEEE8500, IEEE9500).
Multi-can tank templating and lug sequencing across a bank wait until CYME's form is seen; the CIM template class
is then updated to match (user, 2026-11-08).

**Template forms (the user's model, 2026-11-08; settles D10 and amends DSS-2's "lug to lug" for every code).**

**Census** (the instances that wait for S3b, counting duplicate deck copies):

| code kind | instances | form |
|---|---:|---|
| center tap: 1-phase, 3 windings, secondary halves equal (7.2/0.12/0.12, 2.4/0.12/0.12, ...) | 8,828 (IEEE8500, IEEE9500, IEEE123_PV, IEEE13_OCHRE, IEEE13_CDPSM `CT5`) | lugs |
| 1-phase, 3 windings Y-Y-D (IEEE4 YYD, 39.83/7.62/2.4 kV) | 3 | lugs (S3b-3; TankEnd before) |
| 3-phase, 2 windings | 3 | TankEnd |
| 1-phase, 2 windings | none outside the regulators (mapped in S3a) | lugs (S3b-3) |

Every center-tap instance has the split-phase secondary `bus2.1.0` + `bus2.0.2` and a line-to-neutral primary on
one node. No instance overrides its code's values, except `ppm_antifloat` (untranscribed).

- **TankEnd template** (3-phase only, S3b-3): `TransformerTankConfiguration`
  `xc_<code>`. Each DSS winding gives:
  - a `TransformerTankEnd` `xc_<code>_end_<n>` (`endNumber`, `connectionKind`, `rground`/`xground` from
    `Rneut`/`Xneut`; no phases);
  - a `TransformerWinding` `xc_<code>_wdg_<n>` (`FromTransformerEnd` = its tank end), with `ratedU` (LL), `baseU`
    (the coil), `ratedS`, `baseS` (per phase on a 3-phase code) and `r`.

  The mesh between windings carries `x`. The instance's `PowerTransformerEnd` n is template end n
  (`endNumber`); it carries the node, phases and `grounded`. Shapes: `transformer_template`,
  `transformer_by_template` (`xf_t1`).
- **Lug template** (every 1-phase code, S3b-3). Any code but a center tap has two lugs per winding, H1 H2, X1 X2,
  Y1 Y2 (IEEE C57.12.70), numbered in each coil's node order (its direction) over the instance's phase ends,
  end 1 first, so a 2-winding code's are 1-4 and IEEE4 YYD's 1-6; windings H1→H2, X1→X2, Y1→Y2, `baseS` each its
  own kVA. A center tap is a 3-winding tank, as CIMTBL-Models
  `distribution/templates/polemount_1ph_50kva_7200_12470y.cimtbl`:
  - `TransformerLug`s H1, H2, X1, X3, X2 (`sequenceNumber` 1-5: the instance phase end each lands on, below);
  - windings lug to lug from the polarity end: H1→H2, X1→X2 (DSS winding 2, `bus2.1.0`: s1→N) and X2→X3 (winding
    3, `bus2.0.2`: N→s2);
  - `designation` per IEEE C57.12.70 (the profile's text). X1 is the low-side terminal in phase with H1 under
    either polarity, so s1 (in phase with the primary) is X1 and s2 (at 180°) is X3. Additive polarity (X3, X2,
    X1: 1-phase, 200 kVA or less, 8,660 V or less) against subtractive (X1, X2, X3) only says where X1 sits on
    the tank, so the model is the same for both (confirmed by the user, 2026-11-08). Y designations belong to
    a true 3-winding unit's tertiary (IEEE4 YYD).

  The instance has a `PowerTransformerEnd` per bus (end 1: the primary node and phases; end 2: `s1s2N`) and, as the
  inline 1-phase mapper already does, a `TransformerPhaseEnd` per phase of each end's terminal, not per lug:
  `sequenceNumber` unique in the transformer, end 1 first, in terminal phase order, neutral last. A lug's
  `sequenceNumber` names the phase end it lands on, so several lugs may share one: three bussed center-tap cans
  on `bus2.1.2.3.0` are 4 phase ends for 12 lugs. Each DSS Transformer is its own PowerTransformer with one tank
  (DSS-2), so here the numbers line up one to one:
  - end 1 `BN` (line to neutral, DSS's default node 0) or `AB` (line to line) is 1, 2, which H1 and H2 land on;
  - end 2 `s1s2N` is s1 = 3, s2 = 4, N = 5, which X1, X3, X2 land on.

  The template's lug numbers are therefore those of a one-tank instance. A bank of tanks on one PowerTransformer
  needs a configuration per tank position (CIMTBL-Models `bank_oyod_50_50_7200_12470y.cimtbl`), which no DSS deck
  produces. An instance whose secondary is not `bus2.1.0` + `bus2.0.2` raises. Shapes:
  `transformer_template_1ph` and `transformer_by_template` (`xf_t2`), rewritten from today's phase-end template to
  this lug pattern.

**Values.**
- **`ratedU`** is the nameplate: phase to phase. A coil's voltage alone does not fix it, because 7.2 kV is
  7200/12470Y on a 3-phase system and 7200 on a single-phase one. So it comes from the bus system its instances
  sit on (the S3a rule: × √3 for a phase-to-neutral coil on a 3-phase system, × 2 for a split-phase half), and
  instances that disagree raise.
- **The rest:** `baseU` = the code's kV, the coil. `baseS` = winding 1's kVA on every coil. A split-phase half has
  `ratedS` = kVA / 2. `r` = `%Rs` per winding (or `%loadloss` / 2 on windings 1 and 2). The mesh 1-2, 1-3, 2-3
  `x` = Xhl, Xht, Xlt in percent on the From winding's baseU and baseS. `%imag` and `%noloadloss` go on the
  configuration.
- **Defaults** (DSS-6, `dss_default` on XfmrCode): `conns` wye, `%Rs` 0.2, Xhl/Xht/Xlt 7/35/30.

**Instances** (`transformer.cimtbl`): `PowerTransformer` `xf_<name>`, plus `TransformerTank` `xf_<name>_tank` with
`TankConfiguration` = `xc_<code>`, plus the ends above. A lug template's instance phase ends reference their end's
generated Terminal (`xf_<name>_T<n>`), which is their link to the PowerTransformer, since the instance has no
windings. **Amended 2026-11-09 (DSS S6c, T3):** a 1-phase instance of a TankEnd template gets them too, numbered in
its coil's node order, end 1 first (since S3b-3 every 1-phase code is a lug template, whose lugs are numbered so). That order is the coil's direction, which a PhaseCode cannot hold. Without it,
IEEE4 YYD's `tert.3.1` came back `tert.1.3`, and in the engine the 3-can bank's voltages moved by 1.6 kV. A code no unregulated instance uses is not written; the file's comment names it. An instance that sets a slot its code also sets raises
(the template must be the one source), except the untranscribed ones. A regulated instance keeps S3a's rule: it
takes its code's values, because CIM has no AutoTransformer template.

**Fail fast:** a code of other than 1 or 3 phases; windings other than 2 or 3; `Rneut` on a 1-phase code; a mesh From winding rated other than winding 1; a tap other than 1 on an
unregulated code; a center-tap code with an
instance that is not a split-phase secondary; instances of one code on different bus systems; `RdcOhms`,
`Seasons`, `Ratings` set.

**Engine checks:** each template's ratings, r and x against the engine's transformer of each instance.

**Decisions (approved 2026-11-08):**
- **S3b-1:** AutoTrans stays unmapped until a deck has one; the master's not-mapped count is the signal.
- **S3b-2:** the Y-Y-D 1-phase 3-winding code (IEEE4 YYD) is a TankEnd template (3 tank ends, D on the third).
  **Superseded by S3b-3.**
- **S3b-3 (the user's, 2026-11-19, via clallam_cim request 10):** "TransformerTankEnd is only for three-phase
  templates, single-phase should use TransformerPhaseEnd / TransformerLug." Every 1-phase code is a lug template
  (above), the instance's phase ends unchanged; a 2-phase code raises (no deck has one). The engine checks are
  unchanged.

| Xfmrcode field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, XfmrcodeName]` | `CT5`, `FdrXfmr`, `RegLeg` | copied | `TransformerTankConfiguration.name`; mRID = xc_ + name, lowercased |
| `phases` | `Optional[int]` | `1`, `3` | structural | 3: TankEnd template; 1: lug template (a center tap's H1 H2 X1 X3 X2, else two lugs per winding) |
| `windings` | `Optional[int]` | `3`, `2` | structural | one TransformerWinding each; 2 or 3 |
| `wdg` | `Optional[int]` |  | structural | the winding Rneut/Xneut belong to (the reader's tag); none = the last |
| `conn` | `Union[str, ForwardRef('ConnectionType'), NoneType]` |  | structural | the active-winding form; the reader folds wdg= blocks and bare values into the arrays |
| `kV` | `Optional[float]` |  | structural | the active-winding form; the reader folds wdg= blocks and bare values into the arrays |
| `kVA` | `Optional[float]` |  | structural | the active-winding form; the reader folds wdg= blocks and bare values into the arrays |
| `tap` | `Optional[str]` |  | structural | the active-winding form; the reader folds wdg= blocks and bare values into the arrays |
| `pct_R` | `Optional[float]` |  | structural | the active-winding form; the reader folds wdg= blocks and bare values into the arrays |
| `Rneut` | `Optional[float]` |  | structural | TankEnd rground (ohm) of its winding when >= 0; on a 1-phase code raises |
| `Xneut` | `Optional[float]` |  | structural | TankEnd xground (ohm) of its winding, with Rneut >= 0 |
| `conns` | `Union[str, ForwardRef('ConnectionType'), list[Union[str, ForwardRef('ConnectionType')]], NoneType]` | `[ConnectionType(text='wye', descripti...`, `[ConnectionType(text='delta', descrip...` | structural | TankEnd connectionKind (D, Y; grounding is the instance's); a center tap's secondary halves are I; default wye |
| `kVs` | `Union[float, list[float], NoneType]` | `[2.4, 0.12, 0.12]`, `[4.16, 0.48]`, `[2.4, 2.4]` | structural | winding baseU (the coil); ratedU phase-to-phase from the instances' common bus system (x sqrt 3 on a 3-phase system, x 2 for a split-phase half), and instances that disagree raise |
| `kVAs` | `Union[float, list[float], NoneType]` | `[5.0, 5.0, 5.0]`, `[500.0, 500.0]`, `[1666.0, 1666.0]` | structural | winding ratedS (a split-phase half: kVA / 2); baseS = winding 1's kVA on every coil (per phase on a 3-phase code) |
| `taps` | `Union[float, list[float], NoneType]` |  | structural | a tap other than 1 raises (a fixed tap is not mapped yet) |
| `Xhl` | `Optional[float]` | `2.04`, `2.0`, `0.01` | structural | mesh 1-2 x (percent on the From winding's baseU and baseS); default 7 |
| `Xht` | `Optional[float]` | `2.04`, `1.632`, `36.0` | structural | mesh 1-3 x; default 35 |
| `Xlt` | `Optional[float]` | `1.36`, `1.088`, `28.0` | structural | mesh 2-3 x; default 30 |
| `Xscarray` | `Union[float, list[float], NoneType]` |  | untranscribed | for more than 3 windings, which raise |
| `thermal` | `Optional[str]` |  | untranscribed | thermal model; no home in the network profile parts |
| `n` | `Optional[str]` |  | untranscribed | thermal model; no home in the network profile parts |
| `m` | `Optional[str]` |  | untranscribed | thermal model; no home in the network profile parts |
| `flrise` | `Optional[str]` |  | untranscribed | thermal model; no home in the network profile parts |
| `hsrise` | `Optional[str]` |  | untranscribed | thermal model; no home in the network profile parts |
| `pct_loadloss` | `Optional[float]` | `0.01`, `1.1` | derived | when pct_Rs is unset, r = loadloss / 2 on windings 1 and 2; set with pct_Rs, the two must agree |
| `pct_noloadloss` | `Optional[float]` | `0.2`, `0.6` | derived | TransformerTankConfiguration.noLoadLoss (kW) = % x winding 1 kVA |
| `normhkVA` | `Optional[float]` |  | untranscribed | a tank rating; instance OperationalLimitSet or untranscribed (plan D9) |
| `emerghkVA` | `Optional[float]` |  | untranscribed | a tank rating; instance OperationalLimitSet or untranscribed (plan D9) |
| `MaxTap` | `Optional[str]` | `1.1` | untranscribed | tap changer range; a regulated instance takes it (S3a); else untranscribed |
| `MinTap` | `Optional[str]` | `0.9` | untranscribed | tap changer range; a regulated instance takes it (S3a); else untranscribed |
| `NumTaps` | `Optional[int]` |  | untranscribed | tap changer range; a regulated instance takes it (S3a); else untranscribed |
| `pct_imag` | `Optional[float]` | `0.5`, `1.1` | copied | `TransformerTankConfiguration.percentMagnetizingCurrent` (percent) |
| `ppm_antifloat` | `Optional[float]` |  | untranscribed | numerical aid of the DSS solver |
| `pct_Rs` | `Union[float, list[float], NoneType]` | `[0.6, 1.2, 1.2]`, `[0.55, 0.55]`, `[0.0005, 0.0005]` | structural | winding r (percent on its own baseS); default 0.2 |
| `X12` | `Optional[float]` |  | structural | alias of Xhl |
| `X13` | `Optional[float]` |  | structural | alias of Xht |
| `X23` | `Optional[float]` |  | structural | alias of Xlt |
| `RdcOhms` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (home TransformerWinding.rDC) |
| `Seasons` | `Optional[int]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `Ratings` | `Union[float, list[float], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

## Transformer

Mapper: `cimhub_opendss/importer/cimtbl/transformer.py` (`map_transformer(native, buses, container)`). Atoms:
`tests/atoms/transformer/` — `xfm1` (3-phase, IEEE13), `sub3` (3-winding delta-wye-wye, neutral impedance on
winding 2), `reg1` (1-phase regulator unit), `service` (EPRI J1 7.2/0.24 kV), `center_tap` (phase-to-phase primary,
s1/s2 secondary), with `prereq.cimtbl`; tested by `tests/test_cimtbl_transformer.py`. Regulators and LTCs (S3a): see
"Transformer: regulators and LTCs" below. An `XfmrCode` instance no RegControl names waits for the template (S3b).

**Model (the user's, 2026-11-06).** Every DSS Transformer is its own `PowerTransformer` (`bank` is untranscribed),
with one `PowerTransformerEnd` per distinct bus, numbered in winding order. The end's terminal holds the phases.
- **3-phase, balanced ends:** `ratedU` = the DSS kV (phase-to-phase), `ratedS`, `r` (percent on the end's own
  rating) per end. `x` goes on the end-to-end mesh, in percent on winding 1's kVA at the From end's voltage, so a
  From end with another kVA raises. `pct_imag`/`pct_noloadloss` become end 1 `b`/`g` (percent). Wye gives `Yn` when
  grounded (neutral on node 0, or `Rneut` >= 0 on that winding) and `Y` otherwise; delta gives `D`.
- **1-phase, phase ends:** one `TransformerTank`, one `TransformerPhaseEnd` per phase conductor on each bus
  (`sequenceNumber` unique in the transformer, end 1 first, in terminal phase order), and one `TransformerWinding`
  per DSS winding from the phase end of its first conductor to that of its second. Windings 2 and 3 on one bus,
  both on node 0, with nodes 1 and 2, form a split-phase secondary (`s1s2N`, `I`). Otherwise node 1/2/3 is A/B/C,
  0 is N, an LN coil's end is `Y` and an LL coil's is `D`.

**Nameplate ratings** (IEEE C57.12.00-2021 Table 7; the catalog rule):
- `baseU` = the DSS kV, i.e. the coil voltage.
- `ratedU` (derived) is phase-to-phase:
  - an LN coil on a 3-phase system: kV × √3, never rounded (7.2 → 12.4708);
  - a split-phase half: 2 × kV;
  - an LL coil, or an LN coil on a single-phase system (the J1 240 V services): kV.
- `baseS` = winding 1's kVA on every coil. A split-phase half has `ratedS` = kVA / 2. On 1-phase, the kVAs must be
  equal, because each %R is on its own winding's kVA.

Whether a bus's system is 3-phase comes from the topology walk (`cimtopology.core.BusSystem`), as does its
BaseVoltage.

**Defaults** (listed in the row comment, `# defaulted: ...`): `phases` 3, `conns` wye, %R 0.2 per winding
(`pct_loadloss` / 2 on windings 1 and 2 when set), XHL/XHT/XLT 7/35/30. `Rneut`/`Xneut` belong to the reader's `wdg`
tag, else the last winding (the old importer's rule). Missing buses take DSS's default nodes: conductor k on node k,
the neutral on 0.

**Fail fast:**
- `phases` other than 1 or 3, or windings other than 2 or 3;
- an active-winding scalar (`kV`, `kVA`, `conn`, `bus`, `tap`, `%R`) left over after the reader (it resolves them
  to their winding, S3);
- a tap other than 1 on a transformer no RegControl names;
- `pct_Rs` and `pct_loadloss` that disagree, or `XHL` and `X12` that disagree;
- 3-phase nodes other than `1.2.3`;
- two windings on one bus that are not a split-phase secondary;
- a bus missing from the topology result.

| Transformer field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, TransformerName]` | `Reg1`, `Reg2`, `Reg3` | copied | `PowerTransformer.name`; mRID = xf_ + name, lowercased |
| `phases` | `Optional[int]` | `1`, `3` | structural | 1 = by phase ends, 3 = by balanced ends; default 3 |
| `windings` | `Optional[int]` | `3`, `2` | structural | 2 or 3; must match the buses |
| `wdg` | `Optional[int]` | `2` | structural | the winding Rneut/Xneut belong to (the reader's tag); none = the last |
| `bus` | `Optional[str]` |  | structural | the active-winding form; the reader folds wdg= blocks into the arrays, and a bare value raises |
| `conn` | `Union[str, ForwardRef('ConnectionType'), NoneType]` |  | structural | the active-winding form; the reader folds wdg= blocks into the arrays, and a bare value raises |
| `kV` | `Optional[float]` |  | structural | the active-winding form; the reader folds wdg= blocks into the arrays, and a bare value raises |
| `kVA` | `Optional[float]` |  | structural | the active-winding form; the reader folds wdg= blocks into the arrays, and a bare value raises |
| `tap` | `Optional[float]` |  | structural | the active-winding form; the reader folds wdg= blocks into the arrays, and a bare value raises |
| `pct_R` | `Optional[float]` |  | structural | the active-winding form; the reader folds wdg= blocks into the arrays, and a bare value raises |
| `Rneut` | `Optional[float]` | `0.0` | structural | rground (ohm) of its winding's end when >= 0; negative = no impedance |
| `Xneut` | `Optional[float]` | `0.4` | structural | xground (ohm) of its winding's end, with Rneut >= 0 |
| `buses` | `Union[str, list[str], NoneType]` | `['BRKR.1', 'RG60.1']`, `['BRKR.2', 'RG60.2']`, `['BRKR.3', 'RG60.3']` | structural | end node and terminal phases; one end per distinct bus |
| `conns` | `Union[str, ForwardRef('ConnectionType'), list[Union[str, ForwardRef('ConnectionType')]], NoneType]` | `[ConnectionType(text='delta', descrip...`, `[ConnectionType(text='wye', descripti...` | structural | connectionKind, grounded, default nodes; default wye |
| `kVs` | `Union[float, list[float], NoneType]` | `[2.4, 2.4]`, `[115.0, 4.16, 13.2]`, `[4.16, 0.48]` | structural | 3-phase: end ratedU; 1-phase: winding baseU, ratedU derived (x sqrt 3, x 2) |
| `kVAs` | `Union[float, list[float], NoneType]` | `[1666.0, 1666.0]`, `[5000.0, 5000.0, 1000.0]`, `[500.0, 500.0]` | structural | end ratedS / winding ratedS (halves / 2); winding 1's kVA is every baseS |
| `taps` | `Union[float, list[float], NoneType]` | `[1.0, 1.0625]`, `[1.0, 1.05]`, `[1.0, 1.06875]` | structural | the regulated winding's tap is RatioTapChanger.step (regcontrol.cimtbl); any other tap other than 1 raises |
| `XHL` | `Optional[float]` | `0.01`, `2.0`, `5.75` | structural | mesh 1-2 x (percent on winding 1's kVA); default 7 |
| `XHT` | `Optional[float]` | `0.025` | structural | mesh 1-3 x; default 35 |
| `XLT` | `Optional[float]` | `0.025` | structural | mesh 2-3 x; default 30 |
| `Xscarray` | `Union[float, list[float], NoneType]` |  | untranscribed | for more than 3 windings, which raise |
| `thermal` | `Optional[float]` |  | untranscribed | thermal model; no home in the network profile parts |
| `n` | `Optional[float]` |  | untranscribed | thermal model; no home in the network profile parts |
| `m` | `Optional[float]` |  | untranscribed | thermal model; no home in the network profile parts |
| `flrise` | `Optional[float]` |  | untranscribed | thermal model; no home in the network profile parts |
| `hsrise` | `Optional[float]` |  | untranscribed | thermal model; no home in the network profile parts |
| `pct_loadloss` | `Optional[float]` | `0.01`, `0.001`, `0.7639` | derived | when pct_Rs is unset, r = loadloss / 2 on windings 1 and 2; set with pct_Rs, the two must agree |
| `pct_noloadloss` | `Optional[float]` | `0.0851`, `0.34`, `0.1348` | derived | 3-phase: end 1 g (percent); 1-phase: tank noLoadLoss = % x kVA; a regulator has no home for it (row comment) |
| `normhkVA` | `Optional[float]` | `25.0`, `15.0`, `75.0` | untranscribed | instance OperationalLimitSet or untranscribed (plan D9) |
| `emerghkVA` | `Optional[float]` | `35.0`, `21.0`, `105.0` | untranscribed | instance OperationalLimitSet or untranscribed (plan D9) |
| `sub` | `Union[bool, Bool, NoneType]` | `True` | untranscribed | DSS report flag |
| `MaxTap` | `Optional[float]` | `1.1`, `1.05` | structural | the RatioTapChanger range of a regulated transformer (regcontrol.cimtbl); else untranscribed; default 1.1 |
| `MinTap` | `Optional[float]` | `0.9`, `0.95` | structural | the RatioTapChanger range of a regulated transformer (regcontrol.cimtbl); else untranscribed; default 0.9 |
| `NumTaps` | `Optional[int]` | `16`, `32` | structural | the RatioTapChanger range of a regulated transformer (regcontrol.cimtbl); else untranscribed; default 32 |
| `subname` | `Optional[str]` | `M1`, `HVMV_Sub` | untranscribed | DSS report label |
| `pct_imag` | `Optional[float]` | `0.0001`, `0.5` | structural | 3-phase: end 1 b (percent); 1-phase: tank percentMagnetizingCurrent; a regulator has no home for it (row comment) |
| `ppm_antifloat` | `Optional[float]` | `0.0`, `5.0` | untranscribed | numerical aid of the DSS solver |
| `pct_Rs` | `Union[float, list[float], NoneType]` | `[0.0005, 0.0005, 0.0005]`, `[0.55, 0.55]`, `[0.67, 0.67]` | structural | 3-phase: end r (percent); 1-phase: winding r (percent); default 0.2 |
| `bank` | `Optional[str]` | `Reg`, `FEEDER1_REG1`, `FEEDER2_REG2` | untranscribed | each DSS Transformer is its own PowerTransformer |
| `XfmrCode` | `Optional[str]` | `CT5`, `RegLeg`, `SubXfmr` | structural | a regulated instance takes the code's values (with_code); any other waits for the template (S3b) and is counted on the master |
| `XRConst` | `Union[bool, Bool, NoneType]` |  | untranscribed | harmonics option |
| `X12` | `Optional[float]` |  | structural | alias of XHL |
| `X13` | `Optional[float]` |  | structural | alias of XHT |
| `X23` | `Optional[float]` |  | structural | alias of XLT |
| `LeadLag` | `Union[str, ForwardRef('LeadLagType'), NoneType]` | `Lag` | untranscribed | PowerTransformer.vectorGroup clock; vectorGroup not mapped yet |
| `Core` | `Union[str, ForwardRef('CoreType'), NoneType]` |  | untranscribed | core type; no home in the network profile parts |
| `RdcOhms` | `Union[float, list[float], NoneType]` |  | untranscribed | home TransformerWinding.rDC; not mapped until a deck sets it |
| `Seasons` | `Optional[int]` |  | untranscribed | instance OperationalLimitSet or untranscribed (plan D9) |
| `Ratings` | `Union[float, list[float], NoneType]` |  | untranscribed | instance OperationalLimitSet or untranscribed (plan D9) |
| `normamps` | `Optional[float]` |  | untranscribed | instance OperationalLimitSet or untranscribed (plan D9) |
| `emergamps` | `Optional[float]` |  | untranscribed | instance OperationalLimitSet or untranscribed (plan D9) |
| `faultrate` | `Optional[float]` |  | untranscribed | reliability data; no home in the network profile parts |
| `pct_perm` | `Optional[float]` |  | untranscribed | reliability data; no home in the network profile parts |
| `repair` | `Optional[float]` |  | untranscribed | reliability data; no home in the network profile parts |
| `basefreq` | `Optional[float]` |  | untranscribed | no home on a transformer |
| `enabled` | `Union[bool, Bool, NoneType]` | `True` | copied | `PowerTransformer.normallyInService` |
| `like` | `Optional[str]` | `reg3a`, `reg4a`, `reg1a` | untranscribed | the reader resolves like= before mapping |

**Deck sweep (2026-11-06, placeholder bus systems).** 1,365 of the 1,378 inline transformers in 11 decks map. Stops:

| stop | count | next |
|---|---|---|
| taps ≠ 1 | 6 (IEEE13_original regulators) | lifted in S3a: regulators |
| `kVA=750` with no `wdg=` | 8 (ieee9500 `*-DIES1`) | lifted in S3a: the reader's active-winding rule (2-winding kVA sets both) |
| `%R=0.1` with no `wdg=` | 2 (J1 `ExistingSite*`) | lifted in S3a: winding 2 gets 0.1, winding 1 the default 0.2, as the engine |

Reader fixes this slice needed: numeric bus and wire names stayed floats (`634` → `634.0`, i.e. node 0); quoted
arrays (`conns='delta delta'`, IEEE37) failed to build, and the reader dropped `reg1a` with only a log line. A
failed build now raises.

## S3 (S3a approved and done 2026-11-08)

S3 maps the network: lines and switches, the transformers into the orchestrator, regulators and LTCs, and their
RegControls. Census of the 31 sweep decks, 2026-11-07:
- **Lines:** 34,254 in all. By linecode 27,679; by geometry 5,294; inline sequence values 1,162 (678 of them
  switches); inline matrix 4 (1 a switch); spacing + wires 3; switches with no impedance 112.
- **Switch controls:** 98 Fuses, 161 Reclosers, 336 SwtControls.
- **Regulators:** 176 RegControls.

**Scope split (approved, R3).** A non-regulator Transformer by XfmrCode waits for U2. In the sweep that is IEEE8500
1,177, IEEE9500 1,275, IEEE123_PV 82, IEEE13_OCHRE 16, IEEE13_CDPSM 1 (`Tpoletop`). So S3 splits:
- **S3a** (done): lines, switches, transformers in `MAPPING_ORDER`, VoltageRegulators and LTCs (a regulator by
  XfmrCode included), RegControl.
- **S3b** (done 2026-11-08): XfmrCode templates and their instances (section XfmrCode). AutoTrans stays unmapped
  until a deck has one (S3b-1).

Until S3b a Transformer by XfmrCode that no RegControl names was counted on the master's `# not mapped:` line;
S3b maps it by template.

**Result (2026-11-08).** The S3a exit is met:
- IEEE13_CDPSM, IEEE123 and IEEE8500 bind with every line, switch, transformer and regulator. Their XfmrCode
  transformers are counted on the master.
- 25 of the 31 sweep decks bind with every S3a part. The six stops:
  - DSS-10, a line's phases ≠ its code's `nphases`: J1, K1, M1, IEEE13_OCHRE;
  - the `ieee9500_2025` balanced copy (an `Open` of a line it never defines; the engine fails too);
  - the PNNL balanced IEEE9500 deck, whose lines name LineCodes it never loads (the engine fails too).
- Engine checks, on the atoms and the 8 engine decks (IEEE13 ×3, IEEE123, IEEE37, IEEE4, IEEE8500, IEEE9500):
  - every line's ratings, and the z and b totals of every line by code or by inline values;
  - every switch state;
  - every RegControl setting, the tap range and the regulator nameplate and mesh;
  - the tap position, on the atom (a deck that solves when compiled moves its taps).

**Engine rules found in S3** (each pinned with a probe and kept in a test):
- **Ratings.** A line copies each of `normamps`/`emergamps` it leaves unset from its LineCode, or from its
  LineGeometry. A geometry rating left unset is its first conductor's. A wire with `normamps` and no `emergamps` is
  rated 1.5 × normamps. A spacing + wires line takes its first wire's.
- **Default C.** A matrix LineCode without `cmatrix` keeps the engine's default C matrix: self (2 C1 + C0)/3 and
  mutual (C0 − C1)/3 from C1 = 3.4, C0 = 1.6 nF per unit length, on any number of phases
  (`cimhub_core.derived.sequence.balanced_matrix`). IEEE13_original's codes are this case (an amendment to the S2
  LineCode mapper; the row says `# defaulted: cmatrix from C1=3.4, C0=1.6`).
- **Inline defaults.** A sequence line leaves some of r1, x1, r0, x0, C1, C0 unset; they take the DSS defaults.
  r and x stay per unit length as they are. C1 and C0 are kept per kft and converted to the line's `units`.
- **Unitless geometry line.** Its length is in metres.

**Reader fixes in S3** (§3.4 of the plan; each checked against the engine):
- A value with no name goes to the property after the last one named, in the schema's `order`. `{...}` is RPN.
  The decks use this as `Normamps=156 {156 1.25 *}`: emergamps = 195 on the J1, K1, M1, IEEE8500 and IEEE9500
  triplex codes, which the reader used to drop silently. A positional value on a class the reader rewrites by
  blocks (Transformer, XfmrCode, AutoTrans, LineGeometry) raises.
- A bare per-winding property (`bus kV kVA conn tap %R`) goes to the active winding: the last `wdg=`, else the last
  winding an array set (an array sets every winding), else winding 1. On a 2-winding transformer, `kVA` sets both
  windings, even inside a `wdg=` block (`wdg=1 kva=500 wdg=2 kva=300` is [300, 300] in the engine).
  - This lifts the old `kVA=750` stop on the ieee9500 `*-DIES1`/`-ESS`/`-MT` transformers.
  - A winding no property sets takes the per-winding default (`dss_default` on Transformer/XfmrCode `kV kVA conn
    tap %R`, as the engine does), with a warning. J1's `ExistingSite*` `%R=0.1` was this case. An unset `bus`
    raises.

### Line and switches

Mapper: `cimhub_opendss/importer/cimtbl/line.py` (`map_line`; `CONTROLS` for Fuse, Recloser, SwtControl).
Artifact `line.cimtbl`; shapes `line_by_impedance`, `line_by_wire_configuration`, `switch`. Atoms in
`tests/atoms/line/`, tested by `tests/test_cimtbl_line.py`:
- `codes.dss` (after IEEE13_CDPSM): lines by code (one code without `cmatrix`), inline sequence lines (one with
  defaults, one unitless 1-phase), and a LoadBreakSwitch, Fuse, Recloser, an open SwtControl tie and an `Open`
  section;
- `geometry.dss` (after IEEE13_Assets): geometry lines (one unitless), a spacing + wires line, ratings from the
  first wire.

**Identity.** An `ACLineSegment` is `ln_` + name and a switch `sw_` + name, lowercased. Every Switch subclass shares
`sw_`, so the switch's class can change without changing its mRID.

**Class (DSS-9).** A Line with `Switch=y` is a switch:
- a `Fuse` whose `SwitchedObj` (else `MonitoredObj`, the DSS default) is that line makes it a `Fuse`, and its
  `RatedCurrent` becomes `ratedCurrent`;
- a `Recloser` makes it a `Recloser`;
- otherwise (a `SwtControl`, or no control) it is a `LoadBreakSwitch`.

What raises: a Fuse or Recloser on a line without `Switch=y`; two controls of different classes on one line; a
control whose line no `New` defines. In the sweep, every Fuse and Recloser switches the line it monitors.

**Switch state.**
- `open`: an `Open` command on either terminal (`Options.open_terminals`), or a SwtControl with `State=Open`.
- `normalOpen`: the SwtControl's `Normal`, else the same as `open`.

An `Open` command and a SwtControl `State` that disagree raise. A Fuse whose `Normal`/`State` give a value count other than its line's
phases raises (found by the S6b export, 2026-11-09). The engine sets a fuse phase by phase, so `State=open` on a
3-phase line opens phase 1 only, and CIM's `open` is the whole switch's. No sweep deck sets a Fuse state. So does an `Open` on a line that is not a switch:
`Terminal.connected` would be its home, but no deck needs it.
- **Sweep:** 33 SwtControls are Open with `Normal` = `State` on every one. ieee9500 has 9 `Open` commands and
  IEEE123_test_harness 2, all on switch lines.
- **Dropped from switches:** a switch's impedance, length and ratings stay untranscribed (DSS-8). DSS needs them
  only as numerical stand-ins: `r1=1e-4`, or the `Switch=y` defaults.

**Template (`ACLineSegment`).** Exactly one of the following; a line that combines two raises:
- `linecode=` → `WireConfiguration` = the WireConfiguration of the code's template for the line's unit
  (`lc_<code>_wc`, or `lc_<code>_<unit>_wc` when the code's lines disagree, DSS-3, DSS-14);
- `geometry=` → `WireConfiguration` = `wc_<geometry>`;
- `spacing=` + `wires=`/`cncables=`/`tscables=` → a synthesized `WireConfiguration` `ln_<name>_wc` on
  `spc_<spacing>`, conductors in order (IEEE13_Assets `684652`). This is the counterpart of S2's synthesized
  spacing;
- inline `r1`…`B0` or `rmatrix`/`xmatrix`/`cmatrix` → `PerLengthImpedance` = a synthesized
  `PerLengthSequenceImpedance` or `PerLengthPhaseImpedance` `ln_<name>_lc` of the line's own, `isTemplate=false`
  (DSS-14), under `# synthesized` in `line.cimtbl` (DSS-8). It goes through the
  LineCode mapper's own functions, so DSS-3 (units, gate), DSS-3b and DSS-4 apply unchanged.
  - **Naming:** DSS-8 said `lc_<line>`. A line and a code may share a name, so this proposes `ln_<name>_lc`.
  - **Units:** a unitless inline line goes through the same magnitude gate, over the deck's unitless inline
    lines (its own group, so its inference is stated on its own rows). Sweep: 432 in M1, 8 in IEEE123, 1 in IEEE37.
  - Unset sequence values take the engine's defaults (above).

**Length and units.** `length` (default 1, defaulted) is in the line's `units`. A unitless line by code takes the
code's template unit: the code's units, else the gate (DSS-3). A unitless line by geometry (M1, 2 lines) takes
metres, as the engine reads it (`# defaulted: units=m`).

**Phases.** They come from bus1's nodes:
- 1/2/3 → A/B/C, in bus order (`645.3.2` → `CB`, the matrix row order);
- on a split-phase island (the walk, DSS-5): 1/2 → s1/s2;
- no nodes → 1..`phases`;
- a geometry with neutral conductors adds `N` (601: `ABCN`).

What raises:
- bus2's phase nodes differing from bus1's (a transposition);
- `phases` ≠ the code's `nphases` (DSS-10, deferred). That leaves J1 (1,381 lines), K1 (743), M1 (1,949) and
  IEEE13_OCHRE (50) in the sweep table. IEEE8500 and IEEE9500 have no mismatch: their lines take `phases` from the
  code.

**Ratings (R1, approved).** A line's `normamps` and `emergamps` go on an `OperationalLimitSet`
`ln_<name>_limits` (`Equipment` = the segment) with one `CurrentLimit` (`normalValue`, A) each:
- `ln_<name>_norm` on `OperationalLimitType` `olt_normal`: `durationKind=normal`, `isInfiniteDuration=true`,
  `direction=absoluteValue`;
- `ln_<name>_emerg` on `olt_emergency`: `durationKind=emergency`, `isInfiniteDuration=false`,
  `direction=absoluteValue`.

The two types (GridAPPS-D `LimitDurationKind`, added to cim18v17 2026-11-07) are written once in the master, so
later slices (transformers, catalogs) share them. `season` (`CalendarSeasonKind`) stays unset. DSS's `Seasons` and
`Ratings` are an indexed array that a `SeasonSignal` loadshape selects, and they name no calendar season. No deck
in the sweep sets them, so they raise until a deck shows the index-to-season convention. Values:
- the line's own value, else what the engine copies: its code's, else its geometry's, else the geometry's first
  conductor's, with a wire's emergency rating defaulting to 1.5 × normamps (`# ratings: normamps from LineCode
  mtx601`). DSS keeps the last value set, and the reader does not record the order. Decks give a line's ratings
  after its `linecode=`, and the engine check agrees on every engine deck;
- nothing from DSS's 400/600 A defaults.

**Defaults** (from the `dss_default` annotations, filled for Line, Fuse, Recloser and SwtControl in this slice,
DSS-6): `length` 1, `phases` 3, `units` none.

**Expected differences from the hand translation:** IEEE13_CDPSM `Brkr1` becomes a `LoadBreakSwitch`, not a
`Breaker`: DSS has no breaker class, and DSS-9 decides by control.

| Line field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, LineName]` | `632633`, `632645`, `632670` | copied | `ACLineSegment.name`, `Switch.name`; mRID = ln_ + name (segment) or sw_ + name (switch), lowercased |
| `bus1` | `str` | `632.1.2.3`, `632.3.2`, `MID.1.2.3` | structural | node1, and the phases from its nodes: 1/2/3 = A/B/C, s1/s2 on a split-phase island (DSS-5); no nodes = 1..phases |
| `bus2` | `Optional[str]` | `633.1.2.3`, `645.3.2`, `670.1.2.3` | structural | node2; its phase nodes must equal bus1's (a transposition raises) |
| `linecode` | `Optional[str]` | `mtx602`, `mtx603`, `mtx601` | structural | ACLineSegment.WireConfiguration = the WireConfiguration of the code's template for the line's unit (lc_<code>_wc or lc_<code>_<unit>_wc, DSS-3, DSS-14) |
| `length` | `Optional[float]` | `500.0`, `667.0`, `300.0` | copied | `ACLineSegment.length` ({length}); default 1 (defaulted); none on a switch |
| `phases` | `Optional[int]` | `3`, `2`, `1` | structural | the phase count; unset = the code's or geometry's nphases, else 3; one that differs from the code's nphases raises (DSS-10) |
| `r1` | `Optional[float]` | `0.0001`, `0.001`, `1.0` | structural | the line's own PerLengthImpedance ln_<name>_lc (isTemplate=false) in line.cimtbl, values per length as written, through the LineCode mapper's rules (DSS-3 units, DSS-3b, DSS-4, DSS-14); on a switch untranscribed |
| `x1` | `Optional[float]` | `0.0`, `0.001`, `1.0` | structural | the line's own PerLengthImpedance ln_<name>_lc (isTemplate=false) in line.cimtbl, values per length as written, through the LineCode mapper's rules (DSS-3 units, DSS-3b, DSS-4, DSS-14); on a switch untranscribed |
| `r0` | `Optional[float]` | `0.0001`, `0.001`, `1.0` | structural | the line's own PerLengthImpedance ln_<name>_lc (isTemplate=false) in line.cimtbl, values per length as written, through the LineCode mapper's rules (DSS-3 units, DSS-3b, DSS-4, DSS-14); on a switch untranscribed |
| `x0` | `Optional[float]` | `0.0`, `0.001`, `1.0` | structural | the line's own PerLengthImpedance ln_<name>_lc (isTemplate=false) in line.cimtbl, values per length as written, through the LineCode mapper's rules (DSS-3 units, DSS-3b, DSS-4, DSS-14); on a switch untranscribed |
| `C1` | `Optional[float]` | `0.0`, `0.000212206590789194`, `0.000450939005427037` | structural | the line's own PerLengthImpedance ln_<name>_lc (isTemplate=false) in line.cimtbl, values per length as written, through the LineCode mapper's rules (DSS-3 units, DSS-3b, DSS-4, DSS-14); on a switch untranscribed |
| `C0` | `Optional[float]` | `0.0`, `0.000636619772367581`, `0.00135281701628111` | structural | the line's own PerLengthImpedance ln_<name>_lc (isTemplate=false) in line.cimtbl, values per length as written, through the LineCode mapper's rules (DSS-3 units, DSS-3b, DSS-4, DSS-14); on a switch untranscribed |
| `rmatrix` | `Union[float, list[float], NoneType]` | `[1.3238, 0.2066, 1.3294]`, `[0.0001]` | structural | the line's own PerLengthImpedance ln_<name>_lc (isTemplate=false) in line.cimtbl, values per length as written, through the LineCode mapper's rules (DSS-3 units, DSS-3b, DSS-4, DSS-14); on a switch untranscribed |
| `xmatrix` | `Union[float, list[float], NoneType]` | `[1.3569, 0.4591, 1.3471]`, `[0.0]` | structural | the line's own PerLengthImpedance ln_<name>_lc (isTemplate=false) in line.cimtbl, values per length as written, through the LineCode mapper's rules (DSS-3 units, DSS-3b, DSS-4, DSS-14); on a switch untranscribed |
| `cmatrix` | `Union[float, list[float], NoneType]` | `[0.0]` | structural | the line's own PerLengthImpedance ln_<name>_lc (isTemplate=false) in line.cimtbl, values per length as written, through the LineCode mapper's rules (DSS-3 units, DSS-3b, DSS-4, DSS-14); on a switch untranscribed |
| `Switch` | `Union[bool, Bool, NoneType]` | `True` | structural | a Switch (sw_) instead of an ACLineSegment; class from its control (DSS-9) |
| `Rg` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (Carson earth return; the consumer's choice for geometry) |
| `Xg` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (Carson earth return; the consumer's choice for geometry) |
| `rho` | `Optional[float]` |  | structural | the deck's EarthResistivity.rho (ohm-m), which every geometry line must agree on (geometry.earth_statement); on another line it raises |
| `geometry` | `Optional[str]` | `602`, `603`, `601` | structural | ACLineSegment.WireConfiguration = wc_<geometry> |
| `units` | `Union[str, ForwardRef('LengthUnit'), NoneType]` | `Ft`, `mi`, `km` | mapped | the length unit (LENGTH_UNIT); unset: the template's unit (DSS-3) |
| `spacing` | `Optional[str]` | `510` | structural | with spacing=: a synthesized WireConfiguration ln_<name>_wc on spc_<spacing>, conductors in order |
| `cncables` | `Union[str, list[str], NoneType]` |  | structural | with spacing=: a synthesized WireConfiguration ln_<name>_wc on spc_<spacing>, conductors in order |
| `tscables` | `Union[str, list[str], NoneType]` |  | structural | with spacing=: a synthesized WireConfiguration ln_<name>_wc on spc_<spacing>, conductors in order |
| `wires` | `Union[str, list[str], NoneType]` | `['ACSR_1/0', 'ACSR_1/0']` | structural | with spacing=: a synthesized WireConfiguration ln_<name>_wc on spc_<spacing>, conductors in order |
| `EarthModel` | `Union[str, ForwardRef('EarthModelType'), NoneType]` |  | untranscribed | the earth model of the impedance calculation; the consumer's choice |
| `B1` | `Optional[float]` |  | structural | the line's own PerLengthImpedance ln_<name>_lc (isTemplate=false) in line.cimtbl, values per length as written, through the LineCode mapper's rules (DSS-3 units, DSS-3b, DSS-4, DSS-14); on a switch untranscribed |
| `B0` | `Optional[float]` |  | structural | the line's own PerLengthImpedance ln_<name>_lc (isTemplate=false) in line.cimtbl, values per length as written, through the LineCode mapper's rules (DSS-3 units, DSS-3b, DSS-4, DSS-14); on a switch untranscribed |
| `Seasons` | `Optional[int]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (an indexed rating array that names no calendar season; home OperationalLimitType.season) |
| `Ratings` | `Union[float, list[float], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (with Seasons) |
| `LineType` | `Union[str, ForwardRef('LineTypeCode'), NoneType]` |  | untranscribed | no home in the network profile parts |
| `EpsRmedium` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `HeightOffset` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `HeightUnit` | `Union[str, ForwardRef('LengthUnit'), NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `conductors` | `Union[str, list[str], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `normamps` | `Optional[float]` | `230.0`, `90.0`, `450.0` | structural | instance OperationalLimitSet ln_<name>_limits (see Ratings); on a switch untranscribed |
| `emergamps` | `Optional[float]` | `130.0`, `600.0`, `300.0` | structural | instance OperationalLimitSet ln_<name>_limits (see Ratings); on a switch untranscribed |
| `faultrate` | `Optional[float]` |  | untranscribed | reliability data; no home in the network profile parts |
| `pct_perm` | `Optional[float]` |  | untranscribed | reliability data; no home in the network profile parts |
| `repair` | `Optional[float]` |  | untranscribed | reliability data; no home in the network profile parts |
| `basefreq` | `Optional[float]` |  | structural | the line's own impedance's calculatedFrequency and the frequency of its b; unset: the deck's (DSS-3b) |
| `enabled` | `Union[bool, Bool, NoneType]` | `True`, `False` | copied | `ACLineSegment.normallyInService`, `Switch.normallyInService` |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

| Fuse field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, FuseName]` | `Fuse1`, `2002200004641085`, `2002200004868472` | untranscribed | the switch takes the Line's name; the Fuse names no CIM object |
| `MonitoredObj` | `Optional[str]` | `Line.Fuse1`, `Line.2002200004641085_sw`, `Line.2002200004868472_sw` | structural | the Line it switches: SwitchedObj, else MonitoredObj (the DSS default); not a Switch=y line raises |
| `MonitoredTerm` | `Optional[int]` |  | untranscribed | the switch opens both terminals in CIM; DSS's terminal choice has no home |
| `SwitchedObj` | `Optional[str]` | `Line.2002200004641085_sw`, `Line.2002200004868472_sw`, `Line.200220000499_sw` | structural | the Line it switches: SwitchedObj, else MonitoredObj (the DSS default); not a Switch=y line raises |
| `SwitchedTerm` | `Optional[int]` |  | untranscribed | the switch opens both terminals in CIM; DSS's terminal choice has no home |
| `FuseCurve` | `Optional[float]` |  | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `RatedCurrent` | `Optional[float]` | `100.0`, `65.0`, `15.0` | copied | `Fuse.ratedCurrent` (A) |
| `Delay` | `Optional[str]` |  | untranscribed | control timing; no home on a Switch |
| `Action` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the deprecated form of State) |
| `Normal` | `Union[str, list[str], NoneType]` |  | structural | Normal -> normalOpen, State -> open on the switch; with an Open command on the line they must agree |
| `State` | `Union[str, list[str], NoneType]` |  | structural | Normal -> normalOpen, State -> open on the switch; with an Open command on the line they must agree |
| `basefreq` | `Optional[float]` |  | untranscribed | no home on a switch |
| `enabled` | `Union[bool, Bool, NoneType]` |  | untranscribed | a disabled control leaves its switch in place; no home |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

| Recloser field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, RecloserName]` | `Rec1`, `A333_48332`, `G9343_48332` | untranscribed | the switch takes the Line's name; the Recloser names no CIM object |
| `MonitoredObj` | `Optional[str]` | `Line.Rec1`, `Line.A333_48332_sw`, `Line.G9343_48332_sw` | structural | the Line it switches: SwitchedObj, else MonitoredObj (the DSS default); not a Switch=y line raises |
| `MonitoredTerm` | `Optional[int]` |  | untranscribed | the switch opens both terminals in CIM; DSS's terminal choice has no home |
| `SwitchedObj` | `Optional[str]` | `Line.A333_48332_sw`, `Line.G9343_48332_sw`, `Line.L5397_48332_sw` | structural | the Line it switches: SwitchedObj, else MonitoredObj (the DSS default); not a Switch=y line raises |
| `SwitchedTerm` | `Optional[int]` |  | untranscribed | the switch opens both terminals in CIM; DSS's terminal choice has no home |
| `NumFast` | `Optional[int]` |  | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `PhaseFast` | `Optional[float]` |  | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `PhaseDelayed` | `Optional[float]` |  | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `GroundFast` | `Optional[float]` |  | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `GroundDelayed` | `Optional[float]` |  | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `PhaseTrip` | `Optional[str]` | `1200.0`, `200` | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `GroundTrip` | `Optional[str]` | `400.0`, `40` | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `PhaseInst` | `Optional[str]` |  | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `GroundInst` | `Optional[str]` |  | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `Reset` | `Optional[str]` |  | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `Shots` | `Optional[int]` | `3` | structural | one RecloseSequence <switch>_rs<n> per reclosure, Shots - 1 of them, recloseDelay = RecloseIntervals[n] (s); unset: the engine's Shots 4, intervals 0.5 2 2 (defaulted). Both given and disagreeing raise, and so does Shots above 4 without intervals (the engine reads past its defaults) |
| `RecloseIntervals` | `Union[float, list[float], NoneType]` |  | structural | one RecloseSequence <switch>_rs<n> per reclosure, Shots - 1 of them, recloseDelay = RecloseIntervals[n] (s); unset: the engine's Shots 4, intervals 0.5 2 2 (defaulted). Both given and disagreeing raise, and so does Shots above 4 without intervals (the engine reads past its defaults) |
| `Delay` | `Optional[str]` |  | untranscribed | control timing; no home on a Switch |
| `Action` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the deprecated form of State) |
| `TDPhFast` | `Optional[str]` |  | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `TDGrFast` | `Optional[str]` |  | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `TDPhDelayed` | `Optional[str]` |  | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `TDGrDelayed` | `Optional[str]` |  | untranscribed | protection setting; no home in cim18v17's protection function blocks (DSS-11) |
| `Normal` | `Optional[str]` |  | structural | Normal -> normalOpen, State -> open on the switch; with an Open command on the line they must agree |
| `State` | `Optional[str]` |  | structural | Normal -> normalOpen, State -> open on the switch; with an Open command on the line they must agree |
| `basefreq` | `Optional[float]` |  | untranscribed | no home on a switch |
| `enabled` | `Union[bool, Bool, NoneType]` |  | untranscribed | a disabled control leaves its switch in place; no home |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

| Swtcontrol field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, SwtcontrolName]` | `2002200004641085`, `2002200004868472`, `200220000499` | untranscribed | the switch takes the Line's name; the SwtControl names no CIM object |
| `SwitchedObj` | `Optional[str]` | `Line.2002200004641085_sw`, `Line.2002200004868472_sw`, `Line.200220000499_sw` | structural | the Line it switches: SwitchedObj, else MonitoredObj (the DSS default); not a Switch=y line raises |
| `SwitchedTerm` | `Optional[int]` |  | untranscribed | the switch opens both terminals in CIM; DSS's terminal choice has no home |
| `Action` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the deprecated form of State) |
| `Lock` | `Union[bool, Bool, NoneType]` | `True` | untranscribed | control lock; no home on a Switch |
| `Delay` | `Optional[float]` |  | untranscribed | control timing; no home on a Switch |
| `Normal` | `Optional[str]` | `Closed`, `Open` | structural | Normal -> normalOpen, State -> open on the switch; with an Open command on the line they must agree |
| `State` | `Optional[str]` | `Closed`, `Open` | structural | Normal -> normalOpen, State -> open on the switch; with an Open command on the line they must agree |
| `Reset` | `Union[bool, Bool, NoneType]` |  | untranscribed | a command, not a setting |
| `basefreq` | `Optional[float]` |  | untranscribed | no home on a switch |
| `enabled` | `Union[bool, Bool, NoneType]` |  | untranscribed | a disabled control leaves its switch in place; no home |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

### Transformer: regulators and LTCs

`transformer.py` (seeded) joins `MAPPING_ORDER`. A Transformer named by a RegControl changes as follows
(DSS-13):
- **Regulator** (equal winding kV; 133 single-phase, 4 three-phase gang in the sweep): a `VoltageRegulator`
  `xf_<name>` (same prefix, since it is the same DSS object) with two `AutoTransformerEnd`s `xf_<name>_1`,
  `xf_<name>_2`.
  - Each end carries `node`, `endNumber`, `grounded`, `baseU` (kV, the coil voltage), `ratedS` (kVA) and
    `BaseVoltage`. Its `phase` is a PhaseCode: `AN` for a line-to-neutral unit, `AB` for a line-to-line unit
    (IEEE37), `ABCN` for a 3-phase gang unit.
  - **Impedance (the user's model, 2026-11-07):** one `TransformerMeshImpedance` `xf_<name>_mesh_12` from end 1 to
    end 2, with x = `XHL` and r = %R1 + %R2 (percent). Their base is end 1's `baseU`/`ratedS`, the base CIM-Tables'
    `z_base` gives an `AutoTransformerEnd`. The row comment says it is the engine's stand-in impedance: a
    regulator's nameplate has no %Z, and OpenDSS needs XHL only because it has no real autotransformer.
  - What raises: unequal kVAs, a delta winding, more than 2 windings. `%imag` and `%noloadloss` have no home on
    an `AutoTransformerEnd`, so they are untranscribed.
- **LTC** (unequal kV: J1 `SubXfmr`, M1 `M1_XFMR`, one 66/13.8 kV): stays a `PowerTransformer` (DSS-2); the tap
  changer goes on the controlled `PowerTransformerEnd`.
- **Taps** (the RegControl's transformer only; any other tap ≠ 1 still raises):
  - The deck's `taps[winding]` becomes `RatioTapChanger.step` = (tap − 1) / increment, where increment =
    (`MaxTap` − `MinTap`) / `NumTaps` (defaults 1.1, 0.9, 32). A step that is not whole within 1e-6 raises.
  - The range: `highStep` = (`MaxTap` − 1) / increment, `lowStep` = −(1 − `MinTap`) / increment, `neutralStep` 0,
    `stepVoltageIncrement` = increment × 100 (percent), `neutralU` = the winding kV.
  - These sit in the RegControl's rows, because they belong to the tap changer.
- **A regulator by XfmrCode** (the 36 coded RegControls in the sweep) takes the code's values, as the engine copies
  them; the row comment names the code. CIM has no template for an AutoTransformer, so this needs neither U2 nor
  S3b.

The core shape `voltage_regulator.cimtbl` (added in S3a) holds the pattern: VoltageRegulator +
AutoTransformerEnds + mesh + RatioTapChanger + TapChangerControl. The `regulator` shape (PowerTransformer + tap) is
the LTC pattern. Atom: `tests/atoms/regcontrol/regulators.dss` (goldens `regulators_transformer.cimtbl`,
`regulators.cimtbl`), tested by `tests/test_cimtbl_regcontrol.py`.

### RegControl

Mapper: `cimhub_opendss/importer/cimtbl/regcontrol.py` (`map_regcontrol`). Artifact `regcontrol.cimtbl`, after
`transformer.cimtbl`. Atom `tests/atoms/regcontrol/regulators.dss`:
- `reg1`: 1-phase line-to-neutral, LDC (after IEEE13_CDPSM);
- `vr_ll`: 1-phase line-to-line (after IEEE37);
- `gang`: 3-phase gang-operated, PTphase 2;
- `coded`: by XfmrCode, reversible (after IEEE8500);
- `ltc`: a step-down LTC (after M1).

Values: `targetValue`, `targetDeadband`, the reverse ones and `ctRating` are plain floats in cim18v17, so their
headers carry no unit (primary volts, amps).

- `TapChangerControl` `rc_<name>`: `mode=voltage`, `discrete=true`, `Terminal` = `xf_<transformer>_T<winding>`,
  `monitoredPhase` from `PTphase`.
- `RatioTapChanger` `rc_<name>_tap`: `TransformerEnd` = `xf_<transformer>_<winding>`, `ltcFlag=true`,
  `ctRatio` = `CTprim` / 0.2.
- **Secondary to primary** (derived, named functions):
  - targetValue (V) = `vreg` × `ptratio` (Reg1: 122 × 20 = 2440 V); the deadband and the reverse settings
    the same way;
  - line drop (ohm) = `R` × `ptratio` / `CTprim` (Reg1: 3 × 20 / 700 = 0.0857 Ω), and `X` likewise.
- **Defaults** (`dss_default` annotations, filled for RegControl from the EPRI property page in this slice): `vreg`
  120, `band` 3, `ptratio` 60, `CTprim` 300, `delay` 15, `tapdelay` 2, `winding` 1, `revThreshold` 100, `revDelay`
  60.
- **Fail fast:** remote sensing (`bus=`; 1 in the sweep), `tapwinding`, `vlimit`, `TapNum`, `LDC_Z`, any of the
  idle/cogen modes; two RegControls on one transformer; a transformer no New defines.

| Regcontrol field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, RegcontrolName]` | `Reg1`, `Reg2`, `Reg3` | copied | `TapChangerControl.name`, `RatioTapChanger.name`; mRID = rc_ + name (control) and rc_ + name + _tap (tap changer), lowercased |
| `transformer` | `Optional[str]` | `Reg1`, `Reg2`, `Reg3` | structural | the regulator or LTC (DSS-13); a Transformer no New defines, or one two RegControls name, raises |
| `winding` | `Optional[int]` | `2` | structural | RatioTapChanger.TransformerEnd = xf_<transformer>_<winding>; TapChangerControl.Terminal = xf_<transformer>_T<winding>; default 1 |
| `vreg` | `Optional[float]` | `122.0`, `123.0`, `125.0` | derived | targetValue (V) = vreg x ptratio (secondary_to_primary); default 120 |
| `band` | `Optional[float]` | `2.0`, `3.0`, `1.0` | derived | targetDeadband (V) = band x ptratio (secondary_to_primary); default 3 |
| `ptratio` | `Optional[float]` | `20.0`, `60.0`, `63.50852961` | copied | `TapChangerControl.ptRatio`, `RatioTapChanger.ptRatio`; default 60 |
| `CTprim` | `Optional[float]` | `700.0`, `50.0`, `300.0` | copied | `RatioTapChanger.ctRating` (A); default 300; also ctRatio = CTprim / 0.2 (the DSS CT secondary, 0.2 A) and the LDC base |
| `R` | `Optional[float]` | `3.0`, `0.4`, `0.6` | derived | lineDropR (ohm) = R x ptratio / CTprim (line_drop_ohms); default 0; lineDropCompensation = R or X nonzero |
| `X` | `Optional[float]` | `9.0`, `7.5`, `0.4` | derived | lineDropX (ohm) = X x ptratio / CTprim (line_drop_ohms); default 0 |
| `bus` | `Optional[str]` | `temp` | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (remote sensing; 1 RegControl in the sweep, which raises) |
| `delay` | `Optional[float]` | `90.0`, `47.0`, `50.0` | copied | `RatioTapChanger.initialDelay` (s); default 15 |
| `reversible` | `Union[bool, Bool, NoneType]` | `True` | copied | `TapChangerControl.reversible`; default false |
| `revvreg` | `Optional[float]` | `125.0` | derived | reverseTargetValue (V) = revvreg x ptratio (secondary_to_primary); default 120 |
| `revband` | `Optional[float]` | `2.0` | derived | reverseTargetDeadband (V) = revband x ptratio (secondary_to_primary); default 3 |
| `revR` | `Optional[float]` |  | derived | reverseLineDropR (ohm) = revR x ptratio / CTprim (line_drop_ohms); default 0 |
| `revX` | `Optional[float]` |  | derived | reverseLineDropX (ohm) = revX x ptratio / CTprim (line_drop_ohms); default 0 |
| `tapdelay` | `Optional[float]` | `30.0`, `45.0` | copied | `RatioTapChanger.subsequentDelay` (s); default 2 |
| `debugtrace` | `Union[bool, Bool, NoneType]` |  | untranscribed | DSS report flag |
| `maxtapchange` | `Optional[float]` |  | untranscribed | DSS solution control; no home in the network profile parts |
| `inversetime` | `Union[bool, Bool, NoneType]` |  | untranscribed | DSS solution control; no home in the network profile parts |
| `tapwinding` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (a tap winding other than the monitored one) |
| `vlimit` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (home TapChangerControl.maxLimitVoltage) |
| `PTphase` | `Optional[int]` |  | structural | TapChangerControl.monitoredPhase = the phase of the winding's conductor PTphase (default 1); MAX/MIN raise |
| `revThreshold` | `Optional[float]` | `50.0` | copied | `TapChangerControl.reversingPowerThreshold` (kW); default 100 |
| `revDelay` | `Optional[float]` |  | copied | `TapChangerControl.reversingDelay` (s); default 60 |
| `revNeutral` | `Union[bool, Bool, NoneType]` |  | copied | `TapChangerControl.reverseToNeutral`; default false |
| `EventLog` | `Optional[str]` |  | untranscribed | DSS report flag |
| `RemotePTRatio` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `TapNum` | `Optional[int]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (a tap position that overrides the transformer's tap) |
| `Reset` | `Union[bool, Bool, NoneType]` |  | untranscribed | a command, not a setting |
| `LDC_Z` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `rev_Z` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `Cogen` | `Union[bool, Bool, NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `idle` | `Union[bool, Bool, NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `idleReverse` | `Union[bool, Bool, NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `idleForward` | `Union[bool, Bool, NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `basefreq` | `Optional[float]` |  | untranscribed | no home on a control |
| `enabled` | `Union[bool, Bool, NoneType]` | `True` | copied | `TapChangerControl.enabled`, `RatioTapChanger.controlEnabled`; default true |
| `like` | `Optional[str]` | `creg3a`, `creg4a`, `creg1a` | untranscribed | the reader resolves like= before mapping |

### Decisions for S3a (approved 2026-11-08)

- **R1:** line ratings are mapped as above. The season goes on the `OperationalLimitType` when a deck gives one.
- **R2:** `RatioTapChanger.normalStep` is not written. The converter writes `step` (the deck's tap position) only.
- **R3:** S3a/S3b as proposed.
- **R4:** synthesized templates are `ln_<name>_lc` and `ln_<name>_wc`.

## S4 (S4a approved and done 2026-11-08)

S4 maps the injections.

**Result (S4a, 2026-11-08).**
- 25 of the 31 sweep decks bind with every load, capacitor and CapControl; the stops are S3's six (DSS-10 in
  J1, K1, M1, IEEE13_OCHRE; the two balanced IEEE9500 copies).
- Engine checks pass on the atoms and the 8 engine decks: every load's kW, kvar, model, CVR exponents,
  connection and customer count; every capacitor's kvar, kV, connection and steps (states on the atom); every
  CapControl's mode, ON and OFF (rebuilt from target and deadband), ratios, delay, element and terminal. IEEE8500
  and IEEE9500's kvar controls monitor switches (`sw_<name>_T1`).
- Each equipment's BaseVoltage is its bus's (the walk's, as `ConnectivityNode.BaseVoltage` in `bus.cimtbl`).
- Found on the way: `pce/capacitor.yaml` was an orphan copy of `pde/capacitor.yaml` that hid its `dss_default`s
  from the reader; removed.

Census of the 31 sweep decks, 2026-11-08 (throwaway scripts; the counts include the
repeated IEEE8500/IEEE9500 copies):
- **Loads:** 17,447 in 19 decks. Model 1 (ConstantPQ) 14,060; 4 (CVR) 3,184; 5 (ConstantI) 112; 2 (ConstantZ) 86.
  q from `pf` 15,535 (13,356 at 0.97), from `kvar` 3,381; no load sets both. Two ACEP_PSIL loads give `kVA` and `pf`
  without `kW`. 320 K1 loads set `xfkVA` (and `allocationfactor`) besides `kW`. 4 are disabled.
- **Capacitors:** 106 in 11 decks, every one a single step; 78 single-phase, all wye. **CapControls:** 59. 48 are
  kvar (IEEE8500, IEEE9500, M1), 5 voltage (IEEE13_Assets ×2, IEEE13_OCHRE), 3 J1 `volt` and 3 time
  (IEEE13_Assets ×2 + `_geo`).
- **S4b classes:** 950 PVSystems (887 of them 2-phase on a split-phase secondary), 27 Storage, 61 Generators
  (ACEP_PSIL and the IEEE9500 copies; models 1, 3, 7) and 8 Reactors (7 series `HVMV_Sub_HSB` in IEEE8500/IEEE9500,
  and K1's neutral reactor `T2_neutral`, node 4 to node 0 on one bus).

**Scope split (approved, S4-1).** S4a uses only shapes that exist; S4b needs two new ones.
- **S4a:** Load, Capacitor, CapControl (shapes `load`, `shunt`; the core `zip_fractions.cimtbl`, DSS-7).
- **S4b:** PVSystem and Storage (`der`), Generator (new `machine` shape: `SynchronousMachine`), Reactor (new
  `series_compensator` shape), and the full IEEE13_CDPSM artifact directory as the reference golden (D6). Its spec
  section follows S4a, as S3b's followed S3a.

**Findings that change the plan:**
- **U3 is closed.** IEEE13_OCHRE's two voltage controls and IEEE13_Assets' time control monitor their own
  capacitor, so the plan's "all CapControls monitor a line" is wrong. CIM-Tables' `Update` form breaks the reference
  cycle: the compensator row comes first, then the control (naming the compensator's generated `cap_<name>_T1`),
  then `Update LinearShuntCompensator: mRID=cap_<name>, RegulatingControl=cc_<name>`. Checked: this binds, and
  `RegulatingControl.RegulatingCondEq` is the compensator.
- **A 2-phase wye load on a split-phase secondary is two legs to neutral,** not one 240 V load. The engine reads its
  `kV` as line-to-line by the √3 rule: 0.208 = 0.120 × √3. So IEEE13_CDPSM's `House` is phases `s1s2`, wye,
  grounded, with each leg at 120 V. A 240 V load across s1 and s2 would be a 1-phase load on `.1.2`; no deck has one.
- **Every load's kV agrees with its bus** within 1 % (17,447 of 17,447; the nearest misses are 2.4 kV against 4.16/√3, 0.07 %). CIM gives
  a load no rated voltage: `EnergyConsumer.p` is at the BaseVoltage. So `kV` is checked and not written.
- **Engine rules** (pinned with probes; 13 engine decks, every load's kW and kvar equal the engine's):
  - kvar wins over pf in either order;
  - pf alone gives q = kW·tan(acos |pf|) with the sign of pf, and the default pf is 0.88;
  - kVA without kW gives kW = kVA·|pf|;
  - kW, kVA and xfkVA override each other in the order given: `kW=10 pf=0.9 xfkVA=20 allocationfactor=0.5` is
    9 kW, but with kW last it is 10 kW. The reader's record keeps no order.
  - CapControl defaults: type current, ON 300, OFF 200, PTratio 60, CTratio 60, Delay 15; a Capacitor's are
    1200 kvar at 12.47 kV.

**Shared phase rule** (one helper for every S4 mapper): a 1-terminal device's nodes give its phases.
- Nodes 1/2/3 are A/B/C, and s1/s2 on a split-phase island (DSS-5). An omitted node is the DSS default.
- Wye: `phaseConnection=Y`, `grounded=true`. A neutral on node 0, or none, is ground; a neutral on another node
  raises.
- Delta: `D`, `grounded=false`. A 1-phase delta device needs its two nodes: `.3.1` is `AC` (cimtables names its
  phase child C, CIM's delta convention).
- A 3-phase device on a split-phase island raises.

**Artifact order.** `MAPPING_ORDER` grows by load, capacitor and capcontrol, after regcontrol. A control references
a line's or its capacitor's Terminal, so it comes after both.

### Load

Mapper: `cimhub_opendss/importer/cimtbl/load.py` (`map_load`). Artifact `load.cimtbl`; shape `load`. Atom
`tests/atoms/load/loads.dss` (after IEEE13_CDPSM):
- models 1, 2, 4 (two CVR pairs) and 5;
- q from pf, from kvar, and from neither (pf 0.88), plus kVA-only;
- a 1-phase delta on `.3.1`, s1 and s2 legs, a 2-phase `s1s2` load and a disabled load.

**Identity.** `EnergyConsumer` `ld_` + name, lowercased.

**Voltage response (DSS-7).**
- The master imports the fixed `zip_fractions.cimtbl` that core writes: `zip_constant_pq`, `zip_constant_z` and
  `zip_constant_i`, `exponentModel=false`.
- Model 1, 2 or 5 names one of them.
- Model 4 names `exp_<CVRwatts>_<CVRvars>` (`exp_0.8_3`, `exp_1_2`). That is one `LoadResponseCharacteristic` row
  per distinct pair, first in `load.cimtbl`, with `exponentModel=true` and `pVoltageExponent`/`qVoltageExponent`.
  Its constant fractions are unset.
- Models 3, 6, 7 and 8 raise.

**What raises:**
- `kV` more than 1 % off its bus's phase voltage (LL for delta and 2-3 phases, LN for 1-phase wye);
- `kW` with `kVA` or `xfkVA` (K1, which stops earlier on DSS-10);
- `Rneut` ≥ 0;
- the unmapped models.

`enabled=false` gives `normallyInService=false` and the row is written, as for a line. EPRI's ExportCIMXML skips
disabled loads.

### Capacitor

Mapper: `cimhub_opendss/importer/cimtbl/capacitor.py` (`map_capacitor`). Artifact `capacitor.cimtbl`; shape `shunt`.
Atom `tests/atoms/capacitor/caps.dss` (after IEEE13_Assets and IEEE13_OCHRE): a 3-phase and a 1-phase wye bank, a
delta bank, and a bank whose `states=[0]`. The same atom carries the CapControls below.

**Identity.** `LinearShuntCompensator` `cap_` + name, lowercased.

**One section.**
- `nomQ` = kvar (the total over the phases) and `nomU` = kv, as rated. K1's `10548920-1` is 13.8 kV on a 13.2 kV
  bus, and that stays.
- `bPerSection` (S) = nomQ / nomU² (`b_per_section`, through pint). Every CIM consumer reads b.
- `maximumSections=1`. `sections` = `normalSections` = the steps `states` closes (M1's Cap1 and Cap2 are 0), as a
  switch's `normalOpen` follows `open` when nothing else is given.

**What raises:** more than one step; `bus2`; `cmatrix` or `cuf`; a nonzero `R` or `XL` (IEEE4's `Stabilizer`
writes `R=0`, which is untranscribed); `normamps`/`emergamps`.

### CapControl

Mapper: `cimhub_opendss/importer/cimtbl/capcontrol.py` (`map_capcontrol`). Artifact `capcontrol.cimtbl`; shape
`shunt`. Atom: `caps.dss`, with controls of four kinds:
- kvar on a line (after IEEE8500);
- voltage on a line with PTratio 20 and PTPhase 1 (after IEEE13_Assets `Cap2`);
- voltage on its own capacitor (after IEEE13_OCHRE);
- time (after IEEE13_Assets `Cap1`).

**Identity.** `RegulatingControl` `cc_` + name, lowercased. The shape had `<cap>_ctrl`; a DSS control has a name of
its own, and `rc_<name>` is the RegControl precedent (S4-8).

**Rows.**
- `RegulatingControl` with `discrete=true`, `enabled`, `mode`, `monitoredPhase`, `ptRatio`, `ctRatio`,
  `targetValue`, `targetDeadband`.
  - `Terminal` = `ln_<line>_T<terminal>` or `cap_<capacitor>_T<terminal>`. Any other element raises.
  - `monitoredPhase` is the phase of the monitored terminal's conductor `PTPhase` (EPRI's rule).
- Then `Update LinearShuntCompensator: mRID=cap_<capacitor>, RegulatingControl=cc_<name>, aVRDelay (s)=<Delay>,
  controlEnabled=<enabled>`. So the capacitor mapper knows nothing of controls, and the own-terminal cycle is
  broken (U3).

**ON/OFF to target and deadband** (derived, `on_off_target`; EPRI ExportCIMXML's convention, made positive):
- targetValue = (ON + OFF) / 2, targetDeadband = |OFF − ON|. Both are plain floats in cim18v17 (S3a), in primary
  units by mode:
  - voltage: × PTratio, in V;
  - current: × CTratio, in A;
  - kvar: in var, converted through pint;
  - time: hours from midnight.
- The type fixes which side ON is on: below OFF for voltage and time, above it for kvar and current. A control with
  ON on the wrong side raises, so the exporter can invert the pair without a sign (EPRI writes a negative deadband
  for kvar).

| control | ON / OFF | ratio | targetValue | targetDeadband |
|---|---|---|---|---|
| IEEE8500 `CAPBank0A_Ctrl` (kvar) | 200 / −300 kvar | — | −50,000 var | 500,000 var |
| IEEE13_Assets `Cap2` (voltage) | 115 / 125 V | PT 20 | 2,400 V | 200 V |
| IEEE13_OCHRE `CAP1_ctrl` (voltage, own terminal) | 1,950 / 2,500 V | PT 1 | 2,225 V | 550 V |
| IEEE13_Assets `Cap1` (time) | 8 / 19 h | — | 13.5 h | 11 h |

**Untranscribed, with no CIM home:** `VoltOverride`, `Vmax`, `Vmin` (45 IEEE8500/IEEE9500 kvar controls) and
`DelayOFF`, `DeadTime`. `maxAllowedTargetValue` limits the target, not the bus voltage, so it is not a stand-in.
This changes how those controls act when the engine solves (S4-5).

**What raises:** PF and Follow types; `CTPhase`, `VBus`, `UserModel`, `ControlSignal`; PTPhase AVG/MAX/MIN; a
capacitor or element that no `New` defines.

**Schema (DSS-6):**
- `dss_default`s for CapControl and Capacitor (the defaults listed above);
- `OFFsetting`, `Delay`, `DelayOFF` and `DeadTime` ranges → float (they are strings today);
- `type` stays a string read by unique prefix, as the engine reads J1's `volt`.

### Engine checks (S4a)

On the atoms and the engine decks, as in S3:
- every load's kW and kvar (already equal on 13 decks with the rule above) and its model;
- every capacitor's kvar, kV, connection and step count; the states on the atom (a deck that solves when compiled
  switches them);
- every CapControl's mode, ON and OFF (back from target and deadband), PTratio, CTratio, Delay and monitored
  element and terminal.

### Core and shape changes (S4a)

- `cimhub_core`: a `zip_fractions()` document (`zip_constant_pq`, `_z`, `_i`). The `common` shape gains
  `zip_constant_i` from it, and a test keeps the two equal.
- `shunt.cimtbl`: replace the R11 note with the own-terminal form (control, then `Update`). Drop the `(V)` on
  `targetValue`/`targetDeadband` here and in `voltage_regulator.cimtbl` (plain floats, S3a).
- `load.cimtbl`: an `exp_0.8_3` row and a model-4 consumer.
- The `cimtbl-shapes` skill rows to match. `UPSTREAM_REQUESTS.md`: U3 closed.

### Load, Capacitor and CapControl fields

#### Load

| Load field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, LoadName]` | `611`, `634a`, `634b` | copied | `EnergyConsumer.name`; mRID = ld_ + name, lowercased |
| `bus1` | `str` | `611.3`, `634.1`, `634.2` | structural | node; the nodes give the phases: 1/2/3 are A/B/C, and s1/s2 on a split-phase island (DSS-5); an omitted node is the DSS default (conductor k on node k) |
| `phases` | `Optional[int]` | `1`, `3`, `2` | structural | the conductor count; default 3. On a split-phase island 2 wye phases on 1.2 are two legs to neutral (s1s2, kV is LL by the sqrt 3 rule) |
| `kV` | `Optional[float]` | `2.4`, `0.277`, `4.16` | structural | checked, not written: the phase voltage it gives (LL for delta and 2-3 phases, LN for 1-phase wye) must be within 1 % of the bus's, else it raises; CIM p is at the BaseVoltage |
| `kW` | `Optional[float]` | `170.0`, `160.0`, `120.0` | copied | `EnergyConsumer.p` (kW); consumption is positive p |
| `pf` | `Optional[float]` | `0.85`, `0.97`, `0.87` | derived | q (kVAr) = kW x tan(acos abs(pf)) with the sign of pf, when kvar is unset (kvar wins in either order, engine-checked); default 0.88 |
| `model` | `Union[str, ForwardRef('LoadModel'), NoneType]` | `ConstantI`, `ConstantPQ`, `ConstantZ` | mapped | `EnergyConsumer.LoadResponse`; 1 zip_constant_pq, 2 zip_constant_z, 5 zip_constant_i, 4 exp_<CVRwatts>_<CVRvars>; 3, 6, 7, 8 raise; default 1 |
| `yearly` | `Optional[str]` | `Other`, `Commercial`, `AggLoadProfile` | mapped | `ConformLoad.LoadGroup`; the shape's group lg_<shape>: the load is a ConformLoad (S8); a shape the deck does not define raises |
| `daily` | `Optional[str]` | `com` | untranscribed | a second shape has no home: a ConformLoad has one LoadGroup, its yearly shape's (S8) |
| `duty` | `Optional[str]` |  | untranscribed | a second shape has no home: a ConformLoad has one LoadGroup, its yearly shape's (S8) |
| `growth` | `Optional[str]` |  | untranscribed | a GrowthShape reference; not mapped (DSS-11) |
| `conn` | `Union[str, ForwardRef('ConnectionType'), NoneType]` | `wye`, `delta` | mapped | `EnergyConsumer.phaseConnection`, `EnergyConsumer.grounded`; wye -> Y, grounded; delta -> D, not grounded; default wye |
| `kvar` | `Optional[float]` | `80.0`, `110.0`, `90.0` | copied | `EnergyConsumer.q` (kVAr) |
| `Rneut` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (>= 0: a wye neutral impedance) |
| `Xneut` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `status` | `Union[str, ForwardRef('LoadStatus'), NoneType]` | `Variable`, `Fixed` | untranscribed | Fixed/Exempt: whether load multipliers scale it; DSS solution control; no home in the network profile parts |
| `load_class` | `Optional[int]` | `1`, `2` | untranscribed | a DSS report grouping |
| `Vminpu` | `Optional[float]` | `0.88`, `0.85`, `0.75` | untranscribed | below it the engine models the load as constant Z; DSS solution control; no home in the network profile parts |
| `Vmaxpu` | `Optional[float]` | `1.15` | untranscribed | above it the engine models the load as constant Z; DSS solution control; no home in the network profile parts |
| `Vminnorm` | `Optional[float]` |  | untranscribed | an EnergyMeter UE threshold; DSS solution control; no home in the network profile parts |
| `Vminemerg` | `Optional[float]` |  | untranscribed | an EnergyMeter EEN threshold; DSS solution control; no home in the network profile parts |
| `xfkVA` | `Optional[float]` | `1.70148`, `397.465666666668`, `25.1736633333333` | structural | raises: not mapped, and with kW the engine takes whichever comes last (K1 only, behind DSS-10) |
| `allocationfactor` | `Optional[float]` | `1.2136`, `1.2096`, `1.2172` | structural | raises: it scales xfkVA |
| `kVA` | `Optional[float]` | `313.0` | derived | with kW unset: p = kVA x abs(pf), q = kVA x sin(acos abs(pf)) with the sign of pf (ACEP_PSIL); raises with kW: the engine takes whichever of kW, kVA and xfkVA comes last, and the record keeps no order |
| `pct_mean` | `Optional[float]` |  | untranscribed | a Monte Carlo setting; DSS solution control; no home in the network profile parts |
| `pct_stddev` | `Optional[float]` |  | untranscribed | a Monte Carlo setting; DSS solution control; no home in the network profile parts |
| `CVRwatts` | `Optional[float]` | `0.8`, `0.7` | copied | `LoadResponseCharacteristic.pVoltageExponent`; model 4 only (the exp_ row); default 1; unused by other models |
| `CVRvars` | `Optional[float]` | `3.0` | copied | `LoadResponseCharacteristic.qVoltageExponent`; model 4 only (the exp_ row); default 2; unused by other models |
| `kwh` | `Optional[float]` |  | untranscribed | sizes the load only in the AllocateLoads command |
| `kwhdays` | `Optional[float]` |  | untranscribed | sizes the load only in the AllocateLoads command |
| `Cfactor` | `Optional[float]` |  | untranscribed | sizes the load only in the AllocateLoads command |
| `CVRcurve` | `Optional[str]` |  | untranscribed | a LoadShape reference; LoadShape is not mapped (DSS-11) |
| `NumCust` | `Optional[int]` | `1`, `2`, `6` | copied | `EnergyConsumer.customerCount`; default 1 |
| `ZIPV` | `Union[float, list[float], NoneType]` |  | untranscribed | used only by model 8, which raises |
| `pct_SeriesRL` | `Optional[float]` |  | untranscribed | harmonics model; no home in the network profile parts |
| `RelWeight` | `Optional[float]` |  | untranscribed | a reliability weighting |
| `Vlowpu` | `Optional[float]` |  | untranscribed | below it the engine models the load as open; DSS solution control; no home in the network profile parts |
| `puXharm` | `Optional[float]` |  | untranscribed | harmonics model; no home in the network profile parts |
| `XRharm` | `Optional[float]` |  | untranscribed | harmonics model; no home in the network profile parts |
| `spectrum` | `Optional[str]` |  | untranscribed | harmonics model; no home in the network profile parts |
| `basefreq` | `Optional[float]` |  | untranscribed | no home on a load |
| `enabled` | `Union[bool, Bool, NoneType]` | `False` | copied | `EnergyConsumer.normallyInService`; default true |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

#### Capacitor

| Capacitor field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, CapacitorName]` | `Cap1`, `Cap2`, `CAPBank1A` | copied | `LinearShuntCompensator.name`; mRID = cap_ + name, lowercased |
| `bus1` | `Optional[str]` | `675`, `611.3`, `R20185.1` | structural | node and phases, as a load's (1/2/3 are A/B/C) |
| `bus2` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (an ungrounded wye or a series capacitor) |
| `phases` | `Optional[int]` | `3`, `1` | structural | the conductor count; default 3 |
| `kvar` | `Union[float, list[float], NoneType]` | `[600.0]`, `[100.0]`, `[300.0]` | copied | `LinearShuntCompensator.nomQ` (kVAr); the total over the phases; more than one step raises; default 1200 |
| `kv` | `Optional[float]` | `4.16`, `2.4`, `7.2` | copied | `LinearShuntCompensator.nomU` (kV); as rated (LN for 1-phase wye, else LL); also bPerSection (S) = nomQ / nomU^2 (b_per_section); default 12.47 |
| `conn` | `Union[str, ForwardRef('ConnectionType'), NoneType]` | `wye` | mapped | `LinearShuntCompensator.phaseConnection`, `LinearShuntCompensator.grounded`; wye -> Y, grounded; delta -> D, not grounded; default wye |
| `cmatrix` | `Union[float, list[float], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (a capacitance matrix instead of kvar) |
| `cuf` | `Union[float, list[float], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (microfarads instead of kvar) |
| `R` | `Union[float, list[float], NoneType]` | `[0.0]` | structural | 0 is untranscribed; nonzero raises (a series R is not mapped) |
| `XL` | `Union[float, list[float], NoneType]` |  | structural | 0 is untranscribed; nonzero raises (a series reactor is not mapped) |
| `Harm` | `Union[float, list[float], NoneType]` |  | untranscribed | the tuning harmonic of the R/XL filter |
| `Numsteps` | `Optional[int]` |  | structural | maximumSections; more than 1 raises (unequal steps would need a NonlinearShuntCompensator); default 1 |
| `states` | `Union[int, list[int], NoneType]` | `[0]`, `[1]` | structural | sections = normalSections = the steps closed (a switch's normalOpen = open rule); default all closed |
| `normamps` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (an OperationalLimitSet, as a line's) |
| `emergamps` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `faultrate` | `Optional[str]` |  | untranscribed | a reliability setting; no home in the network profile parts |
| `pctperm` | `Optional[float]` |  | untranscribed | a reliability setting; no home in the network profile parts |
| `repair` | `Optional[str]` |  | untranscribed | a reliability setting; no home in the network profile parts |
| `basefreq` | `Optional[float]` |  | untranscribed | no home on a compensator; bPerSection is at the model's frequency |
| `enabled` | `Union[bool, Bool, NoneType]` | `True` | copied | `LinearShuntCompensator.normallyInService`; default true |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

#### CapControl

| Capcontrol field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, CapcontrolName]` | `Cap1`, `Cap2`, `CAPBank1A_Ctrl` | copied | `RegulatingControl.name`; mRID = cc_ + name, lowercased |
| `element` | `Optional[str]` | `capacitor.cap1`, `line.684611`, `line.CAP_1A` | structural | Terminal = ln_<line>_T<n> (sw_ for a switch) or cap_<capacitor>_T<n>; another element class raises |
| `terminal` | `Optional[int]` | `2`, `1` | structural | the element's terminal; default 1 |
| `capacitor` | `Optional[str]` | `cap1`, `cap2`, `CAPBank1A` | structural | the Update row: LinearShuntCompensator cap_<capacitor> gets RegulatingControl; a capacitor no New defines raises |
| `type` | `Optional[str]` | `time`, `voltage`, `kvar` | mapped | `RegulatingControl.mode`; voltage -> voltage, current -> currentFlow, kvar -> reactivePower, time -> timeScheduled (a unique prefix, as the engine reads it: J1's volt); PF and Follow raise; default current |
| `PTratio` | `Optional[float]` | `20.0`, `1.0`, `60.0` | copied | `RegulatingControl.ptRatio`; default 60 |
| `CTratio` | `Optional[float]` | `1.0` | copied | `RegulatingControl.ctRatio`; default 60 |
| `ONsetting` | `Optional[float]` | `8.0`, `115.0`, `150.0` | derived | targetValue = (ON + OFF) / 2 (on_off_target); voltage x PTratio (V), current x CTratio (A), kvar in var, time in hours; ON on the wrong side of OFF for the type raises; default 300 |
| `OFFsetting` | `Optional[float]` | `19.0`, `125.0`, `-225.0` | derived | targetDeadband = abs(OFF - ON) (on_off_target); voltage x PTratio (V), current x CTratio (A), kvar in var, time in hours; default 200 |
| `Delay` | `Optional[float]` | `100.0`, `101.0`, `102.0` | copied | `LinearShuntCompensator.aVRDelay` (s); on the Update row; default 15 |
| `VoltOverride` | `Union[bool, Bool, NoneType]` | `True`, `False` | untranscribed | a voltage override band of a kvar/current control; no home (maxAllowedTargetValue limits the target, not the voltage) |
| `Vmax` | `Optional[float]` | `7740.0`, `126.0` | untranscribed | the VoltOverride band (V on the PT secondary) |
| `Vmin` | `Optional[float]` | `7110.0`, `114.0` | untranscribed | the VoltOverride band (V on the PT secondary) |
| `DelayOFF` | `Optional[float]` | `100.0`, `101.0`, `102.0` | untranscribed | CIM has one aVRDelay (Delay); DSS solution control; no home in the network profile parts |
| `DeadTime` | `Optional[float]` | `0.0` | untranscribed | DSS solution control; no home in the network profile parts |
| `CTPhase` | `Optional[int]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `PTPhase` | `Optional[int]` | `1`, `2` | structural | monitoredPhase = the phase of the monitored terminal's conductor PTPhase (default 1); AVG/MAX/MIN raise |
| `VBus` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (remote voltage sensing) |
| `EventLog` | `Optional[str]` |  | untranscribed | DSS report flag |
| `UserModel` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `UserData` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `pctMinkvar` | `Optional[float]` |  | untranscribed | used only by PF control, which raises |
| `Reset` | `Union[bool, Bool, NoneType]` |  | untranscribed | a command, not a setting |
| `ControlSignal` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `basefreq` | `Optional[float]` |  | untranscribed | no home on a control |
| `enabled` | `Union[bool, Bool, NoneType]` |  | copied | `RegulatingControl.enabled`, `LinearShuntCompensator.controlEnabled`; default true; controlEnabled on the Update row |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

### S4b

The S4b spec is its own section below, [S4b](#s4b-approved-and-done-2026-11-08).

### Decisions for S4 (approved 2026-11-08)

- **S4-1:** split S4a / S4b as above.
- **S4-2:** a load's `kV` is checked against its bus (1 %) and not written; off by more, it raises. The alternative
  is to rescale p and q to the bus voltage by the model's exponent. No deck needs that.
- **S4-3:** `kW` with `kVA` or `xfkVA` raises, because the order decides the value and the record keeps none. `kVA`
  without `kW` is derived (ACEP_PSIL). The alternative is the reader keeping the last of the three; K1 is the only
  user, and it stops on DSS-10 first.
- **S4-4:** CapControl target/deadband by EPRI's midpoint and width, deadband positive, in primary units by mode
  (V, A, var, hours). The side of ON is checked per type.
- **S4-5:** VoltOverride/Vmax/Vmin, DelayOFF and DeadTime untranscribed. A GridAPPS-D extension
  (`RegulatingControl` voltage override limits, an off delay) is the candidate if power-flow parity on IEEE8500 needs
  it.
- **S4-6:** one-step capacitors only. `sections` = `normalSections` from `states`. `bPerSection` is written
  (derived).
- **S4-7:** the CapControl writes the compensator's `RegulatingControl`, `aVRDelay` and `controlEnabled` by
  `Update` (closes U3).
- **S4-8:** `cc_<name>` for a CapControl.
- **S4-9:** disabled loads and capacitors are written with `normallyInService=false`, as lines are.

## S4b (approved and done 2026-11-08)

**Result (2026-11-08).**
- 22 of 31 sweep decks bind, as expected: S3's six stops, the two `ieee9500` copies (`Mode=7`) and
  IEEE123_test_harness (`Battery5`).
- Engine checks pass on the three atoms and the engine decks for every PV (kW, kvar, kVA, Pmpp, kV), every battery
  (kW, state, kVA, kWrated, kWhrated, kWhstored, kV), every series reactor (R, X, buses, ratings) and every
  machine's kW, kvar, ratings and PV-bus settings, including PNNL IEEE9500's `Diesel620` and `LNGengine100`,
  whose kW is edited after their kvar (S4b-8).
- The IEEE13_CDPSM artifact directory is the golden (D6), all 13 files.

**Changes from the proposal, found while building it:**
- **The engine reads a Storage `State` by its first letter.** `charge` is not a prefix of `charging`, but the engine
  takes it, so the mapper matches on the first letter as well.
- **No voltage window in the PV check.** Right after Compile, with no solve, `PVSystems.kW()`/`kvar()` already give
  the dispatch: cut to fit kVA, off below %Cutout, and independent of voltage. The check compares against those.
- **The generator check reads the `kW`/`kvar` properties,** not `Generators.kvar()`. After a solve, the latter is the
  PV bus's solved kvar (SteamGen1: −1000 at Minkvar).
- **`RotatingMachinePhase` comes from the `phases` column.** cimtables writes one per phase for every machine (a 1-phase
  motor's too); the mapper adds nothing.
- **SeriesCompensator has no per-phase class,** so cimtables refuses a `phases` column on it. The mapper writes
  `Update Table Terminal: mRID, phases` for the generated `rx_<name>_T1`/`_T2`. A request for the shorthand (set
  `Terminal.phases` only, as a TransformerEnd's) is U9 in `UPSTREAM_REQUESTS.md`.
- **A balanced three-phase device leaves `phases` blank** (S4b-9, the user's review): cimtables writes a
  `<Class>Phase` child per token, but in CIM, and in the engine's export (`if NPhases = 3 then exit`), per-phase
  children mean a per-phase device. `cimhub_core.cimtbl.phases_cell` blanks `ABC` for loads, capacitors, sources,
  switches, PVs, batteries, machines and series reactors. This also changes the S1, S3 and S4a artifacts. Lines keep
  `phases` (their ACLineSegmentPhases are the conductor order), and the engine writes them for 3-phase lines too. The
  Terminals of a balanced device lose `phases=ABC` until CIM-Tables can tell balanced from three single phases (U10).
- Line's ratings code is now `line.rating_rows`/`rating_tables`, shared with the reactor. `line_phases` takes a
  `label` for its errors.
- Wrong schema ranges fixed in passing: the curve references (`EffCurve`, `P-TCurve`) → string, and the
  `WattPriority`/`PFPriority`/`LimitCurrent` switches → boolean, so `yes` reads as true.

**S4b-8: the deck's assignment order is replayed (approved 2026-11-08).** For some properties the engine's value
depends on the order of assignment, and a record keeps only each slot's last value. The engine rules, pinned with
probes:
- **Generator:** the engine keeps kvar as a power factor. Assigning kvar sets pf = kW / √(kW² + kvar²), with kvar's
  sign, at the kW of that moment; assigning kW or pf recomputes kvar = kW·tan(acos |pf|). A pf of 0 (kvar at kW 0)
  leaves kvar as assigned. So `kW=620 kvar=30` then `kW=0` is 0 kvar (IEEE9500's `Diesel620`), `kvar=30 kW=100` is 3
  (the pf came from the default kW of 1000), and `kW=100 kvar=30` then `kW=50` is 15. A bare New is kW 1000, pf 0.88,
  kvar 60.
- **PVSystem:** pf and kvar: the last assigned wins; kvar stays absolute.
- **Storage:** the engine keeps a discharge and a charge setpoint. A kW > 0 sets the first and discharges, a kW < 0
  the second and charges, 0 idles; `State` picks which runs (`kW=40`, `State=idling`, `State=discharging` discharges
  at 40); `%Discharge`/`%Charge` put the setpoint back to the rating's share. `kWhstored` and `%stored`: the last
  wins.
- **The engine checks a battery's stored energy when its state is assigned,** with the energy of that moment: a
  `%stored` assigned after `State=discharging` does not wake a battery that idled at its reserve. No deck in the sweep
  assigns the energy after the state, so that order raises.

How: `DssReader.read_all()` returns a `DssModel`, a `GraphModel` that also keeps each record's assignment history:
every `(slot, value)` in deck order, from `New`, edits, `BatchEdit`, and the slots `like=` copies (first).
`DssModel.assignments(record)` and `last_of(record, *slots)` read it, and the mappers replay it
(`generator.dispatched_kvar`, `storage.battery_dispatch`, PVSystem's `last_of(pf, kvar)`). Only the history replaces
order guesses; the records stay verbatim.

Not replayed: a Load's kW/kVA/xfkVA (S4-3 stays). kVA last takes the pf that kvar implied (`kW=10 kvar=3` then
`kVA=20` is 19.2 kW), which needs its own replay, and only K1 reaches it, after DSS-10.

S4b maps the rest of the injections and the series reactor: PVSystem and Storage (shape `der`), Generator (new
shape `synchronous_machine`) and Reactor (new shape `series_compensator`). Its exit is the full IEEE13_CDPSM artifact
directory as the reference golden (D6). The two new shape names are the ones RAW's plan requests from core (its C2),
so the two waves share them. RAW adds its bus-branch variants and `GeneratingUnit` later.

Census of the 31 sweep decks, 2026-11-08 (30 read; the balanced ieee9500_2025 copy stops in the reader, as in S3):
- **PVSystem:** 950 in 7 decks. 887 are 2-phase on a split-phase secondary: 356 at kV 0.208 (the IEEE9500 copies)
  and 531 at 0.24 (ieee9500_2025). 45 are 1-phase and 13 are 3-phase.
  - `pf` is always 1.0, and no PV sets `kvar`.
  - `irradiance` is 1.0 or 0.8 (IEEE13_CDPSM). Only ieee9500 sets `%Cutin`/`%Cutout`, at 0.1.
  - 3 PVs are delta (IEEE9500's `M1047PV-3`, 3-phase).
  - IEEE9500's `PVFarm1` has Pmpp 1200 on kVA 1000, so the inverter caps it.
- **Storage:** 27 in 5 decks.
  - States: 22 `charge`/`charging`, 3 `discharging` and 2 `idling`. `pf` is 1.0 wherever it is set, and no record
    sets `kvar`.
  - 21 set `kW`, always after `state=` (IEEE9500: `state=charge kW=150`; IEEE123: `state=charge kW=-0.0`).
  - 6 are delta. No record sets both `kWhstored` and `%stored`.
- **Generator:** 61 in 3 decks (ACEP_PSIL and the IEEE9500 copies), all 3-phase.
  - Models: 41 ConstantPQ, 15 CurrentLimited (7) and 5 ConstantPV (3). 18 are delta.
  - Every record sets `kVA`. `Xdp`/`Xdpp`/`H` are on 45. `Maxkvar`/`Minkvar` are never set.
  - One IEEE9500 machine sets both `pf=0.98` and `kvar=0` at `kW=0`.
- **Reactor:** 8.
  - 7 are IEEE8500/IEEE9500's `HVMV_Sub_HSB`: series, 3-phase, X 14.798 Ω, R 0, normamps = emergamps = 400.
  - 1 is K1's `T2_neutral`, `K_LSB.4` to `K_LSB.0` on one bus.

**Engine rules** (pinned with probes in `/tmp`; the defaults are the engine's readback of a bare `New`):
- **PVSystem.**
  - The panel's power is Pmpp × irradiance, and `%Pmpp` caps it: the available power is min(Pmpp × irradiance,
    Pmpp × %Pmpp / 100). Probed 2026-11-10: Pmpp 100 at irradiance 0.5 gives 50 at %Pmpp 60 and 150, and 10 at
    %Pmpp 10; at irradiance 1.2 it gives 120 at %Pmpp 150. q comes from `pf` (q = P·tan(acos |pf|), with pf's sign)
    or from `kvar`.
  - Over kVA, P is cut to √(kVA² − q²) (var priority, the default), so Pmpp 1200 on kVA 1000 gives 1000.
  - The PV is off (P = 0) when the panel's power, before the %Pmpp cap, is below `%Cutout` × kVA / 100
    (irradiance 0.5 on Pmpp 100 and kVA 100 runs at %Pmpp 10, giving 10 under a 20 % cut-out). The initial state uses
    `%Cutout`, not `%Cutin`: 25 % with cut-in 30 / cut-out 5 runs, and with cut-in 5 / cut-out 30 it is off.
  - **`pf` and `kvar` override each other in the order given** (unlike a load, where kvar always wins).
  - Defaults: 3 phases, kV 12.47, irradiance 1, Pmpp 500, %Pmpp 100, pf 1, kVA 500, %Cutin and %Cutout 20,
    Vminpu 0.9, wye. kvarMax and kvarMaxAbs default to kVA.
- **Storage.**
  - `State` and `kW` override each other in the order given. A `kW` > 0 discharges, < 0 charges, and 0 (or −0.0)
    idles.
  - So IEEE9500's `state=charge kW=150` discharges at 150 kW, and IEEE123's `state=charge kW=-0.0` idles.
  - With no `kW`: charging draws kWrated × %Charge / 100, discharging gives kWrated × %Discharge / 100, and
    idling draws %IdlingkW × kWrated / 100 (1 kW on 100). Every |P| is capped at kVA.
  - The battery idles instead when it is told to charge while full, or to discharge at or below `%reserve`.
  - `kWhstored` and `%stored` override each other in order.
  - With pf ≠ 1, the engine caps q at a kvarMax left over from the default kVA (pf 0.9 on 100 kW gives 25 kvar).
  - Defaults: kV 12.47, kWrated 25, kVA = kWrated, kWhrated 50, %stored 100, %reserve 20, State idling,
    %Charge/%Discharge 100, %EffCharge/%EffDischarge 90, %IdlingkW 1, pf 1, wye.
- **Generator.**
  - q comes from `pf` or `kvar`, and the two override each other in order.
  - Defaults: kW 1000, pf 0.88, kV 12.47, model 1, Vpu 1, kVA 1.2 × kW, Maxkvar = 2 × kvar, Minkvar = −Maxkvar.
  - Model 3 regulates its terminal to Vpu within Maxkvar/Minkvar. Model 7 dispatches as model 1.
- **2-phase PV at 0.24 kV on 120 V legs** (ieee9500_2025): the engine's base is 0.24/√3 = 138.6 V. The legs sit at
  0.866 pu, below Vminpu, so it gives 92.8 % of Pmpp. At 0.208 kV it gives 100 %. This is a power-flow result, not a
  setting; the mapping keeps the deck's kV (S4b-4).
- **The engine's CIM export disagrees with itself on sign.** `ExportCIMXML.pas` writes `PowerElectronicsConnection.p`
  = −kW but `RotatingMachine.p` = +kW. cim18v17 documents both as the load sign, so S4b writes −kW for both (S4b-1).

**Expected sweep:** 22 of 31 decks bind. Besides S3's six, three stop:
- CIMHub_2_0's two `ieee9500` copies: `PVFarm1 ... Mode=7` reads as `model=7`, which the engine rejects too
  (`"7" is not a valid value`), so those decks do not compile.
- IEEE123_test_harness: `Battery5` is `phases=1` on `108.1.2.3`, which puts its neutral on node 2. The shared phase
  rule raises (S4b-6).

### Shared rules (S4b)

- **Terminal:** the S4 shared phase rule (`injection.device_terminal`) for PVSystem, Storage and Generator.
- **`ratedU` is line to line** (S4b-4): the deck's kV, × √3 for a 1-phase wye device; the exporter inverts it. This
  matches the engine's CIM export, which is where GridAPPS-D's files come from. CIMHub_2_0 wrote kV unchanged; the
  tier-3 comparison lists that difference. ratedU is not checked against the bus: a 240 V inverter on 120 V legs
  stays 240 V.
- **Sign:** p and q are the load sign: generation and discharge are negative, q = −kvar (S4b-1).
- **pf with kvar:** the deck's assignment order decides, as in the engine (S4b-8, which replaced S4b-2's raise).
- **Inverter cap** (PVSystem and Storage): `inverter_power(available, q, kva)`, the engine's var-priority cut.
- `enabled=false` gives `normallyInService=false` (S4-9).

### PVSystem

Mapper `importer/cimtbl/pvsystem.py` (`map_pvsystem`). Artifact `pvsystem.cimtbl`; shape `der`. Atom
`tests/atoms/der/der.dss`:
- the IEEE13_CDPSM PVs: 3-phase at irradiance 0.8, and 2-phase `s1s2` at 0.208;
- a 1-phase leg, a delta PV, a kVA-capped PV, one below cut-out, one with a negative pf, one with kvar, and one
  capped at %Pmpp (irradiance 0.9 at %Pmpp 60 gives 6 kW).

**Identity.** `PowerElectronicsConnection` `pv_` + name and `PhotoVoltaicUnit` `pv_<name>_unit`, lowercased. The
prefix keeps IEEE13_CDPSM's `PVSystem.School` and `Storage.School` apart.

**Rows.**
- **Connection:**
  - `node`, `phases`, `phaseConnection` (cim18v17's PowerElectronicsConnection has no `grounded`);
  - `ratedS` = kVA, `ratedU` (S4b-4);
  - `p` = −P and `q` = −q, by the rules above (derived, `pv_power`);
  - `maxQ` = kvarMax, `minQ` = −kvarMaxAbs, `maxIFault` = 1 / Vminpu (the engine's export convention);
  - `normallyInService`, `BaseVoltage`, `EquipmentContainer`.
- **Unit:** `maxP` = Pmpp, `minP` = 0, `irradiance` = irradiance (kW/m2; the gridappsd extension), and its
  connection.

**What raises:**
- `model` other than 1;
- `EffCurve` or `P-TCurve` (both change the snapshot power);
- `WattPriority` or `PFPriority` set to yes; a nonzero `%PminNoVars` or `%PminkvarMax`;
- `UserModel`/`UserData`; `ControlMode=GFM`; `Balanced` or `LimitCurrent` set to yes.

**Untranscribed:**
- the Yearly/Daily/Duty and T-curves, which are time series that a snapshot does not use;
- `%Cutin`, which only acts after the inverter turns off;
- `%R`, `%X`, `kVDC`, `Kp`, `PITol`, `SafeVoltage`, `SafeMode`, `DynamicEq`, `DynOut`, `AmpLimit`, `AmpLimitGain`
  (dynamics);
- `Vmaxpu`, `Temperature` (it acts only through a P-TCurve), `VarFollowInverter` (InvControl), `class`, `spectrum`,
  `basefreq`, `DutyStart`, `DebugTrace`.

### Storage

Mapper `importer/cimtbl/storage.py` (`map_storage`). Artifact `storage.cimtbl`; shape `der`. Atom
`tests/atoms/der/der.dss`:
- the three IEEE13_CDPSM batteries (charging, discharging, idling);
- `state=charge kW=150` (IEEE9500) and `state=charge kW=-0.0` (IEEE123);
- a kVA-capped battery, one with `%stored`, and a delta battery.

**Identity.** `PowerElectronicsConnection` `storage_` + name, and `BatteryUnit` `storage_<name>_unit`.

**Rows.**
- **Connection:** as a PV's, with `ratedS` = kVA (default kWrated). q = 0.
- **Unit:**
  - `ratedE` = kWhrated;
  - `storedE` = kWhstored, else %stored × kWhrated / 100;
  - `minimumE` = %reserve × kWhrated / 100;
  - `maxP` = kWrated, `minP` = −kWrated;
  - `chargingEfficiency` = %EffCharge and `dischargingEfficiency` = %EffDischarge (percent);
  - `idlingP` = %IdlingkW × kWrated / 100.
- **State and p** (derived, `battery_dispatch`; S4b-8): the deck's kW, State, %Discharge and %Charge assignments
  replayed in order (above). Discharging p = −min(setpoint, kVA), charging p = min(setpoint, kVA), idling `waiting`
  with p = idlingP. A setpoint is the last kW of its sign, else kWrated × %Discharge (or %Charge) / 100.
  - The row comment names an override, for example "kW=150 after State=charging: discharging".

**What raises:**
- a battery that the engine would idle instead: charging when full, or discharging at or below `%reserve`;
- `kWhstored`, `%stored`, `kWhrated` or `%reserve` assigned after the last State or kW (above);
- pf ≠ 1 or kvar ≠ 0 (because of the engine's kvarMax quirk above; no deck has one);
- `DispMode` other than default;
- `model` other than 1;
- `EffCurve`, `UserModel`/`UserData`, `DynaDLL`/`DynaData`;
- `WattPriority`/`PFPriority` set to yes, a nonzero `%PminNoVars`/`%PminkvarMax`, `Balanced`/`LimitCurrent` set to yes.

**Untranscribed:** the curves, `DischargeTrigger`/`ChargeTrigger`/`TimeChargeTrig` (dispatch modes, which raise),
`%Idlingkvar` (deprecated), `%CutIn`/`%CutOut`, `%kWRated`, `Vmaxpu`, and the dynamics slots, as for PVSystem.

### Generator

Mapper `importer/cimtbl/generator.py` (`map_generator`). Artifact `generator.cimtbl`; shape `synchronous_machine`.
Atom `tests/atoms/generator/gens.dss`:
- models 1, 3 and 7; wye and delta;
- q from pf, from kvar, and from the default 0.88;
- `kW=0 pf=0.98 kvar=0`; and a 1-phase machine.

**Identity.** `SynchronousMachine` `gen_` + name. A model 3 control is `gen_<name>_ctrl`: the machine has no
control of its own name, as the shape's `<cap>_ctrl` had.

**Rows.**
- `node`, `phases`;
- `ratedS` = kVA (default 1.2 × kW), `ratedU` (S4b-4);
- `p` = −kW, `q` = −q;
- `type=generator`, `operatingMode=generator`;
- `earthing` = not delta (S4b-5);
- `normallyInService`, `BaseVoltage`, `EquipmentContainer`.

**Model 3 (PV bus):**
- `maxQ` = Maxkvar and `minQ` = Minkvar (default ±2 × kvar);
- a `RegulatingControl` `gen_<name>_ctrl`:
  - `mode=voltage`, `discrete=false`, `enabled=true`;
  - `targetValue` = Vpu × ratedU (V), `targetDeadband=0`;
  - `Terminal=gen_<name>_T1`;
- then `Update SynchronousMachine: mRID, RegulatingControl, controlEnabled=true`. This is S4a's own-terminal form
  (U3).

Model 7 maps as model 1, with a row note: below Vminpu it limits current, which is power-flow behaviour.

**What raises:**
- models 2, 4, 5 and 6; `UserModel`/`ShaftModel`;
- `Maxkvar`/`Minkvar` on a model other than 3.

**Untranscribed:**
- `Xd`, `Xdp`, `Xdpp`, `H`, `D`, `XRdp` (dynamics);
- `Vminpu`, `Vmaxpu`, `PVFactor` (a solver aid), `Status`, `DispMode`, `DispValue`, `ForceOn`;
- the curves, the fuel slots, `class`, `spectrum`, `basefreq`.

### Reactor

Mapper `importer/cimtbl/reactor.py` (`map_reactor`). Artifact `reactor.cimtbl`; shape `series_compensator`. Atom
`tests/atoms/reactor/reactors.dss`: IEEE8500's `HVMV_Sub_HSB` and a 1-phase series reactor with R.

**Identity.** `SeriesCompensator` `rx_` + name.

**Rows.**
- `node1`, `node2`, `phases` (the line rule, `line_phases`);
- `r` = R and `x` = X (Ω per phase); `r0` = R and `x0` = X, as in the engine's export (no mutual coupling);
- `normallyInService`, `BaseVoltage` (bus1's), `EquipmentContainer`;
- `rx_<name>_limits`, an `OperationalLimitSet` with `CurrentLimit`s `_norm`/`_emerg`. These come from the deck's own
  normamps/emergamps only (nothing from the engine's kvar-derived defaults), as for a line. Line's ratings code is
  shared.

**What raises:**
- no `bus2`, or `bus2` on the same bus: a shunt or neutral reactor, such as K1's `T2_neutral` (K1 stops on DSS-10
  first);
- X unset, or `kvar` given (X derived from kvar and kV);
- `Rmatrix`/`Xmatrix`, `Z`/`Z1`/`Z2`/`Z0`, `LmH`, `Rp`, `Parallel=yes`, `RCurve`/`LCurve`.

**Untranscribed:** `kV` (it acts only with kvar), `conn` (a series reactor has no neutral), `faultrate`/`pctperm`/
`repair`, `basefreq`.

### Artifact order, schema, shapes (S4b)

- **Order:** `MAPPING_ORDER` gains reactor after line (it is a branch, and its limits use the common limit types),
  then pvsystem, storage and generator after capcontrol.
- **Schema (DSS-6).** The `dss_default`s of the four classes become the engine readback above. This fixes PVSystem's
  `pf` 0.88 → 1, its `Vminpu` 0 → 0.9, and Generator's `Xdp` 0.27 → 0.28. The derived defaults (kvarMax, Storage
  kVA, Generator kVA and Maxkvar) stay in the mapper, named.
- **Core shapes:**
  - `der.cimtbl`: gains `phaseConnection`, `maxQ`/`minQ`/`maxIFault`, a 2-phase `s1s2` PV, and the battery's
    `minimumE`, efficiencies, `idlingP` and `maxP`/`minP`.
  - New `synchronous_machine.cimtbl`: a model 1 machine, and a PV-bus machine with its `RegulatingControl` and the
    `Update`.
  - New `series_compensator.cimtbl`: a reactor between two nodes, with its limit set.
  - The `cimtbl-shapes` skill rows to match.

### Engine checks (S4b)

On the atoms and the engine decks:
- **PVSystem:** kVA, kV, Pmpp; p and q against the engine's dispatch (`PVSystems.kW()`/`kvar()` after Compile);
- **Storage:** kWrated, kVA, kWhrated, kWhstored, the state, and the kW/kvar properties;
- **Generator:** the kW and kvar properties, kVA, kV, delta, and model/Vpu/Maxkvar/Minkvar for model 3;
- **Reactor:** R, X, both buses, normamps and emergamps.

### IEEE13_CDPSM golden directory (D6)

`tests/goldens/IEEE13_CDPSM/` holds every part `to_cimtbl` writes (master, bus, zip_fractions, each class's
document), not only the master and `bus`. The orchestrator test compares the whole directory, and
`CIMHUB_UPDATE_GOLDENS=1` rewrites it.

### PVSystem, Storage, Generator and Reactor fields

Generated from each mapper's `FIELDS` (samples: the 31 sweep decks).

| Pvsystem field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, PvsystemName]` | `House`, `School`, `PVFarm1` | copied | `PowerElectronicsConnection.name`; mRID = pv_ + name, lowercased; the unit is <mRID>_unit |
| `phases` | `Optional[int]` | `2`, `3`, `1` | structural | the conductor count; default 3 |
| `bus1` | `Optional[str]` | `House.1.2`, `634`, `M1047PV-3` | structural | node and phases, by the S4 shared phase rule |
| `kv` | `Optional[float]` | `0.208`, `0.48`, `12.47` | derived | ratedU (kV, LL) = kv, x sqrt 3 for 1-phase wye (S4b-4); not checked against the bus; default 12.47 |
| `irradiance` | `Optional[float]` | `0.8`, `1.0` | copied | `PhotoVoltaicUnit.irradiance` (kW/m2), the gridappsd extension; also p (pv_power); default 1 |
| `Pmpp` | `Optional[float]` | `5.0`, `300.0`, `1000.0` | copied | `PhotoVoltaicUnit.maxP` (kW); also p (pv_power); default 500 |
| `pct_Pmpp` | `Optional[float]` |  | derived | p is capped at Pmpp x %Pmpp / 100 (pv_power); default 100 |
| `Temperature` | `Optional[float]` |  | untranscribed | acts only through a P-TCurve, which raises |
| `pf` | `Optional[float]` | `1.0` | derived | q = -kW x tan(acos abs(pf)) with the sign of pf, unless kvar was assigned after it (the last of the two wins, S4b-8); default 1 |
| `conn` | `Optional[str]` | `wye`, `delta` | mapped | `PowerElectronicsConnection.phaseConnection`; wye -> Y, delta -> D; default wye |
| `kvar` | `Optional[float]` |  | derived | q (kVAr) = -kvar (the load sign), unless pf was assigned after it |
| `kVA` | `Optional[float]` | `5.0`, `300.0`, `1500.0` | copied | `PowerElectronicsConnection.ratedS` (kVA); also caps p (var priority); default 500 |
| `pct_Cutin` | `Optional[float]` | `0.1` | untranscribed | acts only after the inverter turns off; the snapshot state uses %Cutout |
| `pct_Cutout` | `Optional[float]` | `0.1` | derived | p = q = 0 when Pmpp x irradiance is below %Cutout of kVA; default 20 |
| `EffCurve` | `Optional[str]` |  | structural | raises: an efficiency curve changes the snapshot power |
| `P_TCurve` | `Optional[str]` |  | structural | raises: a temperature curve changes the snapshot power |
| `pct_R` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `pct_X` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `model` | `Optional[int]` | `7`, `1` | structural | 1 (constant P, PF) only; any other raises (ieee9500's Mode=7 is model=7, which the engine rejects too); default 1 |
| `Vminpu` | `Optional[float]` |  | derived | maxIFault = 1 / Vminpu (the engine's CIM export); default 0.9 |
| `Vmaxpu` | `Optional[float]` |  | untranscribed | above it the engine models the PV as constant Z; a power-flow setting |
| `Balanced` | `Union[bool, Bool, NoneType]` |  | structural | raises when yes: raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `LimitCurrent` | `Union[bool, Bool, NoneType]` |  | structural | raises when yes: raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `yearly` | `Optional[str]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `daily` | `Optional[str]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `duty` | `Optional[int]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `Tyearly` | `Optional[str]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `Tdaily` | `Optional[str]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `Tduty` | `Optional[int]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `class_class` | `Optional[int]` |  | untranscribed | a DSS report grouping |
| `UserModel` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `UserData` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `debugtrace` | `Union[bool, Bool, NoneType]` |  | untranscribed | a DSS debugging switch |
| `VarFollowInverter` | `Union[bool, Bool, NoneType]` |  | untranscribed | acts only with an InvControl |
| `DutyStart` | `Optional[str]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `WattPriority` | `Union[bool, Bool, NoneType]` |  | structural | raises when yes: raises when set: no deck in the sweep sets it, so a mapping waits for one (var priority is mapped) |
| `PFPriority` | `Union[bool, Bool, NoneType]` |  | structural | raises when yes: raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `pct_PminNoVars` | `Optional[float]` |  | structural | raises when nonzero: raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `pct_PminkvarMax` | `Optional[float]` |  | structural | raises when nonzero: raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `kvarMax` | `Optional[float]` |  | copied | `PowerElectronicsConnection.maxQ` (kVAr); default kVA |
| `kvarMaxAbs` | `Optional[float]` |  | derived | minQ (kVAr) = -kvarMaxAbs; default kVA |
| `kVDC` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `Kp` | `Optional[str]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `PITol` | `Optional[str]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `SafeVoltage` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `SafeMode` | `Optional[str]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `DynamicEq` | `Optional[str]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `DynOut` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `ControlMode` | `Optional[str]` |  | structural | GFL only; GFM raises (raises when set: no deck in the sweep sets it, so a mapping waits for one) |
| `AmpLimit` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `AmpLimitGain` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `spectrum` | `Optional[float]` |  | untranscribed | harmonics model; no home in the network profile parts |
| `basefreq` | `Optional[float]` |  | untranscribed | no home on an inverter |
| `enabled` | `Union[bool, Bool, NoneType]` |  | copied | `PowerElectronicsConnection.normallyInService`; default true |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

| Storage field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, StorageName]` | `BatIdle`, `House`, `School` | copied | `PowerElectronicsConnection.name`; mRID = storage_ + name, lowercased; the unit is <mRID>_unit |
| `phases` | `Optional[int]` | `3`, `2`, `1` | structural | the conductor count; default 3 |
| `bus1` | `Optional[str]` | `634`, `House.1.2`, `m2001-ESS1` | structural | node and phases, by the S4 shared phase rule |
| `kv` | `Optional[float]` | `0.48`, `0.208`, `2.4` | derived | ratedU (kV, LL) = kv, x sqrt 3 for 1-phase wye (S4b-4); default 12.47 |
| `conn` | `Optional[str]` | `wye`, `delta` | mapped | `PowerElectronicsConnection.phaseConnection`; wye -> Y, delta -> D; default wye |
| `kW` | `Optional[float]` | `150.0`, `-0.0`, `0.0` | derived | replayed in deck order (battery_dispatch, S4b-8): > 0 sets the discharge setpoint and discharging, < 0 the charge setpoint and charging, 0 waiting; capped at kVA |
| `kvar` | `Optional[float]` |  | structural | raises when nonzero: raises when set: no deck in the sweep sets it, so a mapping waits for one (q = 0) |
| `pf` | `Optional[float]` | `1.0` | structural | 1 only; another raises (the engine caps q by a kvarMax left from the default kVA); default 1 |
| `kVA` | `Optional[float]` | `250.0`, `125.0`, `200.0` | copied | `PowerElectronicsConnection.ratedS` (kVA); also caps p; default kWrated |
| `pct_Cutin` | `Optional[float]` |  | untranscribed | an inverter cut-in; 0 by default for storage |
| `pct_Cutout` | `Optional[float]` |  | untranscribed | an inverter cut-out; 0 by default for storage |
| `EffCurve` | `Optional[str]` |  | structural | raises: an efficiency curve changes the snapshot power |
| `VarFollowInverter` | `Union[bool, Bool, NoneType]` |  | untranscribed | acts only with an InvControl |
| `kvarMax` | `Optional[float]` |  | copied | `PowerElectronicsConnection.maxQ` (kVAr); default kVA |
| `kvarMaxAbs` | `Optional[float]` |  | derived | minQ (kVAr) = -kvarMaxAbs; default kVA |
| `WattPriority` | `Union[bool, Bool, NoneType]` |  | structural | raises when yes: raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `PFPriority` | `Union[bool, Bool, NoneType]` |  | structural | raises when yes: raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `pct_PminNoVars` | `Optional[float]` |  | structural | raises when nonzero: raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `pct_PminkvarMax` | `Optional[float]` |  | structural | raises when nonzero: raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `kWrated` | `Optional[float]` | `100.0`, `5.0`, `250.0` | copied | `BatteryUnit.maxP` (kW); minP = -kWrated; also p by State; default 25 |
| `pct_kWrated` | `Optional[float]` |  | untranscribed | the kW limit of the dispatch modes, which raise |
| `kWhrated` | `Optional[float]` | `200.0`, `13.5`, `500.0` | copied | `BatteryUnit.ratedE` (kWh); default 50 |
| `kWhstored` | `Optional[float]` | `100.0`, `5.0`, `135.0` | copied | `BatteryUnit.storedE` (kWh); unless %stored was assigned after it (the last wins) |
| `pct_stored` | `Optional[float]` | `60.0`, `40.0`, `35.0` | derived | storedE (kWh) = %stored x kWhrated / 100 unless kWhstored was assigned after it; default 100 |
| `pct_reserve` | `Optional[float]` | `30.0` | derived | minimumE (kWh) = %reserve x kWhrated / 100; default 20 |
| `State` | `Optional[str]` | `idling`, `charging`, `discharging` | mapped | `BatteryUnit.batteryState`; charging, discharging, idling -> waiting (by the first letter, as the engine reads it: the decks' charge); picks the setpoint that runs, replayed with kW (S4b-8); default idling |
| `pct_Discharge` | `Optional[float]` |  | derived | the discharge setpoint kWrated x %Discharge / 100 until a kW > 0 sets it; default 100 |
| `pct_Charge` | `Optional[float]` |  | derived | the charge setpoint kWrated x %Charge / 100 until a kW < 0 sets it; default 100 |
| `pct_EffCharge` | `Optional[float]` |  | copied | `BatteryUnit.chargingEfficiency` (percent); default 90 |
| `pct_EffDischarge` | `Optional[float]` |  | copied | `BatteryUnit.dischargingEfficiency` (percent); default 90 |
| `pct_IdlingkW` | `Optional[float]` |  | derived | idlingP (kW) = %IdlingkW x kWrated / 100, also p when waiting; default 1 |
| `pct_Idlingkvar` | `Optional[float]` |  | untranscribed | deprecated in the engine |
| `pct_R` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `pct_X` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `model` | `Optional[int]` |  | structural | 1 (constant P, PF) only; any other raises; default 1 |
| `Vminpu` | `Optional[float]` |  | derived | maxIFault = 1 / Vminpu (the engine's CIM export); default 0.9 |
| `Vmaxpu` | `Optional[float]` |  | untranscribed | above it the engine models the battery as constant Z; a power-flow setting |
| `Balanced` | `Union[bool, Bool, NoneType]` |  | structural | raises when yes: raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `LimitCurrent` | `Union[bool, Bool, NoneType]` |  | structural | raises when yes: raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `yearly` | `Optional[str]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `daily` | `Optional[str]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `duty` | `Optional[int]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `DispMode` | `Optional[str]` |  | structural | default only; another dispatch mode raises (raises when set: no deck in the sweep sets it, so a mapping waits for one) |
| `DischargeTrigger` | `Optional[str]` |  | untranscribed | acts only in a dispatch mode, which raises |
| `ChargeTrigger` | `Optional[str]` |  | untranscribed | acts only in a dispatch mode, which raises |
| `TimeChargeTrig` | `Optional[str]` |  | untranscribed | acts only in a dispatch mode, which raises |
| `class_class` | `Optional[int]` |  | untranscribed | a DSS report grouping |
| `DynaDLL` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `DynaData` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `UserModel` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `UserData` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `debugtrace` | `Union[bool, Bool, NoneType]` |  | untranscribed | a DSS debugging switch |
| `kVDC` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `Kp` | `Optional[str]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `PITol` | `Optional[str]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `SafeVoltage` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `SafeMode` | `Optional[str]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `DynamicEq` | `Optional[str]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `DynOut` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `ControlMode` | `Optional[str]` |  | structural | GFL only; GFM raises (raises when set: no deck in the sweep sets it, so a mapping waits for one) |
| `AmpLimit` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `AmpLimitGain` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `spectrum` | `Optional[float]` |  | untranscribed | harmonics model; no home in the network profile parts |
| `basefreq` | `Optional[float]` |  | untranscribed | no home on an inverter |
| `enabled` | `Union[bool, Bool, NoneType]` |  | copied | `PowerElectronicsConnection.normallyInService`; default true |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

| Generator field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, GeneratorName]` | `Diesel590`, `Diesel620`, `LNGengine100` | copied | `SynchronousMachine.name`; mRID = gen_ + name, lowercased |
| `phases` | `Optional[int]` |  | structural | the conductor count; default 3 |
| `bus1` | `Optional[str]` | `m1089-DIES1`, `m1209-DIES1`, `M1142-LNG1` | structural | node and phases, by the S4 shared phase rule |
| `kv` | `Optional[float]` | `0.48`, `12.47` | derived | ratedU (kV, LL) = kv, x sqrt 3 for 1-phase wye (S4b-4); default 12.47 |
| `kW` | `Optional[float]` | `0.0`, `50.0`, `100.0` | derived | p (kW) = -kW (the load sign); default 1000 |
| `pf` | `Optional[float]` | `0.95`, `0.98` | derived | q (kVAr) = -kvar, kvar replayed from the kW, pf and kvar assignments in deck order (dispatched_kvar, S4b-8): each kW or pf recomputes kvar = kW x tan(acos abs(pf)); default 0.88 |
| `kvar` | `Optional[float]` | `15.0`, `30.0`, `5.0` | derived | sets the pf, kW / kVA with kvar's sign, at the kW of that moment; a pf of 0 (kvar at kW 0) leaves kvar as set (dispatched_kvar, S4b-8) |
| `model` | `Union[str, ForwardRef('GeneratorModel'), NoneType]` | `CurrentLimited`, `ConstantPQ`, `ConstantPV` | structural | 1 and 7 dispatch kW/kvar; 3 adds a voltage RegulatingControl; 2, 4, 5, 6 raise; default 1 |
| `Vminpu` | `Optional[float]` |  | untranscribed | below it the engine models the machine as constant Z; a power-flow setting |
| `Vmaxpu` | `Optional[float]` |  | untranscribed | above it the engine models the machine as constant Z; a power-flow setting |
| `yearly` | `Optional[str]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `daily` | `Optional[str]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `duty` | `Optional[str]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `dispmode` | `Union[str, ForwardRef('DispatchMode'), NoneType]` |  | untranscribed | a dispatch setting of time-series solutions; a snapshot does not use it |
| `dispvalue` | `Optional[float]` |  | untranscribed | a dispatch setting of time-series solutions; a snapshot does not use it |
| `conn` | `Union[str, ForwardRef('ConnectionType'), NoneType]` | `wye`, `delta` | mapped | `SynchronousMachine.earthing`; wye -> earthing true, delta -> false (no phaseConnection on a machine, S4b-5); default wye |
| `status` | `Union[str, ForwardRef('GenStatus'), NoneType]` |  | untranscribed | Fixed/Variable: whether load multipliers scale it; a dispatch setting of time-series solutions; a snapshot does not use it |
| `gen_class` | `Optional[int]` |  | untranscribed | a DSS report grouping |
| `Vpu` | `Optional[float]` | `1.0` | derived | model 3: the control's targetValue (V) = Vpu x ratedU; default 1 |
| `maxkvar` | `Optional[float]` |  | copied | `SynchronousMachine.maxQ` (kVAr); model 3 only (another model raises); default 2 x kvar |
| `minkvar` | `Optional[float]` |  | copied | `SynchronousMachine.minQ` (kVAr); model 3 only (another model raises); default -2 x kvar |
| `pvfactor` | `Optional[float]` |  | untranscribed | a convergence aid of the engine's model 3 |
| `forceon` | `Union[bool, Bool, NoneType]` |  | untranscribed | a dispatch setting of time-series solutions; a snapshot does not use it |
| `kVA` | `Optional[float]` | `737.0`, `775.0`, `125.0` | copied | `SynchronousMachine.ratedS` (kVA); default 1.2 x kW |
| `MVA` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (kVA is) |
| `Xd` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `Xdp` | `Optional[float]` | `0.27` | untranscribed | a dynamics setting; no home in the network profile parts |
| `Xdpp` | `Optional[float]` | `0.2` | untranscribed | a dynamics setting; no home in the network profile parts |
| `H` | `Optional[float]` | `2.0` | untranscribed | a dynamics setting; no home in the network profile parts |
| `D` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `UserModel` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `UserData` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `ShaftModel` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `ShaftData` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `DutyStart` | `Optional[float]` |  | untranscribed | a time-series curve; a snapshot does not use it (DSS-11) |
| `debugtrace` | `Union[bool, Bool, NoneType]` |  | untranscribed | a DSS debugging switch |
| `Balanced` | `Union[bool, Bool, NoneType]` |  | untranscribed | a power-flow setting of the engine's model |
| `XRdp` | `Optional[float]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `UseFuel` | `Union[bool, Bool, NoneType]` |  | untranscribed | a fuel-limited dispatch setting; a snapshot does not use it |
| `FuelkWh` | `Optional[float]` |  | untranscribed | a fuel-limited dispatch setting; a snapshot does not use it |
| `pct_Fuel` | `Optional[float]` |  | untranscribed | a fuel-limited dispatch setting; a snapshot does not use it |
| `pct_Reserve` | `Optional[float]` |  | untranscribed | a fuel-limited dispatch setting; a snapshot does not use it |
| `Refuel` | `Union[bool, Bool, NoneType]` |  | untranscribed | a fuel-limited dispatch setting; a snapshot does not use it |
| `DynamicEq` | `Optional[str]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `DynOut` | `Union[str, list[str], NoneType]` |  | untranscribed | a dynamics setting; no home in the network profile parts |
| `spectrum` | `Optional[str]` |  | untranscribed | harmonics model; no home in the network profile parts |
| `basefreq` | `Optional[float]` |  | untranscribed | no home on a machine |
| `enabled` | `Union[bool, Bool, NoneType]` |  | copied | `SynchronousMachine.normallyInService`; default true |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

| Reactor field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, ReactorName]` | `HVMV_Sub_HSB`, `T2_neutral` | copied | `SeriesCompensator.name`; mRID = rx_ + name, lowercased |
| `bus1` | `Optional[str]` | `SourceBus`, `sourcebus`, `K_LSB.4` | structural | node1 and the phases (the line rule) |
| `bus2` | `Optional[str]` | `HVMV115_HSB1`, `hvmv115s1_HSB1`, `K_LSB.0` | structural | node2; unset or on bus1's bus (a shunt or neutral reactor) raises |
| `phases` | `Optional[int]` | `1` | structural | the conductor count; default 3 |
| `kvar` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (X from kvar and kV) |
| `kv` | `Optional[float]` |  | untranscribed | acts only with kvar, which raises |
| `conn` | `Optional[str]` |  | untranscribed | a series reactor has no neutral |
| `Rmatrix` | `Optional[int]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `Xmatrix` | `Optional[int]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `Parallel` | `Union[bool, Bool, NoneType]` |  | structural | raises when yes: raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `R` | `Optional[float]` | `0.0` | copied | `SeriesCompensator.r` (ohm), `SeriesCompensator.r0` (ohm); per phase; r0 = r (no mutual); default 0 |
| `X` | `Optional[float]` | `14.798306633595042`, `0.5` | copied | `SeriesCompensator.x` (ohm), `SeriesCompensator.x0` (ohm); per phase; x0 = x (no mutual); unset raises |
| `Rp` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (a parallel R) |
| `Z1` | `Union[float, list[float], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `Z2` | `Union[float, list[float], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `Z0` | `Union[float, list[float], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `Z` | `Union[float, list[float], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `RCurve` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `LCurve` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one |
| `LmH` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (X from an inductance) |
| `normamps` | `Optional[float]` | `400.0` | structural | instance OperationalLimitSet rx_<name>_limits: CurrentLimit _norm (olt_normal); nothing from the engine's kvar-derived default |
| `emergamps` | `Optional[float]` | `400.0` | structural | CurrentLimit _emerg (olt_emergency) in rx_<name>_limits |
| `faultrate` | `Optional[str]` |  | untranscribed | a reliability setting; no home in the network profile parts |
| `pctperm` | `Optional[float]` |  | untranscribed | a reliability setting; no home in the network profile parts |
| `repair` | `Optional[str]` |  | untranscribed | a reliability setting; no home in the network profile parts |
| `basefreq` | `Optional[float]` | `60.0` | untranscribed | no home on a compensator; x is at the model's frequency |
| `enabled` | `Union[bool, Bool, NoneType]` |  | copied | `SeriesCompensator.normallyInService`; default true |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

### Decisions for S4b (approved 2026-11-08)

S4b-1 to S4b-4 were approved as written; S4b-5 to S4b-7 had no objection and stand as proposed. The user
added that cim18v17's `RotatingMachinePhase` names a 1-phase machine's phase.


- **S4b-1:** p and q follow the load sign for everything, PowerElectronicsConnection and SynchronousMachine (−kW for
  generation), as cim18v17 documents. The engine's export writes +kW on machines; the exporter negates.
- **S4b-2 (replaced by S4b-8):** pf with kvar raised unless both gave the same q.
- **S4b-3 (replaced by S4b-8):** a Storage's `kW` decided its state when set. The replay gives the same result on
  every deck (IEEE9500's `state=charge kW=150` still discharges at 150 kW).
- **S4b-4:** `ratedU` is line to line, as the engine exports it: the deck's kV, × √3 for 1-phase wye. It is not
  checked against the bus.
- **S4b-5:** a delta generator is `earthing=false`, because SynchronousMachine has no `phaseConnection`. In DSS a wye
  machine's neutral is ground (the shared rule raises otherwise), so for DSS `earthing` is exactly "not delta".
  A request for `RotatingMachine.phaseConnection` goes to `UPSTREAM_REQUESTS.md` as U8.
- **S4b-6:** IEEE123_test_harness's `Battery5` (1-phase, neutral on node 2) raises under the shared phase rule. The
  deck is wrong (it looks like a 3-phase battery written as `phases=1`), and a guess would put it across A–B.
- **S4b-7:** shape names `synchronous_machine` and `series_compensator`, shared with RAW (its C2), in place of the
  DSS plan's `machine`.
- **S4b-9:** a balanced three-phase device (phases `ABC`) has a blank `phases` cell, so no per-phase children
  and no `Terminal.phases` (above); U10 asks CIM-Tables for the balanced form.
- **S4b-8 (approved 2026-11-08):** the reader keeps each record's assignment history (`DssModel`), and the Generator,
  PVSystem and Storage mappers replay it as the engine does (above). The Load keeps S4-3.

## S5 (approved and done 2026-11-08)

**Result (2026-11-08).**
- Every equipment Location equals the engine's bus coordinates on both atoms and the 8 engine decks that bind:
  - one point per Terminal where every Terminal bus has `Bus.Coorddefined()`, and no Location otherwise;
  - this includes IEEE8500 and IEEE9500, where the engine's x is the longitude.
- The sweep test passes: 18 of the 24 `CIMHUB_DSS_DECKS` decks bind and 6 stop as listed. The throwaway 31-deck sweep
  is unchanged at 22.
- The reader fix (S5-7) recovers the IEEE123 coordinates: IEEE123_PV 214 rows (was 2), deconfliction 134 and
  test_harness 139 (were 0). Every coordinate file in the sweep parses.
- Locations: IEEE9500 unbal 8,072; IEEE8500 6,082; IEEE123_PV 326; IEEE13_CDPSM 46.
- The IEEE13_CDPSM golden directory has 14 files.
- **G7 after S5:**

  | deck | read | map | bind |
  |---|---|---|---|
  | IEEE9500 unbal | 4.0 s | 1.0 s | 8.2 s: 65,282 rows / 80,238 objects, about 7,900 rows/s |
  | IEEE8500 | 0.5 s | 0.7 s | 6.6 s: 47,840 rows, about 7,200 rows/s |

  The coordinates cost about 2 s of bind on each deck.

**The user's review:** keep the CIM17 form, `PositionPoint.Location`, not cim18v17's `Geometry`/`GeometricElement`
form (the catalog lists that as not yet catalogued). The decisions stand as recommended.

**Changes from the proposal:**
- A center-tap transformer gets two points, not three. Its secondary is one Terminal (`s1s2N`), because the windings
  land on lugs (DSS-2). The engine writes a point for each of its 3 windings, but two of them are the same bus.
- The Terminals come from the bound network, not from the document text (S5-2, revised 2026-11-09 when CIM-Tables
  declined U11). So a TransformerEnd's Terminal is whatever binding made of it; no separate end-class check.


S5 adds bus coordinates (`buscoords.cimtbl`), turns the throwaway deck sweep into a test, and records the G7
numbers. Census through today's reader on the 31 sweep decks: 14 decks have coordinates (about 31,000 rows; IEEE9500
5,305, IEEE8500 4,893, J1 3,441, K1 650; the IEEE13s 16-74). Only `PNNL/IEEE9500` uses `LatLongCoords`; every other
deck uses `BusCoords`. No deck uses both.

### Where the coordinates go (S5-1)

In CIM a `Location` hangs off a `PowerSystemResource`. A `ConnectivityNode` is not one, so a bus can't carry
coordinates itself. **Proposed:** each piece of conducting equipment gets one `Location` with one `PositionPoint` per
Terminal, holding the coordinates of that Terminal's bus. So a line is a two-point polyline, a load or capacitor is
one point, and a center-tap transformer has three. This matches the engine's own CIM export (`WritePositions` in
`ExportCIMXML.pas`), CIMHub_2_0's importer and GridAPPS-D. A CYME section's polyline also fits it, with more points
per line. The alternative, rejected: a `Junction` per bus (the CIM note: "to associate ... Location to a
ConnectivityNode"). It is closer to the native table, but it adds about 5,300 one-terminal equipment objects to
IEEE9500, and every consumer and exporter would have to skip them. No tool reads it either.

**Revised 2026-11-10 (S5-8):** the points are drawn as a GIS draws the equipment, through cimtables' `wkt` column.
A line (`ACLineSegment`) is a `LINESTRING` through its Terminals' buses; any other equipment is one `POINT`, at its
bus for one Terminal and at its buses' centroid for more. So a switch, fuse or transformer sits midway between its
buses, as a GIS point feature does, rather than as a two-point polyline.

### Shape `location` (added to the catalog first)

```
Profile = cim18v17
Import common.cimtbl

Object CoordinateSystem: mRID=crs_bus, name=BusCoords, crsUrn=OpenDSSLocalBusCoordinates

Update Table PowerSystemResource: mRID, wkt
    ln_650632,  "LINESTRING (200.0 350.0, 200.0 300.0)"
    sw_671692,  "POINT (225.0 250.0)"
    ld_671,     "POINT (200.0 250.0)"
```

An `Update` on the abstract `PowerSystemResource` resolves any subclass. cimtables' `wkt` binding makes the Location
(`<mRID>_loc`), one Identity-only `PositionPoint` per vertex (`<mRID>_loc_<n>`, `sequenceNumber` from 0) and points
the Location at the CoordinateSystem declared first.

### Buscoords

- **Mapper:** `importer/cimtbl/buscoords.py`, `map_buscoords(native, network)`. It is `DssImporter.bound_parts`:
  core binds every other part first, calls it with that network, writes `buscoords.cimtbl` beside them as the last
  `Import` (DSS_REWRITE_PLAN.md §2, row 16) and binds it onto the same network.
- **Finding the equipment (S5-2, revised 2026-11-09):** the mapper reads each piece of equipment's Terminals from the
  bound network (`terminal_buses`), not from the DSS records, so no mapper's mRID or bus rules are written twice; the
  circuit's buses are the network's ConnectivityNodes. The first version re-read the connectivity columns of the
  written documents (core's `document_terminals`) and asked CIM-Tables for that inverse (U11). CIM-Tables declined:
  a `.cimtbl` means what binding makes. The hook (`CimtblImporter.bound_parts`, `cimtbl_to_cim(bound_parts=)`) is in
  core because any spoke with coordinates needs it (GLM node latitude/longitude, CYME). The bound Terminals equalled
  the stand-in's on IEEE13_CDPSM, IEEE8500 and IEEE9500 unbal before it was deleted.
- **Geometry (S5-8):** one `wkt` cell per equipment, from its Terminal buses in Terminal `sequenceNumber` order. An
  `ACLineSegment` is `LINESTRING (x1 y1, x2 y2)`. Anything else is `POINT (x y)` at the buses' centroid: the bus
  itself for a load, capacitor, PV or source, the midpoint for a switch, fuse, regulator or two-terminal
  transformer. A center-tap transformer has two Terminals (S5-1 above), so it gets the midpoint too.
- **`device_geometry` (S5-9):** `DssImporter(..., device_geometry="linestring")` (and `dss_to_cim`) draws every
  two-terminal equipment as a `LINESTRING` from bus to bus, like a line: switches, fuses, transformers, regulators,
  series reactors. Equipment with one Terminal, or three or more, stays a `POINT`. The default is `"point"`; any
  other value raises when the importer is made. It is a keyword, not an environment variable, so a call's output
  depends only on its arguments.
- **Identity:** cimtables' `wkt` binding names them:
  - Location: `<equipment mRID>_loc`, unnamed (the engine's `<name>_Loc` name is dropped with the Location table);
  - PositionPoint: `<location>_<n>`, `sequenceNumber` = n, the vertex number from 0 (S5-5 is superseded);
  - CoordinateSystem: `crs_bus` (BusCoords) or `crs_latlong` (LatLongCoords), declared first in the file.
- **Order:** equipment in the order its first Terminal binds.
- **Values:** `xPosition`/`yPosition` are strings in CIM. The reader's floats are written by `cell` (`repr`), so a
  line's vertices and a one-Terminal point read back exactly; a centroid is `repr` of the float mean. For
  LatLongCoords the reader has already swapped them (x = longitude, y = latitude).
- **Partial coordinates (S5-3):** equipment gets a Location only if **every** one of its Terminal buses has
  coordinates. The engine writes 0, 0 for a bus without them, which would make a polyline vertex up. The file comment
  counts what is left out: `# not located: <n> of <m> equipment (a terminal bus without coordinates)`. That case is
  K1 (644 of 1,285 buses have none), plus IEEE123_PV and the deconfliction deck before the reader fix below.
- **Coordinates for a bus the circuit doesn't have:** untranscribed, because the engine ignores them too. The comment
  lists the count and the first names: `# no such bus: 17 (0000500000247160_load, ...)`. That covers IEEE8500's 17
  `_load` buses, IEEE9500's 8, IEEE13_CDPSM's older copy's `tap`, and J1's blank-name row.
- **Coordinate system (S5-4):** BusCoords → `crsUrn=OpenDSSLocalBusCoordinates`, the engine's value (a local
  projection the deck does not name). LatLongCoords → `urn:ogc:def:crs:OGC:1.3:CRS84`: WGS84 longitude/latitude in
  x, y order. The engine writes its local URN for both, which loses the fact that the values are degrees.
- **Fail fast:** a deck that uses both BusCoords and LatLongCoords raises (none does). A coordinate row that doesn't
  parse raises with its file and line (the reader fix below).

| Buscoords field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, BuscoordsName]` | `611`, `632`, `190-7361` | structural | picks the bus: every Terminal on it takes its coordinates; a name the circuit has no bus for is ignored, as in the engine (counted in the file comment) |
| `x` | `Optional[float]` | `0.0`, `200.0`, `-119.1650904` | derived | geometry: a line's LINESTRING vertex at each Terminal bus, verbatim; other equipment's POINT at its Terminal buses' centroid (the bus itself for one Terminal) |
| `y` | `Optional[float]` | `100.0`, `250.0`, `46.65388888` | derived | as x |
| `geographic` | `Union[bool, Bool, NoneType]` | `False`, `True` | mapped | the directive (LatLongCoords -> true) picks the CoordinateSystem: COORDINATE_SYSTEMS |


### Reader fix (S5-7)

The reader splits a coordinate row only on commas, and it skips any row it can't parse. The IEEE123 family's files are
whitespace-separated (`1     700     1500`), so IEEE123_PV keeps 2 of 216 rows and IEEE123_deconfliction and
IEEE123_test_harness keep none, all silently. The engine reads the file with its own command parser, which takes
commas or whitespace. The fix:
- split on either;
- raise on a row whose two coordinates aren't numbers, naming the file and line;
- keep J1's blank-name row (its name is `''`, which is no bus).

A bus listed twice keeps its last row, as in the engine; the reader's dict already does that.

### Deck sweep test (S5-6)

`tests/test_cimtbl_sweep.py`, marked `roundtrip`, runs every deck under `CIMHUB_DSS_DECKS` (the 24 in the
`test_data/models/feeders/OpenDSS` layout). Each deck either binds, with its bus voltages equal to the walk's, or
stops with the error its row in `SWEEP_STOPS` names. An unlisted stop fails the test, and so does a listed stop
that now binds, so the table stays true. Expected today:

| deck | stop |
|---|---|
| EPRI J1, K1, M1; IEEE13_OCHRE | DSS-10 (line phases ≠ code nphases) |
| PNNL IEEE9500 `Master-bal-initial-config` | `linecode=3PH_H-4_ACSR4_ACSR4_ACSR4_ACSR is no LineCode`, which the engine rejects too |
| IEEE123_test_harness | `Battery5` (S4b-6) |

So 18 of 24 bind. The other 7 of the throwaway sweep's 31 decks are copies in CIMHub_2_0's private
`cimhub_opendss/tests/test_models/`: IEEE13_CDPSM, IEEE13_assets plus its `_geo` variant, and the `ieee9500` and
`ieee9500_2025` bal/unbal pairs. They are dropped from the sweep, because their findings are already recorded (the
`Mode=7` PV, the open of an undefined switch). The per-slice sweep notes above stay as the history; this table is the current one.

### Engine checks (S5)

On the atom and every engine deck:
- for each line, its PositionPoints equal the engine's coordinates of its Terminals' buses (`Circuit.SetActiveBus`,
  `Bus.X()`, `Bus.Y()`); for other equipment, its one PositionPoint equals their centroid (S5-8);
- every equipment whose buses all have `Bus.Coorddefined()` has a Location, and no other equipment does.

For IEEE9500 the engine's x is the longitude, which also checks the reader's swap.

### Atoms, golden, G7

- **Atoms:** `atoms/buscoords/`:
  - `local.dss` + CSV: a line, a switch, a center-tap transformer, a regulator, a load, a capacitor and a PV. The CSV
    has a whitespace row, a bus the circuit doesn't have, a bus listed twice, and one bus left without coordinates.
  - `latlong.dss`: two buses, by LatLongCoords.
  - `local_linestring.cimtbl`: `local.dss` under `device_geometry="linestring"` (S5-9).
- **Golden:** the IEEE13_CDPSM directory (D6) gains `buscoords.cimtbl`, so it holds 14 files.
- **G7 before S5 (2026-11-08):**

  | deck | read | map | bind |
  |---|---|---|---|
  | IEEE9500 unbal | 4.4 s | 1.2 s | 6.0 s: 35,747 rows / 58,774 objects, about 6,000 rows/s |
  | IEEE8500 | 0.6 s | 0.4 s | 4.9 s: 24,700 rows, about 5,000 rows/s |

  That was about 400 rows/s before R12 (G7's first measurement), so G7 is closed. Coordinates add about 13,400
  points, 6,000-7,000 Locations and as many Update rows to IEEE9500 (the measurement after S5 is under Result).

### Decisions for S5 (approved 2026-11-08)

- **S5-1:** coordinates go on each piece of equipment's Location (one PositionPoint per Terminal), not on a Junction
  per bus. The CIM17 form (`PositionPoint.Location`) stays, not cim18v17's `Geometry` (the user's review).
- **S5-2:** the mapper finds the Terminals on the bound network (`CimtblImporter.bound_parts`); revised 2026-11-09
  from a re-read of the written documents (`document_terminals`) when CIM-Tables declined U11.
- **S5-3:** no Location for equipment with a Terminal bus that has no coordinates; the file comment counts them.
- **S5-4:** `crsUrn` is `OpenDSSLocalBusCoordinates` for BusCoords and CRS84 for LatLongCoords.
- **S5-5:** `sequenceNumber` is the Terminal number, 1-based.
- **S5-6:** the sweep test covers the 24 `CIMHUB_DSS_DECKS` decks; the 7 CIMHub_2_0 `test_models` copies are dropped.
- **S5-7:** the reader reads whitespace-separated coordinate rows and raises on a row it can't parse.
- **S5-8 (2026-11-10, the user's ask):** the coordinates are GIS geometry through cimtables' `wkt` column: a line is a
  `LINESTRING` through its Terminal buses, other equipment one `POINT` at their centroid (the midpoint for a switch
  or transformer). It replaces the Location and PositionPoint tables and S5-5's 1-based Terminal numbering; the
  Location loses its `<name>_Loc` name. The exporter reads it back by F8 (`EXPORT_MAPPING.md`).
- **S5-9 (2026-11-10, the user's ask):** `device_geometry="linestring"` draws every two-terminal device bus to bus
  instead of as a midpoint. The exporter needs nothing new: two points on two Terminals pair one per Terminal, so
  each bus comes back exactly.

## S6g: earth model and reclose sequences (2026-11-09)

Specified with the export in `EXPORT_MAPPING.md#s6g-earth-model-and-reclose-sequences`. On import:
- A deck with geometry gets one `EarthResistivity` (`earth`), first in `linegeometry.cimtbl`, from `Set earthmodel`
  and the geometry lines' `rho` (the engine's Deri and 100 ohm-m when unset, listed). Every WireConfiguration names
  it. FullCarson, disagreeing rho, and rho on a line without geometry raise.
- A Recloser's `Shots` - 1 reclosures are `RecloseSequence` rows `<switch>_rs<n>` in `line.cimtbl`, at its
  `RecloseIntervals` (the engine's defaults filling either, listed). Both given and disagreeing raise, and so does
  Shots above 4 without intervals.

## S8: load shapes (built 2026-11-21 at the user's word)

GLM's S8 (`cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s8-load-players`) maps a player to the
`ConformLoadSchedule → ConformLoadGroup ← ConformLoad` pattern (the user's call, 2026-11-21: ConformLoad groups,
points in a Parquet sidecar). A DSS `LoadShape` a Load names as `yearly` is the same thing: one curve of multipliers
that scales every load naming it. Mapper `importer/cimtbl/loadshape.py`, artifact `loadshape.cimtbl`, shape
`load_schedule`; the loads in `load.cimtbl`. Atom `tests/atoms/loadshape/loadshapes.dss`:
- an hourly shape with `qmult`, shared by two loads (`res`);
- a 15-minute shape given as `minterval` and normalized (`com`, as K1's `action=normalize`);
- a 900 s shape given as `sinterval` (`ind`);
- M1's bare `mult=1` with no `npts` (`flat`), named in another case;
- a shape no Load names (`pv`, as K1's PVSystem irradiance shape);
- a load with no shape.

| # | decision |
|---|---|
| S8-1 | A LoadShape a Load names as `yearly` is a `ConformLoadGroup` `lg_<name>` with one `ConformLoadSchedule` `ls_<name>` (lowercased); each Load naming it is a `ConformLoad` whose `LoadGroup` is the group, its p and q as for any load. Only `yearly`: a ConformLoad has one group, and every load in the sweep names only `yearly` (M1, K1, J1). `daily` and `duty` are untranscribed (listed on the row) |
| S8-2 | Multipliers: `value1` = `mult`, `value1Unit` none; `value2` = `qmult` (`value2Unit` none) when given, else unset: Q follows `mult`, the engine's rule (engine-checked). `action=normalize` divides each array by its largest magnitude, as the engine does; an array assigned after it raises (the engine normalizes only what came before) |
| S8-3 | Time: `timeStep` = the interval slot the deck assigned last (the engine's rule), copied in its unit (`interval` h, `minterval` min, `sinterval` s), one schedule table per unit; none gives the engine's 1 h. DSS has no date: sample k (from 1) is in force from k × interval (engine-checked: yearly mode, hour 1 gives sample 1), so `startTime` = 2020-01-01T00:00Z (ditto's epoch) + one interval (`cimhub_gdm` TIMESERIES_NEEDS.md X2). The engine wraps a shape around; CIM has no repeat, so the wrap is lost (X4) |
| S8-4 | Points: `RegularTimePoint` rows in the Parquet sidecar (`cimhub_core.time_points`), as GLM's: `DssImporter(time_points={})` / `dss_to_cim(..., time_points=)` fills the caller's dict; without it the points are dropped with one warning |
| S8-5 | `npts` unset: the engine reads none of `mult`, inline or from a file (engine-checked with DSS C-API 0.14.5: `Npts` 0, the load constant), so the group has no schedule, its name kept, as GLM's undefined player (M1's five `mult=1` shapes). `npts` set must equal the number of values |
| S8-6 | `UseActual=Yes` raises: a Load naming it takes the shape's peak as its kW and kvar, or keeps its own, depending on whether `yearly=` comes after `kW=` (engine-checked), which the record does not keep. So no DSS form maps a `NonConformLoad` yet, either way |
| S8-7 | A shape no Load names as `yearly` (a PVSystem's irradiance, a Vsource's) is not mapped and not checked; the master's comment counts it (`not mapped: Loadshape 1`) |

**What raises:**
- `UseActual=Yes`;
- `hour`, `csvfile`, `sngfile`, `dblfile`, `PQCSVFile`, `Pmult`, `Pbase`, `Qbase` set (no deck sets them);
- an interval of 0 (an hour array);
- `npts` other than the number of `mult` values, `qmult` of another length, no `mult`;
- an array assigned after `action=normalize`, or an `action` other than normalize, DblSave, SngSave;
- a Load whose `yearly` names no shape of the deck.

**Engine checks.** `test_cimtbl_loadshape.py` compiles the atom and reads each shape's `PMult`, `QMult` and
`HrInterval` from the engine, against the mapper's values (the normalized `com` included, and `flat`'s 0 points).
`test_export_loadshape.py` runs the original atom and its export in yearly mode every 5 minutes for 6 hours, every
load's power equal at every step (rel 1e-9).

**Not mapped:** an `Hour`-array shape and a file the reader does not read (`csvfile=`, ...). A `mult=(file=...)`
with no `npts` is S8-5's case too: the engine reads no points from the file either (engine-checked).

### LoadShape fields

| Loadshape field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, LoadshapeName]` | `com`, `flat`, `ind` | copied | `ConformLoadGroup.name`, `ConformLoadSchedule.name`; mRID = lg_ / ls_ + name, lowercased |
| `npts` | `Optional[int]` | `4`, `3`, `2` | structural | the number of points the engine reads: unset, none of mult (inline or from a file; engine-checked), so the group has no schedule; else it must equal the number of mult values |
| `interval` | `Optional[float]` | `1.0` | copied | `ConformLoadSchedule.timeStep` (h); the interval slot the deck assigned last (the engine's rule); 0 (an hour array) raises; none: 1 h |
| `mult` | `Union[float, list[float], NoneType]` | `[2.0, 4.0, 8.0, 6.0]`, `[1.0]`, `[1.0, 0.9, 0.95]` | copied | `RegularTimePoint.value1`; the points, in the Parquet sidecar (S8-4); action=normalize divides them by their peak |
| `hour` | `Union[float, list[float], NoneType]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (an irregular shape has no RegularIntervalSchedule) |
| `mean` | `Optional[float]` |  | untranscribed | a Monte Carlo statistic; the engine computes it from mult |
| `stddev` | `Optional[float]` |  | untranscribed | a Monte Carlo statistic; the engine computes it from mult |
| `csvfile` | `Optional[int]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the reader reads mult=(file=...)) |
| `sngfile` | `Optional[int]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the reader reads mult=(file=...)) |
| `dblfile` | `Optional[int]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the reader reads mult=(file=...)) |
| `action` | `Optional[str]` | `normalize` | derived | normalize: mult and qmult each divided by its largest magnitude, as the engine does (one assigned after it raises); DblSave, SngSave write files and are untranscribed; others raise |
| `qmult` | `Union[float, list[float], NoneType]` | `[0.4, 0.6, 0.9, 0.7]` | copied | `RegularTimePoint.value2`; in the sidecar; unset: Q follows mult (the engine's rule), value2 unset |
| `UseActual` | `Union[bool, Bool, NoneType]` |  | structural | Yes raises: a Load naming it takes the shape's peak as its kW, or keeps its own, by command order, which the record does not keep (engine-checked); default No |
| `Pmax` | `Optional[float]` |  | untranscribed | used only with UseActual |
| `Qmax` | `Optional[float]` |  | untranscribed | used only with UseActual |
| `sinterval` | `Optional[str]` | `900` | copied | `ConformLoadSchedule.timeStep` (s); the interval slot the deck assigned last (the engine's rule); 0 (an hour array) raises; none: 1 h |
| `minterval` | `Optional[str]` | `15` | copied | `ConformLoadSchedule.timeStep` (min); the interval slot the deck assigned last (the engine's rule); 0 (an hour array) raises; none: 1 h |
| `Pbase` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (a normalize base) |
| `Qbase` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (a normalize base) |
| `Pmult` | `Optional[str]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (a synonym of mult) |
| `PQCSVFile` | `Optional[float]` |  | structural | raises when set: no deck in the sweep sets it, so a mapping waits for one (the reader reads mult=(file=...)) |
| `MemoryMapping` | `Union[bool, Bool, NoneType]` |  | untranscribed | how the engine stores the points |
| `Mode` | `Optional[float]` |  | untranscribed | generator dispatch; no effect on a Load |
| `Interpolation` | `Optional[str]` |  | untranscribed | AVG and EDGE agree at the solution steps, which are on the interval grid (TIMESERIES_NEEDS.md X3) |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |
