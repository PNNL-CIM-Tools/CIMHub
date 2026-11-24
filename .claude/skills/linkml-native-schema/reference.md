# LinkML native schemas: reference

Companion to [SKILL.md](SKILL.md). `cimhub_core/src/cimhub_core/serialization.py` (`get_schema_annotations`) loads
a class's annotations; the spoke's own writer (`dss_writer`, RAW's `record_layout` and `raw34_writer`, GridLAB-D's
`glm_schema` and `glm_writer`) reads the keys it formats from. A key no spoke reads does nothing: if you need one,
add it to that spoke's writer with a test first.

## Root schema (`main.yaml`)

```yaml
id: https://gridappsd.org/cimhub/<fmt>
name: <fmt>-schema
title: <Format> data model
description: LinkML schema for the <format> file format.
license: https://opensource.org/licenses/BSD-3-Clause
version: 1.0.0

prefixes:
  linkml: https://w3id.org/linkml/
  fmt: https://gridappsd.org/cimhub/<fmt>/
  cim: http://iec.ch/TC57/CIM100#

default_prefix: fmt

imports:
  - linkml:types
  - classes/bus
  - classes/branch
  - types/common_types
```

## Field patterns

Integer with a default:

```yaml
area:
  range: integer
  ifabsent: int(1)
  annotations: {order: 5, value_type: int}
# -> 1
```

Float with precision and a unit:

```yaml
voltage_magnitude:
  range: float
  ifabsent: float(1.0)
  unit: {ucum_code: "pu"}
  annotations: {order: 8, value_type: float, precision: 5}
# -> 1.00000
```

Quoted fixed-width string:

```yaml
name:
  range: string
  ifabsent: string("            ")
  annotations: {order: 2, value_type: string, width: 12, quote: true, quote_char: "'"}
# -> 'BUS_NAME    '
```

Conditional output. A keyword format (DSS, GLM) leaves an unset slot out; a positional format (RAW) writes it blank.
Both are the writer's rule for `None`, not an annotation.

Enum / coded value:

```yaml
status:
  range: StatusEnum
  ifabsent: StatusEnum(1)
  annotations: {order: 5, value_type: int}

# types/common_types.yaml
enums:
  StatusEnum:
    permissible_values:
      IN_SERVICE: {description: In service, meaning: "fmt:1"}
      OUT_OF_SERVICE: {description: Out of service, meaning: "fmt:0"}
```

The mapper maps enum codes to CIM values through a code table and `cimhub_core.cimtbl.lookup`, which fails on an
unmapped code.

## Multi-line records (RAW transformers)

Give each field a `line_number`. RAW's `record_layout` groups fields by line and orders each line by `order`, and
`raw34_writer` joins the lines with newlines.

```yaml
Transformer:
  attributes:
    bus_i:      {annotations: {line_number: 1, order: 1, value_type: int}}
    bus_j:      {annotations: {line_number: 1, order: 2, value_type: int}}
    resistance: {annotations: {line_number: 2, order: 1, value_type: float, precision: 5}}
    reactance:  {annotations: {line_number: 2, order: 2, value_type: float, precision: 5}}
```

## Variable-length values

Declare `multivalued: true` on the slot. RAW's writer formats each item of a fixed-size list (`count`) with the
field's own annotations; a keyword format writes the list as the writer decides. Formats with bracketed arrays (DSS `x=[0 2.5 7]`) handle the brackets in
the writer, keyed off the schema field.

## Shared types

```yaml
types:
  PositiveInteger: {typeof: integer, minimum_value: 1}
  BusNumber: {typeof: PositiveInteger, maximum_value: 999997}
```

Use LinkML constraints for validation: `required`, `minimum_value`, `maximum_value`, `pattern`.

## Network structure vs case data

Keep topology and equipment (`classes/`) apart from snapshot data such as load levels and dispatch (`case/`).

## CIM mapping: worked example (OpenDSS Capacitor)

