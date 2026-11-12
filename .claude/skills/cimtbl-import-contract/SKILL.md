---
name: cimtbl-import-contract
description: The inbound contract native → `.cimtbl` → cim18v17 - invariants I1-I9, `CimtblImporter.to_cimtbl`, `cimtbl_to_cim`, the mapper module layout, `Field` classification, mRIDs and provenance headers. Use when writing or reviewing a spoke importer, a mapper under `importer/cimtbl/`, or the `cimhub_core.cimtbl` helpers.
---

# `.cimtbl` import contract

A spoke importer only *maps* native records to `.cimtbl` rows, in the source's own units. cimtables builds the CIM.

```
<Fmt>Reader(path).read_all()            -> SpokeGraphModel   LinkML dataclasses       spoke reader
<Fmt>Importer().to_cimtbl(native)       -> DocumentSet       pure, no I/O, no CIM     spoke mappers
cimtables.document.write_documents(...) -> <dir>/*.cimtbl    the filesystem boundary  cimtables
cimtables.load_model(master)            -> GraphModel        rows -> bind_row         cimtables
<Fmt>Importer().bound_parts(native, network) -> [Document]   reads the bound network  spoke mappers (optional)
```

`CimtblImporter.to_cim` composes the steps through `cimhub_core.cimtbl.cimtbl_to_cim`. `bound_parts` is only for a
part that needs what binding made, chiefly the Terminals (DSS `buscoords.cimtbl` locates each piece of equipment at
its Terminals' buses). Its parts are written beside the rest, imported last, and bound onto the same network, so the
artifact directory stays the complete model. Never re-derive Terminals from document text: a `.cimtbl` means what
binding makes (CIM-Tables declined that inverse, U11).
Profile: **cim18v17 only** (`cimhub_core.cimtbl.CIM_PROFILE`). No other profile is imported anywhere.

## Invariants (check every change against these)

| # | Rule |
|---|---|
| I1 | **The artifact is the only input to CIM.** CIM is built from the written `.cimtbl` text (the caller's `artifact_dir`, or a temp dir), never from the mapper's objects. |
| I2 | **Value-verbatim, source units.** Every copied number is the source value, with the source unit in the header: `ratedS (kVA)`, `r (ohm/mi)`. No unit conversion in spoke code. |
| I3 | **Every field is classified** as exactly one of copied / mapped / structural / derived / untranscribed. A test checks the classification covers every slot of the LinkML class. |
| I4 | **One artifact file per native table.** The master `Import`s them in dependency order: catalogs before instances. |
| I5 | **Spokes never construct CIM objects.** No `cim.X(...)`, no `z_base`, no Terminals in spoke importer code. cimtables (or CIM-Builder) constructs. |
| I6 | **CIM 18 templates, never `*Info` catalogs.** `TransformerTankConfiguration`, `WireConfiguration`, `XYSpacing(isTemplate)`, `PerLengthImpedance`, the `WireInfo` family. `WireSpacingInfo` does not exist. |
| I7 | **Four-ABC filesystem rule.** Mappers are pure (objects in, documents out). Only readers and writers touch the disk. |
| I8 | **Fail fast.** Unknown fields, unmapped codes, unresolved references and untypeable cell text raise. IDs with `# ( ) ,` are quoted, never sanitized. Nothing is dropped silently. |
| I9 | **Upstream first.** Core holds only what no upstream library provides. Check cimtables (`graph_write.set_attr`/`get_qty`, `impedance.z_base`, `diff_models`, `document.*`, `load_model`), cimbuilder, cimgraph, cimprofiles (units, identity) and cim-topology first. Missing upstream? File it in that repo's requests doc (`.development/UPSTREAM_REQUESTS.md`). Never write a local stand-in. |

## Topology (before any artifact)

Spanning trees, islands, voltage zones, sorting and BaseVoltage assignment come from `cimtopology.core`.
It is format-agnostic and runs before any CIM exists. The spoke translates its own records into
`Network(sources, branches, transformers, nodes)`, using `Source`, `Branch` and `Transformer` with one `Coil` per
winding. Equipment names must be unique, so prefix by class. The orchestrator then calls `walk(network)` (bus →
`BusSystem`, which carries the BaseVoltage mRID) or `Topology(network)` (`islands()`, `voltage_zones()`, `sort()`,
`gaps()`). Format-only parsing, such as DSS `bus.1.2.3` node suffixes, stays in the spoke. Never write a
local graph walk or union-find.

## Layout

```
cimhub_<fmt>/src/cimhub_<fmt>/importer/
    <fmt>_to_cimtbl.py        # MAPPING_ORDER, the CimtblImporter subclass, <fmt>_to_cim()
    cimtbl/
        <native_table>.py     # NATIVE_CLASS, PREFIX, FIELDS, map_<native_table>(), derived functions
cimhub_<fmt>/docs/CIMTBL_MAPPING.md   # the approved spec (skill cimtbl-mapping-spec)
```

`cimhub_core.scaffold.scaffold_mapper(format_name, native_cls, prefix=..., table_name=..., records=...)` writes the
mapper and test stubs for one native table. Its `FIELDS` entries are `Field('TODO')`, which does not import until
every field is classified.

## The importer

```python
# cimhub_opendss/src/cimhub_opendss/importer/dss_to_cimtbl.py
MAPPING_ORDER = [map_linecode, ..., map_transformer]   # = the master's Import order

class DssImporter(CimtblImporter):
    def to_cimtbl(self, model: SpokeGraphModel) -> DocumentSet:
        parts = [part for part in (mapper(model) for mapper in MAPPING_ORDER) if part.statements]
        # map_master: the spoke's master document (containers, BaseVoltages, then one Import per part)
        return DocumentSet(master=map_master(model, parts), parts=parts)

def dss_to_cim(model, *, name, artifact_dir=None):   # a parsed model, never a path (I7)
    return DssImporter(name).to_cim(model, artifact_dir=artifact_dir)
```

- `CimtblImporter.model_cls`: `None` (the master's one Feeder or Substation decides) for distribution formats;
  `BusBranchModel` for RAW and MATPOWER.
- `to_cim(model, *, network=None, artifact_dir=None)`: pass `network` to bind several native models onto one network.
- `bound_parts(model, network) -> list[Document]` (default none): parts mapped from the bound network; they read
  it, never construct on it (I5). DSS: `[buscoords.map_buscoords(model, network)]`.
- A native table with no records yields an empty document: no file, no `Import`.
- No `try`/`except` around mappers. The first failure stops the import with its context.
- Builder-native spokes (GDM) subclass `FormatImporter` directly and have no `to_cimtbl` (reference.md).

## A mapper module

```python
NATIVE_CLASS = schema.Linecode
PREFIX = "lc_"
FIELDS = {"name": Field("copied", (("PerLengthPhaseImpedance", "name", None),)), ...}  # every slot

def map_linecode(native) -> Document:
    codes = native.list_by_class(NATIVE_CLASS)
    ...
    return Document(name="linecode", statements=statements, profile=CIM_PROFILE, comment=provenance)
```

- Signature: `map_<native_table>(native: SpokeGraphModel, ...) -> Document`. It reads the whole native graph and
  mutates nothing. Inputs the orchestrator computes (the `BusSystem`s from `cimtopology.core.walk`, the container mRID) are explicit
  arguments: `map_transformer(native, buses, container)`. No module globals.
- `Document.name` is the artifact stem (D4) = the LinkML schema module of the native class: `linecode`.
- Every document passes `profile=CIM_PROFILE`; `cimtbl_to_cim` rejects a master without it.

## Field classification (I3)

| kind | meaning | how it is emitted |
|---|---|---|
| `copied` | same value in every row the record produces for that class | `Field('copied', ((cim_class, column, unit), ...))`; `copied_columns(FIELDS, cim_class, length='mi')` returns `(slot, Column)` pairs; cell = `cell(getattr(record, slot))` |
| `mapped` | through a code table | `lookup(TABLE, value, slot=..., record_id=...)`; plain dict, raises on an unknown value |
| `structural` | decides rows: one record → several rows, a value on one specific row, a row in another file | mapper code, per the spec |
| `derived` | computed because CIM has no attribute for the source quantity | a named, pure, unit-tested function (`b_from_c(c, f)`); the table comment states formula and input slots |
| `untranscribed` | no CIM home | D5 comment (below); `note` says why |

A value that lands on one row only (end 1's kV, end 2's kV) is **structural**, not copied: `copied_columns` raises if
two slots fill one column. A per-record unit is a template, `ohm/{length}`, filled by `copied_columns(..., length=)`.
A derived function moves to core only when two spokes need it.

`check_fields(FIELDS, NATIVE_CLASS)` raises unless `FIELDS` holds exactly the class's fields (new slot or stale entry).

## Decisions

- **D2 value-verbatim:** `cell(value)` gives the cell text. Floats are `repr()` (`500.001020` → `500.00102`), bools
  `true`/`false`, enums their text, strings unchanged. It never converts or rounds; NaN/inf and lists raise.
- **D3 identity:** `mrid(prefix, native_id, *, lowercase=False)`. Prefixes are the `cimtbl-translate` prefix table
  (`lc_`, `ln_`, `xf_`, `xc_` ...). Source case kept; only OpenDSS passes `lowercase=True`. `name` = the native ID.
  Child rows extend the parent (`<xf>_tank`, `<xc>_wdg_1`). Terminals `<eq>_T<n>` and phase children `<mRID>_<phase>`
  are generated by the loader: reference them, never write them. Identity-only classes (`PhaseImpedanceData`) write
  an `identifier` column `<parent>_<row><column>`.
- **D4 one file per native table.** Templates a spoke synthesizes go in the file of the native table that induced
  them, under a `# synthesized: ...` comment.
- **D5 untranscribed:** catalogs put `untranscribed_values(FIELDS, record)` on each row's comment
  (`# untranscribed: Slot=value, ...`). Instance tables put `untranscribed_names(FIELDS)` once on the table comment.

## Provenance header

Deterministic, no dates or versions. Parts name the native table, the record count and the spec anchor. The source
file name goes in the master only, so an atom and a full model produce the same part text:

```
# OpenDSS LineCode -> PerLengthPhaseImpedance + PhaseImpedanceData, PerLengthSequenceImpedance (catalog).
# Source table: LineCode (records: 1)
# Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#linecode
```

## Anti-patterns

- `cim.ACLineSegment(...)`, `get_or_create_*`, terminal wiring or `z_base` in a spoke importer (I5).
- `float(value) * 1000`, `.to('W')`, or `Qty(...)` in a mapper: write the source unit in the header (I2).
- Building CIM from the mapper's objects, or a "fast path" that skips writing text (I1).
- `clean_cim_name(...)` or any sanitizing of mRIDs (I8). Quoting is the formatter's job.
- A `.get(value, default)` on a code table instead of `lookup` (I8).
- Hand-computed derived values pasted into code or goldens; Carson's equations producing a `PerLengthPhaseImpedance`
  for a line that has geometry (skill `conductor-geometry`).
- `WireSpacingInfo`, `TransformerTankInfo`, `TransformerEndInfo`, `ShortCircuitTest` as network templates (I6).
- A local helper that duplicates cimtables/cimbuilder/cimprofiles (I9).

Details (helper signatures, document model, formatter rules, fail-fast table, GDM exception): [reference.md](reference.md).
Related skills: `cimtbl-shapes`, `cimtbl-mapping-spec`, `atom-tests`, `cim-units`, `conductor-geometry`.
