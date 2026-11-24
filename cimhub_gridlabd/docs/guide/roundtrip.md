# Round trip

A round trip imports a `.glm` to CIM and exports it to a new `.glm`. The check that matters is that GridLAB-D
solves both decks to the same bus voltages. This page shows what the round trip keeps and changes, runs one on the
IEEE 13-node deck, and lists the tests that check it.

## Run it yourself

```python
import tempfile
from pathlib import Path

from cimhub_gridlabd.exporter.cim_to_glm import GlmExporter
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.glm_writer import GlmWriter
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim

original = Path("cimhub_gridlabd/tests/decks/IEEE/IEEE13_cdpsm.glm")
work = Path(tempfile.mkdtemp())

model = GlmReader(original, defines={"VSOURCE": "66395.28"}).read_all()
network = glm_to_cim(model, name="IEEE13_cdpsm")
GlmWriter().write(GlmExporter().to_model(network, name_source="name"), work / "exported.glm")

# a second pass gives the same text
again = glm_to_cim(GlmReader(work / "exported.glm").read_all(), name="IEEE13_cdpsm")
GlmWriter().write(GlmExporter().to_model(again, name_source="name"), work / "second.glm")
print((work / "second.glm").read_text() == (work / "exported.glm").read_text())   # True
```

Two warnings are logged. The import warns that the loads read a player the deck does not define, so their group has
no schedule. The export warns that it writes those loads static. [Players and schedules](time-series.md) says why and how to keep the player.

`name_source="name"` keeps the deck's own names, so the two decks compare object by object. The default is `'mrid'`
(or `$CIMHUB_NAME_SOURCE`), which writes the mRIDs the importer made (`ld_ld_house` for the load `ld_house`). The
IEEE decks use `${VSOURCE}` without defining it, so the reader takes it from `defines`, as `gridlabd -D
VSOURCE=66395.28` would. The exported deck is a single power flow: the `clock` starts and stops at one instant.

## What the round trip keeps and changes

The exporter writes what CIM holds. Most of a deck comes back as it was. These differences are known and expected:

| Original | Exported | Why |
|---|---|---|
| a child bus (a meter, or a node with a `parent`) | not written; its root bus carries its loads and equipment | a child bus is its root's node in CIM. The IEEE 13 meters `634_pvmtr` and `house_stmtr` are not written. |
| the source's impedance | not written | GridLAB-D's swing bus is ideal |
| a regulator's reactance and kVA | not written; only its resistance is | a GridLAB-D regulator has neither |
| a regulator's LTC control, a capacitor's non-voltage control | not written | GridLAB-D has no form for them |
| a winding's grounding impedance | a solidly grounded wye | GridLAB-D grounds a wye solidly |
| a non-native two-winding connection (a wye-delta from OpenDSS, for example) | written wye-wye | its phase shift and zero sequence are lost |
| an open-delta bank | a full bank | the same replacement |
| a delta regulator bank | a wye bank | GridLAB-D 6.0 has no delta regulator under NR |
| a line's impedance from geometry | GridLAB-D's own line constants | each engine computes its own |
| a triplex line's shunt susceptance | not written | a `triplex_line` has none |
| a bus's `nominal_voltage` as the deck rounded it | the base voltage's, over the square root of 3 | `2401.78` comes back `2401.7771...` |
| a battery's DC voltage | GridLAB-D's default | CIM has no home for it yet; the number of cells changes with it |
| a load's `constant_power_X` form | a `base_power_X` with fractions and power factors | a ZIP load is written in one form |
| a `triplex_node` with power | a `triplex_load` | it is a consumer in CIM |
| a load of a group with no schedule | a static load, with one warning | a reference to no player would not load |
| a player's start zone | GMT, the same instant | GridLAB-D reads GMT under any clock zone |
| a configuration no equipment uses | not written | configurations are written per use |
| a slot CIM cannot hold (a rating, for example) | GridLAB-D's default | |

The decks keep their own settings only where CIM holds them. An object the importer does not convert (a house, a
recorder) is not in CIM, so it is not in the exported deck. [What converts](coverage.md) lists them.
The [export mapping](../EXPORT_MAPPING.md) has the same table with the size of each difference measured.

