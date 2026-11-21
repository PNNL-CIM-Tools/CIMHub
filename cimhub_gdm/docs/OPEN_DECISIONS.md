# Decisions and risks

Numbers 1-18 are kept from the earlier plan so older notes still resolve. Builder requests B17-B20 (and B21-B25, Phase 2) were filed with the
builder owner on 2026-11-08.

## Decided

1. **Multi-feeder systems.** **Decided (user, 2026-11-06):** several feeders per system.
   - One CIM Feeder `fdr_<name>` per `DistributionFeeder`, and one Substation `sub_<name>` per `DistributionSubstation`.
   - Each piece of equipment's `EquipmentContainer` comes from its own `feeder`, else its `substation`.
   - A component with neither goes to a system Feeder `fdr_<system.name>`. That is the one documented fallback.
   - The model's container (the `Feeder` passed to `new_feeder_model`) is one of these Feeders; it is decorative.
2. **Time series.** **Decided (user, 2026-11-06; amended 2026-11-08, 2026-11-11):** the target is cim18v17's
   `nc_schedule`: one `EnergyConnectionSchedule` per load, in actual values, its points in Parquet (T1-T6 in
   [`TIMESERIES_NEEDS.md`](TIMESERIES_NEEDS.md)). **Built 2026-11-11** on B16: load series map when the caller passes a
   `time_points` dict; without one they are **dropped, not raised on**, and the static snapshot is imported.
   - Not silent (I8): `to_cim` logs one `WARNING` naming the count, each component (class + name) and each dropped
     series (variable name, type, `time_series_uuid`). A test asserts it.
   - Without `time_points`, every time-series type is dropped, `Deterministic` included. With it, `Deterministic`
     raises, and series with no CIM class (PV irradiance, source `pu_voltage`) are dropped with the warning.
     Supplemental attributes still raise.
3. **Network shell.** **Decided (B1 landed 2026-11-08):** `cimbuilder.network.new_feeder_model(authority, model,
   Feeder, name=None, frequency=60)`; further Feeders and Substations through `FeederBuilder` / `SubstationBuilder`.
4. **Frequency.** **Decided (user, 2026-11-06):** 60 Hz, `FREQUENCY_HZ = 60` in `shared.py`, written as the
   `BaseFrequency` and as `calculatedFrequency` on every PerLengthImpedance.
5. **BaseVoltage rounding.** **Decided (user, 2026-11-06):** 4 significant figures for BaseVoltage dedupe and mRID
   (2.4018 kV line-to-ground → 4.160 kV → `bv_4p16kv`). Ratings keep the unrounded line-to-line value. Single-phase
   coil voltages (center-tap `baseU`) are never multiplied by √3.
6. **D10, the 3-phase tank configuration.** **Decided (user, 2026-11-08, in the DSS wave):** a TransformerTankEnd per
   winding, no phases on the template; instance end n is template end n. A center-tap catalog is a 3-winding tank with
   lugs H1 H2 X1 X3 X2 and windings H1→H2, X1→X2, X2→X3 (additive polarity, IEEE C57.12.00); its instance's phase ends
   land on the lugs by `sequenceNumber` (DSS-2). Ratings are nameplate values (`ratedU` line-to-line, `baseU` the coil).
   - **Built (Phase 3, 2026-11-08)** through CIM-Builder: the user had TankEnd marked for deletion, kept for by-end
     templates, and the TankEnd builder method was added this session. A center tap's windings carry the polarity
     (`bus.1.0` / `bus.0.2`); its low side is one PowerTransformerEnd and Terminal with a phase end each for s1, s2,
     N (user, 2026-11-08). Taps sit on the instance's PowerTransformerEnd (a regulator's on its AutoTransformerEnd),
     never on a TankEnd: cim18v17 has no TankEnd tap.
