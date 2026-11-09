# Test design

The `atom-tests` skill applies, with one difference: GDM has no native file and writes no artifact. So the native
atom is a small `DistributionSystem` built in Python in the test, the expectation is a hand-written `.cimtbl` golden,
and the comparison is at CIM level (`cimtables.diff_models`, skill rule 9), not text equality. Atoms never use ditto
or gdm-cases, and no serialized GDM JSON (OPEN_DECISIONS 21). ditto (a dev dependency) drives the sweep and the parity
test only.

R7 (`get_qty`) and R8 (`diff_models`) have landed, so every atom asserts `diff_models(golden, built) == []` from the
first one. There is no interim inventory-parity helper.

## Layout

```
tests/conftest.py                          autouse `with cim_scope(): yield`
tests/gdm_atoms.py                         shell_system() and per-family component factories
tests/atoms/prereqs/shell.cimtbl           what to_cim builds for shell_system(): Substation sub_atom, Feeders fdr_atom +
                                           fdr_atom2, BaseFrequency 60, BaseVoltage rows (bv_4p16kv, bv_480v, bv_240v),
                                           ConnectivityNode rows (mRID = bus name, name, BaseVoltage, container)
tests/atoms/<family>/<case>.cimtbl         golden master: the standard header + `Import ../prereqs/shell.cimtbl` + family rows
tests/atoms/e2e/<case>.cimtbl              self-contained end-to-end golden (Phase 5 reference system), no prereq import
tests/test_<family>_import.py              atoms, check_fields, fail-fast, derived-function units per family
tests/test_shared_import.py                shared.py units
tests/test_coverage_import.py              class coverage, time-series drop, name clashes
```

- **Every golden master has the same header** (`Profile`, `Authority` = the CIMHub authority, `Model` = `atom`), equal
  to what `to_cim` uses for `shell_system()`. A test asserts this, so equal mRIDs get equal UUIDs.
- **The shell part declares no `Authority` or `Model`,** so importing it never re-scopes.
- **The second Feeder is for the multi-feeder rule** (OPEN_DECISIONS 1). One switch atom names `feeder=fdr_atom2`, and
  its `EquipmentContainer` must follow it.
- `Import ../prereqs/shell.cimtbl` resolves relative to the importing file.
- The shell prereq is GDM's own (skill rule 4: a prereq only one spoke needs sits next to its atoms), because its
  rows must equal what `to_cim` builds for `shell_system()`.

## Atom test flow (one family)

Atoms run the whole importer. Because `new_feeder_model` (B1) exists, there is no second "family function on a
preloaded network" path to maintain.

1. **Build the system.** `system = gdm_atoms.shell_system()`, plus the family's component(s), from small, explicit
   pydantic construction.
2. **Import.** `built = GdmImporter().to_cim(system)`.
3. **Load the golden.** `golden = cimtables.load_model(GOLDEN)`. This is the "golden binds" check (tier 1b).
4. **Assert.** `assert diff_models(golden, built) == []`.
5. **Derived values,** asserted on the built objects by mRID, each against an independent formula written in the test
   (skill rule 6): ×√3, ωC, the generation sign, the tap step, the control targets. Percent values are read back in
   GDM's own unit with `get_qty(obj, attr, 'percent')`.

The shell atom (`tests/atoms/shell/shell_only.cimtbl`: `shell_system()` alone) runs first and pins the prereq, so a
shell bug shows as one failure, not one per family.

## Other tests

- **Completeness.** One test per GDM class: `check_fields(FIELDS_<Class>, <Class>)`. It covers components, inline
  equipment, catalogs and controllers.
- **Class coverage** (`tests/test_coverage_import.py`):
  - a `PENDING` class makes `to_cim` raise, naming the class and its phase;
  - an unclassified class (a dummy subclass) raises;
  - orphan inline equipment raises;
  - supplemental attributes raise;
  - every concrete pydantic class in `gdm.distribution.{components,equipment,controllers,common}` sits in exactly one
    of `ORDER`, `INLINE`, `UNTRANSCRIBED` or `PENDING`, so the test fails when GDM adds a class;
  - duplicate names raise (OPEN_DECISIONS 10).
- **Time-series drop** (OPEN_DECISIONS 2): a 3-point `SingleTimeSeries` on a load. `to_cim` succeeds, the result equals
  the load atom's golden (the static snapshot), and `caplog` holds exactly one `WARNING` naming the load, the variable
  and the `time_series_uuid`. When the schedule profile lands, this test becomes the time-series family's atom.
- **Fail fast, per family:**
  - an unmapped enum (the `lookup` message);
  - unequal per-phase source or capacitor values;
  - an asymmetric matrix;
  - an unknown unit spelling (pint raises).
- **`shared.py` units:**
  - the spelling map;
  - `system_voltage` for `line-to-ground` vs `line-to-line`, and a split-phase bus (120 V LG → 240 V);
  - BaseVoltage rounding (2.4018 kV LG → `bv_4p16kv`);
  - ωC: 10 nF/km at 60 Hz → 3.7699e-9 S/m;
  - the generation sign;
  - the tap step.
- **No legacy profile.** Importing `cimhub_gdm` and running one atom loads no `cimhub_2023`, `cim18gad`, `cim17v40`
  or `cimhub_2026` module from CIM-Builder (`sys.modules` check; U5).
- **API conformance.** `GdmImporter` subclasses `FormatImporter`; `model_cls is FeederModel`; the `to_cim` signature
  matches the base class; `gdm_to_cim` is callable.
- **ditto sweep** (`tests/test_ditto_sweep.py`, marked `roundtrip`): `ditto.readers.opendss.reader.Reader(deck).get_system()`
  over the vendored public decks in `cimhub_opendss/tests/decks/` (IEEE13_original, IEEE123, IEEE37, 4bus-OYOD today),
  with `system.name` set to the deck stem. Each deck either imports, or stops with a reason listed in the test as
  expected (a `PENDING` class name, a fail-fast message). The list shrinks phase by phase. Set
  `opendssdirect.Basic.AllowChangeDir(False)` and `AllowEditor(False)` first, as the DSS conftest does.
- **gdmloader sweep** (opt-in: `CIMHUB_GDMLOADER=1`, run as `uv run --with gdmloader pytest ...`; it downloads, so
  never in CI): the 8 `gdm_data` DistributionSystems at the pinned data version (2_4_1), with the same "imports or
  stops at a listed reason" rule. `p1rhs7_1247` (13,380 components, center taps, split-phase, fuses) is the scale
  case. If `gdmloader` isn't importable, the test skips.
- **DSS/GDM parity (Phase 5, tier 4):** one deck through `dss_to_cim` and through ditto + `to_cim`, compared by
  topology in root `tests/cross_format/`, with ditto's losses as listed expected differences
  ([`GDM_MAPPING.md`](GDM_MAPPING.md) §12, §14).
- **XML round trip (Phase 5).** Build → `write_xml` → reload with cim-graph → `diff_models(built, reloaded) == []`,
  plus a check that a PerCent value (`percentImpedance` 5) serializes as `5.0`.
