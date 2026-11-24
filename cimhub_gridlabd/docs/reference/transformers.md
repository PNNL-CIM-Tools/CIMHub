# Transformers and regulators

`transformer_configuration` and `transformer`, and `regulator_configuration` and `regulator`: how each becomes CIM
templates, power transformers, voltage regulators and tap changers, and how they come back. How to read the tables is on
the [reference landing page](index.md).

| GLM | CIM (cim18v17) | Import (shape) | Export |
|---|---|---|---|
| `transformer_configuration` | `TransformerTankConfiguration` with its ends or lugs, and its windings; a bank under a `TransformerBankConfiguration` | `transformer_configuration.cimtbl` (`transformer_template`, `transformer_template_1ph`) | `transformer_configuration`, one per way a unit uses a template |
| `transformer` | `PowerTransformer`, `TransformerTank` per tank, `PowerTransformerEnd` per side, `TransformerPhaseEnd` for lugged templates | `transformer.cimtbl` (`transformer_by_template`) | `transformer`, from a `PowerTransformer` or an `AutoTransformer` that is not a regulator |
| `regulator`, with its `regulator_configuration` | `VoltageRegulator`, two `AutoTransformerEnd`s, `TransformerMeshImpedance`, `TapChangerControl`, `RatioTapChanger` | `regulator.cimtbl` (`voltage_regulator`) | `regulator` and `regulator_configuration` |

The shapes are on the core site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/), and the
getters the exporter reads through (`get_transformer_units`, `get_transformer_model`, `get_tap_changer_control`,
`get_tap_steps`) are on its [transformers reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/transformers/).

**The impedance rule.** GridLAB-D stores a transformer's impedance as one R + jX in per unit and a parallel shunt, on its
own base: `secondary_voltage`² / `power_rating`, line to line, as written. The importer puts that on the tank's nameplate
fields (`percentImpedance`, `loadLoss`, `noLoadLoss`, `percentMagnetizingCurrent`), moved to the tank's own base by
`k = 3 S_coil / S_total`, so GridLAB-D's ohms are kept. There is no winding `r` and no mesh impedance. A wye whose
voltages rate the coil, phase to neutral, rather than the line, has `k = S_coil / S_total`. The deck says which: the
written `primary_voltage` is either the `nominal_voltage` of its `from` bus (a coil rating) or that times the square root
of three (a line rating); anything else raises.

## transformer_configuration

A configuration is written as a template, used or not, in one of three forms. Every transformer that uses one
configuration must wire it the same way (the same phases and bus systems), or the importer raises, because there is one
template per configuration.

| Form | When | CIM |
|---|---|---|
| three-phase tank | a `WYE_WYE` on three phases rated equally or only by `power_rating`; `DELTA_GWYE`; `DELTA_DELTA` | a `TransformerTankConfiguration` `xc_<name>` with a `TransformerTankEnd` per winding (`connectionKind`) and a `TransformerWinding` per end |
| lugged cans | a wye on one phase (one can), on two (a bank), or on three phases rated unequally (a bank) | one `TransformerTankConfiguration` per can with `TransformerLug`s `H1 H2 X1 X2` and windings H1 to H2, X1 to X2; a bank's cans are `xc_<name>_<phase>` under a `TransformerBankConfiguration` `xb_<name>` (an unrated template's cans are `_1`, `_2`) |
| center tap | `SINGLE_PHASE_CENTER_TAPPED`, or a 240 V one-phase service | lugs `H1 H2 X1 X3 X2` (numbered 1 to 5) and windings H1 to H2, X1 to X2 (`s1` to `N`), X2 to X3 (`N` to `s2`); the %Z is the full winding's, which GridLAB-D splits into its star |

Connections: `WYE_WYE` and `SINGLE_PHASE` (one case in GridLAB-D) are Y to Y, `DELTA_GWYE` D to Y, `DELTA_DELTA` D to D.
The grounding is the instance's, not the template's.

