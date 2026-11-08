# OpenDSS → `.cimtbl` mapping spec

**Status:** S1 done (2026-11-07). `LineCode` (Phase 1) and the inline `Transformer` are seeded from CIMHub_2_0 with
their atoms; the master, buses and Vsource are S0/S1's. The other DSS classes follow slice by slice
([`DSS_REWRITE_PLAN.md`](../../.development/DSS_REWRITE_PLAN.md)), each section approved before its code (DSS-12).
Format: the `cimtbl-mapping-spec` skill. Contract: the `cimtbl-import-contract` skill.

The classification tables are generated from each mapper's `FIELDS` with
`cimhub_core.cimtbl.fields_table(..., fields=FIELDS)`. The samples come from `tests/decks/IEEE/IEEE13_CDPSM/` and the
IEEE8500 `LineCodes.dss`. `{length}` in a unit is the code's `units`.

## Artifact files and order

| native class | artifact | shape | depends on |
|---|---|---|---|
| (the deck) | `<Model>.cimtbl` (master) | settings, `common` rows (Substation, Feeder, BaseFrequency, BaseVoltage), `Import`s | every part |
| (the topology walk) | `bus.cimtbl` | one `ConnectivityNode` per bus, with its `BaseVoltage` | the master |
| `Vsource` | `vsource.cimtbl` | `source` | the master, `bus.cimtbl` |
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
| `nphases` | `Optional[int]` | `3`, `2` | copied | `PerLengthPhaseImpedance.conductorCount`; the matrix order of rmatrix/xmatrix/cmatrix; a sequence code must be 3-phase (a 1-phase DSS line uses Z1 as its self impedance, a 2-phase one Zs = (2 Z1 + Z0)/3 and Zm = (Z0 - Z1)/3; neither is the CIM sequence convention) |
| `r1` | `Optional[float]` | `0.769009`, `0.3489`, `0.535622` | copied | `PerLengthSequenceImpedance.r` (ohm/{length}) |
| `x1` | `Optional[float]` | `0.312115`, `0.491691`, `0.560725` | copied | `PerLengthSequenceImpedance.x` (ohm/{length}) |
| `r0` | `Optional[float]` | `1.294322`, `0.613107`, `0.608571` | copied | `PerLengthSequenceImpedance.r0` (ohm/{length}) |
| `x0` | `Optional[float]` | `0.287695`, `1.241561`, `1.19452` | copied | `PerLengthSequenceImpedance.x0` (ohm/{length}) |
| `C1` | `Optional[str]` | `154.240283543118`, `8.96939698228171`, `9.08509466816236` | derived | PerLengthSequenceImpedance bch = 2 pi baseFreq C1 (b_from_c): nF -> nS |
| `C0` | `Optional[str]` | `154.240283543118`, `4.95311934077534`, `5.10821052765362` | derived | PerLengthSequenceImpedance b0ch = 2 pi baseFreq C0 (b_from_c): nF -> nS |
| `units` | `Optional[str]` | `mi`, `km` | mapped | the length unit of every per-length header via LENGTH_UNIT |
| `rmatrix` | `Union[float, list[float], NoneType]` | `[0.3465, 0.1535, 0.3375, 0.158, 0.156...`, `[0.7526, 0.1535, 0.7475, 0.156, 0.158...`, `[1.3238, 0.2066, 1.3294]` | structural | PhaseImpedanceData r, one row per lower-triangle element |
| `xmatrix` | `Union[float, list[float], NoneType]` | `[1.0179, 0.3849, 1.0478, 0.4236, 0.50...`, `[1.1814, 0.3849, 1.1983, 0.5017, 0.42...`, `[1.3569, 0.4591, 1.3471]` | structural | PhaseImpedanceData x, one row per lower-triangle element |
| `cmatrix` | `Union[float, list[float], NoneType]` | `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]`, `[0.0, 0.0, 0.0]` | derived | PhaseImpedanceData b = 2 pi baseFreq C (b_from_c): nF -> nS |
| `baseFreq` | `Optional[str]` | `60` | copied | `PerLengthPhaseImpedance.calculatedFrequency` (Hz), `PerLengthSequenceImpedance.calculatedFrequency` (Hz); also the frequency of the derived b |
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

**Fail fast.** `units` unset or `none`; a 1- or 2-phase sequence code; both C1 and B1 (or C0 and B0); both forms or
neither; a nonzero C without `baseFreq`; a matrix whose length does not fit `nphases`.

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
