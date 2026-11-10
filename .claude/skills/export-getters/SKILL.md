---
name: export-getters
description: The shared lookup layer in both directions - export getters in `cimhub_core/getters/` (one per CIM concept, NamedTuple returns, all unit and base conversion through `cimtables.graph_write.get_qty`, explicit impedance resolution order, cim18v17 only) and the import-side code tables in `cimhub_core/codes.py`. Use when writing a CIM → native exporter, adding or changing a getter, or adding a native-code → CIM-enum table.
---

# Export getters and code tables

```
cim18v17 objects ──core getters (units, bases, resolution)──▶ NamedTuples ──spoke mapper──▶ native dataclass ──writer──▶ file
```

Exporters (`FormatExporter.to_model(network) -> SpokeGraphModel`) never read CIM attributes for values directly.
They call getters, and only shape the result into the native format.

## Rules

1. **One getter per CIM concept, returning all of its fields.** `get_line_sequence_impedance(...)` returns r, x, b, g
   and the zero-sequence values; callers ignore what they don't need. Never `get_line_r_x` + `get_line_r0_x0`.
2. **Return `NamedTuple`s.** They unpack positionally, but `z.x` cannot silently swap with `z.r`, and a new field does
   not break callers.
3. **The caller names the unit:** `get_line_phase_impedance_matrix(line, "ohm/mi")`. Plain floats come out; no CIMUnit
   leaves a getter.
4. **All unit and base conversion goes through `cimtables.graph_write.get_qty`,** the read-side mirror of `set_attr`:
   ```python
   get_qty(source_object, attribute_name, unit, *, base=None, system_base=None) -> float | None
   ```
   `None` means unset. `'pu'`/`'percent'` on an ohm or siemens attribute inverts `set_attr` through the same
   `cimtables.impedance.z_base`; `base='system'` forces the system base like `(pu system)`. Never re-implement it:
   no `* 1e3`, no local `z_base`, no `float(obj.r)` arithmetic. A missing feature goes to
   `.development/UPSTREAM_REQUESTS.md` (I9).
5. **Base selection is `z_base`'s, never the getter's:** a rated class uses its own `baseU`/`baseS` (winding) or
   `ratedU`/`ratedS` (end); a `From*` reference uses the From end (mesh impedance); an unrated class (`ACLineSegment`,
   `EnergySource`) uses its `BaseVoltage` and the system base power (`network.base_power`). A missing rating raises.
6. **cim18v17 only.** No `*Info` electrical catalog. Read these paths (reference.md §2):
   - lines: `ACLineSegment.WireConfiguration` → `WireSpacing` (an `XYSpacing` + `XYConductorPosition`) +
     `WireSequence` (`WireSequenceConfiguration`) → `WireInfo`; or `ACLineSegment.PerLengthImpedance`;
   - catalog transformers: `TransformerTank.TankConfiguration` → `TransformerTankConfiguration` (tank ends,
     windings, core, mesh); balanced transformers: `PowerTransformerEnd` + `TransformerMeshImpedance`;
   - phases: always from the equipment (`ACLineSegment.ACLineSegmentPhases`, `Terminal.phases`), never from a
     template's back-list (`WireConfiguration.ACLineSegements[0]` can be empty).
7. **No profile-module argument.** There is one profile; read classes from the object or `network.cim`.
8. **Format-specific shapes stay in the spoke:** GLM `"BCN"`, DSS `.1.2.3` bus suffixes, RAW bus numbers, naming
   policy. Core returns CIM meaning: phases as `SinglePhaseKind` tokens in conductor order, nodes as objects, and both
   `uri()` and `name` so the spoke chooses (GLM names default to `uri()`).
9. **Getters are pure.** They read and return; they never add objects to the graph or write back into CIM.
10. **Fail fast.** A required value that is missing raises, naming the class and mRID. No silent defaults
    (`0.0`, `1.0`, a 10 m height, 60 Hz).

## Impedance resolution order

Bus-branch formats (RAW, MATPOWER) can only take sequence values, so a getter may have to reduce what CIM holds:

| step | source | assumption introduced |
|---|---|---|
| 1 | `ACLineSegment` lumped `r/x/bch/gch` (`r0/x0/b0ch/g0ch`) | none |
| 2 | `PerLengthSequenceImpedance` × `length` | none beyond the length |
| 3 | `PerLengthPhaseImpedance` (`PhaseImpedanceData`), Kron-reduced if it has a neutral, then to sequence | transposed line |
| 4 | geometry (`WireConfiguration` → spacing + `WireInfo`) → line constants → step 3 | earth model, resistivity, frequency, temperature |

