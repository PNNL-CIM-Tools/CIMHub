"""S5: the deck sweep (S5-1) and the IEEE13_cdpsm reference golden directory (S5-2, D6).

Each deck is read and bound once, and every slice's GridLAB-D check runs on that network. A deck in ``BIND_STOPS``
must stop with its listed error: an unlisted stop fails, and so does a listed stop that now binds.
"""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import cimtables
import pytest
from cimtables.document import write_documents

from conftest import BIND_STOPS, deck, deck_params, defines
from cimhub_core.cimtbl_testing import assert_text_matches_golden
from cimhub_gridlabd.glm_reader import GlmParseError, GlmReader
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim
from test_cimtbl_bus import assert_buses
from test_cimtbl_capacitor import assert_gridlabd_capacitors
from test_cimtbl_catalog import assert_catalogs
from test_cimtbl_inverter import assert_gridlabd_der
from test_cimtbl_line import assert_lines_and_switches
from test_cimtbl_load import assert_gridlabd_loads
from test_cimtbl_regulator import assert_gridlabd_regulation
from test_cimtbl_transformer import assert_transformers

IEEE13 = "IEEE/IEEE13_cdpsm.glm"
GOLDEN_DIRECTORY = Path(__file__).parent / "goldens" / "IEEE13_cdpsm"


def read(relative: str):
    return GlmReader(deck(relative), defines=defines(relative)).read_all()


@pytest.mark.parametrize("relative, stop", deck_params(BIND_STOPS))
def test_every_deck_binds_as_gridlabd_runs_it(relative, stop, scope):
    if stop is not None:
        with pytest.raises((GlmParseError, ValueError), match=stop):
            glm_to_cim(read(relative), name=Path(relative).stem)
        return
    model = read(relative)
    network = glm_to_cim(model, name=Path(relative).stem)
    assert_buses(network)
    assert_catalogs(model, network)
    assert_lines_and_switches(model, network)
    assert_transformers(model, network)
    assert_gridlabd_regulation(model, network)
    assert_gridlabd_loads(model, network)
    assert_gridlabd_capacitors(model, network)
    assert_gridlabd_der(model, network)


def test_ieee13_cdpsm_golden_directory(tmp_path, scope):
    """The written directory is the golden one, file for file, and the golden directory binds on its own (D6)."""
    write_documents(GlmImporter("IEEE13_cdpsm").to_cimtbl(read(IEEE13)), tmp_path)
    written = sorted(path.name for path in tmp_path.glob("*.cimtbl"))
    for name in written:
        assert_text_matches_golden((tmp_path / name).read_text(), GOLDEN_DIRECTORY / name)
    assert sorted(path.name for path in GOLDEN_DIRECTORY.glob("*.cimtbl")) == written
    network = cimtables.load_model(GOLDEN_DIRECTORY / "IEEE13_cdpsm.cimtbl")
    voltages = sorted(float(bv.nominalVoltage.to("kV")) for bv in network.list_by_class(cim.BaseVoltage))
    assert voltages == [0.24, 0.48, 4.16, 115.0]
