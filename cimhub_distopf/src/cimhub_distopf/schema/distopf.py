# Auto generated from main.yaml by pythongen.py version: 0.0.1
# Generation date: 2026-10-26T17:05:44
# Schema: distopf-schema
#
# id: https://gridappsd.org/cimhub/distopf
# description: LinkML schema for the DistOPF three-phase distribution optimal power flow (OPF) CSV file format, enabling round-trip conversion with CIM. This schema is the single source of truth for both data structure and serialization formatting.
# license: https://opensource.org/licenses/BSD-3-Clause

import dataclasses
import re
from dataclasses import dataclass
from datetime import (
    date,
    datetime,
    time
)
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Union
)

from jsonasobj2 import (
    JsonObj,
    as_dict
)
from linkml_runtime.linkml_model.meta import (
    EnumDefinition,
    PermissibleValue,
    PvFormulaOptions
)
from linkml_runtime.utils.curienamespace import CurieNamespace
from linkml_runtime.utils.enumerations import EnumDefinitionImpl
from linkml_runtime.utils.formatutils import (
    camelcase,
    sfx,
    underscore
)
from linkml_runtime.utils.metamodelcore import (
    bnode,
    empty_dict,
    empty_list
)
from linkml_runtime.utils.slot import Slot
from linkml_runtime.utils.yamlutils import (
    YAMLRoot,
    extended_float,
    extended_int,
    extended_str
)
from rdflib import (
    Namespace,
    URIRef
)

from linkml_runtime.linkml_model.types import Boolean, Float, Integer, String
from linkml_runtime.utils.metamodelcore import Bool

metamodel_version = "1.7.0"
version = "1.0.0"

# Namespaces
CIM = CurieNamespace('cim', 'http://iec.ch/TC57/CIM100#')
DISTOPF = CurieNamespace('distopf', 'https://gridappsd.org/cimhub/distopf')
LINKML = CurieNamespace('linkml', 'https://w3id.org/linkml/')
DEFAULT_ = DISTOPF


# Types

# Class references
class BusRecordId(extended_int):
    pass


class BranchRecordName(extended_str):
    pass


class GeneratorRecordId(extended_int):
    pass


class CapacitorRecordId(extended_int):
    pass


class BatteryRecordId(extended_int):
    pass


class RegulatorRecordId(extended_str):
    pass


class ScheduleRecordTime(extended_int):
    pass


