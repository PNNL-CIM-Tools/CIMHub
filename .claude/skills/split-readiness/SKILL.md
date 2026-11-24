---
name: split-readiness
description: Rules that keep CIMHub releasable as a public repo - only the cleared packages live here, vendor spokes are never imported or referenced, fixtures have a documented public origin, and no vendor schema or manual content is copied - plus the leak-gate commands. Use when adding imports, test fixtures, docs, comments or dependencies anywhere in this repo, and before any commit or release review.
---

# Split readiness

CIMHub is private now and goes public after release review, with no second split. Everything committed here
must be publishable as is.

## What lives here

| Class | Packages |
|---|---|
| cleared (in this repo) | `cimhub_core`, `cimhub_opendss`, `cimhub_gridlabd`, `cimhub_distopf`, `cimhub_matpower`, `cimhub_raw`, `cimhub_chat`, `cimhub_gdm` |
| vendor spokes (private repo only) | `cimhub_powersimulator`, `cimhub_cyme`, `cimhub_synergi`, `cimhub_powerworld`, `cimhub_pscad`, `cimhub_arcgis`, `cimhub_bmopf`, `cimhub_repair`, `cimhub_s223` |

Vendor spokes depend on CIMHub core, never the other way round. They consume `cimhub-core` the way any outside
user does: from PyPI, or through an uncommitted local `uv` path override while core is unreleased.

## Rules

1. **Never import a vendor spoke**, in `src/` or `tests/`. That includes lazy imports and imports inside
   `try/except ImportError`.
2. **Never reference a vendor spoke by path or package name**, in code, comments, docs, `.development/` plans or
   test data paths. If a plan must mention one, name the format (CYME, Synergi), not the package or a file in it.
3. **No mixed public/vendor tests.** Cross-format tests here (`tests/cross_format/`) pair cleared formats
   only. A test that needs a vendor format lives with that vendor spoke.
4. **Every fixture has a documented public origin**: IEEE test feeders, GridAPPS-D Powergrid-Models, EPRI test
   circuits, MATPOWER cases. Record the source, URL, license and any local edits in the fixture directory's README.
   No vendor-derived, utility or customer models, ever. A reference output copied from the old converters counts as
   public only if its input model does.
5. **Large models stay out of git.** Anything over 10 MB goes to the external golden store (Zenodo); the repo
   keeps small yardsticks.
6. **Name vendor formats, don't copy them.** Docs may say "CYME" or "Synergi", but must not reproduce a vendor
   schema, file layout, field list or manual text. Worked examples use public formats: DSS, GLM, RAW, MATPOWER.
   (PSS/E RAW is cleared: its schema here describes the public RAW layout.)
7. **Dependencies are versioned, not pathed.** Each package's `pyproject.toml` declares `cimhub-core` with a
   version range. Workspace and sibling `../CIM-*` path sources go only in the root `[tool.uv.sources]`, and the
   `../CIM-*` ones are replaced by released pins before going public.
8. **No private paths.** No absolute home-directory paths and no paths into the old private monorepo. Copy what
   you need (with its origin noted) instead of pointing at it.

## Leak gate

Run from the repo root before committing. Every command must print nothing (the third lists files to justify or
remove).

```bash
# 1. imports of a vendor spoke (split plan §4.1)
grep -rnE "(from|import) cimhub_(powersimulator|cyme|synergi|powerworld|pscad|arcgis|bmopf|repair|s223)\b" \
    cimhub_* tests scripts

# 2. any reference to a vendor spoke by name or path (this skill is the one allowed place)
grep -rnE "cimhub_(powersimulator|cyme|synergi|powerworld|pscad|arcgis|bmopf|repair|s223)\b" . \
    --exclude-dir=.git --exclude-dir=.venv --exclude-dir=split-readiness

# 3. files over 10 MB
find . \( -path ./.git -o -path ./.venv \) -prune -o -type f -size +10M -print
```


## Anti-patterns

```python
# BAD: optional vendor import "just in case"
try:
    from cimhub_<vendor> import VendorReader
except ImportError:
    VendorReader = None
```

```python
# BAD: comment pointing at a vendor spoke
# see cimhub_<vendor>/docs/refactor/CIMTBL_MAPPING.md
# GOOD: describe the pattern itself
# Limits are attached to both the equipment and its terminal so either lookup resolves.
```

- A fixture copied from a utility model "because it's a good test case".
- A worked example built on a vendor format's tables.
- `cimhub-core = { path = "../cimhub_core" }` inside a spoke's `pyproject.toml`.
