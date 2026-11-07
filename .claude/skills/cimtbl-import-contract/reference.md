# `.cimtbl` import contract: reference

Companion to [SKILL.md](SKILL.md). Every name below exists in `cimhub_core` or cimtables; check the source before
relying on a detail that is not listed here.

## 1. Who owns what

| lives in | what |
|---|---|
| **cimtables** (format owner) | `cimtables.document` (document model, `format_document`, `write_documents`), parser, validation, `bind_row`, `load`, `load_model`, `graph_write.set_attr`/`get_qty`, `impedance.z_base`, `diff_models` |
| **cimhub_core** | `cimhub_core.cimtbl`, `cimhub_core.base` (`FormatImporter`, `CimtblImporter`), `cimhub_core.cimtbl_testing`, `cimhub_core.scaffold`, `cimhub_core.topology` (native bus graph), `cimhub_core.codes` (shared code tables), the shapes in `cimhub_core/src/cimhub_core/shapes/` |
| **spoke** | mapper modules, format-only code tables, derived-value functions, `MAPPING_ORDER`, `docs/CIMTBL_MAPPING.md` |

A core change a spoke session needs goes back to the core owner. A missing upstream capability goes to that repo's
requests doc (I9).

## 2. `cimhub_core.cimtbl`

| name | signature | does |
|---|---|---|
| `CIM_PROFILE` | `"cim18v17"` | the one profile every document declares |
| `Field` | `Field(kind, targets=(), note="")`, frozen | rejects an unknown kind and a `copied` field without targets |
| `cell` | `cell(value) -> str \| None` | D2 cell text (table in §4) |
| `mrid` | `mrid(prefix, native_id, *, lowercase=False) -> str` | D3; raises on a missing or blank ID |
| `lookup` | `lookup(table, value, *, slot, record_id)` | `table[value]`, else `ValueError` with record ID, slot, value and the known keys |
| `copied_columns` | `copied_columns(fields, cim_class, **unit_words) -> list[(slot, Column)]` | copied targets on one class, in `FIELDS` order; fills `{length}`-style unit words; raises on a column filled from two slots, `KeyError` on an unfilled word |
| `untranscribed_values` | `untranscribed_values(fields, record) -> str \| None` | D5 catalog row comment, non-empty values only, wrapped at 116 columns |
| `untranscribed_names` | `untranscribed_names(fields) -> str \| None` | D5 instance table comment |
| `field_names` | `field_names(native_cls) -> list[str]` | LinkML dataclass fields or pydantic `model_fields` |
| `check_fields` | `check_fields(fields, native_cls) -> None` | `AssertionError` naming missing and stale slots |
| `fields_table` | `fields_table(native_cls, records=(), *, fields=None, limit=3) -> str` | markdown classification table with samples; fills kind/target from `fields` |
| `fields_stub` | `fields_stub(native_cls, records=(), *, limit=3) -> str` | Python source of a `FIELDS` dict of `Field('TODO', note=<samples>)` |
| `cimtbl_to_cim` | `cimtbl_to_cim(documents, *, model_cls=None, network=None, artifact_dir=None)` | checks the master's profile, writes the documents (to `artifact_dir` or a temp dir), then `cimtables.load_model(master, model_cls=)` or `cimtables.load(master, network)` and returns the network |

`cimhub_core.scaffold.scaffold_mapper(format_name, native_cls, *, prefix, table_name=None, records=(), parent_dir=".")`
writes `importer/cimtbl/<table>.py` and `tests/test_cimtbl_<table>.py`; it never overwrites.

## 3. `cimhub_core.base`

```python
class FormatImporter(ABC):            # builder-native spokes (GDM) implement to_cim directly
    model_cls: type
    @abstractmethod
    def to_cim(self, model, *, network=None) -> CIMGraphModel: ...

class CimtblImporter(FormatImporter):  # every file-format spoke
    model_cls: type | None = None       # None: the master's Feeder/Substation decides; BusBranchModel for RAW, MATPOWER
    @abstractmethod
    def to_cimtbl(self, model) -> DocumentSet: ...          # pure: no I/O, no CIM objects (I5, I7)
    def to_cim(self, model, *, network=None, artifact_dir=None):
        return cimtbl_to_cim(self.to_cimtbl(model), model_cls=self.model_cls,
                             network=network, artifact_dir=artifact_dir)
```

## 4. Typed value → cell text (`cell`)

| value | text |
|---|---|
| `None` | `None`: a blank cell (unset) |
| `bool` (checked before `int`) | `true` / `false` |
| `int` | `str(value)` |
| `float` | `repr(value)`, the shortest text that reads back to the same float; NaN/inf raise `ValueError` |
| `str` | unchanged; a reader that keeps source text puts that text in the artifact |
| LinkML enum | its permissible-value text |
| anything else (a list) | `TypeError`: the mapper expands it (a DSS matrix → one row per element) |

## 5. Document model (`cimtables.document`)

