# CIMHub: Claude Code instructions

CIMHub converts native power-system formats (OpenDSS, GridLAB-D, PSS/E RAW, MATPOWER, DistOPF, GDM) to and from
CIM, **cim18v17 only**. Importers map native records to `.cimtbl` text, and cimtables builds the CIM from that
text. Exporters read CIM through the core getters. The plan is `.development/REWRITE_PLAN.md`; open upstream asks
are in `.development/UPSTREAM_REQUESTS.md`.

## Invariants (every change is checked against these)

| # | Rule |
|---|---|
| I1 | The `.cimtbl` artifact is the only input to CIM. CIM is built from the formatted text, never from mapper objects. |
| I2 | Values are copied verbatim, in source units, with the unit in the column header (`ratedS (kVA)`, `r (ohm/km)`, `x (pu system)`). No unit math in spoke code. |
| I3 | Every field of a mapped native class is classified: copied, mapped, structural, derived or untranscribed. A test checks that the classification covers every slot. |
| I4 | One artifact file per native table. The master `Import`s them in dependency order (catalogs first). |
| I5 | Spokes never construct CIM objects: no `cim.X(...)`, no `z_base`, no terminals in importer code. |
| I6 | CIM 18 templates, never `*Info` catalogs: `TransformerTankConfiguration`, `WireConfiguration`, `XYSpacing(isTemplate)`. |
| I7 | Mappers are pure (objects in, documents out). Only readers and writers touch the filesystem. |
| I8 | Fail fast: unknown fields, unmapped enums and unresolved references all raise. IDs are quoted, never sanitized. |
| I9 | Upstream first. Before adding a core function, check cimtables, cimbuilder, cimgraph, cimprofiles and cim-topology. If the capability belongs upstream, file it in `UPSTREAM_REQUESTS.md`; don't write a local stand-in. |

## Skills: load the matching one before writing code

| skill | use it when |
|---|---|
| `cimhub-style` | writing any code here |
| `cim-units` | anything with a physical quantity, on import or export |
| `conductor-geometry` | touching any line/cable importer, exporter or shape |
| `wire-configuration` | choosing how a line names its impedance: a template LineCode, its own impedance, or geometry |
| `cimtbl-import-contract` | writing an importer or mapper |
| `cimtbl-shapes` | choosing which tables and columns a mapper emits |
| `cimtbl-mapping-spec` | writing a spoke's `docs/CIMTBL_MAPPING.md` |
| `linkml-native-schema` | writing or editing a native LinkML schema |
| `reader-writer` | writing a native reader or writer |
| `export-getters` | writing an exporter, a core getter or a code table |
| `atom-tests` | writing tests (atoms, goldens, tiers 1-4) |
| `split-readiness` | adding files, fixtures, docs or dependencies (this repo must stay publishable) |

The `.cimtbl` format itself is defined by `cimtables` (its `CLAUDE.md`). Model conventions follow the
`cimtbl-translate` skill in CIMTBL-Models.

## Layout and ownership

- `cimhub_core/`: the thin shared layer (`cimtbl.py`, `cimtbl_testing.py`, `base.py`, `getters/`,
  `derived/`, `shapes/`). Spoke sessions don't edit core; they send requests to the core owner.
- Topology (spanning trees, islands, voltage zones, sorting, BaseVoltage walk) is `cimtopology.core` from
  CIM-Graph-Topology-Processor, which is format-agnostic. A spoke builds a `Network` from its native records and never
  writes its own graph walk.
- `cimhub_<fmt>/`: `schema/`, reader, writer, `importer/<fmt>_to_cimtbl.py` + `importer/cimtbl/<native_table>.py`,
  `exporter/`, `tests/atoms/`, `docs/CIMTBL_MAPPING.md`.
- Only the cleared packages live here. Vendor-format spokes stay in the private CIMHub_2_0 repo and are never
  imported, referenced by path, or used as examples.
- Only the bootstrap session edits the root `pyproject.toml` / `uv.lock`. A spoke is added to the workspace when
  its wave starts.

## Commands

- `uv sync`, then `scripts/test-all.sh` (one pytest process per package; never one whole-repo pytest).
- `scripts/test-all.sh core` runs a single package. `CIMHUB_UPDATE_GOLDENS=1` regenerates goldens; review the diff.
- `scripts/leak-gate.sh` must print `clean` before every commit.
- The `../CIM-*` path sources are editable sibling checkouts, so their working tree (including uncommitted
  changes) is what runs.
