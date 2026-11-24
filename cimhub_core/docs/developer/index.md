# Developer docs

How `cimhub_core` is built: the base classes every converter implements, the helpers that turn native records into
`.cimtbl` text, the getters that read CIM back, and the test harness. Each package (spoke) is one native format
that depends on core and never the other way round. These pages are the map; the rules a change must keep are
listed below, and the longer how-to rules live in the repository's
[skills](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/.claude/skills).

## The two pipelines

```mermaid
flowchart LR
    nf["native file"] -->|"Reader.read_all"| nm["native GraphModel"]
    nm -->|"to_cimtbl<br/><small>pure mappers</small>"| docs[".cimtbl documents"]
    docs -->|"cimtbl_to_cim<br/><small>write, then cimtables.load_model</small>"| cim["cim18v17 model"]
    cim -->|"Exporter.to_model<br/><small>core getters</small>"| nm2["native GraphModel"]
    nm2 -->|"Writer.write"| nf2["native file"]
```

Only the reader and the writer touch the filesystem (plus `cimtbl_to_cim`, which writes the `.cimtbl` artifact so
that what a reviewer reads is exactly what was built). Every stage returns something you can inspect.

| Page | Covers |
|---|---|
| [Architecture](architecture.md) | Hub and spoke, the import and export flows, what core holds, what upstream owns, the spoke layout. |
| [Converter API](converter-api.md) | The five base classes, `GraphModel`, the one-call functions of each package, options, the scaffold. |
| [The .cimtbl import contract](cimtbl.md) | `cimhub_core.cimtbl`: `Field` classification, `cell`, `mrid`, `lookup`, `cimtbl_to_cim`. |
| [Canonical shapes](shapes.md) | The `.cimtbl` table shapes in `shapes/` that every importer emits. |
| [Writing a getter](writing-getters.md) | How a getter in `getters/` is written: NamedTuple returns, `get_qty`, explicit resolution order. |
| [Units](units.md) | How physical quantities move through import and export. |
| [Testing](testing.md) | Atoms, goldens, the test types and the `cimtbl_testing` helpers. |
| [Building the docs](docs.md) | One mkdocs site per package, `scripts/build-docs.sh`, notebooks, the generated schema reference. |

## Modules

Everything is under
[`cimhub_core/src/cimhub_core/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_core/src/cimhub_core).

| Module | Role |
|---|---|
| `base.py` | The ABCs: `FormatReader`, `FormatWriter`, `FormatImporter`, `CimtblImporter`, `FormatExporter`. |
| `graph_model.py` | `GraphModel`: the indexed `{class: {identifier: instance}}` store for native LinkML dataclasses. |
| `cimtbl.py` | Import helpers: `cell`, `mrid`, `lookup`, `Field`, `copied_columns`, `check_fields`, `fields_table`, `fields_stub`, `cimtbl_to_cim`. |
| `cimtbl_testing.py` | Atom-test harness: `cim_scope`, `atom_documents`, `assert_matches_golden`, `assert_text_matches_golden`, `record_diff`. |
| `getters/` | One module per CIM concept (terminals, line impedance, spacing, transformer, shunt, tap changer, limits, DER, schedules and more). cim18v17 only. |
| `derived/` | Pure, named functions for values CIM has no attribute for: Kron reduction, capacitance to susceptance, sequence to phase matrix, spacing, control band, regulator settings. |
| `shapes/` | One example `.cimtbl` file per canonical table shape. |
| `names.py` | Export naming: `resolve_name_source`, `export_name` (the `name_source` switch). |
| `export_slots.py` | `Slot`, `check_slots`, `with_default`, `slots_table`: the export mirror of the importer's `FIELDS`. |
| `load_response.py` | `zip_fractions()`: the three shared constant-power, impedance and current load models. |
| `time_points.py` | Parquet sidecar tables for schedule time points (needs the `time-points` extra). |
| `serialization.py` | `get_schema_annotations`: a native class's LinkML slot annotations. Each spoke formats its own records from them. |
| `mermaid.py` | `get_mermaid`, `download_mermaid`: diagrams of native dataclasses. |
| `scaffold.py` | `scaffold_package`, `scaffold_mapper`: stubs for a new spoke and for one mapper. |

## Rules that keep it simple

These are the invariants from the repository's
[`CLAUDE.md`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/CLAUDE.md). A change that breaks one needs a
reason in the pull request.

| # | Rule |
|---|---|
| I1 | The `.cimtbl` artifact is the only input to CIM. CIM is built from the formatted text, never from mapper objects. |
| I2 | Values are copied verbatim, in source units, with the unit in the column header (`ratedS (kVA)`, `r (ohm/km)`). No unit math in spoke code. |
| I3 | Every field of a mapped native class is classified: copied, mapped, structural, derived or untranscribed. A test checks that the classification covers every slot. |
| I4 | One artifact file per native table. The master `Import`s them in dependency order, catalogs first. |
| I5 | Spokes never construct CIM objects: no `cim.X(...)`, no `z_base`, no terminals in importer code. |
| I6 | CIM 18 templates, never `*Info` catalogs: `TransformerTankConfiguration`, `WireConfiguration`, `XYSpacing(isTemplate)`. |
| I7 | Mappers are pure (objects in, documents out). Only readers and writers touch the filesystem. |
| I8 | Fail fast: unknown fields, unmapped enums and unresolved references all raise. IDs are quoted, never sanitized. |
| I9 | Upstream first. Before adding a core function, check cimtables, cimbuilder, cimgraph, cimprofiles and cim-topology. If the capability belongs upstream, file it in [`UPSTREAM_REQUESTS.md`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.development/UPSTREAM_REQUESTS.md); do not write a local stand-in. |

Topology (spanning trees, islands, voltage zones, BaseVoltage walk) is `cimtopology.core`, which is
format-agnostic. A spoke builds a `Network` from its native records and never writes its own graph walk.

## Working on it

```bash
uv sync                       # the ../CIM-* path sources are editable sibling checkouts
scripts/test-all.sh core      # one package's tests; with no argument, one pytest process per package
scripts/leak-gate.sh          # must print "leak-gate: clean" before every commit
```

Run one pytest process per package, never one over the whole repository: cimtables sets the CIM profile and the
model scope process-wide, so suites must not share an interpreter. Tests that load `.cimtbl` run inside
`cimhub_core.cimtbl_testing.cim_scope()`. `CIMHUB_UPDATE_GOLDENS=1` regenerates goldens; review the diff.

The sibling checkouts are what runs, including their uncommitted changes. Only the cleared packages live in this
repository; the [split-readiness skill](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/split-readiness/SKILL.md)
says what may be added.
