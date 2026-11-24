# Writing a getter

A getter is the one place that knows how CIM holds a concept. An exporter never reads a CIM attribute for a value
itself: it calls a getter and shapes the result into the native format.

```text
cim18v17 objects ──getters (units, bases, resolution)──▶ NamedTuples ──spoke mapper──▶ native model ──writer──▶ file
```

The rules below are the ones in the
[`export-getters` skill](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/export-getters/SKILL.md),
shown as they appear in real getters. Where a doc and the code disagree, the code wins. The finished getters are listed
in the [getter reference](../reference/index.md). Before you add one, check the code in
[`getters/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_core/src/cimhub_core/getters), and check that
the capability does not belong upstream (cimtables, cimbuilder, cimgraph, cimprofiles, cim-topology). If it does, file
it in
[`UPSTREAM_REQUESTS.md`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.development/UPSTREAM_REQUESTS.md)
instead of writing a local stand-in (invariant I9).

Spoke sessions do not edit core. A new getter is a request to the core owner; this page is what the core owner (and a
reviewer of a spoke's request) checks it against.

## Where a getter goes

| What | Where |
|---|---|
| A getter for one CIM concept | `cimhub_core/src/cimhub_core/getters/<concept>.py`, one module per concept (`line_impedance.py`, `tap_changer.py`, `shunt.py`) |
| Helpers every getter shares | `getters/__init__.py`: `describe(obj)` and `required_qty(obj, attribute, unit, **bases)` |
| A formula CIM has no attribute for | `cimhub_core/src/cimhub_core/derived/<name>.py`, a pure function ([Derived values](../reference/derived.md)) |
| Its tests | `cimhub_core/tests/test_getters_<module>.py` |
| Its fixture | a shape in `cimhub_core/src/cimhub_core/shapes/`, or an inline atom in the test |
| Its docs | a row in [the reference table](../reference/index.md) and a section on the page for its group |

A module starts with a docstring that says which CIM paths it reads, and what it deliberately does not read. A reader
should learn from it what a new producer has to write. See the docstrings of
[`current_limits.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/src/cimhub_core/getters/current_limits.py)
and
[`tap_changer.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/src/cimhub_core/getters/tap_changer.py).

## The shape of a getter

A getter takes the CIM object and keyword arguments that choose a meaning or a unit. It reads through `get_qty`, raises
for what it cannot go on without, and returns a `NamedTuple`. This is the whole of `get_switch_state`:

```python
import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe

STATE_ATTRIBUTE = {"actual": "open", "normal": "normalOpen"}


def get_switch_state(switch: cim.Switch, *, which: str) -> bool:
    if which not in STATE_ATTRIBUTE:
        raise ValueError(f"which must be one of {sorted(STATE_ATTRIBUTE)}, not {which!r}")
    attribute = STATE_ATTRIBUTE[which]
    is_open = getattr(switch, attribute)
    if is_open is None:
        raise ValueError(f"{describe(switch)}: {attribute} is unset")
    return is_open
```

A toy getter written the same way runs against a public shape. It uses `required_qty`, which is `get_qty` that raises
`ValueError` naming the class and mRID when the attribute is unset.

```python
from pathlib import Path
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables import load_model

from cimhub_core.getters import required_qty
from cimhub_core.getters.switch_state import get_switch_state

SHAPES = Path("cimhub_core/src/cimhub_core/shapes")


def by_mrid(network, cls, mrid):
    return next(obj for obj in network.graph[cls].values() if obj.mRID == mrid)


class LineLength(NamedTuple):
    length: float  # the caller's unit


def get_line_length(line: cim.ACLineSegment, unit: str = "m") -> LineLength:
    return LineLength(required_qty(line, "length", unit))


lines = load_model(SHAPES / "line_by_impedance.cimtbl")
line = by_mrid(lines, cim.ACLineSegment, "ln_l1")
print(round(get_line_length(line, "ft").length, 6), round(get_line_length(line).length, 3))
# 300.0 91.44

line.length = None
try:
    get_line_length(line)
except ValueError as error:
    print(error)
# ACLineSegment 'ln_l1': length is unset

switch = by_mrid(load_model(SHAPES / "switch.cimtbl"), cim.LoadBreakSwitch, "sw_s1")
print(get_switch_state(switch, which="actual"))
# True
try:
    get_switch_state(switch)
except TypeError as error:
    print(error)
# get_switch_state() missing 1 required keyword-only argument: 'which'
```

## The rules

| # | Rule | Real code that shows it |
|---|---|---|
| 1 | One getter per CIM concept, returning all of its fields. Callers ignore what they do not need. Never `get_line_r_x` and `get_line_r0_x0`. | `get_line_sequence_impedance` returns r, x, b, g and the zero-sequence values in one `SequenceImpedance` |
| 2 | Return a `NamedTuple`. It unpacks positionally, `z.x` cannot swap with `z.r`, and a new field does not break callers. Never a bare tuple or a dict of mixed values. | `TransformerModel`, `Winding`, `TapSteps` |
| 3 | The caller names the unit; plain floats come out. No `CIMUnit` leaves a getter. | `get_current_limits(line, "kA")`, `get_wire_info(wire, "in", "ohm/mi")` |
| 4 | All unit and base conversion goes through `get_qty`. | every `get_qty(..., unit)` call in `getters/` |
| 5 | Base selection is `z_base`'s, never the getter's. | `get_line_sequence_impedance(..., "pu", base_power=...)` |
| 6 | cim18v17 only. No electrical `*Info` catalog. | `get_line_geometry` and `get_line_code` instead of `WireSpacingInfo`; `TransformerTankConfiguration` instead of `TransformerTankInfo` |
| 7 | No profile-module argument. There is one profile; read classes from the object. | `cim` is imported once at the top of each module |
| 8 | Format-specific shapes stay in the spoke: GLM `"BCN"`, DSS `.1.2.3` bus suffixes, RAW bus numbers, naming policy. Core returns CIM meaning: phases as `SinglePhaseKind` in conductor order, nodes as objects. | `get_conductor_phases`, `get_terminal_nodes` |
| 9 | Getters are pure. They read and return; they never add objects to the graph or write a computed value back onto CIM. | none writes an attribute |
| 10 | Fail fast. A missing required value raises, naming the class and mRID. No silent default (`0.0`, `1.0`, a 10 m height, 60 Hz). | `required_qty`, `describe` |

Phases come from the equipment (`ACLineSegment.ACLineSegmentPhases`, `Terminal.phases`), never from a template's
back-list: `WireConfiguration.ACLineSegements[0]` can be empty.

## get_qty and base selection

`cimtables.graph_write.get_qty` is the read-side mirror of `set_attr`:

```python
get_qty(source_object, attribute_name, unit, *, base=None, system_base=None, power_base=None) -> float | None
```

It returns the attribute in `unit` (`'kV'`, `'ohm/mile'`, `'MVAr'`), or `None` when it is unset. `'pu'` and
`'percent'` on an ohm- or siemens-typed attribute are `set_attr`'s conversion inverted, through the same
`cimtables.impedance.z_base`. The getter picks no base; the object's own class does:

| The object is | `z_base` uses |
|---|---|
| a rated class: a `TransformerWinding`, a `PowerTransformerEnd` | its own `baseU`/`baseS` (winding) or `ratedU`/`ratedS` (end) |
| a `From*` reference, such as a `TransformerMeshImpedance` | the From end's |
| an unrated class: an `ACLineSegment`, an `EnergySource` | its `BaseVoltage` and the system base power (`network.base_power`), passed as `system_base=` |

A missing rating or BaseVoltage raises. Per-unit on an unrated class without a `system_base` raises too:

```python
from cimhub_core.getters.line_impedance import ImpedanceSource, get_line_sequence_impedance

line = by_mrid(lines, cim.ACLineSegment, "ln_l2")
z = get_line_sequence_impedance(line, "pu", base_power=lines.base_power, derive=ImpedanceSource.PER_LENGTH_SEQ)
print(round(z.r, 4))
# 0.3073
try:
    get_line_sequence_impedance(line, "pu", derive=ImpedanceSource.PER_LENGTH_SEQ)
except ValueError as error:
    print(error)
# ACLineSegment 'ln_l2': a pu/percent impedance needs a rated From* reference, or a BaseVoltage with nominalVoltage and a system_base power (in .cimtbl: a BasePower declared before this row)
```

The options beyond `unit`:

- `base='system'` forces the system base, as a `(pu system)` column does on import.
- `power_base=` reads a mesh impedance's percent on another power at the same voltage. `get_transformer_model` uses it
  for an end form with a declared `base_power`.
- A `PerCent` attribute read as `'percent'` returns the stored number.

`get_qty` raises for an attribute that is not a `CIMUnit`. The one exception in the getters is `get_regulating_control`: a `RegulatingControl`'s `targetValue` is a plain float, so it builds the `CIMUnit` for the control's mode and calls `.to()`.

Never re-implement any of it: no `* 1e3`, no local `z_base`, no `float(obj.r)` arithmetic. See
[Units](units.md) for the import side. If `get_qty` lacks a feature a getter needs, that is an upstream request.

Two kinds of arithmetic are fine. A linear reduction (a mean, a difference, a Kron elimination) of values read in the
caller's unit needs no conversion afterwards, which is how `line_impedance.py` reduces a matrix. A getter that scales
by a ratio of two ratings (`z × S_new / S_old` in `get_transformer_model`) does so on percent values `get_qty`
returned, never on raw `CIMUnit` internals.

## None or raise

| Situation | The getter |
|---|---|
| An optional value CIM leaves unset (a line's `b`, `g`, zero sequence; a tap's `normalStep`) | returns `None`, never `0.0`, so "not modelled" and "zero" stay distinguishable. The spoke decides, with a comment saying why |
| A value the concept cannot be read without (a line's r and x, a winding's `ratedS`) | raises `ValueError` naming the class and mRID |
| Two places hold the same value and differ (lumped and per-length r; `ratedCurrent` and a normal limit) | raises, with the tolerance written down (`DISAGREEMENT_REL_TOL`) |
| An argument that chooses a meaning (`which`, `sign`, `sections`, `voltage`) | has no default and is keyword-only, so omitting it is a `TypeError`; an unknown value raises `ValueError: ... must be one of [...]` |
| A CIM association that is optional (a tap's control, a device's schedule) | returns `None` for the whole result (`get_equipment_control`, `get_load_schedule`) |
| Something the getter does not read | raises when it is set (`get_wire_info` raises on `rAC75`; `get_shunt_reactive_power` on `gPerSection`), until a producer writes one |

Each spoke writes its own rule for a `None`: RAW and MATPOWER write `b = 0.0` (the formats' own default), and DSS
writes `C1=0` because a blank would let the engine default in line charging.

## Semantic rules the getters settle

Each ambiguity in CIM is settled once, in one getter, and the choice is the caller's argument.

| Rule | Getter | How it shows up |
|---|---|---|
| Switch state | `get_switch_state(switch, which=)` | `'actual'` reads `Switch.open`, `'normal'` reads `normalOpen`. `get_in_service(equipment, which=)` and `get_tap_ratio(tap, which=)` do the same: the two differ in any model that is not as built |
| Generator sign | `get_der_output(equipment, sign=)` | CIM terminal `p` is positive into equipment, so generation is negative. `'load'` returns as stored and `'generation'` negates; no spoke negates itself. Nameplate limits are stored in the generation sign and every rating getter returns `(min, max)` in the `sign=` you name |
| Per-phase load | `phase_power.device_power` | the `<Class>Phase` children's own p and q when every child has them, else the total split evenly over the phase conductors. Children with values must be exactly those conductors and sum to the total. Loads and DER share it |
| Shunt Q | `get_shunt_reactive_power(shunt, sections=, voltage=)` | one formula, `Q = bPerSection × V² × sections`, and the caller names both factors: `sections` is `'actual'`, `'normal'` or `'maximum'`; `voltage` is `'nominal'` (`nomU`) or `'base'` (the BaseVoltage) |
| Transformer base | `get_transformer_model(unit, impedance_unit, base_power=)` | every percent or pu on one declared power base, default winding 1's `ratedS`; no format picks or rebases its own |
| Raw floats | `get_qty` | an attribute that is not a `CIMUnit` fails fast; never guess kV against V |
| Frequency | the caller | no getter reads a frequency or hard-codes 60 Hz. A derived function takes `frequency` as an argument, and the spoke passes `network.base_frequency` |
| Unset is `None` | all | the spoke decides |

## Impedance resolution order

A format that takes only sequence values may have to reduce what CIM holds. `line_impedance.py` does this as a
caller-limited order, not a hidden fallback chain; the steps and the `ImpedanceSource` values are on the
[Lines and wires](../reference/lines.md) page. What a new getter with several sources must keep:

- `derive=` caps how far the order may go. The default reads stored values only and raises when they are absent.
- Every result carries `source`, so logs, tests and goldens show which values are derived.
- Two sources present and disagreeing beyond a tolerance raise. The precedence is written down and tested.
- A geometry-capable format never uses the chain. It exports native geometry through the spacing and wire getters, and
  takes the phase matrix only where CIM has no geometry. `get_line_phase_impedance_matrix` raises on a line that has
  geometry and no `PerLengthImpedance`.
- Heights come from `get_line_conductor_xy` (the spacing's y plus `ySpacingOffset`, or a distance to earth) and raise
  when absent.

## Tests

One test file per getter module, `cimhub_core/tests/test_getters_<module>.py`, run with `scripts/test-all.sh core` (one
pytest process per package; never one whole-repo pytest). The files share a layout:

| Piece | How it looks |
|---|---|
| Docstring | one line naming the module and what it is tested on |
| Scope | an autouse fixture: `with cim_scope(): yield`, so `load_model`'s process-wide profile is put back |
| Fixture | a public shape, `load_model(SHAPES / "line_by_impedance.cimtbl")` with `SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"`; or an inline atom written to `tmp_path` (a header, a few rows) for a case no shape holds; or a CIM object built by hand for a one-attribute getter |
| Expected values | hand-computed from the shape text, not from the getter |
| Errors | `pytest.raises(ValueError, match="LinearShuntCompensator 'cap_c1': normalSections is unset")`, so the message naming class and mRID is itself a contract |

What a getter's tests assert:

1. **The value in the declared unit**, with `pytest.approx`: `get_current_limits(line, "kA")` against the shape's 340 A.
2. **Every `None` path**: an unset optional value is `None`, and the NamedTuple compares equal to the whole expected
   tuple, so a silent default shows up.
3. **Every raise**: each required value unset, each unknown argument value, each two-sources-disagree case.
4. **The documented rule once per branch**: both signs of a DER, both `which` values, each `ImpedanceSource` step and
   the `derive` cap.
5. **No mutation**: where a getter might be tempted to write back, the object is unchanged.

A new getter that needs a shape row nobody has written is a change to the shapes (see
[Canonical shapes](shapes.md)) and goes through the core owner. Fixtures must have a documented public origin; see
[Testing](testing.md).

## Anti-patterns

| Do not | Do |
|---|---|
| `line.r.to('ohm') / z_base` or `value * 1000` in an exporter, or a getter with its own `to_float` | `get_qty(line, "r", "pu", system_base=...)` |
| call `get_line_sequence_impedance` from a GLM or DSS converter on a line that has geometry | export geometry through the spacing and wire getters |
| `line.WireConfiguration is not None` as the geometry test, or `line.PerLengthImpedance` as the code | `get_line_geometry(line)` and `get_line_code(line)` |
| read `WireSpacingInfo`, `WirePosition` or `TransformerTankInfo` | read `WireSpacing`, `XYConductorPosition` and `TransformerTankConfiguration` |
| return a dict or a bare tuple, or a different shape per format | one `NamedTuple` per concept |
| `value if value else 1.0`, a `Point(0, 0)` fallback, a default height | return `None`, or raise |
| write a computed value back onto a CIM object | return it |
| copy a code table into a second spoke | keep it in the spoke until two use it, then move it to core |
| `.get(value, default)` on a native-code table | `cimhub_core.cimtbl.lookup(table, value, slot=..., record_id=...)`, which raises on an unmapped value |

## Checklist

1. Check upstream (cimtables, cimbuilder, cimgraph, cimprofiles, cim-topology) and `getters/` for the capability.
2. Name the CIM path in the module docstring, and what it does not read.
3. Write the NamedTuple, then the getter: unit and meaning arguments, `get_qty` for every quantity, `None` for optional
   values, `ValueError` with `describe(obj)` for required ones.
4. Write the tests against a shape or an inline atom; assert units, `None`, and every raise.
5. Add the row to [the reference table](../reference/index.md) and a section to its page.
6. Run `scripts/test-all.sh core`, then `scripts/leak-gate.sh`, which must print `clean`.
