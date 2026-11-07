# CIMHub rewrite plan (fresh start from CIMHub_2_0)

**Status:** approved 2026-11-07. F0 + F1 in progress.

## Context

The `.cimtbl` rewrite (`CIMTBL_REWRITE_PLAN.md`) replaces most spoke code, and the exporter port
(`EXPORTER_RETRIEVAL_ASSESSMENT.md`) replaces most of the rest. Split decision S3 (`PUBLIC_REPO_SPLIT_PLAN.md`)
had already decided that no history carries over, and that the public repo starts from one snapshot after Phase 6.
CIMHub_2_0 has 345 commits and a 775 MB `.git` (deleted 35-39 MB IEEE 9500 XMLs, vendor names in commit messages).
After the rewrite its blame would point at deleted lines.

So the snapshot moves from Phase 6 to now. We write the new architecture directly into
`PNNL-CIM-Tools/CIMHub`: private, created 2026-11-06, one `Initial commit` (LICENSE, README, .gitignore).
Nothing is published until release review.

Decisions (user, 2026-11-07):

| # | Decision |
|---|---|
| F1 | **CIMHub holds only the cleared packages**: `cimhub_core`, `cimhub_opendss`, `cimhub_gridlabd`, `cimhub_distopf`, `cimhub_matpower`, `cimhub_raw`, `cimhub_chat`, `cimhub_gdm`. Vendor spokes are rewritten later in CIMHub_2_0 (private) against CIMHub core. Then CIMHub can go public after release review with no second split. |
| F2 | **Seed + fresh.** Code that is already cim18v17-ready and contract-conformant gets copied, reviewed file by file and committed as a labeled seed: Phase 1 helpers, shapes, LinkML schemas, native readers/writers, the DSS slices. Mappers, exporters and tests are written fresh. |
| F3 | **Shared lookup = both directions.** Import: canonical native-code → CIM-enum tables used through `lookup`. Export: the core getters (assessment §4), with `get_qty` and `diff_models` taken from cimtables, never re-implemented. |
| F4 | **Rules → Claude skills; plans → `.development/`.** |

This supersedes S1 ("cut over after Phase 6") and the snapshot timing in S3. S2, S4 and the §3 split-readiness
rules still apply, and the repo layout now enforces them.

## Upstream-first rule (new invariant I9)

Core only holds what no upstream library provides. Before adding a core function, check cimtables (`set_attr`,
`impedance.z_base`, `get_qty`, `diff_models`, `document.*`, `load_model`), cimbuilder, cimgraph, cimprofiles
(units, identity) and cim-topology. If the capability belongs upstream but is missing, file it in that repo's
requests doc. Don't write a local stand-in. Per-module verdicts are in the core inventory table below.

## Target layout

```
CIMHub/
  pyproject.toml            # uv workspace: 8 members; ../CIM-* path sources until their releases (as today)
  CLAUDE.md                 # short: invariants I1-I9, skill index, ownership rules
  .claude/skills/<rule>/SKILL.md
  .development/             # time-bound plans + assessments (this rewrite's plan, wave plans, requests docs)
  cimhub_core/              # thin: cimtbl helpers, CimtblImporter, code tables, export getters, testing harness
  cimhub_<fmt>/             # schema/ reader/ writer/ importer/cimtbl/ exporter/ tests/{atoms,...}
  tests/cross_format/       # tier 4, public pairs only
  scripts/test-all.sh
```

Distribution names stay (`cimhub-core`, `cimhub-opendss`, …) for PyPI continuity. The version jumps to **3.0.0a0**:
the API break (cim18v17 only, `to_cimtbl`) is a major one, and it keeps CIMHub_2_0's `2.1.0a0` working tree
apart from the new line.

## Skills (F4)

Each lasting rule doc becomes one skill: a trigger description and a tight body. Long tables go to a `reference.md`
next to `SKILL.md`. Ported from `cimhub_core/src/cimhub_core/development/`:

| skill | source doc(s) |
|---|---|
| `cimhub-style` | `STYLE_GUIDE.md` |
| `cim-units` | `UNITS.md` (rewritten for the cimtbl importer: source units in headers, `get_qty` on export) |
| `conductor-geometry` | `CONDUCTOR_GEOMETRY_ANTI_PATTERNS.md` |
| `cimtbl-import-contract` | `CIMTBL_IMPORT_CONTRACT.md` + invariants I1-I8 |
| `cimtbl-shapes` | `SHAPE_CATALOG.md` (+ `shapes/*.cimtbl` stay in core as tested examples) |
| `cimtbl-mapping-spec` | §3 worked example + Phase 2 spec template (switch the exemplar to DSS, per split rule 4) |
| `linkml-native-schema` | `LINKML_TEMPLATE.md` |
| `reader-writer` | `READER_WRITER_GUIDE.md`, four-ABC rule from `CONVERTER_API.md` |
| `export-getters` | assessment §4 + `EXPORTER_FORMAT_EXPECTATIONS.md` §8.2 semantics |
| `atom-tests` | `ATOM_TEST_CREATION.md` + rewrite plan Phase 4 tier table |
| `split-readiness` | split plan §3 rules + leak-gate command |

