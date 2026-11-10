"""Feeder → DistributionFeeder, Substation → DistributionSubstation (``EXPORT_MAPPING.md#shell``)."""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from gdm.systems.distribution.components import DistributionFeeder, DistributionSubstation

from cimhub_gdm.exporter.shared import ExportContext
from cimhub_gdm.exporter.slots import UUID, Slot

#: Feeders first: a substation lists its feeders.
CIM_CLASSES = (cim.Feeder, cim.Substation)

SLOTS = {
    DistributionFeeder: {
        "uuid": UUID,
        "name": Slot("written", "Names (X2)"),
    },
    DistributionSubstation: {
        "uuid": UUID,
        "name": Slot("written", "Names (X2)"),
        "feeders": Slot("written", "the Feeders whose NormalEnergizingSubstation it is, by name"),
    },
}


def export(obj, context: ExportContext):
    names = context.names
    if isinstance(obj, cim.Feeder):
        return DistributionFeeder(**names.own(obj))
    feeders = sorted((context.gdm(feeder) for feeder in obj.NormalEnergizedFeeder), key=lambda feeder: feeder.name)
    return DistributionSubstation(**names.own(obj), feeders=feeders)
