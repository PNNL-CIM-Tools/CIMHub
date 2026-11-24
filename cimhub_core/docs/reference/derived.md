# Derived values

Pure functions for quantities CIM has no attribute for: a susceptance from a capacitance, a band from an ON/OFF pair,
a matrix with its neutral folded out. They live in `cimhub_core/derived/`. Each takes and returns plain floats (or
dictionaries of them), reads no CIM object, and does no unit conversion, so the unit goes with the values: a caller
reads in the unit it needs with [`get_qty`](index.md) and passes the numbers in.

A derived function exists only where CIM has no attribute for the source quantity. A value CIM stores is read with a
getter, never recomputed here.

| Module | Functions | Used by |
|---|---|---|
| `capacitance` | `b_from_c`, `c_from_b` | GLM and DSS line-code importers and exporters |
| `control_band` | `band_from_on_off`, `on_off_from_band` | capacitor control importers and the DSS exporter |
| `kron` | `kron_reduce` | the `MATRIX_REDUCED` step of `get_line_sequence_impedance` and `get_line_sequence_impedance_per_length`, the GLM line-catalog exporter |
| `regulator` | `secondary_to_primary`, `primary_to_secondary`, `line_drop_ohms`, `line_drop_volts` | regulator importers and the DSS exporter |
| `sequence` | `phase_matrix`, `balanced_matrix` | the line getters, the DSS line-code importer |
| `spacing` | `positions_from_distances` | `get_spacing_xy` |

The examples run from the repo root.

## capacitance

Shunt susceptance and capacitance at one frequency: `b = 2π f C`.

```python
b_from_c(c: float, frequency: float) -> float
c_from_b(b: float, frequency: float) -> float
```

| Function | Formula | In | Out | Raises |
|---|---|---|---|---|
| `b_from_c` | `b = 2π f C` | C in nF, f in Hz | b in nS | |
| `c_from_b` | `C = b / (2π f)` | b in nS, f in Hz | C in nF | `ValueError` when `frequency <= 0` |

The units go with the values: C in nF per mile and f in Hz give b in nS per mile. A caller reads b with `get_qty` in nS
(per its length unit) and gets C in nF per the same length, so no unit factor appears. The frequency comes from the
network (`network.base_frequency`), never a literal 60.

```python
from cimhub_core.derived.capacitance import b_from_c, c_from_b

b = b_from_c(10.0, 60.0)
print(round(b, 2), round(c_from_b(b, 60.0), 6))
# 3769.91 10.0
try:
    c_from_b(3769.91, 0.0)
except ValueError as error:
    print(error)
# a capacitance needs a positive frequency, not 0.0
```

`b_from_c` is called by the `cimhub_gridlabd` configuration importer and the `cimhub_opendss` line-code importer;
`c_from_b` by the `cimhub_gridlabd` line-catalog exporter and the `cimhub_opendss` line-code exporter.

## control_band

A switched control's ON/OFF pair as a CIM target and deadband, and back. CIM's `RegulatingControl` holds the band's
midpoint (`targetValue`) and its full width (`targetDeadband`, positive). A switched control, such as a capacitor
control, has two settings, ON and OFF.

```python
band_from_on_off(on: float, off: float) -> tuple[float, float]
on_off_from_band(target: float, deadband: float, *, on_above: bool) -> tuple[float, float]
```

| Function | Formula | Returns |
|---|---|---|
| `band_from_on_off` | `target = (on + off) / 2`, `deadband = abs(off - on)` | `(target, deadband)` |
| `on_off_from_band` | `low = target - deadband / 2`, `high = target + deadband / 2` | `(on, off)` = `(high, low)` when `on_above`, else `(low, high)` |

Which side ON is on follows from the control's mode: below OFF when the control acts on a falling value (voltage,
time), above it when on a rising one (current, reactive power). So the pair is rebuilt without a sign, and the caller
states `on_above`. The values keep whatever unit they came in.

```python
from cimhub_core.derived.control_band import band_from_on_off, on_off_from_band

target, deadband = band_from_on_off(118.0, 122.0)
print(target, deadband)
# 120.0 4.0
print(on_off_from_band(target, deadband, on_above=True), on_off_from_band(target, deadband, on_above=False))
# (122.0, 118.0) (118.0, 122.0)
```