7. **Regulator model.** **Decided (user, 2026-11-08):** a regulator **template**, which CIM-Builder is asked to build
   from the CYME regulator database and the GDM catalog (**B17**). Instances follow DSS-13 (a `VoltageRegulator` with
   two `AutoTransformerEnd`s), built from that template, with `RatioTapChanger` + `TapChangerControl` per instance.
   cim18v17 has no AutoTransformer configuration class, so the template's CIM shape is the builder owner's call
   (`TapChangerInfo` for the tap data; an extension for the impedance).
   - **Built (Phase 3, 2026-11-08):** one single-phase VoltageRegulator per phase, as CIMTBL-Models
     `regulator_example.cimtbl` (lugs S L SL, one series winding); `TapChangerInfoBuilder` (B17's tap data) is each
     tap changer's AssetDatasheet; the impedance stays untranscribed until the owner picks its template home.
8. **Enum strings.** **Decided (user, 2026-11-06):** builders accept strings and build the enum (C1, landed).
9. **mRIDs.** **Decided (user, 2026-11-08):** as planned: `mrid(prefix, gdm.name)`, names as written, prefixes and
   children per the `cimtbl-translate` tables, missing prefixes per the DSS wave where they fit
   (`zip_constant_pq`/`_z`/`_i`, `exp_<p>_<q>`). Where the token is a GUID rather than free text, it is **rehashed
   into a new UUID string** by a core CIM-Builder function (**B18**, e.g. `rehash_mrid(class_name, token)`).
   - Why: `cimprofiles.identity` uses an mRID that parses as a UUID verbatim as the identifier, with no model, authority
     or class seeding. A source GUID used directly would collide across models and across the CIM objects one GDM
     object becomes.
10. **Name clashes.** **Decided (user, 2026-11-08):** same mechanism as 9. An object keeps `mrid(prefix, name)` when its
    name is non-empty and unique within its GDM class. Otherwise its mRID is `rehash_mrid(cim_class, str(gdm.uuid))`
    (B18), with no prefix.
    - GDM's `uuid` is the same value its JSON writes as `__metadata__.fields.uuid` on references, so in memory it is
      `component.uuid`.
    - In the p5r sample (GDM data format 1.2.0), every component and catalog name is present and unique. Only inline
      objects (WindingEquipment, VoltageLimitSet, ThermalLimitSet, Location) have empty or repeated names, and those
      get child mRIDs from their parent (`<xc>_wdg_<n>`, `<ln>_limits`), not uuids.
    - B18 landed 2026-11-08 (`cimbuilder.network.rehash_mrid`); `shared.object_mrid` applies it. Feeder and
      substation names can't be rehashed (their mRIDs come before the model scope exists), so an empty, GUID or
      clashing one raises.
11. **Untranscribed values.** **Decided (user, 2026-11-08):** `FIELDS` is the record. When values are needed, they go
    to a log file: `to_cim` logs each object's untranscribed values at `DEBUG` on the `cimhub_gdm` logger, and the
    caller attaches a `FileHandler`. The importer never opens files itself (I7).
12. **Behavioural gaps.** **Decided in part (user, 2026-11-08):**
    - Fuse, Recloser, Breaker and the other switch classes exist in `electrical_unbalanced` and are mapped (Phase 1).
      Only fuse curves (`FuseCharacteristicCurve`) and reclose sequences (`RecloseSequence`) are missing, in the
      `protection` package. So fuse `tcc_curve` / `delay` and the recloser controller are **untranscribed** (not
      raised on), and each is logged as a gap in `CIMTBL-Models/distribution/CIM18_GAPS.md`.
    - `DailyTimedCapacitorController` is `PENDING` (Phase 2): a system with one stops at the coverage check.
    - Still open: inverter controllers (`function_block_control` has classes, but there
      is no builder), bus coordinates (B14), bus voltage limits, `in_service=False` on buses. *Recommendation:* raise
      on the control gaps; bus voltage limits untranscribed; coordinates untranscribed until B14.
13. **Load phase convention.** **Decided (user, 2026-11-08):**
    - A three-phase load with equal per-phase values is one `EnergyConsumer` with the totals and no
      `EnergyConsumerPhase`.
    - **How (user, 2026-11-08, G3):** balanced three-phase equipment passes `phases=None` to its builder, for loads
      and every other three-phase device (sources, switches, capacitors, DER, ...). So there are no per-phase children
      and no `Terminal.phases`; absent means ABC. This is `shared.builder_phases`. Transformer and regulator ends
    always write their phases (on the Terminal only), as GDM writes them: `Yn` when N is listed, `grounded` from
    `is_grounded`; only a single-phase wye coil written with one phase gets the N it returns to (G8, user
    2026-11-08, revised: never override the grounding flag). The DSS wave adopted the same rule
      (S4b-9, `cimhub_core.cimtbl.phases_cell`).
    - **Lines keep their phases** (Phase 2, G7, as the DSS wave's S4b-9): an ACLineSegment always writes `phases`,
      balanced ABC included, because its ACLineSegmentPhases are the conductor order of its impedance matrix or wire
      positions. Transformer ends will follow the DSS wave's rule too (phases on the Terminal only).
    - `EnergyConsumerPhase` children are written when the per-phase values differ, for a standalone single-phase load
      (A, B or C), and for a split-phase (`s1`/`s2`) triplex load. They carry p and q only when the values differ
      (the DSS goldens' children carry none). A delta load's children are per branch (`ld_x_BC`), as cimtables and
      CIM write them.
14. **Switch class.** **Decided (user, 2026-11-08):** by equipment class.

    | GDM equipment | CIM class | builder |
    |---|---|---|
    | `MatrixImpedanceSwitchEquipment`, `SequenceImpedanceSwitchEquipment` | LoadBreakSwitch | `LoadBreakSwitchBuilder` |
    | `CircuitBreakerEquipment` | Breaker | `BreakerBuilder` |
    | `DisconnectorEquipment` | Disconnector | `DisconnectorBuilder` |
    | `EarthingSwitchEquipment` | GroundDisconnector | none: **B19**; pending until then |
    | `MatrixImpedanceFuseEquipment` | Fuse | `FuseBuilder` |
    | `MatrixImpedanceRecloserEquipment` | Recloser | `RecloserBuilder` |

15. **-18. Catalog detail beyond the templates.** **Decided (user, 2026-11-08):** map what the cim18v17 AssetInfo classes
    can hold, linked through `PowerSystemResource.AssetDatasheet`, and leave the rest untranscribed (**B20** asks for the
    builders):

    | # | GDM | AssetInfo | untranscribed |
    |---|---|---|---|
    | 15 | `InverterEquipment` | `GenerationInverterInfo` (PV) / `StorageInverterInfo` (battery); `rated_apparent_power` also goes to the PEC `ratedS` | what the Info has no slot for |
    | 16 | `Curve` (`eff_curve`, `power_temp_curve`) | none (Curve is not an AssetInfo) | all, until B12 |
    | 17 | `ReactorEquipment` | `SeriesReactorInfo` where a slot fits | r/x (no verbatim slot) |
    | 18 | `PowerTransformerEquipment` | `CoolingInfo` for `cooling_class` | `fluid_type` unless the `Specification`/`Medium` chain is built; `vector_group` is structural (checked against the windings, a mismatch raises) |
    |  | `BatteryEquipment`, `SolarEquipment` | `BatteryInfo`, `SolarPanelInfo` | the rest |
    |  | `CircuitBreakerEquipment.interrupting_current` | `SwitchInfo.breakingCapacity` | |

    - Each row is confirmed with `fields_table` before its family.
    - Until B20 lands, these fields are untranscribed, and the families don't wait for it.
    - **B20 landed** (CIM-Builder `caff0ea`, 2026-11-08). Phase 4 builds InverterInfo `inv_` (Generation- under a PV,
      Storage- under a battery: `apparentPowerMaximum`) and BatteryInfo `batt_` (`ratedCapacity`). No GDM field fits
      a SolarPanelInfo or SeriesReactorInfo slot, so neither is built (`GDM_MAPPING.md` §20-§21).

17b. **The `DistributionReactor` instance.** **Decided (user, 2026-11-08):** a `SeriesCompensator` `rx_<name>`
    (r, x from `ReactorEquipment`, r0 = r, x0 = x), the shape of the DSS wave's series Reactor golden. CIM-Builder had
    no builder, so this session added `SeriesCompensatorBuilder` with the user's go-ahead (uncommitted there;
    `GDM_MAPPING.md` §21).
- **DER panel power in kVA.** **Decided (user, 2026-11-08):** ditto writes `SolarEquipment.rated_power` as an
  ActivePower in kVA; the importer takes an apparent unit there as the same active one, with a WARNING
  (`der.panel_power`), rather than stopping p5r. Every other power keeps the §4 guard.

- **DSS/GDM parity.** **Decided (user, 2026-11-09):** written on rc_1 after `gdm-builder` merges, in root
  `tests/cross_format/`, against rc_1's DSS importer. This branch's scope stops at `cimhub_gdm/`, and its
  `cimhub_opendss` is behind rc_1's.

## Open

- **12, the rest:** see 12 above. Inverter controllers stay `PENDING` (no `function_block_control` builder).
- **TODO (user, 2026-11-08): the missing inverter and DER attributes** [Phase 4 follow-up]. Phase 4 leaves these
  untranscribed because neither `InverterInfo` nor `PowerElectronicsUnit` has a slot for them:
  - `InverterEquipment`: `rise_limit`, `fall_limit`, `cutin_percent`, `cutout_percent`, `dc_to_ac_efficiency`,
    `eff_curve`;
  - `SolarEquipment`: `resistance`, `reactance`, `power_temp_curve` (`DistributionSolar.irradiance` is mapped since
    B16b);
  - `BatteryEquipment.idling_efficiency`.

  They may live in the child classes: `GenerationInverterInfo` / `StorageInverterInfo` under `InverterInfo`, and
  `PhotoVoltaicUnit`, `BatteryUnit`, `PowerElectronicsWindUnit` and the rest under `PowerElectronicsUnit`. A probe of
  the merged cim18v17 profile (2026-11-08) found none there: only `StorageInverterInfo` adds anything
  (`chargeRateActiveMax`, `chargeRateReactiveMax`, `storageCapacity`), and the units add only the battery fields
  already mapped. Next steps:
  - check the full CIM 18 UML (not just the profile slices) for the subclasses' attributes;
  - check the associated classes the profile does carry: `InverterInfo.ShortCircuitRespone`,
    `ProductAssetModel`, and `OperationalLimitSet` (ramp limits as limits);
  - for each attribute found, ask CIM-Profiles to slice it in and CIM-Builder for its keyword; then map it and move
    its `FIELDS` entry from untranscribed to copied;
  - log what has no home anywhere in `CIMTBL-Models/distribution/CIM18_GAPS.md`.

## Risks

19. **Silent wrong-quantity mappings** (X2). W, VA and VAr convert into each other, so pint never catches a `kilowatt`
    written into `ratedS`. The `FIELDS` unit column and the golden diff are the only guard. Reviewers check every power
    target.
20. **The builder API is moving.** The 2026-11-08 handoff had breaking changes, the U5 cleanup is in flight, and
    B17-B20 add more. Each family re-probes its builder methods first (recipe step 1).
21. **GDM version skew.** GDM 2.4.1 can't load the older GDM data formats: the gdm-cases p5r sample (format 1.2.0) fails
    on `gdm.quantities.PositiveVoltage`, which has since been removed. Atoms build their systems in Python, so they
    don't depend on this. Any committed JSON fixture must be written by the pinned GDM version, and the version recorded.
