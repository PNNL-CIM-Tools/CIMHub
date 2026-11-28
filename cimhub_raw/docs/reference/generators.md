# Generators

This page is the conversion reference for the RAW Generator table: the machines at a bus, their voltage control, their
limits, the renewable and power factor forms, and the implicit step-up transformer. One RAW record becomes one machine
or one converter connection with its unit, and the records at one bus share a plant control. The field classes
(copied, mapped, structural, derived, untranscribed) and the conventions every section follows are on the
[reference index](index.md). The getters the exporter reads through, and the generation sign rule they apply, are on
the core site's [distributed energy resources](https://pnnl-cim-tools.github.io/CIMHub/core/reference/der/) page.

| RAW table | CIM classes | `.cimtbl` artifact and shape | Importer | Exporter |
|---|---|---|---|---|
| Generator, WMOD 0 | `SynchronousMachine`, `GeneratingUnit`, `ControlAreaGeneratingUnit` | `generator.cimtbl`, shape `synchronous_machine` with `bus` | `importer/cimtbl/generator.py` | `exporter/generator.py` |
| Generator, WMOD 1, 2, 3 | `PowerElectronicsConnection`, `PowerElectronicsUnit`, `ControlAreaPowerElectronicsUnit` | `generator.cimtbl`, shape `der` with `bus` | `importer/cimtbl/generator.py` | `exporter/generator.py` |
| Generator, one per bus | `RegulatingControl`, the plant's | `generator.cimtbl` | `importer/cimtbl/generator.py` | `exporter/generator.py` |
| Generator, RT + jXT other than 0 | `PowerTransformer` with two `PowerTransformerEnd`s, an internal `TopologicalNode`, and a fixed `RatioTapChanger` when GTAP is not 1 | `generator.cimtbl`, shape `behind_transformer` | `importer/cimtbl/generator.py` | `exporter/generator.py` |

