# Export getters

**Status:** started 2026-11-08 in a worktree, moved onto `rc_1` the same day once the DSS importer was done.
Design: skill `export-getters` (SKILL.md + reference.md). Nothing committed.

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
| G4 | wide fan-out: `get_terminal_nodes`, `get_conductor_phases`, `get_base_voltage`, `get_switch_state(which=)`, `get_current_limits` | next |
| G5 | `get_spacing_xy` / `get_spacing_distances` | |
| G6 | transformers, tap changers, shunts, loads, source, DER (reference.md §3) | |
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
