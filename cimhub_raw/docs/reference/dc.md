# DC lines and FACTS devices

This page is the conversion reference for the RAW tables that hold power electronics on the network: FACTS devices,
two-terminal DC lines and VSC DC lines, and for the three record types the importer does not map yet (multi-terminal
DC, GNE devices and induction machines). The first three are imported to CIM and are not exported. The last three raise
when a case has any. The field classes (copied, mapped, structural, derived, untranscribed) and the conventions every
section follows are on the [reference index](index.md).

| RAW table | CIM classes | `.cimtbl` artifact | Importer | Exporter |
|---|---|---|---|---|
| [FACTS device](#facts-device), shunt only | `StaticSynchronousCompensator`, `RegulatingControl` | `facts_device.cimtbl` | `importer/cimtbl/facts_device.py` | raises |
| [VSC DC line](#vsc-dc-line) | `DCLine`, `DCLineSegment`, `DCTopologicalNode`, `VsConverter`, `VsCapabilityCurve`, limits and tie flows | `vsc_dc.cimtbl` | `importer/cimtbl/vsc_dc.py` | raises |
| [Two-terminal DC line](#two-terminal-dc-line) | `DCLine`, `DCLineSegment`, `DCTopologicalNode`, `CsConverter` and its converter transformer | `two_terminal_dc.cimtbl` | `importer/cimtbl/two_terminal_dc.py` | raises |
| [Multi-terminal DC](#record-types-that-raise), [GNE device](#record-types-that-raise), [Induction machine](#record-types-that-raise) | none | none | `importer/cimtbl/multi_terminal_dc.py`, `gne_device.py`, `induction_machine.py` | not applicable |

The two DC tables share the `DCLine`, `DCTopologicalNode`, `DCLineSegment`, `DCTerminal` and `ACDCConverterDCTerminal` rows of
`importer/cimtbl/dc_topology.py`, described next. The converter transformer of a two-terminal line uses the core
`behind_transformer` shape; see the core site's
[shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/). Source paths are under
[`cimhub_raw/src/cimhub_raw/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_raw/src/cimhub_raw).
The master imports the DC artifacts after the transformer artifact and `facts_device.cimtbl` before
`switched_shunt.cimtbl`, so a switched shunt that regulates a FACTS device finds it (see
[Loads and shunts](loads.md)).

Quoted error messages start with the record, as `FACTS device STATCOM-LOC:` or `two-terminal DC line DC-TIE:`. The key
of each table is its NAME, and the mRID prefixes are `fd_` (FACTS device), `vsc_` (VSC DC line) and `dc2_`
(two-terminal DC line).

The examples run from the repository root with `UV_FROZEN=1 uv run python`. They convert the public test atoms in
[`cimhub_raw/tests/atoms/dc`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_raw/tests/atoms/dc) to CIM.

## Not exported

The exporter does not write FACTS devices or DC lines. `RawExporter.to_model` first checks that every piece of
conducting equipment in the network has an exporting module, and it names the ones that do not, with their counts, so
nothing is dropped silently. A network with a FACTS device, a VSC converter or a current-source converter therefore
raises before any record is made:

```python
import cimprofiles.cim18.cim18v17 as cim

from cimhub_raw.exporter.cim_to_raw import RawExporter
from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader

for atom in ("facts_vsc", "two_terminal"):
    case = Raw34Reader(f"cimhub_raw/tests/atoms/dc/{atom}.raw").read_all()
    network = raw_to_cim(case, name="atom")
    for cim_class in (cim.DCLine, cim.StaticSynchronousCompensator, cim.VsConverter, cim.CsConverter):
        print(cim_class.__name__, sorted(obj.mRID for obj in network.graph.get(cim_class, {}).values()))
    try:
        RawExporter().to_model(network)
    except ValueError as error:
        print(error)
```

```text
DCLine ['vsc_VSC-OUT', 'vsc_VSC-TIE']
StaticSynchronousCompensator ['fd_STATCOM-LOC', 'fd_STATCOM-OUT', 'fd_STATCOM-REM']
VsConverter ['vsc_VSC-OUT_c1', 'vsc_VSC-OUT_c2', 'vsc_VSC-TIE_c1', 'vsc_VSC-TIE_c2']
CsConverter []
no RAW export yet for {'StaticSynchronousCompensator': 3, 'VsConverter': 4}
DCLine ['dc2_DC-B2B', 'dc2_DC-BLOCKED', 'dc2_DC-CURRENT', 'dc2_DC-TIE']
StaticSynchronousCompensator []
VsConverter []
CsConverter ['dc2_DC-B2B_i', 'dc2_DC-B2B_r', 'dc2_DC-BLOCKED_i', 'dc2_DC-BLOCKED_r', 'dc2_DC-CURRENT_i', 'dc2_DC-CURRENT_r', 'dc2_DC-TIE_i', 'dc2_DC-TIE_r']
no RAW export yet for {'CsConverter': 8}
```

A `DCLine` and its segment are not conducting equipment of the AC network, so only the converters and FACTS devices
are named. A case with any of them cannot be exported as a whole, and the tables below have "not exported" in the
export column.

## DC topology

Each DC line is bus-branch, as the AC buses are `TopologicalNode`s. For a line `<line>` (`vsc_<NAME>` or `dc2_<NAME>`):

| CIM class | mRID | Attributes |
|---|---|---|
| `DCLine` | `<line>` | the container; name NAME |
| `DCTopologicalNode` | `<line>_n1`, `<line>_n2` | `<line>_n1` is at converter 1 (the rectifier of a two-terminal line); in the `DCLine` |
| `DCLineSegment` | `<line>_seg` | `resistance (ohm)` = RDC; `inService`; in the `DCLine`. An RDC of 0 is still a segment, and no back-to-back topology is inferred from it |
| `DCTerminal` | `<line>_seg_DC1`, `<line>_seg_DC2` | the segment's two terminals on the two nodes |
| `ACDCConverterDCTerminal` | `<converter>_DC1` | one per converter, on its node, `polarity` positive |

RAW gives one equivalent pole, so there is no return path, and no `DCConverterUnit` because RAW says nothing of poles
or operating mode. Each converter sits in the substation of its AC bus.

## FACTS device

A shunt-only FACTS device, J = 0, is a `StaticSynchronousCompensator` `fd_<NAME>` with a voltage control `fdc_<NAME>`:

| CIM attribute | Value |
|---|---|
| `bus` | I, with its `BaseVoltage` and substation |
| `ratedI (kA)` | SHMX / (sqrt(3) x BASKV of bus I); SHMX is MVA at unity voltage; 0 stays 0, a device with no shunt; blank SHMX is 9999 |
| `inService` | MODE == 1 |
| `controlEnabled` | true |
| `RegulatingControl` | `fdc_<NAME>`: `mode` voltage, `discrete` false, `enabled` true, `targetValue` = VSET x BASKV of the regulated bus, in volts; `Terminal` `bb_<FCREG>_T1`, with FCREG 0 meaning bus I, or the busbar of node NREG of bus FCREG |

A device with a series element, J other than 0 (an SSSC, a UPFC or an IPFC), raises: UPFC and IPFC have no CIM 18
class. MODE 2 to 8 need such an element and raise too. A blank MODE is 1.

### FACTS device fields

| RAW field | Import | Export |
|---|---|---|
| NAME | structural: key `fd_<NAME>`, control `fdc_<NAME>`, name NAME | not exported |
| I | structural: `bus`, `BaseVoltage`, `EquipmentContainer` | not exported |
| J | structural: nonzero raises | not exported |
| MODE | mapped: `inService` = (MODE == 1); 2 to 8 raise; blank is 1 | not exported |
| VSET | derived: the control's `targetValue` = VSET x BASKV(FCREG), in V; blank is 1.0 | not exported |
| SHMX | derived: `ratedI (kA)` | not exported |
| FCREG | structural: the control's `Terminal`; blank is 0 | not exported |
| NREG | structural: a node of bus FCREG; blank is 0 | not exported |
| PDES, QDES, TRMX, VTMN, VTMX, VSMX, IMX, LINX, SET1, SET2, VSREF, MNAME | untranscribed: the series element's, which a shunt-only device does not use; listed on the row when not the default | not exported |
| RMPCT | untranscribed: CIM 18 has no participation share for a shunt; listed on the row when not 100 | not exported |
| OWNER | untranscribed | not exported |

### FACTS device fail-fast rules

| Rule | Message |
|---|---|
| J other than 0 | `FACTS device STATCOM-LOC: J 102, a series element (SSSC, UPFC or IPFC; no case has one yet, and UPFC/IPFC have no CIM 18 class)` |
| MODE 2 to 8, or any value other than 0 and 1 | `FACTS device STATCOM-LOC: mode=2 has no mapping (known: 0, 1)` |
| an FCREG that is no bus; the message also names I as FCREG when FCREG is 0 | `FACTS device STATCOM-LOC: FCREG 999 is no bus` |
| export | `no RAW export yet for {'StaticSynchronousCompensator': 3, ...}`, with every other unexported class of the network |

### FACTS device excerpt

No golden has a FACTS device. From the artifact the importer writes for the atom `cimhub_raw/tests/atoms/dc/facts_vsc.raw`
(`STATCOM-REM` regulates bus 301 and has TRMX 0 and RMPCT 75, both listed; `STATCOM-OUT` is MODE 0 with SHMX 0):

```
# one per device; targetValue in V
Table RegulatingControl: mRID, name, mode, discrete, enabled, targetValue, Terminal
    fdc_STATCOM-LOC, STATCOM-LOC, voltage, false, true, 234600.0, bb_202_T1
    fdc_STATCOM-OUT, STATCOM-OUT, voltage, false, true, 230000.0, bb_102_T1
    fdc_STATCOM-REM, STATCOM-REM, voltage, false, true, 232300.0, bb_301_T1

# shunt only (J = 0); ratedI = SHMX / (sqrt(3) x BASKV)
# untranscribed: pdes, qdes, trmx, vtmn, vtmx, vsmx, imx, linx, rmpct, owner, set1, set2, vsref, mname
Table StaticSynchronousCompensator: mRID, name, bus, ratedI (kA), inService, controlEnabled, RegulatingControl, BaseVoltage, EquipmentContainer
    fd_STATCOM-LOC, STATCOM-LOC, 202, 0.25102185616940254, true,  true, fdc_STATCOM-LOC, bv_230kv, sub_202
    fd_STATCOM-OUT, STATCOM-OUT, 102, 0.0,                 false, true, fdc_STATCOM-OUT, bv_230kv, sub_102
    # untranscribed: trmx=0.0, rmpct=75.0
    fd_STATCOM-REM, STATCOM-REM, 302, 0.25102185616940254, true,  true, fdc_STATCOM-REM, bv_115kv, sub_301
```

## VSC DC line

A VSC DC line is the [DC topology](#dc-topology) of `vsc_<NAME>` and a `VsConverter` `vsc_<NAME>_c1` and `_c2` on IBUS 1
and IBUS 2. MDC 0 sets `inService` false on the segment and on both converters. A blank MDC is 1.

Each converter has its own set of these fields. For converter k:

| RAW field | CIM |
|---|---|
| TYPE | 0: `inService` false, DCSET listed on the row; 1: `pPccControl` udc and `targetUdc (kV)` = DCSET; 2: `pPccControl` pPcc and `targetPpcc (MW)` = -DCSET (RAW's positive DCSET feeds the AC network, and CIM uses the load sign) |
| MODE, ACSET | 1: `qPccControl` voltagePcc and `targetUpcc (kV)` = ACSET x BASKV of the regulated bus; 2: `qPccControl` powerFactorPcc and `targetPowerFactorPcc` = ACSET; blank MODE is 1 and blank ACSET 1.0 |
| ALOSS, BLOSS | `idleLoss (kW)` and `switchingLoss (kW/A)`, so the converter's loss is ALOSS + Idc x BLOSS |
| SMAX, IMAX | an `OperationalLimitSet` `<converter>_ratings` on terminal `<converter>_T1`, typed as the first rating (`olt_rate1`), holding an `ApparentPowerLimit` `<converter>_smax` (MVA) and a `CurrentLimit` `<converter>_imax` (A); a value of 0 means unlimited and writes no limit |
| MAXQ, MINQ | MODE 1: a `VsCapabilityCurve` `<converter>_qcurve`, `curveStyle` constantYValue, with one `CurveData` point at x = 0 (MW), y1 = MINQ and y2 = MAXQ (MVAr), so the limits hold at every P; MODE 2 does not use them |
| VSREG, NREG | the converter's `PccTerminal`: MODE 1: `bb_<VSREG>_T1`, or `bb_<IBUS>_T1` when VSREG is 0, or the busbar of node NREG; MODE 2: `bb_<IBUS>_T1` |
| RMPCT | `qShare`, copied; blank is 100 |
| MINLOSS, PWF | no CIM home: listed on the converter's row when not 0 and 1.0 |

For a MODE 2 converter, VSREG, NREG, MAXQ and MINQ are not used and are listed when off their defaults.

**Ties.** A VSC line whose converters are in two areas is a tie. PSS/E makes the DC voltage converter (TYPE 1) the home
end, and the two `TieFlow`s go on the other converter's terminal `<converter>_T1` (see
[Case, buses, areas and zones](buses.md) for the tie flows). A tie without exactly one TYPE 1 converter raises.

### VSC DC line fields

The converter fields are listed once with k for 1 or 2.

| RAW field | Import | Export |
|---|---|---|
| NAME | structural: key for the line and its converters | not exported |
| MDC | mapped: `inService` of the segment and both converters; blank is 1 | not exported |
| RDC | copied: `DCLineSegment.resistance (ohm)` | not exported |
| IBUS k | structural: the converter's `bus`, `BaseVoltage`, `EquipmentContainer`; an IBUS that is no bus raises | not exported |
| TYPE k | mapped: `pPccControl`, as above; other values raise | not exported |
| DCSET k | derived: `targetUdc (kV)` for TYPE 1, `targetPpcc (MW)` = -DCSET for TYPE 2 | not exported |
| MODE k | mapped: `qPccControl`; blank is 1; other values raise | not exported |
| ACSET k | derived: `targetUpcc (kV)` or `targetPowerFactorPcc` | not exported |
| ALOSS k | copied: `VsConverter.idleLoss (kW)`; blank is 0 | not exported |
| BLOSS k | copied: `VsConverter.switchingLoss (kW/A)`; blank is 0 | not exported |
| SMAX k, IMAX k | structural: the limits of `<converter>_ratings`; 0 writes none | not exported |
| MAXQ k | copied: `CurveData.y2value (MVAr)` | not exported |
| MINQ k | copied: `CurveData.y1value (MVAr)` | not exported |
| VSREG k, NREG k | structural: `PccTerminal` | not exported |
| RMPCT k | copied: `VsConverter.qShare` | not exported |
| MINLOSS k, PWF k | untranscribed: listed when not the default | not exported |
| O1 to O4, F1 to F4 | untranscribed | not exported |

### VSC DC line fail-fast rules

| Rule | Message |
|---|---|
| an IBUS or regulated bus that is no bus | `VSC DC line VSC-TIE: converter 1 IBUS 999 is no bus` |
| a TYPE or MODE out of range | `VSC DC line VSC-TIE: converter_type_1=7 has no mapping (known: 0, 1, 2)` |
| a tie without exactly one TYPE 1 converter | `VSC DC line VSC-TIE: a tie needs exactly one TYPE 1 (DC voltage) converter, its home end; TYPE 1 and 1` |
| export | `no RAW export yet for {'VsConverter': 4, ...}`, with every other unexported class of the network |

### VSC DC line excerpt

No golden has a VSC DC line. From the artifact the importer writes for the atom `cimhub_raw/tests/atoms/dc/facts_vsc.raw`.
`VSC-TIE` is a tie between areas 1 and 2: converter 1 is TYPE 2 with limits, converter 2 is TYPE 1 and the home end.
`VSC-OUT` is blocked (MDC 0):

```
# untranscribed: o1, o2, o3, o4, f1, f2, f3, f4, minloss_1, pwf_1, minloss_2, pwf_2
Table DCLine: mRID, name
    vsc_VSC-OUT, VSC-OUT
    vsc_VSC-TIE, VSC-TIE

# resistance = RDC
Table DCLineSegment: mRID, name, resistance (ohm), inService, EquipmentContainer
    vsc_VSC-OUT_seg, VSC-OUT, 16.0, false, vsc_VSC-OUT
    vsc_VSC-TIE_seg, VSC-TIE, 1.58, true,  vsc_VSC-TIE

# targetPpcc = -DCSET (load sign); targetUpcc = ACSET x BASKV(VSREG or IBUS)
Table VsConverter: mRID, name, bus, inService, pPccControl, targetUdc (kV), targetPpcc (MW), qPccControl, targetUpcc (kV), targetPowerFactorPcc, idleLoss (kW), switchingLoss (kW/A), qShare, PccTerminal, BaseVoltage, EquipmentContainer
    # untranscribed: pwf_1=0.5
    vsc_VSC-TIE_c1, VSC-TIE_1, 102, true,  pPcc, ,      -96.0, voltagePcc,     234.6, ,     1600.0, 3.4,   100.0, bb_102_T1, bv_230kv, sub_102
    # untranscribed: minloss_2=1110.0
    vsc_VSC-TIE_c2, VSC-TIE_2, 202, true,  udc,  300.0, ,      powerFactorPcc, ,      0.95, 615.0,  2.527, 100.0, bb_202_T1, bv_230kv, sub_202
    ...

Table CurveData: identifier, Curve, xvalue, y1value, y2value
    vsc_VSC-TIE_c1_qcurve_1, vsc_VSC-TIE_c1_qcurve, 0.0, -100.0, 200.0

Table TieFlow: mRID, name, positiveFlowIn, ControlArea, Terminal
    tf_1_vsc_VSC-TIE_c1_T1, 1_VSC-TIE_T1, false, ca_1, vsc_VSC-TIE_c1_T1
    tf_2_vsc_VSC-TIE_c1_T1, 2_VSC-TIE_T1, true,  ca_2, vsc_VSC-TIE_c1_T1
```

## Two-terminal DC line

A two-terminal line is the [DC topology](#dc-topology) of `dc2_<NAME>` and two `CsConverter`s: the rectifier
`dc2_<NAME>_r` on the DC node `_n1`, and the inverter `dc2_<NAME>_i` on `_n2`. Each converter sits behind a converter
transformer that RAW gives as data (EBAS, TR, TAP and its range, RC and XC per bridge). The transformer joins the AC bus
to an internal valve-side `TopologicalNode` `<converter>_int` and the converter sits on that node.

**Control.** MDC sets what the rectifier holds, and the inverter always holds its DC voltage:

| MDC | Rectifier `pPccControl` | Order |
|---|---|---|
| 0 blocked | none | `inService` false on the segment and both converters (the transformers stay in service); SETVL is listed on the `DCLine` row, since its unit depends on the mode it was blocked from |
| 1 power | activePower | SETVL 0 or above: `targetPpcc (MW)` on the rectifier; SETVL < 0: `targetPpcc` = SETVL on the inverter, as given, because the load sign already makes an inverter's injection negative |
| 2 current | dcCurrent | `targetIdc (A)` = SETVL on the rectifier |

A blank MDC is 0. Any other MDC raises. The inverter's `pPccControl` is dcVoltage with `targetUdc (kV)` = VSCHD; a
nonzero RCOMP is listed.

**Converter.** For converter e (R for the rectifier, I for the inverter):

| CIM attribute | Value |
|---|---|
| `bus` | the internal node `<converter>_int` |
| `operatingMode` | rectifier or inverter |
| `numberOfValves` | 6 x NBe: six valves per bridge |
| `maxAlpha`, `minAlpha (deg)` | the rectifier's ANMXR, ANMNR |
| `maxGamma`, `minGamma (deg)` | the inverter's ANMXI, ANMNI |
| `BaseVoltage` | EBASe x TRe, the valve side; the master adds these voltages to its `BaseVoltage` table |

**Converter transformer.** One equivalent per converter, `<converter>_xf`, always in service. RAW gives RC and XC per
bridge on the valve side and does not say how the NB bridges' transformers are built, so the importer takes their AC
sides as in parallel:

| CIM class | Value |
|---|---|
| `PowerTransformerEnd` 1 `<converter>_xf_1` | on the AC bus IPe; `ratedU (kV)` = EBAS; `r`, `x (ohm)` = RC, XC / (NB x TR^2) |
| `PowerTransformerEnd` 2 `<converter>_xf_2` | on `<converter>_int`; `ratedU (kV)` = EBAS x TR; no `ratedS`, `r` or `x` |
| `RatioTapChanger` `<converter>_xf_tap1` | on end 1, `ltcFlag` and `controlEnabled` true; steps from TMN in steps of STP; `stepVoltageIncrement` = STP in percent; `highStep` = the last whole step at or below TMX; `neutralStep` = the step nearest ratio 1; `step` from TAP |

The tap has no `TapChangerControl`: PSS/E moves TAP to hold the firing angle within its limits, and no CIM mode says
that. A TMX that is not a whole number of STP steps above TMN is listed on the tap row
(`# untranscribed: tmxr=1.12 (the STP grid tops out at 1.1175)`). Blank TR is 1.0, TAP 1.0, TMX 1.5, TMN 0.51 and STP
0.00625.

**Ties.** A line whose rectifier and inverter buses are in two areas is a tie. METER names the metered converter (R or
I, blank is I); the `TieFlow` pair goes on that converter's transformer terminal `<converter>_xf_T1` at the AC bus, and
the other converter is the home end.

**Listed, not mapped.** VCMOD, RCOMP, DELTI, DCVMIN, CCCITMX and CCCACC have no CIM home and are listed on the `DCLine`
row when not the default. ICR and NDR, the bus the firing angle is measured at, are listed on the converter row when
not 0.

### Two-terminal DC line fields

The converter fields are listed once with `e` for R (rectifier) or I (inverter): IPR and IPI, and so on.

| RAW field | Import | Export |
|---|---|---|
| NAME | structural: key for the line, its converters and transformers | not exported |
| MDC | mapped: the rectifier's `pPccControl`, as above; blank is 0 | not exported |
| RDC | copied: `DCLineSegment.resistance (ohm)`; 0 is still a segment | not exported |
| SETVL | derived: `targetPpcc (MW)` or `targetIdc (A)`, as above | not exported |
| VSCHD | copied: the inverter's `CsConverter.targetUdc (kV)` | not exported |
| VCMOD, RCOMP, DELTI, DCVMIN, CCCITMX, CCCACC | untranscribed: listed on the `DCLine` row when not the default | not exported |
| METER | structural: on a tie, the metered converter (R or I); blank is I | not exported |
| IPe | structural: end 1 of the converter transformer, its substation; the converter's AC bus | not exported |
| NBe | derived: `numberOfValves` = 6 x NB; divides the transformer's r and x | not exported |
| ANMXR, ANMNR | copied: `CsConverter.maxAlpha`, `minAlpha (deg)` | not exported |
| ANMXI, ANMNI | copied: `CsConverter.maxGamma`, `minGamma (deg)` | not exported |
| RCe, XCe | derived: end 1 `r`, `x (ohm)` = RC, XC / (NB x TR^2) | not exported |
| EBASe | copied: end 1 `PowerTransformerEnd.ratedU (kV)`; with TR, end 2 and the internal node's voltage | not exported |
| TRe | derived: end 2 `ratedU (kV)` = EBAS x TR; blank is 1.0 | not exported |
| TAPe | derived: the tap's `step` on the STP grid; blank is 1.0 | not exported |
| TMXe, TMNe, STPe | derived: the tap's `highStep`, step 1 and `stepVoltageIncrement`; blank is 1.5, 0.51 and 0.00625 | not exported |
| ICe, NDe | untranscribed: listed on the converter row when not 0 | not exported |
| IFe, ITe | structural: nonzero raises | not exported |
| IDe | untranscribed: used only with IFe and ITe, which raise | not exported |
| XCAPe | structural: nonzero raises | not exported |

### Two-terminal DC line fail-fast rules

| Rule | Message |
|---|---|
| an IPR or IPI that is no bus | `two-terminal DC line DC-TIE: rectifier IPR 999 is no bus` |
| IFe or ITe other than 0, an AC transformer used as the converter transformer | `two-terminal DC line DC-TIE: IFR / ITR name an AC transformer as the rectifier transformer (COD +-4; no case has one yet)` |
| XCAPe other than 0, a capacitor commutated converter | `two-terminal DC line DC-TIE: XCAPR 0.5, capacitor commutated (no case has one yet)` |
| NBe below 1 | `two-terminal DC line DC-TIE: NBR 0 bridges` |
| EBASe or TRe not above 0 | `two-terminal DC line DC-TIE: EBASI x TRI = 0.0 x 0.5 gives no valve-side voltage` |
| STPe not above 0 | `two-terminal DC line DC-TIE: STP 0.0 must be positive` |
| an MDC out of range, or on a tie a METER other than R or I | `two-terminal DC line DC-TIE: mdc=3 has no mapping (known: 0, 1, 2)`, `two-terminal DC line DC-TIE: meter='X' has no mapping (known: I, R)` |
| export | `no RAW export yet for {'CsConverter': 8, ...}`, with every other unexported class of the network |

### Two-terminal DC line excerpt

No golden has a DC line. From the artifact the importer writes for the atom `cimhub_raw/tests/atoms/dc/two_terminal.raw`.
`DC-TIE` is a tie between areas 1 and 2 with SETVL -250 (inverter power) and METER I; its rectifier's TMX is off the
STP grid:

```
# end 1 at the AC bus: ratedU = EBAS, r = RC / (NB x TR^2), x = XC / (NB x TR^2); end 2 at the internal node: ratedU = EBAS x TR
Table PowerTransformerEnd: mRID, name, bus, endNumber, ratedU (kV), r (ohm), x (ohm), BaseVoltage, PowerTransformer
    dc2_DC-TIE_r_xf_1, DC-TIE_r_1, 102,              1, 230.0,              0.05206380797815381, 10.64663770146947, bv_230kv,    dc2_DC-TIE_r_xf
    dc2_DC-TIE_r_xf_2, DC-TIE_r_2, dc2_DC-TIE_r_int, 2, 138.94299999999998, ,                    ,                  bv_138p94kv, dc2_DC-TIE_r_xf
    ...

# TAP on the STP grid from TMN (converter_tap); no TapChangerControl: PSS/E holds the firing angle in range, which no CIM mode says
Table RatioTapChanger: mRID, name, lowStep, highStep, neutralStep, neutralU (kV), stepVoltageIncrement, step, ltcFlag, controlEnabled, TransformerEnd
    # untranscribed: tmxr=1.12 (the STP grid tops out at 1.1175)
    dc2_DC-TIE_r_xf_tap1, DC-TIE_r_1, 1, 20, 11, 231.14999999999998, 1.2499999999999998, 12.52000000000001, true, true, dc2_DC-TIE_r_xf_1
    ...

# on its internal node; numberOfValves = 6 x NB; the rectifier holds MDC's order (targetPpcc on the inverter when SETVL < 0), the inverter VSCHD
Table CsConverter: mRID, name, bus, inService, operatingMode, numberOfValves, maxAlpha (deg), minAlpha (deg), maxGamma (deg), minGamma (deg), pPccControl, targetPpcc (MW), targetIdc (A), targetUdc (kV), BaseVoltage, EquipmentContainer
    dc2_DC-TIE_r,     DC-TIE_r,     dc2_DC-TIE_r_int,     true,  rectifier, 12, 21.0, 17.0, ,     ,     activePower, ,       ,       ,      bv_138p94kv, sub_102
    dc2_DC-TIE_i,     DC-TIE_i,     dc2_DC-TIE_i_int,     true,  inverter,  12, ,     ,     18.0, 18.0, dcVoltage,   -250.0, ,       475.0, bv_115kv,    sub_201
    ...

Table TieFlow: mRID, name, positiveFlowIn, ControlArea, Terminal
    tf_2_dc2_DC-TIE_i_xf_T1, 2_DC-TIE_T2, false, ca_2, dc2_DC-TIE_i_xf_T1
    tf_1_dc2_DC-TIE_i_xf_T1, 1_DC-TIE_T2, true,  ca_1, dc2_DC-TIE_i_xf_T1
```

## Record types that raise

Three RAW record types have no mapping yet. The importer raises for each, so a case that uses one fails at once and
names the table instead of losing its records. The table is empty in most cases, and an empty section is read and
imported without a message.

| RAW table | Where it raises | Message |
|---|---|---|
| Multi-terminal DC | the reader, when the section has a record | `<path>: the MULTI-TERMINAL DC section has <N> record(s); its layout is phase-2 work (...)` |
| GNE device | the reader, when the section has a record | `<path>: the GNE section has <N> record(s); its layout is phase-2 work (...)` |
| Induction machine | the importer, when the model has a record | `RAW InductionMachineRecord: <N> record(s), but the table is phase 2 and not mapped yet (...)` |

The parenthesis in each message points to the project plan. The importer also has a mapper for the first two
(`importer/cimtbl/multi_terminal_dc.py`, `gne_device.py`) that raises in the induction machine's form for a model built in memory. Nothing
of these tables is exported: none of them exists in CIM yet, so the exporter has nothing to read, and there is no
`.cimtbl` artifact for them.

The raises are in the first two lines of this example, which adds one record of each kind to the IEEE 14 bus case:

```python
from pathlib import Path

from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader

IEEE14 = Path("cimhub_raw/tests/cases/IEEE14/IEEE_14_bus.raw")


def case_with(section_end: str, record: str, path: str) -> Path:
    """Copy the IEEE 14 bus case with one record added before the end of a section."""
    lines = IEEE14.read_text().splitlines()
    position = next(index for index, line in enumerate(lines) if line.startswith(section_end))
    lines.insert(position, record)
    Path(path).write_text("\n".join(lines) + "\n")
    return Path(path)


multi_terminal = case_with("0 / END OF MULTI-TERMINAL DC DATA", "'MT1',2,2,1,1,1", "/tmp/ieee14_mtdc.raw")
induction = case_with("0 / END OF INDUCTION MACHINE DATA", "2,'1 ',1,1,1,1,1,1", "/tmp/ieee14_induction.raw")

try:
    Raw34Reader(multi_terminal).read_all()
except NotImplementedError as error:
    print(str(error).partition(" (")[0])

try:
    raw_to_cim(Raw34Reader(induction).read_all(), name="IEEE14")
except NotImplementedError as error:
    print(str(error).partition(" (")[0])
```

```text
/tmp/ieee14_mtdc.raw: the MULTI-TERMINAL DC section has 1 record(s); its layout is phase-2 work
RAW InductionMachineRecord: 1 record(s), but the table is phase 2 and not mapped yet
```

## CIM 18 gaps

What CIM 18 cannot hold of these tables, and what the importer does instead:

| Gap | RAW fields | What the importer does |
|---|---|---|
| a FACTS device's series element; UPFC and IPFC have no class | J other than 0, MODE 2 to 8 | raises; a shunt-only device lists its series fields when not the default |
| a FACTS shunt's share of a coordinated voltage control | FACTS RMPCT | listed on the row when not 100 |
| a VSC converter's minimum loss and power weighting factor | MINLOSS, PWF | listed on the row when not the default |
| a two-terminal line's mode-switch voltage, margin, compounding, minimum DC voltage, constant-current-control settings and commutating bus; the tap's aim of holding the firing angle | VCMOD, DELTI, RCOMP, DCVMIN, CCCITMX, CCCACC, ICR, NDR; TAP's control | listed on the `DCLine` or converter row when not the default; the tap has no `TapChangerControl` |
| ownership | OWNER, O1 to F4 | untranscribed |

## See also

- [Loads and shunts](loads.md): the switched shunts that regulate a FACTS device (MODSW 6).
- [Transformers and impedance correction](transformers.md): the AC transformer records.
- [Import mapping spec](../CIMTBL_MAPPING.md) and [export mapping spec](../EXPORT_MAPPING.md): the design record, with
  the field-by-field classification.
- [What converts](../guide/coverage.md): the task-level view of what the converters handle.
