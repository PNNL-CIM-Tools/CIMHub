---
name: reader-writer
description: The four-ABC converter contract (FormatReader, FormatWriter, CimtblImporter/FormatImporter, FormatExporter) - "objects in, objects out; only readers and writers touch the filesystem" - and how to build a schema-driven native reader and writer. Use when writing or editing a reader, writer, importer or exporter class, a `<fmt>_to_cim` / `cim_to_<fmt>` entry point, or their round-trip tests.
---

# Readers, writers and the four-ABC contract

> **Objects in, objects out. Only readers and writers touch the filesystem.**

```python
native  = DssReader("Master.dss").read_all()      # parse    file → native GraphModel
feeder  = DssImporter("Master").to_cim(native)    # convert  native → .cimtbl documents → cim18v17 model
out     = DssExporter().to_model(feeder)          # convert  cim18v17 model → native GraphModel
DssWriter().write(out, "out_dir")                 # persist  native GraphModel → file(s)
```

Each stage can be inspected on its own. A wrong export shows up in `out` before it is written, so you can tell a
converter bug from a writer bug. The ABCs are in `cimhub_core/src/cimhub_core/base.py`; the native
`GraphModel` (`{schema_class: {identifier: instance}}`) is in `cimhub_core/src/cimhub_core/graph_model.py`.

## The contract

| ABC | Method | Takes | Returns | File I/O |
|---|---|---|---|---|
| `FormatReader` | `__init__(source)`, `read_all()` | source bound once at construction | native `GraphModel` | reads |
| `FormatWriter` | `write(model, destination)`, `serialize(obj)` | the same native `GraphModel` | `None` / `str` | writes |
| `CimtblImporter` | `to_cimtbl(model)` (abstract), `bound_parts(model, network)`, `to_cim(model, *, network=None, artifact_dir=None)` | native `GraphModel` | `DocumentSet` / cim18v17 cimgraph model | none in `to_cimtbl` |
| `FormatExporter` | `to_model(network, **opts)` | cimgraph model | native `GraphModel` | none |

Rules:

1. **The reader binds its source in `__init__` and never takes it again.** `__init__` doesn't parse. `read_all()`
   takes no arguments, parses the whole source and returns one `GraphModel`. There is no per-class read method.
2. **The writer takes the reader's `GraphModel`**, not a flat list, because one-file-per-class and section formats
   need the grouping. `serialize(obj)` is the primitive; `write` is built on it. Iterate with
   `model.iter_all()` or `model.list_by_class(cls)`. Never iterate `model.graph[cls]` directly: that yields
   identifier strings.
3. **Importers take a parsed model, never a path.** File importers subclass `CimtblImporter` and implement only
   `to_cimtbl`, a pure mapping to documents (invariants I1, I5, I7; see the `cimtbl-import-contract` skill).
   `to_cim` writes the artifact and builds CIM from the written text. Pass `network=` to merge several native
   models; `model_cls` picks the cimgraph model (`BusBranchModel` for RAW and MATPOWER).
4. **Exporters take a network, never a path,** and return a native `GraphModel` of schema dataclasses, so the output
   can go straight back through the importer. No `destination` argument. Reads go through the export getters
   (`export-getters` skill).
5. **Thin public functions:** `<fmt>_to_cim(model, *, network=None)` calls the importer;
   `cim_to_<fmt>(network, destination, **opts)` calls `to_model` then the writer. Class names are
   `{Fmt}Reader`, `{Fmt}Writer`, `{Fmt}Importer`, `{Fmt}Exporter`.
6. **No converter returns text.** If an exporter wants to emit a raw command string, add the missing schema
   dataclass instead. Create-vs-modify distinctions (DSS `Edit Vsource.source` after `New Circuit`) belong in the
   writer's `serialize`, keyed off a schema field.
7. **GDM is the one exemption.** It has no file format, so its importer is builder-native and subclasses
   `FormatImporter` directly.

## Reader rules

- **The schema drives parsing.** Field order comes from the `order` annotations (`get_field_order`,
  `get_schema_annotations` in `cimhub_core/src/cimhub_core/serialization.py`), types from the dataclass. Don't
  hard-code field lists.
- **Deterministic identifiers.** Each class has an `identifier: true` field. Assign composite identifiers (RAW
  branch `from-to-ckt`) before `add_to_graph`. On a collision `add_to_graph` keeps the first object and logs a
  warning. Treat that warning as a bug.
- **Keep values as the source wrote them.** No unit conversion and no rounding in the reader (`cim-units` skill).
  Resolve native-only conveniences (DSS `like=`, redirects, continuation lines) here, in the reader.
- **Fail fast with location.** Raise a format-specific parse error with file, line number and the line text. No
  `print` warnings, and never skip a line you can't parse.
- **Missing optional fields** are left unset. Positional formats get the schema's `ifabsent` default; keyword
  formats (DSS, GLM) stay unset and the mapper fills them from the `<fmt>_default` annotation
  (`linkml-native-schema` rule 5). Don't invent values, and never clamp or replace a value the file gave.
- **Apply commands in file order** where the format has them (DSS `New`/`Edit`/`like=`/`BatchEdit`), with the
  format's own semantics; an edit of an object not yet defined raises.

## Writer rules

- **Annotations drive output.** Use `AnnotationSerializer` (positional and fixed-width formats such as RAW,
  MATPOWER) or a format serializer that reads the same annotations (DSS `key=value`, GLM). Never hand-code
  f-strings per class. If a field formats wrongly, fix its annotations.
- **Section and file order** is a class-level list in the writer (RAW section order, DSS master command order).
- **Create output directories** as needed. Write UTF-8.

## Tests (in `cimhub_<fmt>/tests/`)

- Reader: a small fixture file → expected objects and counts; comments and blank lines skipped; a bad line raises
  with its line number.
- Writer: `serialize(obj)` equals the exact expected text, defaults included.
- Round trip: read → write (`tmp_path`) → read gives equal objects per class; byte-identical where the format
  allows.
- Contract: `issubclass` checks against the ABCs; the importer and exporter take objects, not paths.

Skeletons, parsing strategies and test templates are in [reference.md](reference.md).

## Anti-patterns

| Don't | Do |
|---|---|
| `reader.read(path, schema.Bus)` | `Reader(path).read_all().list_by_class(schema.Bus)` |
| `dss_to_cim("Master.dss")` | `dss_to_cim(DssReader("Master.dss").read_all())` |
| an exporter that writes files or takes `destination` | `to_model(network)` + the writer |
| `writer.write(list_of_objects, path)` | `writer.write(model, path)` |
| `f"{bus.number},'{bus.name}',{bus.kv:.5f}"` | `self.serializer.serialize(bus)` |
| `except Exception: continue` while parsing | raise a parse error with file and line |
| identifiers from `id(obj)` or row order | `identifier: true` + a deterministic composite key |
