# Needs: GDM time series → nc_schedule, and the builders for it

**For:** the user, who owns CIM-Builder. This is a builder request (B16), plus two small profile requests (P1, P2).
**From:** the GDM importer and exporter, 2026-11-06; rewritten 2026-11-11 against cim18v17's new `nc_schedule` module.
Decision 2 in [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md) depends on this.
**Status (2026-11-11): built**, at the user's "go ahead and build it": B16 and B16b in CIM-Builder (uncommitted
there), the import, export and Parquet files in this spoke (§5, "As built"). Without a `time_points` dict, time series
are still dropped and the static snapshot is imported; `to_cim` logs one warning naming every component and series it
dropped, so nothing disappears silently (I8).

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

The ditto OpenDSS writer turns these back into `LoadShape` objects named by `profile_name` (or the series uuid), with
`UseActual` from the feature.

## 2. What cim18v17 has now (`nc_schedule`, CIM-Profiles 512fafd)

The CGMES Network Code schedule package. The parts that matter here:

| class | attributes | links |
|---|---|---|
| `BaseTimeSeries(IdentifiedObject)` | `interpolationKind` (`TimeSeriesInterpolationKind`: linear, next, none, previous, zero), `timeSeriesKind` (`BaseTimeSeriesKind`: actual, forecast, hindcast, schedule), `actionMethod`, `generatedAtTime`, `percentile` | |
| `EnergyConnectionSchedule(BaseIrregularTimeSeries)` | | `EnergyConnection` (one), `EnergyConnectionTimePoint` (many) |
| `EnergyConnectionTimePoint(Identity)` | `atTime` (string), `p` (ActivePower), `q` (ReactivePower), load sign convention | `EnergyConnectionSchedule` |
| `EnergyConnectionRegularSchedule(BaseRegularIntervalSchedule)` | one `p`, `q`, valid over `intervalStartTime`-`intervalEndTime`, `dayOfWeek`, `HourPattern`, `Season` | `EnergyConnection` |
| `PowerSchedule` / `PowerTimePoint` | market power schedule (`powerScheduleKind`, prices, merit order) | `EnergyConnection`, `PowerElectronicsUnit`, ... |
| `RegularIntervalSchedule` / `RegularTimePoint` | classic CIM: `startTime`, `timeStep`, `value1..3`, units | **none to equipment** |

What this means for GDM:
- **Sampled arrays** fit `EnergyConnectionSchedule` + `EnergyConnectionTimePoint`, one point per sample. The
  `*RegularSchedule` classes are one value repeated over a calendar pattern, not a sampled array.
- **EnergyConnection** covers EnergyConsumer, EnergySource and PowerElectronicsConnection in the merged module.
- **One schedule per device.** `EnergyConnectionSchedule.EnergyConnection` is single-valued, so a loadshape shared by
  many loads cannot be one shared schedule.
- **Actual values.** The time points hold `p` and `q` in W and VAr: there is no multiplier form.
- **No voltage magnitude schedule.** Only `VoltageAngleSchedule` and `VoltageLimitSchedule` exist.
- **No irradiance schedule.** `PhotoVoltaicUnit.irradiance` (ActivePowerPerArea) is now a static extension, but no
  schedule class carries it.
- **Serialization works.** A probe (§6) writes the classes under `xmlns:nc="http://entsoe.eu/ns/nc#"` and `write_xml`
  → `XMLFile` reloads them intact. One quirk to check: the unit datatypes come out as
  `http://entsoe.eu/ns/nc#UnitSymbol.watt`, not the `cim#` UnitSymbol.

## 3. Decided (2026-11-11)

