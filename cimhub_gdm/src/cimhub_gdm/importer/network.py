"""The network shell: the FeederModel, its Feeders and Substations (GDM_MAPPING.md §7, OPEN_DECISIONS 1)."""

from __future__ import annotations

from cimbuilder.network import new_feeder_model
from cimbuilder.object_builder import FeederBuilder, SubstationBuilder
from cimhub_core.cimtbl import Field, mrid
from gdm.systems.distribution.components import DistributionFeeder, DistributionSubstation

from cimhub_gdm.importer.shared import (
    AUTHORITY,
    FEEDER_PREFIX,
    FREQUENCY_HZ,
    SUBSTATION_PREFIX,
    Naming,
    check_shell_name,
    components,
)

FIELDS_DistributionSubstation = {
    "uuid": Field("structural", note="never copied; an empty or clashing name raises (check_shell_name)"),
    "name": Field("copied", (("create", "mRID", None), ("create", "name", None)),
                  note="mRID = sub_ + name; a GUID raises"),
    "feeders": Field("structural", note="each listed Feeder's NormalEnergizingSubstation"),
}

FIELDS_DistributionFeeder = {
    "uuid": Field("structural", note="never copied; an empty or clashing name raises (check_shell_name)"),
    "name": Field("copied", (("create", "mRID", None), ("create", "name", None)),
                  note="mRID = fdr_ + name; a GUID raises"),
}


def new_network(system, naming: Naming):
    """An empty cim18v17 FeederModel holding every Feeder and Substation of ``system``.

    The model's own container is the system Feeder ``fdr_<system.name>`` when some component names neither a
    feeder nor a substation, or when the system has no feeder; otherwise the first feeder by name.
    """
    if not system.name or not system.name.strip():
        raise ValueError("DistributionSystem.name is empty; set it, it is the CIM Model name")
    feeders = components(system, DistributionFeeder)
    substations = components(system, DistributionSubstation)
    for shell_component in feeders + substations:
        check_shell_name(shell_component, naming)
    energizing = _energizing_substations(substations)

    if not feeders or _needs_system_feeder(system):
        container_name = system.name
    else:
        container_name = feeders[0].name
    network = new_feeder_model(authority=AUTHORITY, model=system.name, Feeder=mrid(FEEDER_PREFIX, container_name),
                               name=container_name, frequency=FREQUENCY_HZ)

    for substation in substations:
        SubstationBuilder(network, network.container).create(mRID=mrid(SUBSTATION_PREFIX, substation.name),
                                                             name=substation.name)
    feeder_builder = FeederBuilder(network, network.container)
    for feeder in feeders:
        if feeder.name == container_name:
            cim_feeder = network.container
        else:
            cim_feeder = feeder_builder.create(mRID=mrid(FEEDER_PREFIX, feeder.name), name=feeder.name)
        substation_name = energizing.get(feeder.name)
        if substation_name is not None:
            feeder_builder.add_connectivity(cim_feeder,
                                            NormalEnergizingSubstation=mrid(SUBSTATION_PREFIX, substation_name))
    return network


def _energizing_substations(substations) -> dict[str, str]:
    """Feeder name → the name of the substation that lists it. A feeder listed by two substations raises."""
    energizing: dict[str, str] = {}
    for substation in substations:
        for feeder in substation.feeders:
            other = energizing.setdefault(feeder.name, substation.name)
            if other != substation.name:
                raise ValueError(f"DistributionFeeder {feeder.name!r} is listed by substations {other!r} and "
                                 f"{substation.name!r}")
    return energizing


def _needs_system_feeder(system) -> bool:
    """True when some component names neither a feeder nor a substation."""
    for component in system.iter_all_components():
        fields = type(component).model_fields
        if "feeder" in fields and "substation" in fields:
            if component.feeder is None and component.substation is None:
                return True
    return False