The table shapes are on the core site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/).
Source paths are under
[`cimhub_raw/src/cimhub_raw/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_raw/src/cimhub_raw). The
master imports `generator.cimtbl` after the load and fixed shunt artifacts and before the transformer ones. A switched
shunt that regulates a plant's reactive power reads the machine from this table (see [Loads and shunts](loads.md)). The
bus a machine sits on, its area and its IDE come from the bus tables (see
[Case, buses, areas and zones](buses.md)).

Quoted error messages start with the record, as `1_1:` or `plant 2:`. A generator's key is its bus number and ID, and
the name the importer gives it is `<I>_<ID>`; a blank ID is 1.

The examples run from the repository root with `UV_FROZEN=1 uv run python`. They convert the public test atoms in
[`cimhub_raw/tests/atoms/generator`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_raw/tests/atoms/generator)
to CIM and back.

## Records, plants and classes

PSS/E treats VS, IREG and RMPCT as plant quantities: every machine at bus I shares them, and the plant's output and
limits are the sums over its machines in service. The importer follows that. Each bus with generator records gets one
`RegulatingControl` `gc_<I>`, and every machine and connection at the bus names it. The control cannot be `cc_<I>`,
which is the switched shunt's control, because one bus can have both.

WMOD picks the class of each record:

| WMOD | CIM, per record | Plant control |
|---|---|---|
| 0 conventional | `SynchronousMachine` `sm_<I>_<ID>`, `GeneratingUnit` `gu_<I>_<ID>`, `ControlAreaGeneratingUnit` `cagu_<I>_<ID>` | voltage |
| 1 renewable, limits QT and QB | `PowerElectronicsConnection` `pec_<I>_<ID>`, `PowerElectronicsUnit` `pecu_<I>_<ID>`, `ControlAreaPowerElectronicsUnit` `capu_<I>_<ID>` | voltage |
| 2 renewable, limits from WPF | as WMOD 1, with WPF listed on the row | voltage |
| 3 renewable, fixed power factor | as WMOD 1 | power factor |
| 4 infeed | raises `NotImplementedError` | |
| any other value | raises | |

A blank WMOD is 0. The `PowerElectronicsUnit` has no kind: RAW cannot say whether a converter plant is solar or wind,
so the importer writes neither `PhotoVoltaicUnit` nor `PowerElectronicsWindUnit`. A concentrating solar plant that
PSS/E models as a conventional machine is WMOD 0, and lands on `SynchronousMachine` and `GeneratingUnit`. RAW cannot
mark a type 1 or 2 wind plant, an induction machine, entered as WMOD 1: it is a converter connection here. Each unit
joins the `ControlArea` `ca_<AREA of bus I>`; a generator record has no AREA of its own. A bus AREA with no Area
interchange record raises.

### Plant voltage control

For WMOD 0, 1 and 2 the plant control is:

| `RegulatingControl` attribute | Value |
|---|---|
| mRID, name | `gc_<I>`, `<I>` |
| `mode`, `discrete` | voltage, false |
| `targetValue` | VS x the BASKV of the regulated bus, in volts (`232300.0` for VS 1.01 on 230 kV); blank VS is 1.0 |
| `targetDeadband` | blank: PSS/E holds VS exactly |
| `Terminal` | the busbar terminal `bb_<IREG>_T1`, or `bb_<I>_T1` when IREG is 0 or I; NREG other than 0 names a node of bus IREG and the terminal is that node's busbar (see [Substations and node-breaker data](substations.md)) |
| `enabled` | true when the bus's IDE is 2 or 3; every member's `controlEnabled` follows it |

The product VS x BASKV can leave a last-digit float residue (`144209.99999999997` for 1.045 on 138 kV) and is written
as computed. A plant on an IDE 1 bus has its control disabled. IDE 3 is the swing bus: every `SynchronousMachine` at
the bus gets `referencePriority` 1, the angle reference's highest priority, and the exporter writes IDE 3 for a bus
with such a machine. A bus with an enabled plant control exports as IDE 2, and any other as IDE 1.

The plant's records must agree on VS, IREG, NREG and RMPCT, as PSS/E requires. A swing bus must regulate itself,
because PSS/E would silently regulate bus I instead.

### Sign, limits and rating

CIM's terminal `p` and `q` are positive into the equipment, so a generator's are negative. The importer writes
`p (MW)` = -PG and `q (MVAr)` = -QG on both classes, and keeps zero as `0.0`. The limits stay in the generator
convention, as CIM defines them, and are copied: `maxQ` = QT, `minQ` = QB, and PT and PB are
`GeneratingUnit.maxOperatingP` and `minOperatingP`, or `PowerElectronicsUnit.maxP` and `minP`. A negative PB, a pumping
machine, is copied as it is. The exporter asks the getters for `sign="generation"` and so writes PG and QG positive
again.

| CIM value | From |
|---|---|
| `ratedS (MVA)` | MBASE; a blank MBASE is SBASE |
| `ratedU (kV)` | BASKV of bus I: RAW has no machine voltage, and MBASE and ZR are on BASKV |
| `r (ohm)`, a `SynchronousMachine` only | ZR x BASKV^2 / MBASE |
| `qPercent`, a `SynchronousMachine` only | RMPCT, on every machine of the plant |
| `inService` | STAT == 1 on the machine or connection; the unit has no status of its own |

ZX is untranscribed: cim18v17's `SynchronousMachine` has no positive-sequence reactance. On a
`PowerElectronicsConnection`, ZR and RMPCT have no CIM attribute; the row lists them when they are not 0 and 100
(`# untranscribed: zr=0.01`).

## Renewable machines

A WMOD 1, 2 or 3 record is a `PowerElectronicsConnection` with its unit, and the three differ in the limits and the
control:

| WMOD | Reactive limits | Plant control | What the row says |
|---|---|---|---|
| 1 | `maxQ`, `minQ` = QT, QB | voltage, as above | nothing extra |
| 2 | `maxQ`, `minQ` = QT, QB as written; RAW sets them from PG and WPF, which CIM cannot express, so they do not follow a later change of `p` | voltage, as above | `# untranscribed: wpf=0.95`, always, so the importer's own output tells WMOD 2 from 1 |
| 3 | QT, QB as written | `mode` powerFactor, `discrete` false, `targetValue` = WPF as read, `enabled` as above | `# untranscribed: regulated_voltage_setpoint=1.02, regulated_bus_number=3` when VS, IREG or NREG is off its default |

A WMOD 3 plant holds the connection's power factor, not a voltage. The sign of WPF is kept: a positive WPF means `q`
has the sign of `p`, under the generator or the load sign alike. The control sits on the connection's own terminal,
`pec_<I>_<ID>_T1`, where its power factor is. The connection row names the control, so the control row is written
with no `Terminal` and an `Update RegulatingControl` row after the connection table sets it. VS, IREG and NREG are
not used by a fixed power factor. A plant that mixes WMOD 3 with any other record raises, because one control holds
either a voltage or one connection's power factor.

On export a `PowerElectronicsConnection` is WMOD 3 with WPF = the control's `targetValue` when its control is
`powerFactor`, and WMOD 1 otherwise. WMOD 2 comes back as 1, with WPF blank.

## The implicit step-up transformer

RT + jXT other than 0 is PSS/E's implicit step-up between bus I and the machine, with GTAP the off-nominal ratio at bus
I. The importer writes the transformer as data, in the core `behind_transformer` shape, with the machine on an internal
node:

| CIM class | mRID | Attributes |
|---|---|---|
| `TopologicalNode` | `<machine>_int` | name `<I>_<ID> terminal`; no bus number; bus I's `BaseVoltage` and substation |
| `PowerTransformer` | `<machine>_xf` | name `<I>_<ID> step-up`; always in service |
| `PowerTransformerEnd` 1 | `<machine>_xf_1` | on bus I; `ratedU (kV)` = BASKV; `ratedS (MVA)` = MBASE; `r (ohm)` = RT x BASKV^2 / MBASE; `x (ohm)` = XT x BASKV^2 / MBASE |
| `PowerTransformerEnd` 2 | `<machine>_xf_2` | on the internal node; `ratedU (kV)` = BASKV; `ratedS (MVA)` = MBASE; no `r`, `x` |
| `RatioTapChanger`, GTAP other than 1 | `<machine>_xf_tap1` | on end 1; one fixed step (`lowStep`, `highStep`, `neutralStep`, `step` all 1, `ltcFlag` and `controlEnabled` false); `neutralU (kV)` = GTAP x BASKV |

`<machine>` is `sm_<I>_<ID>` or `pec_<I>_<ID>`. The machine's terminal is on the internal node. RAW gives no terminal
voltage for the machine, because XTRAN and GTAP are per unit on MBASE and the system base, so the internal node and end
2 keep bus I's `BaseVoltage`, a per-unit equivalent. The machine's `ratedU` is the same. There is no magnetizing
branch.

Power, limits and control stay on the machine. The plant control stays on bus I's busbar, because PSS/E's power flow
injects PG + jQG at bus I and uses XTRAN only in fault and dynamics studies. A CIM solve that includes the step-up will
therefore see its losses, which the RAW solution does not: an expected difference when solving, not when converting.

GTAP is used only with a step-up. Without one PSS/E ignores it, so the importer lists it on the machine row when it is
not 1 (`# untranscribed: gtap=1.02`).

On export a machine whose terminal node has no bus number sits behind a step-up, and the exporter folds it back:

| Check | Rule |
|---|---|
| the node | holds the machine and exactly one `PowerTransformer` whose other end is on a numbered bus |
| the transformer | in service, two windings, no core admittance, winding 1 on the bus and winding 2 on the machine's node |
| the ratings | each end's `ratedU` equals its node's `BaseVoltage` |
| the tap | only a fixed `RatioTapChanger` on winding 1 |
| the values | RT = the windings' r summed, XT = the mesh x, both per unit on MBASE; GTAP = `neutralU` / `ratedU` of end 1, or 1 with no tap |

The transformer exporter leaves these transformers out, so each is exported once, as the machine's RT, XT and GTAP.
Anything else raises.

## Generator fields

| RAW field | Import | Export |
|---|---|---|
| I | structural: the machine's `bus`, `BaseVoltage`, `EquipmentContainer` and `ControlArea`; the plant key `gc_<I>`; IDE sets `enabled` and `referencePriority` | the bus number of the machine's node, or of the bus across its step-up |
| ID | structural: key for the mRIDs, name `<I>_<ID>`; blank is 1 | the ID in the mRID `sm_<I>_<ID>` or `pec_<I>_<ID>`, else the next free `1`, `2`, ... on the bus |
| PG | derived: `p (MW)` = -PG; blank is 0 | the machine's `p` in generation sign |
| QG | derived: `q (MVAr)` = -QG; blank is 0 | the machine's `q` in generation sign |
| QT | copied: `maxQ (MVAr)` of the machine or connection; blank is 9999 | `maxQ` in generation sign; blank when unset |
| QB | copied: `minQ (MVAr)`; blank is -9999 | `minQ` in generation sign; blank when unset |
| VS | derived: the plant control's `targetValue` = VS x BASKV of the regulated bus, in V; blank is 1.0 | the voltage control's target in kV over the regulated bus's BASKV; blank for WMOD 3 and for a plant with no control |
| IREG | structural: the plant control's `Terminal`; blank is 0 | the bus number of the control's terminal, its own bus included (a RAW 0 comes back as I); blank for WMOD 3 and for a plant with no control |
| MBASE | copied: `ratedS (MVA)`, with `ratedU (kV)` = BASKV; blank is SBASE | the rating's `ratedS` |
| ZR | derived: `r (ohm)` of a `SynchronousMachine` = ZR x BASKV^2 / MBASE; listed on a connection's row when not 0; blank is 0 | a machine's r in pu on its `ratedU` and `ratedS`; blank for a connection |
| ZX | untranscribed | not written |
| RT, XT | derived: the step-up's end 1 `r (ohm)`, `x (ohm)`; blank is 0 | the step-up's r and x in pu on MBASE; 0 with no step-up |
| GTAP | derived: the fixed tap's `neutralU (kV)` = GTAP x BASKV; without a step-up listed when not 1; blank is 1.0 | `neutralU` / `ratedU` of the step-up's tap, 1 with no tap; blank with no step-up |
| STAT | mapped: `inService`; blank is 1 | 0 when `inService` is false, else 1 |
| RMPCT | copied: `SynchronousMachine.qPercent`, on every machine of the plant; a connection lists it when not 100; blank is 100 | the `qPercent` of the plant's machines on every record of the plant; blank for a plant of connections only |
| PT | copied: `maxOperatingP (MW)` or `maxP (MW)`; blank is 9999 | the unit's maximum in generation sign, as stored |
| PB | copied: `minOperatingP (MW)` or `minP (MW)`; blank is -9999 | the unit's minimum in generation sign, as stored, even when it is above PT |
| O1 to O4, F1 to F4 | untranscribed | not written |
| WMOD | mapped: the class, as in the table above; blank is 0 | 0 for a `SynchronousMachine`; 3 for a connection under a `powerFactor` control, else 1 |
| WPF | mapped: WMOD 2 always listed; WMOD 3 the control's `targetValue`; blank is 1.0 | WMOD 3: the control's `targetValue`; else blank |
| NREG | structural: a node of bus IREG, as above; blank is 0 | not written |

### Generator fail-fast rules

| Rule | Message |
|---|---|
| WMOD 4 | `generator 1_1: WMOD 4 (infeed, fixed Q: no case has one yet)` |
| any other WMOD | `1_1: wmod=9 has no mapping (known: 0, 1, 2, 3)` |
| a STAT other than 0 or 1 | `1_1: status=2 has no mapping (known: 0, 1)` |
| records of one plant that disagree | `plant 2: generators 2_G and 2_PV disagree on (IREG, NREG, VS, RMPCT): (3, 0, 1.05, 100.0) vs (3, 0, 1.01, 100.0); PSS/E treats them as plant quantities` |
| an IREG that is no bus | `plant 1: IREG 77 is no bus` |
| a swing bus that regulates another bus | `plant 1: a swing bus regulates remote bus 3 (PSS/E would regulate bus 1 instead)` |
| a swing bus with only converter records | `plant 1: a swing bus with no SynchronousMachine (only converter records), so no referencePriority` |
| a bus AREA with no Area interchange record | `plant 1: AREA 9 has no area-interchange record (no ControlArea ca_9)` |
| WMOD 3 beside another record | `plant 2: WMOD 3 ['2_G'] shares the plant with other records; one control holds either a voltage or one connection's power factor (no case has one yet)` |
| export: machines of one plant whose controls disagree | `plant 2: its machines' controls disagree on (IREG, VS): [...]; PSS/E treats them as plant quantities` |
| export: machines whose `qPercent` disagree | `plant 2: its machines' qPercent disagree: [...]; RMPCT is a plant quantity` |
| export: a control that is neither voltage nor a connection's power factor | `RegulatingControl 'x' of SynchronousMachine 'y': mode ...; a plant regulates voltage, or a connection its power factor` |
| export: a machine on a node with no bus number that is not a step-up | `SynchronousMachine 'x': its TopologicalNode 'y' has no busNumber and holds [...]; a step-up's node holds the machine and one transformer` |
| export: a step-up out of service, with a core, with a moving tap, or rated off its node's `BaseVoltage` | the message names the transformer and the rule, such as `out of service; a RAW step-up has no status of its own` |

One more case is not caught by a message: an explicit MBASE of 0 passes the importer's defaulting (only a blank MBASE
is SBASE) and stops with a bare `ZeroDivisionError`, in the ZR conversion of a `SynchronousMachine` or in the r and x of
a step-up. A connection with no step-up takes it through as `ratedS` 0.

### Generator round trip

| What | Why |
|---|---|
| IREG 0 comes back as the bus's own number | CIM keeps the terminal, not whether RAW wrote 0 or I |
| a blank MBASE comes back as SBASE | the importer defaulted it |
| WMOD 2 comes back as 1 and its WPF comes back blank | CIM has no reactive limit that follows P; the row's note is not read back |
| a WMOD 3 record comes back without its VS and IREG | a fixed power factor does not use them |
| a WMOD 1 record's WPF other than 1 comes back blank | PSS/E uses WPF only in WMOD 2 and 3 |
| a connection's ZR and, in a plant of connections only, RMPCT come back blank | no CIM attribute |
| a GTAP other than 1 without a step-up comes back blank | PSS/E ignores it, and the row's note is not read back |
| ZX, O1 to O4, F1 to F4 and NREG come back blank | no CIM home, or not written |
| ZR, RT, XT and VS can differ in the last digit | per unit to ohm and per unit to volt conversions: relative error 1e-9 |
| a reversed PT and PB come back as written | the exporter returns the unit's limits as stored |

This example converts the step-up atom. It prints each machine's node and its `p` in both signs, the transformers, and
the exported records. The machine `2 G2` has GTAP 1.02 but no step-up, so it stays on bus 2:

```python
import cimprofiles.cim18.cim18v17 as cim

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.getters.der import get_der_output
from cimhub_raw.exporter.cim_to_raw import RawExporter
from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader
from cimhub_raw.raw34_writer import Raw34Writer

case = Raw34Reader("cimhub_raw/tests/atoms/generator/step_up.raw").read_all()
network = raw_to_cim(case, name="atom")

for machine in network.graph[cim.SynchronousMachine].values():
    node = machine.Terminals[0].TopologicalNode
    load_sign = get_der_output(machine, "MW", "MVAr", sign="load").total
    generation_sign = get_der_output(machine, "MW", "MVAr", sign="generation").total
    print(machine.mRID, node.mRID, load_sign.p, generation_sign.p)

print(sorted(transformer.mRID for transformer in network.graph[cim.PowerTransformer].values()))

writer = Raw34Writer()
for record in RawExporter().to_model(network).list_by_class(schema.GeneratorRecord):
    print(writer.serialize(record))
```

```text
sm_1_1 sm_1_1_int -150.0 150.0
sm_2_G1 sm_2_G1_int -80.0 80.0
sm_2_G2 2 -30.0 30.0
sm_4_1 sm_4_1_int -10.0 10.0
['pec_2_PV_xf', 'sm_1_1_xf', 'sm_2_G1_xf', 'sm_4_1_xf']
1,'1 ',150.000,20.000,100.000,-50.000,1.02000,1,200.000,0.0030000000000000005,,0.00200,0.12000,1.00000,1,100.0,180.000,0.000,,,,,,,,,0
2,'G1',80.000,15.000,60.000,-30.000,1.01000,3,100.000,0.00200,,0.0015000000000000002,0.10000,1.02500,1,100.0,90.000,-40.000,,,,,,,,,0
2,'G2',30.000,5.000,20.000,-10.000,1.01000,3,40.000,0.00000,,0.00000,0.00000,,1,100.0,35.000,0.000,,,,,,,,,0
2,'PV',40.000,5.000,20.000,-20.000,1.01000,3,50.000,,,0.00000,0.08000,1.00000,1,100.0,45.000,0.000,,,,,,,,,1
4,'1 ',10.000,2.000,8.000,-4.000,1.00000,4,12.000,0.00000,,0.010000000000000002,0.00000,1.00000,0,100.0,12.000,0.000,,,,,,,,,0
```