@dataclass(repr=False)
class DistopfModel(YAMLRoot):
    """
    Complete DistOPF network model containing every record type in the CSV file set.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DISTOPF["DistopfModel"]
    class_class_curie: ClassVar[str] = "distopf:DistopfModel"
    class_name: ClassVar[str] = "DistopfModel"
    class_model_uri: ClassVar[URIRef] = DISTOPF.DistopfModel

    bus_records: Optional[Union[dict[Union[int, BusRecordId], Union[dict, "BusRecord"]], list[Union[dict, "BusRecord"]]]] = empty_dict()
    branch_records: Optional[Union[dict[Union[str, BranchRecordName], Union[dict, "BranchRecord"]], list[Union[dict, "BranchRecord"]]]] = empty_dict()
    generator_records: Optional[Union[dict[Union[int, GeneratorRecordId], Union[dict, "GeneratorRecord"]], list[Union[dict, "GeneratorRecord"]]]] = empty_dict()
    capacitor_records: Optional[Union[dict[Union[int, CapacitorRecordId], Union[dict, "CapacitorRecord"]], list[Union[dict, "CapacitorRecord"]]]] = empty_dict()
    battery_records: Optional[Union[dict[Union[int, BatteryRecordId], Union[dict, "BatteryRecord"]], list[Union[dict, "BatteryRecord"]]]] = empty_dict()
    regulator_records: Optional[Union[dict[Union[str, RegulatorRecordId], Union[dict, "RegulatorRecord"]], list[Union[dict, "RegulatorRecord"]]]] = empty_dict()
    schedule_records: Optional[Union[dict[Union[int, ScheduleRecordTime], Union[dict, "ScheduleRecord"]], list[Union[dict, "ScheduleRecord"]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        self._normalize_inlined_as_list(slot_name="bus_records", slot_type=BusRecord, key_name="id", keyed=True)

        self._normalize_inlined_as_list(slot_name="branch_records", slot_type=BranchRecord, key_name="name", keyed=True)

        self._normalize_inlined_as_list(slot_name="generator_records", slot_type=GeneratorRecord, key_name="id", keyed=True)

        self._normalize_inlined_as_list(slot_name="capacitor_records", slot_type=CapacitorRecord, key_name="id", keyed=True)

        self._normalize_inlined_as_list(slot_name="battery_records", slot_type=BatteryRecord, key_name="id", keyed=True)

        self._normalize_inlined_as_list(slot_name="regulator_records", slot_type=RegulatorRecord, key_name="id", keyed=True)

        self._normalize_inlined_as_list(slot_name="schedule_records", slot_type=ScheduleRecord, key_name="time", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class BusRecord(YAMLRoot):
    """
    Bus data record for DistOPF three-phase distribution OPF.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DISTOPF["BusRecord"]
    class_class_curie: ClassVar[str] = "distopf:BusRecord"
    class_name: ClassVar[str] = "BusRecord"
    class_model_uri: ClassVar[URIRef] = DISTOPF.BusRecord

    id: Union[int, BusRecordId] = None
    name: Optional[str] = ""
    pl_a: Optional[float] = 0.0
    ql_a: Optional[float] = 0.0
    pl_b: Optional[float] = 0.0
    ql_b: Optional[float] = 0.0
    pl_c: Optional[float] = 0.0
    ql_c: Optional[float] = 0.0
    pl_s1: Optional[float] = 0.0
    ql_s1: Optional[float] = 0.0
    pl_s2: Optional[float] = 0.0
    ql_s2: Optional[float] = 0.0
    pl_s1s2: Optional[float] = 0.0
    ql_s1s2: Optional[float] = 0.0
    bus_type: Optional[str] = "PQ"
    v_a: Optional[float] = 1.0
    v_b: Optional[float] = 1.0
    v_c: Optional[float] = 1.0
    v_ln_base: Optional[float] = 0.0
    s_base: Optional[float] = 1000000.0
    v_min: Optional[float] = 0.95
    v_max: Optional[float] = 1.05
    cvr_p: Optional[float] = 0.0
    cvr_q: Optional[float] = 0.0
    phases: Optional[str] = "abc"
    primary_phase: Optional[str] = ""
    has_gen: Optional[Union[bool, Bool]] = False
    has_load: Optional[Union[bool, Bool]] = False
    has_cap: Optional[Union[bool, Bool]] = False
    latitude: Optional[float] = 0.0
    longitude: Optional[float] = 0.0
    load_shape: Optional[str] = "default"

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, BusRecordId):
            self.id = BusRecordId(self.id)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.pl_a is not None and not isinstance(self.pl_a, float):
            self.pl_a = float(self.pl_a)

        if self.ql_a is not None and not isinstance(self.ql_a, float):
            self.ql_a = float(self.ql_a)

        if self.pl_b is not None and not isinstance(self.pl_b, float):
            self.pl_b = float(self.pl_b)

        if self.ql_b is not None and not isinstance(self.ql_b, float):
            self.ql_b = float(self.ql_b)

        if self.pl_c is not None and not isinstance(self.pl_c, float):
            self.pl_c = float(self.pl_c)

        if self.ql_c is not None and not isinstance(self.ql_c, float):
            self.ql_c = float(self.ql_c)

        if self.pl_s1 is not None and not isinstance(self.pl_s1, float):
            self.pl_s1 = float(self.pl_s1)

        if self.ql_s1 is not None and not isinstance(self.ql_s1, float):
            self.ql_s1 = float(self.ql_s1)

        if self.pl_s2 is not None and not isinstance(self.pl_s2, float):
            self.pl_s2 = float(self.pl_s2)

        if self.ql_s2 is not None and not isinstance(self.ql_s2, float):
            self.ql_s2 = float(self.ql_s2)

        if self.pl_s1s2 is not None and not isinstance(self.pl_s1s2, float):
            self.pl_s1s2 = float(self.pl_s1s2)

        if self.ql_s1s2 is not None and not isinstance(self.ql_s1s2, float):
            self.ql_s1s2 = float(self.ql_s1s2)

        if self.bus_type is not None and not isinstance(self.bus_type, str):
            self.bus_type = str(self.bus_type)

        if self.v_a is not None and not isinstance(self.v_a, float):
            self.v_a = float(self.v_a)

        if self.v_b is not None and not isinstance(self.v_b, float):
            self.v_b = float(self.v_b)

        if self.v_c is not None and not isinstance(self.v_c, float):
            self.v_c = float(self.v_c)

        if self.v_ln_base is not None and not isinstance(self.v_ln_base, float):
            self.v_ln_base = float(self.v_ln_base)

        if self.s_base is not None and not isinstance(self.s_base, float):
            self.s_base = float(self.s_base)

        if self.v_min is not None and not isinstance(self.v_min, float):
            self.v_min = float(self.v_min)

        if self.v_max is not None and not isinstance(self.v_max, float):
            self.v_max = float(self.v_max)

        if self.cvr_p is not None and not isinstance(self.cvr_p, float):
            self.cvr_p = float(self.cvr_p)

        if self.cvr_q is not None and not isinstance(self.cvr_q, float):
            self.cvr_q = float(self.cvr_q)

        if self.phases is not None and not isinstance(self.phases, str):
            self.phases = str(self.phases)

        if self.primary_phase is not None and not isinstance(self.primary_phase, str):
            self.primary_phase = str(self.primary_phase)

        if self.has_gen is not None and not isinstance(self.has_gen, Bool):
            self.has_gen = Bool(self.has_gen)

        if self.has_load is not None and not isinstance(self.has_load, Bool):
            self.has_load = Bool(self.has_load)

        if self.has_cap is not None and not isinstance(self.has_cap, Bool):
            self.has_cap = Bool(self.has_cap)

        if self.latitude is not None and not isinstance(self.latitude, float):
            self.latitude = float(self.latitude)

        if self.longitude is not None and not isinstance(self.longitude, float):
            self.longitude = float(self.longitude)

        if self.load_shape is not None and not isinstance(self.load_shape, str):
            self.load_shape = str(self.load_shape)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class BranchRecord(YAMLRoot):
    """
    Branch data record for DistOPF. A single record type represents lines, triplex lines, switches, transformers, and
    center-tap transformers, distinguished by the branch_type field.
    Impedances r_aa..r_cc and x_aa..x_cc are the upper-triangle elements of the 3x3 symmetric impedance matrix
    (r_s1s1..x_s2s2 the 2x2 triplex matrix), in per-unit (base z_base).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DISTOPF["BranchRecord"]
    class_class_curie: ClassVar[str] = "distopf:BranchRecord"
    class_name: ClassVar[str] = "BranchRecord"
    class_model_uri: ClassVar[URIRef] = DISTOPF.BranchRecord

    name: Union[str, BranchRecordName] = None
    fb: int = None
    tb: int = None
    from_name: Optional[str] = ""
    to_name: Optional[str] = ""
    r_aa: Optional[float] = 0.0
    r_ab: Optional[float] = 0.0
    r_ac: Optional[float] = 0.0
    r_bb: Optional[float] = 0.0
    r_bc: Optional[float] = 0.0
    r_cc: Optional[float] = 0.0
    x_aa: Optional[float] = 0.0
    x_ab: Optional[float] = 0.0
    x_ac: Optional[float] = 0.0
    x_bb: Optional[float] = 0.0
    x_bc: Optional[float] = 0.0
    x_cc: Optional[float] = 0.0
    r_s1s1: Optional[float] = 0.0
    r_s1s2: Optional[float] = 0.0
    r_s2s2: Optional[float] = 0.0
    x_s1s1: Optional[float] = 0.0
    x_s1s2: Optional[float] = 0.0
    x_s2s2: Optional[float] = 0.0
    primary_phase: Optional[str] = ""
    branch_type: Optional[str] = "line"
    status: Optional[str] = ""
    s_base: Optional[float] = 1000000.0
    v_ln_base: Optional[float] = 0.0
    z_base: Optional[float] = 0.0
    phases: Optional[str] = "abc"
    s_a_max: Optional[float] = 0.0
    s_b_max: Optional[float] = 0.0
    s_c_max: Optional[float] = 0.0
    length: Optional[float] = 0.0

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, BranchRecordName):
            self.name = BranchRecordName(self.name)

        if self._is_empty(self.fb):
            self.MissingRequiredField("fb")
        if not isinstance(self.fb, int):
            self.fb = int(self.fb)

        if self._is_empty(self.tb):
            self.MissingRequiredField("tb")
        if not isinstance(self.tb, int):
            self.tb = int(self.tb)

        if self.from_name is not None and not isinstance(self.from_name, str):
            self.from_name = str(self.from_name)

        if self.to_name is not None and not isinstance(self.to_name, str):
            self.to_name = str(self.to_name)

        if self.r_aa is not None and not isinstance(self.r_aa, float):
            self.r_aa = float(self.r_aa)

        if self.r_ab is not None and not isinstance(self.r_ab, float):
            self.r_ab = float(self.r_ab)

        if self.r_ac is not None and not isinstance(self.r_ac, float):
            self.r_ac = float(self.r_ac)

        if self.r_bb is not None and not isinstance(self.r_bb, float):
            self.r_bb = float(self.r_bb)

        if self.r_bc is not None and not isinstance(self.r_bc, float):
            self.r_bc = float(self.r_bc)

        if self.r_cc is not None and not isinstance(self.r_cc, float):
            self.r_cc = float(self.r_cc)

        if self.x_aa is not None and not isinstance(self.x_aa, float):
            self.x_aa = float(self.x_aa)

        if self.x_ab is not None and not isinstance(self.x_ab, float):
            self.x_ab = float(self.x_ab)

        if self.x_ac is not None and not isinstance(self.x_ac, float):
            self.x_ac = float(self.x_ac)

        if self.x_bb is not None and not isinstance(self.x_bb, float):
            self.x_bb = float(self.x_bb)

        if self.x_bc is not None and not isinstance(self.x_bc, float):
            self.x_bc = float(self.x_bc)

        if self.x_cc is not None and not isinstance(self.x_cc, float):
            self.x_cc = float(self.x_cc)

        if self.r_s1s1 is not None and not isinstance(self.r_s1s1, float):
            self.r_s1s1 = float(self.r_s1s1)

        if self.r_s1s2 is not None and not isinstance(self.r_s1s2, float):
            self.r_s1s2 = float(self.r_s1s2)

        if self.r_s2s2 is not None and not isinstance(self.r_s2s2, float):
            self.r_s2s2 = float(self.r_s2s2)

        if self.x_s1s1 is not None and not isinstance(self.x_s1s1, float):
            self.x_s1s1 = float(self.x_s1s1)

        if self.x_s1s2 is not None and not isinstance(self.x_s1s2, float):
            self.x_s1s2 = float(self.x_s1s2)

        if self.x_s2s2 is not None and not isinstance(self.x_s2s2, float):
            self.x_s2s2 = float(self.x_s2s2)

        if self.primary_phase is not None and not isinstance(self.primary_phase, str):
            self.primary_phase = str(self.primary_phase)

        if self.branch_type is not None and not isinstance(self.branch_type, str):
            self.branch_type = str(self.branch_type)

        if self.status is not None and not isinstance(self.status, str):
            self.status = str(self.status)

        if self.s_base is not None and not isinstance(self.s_base, float):
            self.s_base = float(self.s_base)

        if self.v_ln_base is not None and not isinstance(self.v_ln_base, float):
            self.v_ln_base = float(self.v_ln_base)

        if self.z_base is not None and not isinstance(self.z_base, float):
            self.z_base = float(self.z_base)

        if self.phases is not None and not isinstance(self.phases, str):
            self.phases = str(self.phases)

        if self.s_a_max is not None and not isinstance(self.s_a_max, float):
            self.s_a_max = float(self.s_a_max)

        if self.s_b_max is not None and not isinstance(self.s_b_max, float):
            self.s_b_max = float(self.s_b_max)

        if self.s_c_max is not None and not isinstance(self.s_c_max, float):
            self.s_c_max = float(self.s_c_max)

        if self.length is not None and not isinstance(self.length, float):
            self.length = float(self.length)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class GeneratorRecord(YAMLRoot):
    """
    Generator (DER) data record for DistOPF. Covers PV and diesel generation types. Power values are in per-unit (base
    s_base).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DISTOPF["GeneratorRecord"]
    class_class_curie: ClassVar[str] = "distopf:GeneratorRecord"
    class_name: ClassVar[str] = "GeneratorRecord"
    class_model_uri: ClassVar[URIRef] = DISTOPF.GeneratorRecord

    id: Union[int, GeneratorRecordId] = None
    name: Optional[str] = ""
    generator_type: Optional[str] = "pv"
    p_a: Optional[float] = 0.0
    p_b: Optional[float] = 0.0
    p_c: Optional[float] = 0.0
    q_a: Optional[float] = 0.0
    q_b: Optional[float] = 0.0
    q_c: Optional[float] = 0.0
    s_a_max: Optional[float] = 0.0
    s_b_max: Optional[float] = 0.0
    s_c_max: Optional[float] = 0.0
    p_s1: Optional[float] = 0.0
    p_s2: Optional[float] = 0.0
    q_s1: Optional[float] = 0.0
    q_s2: Optional[float] = 0.0
    s_s1_max: Optional[float] = 0.0
    s_s2_max: Optional[float] = 0.0
    s_s1s2_max: Optional[float] = 0.0
    primary_phase: Optional[str] = ""
    phases: Optional[str] = "abc"
    q_a_max: Optional[float] = 0.0
    q_b_max: Optional[float] = 0.0
    q_c_max: Optional[float] = 0.0
    q_a_min: Optional[float] = 0.0
    q_b_min: Optional[float] = 0.0
    q_c_min: Optional[float] = 0.0
    q_s1_max: Optional[float] = 0.0
    q_s2_max: Optional[float] = 0.0
    q_s1_min: Optional[float] = 0.0
    q_s2_min: Optional[float] = 0.0
    control_variable: Optional[str] = "PQ"
    s_base: Optional[float] = 1000000.0

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, GeneratorRecordId):
            self.id = GeneratorRecordId(self.id)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.generator_type is not None and not isinstance(self.generator_type, str):
            self.generator_type = str(self.generator_type)

        if self.p_a is not None and not isinstance(self.p_a, float):
            self.p_a = float(self.p_a)

        if self.p_b is not None and not isinstance(self.p_b, float):
            self.p_b = float(self.p_b)

        if self.p_c is not None and not isinstance(self.p_c, float):
            self.p_c = float(self.p_c)

        if self.q_a is not None and not isinstance(self.q_a, float):
            self.q_a = float(self.q_a)

        if self.q_b is not None and not isinstance(self.q_b, float):
            self.q_b = float(self.q_b)

        if self.q_c is not None and not isinstance(self.q_c, float):
            self.q_c = float(self.q_c)

        if self.s_a_max is not None and not isinstance(self.s_a_max, float):
            self.s_a_max = float(self.s_a_max)

        if self.s_b_max is not None and not isinstance(self.s_b_max, float):
            self.s_b_max = float(self.s_b_max)

        if self.s_c_max is not None and not isinstance(self.s_c_max, float):
            self.s_c_max = float(self.s_c_max)

        if self.p_s1 is not None and not isinstance(self.p_s1, float):
            self.p_s1 = float(self.p_s1)

        if self.p_s2 is not None and not isinstance(self.p_s2, float):
            self.p_s2 = float(self.p_s2)

        if self.q_s1 is not None and not isinstance(self.q_s1, float):
            self.q_s1 = float(self.q_s1)

        if self.q_s2 is not None and not isinstance(self.q_s2, float):
            self.q_s2 = float(self.q_s2)

        if self.s_s1_max is not None and not isinstance(self.s_s1_max, float):
            self.s_s1_max = float(self.s_s1_max)

        if self.s_s2_max is not None and not isinstance(self.s_s2_max, float):
            self.s_s2_max = float(self.s_s2_max)

        if self.s_s1s2_max is not None and not isinstance(self.s_s1s2_max, float):
            self.s_s1s2_max = float(self.s_s1s2_max)

        if self.primary_phase is not None and not isinstance(self.primary_phase, str):
            self.primary_phase = str(self.primary_phase)

        if self.phases is not None and not isinstance(self.phases, str):
            self.phases = str(self.phases)

        if self.q_a_max is not None and not isinstance(self.q_a_max, float):
            self.q_a_max = float(self.q_a_max)

        if self.q_b_max is not None and not isinstance(self.q_b_max, float):
            self.q_b_max = float(self.q_b_max)

        if self.q_c_max is not None and not isinstance(self.q_c_max, float):
            self.q_c_max = float(self.q_c_max)

        if self.q_a_min is not None and not isinstance(self.q_a_min, float):
            self.q_a_min = float(self.q_a_min)

        if self.q_b_min is not None and not isinstance(self.q_b_min, float):
            self.q_b_min = float(self.q_b_min)

        if self.q_c_min is not None and not isinstance(self.q_c_min, float):
            self.q_c_min = float(self.q_c_min)

        if self.q_s1_max is not None and not isinstance(self.q_s1_max, float):
            self.q_s1_max = float(self.q_s1_max)

        if self.q_s2_max is not None and not isinstance(self.q_s2_max, float):
            self.q_s2_max = float(self.q_s2_max)

        if self.q_s1_min is not None and not isinstance(self.q_s1_min, float):
            self.q_s1_min = float(self.q_s1_min)

        if self.q_s2_min is not None and not isinstance(self.q_s2_min, float):
            self.q_s2_min = float(self.q_s2_min)

        if self.control_variable is not None and not isinstance(self.control_variable, str):
            self.control_variable = str(self.control_variable)

        if self.s_base is not None and not isinstance(self.s_base, float):
            self.s_base = float(self.s_base)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class CapacitorRecord(YAMLRoot):
    """
    Shunt capacitor data record for DistOPF. Reactive power values are in per-unit on the fixed distOPF system base of
    1 MVA (the record has no s_base of its own).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DISTOPF["CapacitorRecord"]
    class_class_curie: ClassVar[str] = "distopf:CapacitorRecord"
    class_name: ClassVar[str] = "CapacitorRecord"
    class_model_uri: ClassVar[URIRef] = DISTOPF.CapacitorRecord

    id: Union[int, CapacitorRecordId] = None
    name: Optional[str] = ""
    q_a: Optional[float] = 0.0
    q_b: Optional[float] = 0.0
    q_c: Optional[float] = 0.0
    phases: Optional[str] = "abc"

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, CapacitorRecordId):
            self.id = CapacitorRecordId(self.id)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.q_a is not None and not isinstance(self.q_a, float):
            self.q_a = float(self.q_a)

        if self.q_b is not None and not isinstance(self.q_b, float):
            self.q_b = float(self.q_b)

        if self.q_c is not None and not isinstance(self.q_c, float):
            self.q_c = float(self.q_c)

        if self.phases is not None and not isinstance(self.phases, str):
            self.phases = str(self.phases)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class BatteryRecord(YAMLRoot):
    """
    Battery energy storage system (BESS) data record for DistOPF. Power ratings are in per-unit on the fixed distOPF
    system base of 1 MVA (the record has no s_base of its own). Energy capacity is in per-unit hours (1 MVA × hour).
    State-of-charge fields are fractions (0.0-1.0).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DISTOPF["BatteryRecord"]
    class_class_curie: ClassVar[str] = "distopf:BatteryRecord"
    class_name: ClassVar[str] = "BatteryRecord"
    class_model_uri: ClassVar[URIRef] = DISTOPF.BatteryRecord

    id: Union[int, BatteryRecordId] = None
    name: Optional[str] = ""
    s_max: Optional[float] = 0.0
    phases: Optional[str] = "abc"
    energy_capacity: Optional[float] = 0.0
    min_soc: Optional[float] = 0.0
    max_soc: Optional[float] = 1.0
    start_soc: Optional[float] = 0.5
    charge_efficiency: Optional[float] = 1.0
    discharge_efficiency: Optional[float] = 1.0
    annual_cycle_limit: Optional[int] = 365
    control_variable: Optional[str] = "P"

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, BatteryRecordId):
            self.id = BatteryRecordId(self.id)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.s_max is not None and not isinstance(self.s_max, float):
            self.s_max = float(self.s_max)

        if self.phases is not None and not isinstance(self.phases, str):
            self.phases = str(self.phases)

        if self.energy_capacity is not None and not isinstance(self.energy_capacity, float):
            self.energy_capacity = float(self.energy_capacity)

        if self.min_soc is not None and not isinstance(self.min_soc, float):
            self.min_soc = float(self.min_soc)

        if self.max_soc is not None and not isinstance(self.max_soc, float):
            self.max_soc = float(self.max_soc)

        if self.start_soc is not None and not isinstance(self.start_soc, float):
            self.start_soc = float(self.start_soc)

        if self.charge_efficiency is not None and not isinstance(self.charge_efficiency, float):
            self.charge_efficiency = float(self.charge_efficiency)

        if self.discharge_efficiency is not None and not isinstance(self.discharge_efficiency, float):
            self.discharge_efficiency = float(self.discharge_efficiency)

        if self.annual_cycle_limit is not None and not isinstance(self.annual_cycle_limit, int):
            self.annual_cycle_limit = int(self.annual_cycle_limit)

        if self.control_variable is not None and not isinstance(self.control_variable, str):
            self.control_variable = str(self.control_variable)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class RegulatorRecord(YAMLRoot):
    """
    Step voltage regulator data record for DistOPF. Tap positions are integer step counts (positive = raise, negative
    = lower).
    Note: the `id` field is a synthetic identifier not present in the CSV. The reader constructs it as "{fb}_{tb}"
    (for example, "1_2").
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DISTOPF["RegulatorRecord"]
    class_class_curie: ClassVar[str] = "distopf:RegulatorRecord"
    class_name: ClassVar[str] = "RegulatorRecord"
    class_model_uri: ClassVar[URIRef] = DISTOPF.RegulatorRecord

    id: Union[str, RegulatorRecordId] = None
    fb: int = None
    tb: int = None
    from_name: Optional[str] = ""
    to_name: Optional[str] = ""
    phases: Optional[str] = "abc"
    tap_a: Optional[float] = 0.0
    tap_b: Optional[float] = 0.0
    tap_c: Optional[float] = 0.0

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, RegulatorRecordId):
            self.id = RegulatorRecordId(self.id)

        if self._is_empty(self.fb):
            self.MissingRequiredField("fb")
        if not isinstance(self.fb, int):
            self.fb = int(self.fb)

        if self._is_empty(self.tb):
            self.MissingRequiredField("tb")
        if not isinstance(self.tb, int):
            self.tb = int(self.tb)

        if self.from_name is not None and not isinstance(self.from_name, str):
            self.from_name = str(self.from_name)

        if self.to_name is not None and not isinstance(self.to_name, str):
            self.to_name = str(self.to_name)

        if self.phases is not None and not isinstance(self.phases, str):
            self.phases = str(self.phases)

        if self.tap_a is not None and not isinstance(self.tap_a, float):
            self.tap_a = float(self.tap_a)

        if self.tap_b is not None and not isinstance(self.tap_b, float):
            self.tap_b = float(self.tap_b)

        if self.tap_c is not None and not isinstance(self.tap_c, float):
            self.tap_c = float(self.tap_c)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class ScheduleRecord(YAMLRoot):
    """
    Time-series schedule record for DistOPF. Defines per-hour multipliers for load shapes and PV generation, plus the
    locational marginal price. The `time` field is the integer hour index (0-23 for a 24-hour period).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DISTOPF["ScheduleRecord"]
    class_class_curie: ClassVar[str] = "distopf:ScheduleRecord"
    class_name: ClassVar[str] = "ScheduleRecord"
    class_model_uri: ClassVar[URIRef] = DISTOPF.ScheduleRecord

    time: Union[int, ScheduleRecordTime] = None
    pv_multiplier: Optional[float] = 0.0
    default_multiplier: Optional[float] = 0.0
    price: Optional[float] = 0.0

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.time):
            self.MissingRequiredField("time")
        if not isinstance(self.time, ScheduleRecordTime):
            self.time = ScheduleRecordTime(self.time)

        if self.pv_multiplier is not None and not isinstance(self.pv_multiplier, float):
            self.pv_multiplier = float(self.pv_multiplier)

        if self.default_multiplier is not None and not isinstance(self.default_multiplier, float):
            self.default_multiplier = float(self.default_multiplier)

        if self.price is not None and not isinstance(self.price, float):
            self.price = float(self.price)

        super().__post_init__(**kwargs)