An exporter raises on conducting equipment of a CIM class that no module handles, naming the class and the count
(`no GLM export yet for {...}`), so nothing is dropped silently.

## Compare voltages in GridLAB-D

The [`gridlabd` wheel](https://pypi.org/project/gridlabd/) runs the engine from Python. The package's `solve` extra
installs it: `pip install --pre "cimhub-gridlabd[solve]"`. Solve each deck and compare the bus voltages. Three things make the comparison fair:

- **The run file.** The IEEE 13 deck's loads read `ieeezipload.value`, so the original needs GridAPPS-D's player. The
  exporter writes those loads static, which is the same as a player that holds 1.0. The run file below declares one
  that does.
- **Two settings of the original** that the importer reads differently from the engine. A bus the engine would make a
  second swing (`SWING_PQ`) is a plain bus in CIM, and a battery's `CONSTANT_PF` mode is its `CONSTANT_PQ` set point.
- **Complex output.** The wheel reads GridLAB-D's polar text (`2401.78-120d`) as rectangular, so set
  `complex_output_format` to `RECT` before you read a voltage.

```python
import shutil
import tempfile
from pathlib import Path

import gridlabd

from cimhub_gridlabd.exporter.cim_to_glm import GlmExporter
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.glm_writer import GlmWriter
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim

VSOURCE = "66395.28"
original = Path("cimhub_gridlabd/tests/decks/IEEE/IEEE13_cdpsm.glm")
work = Path(tempfile.mkdtemp())

# the exported deck
network = glm_to_cim(GlmReader(original, defines={"VSOURCE": VSOURCE}).read_all(), name="IEEE13_cdpsm")
GlmWriter().write(GlmExporter().to_model(network, name_source="name"), work / "exported.glm")

# the original, as the importer reads it, behind a run file whose player holds 1.0
text = original.read_text().replace("  nominal_voltage 277.13;\n  bustype SWING_PQ;\n", "  nominal_voltage 277.13;\n")
for p_out in ("100000.000", "-5000.000", "-1000.000"):
    text = text.replace(f"  P_Out {p_out};\n  four_quadrant_control_mode CONSTANT_PF;",
                        f"  P_Out {p_out};\n  four_quadrant_control_mode CONSTANT_PQ;")
(work / "IEEE13_cdpsm.glm").write_text(text)
(work / "ieeezipload.player").write_text("2000-01-01 00:00:00 UTC,1.0\n")
(work / "run.glm").write_text(f"""clock {{ timezone UTC0; starttime '2000-01-01 00:00:00'; stoptime '2000-01-01 00:00:00'; }}
#set relax_naming_rules=1
module powerflow {{ solver_method NR; line_capacitance TRUE; }}
module generators;
module tape;
class player {{ double value; }}
object player {{ name ieeezipload; file ieeezipload.player; }}
#define VSOURCE={VSOURCE}
#include "IEEE13_cdpsm.glm"
""")

BUS_CLASSES = {"node": "ABC", "substation": "ABC", "meter": "ABC", "load": "ABC", "triplex_node": "12",
               "triplex_meter": "12", "triplex_load": "12"}


def solve(path):
    """{bus: {leg: complex volts}} after one power flow."""
    engine = gridlabd.GridLabD()
    engine.set_working_directory(str(path.parent))
    assert engine.load_glm([path.name]) == 0
    engine.global_setvar("complex_output_format", "RECT")
    assert engine.run() == 0
    return {name: {leg: engine.get_object_property_value(name, f"voltage_{leg}") for leg in legs}
            for class_name, legs in BUS_CLASSES.items() for name in engine.get_objects_by_class(class_name)}


before, after = solve(work / "run.glm"), solve(work / "exported.glm")
common = sorted(set(before) & set(after))
worst = max((abs(before[name][leg] - after[name][leg]) / abs(before[name][leg]), name, leg)
            for name in common for leg in before[name] if abs(before[name][leg]) > 1.0)
print(f"{len(common)} common buses; worst {worst[0]:.1e} at {worst[1]} leg {worst[2]}")
print("only in the original:", sorted(set(before) - set(after)))
```

For IEEE 13 this prints `31 common buses; worst 1.7e-05 at ld_house leg 2` (leg `2` is the load's second 120 V leg) and lists the four meters
`634_pvmtr`, `634_stmtr`, `house_pvmtr` and `house_stmtr`, which CIM folds into their parent buses. The package's own
tests allow a relative difference of 1e-4 on the three Java-exported IEEE decks.

## What the tests check

The package's tests run from a checkout (`cimhub_gridlabd/tests/`). The engine-based ones need the `gridlabd` wheel,
which is in the development environment.

| Test file | Checks |
|---|---|
| `test_export_atoms.py` | Each importer atom through the exporter and the importer again. The two CIM models must be equal (`cimtables.diff_models`, in SI) except the differences listed above, each matched by name. Each exported atom deck is a committed golden (`tests/atoms/<table>/*.exported.glm`). |
| `test_export_decks.py` | The IEEE 13 (`cdpsm` and `assets`) and 123 decks through import and export, solved in GridLAB-D against the original's voltages within 1e-4. A second pass gives byte-identical text. The exported IEEE 13 deck is a committed golden. |
| `test_export_players.py`, `test_export_schedules.py` | A player and a schedule through export: the expressions, tape and rules, the static fallback and the raises. GridLAB-D plays the exported IEEE 13 player and the exported schedules and gets the original's values. |
| `test_cimtbl_sweep.py` | Every deck binds, with a check on each class's values in the engine's terms, or stops at a named expected error. An unlisted stop fails, and so does a listed stop that now binds. The IEEE 13 `.cimtbl` directory matches the committed golden. |
| `test_cimtbl_*.py` | Each mapper against its atoms (`tests/atoms/<table>/`): the `.cimtbl` text, the values and the raises. |
| `tests/cross_format/` (repository root) | GridLAB-D against OpenDSS, below. |

The cross-format tests (`scripts/test-all.sh cross_format`) check what a single spoke cannot:

| Test | Checks |
|---|---|
| `test_dss_to_glm.py` | OpenDSS decks through CIM to GridLAB-D, solved in both engines at one frozen state (controls off, CIM's taps, loads at any voltage), line to line on three-phase buses. Each deck has a tolerance that names its known difference. |
| `test_ieee13_glm_vs_dss.py` | The IEEE 13 GLM import against the OpenDSS import of the same model, through the core getters. The expected differences (the source angle, the regulator controls, the DER output) are asserted as differences. |
| `test_glm_to_dss.py` | The transformer forms of a GLM deck exported to OpenDSS and solved there. |
| `test_glm_player_to_dss.py`, `test_glm_schedule_elsewhere.py` | A player becomes an OpenDSS `LoadShape` that solves as the player's values; a schedule is written static in OpenDSS and GDM, with one warning. |

## Running the tests

From a checkout, one pytest process per package:

```bash
scripts/test-all.sh gridlabd                   # the package's tests
scripts/test-all.sh gridlabd -- --roundtrip    # also the decks that are not vendored
scripts/test-all.sh cross_format               # GridLAB-D against OpenDSS
```

The vendored decks (`cimhub_gridlabd/tests/decks/`, origins in its README) are the IEEE 13-node (`cdpsm`, `assets`,
`houses`) and IEEE 123-node decks, two PNNL taxonomy feeders and the zipload player. Three of them stop at import with a
named error, and the sweep checks each stop: `IEEE13_houses` rates its bus 634 center taps for 2401 V on a 480 V bus,
and the two PNNL feeders set no regulator rating. The other taxonomy feeders and IEEE 123 transactive are not
vendored. Set `CIMHUB_GLM_DECKS` to a directory with the same layout (`PNNL/orig_R5-12.47-3.glm`) and pass
`--roundtrip`, and their tests run. Set `CIMHUB_GLM_UTILITY_DECKS` to a directory of your own `*.glm` files and the
sweep binds each of them.

To regenerate a golden after an intended change, set `CIMHUB_UPDATE_GOLDENS=1` and review the diff.
