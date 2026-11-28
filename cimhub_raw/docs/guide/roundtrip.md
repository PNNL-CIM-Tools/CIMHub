# Round trip

A round trip imports a `.raw` to CIM and exports it to a new `.raw`. This page shows what the round trip keeps and
changes, runs one on the IEEE 14-bus case, and lists the tests that check it.

There is no power-flow engine in the loop: nothing here solves a case. The check is a comparison of records. Every
record the exporter writes is compared with the record the reader read, by key and field by field, and the
differences must be exactly the list below.

## Run it yourself

```python
import math
import tempfile
from pathlib import Path

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.exporter.cim_to_raw import cim_to_raw
from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader

original = Path("cimhub_raw/tests/cases/IEEE14/IEEE_14_bus.raw")
work = Path(tempfile.mkdtemp())

model = Raw34Reader(original).read_all()
cim_to_raw(raw_to_cim(model, name="IEEE14"), work / "exported.raw")
exported = Raw34Reader(work / "exported.raw").read_all()


def key(record):
    return getattr(record, "ID", None) or record.bus_number   # a bus has no ID, only its number


def compare(record_class, slots):
    """Print how many records of one table differ in any of ``slots``, at the tolerance the tests use."""
    before = {key(record): record for record in model.list_by_class(record_class)}
    after = {key(record): record for record in exported.list_by_class(record_class)}
    assert before.keys() == after.keys()          # the same records, by key
    differ = []
    for record_key, record in before.items():
        for slot in slots:
            old, new = getattr(record, slot), getattr(after[record_key], slot)
            same = math.isclose(old, new, rel_tol=1e-9) if isinstance(old, float) and isinstance(new, float) else old == new
            if not same:
                differ.append((record_key, slot, old, new))
    print(f"{record_class.__name__:18} {len(before):3} records, {len(differ)} differ {differ[:1]}")


compare(schema.BusRecord, ("name", "base_voltage", "bus_type", "area", "zone", "voltage_magnitude", "voltage_angle"))
compare(schema.LoadRecord, ("constant_real_power", "constant_imag_power", "status"))
compare(schema.BranchRecord, ("r", "x", "b", "ratings"))
compare(schema.GeneratorRecord, ("p_output", "q_output", "status", "rated_mva"))
compare(schema.TransformerRecord, ("r1_2", "x1_2", "windv1", "nomv1"))
print(exported.first(schema.CaseIdentificationRecord).titles)
```

```text
BusRecord           14 records, 0 differ []
LoadRecord          11 records, 0 differ []
BranchRecord        17 records, 0 differ []
GeneratorRecord      5 records, 0 differ []
TransformerRecord    3 records, 3 differ [('4_7_0_1', 'nomv1', 0.0, 138.0)]
['', '']
```

Every bus, load, branch and generator comes back with the values it had. The three transformers differ in one field:
NOMV1 was blank (zero) and comes back as 138 kV, the bus's base voltage, which is what a blank meant. The case's two
title lines come back blank.

The tolerance is a relative 1e-9, not equality. A value goes from per unit to kV and back through CIM, so the last digit
of a float can move: a second pass over the exported file writes `1.0900000000000005` where the first wrote
`1.0900000000000003`.

## What the round trip keeps and changes

The exporter writes what CIM holds. Every other value is left blank and read by RAW as its default. Most of a case
comes back as it was. These differences are known and expected:

| Original | Exported | Why |
|---|---|---|
| the two title lines | two blank lines | a case's titles have no CIM home |
| GENERAL, GAUSS, NEWTON, ADJUST, TYSL and SOLVER records | not written | solution options have no home in the network profile. A THRSHZ other than 0.0001 is lost, and the substations of a re-import may differ |
| owner records and the OWNER fields | not written | CIM 18 cannot hold ownership |
| no `RATING` records (WECC240) | the twelve default `RATING` records | the importer writes all twelve rating sets whether the case names them or not |
| a zone a bus names that has no Zone record | a Zone record | the importer synthesizes the zone |
| an area or zone NAME equal to its own number | blank | a blank NAME is stored as the number |
| ISW (an area's slack bus) | blank | CIM has no association for it |
| AREA of a bus that no generator or tie reaches | blank | CIM has no node to area association, so the exporter traces AREA from generators and ties |
| IDE 4 (an isolated bus) | 1 | CIM has no isolated bus type |
| MET or METERED 2 on a device inside one area | 1 | the metered end has a home only on a tie, where its `TieFlow`s record it |
| NMETR off a tie | blank | the same rule, for a transformer |
| a series capacitor's LEN | 0 | CIM's `SeriesCompensator` has no length |
| a switching device's X | 0.0001 | the format gives X no default and CIM has no X for a switch |
| NXFRAT 1 with nothing rated | 0 | the flag says nothing without a rating |
| a blank MBASE | SBASE | the same meaning |
| a load's blank AREA or ZONE | the load group's AREA, the bus's ZONE | the importer gives every load both |
| a load's ZONE off its bus's | the bus's ZONE | a load's zone has no home in CIM |
| SWREG 0 (a shunt regulating its own bus) and IREG 0 | the bus's number | the control's terminal is the bus's busbar |
| ADJM, and RMPCT other than 100 on a switched shunt | 0 and 100 | no CIM home |
| WMOD 2 | 1, with its WPF | the renewable class has no power-factor limits mode |
| WMOD 3's IREG and VS | not written | a power-factor plant's control holds neither |
| GTAP with no step-up transformer | blank | the generator has no transformer to hold it |
| a WMOD 1 generator's WPF other than 1 | blank | RAW uses WPF only for WMOD 2 and 3 |
| a connection's ZR | blank | a converter has no ZR in CIM |
| transformer CW, CZ or CM 2 or 3 | 1, with the values converted to CW 1, CZ 1 and CM 1 units | the importer stores a transformer in CIM's own terms, in one form |
| NOMV 0 | the bus's base voltage | what a zero meant |
| a 3-winding transformer's SBASE1-2, 2-3 and 3-1 | SBASE | the importer stores one rating base |
| a phase shifter's RMA and RMI with 0 degrees off its grid | moved by the offset | CIM steps start at the neutral angle |
| a ratio range that no tap holds (COD 0) | the defaults | CIM holds the steps, not a range |
| a voltage control's extended range | its extended steps | the range the steps hold |
| a negative CONT | positive | the sign is listed on the control's row, not kept in CIM |

Differences go the other way, too. Everything the importer lists as `untranscribed:` in a comment is gone from the CIM
model. Node-breaker data is the larger one: a SUBSTATION block imports to CIM (nodes, breakers, disconnectors,
equipment terminals) but is not exported, so a case with SUBSTATION blocks comes back as a bus-branch case.
Likewise DC lines and FACTS devices import but are not yet exported, so a case with them does not export. See
[Export](export.md).

## What checks it

The tests are in
[`cimhub_raw/tests`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_raw/tests). Run them with
`scripts/test-all.sh raw`.

| Test | What it checks |
|---|---|
| `test_round_trip` (`test_cim_to_raw.py`) | For every committed case and every atom, RAW to `.cimtbl` to CIM to RAW records. Each exported table is compared with the RAW as read, by key and slot by slot. A slot the exporter leaves unset is skipped, and a blank on both sides is filled with the schema's default first. The slots that differ must be exactly the expected differences, case by case. A new difference fails the test, and so does a missing one |
| `test_written_case_reads_back` | For WECC 240 and ten atoms, the exported records are written with `Raw34Writer` and read back with `Raw34Reader`, and every record is unchanged |
| `test_slots_are_complete` | Every field of every exported record class is classified: written from CIM, a rule, or unset |
| `test_untranscribed_on_import_is_unset_on_export` | A field the importer lists as untranscribed cannot be written on export, unless the exporter recovers it |
| `test_to_model_raises_on_equipment_not_yet_exported` | `to_model` raises on CIM classes it has no module for, and exports IEEE 14 whole |
| the `test_e*` tests | One for each rule the exporter raises on (a line conductance, a moving step-up tap, ratings in both MVA and current, ...) |
| goldens (`test_raw_to_cimtbl.py`) | The `.cimtbl` text the importer writes for IEEE 14 (and IEEE 118's substation and equipment terminal files) equals the reviewed file in `tests/goldens/`, so a change to the text shows in the diff |
| reader tests (`test_raw34_reader.py`) | The reader and the writer read, write and read again IEEE 14, IEEE 118, WECC 240 and a set of atoms with the same records, and the reader's errors |

The cases and atoms are listed in `tests/cases/README.md` and in the README of each folder under `tests/atoms/`. Each
atom is a small hand-built case that isolates one group of features, such as ties between areas, transformer forms
or node-breaker substations. The atoms have no `.cimtbl` golden next to them, but every one goes through
`test_round_trip`.