This is a **caller-limited resolution order**, not hidden fallbacks:

- `derive=` caps how far it may go. The default `ImpedanceSource.LUMPED` reads stored values only and raises when
  absent. A bus-branch exporter opts in to `GEOMETRY`.
- Every result carries `source`, so logs, tests and goldens show which values are derived.
- Two sources present and disagreeing beyond a tolerance raise; the precedence is written down and tested.
- **Geometry-capable formats (GLM, DSS) never use the chain.** They export native geometry (`line_spacing` +
  `overhead_line_conductor`; `LineSpacing` + `LineGeometry`) via the spacing and wire getters, and fall back to the
  phase matrix only when CIM has no geometry (skill `conductor-geometry`).
- Heights matter for shunt `b` and Deri earth return: take them from `get_line_conductor_xy` (the spacing's y plus
  `ACLineSegment.spacingYOffset`, or a distance to earth); raise otherwise.

## Semantic rules the getters settle (one documented rule each)

1. **Switch state:** `get_switch_state(switch, which='actual'|'normal')`; `which` has no default (`open` vs `normalOpen`).
2. **Generator sign:** CIM terminal `p` is positive into equipment; generation is negative `p`.
   `get_der_output(eq, sign='load'|'generation')` takes the sign as an argument, so no spoke negates on its own.
   Nameplate limits (`maxQ`/`minQ`, `maxP`/`minP`) are stored in the generation sign; the rating getters return
   them as `(min, max)` in the same `sign=`.
3. **Per-phase load:** `EnergyConsumerPhase` values when every child has them, else the total split evenly over the
   phase conductors (`phase_power.device_power`, also DER).
4. **Shunt Q:** one formula, Q = bPerSection × V² × sections, with `voltage=` (`nomU` or the BaseVoltage, LN for one
   phase conductor) and `sections=` both required (`get_shunt_reactive_power`).
5. **Transformer per-unit base:** `get_transformer_model(unit, impedance_unit, base_power=...)` puts every percent
   on one declared power base (default winding 1's `ratedS`, DSS/GLM's); no format picks or rebases its own.
6. **Raw floats:** an attribute that is not a CIMUnit fails fast (`get_qty` raises); never guess kV vs V.
7. **Frequency:** from the network (`network.base_frequency`, set by cimgraph's `set_default_bases`), never a
   hard-coded 60 Hz in a getter or spoke.
8. **Unset is `None`, and the spoke decides** (user, 2026-11-08). A getter returns `None` for an optional value CIM
   leaves unset (a line's `b`, `g`, zero sequence), never 0.0, so "not modelled" and "zero" stay distinguishable.
   Each spoke writes its own rule, with a comment saying why:
   - RAW and MATPOWER write `b = 0.0` when `None` (RAW's spec default for `B`; MATPOWER's `BR_B` column cannot be
     blank). Neither has a series line conductance: a set `g` raises until a real case needs a `GI`/`GJ` split.
   - DSS writes `C1=0`/`C0=0` when `b` is `None`. A blank lets the engine default in (C1=3.4, C0=1.6 nF per unit
     length, or the balanced 2.8/-0.6 C matrix on a matrix code), which silently adds line charging.

## Import-side code tables (`cimhub_core/codes.py`)

- Plain dicts, one per CIM enum (`PhaseCode`, `WindingConnection`, `SinglePhaseKind`, `PhaseShuntConnectionKind`,
  load-model kinds), keyed by native spelling, valued by the cim18v17 enum text.
- Used only through `cimhub_core.cimtbl.lookup(table, value, slot=..., record_id=...)`, which raises on an unmapped
  value. Never `.get(value, default)`.
- Values are checked against the cimprofiles enum when `codes.py` is imported, so a typo fails at once.
- **A table enters core only when two spokes use it.** Until then it lives in the spoke's mapper module.
- Format-only spellings stay in the spoke: DSS `.1.2.3` bus suffixes, GLM `BCN`, a format's own unit words.

## Anti-patterns

- An exporter doing `line.r.to('ohm') / z_base` or `value * 1000`; a getter with its own `to_float`.
- `get_line_sequence_impedance` called by a GLM/DSS converter on a line that has a `WireConfiguration`.
- Reading `WireSpacingInfo`, `WirePosition`, or `TransformerTankInfo` in a getter.
- A getter that returns a dict or a bare tuple, or a different one per format.
- `if x else 1.0` style defaults; `Point(0, 0)` fallbacks; writing a computed value back onto a CIM object.
- A code table copied into a second spoke instead of moved to `codes.py`.

Signatures, the getter backlog, cim18v17 attribute paths and test models: [reference.md](reference.md).
