# Lines and wires

The getters for an `ACLineSegment`: its impedance, its geometry, its conductors and its ratings. They live in
`getters/line_impedance.py`, `spacing.py`, `wire.py`, `current_limits.py`, `impedance_table.py` and `earth.py`.
Conventions common to every getter are on the [reference landing page](index.md).

| A line is... | CIM path | Read with |
|---|---|---|
| lumped | `ACLineSegment.r/x/bch/gch` (and `r0/x0/b0ch/g0ch`) | `get_line_sequence_impedance` |
| a per-length sequence code | `ACLineSegment.PerLengthImpedance` or `.WireConfiguration.PerLengthImpedance` → `PerLengthSequenceImpedance` | `get_line_sequence_impedance_per_length`, `get_line_phase_impedance_matrix` |
| a per-length matrix code | the same path → `PerLengthPhaseImpedance` → `PhaseImpedanceData` | `get_line_phase_impedance_matrix` |
| geometry | `ACLineSegment.WireConfiguration` → `WireSpacing` (`XYSpacing` → `XYConductorPosition`, or `ConductorDistanceSpacing` → `ConductorDistance`) and `WireSequence` → `WireSequenceConfiguration.WireInfo` | the spacing and wire getters |

The examples use the shapes in `cimhub_core/src/cimhub_core/shapes/` and run from the repo root. This block is the
setup the later ones share.

```python
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
from cimtables import BusBranchModel, load_model


def by_mrid(network, cls, mrid):
    return next(obj for obj in network.graph[cls].values() if obj.mRID == mrid)


SHAPES = Path("cimhub_core/src/cimhub_core/shapes")
bus_branch = load_model(SHAPES / "line_bus_branch.cimtbl", model_cls=BusBranchModel)
by_code = load_model(SHAPES / "line_by_impedance.cimtbl")
by_geometry = load_model(SHAPES / "line_by_wire_configuration.cimtbl")

lumped = by_mrid(bus_branch, cim.ACLineSegment, "ln_1_2_1")  # r, x, bch in pu
matrix_line = by_mrid(by_code, cim.ACLineSegment, "ln_l1")  # a template matrix code
sequence_line = by_mrid(by_code, cim.ACLineSegment, "ln_l2")  # its own sequence code
geometry_line = by_mrid(by_geometry, cim.ACLineSegment, "ln_g1")  # XYSpacing + conductors
```

## Line impedance

Module `cimhub_core.getters.line_impedance`. A bus-branch format (RAW, MATPOWER) takes only sequence values, so the
sequence getters may reduce what CIM holds. A format with geometry (GLM, DSS) exports the geometry and never calls the
sequence getters on a line that has it.

### ImpedanceSource

An `IntEnum`. Each `SequenceImpedance` carries the step it came from in `source`, and `derive=` takes the furthest
step the getter may go.

| Value | Step | Source | Assumption added |
|---|---|---|---|
| `LUMPED` (1) | 1 | `ACLineSegment.r/x/bch/gch` and the zero-sequence set, as stored | none |
| `PER_LENGTH_SEQ` (2) | 2 | `PerLengthSequenceImpedance`, times `length` for whole-line values | the line's length |
| `MATRIX_REDUCED` (3) | 3 | `PerLengthPhaseImpedance`, Kron-reduced if it has neutral conductors, then reduced to sequence values | a transposed line; neutrals grounded at both ends. A conductor other than A, B, C and N raises |
| `GEOMETRY` (4) | 4 | the WireConfiguration's spacing and wires through line constants | not built: a line with geometry and no lumped values raises `NotImplementedError` at `derive=GEOMETRY` |

The resolution order is the caller's, not a hidden fallback chain:

- `derive=` caps the step. The default `ImpedanceSource.LUMPED` reads stored lumped values only and raises when they
  are absent.
- When the line has lumped values, the per-length source is read only to check them. It is read at most to
  `MATRIX_REDUCED` (geometry is never reached), and not at all when the line has no `length`: the lumped values
  are then returned as they stand, instead of raising.
