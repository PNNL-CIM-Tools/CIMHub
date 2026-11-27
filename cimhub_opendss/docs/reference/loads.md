# Loads, capacitors and shapes

This page is the conversion reference for the OpenDSS classes that draw power or switch a shunt: `Load`,
`Capacitor`, `CapControl` and `LoadShape`. For each one it says what the importer writes, what the exporter reads
back and what raises. The field classes (copied, mapped, structural, derived, untranscribed) and the conventions
every section follows are on the [reference index](index.md). The getters the exporter reads through are on the
core site's [loads, shunts and compensators](https://pnnl-cim-tools.github.io/CIMHub/core/reference/loads/) page.

| DSS class | CIM classes | `.cimtbl` artifact and shape | Importer | Exporter |
|---|---|---|---|---|
| [`Load`](#load) | `EnergyConsumer`, or `ConformLoad` with a `yearly` shape; `LoadResponseCharacteristic` | `load.cimtbl`, shape `load` | `importer/cimtbl/load.py` | `exporter/load.py` |
| [`Capacitor`](#capacitor) | `LinearShuntCompensator` | `capacitor.cimtbl`, shape `shunt` | `importer/cimtbl/capacitor.py` | `exporter/capacitor.py` |
| [`CapControl`](#capcontrol) | `RegulatingControl`, and an update of its `LinearShuntCompensator` | `capcontrol.cimtbl`, shape `shunt` | `importer/cimtbl/capcontrol.py` | `exporter/capcontrol.py` |
| [`LoadShape`](#loadshape) | `ConformLoadGroup`, `ConformLoadSchedule`, and `RegularTimePoint` rows in a Parquet sidecar | `loadshape.cimtbl`, shape `load_schedule` | `importer/cimtbl/loadshape.py` | `exporter/loadshape.py` |

The table shapes are on the core site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/).
The master imports `loadshape.cimtbl` before `load.cimtbl`, and `capcontrol.cimtbl` after `capacitor.cimtbl`, so
each reference resolves. Source paths are under
[`cimhub_opendss/src/cimhub_opendss/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_opendss/src/cimhub_opendss).

Load, capacitor, PV, battery and generator share one terminal rule, in `importer/cimtbl/injection.py`
(`device_terminal`, `rated_phase_kv`, `line_kv`) and, inverted, in `exporter/injection.py` (`device_connection`,
`device_kv`, `rated_kv`). `CapControl` and `RegControl` share `exporter/controls.py` (`pt_phase`, `control_enabled`).

The examples run from the repository root with `uv run python`. They convert the public test atoms in
[`cimhub_opendss/tests/atoms`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_opendss/tests/atoms) to CIM and
back. This helper is shared by all of them:

```python
from pathlib import Path

from cimhub_opendss import DssExporter, DssImporter, DssReader, DssWriter
from cimhub_opendss.schema import opendss_schema as schema

ATOMS = Path("cimhub_opendss/tests/atoms")


def round_trip(atom: str, *classes):
    """Import an atom deck to CIM, export it, and return the DSS lines of `classes`."""
    path = ATOMS / atom
    time_points = {}
    network = DssImporter(path.stem, time_points=time_points).to_cim(DssReader(path).read_all())
    model = DssExporter(time_points).to_model(network, name_source="name")
    writer = DssWriter()
    return [writer.serialize(record) for cls in classes for record in model.list_by_class(cls)]
```

`name_source="name"` writes each object under its CIM `name`, which the importer set to the deck's name. The default
is the mRID (`ld_cvr1`, `cap_c1`).

## Load

One `EnergyConsumer` per `Load`, mRID `ld_` + the name, lowercased. A load that names a `yearly` shape is a
`ConformLoad` of that shape's group (see [LoadShape](#loadshape)). On export an `EnergyConsumer`, `ConformLoad`,
`NonConformLoad` or `StationSupply` each becomes a `Load`. CIM gives a load no rated voltage: `p` and `q` are
at the `BaseVoltage` of the bus.

**Power.** `p` is `kW`. `q` is `kvar`; with `kvar` unset it is `kW` x tan(acos abs(`pf`)) with the sign of `pf`
(default 0.88), and `kvar` wins over `pf` in either order. With `kW` unset, `kVA` gives `p` = `kVA` x abs(`pf`) and
`q` = `kVA` x sin(acos abs(`pf`)), signed by `pf`. The values are in kW and kVAr, as the column headers say.

**Phases and connection.** The bus's node numbers give the phases: 1, 2, 3 are A, B, C, and on a split-phase
island 1 and 2 are `s1` and `s2`. A node list left out is the DSS default (conductor k on node k). `conn=wye` is
`phaseConnection` Y and `grounded` true; `conn=delta` is D and not grounded. A 2-phase delta load raises. On
export, a wye load needs `grounded` true (DSS puts its neutral on node 0), and a delta load across two phases is
written as `phases=1` in branch order (`.1.2`, `.2.3`, `.3.1`).

**Voltage response.** The `model` property picks a `LoadResponseCharacteristic`:

| DSS `model` | Import: `EnergyConsumer.LoadResponse` | Export |
|---|---|---|
| 1, constant PQ | `zip_constant_pq` | the power fractions of `get_load_response` are 1 |
| 2, constant Z | `zip_constant_z` | the impedance fractions are 1 |
| 5, constant I | `zip_constant_i` | the current fractions are 1 |
| 4, CVR | `exp_<CVRwatts>_<CVRvars>`, one row per pair in `load.cimtbl`, `exponentModel` true | exponential: `model=4` with `CVRwatts`, `CVRvars` from the exponents |
| 3, 6, 7, 8 | raises | not produced |
| any other mix of fractions | not produced | raises |

The three `zip_` rows come from the fixed `zip_fractions.cimtbl` that every distribution converter imports.

### Load properties

| Property | Import | Export |
|---|---|---|
| `name` | `EnergyConsumer.name`; mRID `ld_` + name, lowercased | the CIM name or mRID (`name_source`); one load per phase is `<name>_<phase>` |
| `bus1`, `phases` | `node`, `phases` (structural, see above) | `bus1` is the bus on the phase conductors; `phases` counts them |
| `kV` | not written: raises when the phase voltage it gives is more than 1 % off the bus's | the bus's BaseVoltage: line to line for delta and for 2 or 3 phases, line to neutral for 1-phase wye |
| `kW` | `EnergyConsumer.p (kW)` | `get_phase_loads` total p, in kW |
| `kvar` | `EnergyConsumer.q (kVAr)` | `get_phase_loads` total q, in kVAr |
| `pf` | derived into `q` | not written |
| `kVA` | derived into `p` and `q` when `kW` is unset; raises with `kW` | not written |
| `model` | `LoadResponse` (table above); default 1 | `get_load_response` |
| `CVRwatts`, `CVRvars` | `LoadResponseCharacteristic.pVoltageExponent`, `qVoltageExponent`; model 4 only; defaults 1 and 2 | model 4 only, from the response's exponents |
| `conn` | `phaseConnection` and `grounded`; default wye | Y and Yn are wye, D is delta; another kind raises |
| `NumCust` | `EnergyConsumer.customerCount`; default 1 | `customerCount`; unset: not written |
| `enabled` | `EnergyConsumer.normallyInService`; default true | `get_in_service(which='normal')`; unset: not written |
| `yearly` | `ConformLoad.LoadGroup` = `lg_<shape>`; a shape the deck does not define raises | the group's LoadShape when its schedule has points; otherwise the load is static |
| `daily`, `duty`, `growth`, `CVRcurve` | untranscribed: a `ConformLoad` has one group, its `yearly` shape's | not written |
| `status`, `Vminpu`, `Vmaxpu`, `Vminnorm`, `Vminemerg`, `Vlowpu` | untranscribed: solver settings with no CIM home | not written, so the engine's defaults |
| `Rneut`, `Xneut` | raises when set (a `Rneut` below 0, no neutral, is allowed) | not written |
| `xfkVA`, `allocationfactor` | raises: with `kW` the engine takes whichever comes last | not written |
| `ZIPV` | untranscribed: only model 8 uses it, and model 8 raises | model 8 is never produced |
| `kwh`, `kwhdays`, `Cfactor`, `load_class`, `pct_mean`, `pct_stddev`, `RelWeight`, `pct_SeriesRL`, `puXharm`, `XRharm`, `spectrum`, `basefreq`, `like` | untranscribed (`like` is resolved by the reader first) | not written |

An untranscribed value that a deck sets is listed in a `# untranscribed:` comment on the row, so nothing disappears
silently.

### Load fail-fast rules

| Rule | Message |
|---|---|
| `kW` with `kVA` | `Load a: kW with kVA; the engine takes whichever comes last, and the record keeps no order` |
| `kV` more than 1 % off its bus | `Load a: kV=12.47 on bus b1, whose ABC Y phase voltage is 4.16 kV; CIM has no load rating, so p would be at the wrong voltage` |
| `model` 3, 6, 7 or 8 | `Load a: model ConstantPQuadQ is not mapped (models 1, 2, 4 and 5 are)` |
| `yearly` names no LoadShape | `Load a: yearly=nope names no LoadShape of the deck` |
| `Rneut` of 0 or more, or `Xneut` | `Load a: Rneut not mapped yet (no deck in the sweep sets them)` |
| `xfkVA` or `allocationfactor` | `Load a: xfkVA/allocationfactor not mapped (with kW the engine takes whichever comes last, and the record keeps no order)` |
| export: unequal phases on a delta load | `a delta load with unequal phases; a CIM phase on a delta load names no branch (E8)` |
| export: ZIP fractions of no one model | `ZIP fractions {...} are no one DSS model (1, 2, 5)` |

### Load round trip

| What | Why |
|---|---|
| `kV` comes back as the bus's phase voltage (2.4 on a 4.16 kV bus is 2.40178) | CIM has no load rating. A constant-PQ load solves to the same power; a Z, I or CVR load's power follows the voltage ratio, by 0.15 % for a constant-Z load here |
| `pf` and `kVA` come back as `kW` and `kvar` | `p` and `q` carry the power |
| unequal per-phase values come back as one 1-phase `Load` per phase, `<name>_<phase>`, the first carrying `NumCust` and the others 0 | a load from another CIM source can carry `EnergyConsumerPhase` values; a DSS deck never does |
| `daily`, `duty` and the untranscribed settings come back at the engine's defaults | no CIM home |
| a load whose shape has no points comes back static, with one warning that lists the groups | see [LoadShape](#loadshape) |

A disabled load stays in the model with `normallyInService` false and comes back `enabled=No`.

### Load excerpt

From [`tests/atoms/load/loads.cimtbl`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/tests/atoms/load/loads.cimtbl).
The comments name the defaults the deck relied on:

```text
# model 4 (CVR): p = p0 (V/V0)^CVRwatts, q = q0 (V/V0)^CVRvars
Table LoadResponseCharacteristic: mRID, exponentModel, pVoltageExponent, qVoltageExponent
    exp_0.8_3, true, 0.8, 3.0
    exp_1_2,   true, 1.0, 2.0

Table EnergyConsumer: mRID, name, node, phases, phaseConnection, grounded, p (kW), q (kVAr), customerCount, LoadResponse, normallyInService, BaseVoltage, EquipmentContainer=fdr_atom
    # defaulted: NumCust=1, enabled=true
    ld_ca,    ca,    b1,    CA,   D, false, 170.0,  82.33475782243494,   1, zip_constant_i,  true,  bv_4p16kv
    # defaulted: conn=wye, NumCust=1, enabled=true
    ld_cvr1,  cvr1,  b1,    A,    Y, true,  100.0,  32.86841051788632,   1, exp_0.8_3,       true,  bv_4p16kv
```

Round trip two of the atom's loads (`cvr1` is model 4, `house` is a 2-phase split-phase load):

```python
for line in round_trip("load/loads.dss", schema.Load):
    if " Load.cvr1 " in line or " Load.house " in line:
        print(line)
```

```text
new Load.cvr1 phases=1 bus1=b1.1 kV=2.40177711982884 kW=100 model=4 conn=wye kvar=32.8684105178863 CVRwatts=0.8 CVRvars=3 NumCust=1 enabled=Yes
new Load.house phases=2 bus1=house.1.2 kV=0.207846096908265 kW=5 model=1 conn=wye kvar=3.09872169201551 NumCust=1 enabled=Yes
```

The deck's `kV=2.40177711982884` for `cvr1` is already the bus's phase voltage. `house` had `kV=0.208` and comes back
as the leg pair's 0.2078.

## Capacitor

One `LinearShuntCompensator` per `Capacitor`, mRID `cap_` + the name, lowercased. Only a one-section bank maps.

`nomQ` is `kvar` (the total over the phases) and `nomU` is `kv`, both as the deck rates them. `bPerSection` is
`nomQ / nomU^2`: kVAr over kV squared is millisiemens, so the column is `bPerSection (mS)` and no factor appears. `maximumSections` is 1, and `sections`
and `normalSections` are the steps `states` closes. A bank whose `kv` differs
from its bus's keeps its rated `kv` (13.8 kV on a 13.2 kV bus stays).

### Capacitor properties

| Property | Import | Export |
|---|---|---|
| `name` | `LinearShuntCompensator.name`; mRID `cap_` + name, lowercased | the CIM name or mRID (`name_source`) |
| `bus1`, `phases`, `conn` | `node`, `phases`, `phaseConnection` and `grounded`, as for a load; default 3 phases, wye | the same connection rule as a load |
| `kvar` | `nomQ (kVAr)`, the total over the phases; default 1200; more than one step raises | `kvar=[x]` from `get_shunt_reactive_power(sections='maximum', voltage='nominal')`, in kVAr; `maximumSections` other than 1 raises |
| `kv` | `nomU (kV)`, and `bPerSection (mS)`; line to neutral for a 1-phase wye bank, else line to line; default 12.47 | `nomU`, the voltage `bPerSection` was derived on |
| `Numsteps` | `maximumSections`; more than 1 raises (unequal steps would need a `NonlinearShuntCompensator`) | not written; `maximumSections` above 1 raises |
| `states` | `sections` = `normalSections` = the steps closed; default all closed | `states=[sections]`; `sections` other than 0 or 1 raises; `normalSections` is not written |
| `enabled` | `normallyInService`; default true | `get_in_service(which='normal')`; unset: not written |
| `bus2`, `cmatrix`, `cuf`, `normamps`, `emergamps` | raises when set | not written |
| `R`, `XL` | 0 is untranscribed, any other value raises | not written |
| `Harm`, `faultrate`, `pctperm`, `repair`, `basefreq`, `like` | untranscribed | not written |

### Capacitor fail-fast rules

| Rule | Message |
|---|---|
| more than one step | `Capacitor c: 2 steps; only one section is mapped` |
| `bus2`, `cmatrix`, `cuf`, nonzero `R` or `XL`, `normamps`, `emergamps` | `Capacitor c: R not mapped yet (no deck in the sweep sets them)` |
| export: `maximumSections` other than 1 | `maximumSections 2; one section is mapped, as on import` |
| export: `sections` other than 0 or 1 | `sections 2; a one-section bank has 0 or 1` |

### Capacitor round trip

| What | Why |
|---|---|
| `normalSections` is lost | DSS has no normal state for a capacitor; `states` carries `sections` |
| `R=0` and the reliability settings come back at the engine's defaults | untranscribed |

### Capacitor excerpt

From [`tests/atoms/capacitor/caps.cimtbl`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/tests/atoms/capacitor/caps.cimtbl):

```text
# derived: bPerSection = nomQ / nomU^2 (b_per_section); sections = normalSections = the steps states closes
Table LinearShuntCompensator: mRID, name, node, phases, phaseConnection, grounded, nomQ (kVAr), nomU (kV), bPerSection (mS), maximumSections, normalSections, sections, normallyInService, BaseVoltage, EquipmentContainer=fdr_atom
    # defaulted: conn=wye, Numsteps=1, enabled=true
    cap_c1,   c1,   b2, C, Y, true,  100.0, 2.4,  17.36111111111111, 1, 1, 1, true, bv_4p16kv
```

## CapControl

One `RegulatingControl` per `CapControl`, mRID `cc_` + the name, lowercased. The control is in `capcontrol.cimtbl`,
and an update of the `LinearShuntCompensator` it regulates gives that bank its `RegulatingControl`, `aVRDelay (s)`
and `controlEnabled`. So the capacitor mapper knows nothing of controls, and a control on its own capacitor makes no
reference cycle.

The control's `Terminal` is the monitored element's: `ln_<line>_T<n>` for a line, `sw_<switch>_T<n>` for a switch
line, `cap_<capacitor>_T<n>` for a capacitor. An element of another class raises.

**ON and OFF.** CIM has a target and a deadband in primary units, and DSS has ON and OFF settings on the relay's
side. The importer writes `targetValue` = (ON + OFF) / 2 and `targetDeadband` = abs(OFF - ON), after scaling by
`PTratio` (voltage) or `CTratio` (current). A kvar control's values stay in kvar, and the row says so with
`targetValueUnitMultiplier=k`. The exporter inverts it and divides by the same ratio.

| DSS `type` | `RegulatingControl.mode` | ON is | `targetValue` and `targetDeadband` are in |
|---|---|---|---|
| `voltage` | `voltage` | below OFF | V: ON and OFF x `PTratio` |
| `current` | `currentFlow` | above OFF | A: ON and OFF x `CTratio` |
| `kvar` | `reactivePower` | above OFF | kvar, with `targetValueUnitMultiplier=k` |
| `time` | `timeScheduled` | below OFF | hours from midnight |
| `pf`, `follow` | raises | | |

The `type` is read by a unique prefix, as the engine reads it (`volt` is voltage); the default is current. A control
with ON on the wrong side of OFF for its type raises, so the exporter can rebuild the pair from the mode.

### CapControl properties

| Property | Import | Export |
|---|---|---|
| `name` | `RegulatingControl.name`; mRID `cc_` + name, lowercased | the CIM name or mRID (`name_source`) |
| `element`, `terminal` | `RegulatingControl.Terminal`; `terminal` defaults to 1; a Line, switch or Capacitor that no `New` defines raises | `Line.<line or switch>` or `Capacitor.<shunt>` of the monitored Terminal's equipment, and its `sequenceNumber`; other equipment raises |
| `capacitor` | the update row names `cap_<capacitor>`; one that no `New` defines raises, and so do two controls on one capacitor | the one `LinearShuntCompensator` the control regulates; anything else regulated raises |
| `type` | `RegulatingControl.mode` (table above); default current | `voltage`, `currentFlow`, `reactivePower`, `timeScheduled` give voltage, current, kvar, time; another mode raises |
| `PTratio`, `CTratio` | `ptRatio`, `ctRatio`; default 60 | written when set; a voltage control needs `ptRatio` and a current control needs `ctRatio`, else it raises |
| `ONsetting`, `OFFsetting` | `targetValue`, `targetDeadband` (derived); defaults 300 and 200 | ON and OFF = target -+ deadband / 2 (`on_off_from_band`), then divided by the ratio; an unset `targetDeadband` raises |
| `Delay` | `LinearShuntCompensator.aVRDelay (s)` on the update row; default 15 | the shunt's `aVRDelay`; unset: not written |
| `PTPhase` | `monitoredPhase`: the phase of the monitored terminal's conductor `PTPhase` (default 1); a number past the conductors raises, and `AVG`, `MAX` and `MIN` raise `ValueError` in the mapper | the 1-based place of `monitoredPhase` among the monitored equipment's phase conductors |
| `enabled` | `RegulatingControl.enabled`, and `controlEnabled` on the update row; default true | the control's `enabled`; the shunt's `controlEnabled` must agree |
| `VoltOverride`, `Vmax`, `Vmin`, `DelayOFF`, `DeadTime` | untranscribed: no CIM home | not written, so the engine's defaults |
| `CTPhase`, `VBus`, `UserModel`, `UserData`, `ControlSignal` | raises when set | not written |
| `EventLog`, `pctMinkvar`, `Reset`, `basefreq`, `like` | untranscribed | not written |

### CapControl fail-fast rules

| Rule | Message |
|---|---|
| `type=pf` or `follow` | `CapControl cc: type=pf is not mapped` |
| ON on the wrong side of OFF | `CapControl cc: ON -300.0 is not above OFF 150.0 for a reactivePower control` |
| export: another `mode` | `mode ...; a CapControl is voltage, current, kvar or time` |
| export: `targetDeadband` unset | `targetDeadband is unset; a CapControl needs ON and OFF` |
| export: an allowed range or a reverse setting | `[...] have no CapControl slot` |
| export: a control that does not regulate exactly one capacitor | `regulates [...]; a CapControl has one LinearShuntCompensator` |

A `RegulatingControl` that regulates a `SynchronousMachine` is the machine's own and is written by its `Generator`
(see [DER and machines](der.md)). A `TapChangerControl` is a `RegControl`, on the
[transformers page](transformers.md).

### CapControl round trip

| What | Why |
|---|---|
| `VoltOverride`, `Vmax`, `Vmin`, `DelayOFF`, `DeadTime` come back at the defaults | untranscribed. A kvar control that used `VoltOverride` acts differently when the engine solves it |
| `type=volt` comes back `voltage` | the type is written out in full |

### CapControl excerpt

From [`tests/atoms/capacitor/caps_capcontrol.cimtbl`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/tests/atoms/capacitor/caps_capcontrol.cimtbl).
A kvar control on a switch line (ON 150, OFF -225 kvar), then the update of its capacitor:

```text
Table RegulatingControl: mRID, name, mode, discrete=true, enabled, monitoredPhase, ptRatio, ctRatio, targetValue, targetDeadband, targetValueUnitMultiplier, Terminal
    # derived from ON=150.0, OFF=-225.0
    # defaulted: PTPhase=1, enabled=true
    # untranscribed: VoltOverride=true, Vmax=7740.0, Vmin=7110.0, DelayOFF=90.0
    cc_kvar, kvar, reactivePower, true, A, 1.0,  1.0,  -37.5,  375.0, k, sw_capsw_T1

# the compensator's control, delay (Delay) and controlEnabled
Update Table LinearShuntCompensator: mRID, RegulatingControl, aVRDelay (s), controlEnabled
    cap_c3,  cc_kvar, 100.0, true
```

The same atom round trips. `c1` is a 1-phase bank that a voltage control on line `l2` switches:

```python
for line in round_trip("capacitor/caps.dss", schema.Capacitor, schema.Capcontrol):
    if " Capacitor.c1 " in line or " Capcontrol.volt " in line:
        print(line)
```

```text
new Capacitor.c1 phases=1 bus1=b2.3 kvar=[100] kv=2.4 conn=wye states=[1] enabled=Yes
new Capcontrol.volt element=Line.l2 terminal=2 capacitor=c1 type=voltage PTratio=20 CTratio=60 on=115 off=125 Delay=15 PTPhase=1 enabled=Yes
```

## LoadShape

A `LoadShape` that a `Load` names as `yearly` is a curve of multipliers on that load's `kW` and `kvar`. It maps to
a `ConformLoadGroup` `lg_<name>` with one `ConformLoadSchedule` `ls_<name>`, and every load that names it is a
`ConformLoad` of the group. The points are not in the `.cimtbl`: they go to the `RegularTimePoint` table of a
Parquet sidecar, one row per sample, as the core site's
[time series guide](https://pnnl-cim-tools.github.io/CIMHub/core/guide/time-points/) describes. Pass the dict that
receives them to the converters:

| Direction | How the points travel |
|---|---|
| import | `DssImporter(name, time_points={})` (or `dss_to_cim(..., time_points=)`) fills the dict. Without it the points are dropped with one warning |
| export | `DssExporter(time_points)` (or `cim_to_dss(..., time_points=)`) reads the dict. Without it the loads are written static |

A shape that a `PVSystem`, `Storage` or `Generator` names as `yearly` is not a load group. It is that device's own
`EnergyConnectionSchedule`, described on [DER and machines](der.md). A shape that nothing names is not mapped, and
the master's comment counts it (`not mapped: Loadshape 1`).

**Time.** DSS has no date. Sample k (from 1) is in force from k x interval, so `startTime` is 2020-01-01T00:00Z plus
one interval, and `sequenceNumber` counts from 0. The `timeStep` keeps the unit of the interval slot the deck
assigned last, with one `ConformLoadSchedule` table per unit (`h`, `min`, `s`). The engine wraps a shape around, and
CIM has no repeat, so the wrap is lost.

**No `npts`.** The engine reads none of `mult` without `npts` (a bare `mult=1`), so the load stays constant. Such a
shape becomes a `ConformLoadGroup` with no schedule, its name kept.

### LoadShape properties

| Property | Import | Export |
|---|---|---|
| `name` | `ConformLoadGroup.name` and `ConformLoadSchedule.name`; mRIDs `lg_` and `ls_` + name, lowercased | a LoadShape named after the group (the `Loadshape` namespace) |
| `npts` | structural: unset means no schedule; otherwise it must equal the number of `mult` values | the number of points |
| `mult` | `RegularTimePoint.value1` in the sidecar, `value1Unit` none | `mult` = `value1` of each point, in sequence order |
| `qmult` | `RegularTimePoint.value2`, `value2Unit` none; unset: Q follows `mult`, as in the engine | `qmult` = `value2`; not written when `value2` is unset |
| `interval`, `minterval`, `sinterval` | `ConformLoadSchedule.timeStep` in `h`, `min` or `s`, from the slot assigned last; none is 1 h; 0 or less (0 is an hour array) raises | always `sinterval` = `timeStep` in seconds; a `timeStep` that is not positive raises |
| `action` | `normalize` divides `mult` and `qmult` each by its largest magnitude, as the engine does; an array assigned after it raises; `DblSave` and `SngSave` are untranscribed; any other raises | not written |
| `UseActual` | raises when yes: whether a load takes the shape's peak as its kW depends on command order | a `NonConformLoad` is written static |
| `hour`, `csvfile`, `sngfile`, `dblfile`, `PQCSVFile`, `Pmult`, `Pbase`, `Qbase` | raises when set | not written |
| `mean`, `stddev`, `Pmax`, `Qmax`, `MemoryMapping`, `Mode`, `Interpolation`, `like` | untranscribed | not written |

On export, a schedule whose values have a unit other than none raises, because a conform schedule holds
multipliers. Owners whose name, interval and multipliers agree share one LoadShape; another with that name and
other points takes a suffix (`sun`, `sun_2`).

A `ConformLoad` is written static, with one warning that lists its group, when the group has no schedule, the
schedule has no points, the group holds days by season and day type (a GridLAB-D schedule's, which DSS has no
calendar for), or the load is a `NonConformLoad`.

### LoadShape fail-fast rules

| Rule | Message |
|---|---|
| `UseActual=yes` | `LoadShape s: UseActual=Yes; a Load naming it takes the shape's peak as its kW or keeps its own by command order, which the record does not keep` |
| `npts` is not the number of `mult` values | `LoadShape s: npts=3 but mult has 2 values` |
| an interval of 0 | `LoadShape s: interval=0.0; an hour array (interval 0) is not mapped` |
| `qmult` of another length, no `mult`, a file or `hour` array, an unknown `action` | `LoadShape s: ...` naming the property |

### LoadShape round trip

| What | Why |
|---|---|
| `interval=` and `minterval=` come back as `sinterval=` | one written form; the interval is equal |
| a shape that no load names, and a load's `daily` and `duty` | not imported |
| a bare `mult=1` shape is not written, and its loads have no `yearly` | the engine reads no points from it, so the loads are constant either way |
| the wrap-around, and a GridLAB-D player's date | CIM has no repeat, DSS has no date |

### LoadShape excerpt

From [`tests/atoms/loadshape/loadshapes.loadshape.cimtbl`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/tests/atoms/loadshape/loadshapes.loadshape.cimtbl):

```text
Table ConformLoadGroup: mRID, name
    lg_com,  com
    # npts unset: the engine reads none of mult (S8), so no schedule
    lg_flat, flat
    lg_ind,  ind
    lg_res,  res

Table ConformLoadSchedule: mRID, name, startTime, timeStep (h), value1Unit, value2Unit, ConformLoadGroup
    ls_res, res, 2020-01-01T01:00:00+00:00, 1.0, none, none, lg_res
```

Import the atom, look at the sidecar, and export the shape and one of the loads that names it:

```python
path = ATOMS / "loadshape/loadshapes.dss"
time_points = {}
DssImporter(path.stem, time_points=time_points).to_cim(DssReader(path).read_all())
print(sorted(time_points))
rows = time_points["RegularTimePoint"].to_pylist()
print(len(rows), [row["value1"] for row in rows[:4]])

for line in round_trip("loadshape/loadshapes.dss", schema.Loadshape, schema.Load):
    if " Loadshape.res " in line or " Load.r1 " in line:
        print(line)
```

```text
['RegularTimePoint']
11 [0.25, 0.5, 1.0, 0.75]
new Loadshape.res npts=4 mult=[0.5 0.75 1 0.8] qmult=[0.4 0.6 0.9 0.7] sinterval=3600
new Load.r1 phases=1 bus1=b1.1 kV=2.40177711982884 kW=100 model=1 yearly=res conn=wye kvar=40 NumCust=1 enabled=Yes
```

The 11 points are `res` (4), `com` (4) and `ind` (3); the first four are `com` after `action=normalize`
(2 4 8 6 over 8). The export also logs a warning that the group `flat`, a shape with no `npts`, is written static.
