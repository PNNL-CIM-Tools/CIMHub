# Buses, meters and the source

Every GridLAB-D object that equipment lands on is a bus: `node`, `meter`, `triplex_node`, `triplex_meter` and
`substation`. This page covers how those become CIM `ConnectivityNode`s and `BaseVoltage`s, how the swing bus becomes an
`EnergySource`, and what the master file holds (frequency, containers, the feeder head). How to read the tables is on the
[reference landing page](index.md).

| GLM | CIM (cim18v17) | Import (shape) | Export |
|---|---|---|---|
| `node`, `meter`, `triplex_node`, `triplex_meter` (every root bus) | `ConnectivityNode`, `BaseVoltage` | `bus.cimtbl` (a `ConnectivityNode` table) | `node`, or `triplex_node` on a split-phase bus |
| `substation`, any bus with `bustype SWING` | `EnergySource`, `BasePower` | `source.cimtbl` (`source`) | `substation` with `bustype SWING` |
| `module powerflow` `nominal_frequency` | `BaseFrequency` | the master | `module powerflow` `nominal_frequency` |
| the model | `Substation`, `Feeder`, `Feeder.NormalHeadTerminal` | the master | not written |

The shapes are on the core site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/), and the
getters the exporter reads through (`get_source`, `get_base_voltage`, `get_terminal_phases`) are on its
[getters guide](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/).

## The topology walk

In GridLAB-D a `load`, a `capacitor` and a `meter` are each a `node`, and lines end on them, so every bus has to exist
before any equipment is written. The importer therefore builds the buses itself, from a topology walk that runs once over
the whole model. The walk is `cimtopology.core.walk`, shared by every importer; the GLM side builds its input (a
`Network` of sources, branches and transformer coils) in `importer/topology.py`.

| Part | Rule |
|---|---|
| Buses | every object of a `node` or `triplex_node` class, including a `load`, `capacitor` or `triplex_load` that nothing else is parented to |
| Root buses | a bus whose `parent` is a bus is solved by GridLAB-D as its parent's bus. It gets no `ConnectivityNode`; its equipment lands on the root of its parent chain, and its name is listed in the root's row comment (`# children: ld_611`) |
| Sources | every `substation`, and every bus with `bustype SWING`. `SWING_PQ` is a plain bus, and becomes a swing only when its island separates; the row comment says so |
| Branches | every line, switch, fuse, recloser, sectionalizer, series reactor and regulator. A switching device with `status OPEN` is a normally open branch |
| Transformers | one coil per winding, from the `transformer_configuration` ([transformers](transformers.md)) |
| BaseVoltages | the walk's distinct bus voltages, highest first. A voltage of 1 kV or more is rounded to 0.01 kV, a lower one to the volt; the mRID is `bv_12p47kv`, `bv_480v`, `bv_240v` |
| Phases | a link's phases (`N` and `D` aside) must be on both of its end objects, as GridLAB-D requires; a center tap's `S` is on its `to` end only |

A bus's system is read from the walk: three phase (a source, or a polyphase transformer coil), single phase, or split
phase (`triplex_node`). A voltage on a bus object is a phase-to-neutral figure on a three-phase system, so the walk's
BaseVoltage (line to line) is `nominal_voltage` times the square root of three there, and times two on a split-phase bus.

A bus the walk does not reach (an island with no source) has no `BaseVoltage`, so equipment on it raises in its own mapper, today as a bare `KeyError` on the bus name.

The IEEE decks use `${VSOURCE}` without defining it. `GlmReader` takes the macro from its `defines` argument, as
`gridlabd -D` would:

```python
from cimtables.document import format_document
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter

model = GlmReader("cimhub_gridlabd/tests/decks/IEEE/IEEE13_cdpsm.glm", defines={"VSOURCE": "66395.28"}).read_all()
documents = GlmImporter("IEEE13_cdpsm").to_cimtbl(model)  # the master plus one document per GLM class
bus = next(part for part in documents.parts if part.name == "bus")
print("\n".join(format_document(bus).splitlines()[:12]))
print(format_document(documents.master))  # the master, excerpted below
```

## The master

The master document holds what no single GLM object owns, then one `Import` per non-empty part in dependency order
(catalogs first), then the feeder head.

