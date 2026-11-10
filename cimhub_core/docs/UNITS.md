# Units in CIMHub

CIMHub works with cim18v17 only. This page explains how physical quantities move through the code in both
directions. The rule set for Claude sessions, with the full unit tables, is the
[`cim-units` skill](../../.claude/skills/cim-units/SKILL.md); this page is the shorter human version.

## How a CIM quantity is stored

A CIM quantity attribute (`EnergyConsumer.p`, `BaseVoltage.nominalVoltage`, `ACLineSegment.length`) holds a
`CIMUnit` object from `cimprofiles`. It is backed by pint and always stores the value in SI base units: W, VAr,
VA, V, A, ohm, S, m.

```python
>>> load.p
1155000.0 watt
>>> type(load.p).__name__
'ActivePower'
>>> float(load.p)          # the SI magnitude
1155000.0
>>> load.p.to("kW")        # any compatible unit
1155.0
```

CIMHub code never converts units by hand. No `* 1e3`, no `/ 1000`, no `* 1.609344`. Conversion happens in one
place in each direction:

| Direction | Who converts | How you ask for the unit |
|---|---|---|
| Import (native to CIM) | `cimtables`, when it binds the `.cimtbl` text | the unit in the column header |
| Export (CIM to native) | `cimtables.graph_write.get_qty` | the unit argument |

## Import: source value, source unit in the header

An importer writes the native number exactly as the source holds it and names the source unit in the column
header. `cimhub_core.cimtbl.cell()` writes the value as text and never converts or rounds. When `cimtables`
builds the CIM it reads the header, converts to SI, and stores the result. See
[ARCHITECTURE.md](ARCHITECTURE.md) for the whole import path.

Real headers from the shapes in `cimhub_core/src/cimhub_core/shapes/`:

```
Table EnergyConsumer: mRID, name, node, phases, phaseConnection, grounded, p (kW), q (kVAr), ...
Table SynchronousMachine: mRID, name, node, phases, ratedS (kVA), ratedU (kV), p (kW), q (kVAr), ...
Object BaseVoltage: mRID=bv_115kv, nominalVoltage (kV)=115
Object TransformerCore ... TransformerMeshImpedance: ..., r (percent)=1.1, x (percent)=2.0
```

And from a DSS atom (`cimhub_opendss/tests/atoms/linecode/seq_3_1_0c.cimtbl`), where the line code is in
ohm/km and the capacitance has been turned into a susceptance:

```
Table PerLengthSequenceImpedance: mRID, name, r (ohm/km), x (ohm/km), r0 (ohm/km), x0 (ohm/km), calculatedFrequency (Hz), bch (nS/km), b0ch (nS/km)
    lc_3-1/0c_2/0cn_t, 3-1/0C_2/0CN_T, 0.3489, 0.426198, 0.588811, 1.29612, 60, 3932.350000000008, 1690.8100000000002
```

The rules an importer follows (invariants I2 and I5 in the root `CLAUDE.md`):

1. Copy the value verbatim and put the source unit in the header.
2. Spoke code never constructs a CIM object or a unit object: no `cim.X(...)`, no `CIMUnit`, no `z_base`.
3. A unit that depends on the record (the length unit of a line code) is a template, filled once per table.
   The `cimtbl-import-contract` skill has the details.
4. A value with no unit path to the CIM attribute is *derived*: a named, tested pure function computes it and
   the artifact carries a comment. Examples are DSS `C1` in nF to `bch` in nS (`b_from_c`), and the sign flip below.

```python
# Wrong: unit math in a mapper
row = [cell(code.r1 * 1.609344), cell(load.kw * 1000)]
# Right: the number as the source holds it; the header names the unit
row = [cell(code.r1), cell(load.kw)]      # headers: r (ohm/mi), p (kW)
```

## Per-unit and percent on import

Relative values use relative headers. `cimtables` multiplies by the base impedance `z_base = U^2 / S` (it
divides for siemens) and stores ohms. The spoke never computes the base.

| Header unit | Base used |
|---|---|
| `(pu)` or `(percent)` | the row's own rating (`ratedU`/`ratedS` on a `PowerTransformerEnd`, `baseU`/`baseS` on a `TransformerWinding`), else the `From*` target's rating (`TransformerMeshImpedance.FromWinding`), else the system base |
| `(pu system)` or `(percent system)` | the system base: the row's `BaseVoltage` and the case's `BasePower` |

