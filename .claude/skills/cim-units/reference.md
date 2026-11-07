# CIM units: reference

Companion to [SKILL.md](SKILL.md). Profile is cim18v17.

## CIMUnit classes

cim18v17 has 37 `CIMUnit` subclasses. Enumerate them with
`issubclass(getattr(cim, name), cimprofiles.units.units.CIMUnit)`. The common ones:

| CIMUnit | SI base | Typical header units |
|---|---|---|
| `ActivePower` | W | `W`, `kW`, `MW` |
| `ReactivePower` | VAr | `VAr`, `kVAr`, `MVAr` |
| `ApparentPower` | VA | `VA`, `kVA`, `MVA` |
| `Voltage` | V | `V`, `kV` |
| `CurrentFlow` | A | `A`, `kA` |
| `Resistance`, `Reactance`, `Impedance` | ohm | `ohm`, `pu`, `percent` |
| `Conductance`, `Susceptance` | S | `S`, `uS`, `pu`, `percent` |
| `ResistancePerLength`, `ReactancePerLength` | ohm/m | `ohm/mi`, `ohm/km`, `ohm/kft` |
| `ConductancePerLength`, `SusceptancePerLength` | S/m | `nS/mi`, `uS/km` |
| `CapacitancePerLength`, `InductancePerLength` | F/m, H/m | `nF/mi`, `mH/km` |
| `Length`, `Displacement` | m | `m`, `km`, `ft`, `mi`, `kft` |
| `AngleDegrees` / `AngleRadians` | deg / rad | `deg`, `rad` |
| `Frequency` | Hz | `Hz` |
| `Seconds` | s | `s` |
| `PerCent` | none | unitless or `percent` (stores the percent number) |

Header units are pint strings. Unit prefixes (`k`, `M`, `u`, `n`) are handled by pint.

## Attribute → header examples (cim18v17)

| Class.attribute | CIMUnit | Example header |
|---|---|---|
| `BaseVoltage.nominalVoltage` | Voltage | `nominalVoltage (kV)` |
| `EnergyConsumer.p` / `.q` | ActivePower / ReactivePower | `p (kW)`, `q (kVAr)` |
| `SynchronousMachine.p`, `.ratedS` | ActivePower, ApparentPower | `p (MW)`, `ratedS (MVA)` |
| `ACLineSegment.length` | Length | `length (ft)` |
| `ACLineSegment.r` / `.x` / `.bch` | Resistance / Reactance / Susceptance | `r (pu system)`, `bch (pu system)` |
| `PerLengthSequenceImpedance.r`, `.bch` | ResistancePerLength, SusceptancePerLength | `r (ohm/km)`, `bch (nS/km)` |
| `PhaseImpedanceData.r`, `.b` | ResistancePerLength, SusceptancePerLength | `r (ohm/mi)`, `b (nS/mi)` |
| `PowerTransformerEnd.ratedU`, `.ratedS` | Voltage, ApparentPower | `ratedU (kV)`, `ratedS (MVA)` |
| `TransformerWinding.baseU`, `.baseS` | Voltage, ApparentPower | `baseU (kV)`, `baseS (kVA)` |
| `TransformerMeshImpedance.r`, `.x` | Resistance, Reactance | `r (percent)`, `x (percent)` |
| `TransformerTankConfiguration.percentImpedance` | PerCent | unitless |
| `TransformerTankConfiguration.noLoadLoss` | ActivePower | `noLoadLoss (kW)` |
| `RatioTapChanger.stepVoltageIncrement` | PerCent | unitless |
| `LinearShuntCompensator.nomQ`, `.nomU`, `.bPerSection` | ReactivePower, Voltage, Susceptance | `nomQ (kVAr)`, `nomU (kV)`, `bPerSection (S)` |
| `XYConductorPosition.xCoord` / `.yCoord` | Displacement | `xCoord (ft)` |
| `WireInfo.rAC25`, `.gmr`, `.radius`, `.ratedCurrent` | ResistancePerLength, Length, Length, CurrentFlow | `rAC25 (ohm/mi)`, `gmr (ft)`, `radius (in)`, `ratedCurrent (A)` |
| `CurrentLimit.normalValue` | CurrentFlow | `normalValue (A)` |

