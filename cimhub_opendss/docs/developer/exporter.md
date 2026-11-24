# The exporter

The exporter reads a cim18v17 network and returns a `DssModel`, the type `DssReader.read_all()` returns, so
`DssWriter` writes it and the reader and importer read it back. It does no file I/O. The code is
[`exporter/cim_to_dss.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/src/cimhub_opendss/exporter/cim_to_dss.py)
and one module per DSS class beside it. The design record, with a slot table per class generated from the code, is
[EXPORT_MAPPING.md](../EXPORT_MAPPING.md).

## The entry points

```python
from cimhub_core.cimtbl_testing import cim_scope
from cimhub_opendss import DssExporter, DssImporter, DssReader, DssWriter, cim_to_dss
from cimhub_opendss.schema import opendss_schema as schema

with cim_scope():
    atom = DssReader("cimhub_opendss/tests/atoms/line/codes.dss").read_all()
    network = DssImporter("codes").to_cim(atom)

    exported = DssExporter().to_model(network, name_source="name")      # a DssModel, nothing written
    print(sorted(cls.__name__ for cls in exported.graph))
    print(DssWriter().serialize(exported.list_by_class(schema.Linecode)[0])[:60])

    cim_to_dss(network, "/tmp/codes_out/codes.dss", name_source="name")  # to_model, then DssWriter.write
```

| Call | Does |
|---|---|
| `DssExporter(time_points=None)` | `time_points` is the dict of TimePoint tables of the network's schedules (`read_time_points`, or the dict an importer filled). With it, each load group's schedule becomes a `LoadShape` (S8) and so does each device's (S9). Without it the loads and devices are static. |
| `.to_model(network, *, name_source=None, circuit_source="source", switch_state="actual")` | Returns the `DssModel`. |
| `cim_to_dss(network, destination, *, per_class=False, time_points=None, **opts)` | `DssExporter(time_points).to_model(network, **opts)`, then `DssWriter().write(model, destination, per_class=per_class)`. |

The options of `to_model`:

| Option | Meaning |
|---|---|
| `name_source` | What the DSS names are written from: `'name'`, `'mrid'` or `'uri'` (`cimhub_core.names`). Else `$CIMHUB_NAME_SOURCE`, else `'mrid'`. |
| `circuit_source` | With several `EnergySource`s, the one (by its exported name) that becomes `New Circuit` and is named `source`. A single source is the circuit's; zero or several matches raise. |
| `switch_state` | `'actual'` writes `Switch.open` as each switch's `State` and `Open` command; `'normal'` writes `Switch.normalOpen`, for an as-built model whose `open` is unset. `Normal` always reads `normalOpen`. Any other value raises. |

## to_model

`to_model` checks its options, then:

1. `_check_exported(network)` raises `no DSS export yet for {...}` for any `ConductingEquipment` class no module exports,
   so nothing is dropped silently. A `BusbarSection` is its node's bus (`buses.BUS_CLASSES`) and writes no record.
2. It builds an `ExportContext`: the network, the `Names` registry, the circuit's `EnergySource`, `switch_state`, the
   coupled line groups (`linegeometry.coupled_groups`, found once), the schedules' time point rows (`points`,
   `device_points`) and a `ShapeRegistry` that the modules fill as they claim LoadShapes. `context.objects(*cim_classes)`
   returns the network's objects of those classes.
3. For each module in `EXPORT_ORDER`, `module.export(context)` returns DSS records, which are added to the model.
4. `options_record(network, names, switch.open_terminals(context))` adds the `Options` record.

`EXPORT_ORDER` runs `vsource`, `wire`, `linecode`, `linegeometry`, `line`, `switch`, `xfmrcode`, `transformer`,
`regcontrol`, `loadshape`, `load`, `capacitor`, `capcontrol`, `pvsystem`, `storage`, `generator`, `reactor`,
`buscoords`. It is the order the records are *made* in, since later modules ask earlier ones for names (the line asks
its LineCode's name) and for claimed shapes. The order the deck is *written* in is `DssWriter`'s `WRITE_ORDER`.

Each module has the same three names:

| Name | Role |
|---|---|
| `CIM_CLASSES` | The CIM classes it exports. `_check_exported` collects them. A module that exports no equipment (`loadshape`) has `()`. |
| `SLOTS` | `{DSS class: {slot: Slot}}`: what the module does with each slot of the DSS class. |
| `export(context)` | `list[record]` over the whole network. It cannot work object by object: a LineGeometry is one per (WireConfiguration, offset) over the lines, and an inverter is chopped into one DSS device per unit. |

## Reading CIM: only through the core getters

An exporter module never walks CIM attributes to find a value in a unit or a base. Every quantity comes from a
`cimhub_core.getters` function (`get_source`, `get_sequence_impedance_code`, `get_shunt_reactive_power`,
`get_transformer_model`, ...), and any remaining physical attribute is read through `cimtables.graph_write.get_qty(obj,
"attribute", "unit")`, which converts to the unit asked for (the `options.py` voltage bases are read that way, in
kV). The getters and their NamedTuple returns are described on the core site's
[getters guide](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/) and
[reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/); the unit rules are on
[Units](https://pnnl-cim-tools.github.io/CIMHub/core/developer/units/).

The exporter asks for the unit it writes: lengths in metres (`UNIT = "m"` in `linecode.py` and `line.py`, decision B1),
impedances in `ohm/m`, voltages in kV, with the unit named in the getter call (`get_source(source, angle_unit="deg",
voltage_unit="kV", impedance_unit="ohm")` in `vsource.py`, `get_transformer_model(unit, voltage_unit="kV", ...)` in
`windings.py`). Where DSS holds a value CIM does not (a LineCode's capacitance, a Vsource's short-circuit MVA), a named
function computes it: `c_from_b` in `cimhub_core.derived.capacitance` (the inverse of the importer's `b_from_c`) and
`short_circuit_from_thevenin` in `exporter/vsource.py` (the inverse of the importer's `thevenin_from_short_circuit`).

When CIM has a gap DSS cannot leave open, the module either raises or applies a documented rule, marked `rule` in
`SLOTS`: an unset line `b` is `C = 0`, so the engine's default capacitance never applies. A value CIM does not hold
and DSS defaults (`faultrate`, `Seasons`, ...) is `unset`.

## SLOTS

`SLOTS` is the exporter's mirror of the importer's `FIELDS` (I3). It lists every slot of the DSS class with a
`Slot(kind, note)` from `cimhub_core.export_slots`:

| Kind | Meaning |
|---|---|
| `written` | Written from a getter. |
| `rule` | CIM has no value and DSS needs one: a documented rule fills it. |
| `unset` | CIM cannot hold it; DSS's default applies. |
| `not mapped` | A form of the same data that is not written, or a value that raises when set. |

`check_slots(slots, native_class)` raises unless the dict lists exactly the slots of the class, each with a known kind;
`tests/test_export_framework.py::test_slots_are_complete` runs it for every module in `EXPORT_ORDER`. `with_default(
native_class, written, other)` lists `written` and gives every other slot the `other` entry, in the schema's order, so
a module with few written slots lists them and one default. `slots_table(slots, "DSS")` renders the markdown table that
the slot tables in `EXPORT_MAPPING.md` are generated from.

## Naming

`naming.Names` hands out every DSS name, per namespace (a DSS class, or `bus`), compared lowercased as DSS compares
them. The text comes from `cimhub_core.names.export_name`, then `dss_safe_name` replaces the characters DSS cannot
carry.

| Method | Use |
|---|---|
| `name(obj, namespace, *, suffix="")` | The DSS name of `obj` in `namespace`. A `suffix` (`_a`) names one of several DSS objects made from one CIM object. |
| `fixed(name, obj, namespace)` | A name DSS dictates (the circuit's `Vsource.source`), claimed for `obj`. |
| `bus(node, *, suffix="")` | A ConnectivityNode's bus name; `.` is DSS's node delimiter, so it becomes `_`. |

Asking again for the same object returns the same name. Two different objects on one name in one namespace raise,
because DSS would silently merge them:

```python
import cimprofiles.cim18.cim18v17 as cim
from cimhub_opendss.exporter.naming import Names

names = Names("name")
names.name(cim.EnergyConsumer(mRID="ld_a", name="Load 1"), "Load")
try:
    names.name(cim.EnergyConsumer(mRID="ld_b", name="load_1"), "Load")
except ValueError as error:
    print(error)        # EnergyConsumer 'ld_b' and 'ld_a' are both named 'load_1' in DSS Load (name source 'name')
```

`buses.bus_ref(node, phases, names, *, neutral=None)` writes a bus reference, `650.1.2.3`: A, B, C are nodes 1, 2, 3 and
`s1`, `s2` are 1, 2. A reference is never bare. A neutral goes on the node the caller gives, which only a winding does
(its grounding rule); without one it raises.

## options.py

`options_record` makes the `Options` record the writer turns into the deck's `Set` lines:

| Slot | From |
|---|---|
| `circuit` | The one Feeder's name. Several Feeders of one Substation are one circuit named by it; a Feeder with no equipment is not counted among several. No Feeder, or Feeders of different Substations, raises. |
| `defaultbasefreq` | `network.base_frequency`, in Hz. |
| `voltagebases` | The distinct `BaseVoltage.nominalVoltage` values in kV, ascending. The importer keeps the deck's `voltagebases` as BaseVoltages, even those on no bus, so they come back. |
| `earthmodel` | The one earth model of the geometry WireConfigurations (`Carson` or `Deri`); with no geometry at all, that of the network's one EarthResistivity, which no line names; else `None`. Models that differ raise. |
| `open_terminals` | `switch.open_terminals(context)`: `Class.name terminal` for each open switch. |

## One module end to end: LineCode

[`linecode.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/src/cimhub_opendss/exporter/linecode.py)
is the inverse of the importer's `linecode.py`.