# Enumerations


# Slots
class slots:
    pass

slots.distopfModel__bus_records = Slot(uri=DISTOPF.bus_records, name="distopfModel__bus_records", curie=DISTOPF.curie('bus_records'),
                   model_uri=DISTOPF.distopfModel__bus_records, domain=None, range=Optional[Union[dict[Union[int, BusRecordId], Union[dict, BusRecord]], list[Union[dict, BusRecord]]]])

slots.distopfModel__branch_records = Slot(uri=DISTOPF.branch_records, name="distopfModel__branch_records", curie=DISTOPF.curie('branch_records'),
                   model_uri=DISTOPF.distopfModel__branch_records, domain=None, range=Optional[Union[dict[Union[str, BranchRecordName], Union[dict, BranchRecord]], list[Union[dict, BranchRecord]]]])

slots.distopfModel__generator_records = Slot(uri=DISTOPF.generator_records, name="distopfModel__generator_records", curie=DISTOPF.curie('generator_records'),
                   model_uri=DISTOPF.distopfModel__generator_records, domain=None, range=Optional[Union[dict[Union[int, GeneratorRecordId], Union[dict, GeneratorRecord]], list[Union[dict, GeneratorRecord]]]])

slots.distopfModel__capacitor_records = Slot(uri=DISTOPF.capacitor_records, name="distopfModel__capacitor_records", curie=DISTOPF.curie('capacitor_records'),
                   model_uri=DISTOPF.distopfModel__capacitor_records, domain=None, range=Optional[Union[dict[Union[int, CapacitorRecordId], Union[dict, CapacitorRecord]], list[Union[dict, CapacitorRecord]]]])

