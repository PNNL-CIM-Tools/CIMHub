# Transformers and regulators

The getters for a transformer's windings, impedance and core, for its tap changers, and for the controls that drive
them. They live in `getters/transformer.py`, `tap_changer.py` and `control.py`. Conventions common to every getter are
on the [reference landing page](index.md).

The examples use the shapes in `cimhub_core/src/cimhub_core/shapes/` and run from the repo root. This block is the
setup the later ones share.

```python
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
from cimtables import load_model


def by_mrid(network, cls, mrid):
    return next(obj for obj in network.graph[cls].values() if obj.mRID == mrid)


SHAPES = Path("cimhub_core/src/cimhub_core/shapes")
by_ends = load_model(SHAPES / "transformer_by_ends.cimtbl")
by_phase_ends = load_model(SHAPES / "transformer_by_phase_ends.cimtbl")
by_template = load_model(SHAPES / "transformer_by_template.cimtbl")
by_tank_impedance = load_model(SHAPES / "transformer_by_tank_impedance.cimtbl")
regulator = load_model(SHAPES / "regulator.cimtbl")


def summarize(model):
    print(model.form.name, "base_power", model.base_power)
    for winding in model.windings:
        phases = "".join(phase.value for phase in winding.phases)
        print(" ", winding.number, phases, winding.rated_u, winding.rated_s, winding.base_u, winding.r)  # number, phases, ratedU, ratedS, baseU, r
    print("  mesh", {pair: (z.r, round(z.x, 3)) for pair, z in model.mesh.items()})
    print("  core", model.core)
```

## The transformer model

Module `cimhub_core.getters.transformer`. One getter reads the windings, the mesh impedance and the core of a
transformer as one model, whatever CIM form holds them.

### get_transformer_units

```python
get_transformer_units(transformer) -> tuple
```

The units `get_transformer_model` reads: a `PowerTransformer`'s `TransformerTank`s when it has any, else the
transformer itself (a `PowerTransformer` without tanks, or an `AutoTransformer`). A `PowerTransformer` that has tanks
passed straight to `get_transformer_model` raises: read each unit this returns.

### get_transformer_model

```python
get_transformer_model(unit, impedance_unit="percent", *, base_power=None, voltage_unit="V",
                      power_unit="VA") -> TransformerModel
```

| Parameter | Meaning |
|---|---|
| `unit` | a `TransformerTank`, a `PowerTransformer` without tanks, or an `AutoTransformer` |
| `impedance_unit` | `'percent'` or `'pu'`; anything else raises `ValueError: impedance_unit must be one of ['percent', 'pu'], not ...` |
| `base_power` | an `ApparentPower` (for example `network.base_power`) every impedance and admittance is put on. Default: winding 1's `ratedS` |
| `voltage_unit` | unit of `rated_u`, `base_u` |
| `power_unit` | unit of `rated_s`, `base_s` and `TransformerModel.base_power` |

It raises `ValueError` when a form is ambiguous, when a rating a value needs is unset, or when two places that hold the
same value disagree.

```python
from cimhub_core.getters.transformer import get_transformer_model, get_transformer_units

substation = by_mrid(by_ends, cim.PowerTransformer, "xf_sub")
[unit] = get_transformer_units(substation)  # no tanks: the transformer itself
summarize(get_transformer_model(unit, voltage_unit="kV", power_unit="kVA"))
# BY_ENDS base_power 5000.0
#   1 ABC 115.0 5000.0 None 0.5
#   2 ABCN 4.16 5000.0 None 0.5
#   mesh {(1, 2): (None, 8.0)}
#   core CoreAdmittance(g=None, b=None)
```

Called by `cimhub_gdm`, `cimhub_gridlabd`, `cimhub_opendss` and `cimhub_raw`.

### The base every value is on

Every impedance and admittance comes out in percent or pu on one power base, and the voltage is always the From
winding's own (`ratedU`, or a coil's `baseU`).

| Case | How the value is read |
|---|---|
| `base_power` given, and the form is `BY_ENDS` or `AUTO` | Each ohm and siemens is read on that power directly (`get_qty(power_base=)`). The ends need no `ratedS` (a three-winding unit whose ends have none still reads) |
| otherwise | CIM's value is read as a percent on its From winding's own `baseU²/baseS`, then moved to the declared base by the power only: `z × S_new / S_old` and `y × S_old / S_new` |
| no `base_power` | the base is winding 1's `ratedS` (the percent convention of DSS and GLM) |

