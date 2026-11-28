# What converts

Which PSS/E RAW v34 tables import and export today. The source of truth is the code: the importer's mappers are listed
in `MAPPING_ORDER` in `importer/raw_to_cimtbl.py`, the master document it writes first is built in the same file, the
equipment-terminal step runs after the mappers, and the exporter's modules are in `EXPORT_ORDER` in
`exporter/cim_to_raw.py`. The tables that only fail fast are in `importer/cimtbl/phase2.py`. The table below follows
those lists. Field-level detail is in the [import mapping](../CIMTBL_MAPPING.md) and the
[export mapping](../EXPORT_MAPPING.md), where every field is classified. Each table links to the
[conversion reference](../reference/index.md) page that describes it.

## Tables that convert

The importer writes one `.cimtbl` document per RAW table, named for the table (`bus.cimtbl`), and a master that
imports them in this order: catalogs and containers before the equipment that uses them. A table with no records
writes no document and no `Import`. The exporter reads the whole network once and each module writes its RAW records.

| RAW table | CIM classes (cim18v17) | Import | Export | Reference |
|---|---|---|---|---|
| Case identification, system-wide data, RATING | `BasePower`, `BaseFrequency`, `GeographicalRegion`, `BaseVoltage`, `OperationalLimitType` | the master | `case_identification` | [buses](../reference/buses.md) |
| Zone | `SubGeographicalRegion` | `zone.cimtbl` | `zone` | [buses](../reference/buses.md) |
| Area interchange | `ControlArea`; the inter-area transfers are listed on its comment | `area_interchange.cimtbl` | `area_interchange` | [buses](../reference/buses.md) |
| Bus | `Substation`, `TopologicalNode`, `BusbarSection`, `OperationalLimitSet`, `VoltageLimit`, `SvVoltage` | `bus.cimtbl` | `bus` | [buses](../reference/buses.md) |
| Substation, node, switching device | `ConnectivityNode`, `Switch`, `Breaker`, `Disconnector`, `Location`, a `BusbarSection` per regulated node | `substation.cimtbl` | not exported | [substations](../reference/substations.md) |
| Non-transformer branch | `ACLineSegment`, `SeriesCompensator`, `LinearShuntCompensator` for line shunts, `OperationalLimitSet`, `TieFlow` | `branch.cimtbl` | `branch` | [branches](../reference/branches.md) |
| System switching device | `Switch`, `Breaker`, `Disconnector` | `switch.cimtbl` | `switch` | [branches](../reference/branches.md) |
| Multi-section line grouping | `Line` | `multi_section_line.cimtbl` | `multi_section_line` | [branches](../reference/branches.md) |
| Load | `ConformLoad`, `NonConformLoad`, `LoadResponseCharacteristic`, `LoadArea`, `SubLoadArea`, load groups | `load.cimtbl` | `load` | [loads](../reference/loads.md) |
| Fixed shunt | `LinearShuntCompensator` | `fixed_shunt.cimtbl` | `fixed_shunt` | [loads](../reference/loads.md) |
| Generator | `SynchronousMachine`, `GeneratingUnit`, `PowerElectronicsConnection`, `PowerElectronicsUnit`, `RegulatingControl`, a step-up `PowerTransformer` | `generator.cimtbl` | `generator` | [generators](../reference/generators.md) |
| Impedance correction | `ImpedanceTapChangerTable`, `ImpedanceTapChangerTablePoint` | `impedance_correction.cimtbl` | `impedance_correction` | [transformers](../reference/transformers.md) |
| Transformer | `PowerTransformer`, `PowerTransformerEnd`, `TransformerMeshImpedance`, `RatioTapChanger`, `PhaseTapChangerLinear`, `TapChangerControl`, `ImpedanceTapChangerTabular` | `transformer.cimtbl` | `transformer` | [transformers](../reference/transformers.md) |
| Two-terminal DC | `DCLine`, `DCLineSegment`, `DCTopologicalNode`, `CsConverter`, a converter `PowerTransformer` | `two_terminal_dc.cimtbl` | not exported | [dc](../reference/dc.md) |
| VSC DC | `DCLine`, `DCLineSegment`, `DCTopologicalNode`, `VsConverter`, `VsCapabilityCurve` | `vsc_dc.cimtbl` | not exported | [dc](../reference/dc.md) |
| Multi-terminal DC | none | raises | not exported | [dc](../reference/dc.md) |
| FACTS device | `StaticSynchronousCompensator`, `RegulatingControl` | `facts_device.cimtbl` | not exported | [dc](../reference/dc.md) |
| Switched shunt | `LinearShuntCompensator` per block, `RegulatingControl` | `switched_shunt.cimtbl` | `switched_shunt` | [loads](../reference/loads.md) |
| GNE device | none | raises | not exported | [dc](../reference/dc.md) |
| Induction machine | none | raises | not exported | [dc](../reference/dc.md) |
| Equipment terminal | `Terminal` (an `Update` row) | `equipment_terminal.cimtbl`, last | not exported | [substations](../reference/substations.md) |

