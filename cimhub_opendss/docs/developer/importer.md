# The importer

The importer takes a `DssModel` and builds a cim18v17 network in two steps that never share objects: the mappers
turn DSS records into `.cimtbl` documents (text), and cimtables binds that text. The code is
[`importer/dss_to_cimtbl.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/src/cimhub_opendss/importer/dss_to_cimtbl.py)
(the orchestrator), `importer/topology.py` (the bus walk) and one mapper per DSS class in
[`importer/cimtbl/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_opendss/src/cimhub_opendss/importer/cimtbl).
The design record for each class is [CIMTBL_MAPPING.md](../CIMTBL_MAPPING.md). The helpers every mapper uses
(`cell`, `mrid`, `lookup`, `Field`, `check_fields`) are core's, and are described on the core site's
[`.cimtbl` import contract](https://pnnl-cim-tools.github.io/CIMHub/core/developer/cimtbl/) page.

## The entry points

```python
import tempfile
from pathlib import Path

from cimtables.document import format_document
from cimhub_opendss import DssImporter, DssReader, dss_to_cim

model = DssReader("cimhub_opendss/tests/decks/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss").read_all()

documents = DssImporter("IEEE13_CDPSM").to_cimtbl(model)      # pure: a DocumentSet, nothing written
print([part.name for part in documents.parts])
print(format_document(documents.master)[:200])

artifact_dir = Path(tempfile.mkdtemp(prefix="ieee13_artifact_"))     # a new, empty directory
network = dss_to_cim(model, name="IEEE13_CDPSM", artifact_dir=artifact_dir)  # writes, then binds
print(sorted(path.name for path in artifact_dir.iterdir())[:4])
```

| Call | Does |
|---|---|
| `DssImporter(name, *, authority, length_unit, device_geometry, time_points)` | `name` is the master's `Model` and the file stem. `authority` defaults to `AUTHORITY` (`https://github.com/PNNL-CIM-Tools/CIMHub`). `length_unit` sets the per-length unit of line codes with no units on code or line, instead of the magnitude gate. `device_geometry` is `"point"` (default) or `"linestring"`, how a two-terminal device is drawn in `buscoords.cimtbl`; anything else raises. `time_points` is the caller's dict for the yearly shapes' points. |
| `.to_cimtbl(model)` | Returns the `DocumentSet`: master plus parts. No file is written. |
| `.to_cim(model, *, network=None, artifact_dir=None)` | The core `to_cim`: write the documents (to `artifact_dir`, which must hold no `.cimtbl` file the set does not write, else a temporary directory), load them with cimtables, then add the `bound_parts`. With `network`, binds onto it. Then it adds the yearly shapes' time points to `time_points`. |
| `.bound_parts(model, network)` | `[buscoords.map_buscoords(model, network, device_geometry)]`: the one part that reads the bound Terminals. |
| `dss_to_cim(model, *, name, ...)` | Builds a `DssImporter` and calls `to_cim`. |

The yearly shapes' points do not go in the artifact; they go to the caller's `time_points` (the Parquet sidecar,
which needs the `time-points` extra). Without `time_points` they are dropped with one warning that names the shapes.

## to_cimtbl

`to_cimtbl` does five things, in this order:

1. `site(model, length_unit)` runs the topology walk once and returns a `Site` (a `NamedTuple`): the circuit name, the
   walk's `buses`, the `substation` and `feeder` mRIDs (`sub_<circuit>`, `fdr_<circuit>`), `base_frequency` and
   `length_unit`. A deck with no `New Circuit` raises `the deck has no New Circuit`.
2. `map_buses(site)` makes `bus.cimtbl`: one `ConnectivityNode` per bus the walk reached, with its `BaseVoltage`,
   highest voltage first, then by name.
3. `cimhub_core.load_response.zip_fractions()` makes the shared `zip_fractions.cimtbl` (the three ZIP characteristics).
4. Each `(native class, mapper)` of `MAPPING_ORDER` is called as `mapper(model, site)` and returns one document.
5. Documents with no statements are dropped, and `map_master` makes the master, which `Import`s each remaining part
   in order.

`MAPPING_ORDER` is the `Import` order, and a class comes after what it names: the wire catalogs, `LineSpacing`,
`LineGeometry`, `LineCode`, `XfmrCode`, `Vsource`, `Line`, `Reactor`, `Transformer`, `RegControl`, `LoadShape`, `Load`,
`Capacitor`, `CapControl`, `PVSystem`, `Storage`, `Generator`. A lambda per entry passes each mapper only what it
needs from the `Site` (the buses, the feeder mRID, the base frequency, the length unit). A test checks that no native
class is listed twice. `buscoords.cimtbl` is not in the list; `bound_parts` adds it last.

### The master

`map_master` writes the model's containers and its bases, then one `Import` per part:

| Statement | Content |
|---|---|
| `Substation`, `Feeder` | Named after the circuit; the Feeder's `NormalEnergizingSubstation` is the Substation. |
| `BaseFrequency` | `Set defaultbasefreq`, else the DSS default, with a `defaulted:` comment. |
| `BaseVoltage` | One per distinct bus voltage from the walk and one per `voltagebases` value, highest first. A base on no bus is kept: the engine's `CalcVoltageBases` snaps bus bases to it, so the export writes it back. The comment reconciles the two lists (`on no bus`, `not in voltagebases`). |
| `OperationalLimitType` | The two limit types, `olt_normal` and `olt_emergency`, which every `CurrentLimit` names, then `olt_season1` .. `olt_season<N>` for the most seasons any `Transformer` or `XfmrCode` rates (`limit_types(seasons)`), which their `ApparentPowerLimit`s name. |
| comment | `not mapped: Relay 1, ...` lists each DSS class no mapper reads, by count, so nothing disappears silently. A LoadShape no Load names as `yearly` is counted too. |

`READ_BY_OTHERS` lists the classes that another mapper reads in full (`Fuse`, `Recloser`, `SwtControl`, from
`line.CONTROLS`); they count as mapped.

### The topology walk

`importer/topology.py` builds a `cimtopology.core.Network` from the deck, and `walk(network)` gives each bus its nominal
voltage and system (`BusSystem`). A spoke never writes its own graph walk (invariant I9).

| `Network` part | From the DSS model |
|---|---|
| `sources` | Every `Vsource`, `New Circuit` included, with its DSS defaults (`vsource.with_defaults`). `basekv` is line to line on a 3-phase source and the source voltage on a 1-phase one; other phase counts raise. |
| `branches` | Every `Line` (a switch keeps its voltage, open or not), and every `Reactor` or `Capacitor` with a `bus2` on another bus. |
| `transformers` | Every `Transformer`, with `phases`, `windings`, `kVs` and `conns` from the instance, else from its `XfmrCode`. A polyphase winding's kV is line to line. A single-phase coil's connection comes from its nodes (1 to 3 are phase conductors); windings 2 and 3 on one bus form a split-phase secondary (`transformer.is_split_phase`). |

```python
from cimtopology.core import walk
from cimhub_opendss.importer.topology import dss_network

buses = walk(dss_network(model))
print(len(buses), buses["611"])      # 22 BusSystem(kv=4.16, system=<System.THREE_PHASE: '3-phase'>)
```

Bus names are lowercased, as the mappers use them. The `BaseVoltage` of every piece of equipment comes from this walk,
not from a `kV` on the device; a Load whose `kV` is more than 1 % off its bus's raises.

## The mapper layout

Each mapper module in `importer/cimtbl/` has these parts (`wire.py` and `geometry.py` map several classes and have no single `NATIVE_CLASS` or `PREFIX`; `loadshape.py` and `buscoords.py` have no `PREFIX`; `injection.py` and `inverter.py` are shared helpers, not mappers):

| Part | Role |
|---|---|
| `NATIVE_CLASS` | The schema class it maps (`schema.Linecode`). |
| `PREFIX` | The mRID prefix (`lc_`); an mRID is `mrid(PREFIX, name, lowercase=True)`, since DSS names are case-insensitive. |
| `FIELDS` | `{slot: Field}`: every slot of the native class, classified. |
| `map_<class>(native, ...)` | A pure function: records in, one `Document` out. An empty class returns a `Document` with no statements. |
| `_PROVENANCE` | The document's header comment: what it maps, the record count and the spec anchor. |

`Field(kind, targets=(), note="")` is core's classification. `kind` is one of `copied`, `mapped`, `structural`,
`derived`, `untranscribed`. A `copied` field names its targets, `(cim_class, column, unit)`, and the unit can hold a
placeholder such as `ohm/{length}`; `copied_columns(FIELDS, cim_class, length=unit)` fills it from the record's own
unit and returns the `(slot, Column)` pairs. `untranscribed_values(FIELDS, record)` gives the `# untranscribed: ...`
comment for the untranscribed slots a record has set, so nothing is dropped silently. `fill_defaults(FIELDS, record,
defaults)` returns a copy with each unset slot the mapper reads filled from `dss_defaults(NATIVE_CLASS)`, and a
`defaulted:` comment.

The rules a mapper keeps:

- Values are copied verbatim with the deck's unit in the column header: `Column("r", "ohm/km")`, cell text from
  `cell(value)`. A quantity CIM has no attribute for goes through a named function and is marked `derived` in
  `FIELDS` and in a table comment. A formula keeps its units with its values, as
  `cimhub_core.derived.capacitance` does, and the header names the result's unit: kVAr / kV² is `bPerSection (mS)`,
  kV² / kVA is `r (kohm)`. A plain-float target (`RegulatingControl.targetValue`) in kvar or kV carries
  `targetValueUnitMultiplier=k`. No mapper multiplies by 1000 or builds a `cim.X` value.
- An unset property the mapper needs is a `defaulted:` comment or a raise; never a guess.
- A property the mapping does not cover raises when the deck sets it (`not mapped yet (no deck in the sweep sets
  them)`). When a deck needs it, the spec gains the mapping first.
- Ambiguity raises. A property that DSS resolves by assignment order, which the record does not keep, is read from
  `model.assignments` or raises.

## One mapper end to end: LineCode

[`linecode.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/src/cimhub_opendss/importer/cimtbl/linecode.py)
maps `LineCode` to a template `PerLengthImpedance` and a `WireConfiguration` for the lines to reference (I6). Take this
deck line:

```text
New Linecode.3-1/0C_2/0CN_T nphases=3 r1=0.3489 x1=0.426198 r0=0.588811 x0=1.29612 c1=10.4308823411236 c0=4.48501282215346 units=km baseFreq=60 normamps=310 emergamps=310 faultrate=0.1 pctperm=20 repair=3
```

```python
from cimtables.document import format_document
from cimhub_opendss.importer.cimtbl.linecode import map_linecode

atom = DssReader("cimhub_opendss/tests/atoms/linecode/seq_3_1_0c.dss").read_all()
print(format_document(map_linecode(atom, base_frequency=60.0)))
```

The reader gives a `Linecode` record. `map_linecode(native, *, base_frequency, length_unit=None)` then:

1. Finds each code's length unit (`templates`). A code with `units` takes it, looked up in `LENGTH_UNIT` (an unmapped
   unit raises with the known ones). A code with none takes the units of the lines that use it, one template per
   unit (`lc_<name>_<unit>`), and a code used with and without units raises. A code no line gives units for takes
   `length_unit=`, else the magnitude gate (`gated_unit`: the median positive r through `UNITS_GATE`), and says which
   in a comment.
2. Chooses the form (`is_sequence`): a 3-phase `r1/x1/r0/x0/C1/C0/B1/B0` code is a `PerLengthSequenceImpedance`; a matrix
   is a `PerLengthPhaseImpedance` with one `PhaseImpedanceData` row per lower-triangle element, and so is a 1- or
   2-phase sequence code, built as a phase matrix the way the engine builds the line (`phase_matrix`). Both forms or
   neither raises.
3. Fills what the DSS engine would: a missing `cmatrix` becomes the balanced default matrix, and a code with a
   nonzero C and no `baseFreq` takes the deck's base frequency. Both are `defaulted:` comments.
4. Writes the columns with the code's unit (`r (ohm/km)`); `C1` becomes `bch (nS/km)` through `b_from_c`, which is why
   the table's header comment says `derived`.
5. Writes `normamps`, `faultrate` and the rest as an `# untranscribed:` comment, and a `WireConfiguration`
   `lc_<name>_wc` that points at the template.

The result is the golden `tests/atoms/linecode/seq_3_1_0c.cimtbl`:

```text
Table PerLengthSequenceImpedance: mRID, name, r (ohm/km), x (ohm/km), r0 (ohm/km), x0 (ohm/km), calculatedFrequency (Hz), bch (nS/km), b0ch (nS/km), isTemplate
    # untranscribed: normamps=310.0, emergamps=310.0, faultrate=0.1, pctperm=20.0, repair=3
    lc_3-1/0c_2/0cn_t, 3-1/0C_2/0CN_T, 0.3489, 0.426198, 0.588811, 1.29612, 60, 3932.350000000008, 1690.8100000000002, true

Table WireConfiguration: mRID, name, PerLengthImpedance
    lc_3-1/0c_2/0cn_t_wc, 3-1/0C_2/0CN_T, lc_3-1/0c_2/0cn_t
```

The mRID keeps the deck's `-` and `/` (lowercased); a name holding `,`, `(`, `)`, `#` or `"` is quoted by the formatter, never sanitized (I8). The classification is checked by a test, and so is each fail-fast rule:

```python
from cimhub_core.cimtbl import check_fields
from cimhub_opendss.importer.cimtbl.linecode import FIELDS, NATIVE_CLASS

check_fields(FIELDS, NATIVE_CLASS)    # raises AssertionError listing missing and stale slots
```

## Adding a mapper for a new DSS class

1. **Spec first.** Add a section to [CIMTBL_MAPPING.md](../CIMTBL_MAPPING.md): every property of the class classified,
   the CIM class and shape it becomes, the mRID prefix, the fail-fast rules and the expected differences. A mapper
   without an approved section is not merged.
2. **The mapper.** `cimhub_core.scaffold.scaffold_mapper("opendss", schema.Foo, prefix="foo_", records=...)` writes the
   stub and the completeness test: `NATIVE_CLASS`, `PREFIX`, `FIELDS` with one entry per slot, and `map_foo`. Fill
   `FIELDS` from the spec, then write `map_foo(native, ...)` returning a `Document`. Pick the table shape from core's
   [canonical shapes](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/).
3. **The order.** Add `(foo.NATIVE_CLASS, lambda native, site: foo.map_foo(native, site.buses, site.feeder))` to
   `MAPPING_ORDER`, after every class its rows reference. If another mapper reads the class, add it to
   `READ_BY_OTHERS`. If the class needs terminals bound first, make it a `bound_parts` part instead.
4. **The atom pair.** Add `tests/atoms/<table>/<case>.dss` (a few lines from a public deck, with its origin in a
   comment) and the reviewed `<case>.cimtbl` golden.
5. **The tests.** `tests/test_cimtbl_<table>.py`: `check_fields`, the golden (`assert_matches_golden`), the binding under
   cim18v17 with key values checked in SI (`.to(unit)`), and each fail-fast rule with `pytest.raises(..., match=...)`.
   Add the engine as the oracle where OpenDSS computes the same quantity. [Testing](testing.md) lists the helpers.
6. **The golden directory.** If the IEEE13_CDPSM deck has the class, regenerate with `CIMHUB_UPDATE_GOLDENS=1`, and
   review the diff in `tests/goldens/IEEE13_CDPSM/`.
7. **The sweep.** If a deck in `test_cimtbl_sweep.py`'s `SWEEP_STOPS` stopped on this class, update its row; the test
   fails when a listed stop now binds.
8. Run `scripts/test-all.sh opendss` and `scripts/leak-gate.sh`.
