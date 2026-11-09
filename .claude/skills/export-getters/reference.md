# Export getters: reference

Companion to [SKILL.md](SKILL.md). The getter package `cimhub_core/src/cimhub_core/getters/` is written fresh for
cim18v17. Check what exists there before adding a getter; the signatures in §1 are the agreed design, not a promise
that each one is already implemented.

## 1. Design signatures

```python
class ImpedanceSource(IntEnum):   # ordered: as derive=, the furthest step allowed
    LUMPED = 1; PER_LENGTH_SEQ = 2; MATRIX_REDUCED = 3; GEOMETRY = 4

class SequenceImpedance(NamedTuple):   # None: unset in CIM (SKILL.md semantic rule 8)
    r: float; x: float; b: float | None; g: float | None
    r0: float | None; x0: float | None; b0: float | None; g0: float | None
    source: ImpedanceSource

def get_line_sequence_impedance(line, unit="ohm", *, base_power=None,
                                derive=ImpedanceSource.LUMPED) -> SequenceImpedance
def get_line_sequence_impedance_per_length(line, impedance_unit="ohm/m", admittance_unit="S/m", *,
                                           derive=ImpedanceSource.PER_LENGTH_SEQ) -> SequenceImpedance

class MatrixSource(Enum):   # PHASE_CODE (stored) | SEQUENCE_EXPANDED (assumes a transposed line)
class PhaseMatrix(NamedTuple):   # lower triangles {(row, column): value}, 1-based, conductor order
    phases: tuple[SinglePhaseKind, ...]   # N, s1, s2 included as stored
    r: dict; x: dict; b: dict | None; g: dict | None
    source: MatrixSource

def get_line_phase_impedance_matrix(line, impedance_unit="ohm/m", admittance_unit="S/m", *,
                                    expand_sequence=False) -> PhaseMatrix   # geometry-only line raises
class ConductorXY(NamedTuple):   # sequence_number, kind (ConductorPositionKind), x, y
def get_spacing_xy(spacing, unit="m") -> tuple[ConductorXY, ...]          # in the spacing's frame
def get_spacing_distances(spacing, unit="m") -> dict[tuple[int, int], float]   # {(i, j): d}, i < j
def get_line_conductor_xy(line, unit="m") -> tuple[ConductorXY, ...]      # y above ground (+ spacingYOffset)
def get_terminal_nodes(equipment, *, topological=False) -> tuple[Node, ...]   # Terminal.sequenceNumber order
def get_conductor_phases(equipment) -> tuple[SinglePhaseKind, ...]         # e.g. (C, B); blank Terminal.phases = ABC
def get_terminal_phases(terminal) -> tuple[SinglePhaseKind, ...]           # a transformer end's terminal
def get_base_voltage(obj, unit, *, form) -> float                          # form 'LL' | 'LN'; VoltageLevel's if inside one
def get_switch_state(switch, *, which) -> bool                             # True = open; which 'actual' | 'normal'

class CurrentLimits(NamedTuple):   # by OperationalLimitType.durationKind; None when absent
    normal: float | None; short_term: float | None; emergency: float | None

def get_current_limits(equipment, unit="A", *, season=None) -> CurrentLimits   # sets on the equipment and its terminals
```

A RAW branch then reads:

```python
z = get_line_sequence_impedance(line, "pu", base_power=network.base_power, derive=ImpedanceSource.GEOMETRY)
from_bus, to_bus = (context.bus_number(node) for node in get_terminal_nodes(line, topological=True))
return BranchRecord(i=from_bus, j=to_bus, r=z.r, x=z.x, b=z.b, ...)
```

Every getter reads through `get_qty`:

```python
from cimtables.graph_write import get_qty

r_ohm_per_mile = get_qty(data, "r", "ohm/mi")                   # PhaseImpedanceData
x_percent = get_qty(mesh, "x", "percent")                       # on the From winding's baseU²/baseS
r_pu = get_qty(line, "r", "pu", system_base=network.base_power) # BaseVoltage + system base
rated_kv = get_qty(end, "ratedU", "kV")
```

## 2. cim18v17 attribute paths