`band_from_on_off` is called by the `cimhub_gridlabd` capacitor importer and the `cimhub_opendss` capacitor-control
importer; `on_off_from_band` by the `cimhub_opendss` capacitor-control exporter.

## kron

Kron reduction: fold grounded conductors (neutrals) out of a series impedance matrix. With a conductor grounded at both
ends its voltage drop is zero, so its current is eliminated.

```python
kron_reduce(matrix: dict[tuple[int, int], complex], eliminate: Iterable[int]) -> dict[tuple[int, int], complex]
```

```text
Z' = Z_pp - Z_pn · Z_nn⁻¹ · Z_np          (p: kept conductors, n: eliminated ones)
Z'_ij = Z_ij - Z_ik · Z_kj / Z_kk         (one conductor k at a time; the same result in any order)
```

`matrix` is the lower triangle `{(row, column): value}`, 1-based. `eliminate` names the conductors to fold out by their
numbers in `matrix`. The result is the lower triangle of the kept conductors, renumbered 1..k in their original order.
The impedance's unit is whatever you pass in, and per-length stays per-length. It raises `ValueError` when an
eliminated conductor's self impedance is zero. Pure Python, so there is no numpy dependency.

Only the series impedance is Kron-reduced. A shunt matrix with grounded conductors (V_n = 0) keeps its phase block as
it is, because `C_reduced = (P_reduced)⁻¹` is the phase block of `C = P⁻¹`.

```python
from cimhub_core.derived.kron import kron_reduce

z = {(1, 1): 1 + 1j, (2, 1): 0.3j, (2, 2): 2 + 2j, (3, 1): 0.2, (3, 2): 0.1, (3, 3): 4 + 4j}
reduced = kron_reduce(z, [3])  # conductor 3 is the neutral
print({key: complex(round(value.real, 4), round(value.imag, 4)) for key, value in reduced.items()})
# {(1, 1): (0.995+1.005j), (2, 1): (-0.0025+0.3025j), (2, 2): (1.9988+2.0013j)}
```

Used by the `MATRIX_REDUCED` step of `get_line_sequence_impedance` and `get_line_sequence_impedance_per_length` (see
[Lines and wires](lines.md)), which folds a matrix code's neutrals out before reducing it to sequence values, and by the
`cimhub_gridlabd` line-catalog exporter.

## regulator

Voltage regulator settings between the PT secondary and the primary. A regulator relay works on its PT secondary: a
band centre in volts on the 120 V side, and a line drop compensator in volts at rated CT current. CIM holds both on the
primary: target volts, and line drop ohms. `ptratio` is the PT ratio and `ct_primary` the CT primary rating in A, so
every conversion is a ratio and no unit factor appears.

```python
secondary_to_primary(volts, ptratio) -> float
primary_to_secondary(volts, ptratio) -> float
line_drop_ohms(volts, ptratio, ct_primary) -> float
line_drop_volts(ohms, ptratio, ct_primary) -> float
```

| Function | Formula | In | Out |
|---|---|---|---|
| `secondary_to_primary` | `volts × ptratio` | a setting in volts on the PT secondary | primary volts |
| `primary_to_secondary` | `volts / ptratio` | primary volts | volts on the PT secondary |
| `line_drop_ohms` | `volts × ptratio / ct_primary` | compensator setting in volts at rated CT current | primary ohms |
| `line_drop_volts` | `ohms × ct_primary / ptratio` | primary ohms | compensator setting in volts at rated CT current |

```python
from cimhub_core.derived.regulator import line_drop_ohms, line_drop_volts, primary_to_secondary, secondary_to_primary

print(secondary_to_primary(122.0, 20.0), primary_to_secondary(2440.0, 20.0))
# 2440.0 122.0
ohms = line_drop_ohms(3.0, 20.0, 700.0)
print(round(ohms, 6), round(line_drop_volts(ohms, 20.0, 700.0), 6))
# 0.085714 3.0
```

`secondary_to_primary` and `line_drop_ohms` are called by the `cimhub_gridlabd` regulator importer and the
`cimhub_opendss` regulator-control importer; `primary_to_secondary` and `line_drop_volts` by the `cimhub_opendss`
regulator-control exporter. The exporter does not read `ctRatio`: the engine's CT secondary is fixed.