RT, XT and GTAP come back from the transformers: `2 G1` has GTAP 1.025 from its fixed tap, and the machine `2 G2` has no
step-up, so its GTAP is blank. The ZX field, just before RT, is blank for every record, and the last field is WMOD:
1 for the converter `PV`, 0 for the machines. IREG is 1, 3, 3, 3 and 4: the plants at buses 1 and 4 regulate their own
bus, which the source wrote as 0.

This example converts the renewables atom and prints each connection's plant control:

```python
import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters.control import get_regulating_control
from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader

case = Raw34Reader("cimhub_raw/tests/atoms/generator/renewables.raw").read_all()
network = raw_to_cim(case, name="atom")

for connection in network.graph[cim.PowerElectronicsConnection].values():
    control = connection.RegulatingControl
    print(connection.mRID, control.mRID, control.mode.name, get_regulating_control(control).target)
```

```text
pec_2_W gc_2 voltage 232300.0
pec_4_W1 gc_4 voltage 13800.0
pec_5_S gc_5 powerFactor 0.99
pec_6_S2 gc_6 powerFactor -0.905
```

`pec_2_W` and `pec_4_W1` are WMOD 2 and hold their plant's voltage (232.3 kV and 13.8 kV); `pec_5_S` and `pec_6_S2` are
WMOD 3 at WPF 0.99 and -0.905.

