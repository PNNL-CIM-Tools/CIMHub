"""GLM ``transformer`` -> ``transformer.cimtbl``: a ``PowerTransformer`` by template (S3b).

Each transformer is a ``PowerTransformer`` with a ``TransformerTank`` per tank of its configuration's template
(one, or a can per wired phase of a bank, S3b-9) and a ``PowerTransformerEnd`` per side on the root bus of
``from`` and ``to`` (GLM-4). The values live in the template (``transformer_configuration.py``); the ends carry
the node, phases and grounding (S3b-7). A lugged template (a center tap, a one- or two-phase wye, a bank) also
gets a ``TransformerPhaseEnd`` per conductor of each terminal, numbered as the template's lugs. The transformer's
own ratings go on its own ``OperationalLimitSet``, as S3a-5 (S3b-8).

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s3b-transformers``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem, System

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, untranscribed_values
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.importer.cimtbl import transformer_configuration as templates
from cimhub_gridlabd.importer.cimtbl.catalog import label
from cimhub_gridlabd.importer.cimtbl.link import Limits, classify, link_ratings, provenance
from cimhub_gridlabd.importer.topology import WYE_CONNECTIONS
from cimhub_gridlabd.schema import gridlabd as schema

NATIVE_CLASS = schema.Transformer
PREFIX = "xf_"

_THERMAL = Field("untranscribed", note="thermal aging model and its state")
_FLUX = Field("untranscribed", note="inrush state")

FIELDS = classify(NATIVE_CLASS, {
    "name": Field("copied", (("PowerTransformer", "name", None),), "mRID = xf_ + name"),
    "phases": Field("structural", note="the ends' phases and kinds (S3b-7), and a bank's or center tap's phase ends"),
    "status": Field("structural", note="unset or CLOSED; OPEN raises (the walk)"),
    "configuration": Field("structural", note="TransformerTank.TankConfiguration = xc_<configuration> (a bank: one "
                                              "tank per can, xc_<configuration>_<phase>)"),
    **{slot: _THERMAL for slot in ("climate", "ambient_temperature", "top_oil_hot_spot_temperature",
                                   "winding_hot_spot_temperature", "percent_loss_of_life", "aging_constant",
                                   "use_thermal_model", "transformer_replacement_count", "aging_granularity")},
    **{f"phase_{letter}_{side}_flux_value": _FLUX for letter in "ABC" for side in ("primary", "secondary")},
})

#: connect_type -> ((connectionKind, grounded) of end 1, of end 2), S3b-7.
_KINDS = {
    templates.WYE_WYE: (("Yn", True), ("Yn", True)),
    "SINGLE_PHASE": (("Yn", True), ("Yn", True)),
    "DELTA_GWYE": (("D", False), ("Yn", True)),
    "DELTA_DELTA": (("D", False), ("D", False)),
    templates.CENTER_TAP: (("Y", True), ("I", True)),
}


def _letters(xf) -> str:
    return "".join(letter for letter in "ABC" if letter in str(xf.phases or ""))


def end_phases(xf, config, service: str | None = None) -> tuple[str, str]:
    """The phases of end 1 and end 2 (S3b-7); a one-phase service's end 2 is its split-phase conductors
    (``topology.service_phases``)."""
    written = str(xf.phases or "")
    letters = _letters(xf)
    connect = str(config.connect_type)
    unknown = set(written) - set("ABCNS")
    if unknown or not letters:
        raise ValueError(f"{label(xf)}: phases {xf.phases or 'unset'}; A, B, C, N and S are mapped")
    if connect == templates.CENTER_TAP:
        if len(letters) != 1 or "S" not in written:
            raise ValueError(f"{label(xf)}: phases {written} on the center tap {config.name}; it is AS, BS or CS")
        return f"{letters}N", "s1s2N"
    if "S" in written:
        raise ValueError(f"{label(xf)}: phases {written} on the {connect} {config.name}; S needs a center tap "
                         "(transformer.cpp:315)")
    if connect in WYE_CONNECTIONS:
        if "N" not in written:
            raise ValueError(f"{label(xf)}: phases {written} without N on the {connect} {config.name}; not mapped")
        return f"{letters}N", service or f"{letters}N"
    if letters != "ABC":
        raise ValueError(f"{label(xf)}: phases {written} on the {connect} {config.name}; a delta is ABC")
    return "ABC", "ABCN" if connect == "DELTA_GWYE" else "ABC"


def _check_systems(xf, config, wiring: templates.Wiring, node1: str, node2: str,
                   buses: dict[str, BusSystem]) -> None:
    if wiring.coil_rated:  # its ratedU is the systems' its ends are on (S6)
        return
    expected = ((None, System.SPLIT_PHASE) if str(config.connect_type) == templates.CENTER_TAP
                else (System.THREE_PHASE, System.THREE_PHASE))
    for node, system in zip((node1, node2), expected):
        if system is not None and buses[node].system is not system:
            raise ValueError(f"{label(xf)}: its end {node} is on a {buses[node].system.name} system, not "
                             f"{system.name} ({config.connect_type} {config.name})")


def _phase_ends(xf_mrid: str, xf, config, wiring: templates.Wiring) -> list[Row]:
    """A lugged template's TransformerPhaseEnds, numbered as its lugs, on the instance's own phases (an unrated
    template's letters are only a count, S6); a 120 V service's secondary is s1 (S6-10)."""
    letters = _letters(xf)
    if templates.center_tapped(config, wiring):
        numbered = [(1, letters, 1), (1, "N", 2), (2, "s1", 3), (2, "s2", 4), (2, "N", 5)]
    elif templates.lugged(config, wiring):
        labels = templates.can_labels(config, wiring)
        own = {**dict(zip(labels, letters, strict=True)), "N": "N"}
        secondary = {**own, labels[0]: "s1"} if wiring.service == "s1N" else own
        numbered = [(end, (own if end == 1 else secondary)[can], number)
                    for (end, can), number in templates.bank_numbers(labels).items()]
    else:
        return []
    return [Row([f"{xf_mrid}_{end}_{phase}", str(end), str(number), phase, f"{xf_mrid}_T{end}"])
            for end, phase, number in numbered]


class _Rows:
    def __init__(self):
        self.transformers: list[Row] = []
        self.tanks: list[Row] = []
        self.ends: list[Row] = []
        self.phase_ends: list[Row] = []
        self.limits = Limits()


def _transformer(model: GlmModel, xf, roots: dict[str, str], buses: dict[str, BusSystem],
                 wirings: dict[str, templates.Wiring], rows: _Rows) -> None:
    config = templates.configuration_of(model, xf)
    if xf.status is not None and str(xf.status) != "CLOSED":
        raise ValueError(f"{label(xf)}: status {xf.status}; a transformer is not a switch")
    wiring = wirings[str(config.name)]
    xf_mrid = mrid(PREFIX, xf.name)
    node1, node2 = roots[xf.from_node], roots[xf.to]
    _check_systems(xf, config, wiring, node1, node2, buses)
    rows.transformers.append(Row([xf_mrid, str(xf.name)], comment=untranscribed_values(FIELDS, xf)))
    if templates.is_bank(config, wiring):
        # a bank's cans are named <transformer>_<phase>: each is a unit of its own (one DSS Transformer per can)
        rows.tanks += [Row([f"{xf_mrid}_tank_{letter}", f"{xf.name}_{letter}", xf_mrid,
                            templates.tank_name(config, can_label)])
                       for letter, can_label in zip(_letters(xf), templates.can_labels(config, wiring), strict=True)]
    else:  # one tank goes by its transformer's name
        rows.tanks.append(Row([f"{xf_mrid}_tank", None, xf_mrid, templates.tank_name(config)]))
    kinds = _KINDS[templates.CENTER_TAP if templates.center_tapped(config, wiring) else str(config.connect_type)]
    if wiring.service == "s1N":  # a 120 V service's leg is one split-phase half, as a center tap's s1 (S6-10)
        kinds = (kinds[0], _KINDS[templates.CENTER_TAP][1])
    for number, (node, phases, (kind, grounded)) in enumerate(
            zip((node1, node2), end_phases(xf, config, wiring.service), kinds), start=1):
        rows.ends.append(Row([f"{xf_mrid}_{number}", xf_mrid, node, phases, str(number), kind, cell(grounded),
                              buses[node].base_voltage]))
    rows.phase_ends += _phase_ends(xf_mrid, xf, config, wiring)
    rows.limits.add(xf_mrid, link_ratings(xf))


def map_transformers(model: GlmModel, roots: dict[str, str], buses: dict[str, BusSystem], feeder: str) -> Document:
    """Every transformer as one document: transformers, tanks, ends, phase ends, then their limit sets."""
    transformers = model.list_by_class(NATIVE_CLASS)
    wirings = templates.wirings(model, roots, buses)
    rows = _Rows()
    for xf in transformers:
        _transformer(model, xf, roots, buses, wirings, rows)
    if not transformers:
        return Document(name=NATIVE_CLASS.class_name, statements=[], profile=CIM_PROFILE)
    statements = [
        Table("PowerTransformer", [Column("mRID"), Column("name"), Column("EquipmentContainer", default=feeder)],
              rows.transformers),
        Table("TransformerTank", [Column("mRID"), Column("name"), Column("PowerTransformer"),
                                  Column("TankConfiguration"), Column("EquipmentContainer", default=feeder)],
              rows.tanks),
        Table("PowerTransformerEnd", [Column("mRID"), Column("PowerTransformer"), Column("node"), Column("phases"),
                                      Column("endNumber"), Column("connectionKind"), Column("grounded"),
                                      Column("BaseVoltage")], rows.ends),
    ]
    if rows.phase_ends:
        statements.append(Table("TransformerPhaseEnd", [Column("mRID"), Column("endNumber"), Column("sequenceNumber"),
                                                        Column("phase"), Column("Terminal")], rows.phase_ends))
    return Document(name=NATIVE_CLASS.class_name, statements=[*statements, *rows.limits.tables()],
                    profile=CIM_PROFILE,
                    comment=provenance(NATIVE_CLASS.class_name, "PowerTransformer by template (TransformerTank + "
                                       "PowerTransformerEnd)", len(transformers), "s3b-transformers"))
