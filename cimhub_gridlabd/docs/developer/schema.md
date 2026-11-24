# The LinkML schema

The GridLAB-D records are LinkML classes. The YAML is the single source of truth for what a GLM object holds and how
it is written; `gridlabd.py` is generated from it and never edited by hand. Unlike a hand-written schema, the YAML
here is scraped from the GridLAB-D C++ source, class by class, so it follows what GridLAB-D publishes. The schema
describes the native format only: it holds no CIM objects and no unit conversion. How each class reaches CIM is the
mapper's job (see [The importer](importer.md)). The rules for writing a
native schema are in the
[`linkml-native-schema` skill](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/linkml-native-schema/SKILL.md).

## Layout

Everything is under
[`src/cimhub_gridlabd/schema/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_gridlabd/src/cimhub_gridlabd/schema).

| Path | Holds |
|---|---|
| `linkml/main.yaml` | The root. It declares no classes; it imports `types/common` and every class file. |
| `linkml/types/common.yaml` | `Complex` (real and imag), the abstract `glm_object`, and the enums shared by the classes. |
| `linkml/powerflow/` | The powerflow module, one file per class: `node`, `meter`, `load`, `overhead_line`, `transformer`, `regulator`, `capacitor`, ... (46 files). |
| `linkml/generators/` | The generators module: `inverter`, `solar`, `battery`, ... (11 files). |
| `linkml/residential/` | The residential module: `house`, `waterheater`, `ZIPload`, ... (19 files). |
| `linkml/tape/player.yaml` | The tape module's `player`, written by hand (see below). |
| `gridlabd.py` | The generated dataclasses, one per class: `schema.OverheadLine`, `schema.Node`, ... |
| `cpp_parser.py`, `property_parser.py`, `linkml_generator.py` | The scraper. |
| `README.md` | How to run the scraper for one module, and how the dataclasses are regenerated. |

One YAML file holds one class. A class name is its GLM type name (`overhead_line`, `triplex_meter`), unique across the
schema: `glm_schema` raises `GLM schema class ... is defined twice` on a repeat. The generated dataclass is the
PascalCase name (`OverheadLine`) with a `class_name` class variable holding the GLM name. Every class inherits
`glm_object` (directly, or through its GridLAB-D parent: `overhead_line` is a `line`, a `link`, a `powerflow_object`,
a `glm_object`).

`glm_object` holds the header properties GridLAB-D gives every object whatever its class (`name`, `parent`,
`groupid`, `latitude`, `longitude`, ...). No class publishes them, so the scrape does not see them: `linkml_generator`
writes them into `types/common.yaml` itself. `name` is the identifier, unique across a model, as GridLAB-D's names are.
`player.yaml` is also written by hand, from the tape module's published struct, because the scrape does not read that
form. It sits in `tape/`, which none of the scrapes of the other modules writes to.

A property named like a Python keyword is renamed in the slot and kept in the annotation: the GLM property `from` is
the slot `from_node`, with `native_name: from`.

## The scraper

Three scripts, run in order, one GridLAB-D module at a time. They are run by hand and never imported by the package.
The commands, with the intermediate JSON files they pass along, are in
[`schema/README.md`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_gridlabd/src/cimhub_gridlabd/schema/README.md).

| Script | Reads | Writes |
|---|---|---|
| `cpp_parser.py --source <GridLAB-D checkout> --module <module>` | The C++ files of one module directory: each class's `gl_publish_variable` block, its parent class and its doc comment. | `extracted_<module>_classes.json` |
| `property_parser.py --input ... --output ...` | The raw publish blocks. It tokenizes each block on commas at paren depth 0 and walks the tokens as a state machine, so wrapped declarations parse the same. It raises on a token it cannot classify instead of dropping the property. | `parsed_<module>_classes.json`: typed properties (name, C++ type, LinkML range, unit, description, enum values). |
| `linkml_generator.py --input ... --output .../linkml --module <module>` | The parsed JSON. | One YAML per class in `linkml/<module>/`; the enums merged into `types/common.yaml`; the module's imports appended to `main.yaml`. Both are updated idempotently, so a rerun for a new module leaves earlier modules alone. |

GridLAB-D itself is not vendored: `--source` points at a checkout, and the schema's license is BSD-3-Clause, as
GridLAB-D's.

## Regenerating gridlabd.py

After any change to a YAML file, regenerate the module and commit both together:

```bash
scripts/gen-schema.sh gridlabd      # one spoke
scripts/gen-schema.sh               # every spoke with a schema
```

[`scripts/gen-schema.sh`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/scripts/gen-schema.sh) maps each
package to its root YAML and generated module (for `gridlabd`, `schema/linkml/main.yaml` to `schema/gridlabd.py`),
runs `uvx --python 3.13 --from linkml gen-python --no-generation-date`, and copies the result over the module. It
runs linkml through `uvx`, so it never touches `uv.lock`, and `--no-generation-date` keeps the output the same from run
to run, so the diff shows only what the YAML changed. An unknown package name exits with the list of known ones.

The first regeneration after a LinkML upgrade also changes the header: the committed module was generated by an older
LinkML, so the `Generation date` line goes and `metamodel_version` changes. Nothing else differs from the committed
file when the YAML has not.

After regenerating:

- run `scripts/test-all.sh gridlabd`: a mapper's `check_fields(FIELDS, NATIVE_CLASS)` test fails on a slot the
  regeneration added or removed, and `link.classify` and `bus.classify` raise at import time on a slot no
  classification claims, so `FIELDS` (and the exporter's `SLOTS`) are updated in the same commit;
- never edit `gridlabd.py` by hand; the next regeneration would erase the edit. A fix goes in the YAML, then
  regenerate. A change to a scraped class is overwritten by the next scrape of its module, so a change that has to
  survive belongs in the scraper (`linkml_generator.py`) or in a hand-written file.

## The annotations the code reads

gen-python does not carry LinkML annotations into the dataclasses. `glm_schema.py` reads them from the YAML at run
time and indexes them per dataclass, walking `is_a` so an inherited slot (`nominal_voltage` on a `triplex_node`, from
`node`) carries its annotations. (The core `get_schema_annotations` matches a class by its Python `__name__`, which is
the PascalCase name here and never the YAML key, so this package does not use it.)

| Where | Key | Read by |
|---|---|---|
| slot annotation | `native_name` | `glm_schema.slots` (the `SlotInfo.native_name`), then `glm_schema.slot_for_property` (the reader's map from a GLM property to its slot), `GlmWriter.serialize` (the property name written), `importer.cimtbl.catalog.native_name` (error messages). The scrape appends the unit (`primary_voltage[V]`); `glm_schema` strips that suffix. |
| slot, `unit.ucum_code` | the declared unit | `glm_schema.slots` (`SlotInfo.unit`), then `GlmModel.unit` (the unit a value is stored in when none was written) and `exporter.units.glm_unit`. `registry_unit` respells GridLAB-D's unit names for pint. |
| slot annotation | `glm_default` | `glm_schema.slots` (`SlotInfo.default`). No YAML sets it yet and no code reads `default`: the reader leaves a GLM default unset, and the mappers name the defaults they need. |
| slot annotation | `order` | Written by the scraper (the property's position, `0` for the header slots). No code reads it: a deck is written in the order of the dataclass fields, which is the YAML's attribute order. |
| slot annotation | `value_type`, `precision` | Written by the scraper (the C++ type family, and 6 for a double). No code reads them. |
| slot | `range` | The reader reads it from the dataclass type hints (`_slot_kinds`: `Complex`, float, int, bool, an enum or text) to decide how to read a value. |
| slot | `identifier` | `name` on `glm_object`; the reader and `GlmModel` key records by it. |

```python
from cimhub_gridlabd import glm_schema
from cimhub_gridlabd.schema import gridlabd as schema

print(glm_schema.slots(schema.OverheadLine)["from_node"])       # SlotInfo(native_name='from', unit=None, default=None)
print(glm_schema.slot_for_property(schema.OverheadLine)["from"])   # from_node
print(glm_schema.slots(schema.TriplexLineConfiguration)["insulation_thickness"].unit)   # in
print(glm_schema.registry_unit("Ohm/mile"))                      # ohm/mile
```

A default is never written as `ifabsent`: that would make the reader fill every slot, and the writer then write them
all back. An unset GLM property stays unset.

## The CIM mapping slots

Each class the package converts, and each property it copies, maps, derives or reads structurally, names its cim18v17
counterpart, as the OpenDSS schema does:

| slot | meaning | example |
|---|---|---|
| `exact_mappings` | the same concept, copied or mapped | `line.length` → `cim:Conductor.length` |
| `close_mappings` | a derived value, or one of several targets | `capacitor.capacitor_A` → `cim:ShuntCompensator.nomQ`; `load` → `cim:ConformLoad` when a player drives it |
| `related_mappings` | a structural reference | `link.from_node` → `cim:Terminal.ConnectivityNode` |

A short `comments` entry says where the value lands on import (the `.cimtbl` column and its unit) and how the export
writes it back. A class the package does not convert says so in its comment instead. The slots are documentation:
no code reads them, and the schema reference shows them. The mapping itself is the mapper's `FIELDS` and the
exporter's `SLOTS`, and the design record is the [import](../CIMTBL_MAPPING.md) and [export](../EXPORT_MAPPING.md)
specs. An inherited property is mapped once, on the class that declares it.

## The schema reference

The reference pages in `docs/schema/` are generated, never committed (`docs/.gitignore` lists `schema/`).
[`scripts/build-docs.sh`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/scripts/build-docs.sh) generates them
before it builds the site:

```bash
scripts/build-docs.sh gridlabd --serve    # generate docs/schema/, then serve the site
scripts/build-docs.sh gridlabd            # generate, then mkdocs build --strict
```

For `gridlabd` the script removes `cimhub_gridlabd/docs/schema` and runs

```bash
uvx --python 3.13 --from linkml gen-doc -d cimhub_gridlabd/docs/schema \
    cimhub_gridlabd/src/cimhub_gridlabd/schema/linkml/main.yaml
```

`gen-doc` writes `schema/index.md` and one page per class and enum. `mkdocs.yml` puts `schema/index.md` in the nav as
the Schema reference and lists `schema/*` under `not_in_nav`, so the per-class pages are reached from the index and
the build does not warn about them. Building the site with `mkdocs` alone, without the script, fails the strict build
on the missing `schema/index.md`.
