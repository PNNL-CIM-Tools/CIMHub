# OpenDSS → `.cimtbl` mapping spec

**Status:** S2 done (2026-11-07): LineCode units, base frequency and short sequence codes; wire catalogs;
LineSpacing/LineGeometry. XfmrCode is deferred to S3. `LineCode` (Phase 1) and the inline `Transformer` are seeded from CIMHub_2_0 with
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
| `Transformer` (inline) | `transformer.cimtbl` | 3-phase: `transformer_by_ends`; 1-phase: `transformer_by_phase_ends` | the master (Feeder, BaseVoltage) and the topology walk's bus systems |

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

**Form.** A code that sets any of `r1 x1 r0 x0 C1 C0 B1 B0` is a sequence code (OpenDSS
[Line properties](https://opendss.epri.com/Properties14.html)); one that sets `rmatrix`/`xmatrix`/`cmatrix` is a
matrix code. DSS keeps whichever form was set last, and the reader does not record the order, so a code that sets
both raises. So does a code that sets neither (DSS would apply its defaults).

**Values.** The DSS reader yields floats for most slots (written as `repr()`), but `C1`, `C0`, `B1`, `B0` and
`baseFreq` as the file's text. One table per header: matrix data per length unit, sequence codes per (length unit,
`bch`/`b0ch` source), because a C-derived `bch` is in nS and a copied `B1` in uS.

| Linecode field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, LinecodeName]` | `mtx601`, `mtx602`, `mtx603` | copied | `PerLengthPhaseImpedance.name`, `PerLengthSequenceImpedance.name`; mRID = lc_ + name, lowercased |
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

Example (`wiredata.cimtbl`, IEEE13_Assets):

```
Table OverheadWireInfo: mRID, name, rDC20 (ohm/kft), rAC25 (ohm/kft), gmr (in), radius (in), ratedCurrent (A)
    # defaulted: Rac = 1.02 x Rdc
    wire_acsr_1/0,   ACSR_1/0,   0.212121212, 0.21636363624000002, 0.05352, 0.199,  230.0
    ...
Table OverheadWireInfo: mRID, name, rDC20 (ohm/mi), rAC25 (ohm/mi), gmr (in), radius (in), ratedCurrent (A)
    wire_cu_1/0, CU_1/0, , 0.607, 0.13356, 0.184, 100.0