| # | decision |
|---|---|
| T1 | Load P/Q series go to **one `EnergyConnectionSchedule` per EnergyConsumer, in actual values**. A multiplier series becomes `p(t) = multiplier(t) × EnergyConsumer.p` (and q likewise). The profile is unchanged. The export gives back actual-value series per load (`use_actual=True`), so loads no longer share a loadshape after a round trip. |
| T2 | PV irradiance: the static value goes to `PhotoVoltaicUnit.irradiance`. An irradiance **series** stays dropped with the warning until a schedule class carries it (P1). |
| T3 | A source's `pu_voltage` series stays dropped with the warning (no class; P2 if wanted). |
| T4 | The importer stays builder-native (D11): the builder (B16) is in CIM-Builder, and the GDM family is written on top of it. The user had it built here ("go ahead and build it", 2026-11-11); its API is open to the user's redesign. |
| T5 | The work lands on `gdm-exporter` as its own phase, after X4 (committed 4c9ca19). |
| T6 | **Every time point is stored in Parquet**, never as an XML or cim-graph object. The schedules stay in the CIM XML; each Parquet row points back to its schedule by uri (§4, "The points table"). Decided 2026-11-11 after §6's measurements, in the direction of CIM issue #7963 (a CIM header, columnar bulk values). |

## 4. Requests

### The points table (T6)

- **One table per TimePoint class**, written next to the CIM XML as `<stem>.<class>.parquet`, e.g.
  `ieee13.xml` + `ieee13.EnergyConnectionTimePoint.parquet`. Only the spoke's writer and reader touch these files,
  as for the XML (the core reader/writer contract).
- **Columns** are the TimePoint's attributes, with its schedule association as a uri column:

  | column | type | holds |
  |---|---|---|
  | `EnergyConnectionSchedule` | string, dictionary-encoded | the schedule's `uri()`: the UUID in its `rdf:about="urn:uuid:..."` |
  | `atTime` | timestamp (µs, UTC) | the instant the value takes effect (X2) |
  | `p` | float64, W | null where the schedule has only q |
  | `q` | float64, VAr | null where the schedule has only p |

  Values are in SI base units, as in the CIM XML (UNITS.md), with the unit in each field's metadata.
- **No per-point identity.** A point is its (schedule, `atTime`) pair; a repeated pair raises. Rows are grouped by
  schedule, in the order the schedules were built, and sorted by `atTime` within each (pyarrow can't sort on a
  dictionary column, so the groups are not in uri order).
- **The XML is the header's only home.** The file metadata names the profile and the class (`cim:profile`,
  `cim:class`) and copies nothing from the schedules.
- **Checks on read:** a row whose schedule is not a schedule of that class in the XML raises; a schedule with no
  rows warns.
- **In memory:** the points are a `pyarrow.Table` per TimePoint class beside the model; they never become cim-graph
  objects, so cim-graph is unchanged. **As built:** a plain `dict[class name, pyarrow.Table]` that the caller owns
  and passes in: `GdmImporter(time_points)` fills it, `GdmExporter(time_points)` reads it (both by constructor, so
  `to_cim` keeps the core signature), and `write_time_points` / `read_time_points` move it to and from disk.
- **Later classes** follow the same rule: `SwitchTimePoint` (`open`, `locked`), `ShuntCompensatorTimePoint`
  (`sections`), `TapScheduleTimePoint` (`step`), and so on.
- **Not plain CIM.** A consumer with only the XML sees schedules with no points.

### B16. An EnergyConnectionSchedule builder (CIM-Builder)

What the importer needs from it; the shape of the API is the user's call.

1. **Create** an `EnergyConnectionSchedule` linked to one EnergyConnection (EnergyConsumer first; EnergySource and
   PowerElectronicsConnection later), with `name`, and a deterministic identity seeded from the caller's key.
   The GDM importer keys it on the component and the variable pair, so re-importing gives the same uri.
2. **Set** `timeSeriesKind` and `interpolationKind` from strings (C1).
3. **Bulk time points.** Add a schedule's points from arrays in one call: times (datetimes, or a start + step for
   regular data), `p` and/or `q` with an input unit (`'kW'`, `'kVAr'`: UNITS.md, no manual scaling). They become
   rows of the points table (T6), converted to W and VAr, with the schedule's uri; no graph objects.
4. **One schedule for P and Q.** When a load's P and Q series share a time base, both go in the same points. When
   they don't, two schedules, each with only `p` or only `q`.
