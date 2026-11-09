"""Export every importer golden and import it again: the same golden (EXPORT_PLAN.md §4, the CIM fixed point).

The golden is loaded from its ``.cimtbl``, not built, so the exporter can only see what CIM holds. Names come from
the CIM ``name``, so the reimport compiles the same mRIDs. Families the exporter does not cover yet must raise
(the line golden too: it holds geometry lines, X4).
"""

import cimtables
import gdm_atoms
import pytest

from cimhub_gdm import GdmExporter

#: Families exported so far (EXPORT_PLAN.md §2); this grows phase by phase until it is every family.
EXPORTED = {"shell", "source", "switch", "load", "capacitor"}

GOLDENS = sorted(path for path in gdm_atoms.ATOMS.rglob("*.cimtbl") if path.parent.name != "prereqs")


def export_golden(golden):
    network = gdm_atoms.type_limit_durations(cimtables.load_model(golden))  # until B22 b
    return GdmExporter().to_model(network, name_source="name", system_name="atom")


@pytest.mark.parametrize("golden", GOLDENS, ids=lambda path: f"{path.parent.name}/{path.stem}")
def test_golden_survives_export_and_reimport(golden):
    if golden.parent.name not in EXPORTED:
        with pytest.raises(ValueError, match="no GDM export yet"):
            export_golden(golden)
        return
    gdm_atoms.assert_import_matches(export_golden(golden), golden)