| Row | From | Rule |
|---|---|---|
| `Substation`, `Feeder` | the `name` passed to `GlmImporter`, or its `substation=` and `feeder=` | mRIDs `sub_<substation>` and `fdr_<feeder>`; the `Feeder` names the `Substation` as its `NormalEnergizingSubstation`. Every bus, line and device names the feeder (or substation) as its container |
| `BaseFrequency` | `module powerflow { nominal_frequency ...; }`, else `#set powerflow::nominal_frequency=...` | mRID `bf_<f>hz`, in Hz. Neither set: GridLAB-D's 60 Hz, listed as `# defaulted: powerflow::nominal_frequency=60.0` |
| `BaseVoltage` | the walk | `nominalVoltage (kV)`, highest first |
| `OperationalLimitType` | fixed | `olt_normal` and `olt_emergency`, which every `CurrentLimit` names |
| `Update Table Terminal` (last) | every mapped link that touches a swing bus | sets `NormalHeadFeeder` on that link's Terminal at the swing: `<mRID>_T1` for its `from`, `_T2` for its `to` (a regulator: each unit's) |
| comment | every GLM class no mapper reads, with its count | `not mapped: <class> <count>, ...`, including classes the schema lacks |

The frequency is also what turns a line's capacitance `c` (nF) into the susceptance `b` (nS) on import, and the exporter
writes it back as `nominal_frequency`.

```
# defaulted: powerflow::nominal_frequency=60.0
Object BaseFrequency: mRID=bf_60hz, frequency (Hz)=60.0

Table BaseVoltage: mRID, nominalVoltage (kV)
    bv_115kv,  115.0
    bv_4p16kv, 4.16
    bv_480v,   0.48
    bv_240v,   0.24
```

Excerpt from the master of `IEEE13_cdpsm.glm`, printed by the example above (`documents.master`). The master is named after the model, so a model name that equals the name of a non-empty part (`transformer`, `load`, `switch`, `bus`, `source`, ...) fails with `document names repeat`.

**Fail fast.** A value the reader kept as an expression in a property a mapper reads. A head on a link no mapper writes
(a `sectionalizer` touching a swing bus): its Terminal would not exist. The walk raises on a coil that cannot sit on its
island, on a parent that is not a bus object, on a parent loop, and on a link whose phases are not on both of its ends.

## node, meter, triplex_node, triplex_meter

A `node` is a `ConnectivityNode` named by the GLM name, with the walk's `BaseVoltage`, in `ConnectivityNodeContainer`
`fdr_<feeder>`. A `meter` is a `node` with metering and billing properties, and `triplex_meter` is to `triplex_node` as
`meter` is to `node`. Those properties have no CIM home. A `triplex_node` that carries `power_1`, `power_2` or `power_12`
also becomes consumers; that is on the [loads](loads.md) page.

