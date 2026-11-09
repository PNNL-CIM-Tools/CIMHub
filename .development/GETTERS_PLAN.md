# Export getters

**Status:** started 2026-11-08 in a worktree, moved onto `rc_1` the same day once the DSS importer was done.
Design: skill `export-getters` (SKILL.md + reference.md). G1-G3 committed; G4-G5 uncommitted.

**Decision change (user, 2026-11-08):** `REWRITE_PLAN.md` F1 said getters are built on demand, each landing with its
first consumer in the DSS wave. The getters started ahead of DSS S6. Each getter is still tested against
hand-computed numbers on the core shapes (and inline atoms), and the first real consumer (DSS S6, then the RAW
exporter) may ask for signature changes before anything is frozen.

## Scope

- Getters live in `cimhub_core/src/cimhub_core/getters/`, tests in `cimhub_core/tests/test_getters_*.py`; the
  design rules in the `export-getters` skill.
- A missing upstream feature goes to `.development/UPSTREAM_REQUESTS.md` (I9), not a local stand-in.

## Order

| # | getters | status |
|---|---|---|
| G1 | `get_line_sequence_impedance` steps 1-3 (lumped, sequence code × length, phase matrix reduced), `ImpedanceSource`, `SequenceImpedance` | **done 2026-11-08**, 17 tests |
| G2 | Kron reduction of neutral conductors in step 3: series Z by `derived/kron.py`, shunt b/g by the phase block (V_n = 0); s1/s2 still raise | **done 2026-11-08**, 24 getter + Kron tests (Kersting Example 4.1) |
| G3 | `get_line_sequence_impedance_per_length` (steps 2-3 per length), `get_line_phase_impedance_matrix` (`PhaseMatrix`, stored code; sequence code expanded only with `expand_sequence=True`) | **done 2026-11-08**, 31 getter tests |
| G4 | wide fan-out: `get_terminal_nodes`, `get_conductor_phases` (+ `get_terminal_phases`), `get_base_voltage`, `get_switch_state(which=)`, `get_current_limits` | **done 2026-11-08**, 37 tests |
| G5 | `get_spacing_xy` / `get_spacing_distances` (XYSpacing and ConductorDistanceSpacing), `get_line_conductor_xy` (`spacingYOffset`), `derived/spacing.py` | **done 2026-11-08**, 24 tests |
| G6 | transformers, tap changers, shunts, loads, source, DER (reference.md §3) | next |
| G7 | geometry → impedance engine (step 4), validated against `opendssdirect` | raises `NotImplementedError` today |

## G1 decisions (confirmed by the user 2026-11-08)

- **`unit`** is `'ohm'` (admittance in S) or `'pu'` (admittance in pu, one base as in `set_attr`). Anything else
  raises. Per-length units belong to G3's per-length getter.
