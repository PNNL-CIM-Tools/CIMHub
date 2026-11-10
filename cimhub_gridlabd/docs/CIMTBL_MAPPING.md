# GridLAB-D → `.cimtbl` mapping spec

**Status:** S0 (master) built 2026-11-09; each later section is written with its slice and approved before that
slice's code. Plan: `.development/GLM_REWRITE_PLAN.md`. Contract and format: the `cimtbl-import-contract`,
`cimtbl-shapes` and `cimtbl-mapping-spec` skills. Samples come from the vendored decks in `tests/decks/` (origins in
its README).

## Artifact files and order

The master imports the parts in `MAPPING_ORDER` (`importer/glm_to_cimtbl.py`), which follows the plan's section 2.
S0 has no parts; S1 adds `bus.cimtbl` and `source.cimtbl` (below).

## master

Mapper: `importer/glm_to_cimtbl.py` `map_master`. Test: `tests/test_glm_to_cimtbl.py`; golden
`tests/goldens/IEEE13_cdpsm/IEEE13_cdpsm.cimtbl`.

| row | from | rule |
|---|---|---|
| `Substation`, `Feeder` | the `name` the caller passes (D7) | mRIDs `sub_<name>`, `fdr_<name>`, source case |
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

