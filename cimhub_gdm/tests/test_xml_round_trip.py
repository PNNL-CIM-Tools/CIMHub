"""Every atom family in one system: build → write_xml (cim18v17) → reload → nothing lost (TEST_DESIGN.md, Phase 5)."""

import re

import gdm_atoms
from cimgraph.databases import XMLFile
from cimgraph.models import FeederModel
from cimgraph.utils import write_xml
from cimtables.diff import diff_models

from cimhub_gdm import gdm_to_cim

FAMILIES = (gdm_atoms.add_source, gdm_atoms.add_switches, gdm_atoms.add_lines, gdm_atoms.add_loads,
            gdm_atoms.add_capacitors, gdm_atoms.add_transformers, gdm_atoms.add_regulators, gdm_atoms.add_der,
            gdm_atoms.add_reactors)


def test_every_family_survives_an_xml_round_trip(tmp_path):
    system = gdm_atoms.shell_system()
    for add_family in FAMILIES:
        add_family(system)
    built = gdm_to_cim(system)
    xml_path = tmp_path / "atoms.xml"
    write_xml(built, str(xml_path))

    reloaded = FeederModel(connection=XMLFile(filename=str(xml_path)), container=None, distributed=False)
    assert diff_models(built, reloaded) == []
    # a PerCent value is written as the percent number: ess's 95 % charging efficiency is 95.0, not 0.95
    assert re.findall(r">([^<]+)</\w+:BatteryUnit\.chargingEfficiency>", xml_path.read_text()) == ["95.0", "90.0"]