### Generator excerpts

From `cimhub_raw/tests/goldens/IEEE14/generator.cimtbl`, the artifact of the IEEE 14 bus case. Bus 1 is the swing bus
(`referencePriority` 1):

```
# one per plant (bus I); targetValue in V (voltage) or a power factor (powerFactor, a WMOD 3 plant)
Table RegulatingControl: mRID, name, mode, discrete, enabled, targetValue, Terminal
    gc_1, 1, voltage, false, true, 146280.0,           bb_1_T1
    gc_2, 2, voltage, false, true, 144209.99999999997, bb_2_T1
    ...

Table GeneratingUnit: mRID, name, maxOperatingP (MW), minOperatingP (MW), EquipmentContainer
    gu_1_1, 1_1, 10000.0, -10000.0, sub_1
    ...

# WMOD 0
# untranscribed: zx, o1, o2, o3, o4, f1, f2, f3, f4
Table SynchronousMachine: mRID, name, bus, p (MW), q (MVAr), maxQ (MVAr), minQ (MVAr), ratedS (MVA), ratedU (kV), r (ohm), qPercent, referencePriority, inService, controlEnabled, RegulatingControl, GeneratingUnit, BaseVoltage, EquipmentContainer
    # defaulted: wmod=0, wpf=1.0, nreg=0
    sm_1_1, 1_1, 1, -232.392, 16.549,  0.0,  0.0,   615.0, 138.0, 0.0, 100.0, 1, true, true, gc_1, gu_1_1, bv_138kv, sub_1
    # defaulted: wmod=0, wpf=1.0, nreg=0
    sm_2_1, 2_1, 2, -40.0,    -43.556, 50.0, -40.0, 60.0,  138.0, 0.0, 100.0, ,  true, true, gc_2, gu_2_1, bv_138kv, sub_2
    ...
```