5. **`atTime` is a UTC instant** (the table's timestamp column). GridLAB-D player times carry a zone (§7, X1) and
   are converted to UTC on import; naive sources (OpenDSS, ditto) are taken as UTC.
6. **Scale** (§6): arrays in, columns out; nothing per point.

**As built** (`cimbuilder/object_builder/schedule/energy_connection_schedule.py`):
- `EnergyConnectionScheduleBuilder.create(mRID=, name=)`, then `add_schedule(schedule, *, EnergyConnection,
  timeSeriesKind=None, interpolationKind=None, actionMethod=None)` (profile part `nc_schedule`).
- `time_points(schedule, *, times, p=None, q=None, p_unit="W", q_unit="VAr") -> pyarrow.Table` in
  `TIME_POINT_SCHEMA`: pure, nothing added to the graph; raises on no values, a length mismatch or a repeated time.
  Units convert through the profile's pint registry (a factor per call, so arrays need no numpy).
- `TIME_POINT_SCHEMA` and `TIME_POINT_CLASS` are defined there, once; CIM-Builder gained a `pyarrow` dependency.

### B16b. `irradiance` on the PhotoVoltaicUnit builder

A keyword for the static `PhotoVoltaicUnit.irradiance` (ActivePowerPerArea, input unit `'kW/m^2'`), so T2's static
value can be imported. The exporter then writes GDM `irradiance` from it when set, and keeps today's rule (p over
the panel rating at 1 kW/m²) when it is not. **As built:** `PhotoVoltaicUnitBuilder.add_ssh(unit, *, p, irradiance,
inService)`.

### P1 (profile, optional). An irradiance schedule

`PhotoVoltaicUnitSchedule(BaseIrregularTimeSeries)` + `PhotoVoltaicUnitTimePoint(atTime, irradiance)`, linked to
PhotoVoltaicUnit, mirroring `BatteryUnitSchedule`. Until it exists, T2 drops irradiance series.

### P2 (profile, optional). A source voltage schedule

A time point with a voltage magnitude for an EnergySource (pu or kV). Only if GDM `pu_voltage` series matter; until
then T3 drops them.

## 5. What the GDM spoke does (built 2026-11-11)

**Import** (`to_cim`):
1. For each DistributionLoad with series, read its `active_power` and `reactive_power` series.
2. Values: actual values (`use_actual=True`, a Quantity with units) are passed in their units. Multipliers are
   multiplied by the EnergyConsumer's `p` / `q` (T1). The stored infrasys data are already normalized, so
   `NormalizationMax` / `NormalizationByValue` need no extra step; the test pins this.
3. Times: `SingleTimeSeries` gives start + n × resolution; `NonSequentialTimeSeries` gives its timestamps.
4. `timeSeriesKind = schedule`; `interpolationKind = previous` (a sample holds for its interval, as an OpenDSS
   fixed-interval loadshape). To confirm against OpenDSS.
5. Irradiance and `pu_voltage` series, and every other component's series, keep the one drop warning (T2, T3).
   `Deterministic` raises (out of scope).

**Export** (`to_model`):
1. For each EnergyConsumer with an `EnergyConnectionSchedule`, read its rows from the points table.
2. Evenly spaced times give a `SingleTimeSeries` (`initial_timestamp`, `resolution`); otherwise a
   `NonSequentialTimeSeries`.
3. `active_power` in kilowatt and `reactive_power` in kilovar, with features `profile_type=PMult` / `QMult`,
   `use_actual=True`, and `profile_name` = the schedule's name when unique, its uri otherwise (ditto names the
   OpenDSS LoadShape from it, so a repeat would merge two shapes).

**As built:** `importer/time_series.py`, `exporter/time_series.py`, `time_points.py` (since 2026-11-16
`cimhub_core.time_points`, the `time-points` extra, so other spokes can use it; `cimhub_gdm` still re-exports
`read_time_points` / `write_time_points`). Choices made while building:
- schedule mRIDs are `<consumer>_pq`, or `_p` / `_q` when P and Q have different times; the name is the series'
  `profile_name` (the OpenDSS loadshape), else the load's name;
