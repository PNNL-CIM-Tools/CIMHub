"""Every test runs inside ``cim_scope``: CIM-Builder and cimtables set the CIM profile and model scope process-wide."""

import pytest
from cimhub_core.cimtbl_testing import cim_scope


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield
