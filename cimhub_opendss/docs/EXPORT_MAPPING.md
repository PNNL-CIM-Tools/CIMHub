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
- **Matrices at full precision**; `.6g` changed every value past 6 digits. Since S6b every float is written at 15
  significant digits (`FLOAT_DIGITS`, see S6b's goldens note).
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

## S6b: lines, wire catalogs, switches (spec approved 2026-11-09 with B3 and B6 amended; done 2026-11-09)

Content: WireData/CNData/TSData, LineGeometry, LineCode, Line, and switches (a `Switch=y` Line plus a Fuse, Recloser
or SwtControl, and `Open`), with the line ratings. Plan §8.1 row S6b; E3, E5, E6 and E7 apply. Decisions B1-B6
are at the end of this section.

### Layout

```
cimhub_opendss/src/cimhub_opendss/exporter/
    wire.py           OverheadWireInfo / ConcentricNeutralCableInfo / TapeShieldCableInfo -> Wiredata / Cndata / Tsdata
    linecode.py       PerLengthPhaseImpedance / PerLengthSequenceImpedance -> Linecode
    linegeometry.py   (WireConfiguration, spacingYOffset) -> Linegeometry, inline positions (B2)
    line.py           ACLineSegment -> Line
    switch.py         Switch subclasses -> Line Switch=y + Fuse / Recloser / Swtcontrol; open_terminals()
```

`EXPORT_ORDER` becomes `(vsource, wire, linecode, linegeometry, line, switch)`. The writer's `WRITE_ORDER` already
puts catalogs before lines and controls after them. `options_record` fills `open_terminals` from
`switch.open_terminals(context)`.

**Framework change (found in implementation):**
- **A module exports from the whole network.** Its protocol is now `export(context) -> list[record]`, not
  `export(obj, context)`, because a LineGeometry is one record per (configuration, offset) among the lines.
  `ExportContext.objects(*classes)` lists a module's CIM objects.
- **`SLOTS` is `{DSS class: {slot: Slot}}`**, for the modules that write several classes (wire, switch).
  `test_export_framework.test_slots_are_complete` checks every module in `EXPORT_ORDER`.
- **A record shared by several objects** (a code, a wire, a geometry) is named through one function: `wire_name`,
  `linecode_name`, `geometry_name` or `switch_name`. `Names` gives an object the same name again, so a Line names
  its LineCode exactly as the LineCode record does.

### New getters and derived functions (core)

- **`getters/wire.py`**
  - **`get_wire_info(wire, length_unit="m", resistance_unit="ohm/m", current_unit="A") -> WireValues`.** It reads
    `rDC20`, `rAC25`, `gmr` and `radius`, and the ratings: `ratedCurrent`, and the `CurrentLimits` of the wire's
    `AssetInfo.OperationalLimitSet` (normal, emergency). `ratedCurrent` and a normal limit that are both set must
    agree. A cable also gets `cable: CableValues`:
    - `insulationThickness`, and the diameters over insulation, jacket, neutral and screen;
    - CN: `neutralStrandCount`, `neutralStrandRadius`, `neutralStrandGmr`, `neutralStrandRDC20`;
    - TS: `tapeThickness`, `tapeLap`.

    Unset is None. Any other WireInfo subclass raises. A set `rAC50`/`rAC75` raises: only rAC25 is read until a
    producer writes the others.
  - **`get_configuration_wires(configuration) -> tuple[(sequence_number, WireInfo), ...]`.** These are the
    `WireSequenceConfiguration`s in sequence-number order. A repeated or missing number raises.
- **`getters/line_impedance.py`**, code-level getters (B5): `get_phase_impedance_code(code, impedance_unit,
  admittance_unit) -> CodeMatrix(conductor_count, r, x, b, g)` and `get_sequence_impedance_code(code, ...) ->
  SequenceImpedance`. They read a catalog object on its own, so a code no line uses is still exported. The line
  phase-matrix getter shares their reading (`_matrix_values`), with no change in behaviour.
- **`derived/capacitance.py`** (E5, closes the G3 open point): `c_from_b(b, frequency)` = b / (2 pi f), with b in nS
  and f in Hz giving C in nF. Its inverse `b_from_c` moved here from the importer's `linecode.py`. The units go with
  the values: the caller reads b with `get_qty` in `nS/m` and gets nF/m. Found in implementation: E5's
  `cim.Capacitance(...).to('nF')` gives 0.9999999999999999 nF for 1e-9 F, so the conversion is left to `get_qty`.
- **`getters/current_limits.py`:** `get_asset_info_current_limits(info)` reads a catalog's limits through the same
  code as `get_current_limits`. `AssetInfo.OperationalLimitSet` is single-valued (one set), unlike
  `Equipment.OperationalLimitSet`.

### Units (B1)

Every length goes into the deck in metres:
- Line `units=m`, LineCode `units=m`;
- LineGeometry position `units=m`;
- WireData/CNData/TSData `Runits=m GMRunits=m radunits=m`.

Each value is read with `get_qty` in its metre-based unit (`ohm/m`, `nF/m`, `m`). CIM keeps no record of the
deck's own units, and one fixed unit makes a second export the same text (S6f idempotence).

### Wire catalogs

One record per WireInfo in the network, used or not (E3). The three DSS classes share one name namespace (`wire`):
a LineGeometry's conductor list names a wire without saying its catalog, so the writer's `_conductor_kinds` needs
each name in only one catalog.

| DSS slot | from |
|---|---|
| Rdc / Rac | rDC20 / rAC25 (ohm/m). Each is written when set; both unset raises. Rac unset is the engine's 1.02 x Rdc, the importer's rule inverted |
| GMRac | gmr (m). Unset is left unset, and the engine takes 0.7788 x radius (E4) |
| radius | radius (m), required. `diam` is never written |
| normamps / emergamps | the wire's normal / emergency limit, else ratedCurrent for normamps. emergamps unset is left unset: the engine's 1.5 x normamps |
| CN `k`, `DiaStrand`, `GmrStrand`, `Rstrand` | neutralStrandCount, 2 x neutralStrandRadius, neutralStrandGmr, neutralStrandRDC20 |
| CN `DiaCable` | diameterOverNeutral, which the engine uses as the circle of the strands. Unset raises. The importer writes the jacket diameter equal to it |
| TS `DiaShield` | diameterOverScreen + 2 x tapeThickness (the importer's `screen_diameter` inverted) |
| TS `TapeLayer`, `TapeLap` | tapeThickness, tapeLap |
| `InsLayer`, `DiaIns` | insulationThickness, diameterOverInsulation |
| TS `DiaCable` | diameterOverJacket |
| `EpsR`, `Capradius`, `SemiconLayer`, `Seasons`, `Ratings` | unset: not in CIM (the importer's untranscribed or raising fields) |

### LineCode

One record per PerLengthImpedance in the network (E3). `baseFreq` is `network.base_frequency`. A code whose
`calculatedFrequency` is set and differs from it raises: C is computed at the deck's frequency.
- **Phase code:**
  - nphases = `conductorCount`;
  - rmatrix / xmatrix = r / x as lower triangles (ohm/m);
  - cmatrix = C from b (nF/m). An unset b gives zeros, so the engine's 3.4/1.6 nF default never applies (rule 8).
- **Sequence code:**
  - nphases = 3;
  - r1, x1, r0, x0 (ohm/m). An unset r0 or x0 raises: DSS would take its own default;
  - C1, C0 from bch, b0ch. Unset gives 0.

  The importer stores 1- and 2-phase sequence codes as phase matrices (DSS-4), so they come back as matrix codes.
  A line with other than 3 phases on a sequence code raises (DSS-10's mismatch, from the CIM side).
- **Raises:**
  - g, gch or g0ch set and nonzero (DSS lines have no shunt conductance);
  - `rg`/`xg` set (not mapped on import either);
  - a matrix entry with a neutral row: a code-line neutral needs LineCode `Kron`/`neutral`, and no producer writes one.
- **Not written:** normamps and emergamps (no home on PerLengthImpedance, D9), which come from the Line instead.
  The reliability, `Kron`, `neutral` and `Seasons` slots stay unset.

### LineGeometry (B2)

- **One record per (WireConfiguration, spacingYOffset)** among the lines (E3). It is named
  `<configuration>` at offset unset or 0, and `<configuration>_<offset>m` otherwise (offset in m, `.` written as
  `p`).
- **A WireConfiguration no line uses** is written once, with its spacing's positions as stored (offset 0, the CIM
  default).
- **Positions:**
  - `get_line_conductor_xy(line)`, or `get_spacing_xy` for an unused configuration, in m. They are written as `xs`
    / `hs` with the conductor names in `wires`, and the writer emits the cond blocks;
  - the wires are matched to positions by sequence number from `get_configuration_wires`.
- **The other slots:**
  - nconds = the positions;
  - nphases = `numberOfPhases` (required). Position kinds, where set, must be `phase` for 1..nphases and `neutral`
    after;
  - `reduce=y`: the neutrals are Kron-reduced, i.e. grounded at both ends, as the impedance getters assume (G2;
    242 of 243 sweep geometries set it). The import left `reduce` untranscribed for that reason.
- **Raises:**
  - a line with `ACLineSegment.WireSpacing` and no WireConfiguration, or per-phase `ACLineSegmentPhase.WireInfo`.
    No producer writes either: the DSS importer turns `spacing=` + `wires=` into a WireConfiguration (B2);
  - a phase count on the line other than nphases.
- **The importer's spacing sharing.** The importer shares `spc_500` among 601, 602, ...; each geometry now carries
  its own positions, so a re-import gives `wc_<name>_spc` per geometry. That is a listed difference, equal in the
  engine.

### Line

One record per ACLineSegment (a Switch is not an ACLineSegment; switch.py).

| DSS slot | from |
|---|---|
| bus1 / bus2 | `bus_ref` over `get_terminal_nodes`, with the phase conductors of `get_conductor_phases` in order (645 CB is `.3.2`). The neutral is not on the bus: it is reduced (B4) |
| phases | the phase conductors' count |
| linecode / geometry | the code's name, or the (configuration, offset) geometry's name. Geometry wins when both are set (skill `conductor-geometry`) |
| length, units | `required_qty(line, "length", "m")`, `units=m` |
| normamps / emergamps | `get_current_limits(line)` normal / emergency. Unset is left unset, and the engine copies the code's or geometry's. `short_term` and seasonal limits are not mapped |
| enabled | `get_in_service(which="normal")`; unset is not written |

- **A lumped-only line** (B6, the user's rule): `r`/`x` on the segment and no template. It is written inline:
  - `r1 x1 r0 x0` = the whole-line values divided by the length, in ohm/km "for better decimal places";
  - `C1 C0` from `bch`/`b0ch` the same way (nF/km);
  - `length` in km with `units=km`. A line with no length gets `length=1`, so the per-km values are the whole-line
    values.

  The values come from `get_line_sequence_impedance(line, "ohm")` (`LUMPED`). An unset b is C = 0 (rule 8). An
  unset r0/x0 raises, as on a sequence code. A set and nonzero `gch`/`g0ch` raises.
- **Inline values are never written.** The importer's synthesized `ln_<line>_lc` comes back as a LineCode (E3,
  listed).

### Switches (E6)

One `Line` with `Switch=y` per Switch subclass:
- bus1/bus2 and phases as a Line; a blank PhaseCode is `.1.2.3`;
- `normamps`/`emergamps` from `get_current_limits` (the importer writes none);
- `enabled`;
- a small invented impedance (B3, the user's rule), because CIM has none (DSS-8): `r1=1e-3 r0=1e-3 x1=0 x0=0 C1=0
  C0=0 length=1 units=m`, i.e. 1 mOhm. 1e-3 Ohm is the old exporter's zero-impedance floor (`_zero_impedance.py`),
  and it is resistive only, as the IEEE decks write their switches. The slots come after `Switch=y`
  (`_LEADING_SLOTS`), so they replace the engine's `Switch=y` defaults. It is one constant, `SWITCH_IMPEDANCE`, in
  `switch.py`.

The control depends on the class:
- **`Fuse`:** `Fuse.<name> MonitoredObj=Line.<name> RatedCurrent=<ratedCurrent A>`. Its `Normal`/`State` are written
  one value per phase (`[open open open]`). **Engine finding:** the engine sets a fuse phase by phase, so
  `State=open` on a 3-phase line opens phase 1 only (atom `states`, first draft: n1.1 at 75 V, n1.2 and n1.3 at
  2402 V). **Importer fix:** a Fuse whose `Normal`/`State` give a value count other than its line's phases now
  raises. CIM's `open` is the whole switch's, and the importer had read `State=open` as all three phases open. No
  sweep deck sets a Fuse state.
- **`Recloser`:** `Recloser.<name> MonitoredObj=Line.<name>`. The protection settings are untranscribed on import
  (DSS-11).
- **Any other class** (LoadBreakSwitch, Breaker, Disconnector, Sectionaliser, Jumper):
  `SwtControl.<name> SwitchedObj=Line.<name>`, written only when the switch is open in either state.

The state:
- `get_switch_state(which="normal")` → the control's `Normal=open|closed`;
- `which="actual"` → `State=open|closed`, plus `Open Line.<name> 1` in `Options.open_terminals` when open (the
  importer's rule inverted).

A Fuse or Recloser closed in both states writes neither. A one-terminal switch (GroundDisconnector) raises. The
class is lossy on the way back: Breaker, Disconnector, Sectionaliser and Jumper come back as LoadBreakSwitch
(DSS-9, listed).

### Tests

As built (`tests/test_export_line.py`, 34 tests; core `test_getters_wire.py`, `test_derived_capacitance.py`, and
code-level tests in `test_getters_line_impedance.py`):
- **Per atom, in the engine** (§8.3, `engine_compare`): `line/codes`, `line/geometry`, and two new atoms:
  - `line/cables.dss`: the IEEE13_Assets CN and TS geometries 606/607 (607 mixes a TS phase and a bare neutral), the
    IEEE8500 sequence code, and an unused wire and code;
  - `line/states.dss`: an open Fuse (one state per phase), an open Recloser, and a SwtControl with `Normal=open
    State=closed`.

  Each atom is exported under `name`. Per element it checks buses, NodeOrder and YPrim (rel 1e-9), then the
  voltages (rel 1e-8). Under `mrid` and `uri` only the voltages are checked. `assert_same_engine_state` takes the
  listed exceptions:
  - `yprim_differs`: every switch, because the deck's stand-in (`r1=1e-4`, or the `Switch=y` defaults) is not the
    exporter's 1 mOhm (B3). Nothing flows through them in the atoms, so the voltages agree to 1e-9;
  - `added`: the SwtControl of `codes`' `sect` (E6). The Recloser settings have no element of their own.

  Every line by code, by geometry and by cable has the original's YPrim to rel 1e-9.
- **The CIM fixed point for catalog-only atoms is dropped (found in implementation).** `linecode/mtx601`,
  `linecode/seq_3_1_0c`, `wire/*` and `geometry/assets` have no `New Circuit`, so the importer cannot make a
  network of them. The `cables` atom puts every catalog kind on a line instead, so the engine sees each one.
- **Engine catalog values** (`cables`): every WireData/CNData/TSData property of the export equals the original's in
  the engine, each converted to metres by its own unit selector (rel 1e-9).
- **Getters:** `get_wire_info` (the three kinds, ratings agreement, rAC50 raises), `get_configuration_wires`,
  `get_asset_info_current_limits`, the code-level impedance getters, and `c_from_b` as the inverse of `b_from_c`
  (1e-12).
- **Lumped lines:** the `codes` network with `seq2`'s code replaced by its whole-line lumped values, with and without
  a length. Exported, its YPrim equals the original's (rel 1e-9).
- **Spoke unit tests:**
  - the offset geometry name;
  - unused codes, wires and configurations are written;
  - each raise listed above;
  - the switch-control matrix (class x states).
- **Deck round trip:** IEEE13_CDPSM through import → export → engine, element by element. It is not a gate: its
  transformers wait for S6c. So it runs only once S6c lands, and S6b's exit is the atoms.
- **Goldens:** `tests/atoms/line/export/*.dss` (mrid).
- **Float tails clipped (the user, 2026-11-09).** The unit conversions left binary tails
  (`x0=0.0018000000000000002`). Every float the writer writes is now `format_float`, 15 significant digits in the
  shortest form (`0.0018`, `60`, `1e-05`). The LineCode slots the schema types as text (`C1`, `C0`, `baseFreq`) are
  formatted by the exporter the same way. The cost is 1e-15 relative: IEEE8500's `X=14.798306633595042` is written
  `14.798306633595`. The writer round-trip test therefore compares records at the writer's precision, and the
  engine round trips (IEEE13_CDPSM, IEEE123, IEEE4) are unchanged.
- **Test harness fix:** `Set defaultbasefreq` outlives `Clear` in the engine. After the 50 Hz Vsource atom, a deck
  without its own frequency compiled at 50 Hz, and the IEEE13_CDPSM round trip failed when it ran after it.
  `conftest.compile_deck` now sets 60 Hz after `Clear`.

### Decisions for S6b (approved 2026-11-09)

| # | question | decision |
|---|---|---|
| B1 | Deck units | Every length in metres (Line/LineCode `units=m`, geometry `units=m`, wire `Runits/GMRunits/radunits=m`); B6's lumped lines are the one exception |
| B2 | Geometry form | Inline positions (cond blocks) per (WireConfiguration, offset); no LineSpacing is written. A bare-spacing line raises until a producer writes one |
| B3 | Switch impedance (amended by the user) | A small invented impedance: 1 mOhm resistive, `r1=r0=1e-3 x1=x0=0 C1=C0=0 length=1 units=m` |
| B4 | Line neutrals (rationale given to the user 2026-11-09; implemented as recommended, pending their word) | Geometry `reduce=y`, and the neutral is not written on the bus. Engine probe (2026-11-09, geometry 601 under an unbalanced load): `reduce=y` gives the same voltages, to 1e-9 V, as `reduce=n` with the neutral on node 0 at both ends. So `reduce=y` is exactly a neutral grounded at both ends, and it keeps a 3x3 YPrim. `reduce=n` on a `.1.2.3` bus puts the neutral on node 4, ungrounded: it floats (292 V in the probe), and the phase voltages move by up to 4 %. CIM has no per-conductor neutral grounding to export, so `reduce=n` has nothing to carry. A code line with a neutral row raises |
| B5 | Code values | Code-level getters; a code no line uses is still exported |
| B6 | Lumped-only lines (amended by the user) | Written inline: the whole-line values divided by the length, `r1 x1 r0 x0` in ohm/km and `C1 C0` in nF/km, `units=km`; with no length, `length=1` |

### Slot tables (generated from `SLOTS`)

**Wiredata** (`exporter/wire.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, one namespace for the three catalogs |
| Rdc | written | get_wire_info.r_dc20 (ohm/m); Rdc and Rac both unset raises |
| Rac | rule | get_wire_info.r_ac25 (ohm/m); unset -> not written, the engine's 1.02 x Rdc |
| Runits | written | m (B1) |
| GMRac | rule | get_wire_info.gmr (m); unset -> not written, the engine's 0.7788 x radius |
| GMRunits | written | m (B1) |
| radius | written | get_wire_info.radius (m); unset raises |
| radunits | written | m (B1) |
| normamps | written | the wire's normal limit, else ratedCurrent (A) |
| emergamps | rule | the wire's emergency limit (A); unset -> not written, the engine's 1.5 x normamps |
| diam | not mapped | radius is written instead |
| Seasons | unset | not in CIM (untranscribed or raising on import) |
| Ratings | unset | not in CIM (untranscribed or raising on import) |
| Capradius | unset | not in CIM (untranscribed or raising on import) |
| like | not mapped | the writer never writes like= |

**Cndata** (`exporter/wire.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, one namespace for the three catalogs |
| Rdc | written | get_wire_info.r_dc20 (ohm/m); Rdc and Rac both unset raises |
| Rac | rule | get_wire_info.r_ac25 (ohm/m); unset -> not written, the engine's 1.02 x Rdc |
| Runits | written | m (B1) |
| GMRac | rule | get_wire_info.gmr (m); unset -> not written, the engine's 0.7788 x radius |
| GMRunits | written | m (B1) |
| radius | written | get_wire_info.radius (m); unset raises |
| radunits | written | m (B1) |
| normamps | written | the wire's normal limit, else ratedCurrent (A) |
| emergamps | rule | the wire's emergency limit (A); unset -> not written, the engine's 1.5 x normamps |
| diam | not mapped | radius is written instead |
| Seasons | unset | not in CIM (untranscribed or raising on import) |
| Ratings | unset | not in CIM (untranscribed or raising on import) |
| Capradius | unset | not in CIM (untranscribed or raising on import) |
| like | not mapped | the writer never writes like= |
| EpsR | unset | no permittivity on CableInfo; the engine's 2.3 |
| InsLayer | written | cable.insulation_thickness (m) |
| DiaIns | written | cable.diameter_over_insulation (m) |
| k | written | cable.neutral_strand_count |
| DiaStrand | written | 2 x cable.neutral_strand_radius (m) |
| GmrStrand | written | cable.neutral_strand_gmr (m) |
| Rstrand | written | cable.neutral_strand_r_dc20 (ohm/m), CIM's only strand resistance |
| SemiconLayer | unset | not in CIM (untranscribed or raising on import) |
| DiaCable | written | cable.diameter_over_neutral (m), the circle of the strands; unset raises |

**Tsdata** (`exporter/wire.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, one namespace for the three catalogs |
| Rdc | written | get_wire_info.r_dc20 (ohm/m); Rdc and Rac both unset raises |
| Rac | rule | get_wire_info.r_ac25 (ohm/m); unset -> not written, the engine's 1.02 x Rdc |
| Runits | written | m (B1) |
| GMRac | rule | get_wire_info.gmr (m); unset -> not written, the engine's 0.7788 x radius |
| GMRunits | written | m (B1) |
| radius | written | get_wire_info.radius (m); unset raises |
| radunits | written | m (B1) |
| normamps | written | the wire's normal limit, else ratedCurrent (A) |
| emergamps | rule | the wire's emergency limit (A); unset -> not written, the engine's 1.5 x normamps |
| diam | not mapped | radius is written instead |
| Seasons | unset | not in CIM (untranscribed or raising on import) |
| Ratings | unset | not in CIM (untranscribed or raising on import) |
| Capradius | unset | not in CIM (untranscribed or raising on import) |
| like | not mapped | the writer never writes like= |
| EpsR | unset | no permittivity on CableInfo; the engine's 2.3 |
| InsLayer | written | cable.insulation_thickness (m) |
| DiaIns | written | cable.diameter_over_insulation (m) |
| DiaShield | written | cable.diameter_over_screen + 2 x tape_thickness (m): DSS measures over the tape |
| TapeLayer | written | cable.tape_thickness (m) |
| TapeLap | written | cable.tape_lap (percent) |
| DiaCable | written | cable.diameter_over_jacket (m) |

**Linecode** (`exporter/linecode.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names |
| nphases | written | phase code: conductorCount; sequence code: 3 |
| r1 | written | sequence code: r (ohm/m) |
| x1 | written | sequence code: x (ohm/m) |
| r0 | written | sequence code: r0 (ohm/m); unset raises |
| x0 | written | sequence code: x0 (ohm/m); unset raises |
| C1 | rule | sequence code: c_from_b(bch) (nF/m); unset -> 0 |
| C0 | rule | sequence code: c_from_b(b0ch) (nF/m); unset -> 0 |
| units | written | m (B1) |
| rmatrix | written | phase code: r, lower triangle (ohm/m) |
| xmatrix | written | phase code: x, lower triangle (ohm/m) |
| cmatrix | rule | phase code: c_from_b(b), lower triangle (nF/m); unset -> zeros |
| baseFreq | written | network.base_frequency (Hz); a calculatedFrequency that differs raises |
| normamps | unset | no rating on a PerLengthImpedance (D9); the Line carries its own |
| emergamps | unset | no rating on a PerLengthImpedance (D9); the Line carries its own |
| faultrate | unset | not in CIM (untranscribed on import) |
| pctperm | unset | not in CIM (untranscribed on import) |
| repair | unset | not in CIM (untranscribed on import) |
| Kron | unset | not in CIM (untranscribed on import) |
| Rg | not mapped | PerLengthImpedance.rg set raises (not imported either) |
| Xg | not mapped | PerLengthImpedance.xg set raises (not imported either) |
| rho | unset | not in CIM (untranscribed on import) |
| neutral | unset | not in CIM (untranscribed on import) |
| B1 | not mapped | C1 carries the susceptance |
| B0 | not mapped | C0 carries the susceptance |
| Seasons | unset | not in CIM (untranscribed on import) |
| Ratings | unset | not in CIM (untranscribed on import) |
| LineType | unset | not in CIM (untranscribed on import) |
| like | not mapped | the writer never writes like= |

**Linegeometry** (`exporter/linegeometry.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names; <configuration> at offset 0, <configuration>_<offset>m otherwise ('.' as 'p') |
| nconds | written | the spacing's positions |
| nphases | written | WireConfiguration.numberOfPhases, required; position kinds phase then neutral |
| cond | not mapped | the writer folds wires/xs/hs into cond= blocks |
| wire | not mapped | the writer folds wires/xs/hs into cond= blocks |
| x | not mapped | the writer folds wires/xs/hs into cond= blocks |
| h | not mapped | the writer folds wires/xs/hs into cond= blocks |
| units | written | m (B1) |
| normamps | unset | no rating on a WireConfiguration (D9); the Line carries its own |
| emergamps | unset | no rating on a WireConfiguration (D9); the Line carries its own |
| reduce | written | y: the neutrals grounded at both ends, as the impedance getters assume (B4) |
| spacing | not mapped | positions are written inline (B2) |
| wires | written | get_configuration_wires, by sequence number; any of the three catalogs |
| cncable | not mapped | the writer folds wires/xs/hs into cond= blocks |
| tscable | not mapped | the writer folds wires/xs/hs into cond= blocks |
| cncables | not mapped | wires carries every kind (the writer names each block's kind) |
| tscables | not mapped | wires carries every kind (the writer names each block's kind) |
| xs | written | get_line_conductor_xy x (m); an unused configuration: get_spacing_xy |
| hs | written | get_line_conductor_xy y, above ground (m) |
| Seasons | unset | not in CIM (untranscribed on import) |
| Ratings | unset | not in CIM (untranscribed on import) |
| LineType | unset | not in CIM (untranscribed on import) |
| conductors | not mapped | wires carries the names |
| like | not mapped | the writer never writes like= |

**Line** (`exporter/line.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names |
| bus1 | written | bus_ref(get_terminal_nodes[0], the phase conductors of get_conductor_phases) |
| bus2 | written | bus_ref(get_terminal_nodes[1], the same phases) |
| linecode | written | the PerLengthImpedance's LineCode name |
| length | written | required_qty(length, m); lumped: km, unset -> 1 |
| phases | written | the phase conductors (a neutral is reduced, B4) |
| r1 | written | lumped only (B6): the whole-line value / length in km (ohm/km) |
| x1 | written | lumped only (B6): the whole-line value / length in km (ohm/km) |
| r0 | written | lumped only (B6): the whole-line value / length in km (ohm/km); unset raises |
| x0 | written | lumped only (B6): the whole-line value / length in km (ohm/km); unset raises |
| C1 | rule | lumped only (B6): the whole-line value / length in km, c_from_b(bch) (nF/km); unset -> 0 |
| C0 | rule | lumped only (B6): the whole-line value / length in km, c_from_b(b0ch) (nF/km); unset -> 0 |
| rmatrix | not mapped | a phase matrix is always a LineCode |
| xmatrix | not mapped | a phase matrix is always a LineCode |
| cmatrix | not mapped | a phase matrix is always a LineCode |
| Switch | not mapped | a Switch is exported by switch.py |
| Rg | unset | not in CIM (untranscribed or raising on import) |
| Xg | unset | not in CIM (untranscribed or raising on import) |
| rho | unset | not in CIM (untranscribed or raising on import) |
| geometry | written | the (WireConfiguration, spacingYOffset) LineGeometry name |
| units | written | m (B1); lumped: km (B6) |
| spacing | not mapped | a line with WireSpacing and no WireConfiguration raises (B2) |
| cncables | not mapped | per-phase ACLineSegmentPhase.WireInfo raises (B2) |
| tscables | not mapped | per-phase ACLineSegmentPhase.WireInfo raises (B2) |
| wires | not mapped | per-phase ACLineSegmentPhase.WireInfo raises (B2) |
| EarthModel | unset | not in CIM (untranscribed or raising on import) |
| B1 | not mapped | C1 carries the susceptance |
| B0 | not mapped | C0 carries the susceptance |
| Seasons | unset | not in CIM (untranscribed or raising on import) |
| Ratings | unset | not in CIM (untranscribed or raising on import) |
| LineType | unset | not in CIM (untranscribed or raising on import) |
| EpsRmedium | unset | not in CIM (untranscribed or raising on import) |
| HeightOffset | not mapped | spacingYOffset goes into the geometry's heights |
| HeightUnit | not mapped | spacingYOffset goes into the geometry's heights |
| conductors | unset | not in CIM (untranscribed or raising on import) |
| normamps | rule | get_current_limits normal (A); unset -> not written, the engine copies the catalog's |
| emergamps | rule | get_current_limits emergency (A); unset -> not written, as normamps |
| faultrate | unset | not in CIM (untranscribed or raising on import) |
| pct_perm | unset | not in CIM (untranscribed or raising on import) |
| repair | unset | not in CIM (untranscribed or raising on import) |
| basefreq | unset | Options.defaultbasefreq is the deck's |
| enabled | written | get_in_service(which='normal'); unset -> not written |
| like | not mapped | the writer never writes like= |

**Line** (`exporter/switch.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, the Line namespace (shared with ACLineSegments) |
| bus1 | written | bus_ref, as a Line |
| bus2 | written | bus_ref, as a Line |
| linecode | unset | a switch has no other line data (DSS-8) |
| length | rule | SWITCH_IMPEDANCE: CIM has no switch impedance (B3, 1 mOhm) |
| phases | written | the phase conductors |
| r1 | rule | SWITCH_IMPEDANCE: CIM has no switch impedance (B3, 1 mOhm) |
| x1 | rule | SWITCH_IMPEDANCE: CIM has no switch impedance (B3, 1 mOhm) |
| r0 | rule | SWITCH_IMPEDANCE: CIM has no switch impedance (B3, 1 mOhm) |
| x0 | rule | SWITCH_IMPEDANCE: CIM has no switch impedance (B3, 1 mOhm) |
| C1 | rule | SWITCH_IMPEDANCE: CIM has no switch impedance (B3, 1 mOhm) |
| C0 | rule | SWITCH_IMPEDANCE: CIM has no switch impedance (B3, 1 mOhm) |
| rmatrix | unset | a switch has no other line data (DSS-8) |
| xmatrix | unset | a switch has no other line data (DSS-8) |
| cmatrix | unset | a switch has no other line data (DSS-8) |
| Switch | written | y |
| Rg | unset | a switch has no other line data (DSS-8) |
| Xg | unset | a switch has no other line data (DSS-8) |
| rho | unset | a switch has no other line data (DSS-8) |
| geometry | unset | a switch has no other line data (DSS-8) |
| units | rule | SWITCH_IMPEDANCE: CIM has no switch impedance (B3, 1 mOhm) |
| spacing | unset | a switch has no other line data (DSS-8) |
| cncables | unset | a switch has no other line data (DSS-8) |
| tscables | unset | a switch has no other line data (DSS-8) |
| wires | unset | a switch has no other line data (DSS-8) |
| EarthModel | unset | a switch has no other line data (DSS-8) |
| B1 | unset | a switch has no other line data (DSS-8) |
| B0 | unset | a switch has no other line data (DSS-8) |
| Seasons | unset | a switch has no other line data (DSS-8) |
| Ratings | unset | a switch has no other line data (DSS-8) |
| LineType | unset | a switch has no other line data (DSS-8) |
| EpsRmedium | unset | a switch has no other line data (DSS-8) |
| HeightOffset | unset | a switch has no other line data (DSS-8) |
| HeightUnit | unset | a switch has no other line data (DSS-8) |
| conductors | unset | a switch has no other line data (DSS-8) |
| normamps | rule | get_current_limits normal (A); unset -> not written |
| emergamps | rule | get_current_limits emergency (A); unset -> not written |
| faultrate | unset | a switch has no other line data (DSS-8) |
| pct_perm | unset | a switch has no other line data (DSS-8) |
| repair | unset | a switch has no other line data (DSS-8) |
| basefreq | unset | a switch has no other line data (DSS-8) |
| enabled | written | get_in_service(which='normal'); unset -> not written |
| like | not mapped | the writer never writes like= |

**Fuse** (`exporter/switch.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, the switch's |
| MonitoredObj | written | Line.<the switch's Line name> |
| MonitoredTerm | unset | no home on a Switch (untranscribed on import) |
| SwitchedObj | not mapped | the engine takes MonitoredObj |
| SwitchedTerm | unset | no home on a Switch (untranscribed on import) |
| FuseCurve | unset | protection setting; untranscribed on import (DSS-11) |
| RatedCurrent | written | Switch.ratedCurrent (A) |
| Delay | unset | no home on a Switch (untranscribed on import) |
| Action | unset | no home on a Switch (untranscribed on import) |
| Normal | written | get_switch_state(which='normal'); written only when open in either state; one value per phase (the engine sets a fuse per phase) |
| State | written | get_switch_state(which='actual'); written only when open in either state; one value per phase (the engine sets a fuse per phase) |
| basefreq | unset | no home on a Switch (untranscribed on import) |
| enabled | unset | no home on a Switch (untranscribed on import) |
| like | not mapped | the writer never writes like= |

**Recloser** (`exporter/switch.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, the switch's |
| MonitoredObj | written | Line.<the switch's Line name> |
| MonitoredTerm | unset | protection setting; untranscribed on import (DSS-11) |
| SwitchedObj | not mapped | the engine takes MonitoredObj |
| SwitchedTerm | unset | protection setting; untranscribed on import (DSS-11) |
| NumFast | unset | protection setting; untranscribed on import (DSS-11) |
| PhaseFast | unset | protection setting; untranscribed on import (DSS-11) |
| PhaseDelayed | unset | protection setting; untranscribed on import (DSS-11) |
| GroundFast | unset | protection setting; untranscribed on import (DSS-11) |
| GroundDelayed | unset | protection setting; untranscribed on import (DSS-11) |
| PhaseTrip | unset | protection setting; untranscribed on import (DSS-11) |
| GroundTrip | unset | protection setting; untranscribed on import (DSS-11) |
| PhaseInst | unset | protection setting; untranscribed on import (DSS-11) |
| GroundInst | unset | protection setting; untranscribed on import (DSS-11) |
| Reset | unset | protection setting; untranscribed on import (DSS-11) |
| Shots | unset | protection setting; untranscribed on import (DSS-11) |
| RecloseIntervals | unset | protection setting; untranscribed on import (DSS-11) |
| Delay | unset | protection setting; untranscribed on import (DSS-11) |
| Action | unset | protection setting; untranscribed on import (DSS-11) |
| TDPhFast | unset | protection setting; untranscribed on import (DSS-11) |
| TDGrFast | unset | protection setting; untranscribed on import (DSS-11) |
| TDPhDelayed | unset | protection setting; untranscribed on import (DSS-11) |
| TDGrDelayed | unset | protection setting; untranscribed on import (DSS-11) |
| Normal | written | get_switch_state(which='normal'); written only when open in either state |
| State | written | get_switch_state(which='actual'); written only when open in either state |
| basefreq | unset | protection setting; untranscribed on import (DSS-11) |
| enabled | unset | protection setting; untranscribed on import (DSS-11) |
| like | not mapped | the writer never writes like= |

**Swtcontrol** (`exporter/switch.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, the switch's |
| SwitchedObj | written | Line.<the switch's Line name> |
| SwitchedTerm | unset | no home on a Switch (untranscribed on import) |
| Action | unset | no home on a Switch (untranscribed on import) |
| Lock | unset | no home on a Switch (untranscribed on import) |
| Delay | unset | no home on a Switch (untranscribed on import) |
| Normal | written | get_switch_state(which='normal'); written only when open in either state |
| State | written | get_switch_state(which='actual'); written only when open in either state |
| Reset | unset | no home on a Switch (untranscribed on import) |
| basefreq | unset | no home on a Switch (untranscribed on import) |
| enabled | unset | no home on a Switch (untranscribed on import) |
| like | not mapped | the writer never writes like= |

## S6c: transformers, XfmrCode, regulators, RegControl (spec approved 2026-11-09; done 2026-11-09)

Content: every transformer form `get_transformer_model` reads, written as an inline Transformer or as an XfmrCode and
its instances; regulators and LTCs with their taps; RegControl. Plan §8.1 row S6c; DSS-2, DSS-5, DSS-13, E3 and E7
apply. Decisions T1-T7 are at the end of this section.

### Layout

```
cimhub_opendss/src/cimhub_opendss/exporter/
    windings.py      a unit's DSS winding values (model on winding 1's kVA, buses, taps), shared by the three below
    xfmrcode.py      TransformerTankConfiguration -> Xfmrcode (T5)
    transformer.py   PowerTransformer / AutoTransformer (VoltageRegulator) -> Transformer, one per unit (T4), taps
    regcontrol.py    TapChangerControl -> Regcontrol
```

`switch.py`'s slot-defaulting helper moved to `slots.with_default`, which all four modules use.

`EXPORT_ORDER` becomes `(vsource, wire, linecode, linegeometry, line, switch, xfmrcode, transformer, regcontrol)`.
The writer's `WRITE_ORDER` already has XfmrCode before Transformer and RegControl after it. A probe (2026-11-09)
showed the writer's slot order `wdg=2 Rneut=0 Xneut=0.4 buses=[...]` puts the neutral impedance on winding 2, the
same as the deck's `~ wdg=2 ... Rneut=0 Xneut=0.4` (YPrim and voltages equal), and the reader reads it back. A
second probe showed that `XfmrCode=` must come first: written after `buses=`, it re-sizes a center tap to 3
windings and resets winding 3's bus to `t_3`. The writer's `_LEADING_SLOTS` already puts it first.

### Forms

One DSS Transformer per unit of `get_transformer_units` (T4). Every value comes from
`get_transformer_model(unit, base_power=<winding 1's DSS kVA>)`, so every percent is on the base DSS puts it on.

| CIM form | DSS | kV, kVA | |
|---|---|---|---|
| BY_ENDS (`PowerTransformer`, balanced ends) | inline, `phases=3` | `ratedU` (LL), `ratedS` | `%imag`/`%noloadloss` = the core's b/g |
| BY_PHASE_ENDS (a tank's own windings) | inline, `phases=1` | `baseU`, `baseS` (the coil) | the tank's `%imag`/`%noloadloss` |
| BY_TANK_ENDS, BY_LUGS (a `TankConfiguration`) | the configuration's XfmrCode; the instance writes `XfmrCode=`, `buses` and `enabled` | (on the code) | |
| AUTO (`AutoTransformer`, `VoltageRegulator`) | inline, `phases` 1 or 3 (DSS has no AutoTrans mapping here, DSS-11) | `baseU` (the deck's kV, LL on a 3-phase gang unit: an AutoTransformerEnd has no `ratedU`), `ratedS` | no core |

- **kVA on a coil is `baseS`.** A center-tap half is written at the can's kVA (25 for a 25 kVA can), as every deck
  writes it. Probe: writing the half at its `ratedS` (12.5) with its %R moved to that base is not engine-equal
  (0.27 V on the atom): the engine takes more than %R from each winding's kVA.
- **%Rs:** winding n's r from the getter (on winding 1's kVA) times kVA_n / kVA_1. A regulator's mesh r (DSS-13: %R1
  + %R2) is written `%Rs=[r/2 r/2]`. Probe: equal to the deck's `%LoadLoss=r` (YPrim equal).
- **XHL, XHT, XLT:** the mesh x (1,2), (1,3), (2,3), on winding 1's kVA. A missing pair raises. A mesh r on any
  form but AUTO raises: DSS has no home for it.
- **conns:** `connectionKind` D → delta; Y, Yn, I → wye. An AutoTransformerEnd has none: a coil with a neutral is
  wye, a coil between two phases delta (IEEE37's `conns=[delta delta]`). Probe: on a 1-phase coil, wye and delta
  differ only in the engine's anti-float conductance (YPrim within 1.5e-8), so a deck's 1-phase LL coil written
  wye (the `center_tap` atom) comes back delta, a listed YPrim difference.
- **Windings:** 2 or 3; more raise (`Xscarray` not mapped).
- **Not written:** `normhkVA`/`emerghkVA` (untranscribed, D9), `bank`, `LeadLag`, `ppm_antifloat` (an instance's
  `ppm=0` comes back at the engine's default, a listed YPrim difference), `XRConst`, the thermal and reliability
  slots.

### Bus references (E7, the windings' part; T6)

A winding's `phases` in their order (a coil From → To). `bus_ref` gains the neutral's node:
- **A 3-phase wye** (the terminal's ABCN):
  - grounded solidly → `.1.2.3`, the engine's neutral on node 0;
  - grounded through `rground`/`xground` → `.1.2.3.4` with `wdg=<n> Rneut= Xneut=`;
  - ungrounded → `.1.2.3.4` with no Rneut.

  Probe: Rneut on `.1.2.3` is shorted by the neutral on node 0 (the same as solid). Two windings with a neutral
  impedance raise: the record has one `wdg`.
- **A delta:** `.1.2.3`.
- **A coil:** its two conductors, N as `.0` (`feeder.1.0`, `house.0.2`, `n1.1.2`). An ungrounded coil neutral
  raises.

### XfmrCode (T5)

One per `TransformerTankConfiguration` that a unit uses. Its values come from the model of the first unit that uses
it, so they follow the same rules as an inline Transformer:
- `phases`: 3 when winding 1 has three phase conductors, else 1;
- `windings`, `conns`, `kVs`, `kVAs` and `%Rs`;
- `Xhl`, `Xht` and `Xlt`;
- `%imag` and `%noloadloss`;
- `Rneut`/`Xneut` from the TankEnd's `rground`/`xground`.

`MaxTap` and the other tap slots are the instance's. Every instance names it `XfmrCode=<code>` and writes its buses
from its own model.

### Taps

Every `RatioTapChanger` on a unit's end:
- `taps` = 1 on every winding but the tap's, which gets `get_tap_ratio(which='actual')` (R2: `step` is the deck's
  tap; `normalStep` is not read);
- `MaxTap`/`MinTap` = the ratio at `highStep`/`lowStep`;
- `NumTaps` = `highStep - lowStep`.

What raises:
- an unset `step`;
- a `neutralU` other than the winding's kV;
- a tap on an end with two windings (a center-tap secondary);
- any other TapChanger class.

A regulator by XfmrCode (IEEE8500 `regleg`) comes back inline. CIM has no AutoTransformer template, so its code was
never written (S3a), a listed difference that is equal in the engine.

### RegControl

One per `TapChangerControl`, from `get_tap_changer_control`, inverting the importer's `secondary_to_primary` and
`line_drop_ohms`. That pair moves to `cimhub_core/derived/regulator.py` beside its inverses, as `b_from_c` did.

| DSS slot | from |
|---|---|
| `transformer`, `winding` | the tap's unit; the winding whose end holds the tap |
| `vreg`, `band` | target, deadband (V) / `ptRatio` |
| `revvreg`, `revband` | the reverse target and deadband / `ptRatio` |
| `ptratio` | `ptRatio` (tap and control agreed) |
| `CTprim` | `ctRating` (A) |
| `R`, `X`, `revR`, `revX` | line drop (ohm) × `CTprim` / `ptratio` |
| `delay`, `tapdelay` | `initialDelay`, `subsequentDelay` (s) |
| `reversible`, `revNeutral`, `revDelay` | as stored |
| `revThreshold` | `reversingPowerThreshold` (kW) |
| `PTphase` | 1-based place of the `monitoredPhase` among the winding's phase conductors |
| `enabled` | the control's `enabled`; the tap's `controlEnabled` must agree |

`ctRatio` is not read: the engine's CT secondary is fixed at 0.2 A, and R/X go through `CTprim`.

What raises:
- a mode other than voltage;
- an unset `ptRatio`;
- a line drop with no `ctRating`;
- R/X with `lineDropCompensation=false`;
- a monitored Terminal other than the tap end's (remote sensing, `tapwinding`);
- `maxLimitVoltage` (`vlimit`) or `minLimitVoltage`;
- several monitored phases.

### Core changes

- **`get_transformer_model` (T2):** Y on a template TankEnd and Yn on its instance end agree, and the result is the
  instance's. Found in the S6c probe: the getter raises on the importer's own `xfmrcode/codes` (`sub`: `xf_sub_2`
  Yn, `xc_sub_end_2` Y), because grounding is the instance's (S3b) while the getter compared the kinds literally.
- **T3 (polarity), importer and getter.** The importer wrote a 1-phase TankEnd instance's LL end as a PhaseCode,
  which has no order, so IEEE4 YYD's `tert.3.1` came back `tert.1.3`. Probe: the 3-can bank's voltages move by
  1.6 kV. Now:
  - The importer gives every 1-phase instance by template a `TransformerPhaseEnd` per terminal conductor, on the
    end's Terminal. A lug instance keeps terminal order (its lugs name them). A TankEnd instance follows its coil's
    node order (`coil_phase_end_numbers`).
  - BY_TANK_ENDS reads a coil's phases from them, in `sequenceNumber` order (`_ordered_phases`). Phase ends that
    are not the terminal's phases raise.
  - Goldens: `xfmrcode/codes_transformer.cimtbl` (the yyd instances' phase ends) and
    `goldens/IEEE13_CDPSM/transformer.cimtbl` (the table comment only). The sweep still binds every deck it bound.
- **`derived/regulator.py`:** `secondary_to_primary`, `line_drop_ohms` (moved from the importer) and their
  inverses `primary_to_secondary`, `line_drop_volts`.
- **`bus_ref(..., neutral=)`:** a neutral is written on the node the winding gives (0 for a coil, 4 for T6). Without
  one it still raises, so a line can never write a neutral.

### Tests

As built (`tests/test_export_transformer.py`, 28 tests; core `test_derived_regulator.py` and three tests in
`test_getters_transformer.py`):
- **Per atom, in the engine** (§8.3), exported under `name`. Per element: buses, NodeOrder and YPrim (rel 1e-9),
  then the voltages. Under `mrid`/`uri` only the voltages. The atoms:
  - `xfmrcode/codes`: three XfmrCodes and six instances; `transformer.t2` (its `ppm=0`) is the listed YPrim
    difference;
  - `regcontrol/regulators`: every regulator and the LTC inline, every RegControl; no difference;
  - the new `transformer/inline.dss` (with a circuit): sub3, xfm1, the LL center tap `ct_ab` (listed: wye → delta),
    the LN center tap `ct_bn`, the J1 service `svc`, an ungrounded wye `ug` on `.4`, and a delta-delta `dd`.
- **Regulator settings in the engine:** every RegControl property the importer maps and every regulator's `taps`,
  `MaxTap`, `MinTap`, `NumTaps` equal the original's (rel 1e-9; text properties exactly).
- **Spoke unit tests:**
  - the T6 nodes (sub3 `.1.2.3.4` with `wdg=2 Rneut=0 Xneut=0.4`; `ug` `.1.2.3.4` with no Rneut);
  - a center-tap half at the can's kVA;
  - yydc's `tert.3.1` (T3);
  - an instance holding only `XfmrCode=` and buses;
  - the regulator's `%Rs=[r/2 r/2]`;
  - T4's per-tank names on a two-tank PowerTransformer.

  The importer names no TransformerTank, so under `name` a several-tank transformer needs tank names. Without
  them it raises, as any unnamed object does.
- **Raises:**
  - two neutral impedances;
  - a mesh r on balanced ends;
  - an unused configuration (T5);
  - an unset `ptRatio`;
  - remote sensing;
  - a line drop without `ctRating`;
  - a mode other than voltage.
- **Getters:** T2 (a template Y with an instance Yn gives Yn), and T3 (a TankEnd coil in its phase-end order, plus
  phase ends that are not the terminal's, which raise).
- **Deck round trip:** IEEE13_CDPSM still cannot run, and moves to S6d. Its loads and capacitors raise
  "no DSS export yet" (`_check_exported`), so element-by-element parity on a whole deck starts with S6d.
- **Goldens:** `export/*.dss` beside each atom (mrid).
- **Suite:** 1,090 passed. With the external decks (`CIMHUB_DSS_DECKS`, `--roundtrip`), all 607 opendss tests pass,
  the sweep included.

### Decisions for S6c (approved 2026-11-09, as recommended; T3 the phase-end option)

| # | question | recommendation |
|---|---|---|
| T1 | Forms | As the Forms table: an inline Transformer for ends, phase ends and regulators; an XfmrCode plus `XfmrCode=` instances for a TankConfiguration; a coil's kV/kVA are `baseU`/`baseS`, a 3-phase unit's `ratedU`/`ratedS` |
| T2 | Y vs Yn, template vs instance | Fix the getter: the kinds agree up to the grounding, and the instance's wins. The importer stays as built |
| T3 | Polarity of a 1-phase TankEnd instance | The importer gives such an instance a `TransformerPhaseEnd` per terminal conductor in the deck's node order, and BY_TANK_ENDS reads a coil's phases from them when present. Alternatives: the importer writes such an instance inline (BY_PHASE_ENDS, a listed difference), or it raises on a descending LL coil (IEEE4 YYD stops binding) |
| T4 | Several tanks on one PowerTransformer | One DSS Transformer per tank, named by the tank; a PowerTransformer with one tank is named by itself. A tap changer on a several-tank PowerTransformer raises until a producer writes one |
| T5 | An unused TransformerTankConfiguration | Raises: the importer never writes one, and a template alone does not say its phases |
| T6 | Neutral impedance (amends E7) | The neutral goes on `.4` with `Rneut`/`Xneut` (probe: on `.1.2.3` it is shorted); an ungrounded wye is `.4` with no Rneut; two neutral impedances on one transformer raise |
| T7 | Regulator impedance and range | `%Rs=[r/2 r/2]` (equal to `%LoadLoss=r`); `MaxTap`/`MinTap`/`NumTaps` from the step range; an unset `step` or `ptRatio` raises |

### Slot tables (S6c, generated from `SLOTS`)

**Transformer** (`exporter/transformer.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names; a one-unit transformer by itself, each tank of several by the tank (T4) |
| phases | written | 3 when every winding has A, B, C, else 1 (a coil); inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| windings | written | the model's windings, 2 or 3; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| wdg | written | the one winding grounded through rground/xground (T6) |
| bus | not mapped | the active-winding form; the arrays carry every winding |
| conn | not mapped | the active-winding form; the arrays carry every winding |
| kV | not mapped | the active-winding form; the arrays carry every winding |
| kVA | not mapped | the active-winding form; the arrays carry every winding |
| tap | not mapped | the active-winding form; the arrays carry every winding |
| pct_R | not mapped | the active-winding form; the arrays carry every winding |
| Rneut | written | rground (ohm) of winding wdg; its neutral on .4 (T6) |
| Xneut | written | xground (ohm) of winding wdg |
| buses | written | bus_ref of each winding's phases: a coil's N on .0; a 3-phase wye solid .1.2.3, else .1.2.3.4 (E7, T6) |
| conns | written | connectionKind D -> delta, Y/Yn/I -> wye; AUTO: wye with a neutral; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| kVs | written | a coil's or an AutoTransformerEnd's baseU, a 3-phase winding's ratedU (kV); inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| kVAs | written | a coil's baseS (AUTO: ratedS), a 3-phase winding's ratedS (kVA); inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| taps | written | 1, and get_tap_ratio(actual) on the RatioTapChanger's winding |
| XHL | written | mesh (1,2) x, percent on winding 1's kVA; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| XHT | written | mesh (1,3) x; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| XLT | written | mesh (2,3) x; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| Xscarray | not mapped | more than 3 windings raise |
| thermal | unset | untranscribed on import; not in CIM |
| n | unset | untranscribed on import; not in CIM |
| m | unset | untranscribed on import; not in CIM |
| flrise | unset | untranscribed on import; not in CIM |
| hsrise | unset | untranscribed on import; not in CIM |
| pct_loadloss | not mapped | %Rs carries the winding r (AUTO: the mesh r halved, T7) |
| pct_noloadloss | written | the core g (percent on winding 1's kVA); unset -> not written; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| normhkVA | unset | untranscribed on import (D9) |
| emerghkVA | unset | untranscribed (D9) |
| sub | unset | untranscribed on import; not in CIM |
| MaxTap | written | get_tap_ratio(high) |
| MinTap | written | get_tap_ratio(low) |
| NumTaps | written | highStep - lowStep |
| subname | unset | untranscribed on import; not in CIM |
| pct_imag | written | the core b (percent); unset -> not written; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| ppm_antifloat | unset | untranscribed on import; not in CIM |
| pct_Rs | rule | winding r x kVA_n / kVA_1 (AUTO: [r/2 r/2], T7); unset -> 0; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| bank | unset | each DSS Transformer is its own PowerTransformer (DSS-2) |
| XfmrCode | written | the unit's TankConfiguration (BY_TANK_ENDS, BY_LUGS) |
| XRConst | unset | untranscribed on import; not in CIM |
| X12 | unset | untranscribed on import; not in CIM |
| X13 | unset | untranscribed on import; not in CIM |
| X23 | unset | untranscribed on import; not in CIM |
| LeadLag | unset | untranscribed on import; not in CIM |
| Core | unset | untranscribed on import; not in CIM |
| RdcOhms | unset | untranscribed on import; not in CIM |
| Seasons | unset | untranscribed on import; not in CIM |
| Ratings | unset | untranscribed on import; not in CIM |
| normamps | unset | untranscribed on import; not in CIM |
| emergamps | unset | untranscribed on import; not in CIM |
| faultrate | unset | untranscribed on import; not in CIM |
| pct_perm | unset | untranscribed on import; not in CIM |
| repair | unset | untranscribed on import; not in CIM |
| basefreq | unset | untranscribed on import; not in CIM |
| enabled | written | get_in_service(which='normal'); unset -> not written |
| like | not mapped | the writer never writes like= |

**Xfmrcode** (`exporter/xfmrcode.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, the XfmrCode namespace |
| phases | written | as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| windings | written | as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| wdg | written | as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| conn | not mapped | the active-winding form; the arrays carry every winding |
| kV | not mapped | the active-winding form; the arrays carry every winding |
| kVA | not mapped | the active-winding form; the arrays carry every winding |
| tap | not mapped | the active-winding form; the arrays carry every winding |
| pct_R | not mapped | the active-winding form; the arrays carry every winding |
| Rneut | written | as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| Xneut | written | as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| conns | written | as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| kVs | written | as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| kVAs | written | as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| taps | not mapped | a tap is the instance's |
| Xhl | written | as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| Xht | written | as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| Xlt | written | as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| Xscarray | not mapped | more than 3 windings raise |
| thermal | unset | untranscribed on import; not in CIM |
| n | unset | untranscribed on import; not in CIM |
| m | unset | untranscribed on import; not in CIM |
| flrise | unset | untranscribed on import; not in CIM |
| hsrise | unset | untranscribed on import; not in CIM |
| pct_loadloss | not mapped | %Rs carries the winding r |
| pct_noloadloss | written | as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| normhkVA | unset | untranscribed on import (D9) |
| emerghkVA | unset | untranscribed (D9) |
| MaxTap | not mapped | a tap is the instance's |
| MinTap | not mapped | a tap is the instance's |
| NumTaps | not mapped | a tap is the instance's |
| pct_imag | written | as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| ppm_antifloat | unset | untranscribed on import; not in CIM |
| pct_Rs | rule | as the Transformer's (windings.py), read through the first unit; every unit must give the same; unset r -> 0 |
| X12 | unset | untranscribed on import; not in CIM |
| X13 | unset | untranscribed on import; not in CIM |
| X23 | unset | untranscribed on import; not in CIM |
| RdcOhms | unset | untranscribed on import; not in CIM |
| Seasons | unset | untranscribed on import; not in CIM |
| Ratings | unset | untranscribed on import; not in CIM |
| like | not mapped | the writer never writes like= |

**Regcontrol** (`exporter/regcontrol.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, the RegControl namespace |
| transformer | written | the DSS Transformer of the tap's unit (one unit) |
| winding | written | the winding whose end holds the RatioTapChanger |
| vreg | written | targetValue (V) / ptRatio (primary_to_secondary) |
| band | written | targetDeadband (V) / ptRatio (primary_to_secondary); unset -> not written, the engine's default |
| ptratio | written | ptRatio, the tap's and the control's agreed; unset raises |
| CTprim | written | ctRating (A); unset -> not written, and a line drop then raises |
| R | written | lineDropR (ohm) x CTprim / ptRatio (line_drop_volts); unset -> not written (0) |
| X | written | lineDropX (ohm) x CTprim / ptRatio (line_drop_volts); unset -> not written (0) |
| bus | not mapped | the control must monitor its tap end's Terminal (remote sensing raises) |
| delay | written | initialDelay (s); unset -> not written |
| reversible | written | TapChangerControl.reversible |
| revvreg | written | reverseTargetValue (V) / ptRatio (primary_to_secondary); unset -> not written, the engine's default |
| revband | written | reverseTargetDeadband (V) / ptRatio (primary_to_secondary); unset -> not written, the engine's default |
| revR | written | reverseLineDropR (ohm) x CTprim / ptRatio (line_drop_volts); unset -> not written (0) |
| revX | written | reverseLineDropX (ohm) x CTprim / ptRatio (line_drop_volts); unset -> not written (0) |
| tapdelay | written | subsequentDelay (s); unset -> not written |
| debugtrace | unset | untranscribed or raising on import; not in CIM |
| maxtapchange | unset | untranscribed or raising on import; not in CIM |
| inversetime | unset | untranscribed or raising on import; not in CIM |
| tapwinding | not mapped | the tap winding is the monitored one |
| vlimit | not mapped | maxLimitVoltage raises (untranscribed on import) |
| PTphase | written | 1-based place of monitoredPhase among the winding's phase conductors |
| revThreshold | written | reversingPowerThreshold (kW) |
| revDelay | written | reversingDelay (s) |
| revNeutral | written | reverseToNeutral |
| EventLog | unset | untranscribed or raising on import; not in CIM |
| RemotePTRatio | unset | untranscribed or raising on import; not in CIM |
| TapNum | unset | untranscribed or raising on import; not in CIM |
| Reset | unset | untranscribed or raising on import; not in CIM |
| LDC_Z | unset | untranscribed or raising on import; not in CIM |
| rev_Z | unset | untranscribed or raising on import; not in CIM |
| Cogen | unset | untranscribed or raising on import; not in CIM |
| idle | unset | untranscribed or raising on import; not in CIM |
| idleReverse | unset | untranscribed or raising on import; not in CIM |
| idleForward | unset | untranscribed or raising on import; not in CIM |
| basefreq | unset | untranscribed or raising on import; not in CIM |
| enabled | written | the control's enabled; the tap's controlEnabled must agree |
| like | not mapped | the writer never writes like= |
