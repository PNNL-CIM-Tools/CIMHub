"""Export every importer golden and import it again: the same golden (EXPORT_PLAN.md §4, the CIM fixed point).

The golden is loaded from its ``.cimtbl``, not built, so the exporter can only see what CIM holds. Names come from
the CIM ``name``, so the reimport compiles the same mRIDs. Families the exporter does not cover yet must raise
(the reactor golden: X4 waits for S6e's get_series_compensator). A golden that cannot come back whole lists its differences.
"""

import re

import cimtables
import gdm_atoms
import pytest
from cimtables.diff import diff_models

from cimhub_gdm import GdmExporter, gdm_to_cim

#: Families exported so far (EXPORT_PLAN.md §2); this grows phase by phase until it is every family.
EXPORTED = {"shell", "source", "switch", "line", "load", "capacitor", "transformer", "regulator", "der", "e2e"}

#: The regulator catalogs' TransformerTankConfigurations, which no VoltageRegulator links (cim18v17 has no
#: AutoTransformer configuration), are rebuilt from the exported per-unit equipment: its rating per unit (reg3's
#: 5000 kVA bank is 1666.67 kVA a unit) and the impedance fill, r 0.005 % a winding (EXPORT_MAPPING.md#regulators).
CIM_DIFFERENCES = {
    #: house's InverterInfo has no name, so the importer names it by its GDM uuid rehashed (B18); the export's
    #: InverterEquipment has a fresh uuid, so it comes back under another mRID.
    "der/der": [
        "GenerationInverterInfo 53cd40e1-4a74-56af-8ddb-273b080b75b3: missing",
        "GenerationInverterInfo 71c3a9b8-51fb-5fbf-8113-b9accca6acce: extra",
        "PowerElectronicsConnection pv_house.AssetDatasheet: expected '53cd40e1-4a74-56af-8ddb-273b080b75b3', got "
        "'71c3a9b8-51fb-5fbf-8113-b9accca6acce'",
    ],
    #: The reference system's reg1666 as the regulator atom's (below): the impedance fill.
    "e2e/reference": ["TransformerTankConfiguration xc_reg1666.loadLoss: expected 0.0 watt, got 166.6 watt"],
    "regulator/regulators": [
        "TransformerTankConfiguration xc_reg1666.loadLoss: expected 0.0 watt, got 166.6 watt",
        "TransformerTankConfiguration xc_reg3.loadLoss: expected 0.0 watt, got 166.66666666666669 watt",
        "TransformerWinding xc_reg3_wdg_1.r: expected 3.461185944000001e-05 ohm, got 0.00017305929720000003 ohm",
        "TransformerWinding xc_reg3_wdg_1.ratedS: expected 5000000.0 volt_ampere, got 1666666.6666666667 volt_ampere",
        "TransformerWinding xc_reg3_wdg_2.r: expected 3.461185944000001e-05 ohm, got 0.00017305929720000003 ohm",
        "TransformerWinding xc_reg3_wdg_2.ratedS: expected 5000000.0 volt_ampere, got 1666666.6666666667 volt_ampere",
    ],
}

GOLDENS = sorted(path for path in gdm_atoms.ATOMS.rglob("*.cimtbl") if path.parent.name != "prereqs")


def export_golden(golden):
    network = gdm_atoms.type_limit_durations(cimtables.load_model(golden))  # until B22 b
    return GdmExporter().to_model(network, name_source="name", system_name=model_name(golden))


def model_name(golden) -> str:
    """The golden's ``Model =`` header: the reimport seeds its hashed identifiers (PhaseImpedanceData) with it."""
    [name] = re.findall(r"^Model = (\S+)$", golden.read_text(), flags=re.MULTILINE)
    return name


def golden_id(path) -> str:
    return f"{path.parent.name}/{path.stem}"


def golden_param(path):
    return pytest.param(path, id=golden_id(path))


@pytest.mark.parametrize("golden", [golden_param(path) for path in GOLDENS])
def test_golden_survives_export_and_reimport(golden):
    if golden.parent.name not in EXPORTED:
        with pytest.raises(ValueError, match="no GDM export yet"):
            export_golden(golden)
        return
    reimported = gdm_to_cim(export_golden(golden))
    differences = sorted(str(difference) for difference in diff_models(cimtables.load_model(golden), reimported))
    assert differences == sorted(CIM_DIFFERENCES.get(golden_id(golden), []))
