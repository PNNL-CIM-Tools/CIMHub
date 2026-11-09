"""The Phase 5 reference system: an IEEE13-like system with every family on one feeder (tests/atoms/e2e)."""

import gdm_atoms


def test_reference_system_matches_golden():
    gdm_atoms.assert_import_matches(gdm_atoms.reference_system(), gdm_atoms.ATOMS / "e2e" / "reference.cimtbl")