| concept | path |
|---|---|
| line geometry | `ACLineSegment.WireConfiguration` → `WireConfiguration.WireSpacing` (`XYSpacing`, `isTemplate`) → `XYConductorPosition` (`sequenceNumber`, `xCoord`, `yCoord`, `kind`) |
| line height | `ACLineSegment.spacingYOffset`: height of the spacing's origin (ground, pole top or crossarm centre) above earth; unset = origin at ground. The spacing: `ACLineSegment.WireSpacing` or `WireConfiguration.WireSpacing` (both set must agree) |
| distance spacing | `ConductorDistanceSpacing.ConductorDistance` (`sequenceNumber1/2`, `conductorKind1/2`, `distance`); a height is a distance to kind `earth`. The GridAPPS-D `fromPhase`/`toPhase`/`from/toSequenceNumber` are not read |
| line conductors | `WireConfiguration.WireSequence` → `WireSequenceConfiguration` (`sequenceNumber`, `WireInfo`) → `OverheadWireInfo` / `ConcentricNeutralCableInfo` / `TapeShieldCableInfo` |
| line phases | `ACLineSegment.ACLineSegmentPhases` → `ACLineSegmentPhase` (`sequenceNumber`, `phase`) |
| line impedance | lumped `ACLineSegment.r/x/bch/gch/r0/x0/b0ch/g0ch`; `ACLineSegment.PerLengthImpedance` → `PerLengthSequenceImpedance` or `PerLengthPhaseImpedance` + `PhaseImpedanceData` (`row`, `column`, `r`, `x`, `b`) |
| catalog transformer | `TransformerTank.TankConfiguration` → `TransformerTankConfiguration` → `TransformerTankEnd` / `TransformerPhaseEnd`, `TransformerWinding`, `TransformerCore`, `TransformerMeshImpedance` |
| balanced transformer | `PowerTransformer` → `PowerTransformerEnd` (`ratedU`, `ratedS`, `r`, `connectionKind`) + `TransformerMeshImpedance` (`FromTransformerEnd`, `ToTransformerEnd`) |
| terminals | `ConductingEquipment.Terminals` → `Terminal` (`sequenceNumber`, `phases`, `ConnectivityNode`) |
| switch | `Switch.open`, `Switch.normalOpen` |
| ratings | `Equipment.OperationalLimitSet` and `Terminal.OperationalLimitSet` → `CurrentLimit` (`normalValue`, `OperationalLimitType.durationKind`, `.season`) |
| base voltage | `VoltageLevel.BaseVoltage` for contents of a VoltageLevel; else `ConnectivityNode.BaseVoltage`, `ConductingEquipment.BaseVoltage`, `TopologicalNode.BaseVoltage`, `TransformerEnd.BaseVoltage` |
| per-phase load | `EnergyConsumer.EnergyConsumerPhase` |
| tap changer | `RatioTapChanger.step` is a **tap position**, never a turns ratio |
| system bases | `network.base_power`, `network.base_frequency` |

Removed in CIM 18 (never read): `WireSpacingInfo`, `WirePosition`, the electrical use of `TransformerTankInfo`,
`TransformerEndInfo`, `ShortCircuitTest` (asset-only now).

## 3. Getter backlog (cleared formats)

Ported first (widest fan-out): `get_terminal_nodes`, `get_conductor_phases`, `get_base_voltage`,
`get_switch_state(which=)`, `get_current_limits`. Ported from the old `get_utils` and rebuilt on `get_qty`:
base-frequency, operational-limit, shunt and tap-changer reads.

| getter | formats | why shared |
|---|---|---|
| `get_line_sequence_impedance(line, 'pu'/'ohm')` | RAW, MATPOWER, DistOPF (lumped), DSS (no linecode), GDM | per-unit math otherwise written per format |
| `get_line_sequence_impedance_per_length` | GLM, DSS, DistOPF | Zs/Zm expansion |
| `get_line_phase_impedance_matrix` | GLM, DSS, DistOPF, GDM | matrix order and susceptance units |
| `get_spacing_xy` / `get_spacing_distances` | GLM, DSS, GDM (DistOPF needs the geometry engine) | GLM wants distances, DSS wants XY |
| `get_base_voltage(obj, unit, form='LL'/'LN')` | GLM, DistOPF, GDM, RAW, MATPOWER | one lookup path, not five fallback chains |
| `get_phase_loads(ec, unit)` + `get_zip_fractions(ec)` | GLM, DSS, RAW, GDM, DistOPF | per-phase vs total ÷ n; ZIP zeros stay zeros |
| `get_shunt_reactive_power(sh, unit, per_phase=)` | DSS, DistOPF, RAW, MATPOWER, GDM | voltage base and `sections` explicit |
| `get_tap_ratio(rtc)` / `get_tap_range(rtc)` | GLM, DSS, DistOPF, RAW, MATPOWER | position vs ratio |
| `get_xfmr_impedance(xfmr, unit, base=)` | GLM, DSS, DistOPF, RAW, MATPOWER, GDM | the base is declared |
| `get_winding_connection(end)` | GLM, DSS, GDM | unknown pairs raise, no per-format default |
| `get_apparent_power_limits(eq, type, unit)` | RAW, MATPOWER | MVA vs amps |
| `get_source(es)`: voltage (pu/kV, angle) + sequence impedance | DSS, GDM, DistOPF | the angle unit is explicit |
| `get_der_output(unit, sign=)` | GLM, DSS, GDM, DistOPF, RAW, MATPOWER | the sign convention is explicit |
| bus numbering context | RAW, MATPOWER | numbering never written back into CIM |

