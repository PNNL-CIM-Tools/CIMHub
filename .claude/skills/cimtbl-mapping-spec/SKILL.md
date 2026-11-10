---
name: cimtbl-mapping-spec
description: How to write and review a spoke's `docs/CIMTBL_MAPPING.md` - the per-native-table field classification (copied / mapped / structural / derived / untranscribed), artifact order, identity, derived formulas, fail-fast list and expected differences. Use before a spoke's importer wave starts, when classifying the fields of a native class, or when a mapper and its spec disagree.
---

# Writing a `CIMTBL_MAPPING.md`

Each importer spoke has one spec, `cimhub_<fmt>/docs/CIMTBL_MAPPING.md`. It is approved by the user **before** the
spoke's wave writes mappers. It answers, per native table, where every native field goes, so a reviewer can check
the artifact against the source without reading mapper code.

The spec and the mapper's `FIELDS` are one classification in two forms. The field tables are generated from the
code, and the completeness test (`check_fields`) checks the code against the LinkML schema. Contract: skill
`cimtbl-import-contract`. Shapes: skill `cimtbl-shapes`. Worked example (DSS LineCode mtx601) and a section
template: [reference.md](reference.md).

## Method: classify real fields, never invented ones

1. **List the real fields.** Read native records with the spoke's reader and generate the skeleton:
   ```python
   from cimhub_core.cimtbl import fields_table, fields_stub
   print(fields_table(schema.Linecode, native.list_by_class(schema.Linecode)))   # markdown, with samples
   print(fields_stub(schema.Linecode, records))                                  # FIELDS of Field('TODO')
   ```
   `cimhub_core.scaffold.scaffold_mapper(...)` writes the same stub into `importer/cimtbl/<table>.py`.
2. **Pick the shape** from `cimtbl-shapes`. If none fits, add the shape first; the spec never defines a layout.
3. **Classify each field as exactly one kind**, with a target or a reason:

   | kind | test to apply | target column says |
   |---|---|---|
   | copied | the value lands unchanged, the same in every row the record makes for that class | `Class.column (unit)` |
   | mapped | a code or enum, through a plain dict | the table name (`LENGTH_UNIT`, `CONNECTION_KIND`) and what it selects |
   | structural | it decides rows: one record → several rows, a value on one specific row, a row in another file | which rows and where |
   | derived | CIM has no attribute for the source quantity, so a value is computed | the named function and formula, with units |
   | untranscribed | no CIM home in the network profile parts | why (tool metadata, reliability data, catalog rating D9, gap) |

4. **Fill the samples from real models,** not memory. Name the decks or files the samples came from.
5. **Run a sweep.** Map every test model the repo has; list each stop (deck, count, cause, open point).
6. **Regenerate the table from the code** once the mapper exists: `fields_table(NATIVE_CLASS, records, fields=FIELDS)`.
   The spec table and `FIELDS` must never drift.

## Classification rules

- A value on one row only (end 1's kV vs end 2's kV) is **structural**, not copied.
- A unit that depends on the record (DSS `units=mi`) is a template in the target: `ohm/{length}`.
- A field whose value picks the meaning of another field (a units code, a LL/LN flag) is **mapped**, and its note
  says what it selects.
- A field with a CIM home that no test model sets is **untranscribed** with a note naming the home ("home
  `PerLengthImpedance.rg`; not mapped until a deck sets it"). Map it when a model sets it.
- Reader-resolved fields (`like=`) are untranscribed with that reason.
- Catalog-level ratings have no CIM 18 template home: instance `OperationalLimitSet` or untranscribed (D9).
- Never classify a matrix as "derived from geometry": geometry is its own shape (skill `conductor-geometry`).
- A formula is written once, in the spec and on the function's docstring, and as a table comment in the artifact.

## Required contents

1. **Header:** status, links to the contract and plan docs in `.development/`, the models the samples came from.
2. **Artifact files and order:** native class → artifact stem (D4, the LinkML schema module) → shape(s) → depends
   on. This order is the master's `Import` order and `MAPPING_ORDER`.
3. **Per native table, one section** (anchor = the artifact stem, cited by the provenance header):
   - mapper module and function, atoms and test file;
   - **identity:** prefix, case rule, child-row suffixes, identifier columns;
   - **form/selection rules:** which records become which shape (matrix vs sequence code, 1- vs 3-phase);
   - **values:** how the reader types them (float vs text) and how tables group by header;
   - **field classification table** (generated);
   - **derived:** every function, formula and unit path;
   - **defaults** the format applies when a field is absent, and how the artifact records them;
   - **fail fast:** every condition the mapper raises on;
   - **sweep result** and open points;
   - **reader/schema findings** (wrong slot types), filed against the reader, not worked around in the mapper.
4. **Code tables:** each `lookup` table, its keys and CIM values; a table two spokes share moves to `cimhub_core.codes`.
5. **CIM 18 gaps:** fields with no home that a model needs, also logged in the CIM 18 gap register.
6. **Reference model and expected differences:** the model whose artifact directory is the committed golden, how it is
   produced and reviewed, and every known difference from a hand translation (hand translations may carry realism
   corrections a verbatim importer must not make; list them, never hide them).

## Anti-patterns

- Classifying from documentation or memory instead of `fields_table` output.
- "Copied" with a unit conversion in the note: copied means verbatim with the source unit in the header (I2).
- A field split across two kinds, or a field left out because it "looks unused".
- Fixing a source error in the mapper so the import matches a corrected hand translation.
- A spec drafted after the mapper, or edited by hand when `FIELDS` changed.
- A vendor or private model as the worked sample in a public spoke's spec.