- When the lumped values and a per-length source are both read, they must agree to a relative tolerance of
  `DISAGREEMENT_REL_TOL` (1e-6) on every value both set, and the lumped values win. A difference raises.
- No spoke passes `derive=` yet; `cimhub_raw` and `cimhub_opendss` call `get_line_sequence_impedance` with the default.

### SequenceImpedance

Returned by the sequence getters.

| Field | Meaning | Unit |
|---|---|---|
| `r`, `x` | positive-sequence series resistance and reactance; always set | impedance unit |
| `b`, `g` | positive-sequence shunt susceptance and conductance; `None` when unset | admittance unit |
| `r0`, `x0` | zero-sequence series values; `None` when unset | impedance unit |
| `b0`, `g0` | zero-sequence shunt values; `None` when unset | admittance unit |
| `source` | the `ImpedanceSource` step that gave these values | |

The whole-line getter returns whole-line values; the per-length getter returns values per unit length, in the units
you name.

### get_line_sequence_impedance

```python
get_line_sequence_impedance(line, unit="ohm", *, base_power=None, derive=ImpedanceSource.LUMPED) -> SequenceImpedance
```

The whole line's sequence values.

| Parameter | Meaning |
|---|---|
| `line` | an `ACLineSegment` |
| `unit` | `'ohm'` (admittance in siemens) or `'pu'` (admittance in pu). Anything else raises `ValueError: unit must be one of ['ohm', 'pu'], not ...` |
| `base_power` | the power base for `'pu'`, normally `network.base_power`. The voltage base is the line's BaseVoltage; the conversion is `cimtables.impedance.z_base`. Required for `'pu'` |
| `derive` | the furthest `ImpedanceSource` step to take |

It reads the lumped values first. When `derive` allows, it also reads the per-length source (the line's
`get_line_code`) and multiplies by the line's `length`. It raises `ValueError` when:

- nothing within `derive` gives r and x (the message lists whether lumped r/x are set, the `PerLengthImpedance` class
  and whether there is geometry);
- only one of lumped `r` and `x` is set;
- the line has no lumped values, a per-length source gives them and the line has no `length`
  (`a per-length impedance needs the line's length`);
- two sources disagree beyond the tolerance.

It raises `NotImplementedError` (not `ValueError`) only when the line has no lumped values and `derive` reaches
`GEOMETRY` on a line with geometry. A line with lumped values and geometry returns the lumped values.

```python
from cimhub_core.getters.line_impedance import ImpedanceSource, get_line_sequence_impedance

z = get_line_sequence_impedance(lumped, "pu", base_power=bus_branch.base_power)
print(z.r, z.x, z.b, z.g, z.source.name)
# 0.0194 0.0592 0.0528 None LUMPED

# the same line in ohm and siemens, on the line's BaseVoltage (115 kV) and the model's 100 MVA
z = get_line_sequence_impedance(lumped, "ohm")
print(round(z.r, 3), round(z.x, 3), z.source.name)
# 2.566 7.829 LUMPED

# a line with only a per-length code: the default derive raises, derive=PER_LENGTH_SEQ multiplies by the length
try:
    get_line_sequence_impedance(sequence_line)
except ValueError as error:
    print(error)
# ACLineSegment 'ln_l2': no sequence impedance within derive=LUMPED (lumped r/x: unset, PerLengthImpedance: PerLengthSequenceImpedance, geometry: none)

z = get_line_sequence_impedance(sequence_line, derive=ImpedanceSource.PER_LENGTH_SEQ)
print(round(z.r, 4), round(z.x, 4), round(z.r0, 4), z.source.name)
# 0.0532 0.065 0.0897 PER_LENGTH_SEQ
```

Called by `cimhub_opendss` and `cimhub_raw`.

### get_line_sequence_impedance_per_length

```python
get_line_sequence_impedance_per_length(line, impedance_unit="ohm/m", admittance_unit="S/m", *,
                                       derive=ImpedanceSource.PER_LENGTH_SEQ) -> SequenceImpedance
```

