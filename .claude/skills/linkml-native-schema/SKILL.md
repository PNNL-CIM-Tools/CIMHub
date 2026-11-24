---
name: linkml-native-schema
description: How to write the LinkML schema for a native format (DSS, GLM, RAW, MATPOWER, DistOPF) - layout, identifiers, serialization annotations, units, defaults and CIM mapping slots. Use when creating or editing any YAML under `cimhub_<fmt>/src/cimhub_<fmt>/schema/`, or regenerating its dataclasses.
---

# LinkML native-format schemas

**The LinkML YAML is the single source of truth for a native format's structure and its serialization.**

```
schema YAML (classes + annotations) ─gen-python─▶ dataclasses (never hand-edit)
                                     └─ read at runtime by cimhub_core.serialization (get_schema_annotations)
```

The schema describes the native format only. It holds no CIM objects and no unit conversion. CIM mapping is
documented in mapping slots (below) and done by the spoke's `.cimtbl` mapper.

## Layout

```
cimhub_<fmt>/src/cimhub_<fmt>/schema/
  main.yaml            # root: imports every class file
  classes/<thing>.yaml # one file per native record type (bus, line, load, ...)
  case/                # operational / snapshot data, if the format has it
  types/common_types.yaml
  <fmt>.py             # gen-python output; regenerate, never edit
```

OpenDSS keeps its YAML under `schema/linkml/` grouped by DSS class family (`pde/`, `pce/`, `general/`, ...).
`get_schema_annotations` finds the YAML next to the generated module (`schema/`, `../schema/`, `linkml/` or the
module's own directory), so keep the generated `.py` beside its YAML.

## Rules

1. **Exactly one `identifier: true` field per class.** Without it the native `GraphModel` falls back to the first
   set of `ID`, `name`, `identifier`; an object with none of these raises `ValueError`.
2. **Class names are unique within a schema.** The annotation loader takes the first YAML file that defines the
   class name.
3. **Every serialized field has `order` and `value_type`.** `order` is 1-based, in output order.
4. **Physical quantities declare their unit** with LinkML's structured slot: `unit: {ucum_code: "kV"}`. The mapper's
   `Field` target writes the same unit in the `.cimtbl` header (spelled for pint: schema `Ohm/mile`, header
   `ohm/mile`). Never convert in the schema or reader.
5. **Defaults match the native format, and where they live depends on the format.** Note where each default
   comes from.
   - **Positional formats** (RAW, MATPOWER: every field is written): `ifabsent` (`float(1.0)`, `int(1)`,
     `string("")`, `"true"`), so write → read restores them.
   - **Keyword formats** (DSS, GLM: an unset property is left out): a `<fmt>_default` annotation
     (`dss_default: float(1.0)`), never `ifabsent`. `ifabsent` makes the reader fill every slot, and the writer then
     writes them all back. The mapper fills an unset slot from the annotation and lists it as `# defaulted`.
6. **Python-friendly field names**, with the native spelling in `native_name` (`dss_name` / `raw_name` are also
   read) when they differ: `voltage_magnitude` with `native_name: "VM"`.
7. **`annotations` is for serialization only.** CIM information goes in `exact_mappings` / `close_mappings` /
   `related_mappings`, `comments` and `todos`, which gen-doc renders. Nested CIM data in annotations is invisible.
8. **Mapping targets are cim18v17 names.** No `WireSpacingInfo`, `TransformerEndInfo` catalog or other removed
   CIM 17 classes (see the `conductor-geometry` skill). Seeded schemas still carry some of these in comments;
   fix them when you touch the class.
9. **Regenerate after every YAML change** (`gen-python`), and commit YAML and generated module together.

## Annotation vocabulary

`cimhub_core.serialization.get_schema_annotations(cls)` only loads a class's annotations (and the top-level `unit`,
`range`, `required`, `ifabsent`, `identifier`, ... of each slot). It formats nothing: each spoke reads the keys it
needs and writes its own text.

| Key | Meaning | Read by |
|---|---|---|
| `order` | position in the record, 1-based | every spoke's writer |
| `value_type` | `int`, `float`, `string` | RAW (`record_layout`, `raw34_writer`) |
| `line_number` | which line of a multi-line record (default 1) | RAW |
| `count` | list length of a fixed-size `multivalued` slot (the 12 RATEs) | RAW |
| `structural` | filled by the reader, not a field of the record text | RAW |
| `precision`, `width`, `quote`, `quote_char` | float decimals; pad to a width; wrap in quotes (default `'`) | RAW |
| `dss_name`, `dss_format` (`matrix`) | the property name in a `.dss` command; matrix formatting | OpenDSS (`dss_writer`) |
| `dss_default`, `glm_default` | the native default of an unset keyword property | the mapper |
| `native_name` | the field's name in the native format | GridLAB-D (`glm_schema`, indexed by GLM type name, walking `is_a`) |
| `serialize_if` | the slot is written only when the condition holds (a 3-winding transformer's third winding) | RAW (`importer/cimtbl/transformer.py`) |

Don't add a key a spoke doesn't read: an unread key is silently ignored. Full patterns are in
[reference.md](reference.md).

```yaml
active_power:
  description: Active power demand.
  range: float
  ifabsent: float(0.0)
  unit:
    ucum_code: "MW"
  annotations:
    order: 3
    value_type: float
    precision: 3
```

## CIM mapping slots

| Slot | Use for | Usual mapper field kind |
|---|---|---|
| `exact_mappings` | same concept, value copied (with its unit) or through a code table | copied, mapped |
| `close_mappings` | same concept through a formula | derived |
| `related_mappings` | structural traversal or partial overlap (`bus1` ↔ `Terminal.ConnectivityNode`) | structural |
| none + `comments` | native-only concept, no CIM home needed (`like`) | untranscribed |
| none + `todos` | needs a CIM extension (DSS capacitor series `R`) | untranscribed |

Always add a `comment` saying how the field reaches CIM: the `.cimtbl` column and unit, the code table, or the
named derivation. Put a class-level `exact_mappings` on the class for its CIM equivalent.

```yaml
kvar:
  range: float
  multivalued: true
  close_mappings:
    - cim:LinearShuntCompensator.bPerSection
  comments:
    - >-
      Copied to nomQ (kVAr). bPerSection (S) is derived from kvar and kv per step by a named,
      tested function; the formula is written as a comment in capacitor.cimtbl.
```

## Anti-patterns

- Editing the generated `<fmt>.py` by hand.
- A bare-string `unit: MW`. Use `unit: {ucum_code: ...}`.
- Cryptic field names (`I`, `VM`, `PL`) with no `native_name`.
- Import formulas that construct CIM objects in schema comments (`cim.ActivePower(x, 'MW')`). Describe the
  `.cimtbl` column instead.
- Hand-coded format strings in a writer because a field lacks annotations. Fix the schema.

## Checklist

- [ ] One class file per record type, imported from `main.yaml`.
- [ ] Each class has one `identifier: true` field and a class-level CIM mapping or comment.
- [ ] Every serialized field has `order` and `value_type`.
- [ ] Physical quantities have `unit: {ucum_code: ...}`; optional fields carry their native default (rule 5).
- [ ] Mapping slots name cim18v17 classes and attributes; every mapped field has a `comment`.
- [ ] `gen-python` regenerated; reader/writer round trip and the mapper's `check_fields` test pass.