| property | import | export |
|---|---|---|
| `name` | copied to `ConnectivityNode.mRID` and `name`, source case, no prefix; root buses only | written: Names |
| `parent` | structural: a bus whose parent is a bus has no node; its equipment lands on the root of the chain, and its name is listed on the root's row | not written: every exported bus is a root |
| `phases` | structural: a child's phase conductors must be a subset of its root's; on a swing bus, `EnergySource.phases` | written: the A, B, C of every terminal on the node, then `N`; a `triplex_node` the service's letter, then `S` |
| `nominal_voltage` | structural: checked against the walk's kV on the bus's system; a disagreement over 10 % is listed in the table comment, not raised. On a swing bus it is also the source's `nominalVoltage` | written: the `BaseVoltage` over the square root of three on a three-phase bus, unchanged on a single-phase one, over two (one leg, `s1` to `N`) on a split-phase one |
| `bustype` | structural: `SWING` is an `EnergySource`; `PQ`, `PV` and `SWING_PQ` are a plain bus | not written, except `SWING` on the `substation` |
| `voltage_A` (`voltage_1` on a triplex bus) | derived, on a swing bus only: the source's `voltageMagnitude` and `voltageAngle` | not written |
| `power_1`, `power_2`, `power_12` (a plain `triplex_node`) | copied to `EnergyConsumer.p` and `q`; see [loads](loads.md) | not written here |
| `power_A` ... `power_CN`, `current_*`, `shunt_*`, `current_inj_*` (any bus class but a plain `triplex_node`'s `power_1`, `power_2`, `power_12`) | raises when set: a load on the bus object itself; make it a `load` | not written |
| `voltage_B`, `voltage_C`, `voltage_2`, `voltage_N` | untranscribed: the solver's initial guess | not written |
| object metadata, `latitude`, `longitude`, reliability, dynamics (`deltamode_*`, `GFA_*`), solver state and outputs, metering and billing | untranscribed: listed in the table comment as `untranscribed, set here: <class> <slot> <count>`, only for slots the model sets | not written: GridLAB-D's default |

`nominal_voltage` is checked on the walk's system, so a taxonomy meter that says 480 V on a bus the walk puts at 4.16 kV
is listed, not rewritten:

```
# nominal_voltage disagrees with the walk (10%): 480.0 V (0.8314 kV 3-phase) on bv_480v (1): meter_1
```

**Fail fast.** A parent that is not a bus object, or a parent loop. A child whose phases are not a subset of its root's.
A load accumulator on a bus object. A `nominal_voltage` that is an unevaluated expression.

**Expected differences.** A `meter` comes back as a `node` and a `triplex_meter` as a `triplex_node`; child buses are gone,
their equipment parented to the root bus; a `SWING_PQ` bus comes back a plain bus. `nominal_voltage` is the
`BaseVoltage`'s, so the deck's `2401.78` returns as `2401.7771198288...` (4160 V over the square root of three). The name
is the GLM name under `name_source="name"`, and an unsafe name (`.`, `:`, whitespace) is rewritten (`line_spacing:10`
returns as `line_spacing_10`).

Excerpt from `cimhub_gridlabd/tests/atoms/bus/feeder.bus.cimtbl`:

```
Table ConnectivityNode: mRID, name, BaseVoltage, ConnectivityNodeContainer=fdr_feeder
    # children: ld_1
    n1,        n1,        bv_12p47kv
    sourcebus, sourcebus, bv_12p47kv
    # bustype SWING_PQ: a plain bus here; it is a swing only when its island separates
    meter_1,   meter_1,   bv_480v
    # children: tn_1
    tm_1,      tm_1,      bv_240v
```

### Export: the bus's system

CIM does not store a bus's system, but GLM's `nominal_voltage` depends on it. The exporter reads it per voltage zone (the
buses joined without a transformer), from what lands in the zone, in this order:

1. a terminal on `s1` or `s2`: split phase, a `triplex_node` whose phase letter is the service's (the A, B or C of the
   primary of the center-tap transformers in the zone, which must agree);
2. the `EnergySource`, a transformer end on two or three of A, B, C, or one-phase ends on different phases (a bank):
   three phase;
3. one-phase transformer ends all on one phase: single phase.

A zone none of these reach raises (`the zone of bus ... has no source and no transformer end: its system is unknown`).
A split-phase zone whose center taps are not all on one phase raises too.

## substation and the swing source

A `substation` (always a swing) and every bus with `bustype SWING` becomes one `EnergySource` named `src_<name>` on the bus
itself. A swing bus with a `parent` raises. The `BasePower` is a separate object, `sbase_<name>`.

| property | import | export |
|---|---|---|
| `nominal_voltage` | derived: `EnergySource.nominalVoltage` = `line_voltage(nominal_voltage)` on the bus's system (`V`, as written); unset raises | written: `get_source` `nominalVoltage` over the square root of three |
| `positive_sequence_voltage` (`voltage_A`, or `voltage_1` on a triplex bus, when it is unset) | derived: `voltageMagnitude` = `line_voltage` of the magnitude of V, `voltageAngle` = arg(V) in degrees; a polar value is taken as written. Unset: `nominal_voltage` at 0 degrees, listed as `defaulted` | written: `get_source` `voltageMagnitude` over the square root of three, at `voltageAngle` |
| `phases` | structural: the phase letters, `N` dropped, one or three conductors; `ABC` is a blank cell | written, as for any bus |
| `reference_phase` | structural: unset or `PHASE_A`; anything else raises | not written |
| `base_power` | copied to `BasePower.basePower`, in its written unit (`12MVA` is `basePower (MVA)=12.0`) | written: the graph's `BasePower` when it holds one |
| `power_convergence_value`, the negative and zero sequence voltages, `transmission_level_*` | untranscribed | not written |
| source impedance | defaulted: a stiff source, `r`, `x`, `r0`, `x0` with a 10,000 MVA short circuit and X/R of 10 (12.47 kV gives about 0.0155 ohm) | not written: GridLAB-D's swing is ideal |

