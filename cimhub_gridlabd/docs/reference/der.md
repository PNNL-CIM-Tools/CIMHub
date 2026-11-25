# Inverters, solar and batteries

This page is the conversion reference for the GridLAB-D classes that inject power through an inverter: `inverter`
with its nested `solar` or `battery`. For each one it says what the importer writes, what the exporter reads back
and what raises. The field classes (copied, mapped, structural, derived, untranscribed) and the conventions every
section follows are on the [reference index](index.md). The getters the exporter reads through, and the sign
rules, are on the core site's
[sources, DER and machines](https://pnnl-cim-tools.github.io/CIMHub/core/reference/der/) page.

| GLM class | CIM classes | `.cimtbl` artifact and shape | Importer | Exporter |
|---|---|---|---|---|
| [`inverter`](#inverter) with a `solar` child | `PowerElectronicsConnection`, `PhotoVoltaicUnit`, and the datasheets `GenerationInverterInfo`, `SolarArrayInfo`, `SolarPanelInfo` | `inverter.cimtbl`, shape `der` | `importer/cimtbl/inverter.py` | `exporter/inverter.py` |
| [`inverter`](#inverter) with a `battery` child | `PowerElectronicsConnection`, `BatteryUnit`, and the datasheets `StorageInverterInfo`, `BatteryInfo` | `inverter.cimtbl`, shape `der` | `importer/cimtbl/inverter.py` | `exporter/inverter.py` |
| [`solar`](#solar) | the `PhotoVoltaicUnit` and its datasheets | in `inverter.cimtbl` | `importer/cimtbl/inverter.py` | `exporter/inverter.py` |
| [`battery`](#battery) | the `BatteryUnit` and its `BatteryInfo` | in `inverter.cimtbl` | `importer/cimtbl/inverter.py` | `exporter/inverter.py` |

All three GLM classes are one artifact, `inverter.cimtbl`: a `solar` or `battery` is the child of its inverter (its
`parent` is the inverter), and GridLAB-D requires a battery's parent to be one. The table shapes are on the core
site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/). Source paths are under
[`cimhub_gridlabd/src/cimhub_gridlabd/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_gridlabd/src/cimhub_gridlabd).
The master imports `inverter.cimtbl` after `capacitor.cimtbl`; it references only buses and its own datasheets.

Quoted error messages leave off the spec code in parentheses that ends some of them. Most start with
the GLM class and name, as `inverter i:`.

The examples run from the repository root with `uv run python`. They convert the public test atom
[`cimhub_gridlabd/tests/atoms/inverter/inverter.glm`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_gridlabd/tests/atoms/inverter/inverter.glm)
to CIM and back. This helper is shared by all of them:

```python
from pathlib import Path

from cimhub_gridlabd.exporter.cim_to_glm import GlmExporter
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.glm_writer import GlmWriter
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim

ATOMS = Path("cimhub_gridlabd/tests/atoms")


def round_trip(atom: str):
    """Import an atom deck to CIM and export it again. Returns the exported GlmModel and the CIM network."""
    network = glm_to_cim(GlmReader(ATOMS / atom).read_all(), name="atom")
    return GlmExporter().to_model(network, name_source="name"), network


def show(model, *names: str) -> None:
    """Print the exported GLM text of the named objects."""
    writer = GlmWriter()
    for name in names:
        print(writer.serialize(model.by_name(name)))
```

`name="atom"` must not be one of the artifact names, or the artifact files collide. `name_source="name"` writes each
object under its CIM `name`, which the importer set to the deck's name. The default is the mRID (`pv_inv_pv1`,
`storage_inv_b3`).

## Sign convention

CIM's terminal sign is the load's: `p` and `q` are positive **into** the equipment. A PV array and a discharging
battery therefore have negative `p`, and a charging battery positive. GLM's `P_Out` and `Q_Out` are in the
generation sign, so the importer writes `p` = minus the output, and the exporter asks the getters for
`sign="generation"`. A battery's `minP` is its charging power, negative in the generation sign, so the importer
writes `minP` = minus `rated_power`. The getters' sign rules are on the core site's
[DER page](https://pnnl-cim-tools.github.io/CIMHub/core/reference/der/).

## inverter

One `PowerElectronicsConnection` per inverter, on its parent's root bus, with its one child as the unit. Its mRID is
`pv_<name>` with a solar and `storage_<name>` with a battery, and the unit is `<connection>_unit`. An inverter with
no child, with more than one, or with a child whose parent is not an inverter raises: GridLAB-D has no hybrid
inverter model. The inverter is `FOUR_QUADRANT`; any other `inverter_type`, and an unset one (which GridLAB-D reads
as a PWM inverter), raise.

**Ratings.** `rated_power` is per phase. The inverter's `phases` give the phases it outputs:

| GLM `phases` | CIM `phases`, `phaseConnection` | Phases out | `ratedU` |
|---|---|---|---|
| `A`, `B`, `C` letters (with `N`) | the letters, `Y` (3 phases: blank, the balanced default) | 1, 2 or 3 | the bus's line-to-line voltage |
| `S` | `s1s2`, `D`: across the legs | 1 | 240 V, the bus's |
| a `D` or any other letter | raises | | |

GridLAB-D has no delta inverter. `ratedS` = `rated_power` x phases out, and `maxQ` = `ratedS`, `minQ` = -`ratedS`:
GridLAB-D's four-quadrant inverter caps the total apparent power at that. `normallyInService` is false when
`generator_status` is `OFFLINE`, and the output is then 0. `V_base` is untranscribed, since `ratedU` is the bus's.
The inverter's datasheet holds the nameplate: `GenerationInverterInfo` under a solar and `StorageInverterInfo` under
a battery, both with `apparentPowerMaximum`, `reactivePowerInjectedMax` and `reactivePowerAbsorbedMax` = `ratedS`,
and on storage `chargeRateActiveMax` = `max_charge_rate`.

**Control modes.** GridLAB-D runs one `four_quadrant_control_mode` per inverter, and the importer maps the one
dispatch each unit has:

| Unit | `four_quadrant_control_mode` | Result |
|---|---|---|
| `solar` | `CONSTANT_PF`, also the default when unset | GridLAB-D's static-weather output (below); a `\|power_factor\|` other than 1 raises, so `q` is 0 |
| `solar` | any other mode | raises |
| `battery` | `CONSTANT_PQ` | the set point `P_Out`, limited as below; `Q_Out` other than 0 or unset raises, so `q` is 0 |
| `battery` | `CONSTANT_PF`, also the default when unset | read as `CONSTANT_PQ`, with a row comment: GridLAB-D never dispatches a `CONSTANT_PF` battery, so a deck that wrote it meant `CONSTANT_PQ`. A `power_factor` it carries goes in the comment |
| `battery` | any other mode | raises |

The row comment of every connection names the capability flag that the mode as read stands for
(`capability: isModeCapableConstantPowerFactor` for a PV, `isModeCapableActivePowerReactivePower` for a battery).
The `InverterCapabilities` object itself is not written yet, because cim-tables cannot reference that kind of row.
The volt-var, volt-watt, frequency-watt, load-following, group and voltage-source modes, and the multipoint
efficiency model, raise. Their slots are untranscribed.

**A solar's output** is GridLAB-D's own static-weather result, with no climate object: a `solar` with a `weather`
or a deck with a `climate` object raises. With the solar's values after defaults:

| Quantity | Formula |
|---|---|
| insolation | `Rated_Insolation` x `shading_factor` (W/ft^2) |
| module temperature, degF | 59 + (`NOCT` - 68) / 74.32 x insolation |
| DC output | `rated_power` x insolation / `Rated_Insolation` x (1 + `Pmax_temp_coeff` x (module temperature - 77)) x `derating` x `soiling` |
| CIM `p` | -min(DC x `inverter_efficiency`, `ratedS`), or 0 when OFFLINE |

The defaults are GridLAB-D's: `panel_type` `SINGLE_CRYSTAL_SILICON`, `NOCT` 118.4, `Rated_Insolation` 92.902 W/ft^2
(1000 W/m^2), `shading_factor` 1, `soiling` and `derating` 0.95, `inverter_efficiency` 0.9 and `power_factor` 1. An
unset `efficiency` and `Pmax_temp_coeff` default by panel type:

| `panel_type` | `efficiency` | `Pmax_temp_coeff` (per degF) |
|---|---|---|
| `SINGLE_CRYSTAL_SILICON` | 0.2 | -0.00437 / 33.8 |
| `MULTI_CRYSTAL_SILICON` | 0.15 | -0.00416 / 33.8 |
| `AMORPHOUS_SILICON` | 0.07 | 0.1745 / 33.8 |
| `THIN_FILM_GA_AS` | 0.3 | 0 |
| `CONCENTRATOR` | 0.15 | 0 |
| any other | 0.1 | 0 |

The written `P_Out` of a solar is an output that GridLAB-D overwrites, so it is not read: the row comment gives it
beside GridLAB-D's DC output and module temperature (an unset `P_Out` shows as `None`).

**A battery's output** is GridLAB-D's `CONSTANT_PQ` limit applied to `P_Out` (generation sign, default 0): 0 when it
asks to charge a full battery (`state_of_charge` at least 1) or to discharge at or below `soc_reserve`, else capped
at `ratedS`. CIM `p` is minus that. The row comment says when the set point was limited. `batteryState` is
`discharging` for `p` below 0, `charging` above 0 and `waiting` at 0.

### inverter properties

| Property | Import | Export |
|---|---|---|
| `name` | `PowerElectronicsConnection.name`; mRID `pv_` or `storage_` + name | the connection's name, or `<connection>_<n>` for each of several units |
| `parent` | `node`: the parent's root bus; a parent that is not a bus object raises | the connection's bus |
| `phases` | `phases`, `phaseConnection` (table above) | the letters then `N`; on a split-phase bus the bus's letter then `S` |
| `inverter_type` | structural: `FOUR_QUADRANT` | `FOUR_QUADRANT` |
| `four_quadrant_control_mode` | structural: the dispatch above | a battery `CONSTANT_PQ`, a PV `CONSTANT_PF` |
| `generator_status` | `normallyInService`: `ONLINE` (default) true, `OFFLINE` false | `OFFLINE` when `normallyInService` is false, else `ONLINE` |
| `rated_power` | `ratedS (VA)` = it x phases out; `maxQ`, `minQ` = +-`ratedS`; the datasheet's `apparentPowerMaximum`; unset or 0 raises | `ratedS` x the unit's share / phases out |
| `inverter_efficiency` | derived into `p` (PV); CIM has no inverter efficiency. Unset, 0 or negative is 0.9, as GridLAB-D runs it | a PV's 1: the losses are in CIM's `p` |
| `P_Out` | derived into `p`: a battery's set point (generation sign); a PV's only in the comment | a battery's `p`, generation sign (`get_inverter_units`) |
| `Q_Out` | a battery: 0 or unset, else raises | a battery's `q`, generation sign |
| `power_factor` | a PV: `\|pf\|` 1, else raises (default 1); a battery: only in the comment | a PV's p / abs(p + jq), negative when q is; 1 at no output |
| `soc_reserve` | `BatteryUnit.minimumE (Wh)` = it x `battery_capacity`; default 0 | a battery's `minimumE` / `ratedE` |
| `max_charge_rate` | `StorageInverterInfo.chargeRateActiveMax (W)`, copied | the `StorageInverterInfo`'s `chargeRateActiveMax` x the unit's share |
| `use_multipoint_efficiency`, `pf_reg` | structural: `FALSE` and `EXCLUDED` (the defaults); another value raises | not written |
| `V_base` | untranscribed: read only by the volt-var and volt-watt modes | not written |
| `generator_mode`, `sense_object`, `max_discharge_rate`, the charge and discharge thresholds and lockout times | untranscribed: read only by load following and the non-four-quadrant types | not written (`max_discharge_rate` has no CIM home) |
| the volt-var, volt-watt, frequency-power, VSI, droop, IEEE 1547 and deltamode slots | untranscribed: dynamics, not the steady-state snapshot | not written |
| solver state (`VA_Out`, `I_In`, `phaseA_I_Out`, ...) | untranscribed: solver output | not written |
| the object header (`groupid`, `latitude`, `longitude`, `in_svc`, `out_svc`, `rank`, `flags`) | untranscribed | not written |

Every inverter slot is classified, and one that is not in a group raises, so a new schema slot is never silently
untranscribed. A value that a deck sets and the importer does not read is listed in the row's `# untranscribed:`
comment, and the defaults it applied in `# defaulted:`.

### inverter fail-fast rules

| Rule | Message |
|---|---|
| `inverter_type` not `FOUR_QUADRANT`, or unset | `inverter i: inverter_type unset (PWM); FOUR_QUADRANT is mapped` |
| `use_multipoint_efficiency TRUE` | `inverter i: use_multipoint_efficiency TRUE; not mapped` |
| `pf_reg` other than `EXCLUDED` | `inverter i: pf_reg INCLUDED; not mapped` |
| a letter other than A, B, C, N or S in `phases` | `inverter i: phases ABCD; A, B, C, N and S are an inverter's` |
| no A, B, C or S in `phases` | `inverter i: phases N; no phase` |
| `rated_power` unset or 0 (GridLAB-D would use 25 kVA) | `inverter i: rated_power unset or 0; GridLAB-D would use 25 kVA per phase (inverter.cpp:1409)` |
| no solar or battery child, or several | `inverter i: has 0 solar or battery children; one is mapped` |
| a solar or battery whose parent is not an inverter | `solar s: parent x is not an inverter; not mapped` |
| a solar not in `CONSTANT_PF` | `inverter i: four_quadrant_control_mode CONSTANT_PQ on a solar; CONSTANT_PF is mapped` |
| a battery in any mode but `CONSTANT_PQ` or `CONSTANT_PF` | `inverter i: four_quadrant_control_mode VOLT_VAR on a battery; CONSTANT_PQ is mapped` |
| `power_factor` with absolute value other than 1 on a solar (the message says `< 1`) | `inverter i: power_factor 0.9; \|pf\| < 1 is not mapped` |
| a non-zero `Q_Out` on a battery | `inverter i: Q_Out 5.0; a non-zero CONSTANT_PQ Q is not mapped` |

### inverter round trip

| What | Why |
|---|---|
| a solar's `P_Out` is not written; its `power_factor` is | the PV is `CONSTANT_PF` and GridLAB-D computes the output |
| a battery comes back at its limited set point | a charging full battery or a discharging battery at its reserve comes back with `P_Out` 0 |
| a `CONSTANT_PF` battery comes back `CONSTANT_PQ` | the importer read it as `CONSTANT_PQ` |
| `rated_power` is per phase again | ratedS over the phases; a split-phase inverter's is the whole |
| a unit that CIM shares with others is its own inverter, `<connection>_<n>` | each of several `PowerElectronicsUnit`s of one connection takes its `maxP` share of `ratedS`, `q` and the charge rate |
| `V_base`, `generator_mode`, `sense_object`, `max_discharge_rate` and the other untranscribed slots are not written | GridLAB-D's defaults |

```python
model, _ = round_trip("inverter/inverter.glm")
show(model, "inv_b3", "b3")
```

```text
object inverter {
  name "inv_b3";
  parent "n2";
  inverter_type "FOUR_QUADRANT";
  four_quadrant_control_mode "CONSTANT_PQ";
  generator_status "ONLINE";
  P_Out 50000;
  Q_Out 0;
  rated_power 33333.333;
  soc_reserve 0.2;
  phases "ABCN";
  max_charge_rate 80000;
}
object battery {
  name "b3";
  parent "inv_b3";
  use_internal_battery_model TRUE;
  battery_type "LI_ION";
  rated_power 100000;
  battery_capacity 200000;
  round_trip_efficiency 0.86;
  state_of_charge 0.6;
}
```

### inverter excerpt

From `cimhub_gridlabd/tests/atoms/inverter/inverter.inverter.cimtbl`, the split-phase PV `inv_pvs` and the
split-phase battery `inv_bpf` (a `CONSTANT_PF` battery, read as `CONSTANT_PQ`):

```
Table PowerElectronicsConnection: mRID, name, node, phases, phaseConnection, ratedS (VA), ratedU (V), p (W), q (VAr), maxQ (VAr), minQ (VAr), normallyInService, AssetDatasheet, BaseVoltage, EquipmentContainer=fdr_atom
    # defaulted: generator_status=ONLINE, Q_Out=0.0
    # four_quadrant_control_mode CONSTANT_PF read as CONSTANT_PQ (a Java export defect: GridLAB-D never dispatches a CONSTANT_PF battery)
    # CONSTANT_PQ: not read: power_factor=-1.0
    # capability: isModeCapableActivePowerReactivePower (InverterCapabilities not written: cim-tables cannot reference an Identity row yet)
    # untranscribed: generator_mode=CONSTANT_PQ, sense_object=tm1
    storage_inv_bpf,   inv_bpf,   tm1, s1s2, D, 5000.0,    240.0,  3000.0,              0.0, 5000.0,    -5000.0,    true,  storage_inv_bpf_info,   bv_240v
    # defaulted: generator_status=ONLINE
    # P_Out as written (GridLAB-D recomputes it): 4000.0 VA; GridLAB-D's: DC 5965.091 W at Tmodule 122.001 degF
    # capability: isModeCapableConstantPowerFactor (InverterCapabilities not written: cim-tables cannot reference an Identity row yet)
    # untranscribed: V_base=208.0
    pv_inv_pvs,        inv_pvs,   tm1, s1s2, D, 5000.0,    240.0,  -5000.0,             0.0, 5000.0,    -5000.0,    true,  pv_inv_pvs_info,        bv_240v
```

Both are `s1s2` `D` at 240 V. The PV's DC output of 5965 W is above `ratedS` (5000 VA), so `p` is capped at -5000 W.
The battery's `P_Out` of -3000 W is a charge of 3000 W, so `p` is +3000.

## solar

Each `solar` is the `PhotoVoltaicUnit` of its inverter, mRID `<connection>_unit`, with an `AssetDatasheet`
that is a `SolarArrayInfo` (`<connection>_array`) holding one `SolarPanelInfo` (`<connection>_panel`). The unit's
`maxP` is `rated_power` and `minP` is 0. The panel's `referenceTemperature` is the 25 degC default (GridLAB-D's 77 degF rating point). `irradiance (W/m^2)` is the static-weather insolation, `Rated_Insolation` x
`shading_factor`, which is the value that goes into the output formula above.

### solar properties

| Property | Import | Export |
|---|---|---|
| `name` | `PhotoVoltaicUnit.name`; mRID `<connection>_unit` | the unit's name |
| `parent` | structural: its inverter; another parent raises | the inverter |
| `rated_power` | `PhotoVoltaicUnit.maxP (W)`, `minP` 0, and the DC output; unset or 0 raises | `maxP`; a `maxP` that is unset raises |
| `Rated_Insolation` | `SolarPanelInfo.referenceIrradiation (W/m^2)`, and the irradiance | `SolarPanelInfo.referenceIrradiation` |
| `shading_factor` | `SolarArrayInfo.shadingFactor (percent)` and the irradiance; default 1 | `SolarArrayInfo.shadingFactor` |
| `efficiency` | `SolarPanelInfo.efficiency (percent)`; default by `panel_type` | `SolarPanelInfo.efficiency` |
| `tilt_angle`, `orientation_azimuth` | `SolarArrayInfo.tiltAngle`, `orientationAzimuth (deg)`; defaults 45 and 180 | the same attributes |
| `NOCT`, `Pmax_temp_coeff`, `panel_type` | derived into `p` (table above) | not written: GridLAB-D's defaults |
| `derating`, `soiling` | derived into `p`; default 0.95; outside 0 to 1 raises | `soiling` 1; `derating` = CIM's `p` over GridLAB-D's lossless output at its defaults: the whole loss |
| `SOLAR_POWER_MODEL`, `orientation` | structural: `DEFAULT`; another value raises | not written |
| `weather` | structural: unset; a climate object raises | not written |
| `area` | structural: raises when set (with `efficiency` it can override `rated_power`) | not written |
| `SOLAR_TILT_MODEL`, `latitude_angle_fix` | untranscribed: read only with a climate object, which raises | not written |
| the PV curve and flat-plate model slots (`pvc_*`, `a_coeff`, ...) | untranscribed: those models raise | not written |
| `Voc`, `V_Max`, `Voc_Max`, `Voc_temp_coeff`, `Rinternal` | untranscribed: CIM has no DC array model | not written |
| `ambient_temperature`, `wind_speed` | untranscribed: with no climate GridLAB-D uses 59 degF and still air | not written |
| `Tmodule`, `Tambient`, `Insolation`, `Tcell`, `P_Out`, `V_Out`, `I_Out` and other solver state | untranscribed: solver output | not written |

### solar fail-fast rules

| Rule | Message |
|---|---|
| `SOLAR_POWER_MODEL` or `orientation` other than `DEFAULT` | `solar s: SOLAR_POWER_MODEL FLATPLATE; DEFAULT is mapped` |
| a climate object, or a `weather` | `solar s: a climate object; only GridLAB-D's static weather is mapped` |
| `area` set | `solar s: area 100.0; not mapped` |
| `rated_power` unset or 0 | `solar s: rated_power unset or 0; not mapped` |
| `derating` or `soiling` outside 0 to 1 | `solar s: derating 1.2 is outside 0..1 (solar.cpp:1023)` |
| export: a `maxP` that is unset | `PhotoVoltaicUnit 'x': maxP unset; GLM's solar needs its rated_power` |
| export: `p` above GridLAB-D's lossless output, or negative | `PhotoVoltaicUnit 'x': p ... W is outside 0..... W, GridLAB-D's lossless output; its derating is 0..1 (solar.cpp:1039)` |

### solar round trip

| What | Why |
|---|---|
| `derating` carries the whole loss and `soiling` and `inverter_efficiency` are 1 | CIM holds the output `p`, not the factors; `derating` = `p` over GridLAB-D's lossless static-weather output, so a re-import gives the same `p` from any origin |
| `panel_type`, `NOCT` and `Pmax_temp_coeff` are not written | CIM holds none of them; the lossless output is taken at GridLAB-D's defaults for them |
| `efficiency`, `Rated_Insolation`, `shading_factor`, `tilt_angle`, `orientation_azimuth` come back as written (or as defaulted) | the datasheets hold them |

```python
model, network = round_trip("inverter/inverter.glm")
show(model, "inv_pv1", "pv1")
```

```text
object inverter {
  name "inv_pv1";
  parent "n5";
  inverter_type "FOUR_QUADRANT";
  four_quadrant_control_mode "CONSTANT_PF";
  generator_status "ONLINE";
  rated_power 10000;
  inverter_efficiency 1;
  power_factor 1;
  phases "AN";
}
object solar {
  name "pv1";
  parent "inv_pv1";
  Rated_Insolation 92.902;
  efficiency 0.2;
  soiling 1;
  derating 0.81225;
  rated_power 8000;
  shading_factor 1;
  tilt_angle 45;
  orientation_azimuth 180;
}
```

The deck's `pv1` has every default, so GridLAB-D's output is 6460.19 W (DC 7177.99 W x 0.9). The exported deck gives
`derating` 0.81225 = 0.9 x 0.95 x 0.95 with the efficiency of 1: it makes GridLAB-D's lossless output of 7953 W come
to the same 6460.19 W.

## battery

Each `battery` is the `BatteryUnit` of its inverter, mRID `<connection>_unit`, with a `BatteryInfo`
(`<connection>_battery`) as its datasheet. GridLAB-D's internal battery model is the only one mapped.

### battery properties

| Property | Import | Export |
|---|---|---|
| `name` | `BatteryUnit.name`; mRID `<connection>_unit` | the unit's name |
| `parent` | structural: its inverter; another parent raises | the inverter |
| `use_internal_battery_model` | structural: true; false raises | `TRUE` |
| `battery_capacity` | `BatteryUnit.ratedE` and `BatteryInfo.ratedCapacity (Wh)`; unset raises | `ratedE` |
| `state_of_charge` | `BatteryUnit.storedE (Wh)` = it x `battery_capacity`; unset raises | `storedE` / `ratedE` |
| `rated_power` | `BatteryUnit.maxP (W)` = it, `minP` = minus it; unset raises | `maxP` |
| `round_trip_efficiency` | `chargingEfficiency` = `dischargingEfficiency` = its square root, in percent; default 0.8 | the product of the two efficiencies |
| `battery_type` | `BatteryInfo.batteryType`: `LI_ION` is `lithiumIon`, `LEAD_ACID` is `leadAcid`; others blank | `BatteryInfo.batteryType`; none: unset. Another kind raises |
| `nominal_voltage` | `BatteryInfo.numberOfCells` = floor(it / 4.1) on `LI_ION`; default 115 V | not written: CIM holds no DC voltage yet |
| `rfb_size` | structural: raises when set (it overrides the battery's ratings) | not written |
| the legacy-model slots (`generator_mode`, `power_type`, `Energy`, `E_Max`, ...) | untranscribed: read only when `use_internal_battery_model` is false, which raises | not written |
| `reserve_state_of_charge` | untranscribed: set from the inverter's `soc_reserve` | not written |
| solver state (`V_Out`, `I_Out`, `VA_Out`, `battery_load`, ...) | untranscribed: solver output | not written |

The square root is GridLAB-D's: it applies the round-trip efficiency once in each direction.

### battery fail-fast rules

| Rule | Message |
|---|---|
| `use_internal_battery_model` false | `battery b: use_internal_battery_model false; the legacy model is not mapped` |
| `rfb_size` set | `battery b: rfb_size 5.0; not mapped` |
| `battery_capacity`, `state_of_charge` or `rated_power` unset | `battery b: battery_capacity unset; not mapped` |
| export: a battery type with no GLM form | `BatteryUnit 'x': batteryType ... has no GLM battery_type` |
| export: a unit that is neither a PV nor a battery | `... 'x': GLM's inverter takes a solar or a battery` |

### battery round trip

| What | Why |
|---|---|
| `nominal_voltage` is not written | CIM holds no DC voltage yet, so GridLAB-D takes its default 115 V; a LI_ION battery's `numberOfCells` of 11 (48 V) comes back as 28 on a second import |
| `battery_type` is unset when the unit has no `BatteryInfo` | GridLAB-D's default type |
| the efficiencies come back as one `round_trip_efficiency` | the product of the charge and discharge efficiencies |
| a battery that was limited comes back at its limit | see the inverter table |

### battery excerpt

From the same golden, the units and the battery datasheets of the atom's `b3` and `bpf` (the `Table BatteryInfo` and
`Table BatteryUnit` of `inverter.inverter.cimtbl`):

```
Table BatteryInfo: mRID, name, batteryType, ratedCapacity (Wh), numberOfCells
    storage_inv_b3_battery,    b3,    lithiumIon, 200000.0, 11
    storage_inv_bpf_battery,   bpf,   lithiumIon, 13500.0,  11

Table BatteryUnit: mRID, name, ratedE (Wh), storedE (Wh), minimumE (Wh), maxP (W), minP (W), chargingEfficiency (percent), dischargingEfficiency (percent), batteryState, AssetDatasheet, PowerElectronicsConnection, EquipmentContainer=fdr_atom
    storage_inv_b3_unit,    b3,    200000.0, 120000.0, 40000.0, 100000.0, -100000.0, 92.73618495495704, 92.73618495495704, discharging, storage_inv_b3_battery,    storage_inv_b3
    storage_inv_bpf_unit,   bpf,   13500.0,  4995.0,   0.0,     5000.0,   -5000.0,   92.73618495495704, 92.73618495495704, charging,    storage_inv_bpf_battery,   storage_inv_bpf
```

`b3` is 200 kWh at 60 % charge (`storedE` 120 kWh) with a reserve of 20 % (`minimumE` 40 kWh), and its
`round_trip_efficiency` of 0.86 is 92.74 % each way. Its `numberOfCells` 11 is floor(48 / 4.1).
