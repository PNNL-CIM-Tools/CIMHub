# OpenDSS rewrite on `.cimtbl`: wave 1 plan

**Status:** moved from CIMHub_2_0 on 2026-11-07 and updated with the user's decisions of that day (§6). In
CIMHub_2_0 (seeded here in F2): the Phase 1 `LineCode` slice, the inline `Transformer` mapper, the DSS bus graph
(`importer/cimtbl/bus_graph.py`, to be rewritten on `cimtopology.core`, §3.1) and four reader fixes (§3.4).
Every decision in §6 is made; DSS-10 is deferred. Slices are built and approved one at a time (DSS-12).
**S0, S1 and S2 done 2026-11-07; S3a done 2026-11-08** (§4); S3b (XfmrCode templates) done 2026-11-08; S4a (Load, Capacitor, CapControl) done 2026-11-08; S4b (PVSystem, Storage, Generator, Reactor) done 2026-11-08; S5 (bus coordinates, the deck sweep test, G7) done 2026-11-08. The importer is complete for every mapped class; S6 (the exporter) is planned in §8, approved 2026-11-09; S6a (framework, writer, Vsource) done 2026-11-09; S6b (lines, wire catalogs, switches) done 2026-11-09; S6c (transformers, XfmrCode, regulators, RegControl) done 2026-11-09; S6d (Load, Capacitor, CapControl) done 2026-11-09; S6e (PVSystem, Storage, Generator, Reactor; the shared-inverter chop) done 2026-11-09; S6f (bus coordinates, power flow parity on 16 decks, idempotence on the 18 binding decks) done 2026-11-09. S6g (EarthResistivity and RecloseSequence, both directions, on the user's new profile classes) done 2026-11-09. S6 is complete; S7 (switch over, delete the old code) next. **S8 (LoadShapes, both directions) built 2026-11-21, uncommitted** (§9).
**Master plan:** [`REWRITE_PLAN.md`](REWRITE_PLAN.md) (this is its F2 wave for `cimhub_opendss`). **Contract,
shapes, spec format:** the `cimtbl-import-contract`, `cimtbl-shapes` and `cimtbl-mapping-spec` skills.
**Mapping spec:** `cimhub_opendss/docs/CIMTBL_MAPPING.md`, grown one section per slice.

The wave ends with `dss_to_cim` building cim18v17 only from the `.cimtbl` artifacts and `cim_to_dss` reading
cim18v17, with the old importer (`importer/<class>/`, 9,300 lines), its cimhub_2026 imports and the Python atoms
deleted.

## 1. What the decks contain

Census of 12 decks (IEEE13_CDPSM, IEEE13_assets, IEEE13_original, IEEE37, IEEE123, IEEE8500, ieee9500, EPRI J1/K1/M1,
IEEE13_OCHRE, ACEP_PSIL) through today's `DssReader`, 2026-11-06 (throwaway scripts; S0's deck sweep test
replaces them).

| class | objects | decks | mapped by | notes |
|---|---:|---:|---|---|
| Buscoords | 14,465 | 11 | done (S5) | the largest table. The S5 reader fix found 489 more in the IEEE123 family (whitespace-separated files). An equipment Location per piece of equipment, a PositionPoint per Terminal; G7 closed (about 7,900 rows/s bind) |
| Line | 14,184 | 14 | done (S3a) | 2,850 linecode ft · 2,626 geometry · 2,473 linecode km · 1,995 linecode, **no units** · 1,866 linecode m · 1,500 linecode kft · 600 inline r1/x1 (159 of them switches) · 112 bare switches · 1 inline matrix · 1 spacing+wires |
| Load | 7,206 | 14 | done (S4a) | q from `pf` on 4,053, from `kvar` on 3,004; model 1 (3,824), 4 (2,862), 2 (28), 5 (19) |
| Transformer | 3,945 | 14 | done (S3a inline + regulated, S3b by XfmrCode) | of the 3,853 in the 12 census decks: 2,474 by XfmrCode (2,468 single-phase 3-winding center tap) · 1,304 inline single-phase (1,278 in J1) · 28 inline in a `bank` (regulators) · 47 inline 3-phase, 10 of them with `phases` unset (default 3) |
| LineCode | 290 | 13 | done (Phase 1) | open points DSS-3, DSS-4 |
| PVSystem | 208 | 5 | S4 | done (S4b) |
| WireData | 121 | 3 | S2 | |
| LineGeometry | 82 | 4 | S2 | some reference a LineSpacing (`spacing=`), some CN/TS cables |
| RegControl | 69 | 12 | done (S3a) | |
| Monitor | 52 | 3 | not mapped | DSS-11 |
| Capacitor | 45 | 11 | done (S4a) | |
| XfmrCode | 32 | 6 | done (S3b) | TankEnd templates; center taps by lugs (DSS-2 amended, D10) |
| CapControl | 28 | 6 | done (S4a) | 3 in IEEE13_OCHRE/IEEE13_Assets monitor their own capacitor (recounted 2026-11-08); CIM-Tables' `Update` form writes them (U3 closed) |
| LoadShape | 16 | 4 | done (S8) for the shapes a Load names as `yearly`; others not mapped (DSS-11) | the user's ConformLoad pattern (GLM §8.9); `CIMTBL_MAPPING.md` S8 |
| Vsource | 14 | 14 | S1 | `New Circuit` is read as Vsource `source` |
| Generator | 13 | 2 | S4 | done (S4b), shape `synchronous_machine`; kvar replayed in deck order (S4b-8) |
| Storage | 6 | 3 | S4 | done (S4b) |
| EnergyMeter | 6 | 6 | not mapped | DSS-11 |
| CNData, TSData | 3, 1 | 3, 1 | S2 | |
| LineSpacing | 3 | 1 | S2 | |
| Reactor | 3 | 3 | S4 | done (S4b): series only, shape `series_compensator`; shunt and neutral reactors raise |
| Fuse, Recloser | 32, 53 | 1 (ieee9500 `Switches.dss`; IEEE13_CDPSM has one of each) | done (S3a, DSS-9) | recounted through the S0 reader (the old census saw 1 each). Every one switches a `_sw` line with `switch=True`, which also has a `SwtControl` (112) |
| Relay | 0 | 0 | not mapped | DSS-11 |
| AutoTrans | 0 | 0 | not mapped until a deck has one (S3b-1, 2026-11-08) | `AutoTransformer` + `AutoTransformerEnd`; the old `autotrans.py` has no deck, so an atom is the only test |

## 2. Artifacts and their order

One file per native class (D4). The master imports them in this order, which is the reference order (G6):