The line's per-length sequence values, from its `PerLengthImpedance` (steps 2 and 3). The lumped values are whole-line
and never read. `derive` below `PER_LENGTH_SEQ` raises. Raises `ValueError` when nothing within `derive` gives r and x.
`source` is `PER_LENGTH_SEQ`, or `MATRIX_REDUCED` for a matrix code.

```python
from cimhub_core.getters.line_impedance import get_line_sequence_impedance_per_length

z = get_line_sequence_impedance_per_length(sequence_line, "ohm/km", "nS/km")
print(z.r, z.x, round(z.b, 2), z.source.name)
# 0.3489 0.426198 3932.35 PER_LENGTH_SEQ
```

Called by `cimhub_gdm`.

### get_line_phase_impedance_matrix

```python
get_line_phase_impedance_matrix(line, impedance_unit="ohm/m", admittance_unit="S/m", *,
                                expand_sequence=False) -> PhaseMatrix
```

The line's per-length phase matrix in conductor order, neutrals and s1/s2 included as stored. A
`PerLengthPhaseImpedance` is read directly. A `PerLengthSequenceImpedance` becomes a matrix only with
`expand_sequence=True`, by `cimhub_core.derived.sequence` (see [Derived values](derived.md)): one phase is Z1 alone;
more are self `(2 Z1 + Z0) / 3` and mutual `(Z0 - Z1) / 3`. Raises `ValueError` when:

- the code is a sequence code and `expand_sequence` is false ("pass expand_sequence=True");
- the line has geometry and no `PerLengthImpedance` (export the geometry instead);
- the line has no `PerLengthImpedance` at all;
- the code's entries are not the lower triangle of the line's conductors;
- `r` or `x` is unset, or `b`/`g` is set on some entries and not others.

`PhaseMatrix` fields:

| Field | Meaning |
|---|---|
| `phases` | the conductors, as `SinglePhaseKind`, in `get_conductor_phases` order |
| `r`, `x` | `{(row, column): value}`, lower triangle, 1-based, per length |
| `b`, `g` | the same for shunt admittance; `None` when unset |
| `source` | `MatrixSource.PHASE_CODE` (read as stored) or `MatrixSource.SEQUENCE_EXPANDED` (a sequence code expanded, assuming a transposed line) |

```python
from cimhub_core.getters.line_impedance import get_line_phase_impedance_matrix

m = get_line_phase_impedance_matrix(matrix_line, "ohm/mi", "nS/mi")
print([phase.value for phase in m.phases], m.source.name)
print({key: round(value, 4) for key, value in m.r.items()})
# ['C', 'B'] PHASE_CODE
# {(1, 1): 1.3238, (2, 1): 0.2066, (2, 2): 1.3294}

m = get_line_phase_impedance_matrix(sequence_line, "ohm/km", "nS/km", expand_sequence=True)
print(m.source.name, round(m.r[1, 1], 4), round(m.r[2, 1], 4))
# SEQUENCE_EXPANDED 0.4289 0.08
```

Called by `cimhub_gdm` and `cimhub_gridlabd` (only where CIM has no geometry).

### get_phase_impedance_code, get_sequence_impedance_code

```python
get_phase_impedance_code(code, impedance_unit="ohm/m", admittance_unit="S/m") -> CodeMatrix
get_sequence_impedance_code(code, impedance_unit="ohm/m", admittance_unit="S/m") -> SequenceImpedance
```

A `PerLengthPhaseImpedance` or `PerLengthSequenceImpedance` read on its own, whether or not a line uses it, for
exporters that write a catalog of codes. A code of the wrong class raises `ValueError: ... is not a
PerLengthPhaseImpedance`. A phase code needs `conductorCount` and entries that are exactly the lower triangle of that
many conductors. A sequence code needs `r` and `x`; its `source` is `PER_LENGTH_SEQ`.

`CodeMatrix` fields: `conductor_count` (int), and `r`, `x`, `b`, `g` as in `PhaseMatrix` (`b` and `g` are `None` when
unset), keyed by the code's own 1-based rows.

