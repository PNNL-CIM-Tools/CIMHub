# GridLAB-D → `.cimtbl` mapping spec

**Status:** S0 (master) built 2026-11-09; each later section is written with its slice and approved before that
slice's code. Plan: `.development/GLM_REWRITE_PLAN.md`. Contract and format: the `cimtbl-import-contract`,
`cimtbl-shapes` and `cimtbl-mapping-spec` skills. Samples come from the vendored decks in `tests/decks/` (origins in
its README).

## Artifact files and order

The master imports the parts in `MAPPING_ORDER` (`importer/glm_to_cimtbl.py`), which follows the plan's section 2.
S0 has no parts; S1 adds `bus.cimtbl` and `source.cimtbl`; S2 (draft) the six catalog files (below).

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
