# Using the getters

A getter reads one CIM concept from one CIM object and returns plain floats, enums and NamedTuples. The code on this
page runs against [`feeder.cimtbl`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/docs/guide/feeder.cimtbl),
the model of the [quick start](quickstart.ipynb), loaded like this:

```python
import cimprofiles.cim18.cim18v17 as cim
import cimtables

from cimhub_core.cimtbl_testing import cim_scope

with cim_scope():
    network = cimtables.load_model('feeder.cimtbl')


def find(cim_class, mrid):
    return next(obj for obj in network.graph[cim_class].values() if obj.mRID == mrid)
```

A model read from CIM XML with cim-graph works the same way. The getters take cim18v17 objects and nothing else.

## Name the unit

CIM stores SI. A getter takes the unit you want and converts once, through `cimtables.graph_write.get_qty`. The
units are pint strings, such as `'kW'`, `'kV'`, `'ohm/km'` or `'uS/km'`.

```python
from cimhub_core.getters.load import get_phase_loads

load = find(cim.EnergyConsumer, 'ld_n1')
print(get_phase_loads(load, 'kW', 'kVAr').total)   # PhasePower(p=1155.0, q=660.0)
print(get_phase_loads(load).total)                 # PhasePower(p=1155000.0, q=660000.0)
```

Where a getter has a default it is usually the SI unit, so a call with no unit argument returns W, VAr, V, ohm or S.
The exceptions are angles (`'deg'`), time (`'s'`), a transformer's `impedance_unit` (`'percent'`) and a few others, such
as currents (`'A'`) and irradiance (`'W/m2'`). Some getters have no default, because the unit is a decision:
`get_source` makes you pass `angle_unit=`, any pint angle unit such as `'deg'` or `'rad'`.

A unit with the wrong dimension raises pint's `DimensionalityError`. Active and reactive power have the same
dimension, so `'kVAr'` is accepted for an active power and gives a number in the wrong column. Pass the unit that
matches the argument's name.

## Read NamedTuple fields by name

Results are NamedTuples, so every field has a name and the units of the fields are fixed by the call.

```python
loads = get_phase_loads(find(cim.EnergyConsumer, 'ld_n2'), 'kW', 'kVAr')
print(loads.phases)             # (A, B, C) as SinglePhaseKind members
print(loads.split)              # False: each phase holds its own values
for phase, power in loads.per_phase.items():
    print(phase.value, power.p, power.q)
```

Phases are `cim.SinglePhaseKind` members, in the order A, B, C, s1, s2, N. A result keyed by phase is a dict keyed by
those members. Enumerations such as `connection` and `form` are CIM or core enums; read `.value` or `.name`.

## `None` is not zero

A field of a result is `None` when CIM leaves the value unset. Zero and unset are different statements, and a
getter never turns one into the other.

```python
from cimhub_core.getters.line_impedance import ImpedanceSource, get_line_sequence_impedance

line = find(cim.ACLineSegment, 'ln_trunk')
z = get_line_sequence_impedance(line, derive=ImpedanceSource.PER_LENGTH_SEQ)
print(z.r0, z.g)    # 0.359664 None
```

Your code decides what an unset value means in your format. Which fields of a result can be `None` is in the
[reference](../reference/index.md); the type annotation of the field says it too (`float | None`).

One value does have a documented default. `get_shunt_admittance` returns `g` as `0.0` when the shunt's
`gPerSection` is unset.

## Errors

A getter raises `ValueError` when the model cannot be read as asked. Where the fault is in one object, the message
starts with its class and mRID. A bad argument is named instead. A getter does not fall back to a guess.

| Message | Meaning |
|---|---|
| `EnergyConsumer 'ld_n1': p is unset` | The getter needs this attribute and CIM has none. |
| `which must be one of ['actual', 'normal'], not 'now'` | A decision argument was not one of its values. |
| `unit must be one of ['ohm', 'pu'], not 'S'` | The getter takes a fixed set of unit words, not any pint unit. |
| `ACLineSegment 'ln_trunk': no sequence impedance within derive=LUMPED (...)` | No source of the value is within the cap you allowed. |
| `... have different phases ...`, `... has no Terminals` | The model's connectivity is incomplete. |
| `ConformLoadGroup '...': 2 schedules with no Season or DayType ...` | Two places hold the value, and CIM allows one. |
| `... a pu/percent impedance needs a rated From* reference, or a BaseVoltage ...` | A per-unit read has no base. See [Units](units.md). |

```python
try:
    get_line_sequence_impedance(line)
except ValueError as error:
    print(error)
```

A missing keyword raises `TypeError`, as for any Python function. `get_der_output(inverter, 'kW', 'kVAr')` without
`sign=` does.

## Arguments that carry a decision

Some arguments are keyword-only, with no default, so that a call says what it means. A getter that would have
returned the wrong answer for half its callers has one of these.

