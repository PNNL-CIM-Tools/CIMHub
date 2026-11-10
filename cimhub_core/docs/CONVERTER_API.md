# Converter API

This is the public API every CIMHub package presents: how to get from a native file to a cim18v17 model and back.
It covers the four base classes in `cimhub_core`, the one-call functions each package exports, and how a new
package starts. For how the pieces fit together see [ARCHITECTURE.md](ARCHITECTURE.md). For the rules a contributor
(or Claude) follows when writing a converter, see the
[`reader-writer` skill](../../.claude/skills/reader-writer/SKILL.md).

## The rule

> Objects in, objects out. Only readers and writers touch the filesystem.

A conversion is four steps, and each one returns something you can inspect:

```python
native  = DssReader("Master.dss").read_all()          # parse    file -> native GraphModel
network = dss_to_cim(native, name="Master")            # convert  native -> .cimtbl documents -> cim18v17
out     = DssExporter().to_model(network)              # convert  cim18v17 -> native GraphModel
DssWriter().write(out, "out.dss")                      # persist  native GraphModel -> file
```

When an export is wrong, look at `out` before it is written. A bad `out` is a converter bug; a bad file from a good
`out` is a writer bug.

## The base classes

Reader, writer, importer and exporter are the four roles; the importer has two base classes. They are in
`cimhub_core/base.py` and exported from `cimhub_core`.

| Class | Methods | Takes | Returns | Disk |
|---|---|---|---|---|
| `FormatReader` | `__init__(source)`, `read_all()` | source, bound once at construction | native `GraphModel` | reads |
| `FormatWriter` | `write(model, destination)`, `serialize(obj)` | native `GraphModel` | `None`, `str` | writes |
| `CimtblImporter` | `to_cimtbl(model)`, `bound_parts(model, network)`, `to_cim(model, *, network=None, artifact_dir=None)` | native `GraphModel` | `DocumentSet`, list of `Document`, cim18v17 model | none |
| `FormatImporter` | `to_cim(model, *, network=None)` | native model | cim18v17 model | none |
| `FormatExporter` | `to_model(network, **opts)` | cim18v17 model | native `GraphModel` | none |

Points that matter to a caller:

- **A reader binds its source in `__init__` and parses in `read_all()`.** Constructing a reader is cheap. There is no
  per-class read method; one call returns the whole model.
- **A writer takes the reader's `GraphModel`.** `serialize(obj)` renders one object; `write` persists the model.
  Single-file formats take a file path as `destination`; formats with one file per class take a directory.
- **An importer takes a parsed model, never a path.** `CimtblImporter` is for file formats: the spoke implements
  `to_cimtbl`, a pure mapping to `.cimtbl` documents, and `to_cim` writes them and builds CIM from the written text.
  `FormatImporter` is the base for a spoke with no file format (GDM builds CIM through CIM-Builder directly).
- **`bound_parts` is optional.** A spoke overrides it only for a part that reads the Terminals binding made, such
  as OpenDSS bus coordinates. It returns `[]` by default.
- **An exporter takes a network and returns a native model.** It has no `destination` argument and never writes.
  Options such as `name_source` go to `to_model(**opts)`.
- **No converter returns text.** The native `GraphModel` holds schema dataclasses, so export output can go straight
  back through the importer in a round-trip test.

The contract for importers (what a mapper may and may not do) is the
[`cimtbl-import-contract` skill](../../.claude/skills/cimtbl-import-contract/SKILL.md). The contract for exporters
(reading CIM through the core getters) is the [`export-getters` skill](../../.claude/skills/export-getters/SKILL.md).

## GraphModel

`cimhub_core.GraphModel` is the native store: `{schema_class: {identifier: instance}}`. Readers and exporters
return one; writers and importers take one. It is not a cimgraph model. Every class has an `identifier` field, and
adding a second object with the same identifier to a class raises `ValueError`.