slots.distopfModel__battery_records = Slot(uri=DISTOPF.battery_records, name="distopfModel__battery_records", curie=DISTOPF.curie('battery_records'),
                   model_uri=DISTOPF.distopfModel__battery_records, domain=None, range=Optional[Union[dict[Union[int, BatteryRecordId], Union[dict, BatteryRecord]], list[Union[dict, BatteryRecord]]]])

slots.distopfModel__regulator_records = Slot(uri=DISTOPF.regulator_records, name="distopfModel__regulator_records", curie=DISTOPF.curie('regulator_records'),
                   model_uri=DISTOPF.distopfModel__regulator_records, domain=None, range=Optional[Union[dict[Union[str, RegulatorRecordId], Union[dict, RegulatorRecord]], list[Union[dict, RegulatorRecord]]]])

slots.distopfModel__schedule_records = Slot(uri=DISTOPF.schedule_records, name="distopfModel__schedule_records", curie=DISTOPF.curie('schedule_records'),
                   model_uri=DISTOPF.distopfModel__schedule_records, domain=None, range=Optional[Union[dict[Union[int, ScheduleRecordTime], Union[dict, ScheduleRecord]], list[Union[dict, ScheduleRecord]]]])

slots.busRecord__id = Slot(uri=DISTOPF.id, name="busRecord__id", curie=DISTOPF.curie('id'),
                   model_uri=DISTOPF.busRecord__id, domain=None, range=URIRef)

slots.busRecord__name = Slot(uri=DISTOPF.name, name="busRecord__name", curie=DISTOPF.curie('name'),
                   model_uri=DISTOPF.busRecord__name, domain=None, range=Optional[str])

slots.busRecord__pl_a = Slot(uri=DISTOPF.pl_a, name="busRecord__pl_a", curie=DISTOPF.curie('pl_a'),
                   model_uri=DISTOPF.busRecord__pl_a, domain=None, range=Optional[float])

slots.busRecord__ql_a = Slot(uri=DISTOPF.ql_a, name="busRecord__ql_a", curie=DISTOPF.curie('ql_a'),
                   model_uri=DISTOPF.busRecord__ql_a, domain=None, range=Optional[float])

slots.busRecord__pl_b = Slot(uri=DISTOPF.pl_b, name="busRecord__pl_b", curie=DISTOPF.curie('pl_b'),
                   model_uri=DISTOPF.busRecord__pl_b, domain=None, range=Optional[float])