```

**Fail fast:** a unit selector unset; radius and diam both set or neither; GMRac unset; `Capradius` or
`SemiconLayer` set (no deck sets them).

**Oracle:** every written value equals the engine's property in the engine's units (`opendssdirect` WireData /
CNData / TSData), including the filled Rac, on the vendored IEEE13_Assets and IEEE4 decks
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
| `normamps` | `Optional[float]` | `230.0`, `340.0`, `730.0` | copied | `OverheadWireInfo.ratedCurrent` (A) |
| `emergamps` | `Optional[float]` | `200.0`, `239.0`, `172.0` | untranscribed | no home on WireInfo, which has one ratedCurrent (plan D9) |
| `diam` | `Optional[float]` | `0.398`, `0.563`, `0.927` | derived | radius = diam / 2 (radius_from_diameter) |
| `Seasons` | `Optional[int]` |  | untranscribed | no home on WireInfo, which has one ratedCurrent (plan D9) |
| `Ratings` | `Union[float, list[float], NoneType]` |  | untranscribed | no home on WireInfo, which has one ratedCurrent (plan D9) |
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
| `normamps` | `Optional[float]` | `260.0` | copied | `ConcentricNeutralCableInfo.ratedCurrent` (A) |
| `emergamps` | `Optional[float]` |  | untranscribed | no home on WireInfo, which has one ratedCurrent (plan D9) |
| `diam` | `Optional[float]` | `0.567`, `0.935` | derived | radius = diam / 2 (radius_from_diameter) |
| `Seasons` | `Optional[int]` |  | untranscribed | no home on WireInfo, which has one ratedCurrent (plan D9) |
| `Ratings` | `Union[float, list[float], NoneType]` |  | untranscribed | no home on WireInfo, which has one ratedCurrent (plan D9) |
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
| `normamps` | `Optional[float]` | `165.0` | copied | `TapeShieldCableInfo.ratedCurrent` (A) |
| `emergamps` | `Optional[float]` |  | untranscribed | no home on WireInfo, which has one ratedCurrent (plan D9) |
| `diam` | `Optional[float]` | `0.368` | derived | radius = diam / 2 (radius_from_diameter) |
| `Seasons` | `Optional[int]` |  | untranscribed | no home on WireInfo, which has one ratedCurrent (plan D9) |
| `Ratings` | `Union[float, list[float], NoneType]` |  | untranscribed | no home on WireInfo, which has one ratedCurrent (plan D9) |
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

## XfmrCode (deferred to S3, approved 2026-11-07)

XfmrCode maps to `TransformerTankConfiguration` (`transformer_template`, `transformer_template_1ph`), but three
things block it:
- **U2:** both template shapes fail to bind in CIM-Tables today (a `TransformerTankEnd` on a configuration has no
  node).
- **D10:** the 3-phase tank configuration convention is still open.
- **Lugs:** the instance-by-template link (`TransformerLug.sequenceNumber`, now in cim18v17) has no shape yet.

It moves to S3, next to the Transformer instances that use it (2,474 by code), once U2 is fixed.

## Transformer

Mapper: `cimhub_opendss/importer/cimtbl/transformer.py` (`map_transformer(native, buses, container)`). Atoms:
`tests/atoms/transformer/` — `xfm1` (3-phase, IEEE13), `sub3` (3-winding delta-wye-wye, neutral impedance on
winding 2), `reg1` (1-phase regulator unit), `service` (EPRI J1 7.2/0.24 kV), `center_tap` (phase-to-phase primary,
s1/s2 secondary), with `prereq.cimtbl`; tested by `tests/test_cimtbl_transformer.py`. Inline transformers only:
`XfmrCode` instances wait for the lug template (`TransformerLug.sequenceNumber`, being added to CIM UML and
cim-profiles).

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
- an XfmrCode instance;
- `phases` other than 1 or 3, or windings other than 2 or 3;
- an active-winding scalar (`kV`, `kVA`, `conn`, `bus`, `tap`, `%R`) without `wdg=`;
- a tap other than 1 (RegControl slice);
- `pct_Rs` and `pct_loadloss` that disagree, or `XHL` and `X12` that disagree;
- 3-phase nodes other than `1.2.3`;
- two windings on one bus that are not a split-phase secondary;
- a bus missing from the topology result.

| Transformer field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, TransformerName]` | `Sub3`, `Reg1`, `Reg2` | copied | `PowerTransformer.name`; mRID = xf_ + name, lowercased |
| `phases` | `Optional[int]` | `3`, `1` | structural | 1 = by phase ends, 3 = by balanced ends; default 3 |
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
| `buses` | `Union[str, list[str], NoneType]` | `['SourceBus', '650.1.2.3.4', '650z']`, `['BRKR.1', 'RG60.1']`, `['BRKR.2', 'RG60.2']` | structural | end node and terminal phases; one end per distinct bus |
| `conns` | `Union[str, ForwardRef('ConnectionType'), list[Union[str, ForwardRef('ConnectionType')]], NoneType]` | `[ConnectionType(text='delta', descrip...`, `[ConnectionType(text='wye', descripti...` | structural | connectionKind, grounded, default nodes; default wye |
| `kVs` | `Union[float, list[float], NoneType]` | `[115.0, 4.16, 13.2]`, `[2.4, 2.4]`, `[4.16, 0.48]` | structural | 3-phase: end ratedU; 1-phase: winding baseU, ratedU derived (x sqrt 3, x 2) |
| `kVAs` | `Union[float, list[float], NoneType]` | `[5000.0, 5000.0, 1000.0]`, `[1666.0, 1666.0]`, `[500.0, 500.0]` | structural | end ratedS / winding ratedS (halves / 2); winding 1's kVA is every baseS |
| `taps` | `Union[float, list[float], NoneType]` |  | structural | a tap other than 1 raises until the RegControl slice (RatioTapChanger.step) |
| `XHL` | `Optional[float]` | `0.01`, `2.0`, `11.63` | structural | mesh 1-2 x (percent on winding 1's kVA); default 7 |
| `XHT` | `Optional[float]` | `0.025` | structural | mesh 1-3 x; default 35 |
| `XLT` | `Optional[float]` | `0.025` | structural | mesh 2-3 x; default 30 |
| `Xscarray` | `Union[float, list[float], NoneType]` |  | untranscribed | for more than 3 windings, which raise |
| `thermal` | `Optional[float]` |  | untranscribed | thermal model; no home in the network profile parts |
| `n` | `Optional[float]` |  | untranscribed | thermal model; no home in the network profile parts |
| `m` | `Optional[float]` |  | untranscribed | thermal model; no home in the network profile parts |
| `flrise` | `Optional[float]` |  | untranscribed | thermal model; no home in the network profile parts |
| `hsrise` | `Optional[float]` |  | untranscribed | thermal model; no home in the network profile parts |
| `pct_loadloss` | `Optional[float]` | `0.01`, `0.7221`, `0.7639` | derived | when pct_Rs is unset, r = loadloss / 2 on windings 1 and 2; set with pct_Rs, the two must agree |
| `pct_noloadloss` | `Optional[float]` | `0.2423`, `0.0851` | derived | 3-phase: end 1 g (percent); 1-phase: tank noLoadLoss = % x kVA |
| `normhkVA` | `Optional[float]` | `40.0`, `25.0` | untranscribed | instance OperationalLimitSet or untranscribed (plan D9) |
| `emerghkVA` | `Optional[float]` | `56.0`, `35.0` | untranscribed | instance OperationalLimitSet or untranscribed (plan D9) |
| `sub` | `Union[bool, Bool, NoneType]` |  | untranscribed | DSS report flag |
| `MaxTap` | `Optional[float]` |  | untranscribed | tap changer range; RatioTapChanger with the RegControl slice |
| `MinTap` | `Optional[float]` |  | untranscribed | tap changer range; RatioTapChanger with the RegControl slice |
| `NumTaps` | `Optional[int]` | `16` | untranscribed | tap changer range; RatioTapChanger with the RegControl slice |
| `subname` | `Optional[str]` |  | untranscribed | DSS report label |
| `pct_imag` | `Optional[float]` |  | structural | 3-phase: end 1 b (percent); 1-phase: tank percentMagnetizingCurrent |
| `ppm_antifloat` | `Optional[float]` | `5.0` | untranscribed | numerical aid of the DSS solver |
| `pct_Rs` | `Union[float, list[float], NoneType]` | `[0.0005, 0.0005, 0.0005]`, `[0.55, 0.55]`, `[0.596, 0.596]` | structural | 3-phase: end r (percent); 1-phase: winding r (percent); default 0.2 |
| `bank` | `Optional[str]` | `Reg` | untranscribed | each DSS Transformer is its own PowerTransformer |
| `XfmrCode` | `Optional[str]` |  | structural | instances by code raise until the lug template (TransformerLug.sequenceNumber) |
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
| `enabled` | `Union[bool, Bool, NoneType]` |  | copied | `PowerTransformer.normallyInService` |
| `like` | `Optional[str]` |  | untranscribed | the reader resolves like= before mapping |

**Deck sweep (2026-11-06, placeholder bus systems).** 1,365 of the 1,378 inline transformers in 11 decks map. Stops:

| stop | count | next |
|---|---|---|
| taps ≠ 1 | 6 (IEEE13_original regulators) | RegControl slice |
| `kVA=750` with no `wdg=` | 8 (ieee9500 `*-DIES1`) | the engine sets both windings of a 2-winding transformer ([750, 750]), but only the last of a 3-winding one; needs an engine-pinned rule |
| `%R=0.1` with no `wdg=` | 2 (J1 `ExistingSite*`) | the engine applies it to the last winding ([0.2, 0.1]) |

Reader fixes this slice needed: numeric bus and wire names stayed floats (`634` → `634.0`, i.e. node 0); quoted
arrays (`conns='delta delta'`, IEEE37) failed to build, and the reader dropped `reg1a` with only a log line. A
failed build now raises.