`TapChanger.step` is a plain float: a tap position, never a turns ratio.

## Transformer bases

`ratedU`/`ratedS` are the nameplate (phase-to-phase kV, total kVA). `TransformerWinding.baseU` is the coil voltage
(phase-to-neutral for wye, phase-to-phase for delta) and `baseS` the per-coil kVA: `ratedS` for a 1-phase primary,
`2 * ratedS` for a center-tap half, `ratedS / 3` for a 3-phase coil. A `(percent)` or `(pu)` winding or mesh column
is on those bases, so `z_base` needs no phase count. Percent impedances go on the winding base: `r (percent)` on
the end's own base, mesh `x (percent)` on the From winding.

## Per-unit, bus-branch formats (MATPOWER, RAW)

Import: write the per-unit values with `(pu system)`, and bind the case's `BasePower` first.

```
Object BasePower: mRID=sbase, basePower (MVA)=100
Table ACLineSegment: mRID, name, bus1, bus2, phases, r (pu system), x (pu system), bch (pu system), BaseVoltage
    ln_1_2_1, 1-2 ckt 1, bus_1, bus_2, ABC, 0.0194, 0.0592, 0.0528, bv_115kv
```

`bus1`/`bus2` are TopologicalNodes; the full shape is `cimhub_core/src/cimhub_core/shapes/line_bus_branch.cimtbl`.

Export: invert with `get_qty`.

```python
r_pu = get_qty(segment, 'r', 'pu', system_base=network.base_power)
b_pu = get_qty(segment, 'bch', 'pu', system_base=network.base_power)
x_pu = get_qty(end, 'x', 'pu', base='system', system_base=network.base_power)  # RAW CZ=1 transformer
```

MATPOWER `Gs`/`Bs` are MW and MVAr consumed at 1.0 pu voltage. They have no pint path to siemens, so on import
they are derived (`g = Gs / base_kv²` in S when Gs is in MW and base_kv in kV), computed by a named, tested
function and commented in the artifact. On export, do the inverse in a getter or a named function, not inline.

MATPOWER's off-nominal tap ratio lives in the transformer's ratedU relative to the bus BaseVoltage. Recover it by
reading both with `get_qty(..., 'kV')`, not by storing a ratio in `TapChanger.step`.

## Susceptance to capacitance (DSS `cmatrix`, `C1`)

`SusceptancePerLength` has no pint path to farads: `get_qty(data, 'b', 'nF/mi')` raises `DimensionalityError`.
Divide by `2 * pi * f` with pint quantities, inside a named getter or derived function:

```python
import math
from cimprofiles.units.units import ureg

b = ureg.Quantity(get_qty(data, 'b', 'S/mi'), 'S/mi')
c_nf_per_mi = (b / (2 * math.pi * ureg.Quantity(frequency_hz, 'Hz'))).to('nF/mi').magnitude
# 5e-6 S/mi at 60 Hz -> 13.2629 nF/mi
```

The import side is the DSS LineCode slice's `b_from_c` (derived, `b (nS/mi)` keeps the code's length unit).

## PerCent details

- Import: a unitless cell, a bare number or a `(percent)` column all store `PerCent(5.0)` for 5 %. `(pu)` raises.
- Export: `get_qty(obj, attr, 'percent')` (or `''`) returns the stored number; any other unit raises.
- Tests: check a PerCent attribute with `.value` (`assert config.percentImpedance.value == 5.0`).
- Never `.to('percent')` on a PerCent: pint scales the dimensionless 5.0 to 500.
- `(percent)` on an ohm- or siemens-typed attribute (winding `r`, mesh `x`) is a different thing: a relative
  impedance converted through `z_base`. That route is correct.

## Comparisons in tests

```python
assert get_qty(end, 'ratedU', 'kV') == pytest.approx(4.16)
assert float(end.ratedU) == pytest.approx(4160.0)  # float() is the SI magnitude
# end.ratedU == 4160 is silently False and end.ratedU - 4160 raises TypeError: compare floats
```
