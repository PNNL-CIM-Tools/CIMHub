# Converter API

This is the public API every CIMHub package presents: how to get from a native file to a cim18v17 model and back.
It covers the base classes in `cimhub_core`, the one-call functions each package exports, the export naming switch,
and how a new package starts. For how the pieces fit together see [Architecture](architecture.md). For the rules a
contributor (or Claude) follows when writing a converter, see the
[`reader-writer` skill](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/reader-writer/SKILL.md).

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
[`cimhub_core/base.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/src/cimhub_core/base.py)
and exported from `cimhub_core`.

| Class | Methods | Takes | Returns | Disk |
|---|---|---|---|---|
| `FormatReader` | `__init__(source)`, `read_all()` | source, bound once at construction | native `GraphModel` | reads |
| `FormatWriter` | `write(model, destination)`, `serialize(obj)` | native `GraphModel`; one object | `None`; `str` | writes |
| `CimtblImporter` | `to_cimtbl(model)`, `bound_parts(model, network)`, `to_cim(model, *, network=None, artifact_dir=None)` | native `GraphModel` | `DocumentSet`; `list[Document]`; cim18v17 model | `to_cim` writes the artifact files |
| `FormatImporter` | `to_cim(model, *, network=None)`, `make_network(network=None)` | native model | cim18v17 model | none |
| `FormatExporter` | `to_model(network, **opts)` | cim18v17 model | native `GraphModel` | none |

`CimtblImporter` is a `FormatImporter`. `FormatReader`, `FormatWriter` and `FormatExporter` are plain ABCs.

Points that matter to a caller:

- **A reader binds its source in `__init__` and parses in `read_all()`.** Constructing a reader is cheap. There is no
  per-class read method; one call returns the whole model. The reader keeps the bound `source` as an attribute.
- **A writer takes the reader's `GraphModel`.** `serialize(obj)` renders one object; `write` persists the model.
  Single-file formats take a file path as `destination`; formats with one file per class take a directory.
- **An importer takes a parsed model, never a path.** `CimtblImporter` is for file formats: the spoke implements
  `to_cimtbl`, a pure mapping to `.cimtbl` documents, and `to_cim` writes them and builds CIM from the written text.
  Its `model_cls` is `None` (the master's one Feeder or Substation decides the model type) unless the spoke sets it:
  RAW sets `BusBranchModel`. `FormatImporter` is the base for a spoke with no file format (GDM builds CIM through
  CIM-Builder directly); it declares `model_cls` and `make_network` returns a fresh empty `model_cls` network unless
  you hand it one.
- **`bound_parts` is optional.** A spoke overrides it only for a part that reads the Terminals binding made, such
  as OpenDSS bus coordinates. It returns `[]` by default; `to_cim` imports what it returns last.
- **An exporter takes a network and returns a native model.** It has no `destination` argument and never writes.
  Options such as `name_source` go to `to_model(**opts)`.
- **No converter returns text.** The native `GraphModel` holds schema dataclasses, so export output can go straight
  back through the importer in a round-trip test.

The contract for importers (what a mapper may and may not do) is the
[`cimtbl-import-contract` skill](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/cimtbl-import-contract/SKILL.md)
and [The .cimtbl import contract](cimtbl.md). The contract for exporters (reading CIM through the core getters) is
the [`export-getters` skill](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/export-getters/SKILL.md)
and [Writing a getter](writing-getters.md).

## GraphModel

`cimhub_core.GraphModel` is the native store: `{schema_class: {identifier: instance}}`. Readers and exporters
return one; writers and importers take one. It is not a cimgraph model. Adding a second object with the same
identifier to a class raises `ValueError`, because the identifier seeds the object's mRID. Two classes may share
one identifier (an OpenDSS `Line.l1` and `Load.l1`).

The identifier field is the one the LinkML schema flags `identifier: true`. A class without one falls back to the
first of `ID`, `name`, `identifier` that is set. A class with none of these is stored under `str(id(obj))` with a
logged warning, so its order and mRID change from run to run: give every native class an `identifier: true` slot.

| Method | Use |
|---|---|
| `add_to_graph(obj)` | insert an object under its identifier |
| `GraphModel.from_objects(objects)` | build from a flat iterable |
| `list_by_class(cls)` | all objects of one class, sorted by identifier |
| `iter_by_class(cls)` | the same objects in insertion order |
| `iter_all()` | every object, grouped by class |
| `first(cls)`, `next(cls)` | step through a class, sorted; `None` at the end |
| `find_by_attribute(cls, attribute, value)` | objects whose attribute equals the value (compared as text) |
| `count(cls)`, `len(model)`, `cls in model` | size and membership (`cls in model` is false for a class with no objects) |

Iterate with `list_by_class` or `iter_all`. Iterating `model.graph[cls]` directly yields identifier strings, not
objects.

```python
from cimhub_opendss import DssReader
import cimhub_opendss.schema.opendss_schema as schema

model = DssReader("cimhub_opendss/tests/decks/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss").read_all()
loads = model.list_by_class(schema.Load)
print(len(loads), loads[0].name, model.count(schema.Load), schema.Load in model)
try:
    model.add_to_graph(loads[0])
except ValueError as error:
    print(error)
```

```
16 611 16 True
Load identifier '611' is already in the model; identifiers are unique within a class (they seed the mRID)
```

## One-call functions

Each package wraps the classes above in thin functions. The functions take objects, not paths, so a reader always
comes first. Every importer function takes `authority` (default `https://github.com/PNNL-CIM-Tools/CIMHub`), which
is the master's `Authority`.

| Package | Import | Export | Reader / writer |
|---|---|---|---|
| `cimhub_opendss` | `dss_to_cim(model, *, name, authority=..., length_unit=None, device_geometry="point", network=None, artifact_dir=None, time_points=None)` | `cim_to_dss(network, destination, *, per_class=False, time_points=None, **opts)` | `DssReader(path)`, `DssWriter()` |
| `cimhub_gridlabd` | `glm_to_cim(model, *, name, authority=..., substation=None, feeder=None, network=None, artifact_dir=None, time_points=None)` | `cim_to_glm(network, destination, *, time_points=None, **opts)` | `GlmReader(source, *, defines=None)`, `GlmWriter()` |
| `cimhub_raw` | `raw_to_cim(model, *, name, authority=..., network=None, artifact_dir=None)` | `cim_to_raw(network, destination)` | `Raw34Reader(source)`, `Raw34Writer()` |
| `cimhub_gdm` | `gdm_to_cim(system, *, time_points=None)` | `cim_to_gdm(network, destination, *, time_points=None, **opts)` | `read_gdm(path)`, `write_gdm(system, path)` |

Notes per package:

- **OpenDSS.** All names are exported from `cimhub_opendss`: `DssReader`, `DssWriter`, `DssImporter`,
  `DssExporter`, `DssModel`, `DssParseError`, `dss_to_cim`, `cim_to_dss`. `name` is the master's `Model` and the
  file stem; use the deck's name. `length_unit` is the per-length unit for line codes that carry none.
  `device_geometry` is `"point"` or `"linestring"` and anything else raises `ValueError`. `cim_to_dss` writes a
  `.dss` deck, or with `per_class=True` one file per DSS class beside it, and passes `**opts` to
  `DssExporter.to_model`.
- **GridLAB-D.** `cimhub_gridlabd` has no names in its `__init__.py`; import from the modules:
  `cimhub_gridlabd.glm_reader` (`GlmReader`, `GlmModel`, `GlmParseError`), `cimhub_gridlabd.glm_writer`
  (`GlmWriter`), `cimhub_gridlabd.importer.glm_to_cimtbl` (`GlmImporter`, `glm_to_cim`) and
  `cimhub_gridlabd.exporter.cim_to_glm` (`GlmExporter`, `cim_to_glm`). `name` is the master's `Model`; `substation`
  and `feeder` name the containers (each defaults to `name`). `cim_to_glm` writes the players' files beside the deck.
- **RAW.** `cimhub_raw` has no names in its `__init__.py`; import from the modules: `cimhub_raw.raw34_reader`
  (`Raw34Reader`), `cimhub_raw.raw34_writer` (`Raw34Writer`), `cimhub_raw.importer.raw_to_cimtbl` (`RawImporter`,
  `raw_to_cim`) and `cimhub_raw.exporter.cim_to_raw` (`RawExporter`, `cim_to_raw`). The importer produces a
  `BusBranchModel`. `RawExporter.to_model(network)` takes no options and raises on conducting equipment it has no
  module for. The mappings are in
  [CIMTBL_MAPPING.md](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_raw/docs/CIMTBL_MAPPING.md) and
  [EXPORT_MAPPING.md](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_raw/docs/EXPORT_MAPPING.md).
- **GDM.** GDM has no file format of its own, so the "native model" is a grid-data-models `DistributionSystem` and
  `read_gdm` / `write_gdm` are its JSON load and save. `GdmImporter` subclasses `FormatImporter`, builds its own
  network, and raises if you pass `network=`. `GdmExporter.to_model` takes `name_source` and `system_name`. It
  logs a WARNING when it fills required GDM fields that CIM cannot hold (see
  [EXPORT_PLAN.md](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_gdm/docs/EXPORT_PLAN.md)).

### Options

| Option | Where | Meaning |
|---|---|---|
| `artifact_dir` | `CimtblImporter.to_cim`, `dss_to_cim`, `glm_to_cim`, `raw_to_cim` | Directory for the `.cimtbl` files. Default is a temporary directory that is removed after loading. Set it to keep the human-readable artifact; the files are exactly what the model was built from. |
| `network` | `to_cim`, `dss_to_cim`, `glm_to_cim`, `raw_to_cim` | An existing cim18v17 model to bind onto, to merge several native models. Not supported by GDM. |
| `name_source` | `to_model` of every exporter | What an exported native name is written from: `'name'`, `'mrid'` or `'uri'`. Default is the `CIMHUB_NAME_SOURCE` environment variable, else `'mrid'`. Any other value raises `ValueError`. (`RawExporter` takes none.) |
| `switch_state` | `DssExporter.to_model`, `GlmExporter.to_model` | `'actual'` (default) writes `Switch.open`; `'normal'` writes `Switch.normalOpen`. Any other value raises `ValueError`. |
| `circuit_source` | `DssExporter.to_model` | Name of the EnergySource written as `New Circuit` when there are several. Default `"source"`. |
| `system_name` | `GdmExporter.to_model` | Name of the `DistributionSystem`. Default is the one Feeder's exported name; several Feeders raise. |
| `time_points` | importer and exporter constructors (OpenDSS, GridLAB-D, GDM), and the one-call functions | A dict of TimePoint tables, keyed by class name (see `cimhub_core.time_points`; needs the `time-points` extra). An importer fills the dict you pass; without one it drops the points of yearly shapes, players and schedules with one warning. An exporter reads it to write the series back. |

`name_source='mrid'` is the default because importers compile the mRID from the native name, so it is unique by
construction. Use `'uri'` when a target limits name length (GridLAB-D's name references). The mRID is not a stable
join key across rebuilds; `uri()` is. The switch is `cimhub_core.names.resolve_name_source(source=None)`, and each
exporter turns an object into its text with `export_name(obj, source)`, which raises on an unset or blank name. The
spoke then applies its own format's escaping to the result.

Units are never an option. Importers copy values in source units with the unit in the `.cimtbl` column header, and
exporters convert with `get_qty` through the getters. See [Units](units.md).

## Runnable examples

Run from the repository root after `uv sync`. Both use fixtures in the repo, and both run inside
`cim_scope()` because cimtables sets the profile and model scope process-wide.

### OpenDSS: `.dss` to CIM and back

```python
import tempfile
from pathlib import Path

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_opendss import DssExporter, DssReader, DssWriter, dss_to_cim

deck = Path("cimhub_opendss/tests/decks/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss")
out = Path(tempfile.mkdtemp())

with cim_scope():
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

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_gdm import GdmExporter, cim_to_gdm, gdm_to_cim, read_gdm

golden = Path("cimhub_gdm/tests/atoms/load/loads.cimtbl")
out = Path(tempfile.mkdtemp())

with cim_scope():
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
from cimhub_opendss import DssReader
import cimhub_opendss.schema.opendss_schema as schema

registry = ConverterRegistry()

@registry.register(schema.Load)
def convert_load(obj, network):
    return obj.name

model = DssReader("cimhub_opendss/tests/decks/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss").read_all()
load = model.list_by_class(schema.Load)[0]
print(registry.get(schema.Load)(load, None), registry.get(schema.Line), len(registry), schema.Load in registry)
print(registry)
```

```
611 None 1 True
ConverterRegistry(['Load'])
```

It also has `classes()` and iteration. It is a plain dispatch table with no behavior of its own: `get` returns
`None` for an unregistered class, and `register` overwrites an earlier registration for the same class without
warning. The shipped OpenDSS, GridLAB-D, RAW and GDM packages do not use it; they dispatch through their own ordered
module lists (`MAPPING_ORDER` for importers, `EXPORT_ORDER` for exporters). Only the exporter stubs that
`scaffold_package` generates create one.

## Naming and text helpers

| Function | Module | Use |
|---|---|---|
| `resolve_name_source(source=None)`, `export_name(obj, source)` | `cimhub_core.names` | The export naming switch, above. Used by the OpenDSS, GridLAB-D and GDM exporters. |
| `clean_cim_name(raw, default="UNKNOWN")` | `cimhub_core.names` | Replaces whitespace and `. < > & " ' [ ] { } ( ) , = ~ \|` with `_`; `None` or blank gives `default`. No spoke calls it, and it must not be used for mRIDs (I8: IDs are quoted, never sanitized). |
| `AnnotationSerializer`, `format_by_spec`, `get_field_order`, `get_native_name` | `cimhub_core.serialization` | Native text driven by the LinkML annotations `order`, `format`, `separator`, `serialize_if` and `line_number`. A writer uses it from `serialize`. Limits: `serialize_if: not_default` looks the default up in dataclass field metadata, which generated classes do not have, so it always serializes; a `custom` expression that raises (a misspelled field name) counts as true; `skip_defaults` is stored but never read. |
| `get_schema_annotations(cls)` | `cimhub_core.serialization` | The slot annotations of a native class, read from the schema YAML beside the generated module and cached. Returns `{}` when no schema is found, and silently skips a schema file that fails to load. Spoke readers and writers use it for slot order and defaults. |
| `get_mermaid(root, show_attributes=True, theme="neutral")`, `download_mermaid(mermaid, filename, timeout=30)` | `cimhub_core.mermaid` | A mermaid mindmap for one native object, or a class diagram for a class or list of classes. `download_mermaid` fetches a rendered image from mermaid.ink and returns `False` on a network or HTTP error; a diagram with a non-ASCII character raises `UnicodeEncodeError` instead. |

`get_mermaid` takes an instance (a mindmap, which ignores `show_attributes` and `theme`), a class, a list of classes, or a list of instances, and raises `TypeError` for anything else (including a mixed list):

```python
from cimhub_core import get_mermaid
import cimhub_opendss.schema.opendss_schema as schema

print(get_mermaid(schema.Load, show_attributes=False))
```

```
%%{init: {"theme":"neutral"}}%%
classDiagram
    class Load {
        <<A Load object in OpenDSS representing an energy consumer connected to a bus in the distribution system.>>
    }
```

## Starting a new package

```python
import tempfile

from cimhub_core import scaffold_package

parent = tempfile.mkdtemp()
print(scaffold_package("matpower", direction="both", parent_dir=parent))   # <parent>/cimhub_matpower
```

`direction` is `"importer"`, `"exporter"` or `"both"`; any other value is not rejected and creates only the schema
skeleton and `service.py`. It returns the path of the new package and creates
`cimhub_<fmt>/src/cimhub_<fmt>/` with:

- a schema skeleton (`schema/main.yaml`, `types/common_types.yaml`, a placeholder `<fmt>.py`);
- the importer tree: `importer/<fmt>_reader.py`, `importer/<fmt>_to_cimtbl.py` (`MAPPING_ORDER`, `map_master`, the
  `CimtblImporter` subclass and `<fmt>_to_cim`) and an empty `importer/cimtbl/`;
- the exporter tree: `exporter/registry.py`, `exporter/<fmt>_writer.py`, `exporter/cim_to_<fmt>.py` and one stub per
  CIM class, grouped by domain (`topology/`, `lines/`, `loads/`, `generators/`, `transformers/`, `switches/`,
  `shunts/`, `series/`, `hvdc/`, `inverters/`), each registered on the exporter's `ConverterRegistry`;
- a `service.py` stub. It imports `cimhub_core.mcp.DualTransportMCPService`, which does not exist in core, so the
  stub cannot be imported as generated; delete it or replace it.

Once the schema exists, `scaffold_mapper` adds one mapper module and its test per native table:

```python
from cimhub_core.scaffold import scaffold_mapper
import cimhub_opendss.schema.opendss_schema as schema

scaffold_mapper("demo", schema.Load, prefix="ld_", parent_dir="/tmp/scaf")
# writes /tmp/scaf/cimhub_demo/src/cimhub_demo/importer/cimtbl/load.py
```

`prefix` is the mRID prefix (`"ld_"`); `table_name` (default the class name in snake case) is the artifact stem;
`records` are native records whose values become sample notes in the stub. The mapper stub gets `NATIVE_CLASS`,
`PREFIX`, a `FIELDS` dict with one `Field('TODO', note=...)` per slot (a `TODO` kind does not import, so every field
must be classified first) and a `map_<table>` function that raises `NotImplementedError`. The test file
`tests/test_cimtbl_<table>.py` gets `test_classification_is_complete`. `scaffold_mapper` raises `FileExistsError`
rather than overwrite either file; `scaffold_package` overwrites whatever is at its paths.

The scaffold creates files only. A package is added to the workspace in the root `pyproject.toml` by the repository
owner when its wave starts. Naming follows the rule: `{Fmt}Reader`, `{Fmt}Writer`, `{Fmt}Importer`,
`{Fmt}Exporter`, `<fmt>_to_cim`, `cim_to_<fmt>`. Tests are described in [Testing](testing.md).
