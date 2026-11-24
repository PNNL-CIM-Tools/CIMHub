# Units, bases and signs

CIM stores every quantity in SI. The getters hand you the number in the unit you name. This page covers what a unit
string can be, how per-unit and percent get their base, and the sign of generation. The code runs against
[`feeder.cimtbl`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/docs/guide/feeder.cimtbl), loaded as in
[Using the getters](getters.md).

## CIM holds SI

A quantity attribute holds a cim-profiles unit object backed by pint, always in SI base units: W, VAr, VA, V, A, ohm,
S, m.

```python
load = find(cim.EnergyConsumer, 'ld_n1')
print(repr(load.p))         # 1155000.0 watt
print(float(load.p))        # 1155000.0
print(load.p.to('kW'))      # 1155.0
```

Compare a quantity only after `.to()` or `float()`. Arithmetic between a unit object and a bare number raises
`TypeError`.

## `get_qty` and the unit strings

Every getter reads through `cimtables.graph_write.get_qty(obj, attribute, unit)`, and you can call it yourself for an
attribute no getter covers.

```python
from cimtables.graph_write import get_qty

print(get_qty(load, 'p', 'MW'))                          # 1.155
print(get_qty(find(cim.ACLineSegment, 'ln_trunk'), 'length', 'ft'))   # 2000 (to rounding)
print(get_qty(find(cim.ACLineSegment, 'ln_trunk'), 'r', 'ohm'))       # None: unset
```

| Result | Meaning |
|---|---|
| a float | the value in the unit you named |
| `None` | the attribute is unset |
| `ValueError` | not a field of the class, an association, or not a quantity |
| `DimensionalityError` (pint) | the unit does not match the quantity, such as `'ft'` for a power |

Any pint unit of the right dimension works: `kW`, `MW`, `kV`, `ft`, `mi`, `ohm/km`, `uS/km`, `deg`, `rad`. Some
getters narrow this to a few words: a line's `unit` is `'ohm'` or `'pu'`, a transformer's `impedance_unit` is
`'percent'` or `'pu'`.

Active power (W) and reactive power (VAr) share a dimension in pint, so a power unit of the wrong kind is not caught:
`get_qty(load, 'p', 'VAr')` returns the active power's number.

## Per-unit and percent

`'pu'` and `'percent'` on an impedance or admittance divide by a base, `z_base = U² / S`. The base depends on the
class of the object, not on the values on it.

| Object | Base |
|---|---|
| A rated object, such as a `PowerTransformerEnd` | its own `ratedU` and `ratedS` |
| An object that points at a rated one, such as a `TransformerMeshImpedance` | the rating of its From end |
| Anything else, such as an `ACLineSegment` or an `EnergySource` | its `BaseVoltage` and the model's base power (a shunt compensator's `nomU` takes the place of the `BaseVoltage`) |

For the last row the getter needs the base power, which you pass as `network.base_power`. Without it the read
raises.

```python
from cimhub_core.getters.source import get_source

source = find(cim.EnergySource, 'src')
print(get_source(source, angle_unit='deg').impedance.r)                                          # 0.1 ohm
print(get_source(source, angle_unit='deg', impedance_unit='pu', base_power=network.base_power).impedance.r)
```

The feeder's base power is 10 MVA and the source is at 4.16 kV, so `z_base` is 4.16² / 10 = 1.7306 ohm, and 0.1 ohm is
0.0578 pu. Change the base power and the same ohms read as a different per-unit value. `network.base_power` is a
cim-profiles `ApparentPower`, so `.to('MVA')` reads it.

### A transformer's base

A transformer's percent is on a base the result names:

```python
from cimhub_core.getters.transformer import get_transformer_model, get_transformer_units

[tank] = get_transformer_units(find(cim.PowerTransformer, 'xf1'))
own = get_transformer_model(tank, 'percent')
system = get_transformer_model(tank, 'pu', base_power=network.base_power)
print(own.base_power, own.mesh[(1, 2)].x)        # 500000.0 (VA), 2.0 percent
print(system.base_power, system.mesh[(1, 2)].x)  # 10000000.0 (VA), 0.4 pu
```

With no `base_power`, every percent is on winding 1's `ratedS`. With one, the values move to that base by the power
alone: 2 percent on 500 kVA is 0.4 pu on 10 MVA. The result's `base_power` is in `power_unit`, `'VA'` by default.

### Percent attributes

An attribute typed `PerCent` in CIM, such as `TransformerTankConfiguration.percentImpedance`, holds the percent
number. Read it as `'percent'`; any other unit raises.

```python
tank_config = find(cim.TransformerTankConfiguration, 'xc_xfm1')
print(get_qty(tank_config, 'percentImpedance', 'percent'))    # 2.2825
```

### Base voltage

`get_base_voltage` reads the voltage a per-unit value is on, in the form you ask for: `'LL'` as stored, or `'LN'`, the
line-to-neutral value LL / √3.

```python
from cimhub_core.getters.base_voltage import get_base_voltage

print(get_base_voltage(find(cim.ACLineSegment, 'ln_trunk'), 'kV', form='LN'))   # 2.4017771...
```

An `'LN'` read on equipment or a transformer end on a split-phase secondary (s1, s2) raises, because the 120 V leg is
not LL / √3.

## Sign

CIM's sign is the load's: `p` and `q` are positive into the equipment. A generator, a PV array or a discharging battery
has a negative `p`. Native formats usually write generation as positive, so the DER getters make you choose with
`sign=`.

```python
from cimhub_core.getters.der import get_der_output

inverter = find(cim.PowerElectronicsConnection, 'pv_p1')
print(get_der_output(inverter, 'kW', 'kVAr', sign='load').total)         # PhasePower(p=-240.0, q=0.0)
print(get_der_output(inverter, 'kW', 'kVAr', sign='generation').total)   # PhasePower(p=240.0, q=0.0)
```

| `sign=` | Result |
|---|---|
| `'load'` | as CIM stores it: generation is negative |
| `'generation'` | negated: generation is positive |

Nameplate limits are the other way round: a unit's `maxP` is written in the generation sign (its output), and a battery's
`minP` is its charging, negative. Every limit pair comes back as `(min, max)` in the sign you asked for. A minimum above
its maximum raises, which is how a producer that wrote the load sign shows up. The exception is `get_unit_limits`
(a unit's active power limits), which returns the pair as stored, because a source can hold a minimum above a maximum
on a unit that is out of service.

`BatteryUnit.idlingP` is a loss and comes back as stored in either sign.

Loads have no `sign=`. `get_phase_loads` returns the load as CIM stores it, positive into the load.

## Where the conversion happens

The developer view of the same rules, including how importers write a source unit in a `.cimtbl` column header, is
[Units](../developer/units.md).