```python
Column(name, unit=None, default=None)          # header 'name (unit)=default'; unit may carry a base word: 'pu system'
Row(cells, comment=None)                       # one cell per column; None = blank, '' = quoted empty string
Table(cim_class, columns, rows, comment=None)
ObjectStatement(cim_class, cells, comment=None) # cells: list[(Column, text)]
Import(name)                                   # stem of another document in the set
Document(name, statements, profile=None, authority=None, model=None, comment=None)
DocumentSet(master, parts)                     # each part imported exactly once, in Import order
```

- `name` is a stem; the file is `<name>.cimtbl`. CIMHub always passes `profile=CIM_PROFILE`.
- `Import` sits inside `statements` because position matters: the master declares containers and BaseVoltages,
  then imports the parts that use them.
- `format_document(document) -> str` is deterministic: comment, settings, statements separated by blank lines; rows
  indented 4 spaces and padded per column; a cell is quoted when it holds `, ( ) # "`, has edge whitespace, is `''`,
  or reads as a statement start. A newline in a cell raises; a newline in a comment becomes several `# ` lines.
- `write_documents(documents, directory) -> Path` writes master + parts and returns the master path. It raises on
  an `Import` with no part and on a part never imported.

## 6. Artifact conventions

- **Layout:** `<artifact_dir>/<Model>.cimtbl` (master) plus one `<native_table>.cimtbl` per non-empty native table.
- **Settings:** parts declare only `Profile = cim18v17`. The master declares `Profile`, `Authority`, `Model`
  (D7 open; recommendation: `Model` = the source file stem).
- **Provenance header:** parts name the native table, record count and spec anchor
  `cimhub_<fmt>/docs/CIMTBL_MAPPING.md#<native_table>`; only the master names the source file.
- **Derived values:** a table comment with the formula and the input slots
  (`# derived: b = 2 pi baseFreq C (b_from_c), from cmatrix (nF) -> nS`).
- **Defaults the format applies:** listed on the row comment (`# defaulted: ...`) so the reviewer sees them.
- **Synthesized templates:** in the inducing table's file, under `# synthesized: ...`.
- **Untranscribed:** D5 (catalog values per row, instance names per table).

## 7. Fail-fast rules

| condition | caught by | raises |
|---|---|---|
| native slot missing from `FIELDS`, or a stale entry | `check_fields` in the completeness test | `AssertionError` |
| unmapped code value | `lookup` | `ValueError`: record ID, slot, value, known values |
| missing required native value (name, bus, node) | mapper | `ValueError` naming the record |
| reference to a catalog entry that does not exist | mapper | `ValueError` naming both IDs (clearer than the bind error) |
| NaN/inf, a list, a newline in a cell | `cell()` / formatter | `ValueError` / `TypeError` |
| `Import` without a part, or a part never imported | `write_documents` | `ValueError` |
| master without `Profile = cim18v17` | `cimtbl_to_cim` | `ValueError` |
| bad column, unit or base word; unresolved reference; duplicate mRID | cimtables at bind | `CimtblValidationError` / `CimtblBindError` / `ValueError`, with the artifact's file:line |

References resolve immediately, so the artifact order must be topological. The orchestrator owns that order; a
forward reference fails at bind time.

## 8. Decisions (full text)

- **D1. Rows bind only through `bind_row`.** `cimtables.load*` and CIM-Builder's `ObjectBuilder.from_table(row)` call
  the same function. Builder keyword methods are not on the import path of file-format spokes; they are the parity
  oracle in CIM-Builder's tests.
- **D2. Value-verbatim from LinkML.** A cell is the `repr()` of the reader's typed value; readers stay as they are.
  A reader that keeps text keeps text; both bind identically.
- **D3. mRID = prefix + native ID in source case; OpenDSS lowercased.** Quoted cells carry `# ( ) ,`.
- **D4. One file per native table** (`linecode.cimtbl`, `transformer.cimtbl`); the stem is the LinkML schema module
  of the native class. Synthesized templates stay in the inducing table's file.
- **D5. Untranscribed fields** (default, not yet confirmed): catalogs list non-empty values per row, instance tables
  list field names once.
- **D13. cim18v17 is the only profile** on every route. CIM 17/16 output, if needed, is a separate down-converting
  spoke.

## 9. Builder-native spokes (GDM)

GDM's native model is a live pydantic `DistributionSystem` with pint quantities and no file format, so it builds CIM
through CIM-Builder keyword methods (D11). I1 and I4 do not apply; I2, I3, I5, I6, I8 and I9 do.

- `GdmImporter(FormatImporter)` implements `to_cim(system, *, network=None)` with builder calls; no `to_cimtbl`.
- Units: each quantity goes to the builder as `Qty(quantity.magnitude, unit)` in its own unit; no `.to()` in the spoke.
  A unit spelling cimprofiles does not parse goes through a mapping table and is reported upstream.
- `FIELDS` is keyed by `model_fields`; `Field.targets` name `(builder_method, keyword, unit)`. `check_fields` works on
  pydantic classes.
- mRID = `mrid(prefix, gdm_name)`; GDM's `uuid` is not the mRID.
- GDM `*Equipment` classes are catalogs → CIM 18 templates; components are instances referencing them.
- Tests compare the built model with a reviewed `.cimtbl` golden: `cimtables.diff_models(golden, built) == []`.
- The builders belong to the user: the GDM session lists builder gaps, it does not write builders.