The step-up and the fixed tap, from the artifact the importer writes for `cimhub_raw/tests/atoms/generator/step_up.raw`
(machine `2 G1`: RT + jXT = 0.0015 + j0.1 on MBASE 100, GTAP 1.025, on a 115 kV bus):

```
Table TopologicalNode: mRID, name, BaseVoltage, ConnectivityNodeContainer
    sm_2_G1_int, 2_G1 terminal, bv_115kv, sub_2

Table PowerTransformerEnd: mRID, name, bus, endNumber, ratedU (kV), ratedS (MVA), r (ohm), x (ohm), BaseVoltage, PowerTransformer
    sm_2_G1_xf_1, 2_G1_1, 2,           1, 115.0, 100.0, 0.19837500000000002, 13.225, bv_115kv, sm_2_G1_xf
    sm_2_G1_xf_2, 2_G1_2, sm_2_G1_int, 2, 115.0, 100.0, ,                    ,       bv_115kv, sm_2_G1_xf

Table RatioTapChanger: mRID, name, lowStep, highStep, neutralStep, neutralU (kV), step, ltcFlag, controlEnabled, TransformerEnd
    sm_2_G1_xf_tap1, 2_G1_1, 1, 1, 1, 117.87499999999999, 1, false, false, sm_2_G1_xf_1
```

The power factor plants, from the artifact for `cimhub_raw/tests/atoms/generator/renewables.raw`:

```
Table RegulatingControl: mRID, name, mode, discrete, enabled, targetValue, Terminal
    gc_2, 2, voltage,     false, true, 232300.0, bb_3_T1
    # untranscribed: regulated_voltage_setpoint=1.02, regulated_bus_number=3
    gc_5, 5, powerFactor, false, true, 0.99,
    ...

Table PowerElectronicsConnection: mRID, name, bus, p (MW), q (MVAr), maxQ (MVAr), minQ (MVAr), ratedS (MVA), ratedU (kV), inService, controlEnabled, RegulatingControl, BaseVoltage, EquipmentContainer
    # untranscribed: rmpct=50.0, wpf=0.95
    pec_2_W, 2_W, 2, -60.0, -5.0,    19.721, -19.721, 70.0, 13.8, true, true, gc_2, bv_13p8kv, sub_2
    pec_5_S, 5_S, 5, -40.0, -5.6997, 5.6997, 5.6997,  45.0, 13.8, true, true, gc_5, bv_13p8kv, sub_5
    ...

Update Table RegulatingControl: mRID, Terminal
    gc_5, pec_5_S_T1
```

## See also

- [Loads and shunts](loads.md): the switched shunts that regulate a plant's reactive power.
- [Transformers and impedance correction](transformers.md): the transformer records, which the exporter keeps apart
  from the step-up transformers.
- [Import mapping spec](../CIMTBL_MAPPING.md) and [export mapping spec](../EXPORT_MAPPING.md): the design record, with
  the field-by-field classification.
