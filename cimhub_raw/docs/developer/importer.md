# The importer

The importer takes the `GraphModel` the reader builds and makes a cim18v17 network in two steps that never share
objects: the mappers turn RAW records into `.cimtbl` documents (text), and cimtables binds that text. The code is
[`importer/raw_to_cimtbl.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_raw/src/cimhub_raw/importer/raw_to_cimtbl.py)
(the orchestrator), `importer/topology.py` (the substations), `importer/node_breaker.py` (the SUBSTATION blocks) and
one mapper per RAW table in
[`importer/cimtbl/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_raw/src/cimhub_raw/importer/cimtbl).
The design record for each table is [CIMTBL_MAPPING.md](../CIMTBL_MAPPING.md). The helpers every mapper uses (`cell`,
`mrid`, `lookup`, `Field`, `check_fields`, `fill_defaults`) are core's, and are described on the core site's
[`.cimtbl` import contract](https://pnnl-cim-tools.github.io/CIMHub/core/developer/cimtbl/) page.

## The entry points

```python
import tempfile
from pathlib import Path

from cimtables.document import format_document
from cimhub_core.cimtbl_testing import cim_scope
from cimhub_raw.raw34_reader import Raw34Reader
from cimhub_raw.importer.raw_to_cimtbl import RawImporter, raw_to_cim

native = Raw34Reader("cimhub_raw/tests/cases/IEEE14/IEEE_14_bus.raw").read_all()

documents = RawImporter("IEEE14").to_cimtbl(native)         # pure: a DocumentSet, nothing written
print([part.name for part in documents.parts])
print(format_document(documents.master)[:200])

with cim_scope():                                           # puts back the CIM profile cimtables sets
    artifact_dir = Path(tempfile.mkdtemp(prefix="ieee14_artifact_"))     # a new, empty directory
    network = raw_to_cim(native, name="IEEE14", artifact_dir=artifact_dir)   # writes, then binds
    print(sorted(path.name for path in artifact_dir.iterdir())[:4])
```

| Call | Does |
|---|---|
| `RawImporter(name, *, authority)` | `name` is the master's `Model`, its file stem and the name of the case's `GeographicalRegion`. `authority` defaults to `AUTHORITY` (`https://github.com/PNNL-CIM-Tools/CIMHub`). `model_cls` is `BusBranchModel`. |
| `.to_cimtbl(model)` | Returns the `DocumentSet`: the master plus the non-empty parts. No file is written. |
| `.to_cim(model, *, network=None, artifact_dir=None)` | Core's: write the documents (to `artifact_dir`, else a temporary directory), load them with cimtables, bind onto `network` if given. |
| `raw_to_cim(model, *, name, authority=AUTHORITY, network=None, artifact_dir=None)` | Builds a `RawImporter` and calls `to_cim`. |

The model's name must not equal a part's name: the master and the parts are written as `<name>.cimtbl` and
`<part>.cimtbl` in one directory, and cimtables raises `document names repeat` for `name="bus"`.

## to_cimtbl

`to_cimtbl` does these things, in this order:

1. `Site(model, name)` computes what every mapper shares (below).
2. Each `(native class, mapper)` of `MAPPING_ORDER` is called as `mapper(model, site)` and returns one document;
   a document with no statements is dropped.
3. `equipment_terminal.map_equipment_terminal(model, site.node_breaker, parts)` runs last, over the documents the
   other mappers made, and is added when it has rows.
4. `map_master` makes the master, which `Import`s each remaining part in order.

### Site

`Site` is the one object the orchestrator builds so that no mapper walks the model twice:

| Attribute | Holds |
|---|---|
| `values` | `case_identification.case_values(native)`: SBASE, BASFRQ, THRSHZ, NXFRAT and XFRRAT, each with whether it was defaulted. A case with IC other than 0 raises. |
| `region` | The case's `GeographicalRegion` mRID, `rgn_<name>` (lower case). |
| `zones` | Bus number to its zone (`zone.bus_zones`); a blank ZONE takes the schema default. |
| `base_kv`, `areas`, `bus_types` | Bus number to BASKV, AREA (an `int`) and IDE, from `bus.filled_buses`. |
| `node_breaker` | A `NodeBreaker` over the SUBSTATION blocks (below). |
| `substations`, `substation_of` | The `SubstationGroup`s (below) and the bus number to substation mRID map every device mapper reads. |
| `untraced` | The buses whose AREA the export's trace cannot recover (`untraced_area_buses`). |

### MAPPING_ORDER

`MAPPING_ORDER` is the `Import` order: zone, area interchange, bus, substation, branch, switch, multi-section line,
load, fixed shunt, generator, impedance correction, transformer, two-terminal DC, VSC DC, multi-terminal DC, FACTS
device, switched shunt, GNE device, induction machine. A table comes after what it references: the substation
document needs the bus's `TopologicalNode`s, the multi-section line moves branches that `branch` wrote, and the
switched shunt's control may name a generator's machine or a FACTS device (the comment in the source says so).
A lambda per entry hands each mapper only what it needs from the `Site`.

`equipment_terminal.cimtbl` follows all of them, because its `Update Table Terminal` rows move `Terminal`s that the
equipment documents wrote. It matches each record against the mRIDs those documents wrote (`written_equipment`), so a
terminal record that names no equipment, or two, raises.

The three phase-2 stubs (`multi_terminal_dc`, `gne_device`, `induction_machine`) return an empty document when the case
has no such records and raise `NotImplementedError` naming the table when it has some: the case fails at once instead
of losing records. Only `induction_machine` is reachable from a file: the reader already raises for a populated
MULTI-TERMINAL DC or GNE section, so those two stubs are the second guard. `owner` and `interarea_transfer` write no artifact by design (CIM 18 has no ownership or scheduled
transfer; the transfers are listed on the `ControlArea` comment).

### The master

`map_master` writes the case's bases and types, then one `Import` per part:

| Statement | Content |
|---|---|
| `BasePower` | `mRID=sbase`, `basePower (MVA)` = SBASE; first, because every later `(pu system)` column converts on it. A `defaulted: SBASE=100` comment when the file left it blank. |
| `BaseFrequency` | `bf_<f>hz`, `frequency (Hz)` = BASFRQ; defaulted to 60 with a comment. |
| `GeographicalRegion` | The case, `rgn_<name>`. |
| `BaseVoltage` | One per distinct BASKV (and each DC valve voltage), `nominalVoltage (kV)` copied. |
| `OperationalLimitType` | Four types for the bus voltage limits: normal and emergency, high and low. |
| `OperationalLimitType` | Twelve rating-set types `olt_rate1`..`olt_rate12`, named from the `RATING` records (`ratings.rating_type_table`). |
| `Import` | One per non-empty part. |

The master's comment (`_master_comment`) is the audit trail for what no table carries: the case title, the spec link,
`untranscribed:` lines for the solution options present (`GAUSS`, `NEWTON`, ...) and for the owner count,
`defaulted:` lines for NXFRAT and XFRRAT when blank, and a `not mapped:` line counting the record classes in the model
that no mapper handles (`_HANDLED` lists the ones that are handled or deliberately have no artifact).

### The substations: topology.py

A RAW case has no substations, so the importer makes them (`importer/topology.py`, never a graph walk of its own).
`substation_groups(native, zones, threshold, block_of_bus)` builds a `cimtopology.core.Network` of only the merge
edges and takes `Topology(network).islands()`. A bus on no merge edge is its own substation. The merge edges are:

| Edge | Rule |
|---|---|
| System switching device | Every one. |
| Branch | R = 0 and \|X\| at most THRSHZ (the case's `GENERAL` value, else 0.0001), or CKT starting `@` or `*`. |
| Series capacitor | A branch with X < 0. |
| Transformer | Every winding's bus. |

No edge crosses a zone boundary, and a SUBSTATION block's buses are always joined (`_block_edges`); a block across two
zones raises, and so does a group that holds two blocks. A group holding a block is named `sub_s<IS>`, else
`sub_<lowest bus>`. The result is a list of `SubstationGroup(buses, merged_by, block)`, ordered by lowest bus.
`untraced_area_buses` runs the same island rule over RAW's devices to find the buses the export cannot assign an area to
(seeded by generator buses and by buses of a tie); it lists them so that the importer can write `untranscribed: area=` on
their rows. `islands(nodes, edges)` is shared with the exporter's area trace.

```python
from cimhub_raw.importer.raw_to_cimtbl import Site
from cimhub_raw.raw34_reader import Raw34Reader

native = Raw34Reader("cimhub_raw/tests/cases/IEEE14/IEEE_14_bus.raw").read_all()
site = Site(native, "IEEE14")
print(site.substation_of[9])                 # sub_4: bus 9 is joined to bus 4 by a transformer
```

### The node-breaker blocks: node_breaker.py

`NodeBreaker(native, buses)` indexes the SUBSTATION blocks: `blocks` (IS to record), `nodes` ((IS, NI) to node record)
and `block_of_bus` (bus to IS). A node on no bus, a node number twice in a block, or a bus in two blocks raises.
`node(bus, number, record_id)` returns the block and node record of node `number` of `bus`, and raises when the bus has
no block or the node is not the bus's. `regulated_terminal(bus, number, record_id)` returns the `Terminal` a control
that regulates `bus` (or node `number` of it, NREG or NODk) names: `bb_<I>_T1`, or `bb_s<IS>_n<NI>_T1` for a node.
`node_mrid(block, node)` is `sub_s<IS>_n<NI>`; node numbers are unique only within their block.

```python
from cimhub_raw.importer.raw_to_cimtbl import Site
from cimhub_raw.raw34_reader import Raw34Reader

ieee118 = Raw34Reader("cimhub_raw/tests/cases/IEEE118/IEEE118_all_hydro_25_clean_4_subs.raw").read_all()
blocks = Site(ieee118, "IEEE118").node_breaker
print(sorted(blocks.blocks), len(blocks.nodes))          # [8, 37, 49, 100] 42
print(blocks.regulated_terminal(8, 0, "example"))        # bb_8_T1
```

## The mapper layout

Every mapper module in `importer/cimtbl/` that maps a table has these parts:

| Part | Role |
|---|---|
| `NATIVE_CLASS` | The schema class it maps (`schema.FixedShuntRecord`). `substation.py` also has `NODE_CLASS` and `DEVICE_CLASS`, `impedance_correction.py` a `POINT_CLASS`. |
| `PREFIX` | The mRID prefix (`cap_`). An mRID is `mrid(PREFIX, record.ID)`, with the composite ID quoted as written, never sanitized. Modules that write several classes have several (`LINE_PREFIX`, `SERIES_CAPACITOR_PREFIX`, `SHUNT_PREFIX` in `branch.py`). |
| `FIELDS` | `{slot: Field}`: every slot of the native class, classified. `test_classification_is_complete` fails on a slot added by a schema regeneration and on a stale entry. |
| `map_<table>(native, ...)` | A pure function: the model and the `Site`'s pieces in, one `Document` out. An empty table returns a `Document` with no statements. |
| `_PROVENANCE` | The comment at the top of the document: what it maps, the record count and the spec anchor. |

`Field(kind, targets=(), note="")` is core's classification. `kind` is one of `copied`, `mapped`, `structural`,
`derived`, `untranscribed`. A `copied` field names its targets, `(cim_class, column, unit)`; its note says where the
value goes and what a blank means. The note is for the reviewer and is the same text the spec carries.

Four small modules carry what the mappers share:

| Module | Holds |
|---|---|
| `records.py` | `raw_defaults(cls)`: the class's `raw_default` annotations, less the blank-string ones. `fill_keyed_defaults(fields, record, defaults)`: core's `fill_defaults` that keeps the reader's composite `record.ID`, which `dataclasses.replace` drops. It returns the filled copy and the `defaulted: slot=value` comment for the row. `listed_off_default(record, slots, defaults)`: the `untranscribed: a=1.0, b=2` comment for slots CIM cannot hold whose value is not the default. |
| `derived.py` | Named, tested functions for a value CIM has no attribute for, each with the spec formula in its docstring, and each paired with its inverse for the exporter: `kv_from_per_unit` / `per_unit_from_kv`, `ka_from_rating` / `rating_from_ka`, `per_unit_from_mva` / `mva_from_per_unit`, `ohms_from_per_unit` / `per_unit_from_ohms`, `net_import` / `net_export`, and the transformer, tap-changer and ZIP functions. |
| `ratings.py` | `rating_type_table` for the master and `RatingRows`, which collects a device's `OperationalLimitSet` and limit rows: one set `<eq>_ratings` per device on its first terminal (per winding for a transformer), a limit per nonzero `RATEn`. A zero rating is "no limit" and writes no row. |
| `tie_flow.py`, `dc_topology.py` | Rows for a device whose ends are in two areas (`TieFlow` pairs) and the DC side of a DC line. |

The rules a mapper keeps:

- A value is copied as read, with its unit in the column header: `Column("bPerSection", "pu system")`, the cell text
  from `cell(value)`. A blank cell is a blank. A derived value goes through a named function and is classified
  `derived`.
- A blank field the mapper needs takes its `raw_default` through `fill_keyed_defaults`, and the row says so in a
  `defaulted:` comment. A blank field with no default raises; it is never guessed.
- A field the mapping does not cover is `untranscribed` with a reason, or raises when the record sets it to something
  CIM cannot hold. Ambiguity raises (two machines of one plant that disagree).
- An enum is mapped with `lookup(table, value, slot=..., record_id=...)`, which raises with the known values.
- Error messages name the record, `fixed shunt 9_1`, and the RAW field.

## One mapper end to end: fixed_shunt

[`fixed_shunt.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_raw/src/cimhub_raw/importer/cimtbl/fixed_shunt.py)
maps a fixed shunt (I, ID, STATUS, GL, BL) to one always-in `LinearShuntCompensator`. The shunt atom has two shunts at
bus 1. The example blanks the ID and STATUS of the first, in a copy under `/tmp`, to show the defaults:

```text
     1,'1 ',    1,     1.500,    20.000          (the atom)
     1,,,     1.500,    20.000                    (the copy)
     1,'2 ',    0,     0.000,   -10.000
```

```python
from pathlib import Path

from cimtables.document import format_document
from cimhub_raw.importer.cimtbl import fixed_shunt
from cimhub_raw.importer.raw_to_cimtbl import Site
from cimhub_raw.raw34_reader import Raw34Reader

text = Path("cimhub_raw/tests/atoms/shunt/fixed_shunts.raw").read_text()
Path("/tmp/blank_id.raw").write_text(text.replace("     1,'1 ',    1,     1.500", "     1,,,     1.500"))
atom = Raw34Reader("/tmp/blank_id.raw").read_all()
site = Site(atom, "atom")
print(format_document(fixed_shunt.map_fixed_shunt(atom, site.substation_of, site.base_kv, site.values.base_mva)))
```

`map_fixed_shunt(native, substations_by_bus, base_kv_of, base_mva)`, for each record in (bus, ID) order:

1. `fill_keyed_defaults(FIELDS, record, raw_defaults(NATIVE_CLASS))` fills a blank ID and STATUS from the schema
   (`1` and `1`) and returns a comment, `defaulted: shunt_id=1, status=1`, for the row.
2. `per_unit_from_mva(gl, base_mva)` and `per_unit_from_mva(bl, base_mva)` give GL and BL, which RAW states in MW and
   Mvar at one per unit voltage, as per unit on the system base: the columns are `gPerSection (pu system)` and
   `bPerSection (pu system)`, and cimtables converts them to siemens using the `nomU` and the master's `BasePower`.
3. `nomU (kV)` is the bus's BASKV, copied from the `Site`, so the per unit base is the bus's voltage.
4. `lookup(IN_SERVICE, status, ...)` maps STATUS to `inService`; any other STATUS raises.
5. The `BaseVoltage` is the bus's `bv_<BASKV>` and the `EquipmentContainer` is the bus's substation, from
   `substation_of`.

The result:

```text
Table LinearShuntCompensator: mRID, name, bus, gPerSection (pu system), bPerSection (pu system), nomU (kV), maximumSections, normalSections, sections, inService, BaseVoltage, EquipmentContainer
    cap_1_2, 1_2, 1, 0.0,   -0.1, 115.0, 1, 1, 1, false, bv_115kv, sub_1
    # defaulted: shunt_id=1, status=1
    cap_1_1, 1_1, 1, 0.015, 0.2,  115.0, 1, 1, 1, true,  bv_115kv, sub_1
```

(A row's `#` comment is the line above it. The record with the blank ID comes second because the mapper sorts on
`(bus, str(shunt_id))` and a blank ID sorts as `None`, after `2`.) Here the unit math is
`cimtables`' and the derived value is a named function. The classification is checked by a test, and so is each
fail-fast rule:

```python
from cimhub_core.cimtbl import check_fields
from cimhub_raw.importer.cimtbl import fixed_shunt

check_fields(fixed_shunt.FIELDS, fixed_shunt.NATIVE_CLASS)    # raises AssertionError listing missing and stale slots
```

## Adding a mapper for a new RAW table

1. **Spec first.** Add a section to [CIMTBL_MAPPING.md](../CIMTBL_MAPPING.md): every field of the record classified,
   the CIM class and shape it becomes, the mRID prefix, the fail-fast rules and the expected differences. A mapper
   without an approved section is not merged. The
   [`cimtbl-mapping-spec` skill](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/cimtbl-mapping-spec/SKILL.md)
   says how.
2. **The mapper.** Start from a module of the same shape (`fixed_shunt.py` for a device on a bus, `branch.py` for one
   between two). Fill `FIELDS` from the spec, then write `map_<table>(native, ...)` returning a `Document`. Pick the
   table shape from core's
   [canonical shapes](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/). Take a prefix from the
   cimtbl-translate table, or request one (the source marks requested prefixes with a comment). A stub for a table
   with no mapping yet is three lines: `not_mapped_yet(native, NATIVE_CLASS, "<table>")` from `phase2.py`.
3. **The order.** Add `(<module>.NATIVE_CLASS, lambda native, site: <module>.map_<table>(native, ...))` to
   `MAPPING_ORDER`, after every table whose rows it references. If the master should not report the class as `not
   mapped`, it is handled by being in `MAPPING_ORDER` (or in `_HANDLED`, for a class with no artifact).
4. **The exporter.** If the table is to be exported, see [The exporter](exporter.md).
5. **The atom.** Add `tests/atoms/<group>/<case>.raw`, a hand-built case that covers what the public cases lack, and
   a line for it in the group's `README.md`. Each atom says it is synthetic.
6. **The tests.** In `tests/test_raw_to_cimtbl.py`: add the module to `test_classification_is_complete`
   (`check_fields`), check the rows or the bound objects through the core getters in SI, and add each fail-fast rule
   as `pytest.raises(ValueError, match=...)`. If IEEE14 holds the table, add it to `test_part_matches_golden` and
   regenerate its golden. [Testing](testing.md) lists the helpers.
7. **The golden.** Run `CIMHUB_UPDATE_GOLDENS=1 scripts/test-all.sh raw`, review the diff in `tests/goldens/`.
8. Run `scripts/test-all.sh raw` and `scripts/leak-gate.sh`.