GridLAB-D's swing bus has no source impedance and CIM's `EnergySource` needs one for other tools to solve it, so the
importer writes a small default and lists it on the row as `defaulted`. `default_source_impedance(kv)` returns `(r, x)` in
ohm, with `|Z| = kV² / 10000` and `x = 10 r`:

```python
from cimhub_gridlabd.importer.cimtbl.bus import default_source_impedance

print(default_source_impedance(12.47))  # (0.0015472917861112452, 0.015472917861112451)
```

**Fail fast.** A source on any number of conductors but one or three. A source whose voltage (`positive_sequence_voltage` or `voltage_A`) is more than
10 % from `nominal_voltage`: the deck gives the wrong source voltage, or the wrong `defines`. A `reference_phase` other
than `PHASE_A`. A swing bus with a parent. On export, two `EnergySource`s (the Newton-Raphson solver takes one swing), an
`EnergySource` that does not have one terminal, and more than one `BasePower`.

**Expected differences.** The source impedance is not written, and the swing's `nominal_voltage` is recomputed from the
`EnergySource`. `base_power` is written in VA (`12000000`), the unit the schema declares. A source's zone is read as three
phase on export, whatever its phases, so a one-conductor swing (`phases AN`) comes back with its `nominal_voltage` and its zone's divided by the square root of three (7200 becomes 4156.92).

Excerpt from `cimhub_gridlabd/tests/atoms/bus/feeder.source.cimtbl`:

```
Object BasePower: mRID=sbase_sourcebus, basePower (MVA)=12.0

Table EnergySource: mRID, name, node, phases, nominalVoltage (V), voltageMagnitude (V), voltageAngle (deg), r (ohm), x (ohm), r0 (ohm), x0 (ohm), BaseVoltage, EquipmentContainer=sub_feeder
    # derived: nominalVoltage = line_voltage(nominal_voltage=7200.0), voltageMagnitude and voltageAngle from positive_sequence_voltage=7200.0+0.0j; defaulted: r x r0 x0 of a stiff source, 10000 MVA short circuit, X/R 10
    src_sourcebus, sourcebus, sourcebus, , 12470.765814495915, 12470.765814495915, 0.0, 0.0015474818382145749, 0.015474818382145749, 0.0015474818382145749, 0.015474818382145749, bv_12p47kv
```

A taxonomy swing node (`voltage_A 7416-30d`, a polar value) keeps its written magnitude and angle:
`tests/atoms/source/swing_node.cimtbl` has `voltageMagnitude (V)` 12844.9 and `voltageAngle (deg)` -30.0.

## Round trip

```python
from pathlib import Path
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim
from cimhub_gridlabd.exporter.cim_to_glm import cim_to_glm

model = GlmReader("cimhub_gridlabd/tests/decks/IEEE/IEEE13_cdpsm.glm", defines={"VSOURCE": "66395.28"}).read_all()
network = glm_to_cim(model, name="IEEE13_cdpsm")
cim_to_glm(network, "/tmp/IEEE13_back.glm", name_source="name")
text = Path("/tmp/IEEE13_back.glm").read_text()
start = text.index("object substation")
print(text[start:text.index("}", start) + 1])
```

```
object substation {
  name "sourcebus";
  phases "ABCN";
  nominal_voltage 66395.28;
  bustype "SWING";
  positive_sequence_voltage 66395.28+0j;
  base_power 12000000;
}
```

The deck header the exporter writes is one power flow: a `clock` that starts and stops at one instant,
`#set relax_naming_rules=1`, and `module powerflow { solver_method NR; nominal_frequency <f>; line_capacitance TRUE; }`.
`line_capacitance` is on because CIM's line susceptance is part of the model and GridLAB-D ignores every `c` without it.
A `module generators` is added when the deck holds DER.
