# GridLAB-D → `.cimtbl` mapping spec

**Status:** S0 (master) built 2026-11-09; each later section is written with its slice and approved before that
slice's code. Plan: `.development/GLM_REWRITE_PLAN.md`. Contract and format: the `cimtbl-import-contract`,
`cimtbl-shapes` and `cimtbl-mapping-spec` skills. Samples come from the vendored decks in `tests/decks/` (origins in
its README).

## Artifact files and order

The master imports the parts in `MAPPING_ORDER` (`importer/glm_to_cimtbl.py`), which follows the plan's section 2.
S0 has no parts; S1 adds `bus.cimtbl` and `source.cimtbl`; S2 the six catalog files; S3a the six line and switch
files; S3b `transformer_configuration.cimtbl` (after the catalogs) and `transformer.cimtbl` (after the
switches); S3c `regulator.cimtbl` (after the transformers; `regulator_configuration` has no file of its own);
S4a the core `zip_fractions.cimtbl` (after `source.cimtbl`), then `load.cimtbl`, `triplex_load.cimtbl`,
`triplex_node.cimtbl` and `capacitor.cimtbl` (after the regulators).

## master

Mapper: `importer/glm_to_cimtbl.py` `map_master`. Test: `tests/test_glm_to_cimtbl.py`; golden
`tests/goldens/IEEE13_cdpsm/IEEE13_cdpsm.cimtbl`.

| row | from | rule |
|---|---|---|
| `Substation`, `Feeder` | `substation=` and `feeder=`, each the `name` the caller passes unless given (D7; the model's `Model` and file stem stay `name`) | mRIDs `sub_<substation>`, `fdr_<feeder>`, source case |
| `Update Table Terminal` (last, after the Imports) | every mapped link touching a swing bus | `NormalHeadFeeder` = the feeder on that link's Terminal there: `<mRID>_T1` for its `from`, `_T2` for its `to` (a regulator: each unit's); a head on a link no mapper writes (a sectionalizer, a series reactor) raises |
| `BaseFrequency` | `module powerflow { nominal_frequency ...; }`, else `#set powerflow::nominal_frequency=...` | else GridLAB-D's 60 Hz, listed as `# defaulted` |
| `BaseVoltage` | the topology walk's distinct bus voltages (`cimtopology.core`), highest first | `nominal_kv` rounding; mRIDs `bv_12p47kv`, `bv_240v` |
| comment | every GLM type no mapper reads, with its count, including types the schema lacks (`recorder`) | GLM-14 |

Fail fast: an expression the reader kept (`LIGHTS*1.2`) on a record of a mapped class raises, naming the object, its
file and line and the slot (GLM-8). The walk raises on a coil that cannot sit on its island (a deck defect, listed
in `tests/decks/README.md`).

## S1 (approved 2026-11-09 with S1-2 and S1-3 amended; built 2026-11-09)

S1 maps the buses and the swing source. Two artifacts, written by `importer/cimtbl/bus.py`:

| # | artifact | from | shape |
|---|---|---|---|
| 1 | `bus.cimtbl` | every root bus object: any `node` or `triplex_node` subclass (node, meter, substation, triplex_node, triplex_meter, and load, capacitor, triplex_load, ... when they are a root) | `ConnectivityNode` + `BaseVoltage` |
| 2 | `source.cimtbl` | every `substation` and every bus with `bustype SWING` | `source` (`EnergySource`), `BasePower` |

`bus.cimtbl` is not one native table: in GridLAB-D a load, a capacitor and a meter are each a node, and lines end on
them, so every bus must exist before any equipment file (plan section 2, amended in S0). It is the topology walk's
result, as DSS `bus.cimtbl` is.

### Buses

```
# GridLAB-D buses -> ConnectivityNode, BaseVoltage from the topology walk (cimtopology.core); 21 buses.
# Mapping: cimhub_gridlabd/docs/CIMTBL_MAPPING.md#buses
Table ConnectivityNode: mRID, name, BaseVoltage, ConnectivityNodeContainer=fdr_IEEE13_cdpsm
    sourcebus, sourcebus, bv_115kv
    611,       611,       bv_4p16kv  # children: cap_cap2, ld_611
    ...
    634,       634,       bv_480v    # children: 634_pvmtr, 634_stmtr, ld_634c
    house,     house,     bv_240v    # children: house_pvmtr, house_stmtr, ld_house
```

- **Identity:** `mRID` and `name` are the GLM name, in source case (D3), with no prefix: the cell every later `node`
  column writes. GLM names are unique across a model, and every equipment mRID has a prefix, so they cannot collide.
- **Root buses (GLM-4):** a bus object whose `parent` is a bus is solved by GridLAB-D as its parent's bus. It gets
  no row; its equipment lands on the root of its parent chain, and its name is listed in the root row's comment
  (`# children: ...`). A parent that is not a bus object, a loop, or a child whose phase conductors are not a subset
  of its root's raises.
- **BaseVoltage (GLM-1, decided 2026-11-09):** the walk's kV for the bus (source and transformer ratings). Rows are
  sorted highest voltage first, then by name. A bus the walk does not reach has no row; equipment on it raises in its
  own mapper.
- **`nominal_voltage` check:** every bus object, root or child, is checked on the walk's system: `line_voltage(nominal_voltage,
  system)` against the walk's kV. A disagreement over 10 % is listed in the table comment, not raised:
  grouped by how it disagrees: `# nominal_voltage disagrees with the walk (10%): 480.0 V (0.8314 kV 3-phase) on
  bv_480v (12): R1-12-47-4_load_1, ...`.
  The taxonomy feeders give every meter 480 V (plan section 3.5); the IEEE decks agree everywhere.
- **Untranscribed:** the groups are object metadata, location (home: the location shape, mapped when a deck sets
  it), reliability, dynamics, solver state and outputs, metering and billing, and the bus's own loads (`power_12`,
  `power_A`, ...), which the load slice S4a maps. With 80 to 200 slots per class, the table comment lists the
  untranscribed slots **this model sets**, with counts (`# untranscribed, set here: triplex_node power_12 7492`),
  rather than every name: D5's purpose (nothing disappears silently) holds, and the full list is the field tables
  below. Until S4a the taxonomy triplex nodes' `power_12` loads are listed there, not mapped.

### Source

```
# GridLAB-D substation and SWING buses -> EnergySource; 1 source.
# Mapping: cimhub_gridlabd/docs/CIMTBL_MAPPING.md#source
Object BasePower: mRID=sbase_sourcebus, basePower (MVA)=12.0
Table EnergySource: mRID, name, node, phases, nominalVoltage (V), voltageMagnitude (V), voltageAngle (deg), BaseVoltage, EquipmentContainer=sub_IEEE13_cdpsm
    src_sourcebus, sourcebus, sourcebus, , 114999.99834276171, 114999.99834276171, 0.0, bv_115kv  # derived: line_voltage(nominal_voltage=66395.28), line_voltage(|positive_sequence_voltage|=66395.28)
```

