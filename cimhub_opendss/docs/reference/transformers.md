# Transformers and regulators

`XfmrCode`, `Transformer` and `RegControl`: how each becomes CIM templates, power transformers, voltage regulators and tap
changers, and how they come back. How to read the tables is on the [reference landing page](index.md).

| DSS | CIM (cim18v17) | Import (shape) | Export |
|---|---|---|---|
| `XfmrCode` | `TransformerTankConfiguration` and its ends, lugs, windings and mesh | `xfmrcode.cimtbl` (`transformer_template`, `transformer_template_1ph`) | `XfmrCode`, one per configuration a unit uses |
| `Transformer`, 3 phases | `PowerTransformer`, `PowerTransformerEnd` per bus, `TransformerMeshImpedance` | `transformer.cimtbl` (`transformer_by_ends`) | `Transformer` |
| `Transformer`, 1 phase | `PowerTransformer`, `TransformerTank`, `TransformerPhaseEnd`, `TransformerWinding`, mesh | `transformer.cimtbl` (`transformer_by_phase_ends`) | `Transformer` |
| `Transformer` by `XfmrCode` | `PowerTransformer` with a `TransformerTank` on the template | `transformer.cimtbl` (`transformer_by_template`) | `Transformer` with `XfmrCode=` |
| `Transformer` a `RegControl` names, equal winding kV | `VoltageRegulator`, `AutoTransformerEnd`, `TransformerMeshImpedance` | `transformer.cimtbl` (`voltage_regulator`) | `Transformer`, inline |
| `Transformer` a `RegControl` names, step-down (an LTC) | `PowerTransformer` as above, with a tap changer on the controlled end | `transformer.cimtbl` | `Transformer` |
| `RegControl` | `TapChangerControl` and `RatioTapChanger` | `regcontrol.cimtbl` | `RegControl` |
| (CIM only) `AutoTransformer` | `AutoTransformer` | not produced | a `Transformer`, inline |

The shapes are on the core site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/), and the
getters the exporter reads through (`get_transformer_model`, `get_tap_changer_control`) are on its
[transformers reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/transformers/).

**The rating rule.** A winding's `baseU` is the DSS `kV` (the coil voltage), `ratedU` is phase to phase, and `baseS` is
winding 1's `kVA` on every coil, because DSS puts every `x` on winding 1's `kVA`. A split-phase half is rated `kVA / 2`.
The mesh `x` is in percent on the From winding's `baseU` and `baseS`. A 3-phase transformer is by balanced ends: `ratedU`
is the DSS `kV`, `ratedS` the `kVA`, `r` is percent on the end's own rating, and `x` is on the mesh between ends.

## XfmrCode

A code is a template its transformers share by name, built from the instances that use it because `ratedU` (phase to
phase) is not fixed by the coil voltage alone: 7.2 kV is 7200/12470Y on a 3-phase system. Every unregulated instance must
give the same template, else it raises. A code that no unregulated `Transformer` uses is not written; its regulators
take its values directly.

| Code | Template |
|---|---|
| 3 phases | a `TransformerTankEnd` per winding (`connectionKind`, `rground`, `xground`) and a `TransformerWinding` each; instance end n is template end n |
| 1 phase, center tap (3 windings, windings 2 and 3 a split-phase secondary on `bus.1.0` and `bus.0.2`) | `TransformerLug`s `H1 H2 X1 X3 X2` and windings H1 to H2, X1 to X2 (s1 to N), X2 to X3 (N to s2) |
| 1 phase, any other | two lugs per winding, `H1 H2`, `X1 X2`, `Y1 Y2`, numbered in each coil's node order (its direction) |