`get_terminal_nodes` returns ConnectivityNodes, or TopologicalNodes with `topological=True` (a `BusBranchModel`'s
terminals have only those); there is no fallback from one to the other.

A node's or equipment's base voltage is CIM's rule: inside a VoltageLevel, `VoltageLevel.BaseVoltage` (its own is
disregarded); elsewhere its own (`ConnectivityNode.BaseVoltage` is new in cim18v17 for nodes outside a VoltageLevel).
Seasonal ratings: `OperationalLimitType.season` (GridAPPS-D extension); `season=None` reads the all-year limits, a
season reads its own and falls back per kind to the all-year one (CYME and others; DSS `Seasons` index a
SeasonDayTypeSchedule, not imported).

A `ConductorDistanceSpacing` read as XY: the first conductor at x = 0, each later one placed from its distances and
heights, mirror images to the right, then every stored distance checked (`derived/spacing.py`,
`DISTANCE_REL_TOL = 1e-4` because stored distances are rounded). Every conductor needs a height; there is no default.
A spacing's positions are in its own frame; a line's heights above ground are its spacing's y + `spacingYOffset`
(user, 2026-11-08: one crossarm design, the pole height on the line). A ConductorDistanceSpacing's earth distances
are heights above ground, so an offset on its line raises. DSS `h=` and GLM `distance_AE` are per line: an exporter
writes one native spacing per (spacing, offset).

Open: the tolerance at which lumped and per-length values "disagree"; a split-phase leg's 'LN' voltage (raises today).

## 4. Geometry → impedance engine (step 4)

- Overhead conductors: Carson/Deri earth return from GMR, radius and AC resistance (`OverheadWireInfo`).
- Concentric-neutral and tape-shield cables; Kron reduction of neutrals; shunt capacitance from potential coefficients.
- Validate against OpenDSS line constants through `opendssdirect` (Z and Yprim to about 1e-6 on every IEEE 13 / 123
  geometry) rather than porting its code. Call `Basic.AllowChangeDir(False)` first: OpenDSS changes the working
  directory, and a deleted temp dir then crashes the next `Compile`.
- Heights: modified Carson ignores them, but `b` (image distance 2h) and Deri do not. No default height.
- A spacing getter reads positions; it never builds spacing objects or adds them to the graph.

## 5. Code tables (`cimhub_core/codes.py`)

```python
import cimprofiles.cim18.cim18v17 as cim

WINDING_CONNECTION = {"wye": "Y", "delta": "D"}      # native spelling -> cim18v17 enum text

def _check(table: dict, enum) -> None:
    unknown = set(table.values()) - {kind.value for kind in enum}
    if unknown:
        raise ValueError(f"not {enum.__name__} values: {sorted(unknown)}")

_check(WINDING_CONNECTION, cim.WindingConnection)
```

In a mapper: `lookup(WINDING_CONNECTION, conn, slot="conn", record_id=name)`. The example keys are illustrative; a
table's real keys are the spellings two spokes share.

## 6. Tests

- Getters are tested on cimtables-loaded reference models (`IEEE13_CDPSM`, `IEEE13_original` via
  `cimtables.load_model`) and on the shape examples in `cimhub_core/src/cimhub_core/shapes/`. No importer is needed.
- Per getter: values in the requested unit against hand-checked numbers, `source` on every derived result, a raise
  for each missing input, and a pu round trip: `set_attr(Qty(x, 'pu'))` → `get_qty(..., 'pu')` returns x.
- A conformance test asserts that no GLM/DSS converter calls `get_line_sequence_impedance` on a line with geometry.
- Run loads inside `cimhub_core.cimtbl_testing.cim_scope()` (skill `atom-tests`).