| Method | Use |
|---|---|
| `add_to_graph(obj)` | insert an object under its identifier |
| `GraphModel.from_objects(objects)` | build from a flat iterable |
| `list_by_class(cls)` / `iter_by_class(cls)` | all objects of one class |
| `iter_all()` | every object, grouped by class |
| `first(cls)`, `find_by_attribute(cls, attribute, value)` | lookup |
| `count(cls)`, `len(model)`, `cls in model` | size and membership |

Iterate with `list_by_class` or `iter_all`. Iterating `model.graph[cls]` directly yields identifier strings, not
objects.

## One-call functions

Each package wraps the classes above in thin functions. The functions take objects, not paths, so a reader always
comes first.

| Package | Import | Export | Reader / writer |
|---|---|---|---|
| `cimhub_opendss` | `dss_to_cim(model, *, name, authority=..., length_unit=None, network=None, artifact_dir=None)` | `cim_to_dss(network, destination, **opts)` | `DssReader(path)`, `DssWriter()` |
| `cimhub_gdm` | `gdm_to_cim(system)` | `cim_to_gdm(network, destination, **opts)` | `read_gdm(path)`, `write_gdm(system, path)` |
| `cimhub_raw` | `raw_to_cim(model, *, name, authority=..., network=None, artifact_dir=None)` | none yet | `Raw34Reader(path)`, `Raw34Writer()` |

Notes per package:

- **OpenDSS.** All names are exported from `cimhub_opendss`: `DssReader`, `DssWriter`, `DssImporter`,
  `DssExporter`, `DssModel`, `DssParseError`, `dss_to_cim`, `cim_to_dss`. `name` is the master's `Model` and the
  file stem; use the deck's name. `length_unit` is the per-length unit for line codes that carry none.
  `cim_to_dss` writes a single `.dss` file and passes `**opts` to `DssExporter.to_model`.
- **GDM.** GDM has no file format of its own, so the "native model" is a grid-data-models `DistributionSystem` and
  `read_gdm` / `write_gdm` are its JSON load and save. `GdmImporter` subclasses `FormatImporter`, builds its own
  network, and raises if you pass `network=`. `GdmExporter.to_model` takes `name_source` and `system_name`. It
  logs a WARNING when it fills required GDM fields that CIM cannot hold (see
  [EXPORT_PLAN.md](../../cimhub_gdm/docs/EXPORT_PLAN.md)).
- **RAW.** `cimhub_raw` has no names in its `__init__.py`; import from the modules:
  `cimhub_raw.raw34_reader.Raw34Reader`, `cimhub_raw.raw34_writer.Raw34Writer`,
  `cimhub_raw.importer.raw_to_cimtbl.RawImporter` and `raw_to_cim`. The importer produces a `BusBranchModel`.
  There is no RAW exporter yet. The mapping is in [CIMTBL_MAPPING.md](../../cimhub_raw/docs/CIMTBL_MAPPING.md).

### Options

| Option | Where | Meaning |
|---|---|---|
| `artifact_dir` | `CimtblImporter.to_cim`, `dss_to_cim`, `raw_to_cim` | Directory for the `.cimtbl` files. Default is a temporary directory that is removed after loading. Set it to keep the human-readable artifact; the files are exactly what the model was built from. |
| `network` | `to_cim`, `dss_to_cim`, `raw_to_cim` | An existing cim18v17 model to bind onto, to merge several native models. Not supported by GDM. |
| `name_source` | `DssExporter.to_model`, `GdmExporter.to_model` | What an exported native name is written from: `'name'`, `'mrid'` or `'uri'`. Default is the `CIMHUB_NAME_SOURCE` environment variable, else `'mrid'`. Any other value raises `ValueError`. |
| `circuit_source` | `DssExporter.to_model` | Name of the EnergySource written as `New Circuit` when there are several. Default `"source"`. |
| `system_name` | `GdmExporter.to_model` | Name of the `DistributionSystem`. Default is the one Feeder's exported name; several Feeders raise. |

`name_source='mrid'` is the default because importers compile the mRID from the native name, so it is unique by
construction. Use `'uri'` when a target limits name length. The mRID is not a stable join key across rebuilds;
`uri()` is.

