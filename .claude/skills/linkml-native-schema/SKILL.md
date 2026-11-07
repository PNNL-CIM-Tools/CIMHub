---
name: linkml-native-schema
description: How to write the LinkML schema for a native format (DSS, GLM, RAW, MATPOWER, DistOPF) - layout, identifiers, serialization annotations, units, defaults and CIM mapping slots. Use when creating or editing any YAML under `cimhub_<fmt>/src/cimhub_<fmt>/schema/`, or regenerating its dataclasses.
---

# LinkML native-format schemas

**The LinkML YAML is the single source of truth for a native format's structure and its serialization.**

```
schema YAML (classes + annotations) ─gen-python─▶ dataclasses (never hand-edit)
                                     └─ read at runtime by cimhub_core.serialization (AnnotationSerializer)
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

1. **Exactly one `identifier: true` field per class.** Without it the native `GraphModel` falls back to `ID`,
   `name`, `identifier`, then `id(obj)`, which is non-deterministic.
2. **Class names are unique within a schema.** The annotation loader takes the first YAML file that defines the
   class name.
3. **Every serialized field has `order`, `value_type` and `separator`.** `order` is 1-based, in output order.
   The last field of a record has `separator: ""`.
4. **Physical quantities declare their unit** with LinkML's structured slot: `unit: {ucum_code: "kV"}`. The mapper's
   `Field` target writes the same unit in the `.cimtbl` header (spelled for pint: schema `Ohm/mile`, header
   `ohm/mile`). Never convert in the schema or reader.
5. **Defaults match the native format** (`ifabsent: float(1.0)`, `int(1)`, `string("")`, `"true"`), so
   write → read restores them. Note where a default comes from.
6. **Python-friendly field names**, with the native spelling in `native_name` (`dss_name` / `raw_name` are also
   read) when they differ: `voltage_magnitude` with `native_name: "VM"`.
7. **`annotations` is for serialization only.** CIM information goes in `exact_mappings` / `close_mappings` /
   `related_mappings`, `comments` and `todos`, which gen-doc renders. Nested CIM data in annotations is invisible.
8. **Mapping targets are cim18v17 names.** No `WireSpacingInfo`, `TransformerEndInfo` catalog or other removed
   CIM 17 classes (see the `conductor-geometry` skill). Seeded schemas still carry some of these in comments;
   fix them when you touch the class.
9. **Regenerate after every YAML change** (`gen-python`), and commit YAML and generated module together.

## Annotation vocabulary (implemented in `cimhub_core/src/cimhub_core/serialization.py`)

| Key | Meaning |
|---|---|
| `order` | position in the record, 1-based |
| `value_type` | `int`, `float`, `string`, `bool` |
| `separator` | text written after the field; `""` on the last field |
| `precision` | decimal places for floats |
| `width`, `align` | pad to a width; `left` (default), `right`, `center` |
| `quote`, `quote_char` | wrap in quotes; default char `'` |
| `bool_as_int` | write booleans as `1`/`0` (default true) |
| `line_number` | which line of a multi-line record (RAW transformers) |
| `serialize_if` | `always`, `not_null`, `not_default`, or `custom:<expression over fields>` |
| `native_name` | the field's name in the native format |

Multivalued fields (`multivalued: true`) are joined with the field's separator. Don't add annotation keys the
serializer doesn't read: an unread key is silently ignored. Full patterns are in [reference.md](reference.md).

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
    separator: ","
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
- [ ] Every serialized field has `order`, `value_type`, `separator`; the last has `separator: ""`.
- [ ] Physical quantities have `unit: {ucum_code: ...}`; optional fields have native `ifabsent` defaults.
- [ ] Mapping slots name cim18v17 classes and attributes; every mapped field has a `comment`.
- [ ] `gen-python` regenerated; reader/writer round trip and the mapper's `check_fields` test pass.
