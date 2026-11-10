"""The deck sweep (S5-6): every sweep deck maps and binds with its bus voltages equal to the walk's, or stops with
the error its ``SWEEP_STOPS`` row names. An unlisted stop fails, and so does a listed stop that now binds, so the
table (CIMTBL_MAPPING.md, S5) stays true. The decks outside ``tests/decks/`` run when ``CIMHUB_DSS_DECKS`` points at
the ``test_data/models/feeders/OpenDSS`` layout."""

from __future__ import annotations

import re

import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_opendss import dss_to_cim
from cimhub_opendss.dss_reader import DssReader

from conftest import deck
from test_dss_to_cimtbl import assert_base_voltages_agree

_DSS_10 = "the engine's rule is not pinned yet (DSS-10)"

#: Deck -> the text of the error it stops on, or None when it binds.
SWEEP_STOPS = {
    "EPRI/J1/Master.dss": _DSS_10,
    "EPRI/K1/Master.dss": _DSS_10,
    "EPRI/M1/Master.dss": _DSS_10,
    "IEEE/IEEE123/IEEE123Master.dss": None,
    "IEEE/IEEE123_PV/IEEE123Master_fixedVR.dss": None,
    "IEEE/IEEE123_deconfliction/IEEE123Master.dss": None,
    "IEEE/IEEE123_test_harness/IEEE123Master.dss": "Storage Battery5: bus 108.1.2.3 gives more nodes",  # S4b-6
    "IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss": None,
    "IEEE/IEEE13_OCHRE/Master.dss": _DSS_10,
    "IEEE/IEEE13_assets/IEEE13_Assets.dss": None,
    "IEEE/IEEE13_original/IEEE13Nodeckt.dss": None,
    "IEEE/IEEE37/ieee37.dss": None,
    "IEEE/IEEE4_xfmrs/4Bus-DY-Bal.DSS": None,
    "IEEE/IEEE4_xfmrs/4Bus-GrdYD-Bal.DSS": None,
    "IEEE/IEEE4_xfmrs/4Bus-OYOD-Bal.DSS": None,
    "IEEE/IEEE4_xfmrs/4Bus-YD-Bal.DSS": None,
    "IEEE/IEEE4_xfmrs/4Bus-YY-Bal.DSS": None,
    "IEEE/IEEE4_xfmrs/4bus-OYOD-UnBal.dss": None,
    "IEEE/IEEE4_xfmrs/YYD-Master.DSS": None,
    "IEEE/IEEE8500/Master-unbal.dss": None,
    "IEEE/IEEE8500/Master.dss": None,
    # The deck names a line code it never defines; the engine rejects it too.
    "PNNL/IEEE9500/Master-bal-initial-config.dss": "linecode=3PH_H-4_ACSR4_ACSR4_ACSR4_ACSR is no LineCode",
    "PNNL/IEEE9500/Master-unbal-initial-config.dss": None,
    "UAF/ACEP_PSIL.dss": None,
}


@pytest.mark.roundtrip
@pytest.mark.parametrize("relative", sorted(SWEEP_STOPS))
def test_deck_binds_or_stops_as_listed(relative):
    path = deck(relative)
    stop = SWEEP_STOPS[relative]
    with cim_scope():
        if stop is None:
            assert_base_voltages_agree(dss_to_cim(DssReader(path).read_all(), name="sweep"))
            return
        with pytest.raises(ValueError, match=re.escape(stop)):
            dss_to_cim(DssReader(path).read_all(), name="sweep")
