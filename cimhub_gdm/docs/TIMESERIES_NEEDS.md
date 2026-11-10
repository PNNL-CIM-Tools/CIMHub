# Needs: GDM time series → a Curve + RegularIntervalSchedule profile

**For:** the user. The plan is a new profile part holding Curve and RegularIntervalSchedule, plus its builders.
**From:** the GDM importer rewrite, 2026-11-06; updated 2026-11-08. Decision 2 in [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md)
depends on this.
**Until the profile exists:** time series are dropped and the static snapshot is imported. `to_cim` logs one warning
naming every component and series it dropped, so nothing disappears silently (I8).

## 1. What GDM carries

GDM time series are infrasys objects, attached with `system.add_time_series(ts, component, **features)`. They are not
pydantic `model_fields`, so `FIELDS` / `check_fields` never see them, and the coverage check has to look for them
explicitly (`system.has_time_series(component)`).

### Time series types

| infrasys type | fields | seen in |
|---|---|---|
| `SingleTimeSeries` | `name` (the variable), `data` (NDArray, or pint Quantity with units), `resolution` (timedelta), `initial_timestamp` (datetime), `normalization` | ditto OpenDSS loadshapes: the common case |
| `NonSequentialTimeSeries` | `name`, `data`, `timestamps` (array) | GDM API, rare |
| `SingleTimeSeriesScalingFactor` | as `SingleTimeSeries`, with 0-1 factors | GDM API, rare |
| `Deterministic` (forecast) | `horizon`, `interval`, `window_count`, ... | out of scope: raise |

### Metadata on each attachment

- `name`;
- `time_series_uuid`: shared when several components use the same array;
- `features` (dict);
- `units`: `QuantityMetadata`, holding the module, the quantity type and the units string;
- `normalization`: one of `NormalizationMax(max_value)`, `NormalizationByValue(value)` or `None`.

### What ditto attaches (`ditto/readers/opendss/components/loadshapes.py`)

| component | variable (`name`) | units | features |
|---|---|---|---|
| `DistributionLoad` | `active_power` | `kilowatt` | `profile_type=PMult`, `profile_name=<loadshape>`, `use_actual` |
| `DistributionLoad` | `reactive_power` | `kilovar` | `profile_type=QMult`, ... |
| `DistributionSolar` | `irradiance` | `kilowatt/meter**2` | `profile_type=PMult`, ... |
| `DistributionVoltageSource` | `pu_voltage` | none (pu) | `profile_type=PMult`, ... |

Notes on these attachments:
- One OpenDSS loadshape becomes one array, shared through `time_series_uuid` across every component that uses it.
- `initial_timestamp` is fixed at 2020-01-01 by ditto.
- `resolution` is the loadshape's `SInterval`.
- `Normalize=yes` gives `NormalizationByValue` (when PBase/QBase is set) or `NormalizationMax`.
- `use_actual=False` means the values are multipliers on the component's nominal value, OpenDSS `PMult` semantics.

## 2. What cim18v17 has today

There is no generic schedule:
- **Schedules:** only HVDC- and market-specific ones exist: `VsConverterSchedule`, `VsConverterRegularSchedule`,
  `MustRunSchedule`/`MustRunTimePoint`, `PowerSchedule` (DC tie), and `TapSchedule` (a TapChanger link only).
- **Missing classes:** `BasicIntervalSchedule`, `RegularIntervalSchedule`, `RegularTimePoint`, `IrregularIntervalSchedule`,
  `LoadGroup`, `ConformLoadGroup` and `ConformLoadSchedule`.
- **Present:** `Curve`/`CurveData` exist; CurveData is an Identity class. `ConformLoad` exists too, but has no
  `LoadGroup` association.

For reference, the classic CIM 17 shape (cim17v40):

```
BasicIntervalSchedule(IdentifiedObject): startTime, value1Multiplier, value1Unit, value2Multiplier, value2Unit
RegularIntervalSchedule(BasicIntervalSchedule): endTime, timeStep, TimePoints
RegularTimePoint(Identity): sequenceNumber, value1, value2, IntervalSchedule
IrregularIntervalSchedule(BasicIntervalSchedule): TimePoints
IrregularTimePoint(Identity): time, value1, value2, IntervalSchedule
ConformLoadSchedule(SeasonDayTypeSchedule -> RegularIntervalSchedule): ConformLoadGroup
ConformLoadGroup(LoadGroup): EnergyConsumers, ConformLoadSchedules   # only ConformLoad has LoadGroup
```

## 3. Needs