1. `CIM_CLASSES = (PerLengthPhaseImpedance, PerLengthSequenceImpedance)`; `NATIVE_CLASS = schema.Linecode`.
2. `export(context)` takes the network's base frequency (`context.network.base_frequency.to("Hz")`) and writes one
   `Linecode` per impedance with `isTemplate` not `False`. An impedance with `isTemplate=false` is a line's own, which
   its Line carries inline (`line.py`).
3. `_linecode` names the code (`linecode_name`, which every Line that uses it calls too, so the reference and the
   definition agree), sets `nphases`, `units=m` and `baseFreq`, and adds `code_slots`.
4. `code_slots` raises on a `calculatedFrequency` that differs from the network's and on an earth return (`rg`, `xg`).
   For a phase impedance `_matrix_slots` calls `get_phase_impedance_code(code, "ohm/m", "nS/m")`, raises on a nonzero
   `g`, and lists the lower triangle of `r`, `x` and `c_from_b(b)` (unset `b` is zeros). For a sequence impedance
   `get_sequence_impedance_code` gives the values and `sequence_slots` raises on an unset `r0` or `x0` (DSS would take
   its own default) or a nonzero `g`.
5. `C1`, `C0` and `baseFreq` are typed as text in the schema, so `format_float` renders them (`TEXT_SLOTS`).
6. `SLOTS[schema.Linecode]` lists every slot: `written`, `rule` for `C1`, `C0` and `cmatrix`, `unset` for the ones CIM
   cannot hold (`faultrate`, `Seasons`, ...), and `not mapped` for `Rg`, `Xg`, `B1`, `B0` and `like`.