The artifact must hold what the base needs: the ratings, the `BaseVoltage` and `From*` references, and for a
system-base row a `BasePower` bound before it. A bus-branch shape (`line_bus_branch.cimtbl`) does this:

```
Object BasePower: mRID=sbase, basePower (MVA)=100
Object BaseVoltage: mRID=bv_115kv, nominalVoltage (kV)=115
Object ACLineSegment: mRID=ln_1_2_1, ..., r (pu system)=0.0194, x (pu system)=0.0592, bch (pu system)=0.0528, BaseVoltage=bv_115kv
```

A RAW case writes its own `SBASE` into `BasePower` and its impedances as `(pu system)`. Where the source gives
an admittance as MW at 1 pu voltage (RAW `GL`, `BL`), the mapper divides by `SBASE` in a named function
(`per_unit_from_mva` in `cimhub_raw/src/cimhub_raw/importer/cimtbl/derived.py`) and writes
`gPerSection (pu system)`. That is a derived field, not unit math inside the mapper body.

## PerCent attributes

Some CIM attributes are of type `PerCent`: `percentImpedance`, `percentMagnetizingCurrent`,
`stepVoltageIncrement`, efficiencies. They hold the percent number. A unitless cell or a `(percent)` column both
store 5 % as 5.0, never 0.05. A `(pu)` column on a PerCent attribute raises.

```
Object TransformerTankConfiguration: mRID=xc_xfm1, name=XFM1, percentImpedance=2.2825, percentMagnetizingCurrent=0, noLoadLoss (kW)=0
```

`(percent)` on an ohm- or siemens-typed attribute is a different thing: a relative impedance that goes through
`z_base`, as in the winding and mesh `r (percent)`, `x (percent)` above. That route is correct.

## Export: `get_qty`, not hand conversion

An exporter asks for each value in the unit the native format wants. The reads live in the getters under
`cimhub_core/src/cimhub_core/getters/`; the exporter formats what the getters return (see
[CONVERTER_API.md](CONVERTER_API.md) and the `export-getters` skill).

```python
from cimtables.graph_write import get_qty

get_qty(source_object, attribute_name, unit, *, base=None, system_base=None, power_base=None) -> float | None
```

It returns `None` when the attribute is unset, so a getter can pass an unset value through. It raises
`ValueError` for a name that is not a field, an association, or a non-quantity attribute, and pint raises on a
dimension mismatch.

Real calls from the repo:

```python
get_qty(wire, "gmr", length_unit)                                   # getters/wire.py
get_qty(base, "nominalVoltage", "kV")                               # opendss exporter/options.py
get_qty(line, "length", LUMPED_UNIT)                                # opendss exporter/line.py
get_qty(cable, "tapeLap", "percent")                                # getters/wire.py, a PerCent
get_qty(connection, "maxIFault", "pu")                              # getters/der.py
network.base_frequency.to("Hz")                                     # a value already in hand
```

`.to(unit)` is for an absolute quantity you already hold, such as `network.base_frequency`. Prefer `get_qty`:
it also handles `None`, per-unit and percent.

A runnable check against an in-repo shape, run from the repo root:

```python
from pathlib import Path
import cimprofiles.cim18.cim18v17 as cim
from cimtables import load_model
from cimtables.graph_write import get_qty
from cimhub_core.cimtbl_testing import cim_scope

shapes = Path("cimhub_core/src/cimhub_core/shapes")
with cim_scope():
    network = load_model(shapes / "load.cimtbl")
    load = next(iter(network.graph[cim.EnergyConsumer].values()))
    print(get_qty(load, "p", "kW"))      # 1155.0
```

## Per-unit on export

`get_qty` with `'pu'` or `'percent'` on an ohm or siemens attribute inverts the import rule through the same
`z_base`, so one rule picks the base in both directions.

- The object's own rating or its `From*` target's rating is used by default.
- An unrated class such as `ACLineSegment` uses its `BaseVoltage` and the system base. Pass
  `system_base=network.base_power`.
- `base='system'` forces the system base, mirroring `(pu system)`.
- `power_base` reads a mesh impedance on another power at the same voltage.

```python
with cim_scope():
    network = load_model(shapes / "line_bus_branch.cimtbl")
    line = next(iter(network.graph[cim.ACLineSegment].values()))
    print(get_qty(line, "r", "ohm"))                                   # 2.56565
    print(get_qty(line, "r", "pu", system_base=network.base_power))    # 0.0194, the value the file holds
```

## PerCent on export

