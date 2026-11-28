# Loads and shunts

This page is the conversion reference for the RAW tables that draw power or add susceptance at a bus: Load, Fixed
shunt and Switched shunt. For each one it says what the importer writes, what the exporter reads back, what raises
and what comes back different after a round trip. The field classes (copied, mapped, structural, derived,
untranscribed) and the conventions every section follows are on the [reference index](index.md). The getters the
exporter reads through are on the core site's
[loads, shunts and compensators](https://pnnl-cim-tools.github.io/CIMHub/core/reference/loads/) page.

| RAW table | CIM classes | `.cimtbl` artifact and shape | Importer | Exporter |
|---|---|---|---|---|
| [Load](#load) | `ConformLoad` or `NonConformLoad`, `LoadResponseCharacteristic`, and the `LoadArea`, `SubLoadArea` and load group that hold them | `load.cimtbl`, shape `load` with `bus` in place of `node` | `importer/cimtbl/load.py` | `exporter/load.py` |
| [Fixed shunt](#fixed-shunt) | `LinearShuntCompensator`, one section | `fixed_shunt.cimtbl`, shape `shunt` with `bus`, no control | `importer/cimtbl/fixed_shunt.py` | `exporter/fixed_shunt.py` |
| [Switched shunt](#switched-shunt) | one `LinearShuntCompensator` per block, and one `RegulatingControl` for the record | `switched_shunt.cimtbl`, shape `shunt` with `bus` | `importer/cimtbl/switched_shunt.py` | `exporter/switched_shunt.py` |

The table shapes are on the core site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/).
Source paths are under
[`cimhub_raw/src/cimhub_raw/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_raw/src/cimhub_raw).
The master imports `load.cimtbl` and `fixed_shunt.cimtbl` after the branch tables, and `switched_shunt.cimtbl` after
the generator and FACTS device artifacts, because a switched shunt's control can regulate a machine or a FACTS
device (see [Generators](generators.md) and [DC lines and FACTS devices](dc.md)). A bus's `BaseVoltage` and
substation come from the bus tables ([Case, buses, areas and zones](buses.md) and
[Substations and node-breaker data](substations.md)).

Quoted error messages start with the record, as `load 1_1:` or `switched shunt 1:`. The key of a load or shunt is its
bus number and ID, and the name the importer gives it is `<I>_<ID>`. A switched shunt has no ID in RAW v34, so its
key is its bus number.

The examples run from the repository root with `UV_FROZEN=1 uv run python`. They convert the public test atoms in
[`cimhub_raw/tests/atoms`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_raw/tests/atoms) to CIM and
back. Every RAW line printed below is an exported record as the writer formats it.

## Load

One `ConformLoad` or `NonConformLoad` per RAW load, mRID `ld_<I>_<ID>`, on bus I, in the substation of bus I and on
its `BaseVoltage`. A v34 load has no NAME, so the name is `<I>_<ID>`. `p` and `q` are the load at 1 pu voltage, CIM's
nominal voltage, and the ZIP split is a `LoadResponseCharacteristic` shared by every load with the same split.

**Power.** RAW gives each load three parts: constant power (PL, QL), constant current (IP, IQ) and constant
admittance (YP, YQ), all in MW and MVAr at 1 pu voltage. The importer sums them:

| CIM value | Formula |
|---|---|
| `p (MW)` | PL + IP + YP |
| `q (MVAr)` | QL + IQ - YQ |

YQ enters with a minus sign because RAW writes the reactive part of a constant admittance as a negative number for
an inductive load.

**ZIP response.** The `LoadResponseCharacteristic` has `exponentModel` false and the six fractions of the sums:

| Side | Constant power | Constant current | Constant admittance |
|---|---|---|---|
| p | PL / p | IP / p | YP / p |
| q | QL / q | IQ / q | -YQ / q |

- Each distinct set of six fractions is one shared row, mRID `zip_` plus the fractions (`zip_0_1_0_0_0_1`,
  `zip_0.5_0.3_0.2_0.25_0.25_0.5`), written before the loads. A plain constant power load is `zip_1_0_0_1_0_0`.
- A side whose components are all 0 counts as constant power: its fractions are 1, 0, 0.
- A side whose nonzero components add to 0 raises, because its fractions would be undefined.

**Class from SCALE.** SCALE 1, the default, is a `ConformLoad` in a `ConformLoadGroup`. SCALE 0, a load that is not
scaled, is a `NonConformLoad` in a `NonConformLoadGroup`. Any other SCALE raises.

**Area and zone.** The load's own AREA and ZONE pick its group, so a load assigned to a different area or zone than
its bus keeps both. The hierarchy has one row per area and one per (area, zone) pair that has loads:

| CIM class | mRID | Holds |
|---|---|---|
| `LoadArea` | `la_<AREA>` | one per area with loads; its `ControlArea` is `ca_<AREA>` |
| `SubLoadArea` | `sla_<AREA>_<ZONE>` | one per area and zone pair, in its `LoadArea` |
| `ConformLoadGroup` | `clg_<AREA>_<ZONE>` | the SCALE 1 loads of the pair |
| `NonConformLoadGroup` | `nclg_<AREA>_<ZONE>` | the SCALE 0 loads of the pair |

A blank AREA or ZONE is the bus's, and the row's comment says so (`# defaulted: area=2, zone=2`). An AREA with no
Area interchange record raises. CIM has no link from a `SubLoadArea` to a zone, so the exporter reads a load's ZONE
from its bus's substation region. A load whose ZONE differs from its bus's therefore keeps its group but loses the
zone on the way back, and its row says `# untranscribed: zone=2 (bus 2 is in zone 1)`.

**Status.** `inService` is true for STATUS 1 and false for STATUS 0. A blank STATUS is 1. Any other value raises.

### Load fields

| RAW field | Import | Export |
|---|---|---|
| I | structural: `bus`, `BaseVoltage`, `EquipmentContainer` of bus I | the bus number of the load's terminal |
| ID | structural: key `ld_<I>_<ID>`, name `<I>_<ID>`; blank is 1 | the ID in the mRID `ld_<I>_<ID>`, else the next free `1`, `2`, ... on the bus |
| STATUS | mapped: `inService`; blank is 1 | 0 when `inService` is false, else 1 |
| AREA | structural: the group's `LoadArea` and `ControlArea`; blank is the bus's | the area number of the load's group (`LoadGroup`, `SubLoadArea`, `LoadArea`, `ControlArea`); blank for a load with no group |
| ZONE | structural: the group's `SubLoadArea`; blank is the bus's | the zone of the bus's substation region |
| PL, QL | derived: part of `p (MW)`, `q (MVAr)` and of `pConstantPower`, `qConstantPower` | `p`, `q` times the constant power fractions |
| IP, IQ | derived: part of `p (MW)`, `q (MVAr)` and of `pConstantCurrent`, `qConstantCurrent` | `p`, `q` times the constant current fractions |
| YP, YQ | derived: part of `p (MW)`, `q (MVAr)` and of `pConstantImpedance`, `qConstantImpedance`; YQ enters `q` as -YQ | `p` times the constant impedance fraction; YQ is minus `q` times it |
| SCALE | mapped: `ConformLoad` (1) or `NonConformLoad` (0); blank is 1 | 1 for a `ConformLoad`, 0 for a `NonConformLoad`, blank for a plain `EnergyConsumer` |
| OWNER, INTRPT, DGENP, DGENQ, DGENM | untranscribed | not exported |

### Load fail-fast rules

| Rule | Message |
|---|---|
| an AREA with no Area interchange record | `load 1_1: AREA 9 has no area-interchange record (no ControlArea ca_9)` |
| a SCALE or STATUS other than 0 or 1 | `load 1_1: scale=2 has no mapping (known: 0, 1)` |
| a side of the ZIP split whose parts cancel | `load 1_1: the q components (5.0, 0.0, -5.0) cancel to 0; their ZIP fractions are undefined` |
| export: an exponent response (`exponentModel` true) | `ConformLoad 'x': an exponent load response; a RAW load is ZIP only` |
| export: a load group whose chain stops before the `ControlArea` | `ConformLoad 'x': its ConformLoadGroup 'y' reaches no ControlArea through SubLoadArea -> LoadArea` |
| export: a load with no `LoadResponse` | `ConformLoad 'x': has no LoadResponse` |
| export: ZIP fractions that do not add to 1 | `LoadResponseCharacteristic 'z': the p fractions [0.5, 0.3, 0.3] do not sum to 1` |

### Load round trip

| What | Why |
|---|---|
| PL to YQ of a mixed load can differ in the last digit | the exporter multiplies `p` and `q` by the fractions: relative error 1e-9 |
| a blank AREA or ZONE comes back filled | the importer gave the load its bus's area and zone, and the exporter writes the group's area and the bus's zone |
| a ZONE other than the bus's comes back as the bus's | a `SubLoadArea` has no link to a zone |
| a blank SCALE comes back 1 | the importer defaulted it |
| OWNER, INTRPT, DGENP, DGENQ, DGENM come back blank | no CIM home |
| a side with all parts 0 comes back as constant power 0 | its fractions were 1, 0, 0 |

This example converts the load atom, prints each `ConformLoad`'s totals and the fractions of its p side, and exports
the case again.

```python
import cimprofiles.cim18.cim18v17 as cim

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.getters.load import get_load_response, get_phase_loads
from cimhub_raw.exporter.cim_to_raw import RawExporter
from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader
from cimhub_raw.raw34_writer import Raw34Writer

case = Raw34Reader("cimhub_raw/tests/atoms/load/loads.raw").read_all()
network = raw_to_cim(case, name="atom")

for load in network.graph[cim.ConformLoad].values():
    total = get_phase_loads(load, "MW", "MVAr").total
    response = get_load_response(load)
    print(load.mRID, total.p, total.q, response.p_power, response.p_current, response.p_impedance)

writer = Raw34Writer()
for record in RawExporter().to_model(network).list_by_class(schema.LoadRecord):
    print(writer.serialize(record))
```

```text
ld_1_1 10.0 5.0 1.0 0.0 0.0
ld_1_2 10.0 4.0 0.5 0.3 0.2
ld_2_A 7.0 2.0 0.0 1.0 0.0
ld_3_1 25.0 10.0 1.0 0.0 0.0
1,'1 ',1,1,1,10.000,5.000,0.000,0.000,0.000,0.000,,1
1,'2 ',1,1,1,5.000,1.000,3.000,1.000,2.000,-2.000,,1
2,'1 ',0,1,1,0.000,0.000,0.000,0.000,4.000,0.000,,0
2,'A ',1,2,1,0.000,0.000,7.000,2.000,0.000,0.000,,1
3,'1 ',1,2,2,25.000,10.000,0.000,0.000,0.000,0.000,,1
```

The atom's load `2 A` is the constant current load written with AREA 2 and ZONE 2 on a bus in zone 1; it comes back
with ZONE 1. Load `3 1` was written with only PL and QL, and comes back with AREA 2, ZONE 2 and the zero parts
filled. The out-of-service load `2 1` is the `NonConformLoad`, so it is not in the `ConformLoad` lines.

### Load excerpt

From `cimhub_raw/tests/goldens/IEEE14/load.cimtbl`, the artifact of the IEEE 14 bus case. Every load is constant
power and in one area and zone, so the hierarchy is one row each:

```
Table LoadArea: mRID, name, ControlArea
    la_1, 1, ca_1

Table SubLoadArea: mRID, name, LoadArea
    sla_1_1, 1_1, la_1

Table ConformLoadGroup: mRID, name, SubLoadArea
    clg_1_1, 1_1, sla_1_1

# ZIP fractions: PL, IP, YP over p; QL, IQ, -YQ over q (zip_mix)
Table LoadResponseCharacteristic: mRID, exponentModel, pConstantPower, pConstantCurrent, pConstantImpedance, qConstantPower, qConstantCurrent, qConstantImpedance
    zip_1_0_0_1_0_0, false, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0

# untranscribed: owner, interruptible, dgenp, dgenq, dgenf
Table ConformLoad: mRID, name, bus, p (MW), q (MVAr), inService, LoadResponse, LoadGroup, BaseVoltage, EquipmentContainer
    ld_2_1,  2_1,  2,  21.7, 12.7, true, zip_1_0_0_1_0_0, clg_1_1, bv_138kv, sub_2
    ld_3_1,  3_1,  3,  94.2, 19.0, true, zip_1_0_0_1_0_0, clg_1_1, bv_138kv, sub_3
    ...
```

No golden has a mixed load or a fixed load. From the artifact the importer writes for the atom
`cimhub_raw/tests/atoms/load/loads.raw` (the mixed load `1 2`, the fixed load `2 1`, and the load `2 A` that is in
another area and zone than its bus):

```
Table NonConformLoadGroup: mRID, name, SubLoadArea
    nclg_1_1, 1_1, sla_1_1

Table LoadResponseCharacteristic: mRID, exponentModel, pConstantPower, pConstantCurrent, pConstantImpedance, qConstantPower, qConstantCurrent, qConstantImpedance
    zip_0.5_0.3_0.2_0.25_0.25_0.5, false, 0.5, 0.3, 0.2, 0.25, 0.25, 0.5
    ...

Table ConformLoad: mRID, name, bus, p (MW), q (MVAr), inService, LoadResponse, LoadGroup, BaseVoltage, EquipmentContainer
    ld_1_2, 1_2, 1, 10.0, 4.0, true, zip_0.5_0.3_0.2_0.25_0.25_0.5, clg_1_1, bv_69kv, sub_1
    # untranscribed: zone=2 (bus 2 is in zone 1)
    ld_2_A, 2_A, 2, 7.0,  2.0, true, zip_0_1_0_0_1_0,               clg_2_2, bv_69kv, sub_2

Table NonConformLoad: mRID, name, bus, p (MW), q (MVAr), inService, LoadResponse, LoadGroup, BaseVoltage, EquipmentContainer
    ld_2_1, 2_1, 2, 4.0, 0.0, false, zip_0_0_1_1_0_0, nclg_1_1, bv_69kv, sub_2
```

## Fixed shunt

One `LinearShuntCompensator` per RAW fixed shunt, mRID `cap_<I>_<ID>`, name `<I>_<ID>`, on bus I in its substation.
It has one section, always in: `maximumSections`, `normalSections` and `sections` are all 1. GL and BL are MW and
MVAr at 1 pu voltage, so the importer writes them as admittances in per unit on the system base, `gPerSection (pu
system)` = GL / SBASE and `bPerSection (pu system)` = BL / SBASE, and `nomU (kV)` is the bus's BASKV. cimtables turns
them into siemens on those two bases. BL above 0 is a capacitor in RAW and in CIM, so its sign is unchanged. A shunt
with a negative BL is a reactor.

### Fixed shunt fields

| RAW field | Import | Export |
|---|---|---|
| I | structural: `bus`, `nomU (kV)` = BASKV, `BaseVoltage`, `EquipmentContainer` | the bus number of the shunt's terminal |
| ID | structural: key `cap_<I>_<ID>`, name `<I>_<ID>`; the ID is trimmed | the ID in the mRID `cap_<I>_<ID>`, else the next free `1`, `2`, ... on the bus |
| STATUS | mapped: `inService`; blank is 1 | 0 when `inService` is false, else 1 |
| GL | derived: `gPerSection (pu system)` = GL / SBASE; blank is 0 | the shunt's g in pu on its bus base times SBASE, over the sections in service; an unset g is 0 |
| BL | derived: `bPerSection (pu system)` = BL / SBASE; blank is 0 | the shunt's b, as GL |

A `LinearShuntCompensator` with no `RegulatingControl` is a fixed shunt, unless it is a line shunt of an exported
branch: those go back in the branch's GI, BI, GJ and BJ (see [Branches, switches and multi-section
lines](branches.md)). A shunt with a control is a block of a [switched shunt](#switched-shunt).

### Fixed shunt fail-fast rules

| Rule | Message |
|---|---|
| a STATUS other than 0 or 1 | `fixed shunt 1_1: status=2 has no mapping (known: 0, 1)` |
| export: `nomU` is not the shunt's `BaseVoltage` | `LinearShuntCompensator 'x': nomU 230.0 kV is not its BaseVoltage 115.0 kV; RAW states a shunt at 1 pu of its bus voltage` |
| export: a `NonlinearShuntCompensator` | `no RAW export yet for {'NonlinearShuntCompensator': 1}` |

### Fixed shunt round trip

GL and BL come back as written, up to the last digit of the per-unit round trip. The fixed shunt atom's two shunts, `1 1` (GL + jBL = 1.5 + j20) and `1 2` (a
reactor out of service), come back unchanged.

### Fixed shunt excerpt

From `cimhub_raw/tests/goldens/IEEE14/fixed_shunt.cimtbl`:

```
Table LinearShuntCompensator: mRID, name, bus, gPerSection (pu system), bPerSection (pu system), nomU (kV), maximumSections, normalSections, sections, inService, BaseVoltage, EquipmentContainer
    cap_9_1, 9_1, 9, 0.0, 0.19, 138.0, 1, 1, 1, true, bv_138kv, sub_4
```

BL 19.0 Mvar on SBASE 100 is `bPerSection` 0.19.

## Switched shunt

One RAW switched shunt is a bus's whole set of switched banks under one controller: up to eight blocks, each Ni
identical steps of Bi Mvar, and a mode MODSW that says what controls them. The importer writes one
`LinearShuntCompensator` per block, all naming one `RegulatingControl`. The control is written first and the blocks
second. A locked shunt (MODSW 0) still has its control, disabled, so its blocks stay grouped. The mRIDs are
`swsh_<I>_b<k>` for block k in input order and `cc_<I>` for the control.

**Blocks.** The blocks run up to the first Ni or Bi that is 0 or blank, which is RAW's end of the list. For each:

| CIM attribute | Value |
|---|---|
| `maximumSections` | Ni |
| `bPerSection (pu system)` | Bi / SBASE, with `nomU (kV)` = the BASKV of bus I; a negative Bi is a reactor block |
| `sections` | the block's share of BINIT, below |
| `inService` | STATUS == 1, the same on every block |
| `controlEnabled` | the control's `enabled` |

A block after the first zero raises, and so does a record with no blocks at all. The block slots are never defaulted,
because a missing Ni or Bi is the end of the list, not a value.

**Sections.** RAW gives only the total in service, BINIT in Mvar at 1 pu voltage. The importer splits it in RAW's
switching order (ADJM 0): a negative BINIT fills the reactor blocks in input order and a positive one the capacitor
blocks. Each block takes up to its Ni steps, and the block where BINIT runs out takes the rest as a fraction of a step
(CIM allows a non-integer `sections`). A BINIT beyond the blocks' total raises. `normalSections` is not written. ADJM
is untranscribed; the order is kept by the `_b<k>` suffix.

**Control.** MODSW sets the control's mode:

| MODSW | `RegulatingControl` | Regulates |
|---|---|---|
| 0 locked | `mode` voltage, `enabled` false, `discrete` blank, and every block `controlEnabled` false; the target is VSWHI and VSWLO as read, unused | bus SWREG |
| 1 discrete, voltage | `mode` voltage, `discrete` true | bus SWREG |
| 2 continuous, voltage | `mode` voltage, `discrete` false | bus SWREG |
| 3 discrete, plant reactive power | `mode` reactivePower, `discrete` true | the one machine of the plant at SWREG |
| 6 discrete, FACTS shunt reactive power | `mode` reactivePower, `discrete` true | the FACTS device named by RMIDNT |
| 4 (a VSC converter's reactive power), 5 (another shunt's admittance) | raise `NotImplementedError` | |
| any other value | raises | |

*Regulated bus (MODSW 0, 1, 2).* The control's `Terminal` is the busbar terminal `bb_<SWREG>_T1`, or `bb_<I>_T1`
when SWREG is 0. An NREG other than 0 names a node of the regulated bus, and the terminal is that node's busbar
(see [Substations and node-breaker data](substations.md)). A SWREG that is no bus raises, in every mode, MODSW 6 included.

*Voltage target.* `targetValue` is the middle of the band, (VSWHI + VSWLO) / 2 times the regulated bus's BASKV, in
volts. `targetDeadband` is the whole band, (VSWHI - VSWLO) times BASKV, in volts. The subtraction can leave a
last-digit residue: 1.04 - 0.98 gives `6900.0000000000055`. The value is written as computed.

*Plant reactive power (MODSW 3).* VSWLO and VSWHI are fractions of the range QB to QT of the plant's machine at SWREG
(or at bus I when SWREG is 0). The band runs from QB + VSWLO x (QT - QB) to QB + VSWHI x (QT - QB) Mvar, using the
machine's limits as written and ignoring its status. The control's `Terminal` is the machine's own terminal,
`sm_<I>_<ID>_T1` or `pec_<I>_<ID>_T1`, where PSS/E measures the machine's reactive power. `targetValue` is minus
the midpoint of the band and `targetDeadband` its width, both in VAr: a terminal's `q` follows the load sign, so
a machine's `q` is minus QG. A plant of several machines at SWREG raises, because one terminal measures one
machine. With no machine at SWREG the control is written disabled, with no target, on the busbar terminal
`bb_<SWREG>_T1`, and a VSWLO or VSWHI off its default is listed on the row (`# untranscribed: vswlo=0.0`).

*FACTS reactive power (MODSW 6).* The same band over -SHMX to +SHMX of the FACTS device named by RMIDNT, on the device's
terminal `fd_<RMIDNT>_T1`. SWREG is not used. An RMIDNT that names no FACTS device raises, and so does a device with a
series element (see [DC lines and FACTS devices](dc.md)).

### Switched shunt fields

| RAW field | Import | Export |
|---|---|---|
| I | structural: the key; every block's `bus`, `nomU (kV)` = BASKV, `BaseVoltage`, `EquipmentContainer` | the bus number of the blocks' terminals; all blocks of one control must be on one bus, and two controls on one bus raise |
| MODSW | mapped: the control's `mode`, `discrete` and `enabled`, as in the table above; blank is 1 | from the control (the blocks' `controlEnabled` must agree): voltage and locked (`enabled` false, or every block's `controlEnabled` false) 0, voltage with `discrete` true or unset 1, voltage with `discrete` false 2; reactive power on a FACTS device 6; reactive power on a machine, or on anything else when locked, 3; any other mode raises |
| ADJM | untranscribed | not written |
| STATUS | mapped: `inService` of every block; blank is 1 | 0 when the blocks are out of service; blocks in and out of service on one control raise |
| VSWHI, VSWLO | derived: the control's `targetValue` and `targetDeadband`: volts for MODSW 0 to 2, VAr for MODSW 3 and 6; blank is 1.0 | the band's top and bottom from the control's target plus or minus half its deadband: kV over the regulated bus's BASKV for voltage, fractions of the machine's `minQ` to `maxQ` or of the device's -SHMX to SHMX for MODSW 3 and 6; blank for a disabled control with no target. A machine with the same `minQ` and `maxQ` raises |
| SWREG | structural: the control's `Terminal`, as above; MODSW 3: the plant's bus; MODSW 6: not used, but a nonzero SWREG must still be a bus; blank is 0 | the bus number of the control's terminal, its own bus included; blank for MODSW 6 |
| RMIDNT | structural: MODSW 6: the FACTS device | MODSW 6: the name of the FACTS device at the control's terminal; else blank |
| BINIT | derived: split into the blocks' `sections` | the sum over the blocks of `sections` times Bi |
| N1 to N8 | structural: `maximumSections` of block k | the blocks in the order of the mRID `swsh_<I>_b<k>`, else reactors first, then capacitors, each by mRID; more than 8 raise; a `maximumSections` below 1 raises |
| B1 to B8 | structural: `bPerSection (pu system)` = Bi / SBASE | the block's b per section in pu on its bus base times SBASE; a block with g other than 0 raises |
| NREG | structural: a node of the regulated bus, as above; blank is 0 | not written |
| RMPCT | untranscribed: CIM 18 has no participation share for a shunt | not written |

### Switched shunt fail-fast rules

| Rule | Message |
|---|---|
| MODSW 4 or 5 | `switched shunt 1: MODSW 4 (VSC converter reactive power: no case has one yet)` |
| any other MODSW | `switched shunt 1: modsw=9 has no mapping (known: 0, 1, 2, 3, 6)` |
| a block after the first zero Ni or Bi | `switched shunt 1: a block after the first zero Ni or Bi (block 2): [(2, -15.0), (0, 0.0), (2, 5.0), ...]` |
| no block at all | `switched shunt 1: no blocks (N1, B1 = (0, 0.0))` |
| BINIT beyond the blocks' total | `switched shunt switched shunt 1: BINIT=500.0 is beyond its blocks [(2, -15.0), (3, 10.0), (2, 25.0)]` |
| a SWREG that is no bus | `switched shunt 1: SWREG 999 is no bus` |
| MODSW 3 with several machines at SWREG | `switched shunt 2: the plant at bus 1 has 2 machines; one terminal measures one machine (no case)` |
| MODSW 6 naming no FACTS device | `switched shunt 5: RMIDNT 'NOPE' names no FACTS device` |
| export: the blocks of one control with different `controlEnabled` | `RegulatingControl 'x': its blocks' controlEnabled disagree` |
| export: blocks in and out of service on one control | `RegulatingControl 'x': its blocks are in and out of service; a switched shunt has one status` |
| export: a block with `gPerSection` set, or a `maximumSections` below 1 | `LinearShuntCompensator 'x': gPerSection is set; a switched shunt block has no G` |
| export: blocks of one control on two buses | `RegulatingControl 'x': controls shunts on buses [(1,), (2,)]; a switched shunt is on one` |
| export: two controls on one bus | `bus 1: RegulatingControl 'x' and RegulatingControl 'y' both control switched shunts; a v34 switched shunt's key is its bus` |
| export: more than 8 blocks | `RegulatingControl 'x': controls 9 shunts; a switched shunt has 8 blocks` |
| export: a control mode other than voltage or reactive power, or reactive power on equipment that is neither a machine nor a FACTS device | `RegulatingControl 'x': reactive power of ...; MODSW 3 regulates a plant's machine and 6 a FACTS device` |

### Switched shunt round trip

| What | Why |
|---|---|
| SWREG 0 comes back as the bus's own number | CIM keeps the terminal, not whether RAW wrote 0 or I |
| VSWHI and VSWLO, Bi and BINIT can differ in the last digit | the importer converts through volts or per unit and the exporter converts back (`10.000000000000002` for 10); relative error 1e-9 |
| ADJM and RMPCT come back blank | no CIM home |
| NREG comes back blank | not written; a control on a substation node is exported against its bus |
| a MODSW 3 shunt with no plant comes back with VSWHI and VSWLO blank | its control has no target; PSS/E reads blank as 1.0 |
| BINIT can differ in the last digit | the exporter adds up sections times Bi, which inverts the split |

This example converts the switched shunt atom and prints each block's state, each control's target and deadband in
kV, and the exported records:

```python
import cimprofiles.cim18.cim18v17 as cim

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.getters.control import get_regulating_control
from cimhub_raw.exporter.cim_to_raw import RawExporter
from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader
from cimhub_raw.raw34_writer import Raw34Writer

case = Raw34Reader("cimhub_raw/tests/atoms/shunt/switched_shunts.raw").read_all()
network = raw_to_cim(case, name="atom")

for block in network.graph[cim.LinearShuntCompensator].values():
    control = block.RegulatingControl
    print(block.mRID, block.sections, block.maximumSections, control.mRID, control.mode.name, control.enabled)

for control in network.graph[cim.RegulatingControl].values():
    settings = get_regulating_control(control, "kV")
    print(control.mRID, settings.target, settings.deadband)

writer = Raw34Writer()
for record in RawExporter().to_model(network).list_by_class(schema.SwitchedShuntRecord):
    print(writer.serialize(record))
```

```text
swsh_1_b1 1.0 2 cc_1 voltage True
swsh_1_b2 0.0 3 cc_1 voltage True
swsh_1_b3 0.0 2 cc_1 voltage True
swsh_2_b1 2.5 4 cc_2 voltage True
swsh_3_b1 10.0 10 cc_3 voltage False
swsh_3_b2 2.0 5 cc_3 voltage False
cc_1 116.15 6.900000000000006
cc_2 230.0 13.800000000000011
cc_3 230.0 0.0
1,1,,1,1.04000,0.98000,4,,,-15.00000,2,-15.00000,3,10.000000000000002,2,25.00000
2,2,,1,1.03000,0.97000,2,,,31.25000,4,12.50000
3,0,,1,1.00000,1.00000,3,,,13.00000,10,1.00000,5,1.50000
```

The atom's bus 1 has a reactor block of two steps of -15 Mvar and two capacitor blocks, with BINIT -15, so the
reactor block has one step in. Its control regulates remote bus 4 (115 kV), so the target is 1.01 x 115 kV =
116.15 kV. Bus 2 is continuous (MODSW 2) with BINIT 31.25 over four steps of 12.5, so 2.5 sections. Bus 3 is locked,
its blocks 10 x 1.0 and 5 x 1.5 Mvar with BINIT 13 give 10 and 2 steps, and its control is disabled. The exported
SWREG of buses 2 and 3 is their own bus; the source had 0. The ADJM 1 of bus 3 comes back blank.

### Switched shunt excerpt

From the artifact the importer writes for `cimhub_raw/tests/atoms/shunt/switched_shunts.raw`; no golden has a
switched shunt:

```
# untranscribed: adjm, rmpct
# targetValue and targetDeadband in V (voltage) or VAr (reactivePower)
Table RegulatingControl: mRID, name, mode, discrete, enabled, targetValue, targetDeadband, Terminal
    # defaulted: nreg=0
    cc_1, 1, voltage, true,  true,  116150.0, 6900.0000000000055, bb_4_T1
    # defaulted: nreg=0
    cc_3, 3, voltage, ,      false, 230000.0, 0.0,                bb_3_T1

# one per block: Ni sections of Bi; sections split from BINIT (block_sections)
Table LinearShuntCompensator: mRID, name, bus, bPerSection (pu system), nomU (kV), maximumSections, sections, inService, controlEnabled, RegulatingControl, BaseVoltage, EquipmentContainer
    swsh_1_b1, 1_b1, 1, -0.15, 230.0, 2, 1.0, true, true, cc_1, bv_230kv, sub_1
    swsh_1_b2, 1_b2, 1, 0.1,   230.0, 3, 0.0, true, true, cc_1, bv_230kv, sub_1
    ...
```

The reactive power modes are in the artifact for `cimhub_raw/tests/atoms/shunt/plant_and_facts.raw`. Bus 2's shunt
regulates the WMOD 1 machine `PV` at bus 1 (QT 50, QB -30) over 0.25 to 0.75, so the band is -10 to 30 Mvar, target
-10 000 000 VAr and deadband 40 000 000 VAr. Bus 3's shunt has no plant at SWREG. Bus 5's shunt regulates the FACTS
device `SVC-1` (SHMX 100) over 0.4 to 0.6, a band of -20 to +20 Mvar:

```
Table RegulatingControl: mRID, name, mode, discrete, enabled, targetValue, targetDeadband, Terminal
    # defaulted: nreg=0
    cc_2, 2, reactivePower, true, true,  -10000000.0, 40000000.0, pec_1_PV_T1
    # defaulted: nreg=0; untranscribed: vswlo=0.0
    cc_3, 3, reactivePower, true, false, ,            ,           bb_3_T1
    # defaulted: nreg=0
    cc_5, 5, reactivePower, true, true,  0.0,         40000000.0, fd_SVC-1_T1
```

A whole case that holds a FACTS device cannot be exported: see [DC lines and FACTS devices](dc.md).

## See also

- [Generators](generators.md): the machines a MODSW 3 shunt regulates.
- [Import mapping spec](../CIMTBL_MAPPING.md) and [export mapping spec](../EXPORT_MAPPING.md): the design record, with
  the field-by-field classification.
- [Round trip](../guide/roundtrip.md) and [What converts](../guide/coverage.md): the task-level view.