slots.busRecord__ql_b = Slot(uri=DISTOPF.ql_b, name="busRecord__ql_b", curie=DISTOPF.curie('ql_b'),
                   model_uri=DISTOPF.busRecord__ql_b, domain=None, range=Optional[float])

slots.busRecord__pl_c = Slot(uri=DISTOPF.pl_c, name="busRecord__pl_c", curie=DISTOPF.curie('pl_c'),
                   model_uri=DISTOPF.busRecord__pl_c, domain=None, range=Optional[float])

slots.busRecord__ql_c = Slot(uri=DISTOPF.ql_c, name="busRecord__ql_c", curie=DISTOPF.curie('ql_c'),
                   model_uri=DISTOPF.busRecord__ql_c, domain=None, range=Optional[float])

slots.busRecord__pl_s1 = Slot(uri=DISTOPF.pl_s1, name="busRecord__pl_s1", curie=DISTOPF.curie('pl_s1'),
                   model_uri=DISTOPF.busRecord__pl_s1, domain=None, range=Optional[float])

slots.busRecord__ql_s1 = Slot(uri=DISTOPF.ql_s1, name="busRecord__ql_s1", curie=DISTOPF.curie('ql_s1'),
                   model_uri=DISTOPF.busRecord__ql_s1, domain=None, range=Optional[float])

slots.busRecord__pl_s2 = Slot(uri=DISTOPF.pl_s2, name="busRecord__pl_s2", curie=DISTOPF.curie('pl_s2'),
                   model_uri=DISTOPF.busRecord__pl_s2, domain=None, range=Optional[float])

slots.busRecord__ql_s2 = Slot(uri=DISTOPF.ql_s2, name="busRecord__ql_s2", curie=DISTOPF.curie('ql_s2'),
                   model_uri=DISTOPF.busRecord__ql_s2, domain=None, range=Optional[float])

slots.busRecord__pl_s1s2 = Slot(uri=DISTOPF.pl_s1s2, name="busRecord__pl_s1s2", curie=DISTOPF.curie('pl_s1s2'),
                   model_uri=DISTOPF.busRecord__pl_s1s2, domain=None, range=Optional[float])

slots.busRecord__ql_s1s2 = Slot(uri=DISTOPF.ql_s1s2, name="busRecord__ql_s1s2", curie=DISTOPF.curie('ql_s1s2'),
                   model_uri=DISTOPF.busRecord__ql_s1s2, domain=None, range=Optional[float])

slots.busRecord__bus_type = Slot(uri=DISTOPF.bus_type, name="busRecord__bus_type", curie=DISTOPF.curie('bus_type'),
                   model_uri=DISTOPF.busRecord__bus_type, domain=None, range=Optional[str])

slots.busRecord__v_a = Slot(uri=DISTOPF.v_a, name="busRecord__v_a", curie=DISTOPF.curie('v_a'),
                   model_uri=DISTOPF.busRecord__v_a, domain=None, range=Optional[float])

slots.busRecord__v_b = Slot(uri=DISTOPF.v_b, name="busRecord__v_b", curie=DISTOPF.curie('v_b'),
                   model_uri=DISTOPF.busRecord__v_b, domain=None, range=Optional[float])

slots.busRecord__v_c = Slot(uri=DISTOPF.v_c, name="busRecord__v_c", curie=DISTOPF.curie('v_c'),
                   model_uri=DISTOPF.busRecord__v_c, domain=None, range=Optional[float])

slots.busRecord__v_ln_base = Slot(uri=DISTOPF.v_ln_base, name="busRecord__v_ln_base", curie=DISTOPF.curie('v_ln_base'),
                   model_uri=DISTOPF.busRecord__v_ln_base, domain=None, range=Optional[float])

slots.busRecord__s_base = Slot(uri=DISTOPF.s_base, name="busRecord__s_base", curie=DISTOPF.curie('s_base'),
                   model_uri=DISTOPF.busRecord__s_base, domain=None, range=Optional[float])

slots.busRecord__v_min = Slot(uri=DISTOPF.v_min, name="busRecord__v_min", curie=DISTOPF.curie('v_min'),
                   model_uri=DISTOPF.busRecord__v_min, domain=None, range=Optional[float])

slots.busRecord__v_max = Slot(uri=DISTOPF.v_max, name="busRecord__v_max", curie=DISTOPF.curie('v_max'),
                   model_uri=DISTOPF.busRecord__v_max, domain=None, range=Optional[float])

slots.busRecord__cvr_p = Slot(uri=DISTOPF.cvr_p, name="busRecord__cvr_p", curie=DISTOPF.curie('cvr_p'),
                   model_uri=DISTOPF.busRecord__cvr_p, domain=None, range=Optional[float])

slots.busRecord__cvr_q = Slot(uri=DISTOPF.cvr_q, name="busRecord__cvr_q", curie=DISTOPF.curie('cvr_q'),
                   model_uri=DISTOPF.busRecord__cvr_q, domain=None, range=Optional[float])

slots.busRecord__phases = Slot(uri=DISTOPF.phases, name="busRecord__phases", curie=DISTOPF.curie('phases'),
                   model_uri=DISTOPF.busRecord__phases, domain=None, range=Optional[str])

slots.busRecord__primary_phase = Slot(uri=DISTOPF.primary_phase, name="busRecord__primary_phase", curie=DISTOPF.curie('primary_phase'),
                   model_uri=DISTOPF.busRecord__primary_phase, domain=None, range=Optional[str])

slots.busRecord__has_gen = Slot(uri=DISTOPF.has_gen, name="busRecord__has_gen", curie=DISTOPF.curie('has_gen'),
                   model_uri=DISTOPF.busRecord__has_gen, domain=None, range=Optional[Union[bool, Bool]])

slots.busRecord__has_load = Slot(uri=DISTOPF.has_load, name="busRecord__has_load", curie=DISTOPF.curie('has_load'),
                   model_uri=DISTOPF.busRecord__has_load, domain=None, range=Optional[Union[bool, Bool]])

slots.busRecord__has_cap = Slot(uri=DISTOPF.has_cap, name="busRecord__has_cap", curie=DISTOPF.curie('has_cap'),
                   model_uri=DISTOPF.busRecord__has_cap, domain=None, range=Optional[Union[bool, Bool]])

slots.busRecord__latitude = Slot(uri=DISTOPF.latitude, name="busRecord__latitude", curie=DISTOPF.curie('latitude'),
                   model_uri=DISTOPF.busRecord__latitude, domain=None, range=Optional[float])

slots.busRecord__longitude = Slot(uri=DISTOPF.longitude, name="busRecord__longitude", curie=DISTOPF.curie('longitude'),
                   model_uri=DISTOPF.busRecord__longitude, domain=None, range=Optional[float])

slots.busRecord__load_shape = Slot(uri=DISTOPF.load_shape, name="busRecord__load_shape", curie=DISTOPF.curie('load_shape'),
                   model_uri=DISTOPF.busRecord__load_shape, domain=None, range=Optional[str])

slots.branchRecord__fb = Slot(uri=DISTOPF.fb, name="branchRecord__fb", curie=DISTOPF.curie('fb'),
                   model_uri=DISTOPF.branchRecord__fb, domain=None, range=int)

slots.branchRecord__tb = Slot(uri=DISTOPF.tb, name="branchRecord__tb", curie=DISTOPF.curie('tb'),
                   model_uri=DISTOPF.branchRecord__tb, domain=None, range=int)

slots.branchRecord__from_name = Slot(uri=DISTOPF.from_name, name="branchRecord__from_name", curie=DISTOPF.curie('from_name'),
                   model_uri=DISTOPF.branchRecord__from_name, domain=None, range=Optional[str])

slots.branchRecord__to_name = Slot(uri=DISTOPF.to_name, name="branchRecord__to_name", curie=DISTOPF.curie('to_name'),
                   model_uri=DISTOPF.branchRecord__to_name, domain=None, range=Optional[str])

slots.branchRecord__r_aa = Slot(uri=DISTOPF.r_aa, name="branchRecord__r_aa", curie=DISTOPF.curie('r_aa'),
                   model_uri=DISTOPF.branchRecord__r_aa, domain=None, range=Optional[float])