- **`b`, `g` and the zero sequence are `None` when unset**, as `get_qty` returns them. `r` and `x` are required.
  Each spoke states its own rule for `None` (skill semantic rule 8: RAW/MATPOWER write `B` = 0.0, a set `g` raises
  in both; DSS writes `C1=0`/`C0=0` so the engine's 3.4/1.6 nF defaults never apply).
- **Matrix reduction** is the exact inverse of `derived/sequence.phase_matrix`: self/mutual are the means of the
  diagonal/off-diagonal, positive = Zs − Zm, zero = Zs + 2 Zm. Two conductors use the same formula; one conductor
  gives positive = Z11 and no zero sequence. A missing entry, or b/g set on some entries only, raises.
- **Agreement check** runs only when both sources are within `derive` (the default `LUMPED` never reads the code).
  `DISAGREEMENT_REL_TOL = 1e-6`, relative only, so a lumped 0 against a tiny derived b raises. The tolerance is
  reference.md §3's open question.
- `base_power` is ignored for `'ohm'`.

## G3 open point

- **Capacitance.** GLM (`c11` …, nF/mile) and DSS (`C1`/`C0`, `cmatrix`, nF per length) want capacitance; CIM
  and the getters give susceptance. C = b / (2πf) needs a frequency, either the code's `calculatedFrequency` or
  `network.base_frequency` (semantic rule 7). Not built: decide the frequency source with the first GLM/DSS
  exporter, then add one named function (in `derived/`, or a `get_qty` capacitance unit upstream).

## G4 decisions and open points

- **Nodes:** `get_terminal_nodes(equipment, *, topological=False)`. A FeederModel's terminals have only
  ConnectivityNodes, a BusBranchModel's only TopologicalNodes; the caller names which, no fallback.
- **Phases** are `Terminal.phases` (the canonical PhaseCode cimtables writes; blank is balanced ABC, U10). A line
  orders them by `ACLineSegmentPhase.sequenceNumber`, and its children must be its terminals' set. Every terminal of
  the equipment must agree, so a transformer raises: read each end's terminal with `get_terminal_phases`. The line
  impedance getters now take their conductor order from `get_conductor_phases`.
- **Base voltage:** CIM's rule, `form` required ('LL' as stored, 'LN' = LL/√3). A ConnectivityNode or
  ConductingEquipment inside a VoltageLevel takes `VoltageLevel.BaseVoltage` (its own disregarded); elsewhere its own
  (`ConnectivityNode.BaseVoltage` is new in cim18v17 for nodes outside a VoltageLevel; the DSS importer writes it,
  the core shapes don't). TopologicalNode and TransformerEnd: their own.
- **Switch state:** `True` = open; `which` required.
- **Current limits:** every set on the equipment and its terminals; kind by `OperationalLimitType.durationKind`,
  value by `CurrentLimit.normalValue`; limits of one kind and season must agree (`math.isclose`).
- **Seasons** (user, 2026-11-08: wanted for CYME and others): `OperationalLimitType.season` (GridAPPS-D extension).
  `season=None` reads the all-year limits; a season reads its own, per kind falling back to the all-year one. DSS
  `Seasons`/`Ratings` index a SeasonDayTypeSchedule and are not imported.
- **Open:** a split-phase leg's 'LN' raises (120 V is not 240/√3).

## G5 decisions and open points

- Rewritten from CIMHub_2_0 `transformations/lines` (cimhub_2026, `WireSpacingInfo`): its 0.0 default coordinate,
  10 m default height, logged fallbacks and `PhaseToPhaseSpacing` builder are gone. Getters read, `derived/` computes.
- Both getters take the spacing (the exporter's template), key conductors by sequence number (matching
  `ACLineSegmentPhase.sequenceNumber`), and read either form. `height=` from the first sketch is dropped: CIM requires
  a height per position, and a missing one raises.
- `ConductorDistance` is read by the CIM attributes `sequenceNumber1/2` + `conductorKind1/2` (kind `earth` = a
  height). Rows with only the GridAPPS-D `fromPhase`/`toPhase` raise.
- XY from distances: first conductor at x = 0 (CIM's frame origin is the structure centre line; DSS and GLM use only
  relative x), mirror images to the right, every stored distance checked against the result.
- `get_spacing_distances` returns pairwise distances only (they do not depend on the origin). For a
  ConductorDistanceSpacing they are the stored values and every pair is needed; XY positions need only enough pairs
  to place each conductor.
- **Heights are per line** (user, 2026-11-08): `ACLineSegment.spacingYOffset` (cim101 draft) is the height of the
  spacing's origin, which may be the pole top or crossarm centre, so one spacing serves any pole height.
  `get_line_conductor_xy(line)` = spacing y + offset; unset offset = origin at ground (the CIM XYSpacing default). A
  ConductorDistanceSpacing's earth distances are heights above ground; an offset on its line raises. The line's
  spacing is `ACLineSegment.WireSpacing` or `WireConfiguration.WireSpacing`, and both set must be the same one.
  DSS `h=` and GLM `distance_AE` are therefore per line: one native spacing per (spacing, offset).
- **Open:** `DISTANCE_REL_TOL = 1e-4` (GLM writes 6 digits).
