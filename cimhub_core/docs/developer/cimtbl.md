# The .cimtbl import contract

An importer never builds CIM objects. It maps native records to `.cimtbl` text, and
[CIM-Tables](https://pnnl-cim-tools.github.io/CIM-Tables/) builds the model from that text. This page lists the
helpers a spoke uses to do that, in the order a mapper uses them. They live in three modules of
[`cimhub_core`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_core/src/cimhub_core):

| Module | Used for |
|---|---|
| [`cimtbl.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/src/cimhub_core/cimtbl.py) | Cell text, mRIDs, field classification, native defaults, spec skeletons, and `cimtbl_to_cim`. |
| [`export_slots.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/src/cimhub_core/export_slots.py) | The export mirror of `Field`: what an exporter does with each slot of a native class. |
| [`load_response.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/src/cimhub_core/load_response.py) | `zip_fractions()`, the one document every distribution spoke shares. |

The shape of the tables a mapper writes is on [Canonical shapes](shapes.md). The classes that call these helpers
(`CimtblImporter`, `FormatReader`) are on [Converter API](converter-api.md). How the tests check a mapper is on
[Testing](testing.md).

## The path from native file to CIM

```mermaid
flowchart LR
    native["native file"] -->|"FormatReader.read_all()"| records["native records"]
    records -->|"mapper: cell, mrid, lookup, Field"| docs["Document per native table"]
    docs -->|"write_documents"| text[".cimtbl files"]
    text -->|"cimtables.load_model"| cim["cim18v17 model"]
```

`CimtblImporter.to_cim` calls `to_cimtbl` (the mappers, pure) and then
[`cimtbl_to_cim`](#documents-to-cim) (the only step that touches disk and CIM). The file the reviewer reads is the
file the model was built from.

## The invariants, as code

| Invariant | What enforces it |
|---|---|
| I1: CIM is built from the formatted text only | `cimtbl_to_cim` always writes the documents (to `artifact_dir`, or to a temporary directory) and loads the files. There is no path from a `Document` object to CIM. |
| I2: values are copied verbatim, with the unit in the header | `cell` writes the value as text and never converts or rounds. The unit lives in the `Column`. `copied_columns` takes the unit from the `Field`, so each column and unit is stated once. |
| I5: spokes never construct CIM objects | The mapper's output type is `cimtables.document.Document`: text rows, not CIM objects. Only `cimtbl_to_cim` calls `cimtables.load_model`. |
| I8: fail fast | `cell`, `mrid`, `lookup`, `Field`, `copied_columns` and `check_fields` all raise on bad input. IDs are never sanitized: `mrid` keeps the native ID as written and the formatter quotes cells that hold `, ( ) #`. |

## Cell text and identity

### `cell(value) -> str | None`

A native value as the text of one `.cimtbl` cell.

| Input | Output |
|---|---|
| `None` | `None`, a blank cell (unset) |
| `bool` | `"true"` or `"false"` |
| `int` | `str(value)` |
| `float` | `repr(value)`, the shortest text that reads back to the same float |
| `str` | the same text (LinkML `str` subclasses such as `LinecodeName` become plain `str`) |
| LinkML enum value, `PermissibleValue` | its text |

```python
>>> from cimhub_core.cimtbl import cell
>>> cell(None), cell(True), cell(4), cell(0.1 + 0.2), cell("4.160000")
(None, 'true', '4', '0.30000000000000004', '4.160000')
```

A reader that keeps the source text (`'4.160000'`) gets that text in the artifact. `cell` raises `ValueError`
for `nan` and `inf`, and `TypeError` for any other type (`list`, `dict`, ...) with the message
`no .cimtbl cell text for list [1]; map it in the mapper`. A list slot is the mapper's to spread over rows or
columns.

### `mrid(prefix, native_id, *, lowercase=False) -> str`

The mRID of an imported object: the prefix plus the native ID as written. Prefixes follow the
`cimtbl-translate` table (`lc_`, `xc_`, `ld_`, ...). Only the OpenDSS spoke passes `lowercase=True`, because DSS
names are case-insensitive. A missing or blank ID raises `ValueError`.

```python
>>> from cimhub_core.cimtbl import mrid
>>> mrid("lc_", "Mtx601", lowercase=True), mrid("xc_", "XFM1")
('lc_mtx601', 'xc_XFM1')
>>> mrid("lc_", " ")
ValueError: lc_: the native ID is missing (' ')
```

### `phases_cell(phases) -> str | None`

The `phases` cell of a device that is balanced when it has three phases (a load, shunt, source, machine,
inverter, switch). It returns `None` for `"ABC"`, so cimtables writes no per-phase children and no
`Terminal.phases`, and returns `phases` otherwise. A line keeps its phases, because its `ACLineSegmentPhase` order
is the conductor order. `BALANCED_PHASES` is the constant `"ABC"`.

```python
>>> from cimhub_core.cimtbl import phases_cell
>>> phases_cell("ABC"), phases_cell("AB")
(None, 'AB')
```

### `lookup(table, value, *, slot, record_id)`

`table[value]`, or a `ValueError` that names the record, the slot and every known value. Use it for every
native-code-to-CIM-enum table so an unmapped code stops the import.

```python
>>> from cimhub_core.cimtbl import lookup
>>> lookup({"wye": "Y", "delta": "D"}, "star", slot="conn", record_id="t1")
ValueError: t1: conn='star' has no mapping (known: delta, wye)
```

## Classifying native fields

### `Field(kind, targets=(), note="")`

A frozen dataclass: how one native field reaches CIM. A mapper module holds a `FIELDS` dict from every slot name
of its native class to a `Field`. This is invariant I3, and `check_fields` tests it.

| `kind` | Meaning |
|---|---|
| `copied` | The value lands unchanged in a column. The same value goes in every row the record produces for that class. |
| `mapped` | The value goes through an enum or code table (`lookup`). |
| `structural` | The value decides rows: one record becomes several rows, a value belongs to one specific row, or a row goes to another file. |
| `derived` | A named, tested function computes the value, because CIM has no attribute for the source quantity (`b_from_c`). |
| `untranscribed` | No CIM home. The value is recorded in the artifact as a comment. |

`targets` is a tuple of `(cim_class, column, unit)`, one per column the field fills. It is required for `copied`
(`ValueError: a copied Field names its targets`). A builder-native spoke (GDM) names
`(builder_method, keyword, unit)` instead. `note` is free text for the reviewer: the enum table, the formula, the
gap. An unknown `kind` raises `ValueError` listing the five kinds. The constants `FIELD_KINDS` and `FieldKind`
(a `Literal`) hold the same list.

### `copied_columns(fields, cim_class, **unit_words) -> list[tuple[str, Column]]`

`(slot, Column)` for every copied target on `cim_class`, in `fields` order. The mapper writes the columns, then
`cell(getattr(record, slot))` for each pair, so the header and the cells cannot drift apart.

A unit may name a per-record word, such as `"ohm/{length}"`. `unit_words` fills it (`length="km"`). A word left
unfilled raises `KeyError`. Two slots that fill the same column raise `ValueError`: a value that differs per row
(end 1's voltage, end 2's voltage) is `structural`, not `copied`.

```python
>>> from cimhub_opendss.importer.cimtbl.linecode import FIELDS
>>> from cimhub_core.cimtbl import copied_columns
>>> copied_columns(FIELDS, "PerLengthSequenceImpedance", length="km")[:2]
[('name', Column(name='name', unit=None, default=None)), ('r1', Column(name='r', unit='ohm/km', default=None))]
>>> copied_columns(FIELDS, "PerLengthSequenceImpedance")
KeyError: 'length'
```

### `untranscribed_values(fields, record) -> str | None`

The comment text `untranscribed: Slot=value, ...` for one record: every `untranscribed` slot whose value is not
unset (`None`, `""` or `[]`; `0` and `False` count as set). It returns `None` when there is nothing to list. Pass
it as `Row(..., comment=...)` so the reviewer sees every source value that has no CIM home. Lines wrap at 116
characters. A list value is written space-separated.

### `untranscribed_names(fields) -> str | None`

The same comment with slot names only, `untranscribed: Slot, Slot, ...`, once above a table of instances (RAW
uses it above its `TopologicalNode` table).

```python
>>> from cimhub_core.cimtbl import untranscribed_values
>>> untranscribed_values(FIELDS, code)          # code: the mtx601 LineCode
'untranscribed: normamps=730.0'
```

### `check_fields(fields, native_cls) -> None`

Raises `AssertionError` unless `fields` has exactly the slots of `native_cls`. It is the completeness test of
every mapper (`test_classification_is_complete`): it fails on a slot added by a schema regeneration and on a
stale entry.

```python
>>> broken = {**FIELDS, "extra": Field("structural")}
>>> del broken["Kron"]
>>> check_fields(broken, NATIVE_CLASS)
AssertionError: Linecode classification: missing ['Kron'], stale ['extra']
```

### `field_names(native_cls) -> list[str]`

Every field of a native class in declaration order. LinkML dataclasses give their slots, inherited ones
included. Pydantic models (GDM) give `model_fields`. Anything else raises `TypeError`.

## Native defaults

Some formats give a field a default when the deck leaves it blank. The default lives in the native schema as an
annotation (`dss_default`, `raw_default`), and the mapper fills it on purpose, so the artifact shows what was
filled.

### `parse_default(expression)`

A LinkML default expression as a Python value:

```python
>>> from cimhub_core.cimtbl import parse_default
>>> parse_default("float(1.0)"), parse_default("int(3)"), parse_default("string(abc)"), parse_default("true"), parse_default("Deri")
(1.0, 3, 'abc', True, 'Deri')
```

`bool`, `int` and `float` pass through. Text that matches none of the forms is returned as text (an enum value).

### `schema_defaults(native_cls, annotation) -> dict`

`{slot: default}` from a native class's `<fmt>_default` annotations, parsed with `parse_default`. The result is
cached per `(native_cls, annotation)`, so treat it as read-only.

```python
>>> from cimhub_core.cimtbl import schema_defaults
>>> list(schema_defaults(schema.Linecode, "dss_default").items())[:3]
[('nphases', 3), ('r1', 0.058), ('x1', 0.1206)]
```

### `fill_defaults(fields, record, defaults) -> (record, comment)`

Returns a copy of `record` with every unset slot that `fields` classifies and `defaults` names filled in, and the
row comment `defaulted: slot=value, ...` (`None` when nothing was filled). Details:

- `untranscribed` slots are left alone, so a default is never filled for a value that has no CIM home.
- The copy comes from `dataclasses.replace`, so the schema's `__post_init__` types the defaults. The original is
  unchanged.
- Attributes set on the record outside its fields, such as a reader's composite `record.ID`, are carried over.

```python
>>> from cimhub_core.cimtbl import fill_defaults
>>> filled, comment = fill_defaults(FIELDS, code, {"C1": 3.4, "normamps": 400.0, "nphases": 1})
>>> filled.C1, filled.normamps, filled.nphases, comment
(3.4, 730.0, 3, 'defaulted: C1=3.4')
```

`C1` was unset, so it is filled. `nphases` and `normamps` were already set (`normamps` is also untranscribed).

## Skeletons for mapping specs

### `fields_table(native_cls, records=(), *, fields=None, limit=3) -> str`

A markdown table with one row per native field: type, up to `limit` distinct sample values from `records`, and,
when `fields` is given, the kind and the targets. Without `fields` the last two columns are empty, for the person
writing the spec to fill in against the real fields. With a mapper's `FIELDS` the spec table can be regenerated
from the code it describes.

### `fields_stub(native_cls, records=(), *, limit=3) -> str`

Python source for a `FIELDS` dict with one entry per field, each `Field('TODO', note=<samples>)`. `'TODO'` is not
a valid kind, so the stub cannot be imported until each field is classified. `scaffold_mapper` in
[`scaffold.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/src/cimhub_core/scaffold.py)
writes it into a new mapper module.

## Documents to CIM

### `cimtbl_to_cim(documents, *, model_cls=None, network=None, artifact_dir=None, bound_parts=None)`

Writes a `cimtables.document.DocumentSet` and builds CIM from the written files.

| Argument | Effect |
|---|---|
| `documents` | The master plus its parts. The master's `Profile` must be `cim18v17` (`CIM_PROFILE`), or `ValueError`: `master 'm' declares Profile='cim16'; CIMHub artifacts declare 'cim18v17'`. |
| `artifact_dir` | Where the `.cimtbl` files go, the audit artifact. `None` uses a temporary directory that is removed after loading, so an in-memory import and an artifact import cannot differ. |
| `model_cls` | The model class for a new model. `None` lets the master decide (one Feeder gives `FeederModel`). RAW passes `BusBranchModel`. Ignored when `network` is given. |
| `network` | An existing model. The rows are bound onto it and it is returned. This is how several native models merge into one network. |
| `bound_parts` | A function `network -> iterable of Document` for parts that read what binding made (the Terminals a coordinates part locates). Non-empty parts are appended to the master as the last `Import`s, the whole set is written again, and the parts are bound onto the same network. The directory still holds the complete model. |

```python
>>> from cimhub_core.cimtbl import cimtbl_to_cim
>>> from cimhub_core.cimtbl_testing import atom_documents, cim_scope
>>> with cim_scope():
...     network = cimtbl_to_cim(atom_documents(document))
```

`cimtables.load_model` sets the CIM profile and the model scope for the whole process. Tests wrap every load in
`cim_scope()` ([Testing](testing.md#helpers)).

## A mapper end to end

`cimhub_opendss`'s
[`importer/cimtbl/linecode.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/src/cimhub_opendss/importer/cimtbl/linecode.py)
shows every helper in use. Its parts, in the order a mapper is written:

1. `NATIVE_CLASS = schema.Linecode` and `PREFIX = "lc_"`.
2. `FIELDS`: one `Field` per slot of `Linecode`. `r1` is `copied` to `PerLengthSequenceImpedance.r` with the unit
   `"ohm/{length}"`. `C1` is `derived` (`bch = 2 pi f C1`, `b_from_c`). `units` is `mapped`. `rmatrix` is
   `structural` (one `PhaseImpedanceData` row per lower-triangle element). `normamps` is `untranscribed`.
3. A pure function `map_linecode(native, *, base_frequency, length_unit=None) -> Document`. It builds
   `cimtables.document.Table`, `Row` and `Column` objects. It writes columns with `copied_columns`, cells with
   `cell`, the mRID with `mrid(PREFIX, code.name, lowercase=True)`, and the row comment with
   `untranscribed_values`. A code it cannot place raises (`lookup(LENGTH_UNIT, ...)` for the length unit,
   `is_sequence` for a code that sets both a matrix and sequence values).
4. Derived values go through named functions, never inline: `b_from_c` in
   `cimhub_core.derived.capacitance`, `lower_triangle` and `with_default_capacitance` in the module itself.

The same pattern at its smallest, with a native class defined inline. It runs as written:

```python
import dataclasses
from cimtables.document import Column, Document, Row, Table, format_document
from cimhub_core.cimtbl import (CIM_PROFILE, Field, cell, check_fields, cimtbl_to_cim, copied_columns,
                                lookup, mrid, untranscribed_values)
from cimhub_core.cimtbl_testing import atom_documents, cim_scope

@dataclasses.dataclass
class Capacitor:
    name: str
    kvar: float
    kv: float
    conn: str = "wye"
    cost: float | None = None

CONNECTION = {"wye": "Y", "delta": "D"}
FIELDS = {
    "name": Field("copied", (("LinearShuntCompensator", "name", None),), "mRID = cap_ + name"),
    "kvar": Field("copied", (("LinearShuntCompensator", "nomQ", "kVAr"),)),
    "kv": Field("copied", (("LinearShuntCompensator", "nomU", "kV"),)),
    "conn": Field("mapped", note="CONNECTION"),
    "cost": Field("untranscribed", note="no CIM home"),
}

def map_capacitors(records) -> Document:
    copied = copied_columns(FIELDS, "LinearShuntCompensator")
    columns = [Column("mRID"), *(column for _, column in copied), Column("phaseConnection")]
    rows = []
    for record in records:
        cells = [mrid("cap_", record.name), *(cell(getattr(record, slot)) for slot, _ in copied),
                 lookup(CONNECTION, record.conn, slot="conn", record_id=record.name)]
        rows.append(Row(cells, comment=untranscribed_values(FIELDS, record)))
    return Document(name="capacitor", profile=CIM_PROFILE,
                    statements=[Table("LinearShuntCompensator", columns, rows)])

check_fields(FIELDS, Capacitor)
document = map_capacitors([Capacitor("c1", 600, 4.16, cost=12.5), Capacitor("c2", 100, 2.4, "delta")])
print(format_document(document))
with cim_scope():
    network = cimtbl_to_cim(atom_documents(document))
    for cap in network.graph[network.cim.LinearShuntCompensator].values():
        print(cap.mRID, cap.nomQ.to("kVAr"), cap.nomU.to("V"), cap.phaseConnection)
```

It prints:

```text
Profile = cim18v17

Table LinearShuntCompensator: mRID, name, nomQ (kVAr), nomU (kV), phaseConnection
    # untranscribed: cost=12.5
    cap_c1, c1, 600, 4.16, Y
    cap_c2, c2, 100, 2.4,  D

cap_c1 600.0 4160.0 PhaseShuntConnectionKind.Y
cap_c2 100.0 2400.0 PhaseShuntConnectionKind.D
```

The values `600` and `4.16` are the native numbers, and the units are in the header (I2). The model holds 4160 V
because cimtables converted `4.16 kV` while binding. The mapper never multiplied by 1000. `Capacitor("c3", 1, 1,
"star")` raises `c3: conn='star' has no mapping (known: delta, wye)` (I8).

A real spoke adds three things to this: the native reader that produces the records, an orchestrator that lists the
mapper in `MAPPING_ORDER` (catalogs before the instances that use them) and builds the master with its `Import`
statements (see `dss_to_cimtbl.py`), and the atom tests described on [Testing](testing.md).

## Export slots

`export_slots.py` is the export mirror of `Field`. Each exporter module holds a `SLOTS` dict that lists every
slot of its native class, so nothing is dropped without notice. Each spoke's export spec tables are generated from
it.

### `Slot(kind, note="")`

A `NamedTuple`. `kind` is one of `KINDS`:

| `kind` | Meaning |
|---|---|
| `written` | The value comes from a getter. |
| `rule` | A CIM `None` that the native format needs, so the exporter writes a rule's value. |
| `unset` | CIM cannot hold it, so the format's own default applies. |
| `not mapped` | A different form of the same data is written instead. |

### `check_slots(slots, native_class) -> None`

Raises `ValueError` unless `slots` lists exactly the dataclass fields of `native_class`, each with a kind in
`KINDS`:

```python
>>> check_slots({**slots, "bogus": Slot("written")}, Native)
ValueError: Native SLOTS: missing [], not slots ['bogus']
>>> check_slots({**slots, "pf": Slot("guess")}, Native)
ValueError: Native SLOTS: unknown kinds {'pf': 'guess'}
```

### `with_default(native_class, written, other) -> dict[str, Slot]`

`written` plus every other slot of `native_class` as `other`, in the schema's order. An exporter lists the slots
it writes and defaults the rest in one line:

```python
SLOTS = with_default(Native, {"name": Slot("written", "name"), "kw": Slot("written", "p")},
                     Slot("unset", "format default applies"))
```

### `slots_table(slots, format_name) -> str`

The spec's markdown table, headed `<format_name> slot | kind | from / why`:

```text
| Demo slot | kind | from / why |
|---|---|---|
| name | written | name |
| kw | written | p |
| pf | unset | format default applies |
```

`check_slots` takes dataclass fields only. GDM is pydantic-based and keeps its own `check_slots` in
`cimhub_gdm.exporter.slots`.

## Shared load models

### `zip_fractions() -> Document`

`zip_fractions.cimtbl`: three fixed `LoadResponseCharacteristic` rows with `exponentModel` false. The same
fractions apply to p and q.

| mRID (constant) | p/q constant power | constant current | constant impedance |
|---|---|---|---|
| `zip_constant_pq` (`ZIP_CONSTANT_PQ`) | 1 | 0 | 0 |
| `zip_constant_z` (`ZIP_CONSTANT_Z`) | 0 | 0 | 1 |
| `zip_constant_i` (`ZIP_CONSTANT_I`) | 0 | 1 | 0 |

The OpenDSS and GridLAB-D importers include the document in their master. A load names a row by its mRID. A
spoke writes its exponential models (`exp_<p>_<q>`) in its own load file, before the loads that name them. The
rows are the same as those in the `common` shape ([Canonical shapes](shapes.md#common)), and
`cimhub_core/tests/test_shapes.py` checks they stay equal.