- a series is a multiplier when its `use_actual` feature is False; with no feature, when its data have no units
  (ditto labels multipliers kilowatt, so the feature decides first);
- two series of one variable on a load raise (X5: the role has no home yet), as do repeated times (X10);
- on export, a schedule's `interpolationKind` must be `previous` or unset (GDM keeps none); a `p` or `q` column
  null at only some times raises; schedules with no points, or no `time_points` at all, warn and export no series.

**Tests:** `tests/test_time_series.py`, with the expected points written out in the test rather than as golden files.
It covers multiplier and actual loads, P-only and split time bases, XML + Parquet → reload (the schedules diff
clean, the rows come back equal), the warnings, and GDM → CIM → GDM in actual values. The sidecar's own checks
(orphan and repeated rows, a schedule with no points, the schema) moved with it to `cimhub_core/tests/test_time_points.py`. The
ditto test (`test_export_ditto.py`) checks one LoadShape per load with `UseActual=yes` in OpenDSS.

## 6. Scale (N6)

One `EnergyConnectionTimePoint` per sample: an 8760-point year is 8760 Identity objects per load, with no sharing (T1).
Probe (a throwaway script, not kept: plain `add_to_graph` per point, cim-graph `write_xml` / `XMLFile`), 100 schedules ×
8760 points on one load:

| step | time | size |
|---|---|---|
| build (876,000 points) | 112 s (under `tracemalloc`, which slows it) | 819 MB traced peak |
| write_xml | 17 s | 598 MB on disk, about 680 bytes per point |
| reload (`XMLFile`) | 206 s | |
| whole run | 5 min 43 s | 5.8 GB peak resident |

So a year-long hourly series on every load of a real feeder is too heavy as objects: hundreds of MB per hundred
loads, minutes to reload, gigabytes of memory.