The switched shunt follows the FACTS device because a switched shunt that controls a plant's or a FACTS device's
reactive power names that device's terminal. The exporter's modules, in `EXPORT_ORDER`: `case_identification`, `zone`,
`area_interchange`, `bus`, `branch`, `switch`, `multi_section_line`, `load`, `fixed_shunt`, `switched_shunt`,
`generator`, `transformer`, `impedance_correction`.

Notes:

- A RAW table that no mapper reads is counted in the master's `not mapped:` comment, so a record class never disappears
  silently.
- A case that reaches the exporter with conducting equipment of a class no module writes raises
  (`no RAW export yet for {...}`). Today that is every DC converter and FACTS device. The substation data is not
  covered by that check; see the next note.
- The exporter writes no node-breaker data. A case with SUBSTATION blocks exports its buses and equipment, each on its
  bus, and the blocks, nodes, switching devices and equipment terminals are not in the output.
- Quantities are written in the unit RAW uses and the unit is in the `.cimtbl` column header. Per-unit values on the
  system base are written as `(pu system)` and converted by cimtables on the case's `BasePower`.

## Untranscribed as a whole

These are read, counted or listed in a comment, and have no CIM home in the profile.

| what | where it goes |
|---|---|
| Owner records and every owner field (bus OWNER, O1 to O4 and F1 to F4 on other records) | counted in the master comment; no document; the export writes none |
| Solution options: GAUSS, NEWTON, ADJUST, TYSL, SOLVER | named in the master comment; the GENERAL record is read only for THRSHZ, the substation grouping threshold |
| Case title lines | the first goes on the master comment |
| Inter-area transfers | listed on the `ControlArea` comment of `area_interchange.cimtbl`; lost on export |
| An area's slack bus (ISW) | untranscribed |

## Records that raise

| record | raises |
|---|---|
| Case identification with IC other than 0 | a change case is not a model |
| Multi-terminal DC, GNE device, induction machine | `NotImplementedError`, naming the table and its record count; a case without them converts |
| FACTS device with a series element (J other than 0) | raises: only a shunt-only device is mapped |
| Equipment terminal of TYP I, D, V, N or A | `NotImplementedError`; any other unknown TYP is a `ValueError` |
| A bus with BASKV blank or not positive | raises |
| A network with DC converters or FACTS devices, on export | `no RAW export yet for {...}` |

Unmapped codes (a switching-device TYPE, a transformer CZ or CM, a generator WMOD) and unresolved references (an AREA
with no area-interchange record, a node on no bus) raise as well, naming the record and the value.

## CIM 18 gaps

What the profile cannot hold, and what the importer does instead:

- a bus's zone membership: a substation never spans two zones;
- a bus's own control area and an area's slack bus: the export traces AREA from generating units and tie flows, and
  lists a bus it cannot reach;
- the area or zone of machines and DC equipment, and a load's zone when it differs from its bus's: loads sit in a
  `LoadArea` and `SubLoadArea` per area and zone, the rest is untranscribed;
- ownership of network equipment: untranscribed;
- the metered end of a branch, switch or multi-section line, and a transformer's NMETR: recorded by the `TieFlow`s of a
  tie, untranscribed elsewhere;
- a scheduled transfer between two control areas: listed on the `ControlArea` comment;
- a shunt switched with its line in a bus-branch model: a `LinearShuntCompensator` per end, linked by its mRID;
- a node's in-service status, a substation's DC grounding resistance, and a solved voltage per node of a split bus:
  listed on the row or untranscribed;
- a shunt's or converter's share of a coordinated voltage control (RMPCT): untranscribed, or listed when not 100;
- a converter's reactive limits that follow its active power (WPF on WMOD 2): written as given, WPF listed;
- the kind of a renewable bus-branch generator (PV, wind, induction machine): a `PowerElectronicsConnection` with no
  kind;
- a machine's positive-sequence reactance (ZX): untranscribed;
- which side of a voltage-controlling winding its controlled bus is on (the sign of CONTk): the magnitude regulates and
  the sign is listed;
- a FACTS device's series element, and UPFC and IPFC, which have no CIM 18 class: raises;
- a VSC converter's minimum loss and power weighting factor, and a two-terminal DC line's mode-switch, margin,
  compounding and commutation settings: listed on the row when not the default.

Not gaps: a bus's voltage limits and its regulation sit on its `BusbarSection`'s terminal, because CIM puts limits and
regulating controls on terminals. RAW does not say which nodes of a substation are busbars, so the importer adds a
`BusbarSection` only on a node a control regulates.