## sequence

A phase matrix from sequence values. A 3-phase sequence code stays a `PerLengthSequenceImpedance`. Fewer phases have no
CIM sequence convention, so the matrix is written instead.

```python
phase_matrix(positive: float, zero: float | None, phases: int) -> dict[tuple[int, int], float]
balanced_matrix(positive: float, zero: float, conductors: int) -> dict[tuple[int, int], float]
```

Both return the lower triangle `{(row, column): value}`, 1-based. Z1 is `positive` and Z0 is `zero`. The same holds for
r, x and C separately, and the unit is whatever you pass in. It is a closed form, not Carson.

| Function | Phases | Self | Mutual |
|---|---|---|---|
| `phase_matrix` | 1 | Z1 alone: `{(1, 1): positive}`; `zero` is unused and may be `None` | |
| `phase_matrix` | 2 | `(2 Z1 + Z0) / 3`; needs `zero` | `(Z0 - Z1) / 3` |
| `phase_matrix` | other | raises `ValueError: phase_matrix is for 1 or 2 phases, not ...` | |
| `balanced_matrix` | n | `(2 Z1 + Z0) / 3` on every diagonal entry | `(Z0 - Z1) / 3` on every off-diagonal entry |

`balanced_matrix` is the n-conductor form that OpenDSS gives a matrix line code that leaves out its C matrix. The line
getters' inverse, from a matrix back to sequence values, is the mean of the diagonal and of the off-diagonal entries:
positive = Zs - Zm, zero = Zs + 2 Zm.

```python
from cimhub_core.derived.sequence import balanced_matrix, phase_matrix

print(phase_matrix(0.3, 0.9, 1))
# {(1, 1): 0.3}
print({key: round(value, 3) for key, value in phase_matrix(0.3, 0.9, 2).items()})
# {(1, 1): 0.5, (2, 1): 0.2, (2, 2): 0.5}
print(len(balanced_matrix(0.3, 0.9, 4)))
# 10
```

Used by `get_line_phase_impedance_matrix` with `expand_sequence=True` (`balanced_matrix`, and `phase_matrix` for one
conductor) and by the `cimhub_opendss` line-code importer.

## spacing

Conductor positions from pairwise distances and heights: a `ConductorDistanceSpacing` read as XY.

```python
positions_from_distances(heights: dict[int, float], distances: dict[tuple[int, int], float], *,
                         rel_tol: float) -> dict[int, tuple[float, float]]
```

`heights` is `{sequence number: y}` and `distances` is `{(i, j): d}` with i < j. All lengths must share one unit. The
result is `{sequence number: (x, y)}`. Each conductor's height is known, so only x is solved:

1. The first conductor (lowest sequence number) is at x = 0.
2. Each later one is placed from the conductors already placed that it has a distance to. The horizontal run to a
   reference is `sqrt(d² - dy²)`, giving `x_ref ± run`, and the candidate that best fits every reference wins.
3. Where the distances leave a mirror image open (the second conductor, or one placed from a vertical stack), it goes
   to the right (+x).
4. Every stored distance is then checked against the positions.

A distance short of the height difference by no more than `rel_tol` is a vertical run. It raises `ValueError` when a
conductor has no distance to one placed before it, when a distance is shorter than the height difference beyond
`rel_tol`, or when a stored distance disagrees with the positions beyond `rel_tol`.

```python
from cimhub_core.derived.spacing import positions_from_distances

heights = {1: 28.0, 2: 28.0, 3: 28.0, 4: 24.0}
distances = {(1, 2): 2.5, (1, 3): 7.0, (2, 3): 4.5, (1, 4): 5.6569, (2, 4): 4.272, (3, 4): 5.0}
positions = positions_from_distances(heights, distances, rel_tol=1e-4)
print({number: (round(x, 2), y) for number, (x, y) in positions.items()})
# {1: (0.0, 28.0), 2: (2.5, 28.0), 3: (7.0, 28.0), 4: (4.0, 24.0)}
```

Used by `get_spacing_xy` with `rel_tol=DISTANCE_REL_TOL` (1e-4, because GLM writes six digits).