| property | import | export |
|---|---|---|
| `name` | copied to `TransformerTankConfiguration.name`; mRID = xc_ + name, lowercased | written: Names, the XfmrCode namespace |
| `phases` | structural: 3: TankEnd template; 1: lug template (a center tap's H1 H2 X1 X3 X2, else two lugs per winding) | written: as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| `windings` | structural: one TransformerWinding each; 2 or 3 | written: as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| `wdg` | structural: the winding Rneut/Xneut belong to (the reader's tag); none = the last | written: as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| `conn` | structural: the active-winding form; the reader folds wdg= blocks and bare values into the arrays | not written: the active-winding form; the arrays carry every winding |
| `kV` | structural: the active-winding form; the reader folds wdg= blocks and bare values into the arrays | not written: the active-winding form; the arrays carry every winding |
| `kVA` | structural: the active-winding form; the reader folds wdg= blocks and bare values into the arrays | not written: the active-winding form; the arrays carry every winding |
| `tap` | structural: the active-winding form; the reader folds wdg= blocks and bare values into the arrays | not written: the active-winding form; the arrays carry every winding |
| `pct_R` | structural: the active-winding form; the reader folds wdg= blocks and bare values into the arrays | not written: the active-winding form; the arrays carry every winding |
| `Rneut` | structural: TankEnd rground (ohm) of its winding when >= 0; on a 1-phase code raises | written: as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| `Xneut` | structural: TankEnd xground (ohm) of its winding, with Rneut >= 0 | written: as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| `conns` | structural: TankEnd connectionKind (D, Y; grounding is the instance's); a center tap's secondary halves are I; default wye | written: as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| `kVs` | structural: winding baseU (the coil); ratedU phase-to-phase from the instances' common bus system (x sqrt 3 on a 3-phase system, x 2 for a split-phase half), and instances that disagree raise | written: as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| `kVAs` | structural: winding ratedS (a split-phase half: kVA / 2); baseS = winding 1's kVA on every coil (per phase on a 3-phase code) | written: as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| `taps` | structural: a tap other than 1 raises (a fixed tap is not mapped yet) | not written: a tap is the instance's |
| `Xhl` | structural: mesh 1-2 x (percent on the From winding's baseU and baseS); default 7 | written: as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| `Xht` | structural: mesh 1-3 x; default 35 | written: as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| `Xlt` | structural: mesh 2-3 x; default 30 | written: as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| `X12` | structural: alias of Xhl | not written: untranscribed on import; not in CIM |
| `X13` | structural: alias of Xht | not written: untranscribed on import; not in CIM |
| `X23` | structural: alias of Xlt | not written: untranscribed on import; not in CIM |
| `Xscarray` | untranscribed: for more than 3 windings, which raise | not written: more than 3 windings raise |
| `pct_Rs` | structural: winding r (percent on its own baseS); default 0.2 | written by rule: as the Transformer's (windings.py), read through the first unit; every unit must give the same; unset r -> 0 |
| `pct_loadloss` | derived: when pct_Rs is unset, r = loadloss / 2 on windings 1 and 2; set with pct_Rs, the two must agree | not written: %Rs carries the winding r |
| `pct_noloadloss` | derived: TransformerTankConfiguration.noLoadLoss (kW) = % x winding 1 kVA | written: as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| `pct_imag` | copied to `TransformerTankConfiguration.percentMagnetizingCurrent` (percent) | written: as the Transformer's (windings.py), read through the first unit; every unit must give the same |
| `MaxTap` | untranscribed: tap changer range; a regulated instance takes it; else untranscribed | not written: a tap is the instance's |
| `MinTap` | untranscribed: tap changer range; a regulated instance takes it; else untranscribed | not written: a tap is the instance's |
| `NumTaps` | untranscribed: tap changer range; a regulated instance takes it; else untranscribed | not written: a tap is the instance's |
| `RdcOhms` | copied to `TransformerWinding.rDC` (ohm), per template winding, only when set | written: each template winding's rDC (ohm), one `wdg=n RdcOhms=v` block per winding, last on the line |
| `Seasons` | structural: the number of `Ratings`; one by default, and a count other than the Ratings' raises | written by rule: the number of the template's season ratings; none -> not written |
| `Ratings` | copied to `ApparentPowerLimit.normalValue` (kVA): one per season n, of type `olt_season<n>`, in the template's own `OperationalLimitSet` `xc_<name>_ratings`, which the template names | written by rule: the template's ApparentPowerLimits of type olt_season<n> (kVA), in season order; none -> not written |
| `like` | untranscribed: the reader resolves like= before mapping | not written: the writer never writes like= |
| `ppm_antifloat`, `thermal`, `n`, `m`, `flrise`, `hsrise`, `normhkVA`, `emerghkVA` | untranscribed (listed in the table comment) | not written |

**Fail fast.** More than 3 windings; `phases` other than 1 or 3; `Rneut` on a 1-phase code; a fixed `taps` other than 1; two
instances that give the code different templates (for example on different bus systems); a center tap whose secondary is not on
`bus.1.0` and `bus.0.2`; `kVAs` that differ where a base is shared; `RdcOhms` on some windings only; `Seasons` without
`Ratings`, or a `Ratings` count other than `Seasons`.

**Seasonal ratings.** A code's `Ratings` are its template's own limits: an `OperationalLimitSet` written alone, with one
`ApparentPowerLimit` per season, and an `Update` of the `TransformerTankConfiguration` that names it
(`EquipmentConfiguration.OperationalLimitSet`, a GridAPPS-D extension of the profile). The instances do not inherit them.
The season types `olt_season1`, `olt_season2`, ... are declared once in the master. Excerpt from
`cimhub_opendss/tests/atoms/xfmrcode/rated.cimtbl` (code `sub` with `RdcOhms` on each winding and `Seasons=2
Ratings=[22000 25000]`):

```
# RdcOhms: the winding's dc resistance, copied
Update Table TransformerWinding: mRID, rDC (ohm)
    xc_sub_wdg_1, 2.8103125
    xc_sub_wdg_2, 0.011014647

# the seasonal ratings: Ratings, one ApparentPowerLimit per season
Table OperationalLimitSet: mRID
    xc_sub_ratings

Table ApparentPowerLimit: mRID, normalValue (kVA), OperationalLimitType, OperationalLimitSet
    xc_sub_ratings_1, 22000.0, olt_season1, xc_sub_ratings
    xc_sub_ratings_2, 25000.0, olt_season2, xc_sub_ratings

Update Table TransformerTankConfiguration: mRID, OperationalLimitSet
    xc_sub, xc_sub_ratings
```

**Expected differences.** A regulator by `XfmrCode` comes back inline: CIM has no `AutoTransformer` template. A configuration
no unit uses has no `XfmrCode` on export (logged), because a template alone does not say its phases. An instance with a tap changer gets
`MaxTap`, `MinTap` and `NumTaps` of its own, since the tap range is the instance's, not the code's.

Excerpt from `cimhub_opendss/tests/atoms/xfmrcode/codes.cimtbl` (the center-tap code `ct25` and the 3-phase code `sub`):

```
Table TransformerTankConfiguration: mRID, name, percentMagnetizingCurrent (percent), noLoadLoss (kW)
    # defaulted: conns=wye
    # built from 2 instances (t1, ...)
    xc_ct25, ct25, 0.5, 0.05
    # built from 1 instance (sub, ...)
    xc_sub,  sub,  0.4, 20.0

Table TransformerTankEnd: mRID, TankConfiguration, endNumber, connectionKind, rground (ohm), xground (ohm)
    xc_sub_end_1, xc_sub, 1, D, ,
    xc_sub_end_2, xc_sub, 2, Y, ,
```

## Transformer

An instance becomes one `PowerTransformer` with one `PowerTransformerEnd` per distinct bus, and the end's Terminal carries
its phases (`ABCN`, `AN`, `AB`, `s1s2N`). A 1-phase transformer adds a `TransformerTank`, a `TransformerPhaseEnd` per phase of
each terminal and a `TransformerWinding` per DSS winding, between the phase ends of its two conductors.

**Defaults.** Each default is listed in the row comment: `conns` wye, `%Rs` 0.2 (or `%LoadLoss` split over windings 1 and 2),
`XHL` 7, `XHT` 35, `XLT` 30, `phases` 3. `%noloadloss` is end 1's `g` (3 phases) or the tank's `noLoadLoss`
(= percent x winding 1's kVA); `%imag` is end 1's `b` or the tank's `percentMagnetizingCurrent`.

**Regulators.** A `Transformer` named by a `RegControl` whose windings have equal `kV` is a `VoltageRegulator`: two
`AutoTransformerEnd`s with the nameplate (`baseU`, `ratedS`, a PhaseCode: `AN`, `AB`, or `ABCN` for a 3-phase wye) and the
engine's stand-in mesh impedance, `r` = %R1 + %R2 and `x` = `XHL`. A regulator has no home for `%imag` or `%noloadloss`,
which the row comment lists. A regulator takes its code's values when it names an `XfmrCode`. A step-down regulated
transformer (an LTC) stays a `PowerTransformer`.

**DC resistance and seasonal ratings.** `RdcOhms` is per winding; DSS has no array form, so the reader puts each value
at the active `wdg=`'s place. The values are copied verbatim to the 1-phase transformer's `TransformerWinding.rDC`
(ohm), as an `Update` of the windings. `Ratings` (kVA) become one `ApparentPowerLimit` `xf_<name>_ratings_<n>` per
season n, of type `olt_season<n>`, in the `OperationalLimitSet` `xf_<name>_ratings` on the PowerTransformer (a
regulator's on its VoltageRegulator). The master declares the season types, as many as the most seasons any
`Transformer` or `XfmrCode` rates. An instance by `XfmrCode` gets only its own ratings; the code's stay on the template
(a regulator takes its code's, as it takes every other value).
`normhkVA` and `emerghkVA` stay untranscribed. Excerpt from `cimhub_opendss/tests/atoms/transformer/rated.cimtbl` (the
EPRI J1 service with `RdcOhms` on each winding and `Seasons=2 Ratings=[44 52]`):

```
# RdcOhms: the winding's dc resistance, copied
Update Table TransformerWinding: mRID, rDC (ohm)
    xf_b13552-1a_wdg_1, 3.9773268
    xf_b13552-1a_wdg_2, 0.004419252

# the seasonal ratings: Ratings, one ApparentPowerLimit per season
Table OperationalLimitSet: mRID, Equipment
    xf_b13552-1a_ratings, xf_b13552-1a

Table ApparentPowerLimit: mRID, normalValue (kVA), OperationalLimitType, OperationalLimitSet
    xf_b13552-1a_ratings_1, 44.0, olt_season1, xf_b13552-1a_ratings
    xf_b13552-1a_ratings_2, 52.0, olt_season2, xf_b13552-1a_ratings
```

| property | import | export |
|---|---|---|
| `name` | copied to `PowerTransformer.name`; mRID = xf_ + name, lowercased | written: Names; a one-unit transformer by itself, each tank of several by the tank |
| `phases` | structural: 1 = by phase ends, 3 = by balanced ends; default 3 | written: 3 when every winding has A, B, C, else 1 (a coil); inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| `windings` | structural: 2 or 3; must match the buses | written: the model's windings, 2 or 3; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| `wdg` | structural: the winding Rneut/Xneut belong to (the reader's tag); none = the last | written: the one winding grounded through rground/xground |
| `bus` | structural: the active-winding form; the reader folds wdg= blocks into the arrays, and a bare value raises | not written: the active-winding form; the arrays carry every winding |
| `conn` | structural: the active-winding form; the reader folds wdg= blocks into the arrays, and a bare value raises | not written: the active-winding form; the arrays carry every winding |
| `kV` | structural: the active-winding form; the reader folds wdg= blocks into the arrays, and a bare value raises | not written: the active-winding form; the arrays carry every winding |
| `kVA` | structural: the active-winding form; the reader folds wdg= blocks into the arrays, and a bare value raises | not written: the active-winding form; the arrays carry every winding |
| `tap` | structural: the active-winding form; the reader folds wdg= blocks into the arrays, and a bare value raises | not written: the active-winding form; the arrays carry every winding |
| `pct_R` | structural: the active-winding form; the reader folds wdg= blocks into the arrays, and a bare value raises | not written: the active-winding form; the arrays carry every winding |
| `Rneut` | structural: rground (ohm) of its winding's end when >= 0; negative = no impedance | written: rground (ohm) of winding wdg; its neutral on .4 |
| `Xneut` | structural: xground (ohm) of its winding's end, with Rneut >= 0 | written: xground (ohm) of winding wdg |
| `buses` | structural: end node and terminal phases; one end per distinct bus | written: bus_ref of each winding's phases: a coil's N on .0; a 3-phase wye solid .1.2.3, else .1.2.3.4 |
| `conns` | structural: connectionKind, grounded, default nodes; default wye | written: connectionKind D -> delta, Y/Yn/I -> wye; AUTO: wye with a neutral; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| `kVs` | structural: 3-phase: end ratedU; 1-phase: winding baseU, ratedU derived (x sqrt 3, x 2) | written: a coil's or an AutoTransformerEnd's baseU, a 3-phase winding's ratedU (kV); inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| `kVAs` | structural: end ratedS / winding ratedS (halves / 2); winding 1's kVA is every baseS | written: a coil's baseS (AUTO: ratedS), a 3-phase winding's ratedS (kVA); inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| `taps` | structural: the regulated winding's tap is RatioTapChanger.step (regcontrol.cimtbl); any other tap other than 1 raises | written: 1, and get_tap_ratio(actual) on the RatioTapChanger's winding |
| `XHL` | structural: mesh 1-2 x (percent on winding 1's kVA); default 7 | written: mesh (1,2) x, percent on winding 1's kVA; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| `XHT` | structural: mesh 1-3 x; default 35 | written: mesh (1,3) x; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| `XLT` | structural: mesh 2-3 x; default 30 | written: mesh (2,3) x; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| `X12` | structural: alias of XHL | not written: untranscribed on import; not in CIM |
| `X13` | structural: alias of XHT | not written: untranscribed on import; not in CIM |
| `X23` | structural: alias of XLT | not written: untranscribed on import; not in CIM |
| `Xscarray` | untranscribed: for more than 3 windings, which raise | not written: more than 3 windings raise |
| `pct_Rs` | structural: 3-phase: end r (percent); 1-phase: winding r (percent); default 0.2 | written by rule: winding r x kVA_n / kVA_1; unset -> 0; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| `pct_loadloss` | derived: when pct_Rs is unset, r = loadloss / 2 on windings 1 and 2; set with pct_Rs, the two must agree | not written: %Rs carries the winding r |
| `pct_noloadloss` | derived: 3-phase: end 1 g (percent); 1-phase: tank noLoadLoss = % x kVA; a regulator has no home for it (row comment) | written: the core g (percent on winding 1's kVA); unset -> not written; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| `pct_imag` | structural: 3-phase: end 1 b (percent); 1-phase: tank percentMagnetizingCurrent; a regulator has no home for it (row comment) | written: the core b (percent); unset -> not written; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| `MaxTap` | structural: the RatioTapChanger range of a regulated transformer (regcontrol.cimtbl); else untranscribed; default 1.1 | written: get_tap_ratio(high) |
| `MinTap` | structural: the RatioTapChanger range of a regulated transformer (regcontrol.cimtbl); else untranscribed; default 0.9 | written: get_tap_ratio(low) |
| `NumTaps` | structural: the RatioTapChanger range of a regulated transformer (regcontrol.cimtbl); else untranscribed; default 32 | written: highStep - lowStep |
| `RdcOhms` | copied to `TransformerWinding.rDC` (ohm), per winding, only when set, on a 1-phase transformer's coils; on a 3-phase transformer by balanced ends (no TransformerWinding) or a regulator it raises | written by rule: each winding's rDC (ohm), one `wdg=n RdcOhms=v` block per winding, last on the line; an end has none -> not written; inline units only; a unit on a TankConfiguration takes it from its XfmrCode |
| `Seasons` | structural: the number of `Ratings`; one by default, and a count other than the Ratings' raises | written by rule: the number of season ratings; none -> not written |
| `Ratings` | copied to `ApparentPowerLimit.normalValue` (kVA): one per season n, of type `olt_season<n>`, in the `OperationalLimitSet` `xf_<name>_ratings` on the PowerTransformer (a regulator's on its VoltageRegulator) | written by rule: the PowerTransformer's ApparentPowerLimits of type olt_season<n> (kVA), in season order; other types are not written; none -> not written |
| `XfmrCode` | structural: a regulated instance takes the code's values (with_code); any other waits for the template and is counted on the master | written: the unit's TankConfiguration (BY_TANK_ENDS, BY_LUGS) |
| `enabled` | copied to `PowerTransformer.normallyInService` | written: get_in_service(which='normal'); unset -> not written |
| `like` | untranscribed: the reader resolves like= before mapping | not written: the writer never writes like= |
| `thermal`, `n`, `m`, `flrise`, `hsrise`, `normhkVA`, `emerghkVA`, `normamps`, `emergamps`, `sub`, `subname`, `ppm_antifloat`, `bank`, `XRConst`, `LeadLag`, `Core`, `faultrate`, `pct_perm`, `repair`, `basefreq` | untranscribed (listed in the table comment) | not written |

**Fail fast.**

- A bare `bus`, `conn`, `kV`, `kVA`, `tap` or `pct_R` without `wdg=` or an array: the winding it belongs to is not recorded.
- `windings` not 2 or 3, or not one bus each; `kVs`, `kVAs`, `conns` or `pct_Rs` with the wrong count.
- `Transformer t: taps=[1.0, 1.05] with no RegControl; a fixed tap is not mapped yet`.
- `pct_Rs` and `pct_loadloss` that disagree; `XHL` and `X12` (and the other aliases) that disagree.
- A 3-phase end that is not on nodes 1.2.3; windings that share a bus without being a split-phase secondary.
- A mesh whose From winding does not carry winding 1's `kVA`; a 1-phase transformer whose windings differ in `kVA`.
- An `XfmrCode` that is undefined, or a slot set on both the instance and its code.
- A transformer named by two `RegControl`s; a regulator with other than two windings on two buses, with unequal `kVA`, or with a neutral impedance.
- A bus the topology walk did not reach.
- `RdcOhms` on some windings and not others (the engine's default for the rest, 85 % of %R in ohms, is not
  transcribed); `RdcOhms on a 3-phase transformer by balanced ends`; `RdcOhms on a regulator; an AutoTransformerEnd has
  no rDC`.
- `Seasons` without `Ratings` (the engine pads its default rating with zeros), and `Ratings` with a count other than
  `Seasons` (the engine keeps only `Seasons` of them, one by default). The engine also zeroes the Ratings when
  `Seasons` comes after `Ratings` on the line; the reader does not record that order, so this case is not caught.
- On export, `rDC` on some windings only, season ratings that are not seasons 1..n, ratings on a transformer of
  several units, a winding with `connectionKind` or `grounded` unset, a tap changer on a several-tank transformer, tap changers on two windings, a `PhaseTapChanger`, a `neutralU` that is not the winding's kV, a mesh `r` outside an `AutoTransformer`, a missing mesh pair, a neutral impedance on more than one winding, more than 3 windings, an `AutoTransformer` whose two windings differ in kVA, and a delta winding with a neutral.

**Export.** One DSS `Transformer` per unit (a tank, or a transformer without tanks). A unit on a `TransformerTankConfiguration`
writes `XfmrCode=`, its buses, taps and `enabled`; every other form is inline. The forms are:

| CIM form | DSS | `kVs`, `kVAs` |
|---|---|---|
| balanced ends (`PowerTransformerEnd` data) | inline, `phases=3` | `ratedU` (line to line), `ratedS`; `%imag`, `%noloadloss` from the core's `b`, `g` |
| a tank's own windings | inline, `phases=1` | `baseU`, `baseS` (the coil) |
| a tank on a template | `XfmrCode=` | on the code |
| `AutoTransformer`, `VoltageRegulator` | inline, `phases` 1 or 3 | `baseU` (line to line on a 3-phase unit), `ratedS`; the mesh `r` is written `%Rs=[r/2 r/2]` |

`connectionKind` D is `delta`; Y, Yn and I are `wye`; an `AutoTransformerEnd` has no kind, so a coil with a neutral is wye
and one between two phases is delta. A 3-phase wye grounded solidly is `.1.2.3`, grounded through `rground`/`xground` is
`.1.2.3.4` with `wdg`, `Rneut` and `Xneut`, and ungrounded is `.1.2.3.4` with no `Rneut`. A coil's grounded neutral is
`.0` and an ungrounded one is `.4`. A tap is `taps=[1 <ratio>]` with `MaxTap`, `MinTap` and `NumTaps` from the step range.
`Seasons` and `Ratings` come from the `olt_season<n>` limits in season order; `RdcOhms` from each winding's `rDC`, written
last as one `wdg=n RdcOhms=v` block per winding (`... Seasons=2 Ratings=[44 52] wdg=1 RdcOhms=3.9773268 wdg=2
RdcOhms=0.004419252`).

**Expected differences.**

- `%LoadLoss` comes back as `%Rs`; defaulted `XHL`, `%Rs` and `conns` come back explicit.
- A 1-phase line-to-line coil written wye comes back delta: the two differ only in the engine's anti-float conductance.
- `ppm_antifloat`, `bank`, `normhkVA`, `emerghkVA`, `LeadLag`, `XRConst`, the thermal and reliability slots are not in CIM; an instance's `ppm=0` comes back at the engine's default.
- A regulator by `XfmrCode` comes back inline. A `kVA` on a center-tap half is the can's, as decks write it.
- `taps` come back as a tap ratio on the one regulated winding and 1 on the rest.

Excerpt from `cimhub_opendss/tests/atoms/transformer/xfm1.cimtbl` (the 3-phase `wdg=` form from IEEE13_CDPSM):

```
Table PowerTransformerEnd: mRID, PowerTransformer, node, phases, endNumber, connectionKind, grounded, rground (ohm), xground (ohm), ratedU (kV), ratedS (kVA), r (percent), b (percent), g (percent), BaseVoltage
    xf_xfm1_1, xf_xfm1, xf1, ABCN, 1, Yn, true, , , 4.16, 500.0, 0.55, , , bv_4p16kv
    xf_xfm1_2, xf_xfm1, 634, ABCN, 2, Yn, true, , , 0.48, 500.0, 0.55, , , bv_480v

# x in percent on winding 1's kVA at the From end's voltage
Table TransformerMeshImpedance: mRID, FromTransformerEnd, ToTransformerEnd, x (percent)
    xf_xfm1_mesh_12, xf_xfm1_1, xf_xfm1_2, 2.0
```

## RegControl

A `RegControl` becomes a `TapChangerControl` and a `RatioTapChanger` on the controlled winding's end of the transformer it
names: an `AutoTransformerEnd` of a regulator, or a `PowerTransformerEnd` of an LTC. The control monitors that end's
Terminal. Settings DSS gives on the 120 V PT secondary become primary volts (x `ptratio`), and line-drop volts become
ohms (x `ptratio` / `CTprim`). `step` is a tap position, never a ratio: with `increment = (MaxTap - MinTap) / NumTaps`,
`step = (tap - 1) / increment`, `lowStep = -(1 - MinTap) / increment` and `highStep = (MaxTap - 1) / increment`, each of
which must be a whole number of steps. `MaxTap`, `MinTap` and `NumTaps` are the transformer's (defaults 1.1, 0.9 and
32, listed as `defaulted`). `ctRatio` is `CTprim / 0.2`, because DSS's CT secondary is 0.2 A.

| property | import | export |
|---|---|---|
| `name` | copied to `TapChangerControl.name`; `RatioTapChanger.name`; mRID = rc_ + name (control) and rc_ + name + _tap (tap changer), lowercased | written: Names, the RegControl namespace |
| `transformer` | structural: the regulator or LTC; a Transformer no New defines, or one two RegControls name, raises | written: the DSS Transformer of the tap's unit (one unit) |
| `winding` | structural: RatioTapChanger.TransformerEnd = xf_&lt;transformer>_&lt;end>; TapChangerControl.Terminal = xf_&lt;transformer>_T&lt;end>, where the end is the winding itself on a regulator and its bus's end otherwise; default 1 | written: the winding whose end holds the RatioTapChanger |
| `tapwinding` | raises when set (not mapped yet) (a tap winding other than the monitored one) | not written: the tap winding is the monitored one |
| `bus` | raises when set (not mapped yet) (remote sensing) | not written: the control must monitor its tap end's Terminal (remote sensing raises) |
| `PTphase` | structural: TapChangerControl.monitoredPhase = the phase of the winding's conductor PTphase (default 1); MAX/MIN raise | written: 1-based place of monitoredPhase among the winding's phase conductors; 1 on a 1-phase winding, whichever of its conductors CIM names |
| `vreg` | derived: targetValue (V) = vreg x ptratio (secondary_to_primary); default 120 | written: targetValue (V) / ptRatio (primary_to_secondary) |
| `band` | derived: targetDeadband (V) = band x ptratio (secondary_to_primary); default 3 | written: targetDeadband (V) / ptRatio (primary_to_secondary); unset -> not written, the engine's default |
| `ptratio` | copied to `TapChangerControl.ptRatio`; `RatioTapChanger.ptRatio`; default 60 | written: ptRatio, the tap's and the control's agreed; unset raises |
| `CTprim` | copied to `RatioTapChanger.ctRating` (A); default 300; also ctRatio = CTprim / 0.2 (the DSS CT secondary, 0.2 A) and the LDC base | written: ctRating (A); unset -> not written, and a line drop then raises |
| `R` | derived: lineDropR (ohm) = R x ptratio / CTprim (line_drop_ohms); default 0; lineDropCompensation = R or X nonzero | written: lineDropR (ohm) x CTprim / ptRatio (line_drop_volts); unset -> not written (0) |
| `X` | derived: lineDropX (ohm) = X x ptratio / CTprim (line_drop_ohms); default 0 | written: lineDropX (ohm) x CTprim / ptRatio (line_drop_volts); unset -> not written (0) |
| `delay` | copied to `RatioTapChanger.initialDelay` (s); default 15 | written: initialDelay (s); unset -> not written |
| `tapdelay` | copied to `RatioTapChanger.subsequentDelay` (s); default 2 | written: subsequentDelay (s); unset -> not written |
| `reversible` | copied to `TapChangerControl.reversible`; default false | written: TapChangerControl.reversible |
| `revvreg` | derived: reverseTargetValue (V) = revvreg x ptratio (secondary_to_primary); default 120 | written: reverseTargetValue (V) / ptRatio (primary_to_secondary); unset -> not written, the engine's default |
| `revband` | derived: reverseTargetDeadband (V) = revband x ptratio (secondary_to_primary); default 3 | written: reverseTargetDeadband (V) / ptRatio (primary_to_secondary); unset -> not written, the engine's default |
| `revR` | derived: reverseLineDropR (ohm) = revR x ptratio / CTprim (line_drop_ohms); default 0 | written: reverseLineDropR (ohm) x CTprim / ptRatio (line_drop_volts); unset -> not written (0) |
| `revX` | derived: reverseLineDropX (ohm) = revX x ptratio / CTprim (line_drop_ohms); default 0 | written: reverseLineDropX (ohm) x CTprim / ptRatio (line_drop_volts); unset -> not written (0) |
| `revThreshold` | copied to `TapChangerControl.reversingPowerThreshold` (kW); default 100 | written: reversingPowerThreshold (kW) |
| `revDelay` | copied to `TapChangerControl.reversingDelay` (s); default 60 | written: reversingDelay (s) |
| `revNeutral` | copied to `TapChangerControl.reverseToNeutral`; default false | written: reverseToNeutral |
| `vlimit` | raises when set (not mapped yet) (home TapChangerControl.maxLimitVoltage) | not written: maxLimitVoltage raises (untranscribed on import) |
| `TapNum` | raises when set (not mapped yet) (a tap position that overrides the transformer's tap) | not written: untranscribed or raising on import; not in CIM |
| `RemotePTRatio`, `LDC_Z`, `rev_Z`, `Cogen`, `idle`, `idleReverse`, `idleForward` | raises when set (not mapped yet) | not written: untranscribed or raising on import; not in CIM |
| `enabled` | copied to `TapChangerControl.enabled`; `RatioTapChanger.controlEnabled`; default true | written: the control's enabled; the tap's controlEnabled must agree |
| `like` | untranscribed: the reader resolves like= before mapping | not written: the writer never writes like= |
| `maxtapchange`, `inversetime`, `debugtrace`, `EventLog`, `Reset`, `basefreq` | untranscribed (listed in the table comment) | not written |

**Fail fast.** `tapwinding`, `bus` (remote sensing), `vlimit`, `TapNum`, `RemotePTRatio`, `LDC_Z`, `rev_Z`, `Cogen`, `idle`,
`idleReverse` and `idleForward` set; a `transformer` that no `New` defines or that two `RegControl`s name; `winding` outside
the transformer's windings; `PTphase` of `MAX` or `MIN`, or other than 1 on a 1-phase winding; a tap range that is not a
whole number of steps. On export, a control whose `mode` is not voltage, an unset `ptRatio`, a line drop with no `ctRating`
or with `lineDropCompensation` false, a monitored Terminal other than the tap end's, `maxLimitVoltage` or
`minLimitVoltage`, and several monitored phases.

**Expected differences.** The control's `enabled` and the tap changer's `controlEnabled` must agree on export. A 1-phase
winding's `PTphase` comes back 1, whichever of its conductors CIM names. Defaulted `CTprim`, `delay`, `tapdelay`, and the
reverse settings come back explicit. `ctRatio` is not read.

Excerpt from `cimhub_opendss/tests/atoms/regcontrol/regulators.cimtbl` (`reg1`: 700 A CT, `R=3 X=9`, tap 1.0625 on a 0.625 %
step, 10 steps up):

```
Table TapChangerControl: mRID, name, mode=voltage, discrete=true, enabled, monitoredPhase, ptRatio, targetValue, targetDeadband, lineDropCompensation, lineDropR (ohm), lineDropX (ohm), reversible, reverseTargetValue, reverseTargetDeadband, reverseLineDropR (ohm), reverseLineDropX (ohm), reversingPowerThreshold (kW), reversingDelay (s), reverseToNeutral, Terminal
    rc_reg1,  reg1,  true, A, 60.0,  7320.0,  120.0, true,  0.2571428571428571,  0.7714285714285715,  false, 7200.0,  180.0, 0.0, 0.0, 100.0, 60.0, false, xf_reg1_T2

Table RatioTapChanger: mRID, name, TransformerEnd, TapChangerControl, lowStep, highStep, neutralStep=0, step, stepVoltageIncrement (percent), neutralU (kV), ltcFlag=true, controlEnabled, ptRatio, ctRating, ctRatio, initialDelay (s), subsequentDelay (s)
    rc_reg1_tap,  reg1,  xf_reg1_2, rc_reg1,  -16, 16, 10, 0.625, 7.2,   true, 60.0,  700.0, 3500.0, 15.0, 2.0
```

## Run it

This imports regulators and an LTC with their controls, and exports them. It runs from the repository root.

```python
from pathlib import Path

from cimhub_opendss import DssReader, cim_to_dss, dss_to_cim

deck = Path("cimhub_opendss/tests/atoms/regcontrol/regulators.dss")
network = dss_to_cim(DssReader(deck).read_all(), name="regulators", artifact_dir="/tmp/ref-transformers")
cim_to_dss(network, "/tmp/ref-transformers/back.dss", name_source="name")

for line in Path("/tmp/ref-transformers/back.dss").read_text().splitlines():
    if line.lower().startswith(("new transformer.reg1", "new regcontrol.reg1")):
        print(line)
```

```
new Transformer.reg1 phases=1 windings=2 buses=[sub.1.0 rg.1.0] conns=[wye wye] kVs=[7.2 7.2] kVAs=[1666 1666] taps=[1 1.0625] XHL=0.01 MaxTap=1.1 MinTap=0.9 NumTaps=32 %Rs=[0.005 0.005]
new Regcontrol.reg1 transformer=reg1 winding=2 vreg=122 band=2 ptratio=60 CTprim=700 R=3 X=9 delay=15 reversible=No revvreg=120 revband=3 revR=0 revX=0 tapdelay=2 PTphase=1 revThreshold=100 revDelay=60 revNeutral=No enabled=Yes
```

The deck's `%LoadLoss=0.01` is now `%Rs=[0.005 0.005]`, the tap is `taps=[1 1.0625]` with the range written out, and the
control's defaults (`delay`, `revThreshold`, ...) are explicit.