slots.branchRecord__r_ab = Slot(uri=DISTOPF.r_ab, name="branchRecord__r_ab", curie=DISTOPF.curie('r_ab'),
                   model_uri=DISTOPF.branchRecord__r_ab, domain=None, range=Optional[float])

slots.branchRecord__r_ac = Slot(uri=DISTOPF.r_ac, name="branchRecord__r_ac", curie=DISTOPF.curie('r_ac'),
                   model_uri=DISTOPF.branchRecord__r_ac, domain=None, range=Optional[float])

slots.branchRecord__r_bb = Slot(uri=DISTOPF.r_bb, name="branchRecord__r_bb", curie=DISTOPF.curie('r_bb'),
                   model_uri=DISTOPF.branchRecord__r_bb, domain=None, range=Optional[float])

slots.branchRecord__r_bc = Slot(uri=DISTOPF.r_bc, name="branchRecord__r_bc", curie=DISTOPF.curie('r_bc'),
                   model_uri=DISTOPF.branchRecord__r_bc, domain=None, range=Optional[float])

slots.branchRecord__r_cc = Slot(uri=DISTOPF.r_cc, name="branchRecord__r_cc", curie=DISTOPF.curie('r_cc'),
                   model_uri=DISTOPF.branchRecord__r_cc, domain=None, range=Optional[float])

slots.branchRecord__x_aa = Slot(uri=DISTOPF.x_aa, name="branchRecord__x_aa", curie=DISTOPF.curie('x_aa'),
                   model_uri=DISTOPF.branchRecord__x_aa, domain=None, range=Optional[float])

slots.branchRecord__x_ab = Slot(uri=DISTOPF.x_ab, name="branchRecord__x_ab", curie=DISTOPF.curie('x_ab'),
                   model_uri=DISTOPF.branchRecord__x_ab, domain=None, range=Optional[float])

slots.branchRecord__x_ac = Slot(uri=DISTOPF.x_ac, name="branchRecord__x_ac", curie=DISTOPF.curie('x_ac'),
                   model_uri=DISTOPF.branchRecord__x_ac, domain=None, range=Optional[float])

slots.branchRecord__x_bb = Slot(uri=DISTOPF.x_bb, name="branchRecord__x_bb", curie=DISTOPF.curie('x_bb'),
                   model_uri=DISTOPF.branchRecord__x_bb, domain=None, range=Optional[float])

slots.branchRecord__x_bc = Slot(uri=DISTOPF.x_bc, name="branchRecord__x_bc", curie=DISTOPF.curie('x_bc'),
                   model_uri=DISTOPF.branchRecord__x_bc, domain=None, range=Optional[float])

slots.branchRecord__x_cc = Slot(uri=DISTOPF.x_cc, name="branchRecord__x_cc", curie=DISTOPF.curie('x_cc'),
                   model_uri=DISTOPF.branchRecord__x_cc, domain=None, range=Optional[float])

slots.branchRecord__r_s1s1 = Slot(uri=DISTOPF.r_s1s1, name="branchRecord__r_s1s1", curie=DISTOPF.curie('r_s1s1'),
                   model_uri=DISTOPF.branchRecord__r_s1s1, domain=None, range=Optional[float])

slots.branchRecord__r_s1s2 = Slot(uri=DISTOPF.r_s1s2, name="branchRecord__r_s1s2", curie=DISTOPF.curie('r_s1s2'),
                   model_uri=DISTOPF.branchRecord__r_s1s2, domain=None, range=Optional[float])

slots.branchRecord__r_s2s2 = Slot(uri=DISTOPF.r_s2s2, name="branchRecord__r_s2s2", curie=DISTOPF.curie('r_s2s2'),
                   model_uri=DISTOPF.branchRecord__r_s2s2, domain=None, range=Optional[float])

slots.branchRecord__x_s1s1 = Slot(uri=DISTOPF.x_s1s1, name="branchRecord__x_s1s1", curie=DISTOPF.curie('x_s1s1'),
                   model_uri=DISTOPF.branchRecord__x_s1s1, domain=None, range=Optional[float])

slots.branchRecord__x_s1s2 = Slot(uri=DISTOPF.x_s1s2, name="branchRecord__x_s1s2", curie=DISTOPF.curie('x_s1s2'),
                   model_uri=DISTOPF.branchRecord__x_s1s2, domain=None, range=Optional[float])

slots.branchRecord__x_s2s2 = Slot(uri=DISTOPF.x_s2s2, name="branchRecord__x_s2s2", curie=DISTOPF.curie('x_s2s2'),
                   model_uri=DISTOPF.branchRecord__x_s2s2, domain=None, range=Optional[float])

slots.branchRecord__primary_phase = Slot(uri=DISTOPF.primary_phase, name="branchRecord__primary_phase", curie=DISTOPF.curie('primary_phase'),
                   model_uri=DISTOPF.branchRecord__primary_phase, domain=None, range=Optional[str])

slots.branchRecord__branch_type = Slot(uri=DISTOPF.branch_type, name="branchRecord__branch_type", curie=DISTOPF.curie('branch_type'),
                   model_uri=DISTOPF.branchRecord__branch_type, domain=None, range=Optional[str])

slots.branchRecord__name = Slot(uri=DISTOPF.name, name="branchRecord__name", curie=DISTOPF.curie('name'),
                   model_uri=DISTOPF.branchRecord__name, domain=None, range=URIRef)

slots.branchRecord__status = Slot(uri=DISTOPF.status, name="branchRecord__status", curie=DISTOPF.curie('status'),
                   model_uri=DISTOPF.branchRecord__status, domain=None, range=Optional[str])

slots.branchRecord__s_base = Slot(uri=DISTOPF.s_base, name="branchRecord__s_base", curie=DISTOPF.curie('s_base'),
                   model_uri=DISTOPF.branchRecord__s_base, domain=None, range=Optional[float])

slots.branchRecord__v_ln_base = Slot(uri=DISTOPF.v_ln_base, name="branchRecord__v_ln_base", curie=DISTOPF.curie('v_ln_base'),
                   model_uri=DISTOPF.branchRecord__v_ln_base, domain=None, range=Optional[float])

slots.branchRecord__z_base = Slot(uri=DISTOPF.z_base, name="branchRecord__z_base", curie=DISTOPF.curie('z_base'),
                   model_uri=DISTOPF.branchRecord__z_base, domain=None, range=Optional[float])

slots.branchRecord__phases = Slot(uri=DISTOPF.phases, name="branchRecord__phases", curie=DISTOPF.curie('phases'),
                   model_uri=DISTOPF.branchRecord__phases, domain=None, range=Optional[str])

slots.branchRecord__s_a_max = Slot(uri=DISTOPF.s_a_max, name="branchRecord__s_a_max", curie=DISTOPF.curie('s_a_max'),
                   model_uri=DISTOPF.branchRecord__s_a_max, domain=None, range=Optional[float])

slots.branchRecord__s_b_max = Slot(uri=DISTOPF.s_b_max, name="branchRecord__s_b_max", curie=DISTOPF.curie('s_b_max'),
                   model_uri=DISTOPF.branchRecord__s_b_max, domain=None, range=Optional[float])

slots.branchRecord__s_c_max = Slot(uri=DISTOPF.s_c_max, name="branchRecord__s_c_max", curie=DISTOPF.curie('s_c_max'),
                   model_uri=DISTOPF.branchRecord__s_c_max, domain=None, range=Optional[float])

slots.branchRecord__length = Slot(uri=DISTOPF.length, name="branchRecord__length", curie=DISTOPF.curie('length'),
                   model_uri=DISTOPF.branchRecord__length, domain=None, range=Optional[float])

slots.generatorRecord__id = Slot(uri=DISTOPF.id, name="generatorRecord__id", curie=DISTOPF.curie('id'),
                   model_uri=DISTOPF.generatorRecord__id, domain=None, range=URIRef)

slots.generatorRecord__name = Slot(uri=DISTOPF.name, name="generatorRecord__name", curie=DISTOPF.curie('name'),
                   model_uri=DISTOPF.generatorRecord__name, domain=None, range=Optional[str])

slots.generatorRecord__generator_type = Slot(uri=DISTOPF.generator_type, name="generatorRecord__generator_type", curie=DISTOPF.curie('generator_type'),
                   model_uri=DISTOPF.generatorRecord__generator_type, domain=None, range=Optional[str])

