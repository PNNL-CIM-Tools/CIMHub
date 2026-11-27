# The LinkML schema

The OpenDSS records are LinkML classes. The YAML is the single source of truth for what a DSS object holds and how it
is written; `opendss_schema.py` is generated from it and never edited by hand. The schema describes the native format
only: it holds no CIM objects and no unit conversion. How each class reaches CIM is the mapper's job (see
[The importer](importer.md)); the schema's CIM mapping slots only document it. The rules for writing a native schema
are in the
[`linkml-native-schema` skill](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/linkml-native-schema/SKILL.md).

## Layout

Everything is under
[`src/cimhub_opendss/schema/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_opendss/src/cimhub_opendss/schema).

| Path | Holds |
|---|---|
| `linkml/opendss.yaml` | The root. It declares no classes; it imports every class file. |
| `linkml/common_enums.yaml` | The enums shared by several classes (`ConnectionType`, `LoadModel`, ...), with aliases and `dss_value`. |
| `linkml/pce/` | Power conversion elements: `load`, `generator`, `pvsystem`, `storage`, `windgen`, ... |
| `linkml/pde/` | Power delivery elements: `line`, `transformer`, `autotrans`, `capacitor`, `reactor`, ... |
| `linkml/controls/` | `capcontrol`, `regcontrol`, `fuse`, `recloser`, `relay`, `swtcontrol`, ... |
| `linkml/general/` | Supporting data: `linecode`, `linegeometry`, `linespacing`, `wiredata`, `cndata`, `tsdata`, `xfmrcode`, `loadshape`, `buscoords`, ... |
| `linkml/meters/` | `energymeter`, `monitor`, `sensor`, `fmonitor`. |
| `linkml/other/` | `vsource`, `isource`, `fault`, `gicsource` and `options` (the kept `Set` options and the circuit name). |
| `opendss_schema.py` | The generated dataclasses, one per class: `schema.Linecode`, `schema.Line`, ... |

One YAML file holds one class, and class names are unique across the schema: the annotation loaders take the first
file that defines a class name. Every class has exactly one `identifier: true` slot, `name`. The slots are in the
DSS property order, with a comment `(n) name` ahead of each. The generated module must stay beside its YAML, because
`cimhub_core.serialization.get_schema_annotations` finds the YAML from the module's location.

## Regenerating opendss_schema.py

Nothing in the repository runs `gen-python` for you: no Makefile or script calls it. After any change to a YAML file,
regenerate and commit both together:

```bash
uvx --python 3.13 --from linkml gen-python \
    cimhub_opendss/src/cimhub_opendss/schema/linkml/opendss.yaml \
    > cimhub_opendss/src/cimhub_opendss/schema/opendss_schema.py
```

Run it from the repository root. With the same prefixes, the output differs from the committed file only in the
generation date and the `metamodel_version` line.

After regenerating:

- run `scripts/test-all.sh opendss`: a mapper's `check_fields(FIELDS, NATIVE_CLASS)` test fails on a slot the
  regeneration added or removed, so `FIELDS` (and the exporter's `SLOTS`) are updated in the same commit;
- never edit `opendss_schema.py` by hand; the next regeneration would erase the edit.

## The annotations the code reads

gen-python does not carry LinkML annotations into the dataclasses. The code reads them from the YAML at run time:
`cimhub_core.serialization.get_schema_annotations(cls)` returns `{slot: {annotation: value, ...}}` for a class, and
`dss_name_map` loads the YAML itself for the names and enums.

| Annotation | Where | Read by |
|---|---|---|
| `order` | slot | `DssWriter._properties` (the order of properties in a command); `dss_reader._property_order` (where a positional value goes, `_resolve_positional`). |
| `dss_default` | slot | `dss_reader.dss_defaults` (typed defaults for the mappers' `fill_defaults`) and `_preprocess_winding_text` (a transformer winding left unset). Both go through `cimhub_core.cimtbl.schema_defaults`. The form is `float(0.058)`, `int(3)` or `string(...)`. |
| `dss_name` | slot | `dss_name_map.build_class_map` (a DSS property that is not a Python name, `%R` for `pct_R`) and `DssWriter._properties` (the name written). |
| `dss_value` | enum value | `dss_name_map._build_enum_value_map` (the text or number a deck uses for the member). |
| `dss_format: matrix` | slot | `DssWriter._format_value`: the list is written as a lower-triangle matrix. |
| `dss_valid_values` | slot | No code. It documents the numbers a DSS property accepts (`"1,2,3,4,5,6,7,8"` for a Load's `model`). |
| `native_name` | slot | No code in this package, which uses `dss_name`. `get_schema_annotations` returns it for any spoke that wants it. |

`get_schema_annotations` also returns each slot's `unit`, `range`, `required`, `ifabsent`, `identifier`,
`minimum_value`, `maximum_value`, `multivalued` and `description` when the YAML has them. Defaults are never written
as `ifabsent`: that would make the reader fill every slot, and the writer then write them all back. An unset DSS
property stays unset, and the default lives in `dss_default`.

```python
from cimhub_core.serialization import get_schema_annotations
from cimhub_opendss.dss_name_map import get_class_map
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.schema import opendss_schema as schema

print(get_schema_annotations(schema.Linecode)["r1"])   # {'order': 2, 'dss_default': 'float(0.058)', 'range': 'float', ...}
print(dss_defaults(schema.Linecode)["r1"])             # 0.058
print(get_class_map(schema.Load).field_for("kw"))      # kW
print(get_class_map(schema.Transformer).field_for("%noloadloss"))   # pct_noloadloss
```

## The CIM mapping slots

Each class and slot can carry `exact_mappings`, `close_mappings` and `related_mappings` (`cim:PerLengthSequenceImpedance.r`),
and `comments` that start `Import:` or `Export:` and say what the mapper does. They are documentation only: no code
reads them, and they are not the mapping. The mapping is the mapper's `FIELDS` and the exporter's `SLOTS`, and the
design record is the [import](../CIMTBL_MAPPING.md) and [export](../EXPORT_MAPPING.md) specs. The mapping slots are shown
in the schema reference so a reader of a DSS class sees its CIM counterpart. Targets are cim18v17 names. When a mapper
changes, update the slot comment in the same commit, as nothing else checks it.

## The schema reference

The reference pages in `docs/schema/` are generated, never committed (`cimhub_*/docs/schema/` is in `.gitignore`).
[`scripts/build-docs.sh`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/scripts/build-docs.sh) generates them
before it builds the site:

```bash
scripts/build-docs.sh opendss --serve    # generate docs/schema/, then serve the site
scripts/build-docs.sh opendss            # generate, then mkdocs build --strict
```

For `opendss` the script removes `cimhub_opendss/docs/schema` and runs

```bash
uvx --python 3.13 --from linkml gen-doc -d cimhub_opendss/docs/schema \
    cimhub_opendss/src/cimhub_opendss/schema/linkml/opendss.yaml
```

`gen-doc` writes `schema/index.md` and one page per class and enum, with the annotations, the mapping slots and the
comments. `mkdocs.yml` puts `schema/index.md` in the nav as the Schema reference and lists `schema/*` under
`not_in_nav`, so the per-class pages are reached from the index and the build does not warn about them. Building the
site with `mkdocs` alone, without the script, fails the strict build on the missing `schema/index.md`.