**N1. Schedule classes for regular data.**
- **Mapping:** `SingleTimeSeries` → `RegularIntervalSchedule` + `RegularTimePoint`.
- **Schedule attributes:**
  - `startTime` = `initial_timestamp`;
  - `timeStep` = `resolution`, in seconds;
  - `endTime` = start + (n − 1) × resolution. Say which convention you want: the last point, or the end of the last
    interval.
  - `value1Unit` / `value1Multiplier` come from the data's units, or are `none` for multipliers (N3).
- **Points:** `RegularTimePoint` holds `sequenceNumber` and `value1`. It is an Identity class, keyed by `identifier =
  <schedule>_<n>`.
- **Paired series:** `value2` could carry Q next to P when both share one time base. That is optional; separate
  schedules work too.

**N2. Irregular data.**
- **Mapping:** `NonSequentialTimeSeries` → `IrregularIntervalSchedule` + `IrregularTimePoint` (`time`, `value1`).
- **Alternative:** a Curve with time on x, if you'd rather keep the profile small. If neither is added,
  `NonSequentialTimeSeries` raises.

**N3. Multiplier vs actual values.** GDM data are either actual values (`use_actual=True`, carried as a Quantity with
units) or multipliers on the component's nominal value.
- **Normalized multipliers:** these are `NormalizationMax` or `NormalizationByValue(value)`. The schedule has to say
  which kind its values are.
- **Suggested:** multipliers are written as `value1Unit = none`, and actual values with their unit, verbatim (I2).
  `NormalizationByValue(value)` needs its base recorded too: an attribute on the schedule, or a documented rule that the
  base is the equipment's own nominal `p`/`q`.

**N4. Which equipment and which attribute.** This is the key gap: CIM's only link is `ConformLoadGroup` →
`ConformLoad`, which covers loads only and says nothing about the attribute. GDM needs (equipment, scheduled quantity)
for:

| GDM component | scheduled quantity | CIM target |
|---|---|---|
| `DistributionLoad` | `active_power`, `reactive_power` | EnergyConsumer `p`, `q` |
| `DistributionSolar` | `irradiance` | PowerElectronicsConnection, or PhotoVoltaicUnit `p`, via irradiance: no CIM attribute |
| `DistributionVoltageSource` | `pu_voltage` | EnergySource `voltageMagnitude`, as a pu multiplier |

Suggested options:
- **(a) Generic.** A schedule → PowerSystemResource association, plus a `scheduledAttribute` text or enum such as
  `EnergyConsumer.p`.
- **(b) Per family.** Like ConformLoadGroup, but with the attribute implied by the class (P schedule vs Q schedule).

(a) covers all three GDM cases with one association. Irradiance has no CIM attribute at all, so under (b) it needs its
own kind.

**N5. Sharing and identity.**
- **One schedule per array.** Each infrasys `time_series_uuid` (with its normalization) becomes one schedule, and every
  component that uses the array references it. A yearly loadshape is 8760 points, and repeating it per load would
  multiply that by the load count.
- **mRID:** `ts_` + `profile_name`, when that feature exists (ditto loadshapes); otherwise `ts_` + component mRID +
  `_` + variable name. The `ts_` prefix is not yet in the cimtbl-translate table (X7).

**N6. Scale.** At one RegularTimePoint per sample, an 8760-point yearly profile is 8760 Identity objects per schedule.
Before choosing per-point objects over an array-valued attribute, check cim-graph's memory, `add_to_graph` and
`write_xml` cost at, say, 100 schedules × 8760 points.

**N7. Builders** (B16, with B12 Curve):
- a `RegularIntervalScheduleBuilder`:
  - `create(mRID, name)`;
  - `add_schedule(startTime, timeStep, endTime, value1Unit, value1Multiplier)`;
  - `add_time_points(values)`, a bulk method that writes `RegularTimePoint`s with deterministic identifiers;
- a method to link equipment to a schedule, per N4.

**N8. Out of scope.** `Deterministic` forecasts and supplemental attributes raise.

## 4. What the GDM importer will do once N1-N5 and N7 exist

This becomes the time-series family ("Later" in [`PHASES.md`](PHASES.md)):

1. For each component with time series, list its metadata with `system.list_time_series_metadata(component)`.
2. Build one schedule per `time_series_uuid` (N5). Values are passed verbatim, in their units, with the `none` unit for
   multipliers (N3).
3. Link the schedule to the component's CIM equipment and attribute (N4).
4. Raise for unsupported time series types (N2, N8).

Until then `to_cim` drops time series with one warning. The drop test's 3-point `SingleTimeSeries` on a load becomes
the family's atom, with its golden.
