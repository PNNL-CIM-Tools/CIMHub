# cim18v17 → OpenDSS export spec

Plan and decisions: `.development/DSS_REWRITE_PLAN.md` §8 (E1-E10, approved 2026-11-09). One section per
sub-slice, each approved before its code (DSS-12). The exporter reads values only through the core getters (skill
`export-getters`). The `DssModel` it returns has the shape `DssReader.read_all()` returns, so the writer's deck reads
back through the reader and the importer.

## S6a: framework, writer, Vsource (spec approved 2026-11-09; done 2026-11-09)

### Layout

```
cimhub_opendss/src/cimhub_opendss/exporter/
    cim_to_dss.py     DssExporter(FormatExporter), EXPORT_ORDER, cim_to_dss(network, destination, **opts)
    naming.py         Names: the E1 switch + dss_safe_name (kept in the writer) + the per-namespace collision check
    buses.py          bus_ref(node, phases, names) -> "650.1.2.3" (E7)
    options.py        the Options record: circuit, defaultbasefreq, voltagebases (E10)
    slots.py          Slot, check_slots, slots_table
    vsource.py        EnergySource -> Vsource (one module per DSS class from here on)
```

- **`DssExporter().to_model(network, *, name_source=None, circuit_source="source") -> DssModel`.** It runs each
  module of `EXPORT_ORDER` over its CIM classes and adds the records. `history` stays empty: it is a reader
  artifact.
- Each module has `export(obj, context) -> list[record]` and `SLOTS`, which names each slot of its DSS class as
  `written` (from which getter), `rule` (a CIM `None` DSS needs, E4), `unset` (CIM cannot hold it; engine default)
  or `not mapped`. A test checks that `SLOTS` covers every schema slot, as `check_fields` does on import, and the
  tables below are generated from it.
- `context` (`ExportContext`) holds the network, the `Names` and the circuit's EnergySource. Nothing else is shared
  between modules.
- Conducting equipment of a class no module exports raises, with the counts (`no DSS export yet for
  {'ACLineSegment': 1, ...}`), so nothing is dropped silently while the sub-slices land.
- Values the exporter cannot read through an existing getter got one: `getters/in_service.get_in_service(equipment,
  which='actual'|'normal')` (unset is None), the pattern of `get_switch_state`. DSS `enabled` reads `'normal'`, the
  importer's `normallyInService`.

### Names (E1)

