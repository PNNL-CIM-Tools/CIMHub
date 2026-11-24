# Loads, capacitors, players and schedules

This page is the conversion reference for the GridLAB-D classes that draw power or switch a shunt: `load`,
`triplex_load` (with the power of a plain `triplex_node`), `capacitor`, `player` and `schedule`. For each one it says
what the importer writes, what the exporter reads back and what raises. The field classes (copied, mapped,
structural, derived, untranscribed) and the conventions every section follows are on the
[reference index](index.md). The getters the exporter reads through are on the core site's
[loads, shunts and compensators](https://pnnl-cim-tools.github.io/CIMHub/core/reference/loads/) page.

| GLM class | CIM classes | `.cimtbl` artifact and shape | Importer | Exporter |
|---|---|---|---|---|
| [`load`](#load-and-triplex_load) | `EnergyConsumer`, or `ConformLoad` when its base reads a player or schedule; `LoadResponseCharacteristic` | `load.cimtbl`, shape `load` | `importer/cimtbl/load.py` | `exporter/load.py` |
| [`triplex_load`](#load-and-triplex_load) | the same: one consumer for the 120 V legs and one for the 240 V part | `triplex_load.cimtbl`, shape `load` | `importer/cimtbl/load.py` | `exporter/load.py` |
| [`triplex_node`](#load-and-triplex_load) carrying `power_1`, `power_2` or `power_12` | the same | `triplex_node.cimtbl`, shape `load` | `importer/cimtbl/load.py` | written as a `triplex_load` |
| [`capacitor`](#capacitor) | `LinearShuntCompensator`, and a `RegulatingControl` for a `VOLT` control | `capacitor.cimtbl`, shape `shunt` | `importer/cimtbl/capacitor.py` | `exporter/capacitor.py` |
| [`player`](#player) | `ConformLoadGroup`, `ConformLoadSchedule`, and `RegularTimePoint` rows in a Parquet sidecar | `player.cimtbl`, shape `load_schedule` | `importer/cimtbl/player.py` | `exporter/player.py` |
| [`schedule`](#schedule) | `ConformLoadGroup`, one `ConformLoadSchedule` per `Season` and `DayType`, and the sidecar points | `schedule.cimtbl`, shape `load_schedule` | `importer/cimtbl/schedule.py` | `exporter/schedule.py` |

The table shapes are on the core site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/).
Source paths are under
[`cimhub_gridlabd/src/cimhub_gridlabd/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_gridlabd/src/cimhub_gridlabd).
The master imports `player.cimtbl` and `schedule.cimtbl` before the load artifacts, and `capacitor.cimtbl` after
them, so each reference resolves. The points of a player or schedule are not in any artifact: see
[Players and schedules](../guide/time-series.md) and the core site's
[time points](https://pnnl-cim-tools.github.io/CIMHub/core/guide/time-points/) page.

A GLM load or capacitor is itself a bus object, so each one sits on the root bus of its parent chain (a load whose
parent is a meter is on the meter's bus), and its `BaseVoltage` is that bus's.

Quoted error messages leave off the spec code in parentheses that ends some of them. Most start with
the GLM class and name, as `load a:`.

The examples run from the repository root with `uv run python`. They convert the public test atoms in
[`cimhub_gridlabd/tests/atoms`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_gridlabd/tests/atoms) to
CIM and back. This helper is shared by all of them:

```python
from pathlib import Path

from cimhub_gridlabd.exporter.cim_to_glm import GlmExporter
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.glm_writer import GlmWriter
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim

ATOMS = Path("cimhub_gridlabd/tests/atoms")


def round_trip(atom: str):
    """Import an atom deck to CIM and export it again. Returns the exported GlmModel and the time points."""
    time_points = {}
    network = glm_to_cim(GlmReader(ATOMS / atom).read_all(), name="atom", time_points=time_points)
    return GlmExporter(time_points).to_model(network, name_source="name"), time_points


def show(model, *names: str) -> None:
    """Print the exported GLM text of the named objects."""
    writer = GlmWriter()
    for name in names:
        print(writer.serialize(model.by_name(name), model.expressions))
```

The model name (`name="atom"`) must not be one of the artifact names (`load`, `capacitor`, ...), or the artifact
files collide. `name_source="name"` writes each object under its CIM `name`, which the importer set to the deck's
name. The default is the mRID (`ld_ld_delta`, `cap_c_one_A`). The load atoms print a warning that the atom's
`ld_sched` reads a player the deck does not define (see [player](#player)).

## load and triplex_load

One `EnergyConsumer` per GLM load record, mRID `ld_` + the name, on the record's root bus. A record whose base reads
a player or a schedule is a `ConformLoad` of that source's group (see [player](#player) and
[schedule](#schedule)). A `triplex_load` and a plain `triplex_node` that carries `power_1`, `power_2` or `power_12`
are the split-phase case below. On export an `EnergyConsumer`, `ConformLoad` or `NonConformLoad` each becomes a
`load` (or a `triplex_load` on a split-phase bus). CIM gives a load no rated voltage: `p` and `q` are the totals at
nominal voltage, and the exported `nominal_voltage` is the bus's.

**Power per phase.** GLM keeps a load's power per phase, in one of two forms. A phase with `constant_power_X` gives
its `p` + j`q` in the unit written in the deck (`VA`, `kVA`, ...); the importer converts it to the `W` and `VAr` of
the headers. A phase with `base_power_X` is GridLAB-D's split of the base by the ZIP fractions and power factors at
nominal voltage. For each part k (power, current, impedance), with the power factor defaulting to 1:

| Quantity | Value |
|---|---|
| P_k | `base_power_X` x `<k>_fraction_X` x abs(`<k>_pf_X`) |
| Q_k | P_k x sqrt(1 / `<k>_pf_X`^2 - 1), negative when `<k>_pf_X` is negative (leading) |
| pf of 0 | P_k = 0 and Q_k = `base_power_X` x `<k>_fraction_X` |
| fractions that do not sum to 1 | the power fraction becomes 1 - current - impedance, as GridLAB-D does, and the row comment says `defaulted: power_fraction_C=0.4` |

The consumer's `p` and `q` are the sums over its phases. When its phases differ, each phase child gets an
`EnergyConsumerPhase` row with its own `p` and `q` (an `Update Table` row, mRID `ld_<name>_A`). When they are equal,
or there is one child, the consumer's total is the value and no phase rows are written.

**Phases and connection.** A wye load's `phases` are the letters that carry power; the row leaves `phases` blank
when they are `ABC` and equal. It is `Y` and grounded. A load whose `phases` has `D` is delta, `D` and not grounded,
and GridLAB-D reads its `_A`, `_B`, `_C` as the branches AB, BC and CA. So the delta load in the atom, with
`constant_power_C` only, is a consumer on `AC` whose one branch holds all the power. A `load` with `S` in its phases
raises: a split-phase record is a `triplex_load`.

**Voltage response.** One `LoadResponse` per record, from the totals of its parts:

| The record's parts | `EnergyConsumer.LoadResponse` |
|---|---|
| all constant power, or no power | `zip_constant_pq` |
| all constant current | `zip_constant_i` |
| all constant impedance | `zip_constant_z` |
| a mix | a `zip_<pP>_<pI>_<pZ>_<qP>_<qI>_<qZ>` row in the artifact, the fractions of P and of Q over the totals; two sets that round to the same six places raise |

The three shared rows come from the `zip_fractions.cimtbl` that the master imports.

**Split phase.** A `triplex_load` or plain `triplex_node` has legs 1 and 2 (120 V to neutral) and a 240 V part 12.
The legs are one consumer on `s1s2`, `Y`, grounded, with child rows for `s1` and `s2` when they differ. The 240 V
part is a second consumer `ld_<name>_12`, `s1s2`, `D`, not grounded. Only the first consumer of a record has
`customerCount` 1: GLM has no customer count, so each record is counted as one service. A load with no power on any
phase is still a consumer of `p` = `q` = 0 on its wired phases, listed in the artifact's header.

A `load` on the secondary bus of a one-phase service transformer (a `WYE_WYE` or `SINGLE_PHASE` connection on one phase,
rated to its coil, with `secondary_voltage` 0.12 or 0.24 kV) is on that service's split-phase conductors: at 0.12 kV a
consumer on `s1` to neutral, at 0.24 kV a delta consumer across `s1s2`. Only one wye phase of a plain `load` is mapped there; anything else
raises with `phases ... on a s1N service; one wye phase of a load is mapped there` (`s1s2N` for 0.24 kV).

On export a split-phase bus makes a `triplex_load`: a wye consumer is the legs `_1` and `_2`, a delta consumer the
240 V part `_12`. A delta consumer named `<base>_12` on the bus of the wye consumer `<base>` is that record's `_12`
again, so the importer's two consumers come back as one record. A consumer from another model that has only a 240 V
part comes back as a `triplex_load` with `base_power_12`, as the atom's `tn_load` does.

### load properties

| Property | Import | Export |
|---|---|---|
| `name` | `EnergyConsumer.name`; mRID `ld_` + name (`_12` on a 240 V part) | the CIM name or mRID (`name_source`). A 240 V part with a legs consumer `<base>` on its bus is written inside that record; one alone loses its trailing `_12` |
| `parent` | `node`: the root bus | the consumer's bus |
| `phases` | `phases`, `phaseConnection`, `grounded` (see above); `S` on a `load` raises | the letters then `N` (wye) or `D` (delta); on a split-phase bus the bus's letter then `S` |
| `nominal_voltage` | not written: the bus's `BaseVoltage` | the bus's nominal voltage |
| `constant_power_A`, `_B`, `_C` (`_1`, `_2`, `_12` on a `triplex_load`; `power_1`, `power_2`, `power_12` on a `triplex_node`) | `EnergyConsumer.p (W)` and `q (VAr)`, and the phase children | not written: the export always uses the base form |
| `base_power_X` | derived: the split above into `p`, `q`; `<player>.value*K` or `<schedule>*K` is K, with the load a `ConformLoad` | `base_power_X` = the sum of the three parts' absolute values, from `get_phase_loads`; a player or schedule base is written as `<player>.value*K` or `<schedule>*K` |
| `power_fraction_X`, `current_fraction_X`, `impedance_fraction_X` | derived, with `base_power_X`; default 0 | each part's share of the base, from `get_load_response`; a part of zero size is not written |
| `power_pf_X`, `current_pf_X`, `impedance_pf_X` | derived, with `base_power_X`; default 1 | the part's P over its absolute value, negative when its Q is |
| `constant_power_X_real`, `_reac`, `constant_current_X`, `constant_impedance_X` and their `_real`, `_reac` forms | raises when set | not written |
| `constant_current_AN` to `constant_impedance_CA` (the explicit line-to-neutral and line-to-line forms) | raises when set | not written |
| `load_class`, `load_priority` | untranscribed: sorting only | not written |
| `measured_power`, `measured_voltage_*`, `measured_power_*`, `indiv_measured_power_*` | untranscribed: solver output | not written |
| `phase_loss_protection`, `inrush_integration_method_capacitance`, `inrush_integration_method_inductance` | untranscribed: engine options | not written |
| a bus slot of the load (its initial `voltage_X` and the like) | untranscribed: counted once on the table comment | not written |
| `power_A`, `current_A`, `shunt_A`, `current_inj_A` and the like on a `node`, `meter` or other bus | raises: a load on the bus itself | not applicable |
| `current_*`, `shunt_*` on a `triplex_node` | raises | not applicable |

An untranscribed value that a deck sets is listed in a `# untranscribed:` comment on the row, so nothing disappears
silently.

On export a ZIP model is read through `get_load_response`. A voltage-exponent model whose exponents are 0, 1 or 2 is
exactly constant power, current or impedance. Any other exponent raises.

### load fail-fast rules

| Rule | Message |
|---|---|
| `base_power_X` with `constant_power_X` | `load a: base_power_A and constant_power_A are both set; GridLAB-D keeps only the base form (load.cpp:984)` |
| a base that is not `<name>.value*<number>` or `<name>*<number>` | `load a: base_power_A is the expression '5+sin(2)'; only <player>.value*<number> and <schedule>*<number> are mapped` |
| an explicit current, impedance or connection form | `load a: constant_current_A Complex({'real': 10.0, 'imag': 2.0}); not mapped` |
| `S` in the phases of a `load` | `load a: phases ABCS; a split-phase load is a triplex_load` |
| a load on the bus itself | `node x: power_A ... is a load on the bus itself; not mapped` |
| two sources on one record, or a phase with power but no source beside one that has it | `load a: its bases name [...]; a ConformLoad follows one player or schedule` |
| a base naming a schedule the deck does not define | `schedules ['s9'] are read by loads [['a']] but not defined in the deck` |
| two ZIP sets that round alike | `load a: its ZIP fractions (...) differ from another load's beyond the 6 places of zip_...` |
| export: a negative `p` on a part | `EnergyConsumer 'x': a negative p; GLM's base_power holds consumption only` |
| export: a voltage exponent other than 0, 1, 2 | `EnergyConsumer 'x': voltage exponents (...); GLM holds 0, 1 or 2 only` |
| export: a delta load on one phase | `EnergyConsumer 'x': a delta load on one phase` |
| export: a 240 V part that follows another player than its legs | `EnergyConsumer 'x': the 240 V part of 'y' follows another player; a GLM record's bases follow one` |

### load round trip

| What | Why |
|---|---|
| `constant_power_X` comes back as `base_power_X` with `power_fraction_X` 1 and a `power_pf_X` | the export has one form; `base_power_X` is the apparent power at nominal voltage |
| a phase with `0+0j` is not written | a zero part is no part |
| a load on `ABCD` with one branch set comes back on `ACD` | the consumer's phases are the phases that carry power |
| a record that mixes parts on different phases comes back with every phase on the whole load's mix | CIM has one `LoadResponseCharacteristic` per consumer. The atom's `ld_zip` has 100 kVA on A and 50 kVA on C, and comes back as 94.6 kVA and 38.2 kVA with the same fractions on both |
| a `triplex_node` with `power_12` comes back as a `triplex_load` | CIM does not tell them apart |
| `load_class`, `load_priority`, the measured and engine slots are not written | untranscribed |
| `nominal_voltage` is the bus's (2401.777 for the deck's 2401.78) | it follows the `BaseVoltage` |
| `customerCount` is not written | GLM has no customer count |
| a group with no schedule or no points, and a `NonConformLoad`, are written static | a reference to no player would not load; one warning names the groups |

```python
model, _ = round_trip("load/load.glm")
show(model, "ld_delta", "ld_sched")
```

```text
object load {
  name "ld_delta";
  parent "n2";
  phases "ACD";
  nominal_voltage 2401.77711982884;
  base_power_C 227378.539004894;
  power_pf_C 0.747651914485831;
  power_fraction_C 1;
}
object load {
  name "ld_sched";
  parent "n5";
  phases "AN";
  nominal_voltage 2401.77711982884;
  base_power_A 19723.08;
  current_pf_A 0.861934;
  current_fraction_A 1;
}
```

`ld_sched` reads the player `zipsched`, which the deck does not define, so it comes back static.

### load excerpt

From `cimhub_gridlabd/tests/atoms/load/triplex.load.cimtbl` (the load artifact of the load atom):

```
# p, q: the totals at nominal voltage, consumption positive; phases: the phases that carry power, blank when ABC and equal
Table EnergyConsumer: mRID, name, node, phases, phaseConnection, grounded, p (W), q (VAr), customerCount, LoadResponse, BaseVoltage, EquipmentContainer=fdr_atom
    ld_ld_bal,   ld_bal,   n2, ,   Y, true,  300000.0, 150000.0,          1, zip_constant_pq,                                    bv_4p16kv
    ld_ld_delta, ld_delta, n2, AC, D, false, 170000.0, 151000.0,          1, zip_constant_pq,                                    bv_4p16kv
    # untranscribed: load_class=R
    ld_ld_wye,   ld_wye,   n2, AC, Y, true,  20000.0,  7000.0,            1, zip_constant_pq,                                    bv_4p16kv

# the phases differ, so each child carries its own p, q (a delta child is its branch)
Update Table EnergyConsumerPhase: mRID, p (W), q (VAr)
    ld_ld_wye_A, 12000.0, 4000.0
    ld_ld_wye_C, 8000.0,  3000.0
```

`ld_bal` is balanced on `ABC`, so `phases` is blank and it has no phase rows. `ld_delta` is the 170 + 151j kVA
branch written as `constant_power_C`. The triplex part of the same atom is in
`cimhub_gridlabd/tests/atoms/load/triplex.triplex_load.cimtbl`:

```
Table EnergyConsumer: mRID, name, node, phases, phaseConnection, grounded, p (W), q (VAr), customerCount, LoadResponse, BaseVoltage, EquipmentContainer=fdr_atom
    ld_tl_legs,    tl_legs,    tm1, s1s2, Y, true,  4500.0, 1800.0, 1, zip_constant_pq, bv_240v
    ld_tl_legs_12, tl_legs_12, tm1, s1s2, D, false, 4000.0, 1500.0, ,  zip_constant_pq, bv_240v
```

## capacitor

GridLAB-D switches each capacitor phase on its own. Under `control_level INDIVIDUAL`, the default, a `VOLT`
control switches only the phases in `pt_phase`, each on its own phase voltage, and leaves the other phases in their
starting state. The importer follows that: a CIM unit is a set of phases that switch together.

| Capacitor | Units | Control |
|---|---|---|
| `MANUAL` (the default), any `control_level` | one gang unit on the connected phases, mRID `cap_<name>` | none |
| `VOLT`, `BANK` | one gang unit | one `RegulatingControl` `cc_<name>` on the one phase of `pt_phase` |
| `VOLT`, `INDIVIDUAL` | one 1-phase unit per connected phase, `cap_<name>_<phase>` | one `cc_<name>_<phase>` on each unit whose phase is in `pt_phase`; the others stay at their starting state |

So a 3-phase `VOLT` capacitor with `pt_phase B` becomes three 1-phase units and one control, on B. GridLAB-D runs
it that way. A run of the same feeder written as a single gang unit switched on B (what a DSS import of a
DSS-authored deck gives) is a different run: up to two thirds of the bank's kVAr differs whenever B closes. A
cross-format check of a GLM capacitor should compare per-phase switched kVAr against GridLAB-D's own solution.

A unit is wye and grounded, with or without `N` on `phases_connected` (else `phases`): GridLAB-D puts the shunt
phase to ground either way. Each unit carries these values:

| CIM attribute | Value |
|---|---|
| `nomQ (VAr)` | the sum of the unit's `capacitor_X`, in VAr |
| `nomU (V)` | `cap_nominal_voltage` (line to neutral; else the bus's `nominal_voltage`), times sqrt 3 on a 2- or 3-phase unit |
| `bPerSection (S)` | `nomQ` / `nomU`^2, which the shunt getter reads back as Q = b x `nomU`^2 x sections |
| `sections`, `normalSections` | 1 when the phase's `switchX` is `CLOSED`, else 0; an unset switch is `OPEN`, GridLAB-D's default |
| `maximumSections` | 1 |

The control is a `RegulatingControl` of mode `voltage`, discrete and enabled. It monitors the unit's own terminal
(`<unit>_T1`) on the controlled phase, in primary phase-to-neutral volts, with no PT. `voltage_set_low` and
`voltage_set_high` become `targetValue` (their midpoint) and `targetDeadband` (their difference): the unit closes at
or below the low value and opens at or above the high one. The unit's `Update Table` row sets `aVRDelay (s)` to
`dwell_time` + `time_delay` and `controlEnabled` true.

### capacitor properties

| Property | Import | Export |
|---|---|---|
| `name` | `LinearShuntCompensator.name` = name, or `<name>_<phase>` for a 1-phase unit of an `INDIVIDUAL` `VOLT` capacitor; mRID `cap_` + that; control `cc_` + that | the CIM name; the 1-phase units `<base>_<phase>` on one bus are the capacitor `<base>` again |
| `parent` | `node`: the root bus | the unit's bus |
| `phases_connected` (else `phases`) | the unit's phases, `Y`, grounded; `D` raises | `phases` and `phases_connected` are the unit's letters then `N` |
| `nominal_voltage` | not written: the bus's `BaseVoltage` | the bus's |
| `capacitor_A`, `capacitor_B`, `capacitor_C` | `nomQ (VAr)` (the unit's sum) and `bPerSection (S)`; a phase that is not connected is dropped and listed in the row comment | each phase's Q at `nomU` with every section in (`get_shunt_reactive_power`, `sections='maximum'`) |
| `cap_nominal_voltage` | `nomU (V)` (see above); unset with no `nominal_voltage` raises | `nomU` line to neutral: over sqrt 3 on a polyphase unit, rounded to 6 places |
| `switchA`, `switchB`, `switchC` | `sections` and `normalSections`; default `OPEN`; a gang unit's must agree | `CLOSED` when the unit's actual sections are above 0, else `OPEN` |
| `control` | `VOLT`: a `RegulatingControl`; `MANUAL`: none; `VAR`, `VARVOLT`, `CURRENT` raise | `VOLT` for an enabled voltage control, else `MANUAL`; a control of another mode is `MANUAL` at the actual state, with a warning |
| `control_level` | picks the units (table above) | `INDIVIDUAL` for a split capacitor or when every controlled unit is one phase, else `BANK` |
| `pt_phase` | the units that get a control (`INDIVIDUAL`) or the monitored phase (`BANK`); with `D` it raises | the control's monitored phases, else the unit's own |
| `voltage_set_low`, `voltage_set_high` | `RegulatingControl.targetValue`, `targetDeadband` (V); `VOLT` without both raises | target - deadband / 2, target + deadband / 2 |
| `dwell_time`, `time_delay` | `LinearShuntCompensator.aVRDelay (s)` = the sum; both default 0 | `dwell_time` = `aVRDelay` |
| `remote_sense`, `remote_sense_B`, `voltage_deadband`, `VAr_deadband`, `current_deadband` and their `_center` forms | raises when set (a negative deadband is GridLAB-D's unset) | not written |
| `VAr_set_high`, `VAr_set_low`, `current_set_high`, `current_set_low`, `lockout_time` | untranscribed: read only by the unmapped modes | not written |
| `cap_A_switch_count`, `cap_B_switch_count`, `cap_C_switch_count` | untranscribed: solver output | not written |

The importer lists the defaults it applied in a `# defaulted:` comment and the values of unconnected phases in a
`# not connected` comment. For a `MANUAL` capacitor, a `pt_phase` or set points it carries go in a `# MANUAL: not
read` comment.

### capacitor fail-fast rules

| Rule | Message |
|---|---|
| `control` other than `MANUAL` or `VOLT` | `capacitor c: control VAR; MANUAL, VOLT are mapped` |
| a delta `phases_connected` or `pt_phase` | `capacitor c: phases_connected ABCD; a delta capacitor is not mapped` |
| `remote_sense` or a deadband set | `capacitor c: remote_sense ...; not mapped` |
| `VOLT` with no `pt_phase`, or one off the connected phases | `capacitor c: pt_phase unset must name connected phases of ABC` |
| `VOLT` without both voltage set points | `capacitor c: VOLT without voltage_set_low and voltage_set_high` |
| a `BANK` that monitors more than one phase | `capacitor c: a BANK monitors one phase, pt_phase is AB` |
| a gang unit whose switch states differ | `capacitor c: switch states ['CLOSED', 'OPEN'] differ on a gang unit (MANUAL or BANK)` |
| a gang unit whose phases differ in VAr | `capacitor c: phases ABC differ ([1000.0, 2000.0, 1000.0] VAr) on a gang unit; a per-phase rating is not mapped` |
| a connected phase with no `capacitor_X` | `capacitor c: capacitor_B unset or 0 on a connected phase` |
| no `cap_nominal_voltage` and no `nominal_voltage` | `capacitor c: no cap_nominal_voltage and no nominal_voltage` |
| no connected phase | `capacitor c: no phase connected` |
| export: a delta unit | `LinearShuntCompensator 'x': a delta capacitor is not exported yet` |
| export: units of one capacitor at different voltages | `LinearShuntCompensators [...]: rated at [...] V` |
| export: units with different `VOLT` settings | `LinearShuntCompensators [...]: different VOLT settings` |
| export: a voltage control with no deadband | `LinearShuntCompensator 'x': a voltage control without a deadband` |

### capacitor round trip

| What | Why |
|---|---|
| the 1-phase units of an `INDIVIDUAL` capacitor come back as the one capacitor, `VOLT` on the controlled phases | the exporter joins units named `<base>_<phase>` on one bus |
| a `MANUAL` 3-phase capacitor comes back with `phases ABCN` | a unit is wye and grounded with or without `N` |
| `time_delay` comes back inside `dwell_time` | CIM has one delay, `aVRDelay` |
| a `capacitor_X` on a phase that is not connected is not written | GridLAB-D ignores it |
| `nominal_voltage` is the bus's | it follows the `BaseVoltage` |
| a unit with only some of its sections in is `CLOSED` with every section in | GLM has one switch per phase |
| a control with another mode, or a disabled one, is not written | GLM's control has no form for it; the unit is `MANUAL` at its actual state (a control of another mode logs a warning) |
| a delta unit raises on export | GLM's delta capacitor is not mapped either way |
| a lone 1-phase unit named `<base>_<phase>` on that phase loses its suffix | the exporter cannot tell it from a split capacitor's unit: a `MANUAL` capacitor `cap_B` on phase B comes back as `cap` |

```python
model, _ = round_trip("capacitor/capacitor.glm")
show(model, "c_one")
```

```text
object capacitor {
  name "c_one";
  parent "n5";
  phases "AN";
  nominal_voltage 2401.77711982884;
  pt_phase "A";
  phases_connected "AN";
  switchA "CLOSED";
  control "VOLT";
  voltage_set_high 2500;
  voltage_set_low 2350;
  capacitor_A 50000;
  cap_nominal_voltage 2401.78;
  dwell_time 0;
  control_level "INDIVIDUAL";
}
```

### capacitor excerpt

From `cimhub_gridlabd/tests/atoms/capacitor/capacitor.capacitor.cimtbl`:

```
Table LinearShuntCompensator: mRID, name, node, phases, phaseConnection=Y, grounded=true, nomQ (VAr), nomU (V), bPerSection (S), sections, normalSections, maximumSections=1, BaseVoltage, EquipmentContainer=fdr_atom
    # defaulted: time_delay=0.0, dwell_time=0.0, control_level=INDIVIDUAL
    # not connected (GridLAB-D ignores it): capacitor_B=0.05 MVAr, capacitor_C=0.05 MVAr
    cap_c_one_A,  c_one_A,  n5, A, 50000.0,  2401.78,           0.008667693708720822, 1, 1, bv_4p16kv
    cap_c_volt_B, c_volt_B, n2, B, 150000.0, 2401.78,           0.026003081126162467, 0, 0, bv_4p16kv

Table RegulatingControl: mRID, name, mode=voltage, discrete=true, enabled=true, monitoredPhase, targetValue, targetDeadband, Terminal
    cc_c_volt_B, c_volt_B, B, 2425.0, 150.0, cap_c_volt_B_T1

Update Table LinearShuntCompensator: mRID, RegulatingControl, aVRDelay (s), controlEnabled=true
    cap_c_volt_B, cc_c_volt_B, 45.0
```

`c_volt` is a 3-phase `VOLT` capacitor with `pt_phase B`, so only B has a control. The deck gives
`voltage_set_low` 2350 and `voltage_set_high` 2500, so the target is 2425 V and the deadband 150 V.

## player

A load base `<player>.value*K` scales K by the player's value over time. It is read the way GridAPPS-D's run file
declares it: `module tape;`, `class player { double value; }`, then `object player { name zipload; file
zipload.player; }`. One player can drive many loads, so a player is a **group of conform loads** with one regular
schedule of multipliers. Each GLM load whose base names it is a `ConformLoad` of the group, and its `p`, `q` are K
(the base) split as above, not scaled by the player.

| CIM class | mRID | Attributes |
|---|---|---|
| `ConformLoadGroup` | `lg_<player>` | `name` |
| `ConformLoadSchedule` | `ls_<player>` | `name`, `startTime` (the first row's time, with a UTC offset), `timeStep (s)`, `value1Unit` `none`, `ConformLoadGroup` |
| `RegularTimePoint` (sidecar) | the schedule's `uri` | `sequenceNumber` from 0, `value1` |

The points go to the caller's `time_points` dict, not into `player.cimtbl`: pass `time_points={}` to
`GlmImporter` or `glm_to_cim`. Without it the points drop with one warning. A player that a load names but the deck
does not define (the Java exports' run file defines `ieeezipload`, which no deck does) becomes a group with no
schedule and one warning, so the name survives.

On export, a `ConformLoadSchedule` of a group with points is a `player` named after the group, its file
`<name>.player` beside the deck (written by `GlmWriter.write`). The first row is at `startTime` in GMT, which
GridLAB-D reads under any clock zone; each later row is `+<step>s`. Each `ConformLoad` of the group writes its bases
as `<player>.value*K`. The deck's `clock` starts at the earliest player start, so each base is K times the first
point; a later `stoptime` plays the schedule.

### player properties

| Property | Import | Export |
|---|---|---|
| `name` | `ConformLoadGroup.name`, `ConformLoadSchedule.name`; mRIDs `lg_` / `ls_` + name | the group's name |
| `file` | structural: the rows give `startTime`, `timeStep` and the points; unset raises | `<name>.player`, written beside the deck |
| `parent`, `property`, `filetype`, `mode` | structural: must be unset; set raises | not written |
| `loop` | structural: unset or 0; a repeated tape raises | not written |
| `groupid`, `latitude`, `longitude`, `in_svc`, `out_svc`, `rank`, `flags` | untranscribed: object header | not written |
| `all_events_delta` | untranscribed: an engine option | not written |
| a row's time | the first row an absolute `YYYY-MM-DD HH:MM:SS ZONE`, each later one `+N[smhd]` after the row before or absolute | `startTime` as GMT, then `+<step>s` |
| a row's value | `RegularTimePoint.value1` | `value1`; a `value2` other than `value1` raises |

The zones the importer reads are `UTC`, `GMT`, `EST`, `EDT`, `CST`, `CDT`, `MST`, `MDT`, `PST` and `PDT`; each
becomes a fixed offset (`2009-07-21 00:00:00 EDT` is `2009-07-21T00:00:00-04:00`). The one step between rows is the
`timeStep`; a one-row tape has no step.

### player fail-fast rules

| Rule | Message |
|---|---|
| `parent`, `property`, `filetype` or `mode` set | `player zl: parent a; only a player read as zl.value is mapped` |
| `loop` above 0 | `player zl: loop 2; a repeated tape is not mapped` |
| no `file` | `player zl: no file; its rows are the schedule` |
| a file with no rows | `player zl: its file zipload.player has no rows` |
| no `class player { double value; }` in the deck | `player zl: read as zl.value, but the deck has no class player { double value; }` |
| a row time that is not absolute and not `+N[smhd]` | `player zl: row time '...'; an absolute 'YYYY-MM-DD HH:MM:SS ZONE' or +N[smhd] after the first row is mapped` |
| a zone that is not one of the ten above | `player zl: zone XYZ; mapped: UTC, GMT, EST, EDT, CST, CDT, MST, MDT, PST, PDT` |
| steps between rows that differ | `player zl: steps of [60.0, 120.0] s; a ConformLoadSchedule has one step` |
| a row value that is not a number | `player zl: row value 'x' is not a number` |
| a player and a schedule of one name | `['x'] are both a schedule and a player; their load groups would share lg_<name>` |
| export: a `value2` other than `value1` | `ConformLoadSchedule ...: value2 differs from value1; a GLM base scales p and q together` |
| export: a `startTime` with no UTC offset | `ConformLoadSchedule ...: startTime ... has no UTC offset` |
| export: a `timeStep` that is not whole seconds | `ConformLoadSchedule ...: timeStep ... s; a player steps in whole seconds` |

### player round trip

| What | Why |
|---|---|
| the start comes back in GMT (`2009-07-21 04:00:00 GMT` for 00:00 EDT) | the same instant; GridLAB-D reads GMT under any clock zone |
| `+1m` steps come back as `+60s` | CIM holds `timeStep` in seconds |
| a group with no schedule, a schedule with no points and a `NonConformLoad` are written static | one warning names the groups; a reference to no player would not load |

```python
model, time_points = round_trip("player/player.glm")
print(model.tapes)
show(model, "ld_play")
```

```text
{'zipload': [('2009-07-21 04:00:00 GMT', '0.425364'), ('+60s', '0.42153'), ('+60s', '0.418488'), ('+60s', '0.39988')]}
object load {
  name "ld_play";
  parent "n5";
  phases "AN";
  nominal_voltage 2401.77711982884;
  base_power_A zipload.value*19723.08;
  current_pf_A 0.861934;
  current_fraction_A 1;
}
```

### player excerpt

From `cimhub_gridlabd/tests/atoms/player/player.player.cimtbl`:

```
Table ConformLoadGroup: mRID, name
    lg_zipload, zipload

Table ConformLoadSchedule: mRID, name, startTime, timeStep (s), value1Unit, ConformLoadGroup
    # untranscribed: all_events_delta=false
    ls_zipload, zipload, 2009-07-21T00:00:00-04:00, 60.0, none, lg_zipload
```

and its load, from `cimhub_gridlabd/tests/atoms/player/player.load.cimtbl`:

```
Table ConformLoad: mRID, name, node, phases, phaseConnection, grounded, p (W), q (VAr), customerCount, LoadResponse, BaseVoltage, LoadGroup, EquipmentContainer=fdr_atom
    ld_ld_play, ld_play, n5, A, Y, true, 16999.99323672, 10000.005731892072, 1, zip_constant_i, bv_4p16kv, lg_zipload
```

## schedule

A load base `<schedule>*K` scales K by a GridLAB-D `schedule` block, a set of cron rules
`minutes hours days months weekdays [value]`. GridLAB-D reads the ranges as inclusive, months from 1, weekdays from
0 = Sunday, a rule with no value as 1 and a time no rule covers as 0; two rules on one minute fail to load. One
schedule drives many loads, so it is a `ConformLoadGroup` `lg_<schedule>`, and its loads are `ConformLoad`s of it,
as for a player. A schedule recurs by day of the year and week, which CIM's `SeasonDayTypeSchedule` holds, so the
curve is one `ConformLoadSchedule` per `Season` and `DayType`, each a day of multipliers.

| CIM class | mRID | Rule |
|---|---|---|
| `Season` | `season_<first>_<last>` (two-digit months) | a run of consecutive months whose seven weekdays agree; December's run joins January's. `startDate` `--MM-01`, `endDate` the last month's last day (February's 29th) |
| `DayType` | `dt_<name>` | the weekdays that agree within a season, named `all`, `weekday`, `weekend`, `sunday` to `saturday`; another set joins the day names with `_` (`monday_wednesday`) |
| `ConformLoadGroup` | `lg_<schedule>` | `name` |
| `ConformLoadSchedule` | `ls_<schedule>` for a one-day schedule, else `ls_<schedule>_<first>_<last>_<day type>` | `startTime` `00:00:00`, `timeStep (min)` the coarsest step on which the day's value only changes at step boundaries, `value1Unit` `none`, `Season`, `DayType`, `ConformLoadGroup` |
| `RegularTimePoint` (sidecar) | the schedule's `uri` | `sequenceNumber` from 0 (midnight), `value1` |

A day that no rule covers is a schedule of one point of 0. Only the schedules that a load's base reads are mapped;
the others (a house's) are not, and the master's comment counts them (`not mapped: schedule 1`).

On export, a conform group whose schedules each hold a `Season` or `DayType` and have points is a `schedule` block
named after the group, written before the objects. Each day becomes rules: each run of equal values, split at the
hours (`7-59 1`, `* 2-5`, `0-14 6`), on the season's months (`*` for the year, `12,1-2` across December) and the day
type's weekdays. A value of 0 is no rule, which is GridLAB-D's value where none applies. Each `ConformLoad` of the
group writes its bases as `<schedule>*K`.

### schedule properties

| Property | Import | Export |
|---|---|---|
| the block's name | `ConformLoadGroup.name`; mRID `lg_` + name | the group's name |
| a rule's `minutes`, `hours`, `months`, `weekdays` | the day of multipliers per (season, day type), `RegularTimePoint.value1` | the cron fields of each run of equal values |
| a rule's `days` | must be `*`; another day of the month raises | `*` |
| a rule's value | the multiplier; omitted is 1 | the value; 0 is no rule |
| a field | `*`, a number, `a-b` or a comma list of them, inside its range; anything else raises | the same forms |
| a nested block (`weekday { ... }`) | raises | not written |

### schedule fail-fast rules

| Rule | Message |
|---|---|
| a day of the month other than `*` | `schedule s1: rule '0 0 5 * * 1' names days of the month 5; no Season or DayType holds them` |
| two rules on one minute | `schedule s1: two rules cover monday of month 1 at 00:00; GridLAB-D rejects the overlap` |
| a rule with fewer than five or more than six fields | `schedule s1: rule '...'; 'minutes hours days months weekdays [value]' is mapped` |
| a field that is not `*`, a number, a range or a list of them | `schedule s1: rule '...': 'x' is not *, a number, a range or a list of them` |
| a number outside its field's range | `schedule s1: rule '...': 61 is outside 0-59` |
| a value that is not a number | `schedule s1: rule '...': the value 'x' is not a number` |
| a nested block | `schedule s1: a nested block ('...') is not mapped` |
| a base naming a schedule the deck does not define | `schedules ['s9'] are read by loads [['a']] but not defined in the deck` |
| export: a day whose `startTime` is not `00:00:00` | `ConformLoadSchedule ...: startTime ...; a GLM schedule's day starts at 00:00:00` |
| export: a day whose points do not fill 24 h in whole minutes | `ConformLoadSchedule ...: 7 points of 60.0 min; a GLM schedule's day is 1440 whole minutes` |
| export: a season off whole months | `ConformLoadSchedule ...: season ... to ...; a GLM schedule's months are whole` |
| export: a day type that is not `all`, `weekday`, `weekend` or day names joined by `_` | `ConformLoadSchedule ...: day type 'x'; all, weekday, weekend or day names joined by _ are read` |
| export: two days on one month and weekday | `... both cover monday of month 1; a GLM schedule gives one value at a time` |
| export: a `value2` other than `value1` | as for a player |

### schedule round trip

| What | Why |
|---|---|
| the rules come back as written but for spacing, number form and rule order | the exporter rebuilds them from the days |
| a rule of value 0 is not written | GridLAB-D's value where none applies |
| a schedule no load reads is not exported | it was not imported |
| a group one of whose days has no points is written static | one warning names the group |

```python
model, _ = round_trip("schedule/schedule.glm")
print(model.schedules["heat"])
show(model, "ld_zip")
```

```text
['* 6-21 * 3-11 1-5 0.6', '* 0-6 * 12,1-2 1-5 1.2', '* 7-23 * 12,1-2 1-5 0.9', '* * * 12,1-2 0,6 1.1']
object load {
  name "ld_zip";
  parent "n5";
  phases "AN";
  nominal_voltage 2401.77711982884;
  base_power_A zip1*19723.08;
  current_pf_A 0.861934;
  current_fraction_A 1;
}
```

### schedule excerpt

From `cimhub_gridlabd/tests/atoms/schedule/schedule.schedule.cimtbl`:

```
Table Season: mRID, name, startDate, endDate
    season_01_12, 01-12, --01-01, --12-31
    season_03_11, 03-11, --03-01, --11-30
    season_12_02, 12-02, --12-01, --02-29

Table DayType: mRID, name
    dt_all,     all
    dt_weekday, weekday
    dt_weekend, weekend

Table ConformLoadSchedule: mRID, name, startTime, timeStep (min), value1Unit, Season, DayType, ConformLoadGroup
    ls_heat_12_02_weekend, heat, 00:00:00, 1440, none, season_12_02, dt_weekend, lg_heat
    ls_heat_12_02_weekday, heat, 00:00:00, 60,   none, season_12_02, dt_weekday, lg_heat
    ls_zip1,               zip1, 00:00:00, 30,   none, season_01_12, dt_all,     lg_zip1
```

The `heat` schedule in the atom has a winter (`12,1-2`) and the rest of the year, each with weekday and weekend
days, and a summer weekend with no rule, which is a day of one point of 0. `zip1` is one day of 48 half-hour points,
every day of the year.