```python
from cimhub_core.getters.line_impedance import get_line_code, get_phase_impedance_code

code = get_line_code(matrix_line)
print(type(code).__name__, get_phase_impedance_code(code, "ohm/mi", "nS/mi").conductor_count)
# PerLengthPhaseImpedance 2
```

Both are called by `cimhub_opendss`.

### get_line_code, get_line_geometry

```python
get_line_code(line) -> cim.PerLengthImpedance | None
get_line_geometry(line) -> cim.WireConfiguration | None
```

`get_line_code` returns the line's own `ACLineSegment.PerLengthImpedance`, else its WireConfiguration's (a template
LineCode, or the matrix equivalent of a configuration). When both are set and differ it raises. `get_line_geometry`
returns the WireConfiguration only when it names a `WireSpacing`: a configuration that holds only a
`PerLengthImpedance` is a template code, not geometry, and returns `None`. Use these two instead of testing
`line.PerLengthImpedance` or `line.WireConfiguration is not None`.

```python
from cimhub_core.getters.line_impedance import get_line_geometry

print(get_line_geometry(matrix_line), get_line_geometry(geometry_line).mRID)
# None wc_601
print(get_line_code(geometry_line))
# None
```

Both are called by `cimhub_gdm`, `cimhub_gridlabd` and `cimhub_opendss`.

## Spacing

Module `cimhub_core.getters.spacing`. A spacing is read from either CIM form, and conductors are keyed by sequence
number, which matches `ACLineSegmentPhase.sequenceNumber` on a line that uses it. The spacing names no phases.

| Form | What it holds | Positions |
|---|---|---|
| `XYSpacing` | `XYConductorPosition.xCoord/yCoord`, in the spacing's frame. A `ConductorGroupPosition` (a bundle, such as a triplex) is expanded into its `SubConductorPosition`s: a `RegularBundlePosition`'s at the corners of its polygon, any other group's at their own coordinates, both rotated by `orientation` | as stored |
| `ConductorDistanceSpacing` | `ConductorDistance.distance` between `sequenceNumber1` and `sequenceNumber2`, and each conductor's height as its distance to a position of kind `earth` | solved by `cimhub_core.derived.spacing`: first conductor at x = 0, mirror images to the right |

An `XYSpacing`'s origin may be ground, the top of the pole or the centre of the crossarm. The line's `ySpacingOffset`
lifts it to a height above ground, so one crossarm design serves poles of any height. There is no default height: a
missing coordinate, distance or height raises. `circuitNumber` is not read, and two conductors on one sequence number
(parallel conductors) raise.

Two NamedTuples:

| NamedTuple | Fields |
|---|---|
| `ConductorXY` | `sequence_number` (int), `kind` (`ConductorPositionKind` or `None`), `x`, `y` (length unit; y is up) |
| `StoredDistances` | `kinds` (`{sequence number: kind}`), `distances` (`{(i, j): value}`, i < j), `heights` (`{sequence number: y}`: an XYSpacing's y in its own frame, or the stored earth distance) |

### get_line_conductor_xy

```python
get_line_conductor_xy(line, unit="m") -> tuple[ConductorXY, ...]
```

The line's conductors with y above ground: the positions of its `ACLineSegmentPhase`s' sequence numbers, phase
conductors first and then neutrals, each in sequence-number order, raised by `ySpacingOffset` (unset means the origin
is ground). A line without `ACLineSegmentPhase`s takes every position. The spacing is the line's `WireSpacing`, or its
WireConfiguration's; both set must be the same spacing. Raises `ValueError` when the line has no spacing, a phase has no
`sequenceNumber`, a phase's number has no conductor in the spacing, or a `ConductorDistanceSpacing` (which already
holds heights above ground) meets a `ySpacingOffset`.

```python
from cimhub_core.getters.spacing import get_line_conductor_xy

for conductor in get_line_conductor_xy(geometry_line, "ft"):
    print(conductor.sequence_number, conductor.kind.value, round(conductor.x, 2), round(conductor.y, 2))
# 1 phase 0.0 28.0
# 2 phase 2.5 28.0
# 3 phase 7.0 28.0
# 4 neutral 4.0 24.0
```

