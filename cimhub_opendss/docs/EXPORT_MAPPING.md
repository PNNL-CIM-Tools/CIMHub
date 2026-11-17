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
    (Slot, check_slots, slots_table: cimhub_core/export_slots.py, shared with the RAW exporter)
    vsource.py        EnergySource -> Vsource (one module per DSS class from here on)
```

- **`DssExporter().to_model(network, *, name_source=None, circuit_source="source", switch_state="actual") ->
  DssModel`.** It runs each
  module of `EXPORT_ORDER` over its CIM classes and adds the records. `history` stays empty: it is a reader
  artifact.
- Each module has `export(obj, context) -> list[record]` and `SLOTS`, which names each slot of its DSS class as
  `written` (from which getter), `rule` (a CIM `None` DSS needs, E4), `unset` (CIM cannot hold it; engine default)
  or `not mapped`. A test checks that `SLOTS` covers every schema slot, as `check_fields` does on import, and the
  tables below are generated from it.
- `context` (`ExportContext`) holds the network, the `Names`, the circuit's EnergySource and the `switch_state`. Nothing else is shared
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
  - Its name is the one Feeder's, by the same switch. Several Feeders are one circuit (one deck per substation)
    when every one has the same `NormalEnergizingSubstation`, and the Substation names it. No Feeder, or several
    without one Substation, raises.
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
- `earthmodel` the WireConfigurations' one EarthResistivity model (`options.earth_model`, S6g); none -> not set;
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
- `write(model, destination, per_class=True)` (also `cim_to_dss(..., per_class=True)`) writes step 4 as one file
  per class beside the deck (`linecode.dss`, `xfmrcode.dss`, `line.dss`, ...; only classes that have records), and
  the master `destination` has `Redirect <file>` in `WRITE_ORDER` in its place. A master named like a class file
  (`Line.dss`) raises rather than being overwritten. The default is the single deck.

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
  - the three decks are also written `per_class` and checked the same way (records and engine).
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
    wire.py           OverheadWireInfo and CableInfo / ConcentricNeutralCableInfo / TapeShieldCableInfo -> Wiredata / Cndata / Tsdata
    linecode.py       PerLengthPhaseImpedance / PerLengthSequenceImpedance -> Linecode
    linegeometry.py   (WireConfiguration, spacingYOffset) and spacing lines -> Linegeometry, inline positions (B2)
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
each name in only one catalog. A plain CableInfo (no neutral or shield) is a WireData, its insulation unmodelled (B7).

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
  `<configuration>` at offset unset or 0, and `<configuration>_<offset>m` otherwise (offset in m rounded to the
  mm, `.` written as `p`: `10p363m`). Two offsets of one configuration that round to one name raise.
- **A WireConfiguration no line uses** is written once, with its spacing's positions as stored (offset 0, the CIM
  default).
- **A spacing line** (the EPRI line shape: `ACLineSegment.WireSpacing`, no WireConfiguration, a WireInfo on every
  ACLineSegmentPhase) gets one record per (spacing, spacingYOffset, conductors), the conductors being each phase's
  sequence number, WireInfo and whether it is N. It is named `<line>_geometry` after the first line that has it.
  The spacing may hold several circuits (a double circuit, a secondary bundle under a primary): the line takes the
  positions of its own phases' sequence numbers. `circuitNumber` is not read, since cim18v17 says a line's need not
  match its positions'.
- **Positions:**
  - `get_line_conductor_xy(line)`, or `get_spacing_xy` for an unused configuration, in m: phase conductors, then
    neutrals. A bundle (`RegularBundlePosition` triplex, `BundlePosition` quadruplex) is expanded into its
    sub-conductors. They are written as `xs` / `hs` with the conductor names in `wires`, and the writer emits the
    cond blocks;
  - the wires are matched to positions by sequence number from `get_configuration_wires`, or a spacing line's
    `get_line_phase_wires`;
  - a plain CableInfo below grade is written at the same height above it (B7): DSS takes a WireData only above
    grade.
- **The other slots:**
  - nconds = the positions;
  - nphases = `numberOfPhases` (required), or a spacing line's phases other than N. Position kinds, where set, must
    be `phase` for 1..nphases and `neutral` after;
  - `reduce=y`: the neutrals are Kron-reduced, i.e. grounded at both ends, as the impedance getters assume (G2;
    242 of 243 sweep geometries set it). The import left `reduce` untranscribed for that reason.
- **The earth of a spacing line.** cim18v17 associates an EarthResistivity only with a WireConfiguration or a
  PerLengthImpedance, so a spacing line takes the network's one EarthResistivity (`get_network_earth`) for its
  `rho` and the deck's earthmodel. None or several raise.
- **Raises:**
  - a spacing line with a phase without a WireInfo, or a phase whose sequence number its spacing has no conductor
    for; a line with both a WireConfiguration and a phase WireInfo;
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
| linecode / geometry | the code's name, or the (configuration, offset) geometry's name, or a spacing line's `<line>_geometry`. Geometry wins when both are set (skill `conductor-geometry`) |
| rho | the configuration's EarthResistivity, or a spacing line's network EarthResistivity (ohm-m) |
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
- `to_model(..., switch_state="normal")` reads `which="normal"` for `State` and `Open` too, for an as-built model
  whose `Switch.open` is unset. The default, `"actual"`, raises on an unset `open`; there is no silent fallback.

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
| B2 | Geometry form | Inline positions (cond blocks) per (WireConfiguration, offset), and per (spacing, offset, conductors) for a spacing line (a direct WireSpacing and a WireInfo on each phase, the EPRI shape); no LineSpacing is written |
| B3 | Switch impedance (amended by the user) | A small invented impedance: 1 mOhm resistive, `r1=r0=1e-3 x1=x0=0 C1=C0=0 length=1 units=m` |
| B4 | Line neutrals (approved by the user 2026-11-09, as recommended and built) | Geometry `reduce=y`, and the neutral is not written on the bus. Engine probe (2026-11-09, geometry 601 under an unbalanced load): `reduce=y` gives the same voltages, to 1e-9 V, as `reduce=n` with the neutral on node 0 at both ends. So `reduce=y` is exactly a neutral grounded at both ends, and it keeps a 3x3 YPrim. `reduce=n` on a `.1.2.3` bus puts the neutral on node 4, ungrounded: it floats (292 V in the probe), and the phase voltages move by up to 4 %. CIM has no per-conductor neutral grounding to export, so `reduce=n` has nothing to carry. A code line with a neutral row raises |
| B5 | Code values | Code-level getters; a code no line uses is still exported |
| B6 | Lumped-only lines (amended by the user) | Written inline: the whole-line values divided by the length, `r1 x1 r0 x0` in ohm/km and `C1 C0` in nF/km, `units=km`; with no length, `length=1` |
| B7 | Unshielded cable (user, 2026-11-12) | A plain CableInfo (insulated, no neutral or shield: an underground secondary's conductors) is a WireData, its insulation not modelled. DSS takes a WireData only above grade, so a buried one is written at the same height above (`hs` = abs(y)). The series impedance is close: the earth-return depth (about 850 m at 100 ohm-m) dwarfs a few feet |

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
| name | written | Names; <configuration> at offset 0, <configuration>_<offset>m otherwise, to the mm ('.' as 'p'); a spacing line's: <line>_geometry of the first line with its spacing, offset and conductors |
| nconds | written | the spacing's positions; a spacing line's: its phases' positions |
| nphases | written | WireConfiguration.numberOfPhases, required; a spacing line's: its phases other than N; position kinds phase then neutral |
| cond | not mapped | the writer folds wires/xs/hs into cond= blocks |
| wire | not mapped | the writer folds wires/xs/hs into cond= blocks |
| x | not mapped | the writer folds wires/xs/hs into cond= blocks |
| h | not mapped | the writer folds wires/xs/hs into cond= blocks |
| units | written | m (B1) |
| normamps | unset | no rating on a WireConfiguration (D9); the Line carries its own |
| emergamps | unset | no rating on a WireConfiguration (D9); the Line carries its own |
| reduce | written | y: the neutrals grounded at both ends, as the impedance getters assume (B4) |
| spacing | not mapped | positions are written inline (B2) |
| wires | written | get_configuration_wires, or a spacing line's get_line_phase_wires, by sequence number; any of the three catalogs |
| cncable | not mapped | the writer folds wires/xs/hs into cond= blocks |
| tscable | not mapped | the writer folds wires/xs/hs into cond= blocks |
| cncables | not mapped | wires carries every kind (the writer names each block's kind) |
| tscables | not mapped | wires carries every kind (the writer names each block's kind) |
| xs | written | get_line_conductor_xy x (m); an unused configuration: get_spacing_xy |
| hs | written | get_line_conductor_xy y, above ground (m); a plain CableInfo's abs(y) (B7) |
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
| rho | written | a geometry line's WireConfiguration EarthResistivity.rho (ohm-m), unset -> not written; a spacing line's: get_network_earth |
| geometry | written | the (WireConfiguration, spacingYOffset) LineGeometry name; a spacing line's: spacing_geometry_name of its owner |
| units | written | m (B1); lumped: km (B6) |
| spacing | not mapped | positions are written inline in the LineGeometry (B2) |
| cncables | not mapped | the LineGeometry carries the conductors (B2) |
| tscables | not mapped | the LineGeometry carries the conductors (B2) |
| wires | not mapped | the LineGeometry carries the conductors (B2) |
| EarthModel | not mapped | the deck's Set earthmodel carries it (options.py: one model per deck) |
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
| FuseCurve | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| RatedCurrent | written | Switch.ratedCurrent (A) |
| Delay | unset | no home on a Switch (untranscribed on import) |
| Action | unset | no home on a Switch (untranscribed on import) |
| Normal | written | get_switch_state(which='normal'); written only when open in either state; one value per phase (the engine sets a fuse per phase) |
| State | written | get_switch_state(which='actual'); written only when open in either state; one value per phase (the engine sets a fuse per phase) |
| basefreq | unset | no home on a Switch (untranscribed on import) |
| enabled | rule | no: no trip settings or curve in CIM yet (U15), so the engine's defaults would trip it (V7) |
| like | not mapped | the writer never writes like= |

**Recloser** (`exporter/switch.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, the switch's |
| MonitoredObj | written | Line.<the switch's Line name> |
| MonitoredTerm | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| SwitchedObj | not mapped | the engine takes MonitoredObj |
| SwitchedTerm | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| NumFast | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| PhaseFast | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| PhaseDelayed | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| GroundFast | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| GroundDelayed | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| PhaseTrip | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| GroundTrip | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| PhaseInst | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| GroundInst | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| Reset | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| Shots | written | the RecloseSequences + 1 (get_reclose_delays); none -> 1, no reclosure |
| RecloseIntervals | written | each RecloseSequence's recloseDelay (s), in recloseStep order; none -> not written |
| Delay | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| Action | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| TDPhFast | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| TDGrFast | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| TDPhDelayed | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| TDGrDelayed | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| Normal | written | get_switch_state(which='normal'); written only when open in either state |
| State | written | get_switch_state(which='actual'); written only when open in either state |
| basefreq | unset | protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default |
| enabled | rule | no: no trip settings or curve in CIM yet (U15), so the engine's defaults would trip it (V7) |
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
| BY_TANK_IMPEDANCE (two ends and each tank's `percentImpedance`, a GIS's cans) | inline, `phases` 1 or 3; a center-tap end (s1s2N, kind I) is two halves on one bus; a bank is one 1-phase Transformer per can (T4), in tank order (GETTERS_PLAN bank rules) | a coil: `ratedU` derived to the coil (V2), each half `ratedU`/2 at the can's kVA; 3-phase `ratedU`, `ratedS` | `%Rs` and `X**` from %Z and loadLoss (Hopkinson's split on a center tap); the tank's `%imag`/`%noloadloss` |
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
- **A coil:** its two conductors, N as `.0` (`feeder.1.0`, `house.0.2`, `n1.1.2`) when grounded. An ungrounded
  coil neutral is `.4`, as T6 (`head.1.4`): a bank's cans on one bus share that floating node, the wye primary of a
  floating-wye / delta bank. The engine's default antifloat (1 ppm) is enough for it to solve. A coil neutral
  with `grounded` unset raises. The importer has no phase for node 4 on a 1-phase transformer, so it does not read
  such a deck back (it raises).

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
- **Deck round trip:** IEEE13_CDPSM still cannot run. Its loads and capacitors raise "no DSS export yet"
  (`_check_exported`). (S6d found it also has PVSystems and Storage, so it waits for S6e; S6d's deck check runs on
  four other engine decks.)
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
| T6 | Neutral impedance (amends E7) | The neutral goes on `.4` with `Rneut`/`Xneut` (probe: on `.1.2.3` it is shorted); an ungrounded wye, or an ungrounded coil neutral, is `.4` with no Rneut; two neutral impedances on one transformer raise |
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
| PTphase | written | 1-based place of monitoredPhase among the winding's phase conductors; 1 on a 1-phase winding, whichever of its conductors CIM names |
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