A winding's `baseS` is per phase, so the whole-unit power of a coil is winding 1's `ratedS` scaled by the two `baseS`.
The one unit that may leave the base unset is an ideal `AutoTransformer` (no mesh impedance, no `ratedS`): its
`base_power` is `None`.

```python
ten_mva = cim.ApparentPower(10, "MVA")
model = get_transformer_model(unit, "pu", base_power=ten_mva, voltage_unit="kV", power_unit="MVA")
print(model.base_power, model.windings[0].r, model.mesh[1, 2].x)
# 10.0 0.01 0.16
```

The ends' 0.5 % r and 8 % x are on 5 MVA, so on 10 MVA they are 1 % and 16 %, written as 0.01 and 0.16 pu.

### TransformerModel and its parts

`TransformerModel` fields:

| Field | Meaning |
|---|---|
| `form` | the `TransformerForm` that held the values |
| `windings` | a tuple of `Winding`, in winding order |
| `mesh` | `{(i, j): MeshImpedance}` with i < j winding numbers |
| `core` | the magnetizing branch, a `CoreAdmittance` |
| `base_power` | what every percent or pu is on, in `power_unit`; `None` on an unrated ideal `AutoTransformer` |

`Winding` fields. Windings are numbered from 1 in end-number order; a coil of a phase-ends or lugs form by its lowest
phase end `sequenceNumber`. Two windings in the same place raise.

| Field | Meaning | Unit |
|---|---|---|
| `number` | winding number | |
| `end` | the instance end it lands on: a `PowerTransformerEnd` or `AutoTransformerEnd` | |
| `phases` | a coil's two phase ends, else the end's terminal phases (`SinglePhaseKind`) | |
| `connection` | `WindingConnection`, or `None` | |
| `grounded` | `bool` or `None` | |
| `rground`, `xground` | grounding impedance, or `None` | ohm |
| `rated_u` | `ratedU`; an `AutoTransformerEnd` has none | `voltage_unit` |
| `rated_s` | `ratedS`, or `None` when unset. Winding 1's is required, except on an end form with a declared `base_power` and on an ideal `AutoTransformer` | `power_unit` |
| `base_u` | the coil voltage. A `PowerTransformerEnd` has no `baseU`, so for an end of two conductors it is derived from `ratedU`, the phase-to-phase nameplate: as is between two phases, over √3 from a phase to the neutral. `None` for an end of more conductors | `voltage_unit` |
| `base_s` | per-phase power; a `PowerTransformerEnd` has none | `power_unit` |
| `r` | the winding's resistance, on the model's base | percent or pu |
| `phase_shift` | the instance `PowerTransformerEnd`'s fixed `phaseShift` | deg |
| `r_dc` | a `TransformerWinding`'s `rDC` (a tank's or a template's winding), or `None`; an end has none | ohm |

`MeshImpedance(r, x)` is the impedance between two windings on the model's base; `x` is always set, `r` may be
`None`. `CoreAdmittance(g, b)` is the magnetizing branch on the model's base, `None` where unset.

### TransformerForm

`TransformerForm` is an `Enum`. The getter picks the form from what the unit holds and raises when the unit mixes
them.

| Form | The unit holds | Windings come from | Mesh | Core |
|---|---|---|---|---|
| `BY_ENDS` | a `PowerTransformer` without tanks | `PowerTransformerEnd` ratings and `r`. A single-phase coil takes its voltage from `ratedU` (see `base_u`) | `TransformerMeshImpedance` between ends, or each end's star `x` summed by pair (two windings: an unset end `x` counts as 0, CIM's two-winding rule; three or more: any unset end `x` raises); both together raise | `g` and `b` on the one end that holds them (zeros on several ends are one zero core; a non-zero core on several raises) |
| `AUTO` | an `AutoTransformer` | `AutoTransformerEnd` (`baseU`, `ratedS`) | a mesh between ends | none: `CoreAdmittance(None, None)` |
| `BY_PHASE_ENDS` | a `TransformerTank` with its own `TransformerWinding`s and no `TankConfiguration` | each winding is a coil between two `TransformerPhaseEnd`s, matched to the `PowerTransformerEnd` by `endNumber` | a mesh between windings | the tank's `noLoadLoss` and `percentMagnetizingCurrent` |
| `BY_TANK_ENDS` | a tank with a `TankConfiguration` whose windings start at a `TransformerTankEnd` | one winding per `TransformerTankEnd`; template end n is instance end n. Connection and grounding set on both must agree, up to the grounding (Y and Yn): the instance's wins. Phases are the instance end's `TransformerPhaseEnd`s in `sequenceNumber` order, else its terminal phases | the configuration's mesh | the tank's or configuration's `noLoadLoss` and `percentMagnetizingCurrent` |
| `BY_LUGS` | a tank with a `TankConfiguration` whose windings run lug to lug | a lug's `sequenceNumber` names the instance `TransformerPhaseEnd` it lands on (a centre tap). A bank of template tanks is always lugged, every can | the configuration's mesh | as `BY_TANK_ENDS` |
| `BY_TANK_IMPEDANCE` | two `PowerTransformerEnd`s and one tank with `percentImpedance` (and `loadLoss`), nothing else | the two ends; a centre-tap end becomes two halves | split from the nameplate (below) | `noLoadLoss` and `percentMagnetizingCurrent` |