Called by `cimhub_gdm` and `cimhub_opendss`.

### get_spacing_xy, get_spacing_distances, get_stored_distances

```python
get_spacing_xy(spacing, unit="m") -> tuple[ConductorXY, ...]
get_spacing_distances(spacing, unit="m") -> dict[tuple[int, int], float]
get_stored_distances(spacing, unit="m") -> StoredDistances
```

- `get_spacing_xy`: the spacing's conductors in sequence-number order, in the spacing's own frame (no offset). A
  `ConductorDistanceSpacing` needs a height for every conductor and distances that determine one geometry; a distance
  shorter than the height difference, or a stored distance that disagrees with the solved positions by more than a
  relative 1e-4 (`DISTANCE_REL_TOL`), raises.
- `get_spacing_distances`: `{(i, j): d}` for every pair i < j. An `XYSpacing` takes them from
  `get_stored_distances`, which holds every pair. A `ConductorDistanceSpacing` must hold a distance for
  every pair; its heights are not needed.
- `get_stored_distances`: what the spacing holds, as it holds it: an `XYSpacing`'s every pair and its y, a
  `ConductorDistanceSpacing`'s stored rows only. A spacing with no `ConductorDistance` rows at all (GLM's all-zero
  spacing, "no coupling") returns empty dictionaries rather than raising.

Any other `WireSpacing` class raises `ValueError: ... has no conductor positions; only XYSpacing and
ConductorDistanceSpacing are read`.

```python
from cimhub_core.getters.spacing import get_spacing_distances, get_spacing_xy, get_stored_distances

distance_spacing = load_model("cimhub_gridlabd/tests/atoms/catalog/catalog.line_spacing.cimtbl")
spacing = by_mrid(distance_spacing, cim.ConductorDistanceSpacing, "spc_spc_601_ABCN")
print([(c.sequence_number, round(c.x, 2), round(c.y, 2)) for c in get_spacing_xy(spacing, "ft")])
# [(1, 0.0, 28.0), (2, 2.5, 28.0), (3, 7.0, 28.0), (4, 4.0, 24.0)]
print(round(get_spacing_distances(spacing, "ft")[1, 4], 4))
# 5.6569

# a spacing with a pair and no heights: GLM's "AN only" form
no_heights = by_mrid(distance_spacing, cim.ConductorDistanceSpacing, "spc_line_spacing:10")
print(get_stored_distances(no_heights, "in").distances, get_stored_distances(no_heights, "in").heights)
# {(1, 2): 84.0} {}
try:
    get_spacing_xy(no_heights)
except ValueError as error:
    print(error)
# ConductorDistanceSpacing 'spc_line_spacing:10': conductors [1, 2] have no height (a ConductorDistance to a position of kind earth)
```

`get_stored_distances` is called by `cimhub_gridlabd`, which writes any spacing (XY or distances) as a `line_spacing` through it; `get_spacing_xy` by `cimhub_opendss`. No spoke calls
`get_spacing_distances`.

## Wires

Module `cimhub_core.getters.wire`. The conductor catalog entries, and the conductors a configuration or line names.
Four `WireInfo` kinds are read (`WIRE_KINDS`): `OverheadWireInfo`, a plain `CableInfo`,
`ConcentricNeutralCableInfo` and `TapeShieldCableInfo`.

### get_wire_info

```python
get_wire_info(wire, length_unit="m", resistance_unit="ohm/m", current_unit="A") -> WireValues
```

Every value as stored, in the units you name; `None` is unset. `rAC25` and `rAC50` are read. A set `rAC75` raises,
because no producer writes one. A `ratedCurrent` and a normal limit in the wire's own
`AssetInfo.OperationalLimitSet` that are both set must agree. A class other than the four raises.

`WireValues` fields:

| Field | Meaning | Unit |
|---|---|---|
| `kind` | the wire's class, one of `WIRE_KINDS` | |
| `r_dc20`, `r_ac25`, `r_ac50` | resistance at 20 C dc, 25 C ac, 50 C ac | `resistance_unit` (per length) |
| `gmr`, `radius` | geometric mean radius and conductor radius | `length_unit` |
| `rated_current` | `ratedCurrent` | `current_unit` |
| `limits` | the wire's own limits, a `CurrentLimits` | `current_unit` |
| `cable` | a `CableValues`, `None` on an `OverheadWireInfo` | |