- **Identity:** `mRID` = `src_` + name; `node` = the bus itself (a swing bus with a parent raises).
- **Which buses:** every `substation` (GridLAB-D's substation is always the swing) and every bus with `bustype
  SWING`. `SWING_PQ` is ignored, a plain bus with a row comment saying so (S1-2, the user: revisit if something
  breaks): it becomes a swing only when its island separates (IEEE13_cdpsm bus 634, under the PV and storage meters).
- **Phases:** the phase letters of `phases`, `N` dropped (a grounded wye source); `ABC` is a blank cell
  (`phases_cell`). One or three conductors; any other count raises (the walk already does).
- **Voltage (derived, `topology.line_voltage`):** `nominalVoltage` = `line_voltage(nominal_voltage)` on the walk's system.
  `voltageMagnitude` = `line_voltage(|V|)` and `voltageAngle` = `arg(V)` in degrees, where V is the substation's
  `positive_sequence_voltage`, else the bus's `voltage_A` (`voltage_1` on a triplex bus). Unset: V = `nominal_voltage`
  at 0 degrees, listed as `# defaulted`. Units are the written ones (V). |V| more than 10 % from `nominal_voltage`
  raises: the deck gives the wrong source voltage (or the wrong `defines`).
- **`reference_phase`:** unset or `PHASE_A`; anything else raises (the angle would refer to another phase).
- **Impedance: a stiff default (S1-3, the user: so round trips work).** GridLAB-D's swing bus has no source
  impedance, and the DSS exporter needs one. `bus.default_source_impedance(kV)` gives |Z| = kV² / 10,000 MVA with
  X/R 10, the same in zero sequence (12.47 kV: 0.0155 ohm; 115 kV: 1.32 ohm), listed on the row as `# defaulted`.
  The constants are `DEFAULT_SHORT_CIRCUIT_MVA` and `DEFAULT_X_OVER_R`.
- **`base_power`** (substation): copied to a `BasePower` row in its written unit (`12MVA` gives `basePower (MVA)=12.0`).
  Two substations with different bases raise in cimtables.
- **Untranscribed:** `power_convergence_value` (solver setting), the sequence voltages other than positive, the
  transmission interface slots, and every bus slot above.

### Fail fast (S1)

| condition | message names |
|---|---|
| a parent that is not a bus object, or a parent loop | the object and its chain |
| a child bus whose phases are not a subset of its root's | both objects and their phases |
| a swing bus with a parent | the bus |
| a source on 2 conductors | the bus and its phases |
| a source voltage more than 10 % from `nominal_voltage` | the bus, both values |
| `reference_phase` other than `PHASE_A` | the bus |
| a slot of a bus class no group classifies (schema regeneration) | class and slot (`bus.classify`) |

### Decisions for S1

| # | question | recommendation |
|---|---|---|
| S1-1 | Files | **approved:** `bus.cimtbl` for every root bus and `source.cimtbl` for the sources |
| S1-2 | `SWING_PQ` | **approved, amended:** ignored, a plain bus with a row comment; revisit if something breaks |
| S1-3 | Source impedance | **amended by the user:** a small default impedance so round trips work (stiff source, above) |
| S1-4 | Source voltage | **approved:** derived from `positive_sequence_voltage` / `voltage_A`; over 10 % from nominal raises. The tests pass each Java export its own `VSOURCE` (IEEE13: 66395.28, IEEE123: 2401.78 = 4.16 kV / sqrt 3) |
| S1-5 | `nominal_voltage` disagreements | **approved:** listed on `bus.cimtbl`'s table comment, for roots and children alike |
| S1-6 | Field tables | **approved:** generated from `bus.py` `FIELDS` with `fields_table` (below) |

### Built (2026-11-09)

- `importer/cimtbl/bus.py` (`map_buses`, `map_source`, `default_source_impedance`), wired into
  `glm_to_cimtbl.py` before `MAPPING_ORDER`. `CLASSIFIED` (every mapped class's `FIELDS`) drives the master's
  not-mapped list and the expression guard, which now raises only for a slot a mapper reads.
- Atoms `tests/atoms/bus/feeder` (substation + `base_power`, child load and triplex node, a 480 V meter on a 480 V
  bus, `SWING_PQ`, center tap) and `tests/atoms/source/swing_node` (taxonomy-style SWING node, polar voltage);
  goldens `tests/goldens/IEEE13_cdpsm/{bus,source}.cimtbl`; `tests/test_cimtbl_bus.py`.
- Every deck binds master + bus + source except the two listed deck defects (IEEE123_transactive's `Object`,
  IEEE13_houses' bus-634 center taps).

### Explicit fields (every other slot is in an untranscribed group, `bus.py` `_GROUPS`)

| class | slot | kind | target |
|---|---|---|---|
| all bus classes | `name` | copied | `ConnectivityNode.mRID`, `name` (root buses) |
| | `parent` | structural | root merge (GLM-4) |
| | `phases` | structural | child check; `EnergySource.phases` |
| | `nominal_voltage` | structural | check against the walk; `EnergySource.nominalVoltage` (derived) |
| | `bustype` | structural | SWING: an `EnergySource` |
| node, meter, substation | `voltage_A` | derived | swing only: `voltageMagnitude`, `voltageAngle` |
| triplex_node, triplex_meter | `voltage_1` | derived | swing only: `voltageMagnitude`, `voltageAngle` |
| substation | `positive_sequence_voltage` | derived | `voltageMagnitude`, `voltageAngle` |
| | `reference_phase` | structural | unset or `PHASE_A` |
| | `base_power` | copied | `BasePower.basePower` (written unit) |

### Field tables (generated: `fields_table(cls, records, fields=FIELDS[cls])`, samples from tests/decks)

#### node

| Node field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, NodeName]` | `1`, `10`, `100` | copied | `ConnectivityNode.mRID`, `ConnectivityNode.name`; root buses only; a child bus is its root's node (GLM-4) |
| `parent` | `Optional[str]` | `611`, `GC-12-47-1_meter_4`, `R1-12-47-3_meter_22` | structural | a bus whose parent is a bus is solved as the root of its parent chain: no node of its own; its name is listed on the root's row (GLM-4) |
| `groupid` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `latitude` | `Optional[str]` |  | untranscribed | home: the location shape (EquipmentLocation); mapped when a deck sets it |
| `longitude` | `Optional[str]` |  | untranscribed | home: the location shape (EquipmentLocation); mapped when a deck sets it |
| `in_svc` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `out_svc` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `rank` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `flags` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `phases` | `Optional[str]` | `ABCN`, `AN`, `CN` | structural | a child's phase conductors must be a subset of its root's; on a swing bus, EnergySource.phases (blank when ABC) |
| `nominal_voltage` | `Optional[float]` | `2401.78`, `277.13`, `2401.7771` | structural | checked against the walk's kV on the bus's system (line_voltage); a disagreement over 10 % is listed in bus.cimtbl, not written (GLM-1). On a swing bus: EnergySource.nominalVoltage, derived by line_voltage |
| `inrush_integration_method` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `condition` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `solution` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `bustype` | `Optional[str]` | `SWING_PQ`, `SWING` | structural | SWING: an EnergySource row (source.cimtbl). PQ, PV, SWING_PQ: a plain bus. SWING_PQ only turns into a swing when islanded |
| `busflags` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `reference_bus` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `maximum_voltage_error` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `voltage_A` | `Union[dict, Complex, NoneType]` | `Complex({'real': 2401.7771, 'imag': 0...`, `Complex({'real': 480.0, 'imag': 0.0})`, `Complex({'real': 7200.0, 'imag': 0.0})` | derived | on a SWING bus only: EnergySource voltageMagnitude = line_voltage(|V|) and voltageAngle = arg(V) in degrees; elsewhere the solver's initial guess |
| `voltage_B` | `Union[dict, Complex, NoneType]` | `Complex({'real': -1200.8886, 'imag': ...`, `Complex({'real': -240.0, 'imag': -415...`, `Complex({'real': -3600.0, 'imag': -62...` | untranscribed | the solver's initial guess |
| `voltage_C` | `Union[dict, Complex, NoneType]` | `Complex({'real': -1200.8886, 'imag': ...`, `Complex({'real': -240.0, 'imag': 415....`, `Complex({'real': -3600.0, 'imag': 623...` | untranscribed | the solver's initial guess |
| `voltage_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `voltage_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `voltage_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `prerotated_current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `prerotated_current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `prerotated_current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `deltamode_generator_current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_generator_current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_generator_current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_PGenTotal` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_full_Y_matrix` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_full_Y_all_matrix` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `NR_powerflow_parent` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `current_inj_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_inj_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_inj_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_AN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_BN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_CN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_AN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_BN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_CN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_AN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_BN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_CN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `residential_nominal_current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_A_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_A_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_B_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_B_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_C_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_C_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `house_present` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `mean_repair_time` | `Optional[float]` |  | untranscribed | reliability data |
| `frequency_measure_type` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `sfm_Tf` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `pll_Kp` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `pll_Ki` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `measured_angle_A` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_A` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_angle_B` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_B` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_angle_C` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_C` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `service_status` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `service_status_double` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `previous_uptime` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `current_uptime` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `Norton_dynamic` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `Norton_dynamic_child` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `generator_dynamic` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `reset_disabled_island_state` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `GFA_enable` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_low_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_high_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_low_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_high_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_reconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_disconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_disconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_status` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_trip_method` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `topological_parent` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `behaving_as_swing` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |


#### meter

| Meter field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, MeterName]` | `634_pvmtr`, `634_stmtr`, `GC-12-47-1_meter_1` | copied | `ConnectivityNode.mRID`, `ConnectivityNode.name`; root buses only; a child bus is its root's node (GLM-4) |
| `parent` | `Optional[str]` | `634` | structural | a bus whose parent is a bus is solved as the root of its parent chain: no node of its own; its name is listed on the root's row (GLM-4) |
| `groupid` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `latitude` | `Optional[str]` |  | untranscribed | home: the location shape (EquipmentLocation); mapped when a deck sets it |
| `longitude` | `Optional[str]` |  | untranscribed | home: the location shape (EquipmentLocation); mapped when a deck sets it |
| `in_svc` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `out_svc` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `rank` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `flags` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `phases` | `Optional[str]` | `ABCN`, `CN`, `AN` | structural | a child's phase conductors must be a subset of its root's; on a swing bus, EnergySource.phases (blank when ABC) |
| `nominal_voltage` | `Optional[float]` | `277.13`, `480.0`, `7200.0` | structural | checked against the walk's kV on the bus's system (line_voltage); a disagreement over 10 % is listed in bus.cimtbl, not written (GLM-1). On a swing bus: EnergySource.nominalVoltage, derived by line_voltage |
| `inrush_integration_method` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `condition` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `solution` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `bustype` | `Optional[str]` |  | structural | SWING: an EnergySource row (source.cimtbl). PQ, PV, SWING_PQ: a plain bus. SWING_PQ only turns into a swing when islanded |
| `busflags` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `reference_bus` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `maximum_voltage_error` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `voltage_A` | `Union[dict, Complex, NoneType]` | `Complex({'real': 7200.0, 'imag': 0.0})` | derived | on a SWING bus only: EnergySource voltageMagnitude = line_voltage(|V|) and voltageAngle = arg(V) in degrees; elsewhere the solver's initial guess |
| `voltage_B` | `Union[dict, Complex, NoneType]` | `Complex({'real': -3600.0, 'imag': -62...` | untranscribed | the solver's initial guess |
| `voltage_C` | `Union[dict, Complex, NoneType]` | `Complex({'real': -3600.0, 'imag': 623...` | untranscribed | the solver's initial guess |
| `voltage_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `voltage_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `voltage_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `prerotated_current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `prerotated_current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `prerotated_current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `deltamode_generator_current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_generator_current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_generator_current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_PGenTotal` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_full_Y_matrix` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_full_Y_all_matrix` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `NR_powerflow_parent` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `current_inj_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_inj_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_inj_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_AN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_BN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_CN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_AN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_BN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_CN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_AN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_BN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_CN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `residential_nominal_current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_A_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_A_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_B_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_B_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_C_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_C_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `house_present` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `mean_repair_time` | `Optional[float]` |  | untranscribed | reliability data |
| `frequency_measure_type` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `sfm_Tf` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `pll_Kp` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `pll_Ki` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `measured_angle_A` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_A` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_angle_B` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_B` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_angle_C` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_C` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `service_status` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `service_status_double` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `previous_uptime` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `current_uptime` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `Norton_dynamic` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `Norton_dynamic_child` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `generator_dynamic` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `reset_disabled_island_state` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `GFA_enable` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_low_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_high_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_low_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_high_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_reconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_disconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_disconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_status` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_trip_method` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `topological_parent` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `behaving_as_swing` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `measured_real_energy` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_energy_delta` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_energy` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_energy_delta` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_energy_delta_timestep` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_power` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_power_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_power_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_power_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_demand` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_power` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_power` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `meter_power_consumption` | `Union[dict, Complex, NoneType]` |  | untranscribed | metering and billing |
| `measured_voltage_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_voltage_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_voltage_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_voltage_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_voltage_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_voltage_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_voltage_A_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_voltage_B_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_voltage_C_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_max_voltage_A_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_max_voltage_B_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_max_voltage_C_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_voltage_AB_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_voltage_BC_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_voltage_CA_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_max_voltage_AB_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_max_voltage_BC_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_max_voltage_CA_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_voltage_A_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_voltage_B_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_voltage_C_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_min_voltage_A_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_min_voltage_B_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_min_voltage_C_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_voltage_AB_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_voltage_BC_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_voltage_CA_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_min_voltage_AB_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_min_voltage_BC_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_min_voltage_CA_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_voltage_A_mag_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_voltage_B_mag_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_voltage_C_mag_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_voltage_AB_mag_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_voltage_BC_mag_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_voltage_CA_mag_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_power_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_max_power_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_power_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_min_power_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_real_power_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_reactive_power_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_power_A_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_max_power_A_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_power_A_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_min_power_A_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_real_power_A_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_reactive_power_A_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_power_B_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_max_power_B_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_power_B_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_min_power_B_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_real_power_B_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_reactive_power_B_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_power_C_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_max_power_C_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_power_C_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_min_power_C_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_real_power_C_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_reactive_power_C_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_stats_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `customer_interrupted` | `Union[bool, Bool, NoneType]` |  | untranscribed | metering and billing |
| `customer_interrupted_secondary` | `Union[bool, Bool, NoneType]` |  | untranscribed | metering and billing |
| `sustained_count` | `Optional[int]` |  | untranscribed | metering and billing |
| `momentary_count` | `Optional[int]` |  | untranscribed | metering and billing |
| `total_count` | `Optional[int]` |  | untranscribed | metering and billing |
| `s_flag` | `Optional[int]` |  | untranscribed | metering and billing |
| `t_flag` | `Optional[int]` |  | untranscribed | metering and billing |
| `pre_load` | `Union[dict, Complex, NoneType]` |  | untranscribed | metering and billing |
| `monthly_bill` | `Optional[float]` |  | untranscribed | metering and billing |
| `previous_monthly_bill` | `Optional[float]` |  | untranscribed | metering and billing |
| `previous_monthly_energy` | `Optional[float]` |  | untranscribed | metering and billing |
| `monthly_fee` | `Optional[float]` |  | untranscribed | metering and billing |
| `monthly_energy` | `Optional[float]` |  | untranscribed | metering and billing |
| `bill_mode` | `Optional[str]` |  | untranscribed | metering and billing |
| `power_market` | `Optional[str]` |  | untranscribed | metering and billing |
| `bill_day` | `Optional[int]` |  | untranscribed | metering and billing |
| `price` | `Optional[float]` |  | untranscribed | metering and billing |
| `price_base` | `Optional[float]` |  | untranscribed | metering and billing |
| `first_tier_price` | `Optional[float]` |  | untranscribed | metering and billing |
| `first_tier_energy` | `Optional[float]` |  | untranscribed | metering and billing |
| `second_tier_price` | `Optional[float]` |  | untranscribed | metering and billing |
| `second_tier_energy` | `Optional[float]` |  | untranscribed | metering and billing |
| `third_tier_price` | `Optional[float]` |  | untranscribed | metering and billing |
| `third_tier_energy` | `Optional[float]` |  | untranscribed | metering and billing |


#### substation

| Substation field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, SubstationName]` | `150`, `sourcebus` | copied | `ConnectivityNode.mRID`, `ConnectivityNode.name`; root buses only; a child bus is its root's node (GLM-4) |
| `parent` | `Optional[str]` |  | structural | a bus whose parent is a bus is solved as the root of its parent chain: no node of its own; its name is listed on the root's row (GLM-4) |
| `groupid` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `latitude` | `Optional[str]` |  | untranscribed | home: the location shape (EquipmentLocation); mapped when a deck sets it |
| `longitude` | `Optional[str]` |  | untranscribed | home: the location shape (EquipmentLocation); mapped when a deck sets it |
| `in_svc` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `out_svc` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `rank` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `flags` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `phases` | `Optional[str]` | `ABCN` | structural | a child's phase conductors must be a subset of its root's; on a swing bus, EnergySource.phases (blank when ABC) |
| `nominal_voltage` | `Optional[float]` | `2401.78`, `66395.28` | structural | checked against the walk's kV on the bus's system (line_voltage); a disagreement over 10 % is listed in bus.cimtbl, not written (GLM-1). On a swing bus: EnergySource.nominalVoltage, derived by line_voltage |
| `inrush_integration_method` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `condition` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `solution` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `bustype` | `Optional[str]` | `SWING` | structural | SWING: an EnergySource row (source.cimtbl). PQ, PV, SWING_PQ: a plain bus. SWING_PQ only turns into a swing when islanded |
| `busflags` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `reference_bus` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `maximum_voltage_error` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `voltage_A` | `Union[dict, Complex, NoneType]` |  | derived | on a SWING bus only: EnergySource voltageMagnitude = line_voltage(|V|) and voltageAngle = arg(V) in degrees; elsewhere the solver's initial guess |
| `voltage_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | the solver's initial guess |
| `voltage_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | the solver's initial guess |
| `voltage_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `voltage_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `voltage_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `prerotated_current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `prerotated_current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `prerotated_current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `deltamode_generator_current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_generator_current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_generator_current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_PGenTotal` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_full_Y_matrix` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_full_Y_all_matrix` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `NR_powerflow_parent` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `current_inj_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_inj_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_inj_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_AN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_BN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_CN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_AN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_BN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_CN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_AN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_BN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_CN` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `residential_nominal_current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_A_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_A_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_B_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_B_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_C_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_C_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `house_present` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `mean_repair_time` | `Optional[float]` |  | untranscribed | reliability data |
| `frequency_measure_type` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `sfm_Tf` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `pll_Kp` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `pll_Ki` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `measured_angle_A` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_A` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_angle_B` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_B` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_angle_C` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_C` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `service_status` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `service_status_double` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `previous_uptime` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `current_uptime` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `Norton_dynamic` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `Norton_dynamic_child` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `generator_dynamic` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `reset_disabled_island_state` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `GFA_enable` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_low_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_high_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_low_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_high_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_reconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_disconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_disconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_status` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_trip_method` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `topological_parent` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `behaving_as_swing` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `zero_sequence_voltage` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `positive_sequence_voltage` | `Union[dict, Complex, NoneType]` | `Complex({'real': 2401.78, 'imag': 0.0})`, `Complex({'real': 66395.28, 'imag': 0.0})` | derived | EnergySource voltageMagnitude = line_voltage(|V|), voltageAngle = arg(V) in degrees; else voltage_A |
| `negative_sequence_voltage` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `base_power` | `Optional[float]` | `12.0` | copied | `BasePower.basePower` ({unit}); the system base (cimtables BasePower), in its written unit |
| `power_convergence_value` | `Optional[float]` | `100.0` | untranscribed | solver setting |
| `reference_phase` | `Optional[str]` |  | structural | the phase the angle refers to: unset or PHASE_A, else raises |
| `transmission_level_constant_power_load` | `Union[dict, Complex, NoneType]` |  | untranscribed | substation transmission interface (co-simulation with a transmission solver) |
| `transmission_level_constant_current_load` | `Union[dict, Complex, NoneType]` |  | untranscribed | substation transmission interface (co-simulation with a transmission solver) |
| `transmission_level_constant_impedance_load` | `Union[dict, Complex, NoneType]` |  | untranscribed | substation transmission interface (co-simulation with a transmission solver) |
| `distribution_load` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `distribution_power_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `distribution_power_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `distribution_power_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `distribution_voltage_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `distribution_voltage_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `distribution_voltage_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `distribution_voltage_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `distribution_voltage_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `distribution_voltage_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `distribution_current_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `distribution_current_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `distribution_current_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `distribution_real_energy` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |


#### triplex_node

| TriplexNode field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, TriplexNodeName]` | `house`, `trip_node1`, `trip_node10` | copied | `ConnectivityNode.mRID`, `ConnectivityNode.name`; root buses only; a child bus is its root's node (GLM-4) |
| `parent` | `Optional[str]` | `R1-12-47-3_tm_1` | structural | a bus whose parent is a bus is solved as the root of its parent chain: no node of its own; its name is listed on the root's row (GLM-4) |
| `groupid` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `latitude` | `Optional[str]` |  | untranscribed | home: the location shape (EquipmentLocation); mapped when a deck sets it |
| `longitude` | `Optional[str]` |  | untranscribed | home: the location shape (EquipmentLocation); mapped when a deck sets it |
| `in_svc` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `out_svc` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `rank` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `flags` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `phases` | `Optional[str]` | `BS`, `CS`, `AS` | structural | a child's phase conductors must be a subset of its root's; on a swing bus, EnergySource.phases (blank when ABC) |
| `nominal_voltage` | `Optional[float]` | `120.09`, `120.0` | structural | checked against the walk's kV on the bus's system (line_voltage); a disagreement over 10 % is listed in bus.cimtbl, not written (GLM-1). On a swing bus: EnergySource.nominalVoltage, derived by line_voltage |
| `inrush_integration_method` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `condition` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `solution` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `bustype` | `Union[str, ForwardRef('Bustype'), NoneType]` |  | structural | SWING: an EnergySource row (source.cimtbl). PQ, PV, SWING_PQ: a plain bus. SWING_PQ only turns into a swing when islanded |
| `busflags` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `reference_bus` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `maximum_voltage_error` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `voltage_1` | `Union[dict, Complex, NoneType]` | `Complex({'real': -60.0, 'imag': -103....` | derived | on a SWING bus only: EnergySource voltageMagnitude = line_voltage(|V|) and voltageAngle = arg(V) in degrees; elsewhere the solver's initial guess |
| `voltage_2` | `Union[dict, Complex, NoneType]` | `Complex({'real': -60.0, 'imag': -103....` | untranscribed | the solver's initial guess |
| `voltage_N` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.0, 'imag': 0.0})` | untranscribed | the solver's initial guess |
| `voltage_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `voltage_1N` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `voltage_2N` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `prerotated_current_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `prerotated_current_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `prerotated_current_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `deltamode_generator_current_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_PGenTotal` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_full_Y_matrix` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_full_Y_all_matrix` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `NR_powerflow_parent` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `residential_nominal_current_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_1_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_1_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_2_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_2_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_12_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_12_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `current_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_N` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_12` | `Union[dict, Complex, NoneType]` | `Complex({'real': 175181.0364, 'imag':...` | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `house_present` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `Norton_dynamic` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `Norton_dynamic_child` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `generator_dynamic` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `reset_disabled_island_state` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `GFA_enable` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_low_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_high_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_low_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_high_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_reconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_disconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_disconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_status` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_trip_method` | `Union[str, ForwardRef('GfaTripMethod'), NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `service_status` | `Union[str, ForwardRef('ServiceStatus'), NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `service_status_double` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `previous_uptime` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `current_uptime` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `topological_parent` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `behaving_as_swing` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `frequency_measure_type` | `Union[str, ForwardRef('FrequencyMeasureType'), NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `sfm_Tf` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `pll_Kp` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `pll_Ki` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `measured_angle_1` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_1` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_angle_2` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_2` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_angle_12` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_12` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |


#### triplex_meter

| TriplexMeter field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, TriplexMeterName]` | `house_pvmtr`, `house_stmtr`, `trip_meter1` | copied | `ConnectivityNode.mRID`, `ConnectivityNode.name`; root buses only; a child bus is its root's node (GLM-4) |
| `parent` | `Optional[str]` | `house` | structural | a bus whose parent is a bus is solved as the root of its parent chain: no node of its own; its name is listed on the root's row (GLM-4) |
| `groupid` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `latitude` | `Optional[str]` |  | untranscribed | home: the location shape (EquipmentLocation); mapped when a deck sets it |
| `longitude` | `Optional[str]` |  | untranscribed | home: the location shape (EquipmentLocation); mapped when a deck sets it |
| `in_svc` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `out_svc` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `rank` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `flags` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `phases` | `Optional[str]` | `BS`, `CS`, `AS` | structural | a child's phase conductors must be a subset of its root's; on a swing bus, EnergySource.phases (blank when ABC) |
| `nominal_voltage` | `Optional[float]` | `120.09`, `120.0` | structural | checked against the walk's kV on the bus's system (line_voltage); a disagreement over 10 % is listed in bus.cimtbl, not written (GLM-1). On a swing bus: EnergySource.nominalVoltage, derived by line_voltage |
| `inrush_integration_method` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `condition` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `solution` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `bustype` | `Union[str, ForwardRef('Bustype'), NoneType]` |  | structural | SWING: an EnergySource row (source.cimtbl). PQ, PV, SWING_PQ: a plain bus. SWING_PQ only turns into a swing when islanded |
| `busflags` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `reference_bus` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `maximum_voltage_error` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `voltage_1` | `Union[dict, Complex, NoneType]` | `Complex({'real': -60.0, 'imag': -103....` | derived | on a SWING bus only: EnergySource voltageMagnitude = line_voltage(|V|) and voltageAngle = arg(V) in degrees; elsewhere the solver's initial guess |
| `voltage_2` | `Union[dict, Complex, NoneType]` | `Complex({'real': -60.0, 'imag': -103....` | untranscribed | the solver's initial guess |
| `voltage_N` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.0, 'imag': 0.0})` | untranscribed | the solver's initial guess |
| `voltage_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `voltage_1N` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `voltage_2N` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `prerotated_current_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `prerotated_current_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `prerotated_current_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `deltamode_generator_current_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_PGenTotal` | `Union[dict, Complex, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_full_Y_matrix` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `deltamode_full_Y_all_matrix` | `Optional[str]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `NR_powerflow_parent` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `residential_nominal_current_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_1_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_1_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_2_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_2_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_12_real` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `residential_nominal_current_12_imag` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `current_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_N` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `current_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `power_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `shunt_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | a load on the bus (constant power, current or impedance): load slice S4a; until then listed, never set silently |
| `house_present` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `Norton_dynamic` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `Norton_dynamic_child` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `generator_dynamic` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `reset_disabled_island_state` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `GFA_enable` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_low_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_high_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_low_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_high_trip` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_reconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_freq_disconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_volt_disconnect_time` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_status` | `Union[bool, Bool, NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `GFA_trip_method` | `Union[str, ForwardRef('GfaTripMethod'), NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `service_status` | `Union[str, ForwardRef('ServiceStatus'), NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `service_status_double` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `previous_uptime` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `current_uptime` | `Optional[float]` |  | untranscribed | object metadata with no network-profile home |
| `topological_parent` | `Optional[str]` |  | untranscribed | object metadata with no network-profile home |
| `behaving_as_swing` | `Union[bool, Bool, NoneType]` |  | untranscribed | object metadata with no network-profile home |
| `frequency_measure_type` | `Union[str, ForwardRef('FrequencyMeasureType'), NoneType]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `sfm_Tf` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `pll_Kp` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `pll_Ki` | `Optional[float]` |  | untranscribed | dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips) |
| `measured_angle_1` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_1` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_angle_2` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_2` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_angle_12` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency_12` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_frequency` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_energy` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_energy_delta` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_energy` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_energy_delta` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_energy_delta_timestep` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_power` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `indiv_measured_power_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `indiv_measured_power_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `indiv_measured_power_N` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_demand` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_power` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_power` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `meter_power_consumption` | `Union[dict, Complex, NoneType]` |  | untranscribed | metering and billing |
| `measured_voltage_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_voltage_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_voltage_N` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_voltage_1_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_voltage_2_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_voltage_12_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_imag_max_voltage_1_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_imag_max_voltage_2_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_imag_max_voltage_12_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_voltage_1_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_voltage_2_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_voltage_12_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_imag_min_voltage_1_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_imag_min_voltage_2_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_imag_min_voltage_12_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_voltage_1_mag_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_voltage_2_mag_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_voltage_12_mag_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_max_power_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_max_power_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_real_min_power_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_reactive_min_power_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_real_power_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_avg_reactive_power_in_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_stats_interval` | `Optional[float]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_current_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_current_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `measured_current_N` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver state and outputs: the initial guess and the solution, not the network |
| `customer_interrupted` | `Union[bool, Bool, NoneType]` |  | untranscribed | metering and billing |
| `customer_interrupted_secondary` | `Union[bool, Bool, NoneType]` |  | untranscribed | metering and billing |
| `sustained_count` | `Optional[int]` |  | untranscribed | metering and billing |
| `momentary_count` | `Optional[int]` |  | untranscribed | metering and billing |
| `total_count` | `Optional[int]` |  | untranscribed | metering and billing |
| `s_flag` | `Optional[int]` |  | untranscribed | metering and billing |
| `t_flag` | `Optional[int]` |  | untranscribed | metering and billing |
| `pre_load` | `Union[dict, Complex, NoneType]` |  | untranscribed | metering and billing |
| `monthly_bill` | `Optional[float]` |  | untranscribed | metering and billing |
| `previous_monthly_bill` | `Optional[float]` |  | untranscribed | metering and billing |
| `previous_monthly_energy` | `Optional[float]` |  | untranscribed | metering and billing |
| `monthly_fee` | `Optional[float]` |  | untranscribed | metering and billing |
| `monthly_energy` | `Optional[float]` |  | untranscribed | metering and billing |
| `bill_mode` | `Union[str, ForwardRef('BillMode'), NoneType]` |  | untranscribed | metering and billing |
| `power_market` | `Optional[str]` |  | untranscribed | metering and billing |
| `bill_day` | `Optional[int]` |  | untranscribed | metering and billing |
| `price` | `Optional[float]` |  | untranscribed | metering and billing |
| `price_base` | `Optional[float]` |  | untranscribed | metering and billing |
| `first_tier_price` | `Optional[float]` |  | untranscribed | metering and billing |
| `first_tier_energy` | `Optional[float]` |  | untranscribed | metering and billing |
| `second_tier_price` | `Optional[float]` |  | untranscribed | metering and billing |
| `second_tier_energy` | `Optional[float]` |  | untranscribed | metering and billing |
| `third_tier_price` | `Optional[float]` |  | untranscribed | metering and billing |
| `third_tier_energy` | `Optional[float]` |  | untranscribed | metering and billing |


## S2: catalogs (approved 2026-11-09 with S2-3 amended)

S2 maps the conductor, spacing and line configuration catalogs: six artifacts, one per native table (D4), in the
plan's section 2 order. Samples and counts come from the census of all 29 decks (28 read; IEEE123_transactive stops
at read). GridLAB-D citations are to the C++ source (`powerflow/`, the checkout the schema was scraped from).

| # | artifact | native class (records in the decks) | CIM | mRID |
|---|---|---|---|---|
| 2 | `overhead_line_conductor.cimtbl` | overhead_line_conductor (163) | `OverheadWireInfo` | `ohc_<name>` |
| 2 | `underground_line_conductor.cimtbl` | underground_line_conductor (91) | `ConcentricNeutralCableInfo` (84), `TapeShieldCableInfo` (6), `OverheadWireInfo` (1, a bare wire; S2-5) | `ugc_<name>` |
| 2 | `triplex_line_conductor.cimtbl` | triplex_line_conductor (25) | `OverheadWireInfo` | `tpc_<name>` |
| 3 | `line_spacing.cimtbl` | line_spacing (238) | `ConductorDistanceSpacing` + `ConductorDistance` (S2-2) | `spc_<name>` |
| 4 | `line_configuration.cimtbl` | line_configuration: 722 by spacing + conductors, 20 by z-matrix | `WireConfiguration` + `WireSequenceConfiguration`, or `PerLengthPhaseImpedance` + `PhaseImpedanceData` | `wc_<name>`, `lc_<name>` |
| 4 | `triplex_line_configuration.cimtbl` | triplex_line_configuration (25, all by conductors) | `WireConfiguration` + a derived `ConductorDistanceSpacing` (S2-8) | `wc_<name>`, `wc_<name>_spc` |

**Identity (all six):** prefix + the GLM name in source case (D3, GLM names are case-sensitive), never sanitized
(`tpc_triplex_4/0 AA` is a quoted cell, I8). An unnamed object is `<class>:<id>` (S0), so
`ohc_overhead_line_conductor:3`. One prefix per native class: GLM names are unique across a model, so they cannot
collide. Child rows: `<parent mRID>_<letter>` (`spc_602_ABCN_AB`, `wc_lcon_601_2_A`, `lc_lcon_mtx601_ABC_21`).

**Untranscribed on every catalog class:** the object header (`parent`, `groupid`, `latitude`, `longitude`,
`in_svc`, `out_svc`, `rank`, `flags`): a catalog object has no place or service state. Listed per row
(`# untranscribed: ...`) when set, as the DSS catalogs do.

### Conductors

```
# GridLAB-D overhead_line_conductor -> OverheadWireInfo (catalog).
Table OperationalLimitSet: mRID
    ohc_wire_acsr_556_5_limits
Table CurrentLimit: mRID, normalValue (A), OperationalLimitType, OperationalLimitSet
    ohc_wire_acsr_556_5_norm,  730.0, olt_normal,    ohc_wire_acsr_556_5_limits
    ohc_wire_acsr_556_5_emerg, 730.0, olt_emergency, ohc_wire_acsr_556_5_limits
Table OverheadWireInfo: mRID, name, gmr (ft), rAC50 (ohm/mi), radius (in), ratedCurrent (A), OperationalLimitSet
    ohc_wire_acsr_556_5, wire_acsr_556_5, 0.0311, 0.18972, 0.4635, 730.0, ohc_wire_acsr_556_5_limits  # derived: radius = diameter / 2
```

| GLM slot | kind | target |
|---|---|---|
| `name` | copied | `name`; mRID = prefix + name |
| `geometric_mean_radius` (overhead, triplex), `conductor_gmr` (underground) | copied | `gmr (ft)` |
| `resistance` (overhead, triplex), `conductor_resistance` (underground) | copied | `rAC50 (ohm/mi)` (S2-6) |
| `diameter` (overhead), `conductor_diameter` (underground) | derived | `radius = diameter / 2` (in) |
| `outer_diameter` | copied | CN, TS: `diameterOverJacket (in)`; on a bare wire untranscribed (no jacket; the Java exporter writes 1.2 x diameter there, `canBury`) |
| `neutral_strands` | copied | CN `neutralStrandCount`; also selects the class (S2-5) |
| `neutral_gmr` | copied | CN `neutralStrandGmr (ft)` |
| `neutral_diameter` | derived | CN `neutralStrandRadius = neutral_diameter / 2` (in) |
| `neutral_resistance` | copied | CN `neutralStrandRDC20 (ohm/mi)` (the strand's DC value, as the Java exporter reads it) |
| `shield_thickness` | copied | TS `tapeThickness (in)`; also selects the class (S2-5) |
| `shield_diameter` | copied | TS `diameterOverScreen (in)` (the Java exporter writes it from there) |
| `shield_gmr`, `shield_resistance` | untranscribed | no CIM home; Kersting derives both from the screen diameter and tape thickness (eq. 4.89), and the Java exporter does. The taxonomy CN cables write `0.00` |
| `insulation_relative_permitivitty` | untranscribed | no `CableInfo` home (as DSS `EpsR`); GridLAB-D default 1.0, the Java exports write 2.3 |
| `rating.summer.continuous` | copied | `ratedCurrent (A)`, and the normal `CurrentLimit` of the wire's AssetInfo `OperationalLimitSet` (D9, as DSS `normamps`) |
| `rating.summer.emergency` | structural | the emergency `CurrentLimit` of that set |
| `rating.winter.continuous`, `rating.winter.emergency` | untranscribed | equal to summer in every deck that sets them; a different value raises (S2-7) |

### Line spacings (S2-2, S2-3, S2-4)

```
# GridLAB-D line_spacing -> ConductorDistanceSpacing + ConductorDistance (catalog). The distances are copied as
# written; GLM gives no coordinates. Positions 1..n over the phases the distances name (fromPhase/toPhase);
# a height is a distance to earth.
Object ConductorDistanceSpacing: mRID=spc_spc_604_ACN, name=spc_604_ACN, isTemplate=true
Table ConductorDistance: mRID, ConductorDistanceSpacing=spc_spc_604_ACN, sequenceNumber1, conductorKind1, fromPhase, sequenceNumber2, conductorKind2, toPhase, distance (ft)
    spc_spc_604_ACN_AC, 1, phase,   A, 2, phase,   C, 7.0
    spc_spc_604_ACN_AN, 1, phase,   A, 3, neutral, N, 5.6569
    spc_spc_604_ACN_CN, 2, phase,   C, 3, neutral, N, 5.0
    spc_spc_604_ACN_AE, 1, phase,   A,  , earth,    , 28.0
    spc_spc_604_ACN_CE, 2, phase,   C,  , earth,    , 28.0
    spc_spc_604_ACN_NE, 3, neutral, N,  , earth,    , 24.0
```

| GLM slot | kind | target |
|---|---|---|
| `name` | copied | `ConductorDistanceSpacing.name`; `isTemplate = true` |
| `distance_AB`, `_AC`, `_BC`, `_AN`, `_BN`, `_CN` | structural | one `ConductorDistance` each: `distance` in the written unit (`in` on 224 spacings, `ft` on 14; one table per unit), ends numbered and phased by S2-3, kind `phase` or `neutral`. Unset or 0: no row (S2-4) |
| `distance_AE`, `_BE`, `_CE`, `_NE` | structural | the conductor's height: a `ConductorDistance` to a position of kind `earth`, no second sequence number (the G5 getter convention). Only IEEE13_assets sets them |

### Line configurations (S2-9)

```
# geometry: spacing + conductors
Object WireConfiguration: mRID=wc_lcon_604_1, name=lcon_604_1, numberOfPhases=2, WireSpacing=spc_spc_604_ACN
Table WireSequenceConfiguration: mRID, WireConfiguration=wc_lcon_604_1, sequenceNumber, WireInfo
    wc_lcon_604_1_A, 1, ohc_wire_acsr_1/0
    wc_lcon_604_1_C, 2, ohc_wire_acsr_1/0
    wc_lcon_604_1_N, 3, ohc_wire_acsr_1/0

# matrix: z11..z33
Object PerLengthPhaseImpedance: mRID=lc_lcon_mtx604_AC, name=lcon_mtx604_AC, conductorCount=2, calculatedFrequency (Hz)=60.0
Table PhaseImpedanceData: identifier, PhaseImpedance=lc_lcon_mtx604_AC, row, column, r (ohm/mi), x (ohm/mi), b (nS/mi)
    lc_lcon_mtx604_AC_11, 1, 1, 1.3238, 1.3569, 0.0  # A
    lc_lcon_mtx604_AC_21, 2, 1, 0.2066, 0.4591, 0.0  # C-A (z31)
    lc_lcon_mtx604_AC_22, 2, 2, 1.3294, 1.3471, 0.0  # C (z33)
```

| GLM slot | kind | target |
|---|---|---|
| `name` | copied | `WireConfiguration.name` or `PerLengthPhaseImpedance.name` |
| `spacing` | structural | `WireConfiguration.WireSpacing = spc_<spacing>` |
| `conductor_A`, `_B`, `_C`, `_N` | structural | one `WireSequenceConfiguration` each, `sequenceNumber` 1..n in ABCN order (S2-3), equal to its spacing's position for the same phase, `WireInfo` = the conductor's mRID (its class gives the prefix); `numberOfPhases` = the phase conductors set |
| `z11` .. `z33` | structural | form selection; one `PhaseImpedanceData` per lower-triangle element: `r`, `x` = the real and imaginary parts (ohm/mi). Rows and columns are compacted in letter order (CIM: 1 to `conductorCount`), so `z31` of an AC code is row 2, column 1 |
| `c11` .. `c33` | derived | `b = 2 pi f c` (`cimhub_core.derived.capacitance.b_from_c`): nF/mi gives nS/mi, f the base frequency (`powerflow::nominal_frequency`, which GridLAB-D uses); `calculatedFrequency` = f. CIM's `PhaseImpedanceData` has no capacitance, so GLM-11's "c verbatim" is amended. Unset with its z set: GridLAB-D's 0 (`create()`), `# defaulted` |
| `rating.*` | structural | not on the template (D9): the S3a line mapper puts it on each line's own `OperationalLimitSet` (1 triplex configuration sets it) |

### Triplex line configurations (S2-8)

```
# derived: D12 = diameter + 2 insulation_thickness, D1N = D2N = diameter + insulation_thickness (triplex_line.cpp:386)
Object ConductorDistanceSpacing: mRID=wc_triplex_line_configuration:1_spc, name=triplex_line_configuration:1, isTemplate=true
Table ConductorDistance: mRID, ConductorDistanceSpacing=wc_triplex_line_configuration:1_spc, sequenceNumber1, conductorKind1, sequenceNumber2, conductorKind2, distance (in)
    wc_triplex_line_configuration:1_spc_12, 1, phase, 2, phase,   0.682
    wc_triplex_line_configuration:1_spc_1N, 1, phase, 3, neutral, 0.602
    wc_triplex_line_configuration:1_spc_2N, 2, phase, 3, neutral, 0.602
Object WireConfiguration: mRID=wc_triplex_line_configuration:1, name=triplex_line_configuration:1, numberOfPhases=2, WireSpacing=wc_triplex_line_configuration:1_spc
Table WireSequenceConfiguration: ...  sequenceNumber 1 (conductor_1), 2 (conductor_2), 3 (conductor_N); the spacing's phases s1, s2, N
```

| GLM slot | kind | target |
|---|---|---|
| `conductor_1`, `conductor_2`, `conductor_N` | structural | `WireSequenceConfiguration` 1, 2, 3 (GridLAB-D keeps N in its phase C slot, `triplex_line_configuration.cpp:35`); all three required (`triplex_line.cpp` throws) |
| `diameter`, `insulation_thickness` | derived | the spacing's three distances, in their written unit (in); `triplex_spacing`, cited formula. The exporter inverts it: t = D12 - D1N, d = 2 D1N - D12 |
| `spacing`, `conductor_A` .. `_C` | structural | inherited from line_configuration and not read by GridLAB-D's triplex line: set raises |
| `z11`, `z12`, `z21`, `z22` | structural | no readable deck sets them: set raises until one does |

### Fail fast (S2)

| condition | why |
|---|---|
| a conductor without its GMR or resistance | GridLAB-D takes 0, and ln(1/GMR) fails |
| an underground conductor with both `neutral_strands` and `shield_thickness` | two cable kinds |
| a winter rating that differs from summer | no season home is mapped (S2-7) |
| a configuration with neither form, or with both z and conductors | GridLAB-D uses the matrix when any diagonal is set (`underground_line.cpp:162`); GLM-11 amended (S2-9) |
| spacing without conductors, or conductors without spacing | `overhead_line.cpp:120` throws |
| a configuration whose phases differ from the phases its spacing's distances name | S2-3 |
| a conductor or spacing reference to no object, or to the wrong class (a triplex conductor on a line_configuration) | |
| an off-diagonal z without both diagonals, or `z_ij` != `z_ji` | none in the decks |
| a triplex configuration whose D12 or D1N is not positive | `triplex_line.cpp:390` throws |

### Decisions for S2

| # | question | recommendation |
|---|---|---|
| S2-1 | Files and identity | **approved:** The six artifacts above, prefixes `ohc_`, `ugc_`, `tpc_`, `spc_`, `wc_`, `lc_`, source case |
| S2-2 | Spacing form | **approved:** **`ConductorDistanceSpacing`, not `XYSpacing`** (amends plan section 2 and the `conductor-geometry` skill's GLM row). GLM gives distances and heights, not coordinates: 224 of 238 spacings have no heights, and the taxonomy's are not planar (57.6 in between phases, 84 in from each phase to the neutral). Copied verbatim, it stays geometry and needs no derivation. The core G5 getters already read it |
| S2-3 | Position numbers | **Amended by the user:** the phasing goes on the GridAPPS-D extensions `ConductorDistance.fromPhase`/`toPhase` (A, B, C, N; triplex s1, s2, N; blank for earth), and the sequence numbers are compact, 1..n in ABCN order over the phases the spacing's written distances name, as OpenDSS numbers a `LineSpacing` (a line attaches position k to its k-th bus node, so DSS needs no C 3, N 4). A configuration numbers its conductors the same way over its own phases, and the two must agree: in all 28 readable decks every configuration's phases equal its spacing's (663) or the spacing has no distances (59 configurations on the 4 all-zero spacings). A disagreement raises. Matrices compact the same way (S2-9) |
| S2-4 | Zero distances | **approved:** GridLAB-D reads 0 as no mutual term (`DIST` in `overhead_line.cpp`, `Z_DIST` in `underground_line.cpp`), the same as unset; in CIM a 0 distance would be two coincident conductors. Not written; listed on the row (`# 0 (GridLAB-D: no coupling): AB, AC`). 30 spacings, 4 of them all zero (taxonomy underground spacings), which become spacings with no distances |
| S2-5 | Underground conductor kinds | **approved:** `neutral_strands` > 0: `ConcentricNeutralCableInfo`; `shield_thickness` > 0: `TapeShieldCableInfo`; neither: `OverheadWireInfo` (IEEE13_assets `ugwire_cu_1/0`, the bare 607 neutral the Java exporter re-emitted as an underground conductor; it matches the DSS import's WireData). One table per class in the one file |
| S2-6 | Resistance | **approved:** `resistance` / `conductor_resistance` to `rAC50`: Kersting's 50 C AC tables, and the Java exporter writes GLM resistance from `rAC50`. The DSS importer writes `Rac` to `rAC25`, so the IEEE13_assets comparison (GLM-16) lists that difference |
| S2-7 | Conductor ratings | **approved:** Summer continuous and emergency as written (D9). **Unset ratings are not filled** (an exception to GLM-3): GridLAB-D's `create()` constants (1000/2000 A overhead and underground, 202/212.1 A triplex) aren't the conductor's rating, and 156 taxonomy conductors set only `summer.continuous`, so a defaulted 2000 A emergency limit would sit on a 120 A conductor. The row lists the unset ones. Winter: untranscribed while it equals summer, raises otherwise |
| S2-8 | Triplex geometry (GLM-12, amended) | **approved:** A derived `ConductorDistanceSpacing` per triplex configuration (GridLAB-D's formula, which is Kersting's), not an `XYSpacing`. The triplex conductors become `OverheadWireInfo` (CIM has no triplex class; the insulation is on the configuration, and all 25 use one conductor for 1, 2 and N). GLM-12's z-matrix cross-check is dropped: the only triplex z-matrix is in IEEE123_transactive, which stops at read; the atom pins the formula |
| S2-9 | Matrix configurations (GLM-11, amended) | **approved:** As GLM-11, with b derived from c (above), rows compacted, and both forms on one record raising (none in the decks), since GridLAB-D would use the matrix |
| S2-10 | Field tables | **approved:** Generated from the mappers' `FIELDS` with `fields_table` once built, as S1-6 |

**Expected differences from the DSS import of the same models (GLM-16):** the IEEE13_cdpsm matrices match the DSS
`linecode.cimtbl` r and x, but its five overhead configurations carry c = 0 (the Java exporter wrote no overhead
capacitance), and their names are per phasing (`lcon_mtx604_AC`, `lcon_mtx603_CB`). IEEE13_assets: `rAC50` vs
`rAC25`; the spacings are distances, not XY (the same distances); the CN cable has no insulation diameters.

**Owed by core (exporter wave):** `getters.spacing.get_spacing_distances` raises when a conductor has no height,
and 224 GLM spacings and every triplex spacing have none. Distances do not need heights, so a GLM round trip needs
that check moved to `get_spacing_xy`. Plan section 7.

### Built (2026-11-09)

- `importer/cimtbl/catalog.py` (object header, ratings, references, the master's `OperationalLimitType` table),
  `conductor.py` (`map_conductors`, `info_class`), `spacing.py` (`map_line_spacing`, `spacing_statements`),
  `configuration.py` (`map_line_configuration`, `map_triplex_line_configuration`, `triplex_spacing`), wired into
  `MAPPING_ORDER` and `CLASSIFIED`. `glm_schema.registry_unit` spells GridLAB-D's `Ohm` units for the CIM unit
  registry (`Ohm/mile` is `ohm/mile`); the number stays as written.
- The master now declares `olt_normal` and `olt_emergency` (as the DSS master), which the conductor limits name.
- `PhaseImpedanceData` is keyed by `identifier` (it is not an IdentifiedObject in CIM 18), as in the shape.
- Atom `tests/atoms/catalog/catalog.glm` (every form: rated and taxonomy overhead conductors, CN, TS and bare
  underground, spacings with heights, with an inch unit and a zero, geometry by alias, a mixed cable assembly, a
  2-phase matrix, triplex) with one golden per part; golden `tests/goldens/IEEE13_cdpsm/line_configuration.cimtbl`;
  `tests/test_cimtbl_catalog.py` (classification, the formula and its inverse, the atom bound and read back through
  the core spacing getters, 11 fail-fast cases, and a sweep that counts every catalog object on every deck).
- Every deck that binds S1 binds S2: 27 of 29, the same two deck defects.

### Field tables (generated: `fields_table(cls, records, fields=...)`, samples from tests/decks)

#### overhead_line_conductor

| OverheadLineConductor field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, OverheadLineConductorName]` | `wire_acsr_1/0`, `wire_acsr_4/0`, `wire_acsr_556_5` | copied | `OverheadWireInfo.name`; mRID = ohc_ + name |
| `parent` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `groupid` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `latitude` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `longitude` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `in_svc` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `out_svc` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `rank` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `flags` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `geometric_mean_radius` | `Optional[float]` | `0.00446`, `0.00814`, `0.0311` | copied | `OverheadWireInfo.gmr` ({unit}); unset raises |
| `resistance` | `Optional[float]` | `1.1424`, `0.60384`, `0.18972` | copied | `OverheadWireInfo.rAC50` ({unit}); Kersting's 50 C AC value, which the Java exporter writes from rAC50 (S2-6); unset raises |
| `diameter` | `Optional[float]` | `0.398`, `0.563`, `0.927` | derived | `OverheadWireInfo.radius` ({unit}); radius = diameter / 2 (radius_from_diameter), in the diameter's unit |
| `rating_summer_continuous` | `Optional[float]` | `230.0`, `340.0`, `730.0` | copied | `OverheadWireInfo.ratedCurrent` (A); also the normal CurrentLimit of the wire's AssetInfo OperationalLimitSet <mRID>_limits. Unset: GridLAB-D's create() constant is not filled (S2-7) |
| `rating_summer_emergency` | `Optional[float]` | `230.0`, `340.0`, `730.0` | structural | the emergency CurrentLimit of that set; unset: not filled (S2-7) |
| `rating_winter_continuous` | `Optional[float]` | `230.0`, `340.0`, `730.0` | untranscribed | equal to summer in every deck that sets it; a different value raises (no season is mapped, S2-7) |
| `rating_winter_emergency` | `Optional[float]` | `230.0`, `340.0`, `730.0` | untranscribed | equal to summer in every deck that sets it; a different value raises (no season is mapped, S2-7) |

#### underground_line_conductor

| UndergroundLineConductor field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, UndergroundLineConductorName]` | `cncab_cn_250`, `tscab_ts_1/0`, `ugwire_cu_1/0` | copied | `OverheadWireInfo.name`, `ConcentricNeutralCableInfo.name`, `TapeShieldCableInfo.name`; mRID = ugc_ + name |
| `parent` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `groupid` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `latitude` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `longitude` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `in_svc` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `out_svc` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `rank` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `flags` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `outer_diameter` | `Optional[float]` | `1.29`, `1.06`, `0.4416` | copied | `ConcentricNeutralCableInfo.diameterOverJacket` ({unit}), `TapeShieldCableInfo.diameterOverJacket` ({unit}); on a bare wire untranscribed (no jacket; the Java exporter writes 1.2 x diameter, canBury) |
| `conductor_gmr` | `Optional[float]` | `0.0171`, `0.0111`, `0.01113` | copied | `OverheadWireInfo.gmr` ({unit}), `ConcentricNeutralCableInfo.gmr` ({unit}), `TapeShieldCableInfo.gmr` ({unit}); unset raises |
| `conductor_diameter` | `Optional[float]` | `0.567`, `0.368`, `1.152` | derived | `OverheadWireInfo.radius` ({unit}), `ConcentricNeutralCableInfo.radius` ({unit}), `TapeShieldCableInfo.radius` ({unit}); radius = diameter / 2 (radius_from_diameter), in the diameter's unit |
| `conductor_resistance` | `Optional[float]` | `0.41`, `0.97`, `0.607` | copied | `OverheadWireInfo.rAC50` ({unit}), `ConcentricNeutralCableInfo.rAC50` ({unit}), `TapeShieldCableInfo.rAC50` ({unit}); Kersting's 50 C AC value, which the Java exporter writes from rAC50 (S2-6); unset raises |
| `neutral_gmr` | `Optional[float]` | `0.00208`, `0.0111`, `0.0842565914341201` | copied | `ConcentricNeutralCableInfo.neutralStrandGmr` ({unit}) |
| `neutral_diameter` | `Optional[float]` | `0.0641`, `0.0640837`, `0.1019` | derived | `ConcentricNeutralCableInfo.neutralStrandRadius` ({unit}); neutralStrandRadius = neutral_diameter / 2 (radius_from_diameter) |
| `neutral_resistance` | `Optional[float]` | `14.8722`, `14.872`, `0.97` | copied | `ConcentricNeutralCableInfo.neutralStrandRDC20` ({unit}); the strand's DC value, as the Java exporter reads it |
| `neutral_strands` | `Optional[int]` | `13`, `6`, `20` | copied | `ConcentricNeutralCableInfo.neutralStrandCount`; > 0 selects the CN class (S2-5) |
| `shield_thickness` | `Optional[float]` | `0.005` | copied | `TapeShieldCableInfo.tapeThickness` ({unit}); > 0 selects the TS class (S2-5) |
| `shield_diameter` | `Optional[float]` | `0.87` | copied | `TapeShieldCableInfo.diameterOverScreen` ({unit}); the Java exporter writes it from diameterOverScreen |
| `insulation_relative_permitivitty` | `Optional[float]` | `2.3` | untranscribed | no CableInfo home (as DSS EpsR); GridLAB-D default 1.0, the Java exports write 2.3 |
| `shield_gmr` | `Optional[float]` | `0.03625`, `0.0` | untranscribed | no CIM home; Kersting derives it from the screen diameter and tape thickness (eq. 4.89), as the Java exporter does. The taxonomy CN cables write 0.00 |
| `shield_resistance` | `Optional[float]` | `4.327833`, `0.0` | untranscribed | no CIM home; Kersting derives it from the screen diameter and tape thickness (eq. 4.89), as the Java exporter does. The taxonomy CN cables write 0.00 |
| `rating_summer_continuous` | `Optional[float]` | `260.0`, `165.0`, `100.0` | copied | `OverheadWireInfo.ratedCurrent` (A), `ConcentricNeutralCableInfo.ratedCurrent` (A), `TapeShieldCableInfo.ratedCurrent` (A); also the normal CurrentLimit of the wire's AssetInfo OperationalLimitSet <mRID>_limits. Unset: GridLAB-D's create() constant is not filled (S2-7) |
| `rating_summer_emergency` | `Optional[float]` | `260.0`, `165.0`, `100.0` | structural | the emergency CurrentLimit of that set; unset: not filled (S2-7) |
| `rating_winter_continuous` | `Optional[float]` | `260.0`, `165.0`, `100.0` | untranscribed | equal to summer in every deck that sets it; a different value raises (no season is mapped, S2-7) |
| `rating_winter_emergency` | `Optional[float]` | `260.0`, `165.0`, `100.0` | untranscribed | equal to summer in every deck that sets it; a different value raises (no season is mapped, S2-7) |

#### triplex_line_conductor

| TriplexLineConductor field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, TriplexLineConductorName]` | `tp_line_conductor`, `triplex_4/0 AA` | copied | `OverheadWireInfo.name`; mRID = tpc_ + name |
| `parent` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `groupid` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `latitude` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `longitude` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `in_svc` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `out_svc` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `rank` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `flags` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `resistance` | `Optional[float]` | `0.97`, `0.48` | copied | `OverheadWireInfo.rAC50` ({unit}); Kersting's 50 C AC value, which the Java exporter writes from rAC50 (S2-6); unset raises |
| `geometric_mean_radius` | `Optional[float]` | `0.0111`, `0.0158` | copied | `OverheadWireInfo.gmr` ({unit}); unset raises |
| `rating_summer_continuous` | `Optional[float]` |  | copied | `OverheadWireInfo.ratedCurrent` (A); also the normal CurrentLimit of the wire's AssetInfo OperationalLimitSet <mRID>_limits. Unset: GridLAB-D's create() constant is not filled (S2-7) |
| `rating_summer_emergency` | `Optional[float]` |  | structural | the emergency CurrentLimit of that set; unset: not filled (S2-7) |
| `rating_winter_continuous` | `Optional[float]` |  | untranscribed | equal to summer in every deck that sets it; a different value raises (no season is mapped, S2-7) |
| `rating_winter_emergency` | `Optional[float]` |  | untranscribed | equal to summer in every deck that sets it; a different value raises (no season is mapped, S2-7) |

#### line_spacing

| LineSpacing field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, LineSpacingName]` | `spc_510_CN`, `spc_601_ABCN`, `spc_602_ABCN` | copied | `ConductorDistanceSpacing.name`; mRID = spc_ + name; isTemplate = true |
| `parent` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `groupid` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `latitude` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `longitude` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `in_svc` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `out_svc` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `rank` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `flags` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `distance_AB` | `Optional[float]` | `3.0`, `0.5`, `2.5` | structural | one ConductorDistance, distance in the written unit; ends numbered 1..n over the spacing's phases (S2-3), fromPhase/toPhase the letters. Unset or 0: no row (S2-4) |
| `distance_BC` | `Optional[float]` | `4.0`, `7.0`, `0.5` | structural | one ConductorDistance, distance in the written unit; ends numbered 1..n over the spacing's phases (S2-3), fromPhase/toPhase the letters. Unset or 0: no row (S2-4) |
| `distance_AC` | `Optional[float]` | `7.0`, `1.0`, `4.5` | structural | one ConductorDistance, distance in the written unit; ends numbered 1..n over the spacing's phases (S2-3), fromPhase/toPhase the letters. Unset or 0: no row (S2-4) |
| `distance_AN` | `Optional[float]` | `5.6569`, `0.25`, `4.272002` | structural | one ConductorDistance, distance in the written unit; ends numbered 1..n over the spacing's phases (S2-3), fromPhase/toPhase the letters. Unset or 0: no row (S2-4) |
| `distance_BN` | `Optional[float]` | `4.1231`, `5.0`, `5.656854` | structural | one ConductorDistance, distance in the written unit; ends numbered 1..n over the spacing's phases (S2-3), fromPhase/toPhase the letters. Unset or 0: no row (S2-4) |
| `distance_CN` | `Optional[float]` | `5.0249`, `5.0`, `5.6569` | structural | one ConductorDistance, distance in the written unit; ends numbered 1..n over the spacing's phases (S2-3), fromPhase/toPhase the letters. Unset or 0: no row (S2-4) |
| `distance_AE` | `Optional[float]` | `28.0`, `-4.0` | structural | the conductor's height: a ConductorDistance to a position of kind earth, no second sequence number or phase. Unset or 0: no row (S2-4) |
| `distance_BE` | `Optional[float]` | `28.0`, `-4.0` | structural | the conductor's height: a ConductorDistance to a position of kind earth, no second sequence number or phase. Unset or 0: no row (S2-4) |
| `distance_CE` | `Optional[float]` | `29.0`, `28.0`, `-4.0` | structural | the conductor's height: a ConductorDistance to a position of kind earth, no second sequence number or phase. Unset or 0: no row (S2-4) |
| `distance_NE` | `Optional[float]` | `24.0`, `-4.0` | structural | the conductor's height: a ConductorDistance to a position of kind earth, no second sequence number or phase. Unset or 0: no row (S2-4) |

#### line_configuration

| LineConfiguration field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, LineConfigurationName]` | `lcon_mtx601_ABC`, `lcon_mtx602_ABC`, `lcon_mtx603_CB` | copied | `WireConfiguration.name`, `PerLengthPhaseImpedance.name`; mRID = wc_ or lc_ + name |
| `parent` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `groupid` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `latitude` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `longitude` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `in_svc` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `out_svc` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `rank` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `flags` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `conductor_A` | `Optional[str]` | `wire_acsr_556_5`, `wire_acsr_4/0`, `wire_acsr_1/0` | structural | geometry: one WireSequenceConfiguration, sequenceNumber 1..n in ABCN order (S2-3), WireInfo = the conductor's mRID; numberOfPhases = the A, B, C conductors set |
| `conductor_B` | `Optional[str]` | `wire_acsr_556_5`, `wire_acsr_4/0`, `wire_acsr_1/0` | structural | geometry: one WireSequenceConfiguration, sequenceNumber 1..n in ABCN order (S2-3), WireInfo = the conductor's mRID; numberOfPhases = the A, B, C conductors set |
| `conductor_C` | `Optional[str]` | `wire_acsr_1/0`, `wire_acsr_556_5`, `wire_acsr_4/0` | structural | geometry: one WireSequenceConfiguration, sequenceNumber 1..n in ABCN order (S2-3), WireInfo = the conductor's mRID; numberOfPhases = the A, B, C conductors set |
| `conductor_N` | `Optional[str]` | `wire_acsr_1/0`, `wire_acsr_4/0`, `ugwire_cu_1/0` | structural | geometry: one WireSequenceConfiguration, sequenceNumber 1..n in ABCN order (S2-3), WireInfo = the conductor's mRID; numberOfPhases = the A, B, C conductors set |
| `spacing` | `Optional[str]` | `spc_510_CN`, `spc_601_ABCN`, `spc_602_ABCN` | structural | geometry: WireConfiguration.WireSpacing = spc_ + spacing |
| `z11` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.3465, 'imag': 1.01...`, `Complex({'real': 0.7526, 'imag': 1.18...`, `Complex({'real': 1.3238, 'imag': 1.35...` | structural | matrix: one PhaseImpedanceData per lower-triangle element, r and x the real and imaginary parts; rows and columns compacted in ABC order; z_ij must equal z_ji |
| `z12` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.1535, 'imag': 0.38...`, `Complex({'real': 0.318476, 'imag': 0....`, `Complex({'real': 0.5198, 'imag': 0.27...` | structural | matrix: one PhaseImpedanceData per lower-triangle element, r and x the real and imaginary parts; rows and columns compacted in ABC order; z_ij must equal z_ji |
| `z13` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.158, 'imag': 0.4236})`, `Complex({'real': 0.156, 'imag': 0.5017})`, `Complex({'real': 0.2066, 'imag': 0.45...` | structural | matrix: one PhaseImpedanceData per lower-triangle element, r and x the real and imaginary parts; rows and columns compacted in ABC order; z_ij must equal z_ji |
| `z21` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.1535, 'imag': 0.38...`, `Complex({'real': 0.318476, 'imag': 0....`, `Complex({'real': 0.5198, 'imag': 0.27...` | structural | matrix: one PhaseImpedanceData per lower-triangle element, r and x the real and imaginary parts; rows and columns compacted in ABC order; z_ij must equal z_ji |
| `z22` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.3375, 'imag': 1.04...`, `Complex({'real': 0.7475, 'imag': 1.19...`, `Complex({'real': 1.3294, 'imag': 1.34...` | structural | matrix: one PhaseImpedanceData per lower-triangle element, r and x the real and imaginary parts; rows and columns compacted in ABC order; z_ij must equal z_ji |
| `z23` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.156, 'imag': 0.5017})`, `Complex({'real': 0.158, 'imag': 0.4236})`, `Complex({'real': 0.2066, 'imag': 0.45...` | structural | matrix: one PhaseImpedanceData per lower-triangle element, r and x the real and imaginary parts; rows and columns compacted in ABC order; z_ij must equal z_ji |
| `z31` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.158, 'imag': 0.4236})`, `Complex({'real': 0.156, 'imag': 0.5017})`, `Complex({'real': 0.2066, 'imag': 0.45...` | structural | matrix: one PhaseImpedanceData per lower-triangle element, r and x the real and imaginary parts; rows and columns compacted in ABC order; z_ij must equal z_ji |
| `z32` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.156, 'imag': 0.5017})`, `Complex({'real': 0.158, 'imag': 0.4236})`, `Complex({'real': 0.2066, 'imag': 0.45...` | structural | matrix: one PhaseImpedanceData per lower-triangle element, r and x the real and imaginary parts; rows and columns compacted in ABC order; z_ij must equal z_ji |
| `z33` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.3414, 'imag': 1.03...`, `Complex({'real': 0.7436, 'imag': 1.21...`, `Complex({'real': 1.3238, 'imag': 1.35...` | structural | matrix: one PhaseImpedanceData per lower-triangle element, r and x the real and imaginary parts; rows and columns compacted in ABC order; z_ij must equal z_ji |
| `c11` | `Optional[float]` | `0.0`, `383.948`, `236.0` | derived | matrix: PhaseImpedanceData b = 2 pi f c (b_from_c), nF gives nS, f the base frequency (also calculatedFrequency). Unset with its z set: GridLAB-D's 0, defaulted |
| `c12` | `Optional[float]` | `0.0`, `-4.8592`, `-3.0889` | derived | matrix: PhaseImpedanceData b = 2 pi f c (b_from_c), nF gives nS, f the base frequency (also calculatedFrequency). Unset with its z set: GridLAB-D's 0, defaulted |
| `c13` | `Optional[float]` | `0.0`, `-1.852`, `-4.8592` | derived | matrix: PhaseImpedanceData b = 2 pi f c (b_from_c), nF gives nS, f the base frequency (also calculatedFrequency). Unset with its z set: GridLAB-D's 0, defaulted |
| `c21` | `Optional[float]` | `0.0`, `-4.8592`, `-3.0889` | derived | matrix: PhaseImpedanceData b = 2 pi f c (b_from_c), nF gives nS, f the base frequency (also calculatedFrequency). Unset with its z set: GridLAB-D's 0, defaulted |
| `c22` | `Optional[float]` | `0.0`, `383.948`, `2.8` | derived | matrix: PhaseImpedanceData b = 2 pi f c (b_from_c), nF gives nS, f the base frequency (also calculatedFrequency). Unset with its z set: GridLAB-D's 0, defaulted |
| `c23` | `Optional[float]` | `0.0`, `-0.6`, `-3.0889` | derived | matrix: PhaseImpedanceData b = 2 pi f c (b_from_c), nF gives nS, f the base frequency (also calculatedFrequency). Unset with its z set: GridLAB-D's 0, defaulted |
| `c31` | `Optional[float]` | `0.0`, `-1.852`, `-4.8592` | derived | matrix: PhaseImpedanceData b = 2 pi f c (b_from_c), nF gives nS, f the base frequency (also calculatedFrequency). Unset with its z set: GridLAB-D's 0, defaulted |
| `c32` | `Optional[float]` | `0.0`, `-0.6`, `-3.0889` | derived | matrix: PhaseImpedanceData b = 2 pi f c (b_from_c), nF gives nS, f the base frequency (also calculatedFrequency). Unset with its z set: GridLAB-D's 0, defaulted |
| `c33` | `Optional[float]` | `0.0`, `383.948`, `2.8` | derived | matrix: PhaseImpedanceData b = 2 pi f c (b_from_c), nF gives nS, f the base frequency (also calculatedFrequency). Unset with its z set: GridLAB-D's 0, defaulted |
| `rating_summer_continuous` | `Optional[float]` |  | structural | not on the template (D9): the S3a line mapper puts it on each line's own OperationalLimitSet |
| `rating_summer_emergency` | `Optional[float]` |  | structural | not on the template (D9): the S3a line mapper puts it on each line's own OperationalLimitSet |
| `rating_winter_continuous` | `Optional[float]` |  | structural | not on the template (D9): the S3a line mapper puts it on each line's own OperationalLimitSet |
| `rating_winter_emergency` | `Optional[float]` |  | structural | not on the template (D9): the S3a line mapper puts it on each line's own OperationalLimitSet |

#### triplex_line_configuration

| TriplexLineConfiguration field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, TriplexLineConfigurationName]` | `triplex_line_configuration_1`, `triplex_line_configuration:1` | copied | `WireConfiguration.name`; mRID = wc_ + name; its spacing wc_<name>_spc |
| `parent` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `groupid` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `latitude` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `longitude` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `in_svc` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `out_svc` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `rank` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `flags` | `Optional[str]` |  | untranscribed | object header: a catalog object has no place or service state |
| `conductor_A` | `Optional[str]` |  | structural | inherited from line_configuration and not read by GridLAB-D's triplex line: set raises |
| `conductor_B` | `Optional[str]` |  | structural | inherited from line_configuration and not read by GridLAB-D's triplex line: set raises |
| `conductor_C` | `Optional[str]` |  | structural | inherited from line_configuration and not read by GridLAB-D's triplex line: set raises |
| `conductor_N` | `Optional[str]` | `tp_line_conductor`, `triplex_4/0 AA` | structural | WireSequenceConfiguration 3 (spacing phase N; GridLAB-D keeps it in its phase C slot); required |
| `spacing` | `Optional[str]` |  | structural | inherited from line_configuration and not read by GridLAB-D's triplex line: set raises |
| `z11` | `Union[dict, Complex, NoneType]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `z12` | `Union[dict, Complex, NoneType]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `z13` | `Union[dict, Complex, NoneType]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `z21` | `Union[dict, Complex, NoneType]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `z22` | `Union[dict, Complex, NoneType]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `z23` | `Union[dict, Complex, NoneType]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `z31` | `Union[dict, Complex, NoneType]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `z32` | `Union[dict, Complex, NoneType]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `z33` | `Union[dict, Complex, NoneType]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `c11` | `Optional[float]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `c12` | `Optional[float]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `c13` | `Optional[float]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `c21` | `Optional[float]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `c22` | `Optional[float]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `c23` | `Optional[float]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `c31` | `Optional[float]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `c32` | `Optional[float]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `c33` | `Optional[float]` |  | structural | no readable deck sets a triplex matrix: set raises until one does |
| `rating_summer_continuous` | `Optional[float]` |  | structural | not on the template (D9): the S3a line mapper puts it on each line's own OperationalLimitSet |
| `rating_summer_emergency` | `Optional[float]` |  | structural | not on the template (D9): the S3a line mapper puts it on each line's own OperationalLimitSet |
| `rating_winter_continuous` | `Optional[float]` |  | structural | not on the template (D9): the S3a line mapper puts it on each line's own OperationalLimitSet |
| `rating_winter_emergency` | `Optional[float]` |  | structural | not on the template (D9): the S3a line mapper puts it on each line's own OperationalLimitSet |
| `conductor_1` | `Optional[str]` | `tp_line_conductor`, `triplex_4/0 AA` | structural | WireSequenceConfiguration 1 (spacing phase s1); required |
| `conductor_2` | `Optional[str]` | `tp_line_conductor`, `triplex_4/0 AA` | structural | WireSequenceConfiguration 2 (spacing phase s2); required |
| `insulation_thickness` | `Optional[float]` | `0.08` | derived | see diameter |
| `diameter` | `Optional[float]` | `0.368`, `0.522` | derived | the spacing's distances (triplex_spacing): D12 = diameter + 2 insulation_thickness, D1N = D2N = diameter + insulation_thickness |

## S3a: lines and switches (approved 2026-11-09)

S3a maps the branches that are not transformers or regulators: the three line classes and the switching devices,
six artifacts, one per native table (D4), in the plan's section 2 order (rows 8 and 9). Counts are from the 28
readable decks (IEEE123_transactive stops at read); samples from the decks named. GridLAB-D citations are to the C++
source (`powerflow/`).

| # | artifact | native class (records) | CIM | mRID |
|---|---|---|---|---|
| 8 | `overhead_line.cimtbl` | overhead_line (7,306) | `ACLineSegment`: by `WireConfiguration` (7,176) or `PerLengthPhaseImpedance` (130) | `ln_<name>` |
| 8 | `underground_line.cimtbl` | underground_line (4,278) | `ACLineSegment` by `WireConfiguration` (4,245 CN, 33 TS) | `ln_<name>` |
| 8 | `triplex_line.cimtbl` | triplex_line (7,507) | `ACLineSegment` by `WireConfiguration`, phases `s1s2N` | `ln_<name>` |
| 9 | `switch.cimtbl` | switch (580) | `LoadBreakSwitch` | `sw_<name>` |
| 9 | `fuse.cimtbl` | fuse (1,599) | `Fuse` | `sw_<name>` |
| 9 | `recloser.cimtbl` | recloser (35) | `Recloser` | `sw_<name>` |

Shapes: `line_by_wire_configuration`, `line_by_impedance` (ratings on the instance), `switch`. No shape change.

**Identity (S3a-1):** prefix + the GLM name in source case, as S2. The three line classes share `ln_` and the
switching devices share `sw_` (the `switch` shape's rule, so a class change keeps the mRID); GLM names are unique
across a model, so nothing collides. Limits: `<mRID>_limits`, `<mRID>_norm`, `<mRID>_emerg`, as DSS.

**Ends:** `node1` = `from`, `node2` = `to`, each the root bus of its object (GLM-4): 30 lines and switches start on
a child node (15 underground lines, 10 switches, 4 overhead lines, 1 recloser), which GridLAB-D solves as its root.
`BaseVoltage` is the walk's at `node1`; `EquipmentContainer` the feeder.

### Lines

```
# IEEE13_cdpsm: a matrix configuration; GLM phases are a set, so CB is written in ABC order
Table ACLineSegment: mRID, name, node1, node2, phases, length (ft), PerLengthImpedance, BaseVoltage, EquipmentContainer=fdr_IEEE13_cdpsm
    ln_line_632645, line_632645, 632, 645, BC, 500.0, lc_lcon_mtx603_CB, bv_4p16kv
Table OperationalLimitSet: mRID, Equipment
    ln_line_632645_limits, ln_line_632645
Table CurrentLimit: mRID, normalValue (A), OperationalLimitType, OperationalLimitSet
    ln_line_632645_norm,  230.0, olt_normal,    ln_line_632645_limits
    ln_line_632645_emerg, 600.0, olt_emergency, ln_line_632645_limits

# orig_R1-12.47-3: geometry; ACLineSegmentPhase A, C, N are 1, 2, 3, the positions of its spacing (S2-3)
Table ACLineSegment: mRID, name, node1, node2, phases, length (ft), WireConfiguration, BaseVoltage, EquipmentContainer=fdr_orig_R1-12.47-3
    ln_R1-12-47-3_ol_2, R1-12-47-3_ol_2, R1-12-47-3_node_4, R1-12-47-3_node_5, ACN, 68.936, wc_line_configuration:19, bv_12p47kv

# triplex: s1, s2, N are 1, 2, 3, the derived spacing's positions (S2-8)
    ln_R1-12-47-3_tl_1, R1-12-47-3_tl_1, R1-12-47-3_tn_1, R1-12-47-3_tm_1, s1s2N, 30.0, wc_triplex_line_configuration:1, bv_240v  # phases BS
```

| GLM slot | kind | target |
|---|---|---|
| `name` | copied | `ACLineSegment.name`; mRID = `ln_` + name |
| `from`, `to` | structural | `node1`, `node2`: the root bus (GLM-4) |
| `phases` | structural | the `phases` cell, which numbers the ACLineSegmentPhases 1..n in written order (S3a-3) |
| `configuration` | structural | `WireConfiguration = wc_<configuration>` (geometry, triplex) or `PerLengthImpedance = lc_<configuration>` (matrix), by the configuration's form (S2-9) |
| `length` | copied | `length`, in its written unit (ft in every deck); unset raises (GridLAB-D's `create()` 0 is a line of no impedance) |
| `continuous_rating_A`/`_B`/`_C` | structural | the normal `CurrentLimit` of the line's own `OperationalLimitSet` (S3a-4) |
| `emergency_rating_A`/`_B`/`_C` | structural | the emergency `CurrentLimit` of that set |
| `status` | structural | unset or `CLOSED`; `OPEN` raises (a line is not a switch; the walk already raises) |
| `nominal_voltage` | untranscribed | the walk gives the BaseVoltage (GLM-1); no deck sets it on a link |
| `mean_repair_time` | untranscribed | reliability data |
| `power_*`, `current_*`, `fault_*`, `overloaded_status`, `flow_direction`, `triplex_neutral_*_value`, `condition`, `solution` | untranscribed | solver outputs and state |
| `pdispatch`, `pdispatch_offset`, `set_pdispatch` | untranscribed | dispatch control, no network-profile home |
| `inrush_*` | untranscribed | inrush solver settings |
| object header (`parent`, `groupid`, `latitude`, `longitude`, `in_svc`, `out_svc`, `rank`, `flags`) | untranscribed | no deck sets them on a link; listed per row when set |

### Switches, fuses, reclosers

```
# IEEE123: a balanced 3-phase device leaves phases blank (shape switch); GLM has one state, so normalOpen = open
Table LoadBreakSwitch: mRID, name, node1, node2, phases, open, normalOpen, BaseVoltage, EquipmentContainer=fdr_IEEE123
    sw_swt_sw7, swt_sw7, 151, 300, , true, true, bv_4p16kv
    sw_swt_sw8, swt_sw8, 54,  94,  A, true, true, bv_4p16kv
# IEEE13_cdpsm
Table Fuse: mRID, name, node1, node2, phases, ratedCurrent (A), open, normalOpen, BaseVoltage, EquipmentContainer=fdr_IEEE13_cdpsm
    sw_swt_fuse1, swt_fuse1, 633, xf1, , 100.0, false, false, bv_4p16kv
```

| GLM slot | kind | target |
|---|---|---|
| `name`, `from`, `to` | copied, structural | as lines; mRID = `sw_` + name |
| `phases` | structural | the phase conductors, N dropped (S3a-7); `ABC` blank (`phases_cell`) |
| `status` | structural | `open` and `normalOpen` (`OPEN` = true), S3a-6 |
| `phase_A_state`/`_B_`/`_C_` (switch, recloser) | structural | on the device's phases must equal `status`, else raises (S3a-6); on a phase it lacks, untranscribed (the recloser default `CLOSED` the taxonomy writes on all three) |
| `operating_mode` | untranscribed | with every phase state equal to `status`, BANKED and INDIVIDUAL operate the same (`switch_object.cpp:308`) |
| `phase_A_status`/`_B_`/`_C_` (fuse) | structural | unset or `GOOD`; `BLOWN` raises (S3a-6); no deck sets them |
| `current_limit` (fuse) | copied | `Fuse.ratedCurrent (A)` (S3a-8); unset: GridLAB-D's 9999 A (`fuse.cpp:119`, "big current") is not filled, and the row says so |
| `continuous_rating_X`, `emergency_rating_X` | structural | the device's own `OperationalLimitSet`, as lines (S3a-5) |
| `switch_resistance`, `switch_reactance`, `switch_impedance`, `fuse_resistance` | untranscribed | GridLAB-D's numerical stand-in for a closed device (as DSS-8); none set |
| `mean_replacement_time`, `repair_dist_type` (fuse), `mean_repair_time` | untranscribed | reliability data |
| `retry_time`, `max_number_of_tries` (recloser) | untranscribed | protection settings; home `RecloseSequence`, which waits for the protection model as DSS-11 (U15) |
| `number_of_tries` (recloser) | untranscribed | state |
| the link outputs, dispatch, inrush and header slots | untranscribed | as lines |

### Fail fast (S3a)

| condition | why |
|---|---|
| a line without `configuration` or `length`, or with a configuration of the wrong class (a triplex configuration on an overhead line) | `overhead_line.cpp:96`, `:103` throw |
| an overhead line on underground conductors or the reverse; an underground line whose phase cables are not one kind | `overhead_line.cpp:923`, `underground_line.cpp:149` throw; none in the decks |
| a geometry line whose phases are not its configuration's conductors (`ACN` on an `A C N` configuration), or a matrix line whose phases are not its diagonal | the positions must agree (S2-3); GridLAB-D throws on a missing conductor (`test_phases`). All 11,584 agree |
| `D` on any line, `S` on a non-triplex line, a triplex line not `AS`/`BS`/`CS`, or a triplex line whose ends the walk does not put on a split-phase system | none in the decks |
| per-phase ratings that differ; a line's own rating and its configuration's that differ | one limit set per line; none in the decks |
| a switch or recloser phase state that differs from `status` on a phase it has; a `BLOWN` fuse phase | per-phase state needs `SwitchPhase` rows; none in the decks (S3a-6) |
| `status OPEN` on a line, an end that is no bus object | the walk raises (S0) |

### Decisions for S3a

| # | question | decision |
|---|---|---|
| S3a-1 | Files and identity | **approved:** The six artifacts above; `ln_` for every line class, `sw_` for every switching device, source case |
| S3a-2 | Line template | **approved:** The configuration's form decides (S2-9): geometry and triplex give `WireConfiguration`, a matrix gives `PerLengthImpedance`. The line class must match its conductors' class (GridLAB-D throws otherwise); all decks do |
| S3a-3 | Line phases | **approved:** The line's letters in ABC order then N (GLM `phases` is a set: `CB` is `BC`, so matrix row 1 is B, as S2-9 compacts it). It must equal the configuration's conductors (geometry) or diagonal (matrix), so ACLineSegmentPhase k is spacing position k. A triplex line is `s1s2N` whatever its letter (`AS`, `BS`, `CS`): CIM puts the primary phase on the center-tap transformer (S3b); the letter must match its end buses'. **Amended by S6-4:** a matrix line's N is dropped (GridLAB-D's matrix never reads it), and a written 0 diagonal is no phase |
| S3a-4 | Line ratings | **approved:** **The line's own `continuous_rating_X`/`emergency_rating_X`, as written, on its own `OperationalLimitSet` (D9);** else its configuration's `rating.summer.*` (only `triplex_line_configuration:1` of orig_R5-35.00-1, 1200 A, 192 lines); else none. Conductor ratings stay on the WireInfo (S2-7) and are not copied, and GridLAB-D's 1000/2000 A defaults are never filled. Only the three Java exports rate lines (140 lines, always equal across phases). **Note:** GridLAB-D itself replaces a line's written ratings at init, with its conductors' (a running minimum over A, B, C) or, on a matrix configuration, the configuration's (`overhead_line.cpp:133`). The written values are the deck's statement (the Java exports wrote the CIM source's line limits: IEEE13_assets 730/1095 A on 730/730 A conductors), so they are kept. The alternative is to write the engine's effective rating and leave the written ones untranscribed |
| S3a-5 | Switch ratings | **approved:** The same rule as lines: the device's own set (IEEE13_cdpsm, IEEE13_assets, IEEE123: 400/600 A on 12 switches, the fuse and the recloser). GridLAB-D reads no rating on a switch (`link.cpp:681` checks limits on lines and transformers only), and the DSS import drops a switch's ratings as stand-ins (DSS-8), so the alternative is untranscribed |
| S3a-6 | Switch state | **approved:** `status` gives `open`, and `normalOpen` the same (GLM has one state; DSS's rule when no `Normal` is given). Per-phase states that differ raise instead of writing `SwitchPhase` rows: no deck has one (every recloser writes `CLOSED` on all three, status `CLOSED`), so plan section 7's core `switch` per-phase dependency is dropped until a deck needs it. 2 switches are open (IEEE123 `swt_sw7`, `swt_sw8`) |
| S3a-7 | Switch phases | **approved:** The phase conductors, N dropped: GridLAB-D's switch, fuse and recloser have no neutral element, and CIM's `SwitchPhase` is a switched conductor (the DSS import writes none). 568 of 580 switches and 1,598 of 1,599 fuses write N |
| S3a-8 | Fuse rating | **approved:** `current_limit` copied to `ratedCurrent` as written: 1,598 taxonomy fuses write 50000 A (`// 10000` in a trailing comment), a fuse that never blows; IEEE13_cdpsm's is 100 A, as the DSS import |
| S3a-9 | Recloser | **approved:** `Recloser`; its reclosing settings untranscribed until the protection model lands (DSS-11, U15) |
| S3a-10 | Sectionalizer (GLM-10, amended) | **approved:** **Not mapped:** cim18v17 has no `Sectionalizer` class and no deck has one, so it stays on the master's not-mapped list (GLM-14) |
| S3a-11 | Field tables | **approved:** Generated from the mappers' `FIELDS` with `fields_table` once built, as S2-10 |

**Expected differences from the DSS import of IEEE13 (GLM-16):** mRIDs and names carry the Java prefixes
(`ln_line_632645`, `sw_swt_fuse1` vs `ln_632645`, `sw_fuse1`), so the comparison matches by connected nodes. The
`CB` lines are `BC` (DSS writes bus order, `645.3.2`): the same impedance per phase in another row order. The lines
carry an emergency limit (600 A, DSS's default `emergamps` the Java export wrote), which the DSS import does not
fill. With S3a-5, the switches carry 400/600 A limits that the DSS import drops. `swt_brkr1` is a
`LoadBreakSwitch` in both (the Java export's `// CIM Breaker` is a comment, which the reader does not keep).

### Built (2026-11-09)

- `importer/cimtbl/link.py` (the link slots and their untranscribed groups, `classify`, `ends`, `link_ratings`,
  `Limits`), `line.py` (`map_lines`, `LINES`), `switch.py` (`map_switches`, `SWITCHES`), wired into
  `MAPPING_ORDER` and `CLASSIFIED`. `configuration.py` gains `conductor_letters`, `diagonal_letters`, `is_matrix`
  and `template`, which the line mapper reads.
- The schema derives `triplex_line_configuration` from `line_configuration`, so a line's configuration class is
  checked exactly (a triplex configuration on an overhead line raises, as `overhead_line.cpp:103`).
- The S1 atoms' line `l1` now has a configuration (a 3-phase matrix) and phases `ABC`: GridLAB-D needs one, and S3a
  maps the line. Their bus and source goldens are unchanged.
- Atom `tests/atoms/line/line.glm` (on the S2 catalog atom by `#include`: a matrix line written `CA`, a taxonomy
  geometry line in metres, an underground line from a child node, two triplex lines, one on a rated
  configuration, a switch with N and ratings, an open switch, a fuse with and without `current_limit`, a 1-phase
  recloser with three phase states) with one golden per part; goldens `tests/goldens/IEEE13_cdpsm/overhead_line`,
  `switch`, `fuse`, `recloser`; `tests/test_cimtbl_line.py` (classification, the atom bound and read back, 11
  fail-fast cases, and a sweep that counts every line and switching device and checks, on every geometry line,
  that ACLineSegmentPhase k is its spacing's position k).
- Every deck that binds S2 binds S3a: 27 of 29, the same two deck defects; 19,091 segments, 580 switches, 1,599
  fuses, 35 reclosers.

### Field tables (generated: `fields_table(cls, records, fields=...)`, samples from tests/decks and the atom)

Every link class also has these untranscribed groups, left out of the tables: the object header (`parent`,
`groupid`, `latitude`, `longitude`, `in_svc`, `out_svc`, `rank`, `flags`; no deck sets them on a link), solver
outputs and state (`power_*`, `current_*` but `current_limit`, `fault_*`, `overloaded_status`, `flow_direction`,
`triplex_neutral_*_value`, `condition`, `solution`) and inrush solver settings (`inrush_*`).

#### overhead_line

| OverheadLine field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, OverheadLineName]` | `line_632633`, `line_632645`, `line_632670` | copied | `ACLineSegment.name`; mRID = ln_ + name |
| `phases` | `Optional[str]` | `ABC`, `CB`, `AC` | structural | the phases cell: ABC then N, equal to the configuration's conductors (geometry) or diagonal (matrix); s1s2N on a triplex line (S3a-3) |
| `nominal_voltage` | `Optional[float]` |  | untranscribed | the walk gives the BaseVoltage (GLM-1) |
| `status` | `Optional[str]` |  | structural | unset or CLOSED; OPEN raises (the walk: a line is not a switch) |
| `from_node` | `Optional[str]` | `632`, `mid`, `645` | structural | node1: the root bus of the object it names (GLM-4) |
| `to` | `Optional[str]` | `633`, `645`, `670` | structural | node2: the root bus of the object it names (GLM-4) |
| `pdispatch` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `pdispatch_offset` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `set_pdispatch` | `Union[bool, Bool, NoneType]` |  | untranscribed | dispatch control; no network-profile home |
| `mean_repair_time` | `Optional[float]` |  | untranscribed | reliability data |
| `continuous_rating_A` | `Optional[float]` | `340.0`, `730.0`, `230.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_B` | `Optional[float]` | `340.0`, `230.0`, `730.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_C` | `Optional[float]` | `340.0`, `230.0`, `730.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `emergency_rating_A` | `Optional[float]` | `600.0`, `730.0`, `510.0` | structural | the emergency CurrentLimit of that set |
| `emergency_rating_B` | `Optional[float]` | `600.0`, `730.0`, `510.0` | structural | the emergency CurrentLimit of that set |
| `emergency_rating_C` | `Optional[float]` | `600.0`, `730.0`, `510.0` | structural | the emergency CurrentLimit of that set |
| `configuration` | `Optional[str]` | `lcon_mtx602_ABC`, `lcon_mtx603_CB`, `lcon_mtx601_ABC` | structural | WireConfiguration = wc_<configuration> (geometry, triplex) or PerLengthImpedance = lc_<configuration> (matrix), S3a-2 |
| `length` | `Optional[float]` | `500.0`, `667.0`, `300.0` | copied | `ACLineSegment.length` ({unit}); in its written unit; unset raises |


#### underground_line

| UndergroundLine field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, UndergroundLineName]` | `line_684652`, `line_692675`, `GC-12-47-1_ul_1` | copied | `ACLineSegment.name`; mRID = ln_ + name |
| `phases` | `Optional[str]` | `AN`, `ABC`, `ABCN` | structural | the phases cell: ABC then N, equal to the configuration's conductors (geometry) or diagonal (matrix); s1s2N on a triplex line (S3a-3) |
| `nominal_voltage` | `Optional[float]` |  | untranscribed | the walk gives the BaseVoltage (GLM-1) |
| `status` | `Optional[str]` |  | structural | unset or CLOSED; OPEN raises (the walk: a line is not a switch) |
| `from_node` | `Optional[str]` | `684`, `692`, `GC-12-47-1_node_5` | structural | node1: the root bus of the object it names (GLM-4) |
| `to` | `Optional[str]` | `652`, `675`, `GC-12-47-1_node_6` | structural | node2: the root bus of the object it names (GLM-4) |
| `pdispatch` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `pdispatch_offset` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `set_pdispatch` | `Union[bool, Bool, NoneType]` |  | untranscribed | dispatch control; no network-profile home |
| `mean_repair_time` | `Optional[float]` |  | untranscribed | reliability data |
| `continuous_rating_A` | `Optional[float]` | `165.0`, `260.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_B` | `Optional[float]` | `260.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_C` | `Optional[float]` | `260.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `emergency_rating_A` | `Optional[float]` | `247.5`, `390.0` | structural | the emergency CurrentLimit of that set |
| `emergency_rating_B` | `Optional[float]` | `390.0` | structural | the emergency CurrentLimit of that set |
| `emergency_rating_C` | `Optional[float]` | `390.0` | structural | the emergency CurrentLimit of that set |
| `configuration` | `Optional[str]` | `lcon_607_4`, `lcon_606_0`, `line_configuration:6` | structural | WireConfiguration = wc_<configuration> (geometry, triplex) or PerLengthImpedance = lc_<configuration> (matrix), S3a-2 |
| `length` | `Optional[float]` | `800.0`, `500.0`, `340.889` | copied | `ACLineSegment.length` ({unit}); in its written unit; unset raises |


#### triplex_line

| TriplexLine field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, TriplexLineName]` | `R1-12-47-3_tl_1`, `tl_1`, `tl_2` | copied | `ACLineSegment.name`; mRID = ln_ + name |
| `phases` | `Optional[str]` | `BS`, `AS` | structural | the phases cell: ABC then N, equal to the configuration's conductors (geometry) or diagonal (matrix); s1s2N on a triplex line (S3a-3) |
| `nominal_voltage` | `Optional[float]` |  | untranscribed | the walk gives the BaseVoltage (GLM-1) |
| `status` | `Optional[str]` |  | structural | unset or CLOSED; OPEN raises (the walk: a line is not a switch) |
| `from_node` | `Optional[str]` | `R1-12-47-3_tn_1`, `tn1` | structural | node1: the root bus of the object it names (GLM-4) |
| `to` | `Optional[str]` | `R1-12-47-3_tm_1`, `tm1`, `tm2` | structural | node2: the root bus of the object it names (GLM-4) |
| `pdispatch` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `pdispatch_offset` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `set_pdispatch` | `Union[bool, Bool, NoneType]` |  | untranscribed | dispatch control; no network-profile home |
| `mean_repair_time` | `Optional[float]` |  | untranscribed | reliability data |
| `continuous_rating_A` | `Optional[float]` |  | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_B` | `Optional[float]` |  | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_C` | `Optional[float]` |  | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `emergency_rating_A` | `Optional[float]` |  | structural | the emergency CurrentLimit of that set |
| `emergency_rating_B` | `Optional[float]` |  | structural | the emergency CurrentLimit of that set |
| `emergency_rating_C` | `Optional[float]` |  | structural | the emergency CurrentLimit of that set |
| `configuration` | `Optional[str]` | `triplex_line_configuration:1`, `tc_rated` | structural | WireConfiguration = wc_<configuration> (geometry, triplex) or PerLengthImpedance = lc_<configuration> (matrix), S3a-2 |
| `length` | `Optional[float]` | `30.0` | copied | `ACLineSegment.length` ({unit}); in its written unit; unset raises |


#### switch

| Switch field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, SwitchName]` | `swt_671692`, `swt_brkr1`, `swt_sect1` | copied | `LoadBreakSwitch.name`; mRID = sw_ + name |
| `phases` | `Optional[str]` | `ABC`, `C`, `A` | structural | the switched conductors A, B, C, N dropped; ABC is blank (S3a-7) |
| `nominal_voltage` | `Optional[float]` |  | untranscribed | the walk gives the BaseVoltage (GLM-1) |
| `status` | `Optional[str]` | `CLOSED`, `OPEN` | structural | open and normalOpen (OPEN = true); unset: GridLAB-D's CLOSED, defaulted (S3a-6) |
| `from_node` | `Optional[str]` | `671`, `650`, `684` | structural | node1: the root bus of the object it names (GLM-4) |
| `to` | `Optional[str]` | `692`, `brkr`, `tap` | structural | node2: the root bus of the object it names (GLM-4) |
| `pdispatch` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `pdispatch_offset` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `set_pdispatch` | `Union[bool, Bool, NoneType]` |  | untranscribed | dispatch control; no network-profile home |
| `mean_repair_time` | `Optional[float]` |  | untranscribed | reliability data |
| `continuous_rating_A` | `Optional[float]` | `400.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_B` | `Optional[float]` | `400.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_C` | `Optional[float]` | `400.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `emergency_rating_A` | `Optional[float]` | `600.0` | structural | the emergency CurrentLimit of that set |
| `emergency_rating_B` | `Optional[float]` | `600.0` | structural | the emergency CurrentLimit of that set |
| `emergency_rating_C` | `Optional[float]` | `600.0` | structural | the emergency CurrentLimit of that set |
| `phase_A_state` | `Optional[str]` |  | structural | on the device's phases must equal status, else raises (S3a-6); on a phase it lacks, listed on the row |
| `phase_B_state` | `Optional[str]` |  | structural | on the device's phases must equal status, else raises (S3a-6); on a phase it lacks, listed on the row |
| `phase_C_state` | `Optional[str]` |  | structural | on the device's phases must equal status, else raises (S3a-6); on a phase it lacks, listed on the row |
| `operating_mode` | `Optional[str]` |  | untranscribed | with every phase state equal to status, BANKED and INDIVIDUAL operate the same (switch_object.cpp:308) |
| `switch_impedance` | `Union[dict, Complex, NoneType]` |  | untranscribed | GridLAB-D's numerical stand-in for a closed device (as DSS-8) |
| `switch_resistance` | `Optional[float]` |  | untranscribed | GridLAB-D's numerical stand-in for a closed device (as DSS-8) |
| `switch_reactance` | `Optional[float]` |  | untranscribed | GridLAB-D's numerical stand-in for a closed device (as DSS-8) |


#### fuse

| Fuse field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, FuseName]` | `swt_fuse1`, `GC-12-47-1_fuse_1`, `GC-12-47-1_fuse_2` | copied | `Fuse.name`; mRID = sw_ + name |
| `phases` | `Optional[str]` | `ABC`, `ABCN`, `AN` | structural | the switched conductors A, B, C, N dropped; ABC is blank (S3a-7) |
| `nominal_voltage` | `Optional[float]` |  | untranscribed | the walk gives the BaseVoltage (GLM-1) |
| `status` | `Optional[str]` | `CLOSED` | structural | open and normalOpen (OPEN = true); unset: GridLAB-D's CLOSED, defaulted (S3a-6) |
| `from_node` | `Optional[str]` | `633`, `GC-12-47-1_node_11`, `GC-12-47-1_node_16` | structural | node1: the root bus of the object it names (GLM-4) |
| `to` | `Optional[str]` | `xf1`, `GC-12-47-1_node_12`, `GC-12-47-1_node_15` | structural | node2: the root bus of the object it names (GLM-4) |
| `pdispatch` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `pdispatch_offset` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `set_pdispatch` | `Union[bool, Bool, NoneType]` |  | untranscribed | dispatch control; no network-profile home |
| `mean_repair_time` | `Optional[float]` |  | untranscribed | reliability data |
| `continuous_rating_A` | `Optional[float]` | `400.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_B` | `Optional[float]` | `400.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_C` | `Optional[float]` | `400.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `emergency_rating_A` | `Optional[float]` | `600.0` | structural | the emergency CurrentLimit of that set |
| `emergency_rating_B` | `Optional[float]` | `600.0` | structural | the emergency CurrentLimit of that set |
| `emergency_rating_C` | `Optional[float]` | `600.0` | structural | the emergency CurrentLimit of that set |
| `phase_A_status` | `Optional[str]` |  | structural | unset or GOOD; BLOWN raises on a phase the fuse has (S3a-6) |
| `phase_B_status` | `Optional[str]` |  | structural | unset or GOOD; BLOWN raises on a phase the fuse has (S3a-6) |
| `phase_C_status` | `Optional[str]` |  | structural | unset or GOOD; BLOWN raises on a phase the fuse has (S3a-6) |
| `repair_dist_type` | `Optional[str]` |  | untranscribed | reliability data |
| `current_limit` | `Optional[float]` | `100.0`, `50000.0` | copied | `Fuse.ratedCurrent` ({unit}); S3a-8; unset: GridLAB-D's 9999 A (fuse.cpp:119) is not filled, the row says so |
| `mean_replacement_time` | `Optional[float]` | `3600.0`, `1000.0` | untranscribed | reliability data |
| `fuse_resistance` | `Optional[float]` |  | untranscribed | GridLAB-D's numerical stand-in for a closed device (as DSS-8) |


#### recloser

| Recloser field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, RecloserName]` | `swt_rec1`, `recloser_1` | copied | `Recloser.name`; mRID = sw_ + name |
| `phases` | `Optional[str]` | `ABC`, `CN` | structural | the switched conductors A, B, C, N dropped; ABC is blank (S3a-7) |
| `nominal_voltage` | `Optional[float]` |  | untranscribed | the walk gives the BaseVoltage (GLM-1) |
| `status` | `Optional[str]` | `CLOSED` | structural | open and normalOpen (OPEN = true); unset: GridLAB-D's CLOSED, defaulted (S3a-6) |
| `from_node` | `Optional[str]` | `632`, `n1` | structural | node1: the root bus of the object it names (GLM-4) |
| `to` | `Optional[str]` | `mid`, `n10` | structural | node2: the root bus of the object it names (GLM-4) |
| `pdispatch` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `pdispatch_offset` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `set_pdispatch` | `Union[bool, Bool, NoneType]` |  | untranscribed | dispatch control; no network-profile home |
| `mean_repair_time` | `Optional[float]` |  | untranscribed | reliability data |
| `continuous_rating_A` | `Optional[float]` | `400.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_B` | `Optional[float]` | `400.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_C` | `Optional[float]` | `400.0` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `emergency_rating_A` | `Optional[float]` | `600.0` | structural | the emergency CurrentLimit of that set |
| `emergency_rating_B` | `Optional[float]` | `600.0` | structural | the emergency CurrentLimit of that set |
| `emergency_rating_C` | `Optional[float]` | `600.0` | structural | the emergency CurrentLimit of that set |
| `phase_A_state` | `Optional[str]` | `CLOSED` | structural | on the device's phases must equal status, else raises (S3a-6); on a phase it lacks, listed on the row |
| `phase_B_state` | `Optional[str]` | `CLOSED` | structural | on the device's phases must equal status, else raises (S3a-6); on a phase it lacks, listed on the row |
| `phase_C_state` | `Optional[str]` | `CLOSED` | structural | on the device's phases must equal status, else raises (S3a-6); on a phase it lacks, listed on the row |
| `operating_mode` | `Optional[str]` | `INDIVIDUAL` | untranscribed | with every phase state equal to status, BANKED and INDIVIDUAL operate the same (switch_object.cpp:308) |
| `switch_impedance` | `Union[dict, Complex, NoneType]` |  | untranscribed | GridLAB-D's numerical stand-in for a closed device (as DSS-8) |
| `switch_resistance` | `Optional[float]` |  | untranscribed | GridLAB-D's numerical stand-in for a closed device (as DSS-8) |
| `switch_reactance` | `Optional[float]` |  | untranscribed | GridLAB-D's numerical stand-in for a closed device (as DSS-8) |
| `retry_time` | `Optional[float]` | `1.0` | untranscribed | protection setting; home RecloseSequence, which waits for the protection model (DSS-11, U15) |
| `max_number_of_tries` | `Optional[float]` | `3.0` | untranscribed | protection setting; see retry_time |
| `number_of_tries` | `Optional[float]` | `0.0` | untranscribed | state |

## S3b: transformers (approved 2026-11-09 with the user's S3b-1, -4, -5, -9; built 2026-11-09)

S3b maps `transformer_configuration` to templates and `transformer` to instances by template (GLM-6), in plan
section 2 rows 5 and 10. Counts are from the 28 readable decks: 1,469 configurations, 1,459 of them used, and
8,943 transformers. GridLAB-D citations are to `powerflow/transformer.cpp` and `transformer_configuration.cpp`.

| # | artifact | native class (records) | CIM | mRID |
|---|---|---|---|---|
| 5 | `transformer_configuration.cimtbl` | transformer_configuration (1,469) | `TransformerTankConfiguration`: by `TransformerTankEnd` (a three-phase tank), by `TransformerLug` (a center tap, a one-phase can, and each can of a bank), and `TransformerBankConfiguration` over a bank's cans | `xc_<name>`, `xb_<name>` |
| 10 | `transformer.cimtbl` | transformer (8,943) | `PowerTransformer` + its `TransformerTank`s by template + a `PowerTransformerEnd` per side | `xf_<name>` |

Shapes: `transformer_template`, `transformer_template_1ph`, `transformer_by_template`, and the CIMTBL-Models bank
(`distribution/templates/bank_oyod_50_50_7200_12470y.cimtbl`). No shape change: the impedance is the configuration's nameplate
`percentImpedance`, `loadLoss`, `noLoadLoss` and `percentMagnetizingCurrent`, as the CIMTBL-Models templates.

**What the decks hold.**

| connect_type | instances | phases | voltages as written | kVA | GridLAB-D's impedance base |
|---|---:|---|---|---|---|
| `SINGLE_PHASE_CENTER_TAPPED` | 7,508 | `AS` 2,394, `BS` 2,467, `CS` 2,647 | primary = the coil (phase to neutral: 7216.88, 2400), secondary = a half (120) | the instance phase's `powerX_rating` | primary V² / phase kVA, half V² / phase kVA (`:788`, `:1003` for NR) |
| `WYE_WYE` | 1,432 | `ABCN` 721, 2-phase 130, 1-phase 581 | line to line on every phase count (12500/480 on a `CN` can) | `power_rating` (or the phase sum), the whole unit | `secondary_voltage`² / `power_rating` (`:266`) |
| `DELTA_GWYE` | 2 | `ABCN`, `ABC` | line to line | the whole unit | as `WYE_WYE` |
| `DELTA_DELTA` | 1 | `ABCN` | line to line | the whole unit | as `WYE_WYE` |

`WYE_WYE` phase kVAs, by instance: 1,170 rate every wired phase equally (or rate none: GridLAB-D splits
`power_rating` evenly, `init():190`); 145 rate every wired phase but unequally (22 2-phase, 123 3-phase:
`transformer_configuration:1226` of orig_R2-12.47-1, 37.5 + 25 + 25 kVA); 117 leave a wired phase at 0 or unset
(8 2-phase, 109 3-phase: 15 / 0 / 0 kVA on `ABCN`). GridLAB-D reads only the total on a `WYE_WYE` (`:266`). No
configuration is used by instances of different phase counts; 10 `WYE_WYE` configurations have no instance.
24 decks solve by NR, 4 by FBS.

**Identity (S3b-1):** `xc_<configuration>`, `xb_<configuration>` (a bank), `xf_<transformer>`, the GLM name in
source case, as S2 and S3a. Children as the DSS import: `xc_<c>_end_<n>`, `xc_<c>_wdg_<n>`, `xc_<c>_mesh_<ij>`,
`xc_<c>_lug_<h1>`; a bank's cans `xc_<c>_<phase>` (`xc_transformer_configuration:1226_A`); `xf_<t>_tank` (one
tank, unnamed: it goes by its transformer's name) or `xf_<t>_tank_<phase>` (a bank, named `<t>_<phase>`: each can is
a unit of its own on export), `xf_<t>_<n>` (ends), `xf_<t>_<n>_<phase>` (phase ends), `xf_<t>_limits`.

### Templates (`transformer_configuration.cimtbl`)

**Every configuration is written (S3b-1)**, used or not. A template is the configuration as its instances wire it,
so where an instance says more (a center tap's primary system, which phases a bank's cans sit on), every
instance of one configuration must say the same, else it raises. A configuration with no instance is built from
its own phase ratings (none rated: three phases, as `init():190`); an unused center tap leaves its primary
`ratedU` unset (no instance says its system), and none is in the decks.

Three forms (S3b-2). **`TransformerTankEnd` is for three-phase templates only; a single-phase one is
`TransformerLug`s, its instance `TransformerPhaseEnd`s** (the user's rule, 2026-11-19, S3b-13):

- **A three-phase tank by tank ends** (a `WYE_WYE` on three phases rated equally, or not every one rated;
  `DELTA_GWYE`, `DELTA_DELTA`): a `TransformerTankEnd` per winding (`connectionKind` Y or D) and a
  `TransformerWinding` each, with ratings; the impedance is the configuration's %Z fields (S3b-5).
- **Lugged cans**, one per wired phase: a `WYE_WYE` or `SINGLE_PHASE` on one phase (one can, `xc_<c>`) or two (a
  bank), or on three all rated with different kVAs (a bank, S3b-9). A bank is a `TransformerBankConfiguration`
  `xb_<c>` and one `TransformerTankConfiguration` per can `xc_<c>_<label>` (`BankConfiguration = xb_<c>`), as the
  CIMTBL-Models open-wye bank; its instance a tank per can, `<transformer>_<phase>`. A can has lugs H1, H2, X1, X2
  and windings H1→H2, X1→X2; a lug's `sequenceNumber` is the conductor it lands on, numbered over the unit: end
  1's phases then N, then end 2's (`ABCN`: H side A B C N = 1-4, X side 5-8; can A's H1, H2, X1, X2 = 1, 4, 5, 8;
  one can 1-4). Cans rated unequally are labelled and sized by their phases; otherwise they share `power_rating`
  equally, as GridLAB-D runs them, and are labelled by place (`_1`, `_2`), since one template serves instances on
  any phases (the walk collapses an unrated template's letters to a count). The instance's phase ends carry its
  own phases.
- **A center tap by lugs**: H1, H2, X1, X3, X2 (sequence 1-5) with windings H1→H2, X1→X2 (s1→N), X2→X3 (N→s2),
  as the DSS import, with ratings; its %Z fields are the full winding's, which GridLAB-D splits into its star
  (below).

```
# orig_R1-12.47-1: a CN can, 12500/480 V as written (line to line), 75 kVA, z = 0.00133+0.00667j and shunt
# 443.91+424.448j on 480² / 75 kVA, i.e. 3 x on the can's own nameplate (S3b-4)
Table TransformerTankConfiguration: mRID, name, percentImpedance (percent), loadLoss (kW), noLoadLoss (kW), percentMagnetizingCurrent (percent)
    xc_transformer_configuration:3730, transformer_configuration:3730, 2.0404, 0.29925, 0.05632, 0.07853
Table TransformerTankEnd: mRID, TankConfiguration, endNumber, connectionKind
    xc_transformer_configuration:3730_end_1, xc_transformer_configuration:3730, 1, Y
    xc_transformer_configuration:3730_end_2, xc_transformer_configuration:3730, 2, Y
Table TransformerWinding: mRID, TankConfiguration, ratedU (V), baseU (V), ratedS (kVA), baseS (kVA), FromTransformerEnd
    xc_transformer_configuration:3730_wdg_1, ..., 12500.0, 7216.878, 75.0, 75.0, xc_transformer_configuration:3730_end_1
    xc_transformer_configuration:3730_wdg_2, ..., 480.0,   277.128,  75.0, 75.0, xc_transformer_configuration:3730_end_2

# IEEE13_cdpsm xcon_xfm1: 3-phase, GridLAB-D's base is the nameplate: 0.011+0.02j on 500 kVA
    xc_xcon_xfm1, xcon_xfm1, 2.2825, 5.5, , 

# orig_R2-12.47-1: 37.5 + 25 + 25 kVA on ABCN, a bank of three cans (S3b-9); one zt in ohms on every phase, so
# each can's %Z on its own kVA is z x 3 S_can / S_total
Object TransformerBankConfiguration: mRID=xb_transformer_configuration:1226, name=transformer_configuration:1226
Table TransformerTankConfiguration: mRID, name, percentImpedance (percent), loadLoss (kW), noLoadLoss (kW), percentMagnetizingCurrent (percent), BankConfiguration
    xc_transformer_configuration:1226_A, transformer_configuration:1226_A, 0.74863, 0.054964, 0.062059, 0.18261, xb_transformer_configuration:1226
    xc_transformer_configuration:1226_B, transformer_configuration:1226_B, 0.49909, 0.024429, 0.062059, 0.27392, xb_transformer_configuration:1226
    xc_transformer_configuration:1226_C, transformer_configuration:1226_C, 0.49909, 0.024429, 0.062059, 0.27392, xb_transformer_configuration:1226
Table TransformerLug: mRID, TankConfiguration, designation, sequenceNumber
    xc_transformer_configuration:1226_A_lug_h1, xc_transformer_configuration:1226_A, H1, 1
    xc_transformer_configuration:1226_A_lug_h2, xc_transformer_configuration:1226_A, H2, 4
    xc_transformer_configuration:1226_A_lug_x1, xc_transformer_configuration:1226_A, X1, 5
    xc_transformer_configuration:1226_A_lug_x2, xc_transformer_configuration:1226_A, X2, 8
    ...                                                                              # B: 2, 4, 6, 8; C: 3, 4, 7, 8
Table TransformerWinding: mRID, TankConfiguration, ratedU (V), baseU (V), ratedS (kVA), baseS (kVA), FromTransformerLug, ToTransformerLug
    xc_transformer_configuration:1226_A_wdg_1, ..._A, 12470.0, 7199.558, 37.5, 37.5, ..._A_lug_h1, ..._A_lug_h2
    xc_transformer_configuration:1226_A_wdg_2, ..._A, 480.0,   277.128,  37.5, 37.5, ..._A_lug_x1, ..._A_lug_x2
    ...                                                                              # B, C: 25 kVA

# IEEE13_cdpsm xcon_ct5B: its impedance/impedance1/impedance2 are GridLAB-D's split of R = 1.2 %, X = 1.7 %
Table TransformerTankConfiguration: mRID, name, percentImpedance (percent), loadLoss (kW), noLoadLoss (kW), percentMagnetizingCurrent (percent)
    xc_xcon_ct5B, xcon_ct5B, 2.08087, 0.06, 0.01, 0.5
Table TransformerLug: ...                                                            # H1 H2 X1 X3 X2 = 1-5
Table TransformerWinding: mRID, TankConfiguration, ratedU (V), baseU (V), ratedS (kVA), baseS (kVA), FromTransformerLug, ToTransformerLug
    xc_xcon_ct5B_wdg_1, xc_xcon_ct5B, 4156.92, 2400.0, 5.0, 5.0, xc_xcon_ct5B_lug_h1, xc_xcon_ct5B_lug_h2
    xc_xcon_ct5B_wdg_2, xc_xcon_ct5B, 240.0,   120.0,  2.5, 5.0, xc_xcon_ct5B_lug_x1, xc_xcon_ct5B_lug_x2
    xc_xcon_ct5B_wdg_3, xc_xcon_ct5B, 240.0,   120.0,  2.5, 5.0, xc_xcon_ct5B_lug_x2, xc_xcon_ct5B_lug_x3
```

Expanded by the split (below), the center tap equals the DSS import's `xc_ct5` in SI: r 0.6 / 1.2 / 1.2 % and x
2.04 / 2.04 / 1.36 % on 5 kVA.

| GLM slot | kind | target |
|---|---|---|
| `name` | copied | `TransformerTankConfiguration.name` (a bank: `TransformerBankConfiguration.name`, each can `<name>_<phase>`); mRID = `xc_` (`xb_`) + name |
| `connect_type` | structural | the form and connection kinds: `WYE_WYE` Y/Y (on one or two phases lugged cans), `DELTA_GWYE` D/Y, `DELTA_DELTA` D/D (`TransformerTankEnd.connectionKind`; grounding is the instance's); `SINGLE_PHASE_CENTER_TAPPED` lugs; `SINGLE_PHASE` as `WYE_WYE` (S6-2); unset raises |
| `primary_voltage`, `secondary_voltage` | structural | winding `ratedU` and `baseU`, in the written unit (V in every deck), S3b-3 |
| `power_rating`, `powerA_rating`/`_B_`/`_C_` | structural | winding `ratedS`, `baseS` (S3b-3): the whole unit's kVA (`power_rating`, else the phase sum, as `init()`), a can's its phase's when the wired phases are rated unequally, else an equal share; a center tap's is its instance phase's rating. Phase kVAs a one-tank template does not use are listed on the row |
| `impedance`, `resistance`, `reactance` | derived | `percentImpedance` = \|R + jX\| × k × 100 and `loadLoss` = R × k × S (S3b-4, S3b-5); a center tap's are the full winding's |
| `impedance1`, `impedance2` (and their `resistance`/`reactance` forms) | derived | a center tap's star given whole; it must be GridLAB-D's own split of one R + jX (`impedance` = 0.5R + j0.8X, both halves R + j0.4X), which gives the %Z fields; any other split raises (none in the decks), and on any other connection they raise (GridLAB-D ignores them with a warning) |
| `shunt_impedance`, `shunt_resistance`, `shunt_reactance` | derived | `noLoadLoss` = S / (Rsh × k) and `percentMagnetizingCurrent` = 100 / (Xsh × k) (S3b-6); unset: GridLAB-D's 999999999 pu (lossless) is not filled; on a delta connection raises (ignored with a warning) |
| `no_load_loss`, `full_load_loss`, `reactance_resistance_ratio` | structural | raise when set: they replace the impedances on a center tap (`:283`), and no deck sets them |
| `install_type`, `coolant_type`, `cooling_type`, `core_coil_weight`, `tank_fittings_weight`, `oil_volume`, `rated_winding_time_constant`, `rated_winding_hot_spot_rise`, `rated_top_oil_rise`, `installed_insulation_life` | untranscribed | thermal aging model and siting; no network-profile home (as the DSS thermal slots) |
| `magnetization_location`, `inrush_saturation_enabled`, `L_A`, `phi_K`, `phi_M`, `I_M`, `T_D` | untranscribed | inrush model |
| object header | untranscribed | as S2 |

**The tank's own base (S3b-4).** GridLAB-D's per unit is on `secondary_voltage`² / `power_rating` as written
(line to line, the whole unit, `transformer.cpp:266`); CIM's %Z fields are on the tank's own nameplate, per coil.
So every value is GridLAB-D's ohms re-expressed on the tank: `k = 3 × S_coil / S_total`, with `S_coil` the kVA
of one phase coil of the tank (`S_total / n` for one tank of n wye conductors, the can's kVA in a bank). `k` is 1 on
3-phase and delta units, 3 on a 1-phase `WYE_WYE` can, 1.5 on a 2-phase one, and 3 S_can / S_total on a bank's
can. A center tap's base is already its coil (`:784`: primary V² / phase kVA), so `k` = 1.

**Center tap: GridLAB-D's star.** With S the instance phase's rating, GridLAB-D puts `z0 = 0.5 R + j 0.8 X` of
`impedance` on the primary and `z1 = z2 = R + j 0.4 X` on the halves (`transformer.cpp:788`, `:1003` for NR):
the Hopkinson split the CIMTBL-Models pole-mount templates infer from `percentImpedance` and `loadLoss` (mesh 1.5R
+ j1.2X to each half, 2R + j0.8X between them). So the %Z fields carry R + jX and the split is the reader's, as
there. `impedance1`/`impedance2` give the star whole; IEEE13_cdpsm's `xcon_ct5B` (`0.006+0.0136j`, `0.012+0.0068j`
twice) is the split of R = 0.012, X = 0.017.

### Instances (`transformer.cimtbl`)

```
# IEEE13_cdpsm xf_xfm1: ends carry the node, phases and grounding; the values live in the template
Table PowerTransformer: mRID, name, EquipmentContainer=fdr_IEEE13_cdpsm
    xf_xf_xfm1, xf_xfm1
Table TransformerTank: mRID, PowerTransformer, TankConfiguration, EquipmentContainer=fdr_IEEE13_cdpsm
    xf_xf_xfm1_tank, xf_xf_xfm1, xc_xcon_xfm1
Table PowerTransformerEnd: mRID, PowerTransformer, node, phases, endNumber, connectionKind, grounded, BaseVoltage
    xf_xf_xfm1_1, xf_xf_xfm1, xf1, ABCN, 1, Yn, true, bv_4p16kv
    xf_xf_xfm1_2, xf_xf_xfm1, 634, ABCN, 2, Yn, true, bv_480v

# orig_R2-12.47-1 R2-12-47-1_xfmr_115: the bank, a tank per can; the phase ends say which conductor is which
Table TransformerTank: mRID, PowerTransformer, TankConfiguration, EquipmentContainer=fdr_orig_R2-12.47-1
    xf_R2-12-47-1_xfmr_115_tank_A, xf_R2-12-47-1_xfmr_115, xc_transformer_configuration:1226_A
    xf_R2-12-47-1_xfmr_115_tank_B, xf_R2-12-47-1_xfmr_115, xc_transformer_configuration:1226_B
    xf_R2-12-47-1_xfmr_115_tank_C, xf_R2-12-47-1_xfmr_115, xc_transformer_configuration:1226_C
Table PowerTransformerEnd: ...
    xf_R2-12-47-1_xfmr_115_1, ..., ABCN, 1, Yn, true, ...
Table TransformerPhaseEnd: mRID, endNumber, sequenceNumber, phase, Terminal
    xf_R2-12-47-1_xfmr_115_1_A, 1, 1, A, xf_R2-12-47-1_xfmr_115_T1
    ...                                                       # B C N = 2-4; end 2 A B C N = 5-8

# IEEE13_cdpsm xf_tpoletop: values in the template; the DSS import's phase ends B, N, s1, s2, N = 1-5
Table PowerTransformerEnd: mRID, PowerTransformer, node, phases, endNumber, connectionKind, grounded, BaseVoltage
    xf_xf_tpoletop_1, xf_xf_tpoletop, 670,   BN,    1, Y, true, bv_4p16kv
    xf_xf_tpoletop_2, xf_xf_tpoletop, house, s1s2N, 2, I, true, bv_240v
```

| GLM slot | kind | target |
|---|---|---|
| `name` | copied | `PowerTransformer.name`; mRID = `xf_` + name |
| `from`, `to` | structural | end 1 and end 2 `node`: the root bus (GLM-4); each end's `BaseVoltage` is the walk's |
| `phases` | structural | the ends' phases (S3b-7), and a bank's phase ends |
| `configuration` | structural | each `TransformerTank.TankConfiguration` (`xc_<configuration>`, or a bank's `xc_<configuration>_<phase>`); unset or not a `transformer_configuration` raises |
| `status` | structural | unset or `CLOSED`; `OPEN` raises (the walk) |
| `continuous_rating_X`, `emergency_rating_X` | structural | the transformer's own `OperationalLimitSet`, as S3a-5 (S3b-8) |
| `climate`, `ambient_temperature`, `top_oil_hot_spot_temperature`, `winding_hot_spot_temperature`, `percent_loss_of_life`, `aging_constant`, `use_thermal_model`, `transformer_replacement_count`, `aging_granularity` | untranscribed | thermal aging model and its state |
| `phase_X_primary_flux_value`, `phase_X_secondary_flux_value`, `inrush_*` | untranscribed | inrush state and settings |
| the link outputs, dispatch, `nominal_voltage`, `mean_repair_time` and header slots | untranscribed | as S3a |

### Fail fast (S3b)

| condition | why |
|---|---|
| `connect_type` unset; voltages or kVA unset or 0; phase ratings that miss `power_rating` by more than 1 % | `transformer_configuration.cpp:193`, `:211`, `:227`, `:234` throw |
| `resistance` or `reactance` unset or not positive; `impedance` set with a `resistance`/`reactance` that differs | `:337` throws (no lossless unit); the slots are one value |
| `impedance1`/`impedance2` or a shunt on a connection that ignores it; only one of `impedance1`/`impedance2`; `no_load_loss`/`full_load_loss` set | GridLAB-D warns and ignores, or fills in its own; none in the decks |
| a center tap on phases other than one letter + `S`, or whose phase's `powerX_rating` is unset or 0 | `transformer.cpp:772` throws |
| a `WYE_WYE` without N or with S; a delta connection not on `ABC`/`ABCN`; an end the walk does not put on a 3-phase system (center-tap secondary: split-phase) | `transformer.cpp:315` throws on S; the rest is in no deck |
| instances of one configuration that wire it differently (bus systems, phases, so a different template) | one template per configuration |
| per-phase ratings that differ | as S3a |

### Decisions for S3b

| # | question | decision (approved) |
|---|---|---|
| S3b-1 | Files and identity | **The user's: every configuration is written, used or not.** The two artifacts above; `xc_`, `xb_` and `xf_` in source case; children named as the DSS import |
| S3b-2 | Template forms | A three-phase tank by tank ends (a 3-phase `WYE_WYE` equal or not fully rated, the deltas); lugged cans, one (a one-phase wye) or a bank under a `TransformerBankConfiguration` (a two-phase wye, unequal cans, S3b-9); a center tap by lugs H1 H2 X1 X3 X2 (the DSS import's). **Amended by S3b-13** (one- and two-phase wyes were tank ends) |
| S3b-3 | Voltages and kVA (amends GLM-6) | **GLM-6's "1-phase `WYE_WYE` voltages are phase to neutral" is wrong: the decks and the engine take them line to line on every phase count** (the walk's S0 finding). So `ratedU` is the written voltage and `baseU` the coil (÷ √3 on a wye, as written on a delta); `ratedS` the tank's kVA, `baseS` its share per phase conductor. A center tap's primary is the coil: `baseU` as written, `ratedU` × √3 on a 3-phase system (the walk); a half's `baseU` is `secondary_voltage`, its `ratedU` × 2, its `ratedS` S / 2, every `baseS` S. Derived values are never rounded. **Amended by S6-1:** true of the Java exports; a wye whose written voltage is its from bus's `nominal_voltage` is rated by the coil |
| S3b-4 | Impedance base | **The user's: keep GridLAB-D's ohms.** Its per unit is on its own base (written line-to-line voltage, whole-unit kVA); the %Z fields are on each tank's nameplate, so every value is moved by `k = 3 S_coil / S_total` (above): 1 on 3-phase, delta and center-tap units, 3 on the 581 1-phase and 1.5 on the 130 2-phase `WYE_WYE` units, per can in a bank. Copying the written per unit would give a 1-phase can a third of the impedance GridLAB-D solves with |
| S3b-5 | Where the impedance goes | **The user's: GLM stores %Z (one R + jX per unit and a parallel shunt), not a mesh, so it goes on the `TransformerTankConfiguration`: `percentImpedance`, `loadLoss`, `noLoadLoss`, `percentMagnetizingCurrent`.** R comes back exactly as loadLoss / S and X as √(Z² − R²) (GridLAB-D requires both positive). No winding `r`, no mesh, nothing on the instance ends; a center tap's split is GridLAB-D's (the Hopkinson rule the CIMTBL-Models templates use) |
| S3b-6 | Shunt | `shunt_resistance`/`shunt_reactance` are GridLAB-D's parallel branch (`zc = Rsh·jXsh / (Rsh + jXsh)`): the real part is `noLoadLoss` = S / (Rsh k), the reactive part `percentMagnetizingCurrent` = 100 / (Xsh k), as the DSS import's `%noloadloss`/`%imag`. The written value is kept although GridLAB-D's NR ignores the shunt on `WYE_WYE` (`transformer.cpp:362` builds only 1 / zt); FBS and every center tap use it |
| S3b-7 | Instance ends and phases | End 1 = `from`, end 2 = `to`. `WYE_WYE`: the written letters + N on both, `Yn` grounded. `DELTA_GWYE`: `ABC` `D` ungrounded, then `ABCN` `Yn` grounded (the G), whether N is written or not. `DELTA_DELTA`: `ABC` `D` on both, N dropped. Center tap: `XN` `Y`, then `s1s2N` `I`, with the DSS import's phase ends. A bank has a phase end per conductor of each terminal, numbered as its lugs. A one-tank instance has none: every GLM coil runs from its phase to N (or is 3-phase), which the terminal phases already say |
| S3b-8 | Ratings | As S3a-5: the 3 Java-export transformers' `continuous_rating_X`/`emergency_rating_X` go, as written, on the transformer's own `OperationalLimitSet`. They are primary-side amps (27.61 A = 1.1 × the 25.1 A of 5 MVA at 115 kV). GridLAB-D replaces them with the configuration's kVA (`transformer.cpp:234`) |
| S3b-9 | Unequal cans | **The user's: each can a tank, the bank a `TransformerBankConfiguration`.** A `WYE_WYE` instance whose wired phases are all rated, with different kVAs, is a bank (145 instances): a can per wired phase of its phase's kVA, lugged on the bank's conductors as the CIMTBL-Models open-wye bank. GridLAB-D puts one `zt` in ohms on every phase, so each can's %Z fields are those ohms on its own kVA (S3b-4). **Best guess for the 117 that leave a wired phase unrated** (15 / 0 / 0 kVA on `ABCN`): no can size exists for that phase, and GridLAB-D still runs it through the same `zt`, so they stay one tank of `power_rating`, the phase kVAs listed on the row. Equally rated 2-phase units (100) stay one tank too. **Amended by S3b-13:** on one or two phases they are lugged cans of equal shares of `power_rating`, the phase kVAs still listed |
| S3b-10 | Vector group | Not written, as the DSS import: the connection kinds hold the form (the Java export's `// vector group Dyn1y1` is a comment the reader does not keep) |
| S3b-11 | Shared code | The center-tap lug layout and `star_to_mesh` are what DSS uses too. They are copied into this spoke (no cross-spoke import) and listed in plan section 7 as core candidates, as `limit_types` was |
| S3b-12 | Field tables | Generated from the mappers' `FIELDS` with `fields_table` (below), as S3a-11 |
| S3b-13 | TankEnds three-phase only (the user's, 2026-11-19, via clallam_cim request 10) | **"TransformerTankEnd is only for three-phase templates, single-phase should use TransformerPhaseEnd / TransformerLug."** A `WYE_WYE`/`SINGLE_PHASE` on one phase is one lugged can, on two a bank of two (S3b-2), as the DSS import writes a 1-phase XfmrCode. Electrically unchanged: each can's %Z fields are GridLAB-D's ohms on its own kVA (k = 3 S_can / S, or S_can / S coil-rated, S3b-4), as the tank ends' per-phase base was, and the DSS export is one 1-phase Transformer per can in place of a `phases=2` one. JOHNSON CREEK solves the same (per-phase pu range and total kW unchanged over its 4157 nodes), its TankEnds 78 → 36 |

**Core owes (plan section 7):** the transformer getter (`getters/transformer.py`) reads impedance only from
winding `r` and the mesh; `percentImpedance`/`loadLoss` are open in `GETTERS_PLAN.md` ("test summaries ... not
checked against the mesh"), a gap the DSS exporter hit too. It needs to read the %Z fields (with the center tap's
Hopkinson split) and a bank of lugged template tanks by their phase ends (it raises on a bank today) before any
exporter can read these templates. S3b's tests do not go through the getter.

**Tests.** An atom `tests/atoms/transformer/transformer.glm` on the line atom (it already has a center tap):
`xcon_xfm1`, `xcon_sub3`, IEEE123's `DELTA_DELTA`, a taxonomy `CN` can, an unequal 3-can bank and an unequal
2-phase one, a unit with an unrated wired phase, `xcon_ct5B` (impedance1/2 and shunt), a taxonomy center tap
without them, an unused configuration, and a rated instance; one golden per part, fail-fast cases, IEEE13_cdpsm
goldens. **The engine check (GLM-16):** on every deck, each bound transformer's tank fields, turned back into ohms
on the tank's coils (and, on a center tap, through the split), must equal GridLAB-D's `zt` and `zc` (or `z0`,
`z1`, `z2` and `zc`) computed from the configuration by the C++ formulas cited above; and each bank's cans must sum
to `power_rating`.

**Expected differences from the DSS import of IEEE13 (GLM-16).** The DSS import writes `xfm1` and `sub3` inline
(by ends, `r` per end, `x` on a mesh) and `ct5` as a template with winding `r` and a mesh; GLM writes all three by
template with %Z fields, so the comparison is on values in SI, matched by nodes. `xfm1`: equal (2.2825 %Z, 5.5 kW
load loss against 0.55 % on each end and 2 % x). `ct5`: equal through the split. `sub3`: the Java export wrote a 2-winding `DELTA_GWYE` of the
DSS 3-winding unit, so the 13.2 kV tertiary (`650z`, 1000 kVA) and the 0.4 Ω neutral reactance on winding 2 are
missing; the 115/4.16 kV pair agrees. mRIDs carry the Java prefixes (`xf_xf_xfm1` vs `xf_xfm1`). The transformers
carry limit sets the DSS import does not write.

### Built (2026-11-09)

- `importer/cimtbl/transformer_configuration.py` (`map_transformer_configuration`, `wirings`: the three forms,
  the %Z fields on each tank's nameplate, the center-tap split check) and `transformer.py` (`map_transformers`:
  tanks, ends, phase ends, limit sets), wired into `MAPPING_ORDER` (rows 5 and 10) and `CLASSIFIED`.
  `link.provenance` takes the spec anchor.
- The S1 feeder atom's two configurations gained an impedance (GridLAB-D throws without one) and the center tap
  its `powerA_rating`; the bus and source goldens are unchanged.
- Atom `tests/atoms/transformer/transformer.glm` (on the S3a line atom: `xcon_xfm1` with ratings, `DELTA_GWYE`
  written `ABC`, `DELTA_DELTA`, a taxonomy `CN` can with a shunt, a 37.5 + 25 + 25 kVA bank, a 15 + 25 kVA 2-phase
  bank, a unit with unrated wired phases, `xcon_ct5B`, a taxonomy center tap with a shunt, an unused
  configuration) with one golden per part; goldens `tests/goldens/IEEE13_cdpsm/transformer_configuration`,
  `transformer`; `tests/test_cimtbl_transformer.py` (classification, the atom bound and read back, 10 fail-fast
  cases, and on every deck: every configuration written, and each tank's %Z fields turned back into ohms and
  siemens equal GridLAB-D's `zt`/`zc`, or `z0`/`z1`/`zc` on a center tap, from the configuration by the C++
  formulas).
- Every deck that binds S3a binds S3b: 27 of 29, the same two deck defects; 8,927 transformers in 9,195 tanks,
  145 of them banks (95 bank configurations).

### Field tables (generated: `fields_table(cls, records, fields=...)`, samples from tests/decks and the atom)

The object header (`parent`, `groupid`, `latitude`, `longitude`, `in_svc`, `out_svc`, `rank`, `flags`) and, on the
transformer, the link's solver outputs and state and inrush settings (as S3a) are untranscribed and left out.

#### transformer_configuration

| TransformerConfiguration field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, TransformerConfigurationName]` | `xcon_ct5B`, `xcon_sub3`, `xcon_xfm1` | copied | `TransformerTankConfiguration.name`; mRID = xc_ + name; a bank xb_ + name, its cans xc_ + name + _<phase> (_<place> unrated) |
| `connect_type` | `Optional[str]` | `SINGLE_PHASE_CENTER_TAPPED`, `DELTA_GWYE`, `WYE_WYE` | structural | the form and connectionKinds: WYE_WYE and SINGLE_PHASE Y/Y (on one or two phases lugs), DELTA_GWYE D/Y, DELTA_DELTA D/D, SINGLE_PHASE_CENTER_TAPPED lugs; unset raises |
| `install_type` | `Optional[str]` | `POLETOP`, `PADMOUNT` | untranscribed | thermal aging model and siting; no network-profile home |
| `coolant_type` | `Optional[str]` |  | untranscribed | thermal aging model and siting; no network-profile home |
| `cooling_type` | `Optional[str]` |  | untranscribed | thermal aging model and siting; no network-profile home |
| `primary_voltage` | `Optional[float]` | `2400.0`, `115000.0`, `4160.0` | structural | winding 1 ratedU (line to line) and baseU (the coil), S3b-3; a coil-rated wye's is baseU, ratedU on its bus's system (S6) |
| `secondary_voltage` | `Optional[float]` | `120.0`, `4160.0`, `480.0` | structural | winding 2 ratedU and baseU; a center tap's half (ratedU x 2) |
| `power_rating` | `Optional[float]` | `5.0`, `5000.0`, `500.0` | structural | ratedS: the whole unit's kVA, else the phase sum (init()) |
| `powerA_rating` | `Optional[float]` | `0.0`, `75.0`, `1000.0` | structural | a can's kVA when the wired phases are rated unequally; a center tap's S on its phase; else unused, listed when it is not S / n |
| `powerB_rating` | `Optional[float]` | `5.0`, `75.0`, `1000.0` | structural | a can's kVA when the wired phases are rated unequally; a center tap's S on its phase; else unused, listed when it is not S / n |
| `powerC_rating` | `Optional[float]` | `0.0`, `75.0`, `1000.0` | structural | a can's kVA when the wired phases are rated unequally; a center tap's S on its phase; else unused, listed when it is not S / n |
| `resistance` | `Optional[float]` | `1e-05`, `0.011`, `0.0127` | derived | percentImpedance = |R + jX| x k x 100, loadLoss = R x k x S (S3b-4, S3b-5); a center tap's are the full winding's |
| `reactance` | `Optional[float]` | `0.0001`, `0.02`, `8e-05` | derived | percentImpedance = |R + jX| x k x 100, loadLoss = R x k x S (S3b-4, S3b-5); a center tap's are the full winding's |
| `impedance` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.006, 'imag': 0.0136})` | derived | percentImpedance = |R + jX| x k x 100, loadLoss = R x k x S (S3b-4, S3b-5); a center tap's are the full winding's |
| `resistance1` | `Optional[float]` |  | derived | a center tap's star given whole: must be GridLAB-D's split of one R + jX (impedance = 0.5R + j0.8X, both halves R + j0.4X); any other split, or on another connection, raises |
| `reactance1` | `Optional[float]` |  | derived | a center tap's star given whole: must be GridLAB-D's split of one R + jX (impedance = 0.5R + j0.8X, both halves R + j0.4X); any other split, or on another connection, raises |
| `impedance1` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.012, 'imag': 0.0068})` | derived | a center tap's star given whole: must be GridLAB-D's split of one R + jX (impedance = 0.5R + j0.8X, both halves R + j0.4X); any other split, or on another connection, raises |
| `resistance2` | `Optional[float]` |  | derived | a center tap's star given whole: must be GridLAB-D's split of one R + jX (impedance = 0.5R + j0.8X, both halves R + j0.4X); any other split, or on another connection, raises |
| `reactance2` | `Optional[float]` |  | derived | a center tap's star given whole: must be GridLAB-D's split of one R + jX (impedance = 0.5R + j0.8X, both halves R + j0.4X); any other split, or on another connection, raises |
| `impedance2` | `Union[dict, Complex, NoneType]` | `Complex({'real': 0.012, 'imag': 0.0068})` | derived | a center tap's star given whole: must be GridLAB-D's split of one R + jX (impedance = 0.5R + j0.8X, both halves R + j0.4X); any other split, or on another connection, raises |
| `shunt_resistance` | `Optional[float]` | `500.0`, `166.666667` | derived | noLoadLoss = S / (Rsh x k), percentMagnetizingCurrent = 100 / (Xsh x k) (S3b-6); unset: GridLAB-D's 999999999 pu (lossless) is not filled; on a delta connection raises |
| `shunt_reactance` | `Optional[float]` | `200.0`, `90.909092` | derived | noLoadLoss = S / (Rsh x k), percentMagnetizingCurrent = 100 / (Xsh x k) (S3b-6); unset: GridLAB-D's 999999999 pu (lossless) is not filled; on a delta connection raises |
| `shunt_impedance` | `Union[dict, Complex, NoneType]` | `Complex({'real': 6545.46, 'imag': 665...`, `Complex({'real': 1226.16, 'imag': 135...`, `Complex({'real': 391.76, 'imag': 390....` | derived | noLoadLoss = S / (Rsh x k), percentMagnetizingCurrent = 100 / (Xsh x k) (S3b-6); unset: GridLAB-D's 999999999 pu (lossless) is not filled; on a delta connection raises |
| `core_coil_weight` | `Optional[float]` |  | untranscribed | thermal aging model and siting; no network-profile home |
| `tank_fittings_weight` | `Optional[float]` |  | untranscribed | thermal aging model and siting; no network-profile home |
| `oil_volume` | `Optional[float]` |  | untranscribed | thermal aging model and siting; no network-profile home |
| `rated_winding_time_constant` | `Optional[float]` |  | untranscribed | thermal aging model and siting; no network-profile home |
| `rated_winding_hot_spot_rise` | `Optional[float]` |  | untranscribed | thermal aging model and siting; no network-profile home |
| `rated_top_oil_rise` | `Optional[float]` |  | untranscribed | thermal aging model and siting; no network-profile home |
| `no_load_loss` | `Optional[float]` |  | structural | raises when set: it replaces the impedances on a center tap (transformer_configuration.cpp:283), and no deck sets it |
| `full_load_loss` | `Optional[float]` |  | structural | raises when set: it replaces the impedances on a center tap (transformer_configuration.cpp:283), and no deck sets it |
| `reactance_resistance_ratio` | `Optional[float]` |  | structural | raises when set: used only with no_load_loss and full_load_loss |
| `installed_insulation_life` | `Optional[float]` |  | untranscribed | thermal aging model and siting; no network-profile home |
| `magnetization_location` | `Optional[str]` |  | untranscribed | inrush model |
| `inrush_saturation_enabled` | `Union[bool, Bool, NoneType]` |  | untranscribed | inrush model |
| `L_A` | `Optional[float]` |  | untranscribed | inrush model |
| `phi_K` | `Optional[float]` |  | untranscribed | inrush model |
| `phi_M` | `Optional[float]` |  | untranscribed | inrush model |
| `I_M` | `Optional[float]` |  | untranscribed | inrush model |
| `T_D` | `Optional[float]` |  | untranscribed | inrush model |

#### transformer

| Transformer field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, TransformerName]` | `xf_sub3`, `xf_tpoletop`, `xf_xfm1` | copied | `PowerTransformer.name`; mRID = xf_ + name |
| `phases` | `Optional[str]` | `ABCN`, `BS`, `ABC` | structural | the ends' phases and kinds (S3b-7), and a bank's or center tap's phase ends |
| `nominal_voltage` | `Optional[float]` |  | untranscribed | the walk gives the BaseVoltage (GLM-1) |
| `status` | `Optional[str]` |  | structural | unset or CLOSED; OPEN raises (the walk) |
| `from_node` | `Optional[str]` | `sourcebus`, `670`, `xf1` | structural | node1: the root bus of the object it names (GLM-4) |
| `to` | `Optional[str]` | `650`, `house`, `634` | structural | node2: the root bus of the object it names (GLM-4) |
| `pdispatch` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `pdispatch_offset` | `Optional[float]` |  | untranscribed | dispatch control; no network-profile home |
| `set_pdispatch` | `Union[bool, Bool, NoneType]` |  | untranscribed | dispatch control; no network-profile home |
| `mean_repair_time` | `Optional[float]` |  | untranscribed | reliability data |
| `continuous_rating_A` | `Optional[float]` | `27.61`, `76.33`, `22.9` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_B` | `Optional[float]` | `27.61`, `76.33`, `22.9` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `continuous_rating_C` | `Optional[float]` | `27.61`, `76.33`, `22.9` | structural | the normal CurrentLimit of the equipment's own OperationalLimitSet <mRID>_limits (S3a-4, S3a-5); the set phases must agree |
| `emergency_rating_A` | `Optional[float]` | `37.65`, `104.09`, `31.23` | structural | the emergency CurrentLimit of that set |
| `emergency_rating_B` | `Optional[float]` | `37.65`, `104.09`, `31.23` | structural | the emergency CurrentLimit of that set |
| `emergency_rating_C` | `Optional[float]` | `37.65`, `104.09`, `31.23` | structural | the emergency CurrentLimit of that set |
| `configuration` | `Optional[str]` | `xcon_sub3`, `xcon_ct5B`, `xcon_xfm1` | structural | TransformerTank.TankConfiguration = xc_<configuration> (a bank: one tank per can, xc_<configuration>_<phase>) |
| `climate` | `Optional[str]` |  | untranscribed | thermal aging model and its state |
| `ambient_temperature` | `Optional[float]` |  | untranscribed | thermal aging model and its state |
| `top_oil_hot_spot_temperature` | `Optional[float]` |  | untranscribed | thermal aging model and its state |
| `winding_hot_spot_temperature` | `Optional[float]` |  | untranscribed | thermal aging model and its state |
| `percent_loss_of_life` | `Optional[float]` |  | untranscribed | thermal aging model and its state |
| `aging_constant` | `Optional[float]` |  | untranscribed | thermal aging model and its state |
| `use_thermal_model` | `Union[bool, Bool, NoneType]` |  | untranscribed | thermal aging model and its state |
| `transformer_replacement_count` | `Optional[float]` |  | untranscribed | thermal aging model and its state |
| `aging_granularity` | `Optional[float]` |  | untranscribed | thermal aging model and its state |
| `phase_A_primary_flux_value` | `Optional[float]` |  | untranscribed | inrush state |
| `phase_B_primary_flux_value` | `Optional[float]` |  | untranscribed | inrush state |
| `phase_C_primary_flux_value` | `Optional[float]` |  | untranscribed | inrush state |
| `phase_A_secondary_flux_value` | `Optional[float]` |  | untranscribed | inrush state |
| `phase_B_secondary_flux_value` | `Optional[float]` |  | untranscribed | inrush state |
| `phase_C_secondary_flux_value` | `Optional[float]` |  | untranscribed | inrush state |

## S3c: regulators (by the user's direction 2026-11-09; built 2026-11-09)

S3c maps `regulator` with its `regulator_configuration` (GLM-7), plan section 2 rows 6 and 11. The user's
direction: **a regulator is a `VoltageRegulator` with two `AutoTransformerEnd`s, never a `TransformerTankEnd`; an LTC
on a step-down transformer would be a `PowerTransformerEnd`; the lack of impedance is why `AutoTransformerEnd`
exists.** GLM has no LTC: a GridLAB-D regulator has no voltage ratio (it is 1:1 by construction), and a
`transformer` has no tap changer. So every GLM regulator is a `VoltageRegulator`, and the core `voltage_regulator`
shape applies without its mesh. GridLAB-D citations are to `powerflow/regulator.cpp` and
`regulator_configuration.cpp`.

| # | artifact | native class (records) | CIM | mRID |
|---|---|---|---|---|
| 6 | none | regulator_configuration (36) | none on its own: CIM has no regulator template (an AutoTransformer has none), so the mapper copies a configuration's values onto every unit that names it | |
| 11 | `regulator.cimtbl` | regulator (36) | `VoltageRegulator` + two `AutoTransformerEnd`s + `TapChangerControl` + `RatioTapChanger` per unit | `xf_<name>[_<phase>]`, `rc_<name>[_<phase>]` |

**What the decks hold** (the 28 readable decks): 36 regulators, one configuration each, all `WYE_WYE`.
`control_level` is never set (GridLAB-D's default `INDIVIDUAL`); `Control` is `OUTPUT_VOLTAGE` 28, `MANUAL` 7 (the
Java exports, whose `LINE_DROP_COMP` is commented out), `REMOTE_NODE` 1 (IEEE13_houses, which stops at the walk).
`Type` is set on the 6 Java-export configurations (`B`); `CT_phase`, `PT_phase`, `reverse_flow_control` and the
regulator's `tap_X` are never set. Phases: `ABCN` 30 and the Java exports' `CAB`, `BCA`, `CBA`, `ABC`, `CA`, `A`.
`raise_taps` = `lower_taps` = 16 and `regulation` 0.1 everywhere. No regulator sets `regulator_resistance`.

```
# IEEE13_cdpsm xf_Reg (phases CAB, MANUAL, Type B, tap_pos 10 / 8 / 11): three units, as the DSS import's reg1-3
Table VoltageRegulator: mRID, name, construction, EquipmentContainer=fdr_IEEE13_cdpsm
    xf_xf_Reg_A, xf_Reg_A, typeB                       # and _B, _C
Table AutoTransformerEnd: mRID, AutoTransformer, node, phase, endNumber, grounded=true, baseU (V), BaseVoltage
    xf_xf_Reg_A_1, xf_xf_Reg_A, brkr, AN, 1, 2401.78, bv_4p16kv
    xf_xf_Reg_A_2, xf_xf_Reg_A, rg60, AN, 2, 2401.78, bv_4p16kv
Table TapChangerControl: mRID, name, mode=voltage, discrete=true, enabled, monitoredPhase, ptRatio, targetValue, targetDeadband, lineDropCompensation, lineDropR (ohm), lineDropX (ohm), Terminal
    rc_xf_Reg_A, xf_Reg_A, false, A, 20.0, , , false, 0.017142857142857144, 0.05142857142857143, xf_xf_Reg_A_T2
Table RatioTapChanger: mRID, name, TransformerEnd, TapChangerControl, lowStep, highStep, neutralStep=0, step, stepVoltageIncrement (percent), neutralU (V), ltcFlag=true, controlEnabled, ptRatio, ctRatio, initialDelay (s), subsequentDelay (s)
    rc_xf_Reg_A_tap, xf_Reg_A, xf_xf_Reg_A_2, rc_xf_Reg_A, -16, 16, 10, 0.625, 2401.78, false, 20.0, 3500.0, 15.0, 15.0
```

| GLM slot | kind | target |
|---|---|---|
| regulator `name` | derived | `VoltageRegulator.name` = name (BANK) or name_<phase> (INDIVIDUAL); mRID `xf_` + that; the control `rc_` + that, its tap changer + `_tap` |
| `from`, `to` | structural | end 1 and end 2 `node`: the root bus (GLM-4); each end's `BaseVoltage` is the walk's |
| `phases` | structural | the units and each end's `phase`: the letter + N (a gang unit ABCN), N or not written (every unit is wye to neutral) |
| `configuration` | structural | its values on every unit (no template) |
| `tap_A`/`_B`/`_C`, `tap_pos_A`/`_B`/`_C` | derived | `RatioTapChanger.step` of the phase's unit: the regulator's `tap_X`, else the configuration's `tap_pos_X`, else 0 (`regulator.cpp:146`, `:262`) |
| `raise_taps`, `lower_taps` | copied, derived | `highStep`, `lowStep` = -`lower_taps`; `neutralStep` 0 |
| `regulation` | derived | `stepVoltageIncrement` = regulation / raise_taps (GridLAB-D's `tapChangePer`, `:244`), in percent |
| `Type` | mapped | `VoltageRegulator.construction`: A `typeA`, B `typeB` (default B) |
| `Control` | structural | `MANUAL` (default): `TapChangerControl.enabled` = `RatioTapChanger.controlEnabled` = false; `OUTPUT_VOLTAGE`, `LINE_DROP_COMP`: true; `lineDropCompensation` on `LINE_DROP_COMP` only; `REMOTE_NODE` on the regulator's own output as `OUTPUT_VOLTAGE` (S6-6) |
| `band_center`, `band_width` | derived | `targetValue`, `targetDeadband` (full band, as CIM's): primary volts as written, × `power_transducer_ratio` on `LINE_DROP_COMP`, whose band is on the PT secondary (`:1316`) |
| `power_transducer_ratio`, `current_transducer_ratio` | copied | `TapChangerControl.ptRatio`, `RatioTapChanger.ptRatio`, `RatioTapChanger.ctRatio` |
| `compensator_r_setting_X`, `compensator_x_setting_X` | derived | `lineDropR`, `lineDropX` (ohm) of the phase's unit = setting × PT ratio / CT ratio (`line_drop_ohms`; S3c-4) |
| `dwell_time`, `time_delay` | derived | `initialDelay` = `subsequentDelay` = dwell_time + time_delay (S3c-5) |
| `control_level` | structural | `INDIVIDUAL`: a unit per wired phase; `BANK`: one gang unit on ABC (GLM-7), or one unit on its one `PT_phase` (S6-7) |
| `PT_phase`, `CT_phase` | structural | `BANK`: `monitoredPhase` (the two must agree); `INDIVIDUAL`: GridLAB-D ignores them, listed on the row (S6-7) |
| `regulator_resistance` | untranscribed | NR's stand-in (default `powerflow::default_resistance`, 1e-4 Ω); the ends are ideal (S3c-2) |
| the link's ratings | structural | each unit's own `OperationalLimitSet`, its phase's `continuous_rating_X`/`emergency_rating_X` (a gang unit: as S3a-5) |
| `msg_mode`, `remote_voltage_X`, `tap_X_change_count`, the link outputs and header slots | untranscribed | co-simulation messaging, solver output or state, as S3a |

### Fail fast (S3c)

| condition | why |
|---|---|
| `connect_type` other than `WYE_WYE` | `regulator_configuration.cpp:232`: NR takes only `WYE_WYE`; every deck is `WYE_WYE` |
| `raise_taps` or `lower_taps` unset or not positive; `regulation` unset or 0 on an automatic `Control` | `:198`, `:212` throw |
| `Control REMOTE_NODE` sensing a bus other than the regulator's own output | S3c-6, S6-6 |
| `reverse_flow_control` other than `LOCK_NONE`; a `BANK` on neither ABC nor its one `PT_phase`, whose `PT_phase` and `CT_phase` are not one equal phase, or whose taps differ | in no deck; a gang holds one tap |
| a tap outside -lower_taps..+raise_taps | GridLAB-D would clamp it on the first tap change, not at init |
| compensator settings without both transducer ratios | the primary ohms need both; in no deck |
| phases with S or nothing in ABC; status `OPEN` | as S3b |

### Decisions for S3c

| # | question | decision |
|---|---|---|
| S3c-1 | Form (GLM-7) | **The user's: a `VoltageRegulator` with two `AutoTransformerEnd`s, no tank end; an LTC on a step-down transformer would be a `PowerTransformerEnd`, and GLM has none.** One unit per wired phase on `INDIVIDUAL` (each its own `RatioTapChanger` on end 2 and `TapChangerControl` on its `T2`, as the DSS import's IEEE 13), one gang unit on `BANK`. `mRID` `xf_` as the core shape and the DSS import |
| S3c-2 | Impedance and kVA | **The user's: the lack of impedance is why `AutoTransformerEnd` exists.** GridLAB-D's regulator has no impedance and no kVA (its NR stand-in resistance is a solver setting), so the ends carry no `ratedS` and there is no `TransformerMeshImpedance` |
| S3c-3 | Coil voltage | `baseU` = `neutralU` = the from bus's `nominal_voltage` as written (phase to neutral, 2401.78 V): the coil the band works against (`regulator.cpp:1380` compares the to-node's phase voltage). A gang unit's is that × √3 (line to line, as the core shape's 3-phase `vr3`) |
| S3c-4 | Line drop | GridLAB-D's compensator drop is `(I / current_transducer_ratio) × (R + jX)` on the PT secondary (`:1330`), so the primary ohms are the setting × PT ratio / CT ratio: `line_drop_ohms` with the CT ratio where it takes a CT primary rating (GridLAB-D's CT secondary is 1 A). `ctRating` is not written (GLM has no CT primary rating). The settings are written on every unit that has them, also on `MANUAL`, where `lineDropCompensation` is false |
| S3c-5 | Delays | GridLAB-D waits `dwell_time` and then `time_delay` before every tap change, the first and each later one (`regulator.cpp:598`-`611`: a change re-arms the dwell, and the out-of-band branch then sets the mechanism time after it), so `initialDelay` = `subsequentDelay` = the sum. An exporter writes `dwell_time` 0 and `time_delay` = `subsequentDelay` |
| S3c-6 | `REMOTE_NODE` | Raises: a `TapChangerControl.Terminal` is a terminal, and a sense node is a bus with no single terminal to name; its one deck (IEEE13_houses) stops at the walk. As the DSS import's remote `bus`. **Amended by S6-6:** `REMOTE_NODE` on the regulator's own output is mapped as `OUTPUT_VOLTAGE` |
| S3c-7 | Ratings | Each 1-phase unit's `OperationalLimitSet` carries its own phase's ratings (6 Java-export regulators: 763.58 / 1041.25 A); a gang unit's are the link's, as S3a-5 |

**Getter (done 2026-11-10, on this branch):** the transformer getter's `AUTO` form reads an `AutoTransformer` with
no mesh as ideal: no `ratedS` needed, an empty mesh, no core, and `base_power` the declared one, else `None`. One
with a mesh still requires winding 1's `ratedS`. S3c's tests read every bound unit through the getter.

**Tests.** An atom `tests/atoms/regulator/regulator.glm` on the line atom: `OUTPUT_VOLTAGE` written `CAB` with a
regulator `tap_B`, IEEE123's `MANUAL` `CA` unit (`Type A`, compensator settings), a `LINE_DROP_COMP` 1-phase unit with
`regulator_resistance`, a `BANK` gang unit monitoring B, and an unused configuration; its golden, 10 fail-fast
cases, the IEEE13_cdpsm golden, and on every deck **the engine check (GLM-16):** each unit's tap changer gives
GridLAB-D's tap and step, its control GridLAB-D's band and enabled state, a unit per wired phase, and no mesh.

**Expected differences from the DSS import of IEEE13 (GLM-16).** Equal: three units AN/BN/CN on brkr→rg60, the
taps 10/8/11, ±16 steps of 0.625 %, PT ratio 20, CT ratio 3500, the control on `T2`. Different, all from what GLM
holds: no `ratedS` (DSS 1666 kVA) and no mesh (DSS 0.01 % r and x); `baseU`/`neutralU` 2401.78 V (DSS 2.4 kV);
`enabled`/`controlEnabled` false and no band (the Java export wrote `MANUAL` and commented the band out);
`lineDropR`/`X` 0.0171 / 0.0514 Ω against DSS 0.0857 / 0.2571 Ω (the Java export copied the DSS dial volts with the
DSS CT ratio 700 / 0.2 A, which GridLAB-D reads on a 1 A secondary); `initialDelay` 15 and `subsequentDelay` 15
(DSS 15 and 2: the export dropped `tapdelay`); no `ctRating`, no reverse settings; mRIDs `xf_xf_Reg_A` against
`xf_reg1`; the units carry limit sets.

### Built (2026-11-09)

- `importer/cimtbl/regulator.py` (`map_regulators`; `FIELDS` and `CONFIGURATION_FIELDS`), wired into
  `MAPPING_ORDER` (row 11, after the transformers) and `CLASSIFIED` (both classes).
- Atom `tests/atoms/regulator/regulator.glm` with its golden; golden `tests/goldens/IEEE13_cdpsm/regulator`; the
  master golden's new `Import`; `tests/test_cimtbl_regulator.py`.
- Every deck that binds S3b binds S3c: 27 of 29, the same two deck defects; 35 regulators as 102 units (33
  3-phase, one 2-phase, one 1-phase).

### Field tables (generated: `fields_table(cls, records, fields=...)`, samples from tests/decks and the atom)

The object header and the link slots (as S3a) are left out.

#### regulator_configuration

| RegulatorConfiguration field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, RegulatorConfigurationName]` | `rcon_reg3`, `rcon_creg1a`, `rcon_creg2a` | structural | read by every regulator that names it; CIM has no regulator template, so nothing carries it but the units' row comments |
| `connect_type` | `Union[str, ForwardRef('ConnectType'), NoneType]` | `WYE_WYE` | structural | WYE_WYE (every unit wye, grounded); any other raises (regulator_configuration.cpp:232: NR takes WYE_WYE only) |
| `band_center` | `Optional[float]` | `7500.0`, `2440.0`, `122.0` | derived | targetValue = band_center (V): primary volts on OUTPUT_VOLTAGE and MANUAL, x power_transducer_ratio on LINE_DROP_COMP, whose band is on the PT secondary (regulator.cpp:1316) |
| `band_width` | `Optional[float]` | `120.0`, `40.0`, `2.0` | derived | targetDeadband = band_width (V): primary volts on OUTPUT_VOLTAGE and MANUAL, x power_transducer_ratio on LINE_DROP_COMP, whose band is on the PT secondary (regulator.cpp:1316); the full band, as CIM's |
| `time_delay` | `Optional[float]` | `30.0` | derived | initialDelay = subsequentDelay = dwell_time + time_delay (s): every tap change waits both (regulator.cpp:598-611, S3c-5); default 0 |
| `dwell_time` | `Optional[float]` | `15.0` | derived | with time_delay; default 0 |
| `raise_taps` | `Optional[int]` | `16` | copied | `RatioTapChanger.highStep`; also the stepVoltageIncrement divisor; 0 raises (regulator_configuration.cpp:198) |
| `lower_taps` | `Optional[int]` | `16` | derived | RatioTapChanger.lowStep = -lower_taps; 0 raises |
| `current_transducer_ratio` | `Optional[float]` | `3500.0`, `250.0`, `1500.0` | copied | `RatioTapChanger.ctRatio`; and the line drop's CT ratio |
| `power_transducer_ratio` | `Optional[float]` | `20.0` | copied | `TapChangerControl.ptRatio`, `RatioTapChanger.ptRatio`; and the line drop's and LINE_DROP_COMP band's PT ratio |
| `compensator_r_setting_A` | `Optional[float]` | `3.0`, `0.4`, `0.6` | derived | lineDropR (ohm) = the unit's phase setting x power_transducer_ratio / current_transducer_ratio (line_drop_ohms; regulator.cpp:1330); set without both ratios raises |
| `compensator_r_setting_B` | `Optional[float]` | `3.0`, `1.4` | derived | lineDropR (ohm) = the unit's phase setting x power_transducer_ratio / current_transducer_ratio (line_drop_ohms; regulator.cpp:1330); set without both ratios raises |
| `compensator_r_setting_C` | `Optional[float]` | `3.0`, `0.4`, `0.2` | derived | lineDropR (ohm) = the unit's phase setting x power_transducer_ratio / current_transducer_ratio (line_drop_ohms; regulator.cpp:1330); set without both ratios raises |
| `compensator_x_setting_A` | `Optional[float]` | `9.0`, `7.5`, `0.4` | derived | lineDropX (ohm) = the unit's phase setting x power_transducer_ratio / current_transducer_ratio (line_drop_ohms; regulator.cpp:1330); set without both ratios raises |
| `compensator_x_setting_B` | `Optional[float]` | `9.0`, `7.5`, `2.6` | derived | lineDropX (ohm) = the unit's phase setting x power_transducer_ratio / current_transducer_ratio (line_drop_ohms; regulator.cpp:1330); set without both ratios raises |
| `compensator_x_setting_C` | `Optional[float]` | `9.0`, `7.5`, `0.4` | derived | lineDropX (ohm) = the unit's phase setting x power_transducer_ratio / current_transducer_ratio (line_drop_ohms; regulator.cpp:1330); set without both ratios raises |
| `CT_phase` | `Optional[str]` | `B` | structural | BANK: the phase whose compensator setting is read, which must be PT_phase; INDIVIDUAL: GridLAB-D ignores it (regulator.cpp:1328), listed on the row (S6) |
| `PT_phase` | `Optional[str]` | `B` | structural | BANK: TapChangerControl.monitoredPhase; INDIVIDUAL: GridLAB-D ignores it (regulator.cpp:1378), listed on the row (S6) |
| `regulation` | `Optional[float]` | `0.1` | derived | RatioTapChanger.stepVoltageIncrement = regulation / raise_taps (percent), GridLAB-D's tapChangePer (regulator.cpp:244); 0 raises unless MANUAL |
| `control_level` | `Optional[str]` | `BANK` | structural | INDIVIDUAL (default): one unit per wired phase; BANK: one gang unit on ABC (GLM-7), or one unit on its one PT_phase (S6) |
| `Control` | `Optional[str]` | `MANUAL`, `OUTPUT_VOLTAGE`, `LINE_DROP_COMP` | structural | MANUAL (default): enabled = controlEnabled = false; OUTPUT_VOLTAGE, LINE_DROP_COMP: true, lineDropCompensation on LINE_DROP_COMP only; REMOTE_NODE on the regulator's own to bus: as OUTPUT_VOLTAGE (the same voltages, regulator.cpp:1376-1420), elsewhere raises (S3c-6, S6) |
| `reverse_flow_control` | `Optional[str]` |  | structural | unset or LOCK_NONE; others raises when set: no deck sets it, so a mapping waits for one |
| `Type` | `Optional[str]` | `B`, `A` | mapped | `VoltageRegulator.construction`; A -> typeA, B -> typeB (default B): GridLAB-D's ratio 1 / (1 + tap x step) or 1 - tap x step |
| `tap_pos_A` | `Optional[int]` | `10`, `6`, `0` | derived | RatioTapChanger.step of the phase's unit, unless the regulator's tap_A; default 0 (regulator.cpp:146) |
| `tap_pos_B` | `Optional[int]` | `8`, `6`, `4` | derived | RatioTapChanger.step of the phase's unit, unless the regulator's tap_B; default 0 (regulator.cpp:146) |
| `tap_pos_C` | `Optional[int]` | `11`, `6`, `0` | derived | RatioTapChanger.step of the phase's unit, unless the regulator's tap_C; default 0 (regulator.cpp:146) |

#### regulator

| Regulator field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, RegulatorName]` | `xf_Reg`, `xf_reg1a`, `xf_reg2` | derived | VoltageRegulator.name = name (BANK) or name_<phase> (INDIVIDUAL); mRID = xf_ + that; the controls rc_ + that |
| `phases` | `Optional[str]` | `CAB`, `ABC`, `A` | structural | the wired phases A, B, C (N optional: every unit is wye to neutral); S raises |
| `inrush_integration_method` | `Optional[str]` |  | untranscribed | inrush solver setting |
| `status` | `Optional[str]` |  | structural | unset or CLOSED; OPEN raises (the walk) |
| `from_node` | `Optional[str]` | `brkr`, `150`, `9` | structural | node1: the root bus of the object it names (GLM-4) |
| `to` | `Optional[str]` | `rg60`, `150r`, `9r` | structural | node2: the root bus of the object it names (GLM-4) |
| `inrush_convergence_value` | `Optional[float]` |  | untranscribed | inrush solver setting |
| `inrush_integration_method_capacitance` | `Union[str, ForwardRef('InrushIntegrationMethodCapacitance'), NoneType]` |  | untranscribed | inrush solver setting |
| `inrush_integration_method_inductance` | `Union[str, ForwardRef('InrushIntegrationMethodInductance'), NoneType]` |  | untranscribed | inrush solver setting |
| `configuration` | `Optional[str]` | `rcon_reg3`, `rcon_creg1a`, `rcon_creg2a` | structural | a regulator_configuration: its values on every unit |
| `tap_A` | `Optional[int]` |  | derived | RatioTapChanger.step of the phase's unit (over tap_pos_A) |
| `tap_B` | `Optional[int]` | `3` | derived | RatioTapChanger.step of the phase's unit (over tap_pos_B) |
| `tap_C` | `Optional[int]` |  | derived | RatioTapChanger.step of the phase's unit (over tap_pos_C) |
| `msg_mode` | `Optional[str]` |  | untranscribed | co-simulation messaging |
| `remote_voltage_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output or state |
| `remote_voltage_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output or state |
| `remote_voltage_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output or state |
| `tap_A_change_count` | `Optional[float]` |  | untranscribed | solver output or state |
| `tap_B_change_count` | `Optional[float]` |  | untranscribed | solver output or state |
| `tap_C_change_count` | `Optional[float]` |  | untranscribed | solver output or state |
| `sense_node` | `Optional[str]` |  | structural | REMOTE_NODE's monitored node: must solve as the regulator's to bus; on another Control GridLAB-D ignores it, listed on the row (S6) |
| `regulator_resistance` | `Optional[float]` | `0.001` | untranscribed | NR's stand-in series resistance (default powerflow::default_resistance, 1e-4 ohm); the AutoTransformerEnds are ideal (S3c-2) |

## S4a: loads and capacitors (approved and built 2026-11-10)

S4a maps the loads (`load`, `triplex_load`, and the power of a plain `triplex_node`) and `capacitor` with its control
(GLM-8), plan section 2 rows 12 and 13. GridLAB-D citations are to `powerflow/load.cpp`, `triplex_load.cpp`,
`triplex_node.cpp`, `node.cpp` and `capacitor.cpp`. **The user's calls (2026-11-10): S4a-2 approved with a TODO for
the schedule, S4a-5 approved, S4a-8 option (a)** ("breaking away from the sloppy java converter was the right call").
S4a-2 and S4a-5 amend GLM-8.

| # | artifact | native class (records) | CIM | mRID |
|---|---|---|---|---|
| 12 | `load.cimtbl` | load (1,532) | `EnergyConsumer` + per-phase `EnergyConsumerPhase` values | `ld_<name>` |
| 12 | `triplex_load.cimtbl` | triplex_load (1) | `EnergyConsumer` for the legs, a second for the 240 V part | `ld_<name>`, `ld_<name>_12` |
| 12 | `triplex_node.cimtbl` | triplex_node with `power_1`/`_2`/`_12` (7,492) | as triplex_load | as triplex_load |
| 13 | `capacitor.cimtbl` | capacitor (78) | `LinearShuntCompensator` per unit (S4a-8), a `RegulatingControl` per controlled unit | `cap_<name>[_<phase>]`, `cc_<name>[_<phase>]` |

A load or capacitor is itself a bus in GridLAB-D (S0's amendment of section 2), so each device sits on its record's
root bus (GLM-4), and its `BaseVoltage` is that bus's. The bus is already in `bus.cimtbl`.

**What the decks hold** (the 28 readable decks):
- **`load`** (1,532):
  - **Given as constant power.** 1,429 taxonomy loads give `constant_power_X` in VA, with `load_class` set and the
    parent a meter.
  - **Given as base power with fractions.** 103 Java-export loads (IEEE13_cdpsm, IEEE13_assets, IEEE123) give
    `base_power_X ieeezipload.value*<|S| VA>` with `current_fraction_X 1` and `current_pf_X`. `ieeezipload` is the Java
    exporter's run-file schedule (`GldNode.java:475`); no deck defines it.
  - **Not set anywhere:** `constant_current_X`, `constant_impedance_X`, the explicit `_AN`/`_AB` forms,
    `power_fraction_X`, `impedance_fraction_X`, and a node's or meter's own `power_X`/`current_X`/`shunt_X`.
  - **Phases:** wye on 1-3 phases on 1,523 loads; `ABCD` 7 and `BCD` 2 are delta.
- **Triplex:** `power_12` on 7,492 taxonomy `triplex_node`s, each the child of a `triplex_meter`. Nothing else in the
  `power_1`/`current_*`/`shunt_*` family is set. One `triplex_load` (IEEE13_cdpsm `ld_house`, `BS`) has
  `base_power_1`/`_2` with `current_fraction 1`.
- **`capacitor`** (78):
  - `capacitor_X` is in MVAr on 70 and VAr on 4.
  - `control` is `VOLT` 48, `MANUAL` 22, and unset (MANUAL) 8.
  - `control_level` is `INDIVIDUAL` (the default) everywhere it is set.
  - `pt_phase` is a single phase except `ABCN` on 2.
  - `phases_connected` is wye everywhere (`ABC` 47, `ABCN` 5, 1-2 phases 26); none is delta.
  - Switches: CLOSED on 32 (all three phases), unset on 45 (GridLAB-D's default OPEN), OPEN on 1 (IEEE13_assets
    cap1).
  - 24 taxonomy 1-phase capacitors also give `capacitor_X` on unconnected phases, which GridLAB-D ignores
    (`capacitor.cpp:1447-1454`).
  - No deck sets `remote_sense`, `VAR`/`VARVOLT`/`CURRENT`, a delta `pt_phase`, the `*_deadband_center` forms or
    `lockout_time`.

```
# IEEE13_cdpsm ld_670a (one GLM load on 670, three phases) and ld_692 (delta, only phase C = branch CA)
Table EnergyConsumer: mRID, name, node, phases, phaseConnection, grounded, p (W), q (VAr), LoadResponse, BaseVoltage, EquipmentContainer=fdr_IEEE13_cdpsm
    ld_ld_670a, ld_670a, 670, ABC, Y, true,  200000, 116000, zip_constant_i, bv_4p16kv
    ld_ld_692,  ld_692,  692, AC,  D, false, 170000, 151000, zip_constant_i, bv_4p16kv
Update Table EnergyConsumerPhase: mRID, p (W), q (VAr)
    ld_ld_670a_A, 17000,  10000                        # and _B 66 + 38j, _C 117 + 68j kVA
# taxonomy: power_12 on a triplex_node (240 V across the legs)
Table EnergyConsumer: ...
    ld_R1-12-47-1_tn_1_12, R1-12-47-1_tn_1_12, R1-12-47-1_tm_1, s1s2, D, false, 1530, 410, zip_constant_pq, bv_240v
# taxonomy VOLT capacitor, phases_connected ABC, pt_phase B, switches unset (OPEN), under S4a-8 (a)
Table LinearShuntCompensator: mRID, name, node, phases, phaseConnection, grounded, nomQ (VAr), nomU (V), bPerSection (S), sections, normalSections, maximumSections, BaseVoltage, EquipmentContainer
    cap_R1-12-47-1_cap_1_B, R1-12-47-1_cap_1_B, R1-12-47-1_node_422, B, Y, true, 300000, 7200, 0.00579, 0, 0, 1, ...
Table RegulatingControl: mRID, name, mode=voltage, discrete=true, enabled=true, monitoredPhase, targetValue, targetDeadband, Terminal
    cc_R1-12-47-1_cap_1_B, R1-12-47-1_cap_1_B, B, 7200, 200, cap_R1-12-47-1_cap_1_B_T1
```

(Values in the example are illustrative; the goldens hold the real ones.)

### Slots (load, triplex_load, triplex_node)

| GLM slot | kind | target |
|---|---|---|
| `name` | derived | `EnergyConsumer.name`; mRID `ld_` + name (the 240 V part `_12`) |
| `parent` / the record | structural | `node`: the root bus (GLM-4) |
| `phases` | structural | wye unless it has D. `phases` on the consumer = the phases that carry power (S4a-1); S raises on a `load` |
| `constant_power_X` (`power_1`/`_2`/`_12`) | copied | the phase's p + jq, VA via pint; consumption is positive p |
| `base_power_X` + `*_fraction_X` + `*_pf_X` | derived | GridLAB-D's split at nominal voltage (S4a-3); a `<schedule>.value*K` base is K (S4a-2) |
| `constant_current_X`, `constant_impedance_X`, `_AN`/`_AB` forms | structural | raise when set (S4a-5) |
| `load_class`, `load_priority` | untranscribed | sorting only (`load.cpp:518`); `load_priority` is read by nothing |
| `nominal_voltage` | structural | the bus's (S1); not read again |
| `measured_*`, `phase_loss_protection`, `inrush_*`, frequency dependence | untranscribed | solver output or engine options |

### Slots (capacitor)

| GLM slot | kind | target |
|---|---|---|
| `name` | derived | `LinearShuntCompensator.name` = name, or name_<phase> for a per-phase unit (S4a-8); mRID `cap_` + that, the control `cc_` + that |
| `phases_connected` (else `phases`) | structural | the unit's phases, wye and grounded (S4a-11); D raises |
| `capacitor_X` | derived | the phase's VAr via pint; `nomQ` = the unit's sum, `bPerSection` = nomQ / nomU² (S4a-10); a phase not connected is dropped and listed in the row comment |
| `cap_nominal_voltage` | derived | `nomU`: the phase-to-neutral rating (else the bus's `nominal_voltage`, `capacitor.cpp:376`), × √3 on a 2- or 3-phase unit (CIM's line voltage) |
| `switchA`/`B`/`C` | derived | `sections` = `normalSections` = 1 CLOSED, 0 OPEN, default OPEN (S4a-9); `maximumSections` 1 |
| `control` | structural | VOLT: a `RegulatingControl` (S4a-12); MANUAL (default): none; VAR, VARVOLT, CURRENT raise |
| `control_level` | structural | the units (S4a-8) |
| `pt_phase` | structural | which units the control switches; with D it raises |
| `voltage_set_low`, `voltage_set_high` | derived | `targetValue` = the midpoint, `targetDeadband` = high - low (`band_from_on_off`) |
| `dwell_time`, `time_delay` | derived | `aVRDelay` = dwell_time + time_delay (s), as S3c-5 |
| `remote_sense`, `remote_sense_B`, `*_deadband_center`, `*_deadband` | structural | raise when set |
| `VAr_set_*`, `current_set_*`, `lockout_time` | untranscribed | read only by the unmapped modes |
| `cap_X_switch_count` | untranscribed | solver output |

### Fail fast (S4a)

The mapper raises on:
- `base_power_X` and `constant_power_X` both set on one phase, since GridLAB-D keeps only the base form
  (`load.cpp:984`);
- an expression other than `<name>.value*<number>`;
- every unmapped form listed above;
- a capacitor with no capacitance on a connected phase, or no `cap_nominal_voltage` and no bus voltage;
- a gang unit whose phases' switch states or kVAr differ (S4a-8, S4a-10).

### Decisions for S4a

| # | topic | proposal |
|---|---|---|
| S4a-1 | Load shape | One `EnergyConsumer` per GLM load (GLM-8). A load with no power on any phase is a consumer of p = q = 0 on its wired phases (a split-phase record on s1s2), listed in the artifact header (amended 2026-11-16 for the Clallam decks, where every Milsoft consumer is a service: earlier it wrote only a bus; the draft raised). Each record is one service: `customerCount` 1 on its first consumer, unset on a split-phase record's 240 V part (defaulted: GLM has no customer count). Its `phases` are the phases that carry power. On wye these are the letters with a value. On delta they are the letters of the set branches: GLM's A/B/C on a D load are AB/BC/CA (`node.cpp:2535`), so `ld_692`'s phase C is `AC`, as DSS's `CA`. An unset branch inside those letters gets 0. Wye is `Y`, grounded; delta is `D`, not grounded. `p`/`q` on the consumer are the totals. When its phase children differ, each gets an `Update Table EnergyConsumerPhase` row with its p and q (the binder's `ld_x_A`, or `ld_x_AB` on delta), which the load getter reads (`split` False). Equal children, and a single child (one delta branch such as `ld_692`'s `AC`, or the 240 V part), get no rows: the consumer's total is the value. The load getter requires valued children to be the conductors, which one delta branch on two conductors is not, and an equal `ABC` load leaves `phases` blank, as the core load shape's balanced device |
| **S4a-2** | **Schedule-scaled base (approved, with a TODO)** | **`<name>.value*K` is K: CIM's p is the base, and a schedule only scales it over time, as DSS-11 keeps a load's kW and lists its load shape untranscribed. The reference goes in the row comment. Any other expression raises. This amends GLM-8, which said a scheduled base raises. Without it the three Java exports (103 loads) do not map.** TODO (the user, 2026-11-10): map the schedule to the CGMES schedule classes (cim18v17 has `ConformLoadSchedule` and `SeasonDayTypeSchedule`) once profile export works again; it is broken today |
| S4a-3 | Base power form | As GridLAB-D does at nominal voltage (`load.cpp:940-1073`, `triplex_load.cpp:410-731`). Per part k (power, current, impedance), with `pf` defaulting to 1: P_k = base × f_k × \|pf_k\| and Q_k = P_k × √(1/pf_k² - 1), negative when pf_k < 0 (leading). pf_k = 0 gives P_k = 0 and Q_k = base × f_k. When the fractions don't sum to 1, the power fraction becomes 1 - I - Z (GridLAB-D's own repair, `load.cpp:945`), noted as `defaulted:` |
| S4a-4 | Voltage response | ZIP fractions from the load's totals (each part's P and Q over the totals). When every part is one kind, the shared `zip_constant_pq`/`_i`/`_z` row (core `zip_fractions.cimtbl`, which the master imports as DSS's does); otherwise a `zip_<pP>_<pI>_<pZ>_<qP>_<qI>_<qZ>` row in the artifact (GDM's naming; the mRID rounds the fractions to 6 places, the row holds them exactly, and two sets that round alike raise). When Q is 0, the Q fractions are the P fractions. Two artifacts that both use one mixed set would both write the row and fail to bind; no deck has a mixed set. Every deck is one kind: taxonomy constant power, Java exports constant current |
| **S4a-5** | **Explicit current and impedance (approved)** | **`constant_current_X`, `constant_impedance_X`, the `_AN`/`_AB` forms, and `current_*`/`shunt_*` on triplex nodes raise until a deck sets them. They carry angle conventions that no deck exercises: the current is relative to the nominal phasor (0/-120/+120, +30 on delta; `solver_nr.cpp:9409`), and triplex leg 2 has reversed polarity (`node.cpp:1233`). This amends GLM-8, which said they derive** |
| S4a-6 | Split phase | `_1` → s1 and `_2` → s2 are 120 V legs to neutral: one consumer on `s1s2` (or `s1`, `s2`), `Y`, grounded, as the core load shape and DSS's `ld_house`. `_12` is 240 V across the legs: a second consumer `ld_<name>_12` on `s1s2`, `D`, not grounded. The taxonomy has only `_12`, so one D consumer each |
| S4a-7 | Artifacts | One per native class: `load.cimtbl`, `triplex_load.cimtbl`, `triplex_node.cimtbl` (plain `triplex_node`s that carry power). Load slots on any other bus class (node, meter, triplex_meter) raise |
| **S4a-8** | **Capacitor units (option (a), the user's call)** | **GridLAB-D switches each phase separately. Under INDIVIDUAL (the default, all 70 that set it), VOLT switches only the `pt_phase` phases, each on its own phase voltage (`capacitor.cpp:1180-1205`). The other phases stay at their initial state, by default OPEN. (a) Recommended, as S3c's INDIVIDUAL units: one unit per set of phases that switch together. MANUAL or unset is one gang unit, whose switch states must agree (raise otherwise, as S3a's per-phase switch states). Automatic INDIVIDUAL is one 1-phase unit per connected phase, `cap_<name>_<phase>`, with a control on the units whose phase is in `pt_phase`. BANK is one gang unit (no deck). Under (a), 34 taxonomy 3-phase capacitors with `pt_phase B` have phases A and C fixed OPEN, as GridLAB-D runs them, and only B switches. (b) One gang unit per capacitor, controlled on `pt_phase`, as a DSS CapControl would be: all three phases switch on B, which GridLAB-D does not do** |
| S4a-9 | Initial state | `sections` = `normalSections` = the switch state as GridLAB-D starts it: 1 CLOSED, 0 OPEN, OPEN when unset (`capacitor.cpp:151-195`); never overridden. 45 taxonomy capacitors start OPEN |
| S4a-10 | Rating | `nomQ` = the sum of the unit's `capacitor_X` (VAr via pint). `nomU` = `cap_nominal_voltage` (LN) × √3 on 2-3 phases. `bPerSection` = nomQ / nomU², which the shunt getter reads back as Q = b × nomU² × sections; on one phase it is GridLAB-D's capacitor_X / Vc² (`capacitor.cpp:394`). Every gang unit in the decks is balanced, so no per-phase b is written; an unbalanced gang unit raises, and the shunt getter keeps its own raise |
| S4a-11 | Connection | `phases_connected` without D is wye, grounded, with or without N: GridLAB-D puts the shunt phase to ground either way. Ungrounded would change the physics on export. D raises (no deck; GridLAB-D's delta rates on LN², `capacitor.cpp:1398`) |
| S4a-12 | VOLT control | `RegulatingControl` mode voltage, discrete, enabled. It monitors the unit's own terminal (`_T1`) on the unit's phase (a gang unit's: `pt_phase`, one phase or raise). Target and deadband come from `band_from_on_off(voltage_set_low, voltage_set_high)` in primary volts, LN, with no PT: closes at or below low, opens at or above high (`capacitor.cpp:1180`). `aVRDelay` = dwell_time + time_delay, `controlEnabled` true, by the shunt shape's `Update` row. MANUAL has no control; any set points it carries go in the row comment |

**Cross-solver note on S4a-8 (the user asked for it, 2026-11-10, so capacitor controls can be checked across
solvers):** a GLM capacitor is mapped as GridLAB-D runs it, not as a DSS CapControl would.
- Under option (a), the taxonomy's 3-phase VOLT capacitors with `pt_phase B` become three 1-phase units. Only B has a
  control; A and C stay at their initial state, OPEN when the deck doesn't set it. Exported to OpenDSS, that is three
  1-phase capacitors and one CapControl on B: GridLAB-D's behaviour, kept.
- Option (b), not taken, was one gang unit switched on B. That is what the DSS import of a DSS-authored deck gives,
  and likely what the taxonomy authors meant.
- So on these 34 capacitors a GLM → CIM → DSS run and a DSS-native run of "the same" feeder are expected to differ:
  up to two thirds of each bank's kVAr, whenever B closes.
- A cross-format check should compare per-phase switched kVAr against GridLAB-D's own solution, not against the DSS
  golden, and list these capacitors as an expected divergence.
- MANUAL capacitors are one gang unit under both options, so they don't diverge.

**Expected differences vs the DSS import of IEEE 13:**
- The Java export wrote every load as constant current (its ZIP option), where DSS has PQ, Z and I.
- GLM holds one load per node: `ld_670a` carries 670a/b/c as phases. So the comparison is per node and phase:
  p and q agree to the Java export's 0.01 VA.
- The house is `s1s2`, wye, 5 kW + 3.0987 kVAr in both.
- The capacitors match: MANUAL and CLOSED, cap1 600 kVAr at 4.16 kV, cap2 100 kVAr at 2.4 kV.

**Core work in S4a (plan section 7 rows 249-250):**
- The `load` shape gains an unbalanced example with `Update Table EnergyConsumerPhase` rows, a delta branch, and a
  240 V `s1s2` D consumer.
- The `shunt` shape stays as is, since S4a-10 writes no per-phase b.

**Tests.**
- An atom `tests/atoms/load/load.glm` on the line atom:
  - constant power on two wye phases;
  - a delta load on one branch;
  - the base form with mixed fractions and a negative pf, plus fractions that don't sum to 1;
  - a scheduled base;
  - a triplex_load with legs and `_12`;
  - a triplex_node `power_12`.
- An atom `tests/atoms/capacitor/capacitor.glm`:
  - a MANUAL gang unit;
  - a VOLT INDIVIDUAL 3-phase capacitor with `pt_phase B` and switches unset;
  - a 1-phase VOLT capacitor with a value on an unconnected phase;
  - a BANK.
- Goldens for both atoms and for IEEE13_cdpsm.
- GridLAB-D's math against the bound objects on every deck: per-phase p and q from the native record, b × V² =
  capacitor_X, and controls on exactly the `pt_phase` units.
- The fail-fast cases.
- The deck sweep.

### Built (2026-11-10)

- **Code:**
  - `importer/cimtbl/load.py`: load, triplex_load and the plain triplex_node's power.
  - `importer/cimtbl/capacitor.py`.
  - `bus.py`: a bus's own load accumulators raise (`BUS_LOAD`, `check_bus_loads`), and a plain triplex_node's
    `power_1`/`_2`/`_12` are now this slice's. `classify` takes a device's own slots.
  - The orchestrator imports the core `zip_fractions.cimtbl`, and lets a load's scheduled base through the
    expression guard (`load.EXPRESSION_SLOTS`).
- **Core:** the `load` shape gained an unbalanced consumer with `Update Table EnergyConsumerPhase` rows and a 240 V
  `s1s2` D consumer, with two getter tests. The `shunt` shape is unchanged, since S4a-10 writes no per-phase b.
- **Found at build:**
  - A load with no power is a consumer of p = q = 0, listed in the header rather than raising (S4a-1, amended
    2026-11-16).
  - A single delta branch and the 240 V part take no per-phase row: the load getter requires valued children to be
    the conductors.
  - A zip_ row holds its fractions exactly, and only its mRID is rounded (the getter checks the sum to 1e-6).
  - Each row comment lists only the device's own untranscribed values; its inherited bus slots (the solver's initial
    `voltage_X`) are counted once on the table comment.
- **Tests:**
  - `tests/test_cimtbl_load.py` and `tests/test_cimtbl_capacitor.py`, with the atoms `tests/atoms/load/`
    (`load.glm`, `triplex.glm`) and `tests/atoms/capacitor/`.
  - Goldens for the atoms and for IEEE13_cdpsm (`load`, `triplex_load`, `capacitor`).
  - Every deck reads through the core load, shunt and control getters, against GridLAB-D's formulas written out
    again in the test.
- **Results:**
  - 412 GLM tests pass with `--roundtrip` over every deck.
  - 27 decks bind; the same two deck defects stop the other two.
  - The decks give 9,025 consumers, 162 capacitor units (34 closed at start) and 46 VOLT controls.
  - IEEE13_cdpsm matches the DSS golden per node and phase to the Java export's 0.01 VA. Its two capacitors equal
    DSS's.

### Field tables (generated: `fields_table(cls, records, fields=OWN)`, samples from tests/decks and the atoms)

#### `load` (its own slots; its bus slots are S1's, with the load accumulators raising, S4a-7)

| Load field | type | samples | kind | target |
|---|---|---|---|---|
| `load_class` | `Optional[str]` | `I`, `C`, `R` | untranscribed | for sorting only (load.cpp:518) |
| `load_priority` | `Optional[str]` |  | untranscribed | read by nothing in powerflow |
| `constant_power_A` | `Union[dict, Complex, NoneType]` | `Complex({'real': 585277.7504, 'imag':...`, `Complex({'real': 0.0, 'imag': 0.0})`, `Complex({'real': 110387.6944, 'imag':...` | copied | `EnergyConsumer.p` (VA), `EnergyConsumer.q` (VA); the phase's p + jq, VA via pint; with base_power_X raises |
| `constant_power_B` | `Union[dict, Complex, NoneType]` | `Complex({'real': 596917.157, 'imag': ...`, `Complex({'real': 9908.4297, 'imag': 3...`, `Complex({'real': 19800.0, 'imag': 600...` | copied | `EnergyConsumer.p` (VA), `EnergyConsumer.q` (VA); the phase's p + jq, VA via pint; with base_power_X raises |
| `constant_power_C` | `Union[dict, Complex, NoneType]` | `Complex({'real': 592476.6189, 'imag':...`, `Complex({'real': 54848.3315, 'imag': ...`, `Complex({'real': 16454.4994, 'imag': ...` | copied | `EnergyConsumer.p` (VA), `EnergyConsumer.q` (VA); the phase's p + jq, VA via pint; with base_power_X raises |
| `constant_power_A_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_B_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_C_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_A_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_B_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_C_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_A` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_B` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_C` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_A_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_B_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_C_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_A_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_B_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_C_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_A` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_B` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_C` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_A_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_B_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_C_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_A_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_B_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_C_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_AN` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_BN` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_CN` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_AN_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_BN_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_CN_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_AN_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_BN_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_CN_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_AN` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_BN` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_CN` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_AN_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_BN_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_CN_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_AN_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_BN_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_CN_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_AN` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_BN` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_CN` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_AN_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_BN_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_CN_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_AN_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_BN_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_CN_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_AB` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_BC` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_CA` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_AB_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_BC_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_CA_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_AB_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_BC_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_CA_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_AB` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_BC` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_CA` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_AB_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_BC_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_CA_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_AB_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_BC_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_CA_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_AB` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_BC` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_CA` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_AB_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_BC_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_CA_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_AB_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_BC_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_CA_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `measured_voltage_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `measured_voltage_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `measured_voltage_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `measured_voltage_AB` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `measured_voltage_BC` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `measured_voltage_CA` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `phase_loss_protection` | `Union[bool, Bool, NoneType]` |  | untranscribed | engine option |
| `measured_power_A` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `measured_power_B` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `measured_power_C` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `measured_power` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `base_power_A` | `Optional[float]` | `100.0` | derived | GridLAB-D's split at nominal voltage (S4a-3): P = base x fraction x |pf|, Q = P x sqrt(1/pf^2 - 1), negative on a negative pf; pf 0 is all Q; <schedule>.value*K is K (S4a-2) |
| `base_power_B` | `Optional[float]` |  | derived | GridLAB-D's split at nominal voltage (S4a-3): P = base x fraction x |pf|, Q = P x sqrt(1/pf^2 - 1), negative on a negative pf; pf 0 is all Q; <schedule>.value*K is K (S4a-2) |
| `base_power_C` | `Optional[float]` | `50000.0` | derived | GridLAB-D's split at nominal voltage (S4a-3): P = base x fraction x |pf|, Q = P x sqrt(1/pf^2 - 1), negative on a negative pf; pf 0 is all Q; <schedule>.value*K is K (S4a-2) |
| `power_pf_A` | `Optional[float]` | `0.9` | derived | with base_power; default 1 |
| `current_pf_A` | `Optional[float]` | `0.824042`, `0.83005`, `0.861934` | derived | with base_power; default 1 |
| `impedance_pf_A` | `Optional[float]` |  | derived | with base_power; default 1 |
| `power_pf_B` | `Optional[float]` |  | derived | with base_power; default 1 |
| `current_pf_B` | `Optional[float]` | `0.8`, `0.805651`, `0.867313` | derived | with base_power; default 1 |
| `impedance_pf_B` | `Optional[float]` |  | derived | with base_power; default 1 |
| `power_pf_C` | `Optional[float]` |  | derived | with base_power; default 1 |
| `current_pf_C` | `Optional[float]` | `0.904819`, `0.8`, `0.864582` | derived | with base_power; default 1 |
| `impedance_pf_C` | `Optional[float]` |  | derived | with base_power; default 1 |
| `power_fraction_A` | `Optional[float]` | `0.5` | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `current_fraction_A` | `Optional[float]` | `1.0`, `0.3` | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `impedance_fraction_A` | `Optional[float]` | `0.2` | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `power_fraction_B` | `Optional[float]` |  | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `current_fraction_B` | `Optional[float]` | `1.0` | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `impedance_fraction_B` | `Optional[float]` |  | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `power_fraction_C` | `Optional[float]` |  | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `current_fraction_C` | `Optional[float]` | `1.0`, `0.6` | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `impedance_fraction_C` | `Optional[float]` |  | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `inrush_integration_method_capacitance` | `Optional[str]` |  | untranscribed | engine option |
| `inrush_integration_method_inductance` | `Optional[str]` |  | untranscribed | engine option |


#### `triplex_load` (its own slots; its bus slots are S1's, with the load accumulators raising, S4a-7)

| TriplexLoad field | type | samples | kind | target |
|---|---|---|---|---|
| `load_class` | `Union[str, ForwardRef('LoadClass'), NoneType]` |  | untranscribed | for sorting only (load.cpp:518) |
| `load_priority` | `Union[str, ForwardRef('LoadPriority'), NoneType]` |  | untranscribed | read by nothing in powerflow |
| `constant_power_1` | `Union[dict, Complex, NoneType]` | `Complex({'real': 2500.0, 'imag': 1000...` | copied | `EnergyConsumer.p` (VA), `EnergyConsumer.q` (VA); the phase's p + jq, VA via pint; with base_power_X raises |
| `constant_power_2` | `Union[dict, Complex, NoneType]` | `Complex({'real': 2000.0, 'imag': 800.0})` | copied | `EnergyConsumer.p` (VA), `EnergyConsumer.q` (VA); the phase's p + jq, VA via pint; with base_power_X raises |
| `constant_power_12` | `Union[dict, Complex, NoneType]` | `Complex({'real': 4000.0, 'imag': 1500...` | copied | `EnergyConsumer.p` (VA), `EnergyConsumer.q` (VA); the phase's p + jq, VA via pint; with base_power_X raises |
| `constant_power_1_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_2_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_12_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_1_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_2_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_power_12_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_1` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_2` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_12` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_1_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_2_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_12_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_1_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_2_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_current_12_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_1` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_2` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_12` | `Union[dict, Complex, NoneType]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_1_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_2_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_12_real` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_1_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_2_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `constant_impedance_12_reac` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (S4a-5) |
| `measured_voltage_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `measured_voltage_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `measured_voltage_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `indiv_measured_power_1` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `indiv_measured_power_2` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `indiv_measured_power_12` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `measured_power` | `Union[dict, Complex, NoneType]` |  | untranscribed | solver output |
| `base_power_1` | `Optional[float]` |  | derived | GridLAB-D's split at nominal voltage (S4a-3): P = base x fraction x |pf|, Q = P x sqrt(1/pf^2 - 1), negative on a negative pf; pf 0 is all Q; <schedule>.value*K is K (S4a-2) |
| `base_power_2` | `Optional[float]` |  | derived | GridLAB-D's split at nominal voltage (S4a-3): P = base x fraction x |pf|, Q = P x sqrt(1/pf^2 - 1), negative on a negative pf; pf 0 is all Q; <schedule>.value*K is K (S4a-2) |
| `base_power_12` | `Optional[float]` |  | derived | GridLAB-D's split at nominal voltage (S4a-3): P = base x fraction x |pf|, Q = P x sqrt(1/pf^2 - 1), negative on a negative pf; pf 0 is all Q; <schedule>.value*K is K (S4a-2) |
| `power_pf_1` | `Optional[float]` |  | derived | with base_power; default 1 |
| `current_pf_1` | `Optional[float]` | `0.85` | derived | with base_power; default 1 |
| `impedance_pf_1` | `Optional[float]` |  | derived | with base_power; default 1 |
| `power_pf_2` | `Optional[float]` |  | derived | with base_power; default 1 |
| `current_pf_2` | `Optional[float]` | `0.85` | derived | with base_power; default 1 |
| `impedance_pf_2` | `Optional[float]` |  | derived | with base_power; default 1 |
| `power_pf_12` | `Optional[float]` |  | derived | with base_power; default 1 |
| `current_pf_12` | `Optional[float]` |  | derived | with base_power; default 1 |
| `impedance_pf_12` | `Optional[float]` |  | derived | with base_power; default 1 |
| `power_fraction_1` | `Optional[float]` |  | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `current_fraction_1` | `Optional[float]` | `1.0` | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `impedance_fraction_1` | `Optional[float]` |  | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `power_fraction_2` | `Optional[float]` |  | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `current_fraction_2` | `Optional[float]` | `1.0` | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `impedance_fraction_2` | `Optional[float]` |  | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `power_fraction_12` | `Optional[float]` |  | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `current_fraction_12` | `Optional[float]` |  | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |
| `impedance_fraction_12` | `Optional[float]` |  | derived | with base_power; default 0, the power fraction 1 - I - Z when they don't sum to 1 |


#### `capacitor` (its own slots; its bus slots are S1's, with the load accumulators raising, S4a-7)

| Capacitor field | type | samples | kind | target |
|---|---|---|---|---|
| `pt_phase` | `Optional[str]` | `ABCN`, `A`, `B` | structural | VOLT: the units that get a control (INDIVIDUAL) or the gang unit's monitored phase (BANK); D raises |
| `phases_connected` | `Optional[str]` | `ABCN`, `CN`, `AN` | structural | the connected phases (else phases): wye, grounded with or without N (S4a-11); D raises |
| `switchA` | `Optional[str]` | `CLOSED`, `OPEN` | derived | sections = normalSections: 1 CLOSED, 0 OPEN; default OPEN (S4a-9); a gang unit's must agree |
| `switchB` | `Optional[str]` | `CLOSED`, `OPEN` | derived | sections = normalSections: 1 CLOSED, 0 OPEN; default OPEN (S4a-9); a gang unit's must agree |
| `switchC` | `Optional[str]` | `CLOSED`, `OPEN` | derived | sections = normalSections: 1 CLOSED, 0 OPEN; default OPEN (S4a-9); a gang unit's must agree |
| `control` | `Union[str, ForwardRef('Control'), NoneType]` | `VOLT` | structural | VOLT: a RegulatingControl; MANUAL (default): none; VAR, VARVOLT, CURRENT raise |
| `cap_A_switch_count` | `Optional[float]` |  | untranscribed | solver output |
| `cap_B_switch_count` | `Optional[float]` |  | untranscribed | solver output |
| `cap_C_switch_count` | `Optional[float]` |  | untranscribed | solver output |
| `voltage_set_high` | `Optional[float]` | `2500.0`, `2600.0`, `7300.0` | derived | targetValue = the midpoint, targetDeadband = high - low (band_from_on_off); opens at or above it |
| `voltage_set_low` | `Optional[float]` | `1950.0`, `2050.0`, `7200.0` | derived | with voltage_set_high; closes at or below it |
| `voltage_deadband_center` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one |
| `voltage_deadband` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one |
| `VAr_set_high` | `Optional[float]` |  | untranscribed | read only by the VAR, VARVOLT and CURRENT modes |
| `VAr_set_low` | `Optional[float]` |  | untranscribed | read only by the VAR, VARVOLT and CURRENT modes |
| `VAr_deadband_center` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one |
| `VAr_deadband` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one |
| `current_set_low` | `Optional[float]` |  | untranscribed | read only by the VAR, VARVOLT and CURRENT modes |
| `current_set_high` | `Optional[float]` |  | untranscribed | read only by the VAR, VARVOLT and CURRENT modes |
| `current_deadband_center` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one |
| `current_deadband` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one |
| `capacitor_A` | `Optional[float]` | `200000.0`, `0.3`, `0.25` | derived | the phase's VAr via pint: nomQ = the unit's sum, bPerSection = nomQ / nomU^2 (S4a-10); on a phase not connected: dropped, GridLAB-D ignores it (capacitor.cpp:1447) |
| `capacitor_B` | `Optional[float]` | `200000.0`, `0.3`, `0.25` | derived | the phase's VAr via pint: nomQ = the unit's sum, bPerSection = nomQ / nomU^2 (S4a-10); on a phase not connected: dropped, GridLAB-D ignores it (capacitor.cpp:1447) |
| `capacitor_C` | `Optional[float]` | `200000.0`, `100000.0`, `0.3` | derived | the phase's VAr via pint: nomQ = the unit's sum, bPerSection = nomQ / nomU^2 (S4a-10); on a phase not connected: dropped, GridLAB-D ignores it (capacitor.cpp:1447) |
| `cap_nominal_voltage` | `Optional[float]` | `2401.78`, `2400.0`, `2402.0` | derived | nomU: the phase-to-neutral rating (else nominal_voltage, capacitor.cpp:376), x sqrt 3 on 2-3 phases |
| `time_delay` | `Optional[float]` | `0.0`, `300.0`, `30.0` | derived | aVRDelay = dwell_time + time_delay (s), as S3c-5 |
| `dwell_time` | `Optional[float]` | `0.0`, `30.0`, `15.0` | derived | with time_delay |
| `lockout_time` | `Optional[float]` |  | untranscribed | read only by VARVOLT |
| `remote_sense` | `Optional[str]` |  | structural | raises when set: no deck sets it, so a mapping waits for one |
| `remote_sense_B` | `Optional[str]` |  | structural | raises when set: no deck sets it, so a mapping waits for one |
| `control_level` | `Union[str, ForwardRef('ControlLevel'), NoneType]` | `INDIVIDUAL`, `BANK` | structural | the units (S4a-8): INDIVIDUAL (default) VOLT is a unit per phase |

## S4b: inverters, solar and batteries (approved and built 2026-11-10)

S4b maps `inverter` with its nested `solar` or `battery` (GLM-13), plan section 2 row 14. GridLAB-D citations are to
`generators/inverter.cpp`, `solar.cpp` and `battery.cpp`.

**The user's calls (2026-11-10):**
- **S4b-2:** follow GridLAB-D's logic. The output is what GridLAB-D computes, not the `P_Out` the Java export wrote.
  The PV's irradiance goes on `PhotoVoltaicUnit.irradiance` (an SSH extension, added to cim18v17 the same day) and
  its panel data on `SolarArrayInfo`/`SolarPanelInfo`.
- **A battery under `CONSTANT_PF` is a Java export defect:** GridLAB-D never dispatches it (S4b-2). It is read as
  `CONSTANT_PQ`, the mode the Java export meant, whose set point is `P_Out`.
- **S4b-5:** `ratedU` is the real line-to-line voltage, matching the transformer's `PowerTransformerEnd.ratedU` and
  the bus's `BaseVoltage.nominalVoltage` (line to line). Asked whether GridLAB-D tells a wye inverter from a delta
  one, which would put a wye inverter at 120 V: it has no delta inverter (`phases` takes A, B, C, N and S only,
  `inverter.cpp:260-265`).
  - **A, B, C:** wye, injecting on `voltage_A`/`_B`/`_C` (`:897`).
  - **Split phase:** connected across the legs, on `voltage_12`/`current_12` at 240 V (`:861`, `:871`). That is
    `s1s2` D (S4b-4), as S4a-6's 240 V load part, so its ratedU is 240 V, not a 120 V leg.
- **The control modes** are described, at least as capabilities, by `InverterCapabilities`.

The user rebuilt cim18v17 the same day. It adds `PhotoVoltaicUnit.irradiance`, the `InverterInfo` and
`GridEdgeDeviceInfo` attributes, and `InverterInfo.InverterCapabilities` (its typo is fixed and reported upstream).

| # | artifact | native class (records) | CIM | mRID |
|---|---|---|---|---|
| 14 | `inverter.cimtbl` | inverter (5) with its solar (2) or battery (3) | `PowerElectronicsConnection` + `PhotoVoltaicUnit` or `BatteryUnit`; the datasheets below | `pv_<inverter>` / `storage_<inverter>`, the unit `<connection>_unit` |

**Datasheets** (`PowerSystemResource.AssetDatasheet`, the GDM import's pattern):
- **The inverter:** `GenerationInverterInfo` (under PV) or `StorageInverterInfo` (under a battery), `<connection>_info`.
  It holds `apparentPowerMaximum` = ratedS, `reactivePowerInjectedMax`/`AbsorbedMax` = ratedS, and on
  storage `chargeRateActiveMax` = `max_charge_rate`.
- **Its capabilities:** `InverterCapabilities` by S4b-11. Not written yet: cim-tables cannot reference an
  `Identity` row (amended at build, below); the flag goes in the row comment.
- **The solar:** a `SolarArrayInfo` `<connection>_array` (`tiltAngle`, `orientationAzimuth`, `shadingFactor`) with one
  `SolarPanelInfo` `<connection>_panel` (`efficiency`, `referenceIrradiation` = `Rated_Insolation`,
  `referenceTemperature` = 25 °C, the 77 °F GridLAB-D's temperature correction is relative to). The PhotoVoltaicUnit's
  AssetDatasheet is the array.
- **The battery:** a `BatteryInfo` `<connection>_battery` with `batteryType` (LI_ION → lithiumIon, LEAD_ACID →
  leadAcid), `ratedCapacity` = `battery_capacity`, and `numberOfCells` = floor(nominal_voltage / 4.1) on LI_ION
  (GridLAB-D's `n_series`, `battery.cpp:720`).

`InverterCapabilities` is an `Identity`, not an `IdentifiedObject`; whether the binder takes it as a row, and
`BatteryInfo.ratedCapacity`'s unit, are to be checked at build.

An inverter sits on its parent's root bus (GLM-4), whose `BaseVoltage` is already in `bus.cimtbl`. Its `solar` or
`battery` is its child: the reader gives it `parent = <inverter>`, and GridLAB-D requires a battery's parent to be an
inverter (`battery.cpp:657`).

**What the decks hold** (the 28 readable decks):
- **IEEE13_cdpsm** (Java export from the DSS IEEE 13 with DER) has 5 inverters:
  - **Solar:** `inv_pv_school` (ABCN) and `inv_pv_house` (BS), each with a `solar`.
  - **Batteries:** `inv_bat_school`, `inv_bat_batidle` (ABCN) and `inv_bat_house` (BS), each with a `battery`.
  - **Settings:** all are `FOUR_QUADRANT`, `CONSTANT_PF`, `power_factor` ±1, `generator_status ONLINE`,
    `inverter_efficiency` 1.0 (PV) or 0.975 (storage).
  - **Ratings and dispatch:** `rated_power` is written per phase. `V_base` is 480 or 208, and `P_Out` is the Java
    export's snapshot.
  - **The solars:** `SINGLE_CRYSTAL_SILICON`, `efficiency 0.2`, `derating`/`soiling 1`, `rated_power`. No area, no
    climate object, so GridLAB-D runs on static weather.
  - **The batteries:** each gives `battery_capacity`, `state_of_charge`, `round_trip_efficiency 0.86`, `rated_power`,
    `nominal_voltage 48`, `LI_ION` and the internal model. Their inverters set `generator_mode CONSTANT_PQ`,
    `sense_object` and the load-following thresholds, which `CONSTANT_PF` does not read.
- **IEEE123_transactive** has 5 `CONSTANT_PQ` inverters, but its `Object battery` lines stop it at the reader: a
  defect in the deck itself, since GridLAB-D's loader is case-sensitive (`gldcore/load.cpp:1393`).
- **Not set anywhere:** other inverter types, other `four_quadrant_control_mode`s, `use_multipoint_efficiency
  TRUE`, `climate`, other `SOLAR_POWER_MODEL`s or tilt models, `diesel_dg`, `windturb_dg`, `energy_storage` and
  `inverter_dyn`.

```
# IEEE13_cdpsm under S4b-2: GridLAB-D's static-weather PV output; the house battery read as CONSTANT_PQ (charging)
Table PowerElectronicsConnection: mRID, name, node, phases, phaseConnection, ratedS (VA), ratedU (V), p (W), q (VAr), maxQ (VAr), minQ (VAr), normallyInService, AssetDatasheet, BaseVoltage, EquipmentContainer=fdr_IEEE13_cdpsm
    # P_Out as written (GridLAB-D recomputes it): 240000 W
    pv_inv_pv_school,      inv_pv_school, 634,   ,     Y, 300000, 480, -298254.5, 0, 300000, -300000, true, pv_inv_pv_school_info,      bv_480v
    # four_quadrant_control_mode CONSTANT_PF read as CONSTANT_PQ (a Java export defect: GridLAB-D never dispatches a CONSTANT_PF battery)
    storage_inv_bat_house, inv_bat_house, house, s1s2, D, 5000,   240, 5000,      0, 5000,   -5000,   true, storage_inv_bat_house_info, bv_240v
Table PhotoVoltaicUnit: mRID, name, maxP (W), minP (W), irradiance (W/m^2), AssetDatasheet, PowerElectronicsConnection, EquipmentContainer=...
    pv_inv_pv_school_unit, pv_school, 300000, 0, 1000, pv_inv_pv_school_array, pv_inv_pv_school
Table BatteryUnit: mRID, name, ratedE (Wh), storedE (Wh), minimumE (Wh), maxP (W), minP (W), chargingEfficiency (percent), dischargingEfficiency (percent), batteryState, AssetDatasheet, PowerElectronicsConnection, EquipmentContainer=...
    storage_inv_bat_house_unit, bat_house, 13500, 5000.4, 0, 5000, -5000, 92.736, 92.736, charging, storage_inv_bat_house_battery, storage_inv_bat_house
```

(The example values are illustrative; the goldens will hold the real ones.)

### GridLAB-D's static-weather PV output (S4b-2)

With no climate object, the default tilt model (`DEFAULT`) and the default `SOLAR_POWER_MODEL` (`BASEEFFICIENT`),
GridLAB-D's snapshot is a closed form:
- **Insolation:** `Insolation` = `Rated_Insolation` × `shading_factor` (`solar.cpp:1170`). By default that is
  92.902 W/sf = 1000 W/m² × 1, and it goes on `PhotoVoltaicUnit.irradiance` (W/m² via pint).
- **Module temperature:** `Tmodule` = `Tamb` + (NOCT - 68) / 74.32 × Insolation, with `Tamb` = 59 °F (static,
  `solar.cpp:321`) and NOCT = 118.4 °F by default.
- **DC output:** `P_DC` = `rated_power` × Insolation / Rated_Insolation × (1 + Pmax_temp_coeff × (Tmodule - 77)) ×
  derating × soiling (`solar.cpp:1220`). `Pmax_temp_coeff` defaults by `panel_type`; SINGLE_CRYSTAL_SILICON's is
  -0.00437 / 33.8 per °F (`solar.cpp:563`).
- **AC output:** the inverter's `P_DC` × `inverter_efficiency` (`inverter.cpp:3290`), with each phase capped at
  rated_power: \|S\| ≤ p_max = phases out × rated_power (`:1415-1427`, `:3798`). `p` = -(that) in the load sign.

For IEEE 13: Tmodule = 122.0 °F, the factor is 0.99418, so `pv_school` gives -298.25 kW (P_Out written -240) and
`pv_house` -4.97 kW (written -4). The slots this uses with no CIM home (NOCT, Pmax_temp_coeff, derating, soiling,
inverter_efficiency) are listed as `derived` into p. A climate object, FIXED_AXIS and the other power models raise:
they need GridLAB-D's weather and solar position (no deck).

### Slots (inverter)

| GLM slot | kind | target |
|---|---|---|
| `name` | derived | `PowerElectronicsConnection.name`; mRID `pv_`/`storage_` + name by its unit (S4b-6) |
| `parent` | structural | `node`: the root bus (GLM-4) |
| `phases` | structural | 3 phases: blank (balanced, no children); 1-2 phases: the letters, `Y`; `S`: `s1s2` `D` (S4b-4). GridLAB-D has no D keyword on an inverter |
| `inverter_type` | structural | `FOUR_QUADRANT`; any other raises (S4b-1). Unset is GridLAB-D's PWM (`inverter.cpp:1350`), which also raises |
| `four_quadrant_control_mode` | structural | dispatch: `CONSTANT_PF` (the default, `inverter.cpp:515`) on a solar, `CONSTANT_PQ` on a battery, which also takes CONSTANT_PF as the Java defect (S4b-1, S4b-2); others raise. Capability: S4b-11, the mode as read |
| `rated_power` | derived | `ratedS` = rated_power × phases out: 3, 2, or 1 (S counts as 1; `inverter.cpp:1318-1326`, `:1415`); the per-phase cap of S4b-2; `apparentPowerMaximum`. Unset or 0 raises: GridLAB-D silently uses 25 kVA (`:1409`) |
| `inverter_efficiency` | derived | into p (S4b-2); CIM has no inverter efficiency. 0 or unset is GridLAB-D's 0.9 (`:1398`) |
| `P_Out` | derived | battery: the set point, p = -P_Out after GridLAB-D's CONSTANT_PQ limits (S4b-2). Solar: GridLAB-D overwrites it in CONSTANT_PF (`inverter.cpp:433`, `:3879`), so it is only listed in the row comment |
| `power_factor` | derived | CONSTANT_PF: `q` = 0 when \|pf\| = 1; \|pf\| < 1 raises (S4b-3). Not read by CONSTANT_PQ, so on a battery read as CONSTANT_PQ it goes in the row comment |
| `Q_Out` | derived | CONSTANT_PQ: `q` = 0 when unset or 0; any other value raises (S4b-3) |
| `V_base` | untranscribed | read only by the volt-var and volt-watt modes (`inverter.cpp:318`); ratedU is the bus's line-to-line voltage (S4b-5) |
| `generator_status` | derived | `normallyInService`: ONLINE (default) true, OFFLINE false |
| `soc_reserve` | derived | `BatteryUnit.minimumE` = soc_reserve × battery_capacity; default 0 |
| `max_charge_rate` | copied | `StorageInverterInfo.chargeRateActiveMax` (W via pint) |
| `generator_mode`, `sense_object`, `charge_*`/`discharge_*_threshold`, `*_lockout_time`, `max_discharge_rate` | untranscribed | read only by load following and the non-four-quadrant types, which raise (to be verified slot by slot at build) |
| volt-var, volt-watt, VSI, frequency-watt, group-PF, multipoint-efficiency and dynamic slots | untranscribed or raises | their modes raise for the dispatch. `use_multipoint_efficiency TRUE` raises |
| solver state (`VA_Out`, `I_In`, `phaseA_I_Out`, ...) | untranscribed | solver output |

### Slots (solar, battery)

| GLM slot | kind | target |
|---|---|---|
| solar `name` | derived | `PhotoVoltaicUnit.name`; mRID `<connection>_unit` |
| solar `rated_power` | derived | `maxP` (W via pint), `minP` 0, and P_DC (S4b-2). Unset raises (GridLAB-D derives it from area and insolation, `solar.cpp:606`) |
| solar `Rated_Insolation`, `shading_factor` | derived | irradiance (S4b-2); `SolarPanelInfo.referenceIrradiation`; `SolarArrayInfo.shadingFactor` (percent) |
| solar `efficiency` | copied | `SolarPanelInfo.efficiency` (percent); default by panel_type (`solar.cpp:561`) |
| solar `tilt_angle`, `orientation_azimuth` | copied | `SolarArrayInfo.tiltAngle`, `orientationAzimuth` (defaults 45, 180: `solar.cpp:195`) |
| solar `NOCT`, `Pmax_temp_coeff`, `derating`, `soiling`, `panel_type` | derived | into p (S4b-2) |
| solar `SOLAR_POWER_MODEL`, `orientation`, `weather` | structural | the defaults (BASEEFFICIENT, DEFAULT, none); others raise |
| solar DC and other model slots (`area`, `Voc`, `V_Max`, PV_CURVE parameters, ...) | untranscribed | DC side, read by no mapped path |
| battery `name` | derived | `BatteryUnit.name`; mRID `<connection>_unit` |
| battery `battery_capacity` | derived | `ratedE` (Wh via pint), `BatteryInfo.ratedCapacity` |
| battery `state_of_charge` | derived | `storedE` = state_of_charge × battery_capacity |
| battery `rated_power` | derived | `maxP` = rated_power, `minP` = -rated_power (the generation sign, as the DER getter reads it) |
| battery `round_trip_efficiency` | derived | `chargingEfficiency` = `dischargingEfficiency` = √round_trip_efficiency, in percent: GridLAB-D applies its square root each way (`battery.cpp:2220`, `:2230`). Default by `rfb_size`, else 0.8 (`battery.cpp:661-708`) |
| battery `battery_type`, `nominal_voltage` | derived | `BatteryInfo.batteryType`, `numberOfCells` |
| battery `use_internal_battery_model` | structural | true; false raises (the legacy model, no deck) |
| battery internal-model curve and DC slots | untranscribed | DC side; CIM has none |

### Fail fast (S4b)

The mapper raises on:
- an inverter with no `solar` or `battery`, or with more than one;
- a `solar` or `battery` whose parent is not an inverter;
- every unmapped type, mode and solar model listed above, and a climate object;
- `rated_power` unset or 0 on an inverter or a solar;
- \|power_factor\| < 1 under CONSTANT_PF, or a non-zero `Q_Out` under CONSTANT_PQ;
- a battery with no `battery_capacity`;
- CONSTANT_PQ on a solar (no deck: GridLAB-D then caps P at the panel's output).

### Decisions for S4b

| # | topic | proposal |
|---|---|---|
| S4b-1 | Modes (dispatch) | `FOUR_QUADRANT` only. A solar runs `CONSTANT_PF`; a battery runs `CONSTANT_PQ`, or `CONSTANT_PF` read as CONSTANT_PQ (the Java defect, S4b-2). IEEE123_transactive's CONSTANT_PQ batteries would take the same path, but that deck stops at the reader. Every other type and mode raises for the dispatch until a deck has one, as S4a-5; S4b-11 still describes its capability |
| **S4b-2** | **The dispatch (the user's calls: GridLAB-D's logic; the battery mode a Java defect)** | **PV: GridLAB-D's static-weather output (the section above), with the irradiance on `PhotoVoltaicUnit.irradiance`; the written P_Out is listed in the row comment. Battery: GridLAB-D's CONSTANT_PQ (`inverter.cpp:3485-3555`). The set point is P_Out (generation positive), set to 0 when charging a full battery (soc ≥ 1) or discharging at or below soc_reserve, and capped at ratedS; p = -that. A battery whose inverter says CONSTANT_PF is read as CONSTANT_PQ, with a row comment: under CONSTANT_PF GridLAB-D would never dispatch it. The inverter takes P from its DC input `V_In × I_In`, the internal battery writes back only `battery_soc` (`battery.cpp:891`), and the inverter asks for power (`power_in`) only in CONSTANT_PQ, VSI and load following (`inverter.cpp:3545`, `:3716`, `:3865`). The Java export wrote CONSTANT_PF on all three IEEE 13 batteries with P_Out as their dispatch: a producer defect (to report upstream), corrected here by the user's call** |
| S4b-3 | q | CONSTANT_PF: q = 0 when \|pf\| = 1 (all 5); \|pf\| < 1 raises. The sign of GridLAB-D's Q there is "treat like a normal load right now" (`inverter.cpp:3466-3475`), and no deck checks it |
| S4b-4 | Phases | GridLAB-D has no delta inverter (no D keyword, `inverter.cpp:260-265`). On A, B and C it is wye to neutral (`voltage_A`/`_B`/`_C`, `:897`): `Y`, grounded; 3 phases blank, CIM's balanced default, as the core `der` shape. Split phase `S` puts the whole output across the legs (`power_val[0]` on `voltage_12`/`current_12`, `:861`, `:871`, `:3432`): `s1s2` `D`, as S4a-6's 240 V load part. The core shape's `p2` and the DSS golden's `pv_house` say `s1s2` `Y`, two 120 V legs to neutral, which GridLAB-D's inverter is not |
| **S4b-5** | **ratedU (the user's call)** | **Line to line, the root bus's `BaseVoltage.nominalVoltage`, which matches the transformer's `ratedU`. 3-phase wye at 634: 480 V. Split phase across the legs: 240 V. That is the voltage it sits across, so a wye reading of 120 V does not apply (S4b-4). A 1- or 2-phase wye inverter is also its bus's line-to-line voltage, the core DER getter's convention (a 1-phase wye device's kV × √3). `V_base` (480, 208) is untranscribed** |
| S4b-6 | Shape and names | One `PowerElectronicsConnection` per inverter with its one unit. A hybrid (solar and battery under one inverter) raises: GridLAB-D has no such model. mRID `pv_<inverter>` or `storage_<inverter>` and `<connection>_unit`, the DSS import's prefixes; the datasheets `<connection>_info`, `_capabilities`, `_array`, `_panel`, `_battery`; names as written |
| S4b-7 | q limits, fault current | `maxQ` = ratedS, `minQ` = -ratedS: GridLAB-D's four-quadrant inverter caps \|S\| at p_max = phases out × rated_power (`inverter.cpp:3798`), as the DSS golden does. `maxIFault` is blank: GLM has no fault current in CONSTANT_PF |
| S4b-8 | Battery state | `batteryState` from the dispatch: discharging below 0 (load sign), charging above, waiting at 0. IEEE 13: school discharging (-100 kW), house charging (+5 kW), batidle charging (+1 kW: the Java export wrote DSS's idle loss as a charge). `idlingP` is blank: GLM has none |
| S4b-9 | Battery values | ratedE = battery_capacity, storedE = soc × capacity, minimumE = the inverter's soc_reserve × capacity (default 0), maxP/minP = ±battery rated_power, efficiencies √round_trip each way |
| S4b-10 | Order | `MAPPING_ORDER` gains `inverter` after `capacitor`. It references only buses and its own datasheets |
| S4b-11 | Capabilities | `InverterCapabilities` holds the `four_quadrant_control_mode` as read (S4b-2: a Java-defect battery is CONSTANT_PQ) as a capability flag: CONSTANT_PF → `isModeCapableConstantPowerFactor`, CONSTANT_PQ → `isModeCapableActivePowerReactivePower`, VOLT_VAR → `isModeCapableVoltageReactivePower`, VOLT_WATT → `isModeCapableVoltageActivePower`, VOLT_VAR_FREQ_PWR → the volt-var and frequency-watt flags. LOAD_FOLLOWING, GROUP_LF and VSI have no IEEE 1547 flag, so none is set. GridLAB-D runs one mode per inverter, so the other flags are left unset, not false |

**Cross-solver note on S4b-2, S4b-4 and S4b-5:** the GLM artifacts follow GridLAB-D, so the IEEE 13 DER differ from
the DSS golden (`cimhub_opendss/tests/goldens/IEEE13_CDPSM/{pvsystem,storage}.cimtbl`):
- **PV p:** -298.25 vs -240 kW on the school and -4.97 vs -4 kW on the house. GridLAB-D's static weather is full sun
  at 122 °F; DSS's irradiance multiplier gives 80 %.
- **Battery p:** equal (-100, +5, +1 kW; the school to 0.001 W, GridLAB-D's cap at 3 × 33333.333 VA), since the
  batteries are read as CONSTANT_PQ (S4b-2). But batidle is
  charging at 1 kW, where DSS says waiting with a 1 kW idling loss.
- **House inverters:** `s1s2` D at 240 V vs DSS's `s1s2` Y at 208 V. The DSS exporter must write a 240 V
  split-phase DER across the legs.
- **Battery values:** minimumE 0 vs 40 kWh, efficiencies 92.7 % vs 90 %, idlingP blank vs 1 kW.
- **Equal:** node, ratedS, q, maxQ/minQ, PV maxP/minP, ratedE, storedE and battery maxP/minP.

A cross-format check should list these as expected divergences, as for S4a-8's capacitors. The core `der` shape's `p2`
(`s1s2` Y, 208 V) should follow S4b-4/-5: a core follow-up (plan section 7).

### Built (2026-11-10)

- **Code:**
  - `importer/cimtbl/inverter.py`: the inverter with its solar or battery, the datasheets, and GridLAB-D's output
    (`pv_output`, `battery_output`). All 398 slots of the three classes are classified; one not in a group raises.
  - The orchestrator maps `inverter` after `capacitor` and classifies `solar` and `battery` with it.
  - `glm_schema.registry_unit` spells `pu` and `unit` as `dimensionless` and `sf`/`W/sf` as `ft**2`/`W/ft**2`.
    Pint read `pu` as a picounified atomic mass and `unit` as a micronit, and did not know `sf`.
- **Found at build (amendments):**
  - **`InverterCapabilities` is not written.** It is an `Identity`, so cim-tables keys it by `identifier`. cim-tables
    does not index an `Identity` row, so `InverterInfo.InverterCapabilities` cannot reference it
    (`CIM-Tables/docs/CIMTBL_DESIGN.md:141`). The row comment names the flag (`capability: ...`) until cim-tables can
    (plan section 7).
  - **`phaseCount` is dropped** from the inverter datasheet. It is an enum (`singlePhase`, `threePhase`, `other`) that
    only repeats the connection's phases.
  - **GridLAB-D's cap is on the total:** \|S\| ≤ p_max = phases out × rated_power (`inverter.cpp:3798`), not per phase.
    So IEEE 13's `inv_bat_school` gives -99,999.999 W, not -100 kW. Its `rated_power` is written 33333.333 per phase,
    and its P_Out of 100 kW is above that. The row comment says the set point was limited.
  - **The defaults are by path:** PV defaults `inverter_efficiency` and `power_factor`; a battery defaults `P_Out`,
    `Q_Out` and `soc_reserve`.
  - **A climate object is found by the reader's not-read count:** the schema has no `climate` class.
  - **A battery's `maxP` is its own `rated_power`,** its nameplate as written. GridLAB-D's internal model limits the
    battery at the inverter's `rated_battery_power`, phases out × rated_power / inverter_efficiency
    (`battery.cpp:2206`, `inverter.cpp:1415`). That limit is untranscribed.
- **Tests:**
  - `tests/test_cimtbl_inverter.py`, with the atom `tests/atoms/inverter/inverter.glm`. The atom has eight
    inverters: 3-phase, 1-phase and split-phase PV (the last capped), plus five batteries:
    - CONSTANT_PQ discharging;
    - the CONSTANT_PF Java defect;
    - full;
    - at its reserve;
    - OFFLINE.
  - Goldens for the atom and IEEE13_cdpsm (`inverter.cimtbl`).
  - Every deck's inverters read back through the core DER getters (`get_der_output`, `get_inverter_rating`,
    `get_inverter_unit`, `get_photovoltaic_unit`, `get_battery_unit`) against GridLAB-D's formulas written out again
    in the test.
  - IEEE13_cdpsm is checked against the DSS golden's battery dispatch and against GridLAB-D's PV output.
- **Results:**
  - 461 GLM tests pass with `--roundtrip` over every deck, and the core and DSS suites pass (983). The leak gate is
    clean.
  - 27 decks bind; the same two deck defects stop the other two. IEEE13_cdpsm is the only binding deck with DER.
  - IEEE13_cdpsm:
    - PV: -298.25 kW at the school and -4.97 kW at the house (GridLAB-D's static weather).
    - Batteries: -100 kW (the school's 0.001 W under GridLAB-D's cap), +5 kW and +1 kW, as the DSS golden.
    - The house inverters are `s1s2` D at 240 V.

### Field tables (generated: `fields_table(cls, records)`, the read slots only; samples from the atom and IEEE13_cdpsm)
**inverter** (the slots the mapper reads; the untranscribed groups follow)

| Inverter field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, InverterName]` | `inv_b3`, `inv_bfull`, `inv_boff` | derived | PowerElectronicsConnection.name; mRID pv_/storage_ + name by its unit (S4b-6) |
| `parent` | `Optional[str]` | `m3`, `m4`, `tm1` | structural | node: the parent's root bus (GLM-4) |
| `inverter_type` | `Optional[str]` | `FOUR_QUADRANT` | structural | FOUR_QUADRANT; any other raises, unset is GridLAB-D's PWM (inverter.cpp:1350) (S4b-1) |
| `four_quadrant_control_mode` | `Optional[str]` | `CONSTANT_PQ`, `CONSTANT_PF` | structural | CONSTANT_PF on a solar, CONSTANT_PQ on a battery, which also reads CONSTANT_PF as the Java defect (S4b-2); others raise; the capability flag goes in the row comment |
| `pf_reg` | `Optional[str]` |  | structural | EXCLUDED (default); power-factor regulation raises when set: no deck sets it, so a mapping waits for one |
| `generator_status` | `Optional[str]` | `OFFLINE`, `ONLINE` | derived | normallyInService: ONLINE (default) true; OFFLINE false, output 0 (inverter.cpp:2561) |
| `P_Out` | `Optional[float]` | `50000.0`, `-20000.0`, `30000.0` | derived | battery: the CONSTANT_PQ set point (S4b-2); PV: an output GridLAB-D overwrites (inverter.cpp:3879), listed in the row comment |
| `Q_Out` | `Optional[float]` |  | derived | CONSTANT_PQ: q = 0 when unset or 0; any other value raises (S4b-3) |
| `rated_power` | `Optional[float]` | `33333.333`, `15000.0`, `20000.0` | derived | ratedS = rated_power x phases out (3, 2, 1; S is 1, inverter.cpp:1318); maxQ = -minQ = apparentPowerMaximum = ratedS; unset or 0 raises (GridLAB-D's silent 25 kVA, :1409) |
| `inverter_efficiency` | `Optional[float]` | `0.95`, `1.0`, `0.975` | derived | PV: AC = DC x inverter_efficiency (inverter.cpp:3290); default 0.9 (:1398); CIM has no inverter efficiency |
| `soc_reserve` | `Optional[float]` | `0.2`, `0.25` | derived | BatteryUnit.minimumE = soc_reserve x battery_capacity; the battery does not discharge at or below it; default 0 |
| `power_factor` | `Optional[float]` | `-1.0`, `1.0` | derived | CONSTANT_PF: q = 0 when |pf| = 1; |pf| < 1 raises (S4b-3); not read by CONSTANT_PQ (a battery read as CONSTANT_PQ lists it in the row comment) |
| `phases` | `Optional[str]` | `ABCN`, `ACN`, `AS` | structural | A, B, C wye to neutral (3 phases: blank); S: s1s2 D across the legs at 240 V (S4b-4). GridLAB-D has no D keyword on an inverter |
| `use_multipoint_efficiency` | `Union[bool, Bool, NoneType]` | `False` | structural | FALSE (default); TRUE raises (no deck) |
| `max_charge_rate` | `Optional[float]` | `80000.0`, `100000.0`, `5000.0` | copied | `StorageInverterInfo.chargeRateActiveMax` (W); nameplate; GridLAB-D reads it only in load following |


- untranscribed, object header: 7 slots (`groupid` ... `flags`)
- untranscribed, read only by the non-four-quadrant types (inverter.cpp:1337), which raise: 1 slots (`generator_mode`)
- untranscribed, deltamode, VSI, droop and IEEE 1547 trip settings: dynamics, not the steady-state snapshot: 119 slots (`inverter_convergence_criterion` ... `first_iter_counter`)
- untranscribed, solver state or output: 47 slots (`V_In` ... `prev_value_IGenerated_C`)
- untranscribed, read only by the multipoint efficiency model, which raises: 8 slots (`inverter_manufacturer` ... `c_3`)
- untranscribed, read only by load following and the group modes, which raise: 18 slots (`sense_object` ... `lf_dispatch_change_allowed`)
- untranscribed, read only by power-factor regulation (pf_reg), which raises: 10 slots (`pf_reg_activate` ... `pf_reg_next_update_time`)
- untranscribed, read only by the volt-var, volt-watt and frequency-power modes, which raise: 30 slots (`disable_volt_var_if_no_input_power` ... `pc_vw_limited`)
- untranscribed, read only by the volt-var and volt-watt modes (inverter.cpp:318), which raise; ratedU is the bus's line-to-line voltage (S4b-5): 1 slots (`V_base`)

**solar** (the slots the mapper reads; the untranscribed groups follow)

| Solar field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, SolarName]` | `pv1`, `pv3`, `pvs` | derived | PhotoVoltaicUnit.name; mRID <connection>_unit |
| `parent` | `Optional[str]` | `inv_pv1`, `inv_pv3`, `inv_pvs` | structural | its inverter; another parent raises |
| `panel_type` | `Optional[str]` | `MULTI_CRYSTAL_SILICON`, `SINGLE_CRYSTAL_SILICON` | derived | the defaults of efficiency and Pmax_temp_coeff (solar.cpp:559); default SINGLE_CRYSTAL_SILICON |
| `SOLAR_POWER_MODEL` | `Optional[str]` |  | structural | DEFAULT (BASEEFFICIENT); others raise |
| `NOCT` | `Optional[float]` |  | derived | the module temperature (S4b-2); default 118.4 degF |
| `Rated_Insolation` | `Optional[float]` |  | derived | SolarPanelInfo.referenceIrradiation; the irradiance = Rated_Insolation x shading_factor (solar.cpp:1170); default 92.902 W/sf = 1000 W/m^2 |
| `Pmax_temp_coeff` | `Optional[float]` |  | derived | per degF, the DC output's temperature factor; default by panel_type |
| `efficiency` | `Optional[float]` | `0.2` | copied | `SolarPanelInfo.efficiency` (percent); default by panel_type |
| `area` | `Optional[float]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (with efficiency it can override rated_power, solar.cpp:624) |
| `soiling` | `Optional[float]` | `1.0` | derived | a factor of the DC output; default 0.95; outside 0..1 raises |
| `derating` | `Optional[float]` | `1.0` | derived | a factor of the DC output; default 0.95; outside 0..1 raises |
| `rated_power` | `Optional[float]` | `8000.0`, `250000.0`, `6000.0` | derived | maxP (W via pint), minP 0, and the DC output (S4b-2); unset raises (GridLAB-D derives it from area and insolation, solar.cpp:606) |
| `weather` | `Optional[str]` |  | structural | unset, with no climate object in the model; a climate raises (S4b-2) |
| `shading_factor` | `Optional[float]` | `0.8` | derived | SolarArrayInfo.shadingFactor (percent) and the irradiance; default 1 |
| `tilt_angle` | `Optional[float]` | `30.0` | copied | `SolarArrayInfo.tiltAngle` (deg); default 45 |
| `orientation_azimuth` | `Optional[float]` | `200.0` | copied | `SolarArrayInfo.orientationAzimuth` (deg); default 180 |
| `orientation` | `Optional[str]` |  | structural | DEFAULT; others raise (FIXED_AXIS needs a climate, solar.cpp:325) |


- untranscribed, object header: 7 slots (`groupid` ... `flags`)
- untranscribed, read only by the PV_CURVE and FLATPLATE models, which raise: 16 slots (`pvc_Pmax_calc_simp_mode` ... `T_coeff`)
- untranscribed, read only with a climate object, which raises: 2 slots (`SOLAR_TILT_MODEL`, `latitude_angle_fix`)
- untranscribed, solver state or output: 15 slots (`Tmodule` ... `last_DC_power`)
- untranscribed, with no climate GridLAB-D uses 59 degF and still air (solar.cpp:321): 2 slots (`wind_speed`, `ambient_temperature`)
- untranscribed, DC voltage and current: CIM has no DC array model: 5 slots (`Rinternal`, `Voc_temp_coeff`, `V_Max`, `Voc_Max`, `Voc`)

**battery** (the slots the mapper reads; the untranscribed groups follow)

| Battery field | type | samples | kind | target |
|---|---|---|---|---|
| `name` | `Union[str, BatteryName]` | `b3`, `bfull`, `boff` | derived | BatteryUnit.name; mRID <connection>_unit |
| `parent` | `Optional[str]` | `inv_b3`, `inv_bfull`, `inv_boff` | structural | its inverter (GridLAB-D requires one, battery.cpp:657); another raises |
| `rfb_size` | `Optional[str]` |  | structural | raises when set: no deck sets it, so a mapping waits for one (it overrides the battery's ratings, battery.cpp:661) |
| `use_internal_battery_model` | `Union[bool, Bool, NoneType]` | `True` | structural | true; false (the legacy model) raises |
| `battery_type` | `Optional[str]` | `LI_ION`, `LEAD_ACID` | derived | BatteryInfo.batteryType: LI_ION lithiumIon, LEAD_ACID leadAcid; others blank |
| `nominal_voltage` | `Optional[float]` | `48.0` | derived | BatteryInfo.numberOfCells = floor(nominal_voltage / 4.1) on LI_ION (battery.cpp:720); default 115 V |
| `rated_power` | `Optional[float]` | `100.0`, `30000.0`, `60000.0` | derived | maxP = rated_power, minP = -rated_power (the generation sign) |
| `battery_capacity` | `Optional[float]` | `200.0`, `50000.0`, `100000.0` | derived | ratedE and BatteryInfo.ratedCapacity (Wh via pint); unset raises |
| `round_trip_efficiency` | `Optional[float]` | `0.86` | derived | chargingEfficiency = dischargingEfficiency = sqrt of it, percent (battery.cpp:2220); default 0.8 |
| `state_of_charge` | `Optional[float]` | `0.6`, `1.0`, `0.5` | derived | storedE = state_of_charge x battery_capacity; unset raises |


- untranscribed, object header: 7 slots (`groupid` ... `flags`)
- untranscribed, read only by the legacy battery model (use_internal_battery_model false), which raises: 31 slots (`generator_mode` ... `parasitic_power_draw`)
- untranscribed, solver state or output: 29 slots (`V_Out` ... `climate_object_found`)
- untranscribed, set from the inverter's soc_reserve (battery.cpp:727): 1 slots (`reserve_state_of_charge`)

## S5: the deck sweep, tier 4 and G7 (proposed 2026-11-10; approved as recommended and built 2026-11-16)

S5 maps nothing new: no deck holds a `latitude` or `longitude`, so there is no coordinates part (the DSS S5's
`buscoords.cimtbl` has no GLM source). It turns the eight per-slice deck sweeps into one, closes D6 with a complete
IEEE13_cdpsm golden directory, adds the tier-4 IEEE 13 GLM vs DSS check, and records G7.

### The deck sweep (S5-1)

Today each of the eight slice modules (bus, catalog, line, transformer, regulator, load, capacitor, inverter) has its
own `test_every_*` over `ALL_DECKS`, with the same stop boilerplate, so every deck is read and bound eight times
(the GLM suite with `--roundtrip` takes 4 min 30 s).
`tests/test_cimtbl_sweep.py` reads and binds each deck once and runs every slice's GridLAB-D check on that network:

- `assert_gridlabd_ohms` (S3b), `assert_gridlabd_regulation` (S3c), `assert_gridlabd_loads` and
  `assert_gridlabd_capacitors` (S4a), `assert_gridlabd_der` (S4b), and the bus, catalog and line counts the slice
  sweeps assert today, each moved to a named `assert_*` helper in its slice module;
- a deck in `BIND_STOPS` must stop with its listed error, an unlisted stop fails, and a listed stop that binds fails,
  so the table stays true. Expected: 27 of 29 bind; `IEEE123_transactive` (`Object battery`) and `IEEE13_houses`
  (its 634 center taps rated 2401 V on a 480 V bus) stop, as today.

The slice modules keep their atoms, goldens and fail-fast tests. `test_every_deck_walks` stays in
`test_topology_walk.py` (it stops at the walk, not the bind).

### The IEEE13_cdpsm golden directory (S5-2, D6)

The committed directory does not bind on its own: its master imports `zip_fractions.cimtbl` (the core's shared ZIP
rows), which no slice committed. S5 adds it, so the directory holds 16 files, and one test checks the whole
directory: the written file set equals the golden set (no file missing or extra), every file matches its golden, and
the golden directory binds with `cimtables.load_model`. It replaces the nine per-slice IEEE13_cdpsm golden tests
(DRY: one place to regenerate, `CIMHUB_UPDATE_GOLDENS=1`).

### Tier 4: IEEE 13 GLM vs DSS (S5-3)

IEEE13_cdpsm.glm is the Java CIMHub export of the model the DSS importer's `IEEE13_CDPSM` golden holds. The test binds
**the two committed golden directories** with `cimhub_core` and `cimtables` only, matches equipment by its terminal
buses (the bus names agree), and compares through the core getters in SI. It imports neither spoke and needs no
engine, so it lives at the workspace root, `tests/cross_format/test_ieee13_glm_vs_dss.py`, as the tier-4 location
rule says (a test that touches two spokes' artifacts belongs to neither). The root needs a `tests/conftest.py`
(the `cim_scope` fixture) and `scripts/test-all.sh` runs it as one more process.

Probe on 2026-11-10 (both golden directories, the GLM one completed by S5-2):

| class | compared | result |
|---|---|---|
| bus voltages | BaseVoltage of every line, load and capacitor | equal |
| lines (11) | phases, length, the phase R and X matrices in ohms (length x per-length, conductor order sorted) | equal to 4 places |
| switches (5) | class (LoadBreakSwitch, Fuse, Recloser), phases, normal state | equal |
| loads | p, q per bus and phase (DSS has 16 consumers, one per DSS Load; GLM 10) | equal |
| capacitors (2) | nomQ at nomU per bus; neither has a control | equal |
| regulator taps (3) | low, high, neutral, step (8, 10, 11), increment 0.625 % | equal |
| DER (5) | S4b's cross-solver note | batteries and ratings equal; PV and the house's connection follow GridLAB-D |
| transformers | ratings, voltages, connections, impedance, core admittance | equal on xf1 and the house center tap |

**Expected differences** (asserted as differences, so a change on either side shows):
1. **Source:** DSS 30 deg with the deck's short-circuit impedance; GLM 0 deg with the stiff default (S1-3).
2. **Substation transformer:** DSS has three windings (a 13.2 kV tertiary on its internal bus `650z`); the Java
   export wrote two, so GLM has no `650z`.
3. **Transformer impedance:** closed. The core getter now reads a `TankConfiguration`'s %Z (with the Hopkinson
   center tap), so GLM's xf1 and house center tap equal the DSS mesh, and the substation's two windings equal
   DSS's first two; the impedance is compared under `transformers`.
4. **Regulator controls:** the Java export wrote `Control MANUAL` with `band_center` commented out, so GLM's controls
   are disabled with no target; DSS's regulate at 2440 V, 40 V band, delay 15 s. GLM's line drop is 1/5 of DSS's
   (0.01714 + j0.05143 vs 0.0857 + j0.2571 ohm): the Java export wrote DSS's CT ratio, 3500 = 700 A / 0.2 A,
   where GridLAB-D's compensator divides the current by `current_transducer_ratio` as a 1 A secondary
   (`regulator.cpp:1330`, S3c-4). It is not active under MANUAL. See S5-4 and S5-5. Found at build: `neutralU`
   is 2400 V in DSS (its 2.4 kV winding) and 2401.78 V in GLM (the coil: the 4.16 kV bus over sqrt 3, S3c); the
   tap positions, range and increment are equal.
5. **DER:** the S4b cross-solver note (PV output; `s1s2` D at 240 V vs the DSS shape's Y at 208 V).

### G7 (S5-6)

Measured 2026-11-10 on `orig_R3-12.47-3`, the largest deck:

| deck | read | map | bind |
|---|---|---|---|
| orig_R3-12.47-3 | 3.0 s | 0.5 s | 4.8 s: 26,622 rows / 52,118 objects, about 5,500 rows/s |
| IEEE13_cdpsm | <0.1 s | <0.1 s | 0.1 s: 224 rows / 340 objects |

That is the DSS importer's rate (about 7,900 rows/s on IEEE9500 including coordinates), so G7 needs no work; the
sweep test records no timing (it would be flaky).

### Decisions for S5 (approved as recommended, 2026-11-16)

| # | question | recommendation |
|---|---|---|
| S5-1 | Per-slice deck sweeps | One sweep test, one bind per deck, every slice's check on it; the eight `test_every_*` go |
| S5-2 | The IEEE13_cdpsm golden (D6) | Add `zip_fractions.cimtbl`; one directory test (file set, each file, the directory binds) replaces the nine per-slice IEEE13 golden tests |
| S5-3 | Where tier 4 lives | Root `tests/cross_format/`, comparing the two committed golden directories through the core getters (no spoke import, no engine); expected differences asserted, not skipped |
| S5-4 | A disabled `TapChangerControl` with no target (GLM MANUAL) | The core `get_tap_changer_control` raises `targetValue is unset`, so neither tier 4 nor an exporter can read GLM's 3 IEEE 13 regulators (nor any MANUAL unit without a band). Recommended: core returns `target` None when the control is `enabled` false (a plan section 7 core row; tier 4 compares the taps until then). The alternative, the importer writing GridLAB-D's default `band_center` 0, would write a value GridLAB-D never reads |
| S5-5 | The Java export's CT ratio | Keep GridLAB-D's reading (the engine's 1/5 compensation, as the deck would run), list it as an expected difference and a Java export defect, as S4b's battery. The alternative, reading it as DSS's CT primary (x 0.2), would follow the Java exporter's intent the way S4b's battery does; but here the mode is MANUAL, so nothing runs on it |
| S5-6 | G7 | Recorded above; closed with no work |

### Built (2026-11-16)

On rc_1 `ddc6227` (the worktree fast-forwarded the same day; no incoming commit touched `cimhub_gridlabd`).

- **Sweep (S5-1):** `tests/test_cimtbl_sweep.py`, `test_every_deck_binds_as_gridlabd_runs_it`, one read and one bind
  per deck. The checks the slice sweeps made inline are now named helpers in their modules (`assert_buses`,
  `assert_catalogs`, `assert_lines_and_switches`, `assert_transformers`); the others were already
  (`assert_gridlabd_regulation`, `_loads`, `_capacitors`, `_der`). The eight `test_every_*` sweeps are gone, and so is
  S4b's `test_ieee13_cdpsm_against_the_dss_golden`, whose values tier 4 now asserts against the DSS golden itself.
- **D6 (S5-2):** `zip_fractions.cimtbl` added, so `goldens/IEEE13_cdpsm/` has 16 files.
  `test_ieee13_cdpsm_golden_directory` writes the documents, matches every file to its golden, checks that the two
  file sets are the same, and binds the golden directory on its own (`cimtables.load_model`). It replaces the nine
  per-slice IEEE13_cdpsm golden tests, the master's included; `CIMHUB_UPDATE_GOLDENS=1` rewrites the whole directory.
- **Tier 4 (S5-3):** `tests/cross_format/test_ieee13_glm_vs_dss.py` (13 tests) plus a root `tests/conftest.py`;
  `scripts/test-all.sh` runs it as its own process (`scripts/test-all.sh cross_format`, and CI's no-argument run).
  It imports `cimhub_core` and the cim-graph stack only. Eight tests check what is equal (buses, base voltages,
  lines, switches, loads, capacitors, regulator taps, transformer ratings and core). Five assert the expected
  differences 1-5, so either side changing shows. Test 3 asserts that the core getter reads no GLM impedance yet:
  when the template %Z row lands it fails, and the impedance joins `test_transformers`.
- **Amended at build:**
  - **Line matrices:** R, X and B in ohms and siemens are equal to the getter's float precision: the largest relative
    difference is 0.
  - **Loads:** compared at a relative 1e-5. Bus 646's constant-impedance delta load is 66,000.09 W per phase in GLM
    against DSS's 66,000 W, which is the Java export's 6-digit rounding.
  - **Regulators:** `neutralU` differs (expected difference 4).
- **S5-4:** plan section 7 core row (a disabled control may have no target). **S5-5:** listed as expected difference 4
  and a Java export defect; the mapping keeps GridLAB-D's reading.
- **Results:** the GLM suite with `--roundtrip` (29 decks): 249 passed in 51 s, down from 461 in 4 min 30 s.
  That is 461 - 232 sweep runs - 10 IEEE 13 tests + 29 sweep runs + 1 directory test. Core: 449 passed.
  Tier 4: 13 passed. Leak gate and lint are clean.

## S6: a utility's Milsoft WindMil decks (by the user's direction 2026-11-16; built, approved 2026-11-16)

The user's direction: test the converter on a utility's 22 GridLAB-D feeders exported by Milsoft's "WindMil to
GridLabD Export" (2022), and edit the exports so that GridLAB-D loads them. They are kept out of git (the utility's
data). The sweep binds every deck in `CIMHUB_GLM_UTILITY_DECKS` (S6-8); the decks' repair log, a patch against the
originals and the scripts are kept with the data, not here.

The exports are flat: `node`, `load` (constant power), `overhead_line`/`underground_line` on z-matrix
`line_configuration`s (no geometry), `transformer` on `resistance`/`reactance` configurations, `switch`, `recloser`
(WindMil writes fuses as reclosers), `capacitor`, `regulator`. About 60,000 nodes, 37,000 lines, 17,000 transformers.

### What GridLAB-D rejects (deck repairs, by the user's leave)

Each repair answers a GridLAB-D error, not the converter's, so the converter is not taught the defects:
- **lower-case dump `mode rect`** (`convert.cpp:427` matches keywords case-sensitively) and a Windows dump path;
- **no swing bus:** the head node is `bustype PQ`; under FBS the first node in becomes the swing (`node.cpp:1602`),
  so the repair writes the `SWING` FBS gives it;
- **dangling references:** a span `from <capacitor>_n` (WindMil's in-line capacitor), a `sense_node` with its
  leading `_` lost, a second consumer on `X-1_n`, and `sense_node NULL _n` on every `REMOTE_NODE` regulator (the remote
  point is lost; it becomes the regulator's own output, `regulator.cpp:154` throws without one);
- **phasing errors:** 3-phase sections fed through 1-phase spans, which the exporter joins with `fake_g_*_n` nodes
  (children on phases their parent lacks, `node.cpp:1079`; links on phases their ends lack, `link.cpp:664`). The
  user's choice: widen the narrow path to the phases below it, each span on the same conductor's wider Milsoft
  configuration (copied from a sibling deck when the deck lacks it; WindMil writes its catalog in single precision,
  so copies agree to 1e-6). A customer on 2 or 3 phases behind one 1-phase service can is likely a wye-delta bank,
  which GridLAB-D does not model; the user's call: parallel cans, the transformer on the customer's phases with
  Milsoft's own `WYE_WYE-<kVA>x<n>` configuration (n x the can's kVA and per unit, so every phase has the can's ohms);
- **open ties between laterals on different phases** (`link.cpp:649` throws whatever the status): **kept**, the
  user's call, as CIM holds them (S6-9). So 10 decks do not load in GridLAB-D as they stand; without the 21 open
  switches they do, with the same solution;
- **one nameplate:** 12470 V primaries on 14.4 kV (phase-to-neutral) buses; GridLAB-D runs them 15 % high and the
  walk rejects them. The user's choice: `primary_voltage 14400`.

### What the converter now maps (S6-1 to S6-7)

| S6 | Subject | Built |
|---|---|---|
| S6-1 | Wye rating basis (amends S3b-3; approved: `ratedU` line to line, `baseU` the coil, line to neutral on a wye) | GridLAB-D uses a wye's voltages only as `nt = V1 / V2` and the base `V2² / S` (`transformer.cpp:265`), so either reading solves the same; the deck says which. `topology.coil_rated`: the written `primary_voltage` is its from bus's `nominal_voltage` (phase to neutral; the Milsoft exports) or that × √3 (line to line; the Java exports, S3b-3), within the walk's nameplate tolerance; anything else raises. A coil-rated wye: `baseU` as written, `ratedU` on its bus's system (`line_voltage`), `k = S_coil / S_total` (S3b-4's ohms kept); in the walk one phase-to-neutral coil per side on one conductor (a 7200/120 V service is a single-phase system), else polyphase at × √3. An unused configuration keeps S3b-3, noted. **Confirmed by the user 2026-11-16** after an independent hand translation of one deck (the cimtbl-translate skill) wrote the can as `connectionKind I`, phases `A`, `ratedU` = the coil: the converter's tank template, `Yn` on `AN`, `ratedU` line to line and `baseU` the coil stays (as the DSS import). That translation agreed on every line impedance, the source voltage and the can's series ohms |
| S6-2 | `SINGLE_PHASE` | One case with `WYE_WYE` in `transformer.cpp:282`: mapped as it (Y/Y, grounded) |
| S6-3 | One template per phase count | A one-tank wye with no phase ratings depends only on how many phases it is wired on, so one configuration may serve A, B and C (the Milsoft decks share one per kVA) |
| S6-4 | Matrix lines (amends S3a-3) | N on a matrix line is dropped (`line.cpp:226` fills the Kron-reduced A, B, C only); a written 0 `z_ii` is no phase, a nonzero term on such a phase raises, all-zero raises. **The user's call 2026-11-16:** the matrix is written as given, 3x3 and already reduced: GridLAB-D's `line_configuration` has no neutral terms (`line_configuration.cpp:40`-`46`), so there is no 4x4 to write, and an exporter must not reduce it again (a 4x4 with the neutral, where a source gives one, is left for the exporter to reduce, e.g. OpenDSS `reduce=y`). Geometry lines keep their neutral position |
| S6-5 | Link phases | A link's phases (N, D aside) must be on both its end objects, as `link::init` throws (`link.cpp:649`, `:664`; a center tap's S on its to end only): the walk raises, S6-9 aside |
| S6-6 | `REMOTE_NODE` (amends S3c-6; approved) | Sensing the regulator's own output (its `to` bus) GridLAB-D reads the voltages `OUTPUT_VOLTAGE` reads (`regulator.cpp:1376`-`1420`): mapped as it, the records identical; a remote sense node still raises. A `sense_node` on another `Control` GridLAB-D does not read (`:150`): listed on the row |
| S6-7 | Regulator phases | `PT_phase`/`CT_phase` on `INDIVIDUAL` GridLAB-D does not read (`:1328`, `:1378`): listed on the row, no longer raise. A `BANK` on its one `PT_phase` is one unit on it (named as a gang, `xf_<name>`) |
| S6-9 | Open ties across phases (the user's call) | An open switching device whose switched letters are on its from end and whose to end has as many other letters (an `-A` switch from an A lateral to a B one) is `phaseSide1` = its letters, `phaseSide2` = its to end's, paired in ABC order (cim-tables' `phaseSide1`/`phaseSide2` columns; each Terminal on its side's phases), with a row note. Closed, or overlapping letters, still raise (S6-5). GridLAB-D cannot load it: the converter holds what the source system has, not only what GridLAB-D runs. The sweep checks every switch's sides against its GLM ends |
| S6-8 | Utility decks in the sweep | `test_every_utility_deck_binds_as_gridlabd_runs_it`: every non-empty `*.glm` in `CIMHUB_GLM_UTILITY_DECKS` binds and passes every slice check (`--roundtrip`); no stop table, so no names in git |
| S6-10 | One-phase services (the user's, 2026-11-16) | A coil-rated `SINGLE_PHASE`/`WYE_WYE` on one phase and N (a Milsoft service) is split-phase by its `secondary_voltage` (within the walk's 10 % nameplate tolerance, as `coil_rated`: a 110 V can is a leg), as a 208 V secondary of three coils is ABC line to line: 120 V is the s1 leg to N (end 2 `s1N`, kind I on the instance, one split-phase half as a center tap's s1, a can whose X1 lands on s1 (S3b-13); the coil 120 V, ratedU 240); 240 V is a center tap (end 2 `s1s2N`, kind I, the center-tap template of lugs H1 H2 X1 X3 X2 with 120 V halves at S/2 on the can's S, and GridLAB-D's R + jX on 240²/S as the full winding, so a 240 V load sees the same R + jX and each leg reads 120 V to ground; written as one s1-s2 coil its legs floated). Either bus is a 240 V split-phase system (`bv_240v`), and a load's one phase there becomes the s1 leg or the s1-s2 240 V consumer. Only loads may sit on a service bus: a link, capacitor or inverter raises. JOHNSON CREEK: 430 120 V and 278 240 V services; before, 707 nodes read 1.73 pu on a 120 V BaseVoltage taken as line to line. Kind I and the tolerance are merged from glm-repair's build of the same rule (that user's call) |

### Built (2026-11-16)

- **Results:** all 22 utility decks bind and pass every slice check, `assert_gridlabd_ohms` included (17,000
  transformers at GridLAB-D's `zt`); the largest reads in 1.2 s and binds in 6.1 s. The 29 Powergrid-Models decks
  are unchanged (27 bind, the 2 stops as before). The GLM suite with `--roundtrip`: 257 passed; with the utility
  decks the sweep is 52 passed in 105 s. After S6-9 and the parallel cans: 281 passed with both deck sets.
- **Tests:** the S3a/S3b/S3c fail-fast tests of the amended rules now test the mappings (coil-rated wyes against
  GridLAB-D's ohms, a wye off its bus raises, a matrix line's N, a 0 diagonal, `REMOTE_NODE` on its own output against
  `OUTPUT_VOLTAGE`, a remote one raises, the two row notes, a one-phase `BANK`, an open tie across phases and a closed
  one raising); the walk has the coil-rated coils and the link-phase check. A triplex line and a regulator on phases their ends lack now stop at S6-5 first.
