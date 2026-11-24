# The exporter

The exporter reads a cim18v17 network and returns a `GlmModel`, the type `GlmReader.read_all()` returns, so
`GlmWriter` writes it and the reader and importer read it back. It does no file I/O. The code is
[`exporter/cim_to_glm.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_gridlabd/src/cimhub_gridlabd/exporter/cim_to_glm.py)
and one module per GLM concept beside it. The design record, with a slot table per class generated from the code, is
[EXPORT_MAPPING.md](../EXPORT_MAPPING.md).

## The entry points

```python
from cimhub_core.cimtbl_testing import cim_scope
from cimhub_gridlabd.exporter.cim_to_glm import GlmExporter, cim_to_glm
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.glm_writer import GlmWriter
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim
from cimhub_gridlabd.schema import gridlabd as schema

with cim_scope():
    atom = GlmReader("cimhub_gridlabd/tests/atoms/series_reactor/series_reactor.glm").read_all()
    network = glm_to_cim(atom, name="atom")

    exported = GlmExporter().to_model(network, name_source="name")     # a GlmModel, nothing written
    print(sorted(cls.__name__ for cls in exported.graph if exported.count(cls))[:4])
    print(GlmWriter().serialize(exported.list_by_class(schema.SeriesReactor)[0]))

    cim_to_glm(network, "/tmp/reactor_out/reactor.glm", name_source="name")   # to_model, then GlmWriter.write
```

| Call | Does |
|---|---|
| `GlmExporter(time_points=None)` | `time_points` is the dict of time point tables of the network's schedules. With its `RegularTimePoint` table, a load group's schedule becomes a `player` and its loads read it. Without it the loads are static, with one warning. |
| `.to_model(network, *, name_source=None, switch_state="actual")` | Returns the `GlmModel`. |
| `cim_to_glm(network, destination, *, time_points=None, **opts)` | `GlmExporter(time_points).to_model(network, **opts)`, then `GlmWriter().write(model, destination)`. |

The options of `to_model`:

| Option | Meaning |
|---|---|
| `name_source` | What the GLM names are written from: `'name'`, `'mrid'` or `'uri'` (`cimhub_core.names`). Else `$CIMHUB_NAME_SOURCE`, else `'mrid'`. |
| `switch_state` | `'actual'` writes `Switch.open` as each switching device's `status`; `'normal'` writes `Switch.normalOpen`. Any other value raises. |

## to_model

`to_model` checks its options, then:

1. `_check_exported(network)` raises `no GLM export yet for {...}` for any `ConductingEquipment` class no module
   exports, so nothing is dropped silently. A `BusbarSection` (`NOT_EXPORTED`) is its node's bus and writes no
   record.
2. It builds the `Names` registry, reads the base frequency, and builds an `ExportContext`.
3. For each module in `EXPORT_ORDER`, `module.export(context)` returns GLM records, which are added to the model.
4. `_set_header` fills the model's `clock`, `#set` and `module` settings.

`ExportContext` is a `NamedTuple`:

| Field | Holds |
|---|---|
| `network` | The CIM network. `context.objects(*cim_classes)` returns its objects of those classes, class by class. |
| `names` | The `Names` registry. Modules take every name from it, never from the CIM object. |
| `switch_state` | `'actual'` or `'normal'`. |
| `buses` | `bus_table(network, names)`: each `ConnectivityNode` to its `Bus` (GLM name, system, phase letters, `nominal_voltage`). |
| `frequency` | The network's base frequency in Hz. |
| `model` | The `GlmModel` being built. A module may add to it what is not a record: `load` its expressions, `player` its tapes, the `player` class block and the `tape` module, `schedule` its schedule blocks. |
| `points` | Schedule uri to its `RegularTimePoint` rows (empty without `time_points`). |

`EXPORT_ORDER` is `buses`, `line`, `switch`, `series_reactor`, `transformer`, `regulator`, `player`, `schedule`,
`load`, `capacitor`, `inverter`. It is the order the records are *made* in, since later modules ask earlier ones for
names and for the schedules they claim (a load reads the player or schedule of its group). The order the deck is
*written* in is `GlmWriter`'s `WRITE_ORDER`.

The header `_set_header` writes is one power flow: a `clock` that starts and stops at one instant (`INSTANT`,
`'2000-01-01 00:00:00'`; with players, the earliest player start, so each scheduled load is its base times the first
point), `#set relax_naming_rules=1`, `module powerflow` on the NR solver at the network's frequency with
`line_capacitance TRUE` (CIM's line b is part of the model, and GridLAB-D ignores every `c` without it), and
`module generators;` when the model holds an inverter, solar or battery.

Each module has the same three names (`NATIVE_CLASS` is also there in the modules that write one GLM class):

| Name | Role |
|---|---|
| `CIM_CLASSES` | The CIM classes it exports. `_check_exported` collects them. It is `()` in `player.py` and `schedule.py`, which read a `ConformLoadSchedule` and are not conducting equipment, and `buses.py` lists only `EnergySource` (the `ConnectivityNode`s are read through `bus_table`). |
| `SLOTS` | `{GLM class: {slot: Slot}}`: what the module does with each slot of the GLM class. `schedule.py` has `{}`: a GLM `schedule` is a block of rules in `GlmModel.schedules`, not a schema class. |
| `export(context)` | `list[record]` over the whole network. It cannot work object by object: a template line configuration is one GLM object per way the lines use it, a transformer may add a star bus, and a bank of regulators is one GLM regulator. |

## Reading CIM: only through the core getters

An exporter module never walks CIM attributes to find a value in a unit or a base. Every quantity comes from a
`cimhub_core.getters` function (`get_source`, `get_line_code`, `get_shunt_reactive_power`, `get_transformer_model`,
`get_series_compensator`, ...). The getters and their NamedTuple returns are described on the core site's
[getters guide](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/) and
[reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/); the unit rules are on
[Units](https://pnnl-cim-tools.github.io/CIMHub/core/developer/units/).

The exporter asks each getter for the unit the GLM slot is stored in. GridLAB-D keeps each property in one fixed unit
(ft, ohm/mile, V, kVA, ...), which the schema declares, so `exporter/units.py` gives it:

| Function | Does |
|---|---|
| `glm_unit(native_class, slot)` | The pint unit of the slot (`Ohm/mile` is `ohm/mile`); a slot with no declared unit raises. |
| `from_percent(value, native_class, slot)` | A percent number (CIM's PerCent) in the slot's unit, as a fraction. |

So the deck holds numbers only, and no spoke code converts a unit. A value CIM does not hold and GLM needs goes
through a named function, from core where there is one (`c_from_b`, `kron_reduce`) and from this package where not
(`line_catalog.tape_shield_gmr` and `tape_shield_resistance`).

When CIM has a gap GLM cannot leave open, the module either raises or applies a documented rule, marked `rule` in
`SLOTS`. A value CIM cannot hold and GridLAB-D defaults (`rated_power`, a rating, ...) is `unset`.

## SLOTS

`SLOTS` is the exporter's mirror of the importer's `FIELDS` (I3). It lists every slot of the GLM class with a
`Slot(kind, note)` from `cimhub_core.export_slots`:

| Kind | Meaning |
|---|---|
| `written` | Written from a getter. |
| `rule` | CIM has no value and GLM needs one: a documented rule fills it. |
| `unset` | CIM cannot hold it; GridLAB-D's default applies. |
| `not mapped` | A form of the same data that is not written, or a value that raises when set. |

`check_slots(slots, native_class)` raises unless the dict lists exactly the slots of the class, each with a known kind;
`tests/test_export_framework.py::test_slots_cover_every_schema_slot` runs it for every module in `EXPORT_ORDER`.
`with_default(native_class, written, other)` lists `written` and gives every other slot the `other` entry, in the
schema's order, so a module with few written slots lists them and one default. `slots_table(slots, "GLM")` renders the
markdown table. The slot tables in `EXPORT_MAPPING.md` are generated from `SLOTS`, and
`test_the_spec_tables_are_the_slots` fails when the file's text is not what `spec_tables()` prints, so a change to
`SLOTS` means regenerating those tables in the spec.

## Naming

`naming.Names` hands out every GLM name. GLM names are global to a deck, so there is one namespace. The text comes
from `cimhub_core.names.export_name` (the CIM `name`, `mRID` or `uri()`, as `name_source` says), then `glm_safe_name`
replaces each run of characters GridLAB-D cannot take in a name (whitespace, `.`, `:`, `"`, `'`, `;`, `{`, `}`, `$`)
with one `_`. A `.` would make GridLAB-D read `object.property`, and `:` is its `class:id` form.

| Method | Use |
|---|---|
| `name(obj, *, suffix="", drop="")` | The GLM name of `obj`. A `suffix` (`_star`) names one of several GLM objects made from one CIM object. `drop` is an ending the text must have and loses: a regulator's units `<base>_<phase>` written as one GLM regulator named `<base>`. |

Asking again for the same object (and suffix) returns the same name. Two different objects on one name raise, because
GridLAB-D would refuse the deck or link the wrong object:

```python
import cimprofiles.cim18.cim18v17 as cim
from cimhub_gridlabd.exporter.naming import Names

names = Names("name")
names.name(cim.EnergyConsumer(mRID="ld_a", name="Load 1"))
try:
    names.name(cim.EnergyConsumer(mRID="ld_b", name="Load.1"))
except ValueError as error:
    print(error)        # EnergyConsumer 'ld_b' and 'ld_a' are both named 'Load_1' in GLM (name source 'name')
```

`buses.letters(phases)` gives the A, B, C among a list of `SinglePhaseKind`s in ABC order; every module writes
`phases` from it. A `Bus` carries its GLM phases (`ABCN`, or `BS` on a split-phase bus) and its `nominal_voltage`,
which is line to neutral on a three-phase system, the coil voltage on a single-phase one and one leg on a split-phase
one. CIM stores a line-to-line BaseVoltage and no system, so `buses.py` reads the system per voltage zone
(`cimtopology.core.Topology.voltage_zones`) from what lands in it. The order of its rules is in the module docstring
and in [EXPORT_MAPPING.md](../EXPORT_MAPPING.md).

## One module end to end: series_reactor

[`series_reactor.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_gridlabd/src/cimhub_gridlabd/exporter/series_reactor.py)
is the inverse of the importer's `series_reactor.py`.

1. `CIM_CLASSES = (cim.SeriesCompensator,)`; `NATIVE_CLASS = schema.SeriesReactor`.
2. `export(context)` returns one `SeriesReactor` per compensator in `context.objects(*CIM_CLASSES)`.
3. `_reactor` reads the compensator once: `get_series_compensator(compensator, glm_unit(NATIVE_CLASS,
   "phase_A_impedance"))` gives `r`, `x`, `r0`, `x0` in the unit the slot is stored in (ohm). GridLAB-D's reactor
   has no coupling between phases, so `r0` and `x0`, when set, must equal `r` and `x`, and a varistor raises, each
   with `describe(compensator)` (the class and mRID) in the message.
4. The phases are `letters(get_conductor_phases(compensator))`, and the two ends are the buses of
   `get_terminal_nodes(compensator)`, by their names in `context.buses`.
5. The impedance is one `schema.Complex(real=r, imag=x)` on each of the phases. The ratings come from
   `exporter.line.ratings`, which reads the equipment's `CurrentLimit`s through `get_current_limits`.
6. The name is `context.names.name(compensator)`.
7. `SLOTS[schema.SeriesReactor]` lists every slot: `written` for the name, phases, ends, the per-phase impedances and
   ratings, `not mapped` for the resistance and reactance parts (the impedance is written), `unset` for the rest
   (`with_default`).

The exported block, written from the importer's atom:

```text
object series_reactor {
  name "hsb";
  phases "ABC";
  from "n2";
  to "rb1";
  continuous_rating_A 400;
  ...
  phase_A_impedance 0+14.798307j;
  phase_B_impedance 0+14.798307j;
  phase_C_impedance 0+14.798307j;
}
```

The deck's slots are in the schema's order, not the order the module lists them.

## Adding an exporter module

1. **Spec first.** Add a section to [EXPORT_MAPPING.md](../EXPORT_MAPPING.md): the CIM classes, the GLM slots, the
   rules and what raises.
2. **Getters.** Read through `cimhub_core.getters`. If the value you need has no getter, the capability belongs in
   core (I9): ask the core owner, and do not write a local stand-in.
3. **The module** in `exporter/<name>.py`: `CIM_CLASSES`, `NATIVE_CLASS`, `SLOTS` (use `with_default` and one `unset`
   entry for the slots CIM cannot hold), `export(context)`. Take names from `context.names`, never from the CIM
   object, and units from `glm_unit`. Raise with `describe(obj)` (core's, the class and mRID) in the message.
4. **Register it.** Add the module to the import and to `EXPORT_ORDER` in `cim_to_glm.py`, after every module whose
   names or shapes it reads. If the GLM class is new to the writer, add it to `WRITE_ORDER` in `glm_writer.py`, after
   what it references.
5. **Tests.** `test_slots_cover_every_schema_slot` runs `check_slots` for you. Regenerate the slot tables in
   `EXPORT_MAPPING.md` (`print(spec_tables())` from `test_export_framework.py`). Export the importer's atom for
   the class: `test_export_atoms.py` runs every `tests/atoms/*/*.glm` through import, export, write, read and import
   again, compares the two CIM models, and checks the deck against its golden `<atom>.exported.glm`; list any
   difference the spec names in `EXPECTED`. Add one test per `raises`. See [Testing](testing.md).