`get_qty(obj, attr, "percent")` returns the stored number. Never call `.to("percent")` on a `PerCent`: pint
treats it as a dimensionless fraction and returns 100 times the stored value.

```python
with cim_scope():
    network = load_model(shapes / "transformer_template.cimtbl")
    config = next(iter(network.graph[cim.TransformerTankConfiguration].values()))
    get_qty(config, "percentImpedance", "percent")   # 2.2825
    config.percentImpedance.value                    # 2.2825
    config.percentImpedance.to("percent")            # 228.25  (wrong)
```

## Comparisons

A `CIMUnit` is not a float. Arithmetic with a bare number raises `TypeError`, and `==` against a number is
silently `False`. Compare the floats that `get_qty` returns, or `float(x)` for the SI magnitude.

```python
load.p - 1000          # TypeError: unsupported operand type(s) for -: 'ActivePower' and 'int'
load.p == 1155000      # False, no error
get_qty(load, "p", "kW") == pytest.approx(1155.0)   # right
float(load.p) == pytest.approx(1155000.0)           # right, SI magnitude
```

For a `PerCent`, test the stored number with `.value`.

## Generator sign convention

CIM uses the load sign: positive `p` is power flowing into the equipment. A generator or a battery
discharging has negative `p` and `q`.

- **Import:** a source that reports generation as positive (RAW `PG`, MATPOWER `Pg`, DSS `kW` on a generator)
  is negated. The negation is a derived field, written by a named function (`generation_p_q` in
  `cimhub_raw/src/cimhub_raw/importer/cimtbl/derived.py`) and noted in the artifact. The DSS generator atom
  shows the result: `# p = -kW, q = -kvar (the load sign)`, then `p (kW)` of `-50.0` for a 50 kW machine.
- **Export:** do not negate in the exporter. `get_der_output(equipment, active_unit, reactive_unit, sign=...)`
  in `cimhub_core/getters/der.py` takes `sign="generation"` (negated, positive output) or `sign="load"` (as
  stored). A zero is kept as zero.

```python
from cimhub_core.getters.der import get_der_output

with cim_scope():
    network = load_model(shapes / "synchronous_machine.cimtbl")
    machine = next(iter(network.graph[cim.SynchronousMachine].values()))
    print(get_qty(machine, "p", "MW"))                                       # -0.1
    print(get_der_output(machine, "MW", "MVAr", sign="generation").total)    # PhasePower(p=0.1, q=0.0203)
```

## Susceptance and capacitance

`SusceptancePerLength` has no pint path to farads, so `get_qty(data, "b", "nF/mi")` raises. DSS stores line
capacitance (`C1`, `cmatrix`) and CIM stores susceptance. The conversion uses `2 * pi * f` and lives in two named
functions in `cimhub_core/src/cimhub_core/derived/capacitance.py`: `b_from_c` on import and `c_from_b` on export.
Both take a frequency, and the OpenDSS exporter reads the base frequency with `network.base_frequency.to("Hz")`.
When an exporter needs a CIM value in another absolute unit, it goes through the CIMUnit class and not a
factor, as the DSS line exporter does before calling `c_from_b`:

```python
cim.Susceptance(value, "S").to("nS")      # cimhub_opendss/exporter/line.py
```

## Common mistakes

| Mistake | Fix |
|---|---|
| `cell(kv * 1000)` under a `(V)` header | `cell(kv)` under a `(kV)` header |
| `r_ohm = r_pu * base_kv**2 / base_mva` in a mapper | write `r (pu)` or `r (pu system)` and let `cimtables` convert |
| `percentImpedance (pu)`, or the fraction 0.05 | unitless or `(percent)`, value 5.0 |
| `end.ratedU.to("kV")` scattered through an exporter | one getter that calls `get_qty(end, "ratedU", "kV")` |
| a hard-coded 100 MVA base | the case's own `BasePower` on import, `network.base_power` on export |
| `bv.nominalVoltage - 4160` or `== 4160` | compare `get_qty(bv, "nominalVoltage", "V")` to the number |
| negating generator `p` inside an exporter | `get_der_output(..., sign="generation")` |
| storing a turns ratio in `TapChanger.step` | `step` is a tap position; the ratio comes from `stepVoltageIncrement` |
| `.to("percent")` on a `PerCent` | `get_qty(obj, attr, "percent")` |

The full unit tables and per-attribute header examples are in the skill's
[reference.md](../../.claude/skills/cim-units/reference.md).
