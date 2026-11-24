# DER and machines

This page is the conversion reference for the OpenDSS classes that inject power: `PVSystem`, `Storage` and
`Generator`. For each one it says what the importer writes, what the exporter reads back and what raises. The field
classes (copied, mapped, structural, derived, untranscribed) and the conventions every section follows are on the
[reference index](index.md). The getters the exporter reads through are on the core site's
[sources, DER and machines](https://pnnl-cim-tools.github.io/CIMHub/core/reference/der/) page.

| DSS class | CIM classes | `.cimtbl` artifact and shape | Importer | Exporter |
|---|---|---|---|---|
| [`PVSystem`](#pvsystem) | `PowerElectronicsConnection` and its `PhotoVoltaicUnit` | `pvsystem.cimtbl`, shape `der` | `importer/cimtbl/pvsystem.py` | `exporter/pvsystem.py` |
| [`Storage`](#storage) | `PowerElectronicsConnection` and its `BatteryUnit` | `storage.cimtbl`, shape `der` | `importer/cimtbl/storage.py` | `exporter/storage.py` |
| [`Generator`](#generator) | `SynchronousMachine`, and a `RegulatingControl` for model 3 | `generator.cimtbl`, shape `synchronous_machine` | `importer/cimtbl/generator.py` | `exporter/generator.py` |
| `InvControl` | not converted | none | none | none |

`InvControl` has no mapper. The master's comment counts it (`not mapped: Invcontrol 1`), so a deck's inverter
control is not silently lost, but nothing of it reaches CIM. A PV's or battery's own setpoints are
converted without it. A battery's `VarFollowInverter` acts only with one, so it is untranscribed; a PV's is used in
the snapshot (see [PVSystem](#pvsystem)). A deck whose `InvControl` gives `mode` or `combimode` as a name
(`VOLTVAR`) does not read at all today: the reader raises `DssParseError` on it, so the count above is reached only
with a numeric mode or none.

A yearly `LoadShape` on a device is the device's own `EnergyConnectionSchedule`, which the section of each class
covers. The load-side shapes are on [Loads, capacitors and shapes](loads.md). The table shapes are on the core
site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/). Source paths are under
[`cimhub_opendss/src/cimhub_opendss/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_opendss/src/cimhub_opendss).

`PVSystem` and `Storage` share `importer/cimtbl/inverter.py` (the connection row) and `exporter/inverter.py`
(`inverter_pieces`, the chop below). All five classes share the terminal rule in `importer/cimtbl/injection.py` and
`exporter/injection.py`.

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
is the mRID (`pv_dim`, `storage_capped`, `gen_steam`).

## Sign convention

CIM's terminal sign is the load's: `p` and `q` are positive **into** the equipment. A PV array, a generator and a
discharging battery therefore carry negative `p`. The importer writes `p` = -(the output) and `q` = -`kvar`, and the
exporter asks the core getters for the generation sign (`sign='generation'`), so DSS `kW` and `kvar` come back
positive for output. The rule and its limit pairs are on the core
[DER reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/der/#the-sign-convention).

## Rules shared by PVSystem, Storage and Generator

**Terminal.** The importer's phase rule is the load's: the bus's nodes give the phases (1, 2, 3 are A, B, C; 1 and
2 are `s1` and `s2` on a split-phase island), a wye device's neutral is ground and a delta device has none. The
exporter puts the phase conductors on `bus1`; a delta across two conductors is `phases=1`.

**Rated voltage.** `ratedU` (kV, line to line) is `kv`, times the square root of 3 for a 1-phase wye device. The
exporter divides it back. It is the device's own rating and is **not** checked against the bus, unlike a load's
`kV`: a 240 V inverter on 120 V legs stays 240 V.

**The inverter row.** A `PVSystem` and a `Storage` share one `PowerElectronicsConnection` row:

| Column | Import | Export |
|---|---|---|
| `ratedS (kVA)` | `kVA` | `ratedS`, times the unit's share |
| `maxQ (kVAr)` | `kvarMax`; default `kVA` | `kvarMax`, times the share; unset: not written |
| `minQ (kVAr)` | -`kvarMaxAbs`; default `kVA` | `kvarMaxAbs` = -`minQ`, times the share; unset: not written |
| `maxIFault` | 1 / `Vminpu`; default `Vminpu` 0.9 | `Vminpu` = 1 / `maxIFault`; unset: not written |
| `normallyInService` | `enabled`; default true | `get_in_service(which='normal')`; unset: not written |
| `p (kW)`, `q (kVAr)` | the dispatch, in the load sign | the unit's output, in the generation sign |

The unit is `<connection mRID>_unit`: a `PhotoVoltaicUnit` for a PV, a `BatteryUnit` for a battery.

**The chop on export.** A DSS `PVSystem` or `Storage` is one inverter with one DC device, and CIM lets several units
share a connection. The exporter writes one DSS device per unit of the right class:

| Case | Result |
|---|---|
| one unit | the device keeps the connection's name |
| several units | each takes its unit's name, and a share of `ratedS`, `maxQ` and `minQ` equal to its `maxP` over the units' total |
| unequal phases, one unit | one 1-phase device per phase, `<name>_<phase>`, each a 1/n share of the connection and of the unit's own ratings |
| unequal phases, several units, or a delta inverter | raises |
| a device's output above its share of `ratedS` | raises, because the engine would cut it (a DC-coupled PV feeding its battery can do this) |
| a `PowerElectronicsWindUnit` | a model 1 `Generator` at the unit's output, as a [Generator](#generator) |
| any other unit class | raises |

Units, shares and the getters behind them are `get_inverter_units`, `get_der_output` and `get_inverter_rating`, on the
core [DER reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/der/#get_inverter_units).

## PVSystem

One `PowerElectronicsConnection` `pv_<name>` (lowercased) and one `PhotoVoltaicUnit` `pv_<name>_unit`. The `p` is the
engine's snapshot dispatch at rated voltage, worked out by the importer:

1. The panel gives `Pmpp` x `irradiance`. Below `%Cutout` of `kVA` the inverter is off and `p` is 0 (the row comment
   says `off: below %Cutout of kVA`).
2. Otherwise the power is capped at `Pmpp` x `%Pmpp` / 100, then cut to fit `kVA` with `kvar` kept (var priority).
3. `q` is `kvar`, or the power after the `%Pmpp` cap and before the cut to `kVA`, x tan(acos abs(`pf`)) with the sign of `pf`, whichever the deck assigned last (default `pf`
   1). An inverter that is off still gives a set `kvar`, unless `VarFollowInverter` is yes.

`irradiance` is also copied to `PhotoVoltaicUnit.irradiance (kW/m2)`, a property that `cim18v17` carries for it.

### PVSystem properties

| Property | Import | Export |
|---|---|---|
| `name` | `PowerElectronicsConnection.name`; mRID `pv_` + name, lowercased | the CIM name or mRID; the connection's for one unit, the unit's for several, `<name>_<phase>` per phase |
| `phases`, `bus1`, `conn` | `node`, `phases`, `phaseConnection` (Y or D); default 3 phases, wye | as the shared terminal rule |
| `kv` | `ratedU (kV)`, line to line (derived); default 12.47 | `kv` from `ratedU` |
| `irradiance` | `PhotoVoltaicUnit.irradiance (kW/m2)`, and `p`; default 1 | the unit's `irradiance`; unset: the unit's output over `Pmpp`, so the panel gives exactly the output |
| `Pmpp` | `PhotoVoltaicUnit.maxP (kW)` with `minP` 0, and `p`; default 500 | `maxP` times the share; unset or 0 raises, and so does a `minP` other than 0 |
| `pct_Pmpp` | derived into `p`; default 100 | 100 x output / `Pmpp` when the output is below the panel's power; not written otherwise; an output above the panel raises |
| `kVA` | `ratedS (kVA)`, and caps `p`; default 500 | `ratedS` times the share |
| `kvar`, `pf` | derived into `q` (the later of the two wins) | `kvar` is the unit's q; `pf` only with a yearly shape whose q follows p |
| `pct_Cutout` | derived: `p` is 0 below it; default 20 | 0 when the output is above 0 and the panel is below 20 % of `kVA`, or with a yearly shape; else not written |
| `pct_Cutin` | structural: acts only after the inverter turns off; default 20 | 0 with a yearly shape; else not written |
| `VarFollowInverter` | derived into `q` when the inverter is off; default no | not written |
| `kvarMax`, `kvarMaxAbs`, `Vminpu` | inverter row (table above) | inverter row |
| `model` | structural: only 1 maps, any other raises | not written, so the engine's 1 |
| `yearly` | the PV's `EnergyConnectionSchedule` `<mRID>_yearly` (see below) | a LoadShape; see below |
| `enabled` | `normallyInService` | inverter row |
| `EffCurve`, `P_TCurve`, `UserModel`, `UserData` | raises when set: they change the snapshot power or have no home | not written |
| `Balanced`, `LimitCurrent`, `WattPriority`, `PFPriority` | raises when yes | not written |
| `pct_PminNoVars`, `pct_PminkvarMax` | raises when nonzero | not written |
| `ControlMode` | GFL maps; GFM raises | not written |
| `Temperature`, `Vmaxpu`, `daily`, `duty`, `Tyearly`, `Tdaily`, `Tduty`, `DutyStart`, `class_class`, `debugtrace`, `spectrum`, `basefreq`, `like` | untranscribed | not written |
| `pct_R`, `pct_X`, `kVDC`, `Kp`, `PITol`, `SafeVoltage`, `SafeMode`, `DynamicEq`, `DynOut`, `AmpLimit`, `AmpLimitGain` | untranscribed: dynamics settings with no home in the network profile | not written |

**Yearly shape.** A `yearly` LoadShape scales the irradiance. The importer writes an `EnergyConnectionSchedule`
`<mRID>_yearly` in `pvsystem.cimtbl`, and its points (`p` and `q` at each sample, in the load sign, SI units) go to
the `EnergyConnectionTimePoint` table of the sidecar, each sample solved as above at `irradiance` x `mult`. A
`qmult` on the shape raises. A sample whose panel power falls between `%Cutout` and `%Cutin` of `kVA` raises: the
engine keeps the inverter on or off as it was, which depends on the earlier samples.

The exporter turns the schedule back into a LoadShape with `mult` = `p` / (`Pmpp` x `irradiance`) at each point, and
writes `%Cutin=0 %Cutout=0` so that the engine gives every point's `p`, the low ones too. It writes `q` as `kvar`
when every point's `q` is the written `kvar`, as `pf` when `q` is in proportion to `p`, and otherwise raises.

### PVSystem fail-fast rules

| Rule | Message |
|---|---|
| `model` other than 1 | `PVSystem p: model=2 is not mapped (model 1 is; the engine rejects anything but 1, 2 and 3)` |
| a curve, `Balanced`, `WattPriority`, ... set | `PVSystem p: ... not mapped yet (no deck in the sweep sets them)` |
| `kvar` above `kVA` | `PVSystem p: ... kvar is above its ... kVA` |
| a yearly sample between `%Cutout` and `%Cutin` | `PVSystem p: sample 1 of yearly=s puts the panel at 25 kW, between %Cutout (20) and %Cutin (30); the engine keeps the inverter as it was, which is not mapped` |
| export: output above `Pmpp` x `irradiance` | `p ... kW is above the panel's ... kW (maxP x irradiance ...)` |
| export: `p` into the PV | `p ... kW into the PV; a PVSystem only generates` |
| export: a yearly `q` that is neither the `kvar` nor in proportion to `p` | `its q is neither the PV's ... kvar nor in proportion to p; a PVSystem gives one or the other` |

### PVSystem round trip

| What | Why |
|---|---|
| `%Pmpp` is written when the output is below the panel's power (a PV cut to fit `kVA`, or held back) | the engine gives CIM's `p`; a PV that was off comes back `%Pmpp=0` |
| `%Cutout=0` is written for a running PV whose panel is below 20 % of `kVA` | the engine would switch it off at its default cut-out |
| with a yearly shape, `%Cutin` and `%Cutout` come back 0 and `q` as `kvar` or `pf` | the engine then gives the points' `p` and `q` |
| devices that shared a shape but whose multipliers differ get their own, `sun`, `sun_2` | one shape scales one way |
| `irradiance` is the unit's when set, else the output over `Pmpp` | a CIM PV need not have one |

### PVSystem excerpt

From [`tests/atoms/der/pvsystem.cimtbl`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/tests/atoms/der/pvsystem.cimtbl).
`pmppcap` has `irradiance=0.9`, `Pmpp=10` and `%Pmpp=60`, so the panel's 9 kW is capped at 6:

```text
Table PowerElectronicsConnection: mRID, name, node, phases, phaseConnection, ratedS (kVA), ratedU (kV), p (kW), q (kVAr), maxQ (kVAr), minQ (kVAr), maxIFault, normallyInService, BaseVoltage, EquipmentContainer=fdr_atom
    # defaulted: phases=3, pf=1.0, conn=wye, pct_Cutin=20.0, pct_Cutout=20.0, model=1, Vminpu=0.9, enabled=true
    pv_pmppcap,  pmppcap,  b2,    ,     Y, 12.0,   0.48,                -6.0,    0.0,                12.0,   -12.0,   1.1111111111111112, true, bv_480v

Table PhotoVoltaicUnit: mRID, maxP (kW), minP (kW), irradiance (kW/m2), PowerElectronicsConnection, EquipmentContainer=fdr_atom
    pv_pmppcap_unit,  10.0,   0.0, 0.9, pv_pmppcap
```

(The two rows are from different tables of the file, with the other devices' rows between them left out.)

## Storage

One `PowerElectronicsConnection` `storage_<name>` (lowercased) and one `BatteryUnit` `storage_<name>_unit`. The engine
keeps a discharge setpoint and a charge setpoint, and `State` picks the one that runs. The importer replays the
deck's assignments in order and gets the snapshot state and `p`:

- `kW` > 0 sets the discharge setpoint and the state discharging; `kW` < 0 sets the charge setpoint and charging;
  `kW` = 0 idles. So `state=charge kW=150` discharges at 150 kW.
- `%Discharge` or `%Charge` puts its setpoint back to that percent of `kWrated`; `State` is read by its first
  letter (`charge` is charging).
- The output is capped at `kVA` (default `kWrated`). A battery that waits draws its idling loss, `%IdlingkW` x
  `kWrated` / 100, which is its `p`. `q` is 0.

The load sign applies: discharge is negative `p`, charging positive.

### Storage properties

| Property | Import | Export |
|---|---|---|
| `name` | `PowerElectronicsConnection.name`; mRID `storage_` + name, lowercased | as for a PV |
| `phases`, `bus1`, `conn`, `kv` | as for a PV | as for a PV |
| `kW` | derived: replayed with `State` into `p` | not written: `%Discharge` and `%Charge` carry the output, because the engine turns `kW` into a percent of the `kWrated` of that moment and `kWrated` is written after it |
| `State` | `BatteryUnit.batteryState`: charging, discharging, idling become `charging`, `discharging`, `waiting`; default idling | `batteryState` charging, discharging, waiting give `State`; another state raises, and so does an output of the wrong sign |
| `kWrated` | `BatteryUnit.maxP (kW)` and `minP` = -`kWrated`; default 25 | `maxP` times the share; unset raises, and a `minP` other than -`maxP` raises |
| `kWhrated` | `BatteryUnit.ratedE (kWh)`; default 50 | `ratedE`; unset: not written |
| `kWhstored`, `pct_stored` | `BatteryUnit.storedE (kWh)`: `kWhstored`, or `%stored` x `kWhrated` / 100, whichever the deck assigned last; default `%stored` 100 | `kWhstored` = `storedE` |
| `pct_reserve` | `BatteryUnit.minimumE (kWh)` = `%reserve` x `kWhrated` / 100; default 20 | `%reserve` = `minimumE` / `ratedE` x 100; either unset: not written |
| `pct_Discharge`, `pct_Charge` | derived into `p`; default 100 | the output over `kWrated` x 100, for the matching state |
| `pct_EffCharge`, `pct_EffDischarge` | `chargingEfficiency`, `dischargingEfficiency` (percent); default 90 | the efficiencies; unset: not written |
| `pct_IdlingkW` | `BatteryUnit.idlingP (kW)` = `%IdlingkW` x `kWrated` / 100, also the `p` when waiting; default 1 | `idlingP` / `kWrated` x 100; a waiting battery's `p` must equal `idlingP` when both are set |
| `kVA`, `kvarMax`, `kvarMaxAbs`, `Vminpu`, `enabled` | inverter row; `kVA` defaults to `kWrated` | inverter row |
| `kvar` | raises when nonzero | not written; a `q` other than 0 raises |
| `pf` | 1 only; any other raises | not written |
| `model` | 1 only; any other raises | not written |
| `DispMode` | `default`, or `follow` with a yearly shape; any other raises | `follow` with a yearly shape; else not written |
| `yearly` | `DispMode=follow`: the battery's `EnergyConnectionSchedule` `<mRID>_yearly` (see below); with another `DispMode`, a shape raises | a LoadShape (see below) |
| `EffCurve`, `DynaDLL`, `DynaData`, `UserModel`, `UserData` | raises when set | not written |
| `Balanced`, `LimitCurrent`, `WattPriority`, `PFPriority` | raises when yes | not written |
| `pct_PminNoVars`, `pct_PminkvarMax` | raises when nonzero | not written |
| `ControlMode` | GFL maps; GFM raises | not written |
| `pct_Cutin`, `pct_Cutout`, `VarFollowInverter`, `pct_kWrated`, `pct_Idlingkvar`, `DischargeTrigger`, `ChargeTrigger`, `TimeChargeTrig`, `Vmaxpu`, `daily`, `duty`, `class_class`, `debugtrace`, `spectrum`, `basefreq`, `like` | untranscribed | not written |
| `pct_R`, `pct_X`, `kVDC`, `Kp`, `PITol`, `SafeVoltage`, `SafeMode`, `DynamicEq`, `DynOut`, `AmpLimit`, `AmpLimitGain` | untranscribed: dynamics settings | not written |

**Energy checks.** The engine checks the stored energy against full and the reserve when the state is assigned.
Charging a full battery, or discharging at or below the reserve, makes it idle, and the mapping cannot say so: both
raise on import and on export. An energy assigned after the last `State` or `kW` raises on import. The exporter writes
the energies before `State` for the same reason.

**Yearly shape.** With `DispMode=follow`, a LoadShape is the battery's output at each sample: it discharges at
`mult` x `kWrated` when `mult` > 0, charges at -`mult` x `kWrated` when < 0 and idles at 0, capped at `kVA`. The
importer writes the points (`p` only) to the sidecar, and a `kW` or `State` on such a battery raises, because its
snapshot idles. A shape in another dispatch mode raises. The exporter writes `DispMode=follow` and the LoadShape with
`mult` = output / `kWrated`, 0 where the output is the idling loss, and does not write `State` (the battery must be
waiting). A point above `kVA`, or a `q` other than 0, raises.

### Storage fail-fast rules

| Rule | Message |
|---|---|
| `kvar` set | `Storage s: kvar not mapped yet (no deck in the sweep sets them)` |
| `DispMode` other than `default` and `follow` | `Storage s: DispMode=peakshave not mapped yet (no deck in the sweep sets them)` |
| charging a full battery | `Storage s: charging with 200 of 200 kWh stored; the engine idles a full battery, which is not mapped` |
| discharging at or below the reserve | `Storage s: discharging with ... kWh stored, at or below its ... kWh reserve; the engine idles it, which is not mapped` |
| `DispMode=follow` without a `yearly` shape, or the reverse | `Storage s: DispMode=... with yearly=...; only a follow-mode battery's yearly shape is mapped (S9-6)` |
| export: `batteryState` other than charging, discharging, waiting | `batteryState ...; a Storage State is charging, discharging or waiting` |
| export: `q` other than 0 | `q ... kVAr; a Storage's kvar is not mapped, as on import` |

### Storage round trip

| What | Why |
|---|---|
| `kW` never comes back; the output is `%Discharge` or `%Charge` | see the `kW` row |
| a battery capped by its `kVA` comes back with the capped percent (80 kVA on 100 kW: `%Discharge=80`) | CIM keeps only the capped output |
| in follow mode, `%Charge`, `%Discharge` and `State` are not written; a capped sample comes back at the cap (mult 0.8, not 1) | follow mode does not use them, and the schedule holds the output |
| `%stored` comes back as `kWhstored` | `storedE` is in kWh |

### Storage excerpt

From [`tests/atoms/der/storage.cimtbl`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/tests/atoms/der/storage.cimtbl).
`capped` has `kWrated=100` and `kVA=80`, so its discharge is capped at 80 kW:

```text
Table PowerElectronicsConnection: mRID, name, node, phases, phaseConnection, ratedS (kVA), ratedU (kV), p (kW), q (kVAr), maxQ (kVAr), minQ (kVAr), maxIFault, normallyInService, BaseVoltage, EquipmentContainer=fdr_atom
    # defaulted: phases=3, conn=wye, pf=1.0, pct_stored=100.0, pct_reserve=20.0, pct_Discharge=100.0, pct_Charge=100.0,
    # pct_EffCharge=90.0, pct_EffDischarge=90.0, pct_IdlingkW=1.0, model=1, Vminpu=0.9, DispMode=default, enabled=true
    storage_capped,   capped,   b2,    ,     Y, 80.0,  0.48,              -80.0,  0.0, 80.0,  -80.0,  1.1111111111111112, true, bv_480v

Table BatteryUnit: mRID, ratedE (kWh), storedE (kWh), minimumE (kWh), maxP (kW), minP (kW), chargingEfficiency (percent), dischargingEfficiency (percent), idlingP (kW), batteryState, PowerElectronicsConnection, EquipmentContainer=fdr_atom
    storage_capped_unit,   200.0, 200.0, 40.0,  100.0, -100.0, 90.0, 90.0, 1.0,  discharging, storage_capped
```

(The two rows are from different tables of the file, with the other batteries' rows between them left out.)

Round trip the DER atom. `dim` is a PV whose panel (1 kW) is below 20 % of its 12 kVA, so it is off. `pmppcap` is
capped by `%Pmpp`, and `capped` is the battery above:

```python
for line in round_trip("der/der.dss", schema.Pvsystem, schema.Storage):
    if " Pvsystem.dim " in line or " Pvsystem.pmppcap " in line or " Storage.capped " in line:
        print(line)
```

```text
new Pvsystem.dim phases=3 bus1=b2.1.2.3 kv=0.48 irrad=0.1 Pmpp=10 %Pmpp=0 conn=wye kvar=0 kVA=12 Vminpu=0.9 kvarMax=12 kvarMaxAbs=12 enabled=Yes
new Pvsystem.pmppcap phases=3 bus1=b2.1.2.3 kv=0.48 irrad=0.9 Pmpp=10 %Pmpp=60 conn=wye kvar=0 kVA=12 Vminpu=0.9 kvarMax=12 kvarMaxAbs=12 enabled=Yes
new Storage.capped phases=3 bus1=b2.1.2.3 kv=0.48 conn=wye kVA=80 kvarMax=80 kvarMaxAbs=80 kWrated=100 kWhrated=200 kWhstored=200 %reserve=20 State=discharging %Discharge=80 %EffCharge=90 %EffDischarge=90 %IdlingkW=1 Vminpu=0.9 enabled=Yes
```

## Generator

One `SynchronousMachine` `gen_<name>` (lowercased), with `type` generator and `operatingMode` generator. `p` = -`kW`
and `q` = -`kvar`, in the load sign. `kW` defaults to 1000 and `kVA` to 1.2 x `kW`.

**kvar.** The engine keeps `kvar` as a power factor. Assigning `kvar` sets the power factor at the `kW` of that
moment; assigning `kW` or `pf` recomputes `kvar` = `kW` x tan(acos abs(`pf`)). The importer replays the deck's
`kW`, `pf` and `kvar` assignments in order from the engine's start (1000 kW, pf 0.88, 60 kvar), so `kW=620 kvar=30`
followed by `kW=50` is 2.4 kvar, and `kvar=30 kW=100` is 3. The exporter writes `kW` first and `kvar` after it, so
that `kvar` is the engine's at that `kW`.

**Connection.** `SynchronousMachine` has no `phaseConnection`: `conn=wye` is `earthing` true and `conn=delta` is
false. On export an unset `earthing` raises.

**Models.** The mapped `model` values are:

| DSS `model` | Import | Export |
|---|---|---|
| 1, constant PQ | a machine at `kW` and `kvar` | model 1 when the machine has no control, or a disabled one on its own terminal |
| 7, current limited | as model 1; below `Vminpu` the engine limits its current, a power-flow behaviour (noted on the row) | comes back as model 1: CIM has no current limit |
| 3, PV bus | as model 1, plus a voltage `RegulatingControl` `gen_<name>_ctrl` on the machine's own terminal, given to the machine by an update | model 3 when an enabled voltage control regulates its own terminal |
| 2, 4, 5, 6 | raises | not produced |

The control has `targetValue` = `Vpu` x `ratedU`, in volts, and `targetDeadband` 0. The exporter writes
`Vpu` = `targetValue` / `ratedU`. A disabled control gives model 1, because DSS has no disabled PV bus.

### Generator properties

| Property | Import | Export |
|---|---|---|
| `name` | `SynchronousMachine.name`; mRID `gen_` + name, lowercased | the CIM name or mRID |
| `phases`, `bus1` | `node`, `phases`; default 3 phases | as the shared terminal rule |
| `kv` | `ratedU (kV)`, line to line (derived); default 12.47 | `kv` from `ratedU` |
| `kW` | `p (kW)` = -`kW` (derived); default 1000 | `get_der_output` total p, generation sign |
| `pf`, `kvar` | `q (kVAr)` = -`kvar`, replayed (derived); `pf` default 0.88 | `kvar` = total q, written after `kW`; `pf` is not written |
| `kVA` | `ratedS (kVA)`; default 1.2 x `kW` | `ratedS` |
| `conn` | `earthing`: wye true, delta false | `earthing` true is wye, false is delta; unset raises |
| `model` | table above | table above |
| `Vpu` | model 3: `RegulatingControl.targetValue` (V) = `Vpu` x `ratedU`; default 1 | model 3: `target` / `ratedU` |
| `maxkvar`, `minkvar` | `maxQ`, `minQ (kVAr)`, model 3 only; default 2 x `kvar` and -`maxkvar`; on another model they raise | model 3: `maxQ`, `minQ`; unset: not written |
| `yearly` | the machine's `EnergyConnectionSchedule` `<mRID>_yearly` (see below) | a LoadShape (see below) |
| `enabled` | `normallyInService`; default true | `get_in_service(which='normal')`; unset: not written |
| `MVA`, `UserModel`, `UserData`, `ShaftModel`, `ShaftData` | raises when set | not written |
| `Xd`, `Xdp`, `Xdpp`, `H`, `D`, `XRdp` | untranscribed: dynamics | not written: `cim18v17` has no machine reactance or inertia, so the engine's defaults |
| `Vminpu`, `Vmaxpu`, `pvfactor`, `Balanced`, `forceon`, `gen_class`, `debugtrace`, `DutyStart`, `daily`, `duty`, `DynamicEq`, `DynOut`, `spectrum`, `basefreq`, `like` | untranscribed | not written |
| `dispmode`, `dispvalue`, `status`, `UseFuel`, `FuelkWh`, `pct_Fuel`, `pct_Reserve`, `Refuel` | untranscribed: dispatch and fuel settings of a time series; with a yearly shape a `dispmode` other than default, a `dispvalue` above 0 or a `status` of Fixed raises | not written |

**Yearly shape.** The engine scales `kW` and `kvar` by `mult`. The importer writes the machine's
`EnergyConnectionSchedule` with `p` = -`kW` x `mult` and `q` = -`kvar` x `mult` at each sample; a model 3 machine's
`q` is its control's, so its schedule carries `p` only. The exporter writes `mult` = `p` / `kW`, and each point's `q`
must be `kvar` x `mult` (a model 3 machine's is not checked); a `kW` of 0 raises.

**Wind turbines.** A `PowerElectronicsWindUnit` behind a `PowerElectronicsConnection` has no DSS inverter class, so
the exporter writes a model 1 `Generator` at the unit's output, on the inverter's bus, voltage and share of `kVA`. The
inverter's q limits and `maxIFault` have no home on a model 1 generator and are not written. A schedule on a wind unit
raises. The deck reads back as a `SynchronousMachine`.

### Generator fail-fast rules

| Rule | Message |
|---|---|
| `model` 2, 4, 5, 6 | `Generator g: model ConstantZ is not mapped (models 1, 3 and 7 are)` |
| `maxkvar` or `minkvar` on another model | `Generator g: Maxkvar/Minkvar on model ConstantPQ; only model 3 uses them` |
| `MVA`, `UserModel`, `UserData`, `ShaftModel`, `ShaftData` | `Generator g: ... not mapped yet (no deck in the sweep sets them)` |
| a yearly shape with a dispatch setting | `Generator g: yearly=... with dispmode=..., ...; only a generator that follows its shape is mapped (S9)` |
| export: a control on another terminal | `its control monitors another terminal; a Generator regulates its own` |
| export: a control that is not voltage, or has a deadband, an allowed range or a reverse target | `a ... control; a Generator regulates voltage`, or `[...] have no Generator slot` |
| export: a yearly `q` off `kvar` x `mult` | `point 2 has q ... kVAr, not kvar ... x mult ...; the engine scales kvar with kW` |

### Generator round trip

| What | Why |
|---|---|
| model 7 comes back as model 1 | CIM has no current limit |
| `Xd`, `Xdp`, `Xdpp`, `H` come back at the engine's defaults | `cim18v17` has no machine reactance or inertia. A model 3 machine's admittance depends on `Xdp`, so a deck that sets it solves slightly differently |
| `pf` comes back as `kvar` | `q` carries it |
| a machine without a `kVA` comes back with 1.2 x `kW` written | `ratedS` carries it |

### Generator excerpt

From [`tests/atoms/generator/gens.cimtbl`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/tests/atoms/generator/gens.cimtbl).
`steam` is a model 3 machine with `Vpu=1.02` on a 4.16 kV bus, so its control's target is 4243.2 V. Its row is
copied from the file's `SynchronousMachine` table, with the table's header:

```text
Table SynchronousMachine: mRID, name, node, phases, ratedS (kVA), ratedU (kV), p (kW), q (kVAr), maxQ (kVAr), minQ (kVAr), earthing, normallyInService, BaseVoltage, type=generator, operatingMode=generator, EquipmentContainer=fdr_atom
    # model ConstantPV: a PV bus: a voltage RegulatingControl
    # defaulted: phases=3, pf=0.88, conn=wye, enabled=true
    gen_steam,     steam,     b1, ,  4000.0, 4.16,                -1000.0, -539.7428221380871,  1079.4856442761743, -1079.4856442761743, true,  true, bv_4p16kv

# model 3 (PV bus): the machine regulates its own terminal
Table RegulatingControl: mRID, targetValue, Terminal, mode=voltage, discrete=false, enabled=true, targetDeadband=0
    # derived: targetValue (V) = Vpu=1.02 x ratedU
    gen_steam_ctrl, 4243.2, gen_steam_T1

Update Table SynchronousMachine: mRID, RegulatingControl, controlEnabled=true
    gen_steam, gen_steam_ctrl
```

Round trip two of the atom's generators. `edited` sets `kW=620 kvar=30` and then `kW=50`, and is model 7:

```python
for line in round_trip("generator/gens.dss", schema.Generator):
    if " Generator.steam " in line or " Generator.edited " in line:
        print(line)
```

```text
new Generator.edited phases=3 bus1=b2.1.2.3 kv=0.48 kW=50 kvar=2.41935483870966 model=1 conn=wye kVA=775 enabled=Yes
new Generator.steam phases=3 bus1=b1.1.2.3 kv=4.16 kW=1000 kvar=539.742822138087 model=3 conn=wye Vpu=1.02 maxkvar=1079.48564427617 minkvar=-1079.48564427617 kVA=4000 enabled=Yes
```

## Device shapes

A `yearly` LoadShape on a `PVSystem`, `Storage` or `Generator` is that device's own `EnergyConnectionSchedule`
`<mRID>_yearly`, not a load group. The rows are in the device's `.cimtbl`; the points (`p` and `q` at each sample,
in watts and vars, the load sign) are in the `EnergyConnectionTimePoint` table of the sidecar, with `atTime` the
epoch 2020-01-01T00:00Z plus k x interval for sample k. The sidecar travels as for load shapes, through the
`time_points` dict of `DssImporter` and `DssExporter` (see [LoadShape](loads.md#loadshape)), and the core
[time series guide](https://pnnl-cim-tools.github.io/CIMHub/core/guide/time-points/) describes the table.

The exporter writes one LoadShape per schedule, named after the schedule and shared when name, interval and
multipliers agree. A schedule with uneven points raises (a LoadShape has one interval), and so does a schedule on a
connection written as several DSS objects or with several units: one shape would scale them all by one multiplier,
which CIM does not say.

```python
path = ATOMS / "loadshape/devices.dss"
time_points = {}
DssImporter(path.stem, time_points=time_points).to_cim(DssReader(path).read_all())
rows = time_points["EnergyConnectionTimePoint"].to_pylist()
print(len(rows), [(row["atTime"].isoformat(), round(row["p"], 1)) for row in rows[:3]])

for line in round_trip("loadshape/devices.dss", schema.Loadshape, schema.Pvsystem):
    if " Loadshape.sun" in line or " Pvsystem.p2 " in line:
        print(line)
```

```text
20 [('2020-01-01T00:30:00+00:00', 0.0), ('2020-01-01T01:00:00+00:00', -18000.0), ('2020-01-01T01:30:00+00:00', -54000.0)]
new Loadshape.sun npts=6 mult=[0 0.2 0.6 1 0.5 0] sinterval=1800
new Loadshape.sun_2 npts=6 mult=[0 0.2 0.6 0.816496580927726 0.5 0] sinterval=1800
new Pvsystem.p2 phases=1 bus1=b1.1 kv=2.40177711982884 irrad=1 Pmpp=60 %Pmpp=81.6496580927726 conn=wye kvar=10 kVA=50 %Cutin=0 %Cutout=0 Vminpu=0.9 yearly=sun_2 kvarMax=50 kvarMaxAbs=50 enabled=Yes
```

Two PVs (`p1`, `p2`) name `sun` in the deck. `p2` is cut to fit its 50 kVA, so its multipliers differ and it takes
`sun_2`.
