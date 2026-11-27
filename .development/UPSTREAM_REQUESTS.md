# What CIMHub needs from upstream

Open requests to the libraries CIMHub builds on (invariant I9: file it here, never write a local stand-in).
Each entry says the repo, why CIMHub needs it, and how to reproduce it. Move an entry to "Closed" with the fixing
commit once it is verified from this repo.

| # | repo | ask | blocks |
|---|---|---|---|
| U1 | CIM-Graph | Import legacy profiles lazily. `import cimgraph.models` loads `cim17v40` (from `cimgraph.queries.sparql.get_all_nodes`) and `cimhub_2023` (from `cimgraph.models.feeder_model`) at module import: about 0.6 s and two profiles a cim18v17-only process never uses. | F1 exit check "importing `cimhub_core` loads no legacy profile". Until it is fixed, the check is a grep of `cimhub_*/src`. |
| U4 | CIM-Tables or CIM-Builder | Upstream homes for derived math that is now in `cimhub_core/derived/`: star↔mesh impedance, short-circuit/no-load test → mesh/core admittance, conductor distances → XY positions (`derived/spacing.py`, getters G5), ZIPV coefficients, a 1- or 2-phase line's phase matrix from sequence values and the n-conductor balanced matrix (`derived/sequence.py`, S2, S3), Kron reduction of grounded conductors (`derived/kron.py`, getters G2). | nothing; move upstream when accepted |
| U5 | CIM-Builder | About 15 builder modules (`new_base_voltage`, …) still import cimhub_2023 or cim18gad. Spokes use only the cim18v17 builders until they are ported. | GDM wave, if it needs one of them |
| U6 | CIM-Profiles | Native unit spellings that pint misreads (`sf`, `$` → `USD`) need a home in the shared unit registry. Today they are in the old core `units.py`, which is not carried over. | any spoke whose reader meets them |
| U8 | CIM-Profiles (CIM WG13) | `RotatingMachine.phaseConnection` (`PhaseShuntConnectionKind`), as `EnergyConsumer` and `PowerElectronicsConnection` have. SynchronousMachine has none, so a delta OpenDSS Generator is written as `earthing=false` (S4b-5), which an ungrounded wye would also be. | DSS exporter: a delta machine back to `conn=delta` without relying on DSS having no ungrounded-wye machine |
| U9 | CIM-Tables | A `phases` column on a class with no `<Class>Phase` child (SeriesCompensator) should set `Terminal.phases` only, as on a TransformerEnd, instead of raising. Today `reactor.cimtbl` writes `Update Table Terminal: mRID, phases` for the generated Terminals. | nothing; the Update works |
| U10 | CIM-Tables | Tell a balanced three-phase device from three separate A, B, C phases. Today `phases=ABC` always writes three `<Class>Phase` children, which in CIM (and the OpenDSS CIM export) means a per-phase device; a balanced one has none. CIMHub writes a blank `phases` cell for balanced ABC (`cimhub_core.cimtbl.phases_cell`), so its Terminals lose `phases=ABC`. Ask: a spelling (a column or a value) that sets `Terminal.phases` without children; U9 (SeriesCompensator) would fall out of it. | nothing; Terminal.phases of balanced devices is unset until then |
| U12 | CIM-Tables | `get_qty` on a declared power base: a transformer percent read on another S at the From winding's own voltage (e.g. `get_qty(mesh, "x", "percent", power_base=...)`). DSS and GLM put every percent on winding 1's kVA and RAW on the system MVA, while CIM stores each on its From winding's `baseU²/baseS`. Until then `getters/transformer.py` moves the stored percent itself, z × S_new/S_old and y × S_old/S_new (powers only, no local `z_base`; getters G6). | nothing; the getter's power ratio works |
| U13 | CIM-Profiles (CIM WG13) | A positive-sequence (subtransient/transient/synchronous) reactance on SynchronousMachine. cim18v17 has r, r0/x0, r2/x2 and no x (CIM16's `satDirectSubtransX` and the like are gone), so RAW ZX and DSS Xd/Xdp/Xdpp have no home and `getters.der.MachineImpedance` has no x. | RAW generator ZSORCE round trip; DSS Generator Xd |
| U15 | CIM-Profiles (the user, FunctionBlock package in the UML) | **TODO, waiting on the user's repair of the FunctionBlock package.** Recloser trip settings: phase and ground pickups (DSS `PhaseTrip`, `GroundTrip`, `PhaseInst`, `GroundInst`), the fast and delayed time-current curves (`PhaseFast`, `PhaseDelayed`, `GroundFast`, `GroundDelayed`) with their time dials (`TDPhFast`, `TDGrFast`, `TDPhDelayed`, `TDGrDelayed`), `NumFast`, `Reset` and `Delay`. In cim18v17 `OverCurrentProtectionFunctionBlock` and its parents carry only `operatingQuantityType`. CIM17's `RecloserInfo` had `phaseTripRating`, `groundTripRating` and `recloseLockoutCount`. Census: 54 reclosers set PhaseTrip/GroundTrip (IEEE9500 53, IEEE13_CDPSM 1). Then: map them in `importer/cimtbl/line.py` `RECLOSER_FIELDS` (untranscribed today, note `_PROTECTION`) and `exporter/switch.py` (Recloser slots, engine default today), and drop F5/G5 from EXPORT_MAPPING.md. The same repair may give the Fuse curves (`FuseCurve`) and the Relay (DSS-11) a home. | the exported recloser trips at the engine's 1 A in a controls-on solve (EXPORT_MAPPING.md S6f F5, S6g G5); parity runs controls off |
| U17 | CIM-Profiles (CIM WG13) | An overhead / underground marker on `ACLineSegment` that needs no conductor data: `PowerSystemResource.PSRType` (absent from cim18v17) or a construction kind on the segment. Today the kind reaches CIM only through a WireInfo class (`OverheadWireInfo` vs `CableInfo`) on the line's phases or `WireConfiguration`, and a matrix line has none: GLM `overhead_line`/`underground_line` with a `z11`..`z33` `line_configuration` (every Milsoft WindMil export) becomes a `PerLengthPhaseImpedance` only, so the class is lost. Reported by the clallam_cim workspace (2026-11-16), which needs a site's underground share. | GLM matrix lines' overhead/underground kind; any GIS line known only by impedance |
| U18 | CIM-Profiles | Make reactive power its own dimension in the unit registry. `units.txt` defines `imaginary = [] = i = reactive` (dimensionless) and `VAr = watt * imaginary`, so pint converts W to VAr: `cim.ActivePower(1, 'kW').to('VAr')` is 1000.0, and `get_qty(device, "p", "VAr")` returns the active power as if it were reactive. A getter called with its active and reactive units swapped (`getters.phase_power.device_power(device, children, "kVAr", "kW")`) gives wrong numbers with no error. Ask: `imaginary` as a base dimension (`[imaginary]`), so W to VAr raises `DimensionalityError`. A local check in core would be a stand-in (I9). | nothing today (every caller passes the right units); a swapped unit is silent |
| U19 | CIM-Tables | A `(pu)` column on a PerCent attribute. `set_attr` raises on any unit but unitless and `(percent)` there (R14), and `get_qty` reads a PerCent only as `'percent'`. GridLAB-D writes these values as fractions (inverter `efficiency`, solar `shading_factor`, battery `round_trip_efficiency`, a transformer's pu impedance as `percentImpedance`), so the GLM importer converts pu to percent itself through pint (`importer/cimtbl/inverter.py`, `transformer_configuration.py` `_percent`), and the exporter converts back (`exporter/units.py`). Ask: `x (pu)` on a PerCent stores `PerCent(x × 100)`, and `get_qty(obj, attr, 'pu')` returns the stored number / 100. Reproduce: `Object TransformerTankConfiguration: mRID=t, percentImpedance (pu)=0.02` raises. | nothing; the spoke's pint conversion works, but the pu value is not verbatim in the artifact (I2) |
| U20 | CIM-Tables | `impedance.z_base` should raise ValueError on a U or S of 0 or less. Today a `ratedS` of 0 divides by zero and a negative base silently flips the sign of every pu/percent value read on it. Until then `getters/transformer.py` `_check_ratings` and `getters/der.py` `_rating` check the ratings before reading (found porting PR #14, X38). | nothing; the core checks work, but each class needs its own |

## Upstream responses (not yet verified from this repo)

From CIM-Tables, 2026-11-09, `rc1`, uncommitted at the time of writing. Verify, then close or reopen.

- **U10, declined: a blank `phases` is the balanced three-phase spelling.** No new column or value. A blank (or
  absent) `phases` cell makes no `<Class>Phase` children and leaves `Terminal.phases` unset, which CIM defines
  as ABC (`Terminal.phases`: "If the attribute is missing, three phases (ABC) shall be assumed"). `phases=ABC`
  means a per-phase device with three children. So `cimhub_core.cimtbl.phases_cell` is the intended form, not a
  stand-in. A consumer that wants every Terminal's phases explicit fills the missing ones as ABC after loading (a
  topology-processor step). Documented in CIM-Tables `docs/CIMTBL_DESIGN.md`, Phases.
- **U9, declined: follows from U10.** A balanced SeriesCompensator leaves `phases` blank. `phases` still
  raises on a class with no `<Class>Phase` child, so per-phase information is never silently dropped. A
  non-ABC one keeps today's form: its Terminals' phases written literally (`Update Table Terminal: mRID,
  phases`), or the Terminals as their own rows (U11, closed).
- **U12, done.** `graph_write.get_qty(obj, attr, unit, ..., power_base=...)` takes a CIMUnit, a `Qty` or a
  number in VA. It replaces only S. U comes from the usual rule (the From winding's `baseU` for a mesh
  impedance, the BaseVoltage for an unrated class), so z × S_new/S_old and y × S_old/S_new fall out:
  `get_qty(mesh, "x", "percent", power_base=Qty(1500, "kVA"))`. It is read-only; `set_attr` has no
  `power_base`. `getters/transformer.py` can drop its power ratio.
- **U4, CIM-Tables declines; CIM-Builder is the better home.** cimtables is the file format; its only math is
  unit and base conversion (`impedance.z_base`). Star↔mesh, Kron, sequence → phase matrices, ZIPV and
  conductor positions are engineering derivations for the builders.
- **Heads-up (not a request):** cim-graph `45822b4` makes `XMLFile` raise on a missing file. A test that builds
  a model over `XMLFile(filename=tempfile.mktemp(...))` as a dummy connection now fails. Use `connection=None`
  (in memory), as CIM-Tables' tests now do. No CIMHub or CIM-Builder test does this today.

## Closed (verified from this repo, 2026-11-07)

- U7 (2026-11-20): all five upstream packages are released on PyPI: cim-graph 0.6.1a1, cim-profiles 0.2.0a6,
  cim-tables 0.1.1a1, cim-builder 0.1.1a1 and cim-topology 0.1.2a1 (with `cimtopology.core`). The packages pin
  them as floors. Every suite passed on wheels built with `--no-sources` and installed from PyPI alone (core 466,
  gdm 269, gridlabd 194, opendss 715, raw 368, cross_format 17). 0.2.0a5 typed 134 enum fields as associations;
  0.2.0a6 fixed it and renamed `Elbow` to `ElbowSwitch` (`cimhub_opendss/exporter/switch.py` follows).
- U16 (2026-11-20): `TransformerTank.baseS` is in every cim-profiles release from 0.2.0a1; the floor is 0.2.0a6.

- U11 (2026-11-09): declined by CIM-Tables, closed. A `.cimtbl` means what binding makes, so there is no
  text-level inverse of the connectivity columns; explicit Terminal rows bind (CIM-Tables `rc1` `f8718d3`,
  `tests/test_update.py`, 12 pass). CIMHub reads the Terminals from the bound network instead:
  `CimtblImporter.bound_parts(model, network)` maps the parts that need them, and `cimtbl_to_cim(bound_parts=)`
  writes them beside the rest, imports them last and binds them onto the same network (one bind). DSS
  `buscoords.cimtbl` is the one such part; core's stand-in `document_terminals` is deleted. Before deleting it, the
  bound Terminals were checked equal to its output on IEEE13_CDPSM (46 equipment), IEEE8500 (6,082) and IEEE9500
  unbal (8,072).
- U14 (2026-11-09): CIM-Graph `GraphModel.set_default_bases` takes `base_frequency` from the graph's
  `BaseFrequency` (a shared `_graph_base` with BasePower). Several that disagree, or one against an explicit base,
  raise. CIM-Graph tests 177 pass; a 50 Hz DSS deck now imports with `network.base_frequency` 50 Hz. Uncommitted
  in `~/CIM-Graph` (branch `cimprofiles-0.6`).
- U3 (2026-11-08): own-terminal control. CIM-Tables' additive `Update` breaks the cycle: the compensator row,
  then the control naming its generated `cap_<name>_T1`, then `Update LinearShuntCompensator: mRID=...,
  RegulatingControl=...`; `RegulatingControl.RegulatingCondEq` binds as the compensator (S4a CapControl).
- U2 (2026-11-08): the template shapes bind. CIM-Tables `8fc537f` keeps a TransformerEnd's phases on its Terminal
  only, so a `phases` column on a `TransformerTankEnd` (which has none on a configuration) raises by design. The
  fix was in core: `shapes/transformer_template.cimtbl` no longer gives its tank ends phases; the instance's
  `PowerTransformerEnd` carries them.

- R1a: a `.cimtbl` suffix in a document name raises (`cimtables/document.py`).
- R7 `get_qty` (`cimtables/graph_write.py`), R8 `diff_models` (`cimtables/diff.py`).
- R10: mRIDs holding `#` seed distinct UUIDs (`lc_1p_#2acsr_#2n` vs `lc_1p_#2arv_#2n`).
- R12: type hints cached per class (`graph_write.type_hints = functools.cache(...)`).
- R14: `Qty(5, 'percent')` on a PerCent attribute stores `5.0`.
