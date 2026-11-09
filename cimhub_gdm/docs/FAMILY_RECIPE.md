# Per-family recipe

Every GDM family follows these steps (Phases 1-4). The cross-cutting rules are in [`GDM_MAPPING.md`](GDM_MAPPING.md)
(Phase 0). The field-classification helpers (`Field`, `check_fields`, `fields_stub`, `fields_table`), `mrid` and
`lookup` come from `cimhub_core.cimtbl`; all of them already accept pydantic models.

## Module layout

One module per family, not per GDM class. A family module keeps a component together with its inline equipment, its
catalogs and its controllers, so it reads as one mapping.

```
src/cimhub_gdm/
    gdm_reader.py         read_gdm (the only filesystem access)
    importer/
        gdm_to_cim.py     GdmImporter, gdm_to_cim, ORDER / INLINE / UNTRANSCRIBED / PENDING, coverage and name checks,
                          the time-series drop warning
        shared.py         qty, UNIT_SPELLINGS, system_voltage, base_voltage_mrid, phases_text, container_mrid,
                          susceptance, FREQUENCY_HZ, AUTHORITY
        network.py        the shell: new_feeder_model, Feeders, Substations
        bus.py  source.py  switch.py  line.py  load.py  capacitor.py  transformer.py  der.py
```

No registry and no decorators: the orchestrator's `ORDER` list is the dispatch.

## Inside a family module, in this order

1. **Prefix constants:** `PREFIX = 'sw_'`, from the `cimtbl-translate` table.
2. **Enum tables:** plain dicts mapping a GDM enum to the CIM enum's string, read through `lookup(table, value,
   slot=..., record_id=gdm.name)`. A table moves to `cimhub_core/codes.py` only once a second spoke uses it (and
   that is the core owner's change).
3. **`FIELDS_<Class>`**, one for each GDM class handled: the component, its inline equipment, its catalogs and its
   controllers.
   - It is keyed by pydantic `model_fields`.
   - A `copied` field's targets are `(builder_method, keyword, unit)`.
   - An `untranscribed` field's note says why CIM 18 has no home for it.
4. **Derived functions:** pure, named, unit-tested. A function moves to `shared.py` once two families use it. A
   function that is shared with another spoke belongs in `cimhub_core/derived/` (ask the core owner) or upstream (I9).
5. **`add_<catalog>(network, equipment)`** for each catalog class.
6. **`add_<component>(network, component)`:**
   - reads GDM;
   - creates one builder per CIM object, e.g. `LoadBreakSwitchBuilder(network, container)`;
   - calls `create(mRID=mrid(PREFIX, c.name), name=c.name)`;
   - then the builder's `add_*` methods, with keyword arguments only;
   - passes every quantity as `qty(gdm_value)`, percent ones included (R14 landed: `Qty(v, 'percent')` on a PerCent
     attribute stores `v`; on an ohm attribute it converts through `z_base`, so set the winding base first);
   - never uses `.to()`, and never wraps a call in try/except.

## The orchestrator

- **`ORDER`** is an explicit list of `(GdmClass, add_fn)`, in this order:
  1. the network shell (feeders, substations), then buses;
  2. catalogs;
  3. sources;
  4. branches (switches, lines, transformers, regulators, reactors);
  5. shunts (loads, capacitors), then their controls;
  6. DER.
- **`components(system, cls)`** keeps exact classes only. infrasys `get_components` recurses into subclasses, so exact
  matching means no class is handled twice (`PowerTransformerEquipment` is a `DistributionTransformerEquipment`).
- **`check_coverage(system)`** runs before anything is built and raises, naming the class and the count, on:
  - a component class in no list;
  - a `PENDING` class, also naming the phase that ports it;
  - inline equipment with no parent (`system.list_parent_components(eq) == []`);
  - supplemental attributes.
- **Time series** are not an error in the first pass (OPEN_DECISIONS 2): `drop_time_series_warning(system)` logs one
  warning listing every component with `system.has_time_series(c)` and its series metadata, then the build goes on.

## Catalogs: built once, reused by identity

- **Built eagerly.** Every `*Equipment` class with a CIM template home is in `ORDER` and built from
  `components(system, EquipmentCls)`. infrasys stores each equipment object once, so each template is built exactly
  once, unreferenced ones included (I8: nothing dropped).
- **Referenced, never built, by instances.** An instance refers to its template by `mrid(PREFIX,
  component.equipment.name)`.
- **Name clashes.** `check_unique_names(system, cls)` runs for every mapped class before anything is built
  (OPEN_DECISIONS 10).
- **Inline equipment** (Load, PhaseLoad, Capacitor, PhaseCapacitor, VoltageSource, PhaseVoltageSource, Winding, Solar,
  Battery, Reactor, the switch equipment, and Inverter unless it is templated) is listed in `INLINE` and read through
  its parent.

## Steps per family

1. **Probe the builders.** Check every builder method and keyword the family will call against the current CIM-Builder
   working tree. Record anything broken in the plan's upstream table. If a builder isn't ready, its class stays in
   `PENDING`; don't work around it.
2. **Stub the fields.** Paste `fields_stub(Model)` for each GDM class and classify every field.
3. **Write the golden by hand** in the core shapes, following the cimtbl-translate rules:
   - units as GDM writes them;
   - line-to-line BaseVoltage;
   - the load sign convention;
   - percent on the winding base;
   - a comment above every derived value showing the arithmetic.

   Writing the golden before the code keeps it an independent oracle. Where the DSS wave already has a golden for the
   same CIM pattern, start from it.
4. **Write the code:** enum maps, derived functions, `add_*` functions.
5. **Write the tests** ([`TEST_DESIGN.md`](TEST_DESIGN.md)): `check_fields`, derived-function units, atoms, fail-fast
   cases.
6. **Register the classes:** move each one from `PENDING` to `ORDER`, `INLINE` or `UNTRANSCRIBED`.
7. **Update `GDM_MAPPING.md`:** the generated field table (`fields_table(Model, fields=FIELDS)`), the gaps, the atom
   list. The user approves the section before the next family starts (as DSS-12).