- **Core**, `cimhub_core/names.py`:
  - `NAME_SOURCES = ("name", "mrid", "uri")` and `NAME_SOURCE_ENV = "CIMHUB_NAME_SOURCE"`;
  - `resolve_name_source(source)`: the argument, else the env var, else `"mrid"`. Any other value raises;
  - `export_name(obj, source) -> str`: `obj.name`, `obj.mRID` or `obj.uri()` (the stable UUID: fixed length, which
    GridLAB-D's name-reference limit needs). Unset or blank raises, naming the class and mRID.

  Every exporter (GLM, RAW, ...) uses the same three.
- **Spoke**, `exporter/naming.py`, `Names(source)`:
  - `name(obj, dss_class)` returns `dss_safe_name(export_name(obj, source))` (the writer's sanitizer, which stays in
    the writer: it sanitizes every name it writes, idempotently). `bus(node)` also replaces `.`, DSS's node
    delimiter.
  - It records the name per DSS class, lowercased. A second object on the same name raises, naming both mRIDs.
    Buses (ConnectivityNodes) are one namespace of their own.
- **The circuit:**
  - Its name is the one Feeder's, by the same switch. No Feeder, or several, raises.
  - Its source's Vsource is always named `source`, whatever the switch: that is DSS's name for `New Circuit`'s
    source (the reader's rule).
  - The circuit source is the only EnergySource, or the one whose exported name is `circuit_source` (E2). Several
    EnergySources and no match raises.
- **E8's per-phase objects** are named `<name>_<phase>` (lowercase phase, `ld_x_a`) through the same check.

### Bus references (E7, S6a part)

`bus_ref(terminal, names)` returns `<bus>.<n>...`:
- the bus is `names.bus(get_terminal_nodes(eq)[i])`;
- the nodes are `get_terminal_phases` in conductor order, A/B/C → 1/2/3 and s1/s2 → 1/2;
- a blank (balanced) PhaseCode is ABC, written `.1.2.3`, never bare.

S6a needs only phase conductors (Vsource). The neutral cases (`.0`, `.4`, `Rneut`) arrive with the windings in S6c,
and an `N` before then raises.

### Options (E10)

One `Options(name="options", circuit=..., defaultbasefreq=..., voltagebases=[...])` record:
- `defaultbasefreq` = `network.base_frequency` in Hz;
- `voltagebases` = the distinct `BaseVoltage.nominalVoltage` values in kV, sorted ascending;
- `earthmodel` not set (engine default);
- `open_terminals` filled by S6b's switches.

`network.base_frequency` follows the graph's `BaseFrequency` (U14, closed 2026-11-09 in CIM-Graph), so a 50 Hz
model writes `defaultbasefreq=50`. An atom at 50 Hz pins it.

### Vsource

One `Vsource` per `EnergySource`, through `get_source(es, angle_unit="deg", voltage_unit="kV",
impedance_unit="ohm")`. **The impedance form depends on the phases (found in implementation, engine-checked):**
- **3-phase:** the ohms group R1 X1 R0 X0, the importer's copied form.
- **1-phase:** the engine forces Z0 = Z1 when a 1-phase source is given ohms, so its single impedance is Z1. Given
  MVAsc it is (2 Z1 + Z0) / 3. The importer reads a 1-phase source's MVAsc into Z1 and Z0, so the exporter writes
  the MVAsc group back: MVAsc3 = kV²/abs(Z1), MVAsc1 = 3 kV²/abs(2 Z1 + Z0), x1r1 = X1/R1, x0r0 = X0/R0.
  `short_circuit_from_thevenin` is the exact inverse of the importer's `thevenin_from_short_circuit` (tested to
  1e-12). A zero r or r0 raises. The atom `single_phase` showed this: its ohms export had another YPrim.

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names; the circuit's source is always `source` |
| bus1 | written | bus_ref(get_terminal_nodes, get_source.phases) |
| basekv | written | get_source.nominal_u (kV) |
| pu | written | get_source.magnitude_pu |
| angle | rule | get_source.angle (deg); unset -> 0, the reference angle |
| phases | written | the phase conductors: 3 or 1, any other count raises |
| R1 | written | 3-phase: get_source.impedance.r (ohm); r, x, r0, x0 unset raises (DSS takes one group) |
| X1 | written | 3-phase: get_source.impedance.x (ohm) |
| R0 | written | 3-phase: get_source.impedance.r0 (ohm) |
| X0 | written | 3-phase: get_source.impedance.x0 (ohm) |
| MVAsc3 | written | 1-phase: kV^2 / abs(Z1) (short_circuit_from_thevenin) |
| MVAsc1 | written | 1-phase: 3 kV^2 / abs(2 Z1 + Z0) |
| x1r1 | written | 1-phase: x / r; r = 0 raises |
| x0r0 | written | 1-phase: x0 / r0; r0 = 0 raises |
| enabled | written | get_in_service(which='normal'); unset -> not written |
| Isc3 | not mapped | not written: the ohms or the MVAsc group carries the same impedance |
| Isc1 | not mapped | not written: the ohms or the MVAsc group carries the same impedance |
| Z1 | not mapped | not written: the ohms or the MVAsc group carries the same impedance |
| Z0 | not mapped | not written: the ohms or the MVAsc group carries the same impedance |
| Z2 | not mapped | r2/x2 set and different from r/x raises: the Z2 group is not mapped (nor imported) |
| puZ1 | not mapped | not written: the ohms or the MVAsc group carries the same impedance |
| puZ0 | not mapped | not written: the ohms or the MVAsc group carries the same impedance |
| puZ2 | not mapped | not written: the ohms or the MVAsc group carries the same impedance |
| baseMVA | not mapped | not written: the ohms or the MVAsc group carries the same impedance |
| frequency | unset | Options.defaultbasefreq is the deck's |
| basefreq | unset | Options.defaultbasefreq is the deck's |
| ScanType | unset | not in CIM (untranscribed on import) |
| Sequence | unset | not in CIM (untranscribed on import) |
| spectrum | unset | not in CIM (untranscribed on import) |
| Yearly | unset | not in CIM (untranscribed on import) |
| Daily | unset | not in CIM (untranscribed on import) |
| Duty | unset | not in CIM (untranscribed on import) |
| Model | unset | not in CIM (untranscribed on import) |
| puZideal | unset | not in CIM (untranscribed on import) |
| bus2 | not mapped | an EnergySource has one terminal |
| like | not mapped | the writer never writes like= |

### Writer changes (§8.2)

- `WRITE_ORDER`: a class-level list of the DSS classes in definition order. Catalogs (WireData, CNData, TSData,
  LineSpacing, LineGeometry, LineCode, XfmrCode), Vsource, Line, Fuse, Recloser, SwtControl, Transformer,
  RegControl, Load, Capacitor, CapControl, PVSystem, Storage, Generator, Reactor. A class in the model that is not on
  the list raises.
- `write(model, destination)` emits, in order:
  1. `Clear`;
  2. `Set defaultbasefreq=<f>`;
  3. `New Circuit.<circuit>` with the slots of `Vsource.source`;
  4. the records in `WRITE_ORDER` (`Vsource.source` not again);
  5. `Set voltagebases=[...]`;
  6. `CalcVoltageBases`;
  7. `Open <Class>.<name> <terminal>` per `open_terminals`;
  8. `Buscoords <stem>_buscoords.csv` (`LatLongCoords` for geographic rows), with the CSV written beside the deck.
- `serialize(obj)` is unchanged for an ordinary record. `Options` and `Buscoords` are not ordinary records, so
  `serialize` raises on them, and `write` handles them as above.

**Found by the round-trip test** (atoms and the IEEE13_CDPSM, IEEE123, IEEE4 OYOD decks; each is engine-checked):
- **`like=` is never written.** The reader has already copied the other object's values into the record. `like=`
  written after them (schema order) copied reg4a back over IEEE123's reg4b/reg4c (buses, R, X).
- **Some slots go first** (`_LEADING_SLOTS`): `XfmrCode`, `linecode`, `geometry`, `spacing`, `phases`, `Switch`. A
  template set after `buses=` re-sizes the windings and resets their buses (IEEE13 `Tpoletop`'s third winding
  became `tpoletop_3`), and `Switch=y` sets r1=1, x1=1, .... `phases` goes before `Switch`, as the decks write it:
  the engine's recalculation of a switch line at `CalcVoltageBases` depends on that order (IEEE13 `Sect1`).
- **A LineGeometry with positions is written as `cond=` blocks**, each naming its conductor's kind (`wire`,
  `cncable`, `tscable`) from the catalog that defines the name. The reader folds the blocks into
  `wires`/`xs`/`hs` (mixed kinds into one cond-ordered `wires` list) and leaves the last block in the cursor slots.
  Only blocks can mix kinds (IEEE13_Assets 607: a TS phase and a bare neutral). `serialize` raises on one, because
  the kinds need the model's catalogs.
