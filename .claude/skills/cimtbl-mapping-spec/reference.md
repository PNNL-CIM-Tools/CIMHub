# Mapping spec: worked example and template

Companion to [SKILL.md](SKILL.md). The example is the OpenDSS `LineCode` slice: mapper
`cimhub_opendss/src/cimhub_opendss/importer/cimtbl/linecode.py` (`map_linecode`), atoms
`cimhub_opendss/tests/atoms/linecode/mtx601.{dss,cimtbl}` (matrix code, IEEE 13) and `seq_3_1_0c.{dss,cimtbl}`
(sequence code, IEEE 8500), test `cimhub_opendss/tests/test_cimtbl_linecode.py`.

## 1. Source record

```
New linecode.mtx601 nphases=3 BaseFreq=60
~ rmatrix = (0.3465 | 0.1535 0.3375 | 0.1580 0.1560 0.3414 )
~ xmatrix = (1.0179 | 0.3849 1.0478 | 0.4236 0.5017 1.0348 )
~ cmatrix = (0 | 0 0 | 0 0 0)
~ units=mi normamps=730
```

## 2. The section as written in the spec

**Identity.** `mRID` = `lc_` + `name`, lowercased (DSS names are case-insensitive). `PhaseImpedanceData` has no mRID;
its `identifier` column is `<mRID>_<row><column>`.

**Form.** A code that sets any of `r1 x1 r0 x0 C1 C0 B1 B0` is a sequence code → `PerLengthSequenceImpedance`. One
that sets `rmatrix`/`xmatrix`/`cmatrix` is a matrix code → `PerLengthPhaseImpedance` + one `PhaseImpedanceData` per
lower-triangle element. DSS keeps whichever form was set last and the reader does not record the order, so a code that
sets both raises. So does a code that sets neither (DSS would apply its defaults).

**Values.** The reader yields floats for most slots (written as `repr()`), but `C1`, `C0`, `B1`, `B0` and `baseFreq`
as the file's text. One table per header: matrix data per length unit; sequence codes per (length unit, `bch`/`b0ch`
source), because a C-derived `bch` is in nS and a copied `B1` in uS.

**Field classification** (generated with `fields_table(schema.Linecode, records, fields=FIELDS)`; samples from `IEEE13_CDPSM.dss`
and the IEEE8500 `LineCodes.dss`; `{length}` is the code's `units`):

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
gives b = 0 without a `baseFreq`.

**Fail fast.** `units` unset or `none`; a 1- or 2-phase sequence code; both C1 and B1 (or C0 and B0); both forms or
neither; a nonzero C without `baseFreq`; a matrix whose length does not fit `nphases`.

**Sweep (2026-11-06).** 9 of the 24 decks with line codes map and bind. The rest stop on:

| stop | decks | open point |
|---|---|---|
| nonzero `cmatrix` without `baseFreq` | ieee9500, IEEE8500 and EPRI K1 triplex | DSS takes the circuit's default base frequency: take it from the deck's `Circuit`/`Set DefaultBaseFrequency`, else 60 Hz? |
| `units` unset | IEEE13_original, IEEE123, EPRI M1 and J1 | DSS reads the values per unit of the *line's* length, so the unit belongs to the instance: defer to the `Line` mapper, or require `units`? |
| 1-/2-phase sequence code | EPRI J1 (17 codes) | the engine builds a 1-phase line from Z1 alone and a 2-phase one from Zs = (2Z1 + Z0)/3, Zm = (Z0 - Z1)/3; neither is the CIM sequence convention |
| two mRIDs give one UUID | IEEE8500 (`lc_1p_#2acsr_#2n` vs `lc_1p_#2arv_#2n`) | upstream bug: the mRID seed drops text up to the last `#` (filed in `.development/UPSTREAM_REQUESTS.md`, R10) |
| `nphases=4` read as 3 | IEEE13_OCHRE | reader bug: it limits nphases to 1..3, so the 10-value `rmatrix` no longer fits; filed against the reader |

**Reader/schema findings.** `faultrate` is typed `int` (so `0.1` reads as `0`); `LineType` is typed `float` (DSS
values are words); `C1`/`C0`/`B1`/`B0`/`baseFreq` are typed `str`.

**Expected differences from the hand translation.** The IEEE 13 hand translation carries corrected off-diagonals;
the import keeps the deck's values (`mtx601` r21 = 0.1535).

## 3. The artifact this produces (`mtx601.cimtbl`, the reviewed golden)

```
# OpenDSS LineCode -> PerLengthPhaseImpedance + PhaseImpedanceData, PerLengthSequenceImpedance (catalog).
# Source table: LineCode (records: 1)
# Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#linecode

Profile = cim18v17

Table PerLengthPhaseImpedance: mRID, name, conductorCount, calculatedFrequency (Hz)
    # untranscribed: normamps=730.0
    lc_mtx601, mtx601, 3, 60

# units=mi. row/column are conductor indices of the lower triangle.
# derived: b = 2 pi baseFreq C (b_from_c), from cmatrix (nF) -> nS
Table PhaseImpedanceData: identifier, PhaseImpedance, row, column, r (ohm/mi), x (ohm/mi), b (nS/mi)
    lc_mtx601_11, lc_mtx601, 1, 1, 0.3465, 1.0179, 0.0
    lc_mtx601_21, lc_mtx601, 2, 1, 0.1535, 0.3849, 0.0
    lc_mtx601_22, lc_mtx601, 2, 2, 0.3375, 1.0478, 0.0
    lc_mtx601_31, lc_mtx601, 3, 1, 0.158,  0.4236, 0.0
    lc_mtx601_32, lc_mtx601, 3, 2, 0.156,  0.5017, 0.0
    lc_mtx601_33, lc_mtx601, 3, 3, 0.3414, 1.0348, 0.0
```

What a reviewer checks against §1:

- every copied value is the deck's text, in the deck's unit (`ohm/mi` from `units=mi`, `60` Hz verbatim);
- `0.1580` became `0.158`: the reader's float, `repr()`-ed (D2), not a rounding;
- `baseFreq` is copied to `calculatedFrequency` and also feeds the derived `b`; the table comment states the formula;
- the untranscribed non-empty value (`normamps=730.0`) is on the catalog row (D5);
- `row`/`column` are conductor indices, not phases; the line's phase order picks the row later;
- it binds under cim18v17 with `cimtbl_to_cim(atom_documents(document))`, and `r21` reads back 0.1535 ohm/mi.

## 4. Section template

```markdown
## <NativeClass>

Mapper: `cimhub_<fmt>/src/cimhub_<fmt>/importer/cimtbl/<table>.py` (`map_<table>`). Atoms:
`cimhub_<fmt>/tests/atoms/<table>/<case>.{<ext>,cimtbl}`; test `tests/test_cimtbl_<table>.py`.

**Identity.** mRID = `<prefix>` + <native id slot>, <case rule>. Children: ... Identifier columns: ...

**Form.** Which records become which shape (link the shape in `cimtbl-shapes`).

**Values.** Reader typing (float vs text), header grouping, per-record units.

<fields_table(NATIVE_CLASS, records, fields=FIELDS) output>

**Derived.** `<function>(...)`: formula, input slots, units.

**Defaults.** What the format assumes when a field is absent; recorded as `# defaulted: ...` on the row.

**Fail fast.** Every condition that raises.

**Sweep.** <n> of <m> models map and bind; table of stops.

**Reader/schema findings.** Wrong slot types, filed against the reader.

**Expected differences** from the reference hand translation.
```