| # | artifact | native class | shape | references |
|---|---|---|---|---|
| 0 | `<model>.cimtbl` (master) | `New Circuit` name, `Set defaultbasefreq`, the walk's bus voltages | `common` (Substation, Feeder, BaseFrequency, BaseVoltage) | |
| 0a | `bus.cimtbl` | none (the topology walk, section 3.1) | `ConnectivityNode` + `BaseVoltage` (cim18v17's new association) | 0 |
| 0b | `zip_fractions.cimtbl` | none (fixed content, always written) | `common` (LoadResponseCharacteristic `zip_constant_pq`, `_z`, `_i`; DSS-7) | |
| 1 | `wiredata.cimtbl`, `cndata.cimtbl`, `tsdata.cimtbl` | WireData, CNData, TSData | `wire_info` | |
| 2 | `linespacing.cimtbl` | LineSpacing | `line_by_wire_configuration` (XYSpacing) | |
| 3 | `linegeometry.cimtbl` | LineGeometry | `line_by_wire_configuration` (XYSpacing + WireConfiguration) | 1, 2 |
| 4 | `linecode.cimtbl` | LineCode | `line_by_impedance` (catalog) | |
| 5 | `xfmrcode.cimtbl` | XfmrCode | `transformer_template`, `transformer_template_1ph` | |
| 6 | `vsource.cimtbl` | Vsource | `source` | 0, 0a |
| 7 | `line.cimtbl` | Line (incl. `Switch=y`; the Fuse/Recloser that switches it sets the class, DSS-9) | `line_by_impedance`, `line_by_wire_configuration`, `switch`; synthesized templates under `# synthesized` | 0, 3, 4 |
| 8 | `transformer.cimtbl` | Transformer (one a RegControl names → `VoltageRegulator`, DSS-13) | `transformer_by_template`, `transformer_by_ends`, new: `voltage_regulator`; synthesized tank configurations (DSS-2) | 0, 5 |
| 8b | `autotrans.cimtbl` | AutoTrans | new: `auto_transformer` (DSS-11) | 0 |
| 9 | `regcontrol.cimtbl` | RegControl | `regulator` (RatioTapChanger on an AutoTransformerEnd + TapChangerControl) | 8 |
| 10 | `load.cimtbl` | Load | `load`; `exp_` LoadResponseCharacteristic rows (DSS-7) | 0, 0b |
| 11 | `capcontrol.cimtbl` | CapControl | `shunt` (RegulatingControl) | 7 |
| 12 | `capacitor.cimtbl` | Capacitor | `shunt` (compensator) | 0, 11 |
| 13 | `pvsystem.cimtbl`, `storage.cimtbl` | PVSystem, Storage | `der` | 0 |
| 14 | `generator.cimtbl` | Generator | `synchronous_machine` | 0 |
| 15 | `reactor.cimtbl` | Reactor | `series_compensator` | 0 |
| 16 | `buscoords.cimtbl` | Buscoords | `location` (CoordinateSystem, Location, PositionPoint, `Update` of PowerSystemResource) | every equipment file (their bound Terminals: `bound_parts`, S5-2) |

CapControl comes before Capacitor. In the `shunt` shape the compensator names its control
(`RegulatingControl` column), and the control names the monitored Terminal, which here is always a line's
(`ln_<line>_T<n>`). The orchestrator's `MAPPING_ORDER` holds this order, and a test loads the reference model
through it.

## 3. Native passes the mappers share

These run on the reader's objects, before any mapper, and produce plain Python data. They construct no CIM (I5).

### 3.1 Bus voltages (DSS-1)

Every equipment row needs a `BaseVoltage`, but a DSS Line, switch or reactor has no voltage of its own. OpenDSS
assigns one with `CalcVoltageBases`: it solves a no-load power flow and then snaps each bus's kV to the nearest value
in `Set voltagebases`. ExportCIMXML (the EPRI reference exporter, `importer/ExportCIMXML.pas`) reads that solved
`kVBase`. The old importer instead walks the CIM topology afterwards (`propagate_base_voltages`), which is ruled out
because it changes CIM after the bind (I1).

Decided (DSS-1, amended 2026-11-07): the format-agnostic `cimtopology.core` (CIM-Graph-Topology-Processor)
replaces the old `cimhub_core.topology`. Each spoke builds a `cimtopology.core.Network` from its native objects; the
DSS one is `importer/cimtbl/bus_graph.py`, rewritten on `Network` in F2:
- **Sources:** every `Vsource` (`New Circuit` too). Unset slots take the DSS defaults: `bus1=sourcebus`, `basekv=115`.
- **Branches:** every `Line` (open switches too) and every series `Reactor` or `Capacitor` (`bus2` on another bus).
- **Transformers (coils):** every `Transformer` and `AutoTrans` winding, with `phases`/`windings`/`kVs`/`conns`
  from the instance, else its `XfmrCode`. A coil is polyphase (kV phase-to-phase), phase-to-neutral,
  phase-to-phase, or a split-phase half.

`walk` gives every bus a `BusSystem(kv, system)`, where the system is 3-phase, single-phase or split-phase.
`base_voltage` (the mRID) and `three_phase` are derived from these. Islands are buses joined by ties. An island's
system is decided once, from every coil that lands on it:
1. A polyphase coil, or the single-phase coils of two or more transformers on different conductors (a bank, a
   regulator bank, an open-delta pair) make it 3-phase.
2. Otherwise a split-phase half makes it split-phase.
3. Otherwise a single-phase transformer with equal coil kV (a regulator) keeps the system it came from.
4. Otherwise (a service or a step-down) it is single-phase.

An island's voltage:
- **A source island** takes the source `basekv`.
- **Any other island** takes the most common rounded value its coils give, each coil in its own kV, never by ratio.
  This is why J1's 13.09 kV substation secondary under 1,278 service primaries of 7.2 kV is 12.47.
- **Tolerance:** every coil must be within 10 % of the island (a nameplate off the system voltage is normal:
  K1's 66 kV winding on a 69 kV source). Every coil must also be able to sit on the island's system. Otherwise the
  walk raises.

The walk's result is written, not only passed to the mappers: `bus.cimtbl` gives every bus a `ConnectivityNode` with its
`BaseVoltage` (cim18v17's new `ConnectivityNode.BaseVoltage`, used when there is no VoltageLevel; mapping spec
`#buses`).

There is no snapping to `voltagebases`. `nominal_kv` rounds a computed value (2 decimals in kV at 1 kV and above,
whole volts below), so the rounding noise of 12.4708 against 12.47 gives one BaseVoltage, while a real mismatch
(0.24 against 0.208) stays two.

The engine is the test oracle (`opendssdirect`, tests only; `tests/test_topology_walk.py`), compared bus by bus.
`CalcVoltageBases` snaps each bus to the nearest of the deck's `voltagebases`. So the engine must agree wherever the
walk's voltage is one of those bases; where it is not, the engine squashes the bus, and the test lists it. The atom
deck shows this: its 240 V 2-wire service is listed as squashed against bases of 0.208 and 0.48.

Every bus of 11 decks agrees with the engine: IEEE13_CDPSM, IEEE13_assets, IEEE13_original, IEEE13_OCHRE,
IEEE123, IEEE37, 4bus-OYOD, ACEP_PSIL, and with `--roundtrip` J1, IEEE8500 and ieee9500_2025. None of them squashes
a bus. J1 lists 0.416 in `voltagebases`, so its 240 V services happen to agree. K1 and M1 walk, but the engine
cannot compile them on Linux (their `Redirect` file-name case is wrong). The old ieee9500 copy does not compile on
the current engine (`PVSystem` model 7).

### 3.2 Bus, node and phases

`bus1=650.1.2.3` gives `node` = `650` (lowercased) and `phases` from the conductor numbers (1→A, 2→B, 3→C; `.0` is
ground, `.4` a neutral). Center-tap secondaries (`s1`, `s2`, `s12`, DSS-5) come from the walk: a bus whose
system is `SPLIT_PHASE` reads nodes 1 and 2 as s1 and s2. ExportCIMXML uses `kVBase < 0.25` instead, which would
misread 208/120 V three-phase secondaries.

### 3.3 DSS defaults (DSS-6)

A slot the deck does not set has the DSS default, e.g. `Transformer.windings` = 2 and `phases` = 3. The reader
leaves these as `None`. A verbatim artifact cannot leave them out, because the CIM would then be incomplete. Decided:
- The default lives in the LinkML schema as a `dss_default` annotation, never as `ifabsent`. `ifabsent` makes the
  reader fill every slot, and the writer then writes them all back (why they were removed in March 2026).
- A mapper fills a slot from `dss_default` only when the slot is unset.
- It lists the filled slots in the row comment (`# defaulted: windings=2, XHL=7`), like D5's untranscribed record.

This needs one core helper next to `untranscribed_values`, reading the annotation through the schema view. Each
slice first fills the missing `dss_default` annotations for its classes: from the description text, then from the
EPRI property pages (`opendss.epri.com/PropertiesNN.html`).

### 3.4 Reader fixes (S0, done 2026-11-07)

The reader is the spoke's own code. It now applies the commands in deck order, as DSS does, and raises
`DssParseError` with file and line instead of logging and skipping:

| was | now |
|---|---|
| a command that fails to parse is logged and skipped | raises |
| a duplicate `New` is stored as `<name>_<n>` | applied as an edit, as DSS does; one warning per object |
| an `Edit` on an unknown object, or an unknown `like=`, is a warning | raises; `like=` copies from an object defined earlier |
| `Set` commands are dropped | `voltagebases`, `defaultbasefreq`, `earthmodel` kept on one `Options` object (new schema class); solution settings ignored |
| an unknown DSS class or property is skipped | raises. Abbreviations resolve to the first property, in DSS order, that starts with the text (`Vmin` = `Vminpu`, `GMR` = `GMRac`, `ppm` = `ppm_antifloat`), as DSS does |
| a value that fails to convert, or an unknown enum value, is dropped with a warning | raises |
| a sanitizer clamped out-of-range values to the `dss_default` (`nphases=4` → 3, `pf=1.5` → 0.88) | removed: values are kept as written |
| a missing `Redirect` target or `BusCoords` file is a warning | raises |
| `BatchEdit Class..<regex>` was misread as an edit | applied to every matching object; matching none raises |
| `vreg=(122)`, `npts='1,'`, `mult=(file=shape.csv)` failed | RPN of one number; a trailing comma is a delimiter; `file=` arrays read from the deck directory |
| ~~blanks around `=`, numeric bus names as floats, quoted arrays~~ | done in CIMHub_2_0 |
| a record kept only each slot's last value, so an order-dependent engine value was lost | `read_all()` returns a `DssModel`: a `GraphModel` with each record's assignment history (`(slot, value)` in deck order); the S4b mappers replay it (S4b-8, 2026-11-08) |
| `New Circuit` dropped the circuit name and wrote `bus1=sourcebus` into the parameters (S1) | the name is kept on `Options.circuit`; the default comes from the schema; a second `New Circuit` raises |
| `Clear` was skipped (S1) | discards everything defined before it, as DSS does |
| an unknown command verb was skipped silently (S2) | raises. `DSS_COMMANDS` is the engine's 125 commands (a test checks them); a word is the first command it abbreviates (`CalcV`), as in the engine. `SKIPPED_COMMANDS` (solve, report, plot, export, `setkvbase`, ...) are skipped; any other command not read (`Disable`, `Remove`, `Select`, `var`, ...) raises. The balanced IEEE9500 master's `Reditect Switches.dss` typo, which loaded no switches (2 buses walked), is fixed in the local deck (5297 buses) |
| `/* ... */` block comments were not handled (S2): text lines were skipped as unknown verbs, but a `New` inside one was read (IEEE13_original's commented-out `mtx606`) | a line starting `/*` opens a block, the line holding `*/` closes it, and both are skipped whole, as the engine does (engine-checked) |
| `More` / `M` continuations were skipped; an orphan `~` became a standalone line (S2) | `More`, `M` and `~` all continue the last `New`/`Edit`; a continuation with none before it raises |
| a LineGeometry's cond= blocks kept only the last `units` (S2) | the blocks must agree (a block without `units` takes the last given, else `ft`, as DSS does); otherwise raises |
| `Open` / `Close` were skipped (S2) | `Options.open_terminals` keeps `Class.name terminal` (terminal defaults to 1; engine-checked); `Close` removes it; the object must exist; opening one conductor raises. The S3a line mapper reads them as open switches |
| a value with no property name was dropped silently (S3): `Normamps=156 {156 1.25 *}` lost emergamps on every J1, K1, M1, IEEE8500 and IEEE9500 triplex code | it goes to the property after the last one named, in the schema's `order`, as DSS's parser does; `{...}` is RPN (the existing `_eval_rpn`); a positional value on Transformer, XfmrCode, AutoTrans or LineGeometry raises (engine-checked) |
| a bare per-winding `kV kVA conn tap %R` was left for the mapper, which raised; a 2-winding `wdg=1 kva=500 wdg=2 kva=300` was kept as [500, 300] (S3) | applied in order to the active winding: the last `wdg=`, else the last an array set, else 1. On a 2-winding transformer `kVA` sets both, as the engine does ([300, 300]). An unset winding of a partly given array takes the per-winding `dss_default` with a warning; an unset `bus` raises (engine-checked). This lifts the ieee9500 `kVA=750` and J1 `%R=0.1` stops |
| a coordinate row was split only on commas, and an unreadable one skipped (S5): the whitespace-separated IEEE123 files lost every row | split on a comma or whitespace, as the engine's parser does; a row whose coordinates are not two numbers raises with file and line |

Schema fixes found by the strict reader (all 31 local decks now read): `Relay.type`, `RegControl.bus` → string;
`LineCode.faultrate` → float; nine `{Yes/True | No/False}` slots → boolean; `LoadShape.action` → string; 55
array slots (`LoadShape.mult`/`qmult`/`hour`, `EnergyMeter.peakcurrent`/`option`, `Vsource.Z1`, ...) marked
`multivalued`. S1 added `Vsource` `dss_default`s (`bus1`, `angle`, `phases`, `MVAsc3`, `MVAsc1`, `x1r1`, `x0r0`), typed
`x1r1`/`x0r0`/`frequency` as floats, made `puZ1`/`puZ0`/`puZ2` arrays, and added `Options.circuit`; S2 added `Options.open_terminals`.
S3 added `dss_default`s for RegControl (19 slots), Fuse, Recloser, SwtControl (`Normal`, `State`), Line and LineCode
(`r1 x1 r0 x0 C1 C0`), and Transformer/XfmrCode (`kV kVA conn tap %R`); it typed RegControl `band`, `R`, `X`,
`revR`, `revX`, `tapdelay`, `revDelay` and Fuse `RatedCurrent` as floats. `opendss_schema.py` is
regenerated with `gen-python` 1.10.

## 4. Slices

Each slice delivers its mapper(s), atoms with goldens (`tests/atoms/<class>/`), the classification table in
`CIMTBL_MAPPING.md` (generated with `fields_table(..., fields=FIELDS)`), and an extended deck sweep (§5).
`scaffold_mapper` writes the stubs. The spec section of a slice is approved before its code (DSS-12).

| slice | content | exit |
|---|---|---|
| S0 | reader fixes (§3.4); `importer/topology.py` (`dss_network` on `cimtopology.core`), bus/phase parsing, `dss_defaults` + core `fill_defaults`; orchestrator `dss_to_cimtbl.py` with `MAPPING_ORDER`, master document, `DssImporter(CimtblImporter)` | **done 2026-11-07:** the IEEE13_CDPSM master + `linecode.cimtbl` bind; bus kV equal to the engine's on every engine deck (5 vendored, 5 external), K1 and M1 walk |
| S1 | master `common` rows (Substation, Feeder, BaseFrequency, BaseVoltage from the walk); `bus.cimtbl` (ConnectivityNode.BaseVoltage); Vsource (`source`, Thevenin impedance from the three DSS groups); reader keeps the circuit name | **done 2026-11-07:** IEEE13_CDPSM master, bus, vsource and linecode bind; source r/x/r0/x0 equal the engine's on all 10 engine decks; equipment BaseVoltage equals its nodes'; master + bus + vsource import and bind on all 31 sweep decks (16 stop in LineCode on the S2 open points: units, baseFreq, 1-phase sequence codes) |
| S2 | catalogs: WireData, CNData, TSData, LineSpacing, LineGeometry; LineCode open points (DSS-3, DSS-3b, DSS-4); reader command rules (§3.4) | **done 2026-11-07:** wire values and geometries equal the engine's (IEEE13_Assets, IEEE4; IEEE9500 by hand); 1-/2-phase code matrices equal the engine's line matrices; 30 of 31 sweep decks import and bind with every S2 part (the 31st, the `ieee9500_2025` balanced copy, opens a switch it never defines, and the engine fails on it too). XfmrCode moved to S3 (approved): it waits for U2 and D10 |
| S3a | network: Line (impedance, geometry, switch, synthesized templates, ratings), Transformer in the orchestrator, VoltageRegulator / LTC, RegControl; reader fixes (§3.4) | **done 2026-11-08:** IEEE13_CDPSM, IEEE123 and IEEE8500 bind with every line, switch, transformer and regulator (XfmrCode instances counted on the master); 25 of 31 sweep decks bind (stops: DSS-10 in J1, K1, M1, IEEE13_OCHRE; the two balanced IEEE9500 copies the engine rejects too); lines (ratings, z, b, switch states) and regulators (settings, tap range, nameplate, mesh) equal the engine's on the 8 engine decks. Found: the engine's rating copies, a matrix code's default C, the inline default C per kft |
| S3b | XfmrCode templates and their instances | **done 2026-11-08:** TankEnd templates (3-phase, IEEE4 YYD) and center-tap lug templates (IEEE8500, IEEE9500, IEEE123_PV, IEEE13_CDPSM); 25 of 31 sweep decks bind (the S3a stops only); every template equals the engine's transformer of each instance. AutoTrans waits for a deck (S3b-1). Multi-can tank templating and bank lug sequencing wait for CYME's form |
| S4a | Load, Capacitor + CapControl (shapes `load`, `shunt`; core `zip_fractions.cimtbl`) | **done 2026-11-08:** 25 of 31 sweep decks bind (S3's stops only); every load's p, q and model and every capacitor and CapControl setting equal the engine's on the atoms and the 8 engine decks. Own-terminal controls by `Update` (U3 closed) |
| S4b | PVSystem, Storage, Generator, Reactor; the two new shapes (`synchronous_machine`, `series_compensator`, shared with RAW C2) added to the catalog first; approved and done 2026-11-08 (CIMTBL_MAPPING.md S4b); the reader keeps each record's assignment history (`DssModel`, S4b-8) | done: 22 of 31 decks bind (S3 six + two `ieee9500` copies with an engine-invalid PV `Mode=7` + IEEE123_test_harness `Battery5`); full IEEE13_CDPSM artifact directory committed as the reference golden (D6) |
| S5 | Buscoords (Location shape added to the catalog first); deck sweep to green or listed stops; G7 numbers on ieee9500 | **done 2026-11-08:** shape `location`; every equipment Location equals the engine's bus coordinates on the atoms and the engine decks (IEEE9500 by LatLongCoords); `tests/test_cimtbl_sweep.py`: 18 of 24 bind, 6 stop as listed (DSS-10 ×4, PNNL IEEE9500 bal's missing line code, `Battery5`); G7: IEEE9500 binds 65,282 rows in 8.2 s |
| S6 | exporter `cim_to_dss` ported to cim18v17 on the core getters (master plan §4 Phase 5 step 3, exporter assessment E0-E6), tested from the `.cimtbl` atoms | tier 2 per class; roundtrip and power flow parity (§5) |
| S7 | delete the old importer, the Python atoms and every cimhub_2026 import in the spoke; update conformance tests and `README` | the spoke imports cim18v17 only |

S0-S5 are the importer and S6 the exporter. The importer and the exporter must flip together (master plan §4 Phase
5), so `dss_to_cim` keeps calling the old importer until S6 passes. Then S7 switches both and deletes the old code
in one change.

## 5. Tests

- **Tier 1/1b per class:** a native atom gives the golden, and the golden plus prereqs binds (the `test_cimtbl_linecode.py`
  pattern).
- **Completeness:** `check_fields(FIELDS, NATIVE_CLASS)` per mapper.
- **Decks:** small public decks are vendored in `cimhub_opendss/tests/decks/` (origins in its README); the large ones
  (J1, IEEE8500, IEEE9500, ...) run when `CIMHUB_DSS_DECKS` points at a directory with the same layout.
- **Deck sweep** (`tests/test_cimtbl_sweep.py`, marked `roundtrip`, built in S5): each of the 24 decks either maps and binds, or stops
  with an error listed in the sweep table. A new stop fails the test, so the table stays true.
- **Bus voltages vs the engine** (§3.1) on every sweep deck.
- **Power flow parity:** run the original deck, then deck → artifacts → CIM → `cim_to_dss` → engine. Compare bus
  voltages within 0.1 %, using `engine_compare.assert_same_power_flow` (S6f; the old `powerflow_harness.py` was not ported). This is the end-to-end check the per-class
  goldens cannot give, and it replaces the old roundtrip tests in S7.
- **Baseline today:** 11 failures in the old suite (5 `line_roundtrip`, 6 `linegeometry`). They are not fixed; S7 deletes
  them with the code they test.

## 6. Decisions

Each item has a recommendation. They are needed by the slice in the last column.

| # | question | recommendation | slice |
|---|---|---|---|
| DSS-1 | Where bus voltages come from | **Decided 2026-11-06, amended 2026-11-07:** a format-agnostic topology processor (`cimtopology.core`, CIM-Graph-Topology-Processor) walks a `Network` from the source bus, before any artifact. It does **not** snap to `voltagebases`, because CalcVoltageBases squashes mismatched bases (a 240 V service onto 208 V). Per bus it returns a `BusSystem`: the BaseVoltage, plus whether the bus's island is 3-phase. `nominalVoltage` is rounded to 2 decimals in kV at 1 kV and above and to whole volts below, so 12.4708 and 12.47 share one BaseVoltage. In CIMHub_2_0 the walk and the DSS bus graph agree with the engine on every bus of 11 decks; F2 rewrites `bus_graph.py` on `Network` and keeps the engine as the test oracle | S0 |
| DSS-2 | Transformers | **Decided 2026-11-06 (the user's model):** every DSS Transformer that is not a regulator (DSS-13) is its own PowerTransformer (`bank` untranscribed), with one PowerTransformerEnd per bus and the phases on its terminal. 3-phase: balanced ends. 1-phase: a TransformerPhaseEnd per conductor (global `sequenceNumber`) and windings between phase ends. No TankEnd. XfmrCode becomes a template (amended 2026-11-08): a TankEnd per winding for 3-phase and non-center-tap codes, linked to the instance by `endNumber`; a center-tap code is a 3-winding tank with lugs H1 H2 X1 X3 X2 and windings H1→H2, X1→X2, X2→X3 (additive polarity, IEEE C57.12.00), its instance's phase ends landing on the lugs by `sequenceNumber`. Ratings are nameplate values (`ratedU` LL, `baseU` the coil). **Inline done:** `importer/cimtbl/transformer.py`, 24 tests, 1,365 of 1,378 inline transformers in 11 decks map | S3 (started early) |
| DSS-3 | A LineCode without `units` | **Decided 2026-11-07.** (a) Code used by lines that have units (J1: 1,382 lines, all `kft`): the code takes the line's unit, as DSS does. Lines that disagree give one template per unit, `lc_<name>_<unit>`. (b) Code and line both unitless (M1: 1,960 lines; IEEE123_deconfliction: 118), or a unitless code no line uses (IEEE13_original: 29): a deck-level magnitude gate on the median positive r1 (or rmatrix diagonal) of the deck's unitless codes. 0.006 to 10 per unit → `km`; 1e-5 to 0.006 → `m`; anything else raises. `length_unit=` overrides the gate. Real conductors run about 0.01 to 3.5 Ω/km, so the per-m/ft and per-km/kft/mile bands don't overlap. The inferred unit goes in the header and the file says `# units inferred: km (median r1 0.134 per unit; no units on code or line)`. Because code and line share the unit, z·length is exact for any label; a wrong label (kft read as km) only scales the physical length. Census 2026-11-07: M1 median r1 0.134 (0.044 to 0.76), IEEE123 0.245 (0.055 to 0.53), so both read `km` (they are per kft by origin) | **done in S2** |
| DSS-3b | A LineCode with a nonzero C and no `baseFreq` | **Decided 2026-11-07:** the model's base frequency (`Set defaultbasefreq`, kept on the model by the §3.4 reader fix), else 60 Hz (the DSS default). Recorded as `# defaulted` (§3.3) | **done in S2** |
| DSS-4 | 1- and 2-phase sequence codes (J1, 17 codes) | **Decided 2026-11-07:** match the engine with a derived `PerLengthPhaseImpedance` + `PhaseImpedanceData` matrix (`row`, `column`, `r`, `x`, `b`). 1-phase is z = Z1 and b from C1; 2-phase is Zs = (2Z1+Z0)/3 and Zm = (Z0−Z1)/3, with the same for C. This is closed-form, not Carson; the function lives in `cimhub_core/derived/` (U4 candidate). Each is checked against the engine's line matrices (`oh_b13552`, `oh_b41869`) | **done in S2** |
| DSS-5 | Center-tap secondary phases | **Done locally in the transformer mapper:** windings 2 and 3 on one bus, both on node 0, with nodes 1 and 2, form `s1s2N`. Downstream, the walk marks every bus of the secondary's island `System.SPLIT_PHASE`, so line and load mappers read nodes 1 and 2 there as s1 and s2 (same rule, `transformer.is_split_phase`) | S0 |
| DSS-6 | DSS defaults | **Decided 2026-11-07:** one source, the LinkML schema. The `ifabsent` defaults were removed in March 2026 (commit `792e8273`) because the reader filled every slot, so the roundtrip wrote them all back. What's left is a non-populating `dss_default` annotation on 93 of the 737 slots of the classes this wave maps; 111 more state their default only in the description text, and the rest have none (RegControl, Fuse, Recloser, XfmrCode, WireData: zero). Plan: (1) fill `dss_default` (annotation, never `ifabsent`) from the description text, then from the EPRI property pages (`opendss.epri.com/PropertiesNN.html`, e.g. RegControl `vreg` 120, `band` 3, `ptratio` 60), and extend `gen-dss-schema` to emit it; (2) a mapper fills an unset slot from `dss_default` and lists it in the row comment (`# defaulted: windings=2, XHL=7`). No hand-written `DEFAULTS` dicts. Each slice fills the annotations for its own classes | S0 + per slice |
| DSS-7 | Load p, q and voltage response | **Decided 2026-11-07:** `EnergyConsumer` p (kW), q (kVAr) plus `LoadResponse`. A fixed `zip_fractions.cimtbl` is always written, with `zip_constant_pq` (1,0,0 / 1,0,0), `zip_constant_z` (0,0,1 / 0,0,1) and `zip_constant_i` (0,1,0 / 0,1,0) (`exponentModel` false). `model` 1/2/5 → pq/z/i. `kvar` is copied; `pf` gives a derived q = p·tan(acos pf) with the sign of pf; `kVA`/`xfkVA`/`allocationfactor` untranscribed until a deck needs them. Model 4 (exponential; about 2,860 loads in M1, J1, IEEE37, IEEE8500) → one `exp_<cvrwatts>_<cvrvars>` row per distinct pair in `load.cimtbl`: `exponentModel` true, `pVoltageExponent`/`qVoltageExponent` from `CVRwatts`/`CVRvars` (DSS defaults 1 and 2, §3.3). The decks hold only a few pairs: 0.8/3, 0.7/3 (M1's `CVRwatt=`, the prefix rule in §3.4), 1/2. Models 3, 6, 7, 8 are in no deck and raise. Amended 2026-11-08 (S4-2, S4-3): `kV` is checked against the bus (1 %), not written; `kVA` without `kW` is derived; `kW` with `kVA` or `xfkVA` raises (the engine takes the last one given) Core: `zip_fractions.cimtbl` is shared by every distribution spoke, so it belongs in `cimhub_core` (the core `common` shape lacks `zip_constant_i` today) | S4 |
| DSS-8 | Lines with inline r1/x1 (600) or an inline matrix (1) | **Decided 2026-11-07:** a synthesized `PerLengthSequenceImpedance`/`PerLengthPhaseImpedance` `ln_<line>_lc` (R4, amended 2026-11-08: `lc_<line>` could collide with a LineCode name) in `line.cimtbl` (values stay verbatim per length), not `ACLineSegment.r/x` totals (those would be derived by length). Switch lines keep their impedance untranscribed | **done in S3a** |
| DSS-9 | Switch class for `Switch=y` | **Decided 2026-11-07:** the line's class comes from the control object that switches it (`SwitchedObj=Line.<x>`, else `MonitoredObj`): a Fuse → `Fuse`, a Recloser → `Recloser`, otherwise (a `SwtControl` or nothing) → `LoadBreakSwitch`. The line mapper takes an index of these controls as structural input. Fuse `ratedCurrent` → `Switch.ratedCurrent`. Recloser `phaseTrip`/`groundTrip`/`shots` and Fuse curves are untranscribed: see DSS-11. A Fuse/Recloser on a line with `switch=False` raises (none in the decks). If S3 runs long, the class split falls back to `LoadBreakSwitch` plus a TODO gap row | **done in S3a** |
| DSS-10 | Line phases ≠ code `nphases` (census: J1 1,381, K1 743, M1 1,949) | **Deferred 2026-11-07.** This mismatch may be why J1 segfaults opendssdirect.py without explanation. Until it is understood, a mismatched line raises with the deck, line and code named, so the deck sweep lists it. Pin the engine's behaviour per case before writing a rule | after S3 |
| DSS-11 | Classes with no mapping | **Decided 2026-11-07.** Mapped: Fuse and Recloser (DSS-9), and AutoTrans → `AutoTransformer` + `AutoTransformerEnd` (CIM18; new `auto_transformer` shape), amended 2026-11-08 (S3b-1): not mapped until a deck has one; the master's not-mapped count is the signal. Not mapped: Monitor, EnergyMeter, LoadShape, Relay (LoadShape **mapped since S8**, 2026-11-21, for the shapes a Load names as `yearly`). The master's comment lists their counts (`# not mapped: Monitor 52, LoadShape 16`), so nothing disappears silently. TODO (by hand, before any mapper): how `FuseCharacteristicCurve` and `RecloseSequence` express DSS fuse curves and recloser `shots`/trip settings. Both exist only in the cim18v17 `protection` sub-profile, not the main profile | S0 / S3 |
| DSS-12 | Spec approval | **Decided 2026-11-07:** build and approve one slice at a time. One section of `CIMTBL_MAPPING.md` per slice, approved before that slice's code. Each section's classification table is generated from the mapper's `FIELDS`, so it is written together with the mapper stub | now |
| DSS-13 | Voltage regulators and LTCs | **Decided 2026-11-07 (the user's model).** A DSS Transformer named by a RegControl is either a regulator or an LTC. Equal winding kV (a regulator): a `VoltageRegulator` (an `AutoTransformer` subclass in CIM18) whose two `~ wdg=` windings become two `AutoTransformerEnd`s. A 1-phase unit puts its phase on each end (`phase` is a `PhaseCode`). A 3-phase gang-operated unit (one DSS Transformer, `phases=3`; tap A = B = C) puts `ABCN` on both ends. Either way there is one `RatioTapChanger`, on the tap-side end. A step-down (J1 `SubXfmr` 68.8/13.09 kV, M1 `M1_XFMR` 67/12.47 kV) is an LTC: a `PowerTransformer` (DSS-2) with the `RatioTapChanger` on the controlled `PowerTransformerEnd` (`winding=`). The RegControl gives the `RatioTapChanger` + `TapChangerControl` in both cases. Impedance (the user's model, 2026-11-07): one `TransformerMeshImpedance` between the two `AutoTransformerEnd`s, r = %R1 + %R2 and x = XHL in percent on end 1's baseU/ratedS; the ends carry only the nameplate, which has no %Z (OpenDSS needs XHL because it has no real autotransformer). `normalStep` is not written (R2) | **done in S3a** |
| DSS-14 | LineCode templates and a line's own impedance | **Decided 2026-11-21 (the user's rule):** a LineCode, shared by name, is a `PerLengthImpedance` with `isTemplate=true` behind a `WireConfiguration` `<template>_wc` (its `PerLengthImpedance`, no `WireSpacing`), and its lines reference the WireConfiguration. A line's inline values (DSS-8) stay `ACLineSegment.PerLengthImpedance`, `isTemplate=false`. The WireConfiguration is the equivalence route: a spacing makes it geometry, a PerLengthImpedance alone a template LineCode; exporters read it through `get_line_geometry`/`get_line_code`. The DSS exporter writes a template (`isTemplate` true or unset) as a LineCode and a line's own impedance inline on the Line. The GLM and GDM importers write their matrix/sequence catalogs the same way (skill `wire-configuration`) | **done 2026-11-21** |

Master-plan decisions this wave needs: **D6** (goldens vendored in `cimhub_opendss/tests/`, recommended) by S4;
**D7** (applied in S0 as recommended, pending approval: `Model` = the name the caller passes, `Authority` = the CIMHub repo URL unless the caller passes another); **D9** (catalog ratings: `normamps`/`emergamps`
on a LineCode, untranscribed; a wire's `normamps` is `WireInfo.ratedCurrent`) applied in S2; amended 2026-11-08: a wire's ratings also go on `AssetInfo.OperationalLimitSet` (GridAPPS-D extension), normal and emergency `CurrentLimit`s; a line's on its own `OperationalLimitSet` (S3a); **D10** (3-phase tank configuration convention) by S3b's XfmrCode: decided by the user 2026-11-08 (a TankEnd per winding, no phases on the template; the instance end n is template end n; center-tap codes use lugs, see DSS-2).

## 7. Dependencies

| owed by | item | blocks |
|---|---|---|
| ~~cimtables~~ core | ~~U2~~ closed 2026-11-08: the template shapes bind (core's 3-phase template gave its tank ends a `phases` column, which CIM-Tables rejects by design) | — |
| core | `zip_fractions.cimtbl` + `zip_constant_i` in the `common` shape (DSS-7); `getters/` | S4; S6 |
| user | `FuseCharacteristicCurve` / `RecloseSequence` mapping by hand (DSS-11 TODO) | protection settings only; Fuse/Recloser rows map without them |
| user | D14 open-delta template | DSS open-delta banks; none were seen in the census, so they fail fast |

Closed 2026-11-07 (see `UPSTREAM_REQUESTS.md`): R10 (`#` in an mRID), R12 (type-hint cache), R7 (`get_qty`).

## 8. S6: the exporter (plan 2026-11-09, approved by the user 2026-11-09 with E1, E4 and E8 amended)

`DssExporter(FormatExporter).to_model(network) -> DssModel`, written fresh in `cimhub_opendss/exporter/`, one module
per DSS class. It reads every value through the core getters (`export-getters` skill), and the `DssModel` it
returns has the same shape `DssReader.read_all()` returns: schema dataclasses, one `Options`, `Buscoords` rows. So
`DssWriter().write(model, path)` gives a deck the reader reads back. The old exporter (CIMHub_2_0, 4,600 lines,
cimhub_2026) is only the oracle. `dss_to_cim` already runs on the new importer here, so the "flip together" of §4
reduces to S7's clean-up.

### 8.1 Sub-slices

Each one has its own spec section in `cimhub_opendss/docs/EXPORT_MAPPING.md`, approved before its code
(DSS-12). Each one's exit is the per-atom check of §8.3 on its atoms.

| # | content | getters needed (new in **bold**) |
|---|---|---|
| S6a (**done 2026-11-09**) | framework: `DssExporter`, `EXPORT_ORDER`, naming (E1), bus references `bus.1.2.3` from terminals (E7), `Options` (circuit, `defaultbasefreq`, `voltagebases`); writer fixes (§8.2); Vsource; the per-atom harness (§8.3) | `get_source`, `get_terminal_nodes`, `get_terminal_phases`, `get_base_voltage` |
| S6b (**done 2026-11-09**) | lines: WireData/CNData/TSData, LineSpacing, LineGeometry, LineCode, Line, switches (Line `switch=y` + Fuse/Recloser/SwtControl, `Open`), ratings | **`get_wire_info`**, **b → C** (`derived/`), `get_spacing_xy`, `get_line_conductor_xy`, `get_line_*_impedance*`, `get_switch_state`, `get_current_limits` |
| S6c (**done 2026-11-09**) | transformers: inline Transformer (every form), XfmrCode from a `TransformerTankConfiguration`, center taps, VoltageRegulator/LTC + RegControl | `get_transformer_units`, `get_transformer_model`, `get_tap_steps`, `get_tap_changer_control` |
| S6d (**done 2026-11-09**) | Load, Capacitor, CapControl; whole-deck elements and settings on IEEE13_original, IEEE123, IEEE37, IEEE13_Assets (IEEE13_CDPSM waits for S6e: PVSystem, Storage) | `get_phase_loads`, `get_load_response`, `get_shunt_reactive_power`, `get_regulating_control`, `get_equipment_control` |
| S6e (**done 2026-11-09**) | PVSystem, Storage, Generator, Reactor; a PowerElectronicsConnection with several units chopped by maxP share (the GDM rule, P1); whole-deck elements and settings on IEEE13_CDPSM, IEEE123_PV, IEEE8500, IEEE9500, ACEP_PSIL | `get_der_output`, G6d rating getters, **`get_inverter_units`**, **`get_series_compensator`** |
| S6f (**done 2026-11-09**) | Buscoords; whole-deck power flow parity (16 decks within 0.1 %, controls off at the original's control state and untranscribed settings, F2-F3); the idempotence sweep (18 decks) | **`get_location_coordinates`** |
| S6g (**done 2026-11-09**) | earth model (`EarthResistivity` on every WireConfiguration ↔ `Set earthmodel` + geometry-line `rho`) and reclosing (`RecloseSequence` ↔ Recloser `Shots`/`RecloseIntervals`), import and export; trip settings still have no home (G5) | **`get_earth_resistivity`**, **`get_reclose_delays`** |

### 8.2 Writer fixes (S6a)

The writer is seed code that only ever wrote `new Class.name ...` lines in `iter_all()` order. To give a deck the
engine and the reader accept, it needs:
- **Class order** as a class-level list (`WRITE_ORDER`, reader-writer skill). Each class comes after everything it
  references: catalogs, Line, then Fuse/Recloser/SwtControl; Transformer, then RegControl; **Capacitor, then
  CapControl**. That is the reverse of the importer's order, which suits the cimtbl and not the engine.
- **The circuit:** `Clear`, then `Set defaultbasefreq=` (before the circuit, as the engine needs), then
  `New Circuit.<Options.circuit>` carrying the slots of Vsource `source`, which is not also written as a Vsource.
- **After the objects:** `Set voltagebases=[...]`, `CalcVoltageBases`, one `Open Class.name terminal` per
  `Options.open_terminals`, and `Buscoords <stem>_buscoords.csv` (`LatLongCoords` for geographic rows), with the
  CSV written next to the deck.
- **One file** (`destination` is the `.dss` path) plus the coordinates CSV. Splitting into per-class files is
  layout only (the `to_model` docstring of the old exporter), so it is not done.

### 8.3 Tests

- **Per atom (tier 2, every sub-slice):** atom deck → `DssImporter.to_cim` → `to_model` → writer → engine,
  compared with the original atom in the engine. Per element: the class, the buses, `YPrim` (rel 1e-6), and the
  properties the importer's engine checks already read (load p/q/model, regulator and capacitor settings, ...).
  Then the bus voltages after `Solve` (rel 1e-6 on an atom). An exported golden `.dss` per atom is committed beside
  it (D6) so a diff shows what changed.
- **Idempotence (S6f):** export(import(export(import(deck)))) is the same text as export(import(deck)) on every
  sweep deck that binds. A second pass must be a fixed point. Without the engine it catches lost or drifting values
  cheaply.
- **Power flow parity (S6f, §5):** bus voltages within 0.1 % of the original deck on the engine decks
  (`powerflow_harness.py`).

### 8.4 Decisions (approved 2026-11-09)

| # | question | recommendation |
|---|---|---|
| E1 | Names (amended by the user) | **One naming switch shared by every exporter:** written from the CIM `name`, the `mRID` or `uri()` (the fixed-length UUID; the third option added by the user 2026-11-09). It is chosen by the exporter option `name_source=` (`"name"`, `"mrid"` or `"uri"`), else the `CIMHUB_NAME_SOURCE` environment variable, else `"mrid"`. One core function, `cimhub_core.names.export_name(obj, source)`, returns the text, and an unset one raises. Each spoke sanitizes it with its own rule: DSS `dss_safe_name` (whitespace, quotes, brackets, `=` ...). Every name a spoke writes (equipment, catalogs, buses) goes through it. Two objects of one DSS class that land on the same sanitized name (lowercased, as DSS compares names) raise, naming both. `mrid` is the default because it is unique by construction: the importers compile it from the native name (`ln_632633` for Line `632633`), so the deck is unique but not byte identical. GLM users asked for it too. The circuit name is the one Feeder's, by the same switch; several Feeders raise |
| E2 | The circuit's source | With one EnergySource, it is the circuit. With several, the option `circuit_source=` (default `"source"`, the DSS importer's name) names the one written as `New Circuit`; the others are Vsources |
| E3 | Catalogs or inline | Keep CIM's structure. Every PerLengthImpedance is a LineCode. Every WireInfo is a WireData/CNData/TSData. A WireConfiguration is a LineGeometry, one per (WireConfiguration, `ySpacingOffset`) (G5: DSS `h=` is per line), named `<config>` at offset 0 and `<config>_<offset m>` otherwise; a bare XYSpacing is a LineSpacing. A TransformerTankConfiguration is an XfmrCode. Everything else is inline. The importer's synthesized templates (`ln_<line>_lc`) come back as LineCodes, a listed difference that is equal in the engine |
| E4 | Values CIM leaves unset (amended by the user) | This is about a value that is `None` in CIM but that DSS needs. It is not about the LinkML `dss_default`s, which the exporter never reads. Every value the getters give is written. A getter's `None` for a slot DSS needs follows the spoke's written rule, with a comment (skill rule 8: `C1=0`/`C0=0` when b is unset, so the engine's 3.4/1.6 nF never applies). A slot CIM cannot hold (Generator `Xd`, U13; untranscribed values) is left unset and listed in `EXPORT_MAPPING.md` as engine-defaulted |
| E5 | Capacitance | C = b / (2π f), with f = `network.base_frequency`: one named function in `derived/`, converted through `cim.Capacitance(...).to('nF')`, never a factor. The deck sets `defaultbasefreq` and every LineCode `baseFreq` to that frequency. This closes the G3 open point |
| E6 | Switch state | Both of CIM's states go back: `normalOpen` → the control's `Normal`, `open` → `State` and an `Open` command (the importer's `_STATE` rule inverted). A switch with no Fuse/Recloser class gets a SwtControl only when it is open in either state |
| E7 | Bus references | A terminal's phases in conductor order: A/B/C → `.1.2.3`, s1/s2 → `.1.2` (DSS-5). A wye winding (the transformer mapper's `_neutral`, inverted): grounded solidly → its neutral on `.0`; grounded through `rground`/`xground` → `Rneut`/`Xneut` with the neutral left on the engine's own node; ungrounded → `.4`. A balanced 3-phase terminal is written `.1.2.3` and never left bare |
| E8 | Per-phase values (amended by the user) | Equal per-phase p/q (or none, `split` True) give one DSS object. When the per-phase values differ (rel 1e-6), each phase gets its own 1-phase DSS object with that phase's p/q, named `<name>_<phase>` (`ld_x_a`), for loads and DER. A delta device with unequal phases raises until a producer writes one, because a CIM phase on a delta load names a branch (orderedPhases gap) |
| E9 | Element kV | From `get_base_voltage`: LL for polyphase and delta, LN for a 1-phase wye device, LL for a split-phase load (DSS-5). It is undone exactly as the importer's `injection.line_kv` did it |
| E10 | Options | Only `Set defaultbasefreq` and `voltagebases` (the distinct nominal BaseVoltages, in kV) are written. `earthmodel` is not in CIM and is engine-defaulted |

## 9. S8: load shapes (2026-11-21; built at the user's "implement the remaining changes across the other spokes")

GLM's §8.9 (`GLM_REWRITE_PLAN.md`) settled the CIM: the user's `ConformLoadSchedule → ConformLoadGroup ←
ConformLoad` pattern, its points in the Parquet sidecar. This is the DSS half, onto the same CIM. Decisions S8-1 to
S8-7 are in `cimhub_opendss/docs/CIMTBL_MAPPING.md#s8-load-shapes` (import) and `docs/EXPORT_MAPPING.md#s8-load-shapes`
(export); they were made while building, from the engine's behaviour, not approved one by one.

| where | what |
|---|---|
| import | `importer/cimtbl/loadshape.py`: a shape a Load names as `yearly` → `lg_` group + `ls_` schedule (multipliers, `qmult` as value2, the interval slot assigned last, `startTime` = 2020-01-01T00:00Z + one interval, `action=normalize` applied); `load.py`: those loads are ConformLoads; `DssImporter(time_points=)` fills the `RegularTimePoint` table |
| export | `exporter/loadshape.py` + `load.py`'s `yearly=`; `DssExporter(time_points)`; the writer writes Loadshape first |
| core | `time_points.add_regular_time_points` (by mRID, after binding; GLM now uses it too) and `regular_time_points(value2=)`; `getters/load_schedule.get_schedule_points` (GLM's player check, moved) |
| engine findings | sample k is in force at k × interval, and wraps; Q follows mult without qmult; without `npts` the engine reads no points, inline or from a file; `UseActual` makes a load's snapshot kW depend on command order |
| not built | `daily` / `duty` roles (one LoadGroup per ConformLoad); Hour-array shapes; `UseActual` (so no DSS form for a NonConformLoad); ~~shapes on PVSystem, Storage, Generator~~ (§10); shapes on a Vsource |
| tests | `test_cimtbl_loadshape.py` (19), `test_export_loadshape.py` (5); `tests/cross_format/test_glm_player_to_dss.py` (2) |

`cimhub_opendss` imports `cimhub_core.time_points` only when points are passed; ~~its pyproject should gain the
`cimhub-core[time-points]` extra~~: done 2026-11-21 at the user's "fix the pyproject.toml files"
(`cimhub_opendss[time-points]`, installed by the workspace root; `uv lock` rerun).

## 10. S9: device shapes (2026-11-21; built at the user's "shapes for PV, storage, etc using the nc_schedule profile classes")

A yearly LoadShape on a PVSystem, Storage or Generator is nc_schedule's per-device `EnergyConnectionSchedule` on its
`PowerElectronicsConnection` or `SynchronousMachine`, its points the device's p and q at each sample
(`EnergyConnectionTimePoint` rows in the sidecar, as GDM's T1). The user confirmed it (asked: per-device
EnergyConnectionSchedule with actual points, storage in follow mode only) over a `PowerSchedule` on the unit.
Decisions S9-1 to S9-8 are in `cimhub_opendss/docs/CIMTBL_MAPPING.md#s9-device-shapes` (import) and
`docs/EXPORT_MAPPING.md#s9-device-shapes` (export); they were made while building, from the engine.

| where | what |
|---|---|
| import | `pvsystem.py`, `storage.py`, `generator.py`: the `<mRID>_yearly` schedule row in their documents and `schedule_points` (the snapshot rule at each sample: `pv_power` at irradiance x mult, `follow_power`, kW and kvar x mult); `loadshape.py`'s `device_shape`, `point_times`, `device_schedules`, `DevicePoints`; `DssImporter.to_cim` adds the `EnergyConnectionTimePoint` table |
| export | `loadshape.py`'s `ShapeRegistry` (shared shapes, `_2` suffixes), `device_schedule`, `device_yearly`; `pvsystem.py` (mult = p / panel, `%Cutin=0 %Cutout=0`, q by kvar or pf), `storage.py` (`DispMode=follow`, mult = output / kWrated), `generator.py` (mult = p / kW, q checked) |
| core | `time_points.add_device_time_points` (by mRID, through CIM-Builder's `EnergyConnectionScheduleBuilder.time_points`); `getters/device_schedule.get_device_schedule` |
| engine findings | the shape scales a PV's irradiance (%Pmpp, %Cutout and the kVA cut per sample) and a generator's kW and kvar together; a PV's cut-in/cut-out has hysteresis; an off PV keeps a set kvar unless `VarFollowInverter` (snapshot too: `pv_power` fixed, no golden changed); a follow-mode battery runs at mult x kWrated capped at kVA, idles at 0, and ignores %Charge, %Discharge, %kWrated |
| not built | `daily` / `duty`; temperature shapes; a battery's trigger modes; a shape on a Vsource or a wind generator; a schedule on a connection written as several DSS objects; the GDM export of a device schedule (`_consumer` raises for a schedule on anything but an EnergyConsumer) |
| tests | `test_cimtbl_device_shape.py` (21: goldens, the engine's p and q at every sample of every device, raises), `test_export_device_shape.py` (10: the export golden, yearly-mode engine parity every 30 minutes for 8 hours, shared shapes, raises); core `test_time_points.py` (+3) |