The same 876,000 points as one Parquet table (T6's layout, zstd, pyarrow 24):

| step | time | size |
|---|---|---|
| write | 0.6 s | 0.7 MB on disk (the probe's data repeat daily; real shapes compress less, up to the 25 MB in memory) |
| read all | 0.03 s | 25 MB in memory |
| read one schedule (filter on its uri) | 0.014 s | 8760 rows |
| whole run | | 0.3 GB peak resident |

Hence T6. Through the spoke as built (200 loads × 8760 hourly points = 1.75 M rows, one synthetic run): import
0.9 s, write Parquet 0.2 s (8.4 MB), read and check 0.5 s, export 1.8 s, 1 GB peak resident for the whole run.

## 7. Cross-check: OpenDSS shapes and GridLAB-D players (2026-11-11)

Can the T1 design carry what the DSS and GLM spokes will need, so that DSS → CIM, GLM → CIM and DSS → ditto → GDM →
CIM agree (`tests/cross_format/`)? Neither spoke maps time series today: DSS marks every `yearly` / `daily` / `duty`
/ `T*` reference untranscribed (DSS-11), and GLM maps a `<schedule>.value*K` base as K, with the schedule TODO
(S4a-2). Players are not in the GLM schema. Sources: OpenDSS `LoadShape.pas` (`GetMultAtHour`), GridLAB-D
`tape/player.cpp`, ditto 0.1.8 `readers/opendss/components/loadshapes.py`.

### What each format means

| | OpenDSS LoadShape | GridLAB-D player | GDM (ditto) |
|---|---|---|---|
| values | multipliers on the element's kW / kvar, or actual (`UseActual`) | actual values of the target property (a complex VA as `P+Qj`, or `.real` / `.imag` alone) | multipliers or actual, `use_actual` feature |
| time axis | fixed `Interval` (sample k, counted from 1, is at k × Interval), or an `Hour` array | absolute timestamps with an optional zone, or `+1h` / `+30s` deltas | `initial_timestamp` + i × `resolution`; sample 1 at 2020-01-01T00:00 |
| between samples | fixed interval: nearest sample (`round`), or the one before (`Interpolation=EDGE`, `floor`); `Hour` array: linear (AVG) or the one before (EDGE) | the value holds until the next record | not stated |
| after the last sample | wraps around (`i mod NumPoints`): a 24-point daily shape repeats every day | stops, unless `loop N` replays the file (relative records only) | not stated |
| Q without its own series | Q multiplier = P multiplier; zero when `UseActual` | only what is played | no `reactive_power` series |
| role | one element can have a `yearly`, a `daily` and a `duty` shape, each for its own solution mode | one player per target | role not kept |
| scope | Load, Generator, Storage (dispatch), PVSystem (irradiance; `T*` temperature), Vsource, Isource, StorageController | any property: load power (per phase), meter voltage, switch status, capacitor, tap, inverter output | load P/Q, PV irradiance, source pu voltage |

### Fits the design as it stands

- Load P/Q from either format becomes EnergyConnectionSchedule p/q in actual values (T1). For DSS, the rule is
  `q(t) = Pmult(t) × kvar` when the shape has no QMult (zero with `UseActual`). The GDM importer uses the same
  rule when a load has only an `active_power` multiplier series, since that is what ditto's DSS deck does with it.
- A DSS `Hour` array and a GLM player are irregular: their times go straight to `atTime`.
- A GLM player is a step function: `interpolationKind = previous`. A player listing several targets
  (`property constant_power_A,constant_power_B`) is one series per target.
- Beyond loads, the classes exist when the time comes:
  - Generator and Storage dispatch (on the RotatingMachine or PowerElectronicsConnection, both EnergyConnections),
    with p(t) in the load sign convention, so generation is negative;
  - GLM players on switches (`SwitchSchedule.open`), capacitors (`ShuntCompensatorSchedule.sections`) and taps
    (`TapSchedule.step`).

### Gaps

| # | gap | affects | proposal |
|---|---|---|---|
| X1 | **Time zones.** GLM timestamps carry a zone; DSS and ditto times are naive. | GLM | `atTime` is a UTC instant (B16 item 5). The GLM exporter writes it back in the model's `clock` timezone. |
| X2 | **The epoch and the one-interval offset.** DSS has no date: time 0 is the start of the run, and sample k is in force from k × Interval (EDGE; AVG agrees at the solution steps). ditto puts sample 1 at t = 0, one interval early. | DSS, GDM | `atTime` = the time the value takes effect (`previous`); the epoch is 2020-01-01T00:00:00+00:00, as in ditto. DSS sample k → epoch + k × Interval; GDM sample i → `initial_timestamp` + i × resolution, verbatim. So DSS → CIM and DSS → ditto → GDM → CIM differ by one interval: a listed cross-format difference, and a ditto issue. |
| X3 | **Interpolation.** DSS fixed-interval AVG is nearest-sample, which no `TimeSeriesInterpolationKind` names. | DSS | fixed interval → `previous` (exact at the solution steps, which is how shapes are used); `Hour` + AVG → `linear`; EDGE → `previous`. The DSS exporter writes `linear` as an `Hour` array, and `previous` as `Interval` when even. |
| X4 | **Repetition.** A DSS shape wraps (a daily shape serves a whole year); a GLM player can `loop`. NC schedules have no period or repeat. | DSS, GLM | **P3** (profile): a period or repeat count on BaseTimeSeries. Without it, either expand over a horizon (GLM has `clock` start/stop; a DSS deck may only set it in its solve commands) or drop the repetition with a warning. |
| X5 | **Role.** A DSS Load can have `yearly`, `daily` and `duty` shapes at once; three schedules on one EnergyConsumer can't be told apart. | DSS | `BaseTimeSeries.actionMethod` = `yearly` / `daily` / `duty` (NC: "identification in the case where there is multiple time series for the same validity period and kind"). A stretch of its meaning, so the user's call. |
| X6 | **Per-phase players.** GLM plays `constant_power_A` on its own, but a GLM load is one EnergyConsumer (GLM-4), and no `*Phase` class has a schedule link. | GLM | **P4** (profile): an EnergyConnectionSchedule → phase link, or a phase on the schedule. Without it, per-phase players raise unless every phase is played; when they all are, they are summed with a warning (unequal phases are lost). |
| X7 | **Calendar schedules.** A GLM `schedule` (cron blocks) behind `<schedule>.value*K` repeats by weekday and hour. `EnergyConnectionRegularSchedule` (dayOfWeek, HourPattern, Season, one p/q each) can hold that pattern, but needs one schedule per block. | GLM | Expand over the GLM `clock` into EnergyConnectionTimePoints: p(t) = value(t) × K, split by the ZIP fractions as the static base is (S4a-3). Revisit if the regular-schedule form is wanted. |
| X8 | **Shapes with no CIM home:** PV irradiance shapes (P1), PV temperature `TShape` (`Tyearly` / `Tdaily` / `Tduty`; no class), Vsource / Isource (P2), GrowthShape, PriceShape, StorageController shapes, GLM `climate` weather files. | all | Drop with the one warning, as T2 and T3. XYCurves (`EffCurve`, `P-TCurve`, InvControl curves) are Curves (B12), not time series. |
| X9 | **Scale with no sharing (T1).** As objects, a DSS yearly shape on every load of IEEE 8500 (about 1,200 loads) would be about 10 million points: about 7 GB of XML and tens of GB of memory. | DSS, GDM | **Resolved by T6**: the points live in Parquet (§6: 876,000 points in under 1 s and well under 25 MB). Duplication across loads remains (T1), at a few MB per hundred yearly series. |
| X10 | **ditto upstream.** An `Hour`-array shape has `SInterval` 0, so ditto stamps every sample at 2020-01-01 (all times equal); the shape's role is not kept; sample 1 is at t = 0 (X2). | GDM | Report upstream. The GDM importer raises on repeated timestamps rather than importing them. |

## 8. Load groups (2026-11-21)

GridLAB-D players (`GLM_REWRITE_PLAN.md` §8.9) and OpenDSS yearly LoadShapes (`DSS_REWRITE_PLAN.md` §9) now import
as the user's `ConformLoadSchedule → ConformLoadGroup ← ConformLoad` pattern (2026-11-21): one regular schedule of
multipliers shared by the group's loads, its points `RegularTimePoint` rows in the same sidecar (T6;
`cimhub_core.time_points`). The core shape `load_schedule` also holds a `NonConformLoadGroup` whose schedule is
actual power (`value1Unit` W, `value2Unit` VAr). The GDM export reads both (`exporter/time_series.add_group_series`,
built at the user's "implement the remaining changes across the other spokes"):

| CIM | GDM |
|---|---|
| the group's schedule, `startTime` + n × `timeStep` | one `SingleTimeSeries` per value column: `initial_timestamp` = `startTime` as naive UTC, `resolution` = `timeStep` |
| its loads | the one series attached to every member's DistributionLoad (one `time_series_uuid`), as ditto shares a loadshape |
| ConformLoad: value1, value2 (multipliers) | `active_power` `PMult`, `reactive_power` `QMult` (none when value2 is unset: Q follows P, as in OpenDSS), `use_actual=False`, labelled kilowatt and kilovar as ditto labels a loadshape's multipliers (its writer needs units) |
| NonConformLoad: value1 in W or kW, value2 in VAr or kVAr | the same, in kilowatt and kilovar, `use_actual=True` |
| `profile_name` | the group's name; its uri when two groups share a name |
| a group with no schedule, or no points | no series; one WARNING naming the groups |

**The import is unchanged (T1).** A GDM series still imports as one `EnergyConnectionSchedule` per load in actual
values, so CIM → GDM → CIM turns a group into per-load schedules (the test pins it: the group's multipliers times
each load's p and q). Importing a shared multiplier series as a ConformLoad group instead would change T1, which is
the user's call. Tests: `test_time_series.py` (5), `test_export_ditto.py` (1).