`CableValues` fields: `insulation_thickness`, `diameter_over_insulation`, `diameter_over_jacket`,
`diameter_over_screen` (length unit). Five are `None` unless the wire is a `ConcentricNeutralCableInfo`:
`diameter_over_neutral`, `neutral_strand_radius` and `neutral_strand_gmr` (length unit), `neutral_strand_count` (an
int) and `neutral_strand_r_dc20` (resistance unit). Two are `None` unless it is a `TapeShieldCableInfo`:
`tape_thickness` (length unit) and `tape_lap` (percent).

```python
from cimhub_core.getters.wire import get_wire_info

wire = by_mrid(by_geometry, cim.OverheadWireInfo, "wire_acsr_556_5")
values = get_wire_info(wire, "in", "ohm/mi")
print(values.kind.__name__, round(values.r_dc20, 3), round(values.gmr, 4), round(values.radius, 4), values.rated_current)
# OverheadWireInfo 0.186 0.3732 0.4635 730.0

cables = load_model("cimhub_gridlabd/tests/atoms/catalog/catalog.underground_line_conductor.cimtbl")
cable = get_wire_info(by_mrid(cables, cim.ConcentricNeutralCableInfo, "ugc_cncab_cn_250"), "in", "ohm/mi").cable
print(cable.neutral_strand_count, cable.tape_thickness)
# 13 None
```

Called by `cimhub_gdm`, `cimhub_gridlabd` and `cimhub_opendss`.

### get_configuration_wires, get_line_phase_wires

```python
get_configuration_wires(configuration) -> tuple[tuple[int, cim.WireInfo], ...]
get_line_phase_wires(line) -> tuple[tuple[int, cim.WireInfo], ...]
```

`(sequenceNumber, WireInfo)` pairs in sequence-number order. `get_configuration_wires` reads a WireConfiguration's
`WireSequenceConfiguration`s. `get_line_phase_wires` reads a line's own `ACLineSegmentPhase.WireInfo`, and returns an
empty tuple when no phase names a conductor. Both raise on an unset or repeated sequence number. A configuration's
conductor without a `WireInfo` raises, and so does a phase without one beside a phase that has one.

```python
from cimhub_core.getters.wire import get_configuration_wires, get_line_phase_wires

wires = get_configuration_wires(get_line_geometry(geometry_line))
print([(number, wire.mRID) for number, wire in wires])
# [(1, 'wire_acsr_556_5'), (2, 'wire_acsr_556_5'), (3, 'wire_acsr_556_5'), (4, 'wire_acsr_4/0')]
print(get_line_phase_wires(geometry_line))
# ()
```

`get_configuration_wires` is called by `cimhub_gdm`, `cimhub_gridlabd` and `cimhub_opendss`; `get_line_phase_wires`
by `cimhub_opendss`.

## Current limits

Module `cimhub_core.getters.current_limits`.

```python
get_current_limits(equipment, unit="A", *, season=None) -> CurrentLimits
get_asset_info_current_limits(info, unit="A", *, season=None) -> CurrentLimits
equipment_limit_sets(equipment) -> list[OperationalLimitSet]
agreed_limit(owner, what, found) -> float | None
```

CIM hangs an `OperationalLimitSet` on the rated equipment, on its `Terminal`s, or on both. `get_current_limits` reads
every set on the equipment and its terminals (`equipment_limit_sets` lists them, each once). Each `CurrentLimit` is
classified by its `OperationalLimitType.durationKind` (`normal`, `shortTerm`, `emergency`) and valued by
`normalValue`. A type's `season` (`CalendarSeasonKind`, a GridAPPS-D extension) makes the limit seasonal; a type with
no season holds all year.