## S6d: loads, capacitors, CapControl (built 2026-11-09 at the user's word, with decisions L1-L7 as recommended)

Content: EnergyConsumer → Load, LinearShuntCompensator → Capacitor, the RegulatingControl of a shunt →
CapControl. Plan §8.1 row S6d; DSS-5, DSS-7, S4-2, E4, E8 and E9 apply. The user approved S6d together with B4
("go ahead and implement that and 6d"), so this spec was written alongside the code. Its decisions, L1-L7, are
at the end of this section, as recommended; any of them can still be amended.

### Layout

```
cimhub_opendss/src/cimhub_opendss/exporter/
    injection.py     a one-terminal device's bus1, phases, conn and a load's kV (Load, Capacitor; DER in S6e)
    controls.py      PTPhase and enabled, shared by RegControl and CapControl (moved out of regcontrol.py)
    load.py          EnergyConsumer (ConformLoad, NonConformLoad, StationSupply) -> Load
    capacitor.py     LinearShuntCompensator -> Capacitor
    capcontrol.py    RegulatingControl -> Capcontrol
```

`EXPORT_ORDER` gains `load, capacitor, capcontrol` after `regcontrol`. The writer's `WRITE_ORDER` already has
Capacitor before CapControl.

### Connection (the importer's shared phase rule inverted)

- `bus1`: the phase conductors (no neutral), A/B/C as 1/2/3 and s1/s2 as 1/2.
- A wye device's neutral is the engine's node 0, so the device must be `grounded=true`. Unset or false raises (an
  ungrounded or impedance-grounded neutral is not mapped, as on import).
- `phaseConnection` Y and Yn are wye and D is delta; I, G and unset raise.
- A delta across two conductors is DSS's 1-phase delta, written in branch order A-B, B-C, C-A (L2). Engine
  probe: CIM's PhaseCode `AC` written `.1.3` gives the same YPrim, but the node order differs from the deck's `.3.1`.
- A delta on another count raises.

### Load

| DSS slot | from |
|---|---|
| `kW`, `kvar` | `get_phase_loads` total (kW, kVAr) |
| `kV` | the BaseVoltage (L1) |
| `model` | `get_load_response`: pure constant PQ → 1, Z → 2, I → 5; exponential → 4 with `CVRwatts`/`CVRvars` |
| `NumCust` | `customerCount`; unset → not written |
| `enabled` | `get_in_service(which='normal')` |

- **kV (L1, E9):** CIM gives a load no rating (S4-2), so `kV` is the bus's: LL for delta and for 2 or 3 phases,
  LN for 1-phase wye. On a split-phase secondary the BaseVoltage (240 V) is the whole coil, so a leg is half of it
  (0.12) and a 2-phase wye leg pair is read by the engine's sqrt 3 rule (0.2078). A deck's rounded kV comes back
  as the bus's: IEEE13's `kV=2.4` as 2.40178. Probe: the YPrim moves by (2.4 / 2.40178)^2, 0.15 %. A constant PQ
  load solves to the same power, but a Z, I or CVR load's power moves by the same ratio.
- **Model (L3):** a mix of fractions raises. ZIPV (model 8) and model 3 raise on import too.
- **Per phase (E8, L4):** when the `EnergyConsumerPhase` values differ, each phase becomes a 1-phase wye Load
  `<name>_<phase>`. Its kV is LN, and the first carries `customerCount`, the others `NumCust=0`, so the deck's
  total is CIM's. A delta load with unequal phases raises. The importer never writes phase values, so a unit test
  builds them.