Either template form (`BY_TANK_ENDS`, `BY_LUGS`) may hold its impedance as the configuration's `percentImpedance` and
`loadLoss` instead of a winding `r` and a mesh. It is read as the nameplate form below when no winding has an `r` or a
mesh. When one does, the `percentImpedance` beside it is the nameplate's figure and is not read.

#### Nameplate impedance (`BY_TANK_IMPEDANCE`)

The magnitude |z| is `percentImpedance` on the can's kVA: winding 1's `ratedS` for a single tank (its `baseS`, when set, must equal that `ratedS`), or the tank's own `baseS` for a can of a bank. Then:

```text
r = loadLoss / ratedS × 100        (0 when loadLoss is unset)
x = sqrt(z² - r²)                  (loadLoss above the impedance raises)
```

| Case | Winding r (share of r) | Mesh x (share of x) |
|---|---|---|
| two windings (`TWO_WINDING_SPLIT`) | 0.5, 0.5 | (1, 2): 1.0 |
| centre tap, three windings (`CENTER_TAP_SPLIT`) | 0.5, 1.0, 1.0 | (1, 2): 1.2, (1, 3): 1.2, (2, 3): 0.8 |

A centre tap is an end on `s1`, `s2` and `N` with `connectionKind` `I`: two halves, s1 to N and N to s2, each at half
the end's `ratedU` and `ratedS`. The split is Hopkinson's rule for an interlaced secondary. A bank of cans (one tank
per can, each with its own `baseS`) puts each can's primary on one phase of end 1, and its secondary on a wye end's
phase or across two phases of a delta end; the cans' `baseS` must add up to end 1's `ratedS`. A tank whose end
already holds `r`, `x`, `g`, `b` or a mesh raises: one value would have two homes.

#### Examples by form

```python
unit = get_transformer_units(by_mrid(by_phase_ends, cim.PowerTransformer, "xf_t3"))[0]
summarize(get_transformer_model(unit, voltage_unit="V", power_unit="VA"))
# BY_PHASE_ENDS base_power 5000.0
#   1 AB 4160.0 5000.0 4160.0 0.6
#   2 s1N 240.0 2500.0 120.0 1.2
#   3 Ns2 240.0 2500.0 120.0 1.2
#   mesh {(1, 2): (None, 2.04), (1, 3): (None, 2.04), (2, 3): (None, 1.36)}
#   core CoreAdmittance(g=0.2, b=0.5)
```

A template form:

```python
unit = get_transformer_units(by_mrid(by_template, cim.PowerTransformer, "xf_t1"))[0]
model = get_transformer_model(unit, voltage_unit="V", power_unit="VA")
print(model.form.name, model.mesh[1, 2], [round(w.base_u) for w in model.windings])
# BY_TANK_ENDS MeshImpedance(r=1.1, x=2.0) [2400, 277]

unit = get_transformer_units(by_mrid(by_template, cim.PowerTransformer, "xf_t2"))[0]
print(get_transformer_model(unit).form.name)
# BY_LUGS
```

A nameplate form with a centre tap:

```python
unit = get_transformer_units(by_mrid(by_tank_impedance, cim.PowerTransformer, "xf_t6"))[0]
model = get_transformer_model(unit, voltage_unit="V", power_unit="VA")
print(model.form.name, [(w.number, "".join(p.value for p in w.phases), w.r) for w in model.windings])
print({pair: round(z.x, 3) for pair, z in model.mesh.items()})
# BY_TANK_IMPEDANCE [(1, 'BN', 0.248), (2, 's1N', 0.496), (3, 'Ns2', 0.496)]
# {(1, 2): 2.695, (1, 3): 2.695, (2, 3): 1.797}
```

