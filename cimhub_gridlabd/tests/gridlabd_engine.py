"""GridLAB-D 6.0 (the ``gridlabd`` wheel, a dev dependency) as a test oracle: solve a deck and read its bus voltages.

Notes on the wheel (GLM_REWRITE_PLAN.md section 8.5 Q3):

- ``GridLabD`` runs the engine in a worker process and reports a failed load only as "failed to load model file";
  ``engine_messages`` reruns the deck in process (``DirectGridLabD``), which prints the parser's own message.
- The bindings read GridLAB-D's polar text (``2401.78-120d``) as rectangular, so every voltage is read after
  ``complex_output_format`` is set to ``RECT``.
- The Java CIMHub exports drive their loads by ``ieeezipload.value*K``, which needs GridAPPS-D's run-file pattern: a
  tape ``player`` named ``ieeezipload`` with a declared ``value`` (``run_file``).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import gridlabd

#: every bus class whose voltages are compared, and its voltage properties
BUS_CLASSES = {"node": ("A", "B", "C"), "substation": ("A", "B", "C"), "meter": ("A", "B", "C"),
               "load": ("A", "B", "C"), "triplex_node": ("1", "2"), "triplex_meter": ("1", "2"),
               "triplex_load": ("1", "2")}

#: GridAPPS-D's run file for a Java CIMHub export body: one NR power flow, its loads at the schedule's 1.0
RUN_FILE = """clock {{
  timezone UTC0;
  starttime '2000-01-01 00:00:00';
  stoptime '2000-01-01 00:00:00';
}}
#set relax_naming_rules=1
module powerflow {{
  solver_method NR;
  line_capacitance TRUE;
}}
module generators;
module tape;
class player {{
  double value;
}}
object player {{
  name ieeezipload;
  file ieeezipload.player;
}}
#define VSOURCE={vsource}
#include "{body}"
"""


def run_file(body: Path, vsource: str) -> Path:
    """Write the run file (and its player) beside ``body``, a Java export without a header; return its path."""
    (body.parent / "ieeezipload.player").write_text("2000-01-01 00:00:00 UTC,1.0\n")
    path = body.parent / f"run_{body.stem}.glm"
    path.write_text(RUN_FILE.format(vsource=vsource, body=body.name))
    return path


def solve(path: Path) -> dict[str, tuple[complex, ...]]:
    """``{bus: voltages}`` after one power flow, for every object of ``BUS_CLASSES``."""
    engine = gridlabd.GridLabD()
    engine.set_working_directory(str(path.parent))
    if engine.load_glm([path.name]) != 0:
        raise AssertionError(f"GridLAB-D could not load {path}:\n{engine_messages(path)}")
    engine.global_setvar("complex_output_format", "RECT")
    if engine.run() != 0:
        raise AssertionError(f"GridLAB-D could not solve {path}:\n{engine_messages(path)}")
    voltages = {}
    for class_name, legs in BUS_CLASSES.items():
        for name in engine.get_objects_by_class(class_name):
            voltages[name] = tuple(engine.get_object_property_value(name, f"voltage_{leg}") for leg in legs)
    return voltages


def worst_difference(original: dict, exported: dict) -> tuple[float, str]:
    """The largest |V_original - V_exported| / |V_original| over the buses both hold, and where."""
    worst = (0.0, "")
    for name in sorted(set(original) & set(exported)):
        for leg, (first, second) in enumerate(zip(original[name], exported[name], strict=True)):
            if abs(first) > 1.0:
                worst = max(worst, (abs(first - second) / abs(first), f"{name}[{leg}]"))
    return worst


def engine_messages(path: Path) -> str:
    """GridLAB-D's own messages for ``path``, from an in-process run in a child interpreter."""
    script = ("import sys, gridlabd; g = gridlabd.DirectGridLabD(); g.set_working_directory(sys.argv[1]); "
              "g.load_glm([sys.argv[2]]) == 0 and g.run()")
    result = subprocess.run([sys.executable, "-c", script, str(path.parent), path.name], capture_output=True,
                            text=True, timeout=600)
    lines = (result.stdout + result.stderr).splitlines()
    return "\n".join(line for line in lines if "ERROR" in line or "FATAL" in line or "error" in line)
