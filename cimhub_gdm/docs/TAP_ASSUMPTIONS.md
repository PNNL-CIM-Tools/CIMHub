# Tap assumptions (for later review)

Recorded 2026-11-09, when X3 was built. These are the choices the GDM importer and exporter make about transformer
and regulator taps that are not forced by CIM or GDM. Several are there only because of what ditto 0.1.8 can write.
Each entry says why it was chosen, how it would show up as a problem, and what the fix would be.

The tap ratio is always computed by the core getter `get_tap_ratio`:
`1 + (position − neutralStep) × stepVoltageIncrement / 100`.
`TapChanger.step` is a tap position, never a ratio.

## Exporter (CIM → GDM)

### T1. A transformer's taps go on its catalog, not the instance

- **Rule.** Each winding's actual ratio, read from its end's RatioTapChanger, is written to the catalog winding's
  `tap_positions`. `DistributionTransformer.tap_positions` is left unset, and GDM fills it with 1.0.
- **Why.** ditto 0.1.8's OpenDSS Transformer has no instance tap field (`Tap_wdg` is not an altdss field), so an
  instance tap never reaches OpenDSS. Through ditto, the atom `t_ln` with its tap on the instance solved as if
  untapped. With the tap on the catalog it matched within 1e-4 pu.
- **Cost.**
  - Instances of one catalog on different taps split it: `ln1`, `ln1_2`, …
  - A GDM-origin instance tap comes back as a catalog tap (a listed GDM-level difference).
  - GDM's own meaning, a shared catalog with per-instance taps, is not what the export writes.
- **Watch for.**
  - Many `<catalog>_<n>` variants on real feeders.
  - A GDM consumer other than ditto that reads instance taps and ignores catalog ones.
- **Fix.** Write the instance's `tap_positions` instead, and keep the catalog nominal; once ditto writes instance
  taps, the catalog no longer splits. The importer reads either (G4), so only the exporter changes.

### T2. A regulator's tap goes on the instance, not the catalog

- **Rule.** This is the opposite of T1:
  - `DistributionRegulator.tap_positions` is `[[1.0], [ratio]]`: the tapped winding's actual ratio, and 1.0 on the
    other winding.
  - The equipment's taps are nominal.
- **Why.** A regulator's tap is its controller's state, not a property of the unit. Putting it on the catalog would
  split the shared TapChangerInfo equipment by every tap the bank's units happen to sit on (`reg3`, `reg3_2`,
  `reg3_3`).
- **Cost.** ditto drops instance taps (T1), so OpenDSS starts every regulator at tap 0, and its RegControl has to step
  the whole way. On IEEE13 the deck's starting taps (10, 8, 11) are lost.
- **Watch for.** Regulators that reach the wrong tap in OpenDSS, or that run out of control iterations.
- **Fix.** Use the T1 rule for regulators too, accepting the catalog split. Or get ditto to write instance taps.

### T3. One ratio per winding, repeated on every phase

- **Rule.** A catalog winding's `tap_positions` is the same ratio once per phase (`num_phases` entries).
- **Why.** CIM holds one RatioTapChanger per TransformerEnd, so a winding has one tap.
- **Cost.**
  - GDM can hold a different tap per phase; CIM-origin GDM never will.
  - On import, phases with different taps raise (`winding_tap`).
- **Fix.** Per-phase taps would need a tap changer per phase end in CIM (a TransformerTankEnd or PhaseEnd shape),
  which is a builder and CIM question.

### T4. The actual position is required

- **Rule.** The exporter reads `get_tap_ratio(which='actual')`, i.e. `step`. An unset `step` raises. There is no
  fallback to `normalStep`.
- **Why.** The getter has no default because the actual and normal positions differ in any model that is not as
  built. Both importers write `step`.
- **Watch for.** CIM from a source that only sets `normalStep` (a planning model) raises `step is unset`.
- **Fix.** Use `which='normal'` when `step` is unset, as a documented fallback rule.

### T5. A winding with no tap changer gets GDM's default range

- **Rule.** `total_taps`, `min_tap_pu` and `max_tap_pu` come from the end's RatioTapChanger:
  - `total_taps` = highStep − lowStep;
  - `min_tap_pu` and `max_tap_pu` are the ratios at lowStep and highStep.

  With no tap changer, the fields are left at GDM's defaults: 32 taps, 0.9–1.1 pu.