| Argument | Getters | Values |
|---|---|---|
| `sign=` | the DER getters, `get_device_schedule` | `'load'` as CIM stores it, `'generation'` negated. See [Units](units.md). |
| `which=` | `get_switch_state`, `get_in_service`, `get_tap_ratio`, `get_tap_voltage` | `'actual'` or `'normal'` (taps also `'low'`, `'high'`) |
| `derive=` | `get_line_sequence_impedance`, `get_line_sequence_impedance_per_length` | an `ImpedanceSource` |
| `expand_sequence=` | `get_line_phase_impedance_matrix` | `True` to build a phase matrix from a sequence code, which assumes a transposed line; without it the getter raises |
| `base_power=` | line, source, shunt and transformer getters | `network.base_power`, for `'pu'` and `'percent'` |
| `sections=`, `voltage=` | `get_shunt_reactive_power` | which section count, which voltage |
| `form=` | `get_base_voltage` | `'LL'` or `'LN'` |
| `topological=` | `get_terminal_nodes` | read the bus-branch `TopologicalNode` instead of the `ConnectivityNode` |

### `which=`: actual or normal

CIM keeps a state and its normal value apart: `Switch.open` and `normalOpen`, `inService` and `normallyInService`. They
differ in any model that is not as built, so there is no default.

```python
from cimhub_core.getters.in_service import get_in_service

print(get_in_service(line, which='actual'))   # None: the file does not say
```

`get_switch_state` returns `True` for open, and raises when the attribute is unset. `get_in_service` returns `None`.

### `derive=`: how far a line may look

A line's impedance can be on the line itself, in a per-length code, in a matrix, or only in its geometry.
`ImpedanceSource` names these steps in order, and `derive=` is the furthest the getter may go.

| `ImpedanceSource` | Reads |
|---|---|
| `LUMPED` | `ACLineSegment.r`, `x`, `bch`, `gch` (and the zero-sequence ones) |
| `PER_LENGTH_SEQ` | a `PerLengthSequenceImpedance`, times the length |
| `MATRIX_REDUCED` | a `PerLengthPhaseImpedance` reduced to sequence values |
| `GEOMETRY` | a WireConfiguration's spacing and wires through line constants (not built: it raises `NotImplementedError`) |

The default for `get_line_sequence_impedance` is `LUMPED`, and for the per-length getter it is `PER_LENGTH_SEQ`. The
result's `source` field says which step produced it. When the lumped values and a per-length source both lie within the
cap and disagree, the getter raises; when they agree, the lumped values win.

```python
z = get_line_sequence_impedance(line, 'ohm', derive=ImpedanceSource.PER_LENGTH_SEQ)
print(z.source.name, round(z.r, 4))      # PER_LENGTH_SEQ 0.2134
```

### `base_power=`: the per-unit base

`'pu'` and `'percent'` need a base power. Pass `network.base_power`, which is the model's `BasePower` object. See
[Units, bases and signs](units.md).

### `sections=` and `voltage=`: a shunt

`get_shunt_reactive_power` gives the reactive power of the sections in service. `sections=` is `'actual'`,
`'normal'` or `'maximum'`, and `voltage=` is `'nominal'` (the shunt's `nomU`) or `'base'` (its BaseVoltage). The
reactive power is `b V² n`, so the voltage you choose changes the answer.

### Where frequency and the system base come from

No getter takes a frequency. A line code carries its own `calculatedFrequency`, and the model carries a system
frequency and a system base power:

```python
from cimhub_core.getters.line_impedance import get_line_code

print(network.base_power.to('MVA'))    # 10.0
print(network.base_frequency)          # 60.0 rotPers
print(get_line_code(line).calculatedFrequency)   # 60.0 rotPers
```

`network.base_power` and `network.base_frequency` come from the file's `BasePower` and `BaseFrequency` objects. When
a file has neither, cim-graph's own defaults are in their place: 100 MVA and 60 Hz. Declare both in a model
where a per-unit value matters.

## Which getter

| To read | Getter | Reference |
|---|---|---|
| A line's sequence impedance, whole line or per length | `get_line_sequence_impedance`, `get_line_sequence_impedance_per_length` | [Lines and wires](../reference/lines.md) |
| A line's phase matrix, its code, its geometry | `get_line_phase_impedance_matrix`, `get_line_code`, `get_line_geometry` | [Lines and wires](../reference/lines.md) |
| A transformer's windings, mesh and core | `get_transformer_units`, `get_transformer_model` | [Transformers](../reference/transformers.md) |
| Tap changers and regulator control | `get_tap_steps`, `get_tap_ratio`, `get_tap_changer_control` | [Transformers](../reference/transformers.md) |
| A load's phases, response and schedule | `get_phase_loads`, `get_load_response`, `get_load_schedule` | [Loads](../reference/loads.md) |
| A shunt's reactive power or admittance | `get_shunt_reactive_power`, `get_shunt_admittance` | [Loads](../reference/loads.md) |
| A source, an inverter, a machine | `get_source`, `get_der_output`, `get_inverter_rating` | [Sources and DER](../reference/der.md) |
| A node's connection, phases, base voltage, limits, switch state | `get_terminal_nodes`, `get_conductor_phases`, `get_base_voltage`, `get_current_limits`, `get_switch_state` | [Topology and state](../reference/topology.md) |