- **Not written:** `pf`, `kVA`, `xfkVA` (kW and kvar carry the power); `Vminpu`, `Vmaxpu`, `status` and the other
  untranscribed slots (L6, the engine's defaults).

### Capacitor

- `kvar` = `get_shunt_reactive_power(sections='maximum', voltage='nominal')` (kVAr), that is, bPerSection x
  nomU^2. `maximumSections` other than 1 raises (L5, as on import).
- `kv` = `nomU`, the voltage bPerSection was derived on.
- `states` = `[sections]`, the sections in service. DSS has no normal state for a capacitor, so `normalSections`
  is not written (L5). A `sections` other than 0 or 1 raises.
- `conn`, `bus1` and `phases` as above, and `enabled`.

### CapControl

One per `RegulatingControl` (a TapChangerControl is another class, RegControl's). It must regulate exactly one
LinearShuntCompensator; anything else raises, because other regulated equipment is not exported yet (L7).

| DSS slot | from |
|---|---|
| `type` | mode voltage, currentFlow, reactivePower, timeScheduled → voltage, current, kvar, time; others raise |
| `ONsetting`, `OFFsetting` | `on_off_from_band(target, deadband)`: ON = target - deadband / 2 for voltage and time, + for current and kvar; then voltage / PTratio, current / CTratio, kvar in kvar, time in hours |
| `PTratio`, `CTratio` | `ptRatio`, `ctRatio`; unset → not written. A voltage control needs PTratio and a current control needs CTratio: unset raises |
| `element`, `terminal` | the monitored Terminal's equipment, as its record is named (`Line.<line>`, `Line.<switch>`, `Capacitor.<shunt>`; others raise), and its `sequenceNumber` |
| `capacitor` | the regulated shunt |
| `Delay` | the shunt's `aVRDelay` (s) |
| `PTPhase` | the 1-based place of `monitoredPhase` among the monitored equipment's phase conductors (`controls.pt_phase`, shared with RegControl) |
| `enabled` | the control's `enabled`; the shunt's `controlEnabled` must agree (`controls.control_enabled`) |

What raises:
- an unset `targetDeadband` (DSS needs both settings);
- `minAllowedTargetValue`, `maxAllowedTargetValue`, or a reverse target or deadband (no CapControl slot).

`VoltOverride`, `Vmax`, `Vmin`, `DelayOFF` and `DeadTime` are untranscribed on import (S4-5), so they come back at
the engine's defaults (L6).

### Core changes

- **`derived/control_band.py`:** `band_from_on_off` (the importer's midpoint and width, moved out of
  `on_off_target`) and its inverse `on_off_from_band`, as `derived/regulator.py` did for RegControl.
- **Getters:** none new; `get_phase_loads`, `get_load_response`, `get_shunt_reactive_power`,
  `get_equipment_control` and `get_base_voltage` as built in G6.

### Findings

- **An XfmrCode that leaves its reactances unset.** The engine reports XHL=7, XHT=35, XLT=30, but it builds the
  instance with X near 0. Probe: YPrim almost purely resistive, while an inline transformer with the same unset
  slots gets 7 %. The importer reads the reported defaults (DSS-6), so it disagrees with the engine on such a code.
  No sweep deck has one; only the old `load/loads` atom did, and it now sets them (after CDPSM's CT5).
  Proposed follow-up: the importer raises on an XfmrCode with unset reactances.
- **Decks that solve when compiled** (IEEE13_original, IEEE37, IEEE13_Assets) run `Solve` with controls on. That
  moves regulator taps and switches capacitors (IEEE13_Assets' time-controlled `cap1` is off at hour 0) before a
  comparison can read the model. A whole-deck YPrim and voltage comparison therefore compares solved states, and
  belongs to S6f.
- **IEEE37's `reg1c`** is a coil C → B, which an AutoTransformerEnd's PhaseCode holds as BC. It comes back
  `.2.3`, with its RegControl's node 2. Both windings reverse together, so it is the same coil. It is a listed node
  order difference; T3's phase ends cover templates only.
- **The IEEE13_CDPSM round trip** waits for S6e: the deck also has PVSystems and Storage.

### Tests

As built (`tests/test_export_injection.py`, 24 tests; core `test_derived_control_band.py`):
- **Per atom, in the engine** (§8.3), exported under `name`: per element, buses, NodeOrder and YPrim (rel 1e-9),
  then the voltages. Under `mrid`/`uri` only the voltages. The atoms:
  - `load/loads`. Changed so that it compares: the CVR loads' kV is now the bus's to full precision, and the
    XfmrCode sets its reactances. `load.house` (0.208 → 0.2078) is the listed YPrim difference.
  - `capacitor/caps`. Its switch now carries B3's 1 mOhm, so the bank behind it solves alike.

  The import goldens do not change: kV is not written, and the switch impedance is untranscribed.
- **Settings in the engine:**
  - every Load's phases, conn, kW, kvar, model, CVR exponents, NumCust and enabled (rel 1e-9), and its kV
    within 1 %;
  - every Capacitor's phases, conn, kvar, kv, states and enabled;
  - every CapControl's element, terminal, capacitor, type, ratios, ON, OFF, Delay, PTPhase and enabled.
- **Whole decks** (IEEE13_original, IEEE123, IEEE37, IEEE13_Assets; vendored, about 1 s each): the same elements,
  each on the same buses and node order (listed: IEEE37's `reg1c`/`creg1c`), and every Load, Capacitor (states
  aside) and CapControl set alike.
- **Spoke unit tests:**
  - the kV rule (LN, LL, a leg, two legs);
  - branch order (`.3.1`);
  - E8 per-phase loads, with the customer count;
  - an open bank `states=[0]`;
  - ON/OFF rebuilt for all four types.
- **Raises:**
  - mixed ZIP fractions;
  - an ungrounded wye load;
  - two sections;
  - an unset deadband;
  - an unset ptRatio on a voltage control;
  - another mode;
  - a control that regulates no shunt.
- **Harness:** `engine_compare` records a disabled element as disabled; the engine gives it no nodes.
- **Goldens:** `export/loads.dss` and `export/caps.dss` (mrid).
- **Suite:** 1,120 passed. With the external decks (`CIMHUB_DSS_DECKS`, `--roundtrip`), all 634 opendss tests pass,
  the sweep included.

### Decisions for S6d (recommended; built at the user's word 2026-11-09)

| # | question | recommendation |
|---|---|---|
| L1 | A load's kV | The BaseVoltage by E9 and DSS-5 (a leg half the coil, a 2-phase leg pair x sqrt 3). A deck's rounded kV comes back as the bus's, a listed YPrim difference. A 1-phase source's island (its BaseVoltage is the LN source voltage) is not told apart: no sweep deck has a 1-phase source, so a load there would be written at LN / sqrt 3 |
| L2 | 1-phase delta order | Branch order A-B, B-C, C-A (IEEE13's `692.3.1`), since a PhaseCode has none |
| L3 | Load models | A pure ZIP is 1, 2 or 5 and exponential is 4; a mix raises (model 8, as on import) |
| L4 | E8 per-phase loads and NumCust | The first phase's load carries customerCount and the others 0, so the total is kept |
| L5 | Capacitor sections | One section; `states=[sections]` (actual), and normalSections is not written |
| L6 | Untranscribed settings | Load `Vminpu`/`Vmaxpu`/`status`, CapControl `VoltOverride`/`Vmax`/`Vmin`/`DelayOFF`/`DeadTime`: the engine's defaults |
| L7 | Which RegulatingControls | Every plain RegulatingControl is a CapControl on its one LinearShuntCompensator; one regulating anything else raises until S6e exports that equipment |

### Slot tables (S6d, generated from `SLOTS`)

**Load** (`exporter/load.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names; one load per phase is <name>_<phase> (E8) |
| bus1 | written | bus_ref of the phase conductors; a wye's neutral is node 0, so it must be grounded |
| phases | written | the phase conductors; a delta across two is 1 |
| kV | written | the BaseVoltage: LL for delta and 2-3 phases, LN for 1-phase wye; a split-phase leg half the coil, a 2-phase wye leg pair x sqrt 3 (E9, DSS-5) |
| kW | written | get_phase_loads total p (kW); per phase when the phases differ (E8) |
| pf | not mapped | kvar carries q |
| model | written | get_load_response: a pure ZIP 1 (PQ), 2 (Z), 5 (I); exponential 4 (CVR); a mix raises |
| yearly | unset | untranscribed or raising on import; not in CIM |
| daily | unset | untranscribed or raising on import; not in CIM |
| duty | unset | untranscribed or raising on import; not in CIM |
| growth | unset | untranscribed or raising on import; not in CIM |
| conn | written | phaseConnection Y/Yn -> wye, D -> delta; others raise |
| kvar | written | get_phase_loads total q (kVAr); per phase when the phases differ (E8) |
| Rneut | unset | untranscribed or raising on import; not in CIM |
| Xneut | unset | untranscribed or raising on import; not in CIM |
| status | unset | DSS solution control; untranscribed on import, the engine's default |
| load_class | unset | untranscribed or raising on import; not in CIM |
| Vminpu | unset | DSS solution control; untranscribed on import, the engine's default |
| Vmaxpu | unset | DSS solution control; untranscribed on import, the engine's default |
| Vminnorm | unset | DSS solution control; untranscribed on import, the engine's default |
| Vminemerg | unset | DSS solution control; untranscribed on import, the engine's default |
| xfkVA | not mapped | kW carries p |
| allocationfactor | not mapped | kW carries p |
| kVA | not mapped | kW and kvar carry the power |
| pct_mean | unset | untranscribed or raising on import; not in CIM |
| pct_stddev | unset | untranscribed or raising on import; not in CIM |
| CVRwatts | written | pVoltageExponent; model 4 only |
| CVRvars | written | qVoltageExponent; model 4 only |
| kwh | unset | untranscribed or raising on import; not in CIM |
| kwhdays | unset | untranscribed or raising on import; not in CIM |
| Cfactor | unset | untranscribed or raising on import; not in CIM |
| CVRcurve | unset | untranscribed or raising on import; not in CIM |
| NumCust | written | customerCount; unset -> not written; per phase on the first load, 0 on the others |
| ZIPV | not mapped | model 8 raises, as on import |
| pct_SeriesRL | unset | untranscribed or raising on import; not in CIM |
| RelWeight | unset | untranscribed or raising on import; not in CIM |
| Vlowpu | unset | DSS solution control; untranscribed on import, the engine's default |
| puXharm | unset | untranscribed or raising on import; not in CIM |
| XRharm | unset | untranscribed or raising on import; not in CIM |
| spectrum | unset | untranscribed or raising on import; not in CIM |
| basefreq | unset | untranscribed or raising on import; not in CIM |
| enabled | written | get_in_service(which='normal'); unset -> not written |
| like | not mapped | the writer never writes like= |

**Capacitor** (`exporter/capacitor.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, the Capacitor namespace |
| bus1 | written | bus_ref of the phase conductors; a wye's neutral is node 0, so it must be grounded |
| bus2 | not mapped | a shunt has one terminal |
| phases | written | the phase conductors; a delta across two is 1 |
| kvar | written | get_shunt_reactive_power(sections='maximum', voltage='nominal') (kVAr); maximumSections other than 1 raises |
| kv | written | nomU (kV), the voltage bPerSection was derived on |
| conn | written | phaseConnection Y/Yn -> wye, D -> delta; others raise |
| cmatrix | not mapped | kvar carries the susceptance |
| cuf | not mapped | kvar carries the susceptance |
| R | unset | untranscribed or raising on import; not in CIM |
| XL | unset | untranscribed or raising on import; not in CIM |
| Harm | unset | untranscribed or raising on import; not in CIM |
| Numsteps | not mapped | one section; more raise, as on import |
| states | written | [sections], the sections in service (0 or 1); normalSections is not written |
| normamps | unset | untranscribed or raising on import; not in CIM |
| emergamps | unset | untranscribed or raising on import; not in CIM |
| faultrate | unset | untranscribed or raising on import; not in CIM |
| pctperm | unset | untranscribed or raising on import; not in CIM |
| repair | unset | untranscribed or raising on import; not in CIM |
| basefreq | unset | untranscribed or raising on import; not in CIM |
| enabled | written | get_in_service(which='normal'); unset -> not written |
| like | not mapped | the writer never writes like= |

**CapControl** (`exporter/capcontrol.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, the CapControl namespace |
| element | written | the monitored Terminal's equipment: Line.<line or switch>, Capacitor.<shunt>; others raise |
| terminal | written | the monitored Terminal's sequenceNumber |
| capacitor | written | the one LinearShuntCompensator the control regulates |
| type | written | mode voltage, currentFlow, reactivePower, timeScheduled -> voltage, current, kvar, time; others raise |
| PTratio | written | ptRatio; unset -> not written, and a voltage control raises |
| CTratio | written | ctRatio; unset -> not written, and a current control raises |
| ONsetting | written | targetValue -+ targetDeadband / 2 (on_off_from_band), voltage / PTratio, current / CTratio; ON below OFF for voltage and time |
| OFFsetting | written | targetValue +- targetDeadband / 2 (on_off_from_band), voltage / PTratio, current / CTratio; an unset deadband raises |
| Delay | written | the shunt's aVRDelay (s); unset -> not written |
| VoltOverride | unset | untranscribed on import (S4-5); the engine's default |
| Vmax | unset | untranscribed on import (S4-5); the engine's default |
| Vmin | unset | untranscribed on import (S4-5); the engine's default |
| DelayOFF | unset | untranscribed on import (S4-5); the engine's default |
| DeadTime | unset | untranscribed on import (S4-5); the engine's default |
| CTPhase | unset | untranscribed or raising on import; not in CIM |
| PTPhase | written | 1-based place of monitoredPhase among the monitored equipment's phase conductors |
| VBus | unset | untranscribed or raising on import; not in CIM |
| EventLog | unset | untranscribed or raising on import; not in CIM |
| UserModel | unset | untranscribed or raising on import; not in CIM |
| UserData | unset | untranscribed or raising on import; not in CIM |
| pctMinkvar | unset | untranscribed or raising on import; not in CIM |
| Reset | unset | untranscribed or raising on import; not in CIM |
| ControlSignal | unset | untranscribed or raising on import; not in CIM |
| basefreq | unset | untranscribed or raising on import; not in CIM |
| enabled | written | the control's enabled; the shunt's controlEnabled must agree |
| like | not mapped | the writer never writes like= |

## S6e: DER and reactors (built 2026-11-09 at the user's word, with decisions P1-P9 as recommended; P2 confirmed by the user)

Content: PowerElectronicsConnection → one PVSystem per PhotoVoltaicUnit and one Storage per BatteryUnit,
SynchronousMachine → Generator, SeriesCompensator → series Reactor. Plan §8.1 row S6e; S4b, E4, E8 and E9 apply.
The user asked for S6e with the old GDM code's chop of a shared inverter ("CIM permits multiple DC devices behind
single inverter, so we will need to chop up the inverter same way previous code did"), and with cim18v17's new
unit attributes (`PowerElectronicsUnit.p`, `idlingP`). The spec was written alongside the code. Its decisions, P1-P9,
are at the end of this section; the user confirmed P2 (the raise above a unit's share) on 2026-11-09.

### Layout

```
cimhub_opendss/src/cimhub_opendss/exporter/
    injection.py     + rated_kv (a DER's kv from ratedU), equal_phases (E8; shared with load.py)
    inverter.py      a PowerElectronicsConnection chopped into one InverterPiece per unit (or per phase)
    pvsystem.py      PhotoVoltaicUnit -> PVSystem
    storage.py       BatteryUnit -> Storage
    generator.py     SynchronousMachine -> Generator (model 3 from its own voltage control)
    reactor.py       SeriesCompensator -> Reactor
```

`EXPORT_ORDER` gains `pvsystem, storage, generator, reactor` after `capcontrol`. `capcontrol` skips a
RegulatingControl that regulates one SynchronousMachine: the Generator carries it.

### Inverters: the chop (P1-P4)

A DSS PVSystem or Storage is one inverter with one DC device. CIM lets several PowerElectronicsUnits share one
PowerElectronicsConnection (a PV array and a battery behind one inverter). `get_inverter_units` (core) chops the
connection the way the old GDM exporter did:
- **Share:** each unit's maxP / the units' total maxP (1 for one unit). Each unit takes its share of the
  connection's ratedS, q, maxQ and minQ. With several units, every maxP must be above 0.
- **p:** each unit's own `PowerElectronicsUnit.p` (new in cim18v17) when every unit has one. Their sum must be the
  connection's p (rel `SUM_REL_TOL`). When no unit has p, each takes its share of the connection's p (the GDM rule).
  Some with p and some without raises.
- **Names (P3):** one unit keeps the connection's name (a round trip of a DSS deck is unchanged); several take their
  units' names.
- **Above the share (P2):** a piece whose output is above its share of ratedS (`KVA_REL_TOL` 1e-9) raises, because
  the engine would cut it. A DC-coupled PV that feeds its battery is the case: `hybrid_h1`'s PV at 80 kW of a
  100 kW maxP is inside its 100 kVA share, but the same PV at 300 kW on a 225 kVA share is not. The alternative,
  each piece keeping the whole rating, was offered and not taken.
- **Per phase (E8, P4):** a connection with one unit and unequal phases gives one 1-phase device per phase,
  `<name>_<phase>`. Each is a 1/n share of the connection and of the unit's own ratings (Pmpp, kWrated, the
  energies, idlingP). Several units with unequal phases raise, and so does a delta inverter with unequal phases.
- A unit of another class (a PowerElectronicsWindUnit) raises: DSS has no class for it.

Each piece's inverter slots:

| DSS slot | from |
|---|---|
| `bus1`, `phases`, `conn` | `device_connection`; cim18v17's connection has no `grounded`, so a wye inverter's neutral is node 0, as on import |
| `kv` | `ratedU` (kV, LL), / sqrt 3 for a 1-phase wye device (`rated_kv`, S4b-4 inverted). Not the bus's: a 240 V inverter on 120 V legs stays 240 V |
| `kVA` | share x ratedS |
| `kvarMax`, `kvarMaxAbs` | share x maxQ, share x -minQ; unset → not written |
| `Vminpu` | 1 / maxIFault (the importer's rule inverted) |
| `enabled` | `get_in_service(which='normal')` |

### PVSystem

- `Pmpp` = the unit's maxP x its 1/n share. `irradiance` = the unit's `PhotoVoltaicUnit.irradiance` (kW/m2, the
  gridappsd extension); unset, it falls back to p / Pmpp, so the panel gives exactly p. `kvar` = the piece's q
  (generation sign).
- `%Pmpp` = 100 x p / Pmpp when p is below the panel's Pmpp x irradiance (a PV cut to fit kVA, or held back); the
  engine caps the panel at it (S4b engine rules), so it gives CIM's p at the default P-T curve. Not written when p
  is the panel's power.
- `%Cutout=0` only when p > 0 and Pmpp x irradiance < 20 % of kVA (`ENGINE_CUTOUT_PERCENT`): the engine would
  switch the PV off below its default cut-out.
- Raises: maxP unset or 0, minP other than 0, p into the PV, p above Pmpp x irradiance.

### Storage (P6)

- `State` from batteryState: discharging, charging, waiting → idling. full, empty and unset raise. An output of the
  wrong sign for the state raises, and so do charging a full battery and discharging at or below its reserve (the
  engine idles both, S4b).
- **The output is `%Discharge`/`%Charge`** = |p| / kWrated x 100, and `kW` is never written. The engine keeps the
  setpoint as a percent of the kWrated at the moment `kW` is assigned, and the writer puts kW before kWrated.
  Probe: `kW=-5` then `kWrated=5` charges at 1 kW.
- `kWrated` = maxP x 1/n; minP must be -maxP (one kWrated both ways). `kWhrated`, `kWhstored` scaled likewise;
  `%reserve` = minimumE / ratedE x 100; `%EffCharge`, `%EffDischarge` from the efficiencies.
- `%IdlingkW` = idlingP / kWrated x 100 (new in cim18v17). A waiting battery's p must equal its idlingP (scaled)
  when both are set; otherwise its p is the idling loss.
- q must be 0, as on import.
- The writer's order puts the energies before `State`, which the engine checks when the state is assigned.

### Generator (P7)

- `kW` = -p and `kvar` = -q, kW first (S4b-8); `kVA` = ratedS; `conn` from `earthing` (true wye, false delta,
  unset raises; S4b-5); `kv` by `rated_kv`.
- **Model 3** when the machine's enabled RegulatingControl is a voltage control on its own terminal: `Vpu` =
  target / ratedU, `Maxkvar`/`Minkvar` = maxQ/minQ. A disabled control gives model 1, since DSS has no disabled
  PV bus. A control on another terminal, another mode, or a nonzero deadband, allowed limit or reverse target
  raises. Model 7 comes back as model 1 (CIM has no current limit; listed).
- `Xd`, `Xdp`, `Xdpp`, `H`, `D`, `XRdp` are unset: cim18v17 has no machine reactance or inertia (U13), so they
  take the engine's defaults (E4).
- **A PowerElectronicsWindUnit** (user, 2026-11-09, for a GIS spoke) is a model 1 Generator at the unit's output:
  `inverter_pieces` gives its name, bus, `kv`, its share of the inverter's `kVA`, and its share of p and q. DSS has
  no inverter wind class, and IEEE 9500 writes its turbines as Generators. The inverter's q limits and `maxIFault`
  have no home on a model 1 Generator and are not written. The deck reads back as a SynchronousMachine.

### Reactor (P8)

- `R`, `X` from `get_series_compensator` (ohm); `bus1`/`bus2` from `line.terminal_buses`; `normamps`/`emergamps`
  from `line.ratings`.
- A DSS Reactor has no mutual coupling: r0 or x0 other than r/x raises. A varistor raises.

### Core changes

- **`getters/der.py`:** `get_inverter_units(connection, active_unit, reactive_unit, *, sign)` →
  `InverterUnitShare(unit, share, p, q)` per unit, the chop above.
- **`getters/series_compensator.py`** (new): `get_series_compensator` → `SeriesCompensatorData(r, x, r0, x0,
  compensator_type, varistor_present, varistor_rated_current, varistor_voltage_threshold)`, in ohm, A and V; r and
  x are required. Per unit is not offered: a SeriesCompensator has no base of its own.
- **`shapes/der.cimtbl`:** `hybrid_h1`, a 150 kVA two-unit inverter (a 100 kW PV at 80 kW and a 50 kW battery
  charging at 20 kW, net 60 kW out).

### Findings

- **A model 3 Generator's YPrim depends on `Xdp`.** IEEE8500's `SteamGen1` sets 0.27 against the 0.28 default, a
  listed U13 difference in the solved state (S6f).
- **IEEE9500's Fuses come back named by the switch line they switch** (a CIM Fuse is the switch, S6b), and E6
  drops a SwtControl on a switch closed in both states. The deck test maps them.
- **IEEE9500's regulator taps are moved by its in-deck `Solve`,** and the original does not converge with
  controls off at tolerance 1e-10. Its YPrim and voltages wait for S6f.
- **IEEE8500's `Master-unbal`** redirects a file the original does not have; the test uses `Master.dss`.
- **A battery capped by its kVA** keeps only the capped output in CIM, so its `%Discharge` differs (listed).
- **The `der` atom's XfmrCode `ct`** left its reactances unset (the S6d finding); it now sets them.

### Tests

As built (`tests/test_export_der.py`, 29 tests; core `test_getters_der.py`, `test_getters_series_compensator.py`):
- **Per atom, in the engine** (§8.3), under `name`: per element, buses, NodeOrder and YPrim, then the voltages.
  Under `mrid`/`uri` only the voltages. Atoms `der/der`, `generator/gens`, `reactor/reactors` (listed: the reactor
  atom's `load.l3`, kV 2.4 → 2.40178, S6d L1).
- **Settings in the engine:** every PVSystem, Storage, Generator and Reactor slot the importer maps, and each PV's
  dispatch after Compile (`PVsystems.kW`/`kvar`; irradiance and pf may come back otherwise for the same output).
- **Whole decks** (`CIMHUB_DSS_DECKS`, `--roundtrip` but CDPSM): IEEE13_CDPSM, IEEE123_PV, IEEE8500, IEEE9500,
  ACEP_PSIL. The same elements on the same buses, and every DER and reactor set alike. Listed: classes the importer
  does not map (`relay.brkr1`, the EnergyMeters, DSS-11) and the switch controls above.
- **Spoke unit tests:** the hybrid inverter (records, then 200 kW PV and 40 kW storage in the engine at its
  shares), shares without p, the above-share raise, per phase, a wind unit, a full battery, a battery with q,
  idling, a disabled machine control (model 1), a control of another terminal, unset earthing, a coupled reactor.
- **Harness:** `engine_compare.engine_buses` (compile only; a disabled element is `("disabled",)`),
  `engine_settings` and `assert_same_settings`, shared with `test_export_injection.py`.
- **Goldens:** `export/der.dss`, `export/gens.dss`, `export/reactors.dss` (mrid).
- **Suite:** 1,157 passed, 80 skipped, 2 xfailed; every binding sweep deck (18) exports with its elements on the
  same buses.

### Decisions for S6e (recommended; built at the user's word 2026-11-09)

| # | question | recommendation |
|---|---|---|
| P1 | Chopping a shared inverter | The GDM rule: share = maxP / the units' total; ratedS, q and the q limits by share; each unit's own p when all have one (summing to the connection's), else its share of the connection's p; a partial set raises |
| P2 | A unit above its share of ratedS (**confirmed by the user 2026-11-09**) | Raises, naming the unit, its output and its share. Giving each piece the whole rating was the alternative |
| P3 | Names of the pieces | One unit: the connection's; several: the units' |
| P4 | Unequal phases (E8) | One unit: one 1-phase device per phase, each 1/n of the connection and of the unit; several units or delta raise |
| P5 | PV output | `irradiance` = the unit's (the extension, 2026-11-10), else p / Pmpp, at Pmpp = maxP; `%Pmpp` holds the output at p below the panel; `%Cutout=0` below the engine's 20 % so a running PV keeps running |
| P6 | Storage output | `%Discharge`/`%Charge`, never `kW` (the engine's percent of the kWrated of the moment); waiting is idling at idlingP |
| P7 | Generator model | 3 from an enabled voltage control on its own terminal; disabled → 1; model 7 → 1 (listed); reactances at the engine's defaults (U13) |
| P8 | Reactor coupling | r0/x0 must equal r/x; a varistor raises |
| P9 | DER kv | ratedU (S4b-4 inverted), not the bus's |

### Slot tables (S6e, generated from `SLOTS`)

**PVSystem** (`exporter/pvsystem.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names: the connection's for one unit, the unit's for several, <name>_<phase> per phase |
| phases | written | the phase conductors; a delta across two is 1 |
| bus1 | written | bus_ref of the phase conductors; a wye inverter's neutral is node 0 |
| kv | written | ratedU (kV, LL), / sqrt 3 for 1-phase wye (S4b-4 inverted) |
| irradiance | written | the unit's irradiance (kW/m2); unset -> the unit's output / Pmpp (get_inverter_units p, generation sign) |
| Pmpp | written | the unit's maxP (kW), x 1/n for one of n phases; unset raises, a minP other than 0 raises |
| pct_Pmpp | rule | 100 x output / Pmpp when the output is below Pmpp x irradiance, else not written; an output above it raises |
| Temperature | unset | untranscribed or raising on import; not in CIM |
| pf | not mapped | kvar carries q |
| conn | written | phaseConnection Y/Yn -> wye, D -> delta; others raise |
| kvar | written | the unit's share of q (generation sign: -q) |
| kVA | written | ratedS, the connection's, by the unit's share (inverter_pieces) |
| pct_Cutin | unset | untranscribed or raising on import; not in CIM |
| pct_Cutout | rule | 0 when the output is above 0 and Pmpp x irradiance below the engine's 20 % of kVA, else not written |
| EffCurve | unset | untranscribed or raising on import; not in CIM |
| P_TCurve | unset | untranscribed or raising on import; not in CIM |
| pct_R | unset | untranscribed or raising on import; not in CIM |
| pct_X | unset | untranscribed or raising on import; not in CIM |
| model | not mapped | model 1, the engine's default; others raise on import |
| Vminpu | written | 1 / maxIFault (the importer's rule inverted); unset -> not written |
| Vmaxpu | unset | untranscribed or raising on import; not in CIM |
| Balanced | unset | untranscribed or raising on import; not in CIM |
| LimitCurrent | unset | untranscribed or raising on import; not in CIM |
| yearly | unset | untranscribed or raising on import; not in CIM |
| daily | unset | untranscribed or raising on import; not in CIM |
| duty | unset | untranscribed or raising on import; not in CIM |
| Tyearly | unset | untranscribed or raising on import; not in CIM |
| Tdaily | unset | untranscribed or raising on import; not in CIM |
| Tduty | unset | untranscribed or raising on import; not in CIM |
| class_class | unset | untranscribed or raising on import; not in CIM |
| UserModel | unset | untranscribed or raising on import; not in CIM |
| UserData | unset | untranscribed or raising on import; not in CIM |
| debugtrace | unset | untranscribed or raising on import; not in CIM |
| VarFollowInverter | unset | untranscribed or raising on import; not in CIM |
| DutyStart | unset | untranscribed or raising on import; not in CIM |
| WattPriority | unset | untranscribed or raising on import; not in CIM |
| PFPriority | unset | untranscribed or raising on import; not in CIM |
| pct_PminNoVars | unset | untranscribed or raising on import; not in CIM |
| pct_PminkvarMax | unset | untranscribed or raising on import; not in CIM |
| kvarMax | written | maxQ, the connection's, by the unit's share (inverter_pieces); unset -> not written |
| kvarMaxAbs | written | -minQ, the connection's, by the unit's share (inverter_pieces); unset -> not written |
| kVDC | unset | untranscribed or raising on import; not in CIM |
| Kp | unset | untranscribed or raising on import; not in CIM |
| PITol | unset | untranscribed or raising on import; not in CIM |
| SafeVoltage | unset | untranscribed or raising on import; not in CIM |
| SafeMode | unset | untranscribed or raising on import; not in CIM |
| DynamicEq | unset | untranscribed or raising on import; not in CIM |
| DynOut | unset | untranscribed or raising on import; not in CIM |
| ControlMode | unset | untranscribed or raising on import; not in CIM |
| AmpLimit | unset | untranscribed or raising on import; not in CIM |
| AmpLimitGain | unset | untranscribed or raising on import; not in CIM |
| spectrum | unset | untranscribed or raising on import; not in CIM |
| basefreq | unset | untranscribed or raising on import; not in CIM |
| enabled | written | get_in_service(which='normal'); unset -> not written |
| like | not mapped | the writer never writes like= |

**Storage** (`exporter/storage.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names: the connection's for one unit, the unit's for several, <name>_<phase> per phase |
| phases | written | the phase conductors; a delta across two is 1 |
| bus1 | written | bus_ref of the phase conductors; a wye inverter's neutral is node 0 |
| kv | written | ratedU (kV, LL), / sqrt 3 for 1-phase wye (S4b-4 inverted) |
| conn | written | phaseConnection Y/Yn -> wye, D -> delta; others raise |
| kW | not mapped | %Discharge/%Charge carry the output: the engine makes kW a percent of the kWrated of the moment, and kWrated is written after kW |
| kvar | not mapped | q must be 0 (it raises on import); another raises |
| pf | not mapped | q is 0 |
| kVA | written | ratedS, the connection's, by the unit's share (inverter_pieces) |
| pct_Cutin | unset | untranscribed or raising on import; not in CIM |
| pct_Cutout | unset | untranscribed or raising on import; not in CIM |
| EffCurve | unset | untranscribed or raising on import; not in CIM |
| VarFollowInverter | unset | untranscribed or raising on import; not in CIM |
| kvarMax | written | maxQ, the connection's, by the unit's share (inverter_pieces); unset -> not written |
| kvarMaxAbs | written | -minQ, the connection's, by the unit's share (inverter_pieces); unset -> not written |
| WattPriority | unset | untranscribed or raising on import; not in CIM |
| PFPriority | unset | untranscribed or raising on import; not in CIM |
| pct_PminNoVars | unset | untranscribed or raising on import; not in CIM |
| pct_PminkvarMax | unset | untranscribed or raising on import; not in CIM |
| kWrated | written | the unit's maxP (kW), x 1/n for one of n phases; unset raises, a minP other than -maxP raises |
| pct_kWrated | unset | untranscribed or raising on import; not in CIM |
| kWhrated | written | ratedE (kWh), x 1/n for one of n phases; unset -> not written |
| kWhstored | written | storedE (kWh), x 1/n for one of n phases; unset -> not written |
| pct_stored | not mapped | kWhstored carries the energy |
| pct_reserve | written | minimumE / ratedE x 100; either unset -> not written |
| State | written | batteryState charging, discharging, waiting -> charging, discharging, idling; others raise, and so does an output of the wrong sign |
| pct_Discharge | written | discharging: the unit's output / kWrated x 100 |
| pct_Charge | written | charging: -(the unit's output) / kWrated x 100 |
| pct_EffCharge | written | chargingEfficiency (percent); unset -> not written |
| pct_EffDischarge | written | dischargingEfficiency (percent); unset -> not written |
| pct_IdlingkW | written | idlingP / kWrated x 100; waiting: its p (which idlingP, when set, must be) |
| pct_Idlingkvar | unset | untranscribed or raising on import; not in CIM |
| pct_R | unset | untranscribed or raising on import; not in CIM |
| pct_X | unset | untranscribed or raising on import; not in CIM |
| model | not mapped | model 1, the engine's default; others raise on import |
| Vminpu | written | 1 / maxIFault (the importer's rule inverted); unset -> not written |
| Vmaxpu | unset | untranscribed or raising on import; not in CIM |
| Balanced | unset | untranscribed or raising on import; not in CIM |
| LimitCurrent | unset | untranscribed or raising on import; not in CIM |
| yearly | unset | untranscribed or raising on import; not in CIM |
| daily | unset | untranscribed or raising on import; not in CIM |
| duty | unset | untranscribed or raising on import; not in CIM |
| DispMode | unset | untranscribed or raising on import; not in CIM |
| DischargeTrigger | unset | untranscribed or raising on import; not in CIM |
| ChargeTrigger | unset | untranscribed or raising on import; not in CIM |
| TimeChargeTrig | unset | untranscribed or raising on import; not in CIM |
| class_class | unset | untranscribed or raising on import; not in CIM |
| DynaDLL | unset | untranscribed or raising on import; not in CIM |
| DynaData | unset | untranscribed or raising on import; not in CIM |
| UserModel | unset | untranscribed or raising on import; not in CIM |
| UserData | unset | untranscribed or raising on import; not in CIM |
| debugtrace | unset | untranscribed or raising on import; not in CIM |
| kVDC | unset | untranscribed or raising on import; not in CIM |
| Kp | unset | untranscribed or raising on import; not in CIM |
| PITol | unset | untranscribed or raising on import; not in CIM |
| SafeVoltage | unset | untranscribed or raising on import; not in CIM |
| SafeMode | unset | untranscribed or raising on import; not in CIM |
| DynamicEq | unset | untranscribed or raising on import; not in CIM |
| DynOut | unset | untranscribed or raising on import; not in CIM |
| ControlMode | unset | untranscribed or raising on import; not in CIM |
| AmpLimit | unset | untranscribed or raising on import; not in CIM |
| AmpLimitGain | unset | untranscribed or raising on import; not in CIM |
| spectrum | unset | untranscribed or raising on import; not in CIM |
| basefreq | unset | untranscribed or raising on import; not in CIM |
| enabled | written | get_in_service(which='normal'); unset -> not written |
| like | not mapped | the writer never writes like= |

**Generator** (`exporter/generator.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, the Generator namespace; a wind unit as inverter_pieces names it |
| phases | written | the phase conductors; a delta across two is 1 |
| bus1 | written | bus_ref of the phase conductors; a wye machine's neutral is node 0 |
| kv | written | ratedU (kV, LL), / sqrt 3 for 1-phase wye (S4b-4 inverted) |
| kW | written | get_der_output total p (kW, generation sign); a wind unit: its share of the connection's p (inverter_pieces) |
| pf | not mapped | kvar carries q |
| kvar | written | get_der_output total q (kVAr, generation sign), after kW; a wind unit: its share of q |
| model | written | 3 (ConstantPV) when an enabled control regulates its own terminal's voltage, else 1 (ConstantPQ); model 7 comes back as 1 |
| Vminpu | unset | untranscribed or raising on import; not in CIM |
| Vmaxpu | unset | untranscribed or raising on import; not in CIM |
| yearly | unset | untranscribed or raising on import; not in CIM |
| daily | unset | untranscribed or raising on import; not in CIM |
| duty | unset | untranscribed or raising on import; not in CIM |
| dispmode | unset | untranscribed or raising on import; not in CIM |
| dispvalue | unset | untranscribed or raising on import; not in CIM |
| conn | written | earthing true -> wye, false -> delta; unset raises |
| status | unset | untranscribed or raising on import; not in CIM |
| gen_class | unset | untranscribed or raising on import; not in CIM |
| Vpu | written | model 3: the control's target / ratedU |
| maxkvar | written | model 3: maxQ (kVAr); unset -> not written |
| minkvar | written | model 3: minQ (kVAr); unset -> not written |
| pvfactor | unset | untranscribed or raising on import; not in CIM |
| forceon | unset | untranscribed or raising on import; not in CIM |
| kVA | written | ratedS (kVA); a wind unit: its share of the inverter's ratedS |
| MVA | not mapped | kVA carries ratedS |
| Xd | unset | no machine reactance or inertia in cim18v17 (U13); the engine's default |
| Xdp | unset | no machine reactance or inertia in cim18v17 (U13); the engine's default |
| Xdpp | unset | no machine reactance or inertia in cim18v17 (U13); the engine's default |
| H | unset | no machine reactance or inertia in cim18v17 (U13); the engine's default |
| D | unset | no machine reactance or inertia in cim18v17 (U13); the engine's default |
| UserModel | unset | untranscribed or raising on import; not in CIM |
| UserData | unset | untranscribed or raising on import; not in CIM |
| ShaftModel | unset | untranscribed or raising on import; not in CIM |
| ShaftData | unset | untranscribed or raising on import; not in CIM |
| DutyStart | unset | untranscribed or raising on import; not in CIM |
| debugtrace | unset | untranscribed or raising on import; not in CIM |
| Balanced | unset | untranscribed or raising on import; not in CIM |
| XRdp | unset | no machine reactance or inertia in cim18v17 (U13); the engine's default |
| UseFuel | unset | untranscribed or raising on import; not in CIM |
| FuelkWh | unset | untranscribed or raising on import; not in CIM |
| pct_Fuel | unset | untranscribed or raising on import; not in CIM |
| pct_Reserve | unset | untranscribed or raising on import; not in CIM |
| Refuel | unset | untranscribed or raising on import; not in CIM |
| DynamicEq | unset | untranscribed or raising on import; not in CIM |
| DynOut | unset | untranscribed or raising on import; not in CIM |
| spectrum | unset | untranscribed or raising on import; not in CIM |
| basefreq | unset | untranscribed or raising on import; not in CIM |
| enabled | written | get_in_service(which='normal'); unset -> not written |
| like | not mapped | the writer never writes like= |

**Reactor** (`exporter/reactor.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | Names, the Reactor namespace |
| bus1 | written | terminal_buses (line.py): the first terminal on the phase conductors |
| bus2 | written | terminal_buses: the second terminal |
| phases | written | the phase conductors |
| kvar | not mapped | R and X carry the impedance; r0/x0 other than r/x raise |
| kv | unset | untranscribed or raising on import; not in CIM |
| conn | unset | untranscribed or raising on import; not in CIM |
| Rmatrix | not mapped | R and X carry the impedance; r0/x0 other than r/x raise |
| Xmatrix | not mapped | R and X carry the impedance; r0/x0 other than r/x raise |
| Parallel | not mapped | R and X carry the impedance; r0/x0 other than r/x raise |
| R | written | get_series_compensator r (ohm) |
| X | written | get_series_compensator x (ohm) |
| Rp | not mapped | R and X carry the impedance; r0/x0 other than r/x raise |
| Z1 | not mapped | R and X carry the impedance; r0/x0 other than r/x raise |
| Z2 | not mapped | R and X carry the impedance; r0/x0 other than r/x raise |
| Z0 | not mapped | R and X carry the impedance; r0/x0 other than r/x raise |
| Z | not mapped | R and X carry the impedance; r0/x0 other than r/x raise |
| RCurve | unset | untranscribed or raising on import; not in CIM |
| LCurve | unset | untranscribed or raising on import; not in CIM |
| LmH | not mapped | R and X carry the impedance; r0/x0 other than r/x raise |
| normamps | written | get_current_limits normal (A); unset -> not written |
| emergamps | written | get_current_limits emergency (A); unset -> not written |
| faultrate | unset | untranscribed or raising on import; not in CIM |
| pctperm | unset | untranscribed or raising on import; not in CIM |
| repair | unset | untranscribed or raising on import; not in CIM |
| basefreq | unset | untranscribed or raising on import; not in CIM |
| enabled | written | get_in_service(which='normal'); unset -> not written |
| like | not mapped | the writer never writes like= |

## S6f: bus coordinates, power flow parity, idempotence (built 2026-11-09 at the user's word, with decisions F1-F7 as recommended)

Content: equipment Locations → `Buscoords` rows; whole-deck power flow parity in the engine (plan §5, §8.3); the
idempotence sweep. Plan §8.1 row S6f. The user asked for "the next phase" after confirming S6e's P2, so this spec
was written alongside the code. Its decisions, F1-F7, are at the end of this section; F3 and F5 carry an open
question each.

### Layout

```
cimhub_core/src/cimhub_core/getters/location.py    get_location_coordinates (new)
cimhub_opendss/src/cimhub_opendss/exporter/
    buscoords.py     equipment Locations -> Buscoords rows (last in EXPORT_ORDER)
    regcontrol.py    PTphase 1 on a 1-phase winding (a fix the idempotence sweep found)
cimhub_opendss/tests/
    engine_compare.py         + assert_same_power_flow, engine_coordinates
    test_export_buscoords.py  the coordinate atoms
    test_export_decks.py      parity and coordinates on 16 decks, idempotence on the 18 binding decks
```

The writer already writes `Buscoords <stem>_buscoords.csv` or `LatLongCoords <stem>_latlongcoords.csv` beside the
deck (S6a, §8.2).

### Coordinates (F1)

The importer's S5-1 inverted. `get_location_coordinates(equipment)` (core) gives the Location's points in
PositionPoint `sequenceNumber` order and each Terminal's point:
- one point per Terminal: they pair in order (a one-Terminal POINT, a two-point LINESTRING);
- a two-terminal polyline (more than two points): its ends go to its Terminals (CIM's line route);
- one point on equipment with several Terminals: a device point (F8), which pairs with no Terminal, so `terminals`
  is None;
- any other count raises, and so do a point without a sequenceNumber or a position, and two points with one
  number. No Location, or a Location without points, is None. `zPosition` is not read.

`buscoords.export` gives each Terminal's bus of located equipment that Terminal's point, one row per bus in the
network's ConnectivityNode order:
- Equipment without a Location gives none, so a bus no located equipment touches has no coordinates, as on import
  (S5-3).
- Two points for one bus (rel 1e-9) raise, naming both pieces of equipment.
- **Device points (F8, 2026-11-10):** the importer puts a switch, fuse or transformer at its buses' centroid (S5-8),
  so a device point places only the buses no Terminal point placed. With k of its N buses open, each goes at
  (N · point − Σ placed) / k: a two-terminal device next to one placed bus reflects it across the point, which gives
  back the importer's bus to float noise (the midpoint rounded a + b once); with none placed, every bus goes at the
  point. A device with one open bus goes first, so a chain of switches fills from its placed end. The parity and
  atom tests compare coordinates to rel 1e-12 / abs 1e-9 (`assert_same_coordinates`) for that noise. An import
  under `device_geometry="linestring"` (S5-9) has no device points: each device's buses pair one per Terminal and
  come back exactly.
- The CoordinateSystem picks the file: `urn:ogc:def:crs:OGC:1.3:CRS84` is `LatLongCoords` (x = longitude, written
  latitude first), `OpenDSSLocalBusCoordinates` is `BusCoords` (the importer's `COORDINATE_SYSTEMS` inverted).
  Another URN, or Locations in two systems, raise.
- Non-conducting resources with a Location (a Substation) are skipped: they have no bus.

### Power flow parity (F2-F4)

`engine_compare.assert_same_power_flow(original, written)`: every node voltage within 0.1 % of its bus's base
(the original's `kVBase`), both decks solved with **controls off** at the original's control state and
untranscribed settings. What the written deck had otherwise is returned, and each deck's set is listed in the test
so the list stays true:

| copied from the original | why | decks |
|---|---|---|
| `Transformer.taps`, `Capacitor.states` | an in-deck `Solve` moves them; the importer reads the deck's text (F2) | IEEE13_original, IEEE37, IEEE13_Assets (caps), IEEE123_PV, IEEE123_deconfliction, IEEE9500 |
| `earthmodel` | not in CIM (E10); Carson against the engine's Deri moves a geometry line's YPrim by 0.6 % | IEEE13_CDPSM, IEEE13_Assets, IEEE4 Bal (DY, GrdYD, YD, YY), IEEE123_PV, IEEE9500, ACEP_PSIL |
| `Load.Vminpu`/`Vmaxpu` | not in CIM (L6); below Vminpu a load turns constant Z | IEEE13_CDPSM, every IEEE4 deck, IEEE8500 (all 1,177 loads `Vminpu=.88`), IEEE9500 |
| `Transformer.ppm_antifloat` | not in CIM; `ppm=0` against the engine's 1 ppm moves a floating delta's voltage to ground | IEEE123, 4bus-OYOD-UnBal, IEEE123_PV, IEEE123_deconfliction, IEEE8500, IEEE9500 |

`earthmodel` goes into a copy of the written deck after `New Circuit` (after Compile the lines are built); the
others are set after Compile. Results (worst node, % of the bus base):

| deck | nodes | worst |
|---|---|---|
| IEEE13_CDPSM | 57 | 0.056 % (675.3; the loads' kV 2.4 → 2.40178, L1) |
| IEEE13_original | 41 | 0.009 % |
| IEEE13_Assets | 41 | 0.010 % |
| IEEE123 | 278 | 0.015 % |
| IEEE123_PV | 442 | 0.017 % |
| IEEE123_deconfliction | 271 | 0.020 % |
| IEEE37 | 117 | 0.0003 % |
| IEEE4: DY, GrdYD, OYOD, YD, YY (Bal), OYOD-UnBal | 12-13 | 0.003-0.018 % |
| IEEE8500 | 8,531 | 0.072 % (a secondary; not traced further) |
| IEEE9500 | 9,536 | 0.095 % (m2001-mt1: B3's 1 mOhm switch against the original's 1e-6 ohm, 300 A from a 250 kVA microturbine) |
| ACEP_PSIL | 24 | 0.000 % |

Every deck's bus coordinates come back as the engine had them (`engine_coordinates`, compile only). Not in parity:
YYD-Master (it ends in a fault study with every load disabled, and its `Export` commands write files beside it)
and IEEE8500 `Master-unbal` (it redirects a file the original lacks).

### Idempotence (F6)

export(import(export(import(deck)))) is the same text as export(import(deck)), deck and coordinate files, on all
18 binding sweep decks, under `name_source="name"`. Under `mrid` it cannot be: the importer compiles an mRID from
the native name, so a second pass prefixes again (`ln_ln_632633`).

The sweep found one bug: **IEEE37's `creg1c`** (coil C → B) comes back `.2.3`, and the exporter wrote `PTphase=2`,
the place of C among the coil's conductors. A 1-phase DSS winding has one phase, and the importer raises on 2. The
exporter now writes 1 on a 1-phase winding; the re-import then monitors B, the same coil voltage.

### Findings

- **Protection has no trip settings (F5).** Recloser `PhaseTrip`/`GroundTrip` and Relay settings are untranscribed
  (DSS-11's protection TODO). In a controls-on solve of the exported IEEE13_CDPSM, `Recloser.Rec1` trips at the
  engine's 1 A default, recloses and locks out after 7 control iterations. Parity runs controls off, so protection
  does not act there.
- **Protection controls are written disabled (V7, the user's rule 2026-11-09, until U15).** Every Fuse and Recloser
  control gets `enabled=no`, keeping `RatedCurrent`, `Shots`, `RecloseIntervals` and its states. Without CIM trip
  settings or curves, the engine's defaults locked out a GIS spoke's feeders behind their head reclosers on the
  first snapshot. A fuse blew under backfeed. The switch Line stays as CIM says, and an open switch is still opened
  by its `Open` command (E6). The importer reads a disabled control back as the same Fuse or Recloser (its `enabled`
  is untranscribed). The engine comparisons treat the original's controls as disabled (`engine_compare.as_exported`).
  Once U15 maps the settings, a device that has them is written enabled (`switch.PROTECTION_ENABLED`).
- **Controls on is fragile for parity (F2).** From the same starting state, IEEE9500's `vreg3_a` ends on tap 3 in the
  original and 4 in the export: the 0.095 % differences tip one band decision. IEEE13_CDPSM's deck itself ends in
  `Set Controlmode=OFF` with taps set by hand.
- **Untranscribed solution settings move voltages by percent (F3).** Without them a plain solve of the exported
  IEEE8500 is 5.8 % off on its secondaries (Vminpu), the IEEE4 decks 2-9 % (earthmodel, Vminpu), 4bus-OYOD-UnBal
  9 % (Vminpu 0.7, ppm).
- YYD-Master writes `YYDTestCase_*` result files beside itself whenever the engine compiles it; the tests never
  compile it.

### Tests

As built (core `test_getters_location.py`, 6 tests; opendss `test_export_buscoords.py`, 7; `test_export_decks.py`,
34):
- **Getter:** one point per Terminal, a polyline's ends, no Location, and the raises (a count the Terminals cannot
  pair, a repeated number, a missing position).
- **Coordinate atoms** (`buscoords/local`, `buscoords/latlong`): the engine's coordinates equal the original's
  (far stays without, ghost is no bus); lat-long written latitude first under `LatLongCoords`; b1's last row; the
  raises (two points for one bus, an unmapped crsUrn, two systems).
- **Parity and coordinates** on the 16 decks above; **idempotence** on the 18 binding sweep decks. The external
  decks are marked `roundtrip`.
- **Suite:** 1,194 passed. With the external decks and `--roundtrip`, every opendss test passes.

### Decisions for S6f (recommended; built at the user's word 2026-11-09)

| # | question | recommendation |
|---|---|---|
| F1 | Bus coordinates | Each Terminal's point from its equipment's Location (one per Terminal, or a two-terminal polyline's ends); conflicting points raise; CRS84 → LatLongCoords, the local URN → BusCoords, others raise |
| F2 | Parity solve | Controls off, from the original's compiled taps and capacitor states; control settings are compared one by one (S6c, S6d). Controls on was the alternative: deterministic only when no band decision is near its edge |
| F3 | Untranscribed settings that move voltages (**open**; earthmodel closed by S6g) | The harness copies earthmodel, load Vminpu/Vmaxpu and transformer ppm_antifloat, listed per deck; the exporter leaves them at the engine's defaults (E4, E10, L6). Open: whether to give them a home (a CIMHub extension, or an exporter option such as `load_vminpu=`), since IEEE8500's export solves 5.8 % off without Vminpu |
| F4 | Tolerance | 0.1 % of the bus base (plan §5); the largest residual is B3's switch impedance on IEEE9500 (0.095 %) |
| F5 | Protection settings (**open**; reclosing closed by S6g, trip settings still open, G5) | Untranscribed for now (DSS-11), listed: the exported recloser trips at the engine's 1 A in a controls-on solve. Open: map Recloser PhaseTrip/GroundTrip (and Relay settings) once DSS-11's protection TODO picks the CIM classes |
| F6 | Idempotence | Under `name_source="name"`, deck and coordinate files; `mrid` re-prefixes by design |
| F7 | Decks out of parity | YYD-Master (a fault study that writes files) and IEEE8500 Master-unbal (a missing redirect): idempotence only |
| F8 | Device points (2026-11-10, the user's pick) | A single POINT on multi-terminal equipment places only open buses, at (N · point − Σ placed) / k: reflection across the point next to a placed bus, the point itself with none. Placing every open bus at the point was the alternative: simpler and closer to real GIS, but a DSS round trip moves a bus only a device touches (a regulator's output) |

### Slot table (S6f, generated from `SLOTS`)

**Buscoords** (`exporter/buscoords.py`)

| DSS slot | kind | from / why |
|---|---|---|
| name | written | the bus (Names.bus) of each Terminal of located equipment |
| x | written | the Terminal's PositionPoint xPosition (get_location_coordinates); a bus only a device point touches is solved from it as the centroid of the device's buses |
| y | written | as x, from yPosition |
| geographic | written | crsUrn CRS84 -> true (LatLongCoords), OpenDSSLocalBusCoordinates -> false; others raise |

## S6g: earth model and reclose sequences (built 2026-11-09 at the user's word, with decisions G1-G5 as recommended)

Content: the user added `EarthResistivity` (WiresEXT) and rebuilt the protection profile with
`RecloseSequence.ProtectedSwitch` (2026-11-09). That gives two of S6f's open items a home: F3's `earthmodel`, and
the reclosing part of F5. Both directions are changed here, because each value must come back.

### Layout

```
cimhub_core/src/cimhub_core/
    getters/earth.py             get_earth_resistivity (new): EarthData(model, rho ohm-m, earth_return_gmr m)
    getters/switch_state.py      + get_reclose_delays: the recloseDelay of each RecloseSequence, in step order
    shapes/line_by_wire_configuration.cimtbl   + EarthResistivity earth_carson on wc_601
    shapes/switch.cimtbl         + RecloseSequence sw_r1_rs1, sw_r1_rs2 (0.5 s, 2 s)
cimhub_opendss/src/cimhub_opendss/
    schema/linkml/controls/recloser.yaml       + dss_default Shots 4, RecloseIntervals [0.5 2 2] (DSS-6)
    importer/cimtbl/geometry.py  earth_statement: the deck's EarthResistivity, first in linegeometry.cimtbl
    importer/cimtbl/line.py      RecloseSequence rows; rho on a geometry line; spacing= configurations name the earth
    exporter/options.py          earthmodel = the configurations' one model
    exporter/line.py             rho on a geometry line
    exporter/switch.py           Recloser Shots and RecloseIntervals
```

### Earth model (G1, G2)

**Import.** A deck with geometry (a LineGeometry, or a Line by `spacing=`) gets one `EarthResistivity`, mRID
`earth`, written first in `linegeometry.cimtbl`. Every WireConfiguration names it, the `spacing=` lines' synthesized
ones too.
- `earthModelType` comes from `Set earthmodel`: Carson → carson, Deri → deri. `FullCarson` raises, because
  EarthModelKind has no member for it.
- `rho` is the geometry lines' `rho`, which must all agree.
- Unset values take the engine's defaults, Deri and 100 ohm-m, listed as `# defaulted:` (DSS-6).
- `rho` on a line without geometry raises: it computes nothing there.
- A deck without geometry gets no EarthResistivity, since its earth model computes nothing. Its `Set earthmodel` is
  then lost; the parity harness still lists it for IEEE13_CDPSM, IEEE123_PV, IEEE9500 and ACEP_PSIL.

**Export.**
- `Set earthmodel` is the one model of every WireConfiguration (`options.earth_model`). DSS's earthmodel is the
  deck's, so configurations over different models raise. So does one without an EarthResistivity beside one with,
  which would silently take the other's model.
- Each geometry line writes `rho` from its configuration's EarthResistivity. DSS's LineGeometry has no rho.
- `earthReturnGMR` is not written: DSS derives Carson's earth return from rho and the frequency.
- The per-line `EarthModel` slot is not written; the deck's `Set earthmodel` carries it.

**Profile note:** `EarthResistivity.rho` is typed `Resistance` (ohm). A resistivity is ohm-m, and the profile has no
CIMUnit for it, so the value is read in ohm and stands for ohm-m (`get_earth_resistivity`).

### Reclose sequences (G3, G4)

**Import.** A Recloser's `Shots` - 1 reclosures become one `RecloseSequence` each, `<switch>_rs<n>`, with
`ProtectedSwitch` the switch, `recloseStep` n and `recloseDelay` = `RecloseIntervals[n]` (s). The engine's rules,
probed:
- `RecloseIntervals` defaults to (0.5, 2, 2) and `Shots` to 4, and the engine keeps the first `Shots` - 1 intervals.
  Unset values are defaulted from the schema's new `dss_default`s and listed on the first row.
- Giving the intervals sets `Shots` to their count + 1, so both given and disagreeing raise: the engine's result
  depends on their order.
- `Shots` above 4 without intervals raises: the engine reads past its three defaults (probe: `5.5e-310`).
- `Shots=1` gives no sequence.

All 53 IEEE9500 reclosers set `Shots=3`: two reclosures at 0.5 s and 2 s.

**Export.** A Recloser writes `Shots` = its RecloseSequences + 1 and `RecloseIntervals` their delays in step order
(`get_reclose_delays`; the steps must be 1..n, each with a delay). A recloser without sequences writes `Shots=1`: no
reclosure, as CIM says (G4). RecloseSequences on another ProtectedSwitch (a Breaker) raise: in DSS a Relay recloses
a breaker, and Relay is not mapped (DSS-11).

### What is still open (G5)

- **Trip settings.** The pickups (`PhaseTrip`, `GroundTrip`, `PhaseInst`, `GroundInst`), the curves
  (`PhaseFast`/`PhaseDelayed`/`GroundFast`/`GroundDelayed`), the time dials and `NumFast` still have no attribute. In
  cim18v17 the overcurrent function blocks carry only `operatingQuantityType`. So the exported recloser still trips
  at the engine's 1 A default in a controls-on solve (S6f F5). CIM17's `RecloserInfo` had `phaseTripRating`,
  `groundTripRating` and `recloseLockoutCount`. A pickup (and a time-current curve link) on
  `OverCurrentProtectionFunctionBlock`, or an extension on the Recloser, would close it.
- `EarthModelKind` has no `fullCarson`.
- Fuse's minimum-melt association is spelled `MiinimumMeltCurve` in the profile.

### Findings

- The parity harness compared the original's earth model with the engine's Deri, not with the written deck. It now
  compiles the written deck and reads its earthmodel. With S6g, `earthmodel` drops from the parity lists of every
  deck with geometry: IEEE13_Assets and the IEEE4 Bal decks (DY, GrdYD, YD, YY).

### Tests

- Core: `test_getters_earth.py` (2) and `test_getters_reclose.py` (4): model and rho; no earth; delays in order and in
  ms; no sequence; a missing step; an unset delay.
- Import:
  - goldens: `line/codes` (`sw_rec1`'s two sequences), `line/geometry`, `geometry/assets_linegeometry`
    (`EarthResistivity earth`), IEEE13_CDPSM's `line.cimtbl`;
  - `test_cimtbl_line.py`: the four reclose rules, and three new raises (Shots=6 without intervals, Shots and
    intervals disagreeing, rho without geometry);
  - `test_cimtbl_geometry.py`: the deck's model and rho, the defaults, FullCarson, disagreeing rho, no geometry.
- Export:
  - goldens: `line/codes`, `line/geometry`, `line/cables`, `line/states` (`Set earthmodel=Deri`, `rho=100`,
    `Shots=3 RecloseIntervals=[0.5 2]`);
  - `test_export_line.py`: the engine's `Shots`/`RecloseIntervals` equal the original's on `codes` and `states`; a
    recloser without sequences is `Shots=1`; sequences on a Breaker raise; geometry lines write their earth; two
    earth models raise.
- Every atom's YPrim and voltages are still equal in the engine.

### Decisions for S6g (recommended; built at the user's word 2026-11-09)

| # | question | recommendation |
|---|---|---|
| G1 | Where the earth goes | One EarthResistivity per deck (DSS's earthmodel is global), named by every WireConfiguration; rho from the geometry lines, which must agree; defaults listed (DSS-6) |
| G2 | Earth on export | `Set earthmodel` from the configurations' one model (several raise); `rho` on each geometry line |
| G3 | Reclosures on import | Shots - 1 RecloseSequences at RecloseIntervals, the engine's defaults filling either; the cases the engine resolves by order or by reading past its defaults raise |
| G4 | A recloser with no RecloseSequence | `Shots=1`, no reclosure, as CIM says, rather than the engine's 4 |
| G5 | Trip settings (**open**, TODO U15) | Still untranscribed: they need an attribute in the profile (see "What is still open"). Tracked as `.development/UPSTREAM_REQUESTS.md` U15 until the user repairs the FunctionBlock package in the UML |
