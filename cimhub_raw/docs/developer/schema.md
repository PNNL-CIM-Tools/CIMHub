# The LinkML schema

The RAW records are LinkML classes. The YAML is the single source of truth for what a RAW record holds and where each
field sits in the file; `raw34_schema.py` is generated from it and never edited by hand. The schema describes the
native format only: it holds no CIM objects and no unit conversion. How each table reaches CIM is the mapper's job (see
[The importer](importer.md)). The rules for writing a native schema are in the
[`linkml-native-schema` skill](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/linkml-native-schema/SKILL.md).

## Layout

Everything is under
[`src/cimhub_raw/schema/raw_v34/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_raw/src/cimhub_raw/schema/raw_v34).

| Path | Holds |
|---|---|
| `main.yaml` | The root. It imports `linkml:types`, `types/common_types` and the 22 class files, and declares one class, `RawModel`, a container with a list slot per record class. The package does not use `RawModel`; records are held in a `GraphModel`. |
| `types/common_types.yaml` | Four shared types: `BusNumber`, `BusId`, `CircuitId` and `Status`. |
| `classes/*.yaml` | One file per RAW table, 22 files: `bus`, `load`, `fixed_shunt`, `generator`, `branch`, `switch`, `transformer`, `area_interchange`, `two_terminal_dc`, `vsc_dc`, `impedance_correction`, `multi_terminal_dc`, `multi_section_line`, `zone`, `interarea_transfer`, `owner`, `facts_device`, `switched_shunt`, `gne_device`, `induction_machine`, `case_identification`, `substation`. |
| `raw34_schema.py` | The generated dataclasses, one per class: `schema.BusRecord`, `schema.TransformerRecord`, ... |
| `composite_id.py` | `KEY_FIELDS` and `assign_composite_id`: the natural key of each record type (below). Hand-written. |
| `README.md` | A short note on the directory. |

A file holds one RAW table, or more when the table has parts: `case_identification.yaml` also holds `RatingRecord`,
`substation.yaml` holds the node, switching device and equipment terminal records of the SUBSTATION section,
`impedance_correction.yaml` the table's `ImpedanceCorrectionPoint`, and `multi_terminal_dc.yaml` the converter, DC bus and
link records. Thirty classes in all. A class is `<Table>Record`, and its slots are `snake_case` names with the RAW field
name first in the description (`constant_real_power`: `PL - Active power component of constant MVA load in MW`). The RAW names the
docs use (`PL`, `QL`, `NXFRAT`) are in those descriptions, and the schema reference shows them.

## Regenerating raw34_schema.py

After any change to a YAML file, regenerate the module and commit both together:

```bash
scripts/gen-schema.sh raw         # this package
scripts/gen-schema.sh             # every spoke with a schema
```

[`scripts/gen-schema.sh`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/scripts/gen-schema.sh) maps each
package to its root YAML and generated module (for `raw`, `schema/raw_v34/main.yaml` to
`schema/raw_v34/raw34_schema.py`), runs `uvx --python 3.13 --from linkml gen-python --no-generation-date`, and copies the
result over the module. It runs linkml through `uvx`, so it never touches `uv.lock`, and `--no-generation-date` keeps the
output the same from run to run, so the diff shows only what the YAML changed. An unknown package name exits with the
list of known ones. With the YAML as committed, regenerating gives a byte-identical module.

After regenerating:

- run `scripts/test-all.sh raw`: a mapper's `check_fields(FIELDS, NATIVE_CLASS)` test fails on a slot the regeneration
  added or removed, and `check_slots` does the same for an exporter module's `SLOTS`, so `FIELDS` and `SLOTS` are
  updated in the same commit;
- never edit `raw34_schema.py` by hand; the next regeneration would erase the edit. A fix goes in the YAML.

## The annotations the code reads

`gen-python` does not carry LinkML annotations into the dataclasses. They are read from the YAML at run time by
`cimhub_core.serialization.get_schema_annotations(record_class)`, which finds the class by its Python name in
the YAML files under the schema directory and returns, per slot, its `annotations` plus the top-level properties
`unit`, `range`, `required`, `ifabsent`, `identifier`, `minimum_value`, `maximum_value`, `multivalued` and `description`.
Everything else in this package asks that function, usually through `record_layout.record_lines` or core's
`schema_defaults`.

| Where | Key | Meaning | Read by |
|---|---|---|---|
| annotation | `order` | The field's position on its line, from 1. A slot with no `order` is not a field of the record text (the composite `ID`). | `record_layout.record_lines` |
| annotation | `line_number` | Which line of a multi-line record the field is on; default 1. | `record_layout.record_lines` |
| annotation | `value_type` | `int`, `float` or `string` (default `string`): how the reader converts the token and the writer formats it. | `Raw34Reader._convert` and `Raw34Writer.format_field`, through `Slot.value_type` |
| annotation | `structural` | The reader fills it, it is not in the text (a node's `substation_number`). | `record_layout.record_lines` (left out of the layout) |
| top level and annotation | `multivalued`, `count` | A fixed-size list: `count` positions on the line (`ratings`, 12). | `record_layout.record_lines` |
| annotation | `precision` | Decimal places a float is written with, if that reads back as the same number. | `format_field` |
| annotation | `width` | A string is padded to this many characters. | `format_field` |
| annotation | `quote`, `quote_char` | A string is wrapped in quotes (default `'`). | `format_field` |
| annotation | `raw_default` | The value PSS/E applies when the field is blank or missing, in the spec's own default. | core's `schema_defaults(cls, "raw_default")` (through `records.raw_defaults`, `fill_keyed_defaults`, `zone.bus_zones`, `case_identification.case_values`, `topology._value`), and `composite_id._key_text` |
| top level | `identifier` | The slot a `GraphModel` keys the record on. | `cimhub_core.graph_model._get_identifier` |
| annotation | `serialize_if` | A condition under which a field is written (`custom:k != 0` for the third winding's fields, `custom:dum2 != 0` for a multi-section line's dummy buses). | Only `importer/cimtbl/transformer.py`: `THREE_WINDING_SLOTS` is the set of slots that carry it, which the transformer mapper leaves out of the defaults of a two-winding unit. Whether a line exists comes from `line_count`, and the writer drops trailing blank fields. |
| annotation | `raw_default_rule` | A default that depends on other fields, in words. | Nothing; documentation. |
| top level | `unit.ucum_code` | The unit the spec gives the field. | Nothing in the code: the unit is in the `.cimtbl` column header the mapper writes, and in the schema reference. |
| top level | `range`, `required`, `ifabsent`, `minimum_value`, `maximum_value` | LinkML's own. | The generated dataclasses (their types and `__post_init__` checks); not the layout. |

A `raw_default` is never written as `ifabsent`: that would make the reader fill every slot, and the writer then write
them all back. A blank RAW field stays `None` in the model.

```python
import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import schema_defaults
from cimhub_raw.record_layout import record_lines

print(schema_defaults(schema.FixedShuntRecord, "raw_default"))     # {'shunt_id': '1', 'status': 1, 'gl': 0.0, 'bl': 0.0}
slot = record_lines(schema.FixedShuntRecord)[0][1]
print(slot.name, slot.value_type, slot.annotations["width"], slot.annotations["quote_char"])    # shunt_id string 2 '
```

## composite_id.py

Most RAW records have a natural key of several fields (a load is its bus and its load ID), which a single
`identifier` slot cannot express. [`composite_id.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_raw/src/cimhub_raw/schema/raw_v34/composite_id.py)
holds `KEY_FIELDS`, a dict from record class to the slots of its key, and `assign_composite_id(record)`, which sets
`record.ID` to their trimmed values joined with `_`; a blank key field takes its `raw_default`. It does nothing for a
class not in `KEY_FIELDS`. The reader calls it on every record it adds and `export_tables` on every record it exports,
so the key is the same in both directions and seeds the same mRID. The table of keys is on
[Reader and writer](reader-writer.md). A new record type whose natural key is more than one field needs an entry in
`KEY_FIELDS`; one with a single numeric key marks that slot `identifier: true` in the YAML.

## The CIM mapping slots

The schema does not carry CIM mapping slots. OpenDSS's and GridLAB-D's schemas name each property's cim18v17
counterpart in `exact_mappings`, `close_mappings` and `related_mappings`; the RAW YAML has none yet. The mapping is the
mappers' `FIELDS` (field to CIM class, column and unit, with a note) and the exporter's `SLOTS`, and the design record
is the [import](../CIMTBL_MAPPING.md) and [export](../EXPORT_MAPPING.md) specs. Because those are tested for
completeness against the schema, a field cannot be added to the schema without being classified.

## The schema reference

The reference pages in `docs/schema/` are generated, never committed.
[`scripts/build-docs.sh`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/scripts/build-docs.sh) generates them
before it builds the site:

```bash
scripts/build-docs.sh raw --serve    # generate docs/schema/, then serve the site
scripts/build-docs.sh raw            # generate, then mkdocs build --strict
```

For `raw` the script removes `cimhub_raw/docs/schema` and runs

```bash
uvx --python 3.13 --from linkml gen-doc -d cimhub_raw/docs/schema \
    cimhub_raw/src/cimhub_raw/schema/raw_v34/main.yaml
```

`gen-doc` writes `schema/index.md` and one page per class, type and enum. `mkdocs.yml` puts `schema/index.md` in the nav
as the Schema reference and lists `schema/*` under `not_in_nav`, so the per-class pages are reached from the index and
the build does not warn about them. Building the site with `mkdocs` alone, without the script, fails the strict build
on the missing `schema/index.md`.
