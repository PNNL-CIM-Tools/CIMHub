# GDM class → CIM target

GDM 2.4.1 classes against CIM-Builder `gdm_support` (`6d05e54` + working tree), checked 2026-11-08 (Phase 2 targets as built: `GDM_MAPPING.md` §15-§17). Re-probe each
builder before its family (recipe step 1).

| code | meaning |
|---|---|
| **R** | builder ready |
| **U** | needs a builder or a fix from the user (plan's upstream table) |
| **G** | CIM 18 gap: untranscribed, or raise ([`OPEN_DECISIONS.md`](OPEN_DECISIONS.md) 12) |
| **D** | waits on a decision |

Decision numbers refer to [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md); B17-B20 are the 2026-11-08 builder requests.

## Components

| GDM class | role | CIM target (mRID) | builder | ready | phase |
|---|---|---|---|---|---|
| DistributionSubstation | instance | Substation `sub_`; `Feeder.NormalEnergizingSubstation`; `feeders` structural | `SubstationBuilder` | R | 1 |
| DistributionFeeder | shell | Feeder `fdr_`; the first one is the model container | `new_feeder_model`, `FeederBuilder` | R | 1 |
| DistributionBus | instance | ConnectivityNode (bare name, `name`, BaseVoltage, container); BaseVoltage `bv_…` from `system_voltage(rated_voltage, voltage_type)` | `ConnectivityNodeBuilder`, `BaseVoltageBuilder` | R | 1 |
| bus `voltagelimits` | inline | OperationalLimitSet + VoltageLimit, or untranscribed | `OperationalLimitSetBuilder` | D (12) | 1 |
| bus `coordinate` | inline | none: ConnectivityNode is not a PowerSystemResource (B14) | none | G | 1 |
| bus `phases`, `in_service` | structural | phases checked against attached equipment; `in_service=False` raises | none | n/a | 1 |
| DistributionVoltageSource | instance | EnergySource `src_` + EnergySourcePhase: nominalVoltage, voltageMagnitude (LL), voltageAngle (degree), r/x/r0/x0; unequal per-phase values raise (EnergySourcePhase has only `phase`) | `EnergySourceBuilder` | R | 1 |
| MatrixImpedanceSwitch, SequenceImpedanceSwitch *(new in 2.4)* | instance | class by equipment (14) `sw_`: open = not `is_closed`, normalOpen from the controller; per-phase states that differ → SwitchPhase `open` | switch builders | R (GroundDisconnector U, B19) | 1 (done) |
| GeometrySwitch *(new in 2.4)* | instance | LoadBreakSwitch `sw_`; its equipment is a `GeometryBranchEquipment` catalog | switch builders | R | 2 (done) |
| MatrixImpedanceFuse | instance | Fuse `sw_` | `FuseBuilder` | R | 1 |
| MatrixImpedanceRecloser | instance | Recloser `sw_`; `controller` untranscribed (no RecloseSequence, 12) | `RecloserBuilder` | R | 1 |
| MatrixImpedanceBranch | instance | ACLineSegment `ln_`: node1/node2, phases, length; PerLengthImpedance `lc_` | `ACLineSegmentBuilder` | R | 2 (done) |
| SequenceImpedanceBranch | instance | ACLineSegment → PerLengthSequenceImpedance (prefix X7) | same | R | 2 (done) |
| GeometryBranch | instance | ACLineSegment + WireConfiguration `wc_` (never an impedance matrix: `conductor-geometry` skill) | `ACLineSegmentBuilder.add_wire_configuration` | R | 2 (done) |
| DistributionLoad | instance | EnergyConsumer `ld_`: phaseConnection, grounded, p/q totals, customerCount, LoadResponse; EnergyConsumerPhase p/q only when the phases differ, for a single-phase load, or for s1/s2 triplex (13) | `EnergyConsumerBuilder`, `EnergyConsumerPhaseBuilder` | R | 2 (done) |
| DistributionCapacitor | instance | LinearShuntCompensator `cap_`: nomU (LL), nomQ, bPerSection, sections (int); controllers → RegulatingControl `<cap>_ctrl` | `LinearShuntCompensatorBuilder` (+Phase), `RegulatingControlBuilder` | R | 2 (done) |
| DistributionTransformer | instance | PowerTransformer `xf_` + TransformerTank `<xf>_tank` (TankConfiguration `xc_`) + PowerTransformerEnd `<xf>_<n>` per bus (a center tap's halves one end, `s1s2N`) + TransformerPhaseEnd `<xf>_<n>_<phase>` (center tap only) + RatioTapChanger `<end>_tap` off nominal (G4) | `TransformerBankFromConfigurationBuilder`, `RatioTapChangerBuilder` | R | 3 (done) |
| DistributionRegulator | instance (a `DistributionTransformerBase`, not a `DistributionTransformer`) | a VoltageRegulator `vr_<name>[_<phase>]` per phase (AutoTransformerEnds, lugs S L SL, series winding) + RatioTapChanger `<vr>_tap` + TapChangerControl `<vr>_ctrl`; TapChangerInfo `tci_<equipment>` (B17) | `VoltageRegulatorBuilder`, `RatioTapChangerBuilder`, `TapChangerControlBuilder`, `TapChangerInfoBuilder` | R | 3 (done) |
| DistributionSolar | instance | PowerElectronicsConnection `pv_` (ratedS, ratedU LL, p = −output, q = −output) + PhotoVoltaicUnit `<pec>_unit` (maxP, irradiance B16b); no phaseConnection (GDM has none); controller `PENDING` (12) | `PowerElectronicsConnectionBuilder`, `PhotoVoltaicUnitBuilder` | R | 4 (done) |
| DistributionBattery | instance | PowerElectronicsConnection `storage_` + BatteryUnit `<pec>_unit` (ratedE, maxP/minP ± rated_power, efficiencies, batteryState from the sign); discharge p < 0; storedE has no GDM source | same + `BatteryUnitBuilder` | R | 4 (done) |
| DistributionReactor *(new in 2.4)* | instance (branch) | SeriesCompensator `rx_` (r, x, r0 = r, x0 = x; Terminal phases); length untranscribed (17b, decided) | `SeriesCompensatorBuilder` (added this session) | R | 4 (done) |
| `substation` / `feeder` on every component | structural | EquipmentContainer (1) | `EquipmentContainer=` keyword | R | 1 |
| `uuid` on every class | structural | not the mRID; used, rehashed (B18), only when the name is empty or clashes (9, 10) | B18 | U | all |

## Equipment

| GDM class | role | CIM target | builder | ready | phase |
|---|---|---|---|---|---|
| Matrix{Switch,Fuse,Recloser}Equipment, SequenceImpedanceSwitchEquipment, CircuitBreakerEquipment, DisconnectorEquipment, EarthingSwitchEquipment *(last four new in 2.4)* | inline | the class picks the CIM switch class (14); ampacity → ratedCurrent; r/x/c matrices and construction untranscribed; breaker `interrupting_current` → `SwitchInfo.breakingCapacity` (B20, untranscribed until then); fuse `delay`, `tcc_curve` untranscribed (no FuseCharacteristicCurve, 12) | switch builders | R | 1 |
| DistributionSwitchController | controller | normal_state → normalOpen; is_locked, delay untranscribed | switch builders | R | 1 |
| RecloserControllerEquipment, DistributionRecloserController | controller | untranscribed: no RecloseSequence in cim18v17 `protection` (12) | none | G | 1 |
| VoltageSourceEquipment / PhaseVoltageSourceEquipment | inline | EnergySource attributes; raise unless every phase is equal | `EnergySourceBuilder` | R | 1 |
| MatrixImpedanceBranchEquipment | catalog | PerLengthPhaseImpedance `lc_` + PhaseImpedanceData `<lc>_<row><column>` (lower triangle); ampacity → the instance's limits | `PerLengthPhaseImpedanceBuilder` | R | 2 (done) |
| SequenceImpedanceBranchEquipment | catalog | PerLengthSequenceImpedance (r, x, r0, x0; bch/b0ch = ωC) | `PerLengthSequenceImpedanceBuilder` | R | 2 (done) |
| GeometryBranchEquipment | catalog | WireConfiguration `wc_` + XYSpacing `spc_` (isTemplate) + XYConductorPosition `<spc>_<n>` + WireSequenceConfiguration `<wc>_<n>`; insulation G | `WireConfigurationBuilder`, `XYSpacingBuilder` | R | 2 (done) |
| BareConductorEquipment | catalog | OverheadWireInfo `wire_` (gmr, radius = diameter / 2, rAC, rDC20, ratedCurrent); emergency_ampacity → limits | `OverheadWireInfoBuilder` | R | 2 (done) |
| ConcentricCableEquipment | catalog | ConcentricNeutralCableInfo `cn_` | `ConcentricNeutralCableInfoBuilder` | R | 2 (done) |
| LoadEquipment / PhaseLoadEquipment | inline | connection_type → phaseConnection + grounded; real/reactive_power → p/q; ZIP → LoadResponseCharacteristic (`zip_constant_*`, else one per distinct ZIP tuple); num_customers → customerCount | `EnergyConsumerBuilder`, `LoadResponseCharacteristicBuilder` | R | 2 (done) |
| CapacitorEquipment / PhaseCapacitorEquipment | inline | connection_type, rated_voltage (LL), rated_reactive_power, num_banks(_on) → sections (int); R/X untranscribed | `LinearShuntCompensatorBuilder` (+Phase) | R | 2 (done) |
| DistributionTransformerEquipment | catalog | TransformerTankConfiguration `xc_` (D10): TankEnd `<xc>_end_<n>` + TransformerWinding `<xc>_wdg_<n>` per winding, or (center tap) lugs `<xc>_lug_<d>` + windings lug to lug; mesh `<xc>_mesh_<i><j>`; losses derived from pct × rated; mounting untranscribed | `TransformerTankConfigurationBuilder` (+ `add_transformer_tank_end`, added 2026-11-08) | R | 3 (done) |
| PowerTransformerEquipment *(new in 2.4)* | catalog | as above; vector_group structural; cooling_class → CoolingInfo `cool_` (B20); fluid_type untranscribed (18) | same + `CoolingInfoBuilder` | R | 3 (done) |
| WindingEquipment | inline in catalog | TransformerTankEnd (connection) + TransformerWinding (ratedS, baseS, ratedU, baseU, r percent); taps → the instance's RatioTapChanger (G4) | same | R | 3 (done) |
| SolarEquipment | inline | rated_power → maxP (kVA taken as kW with a WARNING, ditto); rated_voltage → PEC ratedU (LL); no SolarPanelInfo slot fits; R/X untranscribed; power_temp_curve untranscribed (16) | `PhotoVoltaicUnitBuilder` | R | 4 (done) |
| InverterEquipment | inline (AssetInfo on first use) | rated_apparent_power → PEC ratedS and `GenerationInverterInfo` / `StorageInverterInfo` `inv_` apparentPowerMaximum; limits, cut-in/out, efficiency untranscribed (no slot); eff_curve untranscribed (16) | `GenerationInverterInfoBuilder`, `StorageInverterInfoBuilder` (B20) | R | 4 (done) |
| BatteryEquipment | inline (AssetInfo on first use) | rated_energy → ratedE and `BatteryInfo` `batt_` ratedCapacity; rated_power → maxP / −minP; charging/discharging efficiency; idling_efficiency untranscribed | `BatteryUnitBuilder`, `BatteryInfoBuilder` (B20) | R | 4 (done) |
| ReactorEquipment *(new in 2.4)* | inline | SeriesCompensator r, x (r0, x0); no SeriesReactorInfo slot fits | `SeriesCompensatorBuilder` | R | 4 (done) |

## Controllers

| GDM class | target | ready | phase |
|---|---|---|---|
| Voltage / ActivePower / ReactivePower / Current CapacitorController | RegulatingControl `<cap>_ctrl`. Mode by class. target = (on + off) / 2, deadband = off − on, × pt/ct ratio. Terminal = the capacitor's own terminal. delay_on → `aVRDelay` (`LinearShuntCompensatorBuilder.add_regulating_control`). dead_time G | R (golden waits on U3) | 2 (done) |
| DailyTimedCapacitorController | needs a schedule | G (`PENDING`) | 2 |
| RegulatorController | TapChangerControl: targetValue, targetDeadband, lineDropCompensation, lineDropR/X, reversible, min/maxLimitVoltage, monitoredPhase = controlled_phase, Terminal on controlled_bus. RatioTapChanger: ptRatio, ctRating, initialDelay, high/low step | R | 3 (done) |
| InverterController + settings (VoltVar, VoltWatt, PF, CapacityFirming, PeakShaving, TOU, TimeBased, SelfConsumption, DemandCharge) | function-block classes; no builder | G (`PENDING`) | 4 |

## Other

| GDM | target | ready | phase |
|---|---|---|---|
| Curve | untranscribed until B12 (16); then Curve + CurveData `<curve>_<n>` | U (B12) | 4 |
| TimeCurrentCurve | untranscribed: no FuseCharacteristicCurve (12) | G | 1 |
| VoltageLimitSet | see bus `voltagelimits` | D (12) | 1 |
| ThermalLimitSet | not referenced by any GDM field; standalone only | coverage raises | 1 |
| infrasys time series | load P/Q → nc_schedule `EnergyConnectionSchedule` `<ld>_pq`, points in the `EnergyConnectionTimePoint` table ([`TIMESERIES_NEEDS.md`](TIMESERIES_NEEDS.md)); others dropped with a warning (2) | `EnergyConnectionScheduleBuilder` (B16) | time series (done) |
| supplemental attributes | none | raise | 1 |
