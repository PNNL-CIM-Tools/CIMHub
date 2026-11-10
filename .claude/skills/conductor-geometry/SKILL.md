---
name: conductor-geometry
description: Rules for line and cable conductor geometry in cim18v17 (WireConfiguration, XYSpacing, WireSequenceConfiguration, WireInfo) and its native forms (DSS LineSpacing/LineGeometry, GLM line_spacing/overhead_line_conductor). Use when writing or editing any line or cable importer mapper, export getter or exporter (cim_to_glm, cim_to_dss, a `.cimtbl` line mapper), or before emitting any impedance matrix (z11, rmatrix, xmatrix, PhaseImpedanceData).
---

# Conductor geometry

**STOP** if you are about to compute or write an impedance matrix for a line that has geometry. This bug keeps
coming back.

## The core rule

**Never substitute a computed impedance matrix for conductor geometry, on import or on export.**

Map native geometry to CIM geometry, and CIM geometry to native geometry. Don't run Carson's equations, and
don't write a `PerLengthPhaseImpedance` in place of geometry.

## The cim18v17 geometry model

CIM 18 removed `WireSpacingInfo` and the rest of the `*Info` catalog. Geometry is a template:

```
ACLineSegment.WireConfiguration ─▶ WireConfiguration
                                     ├─ WireSpacing ─▶ XYSpacing (isTemplate=true)
                                     │                   └─ XYConductorPosition × n  (sequenceNumber, xCoord, yCoord, kind)
                                     └─ WireSequenceConfiguration × n  (sequenceNumber)
                                          └─ WireInfo  (OverheadWireInfo, ConcentricNeutralCableInfo, TapeShieldCableInfo)
```

Phasing comes from the segment: `ACLineSegment.ACLineSegmentPhases`. The `.cimtbl` shape is
`line_by_wire_configuration` (`cimhub_core/src/cimhub_core/shapes/line_by_wire_configuration.cimtbl`, see the
`cimtbl-shapes` skill).

| Native | CIM |
|---|---|
| DSS `LineSpacing`, GLM `line_spacing` | `XYSpacing(isTemplate=true)` + `XYConductorPosition` |
| DSS `LineGeometry`, GLM `line_configuration` (conductor form) | `WireConfiguration` + one `WireSequenceConfiguration` per conductor |
| DSS `WireData` / `CNData` / `TSData`, GLM `overhead_line_conductor` / `underground_line_conductor` | `OverheadWireInfo` / `ConcentricNeutralCableInfo` / `TapeShieldCableInfo` |
| DSS `Line geometry=`, GLM `overhead_line configuration=` | `ACLineSegment.WireConfiguration` |

## Why it keeps happening

`PerLengthPhaseImpedance` / `PerLengthSequenceImpedance` exist for sources that only carry matrices (DSS
`LineCode`, GLM `z11` configurations, MATPOWER/RAW branches). It is tempting to write them out for every line.
That is wrong because:

1. Most distribution feeders (IEEE 13 included) carry geometry, not matrices. A non-zero matrix on such a line came
   from a computation, not from the data.
2. Even when a matrix exists, the target prefers geometry. GridLAB-D's NR solver and OpenDSS compute their own
   impedances from geometry at solve time, with their own frequency and earth-return models. A precomputed matrix
   bypasses that and gives subtly wrong results.

## Export decision tree

```
Does the ACLineSegment have a WireConfiguration?
├── YES → export its XYSpacing as LineSpacing / line_spacing,
│         each WireSequenceConfiguration.WireInfo as the conductor in that position,
│         and link them by name in LineGeometry / line_configuration.
│         STOP. Do not touch impedance.
└── NO  → does it have a PerLengthImpedance (phase or sequence) with values?
          ├── YES → export the matrix form (DSS LineCode, GLM z11..z33)
          └── NO  → log a warning naming the segment and skip the configuration.
                    Never fabricate values.
```

## What the output should look like

```
! DSS: CORRECT, geometry
New WireData.acsr_556_5 rac=0.1859 runits=mi gmrac=0.0313 gmrunits=ft
New LineSpacing.spc_500 nconds=4 nphases=3 units=ft x=[0 2.5 7 4] h=[28 28 28 24]
New LineGeometry.wc_601 nconds=4 nphases=3 spacing=spc_500 wires=[acsr_556_5 acsr_556_5 acsr_556_5 acsr_4/0]
New Line.g1 bus1=n1.1.2.3 bus2=n5.1.2.3 geometry=wc_601 length=2000 units=ft

! DSS: WRONG for a segment that has a WireConfiguration
New Line.g1 bus1=n1.1.2.3 bus2=n5.1.2.3 rmatrix=[0.3465 | 0.1560 0.3375 | ...] length=2000 units=ft
```

```glm
// GLM: CORRECT, geometry
object line_configuration {
  name "lcon_601_ABC";
  spacing "spc_601_ABCN";
  conductor_A "wire_acsr_556";
  conductor_B "wire_acsr_556";
  conductor_C "wire_acsr_556";
  conductor_N "wire_acsr_4/0";
}

// GLM: WRONG for a segment that has a WireConfiguration (the syntax is fine, the data source is not)
object line_configuration {
  z11 0.7917+0.4383j;
  z21 0.3184+0.0276j;
  z22 0.7816+0.3966j;
}
```

## GLM complex syntax

GLM complex values are rectangular `a+bj`: `z11 0.457600+1.07800j;`. This matches the Java exporter
(`DistComponent.CFormat`: `%6g`, explicit sign, `%6g`, `j`) and every golden `.glm` it produced (IEEE13_cdpsm,
IEEE123). That output has years of GridLAB-D round-trip testing behind it, so it is the reference.

- No leading `+` on the real part: `0.457600+1.07800j`, not `+0.457600+1.07800j`.
- The imaginary sign is always explicit, magnitude unsigned: `0.4576-1.0780j`.
- Never a comma pair `real,imag`. GridLAB-D does not use it for these fields, and the GLM reader's complex regex
  will not parse it. Use the GLM writer's `_format_complex`, don't write a new formatter.

## Import rules

- A DSS `LineGeometry` / `LineSpacing` / `WireData`, or a GLM `line_spacing` + conductors, becomes the
  `line_by_wire_configuration` shape. Never a Carson-computed `PerLengthPhaseImpedance`.
- Positions are copied verbatim with their source unit: `xCoord (ft)`, `yCoord (ft)`. Use `XYConductorPosition`,
  not the deprecated `WirePosition`.
- Native `LineCode` / matrix configurations stay matrices (`line_by_impedance`); do not invent geometry for them.

## Checklist

- [ ] No `z11`/`z12`, `rmatrix`/`xmatrix` or `PhaseImpedanceData` is written for a segment that has a
      `WireConfiguration`.
- [ ] No importer writes `PerLengthPhaseImpedance` rows computed from native geometry.
- [ ] No conductor-name field holds a number.
- [ ] GLM complex values use `a+bj`, with no leading `+` on the real part.
- [ ] Phasing comes from `ACLineSegment.ACLineSegmentPhases`, never from a template's back-list
      (`XYSpacing.ACLineSegment[0]`, `WireConfiguration.ACLineSegements[0]`). Templates are shared and those lists
      can be empty, so the code must not hit an `IndexError`. Always traverse from the segment to its template,
      never back.
