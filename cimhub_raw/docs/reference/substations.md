# Substations and node-breaker data

Every bus lands in a CIM `Substation`. Most come from the importer, which groups buses that sit in one substation. A
case may also carry SUBSTATION blocks, RAW's node-breaker data: nodes inside a bus, the breakers and disconnectors
between them, and the equipment terminals that say which node each device connects to. How to read the tables is on the
[reference landing page](index.md).

| RAW table | CIM classes | Import | Export |
|---|---|---|---|
| [Synthesized substations](#synthesized-substations) (no RAW table: buses and the equipment between them) | `Substation` | `bus.cimtbl` | no |
| [Substation (SUBSTATION block)](#substation-blocks) | `Substation`, `Location`, `PositionPoint`, `CoordinateSystem` | `bus.cimtbl`, `substation.cimtbl` | no |
| [Substation node](#substation-nodes) | `ConnectivityNode` | `substation.cimtbl` | no |
| [Substation switching device](#substation-switching-devices) | `Switch`, `Breaker`, `Disconnector` | `substation.cimtbl` | no |
| [Regulated nodes](#regulated-nodes) (NREG, NOD1 to NOD3 on other records) | `BusbarSection` | `substation.cimtbl` | no |
| [Equipment terminal](#equipment-terminals) | `Terminal` (an `Update` row) | `equipment_terminal.cimtbl` | no |

The import is a bus-branch model (`TopologicalNode`s and `BusbarSection`s) that also holds `ConnectivityNode`s for the
buses a SUBSTATION block covers. A bus outside every block keeps its bare `TopologicalNode`; a bus inside one also gets
its block's nodes, and a device placed on a node sits on both. The export does not write the node-breaker data yet, see
[Export](#export).

## Synthesized substations

RAW has no substation for a bus-branch case, but CIM needs one to contain the busbars and equipment. The importer
joins buses that the network treats as one site, and it never joins across a zone boundary. The grouping runs
`cimtopology`'s island search over the merge edges, with every bus listed, so a bus on no merge edge is its own
substation.

| merge edge | joins |
|---|---|
| every system switching device | its two buses |
| a branch with R = 0 and \|X\| at or below THRSHZ | its two buses; THRSHZ is in pu on the system base, from the GENERAL record, default 0.0001 |
| a branch whose CKT starts with `@` or `*` | its two buses |
| a series capacitor, a branch with X < 0 | its two buses |
| every transformer | all of its windings' buses |
| the nodes of a SUBSTATION block | every bus the block's nodes name |

A merge edge between two zones is skipped, so that equipment sits on the boundary between two substations.

| substation | mRID | name | Region |
|---|---|---|---|
| a group that holds a SUBSTATION block | `sub_s<IS>` | the block's NAME; blank: IS | `srgn_<zone of its first bus>` |
| any other group | `sub_<lowest bus number>` | that bus's NAME; blank: its number | `srgn_<zone of the lowest bus>` |

A group's row comment lists its buses and the equipment that joined them (`# buses 4, 7, 9; xf_4_7_0_1, xf_4_9_0_1`),
and the table comment counts the substations.

**Fail fast.** A group that holds two SUBSTATION blocks (`buses [...] form one substation holding SUBSTATION blocks [...]
(merged by ...)`). A block whose buses are in two zones, since a `Substation` has one `Region`. A branch with a blank R or
X, which has no schema default, so the zero-impedance test cannot run.

**Counts.** IEEE14 gives 11 substations (two of several buses: 4, 7, 9 and 5, 6). WECC240 gives 134, 79 of them of
several buses, the largest of seven. IEEE118 with its four blocks gives 108, four of them from blocks.

**Export.** The `Substation` is not exported. The exporter reads a bus's ZONE from the `Region` of the substation its
node sits in, and nothing else about it, so the grouping and the substation names do not come back.

Excerpt from `cimhub_raw/tests/goldens/IEEE14/bus.cimtbl`:

```
# synthesized: substations, buses merged across switching devices, zero-impedance branches (R = 0, |X| <= THRSHZ 0.0001),
# series capacitors and transformers, within a zone (11 substations)
Table Substation: mRID, name, Region
    sub_1,  BUS 1,  srgn_1
    sub_2,  BUS 2,  srgn_1
    sub_3,  BUS 3,  srgn_1
    # buses 4, 7, 9; xf_4_7_0_1, xf_4_9_0_1
    sub_4,  BUS 4,  srgn_1
    # buses 5, 6; xf_5_6_0_1
    sub_5,  BUS 5,  srgn_1
    ...
```

## Substation blocks

A SUBSTATION block (RAW's `SubstationRecord`, key IS) is one `Substation` `sub_s<IS>`, written in `bus.cimtbl` because
the buses' nodes name their substation. `substation.cimtbl` adds its location, nodes, switching devices and regulated
busbars.

| field | import | export |
|---|---|---|
| IS (`substation_number`) | structural: the key, the substation `sub_s<IS>`, and the scope of its node numbers | not exported |
| NAME (`name`) | structural: the `Substation` name in `bus.cimtbl`; blank: IS | not exported |
| LATI (`latitude`) | copied to `PositionPoint.yPosition` (deg) of the point `sub_s<IS>_loc_1` of `Location` `sub_s<IS>_loc` | not exported |
| LONG (`longitude`) | copied to `PositionPoint.xPosition` (deg) | not exported |
| SGR (`grounding_resistance`) | untranscribed: a substation's DC grounding resistance for GIC studies has no CIM 18 home | not exported |

The `CoordinateSystem` is one `crs_latlong` named `LatLongCoords`, with `crsUrn` `urn:ogc:def:crs:OGC:1.3:CRS84` (x is
longitude, y latitude), the same form the OpenDSS spoke writes. LATI = LONG = 0, the default, writes no `Location`, and the
document comment lists the blocks left without one.

**Fail fast.** A bus with nodes in two blocks. A group holding two blocks, and a block across two zones, as above.

Excerpt from the artifact the importer writes for `cimhub_raw/tests/atoms/substation/node_breaker_forms.raw` (block 10 at
46.2 N, 119.1 W):

```
Object CoordinateSystem: mRID=crs_latlong, name=LatLongCoords, crsUrn=urn:ogc:def:crs:OGC:1.3:CRS84

Table Location: mRID, CoordinateSystem=crs_latlong
    sub_s10_loc

# copied: xPosition = LONG, yPosition = LATI (deg)
Table PositionPoint: identifier, Location, sequenceNumber, xPosition, yPosition
    sub_s10_loc_1, sub_s10_loc, 1, -119.1, 46.2

Update Table Substation: mRID, Location
    sub_s10, sub_s10_loc
```

## Substation nodes

One `ConnectivityNode` `sub_s<IS>_n<NI>` per node, in its bus's `TopologicalNode` and its block's substation, with its
bus's `BaseVoltage`.

| field | import | export |
|---|---|---|
| IS (`substation_number`) | structural: the enclosing block, filled by the reader; `ConnectivityNodeContainer` is `sub_s<IS>` | not exported |
| NI (`node_number`) | structural: with IS the key; a node number given twice in one block raises | not exported |
| NAME (`name`) | copied to `ConnectivityNode.name`; blank: `<IS>_<NI>` | not exported |
| I (`bus_number`) | structural: the `TopologicalNode` and the `BaseVoltage` of bus I; a node on no bus raises, and so does a bus with nodes in two blocks | not exported |
| STATUS (`status`) | untranscribed: a `ConnectivityNode` has no in-service flag; STATUS 0 is listed on the row as `untranscribed: status=0` | not exported |
| VM (`vm`) | untranscribed: `SvVoltage` attaches only to a `TopologicalNode`, which has the bus's VM; a value other than the default -1.0 is listed on the row | not exported |
| VA (`va`) | untranscribed: as VM; listed when not 0.0 | not exported |

**Fail fast.** The messages name the block and node: `SUBSTATION block 1 node 3: the node number is given twice in the
block`, `...: bus 7 is no bus`, `...: bus 7 also has nodes in block 2`.

Excerpt from the artifact the importer writes for `cimhub_raw/tests/atoms/substation/node_breaker_forms.raw` (node 17 has
no name, VM 1.02 and VA -2.5):

```
# untranscribed: status, vm, va
Table ConnectivityNode: mRID, name, TopologicalNode, BaseVoltage, ConnectivityNodeContainer
    sub_s10_n1,  HV BUS,   1, bv_230kv, sub_s10
    ...
    # untranscribed: vm=1.02, va=-2.5
    sub_s10_n17, 10_17,    2, bv_115kv, sub_s10
```

## Substation switching devices

Each record becomes a `Switch`, `Breaker` or `Disconnector` by TYPE, with `node1` and `node2` on its nodes and `bus1`
and `bus2` on their buses, in the substation `sub_s<IS>`. The mRID is `sw_s<IS>_<NI>_<NJ>_<CKT>`. The code tables are the
[system switching device](branches.md)'s.

| field | import | export |
|---|---|---|
| IS (`substation_number`) | structural: `EquipmentContainer` is `sub_s<IS>` | not exported |
| NI (`from_node`) | structural: `node1` is `sub_s<IS>_n<NI>` and `bus1` that node's bus; `BaseVoltage` is its bus's | not exported |
| NJ (`to_node`) | structural: `node2` and `bus2`; NI = NJ raises; a node not in the block raises | not exported |
| CKT (`circuit`) | structural: with IS, NI and NJ the key; blank is 1, marked defaulted | not exported |
| NAME (`name`) | copied to `name`; blank: the key `<IS>_<NI>_<NJ>_<CKT>` | not exported |
| TYPE (`device_type`) | mapped: 1 `Switch` (a generic connector), 2 `Breaker`, 3 `Disconnector`; any other code raises | not exported |
| STATUS (`status`) | mapped: 1 is closed and 0 is `open`; any other code raises; blank is 1, marked defaulted | not exported |
| NSTAT (`normal_status`) | mapped: 1 is closed and 0 is `normalOpen`; any other code raises; blank is 1, marked defaulted | not exported |
| X (`reactance`) | untranscribed: a `Switch` has no impedance | not exported |
| RATE1 to RATE3 (`rate1`, `rate2`, `rate3`) | structural: an `OperationalLimitSet` `sw_s<key>_ratings` on terminal 1 with a limit per nonzero rating, typed by the [rating sets](buses.md#rating-sets); units follow NXFRAT | not exported |

**Fail fast.** NI = NJ (`substation switching device <key>: NI = NJ = 3`). A node that is not in the block. A TYPE with no
mapping. A device whose two nodes' buses are in different areas, which would be a tie inside a substation: it raises
`NotImplementedError`, since no case has one.

Excerpt from `cimhub_raw/tests/goldens/IEEE118/substation.cimtbl`:

```
# untranscribed: reactance
Table Breaker: mRID, name, node1, node2, bus1, bus2, open, normalOpen, BaseVoltage, EquipmentContainer
    sw_s8_1_3_1,    8_1_3_1,    sub_s8_n1,   sub_s8_n3,    8,   8,   false, false, bv_345kv, sub_s8
    ...
    sw_s100_1_2_1,  100_1_2_1,  sub_s100_n1, sub_s100_n2,  100, 100, true,  true,  bv_138kv, sub_s100

Table Disconnector: mRID, name, node1, node2, bus1, bus2, open, normalOpen, BaseVoltage, EquipmentContainer
    sw_s100_2_3_1,  100_2_3_1,  sub_s100_n2, sub_s100_n3,  100, 100, true, true, bv_138kv, sub_s100
    ...
```

## Regulated nodes

A control on another record can regulate one node of a bus: a generator's, switched shunt's or transformer's NREG or
NODk, and the same fields on VSC DC and FACTS devices. RAW does not say which nodes are busbars, so the importer writes a
`BusbarSection` only on a node some control regulates, and no others. The control's `Terminal` is then
`bb_s<IS>_n<NI>_T1`. The bus's own `bb_<I>` stays on the bus and holds its voltage limits and any bus-level regulation
(see [buses](buses.md#bus)).

| field | import | export |
|---|---|---|
| NREG and NODk, nonzero | structural: the control regulates node NI of the regulated bus, and its `Terminal` is the terminal of `BusbarSection` `bb_s<IS>_n<NI>`, with `node`, `bus`, `BaseVoltage` and the container `sub_s<IS>`, named for the node's NAME | not exported |
| NREG or NODk, zero | the bus's own `bb_<I>_T1` | the control's terminal is on the bus |

**Fail fast.** The regulated bus has no block. The block has no node NI of that bus. NODk is nonzero while CONTk is 0.

Excerpt from the artifact the importer writes for `cimhub_raw/tests/atoms/substation/node_breaker_forms.raw`:

```
Table BusbarSection: mRID, name, node, bus, BaseVoltage, EquipmentContainer
    bb_s10_n1,  HV BUS, sub_s10_n1,  1, bv_230kv, sub_s10
    bb_s10_n11, LV BUS, sub_s10_n11, 2, bv_115kv, sub_s10
```

## Equipment terminals

An equipment terminal record says which node of a bus a device's terminal is on. The importer writes one `Update` row
per terminal, in `equipment_terminal.cimtbl`, which comes last so every equipment document has already written its
`Terminal`s. The record is matched against the equipment those documents wrote, so no mRID rule is repeated here. A
terminal with no record stays on its bus only.

| TYP | equipment (key) | Terminals updated |
|---|---|---|
| L | load (I, ID) | `ld_<I>_<ID>_T1` |
| F | fixed shunt (I, ID) | `cap_<I>_<ID>_T1` |
| M | generator (I, ID) | `sm_<I>_<ID>_T1` (WMOD 0) or `pec_<I>_<ID>_T1` (WMOD 1, 2, 3), or the machine's step-up transformer terminal when it has one |
| B or 2 | a branch or a two-winding transformer (I, J, CKT) | a branch: `ln_` or `sc_<key>_T1` when I is its from bus, `_T2` when its to bus, and that end's line shunt `cap_<key>_i` or `_j`; a transformer: `xf_<key>_T1` or `_T2`, by which winding I is |
| 3 | three-winding transformer (I, J, K, CKT) | `xf_<key>_T<k>`, the winding at I; the buses may be in any order |
| S | switched shunt (I) | every block's `swsh_<I>_b<k>_T1` |
| I, D, V, N, A | induction machine, two-terminal DC, VSC DC, multi-terminal DC, FACTS | raises (`NotImplementedError`) |

The key is matched in either bus order. B and 2 are one form.

| field | import | export |
|---|---|---|
| IS (`substation_number`) | structural: the block whose node NI is meant, filled by the reader | not exported |
| I (`bus_number`) | structural: which terminal of the equipment; node NI's bus must be I | not exported |
| NI (`node_number`) | structural: the terminal's `ConnectivityNode` `sub_s<IS>_n<NI>`; 0 means bus I has no node-breaker model and writes no row | not exported |
| TYP (`terminal_type`) | structural: the equipment form in the table above | not exported |
| J (`j_bus`) | structural: the other end of a B, 2 or 3 key | not exported |
| K (`k_bus`) | structural: the third winding of a 3 key | not exported |
| ID or CKT (`identifier`) | structural: the rest of the key; blank is 1 for L, F, M, I, B, 2 and 3, marked defaulted | not exported |

**Fail fast.** A TYP that is no equipment form. A phase-2 TYP. Equipment no document wrote (`names no load`), a key that
matches two pieces of equipment, and a Terminal placed twice. NI = 0 at a bus that has nodes, and a nonzero NI at a bus
that has none. A node that is in another block than IS. A B key that names only a system switching device, which has no
terminal-record form.

Excerpt from `cimhub_raw/tests/goldens/IEEE118/equipment_terminal.cimtbl`:

```
# each named equipment terminal on its node
Update Table Terminal: mRID, ConnectivityNode
    ln_9_8_1_T2,     sub_s8_n3
    ln_8_30_1_T1,    sub_s8_n4
    xf_8_5_0_1_T1,   sub_s8_n5
    ld_8_1_T1,       sub_s8_n6
    sm_8_1_T1,       sub_s8_n7
    ...
```

## Export

The exporter writes none of the node-breaker data: no SUBSTATION block, node, switching device or equipment terminal
record, and no NREG or NODk (they come back blank). It does not stop or warn: the `Substation`, `ConnectivityNode`s and
the `Switch`, `Breaker` and `Disconnector`s that sit between two nodes are skipped, and the case comes back with its
buses, branches, transformers, loads, shunts and generators, each on its bus. A switch on a node at one terminal only
raises. The design record, [export mapping](../EXPORT_MAPPING.md), lists this as the next export step.

On the IEEE118 case with four node-breaker substations, the import has 4 blocks, 42 nodes, 59 switching devices and 36
equipment terminals; the export has none of them.

**Expected differences once the export is written** (from the design record): SGR comes back as 0.1, a node's STATUS 0
as 1 and its VM and VA as the defaults (-1.0 and 0.0), a switching device's X as 0.0001, a block at 0, 0 as 0, 0, and an
equipment terminal record with NI = 0 is not written. A B or 2 record comes back as 2 for a transformer and B for a
branch. A free bus merged into a block's substation by a transformer stays outside the block's node data.
