"""Class coverage, the time-series drop, and API conformance (TEST_DESIGN.md)."""

import inspect
import logging
import sys
from datetime import datetime, timedelta

import gdm_atoms
import pydantic
import pytest
from cimgraph.models import FeederModel
from cimhub_core.base import FormatImporter
from cimhub_gdm.importer.gdm_to_cim import INLINE, ORDER, PENDING, SHELL, UNTRANSCRIBED
from gdm.systems.distribution import common, components, controllers, equipment
from gdm.systems.distribution.components import DistributionFeeder, DistributionVoltageSource
from gdm.systems.distribution.controllers import PowerfactorControlSetting
from gdm.systems.distribution.equipment import VoltageSourceEquipment
from infrasys.time_series_models import SingleTimeSeries

from cimhub_gdm import GdmImporter, gdm_to_cim

LEGACY_PROFILES = ("cimhub_2023", "cim18gad", "cim17v40", "cimhub_2026")


def _concrete_gdm_classes():
    found = set()
    for module in (components, equipment, controllers, common):
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, pydantic.BaseModel) and cls.__module__.startswith("gdm") and not name.endswith("Base"):
                found.add(cls)
    return found


def test_every_gdm_class_is_in_exactly_one_list():
    lists = [set(SHELL), {cls for cls, _, _ in ORDER}, set(INLINE), set(UNTRANSCRIBED), set(PENDING)]
    for cls in _concrete_gdm_classes():
        assert sum(cls in group for group in lists) == 1, cls.__name__


def test_pending_class_raises_naming_what_it_waits_for():
    system = gdm_atoms.shell_system()
    system.add_component(PowerfactorControlSetting.example())
    with pytest.raises(ValueError, match=r"PowerfactorControlSetting x1: pending, inverter controls"):
        gdm_to_cim(system)


def test_unclassified_class_raises():
    class LocalFeeder(DistributionFeeder):
        pass

    system = gdm_atoms.shell_system()
    system.add_component(LocalFeeder(name="local"))
    with pytest.raises(ValueError, match="LocalFeeder x1: not classified"):
        gdm_to_cim(system)


def test_orphan_inline_equipment_raises():
    system = gdm_atoms.shell_system()
    source = gdm_atoms.add_source(system)
    system.add_component(VoltageSourceEquipment(name="spare", sources=list(source.equipment.sources)))
    with pytest.raises(ValueError, match="VoltageSourceEquipment x1: inline equipment with no parent"):
        gdm_to_cim(system)


def test_time_series_are_dropped_with_one_warning(caplog):
    system = gdm_atoms.shell_system()
    source = gdm_atoms.add_source(system)
    series = SingleTimeSeries.from_array(data=[1.0, 1.02, 0.98], name="pu_voltage",
                                         initial_timestamp=datetime(2020, 1, 1), resolution=timedelta(hours=1))
    system.add_time_series(series, system.get_component(DistributionVoltageSource, source.name))
    with caplog.at_level(logging.WARNING, logger="cimhub_gdm"):
        gdm_atoms.assert_import_matches(system, gdm_atoms.ATOMS / "source" / "balanced_3ph.cimtbl")
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "dropping 1 time series" in warnings[0].getMessage()
    assert "DistributionVoltageSource 'src': pu_voltage" in warnings[0].getMessage()


def test_importer_conforms_to_the_core_api():
    assert issubclass(GdmImporter, FormatImporter)
    assert GdmImporter.model_cls is FeederModel
    def parameters(function):  # annotations differ by design: GDM passes a DistributionSystem (contract §9)
        return [(p.name, p.kind, p.default) for p in inspect.signature(function).parameters.values()]

    assert parameters(GdmImporter.to_cim) == parameters(FormatImporter.to_cim)
    with pytest.raises(ValueError, match="builds its own network"):
        GdmImporter().to_cim(gdm_atoms.shell_system(), network=object())


def test_no_builder_module_uses_a_legacy_profile():
    gdm_to_cim(gdm_atoms.shell_system())
    legacy = []
    for name, module in list(sys.modules.items()):
        if not name.startswith("cimbuilder") or module is None:
            continue
        for value in vars(module).values():
            if inspect.ismodule(value) and any(profile in value.__name__ for profile in LEGACY_PROFILES):
                legacy.append(f"{name} uses {value.__name__}")
    assert legacy == []