slots.generatorRecord__p_a = Slot(uri=DISTOPF.p_a, name="generatorRecord__p_a", curie=DISTOPF.curie('p_a'),
                   model_uri=DISTOPF.generatorRecord__p_a, domain=None, range=Optional[float])

slots.generatorRecord__p_b = Slot(uri=DISTOPF.p_b, name="generatorRecord__p_b", curie=DISTOPF.curie('p_b'),
                   model_uri=DISTOPF.generatorRecord__p_b, domain=None, range=Optional[float])

slots.generatorRecord__p_c = Slot(uri=DISTOPF.p_c, name="generatorRecord__p_c", curie=DISTOPF.curie('p_c'),
                   model_uri=DISTOPF.generatorRecord__p_c, domain=None, range=Optional[float])

slots.generatorRecord__q_a = Slot(uri=DISTOPF.q_a, name="generatorRecord__q_a", curie=DISTOPF.curie('q_a'),
                   model_uri=DISTOPF.generatorRecord__q_a, domain=None, range=Optional[float])

slots.generatorRecord__q_b = Slot(uri=DISTOPF.q_b, name="generatorRecord__q_b", curie=DISTOPF.curie('q_b'),
                   model_uri=DISTOPF.generatorRecord__q_b, domain=None, range=Optional[float])

slots.generatorRecord__q_c = Slot(uri=DISTOPF.q_c, name="generatorRecord__q_c", curie=DISTOPF.curie('q_c'),
                   model_uri=DISTOPF.generatorRecord__q_c, domain=None, range=Optional[float])

slots.generatorRecord__s_a_max = Slot(uri=DISTOPF.s_a_max, name="generatorRecord__s_a_max", curie=DISTOPF.curie('s_a_max'),
                   model_uri=DISTOPF.generatorRecord__s_a_max, domain=None, range=Optional[float])

slots.generatorRecord__s_b_max = Slot(uri=DISTOPF.s_b_max, name="generatorRecord__s_b_max", curie=DISTOPF.curie('s_b_max'),
                   model_uri=DISTOPF.generatorRecord__s_b_max, domain=None, range=Optional[float])

slots.generatorRecord__s_c_max = Slot(uri=DISTOPF.s_c_max, name="generatorRecord__s_c_max", curie=DISTOPF.curie('s_c_max'),
                   model_uri=DISTOPF.generatorRecord__s_c_max, domain=None, range=Optional[float])

slots.generatorRecord__p_s1 = Slot(uri=DISTOPF.p_s1, name="generatorRecord__p_s1", curie=DISTOPF.curie('p_s1'),
                   model_uri=DISTOPF.generatorRecord__p_s1, domain=None, range=Optional[float])

slots.generatorRecord__p_s2 = Slot(uri=DISTOPF.p_s2, name="generatorRecord__p_s2", curie=DISTOPF.curie('p_s2'),
                   model_uri=DISTOPF.generatorRecord__p_s2, domain=None, range=Optional[float])

slots.generatorRecord__q_s1 = Slot(uri=DISTOPF.q_s1, name="generatorRecord__q_s1", curie=DISTOPF.curie('q_s1'),
                   model_uri=DISTOPF.generatorRecord__q_s1, domain=None, range=Optional[float])

slots.generatorRecord__q_s2 = Slot(uri=DISTOPF.q_s2, name="generatorRecord__q_s2", curie=DISTOPF.curie('q_s2'),
                   model_uri=DISTOPF.generatorRecord__q_s2, domain=None, range=Optional[float])

slots.generatorRecord__s_s1_max = Slot(uri=DISTOPF.s_s1_max, name="generatorRecord__s_s1_max", curie=DISTOPF.curie('s_s1_max'),
                   model_uri=DISTOPF.generatorRecord__s_s1_max, domain=None, range=Optional[float])

slots.generatorRecord__s_s2_max = Slot(uri=DISTOPF.s_s2_max, name="generatorRecord__s_s2_max", curie=DISTOPF.curie('s_s2_max'),
                   model_uri=DISTOPF.generatorRecord__s_s2_max, domain=None, range=Optional[float])

slots.generatorRecord__s_s1s2_max = Slot(uri=DISTOPF.s_s1s2_max, name="generatorRecord__s_s1s2_max", curie=DISTOPF.curie('s_s1s2_max'),
                   model_uri=DISTOPF.generatorRecord__s_s1s2_max, domain=None, range=Optional[float])

slots.generatorRecord__primary_phase = Slot(uri=DISTOPF.primary_phase, name="generatorRecord__primary_phase", curie=DISTOPF.curie('primary_phase'),
                   model_uri=DISTOPF.generatorRecord__primary_phase, domain=None, range=Optional[str])

slots.generatorRecord__phases = Slot(uri=DISTOPF.phases, name="generatorRecord__phases", curie=DISTOPF.curie('phases'),
                   model_uri=DISTOPF.generatorRecord__phases, domain=None, range=Optional[str])

slots.generatorRecord__q_a_max = Slot(uri=DISTOPF.q_a_max, name="generatorRecord__q_a_max", curie=DISTOPF.curie('q_a_max'),
                   model_uri=DISTOPF.generatorRecord__q_a_max, domain=None, range=Optional[float])

slots.generatorRecord__q_b_max = Slot(uri=DISTOPF.q_b_max, name="generatorRecord__q_b_max", curie=DISTOPF.curie('q_b_max'),
                   model_uri=DISTOPF.generatorRecord__q_b_max, domain=None, range=Optional[float])

slots.generatorRecord__q_c_max = Slot(uri=DISTOPF.q_c_max, name="generatorRecord__q_c_max", curie=DISTOPF.curie('q_c_max'),
                   model_uri=DISTOPF.generatorRecord__q_c_max, domain=None, range=Optional[float])

slots.generatorRecord__q_a_min = Slot(uri=DISTOPF.q_a_min, name="generatorRecord__q_a_min", curie=DISTOPF.curie('q_a_min'),
                   model_uri=DISTOPF.generatorRecord__q_a_min, domain=None, range=Optional[float])

slots.generatorRecord__q_b_min = Slot(uri=DISTOPF.q_b_min, name="generatorRecord__q_b_min", curie=DISTOPF.curie('q_b_min'),
                   model_uri=DISTOPF.generatorRecord__q_b_min, domain=None, range=Optional[float])

slots.generatorRecord__q_c_min = Slot(uri=DISTOPF.q_c_min, name="generatorRecord__q_c_min", curie=DISTOPF.curie('q_c_min'),
                   model_uri=DISTOPF.generatorRecord__q_c_min, domain=None, range=Optional[float])

slots.generatorRecord__q_s1_max = Slot(uri=DISTOPF.q_s1_max, name="generatorRecord__q_s1_max", curie=DISTOPF.curie('q_s1_max'),
                   model_uri=DISTOPF.generatorRecord__q_s1_max, domain=None, range=Optional[float])

slots.generatorRecord__q_s2_max = Slot(uri=DISTOPF.q_s2_max, name="generatorRecord__q_s2_max", curie=DISTOPF.curie('q_s2_max'),
                   model_uri=DISTOPF.generatorRecord__q_s2_max, domain=None, range=Optional[float])

slots.generatorRecord__q_s1_min = Slot(uri=DISTOPF.q_s1_min, name="generatorRecord__q_s1_min", curie=DISTOPF.curie('q_s1_min'),
                   model_uri=DISTOPF.generatorRecord__q_s1_min, domain=None, range=Optional[float])

slots.generatorRecord__q_s2_min = Slot(uri=DISTOPF.q_s2_min, name="generatorRecord__q_s2_min", curie=DISTOPF.curie('q_s2_min'),
                   model_uri=DISTOPF.generatorRecord__q_s2_min, domain=None, range=Optional[float])

slots.generatorRecord__control_variable = Slot(uri=DISTOPF.control_variable, name="generatorRecord__control_variable", curie=DISTOPF.curie('control_variable'),
                   model_uri=DISTOPF.generatorRecord__control_variable, domain=None, range=Optional[str])

slots.generatorRecord__s_base = Slot(uri=DISTOPF.s_base, name="generatorRecord__s_base", curie=DISTOPF.curie('s_base'),
                   model_uri=DISTOPF.generatorRecord__s_base, domain=None, range=Optional[float])