`.development/` holds only live, time-bound docs: this plan and `UPSTREAM_REQUESTS.md`. A spoke's wave plan and
mapping spec live in that spoke (`cimhub_<fmt>/docs/`) from its wave on. The old assessments and request history
(`EXPORTER_RETRIEVAL_ASSESSMENT.md`, `EXPORTER_FORMAT_EXPECTATIONS.md`, `TEST_FIXTURE_ARCHITECTURE.md`,
`CIMTABLES_REQUESTS.md`) are not copied, because each has vendor-specific content. Their lasting rules are in the
skills; the originals stay in the private CIMHub_2_0 as history.

## Shared lookup (F3)

- **Import code tables:** `cimhub_core/codes.py` holds plain dicts, one per CIM enum (`PhaseCode` strings,
  `WindingConnection`, `SinglePhaseKind`, load model kinds), keyed by spelling and used through the existing
  `cimtbl.lookup(table, value, slot=, record_id=)`, which fails fast on an unmapped value. A table moves into core
  only once two spokes use it. Format-only spellings (DSS `.1.2.3` bus suffixes, GLM `BCN`) stay in the spoke.
  Values are checked against the cimprofiles enum, so a typo fails at import time.
- **Export getters:** `cimhub_core/getters/`, one module per CIM concept (terminals/phases, line impedance,
  spacing, transformer, shunt, limits). Each returns `NamedTuple`s, reads cim18v17 only, and uses `cimtables.get_qty`
  for every unit and base conversion. Tested on cimtables-loaded `IEEE13_CDPSM` / `IEEE13_original`.

## Phases

**F0. Bootstrap** (one session, before any parallel work)
1. Workspace `pyproject.toml` with the 8 members, the `../CIM-Graph`, `../CIM-Tables`, `../CIM-Builder` and
   `../CIM-Profiles` path sources, ruff/pytest config, and `scripts/test-all.sh`. `uv lock` once. After this,
   no parallel session touches the root lockfile (as in rewrite plan 1.0).
2. `CLAUDE.md`, the skills and `.development/` docs listed above. Add a "superseded → CIMHub" banner to the three
   plan docs in CIMHub_2_0 (`PUBLIC_REPO_SPLIT_PLAN.md` S1/S3, `CIMTBL_REWRITE_PLAN.md` header,
   `EXPORTER_RETRIEVAL_ASSESSMENT.md` header).
3. CI: `ci.yaml` (checks out the sibling `CIM-*` repos until they are released). Leak-gate step from split plan §4.1.
4. `AUTHORS` crediting CIMHub_2_0 contributors (S3).

**F1. Core seed + fresh core.** Module verdicts come from the inventory (checked against upstream source, 2026-11-07):

| verdict | modules (old repo `cimhub_core/src/cimhub_core/`) |
|---|---|
| COPY | `base.py`, `cimtbl.py`, `cimtbl_testing.py`, `graph_model.py`, `serialization.py`, `topology.py` (native BusGraph; cim-topology works on CIM models, so it is not a substitute), `names.py` (export naming only), `registry.py` (+ fail on duplicate keys), `scaffold.py` (then regenerate its templates), `get_utils/mermaid.py` (native diagrams; use `cimgraph.utils.mermaid` for CIM), `development/shapes/` → `cimhub_core/shapes/` |
| REPLACE-WITH-UPSTREAM | `connectivity/` → `cimtables.connectivity` / `graph_write.resolve`; `transformations/transformers/per_unit.py` → `cimtables.impedance.z_base`, `get_qty`, `(pu system)` headers; `units.py` → `cimprofiles.units` (native aliases `sf`, `$` → filed upstream); limit setters → cimbuilder `OperationalLimitSetBuilder` |
| PORT (into fresh `getters/`) | base-frequency, operational-limit, shunt and tap-changer reads, rebuilt on `cimtables.get_qty` with cim18v17 attribute names |
| PORT (into fresh `derived/`) | star↔mesh, short-circuit-test → mesh/core math, trilateration (→ `XYSpacing(isTemplate)`), ZIPV. Pure, named, tested functions: the rewrite plan's "derived values come only from named, tested functions". Each one is filed as an upstream candidate in `CIMTABLES_REQUESTS.md` / CIM-Builder |
| MOVE | `mcp/` → `cimhub_chat` (its only user) |
| DROP | `domains.py`, `get_utils/get_base_voltage|get_substation|get_voltage_level` (dead, cim17v40), `wire_position_to_wire_spacing`, load-response get-or-create (I5), `tests/atoms*.py`, `assertions*.py` |

