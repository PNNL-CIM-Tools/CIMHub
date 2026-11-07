---
name: cim-units
description: Unit, per-unit, percent and sign rules for CIMHub converters. Importers write source values with source units in `.cimtbl` column headers; exporters read values with `cimtables.get_qty`. Use when writing or editing any importer mapper, export getter or exporter that touches a physical quantity, a per-unit or percent value, or generator power.
---

# CIM units in CIMHub

Profile is **cim18v17** only. A CIM quantity attribute holds a `CIMUnit` (pint-backed, from `cimprofiles.units`)
stored in SI base units (W, VAr, VA, V, A, ohm, S, m). CIMHub code never does the conversion itself:

- **Import:** cimtables converts. The spoke writes the source number and the source unit.
- **Export:** `cimtables.graph_write.get_qty` converts. The getter names the unit it wants.

The old pattern (`cim.ActivePower(value, 'MW')` in a converter) is gone along with the cim17v40/cimhub_2026
profiles.

## Import rules (invariants I2, I5)

1. **Value verbatim, source unit in the header.** `ratedS (kVA)`, `r (ohm/km)`, `length (ft)`, `p (kW)`.
   `cimhub_core.cimtbl.cell()` writes the value as text and never converts or rounds.
2. **Spoke importer code never constructs a CIM or unit object.** No `cim.X(...)`, no `CIMUnit`, no `Qty`, no
   `z_base`, no `* 1e3`, no `/ 1000`. A mapper produces documents, not quantities.
3. **State each unit once, in the `Field` target.** `Field('copied', targets=(('ACLineSegment', 'length', 'ft'),))`.
   A unit that depends on the record is a template, `'ohm/{length}'`, filled by
   `copied_columns(FIELDS, 'PerLengthSequenceImpedance', length='mi')`.
4. **Relative values use relative headers.** `r (pu)`, `x (percent)`: cimtables multiplies by `z_base = U²/S`
   (siemens: divides), choosing the base from the class shape: the row's own rating (`PowerTransformerEnd`
   `ratedU`/`ratedS`, `TransformerWinding` `baseU`/`baseS`), else a `From*` target's rating
   (`TransformerMeshImpedance.FromWinding`), else the system base (`BaseVoltage` + `BasePower`).
   `(pu system)` / `(percent system)` forces the system base, e.g. PSS/E RAW impedances on SBASE.
   The artifact must hold the ratings, `BaseVoltage` and `From*` references, and system-base rows need a
   `BasePower` bound before them: `Object BasePower: basePower (MVA)=100`. Never compute ohms by hand.
5. **PerCent attributes hold the percent number.** `percentImpedance`, `stepVoltageIncrement`, `pfixedPct`, ...:
   a unitless cell or a `(percent)` column stores 5 % as `PerCent(5.0)`, never the fraction 0.05. Any other
   unit on a PerCent attribute, `pu` included, raises.
6. **No pint path → derived.** When the source quantity has no unit conversion to the CIM attribute (DSS
   `cmatrix` in nF → `b (nS/mi)`, DSS capacitor `kvar` → `bPerSection (S)`, MATPOWER `Gs`/`Bs` in MW at 1 pu,
   a sign flip), the field is *derived*: computed by a named, tested pure function (the DSS LineCode slice's
   `b_from_c`), with the formula in an artifact comment. The result keeps the source's length unit. Copy the
   source quantity too where CIM has a home for it (`nomQ (kVAr)`).

```
# GOOD: verbatim, units in the header
Object PerLengthSequenceImpedance: mRID=lc_seq1, name=seq1, r (ohm/km)=0.3489, x (ohm/km)=0.426198
Table ACLineSegment: mRID, name, node1, node2, phases, length (ft), PerLengthImpedance
    ln_l2, l2, n1, n4, ABC, 500, lc_seq1
```

```python
# BAD: unit math in a mapper
row = [cell(code.r1 * 1.609344), cell(load.kw * 1000)]
```

## Export rules

1. **Read with `get_qty`.** Signature (confirmed in `cimtables/graph_write.py`):

   ```python
   get_qty(source_object, attribute_name, unit, *, base=None, system_base=None) -> float | None
   ```

   It returns `None` when the attribute is unset and raises `ValueError` for a non-field, an association or a
   non-CIMUnit attribute. `'pu'`/`'percent'` on an ohm or siemens attribute inverts the import rule through the
   same `impedance.z_base`, so one rule picks the base both ways. `base='system'` mirrors `(pu system)`;
   pass `system_base=network.base_power` on the system-base path.
2. **Export getters own the reads.** Put them in `cimhub_core/src/cimhub_core/getters/`, one module per CIM concept,
   returning `NamedTuple`s (see the `export-getters` skill). Exporters format what the getters return.
3. **`.to(unit)` only on absolute units**, and only on a value you already hold. Prefer `get_qty`, which also
   handles `None`, pu, percent and PerCent.
4. **PerCent on export:** `get_qty(obj, 'percentImpedance', 'percent')` returns the stored number. Never call
   `.to('percent')` on a PerCent: pint returns 500 for a stored 5.0.
5. **Never compare a CIMUnit to a float.** `bv.nominalVoltage - 4160` raises `TypeError` and `== 4160` is silently `False`. Compare the floats that
   `get_qty` returns.

```python
from cimtables.graph_write import get_qty

kv = get_qty(base_voltage, 'nominalVoltage', 'kV')                  # 4.16
r_pu = get_qty(segment, 'r', 'pu', system_base=network.base_power)  # unrated class -> system base
r_pct = get_qty(end, 'r', 'percent')                                # end's own ratedU/ratedS
z_pct = get_qty(tank_config, 'percentImpedance', 'percent')         # stored percent number
```

## Generator sign convention

CIM uses the load sign convention: positive `p` is power flowing **into** the equipment, so generation and battery
discharge are negative `p`.

- **Import:** MATPOWER `Pg` or RAW `PG` (positive = generation) becomes a negative `p`. The negation is a *derived*
  field, commented in the artifact.
- **Export:** negate: `pg_mw = -get_qty(machine, 'p', 'MW')`.

## Anti-patterns

| Don't | Do |
|---|---|
| `cell(kv * 1000)` with a `(V)` header | `cell(kv)` with a `(kV)` header |
| `r_ohm = r_pu * base_kv**2 / base_mva` in a mapper | `r (pu)` or `r (pu system)` header |
| `percentImpedance (pu)` or a fraction 0.05 | unitless or `(percent)`, value 5.0 |
| `end.ratedU.to('kV')` scattered through an exporter | a getter calling `get_qty(end, 'ratedU', 'kV')` |
| hard-coding a 100 MVA system base | the case's own `BasePower` / `network.base_power` |
| writing the same attribute twice in one row set | one column, one value |
| `TapChanger.step` as a turns ratio | `step` is a tap position |

More detail (CIMUnit classes, header unit strings, per-unit worked examples, B → C conversion) is in
[reference.md](reference.md).