slots.capacitorRecord__id = Slot(uri=DISTOPF.id, name="capacitorRecord__id", curie=DISTOPF.curie('id'),
                   model_uri=DISTOPF.capacitorRecord__id, domain=None, range=URIRef)

slots.capacitorRecord__name = Slot(uri=DISTOPF.name, name="capacitorRecord__name", curie=DISTOPF.curie('name'),
                   model_uri=DISTOPF.capacitorRecord__name, domain=None, range=Optional[str])

slots.capacitorRecord__q_a = Slot(uri=DISTOPF.q_a, name="capacitorRecord__q_a", curie=DISTOPF.curie('q_a'),
                   model_uri=DISTOPF.capacitorRecord__q_a, domain=None, range=Optional[float])

slots.capacitorRecord__q_b = Slot(uri=DISTOPF.q_b, name="capacitorRecord__q_b", curie=DISTOPF.curie('q_b'),
                   model_uri=DISTOPF.capacitorRecord__q_b, domain=None, range=Optional[float])

slots.capacitorRecord__q_c = Slot(uri=DISTOPF.q_c, name="capacitorRecord__q_c", curie=DISTOPF.curie('q_c'),
                   model_uri=DISTOPF.capacitorRecord__q_c, domain=None, range=Optional[float])

slots.capacitorRecord__phases = Slot(uri=DISTOPF.phases, name="capacitorRecord__phases", curie=DISTOPF.curie('phases'),
                   model_uri=DISTOPF.capacitorRecord__phases, domain=None, range=Optional[str])

slots.batteryRecord__id = Slot(uri=DISTOPF.id, name="batteryRecord__id", curie=DISTOPF.curie('id'),
                   model_uri=DISTOPF.batteryRecord__id, domain=None, range=URIRef)

slots.batteryRecord__name = Slot(uri=DISTOPF.name, name="batteryRecord__name", curie=DISTOPF.curie('name'),
                   model_uri=DISTOPF.batteryRecord__name, domain=None, range=Optional[str])

slots.batteryRecord__s_max = Slot(uri=DISTOPF.s_max, name="batteryRecord__s_max", curie=DISTOPF.curie('s_max'),
                   model_uri=DISTOPF.batteryRecord__s_max, domain=None, range=Optional[float])

slots.batteryRecord__phases = Slot(uri=DISTOPF.phases, name="batteryRecord__phases", curie=DISTOPF.curie('phases'),
                   model_uri=DISTOPF.batteryRecord__phases, domain=None, range=Optional[str])

slots.batteryRecord__energy_capacity = Slot(uri=DISTOPF.energy_capacity, name="batteryRecord__energy_capacity", curie=DISTOPF.curie('energy_capacity'),
                   model_uri=DISTOPF.batteryRecord__energy_capacity, domain=None, range=Optional[float])

slots.batteryRecord__min_soc = Slot(uri=DISTOPF.min_soc, name="batteryRecord__min_soc", curie=DISTOPF.curie('min_soc'),
                   model_uri=DISTOPF.batteryRecord__min_soc, domain=None, range=Optional[float])

slots.batteryRecord__max_soc = Slot(uri=DISTOPF.max_soc, name="batteryRecord__max_soc", curie=DISTOPF.curie('max_soc'),
                   model_uri=DISTOPF.batteryRecord__max_soc, domain=None, range=Optional[float])

slots.batteryRecord__start_soc = Slot(uri=DISTOPF.start_soc, name="batteryRecord__start_soc", curie=DISTOPF.curie('start_soc'),
                   model_uri=DISTOPF.batteryRecord__start_soc, domain=None, range=Optional[float])

slots.batteryRecord__charge_efficiency = Slot(uri=DISTOPF.charge_efficiency, name="batteryRecord__charge_efficiency", curie=DISTOPF.curie('charge_efficiency'),
                   model_uri=DISTOPF.batteryRecord__charge_efficiency, domain=None, range=Optional[float])

slots.batteryRecord__discharge_efficiency = Slot(uri=DISTOPF.discharge_efficiency, name="batteryRecord__discharge_efficiency", curie=DISTOPF.curie('discharge_efficiency'),
                   model_uri=DISTOPF.batteryRecord__discharge_efficiency, domain=None, range=Optional[float])

slots.batteryRecord__annual_cycle_limit = Slot(uri=DISTOPF.annual_cycle_limit, name="batteryRecord__annual_cycle_limit", curie=DISTOPF.curie('annual_cycle_limit'),
                   model_uri=DISTOPF.batteryRecord__annual_cycle_limit, domain=None, range=Optional[int])

slots.batteryRecord__control_variable = Slot(uri=DISTOPF.control_variable, name="batteryRecord__control_variable", curie=DISTOPF.curie('control_variable'),
                   model_uri=DISTOPF.batteryRecord__control_variable, domain=None, range=Optional[str])

slots.regulatorRecord__id = Slot(uri=DISTOPF.id, name="regulatorRecord__id", curie=DISTOPF.curie('id'),
                   model_uri=DISTOPF.regulatorRecord__id, domain=None, range=URIRef)

slots.regulatorRecord__fb = Slot(uri=DISTOPF.fb, name="regulatorRecord__fb", curie=DISTOPF.curie('fb'),
                   model_uri=DISTOPF.regulatorRecord__fb, domain=None, range=int)

slots.regulatorRecord__tb = Slot(uri=DISTOPF.tb, name="regulatorRecord__tb", curie=DISTOPF.curie('tb'),
                   model_uri=DISTOPF.regulatorRecord__tb, domain=None, range=int)

slots.regulatorRecord__from_name = Slot(uri=DISTOPF.from_name, name="regulatorRecord__from_name", curie=DISTOPF.curie('from_name'),
                   model_uri=DISTOPF.regulatorRecord__from_name, domain=None, range=Optional[str])

slots.regulatorRecord__to_name = Slot(uri=DISTOPF.to_name, name="regulatorRecord__to_name", curie=DISTOPF.curie('to_name'),
                   model_uri=DISTOPF.regulatorRecord__to_name, domain=None, range=Optional[str])

slots.regulatorRecord__phases = Slot(uri=DISTOPF.phases, name="regulatorRecord__phases", curie=DISTOPF.curie('phases'),
                   model_uri=DISTOPF.regulatorRecord__phases, domain=None, range=Optional[str])

slots.regulatorRecord__tap_a = Slot(uri=DISTOPF.tap_a, name="regulatorRecord__tap_a", curie=DISTOPF.curie('tap_a'),
                   model_uri=DISTOPF.regulatorRecord__tap_a, domain=None, range=Optional[float])

slots.regulatorRecord__tap_b = Slot(uri=DISTOPF.tap_b, name="regulatorRecord__tap_b", curie=DISTOPF.curie('tap_b'),
                   model_uri=DISTOPF.regulatorRecord__tap_b, domain=None, range=Optional[float])

slots.regulatorRecord__tap_c = Slot(uri=DISTOPF.tap_c, name="regulatorRecord__tap_c", curie=DISTOPF.curie('tap_c'),
                   model_uri=DISTOPF.regulatorRecord__tap_c, domain=None, range=Optional[float])

slots.scheduleRecord__time = Slot(uri=DISTOPF.time, name="scheduleRecord__time", curie=DISTOPF.curie('time'),
                   model_uri=DISTOPF.scheduleRecord__time, domain=None, range=URIRef)

slots.scheduleRecord__pv_multiplier = Slot(uri=DISTOPF.pv_multiplier, name="scheduleRecord__pv_multiplier", curie=DISTOPF.curie('pv_multiplier'),
                   model_uri=DISTOPF.scheduleRecord__pv_multiplier, domain=None, range=Optional[float])

slots.scheduleRecord__default_multiplier = Slot(uri=DISTOPF.default_multiplier, name="scheduleRecord__default_multiplier", curie=DISTOPF.curie('default_multiplier'),
                   model_uri=DISTOPF.scheduleRecord__default_multiplier, domain=None, range=Optional[float])

slots.scheduleRecord__price = Slot(uri=DISTOPF.price, name="scheduleRecord__price", curie=DISTOPF.curie('price'),
                   model_uri=DISTOPF.scheduleRecord__price, domain=None, range=Optional[float])

