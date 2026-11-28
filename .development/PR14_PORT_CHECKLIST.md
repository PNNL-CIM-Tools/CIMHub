# PR #14 (Gemini audit) port checklist

PR #14 (`dss-review-fixes`, commit 42b741a) will not be merged. The changes worth keeping are re-implemented on rc_2,
each with its own test. Four read-only reviewers classified every change in the PR and checked disputed behaviour
against OpenDSS (opendssdirect 0.9.4). IDs: **R** reader, **W/N/T/D** writer, name map, topology, master,
**M** cimtbl mappers, **X** exporters. Line numbers refer to the PR branch.

The PR changes no goldens or expected values. rc_2's own suite passes against the PR code, so every behaviour change
below is reached only by new inputs. Tick a box to port it; delete the line to drop it.

## Port status (2026-11-27, uncommitted on rc_2)

Every no-regrets item in section 1 is ported, each with a test that failed first. The open boxes wait on a
decision. Suites: opendss went from 837 to 986 passed (1000 with `--roundtrip`); all 6 suites pass; leak gate clean; no golden changed.
Section 3's getter items were fixed in core directly (the user authorized it), and R37 and section 6's nested Redirect,
brace arrays and `bus1=(1 2 +)` bugs are fixed too.

Where the result differs from the line above:
- R4: case-insensitive matching now covers folders. The Linux engine is case-sensitive (#243); kept for decks written on Windows.
- R16: the engine accepts `Open Line.sw1 0` and opens terminal 1; we raise.
- R21: `DssCommand.params` is now an ordered list of pairs (keys can repeat).
- R22: still open in the engine's favour: `New Linecode.b r1=0.5 like=a` gives r1 from `a` (like= overrides earlier values); the reader keeps 0.5, as rc_2 did.
- R30: a bracketed expression on a numeric slot that doesn't evaluate now raises instead of staying text.
- W11: quotes the coordinates file name only when it needs it (always quoting broke an exporter test).
- N5: `Options` and `Buscoords` are removed from the `New` registry. N6: only `tcc_curve`; rc_2's alias block never ran (the schema class is `TccCurve`).
- M1/M2/M3: `reactive_power`, `power_from_kva` and `dispatched_kvar` take a record label first.
- M37: 17 doubled notes fixed, not 6. Vsource gained a field table in CIMTBL_MAPPING.md.
- X9: refactor only, no failing test possible. X26: unreachable in cim18v17 (2 kinds, both mapped); guard test added.
- X38: in the core transformer getter (`_check_ratings`), because a ratedS of 0 crashed inside the getter first. Root cause filed as U20.
- X40: narrower. The engine ignores Rneut on a delta winding (same YPrim), so only an ungrounded wye raises.
- X11/X14/X36: one check in `getters/der.py` `_rating`, also covering ratedS. X23: new `get_group_schedule`; Season/DayType
  schedules are skipped (valid recurring days, not a time series). X25: raises on a multiplier on a unitless curve only (GDM's W+k is right).
- Follow-up, not done: the gridlabd player keeps its own `is_day` rule; it could call `get_group_schedule`.

## Decisions applied (2026-11-27, uncommitted on rc_2)

The user's answers to section 5, and what was done. Every rule below was checked against opendssdirect 0.9.4 and
EPRI's Pascal source (`~/electricdss-code/Version8/Source`); the tests cite file:line.
- 1 (W17): the reader replays `ParseAsSymMatrix` (Parser/ParserDel.pas:817-829) on `|` rows and stores the
  lower triangle; a row shorter than its index raises. A flat list longer than one row is rejected by the engine.
- 2 (W16): the engine silently drops an empty value and the rest of the command (Load.pas:566); the reader raises
  instead (fail fast). `kW= 5` is not empty.
- 3 (W4/R41): a missing cond x is 0 (LineGeometry.pas:1075). Reader fills it; the writer writes x=0. A position with
  no h raises (deviation: the engine would put it at h=0).
- 4 (N6): only engine class names resolve; `tcccurve` / `tcc curve` raise #263. fmonitor, generic5, pycontrol and
  windgen exist in EPRI's source but not in opendssdirect; left as is.
- 5 (P1-P3): not edited (bootstrap session). linkml-runtime is a runtime dep (the generated schema imports it);
  declare `linkml-runtime~=1.9.5` and `cim-profiles` (pin 0.2.0 at release); no rdflib.
- 6 (R17): the active winding is tracked per object across commands; `windings=` resets the windings; a short array
  keeps the other windings' values; `wdg=` past the last raises; a per-winding BatchEdit raises.
- 7 (M4/M46): `DssModel.commands()` keeps command boundaries (each `~` line is its own command, ExecHelper.pas:887);
  the Load mapper replays the engine's per-command recalculation (Load.pas:634-681, 1138-1160). `taps` longer than windings is cut; shorter keeps the earlier taps.
- 8 (M5/M6): already the load sign (p = -kW, q = -kvar); engine-default kVA/Maxkvar/Minkvar keep their signs.
- 9 (M38): raises; logged in `.development/TODO.md`.
- 10 (M19): `detailed=Yes` maps; `detailed=No` and EqDist*/Avg* raise (LineConstants.pas:218-297: no XY positions
  reproduce the equivalent-spacing form).
- 11 (X41): DSS Rac = rAC25, else rAC50 (in the exporter; GLM prefers rAC50). Writing both on import is not done.
- 12 (X34/X35): export raises on a waiting battery with generation and on a negative idlingP; import raises on a
  negative %IdlingkW.
- 13 (X7): no change; a phase-to-phase capacitor is a real device.
- 14 (M41): an unmapped RegControl slot at its `dss_default` is unset, any other value raises (`TapNum=0` raises: it
  moves the tap). `dss_default` added for vlimit, LDC_Z, rev_Z and Cogen.

Open: a `~` after `New X.b like=a` edits `a` in the engine (DSSClass.pas:256); `like=` cannot supply a required
`bus1`; the Load "defaulted:" comment can list kW=10 when an earlier kVA set kW (comment only).

Not done, found along the way: a second `New` of an existing object (engine #266); `XfmrCode=` resizing windings;
`Edit windings=N` bus names; per-winding MaxTap/MinTap/NumTaps; the same drop-on-falsy rule in geometry
`conductors` and the PV/Storage unmapped lists.

## 1. Port: engine-verified or spec-backed bug fixes

### Reader (`dss_reader.py`)
- [x] R2 `_engine_name("")` returns None (`Set =5` must raise, as the engine does; rc_2 resolves it to `type`)
- [x] R4 case-insensitive path resolution and `\` to `/` in Redirect
- [x] R5 `utf-8-sig` for .dss and the BusCoords CSV (not for `file=` arrays: the engine rejects a BOM there)
- [x] R7 BusCoords/LatLongCoords become ordered commands: `Clear` resets them, last one wins
- [x] R8 `Redirect`/`BusCoords` with no path raises
- [x] R9 strip `()[]` around a Redirect path
- [x] R10 redirect-cycle detection (keep diamonds allowed); rc_2 hits RecursionError
- [x] R12 `Clear` resets the `~` target
- [x] R13 a dotted edit (`Line.l1.length=5`) becomes the `~` target
- [x] R15 Open/Close strips quotes (`Open "Line.sw1" 2`). The `_join_equals` concern was refuted: the tokenizer already joins
- [x] R16 Open/Close terminal < 1 raises
- [x] R18 bare `New` raises
- [x] R21 history keeps every assignment in deck order (`kW=100 kvar=50 kW=200` gives kvar 100 in the engine)
- [x] R22 `like=` history in source order. **Better than the PR:** prepend the source's full history (both readers still get `like=g3 kW=200` wrong)
- [x] R24 LineGeometry `cond=` on an Edit raises (rc_2 drops cond 1 silently)
- [x] R26 `file=` missing file gives ValueError with location (message only; keep rc_2's raise on comment lines)
- [x] R27 `windings=3.0` accepted
- [x] R28 `wdg=` through RPN; `wdg=0` raises (rc_2 writes index -1)
- [x] R30 scalar RPN only on numeric slots (`bus1="pi"` stays `pi`); `{}` on dotted edits
- [x] R31 `_try_eval_rpn` accepts `{}`
- [x] R34 `{…}` elements inside arrays
- [x] R38 a bad BatchEdit regex gives ValueError with location
- [x] R41 LineGeometry: `units=` before cond, repeated `cond=` blocks merge, mixed units raise (rc_2 misaligns xs)
- [x] R43 delete the dead `_extract_winding_arrays`

### Writer, name map, topology, master
- [x] W2 `!` and `//` count as unsafe name characters (the engine reads them as a comment)
- [x] W3 NaN/inf raise in `format_float`. **Also** apply to Buscoords rows (they use `repr`)
- [x] W4 a geometry with heights but no x raises (improve the message; root cause in the reader, see decision 3)
- [x] W7 write files only after every line is formatted
- [x] W8 sanitize the Open target (hand-built models); add a test
- [x] W9 Buscoords with x/y None raises
- [x] W10 sanitize the bus name in the coordinates CSV (rc_2 leaves `bus_1` without coordinates)
- [x] W11 quote the coordinates filename (always quote; simpler)
- [x] W17 non-triangular matrix: raise or convert (see decision 1). rc_2 silently corrupts a full 3×3
- [x] N2 `encoding="utf-8"` when loading schema yaml
- [x] N3 `field_for("")` raises
- [x] N4 prefix match skips `name` (`New Loadshape.s n=2` loses npts on rc_2)
- [x] N5 `New Options` / `New Buscoords` raise (engine #263)
- [x] N6 `tcc_curve` alias (see decision 4 on the non-engine aliases)
- [x] T2 a 1-phase winding needs two distinct nodes (`.1.1` raises)
- [x] W14 **rc_2 fix, not the PR change:** keep raising on `circuit=""`, but correct the message (`circuit is not None`)

### cimtbl mappers
- [x] M1 kvar takes kW's sign (`kW=-50 pf=0.9` gives kvar -24.2 in the engine)
- [x] M2 `reactive_power` raises unless 0 < |pf| ≤ 1
- [x] M3 **rc_2 fix, not the PR formula:** `power_from_kva` raises on pf=0 (the engine gives NaN; the PR's (0, kVA) is wrong)
- [x] M4 kVA together with kvar raises (or resolve by order, see decision 7)
- [x] M12 Capacitor Numsteps=0 raises (rc_2 maps it as 1)
- [x] M13 Capacitor `states` must be one value, 0 or 1
- [x] M15 CapControl phase count also from LineSpacing.nphases. **Share one helper with line.py**
- [x] M16 CapControl Line terminal must be 1 or 2
- [x] M17 CapControl Capacitor terminal must be 1
- [x] M18 geometry `_not_mapped`: drop the unused `fields` parameter
- [x] M19 LineSpacing `detailed`: No raises, Yes maps (rc_2 has it inverted); update the spec note
- [x] M22 `spacing=` with folded cond/wire/x/h slots raises
- [x] M23 switch lines are excluded from geometry, earth rho and linecode unit templates; add `rho` to `_SWITCH_DROPPED`
- [x] M24 Recloser Shots < 1 raises (skip the Shots=1 branch)
- [x] M25 Fuse RatedCurrent=0 is copied (rc_2's truthiness test drops it)
- [x] M28/M30/M31 a LineCode with no nphases defaults to 3. **One helper in linecode.py that reads `dss_defaults`**, used by line.py too, with a "defaulted" note
- [x] M34 2-phase sequence code with C0 but no C1 raises
- [x] M35/M36 loadshape actions from the assignment history (`normalize` then `DblSave`). Drop the PR's `shape.action` fallback
- [x] M37 de-duplicate the PV/reactor "raises when" notes, properly (a `_RAISES` constant, all 6 notes); regenerate CIMTBL_MAPPING.md
- [x] M38 PV below cutout with |kvar| > kVA: raise or clamp (see decision 9)
- [x] M39 PV hysteresis band check in `map_pvsystem`. **Only the check**, not the double pass over every sample
- [x] M40 tap_range: NumTaps > 0, MaxTap > MinTap, tap within range
- [x] M41 RegControl unmapped-slot test: see decision 14 (both the rc_2 and PR rules are wrong)
- [x] M42 a non-1 fixed tap on a non-controlled winding raises (rc_2 drops it)
- [x] M46 `taps` length ≠ windings: raise or pad (see decision 7)
- [x] M47 regulator `grounded`: 3-phase uses nodes[-1]==0, 1-phase uses 0 in nodes (`.1.2.3.4` floats in the engine)
- [x] M48 **rc_2 fix, not the PR formula:** raise clearly on x1r1 ≤ 0 (the engine refuses it; the PR returns X1=0)
- [x] M49 Vsource kv/MVAsc > 0, x0r0 ≥ 0, R0 ≥ 0
- [x] M50 Vsource partial Isc3/Isc1 raises clearly

### Exporters
- [x] X1 buscoords `abs_tol=1e-9` on the position compare
- [x] X3 CapControl unset targetValue raises ValueError
- [x] X4 CapControl PT/CT ratio ≤ 0 raises (a negative ratio switches the cap the wrong way in the engine)
- [x] X5 CapControl on a coupled line names the right jumper Line. **One `(line, terminal) → DSS element` helper in line.py**, used by capcontrol
- [x] X9 generator reads `rating.earthing` (through the getter)
- [x] X10 generator: add `reverseTargetDeadband` to the unmapped list
- [x] X12 `equal_phases` abs_tol
- [x] X14 inverter maxIFault ≤ 0 raises
- [x] X15 line length ≤ 0 raises (negative solves silently; 0 fails to invert); update the `length` Slot text
- [x] X17 lumped length ≤ 0 raises
- [x] X18 LineGeometry name from the mm-rounded offset
- [x] X19 coupled group length ≤ 0 raises
- [x] X24 loadshape: ConformLoadGroup None raises clearly
- [x] X26 options: unmapped EarthModelKind raises ValueError
- [x] X27 negative PV points raise
- [x] X29 reactor abs_tol on r0/x0
- [x] X30 RegControl ptRatio ≤ 0 raises
- [x] X31 RegControl unset targetValue raises
- [x] X32 RegControl tap end type check
- [x] X33 storage abs_tol on the mult and idling compares
- [x] X36 storage ratedE ≤ 0 raises; `is not None` instead of truthiness
- [x] X37 vsource abs_tol on r2/x2
- [x] X38 winding-1 kVA ≤ 0 raises
- [x] X39 AutoTransformer kVA compare uses `isclose`
- [x] X40 rground/xground on a winding that isn't a grounded wye raises (the engine grounds it silently)
- [x] X41 wire Rac = rAC25, else rAC50 (rc_2 drops rAC50 silently, so a GLM line fails to export). Update the Slot text and EXPORT_MAPPING.md:244; see decision 11

### Docs and tests (true of rc_2 already)
- [x] README `cim_to_dss` signature and the support table (Switches, LoadShape)
- [x] EXPORT_MAPPING.md WindUnit allowed (E2); tolerance text (E3, with X1). E1 (rAC50 text) waits with X41
- [x] developer docs: importer.md yearly shapes, schema.md drop the prefix warning, testing.md test_schema_types, loads.md PTPhase raises ValueError
- [x] dss_to_cimtbl docstring (D2)
- [x] test fixture: `Set defaultbasefreq=60` after `Clear` (the engine keeps 50 Hz across Clear), as **one conftest fixture**
- [x] test_cimtbl_line `_matrix`: compare template-LineCode lines too, via `get_line_code`

## 2. Don't port (regressions, invariant breaks or dead code)

- R14 BatchEdit as the `~` target (the engine doesn't change the active object)
- R17 as written: per-winding Edit raises. It breaks the correct 2-winding `Edit kva=600` and IEEE34's `reg1a.wdg=2 Tap=`. See decision 6
- R20 dotted edit `Line.a.b.length` edits Line `a.b` (the engine raises #110, as rc_2 does)
- R26 skipping comment lines in `file=` arrays (the engine counts them as 0; keep rc_2's raise)
- R32 `{}` removed as an array delimiter (`kvar={100 200}`, `mult={1 2 3}` and `wires={w w}` break)
- R33 whole-array RPN shortcut (`kvar=(600 3 /)` becomes [200]; the engine reads [600])
- R37 rollup/rolldn: both versions are wrong. **Make rollup/rolldn raise "not read"**; no local deck uses them
- R42 deleting the mixed-conductor NOTE comments
- W1 / W12 dead `Bool` and `int(order)` code
- W15 dropping None/empty list items (silently shifts positional arrays)
- W16 omitting `''` values (decide in the reader, decision 2)
- T1 `cell()` and `is_wye_conn` in topology; rc_2 is already right
- M3 / M48 the PR's pf=0 and x1r1=0 formulas (replaced by raises above)
- M5 / M6 Generator Maxkvar/Minkvar/kVA defaults with `abs()` (the engine keeps signs; rc_2 matches). See decision 8
- M9 / M10 buscoords mapper None guard and dropping "not located" diagnostics
- M26 raising on extra bus nodes beyond `phases` (the engine ignores them, as rc_2 does)
- M29 neutrals < 0 check (unreachable)
- M45 `is_wye_conn` (the reader already normalizes; `star` is rejected everywhere)
- X7 PTPhase=1 on single-phase caps (breaks 1-phase delta: the engine reads about 0 V)
- X13 inverter `output.connection` plumbing (same value)
- X16 `_own_code` reading `line.PerLengthImpedance` directly (bypasses the getter)
- X20 skipping coupled lines in the first-line-per-geometry pick (names a template below ground)
- X21 load checking `shapes.by_owner` (hidden ordering dependency)
- Tests that only lock in PR output: rollup/rolldn, `kvar=(600 3 /)`, ShapeRegistry collision, waiting-storage (never reaches its branch), buscoords None guard, `power_from_kva(100, 0)`, x1r1=0, extra-node

## 3. Upstream (I9): file in UPSTREAM_REQUESTS.md, not local

- X23 skip Season/DayType schedules: belongs in `get_load_schedule`
- X25 value1/value2 multiplier ≠ none raises: belongs in `get_schedule_points` (rc_2 is 1000× off with `k`)
- X11 ratedU > 0: `get_machine_rating`. Consider the same for X14 maxIFault and X36 ratedE
- P1–P3 declare `cim-profiles`, `linkml-runtime` and `rdflib` in cimhub_opendss (all three are imported directly); `uv.lock` goes to the bootstrap session

## 4. Optional (cosmetic or clearer errors only)

R1 R6 R11 R19 R23 R25 R29 R35 R36 R39 R40 R44 · W5 W6 W13 N1 D1 P4 · M7 M8 M11 M14 M20 M21 M27 M32 M33 M43 M44 M51 M52 ·
X6 X22 X28

## 5. Decisions needed

1. **Full n×n matrix** (W17): convert to the lower triangle (DSS accepts both forms) or raise? In the reader or the writer?
2. **Empty `prop=` value** (W16): drop, keep `''`, or raise?
3. **LineGeometry cond with no `x`** (W4, R41): default x=0 as the engine does, or raise?
4. **Non-engine aliases `tcccurve` / `tcc curve`** (N6): keep or drop?
5. **Transitive deps** (P3): also declare `jsonasobj2`, or declare none of them?
6. **Transformer per-winding edits** (R17): track each object's active winding across commands (matches the engine), or raise?
7. **kVA+kvar order and a short `taps` list** (M4, M46): follow the engine's order and padding rules, or raise?
8. **Generator negative kW/kvar defaults** (M5, M6): copy the engine's signed values (rc_2) or raise?
9. **PV below cutout with |kvar| > kVA** (M38): clamp to kvarMax (engine) or raise?
10. **Reference engine for newer LineSpacing slots** (M19): `detailed`, `EqDist*` and `Avg*` are unknown to 0.9.4
11. **Wire with both rAC25 and rAC50** (X41): raise, prefer rAC25 (DSS label) or prefer rAC50 (GLM rule)? List the rAC50 → rAC25 relabel as an expected round-trip difference?
12. **Storage waiting with generation / negative idlingP** (X34, X35): raise (spec's wrong-sign rule) or keep rc_2's faithful round trip (the engine honours it)?
13. **1-phase delta cap with PTPhase=1** (X7): flag it, or round-trip as is?
14. **RegControl unmapped-slot zero rule** (M41 / exporter R): rc_2 drops `TapNum=0`; the PR raises on `LDC_Z=0`, `vlimit=0` and `rev_Z=0`, which are engine defaults. Proposed: treat a value equal to its `dss_defaults` value as unset

## 6. Pre-existing bugs found along the way (in rc_2 and the PR alike)

- Nested Redirect resolves against the master's folder; the engine resolves against the including file's folder
- Transformer brace arrays (`buses={a b}`, `kvs={12.47 4.16}`) fail; the engine accepts them
- A second `New` of an existing element raises warning #266 in this engine build and isn't applied, which calls the reader's "redefinition = Edit" premise into question
- `Clear` keeps defaultbasefreq, so engine helpers such as `assert_same_power_flow` may leak 50 Hz between tests
- `bus1=(1 2 +)` is evaluated as RPN; the engine treats it as a bus name