Units are never an option. Importers copy values in source units with the unit in the `.cimtbl` column header, and
exporters convert with `.to(...)` on the CIM quantity. See [UNITS.md](UNITS.md).

## Runnable examples

Run from the repository root after `uv sync`. Both use fixtures in the repo.

### OpenDSS: `.dss` to CIM and back

```python
import tempfile
from pathlib import Path

from cimhub_opendss import DssExporter, DssReader, DssWriter, dss_to_cim

deck = Path("cimhub_opendss/tests/decks/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss")
out = Path(tempfile.mkdtemp())

native = DssReader(deck).read_all()                               # parse: file -> native GraphModel
network = dss_to_cim(native, name="IEEE13_CDPSM", artifact_dir=out / "cimtbl")
print(type(network).__name__, len(list((out / "cimtbl").glob("*.cimtbl"))), "cimtbl files")

exported = DssExporter().to_model(network, name_source="name")    # CIM -> native GraphModel
DssWriter().write(exported, out / "back.dss")                     # persist
print(len(DssReader(out / "back.dss").read_all()), "objects read back")
```

Output:

```
FeederModel 14 cimtbl files
82 objects read back
```

`cim_to_dss(network, out / "back.dss", name_source="name")` does the last two steps in one call.

### GDM: CIM to a `DistributionSystem` and back

```python
import tempfile
from pathlib import Path

import cimtables

from cimhub_gdm import GdmExporter, cim_to_gdm, gdm_to_cim, read_gdm

golden = Path("cimhub_gdm/tests/atoms/load/loads.cimtbl")
out = Path(tempfile.mkdtemp())

network = cimtables.load_model(golden)                            # a cim18v17 FeederModel
system = GdmExporter().to_model(network, name_source="name", system_name="loads")
print(type(system).__name__, system.name)                         # inspect before writing

cim_to_gdm(network, out / "loads.json", name_source="name", system_name="loads")   # export + write
reimported = gdm_to_cim(read_gdm(str(out / "loads.json")))        # read + import
print(type(reimported).__name__)
```

Output (the exporter also logs a WARNING about neutral values for one required GDM field):

```
DistributionSystem loads
FeederModel
```

The example starts from a `.cimtbl` file because GDM has no text format to import. In real use the CIM comes from
another importer, such as `dss_to_cim`, and `cim_to_gdm` writes the GDM JSON.

## ConverterRegistry

`ConverterRegistry` maps native or CIM classes to converter functions by decorator:

```python
from cimhub_core import ConverterRegistry

registry = ConverterRegistry()

@registry.register(SomeClass)
def convert_some_class(obj, network):
    ...

convert = registry.get(SomeClass)
```

It also has `classes()`, `in`, iteration and `len`. It is a plain dispatch table with no behavior of its own. The
shipped OpenDSS, GDM and RAW packages do not use it; they dispatch through their own ordered module lists
(`MAPPING_ORDER` for importers, `EXPORT_ORDER` for exporters). The exporter stubs that `scaffold_package` generates
do create one. `register` overwrites an earlier registration for the same class without warning.

## Starting a new package

```python
from cimhub_core import scaffold_package

scaffold_package("matpower", direction="both", parent_dir=".")   # creates ./cimhub_matpower
```

`direction` is `"importer"`, `"exporter"` or `"both"`. It creates `cimhub_<fmt>/src/cimhub_<fmt>/` with a schema
skeleton, the importer tree (`<fmt>_reader.py`, `<fmt>_to_cimtbl.py`, `cimtbl/`), the exporter tree (one stub per
CIM class, grouped by domain), and an MCP `service.py` stub. Once the schema exists,
`scaffold_mapper(format_name, native_cls, prefix=...)` (from `cimhub_core.scaffold`) adds one mapper module and
its test per native table.

The scaffold creates files only. A package is added to the workspace in the root `pyproject.toml` by the repository
owner when its wave starts. Naming follows the rule: `{Fmt}Reader`, `{Fmt}Writer`, `{Fmt}Importer`,
`{Fmt}Exporter`, `<fmt>_to_cim`, `cim_to_<fmt>`. Tests are described in [TESTING.md](TESTING.md).
