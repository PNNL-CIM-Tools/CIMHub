# Decisions and risks

Numbers 1-18 are kept from the earlier plan so older notes still resolve. Builder requests B17-B20 were filed with the
builder owner on 2026-11-08.

## Decided

1. **Multi-feeder systems.** **Decided (user, 2026-11-06):** several feeders per system.
   - One CIM Feeder `fdr_<name>` per `DistributionFeeder`, and one Substation `sub_<name>` per `DistributionSubstation`.
   - Each piece of equipment's `EquipmentContainer` comes from its own `feeder`, else its `substation`.
   - A component with neither goes to a system Feeder `fdr_<system.name>`. That is the one documented fallback.
   - The model's container (the `Feeder` passed to `new_feeder_model`) is one of these Feeders; it is decorative.
2. **Time series.** **Decided (user, 2026-11-06; amended 2026-11-08):** the target is the user's Curve +
   RegularIntervalSchedule profile ([`TIMESERIES_NEEDS.md`](TIMESERIES_NEEDS.md)). Until it exists, time series are
   **dropped, not raised on**, and the static snapshot is imported.
   - Not silent (I8): `to_cim` logs one `WARNING` naming the count, each component (class + name) and each series
     (variable name, type, `time_series_uuid`). A test asserts it.
   - Every time-series type is dropped, `Deterministic` included. Supplemental attributes still raise.
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
7. **Regulator model.** **Decided (user, 2026-11-08):** a regulator **template**, which CIM-Builder is asked to build
   from the CYME regulator database and the GDM catalog (**B17**). Instances follow DSS-13 (a `VoltageRegulator` with
   two `AutoTransformerEnd`s), built from that template, with `RatioTapChanger` + `TapChangerControl` per instance.
   cim18v17 has no AutoTransformer configuration class, so the template's CIM shape is the builder owner's call
   (`TapChangerInfo` for the tap data; an extension for the impedance). `DistributionRegulator` stays `PENDING` until
   B17 lands.
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
    - Until B18 lands, a clash raises, naming both uuids.
11. **Untranscribed values.** **Decided (user, 2026-11-08):** `FIELDS` is the record. When values are needed, they go
    to a log file: `to_cim` logs each object's untranscribed values at `DEBUG` on the `cimhub_gdm` logger, and the
    caller attaches a `FileHandler`. The importer never opens files itself (I7).
12. **Behavioural gaps.** **Decided in part (user, 2026-11-08):**
    - Fuse, Recloser, Breaker and the other switch classes exist in `electrical_unbalanced` and are mapped (Phase 1).
      Only fuse curves (`FuseCharacteristicCurve`) and reclose sequences (`RecloseSequence`) are missing, in the
      `protection` package. So fuse `tcc_curve` / `delay` and the recloser controller are **untranscribed** (not
      raised on), and each is logged as a gap in `CIMTBL-Models/distribution/CIM18_GAPS.md`.
    - Still open: DailyTimed capacitor control, inverter controllers (`function_block_control` has classes, but there
      is no builder), bus coordinates (B14), bus voltage limits, `in_service=False` on buses. *Recommendation:* raise
      on the control gaps; bus voltage limits untranscribed; coordinates untranscribed until B14.
13. **Load phase convention.** **Decided (user, 2026-11-08):**
    - A three-phase load with equal per-phase values is one `EnergyConsumer` with the totals and no
      `EnergyConsumerPhase`.
    - **How (user, 2026-11-08, G3):** balanced three-phase equipment passes `phases=None` to its builder, for loads
      and every other three-phase class (sources, switches, lines, ...). So there are no per-phase children and no
      `Terminal.phases`; absent means ABC. This is `shared.builder_phases`. The core shapes and the DSS goldens still
      write `phases=ABC`, so the DSS wave has to adopt the same rule before the DSS/GDM parity test.
    - `EnergyConsumerPhase` children are written when the per-phase values differ, for a standalone single-phase load
      (A, B or C), and for a split-phase (`s1`/`s2`) triplex load.
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

## Open

- **17b. The `DistributionReactor` instance** [Phase 4]. The catalog follows 15-18, but the reactor itself is a
  series branch (`buses`, `length`). Leaving it out would split the network at that point. *Recommendation:*
  `SeriesCompensator` (r, x from `ReactorEquipment`) with the shape the DSS S4 slice adds for its series reactor. Until
  there is a builder, it stays `PENDING`, so a system with a reactor raises instead of importing disconnected.
- **12, the rest:** see 12 above.

## Risks

19. **Silent wrong-quantity mappings** (X2). W, VA and VAr convert into each other, so pint never catches a `kilowatt`
    written into `ratedS`. The `FIELDS` unit column and the golden diff are the only guard. Reviewers check every power
    target.
20. **The builder API is moving.** The 2026-11-08 handoff had breaking changes, the U5 cleanup is in flight, and
    B17-B20 add more. Each family re-probes its builder methods first (recipe step 1).
21. **GDM version skew.** GDM 2.4.1 can't load the older GDM data formats: the gdm-cases p5r sample (format 1.2.0) fails
    on `gdm.quantities.PositiveVoltage`, which has since been removed. Atoms build their systems in Python, so they
    don't depend on this. Any committed JSON fixture must be written by the pinned GDM version, and the version recorded.