- **Why.** GDM requires the fields, and the defaults are what the importer's atoms use, so GDM-origin systems
  round-trip.
- **Cost.**
  - A fixed-tap transformer is exported claiming a ±10 % range in 32 steps.
  - ditto writes it as OpenDSS `MinTap`, `MaxTap` and `NumTaps`. Those only matter if something later controls that
    winding.
- **Watch for.** A consumer that treats `total_taps` as "this unit has a tap changer".

### T6. A regulator's range comes from its tapped end only

- **Rule.** Only the tapped winding gets the RatioTapChanger's range. The other winding has GDM's defaults (T5).
- **Cost.** Nothing through ditto, which taps one winding (`Winding=` on the RegControl).

### T7. `max_step` is the full range

- **Rule.** `RegulatorController.max_step` = highStep − lowStep. This is an X4 fill, counted in the WARNING.
- **Why.** CIM has no steps-per-iteration limit, so the full range means no limit.
- **Cost.** ditto writes `MaxTapChange=32`, where OpenDSS's own default is 16.

### T8. Tap control on a PowerTransformer (an LTC) raises

- **Rule.** A PowerTransformer whose RatioTapChanger has a TapChangerControl raises `no GDM export yet`.
- **Why.** GDM regulates through DistributionRegulator, and no CIM sample needed this yet.
- **Fix.** Export an LTC as a DistributionRegulator on its PowerTransformer's windings. That needs one controller per
  phase (a GDM rule).

## Importer (GDM → CIM), which the exporter must invert

### T9. Instance taps, else the catalog's (G4, user 2026-11-08)

- **Rule.** A winding's tap is the instance's when the instance's taps are set and off nominal, else the catalog
  winding's. Both off nominal and different raises.
- **Why.** ditto's DSS reader writes a DSS tap on the catalog.

### T10. Taps must be symmetric whole steps about 1.0

- **Rule.** `tap_step` writes:
  - highStep = total_taps / 2;
  - lowStep = −total_taps / 2;
  - neutralStep = 0;
  - stepVoltageIncrement = (max − min) / total × 100 %.

  An odd tap count, a range that is not symmetric about 1.0, or a tap that is not a whole step raises.
- **Watch for.** Real equipment with asymmetric ranges (e.g. +5 % / −15 %), or taps given as arbitrary ratios.
- **Fix.** Pick neutralStep so the range need not be symmetric. Or allow fractional ratios through
  stepVoltageIncrement.

### T11. normalStep differs between transformers and regulators

- **Rule.**
  - A transformer's RatioTapChanger gets normalStep = step (the tap as found).
  - A regulator's gets normalStep = 0 (neutral) and step = the tap.
- **Why.** A regulator's tap moves under control, so its normal position is neutral. A transformer's off-load tap is
  set and left.
- **Watch for.** Anything that reads `normalStep` (T4's fallback, if it is ever added) would see a different meaning
  for the two.

### T12. A center tap's halves are never off nominal

- **Rule.** A center-tap half with a tap other than 1.0 raises: its two halves share one PowerTransformerEnd, and so
  one tap changer.

### T13. A transformer's tap changer has no control

- **Rule.** An off-nominal winding gets a RatioTapChanger `<end>_tap` with no TapChangerControl. Only regulators get
  controls.
- **Note.** This is the inverse of T8, so a GDM DistributionTransformer never becomes an LTC.

## Where these live

| assumption | code |
|---|---|
| T1, T3, T4, T5 | `exporter/transformer.py` (`winding_equipment`, `tap_ratio`, `tap_range`) |
| T2, T6, T7 | `exporter/regulator.py` (`export`, `controller`) |
| T8 | `exporter/transformer.py` `export` |
| T9, T10, T12, T13 | `importer/transformer.py` (`winding_tap`, `tap_step`, `add_tap`) |
| T11 | `importer/transformer.py` `add_tap`, `importer/regulator.py` `add_tap_changer` |
| tests | `test_export_gdm_level.py` (`TRANSFORMER_DIFFERENCES`, `test_a_catalog_splits_by_tap`), `test_export_ditto.py` |