```yaml
classes:
  Capacitor:
    description: Shunt or series capacitor bank.
    class_uri: dss:Capacitor
    exact_mappings:
      - cim:LinearShuntCompensator
    comments:
      - Per-phase data is carried on LinearShuntCompensatorPhase rows.
    attributes:
      kv:                                  # copied
        range: float
        unit: {ucum_code: "kV"}
        exact_mappings: [cim:ShuntCompensator.nomU]
        comments: ["Copied to nomU (kV)."]
        annotations: {order: 5}
      kvar:                                # derived (and copied to nomQ)
        range: float
        multivalued: true
        close_mappings: [cim:LinearShuntCompensator.bPerSection]
        comments:
          - >-
            Copied to nomQ (kVAr). bPerSection (S) is derived per step from kvar and kv by a named, tested
            function, with the formula commented in the artifact.
        annotations: {order: 4}
      bus1:                                # structural
        range: string
        required: true
        related_mappings: [cim:Terminal.ConnectivityNode]
        comments:
          - "node = bus name without the node suffix; phases = the suffix (.1.2.3 -> ABC)."
        annotations: {order: 1}
      R:                                   # untranscribed, needs an extension
        range: float
        multivalued: true
        comments: ["Filter-capacitor series resistance; no CIM attribute."]
        todos: ["Needs a CIM extension to round-trip."]
        annotations: {order: 9}
      like:                                # untranscribed, native-only
        range: string
        comments: ["DSS template inheritance, resolved by the reader; no CIM equivalent needed."]
        annotations: {order: 21}
```

Decision order for a field:

1. No CIM counterpart and native-only → no mapping slot, a `comment` saying why.
2. No counterpart, needs an extension → no mapping slot, a `todo`.
3. Counterpart exists but no mapper yet → the intended slot plus a `todo` saying the mapper is missing.
4. Same concept, value copied → `exact_mappings`.
5. Same concept through a formula → `close_mappings`.
6. Traversal, structural or partial overlap → `related_mappings`.
7. Always a `comment` on how the field reaches CIM, even for `exact_mappings`.

gen-doc renders a `Mappings` table (exact/close/related + CURIE), `Comments` and `TODOs` per attribute.

## Complete minimal class

```yaml
id: https://gridappsd.org/cimhub/myformat/classes/load
name: load
imports: [linkml:types]
prefixes:
  linkml: https://w3id.org/linkml/
  fmt: https://gridappsd.org/cimhub/myformat/
default_prefix: fmt

classes:
  LoadRecord:
    description: A load record.
    exact_mappings: [cim:EnergyConsumer]
    attributes:
      id:
        identifier: true
        range: string
        required: true
        annotations: {order: 1, value_type: string, width: 12, quote: true, quote_char: "'"}
      bus:
        range: string
        required: true
        related_mappings: [cim:Terminal.ConnectivityNode]
        annotations: {order: 2, value_type: string}
      active_power:
        range: float
        ifabsent: float(0.0)
        unit: {ucum_code: "MW"}
        exact_mappings: [cim:EnergyConsumer.p]
        comments: ["Copied to p (MW)."]
        annotations: {order: 3, value_type: float, precision: 3}
      reactive_power:
        range: float
        ifabsent: float(0.0)
        unit: {ucum_code: "MVAr"}
        exact_mappings: [cim:EnergyConsumer.q]
        comments: ["Copied to q (MVAr)."]
        annotations: {order: 4, value_type: float, precision: 3}
```

Output: `'LOAD_001    ',BUS_1,45.500,12.300`

## Schema tests

- **Serialization:** build a dataclass, call the writer's `serialize`, compare to the exact expected text.
- **Round trip:** reader → writer → reader gives equal objects (see the `reader-writer` skill).
- **Classification:** the mapper's `check_fields(FIELDS, schema.LoadRecord)` fails when a regenerated schema adds
  or drops a slot, so every slot stays classified (invariant I3).