Windings carry `ratedU` and `baseU` in the unit the deck writes the voltage in, and `ratedS` and `baseS` in the unit of
`power_rating`. On a line-rated wye `ratedU` is the written voltage and `baseU` is that over the square root of three; a
delta's are equal. On a coil-rated wye `baseU` is the written voltage and `ratedU` is that on the bus's system. A center
tap's halves have `baseU` = `secondary_voltage` and `ratedU` twice that, at half the kVA each (a 240 V service's halves
are each half of its `secondary_voltage`).

| property | import | export |
|---|---|---|
| `name` | copied to `TransformerTankConfiguration.name`; mRID `xc_` + name (a bank `xb_` + name, its cans `xc_` + name + `_<phase>`) | written: the `TankConfiguration`'s name when every instance wires it alike, else `<unit>_config` |
| `connect_type` | structural: the form and the connection kinds; unset or any other value raises | written: `WYE_WYE`, `SINGLE_PHASE`, `DELTA_DELTA`, `DELTA_GWYE`, `SINGLE_PHASE_CENTER_TAPPED`, by the table below |
| `primary_voltage` | structural: winding 1 `ratedU` and `baseU`; unset or 0 raises | written: winding 1's `ratedU` (V), a coil's `baseU`; an LTC at its actual step is folded in |
| `secondary_voltage` | structural: winding 2 `ratedU` and `baseU`; a center tap's half has `baseU` = this and `ratedU` twice it | written: winding 2's, likewise; a center tap's half; a star leg's 1000 V |
| `power_rating` | structural: `ratedS` of the whole unit (kVA), else the sum of the phase ratings; unset or 0 raises | written: winding 1's `ratedS` (kVA); a star leg's own winding's |
| `powerA_rating`, `powerB_rating`, `powerC_rating` | structural: a can's kVA when the wired phases are rated unequally; a center tap's kVA on its phase (unset or 0 there raises); otherwise unused, and listed when not `power_rating` over the phase count. They must sum to `power_rating` within 1 %, else raises | written: a coil's or a center tap's kVA on its phase; a bank's each can's |
| `resistance`, `reactance`, `impedance` | derived: `percentImpedance` = \|R + jX\| x k x 100, `loadLoss` = R x k x S (kW); both parts positive, else raises; `impedance` and its parts that differ raise | written: the (1, 2) R + jX in per unit (the windings' `r` plus the mesh); a center tap's or a star leg's branch; a part that is not positive is written as 1e-6 and logged |
| `resistance1`, `reactance1`, `impedance1`, and the same for `2` | derived: a center tap's star given whole must be GridLAB-D's split of one R + jX (`impedance` = 0.5 R + j0.8 X, each half R + j0.4 X); any other split, one half only, or another connection raises | written: a center tap's `impedance1` and `impedance2`, the halves of the star |
| `shunt_resistance`, `shunt_reactance`, `shunt_impedance` | derived: `noLoadLoss` = S / (Rsh x k), `percentMagnetizingCurrent` = 100 / (Xsh x k); unset is GridLAB-D's lossless core, not filled; on a delta connection raises | written: `shunt_resistance` = 1 / the core's g, `shunt_reactance` = 1 / its b, per unit; unset parts are not written |
| `no_load_loss`, `full_load_loss`, `reactance_resistance_ratio` | raises when set: they replace the impedances, and no deck sets them | not written |
| `install_type`, `coolant_type`, `cooling_type`, the thermal slots (`oil_volume`, `core_coil_weight`, ...), the inrush slots (`L_A`, `phi_K`, ...), object header | untranscribed: listed in the row comment | not written: GridLAB-D's default |

How a unit is chosen for export (`get_transformer_model`, per unit on winding 1's `ratedS`):

| Model | Written as |
|---|---|
| two windings, Y, Yn or I on both, on one phase set | `WYE_WYE`, or `SINGLE_PHASE` for one coil |
| two windings, D to D on three phases | `DELTA_DELTA` |
| two windings, D to Yn on three phases, `phaseShift` unset or -30 degrees | `DELTA_GWYE` |
| three windings on `s1`, `s2`, `N` | `SINGLE_PHASE_CENTER_TAPPED`, the star written whole |
| any other two windings | `WYE_WYE` on both windings' phases; the phase shift, zero-sequence path and grounding are lost, and each is logged |
| three windings, not a center tap | three legs to a 1 kV star bus `<unit>_star`; a D leg `DELTA_GWYE`, otherwise `WYE_WYE`; the star branch of winding i is (Zij + Zik - Zjk) / 2 |
| single-phase cans with a phase-to-phase coil on the same buses | one bank, then the rows above |
| one `PowerTransformer`'s lugged cans under a `TransformerBankConfiguration` | one `WYE_WYE`, `powerX_rating` each can's, named by the bank configuration |

GridLAB-D's base is `secondary_voltage`² / `power_rating`: a polyphase unit is written line to line on its whole kVA, a
coil on its own voltage and kVA, and a polyphase wye on two phases has a coil base of n/3 of GridLAB-D's. A bank's cans
all get GridLAB-D's one impedance, so each can's own per unit times S_total / (3 S_can) must agree, else the export raises.

**Fail fast.** `connect_type` unset or unmapped; voltages or kVA unset or 0; phase ratings that miss `power_rating` by more
than 1 %; `resistance` or `reactance` unset or not positive; `impedance1` and `impedance2` on a connection that ignores
them, or a split other than GridLAB-D's; a shunt on a connection that ignores it; `no_load_loss` and the like set; a
center tap on a phase it does not rate; two instances that wire one configuration differently. On export, four or more
windings; a tap changer on a bank can; a bank's cans that give different impedances; a `ratedU` unset.

**Expected differences.** A configuration is written once per distinct use, so a template no transformer uses is not
written. A tap changer is folded into its winding's voltage at the actual step, and its control is not written. A
winding's grounding impedance is lost, since GridLAB-D grounds a wye solidly. Non-native two-winding models and open
delta banks are written as `WYE_WYE`, with the differences above. The per-unit impedance comes back on GridLAB-D's base
(`0.011+0.02j` returns as `0.011+0.02j`, up to rounding); a part that was not positive returns as 1e-6.

Excerpt from `cimhub_gridlabd/tests/atoms/transformer/transformer.transformer_configuration.cimtbl`, a bank of three cans
rated 37.5, 25 and 25 kVA (`xc_bank3`) and the three-phase `xcon_xfm1`:

```
Table TransformerBankConfiguration: mRID, name
    xb_xc_bank3, xc_bank3

Table TransformerTankConfiguration: mRID, name, percentImpedance (percent), loadLoss (kW), noLoadLoss (kW), percentMagnetizingCurrent (percent)
    xc_xcon_xfm1, xcon_xfm1, 2.2825424421026654, 5.5, ,

Table TransformerTankConfiguration: mRID, name, percentImpedance (percent), loadLoss (kW), noLoadLoss (kW), percentMagnetizingCurrent (percent), BankConfiguration
    xc_xc_bank3_A, xc_bank3_A, 0.7486313634675927,  0.054964285714285716, 0.062058718186041396, 0.1826112363302446,  xb_xc_bank3
    xc_xc_bank3_B, xc_bank3_B, 0.49908757564506173, 0.024428571428571424, 0.062058718186041396, 0.27391685449536685, xb_xc_bank3

Table TransformerWinding: mRID, TankConfiguration, ratedU (V), baseU (V), ratedS (kVA), baseS (kVA), FromTransformerLug, ToTransformerLug
    xc_xc_bank3_A_wdg_1, xc_xc_bank3_A, 4160.0, 2401.7771198288433, 37.5, 37.5, xc_xc_bank3_A_lug_h1, xc_xc_bank3_A_lug_h2
```

(rows abridged)

## transformer

A transformer is a `PowerTransformer` `xf_<name>` with a `TransformerTank` for each tank of its template (one, named
`xf_<name>_tank` with no name of its own; a bank has a tank per can, `xf_<name>_tank_<phase>` named `<name>_<phase>`), and
a `PowerTransformerEnd` per side, on the root bus of `from` and `to`. The values live in the template; the ends carry the
node, phases, connection kind and grounding. A lugged template (a center tap, a one- or two-phase wye, a bank) also gets a
`TransformerPhaseEnd` per conductor of each terminal, numbered as the template's lugs, so a center tap's secondary is `s1`,
`s2`, `N`.

| `connect_type` | End 1: phases, kind, grounded | End 2: phases, kind, grounded |
|---|---|---|
| `WYE_WYE`, `SINGLE_PHASE` | the transformer's phases, `N`; `Yn`, true (without `N`, or with `S`, raises) | the same |
| `DELTA_GWYE` | `ABC`; `D`, false | `ABCN`; `Yn`, true |
| `DELTA_DELTA` | `ABC`; `D`, false | `ABC`; `D`, false |
| `SINGLE_PHASE_CENTER_TAPPED` | the phase letter and `N`; `Y`, true | `s1s2N`; `I`, true |

A coil-rated one-phase wye whose `secondary_voltage` is 120 V is a split-phase leg: its end 2 is `s1N`, kind `I`, and the
bus is a 240 V split-phase system. At 240 V it is a center tap (end 2 `s1s2N`), with the unit's R + jX taken as the full
winding's. Another one-phase secondary (a 277 V coil) is one phase of a wye on a three-phase system. Only loads may sit on
a service bus: a link, a capacitor or an inverter there raises.

| property | import | export |
|---|---|---|
| `name` | copied to `PowerTransformer.name`; mRID `xf_` + name | written: the transformer's; a tank of several `<transformer>_<n>`; a star leg `<unit>_<winding>` |
| `phases` | structural: the ends' phases and kinds above, and the phase ends; unknown letters raise; a delta must be `ABC` | written: winding 1's A, B, C, then `N`; a center tap's letter, then `S` |
| `from`, `to` | structural: `node` of end 1 and end 2, the root buses; each end's system must be as the connection needs (a polyphase transformer's three phase, a center tap's secondary split phase) | written: winding 1's bus; winding 2's, or a star leg's star bus |
| `configuration` | structural: `TransformerTank.TankConfiguration` = `xc_` + configuration (a bank: one tank per can); unset raises | written: its `transformer_configuration` |
| `continuous_rating_A` to `_C`, `emergency_rating_A` to `_C` | structural: the transformer's own `<mRID>_limits`; per-phase ratings that differ raise | written: `get_current_limits` on the unit's phases |
| `status` | structural: unset or `CLOSED`; `OPEN` raises (a transformer is not a switch) | not written |
| thermal and flux slots (`climate`, `ambient_temperature`, `percent_loss_of_life`, `phase_A_primary_flux_value`, ...), object header, solver outputs | untranscribed | not written |

**Fail fast.** A transformer without a configuration, or one that names another class. A center tap on phases other than
one letter and `S`. A wye without `N` or with `S`. A delta not on `ABC`. A `status` other than `CLOSED`. An end on the
wrong system. A written voltage that is neither the coil's nor the line's. A one-phase service whose secondary bus has a
link, capacitor or inverter on it.

**Expected differences.** A `DELTA_DELTA` transformer written `ABCN` comes back `ABC`, and a `DELTA_GWYE` written `ABC`
comes back `ABCN`. Several lugged cans of one transformer come back as one `WYE_WYE`. A transformer keeps its name; its
configuration may be renamed. Tap changers and per-phase ratings follow the template rules above.

Excerpt from `cimhub_gridlabd/tests/atoms/transformer/transformer.transformer.cimtbl` (a center tap `xf_ct` and a delta-wye
`xf_dg`):

```
Table PowerTransformerEnd: mRID, PowerTransformer, node, phases, endNumber, connectionKind, grounded, BaseVoltage
    xf_xf_ct_1, xf_xf_ct, n5,  AN,    1, Y,  true,  bv_4p16kv
    xf_xf_ct_2, xf_xf_ct, tn1, s1s2N, 2, I,  true,  bv_240v
    xf_xf_dg_1, xf_xf_dg, n2,  ABC,   1, D,  false, bv_4p16kv
    xf_xf_dg_2, xf_xf_dg, m_dg, ABCN, 2, Yn, true,  bv_480v

Table TransformerPhaseEnd: mRID, endNumber, sequenceNumber, phase, Terminal
    xf_xf_ct_2_s1, 2, 3, s1, xf_xf_ct_T2
    xf_xf_ct_2_s2, 2, 4, s2, xf_xf_ct_T2
    xf_xf_ct_2_N,  2, 5, N,  xf_xf_ct_T2
```

(rows abridged)

The steps from a deck to this and back:

```python
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim
from cimhub_gridlabd.exporter.cim_to_glm import GlmExporter

model = GlmReader("cimhub_gridlabd/tests/atoms/transformer/transformer.glm").read_all()
network = glm_to_cim(model, name="xfmr")  # a model name that no GLM class shares
exported = GlmExporter().to_model(network, name_source="name")
by_class = {cls.class_name: cls for cls in exported.graph}
for record in exported.graph[by_class["transformer_configuration"]].values():
    print(record.name, record.connect_type, record.power_rating)
```

## regulator_configuration and regulator

A GridLAB-D regulator is a 1:1 step-voltage regulator with no nameplate impedance and no kVA, so each unit is a
`VoltageRegulator` (an `AutoTransformer`) with two `AutoTransformerEnd`s. There is no step-down LTC in GLM, so there is no
`PowerTransformerEnd` and no tank. CIM has no regulator template, so a configuration's values go on every unit that names
it, and a configuration no regulator names is listed in the file comment and not written.

| `control_level` | Units |
|---|---|
| `INDIVIDUAL` (default) | one single-phase unit per wired phase, `xf_<name>_<phase>`, each with its own `RatioTapChanger` and `TapChangerControl` |
| `BANK` | one gang unit `xf_<name>` on `ABC`, whose taps must agree; or, when the regulator is wired on its one `PT_phase`, one unit on that phase |

| CIM row | Written from |
|---|---|
| `VoltageRegulator` | `construction` from `Type`: `A` is `typeA`, `B` is `typeB` (default B) |
| `AutoTransformerEnd` (two) | `node` the root buses of `from` and `to`; `phase` `<letters>N`; `grounded` true; `baseU` (V) the `from` bus's `nominal_voltage`, the coil phase to neutral (x the square root of three on a gang unit); `ratedS` (VA) the continuous rating x `baseU` (x the square root of three on a gang unit) |
| `TransformerMeshImpedance` | `r` (ohm) `regulator_resistance`, default 1e-4 ohm (GridLAB-D's `default_resistance`); `x` a 0.01 percent stand-in on `ratedS` |
| `TapChangerControl` `rc_<unit>` | `enabled` unless `Control` is `MANUAL`; `monitoredPhase`; `ptRatio`; `targetValue` and `targetDeadband` from the band; `lineDropCompensation` on `LINE_DROP_COMP`; `lineDropR`, `lineDropX` (ohm) |
| `RatioTapChanger` `rc_<unit>_tap` | `lowStep`, `highStep`, `neutralStep` 0, `step`, `stepVoltageIncrement` (percent), `neutralU` (V) = `baseU`, `ltcFlag` true, `controlEnabled`, `ptRatio`, `ctRatio`, `ctRating` (A), `initialDelay`, `subsequentDelay` (s) |

### regulator_configuration

| property | import | export |
|---|---|---|
| `connect_type` | structural: `WYE_WYE`; any other raises (the Newton-Raphson solver takes only that) | written: `WYE_WYE`, since CIM's `AutoTransformerEnd`s are grounded wye coils |
| `Control` | structural: `MANUAL` (default) is `enabled` and `controlEnabled` false; `OUTPUT_VOLTAGE` and `LINE_DROP_COMP` true, with `lineDropCompensation` on `LINE_DROP_COMP` only; `REMOTE_NODE` on the regulator's own `to` bus is read as `OUTPUT_VOLTAGE`, elsewhere raises | written: `MANUAL` when the `TapChangerControl` is disabled or absent, `LINE_DROP_COMP` with line drop compensation, else `OUTPUT_VOLTAGE` |
| `Type` | mapped: `A` to `typeA`, `B` to `typeB`; default B | written: `B` on `construction` typeB, else `A` |
| `band_center`, `band_width` | derived: `targetValue`, `targetDeadband` (V), primary volts on `OUTPUT_VOLTAGE` and `MANUAL`, times `power_transducer_ratio` on `LINE_DROP_COMP`, whose band is on the PT secondary; `band_width` is the full band | written: the target and the deadband (V); over `ptRatio` on `LINE_DROP_COMP`; unset on a disabled control |
| `raise_taps` | copied to `RatioTapChanger.highStep`; also the divisor of the step; unset or not positive raises | written: `highStep` - `neutralStep`; a fixed tap raises |
| `lower_taps` | derived: `lowStep` = -`lower_taps`; unset or not positive raises | written: `neutralStep` - `lowStep` |
| `regulation` | derived: `stepVoltageIncrement` = `regulation` / `raise_taps`, as percent (`regulation` is a fraction: 0.10 over 16 taps is 0.625); 0 or unset raises unless `MANUAL` | written: `stepVoltageIncrement` x `raise_taps` as a per-unit fraction |
| `tap_pos_A`, `tap_pos_B`, `tap_pos_C` | derived: `step` of the phase's unit, unless the regulator sets its own `tap_X`; default 0; outside -`lower_taps` to +`raise_taps` raises | written: `step` - `neutralStep` on each phase |
| `current_transducer_ratio` | copied to `RatioTapChanger.ctRatio` and `ctRating` (A: GridLAB-D's compensator takes amperes on a 1 A secondary, so the ratio is the CT primary rating) | written: `ctRatio` |
| `power_transducer_ratio` | copied to `TapChangerControl.ptRatio` and `RatioTapChanger.ptRatio` | written: `ptRatio` |
| `compensator_r_setting_A` to `_C`, `compensator_x_setting_A` to `_C` | derived: `lineDropR`, `lineDropX` (ohm) = the monitored phase's setting x `power_transducer_ratio` / `current_transducer_ratio` (`line_drop_ohms`); set without both ratios raises | written wherever CIM holds a line drop: lineDrop x `ctRatio` / `ptRatio` on each phase |
| `dwell_time`, `time_delay` | derived: `initialDelay` = `subsequentDelay` = `dwell_time` + `time_delay` (s); default 0 | written: `dwell_time` = `initialDelay` |
| `control_level` | structural: see above | written: `BANK` for one `VoltageRegulator` alone, else unset (`INDIVIDUAL`) |
| `PT_phase`, `CT_phase` | structural: on `BANK`, `TapChangerControl.monitoredPhase`, one phase, the same for both; on `INDIVIDUAL` GridLAB-D ignores them and the row lists them | written on `BANK`: the control's monitored phase, else its first phase; an enabled control without one raises |
| `reverse_flow_control` | structural: unset or `LOCK_NONE`; any other raises | not written |
| object header | untranscribed | not written |

### regulator

| property | import | export |
|---|---|---|
| `name` | derived: `VoltageRegulator.name` = name (`BANK`) or `<name>_<phase>` (`INDIVIDUAL`); mRID `xf_` + that | written: Names; units that are `<base>_<phase>` on the same two buses are the one regulator `<base>` again |
| `phases` | structural: the wired phases A, B, C (`N` optional); `S` raises | written: the A, B, C of end 1 |
| `from`, `to` | structural: `node` of end 1 and end 2, the root buses | written: end 1's and end 2's bus |
| `configuration` | structural: a `regulator_configuration`, else raises; its values go on every unit | written: `<regulator>_config` |
| `tap_A`, `tap_B`, `tap_C` | derived: `step` of the phase's unit, over `tap_pos_X` | not written: `tap_pos_X` of the configuration |
| `regulator_resistance` | copied to `TransformerMeshImpedance.r` (ohm); unset is 1e-4 ohm, listed as `defaulted` | written: the mesh `r` (ohm); none: unset |
| `continuous_rating_A` to `_C` | structural: `ratedS` = the rating x `baseU`; the unit's phase (a gang unit's any); unset raises, since GridLAB-D's default is not the regulator's | written: `get_current_limits` on its phases |
| `emergency_rating_A` to `_C` | structural: the emergency `CurrentLimit` of the unit's `<mRID>_limits` | written: `get_current_limits` |
| `sense_node` | structural: `REMOTE_NODE` only, and it must solve as the regulator's own `to` bus; on another `Control` GridLAB-D ignores it and the row lists it | not written |
| `status` | structural: unset or `CLOSED`; `OPEN` raises | not written |
| `msg_mode`, `remote_voltage_A` to `_C`, `tap_A_change_count` to `_C`, object header, solver outputs | untranscribed | not written |

**Fail fast.** A `connect_type` other than `WYE_WYE`. `raise_taps` or `lower_taps` unset or not positive. `regulation` unset
or 0 on an automatic `Control`. `REMOTE_NODE` sensing a bus other than the regulator's output. A `reverse_flow_control`
other than `LOCK_NONE`. A `BANK` on neither `ABC` nor its one `PT_phase`, whose `PT_phase` and `CT_phase` are not one equal
phase, or whose taps differ. A tap outside the range. Compensator settings without both transducer ratios. Phases with `S`
or none of A, B, C. A unit with no `continuous_rating_X`. On export, a `VoltageRegulator` without exactly two ends or one
`RatioTapChanger`; a fixed tap; a line drop without both ratios; an enabled `BANK` control with no monitored phase; shared
settings of one GLM regulator's units that disagree.

**Expected differences.** A regulator's reactance and kVA are not in GridLAB-D, so only the mesh `r` is written back. A delta
regulator bank (coils between phases) is written as one `WYE_WYE` regulator, each coil's tap and compensator on its own
phase, and logged, since GridLAB-D 6.0 solves no delta regulator under the Newton-Raphson solver. A regulator that came from
CIM comes back with `<regulator>_config` as its configuration. A bus's `nominal_voltage` is its `BaseVoltage`'s, so a
regulator end's `baseU` and `ratedS` follow it.

Excerpt from `cimhub_gridlabd/tests/atoms/regulator/regulator.regulator.cimtbl`, the line-drop-compensating `reg_ldc` on
phase A:

```
Table VoltageRegulator: mRID, name, construction, EquipmentContainer=fdr_reg
    # configuration rc_ldc
    # defaulted: time_delay=0.0, dwell_time=0.0, control_level=INDIVIDUAL, Type=B
    xf_reg_ldc_A, reg_ldc_A, typeB

Table TapChangerControl: mRID, name, mode=voltage, discrete=true, enabled, monitoredPhase, ptRatio, targetValue, targetDeadband, lineDropCompensation, lineDropR (ohm), lineDropX (ohm), Terminal
    rc_reg_ldc_A, reg_ldc_A, true, A, 20.0, 2440.0, 40.0, true, 0.08571428571428572, 0.2571428571428571, xf_reg_ldc_A_T2
```

(rows abridged) The band 122 V and 2 V are on the PT secondary, so with `power_transducer_ratio` 20 they become
`targetValue` 2440 V and `targetDeadband` 40 V, and the settings 3 and 9 become `lineDropR` 3 x 20 / 700 and `lineDropX`
9 x 20 / 700 ohm.