- `season=None` reads the all-year limits only.
- With a season, each kind is that season's limit, or the all-year one where the season has none.
- Limits of one kind and season must agree (`agreed_limit`; differing values raise). `agreed_limit(owner, what, found)` takes `found`, a list of `(CurrentLimit, value)` pairs, and returns the one value, or `None` for an empty list.
- Raises when a `CurrentLimit` has no `OperationalLimitType`, a type has no `durationKind` or an unsupported one, or a
  limit has no `normalValue`.

`CurrentLimits` fields: `normal`, `short_term`, `emergency`, each a float in `unit` or `None` when the equipment has
no limit of that kind.

`get_asset_info_current_limits` reads a catalog entry's limits, from `AssetInfo.OperationalLimitSet`. An equipment does
not inherit them; `get_wire_info` calls it for a wire's `limits`.

```python
from cimhub_core.getters.current_limits import get_current_limits

print(get_current_limits(matrix_line))
# CurrentLimits(normal=340.0, short_term=None, emergency=600.0)
print(get_current_limits(matrix_line, "kA"))
# CurrentLimits(normal=0.34, short_term=None, emergency=0.6)
```

`get_current_limits` is called by `cimhub_gdm`, `cimhub_gridlabd` and `cimhub_opendss`.

## Impedance tap changer table

Module `cimhub_core.getters.impedance_table`.

```python
get_impedance_table(table, angle_unit="deg") -> tuple[ImpedanceTablePoint, ...]
```

The points of an `ImpedanceTapChangerTable`, in its list order. Which of step, ratio and angle a consumer looks a
point up by is the consumer's, so each is returned as stored. A table with no points raises.

`ImpedanceTablePoint` fields:

| Field | Meaning | Unit |
|---|---|---|
| `step` | tap position, or `None` | |
| `ratio` | turns ratio, or `None` | pu of the end's `ratedU` |
| `angle` | phase angle, or `None` | `angle_unit`, CIM's sign |
| `r` | `(rEnd1, rEnd2, rEnd3)`, each `None` when unset | percent of the end's nominal r |
| `x` | `(xEnd1, xEnd2, xEnd3)`, each `None` when unset | percent of the end's nominal x |

```python
from cimhub_core.getters.impedance_table import get_impedance_table

table = cim.ImpedanceTapChangerTable(mRID="ict_1")
point = cim.ImpedanceTapChangerTablePoint(step=3, ratio=0.95, angle=cim.AngleDegrees(30.0),
                                          rEnd1=cim.PerCent(20.0), xEnd1=cim.PerCent(20.0))
point.ImpedanceTapChangerTable = table
table.ImpedanceTapChangerTablePoint.append(point)
print(get_impedance_table(table))
# (ImpedanceTablePoint(step=3, ratio=0.95, angle=30.0, r=(20.0, None, None), x=(20.0, None, None)),)
```

Called by `cimhub_raw`.

## Earth

Module `cimhub_core.getters.earth`. A geometry is only an impedance once an earth model and a resistivity are chosen.
cim18v17 holds them on `EarthResistivity`, shared by the configurations computed over one earth.

```python
get_earth_resistivity(configuration) -> EarthData | None
get_network_earth(network) -> EarthData
```

`get_earth_resistivity` reads the configuration's `EarthResistivity`, and returns `None` when it names none.
`get_network_earth` is for a line with a direct `WireSpacing`, which cim18v17 cannot associate with an
`EarthResistivity`: it returns the network's one, and raises when the network has none or several.

`EarthData` fields:

| Field | Meaning | Unit |
|---|---|---|
| `model` | `EarthModelKind` (for example `carson`, `deri`), or `None` | |
| `rho` | resistivity | ohm-m (typed `Resistance` in the profile, so it is read in ohm and stands for ohm-m) |
| `earth_return_gmr` | Carson earth-return GMR | m |

```python
from cimhub_core.getters.earth import get_earth_resistivity, get_network_earth

earth = get_earth_resistivity(get_line_geometry(geometry_line))
print(earth.model.value, earth.rho, earth.earth_return_gmr)
# carson 100.0 None
print(get_network_earth(by_geometry) == earth)
# True
```

Both are called by `cimhub_opendss`.