## Adding an exporter module

1. **Spec first.** Add a section to [EXPORT_MAPPING.md](../EXPORT_MAPPING.md): the CIM classes, the DSS slots, the
   rules and what raises.
2. **Getters.** Read through `cimhub_core.getters`. If the value you need has no getter, the capability belongs in
   core (I9): ask the core owner, and do not write a local stand-in.
3. **The module** in `exporter/<name>.py`: `CIM_CLASSES`, `NATIVE_CLASS`, `SLOTS` (use `with_default` and one
   `unset` entry for the slots CIM cannot hold), `export(context)`. Take names from `context.names`, never from the
   CIM object. Raise with `describe(obj)` (core's, the class and mRID) in the message.
4. **Register it.** Add the module to the import and to `EXPORT_ORDER` in `cim_to_dss.py`, after every module whose
   names or shapes it reads. If the DSS class is new to the writer, add it to `WRITE_ORDER` after what it references.
5. **Tests.** `check_slots` runs for you through `test_slots_are_complete`. Add `tests/test_export_<name>.py`:
   the atom through `export_atom` (import, then export), the engine comparison against the original deck
   (`assert_same_engine_state`), the exported deck against its golden in `atoms/<table>/export/`
   (`assert_matches_dss_golden`), and one test per `raises`. See [Testing](testing.md).