- Fresh: `codes.py`, `getters/`, `derived/`, **built on demand during F2** (decided 2026-11-07). Each getter,
  code table and derived function lands with its first consumer, the DSS mapper or exporter, so none is designed
  without a caller. The PORT rows above are the inventory to draw from.
- Exit: `scripts/test-all.sh core` passes, except the 3 template-shape tests blocked on UPSTREAM_REQUESTS U2. The
  "no legacy profile" check is a grep of `cimhub_*/src` until U1 lands: today cimgraph itself loads cim17v40 and
  cimhub_2023 at import.

**F1 status 2026-11-07:** seed copied and trimmed. 116/120 core tests pass; the 4 failures are U2 (3) plus the
shape-catalog test, which reads the `cimtbl-shapes` skill.
- Upstream caveats to file, not to work around: about 15 cimbuilder modules still import cimhub_2023/cim18gad
  (`new_base_voltage` …), and the cim-topology profile is unverified. Spokes use only the cim18v17 builders.

**F2. Wave 1: OpenDSS** (`DSS_REWRITE_PLAN.md`, decisions DSS-1..12 still open)
- Seed: the LinkML schema, `DssReader`/writer (with the four reader fixes), `importer/cimtbl/` slices (LineCode,
  inline Transformer, `bus_graph.py`), and their atoms/goldens.
- Fresh: the remaining mappers (S3-S5 …), the orchestrator `dss_to_cimtbl.py`, the cim18v17 exporter on the getters,
  and tier 1-3 tests.
- Exit: `dss_to_cim` and `cim_to_dss` round-trip `IEEE13_CDPSM` with expected differences listed.

**F2'. GDM** (own session, builder-native, D11). Starts after F1; owns only `cimhub_gdm/`.

**Spoke seed rule (all waves).** The inventory confirmed that no reader or writer imports a CIM profile, so each
spoke's `schema/` (LinkML yaml + generated dataclasses), reader and writer are copied as the seed. Every converter
tree is written fresh. RAW drops `schema/data_profile/raw_extension.py` and `models/rawModel.py` (both cim17v40).
GDM's `gdm_to_cim` tree (cimhub_2026) is rewritten builder-native.

**F3+. Remaining cleared spokes**, one wave each, same pattern: RAW and MATPOWER (bus-branch shapes), then
GridLAB-D, then DistOPF; chat adapts last. Each needs its `CIMTBL_MAPPING.md` approved first.

**F-end.** Release cim-graph 0.6 / cimtables / cim-builder / cimprofiles, switch to version pins, PyPI release,
PNNL release review, then flip CIMHub public. CIMHub_2_0 deletes its cleared packages and pins `cimhub-core>=3`
from PyPI (S4).

## CIMHub_2_0 after F0

- Frozen for the cleared spokes: no new work there. It stays the **regression oracle**: old converters produce
  reference outputs that the new tier-3 tests can compare against, read-only. Copy outputs, never import code.
- Vendor spokes (cyme, powersimulator, synergi, …) keep working on their old code until their own rewrite.
  Their rewrite then targets CIMHub core through an uncommitted local `uv` path override.
- The CYME `TransformerDB` slice and its spec stay private. The core contract tests that used it switch to the DSS
  LineCode / transformer slices.

## Verification

- F0: `cd ~/CIMHub && uv sync && uv run pytest` (empty suite passes); every skill appears in a fresh Claude session's
  skill list; the leak-gate grep prints nothing.
- F1: core tests pass; `grep -rn "data_profile.cim17v40\|cimhub_2026" cimhub_*/src` prints nothing.
- Per wave: tier 1 golden equality, tier 1b bind, tier 2 field-by-field export, tier 3 round trip;
  `scripts/test-all.sh` green.
- Before going public: a clean clone outside `~/` with released upstreams: `uv sync && scripts/test-all.sh`,
  `uv build`, `twine check`.
- Nothing gets committed without an explicit "commit" from the user.
