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
def get_line_sequence_impedance_per_length(line, unit="ohm/m") -> SequenceImpedance
def get_line_phase_impedance_matrix(line, unit="ohm/m") -> PhaseMatrix      # conductor order
def get_spacing_xy(spacing, unit="m", *, height=None) -> tuple[ConductorXY, ...]
def get_spacing_distances(spacing, unit="m") -> SpacingDistances           # pairwise + heights
def get_terminal_nodes(equipment) -> tuple[Node, ...]                      # Terminal.sequenceNumber order
def get_conductor_phases(equipment) -> tuple[SinglePhaseKind, ...]         # e.g. (C, B)
def get_current_limits(equipment) -> tuple[float | None, float | None]     # (normal, emergency) amps
```

A RAW branch then reads:

```python
z = get_line_sequence_impedance(line, "pu", base_power=network.base_power, derive=ImpedanceSource.GEOMETRY)
from_bus, to_bus = (context.bus_number(node) for node in get_terminal_nodes(line))
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
| line conductors | `WireConfiguration.WireSequence` → `WireSequenceConfiguration` (`sequenceNumber`, `WireInfo`) → `OverheadWireInfo` / `ConcentricNeutralCableInfo` / `TapeShieldCableInfo` |
| line phases | `ACLineSegment.ACLineSegmentPhases` → `ACLineSegmentPhase` (`sequenceNumber`, `phase`) |
| line impedance | lumped `ACLineSegment.r/x/bch/gch/r0/x0/b0ch/g0ch`; `ACLineSegment.PerLengthImpedance` → `PerLengthSequenceImpedance` or `PerLengthPhaseImpedance` + `PhaseImpedanceData` (`row`, `column`, `r`, `x`, `b`) |
| catalog transformer | `TransformerTank.TankConfiguration` → `TransformerTankConfiguration` → `TransformerTankEnd` / `TransformerPhaseEnd`, `TransformerWinding`, `TransformerCore`, `TransformerMeshImpedance` |
| balanced transformer | `PowerTransformer` → `PowerTransformerEnd` (`ratedU`, `ratedS`, `r`, `connectionKind`) + `TransformerMeshImpedance` (`FromTransformerEnd`, `ToTransformerEnd`) |
| terminals | `ConductingEquipment.Terminals` → `Terminal` (`sequenceNumber`, `phases`, `ConnectivityNode`) |
| switch | `Switch.open`, `Switch.normalOpen` |
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
| `get_base_voltage(node_or_eq, unit, form='LL'/'LN')` | GLM, DistOPF, GDM, RAW, MATPOWER | one lookup path, not five fallback chains |
| `get_phase_loads(ec, unit)` + `get_zip_fractions(ec)` | GLM, DSS, RAW, GDM, DistOPF | per-phase vs total ÷ n; ZIP zeros stay zeros |
| `get_shunt_reactive_power(sh, unit, per_phase=)` | DSS, DistOPF, RAW, MATPOWER, GDM | voltage base and `sections` explicit |
| `get_tap_ratio(rtc)` / `get_tap_range(rtc)` | GLM, DSS, DistOPF, RAW, MATPOWER | position vs ratio |
| `get_xfmr_impedance(xfmr, unit, base=)` | GLM, DSS, DistOPF, RAW, MATPOWER, GDM | the base is declared |
| `get_winding_connection(end)` | GLM, DSS, GDM | unknown pairs raise, no per-format default |
| `get_apparent_power_limits(eq, type, unit)` | RAW, MATPOWER | MVA vs amps |
| `get_source(es)`: voltage (pu/kV, angle) + sequence impedance | DSS, GDM, DistOPF | the angle unit is explicit |
| `get_der_output(unit, sign=)` | GLM, DSS, GDM, DistOPF, RAW, MATPOWER | the sign convention is explicit |
| bus numbering context | RAW, MATPOWER | numbering never written back into CIM |

Open: whether `get_terminal_nodes` returns ConnectivityNodes or TopologicalNodes on a `BusBranchModel` (decide in the
first bus-branch wave), and the tolerance at which lumped and per-length values "disagree".

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
