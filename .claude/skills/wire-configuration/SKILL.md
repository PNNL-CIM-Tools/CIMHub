---
name: wire-configuration
description: How a cim18v17 ACLineSegment reaches its impedance or geometry through WireConfiguration - the one rule every CIMHub importer writes and every exporter reads (template LineCode vs a line's own impedance vs geometry, isTemplate, the `<lc>_wc` naming, `get_line_code` / `get_line_geometry`). Use when writing or editing any line importer mapper, line exporter, line getter or line shape, or when deciding between ACLineSegment.PerLengthImpedance and ACLineSegment.WireConfiguration.
---

# WireConfiguration: how a line names its impedance

A line's electrical model comes in three forms. `WireConfiguration` is the **equivalence route**: one object that
geometry, a template impedance, or both hang from, so lines that share a catalog share one object.

| form | CIM | who writes it |
|---|---|---|
| **geometry** | `ACLineSegment.WireConfiguration` → `WireConfiguration` that names a `WireSpacing` (`XYSpacing` or `ConductorDistanceSpacing`, `isTemplate=true`) + one `WireSequenceConfiguration` per conductor (skill `conductor-geometry`) | DSS LineGeometry / `spacing=`+`wires=`, GLM conductor `line_configuration`, GDM GeometryBranchEquipment |
| **template code** (a named catalog lines share) | `ACLineSegment.WireConfiguration` → `WireConfiguration` `<lc>_wc` with `PerLengthImpedance` = the code and **no WireSpacing**; the code has `isTemplate=true` | DSS LineCode, GLM z-matrix `line_configuration`, GDM Matrix/SequenceImpedanceBranchEquipment |
| **a line's own impedance** (values only this line has) | `ACLineSegment.PerLengthImpedance` → the code, `isTemplate=false`; no WireConfiguration | DSS Line with inline `r1 x1 ...` or `rmatrix ...` (`ln_<line>_lc`) |

A WireConfiguration with **both** a WireSpacing and a PerLengthImpedance is geometry that also carries its
equivalent impedance. Geometry wins for a geometry-capable format, and bus-branch formats may use the impedance.

Lumped `ACLineSegment.r/x` (bus-branch, RAW/MATPOWER) is outside this rule: no per-length code at all.

## Importer rules

1. **A named catalog is a template.** Write the impedance with `isTemplate=true` and a `WireConfiguration`:
   `mRID` = `<impedance mRID>_wc` (`lc_mtx601_wc`; per unit `lc_<code>_<unit>_wc`), `name` = the catalog's name,
   `PerLengthImpedance` = the impedance, no `WireSpacing`. Declare it after the impedance and before the lines.
   The line names it in its `WireConfiguration` column and leaves `PerLengthImpedance` empty. A named catalog is a
   template even when only one line uses it.
2. **A line's own values are not a template.** Write `isTemplate=false` and reference the code from
   `ACLineSegment.PerLengthImpedance`. Only one line may reference it.
3. **Write the association from the WireConfiguration side** (`WireConfiguration.PerLengthImpedance`). cimtables
   and cimbuilder fill in the inverse `PerLengthImpedance.WireConfiguration`.
4. **Never both on a line.** A line names a WireConfiguration *or* its own PerLengthImpedance, never both
   (`get_line_code` raises when they disagree).
5. **Geometry is unchanged**, and never a computed matrix (skill `conductor-geometry`).

```
# a template LineCode (linecode.cimtbl)
Table PerLengthPhaseImpedance: mRID, name, conductorCount, calculatedFrequency (Hz), isTemplate
    lc_mtx601, mtx601, 3, 60, true
Table WireConfiguration: mRID, name, PerLengthImpedance
    lc_mtx601_wc, mtx601, lc_mtx601

# a line's own values (line.cimtbl)
Table PerLengthSequenceImpedance: mRID, name, r (ohm/km), x (ohm/km), r0 (ohm/km), x0 (ohm/km), isTemplate
    ln_seq1_lc, seq1, 0.3, 0.6, 0.6, 1.8, false

Table ACLineSegment: mRID, name, node1, node2, phases, length (ft), WireConfiguration, BaseVoltage
    ln_l1, l1, sourcebus, n1, ABC, 2000, lc_mtx601_wc, bv_4p16kv
Table ACLineSegment: mRID, name, node1, node2, phases, length (km), PerLengthImpedance, BaseVoltage
    ln_seq1, seq1, n1, n8, ABC, 1.0, ln_seq1_lc, bv_4p16kv
```

The core shape is `cimhub_core/src/cimhub_core/shapes/line_by_impedance.cimtbl`, with both forms.

## Exporter and getter rules

1. **Never read `line.WireConfiguration` or `line.PerLengthImpedance` to decide the form.** Use the core getters in
   `cimhub_core.getters.line_impedance`:
   - `get_line_geometry(line)` returns the WireConfiguration when it names a WireSpacing, else `None`;
   - `get_line_code(line)` returns the line's own PerLengthImpedance, else its WireConfiguration's, else `None`.
     Both set and different raises.
2. **Decision order:** geometry, if the format can take it, then the code, then lumped values. A
   `WireConfiguration` with no `WireSpacing` is never geometry. Don't export it as a LineGeometry or
   `line_spacing`, and don't count it as an earth model.
3. **Template versus own, when the format can tell them apart.** `isTemplate=false` is the line's own
   impedance: DSS writes it inline on the Line (`r1 ...` or `rmatrix ...`, per metre), so an inline deck line
   comes back inline. `isTemplate` true *or unset* is a catalog: a DSS LineCode written once and named by its
   lines. Unset counts as a template because it is the CIM default when no producer marked the code. A format
   that writes a configuration per use (GLM, GDM) treats both the same.
4. **Names come from the code** (`PerLengthImpedance.name`), not the WireConfiguration, so a template exports
   under the catalog's own name.
5. **Phasing comes from the segment** (`ACLineSegment.ACLineSegmentPhases`), never from a template's back-list
   (`WireConfiguration.ACLineSegements` may be empty or shared).

## Where it is implemented

| spoke | importer | exporter |
|---|---|---|
| OpenDSS | `importer/cimtbl/linecode.py` (templates + `<lc>_wc`), `line.py` (inline → own, `isTemplate=false`) | `exporter/line.py` (`get_line_geometry`/`get_line_code`; own inline), `linecode.py` (templates only), `linegeometry.py`, `options.py` |
| GridLAB-D | `importer/cimtbl/configuration.py` (z-matrix → template + `lc_<name>_wc`), `line.py` | `exporter/line.py` `line_key` |
| GDM | `importer/line.py` (`add_template_configuration`) | `exporter/line.py` |

Decision record: DSS-14 (`.development/DSS_REWRITE_PLAN.md`), X26 (`.development/GLM_REWRITE_PLAN.md`).

## Anti-patterns

- `if line.WireConfiguration is not None:` treated as "geometry".
- A shared catalog written as `ACLineSegment.PerLengthImpedance` on every line that uses it.
- A line's own inline values written as a template, or one own impedance shared by two lines.
- A template WireConfiguration given a WireSpacing, a numberOfPhases or an EarthResistivity it does not have.
- An exporter that builds a LineGeometry or `line_spacing` for a WireConfiguration with no WireSpacing.
- Reading `PerLengthImpedance.ACLineSegments[0]` or `WireConfiguration.ACLineSegements[0]` for a line's phases.