The `get_transformer_model` raises that you will meet most often:

| Message starts | Cause |
|---|---|
| `PowerTransformer '...': has tanks; read each unit get_transformer_units gives` | a transformer with tanks was passed whole |
| `TransformerTank '...': has its own TransformerWindings and a TankConfiguration` | two homes for the windings |
| `... a bank mixes tanks by percentImpedance with ...` | tanks of one transformer use different forms |
| `... two windings have the same place` | duplicate end numbers or phase-end sequence numbers |
| `... both a star impedance (PowerTransformerEnd.x) and a mesh impedance` | two homes for the impedance |
| `... ratedS is unset` | winding 1 has no rating and the base is not `base_power` on an end form |
| `... the star x of winding(s) [...] is unset` | three or more windings, and an end has no `x` |
| `... more than one end holds the core admittance` | a non-zero `g` or `b` on two ends |

## Tap changers

Module `cimhub_core.getters.tap_changer`. `TapChanger.step` is a tap **position**, never a turns ratio, and so are
`normalStep`, `lowStep`, `highStep` and `neutralStep`. The ratio at a position is

```text
ratio   = 1 + (position - neutralStep) × stepVoltageIncrement / 100
voltage = neutralU + (position - neutralStep) × stepVoltageIncrement / 100 × ratedU
```

where `ratedU` is the tap's `TransformerEnd` and `stepVoltageIncrement` is a percent of it. There is no default
increment: an unset one raises, except on a fixed tap (`lowStep` = `highStep`), which has no step to increment. A fixed
tap's increment is `None`, its ratio is 1 and its voltage is its `neutralU`.

### get_tap_steps, get_phase_tap_steps

```python
get_tap_steps(tap, voltage_unit="V") -> TapSteps
get_phase_tap_steps(tap, angle_unit="deg") -> PhaseTapSteps
```

`TapSteps` fields:

| Field | Meaning | Unit |
|---|---|---|
| `low`, `high`, `neutral` | `lowStep`, `highStep`, `neutralStep`; required | position |
| `normal` | `normalStep`, or `None` | position |
| `step` | the actual position, or `None` | position |
| `increment` | `stepVoltageIncrement`; required unless the tap is fixed, then `None` | percent per step |
| `neutral_u` | `neutralU`, or `None` | `voltage_unit` |

`PhaseTapSteps` (for a `PhaseTapChangerLinear`) has `low`, `high`, `neutral`, `normal`, `step` as above and a required
`increment`, the `stepPhaseShiftIncrement` per step in `angle_unit`, in CIM's sign (from the terminal into the
transformer).

```python
from cimhub_core.getters.tap_changer import get_phase_tap_steps, get_tap_ratio, get_tap_steps, get_tap_voltage

tap = by_mrid(regulator, cim.RatioTapChanger, "xf_reg1_tap")
print(get_tap_steps(tap))
# TapSteps(low=-16, high=16, neutral=0, normal=0, step=10.0, increment=0.625, neutral_u=2400.0)

phase_tap = cim.PhaseTapChangerLinear(mRID="pt", lowStep=1, highStep=33, neutralStep=17, step=20.0,
                                      stepPhaseShiftIncrement=cim.AngleDegrees(-1.875))
print(get_phase_tap_steps(phase_tap))
# PhaseTapSteps(low=1, high=33, neutral=17, normal=None, step=20.0, increment=-1.875)
```

`get_tap_steps` is called by all four spokes; `get_phase_tap_steps` by `cimhub_raw`.

### get_tap_ratio, get_tap_voltage

```python
get_tap_ratio(tap, *, which) -> float
get_tap_voltage(tap, *, which, voltage_unit="V") -> float
```

`which` is `'actual'` (`step`), `'normal'`, `'low'` or `'high'`, and has no default, because the actual and normal
positions differ in any model that is not as built. Anything else raises `ValueError: which must be one of
['actual', 'high', 'low', 'normal'], not ...`. An unset position raises. `get_tap_voltage` also requires `neutralU`,
and on a tap that moves requires the tap's `TransformerEnd` and its `ratedU`.

```python
for which in ("actual", "normal", "low", "high"):
    print(which, get_tap_ratio(tap, which=which), get_tap_voltage(tap, which=which))
# actual 1.0625 2550.0
# normal 1.0 2400.0
# low 0.9 2160.0
# high 1.1 2640.0
```

`get_tap_ratio` is called by `cimhub_gdm`, `cimhub_gridlabd` and `cimhub_opendss`; `get_tap_voltage` by `cimhub_raw`.