- **`Set earthmodel` goes after `New Circuit`:** the engine refuses it before. `defaultbasefreq` stays before.
- **Matrices at full precision** (`repr`); `.6g` changed every value past 6 digits.
- **A deck without a circuit** (a catalog fragment, which the reader also reads) is written without one. Only one
  of `Options.circuit` and `Vsource.source` raises.
- `Relay` joins `WRITE_ORDER` after Line (IEEE13_CDPSM has one).

### Tests

- **Writer round trip** (`tests/test_dss_writer.py`): every atom deck, plus IEEE13_CDPSM, IEEE123 and IEEE4 OYOD, is
  read, written and read again, and gives equal records (`like` dropped; `history` excluded). The three decks are
  also compared in the engine (`tests/engine_compare.py`, shared by every export test):
  - per element, its buses (bus names and `NodeOrder`) and YPrim (rel 1e-9);
  - the node voltages, solved with `controlmode=off tolerance=1e-10` (rel 1e-8 + 10 µV). Solution settings are not
    part of the model, so the reader drops them; the tight tolerance makes both decks converge to one answer.
- **Names:** core precedence (argument > env var > `mrid`), a bad value raises, an unset name raises, `uri` is 36
  characters. Spoke: sanitizing, dots in bus names, a collision after sanitizing raises, namespaces are separate,
  the per-phase suffix.
- **Framework:** options, unexported equipment raises, and `circuit_source` with two sources (its collision with
  the other source's own name `source` raises under `name`).
- **Vsource per atom** (`mvasc`, `ohms`, `isc`, `defaults`, `single_phase`, and a new `fifty_hz`), each exported and
  compared with the original in the engine:
  - under `name`: the source's R1 X1 R0 X0 basekv pu angle phases (rel 1e-9), every element's YPrim, the voltages;
  - under `mrid` and `uri`: the voltages, with the buses renamed under `uri`.
- **Goldens:** `tests/atoms/vsource/export/<atom>.dss` (`name_source="mrid"`).