## Controls

Module `cimhub_core.getters.control`. A `RegulatingControl`'s target is a plain float in the primary units of its mode
(V, A, W, VAr), times `targetValueUnitMultiplier` when set.

| Mode | Quantity | SI unit |
|---|---|---|
| `voltage` | `Voltage` | `V` |
| `currentFlow` | `CurrentFlow` | `A` |
| `activePower` | `ActivePower` | `W` |
| `reactivePower` | `ReactivePower` | `VAr` |

A mode with no quantity here (`powerFactor`, `timeScheduled`, `admittance`, `temperature`) is returned as stored, and
naming a unit or a multiplier for it raises.

### get_regulating_control

```python
get_regulating_control(control, unit=None) -> RegulatingSettings
```

The control's mode, targets in `unit` (default: its mode's SI unit), monitored terminal and phases. It raises when the
mode is unset, when the control monitors no `Terminal`, or when `targetValue` is unset on a control that is not
disabled. A disabled control (`enabled` false, such as a manual regulator) may leave `targetValue` unset; its target is
then `None`.

`RegulatingSettings` fields:

| Field | Meaning | Unit |
|---|---|---|
| `mode` | `RegulatingControlModeKind` | |
| `unit` | what the targets are in; `None` for a mode returned as stored | |
| `target` | `targetValue`; `None` only on a disabled control | `unit` |
| `deadband` | `targetDeadband` (the full band width) | `unit` |
| `min_allowed`, `max_allowed` | `minAllowedTargetValue`, `maxAllowedTargetValue` | `unit` |
| `reverse_target`, `reverse_deadband` | the reverse-flow target and band | `unit` |
| `terminal` | the monitored `Terminal` | |
| `monitored_phases` | `SinglePhaseKind` tokens, or `None` when `monitoredPhase` is unset | |
| `enabled`, `discrete` | as stored, or `None` | |
| `pt_ratio`, `ct_ratio` | as stored on the control, or `None` | |

Called by `cimhub_raw`.

### get_tap_changer_control

```python
get_tap_changer_control(tap, *, unit=None, time_unit="s", voltage_unit="V", power_unit="W") -> TapChangerSettings
```

The tap changer's control settings. `unit` is the targets' unit as in `get_regulating_control`. `ptRatio` and
`ctRatio` may sit on the `TapChanger`, its `TapChangerControl`, or both; both set must agree, or it raises.

`TapChangerSettings` fields:

| Field | Meaning | Unit |
|---|---|---|
| `control` | the `TapChangerControl`'s `RegulatingSettings` with `pt_ratio` and `ct_ratio` agreed; `None` when the tap has no control | |
| `control_enabled`, `ltc` | `controlEnabled`, `ltcFlag` | |
| `ct_rating` | the tap's `ctRating` | A |
| `initial_delay`, `subsequent_delay` | the tap's delays | `time_unit` |
| `line_drop_compensation` | `lineDropCompensation` of the control | |
| `line_drop`, `reverse_line_drop` | `LineDrop(r, x)`: `lineDropR/X` and `reverseLineDropR/X`, in primary ohms | ohm |
| `reversible`, `reverse_to_neutral` | the control's flags | |
| `reversing_delay` | `reversingDelay` | `time_unit` |
| `reversing_power_threshold` | `reversingPowerThreshold` | `power_unit` |
| `min_limit_u`, `max_limit_u` | `minLimitVoltage`, `maxLimitVoltage` | `voltage_unit` |

```python
from cimhub_core.getters.control import get_tap_changer_control

settings = get_tap_changer_control(tap, unit="kV")
print(settings.control.target, settings.control.deadband, settings.control.unit)
print(settings.line_drop, settings.initial_delay, settings.ct_rating)
# 2.44 0.04 kV
# LineDrop(r=0.085714, x=0.257143) 15.0 700.0
```

Called by all four spokes.

### get_equipment_control

```python
get_equipment_control(equipment, *, unit=None, time_unit="s") -> EquipmentControl | None
```

The control of a regulated device (a shunt, a machine, an inverter), or `None` when it has none. `EquipmentControl`
fields: `control` (a `RegulatingSettings`), `control_enabled` (`RegulatingCondEq.controlEnabled`) and `delay`
(`ShuntCompensator.aVRDelay` in `time_unit`; `None` on other equipment). Called by `cimhub_gdm`, `cimhub_gridlabd` and
`cimhub_opendss`.
