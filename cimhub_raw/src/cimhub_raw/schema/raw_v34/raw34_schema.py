# Auto generated from main.yaml by pythongen.py version: 0.0.1
# Generation date: 2026-11-08T20:52:19
# Schema: raw-raw-v34-schema
#
# id: https://gridappsd.org/cimhub/raw_v34
# description: LinkML schema for PSS/E RAW file format version 34 data
# license: https://creativecommons.org/publicdomain/zero/1.0/

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

from linkml_runtime.linkml_model.types import Float, Integer, String

metamodel_version = "1.7.0"
version = "1.0.0"

# Namespaces
LINKML = CurieNamespace('linkml', 'https://w3id.org/linkml/')
RAW = CurieNamespace('raw', 'https://gridappsd.org/cimhub/raw_v34')
XSD = CurieNamespace('xsd', 'http://www.w3.org/2001/XMLSchema#')
DEFAULT_ = RAW


# Types
class BusNumber(Integer):
    """ Bus number identifier """
    type_class_uri = XSD["integer"]
    type_class_curie = "xsd:integer"
    type_name = "BusNumber"
    type_model_uri = RAW.BusNumber


class BusId(String):
    """ Bus identifier (can be number or extended string) """
    type_class_uri = XSD["string"]
    type_class_curie = "xsd:string"
    type_name = "BusId"
    type_model_uri = RAW.BusId


class CircuitId(String):
    """ Circuit identifier (1 or 2 characters) """
    type_class_uri = XSD["string"]
    type_class_curie = "xsd:string"
    type_name = "CircuitId"
    type_model_uri = RAW.CircuitId


class Status(Integer):
    """ Status flag (0=out of service, 1=in service) """
    type_class_uri = XSD["integer"]
    type_class_curie = "xsd:integer"
    type_name = "Status"
    type_model_uri = RAW.Status


# Class references
class CaseIdentificationRecordNewCaseFlag(extended_int):
    pass


class RatingRecordRatingSetNumber(extended_int):
    pass


class BusRecordBusNumber(extended_int):
    pass


class AreaInterchangeRecordAreaNumber(extended_int):
    pass


class TwoTerminalDCRecordName(extended_str):
    pass


class ImpedanceCorrectionRecordTableNumber(extended_int):
    pass


class ZoneRecordZoneNumber(extended_int):
    pass


class OwnerRecordOwnerNumber(extended_int):
    pass


class SubstationRecordSubstationNumber(extended_int):
    pass


@dataclass(repr=False)
class RawModel(YAMLRoot):
    """
    Complete raw RAW file model containing all record types
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["RawModel"]
    class_class_curie: ClassVar[str] = "raw:RawModel"
    class_name: ClassVar[str] = "RawModel"
    class_model_uri: ClassVar[URIRef] = RAW.RawModel

    case_record: Union[dict, "CaseIdentificationRecord"] = None
    bus_records: Optional[Union[dict[Union[int, BusRecordBusNumber], Union[dict, "BusRecord"]], list[Union[dict, "BusRecord"]]]] = empty_dict()
    load_records: Optional[Union[Union[dict, "LoadRecord"], list[Union[dict, "LoadRecord"]]]] = empty_list()
    fixed_shunt_records: Optional[Union[Union[dict, "FixedShuntRecord"], list[Union[dict, "FixedShuntRecord"]]]] = empty_list()
    generator_records: Optional[Union[Union[dict, "GeneratorRecord"], list[Union[dict, "GeneratorRecord"]]]] = empty_list()
    branch_records: Optional[Union[Union[dict, "BranchRecord"], list[Union[dict, "BranchRecord"]]]] = empty_list()
    switch_records: Optional[Union[Union[dict, "SwitchRecord"], list[Union[dict, "SwitchRecord"]]]] = empty_list()
    transformer_records: Optional[Union[Union[dict, "TransformerRecord"], list[Union[dict, "TransformerRecord"]]]] = empty_list()
    area_interchange_records: Optional[Union[dict[Union[int, AreaInterchangeRecordAreaNumber], Union[dict, "AreaInterchangeRecord"]], list[Union[dict, "AreaInterchangeRecord"]]]] = empty_dict()
    two_terminal_dc_records: Optional[Union[dict[Union[str, TwoTerminalDCRecordName], Union[dict, "TwoTerminalDCRecord"]], list[Union[dict, "TwoTerminalDCRecord"]]]] = empty_dict()
    vsc_dc_records: Optional[Union[Union[dict, "VscDcRecord"], list[Union[dict, "VscDcRecord"]]]] = empty_list()
    impedance_correction_records: Optional[Union[dict[Union[int, ImpedanceCorrectionRecordTableNumber], Union[dict, "ImpedanceCorrectionRecord"]], list[Union[dict, "ImpedanceCorrectionRecord"]]]] = empty_dict()
    multi_terminal_dc_records: Optional[Union[Union[dict, "MultiTerminalDCRecord"], list[Union[dict, "MultiTerminalDCRecord"]]]] = empty_list()
    multi_section_line_records: Optional[Union[Union[dict, "MultiSectionLineRecord"], list[Union[dict, "MultiSectionLineRecord"]]]] = empty_list()
    zone_records: Optional[Union[dict[Union[int, ZoneRecordZoneNumber], Union[dict, "ZoneRecord"]], list[Union[dict, "ZoneRecord"]]]] = empty_dict()
    interarea_transfer_records: Optional[Union[Union[dict, "InterareaTransferRecord"], list[Union[dict, "InterareaTransferRecord"]]]] = empty_list()
    owner_records: Optional[Union[dict[Union[int, OwnerRecordOwnerNumber], Union[dict, "OwnerRecord"]], list[Union[dict, "OwnerRecord"]]]] = empty_dict()
    facts_device_records: Optional[Union[Union[dict, "FactsDeviceRecord"], list[Union[dict, "FactsDeviceRecord"]]]] = empty_list()
    switched_shunt_records: Optional[Union[Union[dict, "SwitchedShuntRecord"], list[Union[dict, "SwitchedShuntRecord"]]]] = empty_list()
    gne_device_records: Optional[Union[Union[dict, "GneDeviceRecord"], list[Union[dict, "GneDeviceRecord"]]]] = empty_list()
    induction_machine_records: Optional[Union[Union[dict, "InductionMachineRecord"], list[Union[dict, "InductionMachineRecord"]]]] = empty_list()
    substation_records: Optional[Union[dict[Union[int, SubstationRecordSubstationNumber], Union[dict, "SubstationRecord"]], list[Union[dict, "SubstationRecord"]]]] = empty_dict()
    substation_node_records: Optional[Union[Union[dict, "SubstationNodeRecord"], list[Union[dict, "SubstationNodeRecord"]]]] = empty_list()
    station_switching_device_records: Optional[Union[Union[dict, "StationSwitchingDeviceRecord"], list[Union[dict, "StationSwitchingDeviceRecord"]]]] = empty_list()
    equipment_terminal_records: Optional[Union[Union[dict, "EquipmentTerminalRecord"], list[Union[dict, "EquipmentTerminalRecord"]]]] = empty_list()
    multi_terminal_converter_records: Optional[Union[Union[dict, "MultiTerminalConverterRecord"], list[Union[dict, "MultiTerminalConverterRecord"]]]] = empty_list()
    multi_terminal_dc_bus_records: Optional[Union[Union[dict, "MultiTerminalDCBusRecord"], list[Union[dict, "MultiTerminalDCBusRecord"]]]] = empty_list()
    multi_terminal_dc_link_records: Optional[Union[Union[dict, "MultiTerminalDCLinkRecord"], list[Union[dict, "MultiTerminalDCLinkRecord"]]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.case_record):
            self.MissingRequiredField("case_record")
        if not isinstance(self.case_record, CaseIdentificationRecord):
            self.case_record = CaseIdentificationRecord(**as_dict(self.case_record))

        self._normalize_inlined_as_list(slot_name="bus_records", slot_type=BusRecord, key_name="bus_number", keyed=True)

        if not isinstance(self.load_records, list):
            self.load_records = [self.load_records] if self.load_records is not None else []
        self.load_records = [v if isinstance(v, LoadRecord) else LoadRecord(**as_dict(v)) for v in self.load_records]

        if not isinstance(self.fixed_shunt_records, list):
            self.fixed_shunt_records = [self.fixed_shunt_records] if self.fixed_shunt_records is not None else []
        self.fixed_shunt_records = [v if isinstance(v, FixedShuntRecord) else FixedShuntRecord(**as_dict(v)) for v in self.fixed_shunt_records]

        if not isinstance(self.generator_records, list):
            self.generator_records = [self.generator_records] if self.generator_records is not None else []
        self.generator_records = [v if isinstance(v, GeneratorRecord) else GeneratorRecord(**as_dict(v)) for v in self.generator_records]

        if not isinstance(self.branch_records, list):
            self.branch_records = [self.branch_records] if self.branch_records is not None else []
        self.branch_records = [v if isinstance(v, BranchRecord) else BranchRecord(**as_dict(v)) for v in self.branch_records]

        if not isinstance(self.switch_records, list):
            self.switch_records = [self.switch_records] if self.switch_records is not None else []
        self.switch_records = [v if isinstance(v, SwitchRecord) else SwitchRecord(**as_dict(v)) for v in self.switch_records]

        if not isinstance(self.transformer_records, list):
            self.transformer_records = [self.transformer_records] if self.transformer_records is not None else []
        self.transformer_records = [v if isinstance(v, TransformerRecord) else TransformerRecord(**as_dict(v)) for v in self.transformer_records]

        self._normalize_inlined_as_list(slot_name="area_interchange_records", slot_type=AreaInterchangeRecord, key_name="area_number", keyed=True)

        self._normalize_inlined_as_list(slot_name="two_terminal_dc_records", slot_type=TwoTerminalDCRecord, key_name="name", keyed=True)

        if not isinstance(self.vsc_dc_records, list):
            self.vsc_dc_records = [self.vsc_dc_records] if self.vsc_dc_records is not None else []
        self.vsc_dc_records = [v if isinstance(v, VscDcRecord) else VscDcRecord(**as_dict(v)) for v in self.vsc_dc_records]

        self._normalize_inlined_as_list(slot_name="impedance_correction_records", slot_type=ImpedanceCorrectionRecord, key_name="table_number", keyed=True)

        if not isinstance(self.multi_terminal_dc_records, list):
            self.multi_terminal_dc_records = [self.multi_terminal_dc_records] if self.multi_terminal_dc_records is not None else []
        self.multi_terminal_dc_records = [v if isinstance(v, MultiTerminalDCRecord) else MultiTerminalDCRecord(**as_dict(v)) for v in self.multi_terminal_dc_records]

        if not isinstance(self.multi_section_line_records, list):
            self.multi_section_line_records = [self.multi_section_line_records] if self.multi_section_line_records is not None else []
        self.multi_section_line_records = [v if isinstance(v, MultiSectionLineRecord) else MultiSectionLineRecord(**as_dict(v)) for v in self.multi_section_line_records]

        self._normalize_inlined_as_list(slot_name="zone_records", slot_type=ZoneRecord, key_name="zone_number", keyed=True)

        if not isinstance(self.interarea_transfer_records, list):
            self.interarea_transfer_records = [self.interarea_transfer_records] if self.interarea_transfer_records is not None else []
        self.interarea_transfer_records = [v if isinstance(v, InterareaTransferRecord) else InterareaTransferRecord(**as_dict(v)) for v in self.interarea_transfer_records]

        self._normalize_inlined_as_list(slot_name="owner_records", slot_type=OwnerRecord, key_name="owner_number", keyed=True)

        if not isinstance(self.facts_device_records, list):
            self.facts_device_records = [self.facts_device_records] if self.facts_device_records is not None else []
        self.facts_device_records = [v if isinstance(v, FactsDeviceRecord) else FactsDeviceRecord(**as_dict(v)) for v in self.facts_device_records]

        if not isinstance(self.switched_shunt_records, list):
            self.switched_shunt_records = [self.switched_shunt_records] if self.switched_shunt_records is not None else []
        self.switched_shunt_records = [v if isinstance(v, SwitchedShuntRecord) else SwitchedShuntRecord(**as_dict(v)) for v in self.switched_shunt_records]

        if not isinstance(self.gne_device_records, list):
            self.gne_device_records = [self.gne_device_records] if self.gne_device_records is not None else []
        self.gne_device_records = [v if isinstance(v, GneDeviceRecord) else GneDeviceRecord(**as_dict(v)) for v in self.gne_device_records]

        if not isinstance(self.induction_machine_records, list):
            self.induction_machine_records = [self.induction_machine_records] if self.induction_machine_records is not None else []
        self.induction_machine_records = [v if isinstance(v, InductionMachineRecord) else InductionMachineRecord(**as_dict(v)) for v in self.induction_machine_records]

        self._normalize_inlined_as_list(slot_name="substation_records", slot_type=SubstationRecord, key_name="substation_number", keyed=True)

        if not isinstance(self.substation_node_records, list):
            self.substation_node_records = [self.substation_node_records] if self.substation_node_records is not None else []
        self.substation_node_records = [v if isinstance(v, SubstationNodeRecord) else SubstationNodeRecord(**as_dict(v)) for v in self.substation_node_records]

        if not isinstance(self.station_switching_device_records, list):
            self.station_switching_device_records = [self.station_switching_device_records] if self.station_switching_device_records is not None else []
        self.station_switching_device_records = [v if isinstance(v, StationSwitchingDeviceRecord) else StationSwitchingDeviceRecord(**as_dict(v)) for v in self.station_switching_device_records]

        if not isinstance(self.equipment_terminal_records, list):
            self.equipment_terminal_records = [self.equipment_terminal_records] if self.equipment_terminal_records is not None else []
        self.equipment_terminal_records = [v if isinstance(v, EquipmentTerminalRecord) else EquipmentTerminalRecord(**as_dict(v)) for v in self.equipment_terminal_records]

        if not isinstance(self.multi_terminal_converter_records, list):
            self.multi_terminal_converter_records = [self.multi_terminal_converter_records] if self.multi_terminal_converter_records is not None else []
        self.multi_terminal_converter_records = [v if isinstance(v, MultiTerminalConverterRecord) else MultiTerminalConverterRecord(**as_dict(v)) for v in self.multi_terminal_converter_records]

        if not isinstance(self.multi_terminal_dc_bus_records, list):
            self.multi_terminal_dc_bus_records = [self.multi_terminal_dc_bus_records] if self.multi_terminal_dc_bus_records is not None else []
        self.multi_terminal_dc_bus_records = [v if isinstance(v, MultiTerminalDCBusRecord) else MultiTerminalDCBusRecord(**as_dict(v)) for v in self.multi_terminal_dc_bus_records]

        if not isinstance(self.multi_terminal_dc_link_records, list):
            self.multi_terminal_dc_link_records = [self.multi_terminal_dc_link_records] if self.multi_terminal_dc_link_records is not None else []
        self.multi_terminal_dc_link_records = [v if isinstance(v, MultiTerminalDCLinkRecord) else MultiTerminalDCLinkRecord(**as_dict(v)) for v in self.multi_terminal_dc_link_records]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class CaseIdentificationRecord(YAMLRoot):
    """
    Case identification and system-wide data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["CaseIdentificationRecord"]
    class_class_curie: ClassVar[str] = "raw:CaseIdentificationRecord"
    class_name: ClassVar[str] = "CaseIdentificationRecord"
    class_model_uri: ClassVar[URIRef] = RAW.CaseIdentificationRecord

    new_case_flag: Union[int, CaseIdentificationRecordNewCaseFlag] = None
    system_base_mva: Optional[float] = None
    revision: Optional[float] = None
    transformer_ratings_units: Optional[int] = None
    branch_ratings_units: Optional[int] = None
    system_base_frequency: Optional[float] = None
    titles: Optional[Union[str, list[str]]] = empty_list()
    general: Optional[str] = None
    gauss: Optional[str] = None
    newton: Optional[str] = None
    adjust: Optional[str] = None
    tysl: Optional[str] = None
    solver: Optional[str] = None
    ratings: Optional[Union[dict[Union[int, RatingRecordRatingSetNumber], Union[dict, "RatingRecord"]], list[Union[dict, "RatingRecord"]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.new_case_flag):
            self.MissingRequiredField("new_case_flag")
        if not isinstance(self.new_case_flag, CaseIdentificationRecordNewCaseFlag):
            self.new_case_flag = CaseIdentificationRecordNewCaseFlag(self.new_case_flag)

        if self.system_base_mva is not None and not isinstance(self.system_base_mva, float):
            self.system_base_mva = float(self.system_base_mva)

        if self.revision is not None and not isinstance(self.revision, float):
            self.revision = float(self.revision)

        if self.transformer_ratings_units is not None and not isinstance(self.transformer_ratings_units, int):
            self.transformer_ratings_units = int(self.transformer_ratings_units)

        if self.branch_ratings_units is not None and not isinstance(self.branch_ratings_units, int):
            self.branch_ratings_units = int(self.branch_ratings_units)

        if self.system_base_frequency is not None and not isinstance(self.system_base_frequency, float):
            self.system_base_frequency = float(self.system_base_frequency)

        if not isinstance(self.titles, list):
            self.titles = [self.titles] if self.titles is not None else []
        self.titles = [v if isinstance(v, str) else str(v) for v in self.titles]

        if self.general is not None and not isinstance(self.general, str):
            self.general = str(self.general)

        if self.gauss is not None and not isinstance(self.gauss, str):
            self.gauss = str(self.gauss)

        if self.newton is not None and not isinstance(self.newton, str):
            self.newton = str(self.newton)

        if self.adjust is not None and not isinstance(self.adjust, str):
            self.adjust = str(self.adjust)

        if self.tysl is not None and not isinstance(self.tysl, str):
            self.tysl = str(self.tysl)

        if self.solver is not None and not isinstance(self.solver, str):
            self.solver = str(self.solver)

        self._normalize_inlined_as_list(slot_name="ratings", slot_type=RatingRecord, key_name="rating_set_number", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class RatingRecord(YAMLRoot):
    """
    RATING record naming one rating set (1-12)
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["RatingRecord"]
    class_class_curie: ClassVar[str] = "raw:RatingRecord"
    class_name: ClassVar[str] = "RatingRecord"
    class_model_uri: ClassVar[URIRef] = RAW.RatingRecord

    rating_set_number: Union[int, RatingRecordRatingSetNumber] = None
    rating_name: str = None
    rating_description: str = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.rating_set_number):
            self.MissingRequiredField("rating_set_number")
        if not isinstance(self.rating_set_number, RatingRecordRatingSetNumber):
            self.rating_set_number = RatingRecordRatingSetNumber(self.rating_set_number)

        if self._is_empty(self.rating_name):
            self.MissingRequiredField("rating_name")
        if not isinstance(self.rating_name, str):
            self.rating_name = str(self.rating_name)

        if self._is_empty(self.rating_description):
            self.MissingRequiredField("rating_description")
        if not isinstance(self.rating_description, str):
            self.rating_description = str(self.rating_description)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class BusRecord(YAMLRoot):
    """
    Bus data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["BusRecord"]
    class_class_curie: ClassVar[str] = "raw:BusRecord"
    class_name: ClassVar[str] = "BusRecord"
    class_model_uri: ClassVar[URIRef] = RAW.BusRecord

    bus_number: Union[int, BusRecordBusNumber] = None
    name: Optional[str] = None
    base_voltage: Optional[float] = None
    bus_type: Optional[int] = None
    area: Optional[int] = None
    zone: Optional[int] = None
    owner: Optional[int] = None
    voltage_magnitude: Optional[float] = None
    voltage_angle: Optional[float] = None
    normal_voltage_magnitude_high_limit: Optional[float] = None
    normal_voltage_magnitude_low_limit: Optional[float] = None
    emergency_voltage_magnitude_high_limit: Optional[float] = None
    emergency_voltage_magnitude_low_limit: Optional[float] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.bus_number):
            self.MissingRequiredField("bus_number")
        if not isinstance(self.bus_number, BusRecordBusNumber):
            self.bus_number = BusRecordBusNumber(self.bus_number)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.base_voltage is not None and not isinstance(self.base_voltage, float):
            self.base_voltage = float(self.base_voltage)

        if self.bus_type is not None and not isinstance(self.bus_type, int):
            self.bus_type = int(self.bus_type)

        if self.area is not None and not isinstance(self.area, int):
            self.area = int(self.area)

        if self.zone is not None and not isinstance(self.zone, int):
            self.zone = int(self.zone)

        if self.owner is not None and not isinstance(self.owner, int):
            self.owner = int(self.owner)

        if self.voltage_magnitude is not None and not isinstance(self.voltage_magnitude, float):
            self.voltage_magnitude = float(self.voltage_magnitude)

        if self.voltage_angle is not None and not isinstance(self.voltage_angle, float):
            self.voltage_angle = float(self.voltage_angle)

        if self.normal_voltage_magnitude_high_limit is not None and not isinstance(self.normal_voltage_magnitude_high_limit, float):
            self.normal_voltage_magnitude_high_limit = float(self.normal_voltage_magnitude_high_limit)

        if self.normal_voltage_magnitude_low_limit is not None and not isinstance(self.normal_voltage_magnitude_low_limit, float):
            self.normal_voltage_magnitude_low_limit = float(self.normal_voltage_magnitude_low_limit)

        if self.emergency_voltage_magnitude_high_limit is not None and not isinstance(self.emergency_voltage_magnitude_high_limit, float):
            self.emergency_voltage_magnitude_high_limit = float(self.emergency_voltage_magnitude_high_limit)

        if self.emergency_voltage_magnitude_low_limit is not None and not isinstance(self.emergency_voltage_magnitude_low_limit, float):
            self.emergency_voltage_magnitude_low_limit = float(self.emergency_voltage_magnitude_low_limit)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class LoadRecord(YAMLRoot):
    """
    Load data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["LoadRecord"]
    class_class_curie: ClassVar[str] = "raw:LoadRecord"
    class_name: ClassVar[str] = "LoadRecord"
    class_model_uri: ClassVar[URIRef] = RAW.LoadRecord

    bus_number: int = None
    load_id: Optional[str] = None
    status: Optional[int] = None
    area: Optional[int] = None
    zone: Optional[int] = None
    constant_real_power: Optional[float] = None
    constant_imag_power: Optional[float] = None
    constant_current_real_power: Optional[float] = None
    constant_current_imag_power: Optional[float] = None
    constant_admittance_real_power: Optional[float] = None
    constant_admittance_imag_power: Optional[float] = None
    owner: Optional[int] = None
    scale: Optional[int] = None
    interruptible: Optional[int] = None
    dgenp: Optional[float] = None
    dgenq: Optional[float] = None
    dgenf: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.bus_number):
            self.MissingRequiredField("bus_number")
        if not isinstance(self.bus_number, int):
            self.bus_number = int(self.bus_number)

        if self.load_id is not None and not isinstance(self.load_id, str):
            self.load_id = str(self.load_id)

        if self.status is not None and not isinstance(self.status, int):
            self.status = int(self.status)

        if self.area is not None and not isinstance(self.area, int):
            self.area = int(self.area)

        if self.zone is not None and not isinstance(self.zone, int):
            self.zone = int(self.zone)

        if self.constant_real_power is not None and not isinstance(self.constant_real_power, float):
            self.constant_real_power = float(self.constant_real_power)

        if self.constant_imag_power is not None and not isinstance(self.constant_imag_power, float):
            self.constant_imag_power = float(self.constant_imag_power)

        if self.constant_current_real_power is not None and not isinstance(self.constant_current_real_power, float):
            self.constant_current_real_power = float(self.constant_current_real_power)

        if self.constant_current_imag_power is not None and not isinstance(self.constant_current_imag_power, float):
            self.constant_current_imag_power = float(self.constant_current_imag_power)

        if self.constant_admittance_real_power is not None and not isinstance(self.constant_admittance_real_power, float):
            self.constant_admittance_real_power = float(self.constant_admittance_real_power)

        if self.constant_admittance_imag_power is not None and not isinstance(self.constant_admittance_imag_power, float):
            self.constant_admittance_imag_power = float(self.constant_admittance_imag_power)

        if self.owner is not None and not isinstance(self.owner, int):
            self.owner = int(self.owner)

        if self.scale is not None and not isinstance(self.scale, int):
            self.scale = int(self.scale)

        if self.interruptible is not None and not isinstance(self.interruptible, int):
            self.interruptible = int(self.interruptible)

        if self.dgenp is not None and not isinstance(self.dgenp, float):
            self.dgenp = float(self.dgenp)

        if self.dgenq is not None and not isinstance(self.dgenq, float):
            self.dgenq = float(self.dgenq)

        if self.dgenf is not None and not isinstance(self.dgenf, int):
            self.dgenf = int(self.dgenf)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class FixedShuntRecord(YAMLRoot):
    """
    Fixed bus shunt data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["FixedShuntRecord"]
    class_class_curie: ClassVar[str] = "raw:FixedShuntRecord"
    class_name: ClassVar[str] = "FixedShuntRecord"
    class_model_uri: ClassVar[URIRef] = RAW.FixedShuntRecord

    bus_number: int = None
    shunt_id: Optional[str] = None
    status: Optional[int] = None
    gl: Optional[float] = None
    bl: Optional[float] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.bus_number):
            self.MissingRequiredField("bus_number")
        if not isinstance(self.bus_number, int):
            self.bus_number = int(self.bus_number)

        if self.shunt_id is not None and not isinstance(self.shunt_id, str):
            self.shunt_id = str(self.shunt_id)

        if self.status is not None and not isinstance(self.status, int):
            self.status = int(self.status)

        if self.gl is not None and not isinstance(self.gl, float):
            self.gl = float(self.gl)

        if self.bl is not None and not isinstance(self.bl, float):
            self.bl = float(self.bl)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class GeneratorRecord(YAMLRoot):
    """
    Generator data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["GeneratorRecord"]
    class_class_curie: ClassVar[str] = "raw:GeneratorRecord"
    class_name: ClassVar[str] = "GeneratorRecord"
    class_model_uri: ClassVar[URIRef] = RAW.GeneratorRecord

    bus_number: int = None
    gen_id: Optional[str] = None
    p_output: Optional[float] = None
    q_output: Optional[float] = None
    max_q_output: Optional[float] = None
    min_q_output: Optional[float] = None
    regulated_voltage_setpoint: Optional[float] = None
    regulated_bus_number: Optional[int] = None
    rated_mva: Optional[float] = None
    zr: Optional[float] = None
    zx: Optional[float] = None
    rt: Optional[float] = None
    xt: Optional[float] = None
    gtap: Optional[float] = None
    status: Optional[int] = None
    rmpct: Optional[float] = None
    max_p_output: Optional[float] = None
    min_p_output: Optional[float] = None
    o1: Optional[int] = None
    f1: Optional[float] = None
    o2: Optional[int] = None
    f2: Optional[float] = None
    o3: Optional[int] = None
    f3: Optional[float] = None
    o4: Optional[int] = None
    f4: Optional[float] = None
    wmod: Optional[int] = None
    wpf: Optional[float] = None
    nreg: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.bus_number):
            self.MissingRequiredField("bus_number")
        if not isinstance(self.bus_number, int):
            self.bus_number = int(self.bus_number)

        if self.gen_id is not None and not isinstance(self.gen_id, str):
            self.gen_id = str(self.gen_id)

        if self.p_output is not None and not isinstance(self.p_output, float):
            self.p_output = float(self.p_output)

        if self.q_output is not None and not isinstance(self.q_output, float):
            self.q_output = float(self.q_output)

        if self.max_q_output is not None and not isinstance(self.max_q_output, float):
            self.max_q_output = float(self.max_q_output)

        if self.min_q_output is not None and not isinstance(self.min_q_output, float):
            self.min_q_output = float(self.min_q_output)

        if self.regulated_voltage_setpoint is not None and not isinstance(self.regulated_voltage_setpoint, float):
            self.regulated_voltage_setpoint = float(self.regulated_voltage_setpoint)

        if self.regulated_bus_number is not None and not isinstance(self.regulated_bus_number, int):
            self.regulated_bus_number = int(self.regulated_bus_number)

        if self.rated_mva is not None and not isinstance(self.rated_mva, float):
            self.rated_mva = float(self.rated_mva)

        if self.zr is not None and not isinstance(self.zr, float):
            self.zr = float(self.zr)

        if self.zx is not None and not isinstance(self.zx, float):
            self.zx = float(self.zx)

        if self.rt is not None and not isinstance(self.rt, float):
            self.rt = float(self.rt)

        if self.xt is not None and not isinstance(self.xt, float):
            self.xt = float(self.xt)

        if self.gtap is not None and not isinstance(self.gtap, float):
            self.gtap = float(self.gtap)

        if self.status is not None and not isinstance(self.status, int):
            self.status = int(self.status)

        if self.rmpct is not None and not isinstance(self.rmpct, float):
            self.rmpct = float(self.rmpct)

        if self.max_p_output is not None and not isinstance(self.max_p_output, float):
            self.max_p_output = float(self.max_p_output)

        if self.min_p_output is not None and not isinstance(self.min_p_output, float):
            self.min_p_output = float(self.min_p_output)

        if self.o1 is not None and not isinstance(self.o1, int):
            self.o1 = int(self.o1)

        if self.f1 is not None and not isinstance(self.f1, float):
            self.f1 = float(self.f1)

        if self.o2 is not None and not isinstance(self.o2, int):
            self.o2 = int(self.o2)

        if self.f2 is not None and not isinstance(self.f2, float):
            self.f2 = float(self.f2)

        if self.o3 is not None and not isinstance(self.o3, int):
            self.o3 = int(self.o3)

        if self.f3 is not None and not isinstance(self.f3, float):
            self.f3 = float(self.f3)

        if self.o4 is not None and not isinstance(self.o4, int):
            self.o4 = int(self.o4)

        if self.f4 is not None and not isinstance(self.f4, float):
            self.f4 = float(self.f4)

        if self.wmod is not None and not isinstance(self.wmod, int):
            self.wmod = int(self.wmod)

        if self.wpf is not None and not isinstance(self.wpf, float):
            self.wpf = float(self.wpf)

        if self.nreg is not None and not isinstance(self.nreg, int):
            self.nreg = int(self.nreg)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class BranchRecord(YAMLRoot):
    """
    Non-transformer branch (line) data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["BranchRecord"]
    class_class_curie: ClassVar[str] = "raw:BranchRecord"
    class_name: ClassVar[str] = "BranchRecord"
    class_model_uri: ClassVar[URIRef] = RAW.BranchRecord

    from_bus_number: int = None
    to_bus_number: int = None
    r: float = None
    x: float = None
    circuit: Optional[str] = None
    b: Optional[float] = None
    name: Optional[str] = None
    ratings: Optional[Union[float, list[float]]] = empty_list()
    g_from: Optional[float] = None
    b_from: Optional[float] = None
    g_to: Optional[float] = None
    b_to: Optional[float] = None
    status: Optional[int] = None
    metered_end: Optional[int] = None
    length: Optional[float] = None
    o1: Optional[int] = None
    f1: Optional[float] = None
    o2: Optional[int] = None
    f2: Optional[float] = None
    o3: Optional[int] = None
    f3: Optional[float] = None
    o4: Optional[int] = None
    f4: Optional[float] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.from_bus_number):
            self.MissingRequiredField("from_bus_number")
        if not isinstance(self.from_bus_number, int):
            self.from_bus_number = int(self.from_bus_number)

        if self._is_empty(self.to_bus_number):
            self.MissingRequiredField("to_bus_number")
        if not isinstance(self.to_bus_number, int):
            self.to_bus_number = int(self.to_bus_number)

        if self._is_empty(self.r):
            self.MissingRequiredField("r")
        if not isinstance(self.r, float):
            self.r = float(self.r)

        if self._is_empty(self.x):
            self.MissingRequiredField("x")
        if not isinstance(self.x, float):
            self.x = float(self.x)

        if self.circuit is not None and not isinstance(self.circuit, str):
            self.circuit = str(self.circuit)

        if self.b is not None and not isinstance(self.b, float):
            self.b = float(self.b)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if not isinstance(self.ratings, list):
            self.ratings = [self.ratings] if self.ratings is not None else []
        self.ratings = [v if isinstance(v, float) else float(v) for v in self.ratings]

        if self.g_from is not None and not isinstance(self.g_from, float):
            self.g_from = float(self.g_from)

        if self.b_from is not None and not isinstance(self.b_from, float):
            self.b_from = float(self.b_from)

        if self.g_to is not None and not isinstance(self.g_to, float):
            self.g_to = float(self.g_to)

        if self.b_to is not None and not isinstance(self.b_to, float):
            self.b_to = float(self.b_to)

        if self.status is not None and not isinstance(self.status, int):
            self.status = int(self.status)

        if self.metered_end is not None and not isinstance(self.metered_end, int):
            self.metered_end = int(self.metered_end)

        if self.length is not None and not isinstance(self.length, float):
            self.length = float(self.length)

        if self.o1 is not None and not isinstance(self.o1, int):
            self.o1 = int(self.o1)

        if self.f1 is not None and not isinstance(self.f1, float):
            self.f1 = float(self.f1)

        if self.o2 is not None and not isinstance(self.o2, int):
            self.o2 = int(self.o2)

        if self.f2 is not None and not isinstance(self.f2, float):
            self.f2 = float(self.f2)

        if self.o3 is not None and not isinstance(self.o3, int):
            self.o3 = int(self.o3)

        if self.f3 is not None and not isinstance(self.f3, float):
            self.f3 = float(self.f3)

        if self.o4 is not None and not isinstance(self.o4, int):
            self.o4 = int(self.o4)

        if self.f4 is not None and not isinstance(self.f4, float):
            self.f4 = float(self.f4)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class SwitchRecord(YAMLRoot):
    """
    System switching device data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["SwitchRecord"]
    class_class_curie: ClassVar[str] = "raw:SwitchRecord"
    class_name: ClassVar[str] = "SwitchRecord"
    class_model_uri: ClassVar[URIRef] = RAW.SwitchRecord

    from_bus_number: int = None
    to_bus_number: int = None
    circuit: Optional[str] = None
    x: Optional[float] = None
    ratings: Optional[Union[float, list[float]]] = empty_list()
    status: Optional[int] = None
    nstat: Optional[int] = None
    metered_end: Optional[int] = None
    stype: Optional[int] = None
    name: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.from_bus_number):
            self.MissingRequiredField("from_bus_number")
        if not isinstance(self.from_bus_number, int):
            self.from_bus_number = int(self.from_bus_number)

        if self._is_empty(self.to_bus_number):
            self.MissingRequiredField("to_bus_number")
        if not isinstance(self.to_bus_number, int):
            self.to_bus_number = int(self.to_bus_number)

        if self.circuit is not None and not isinstance(self.circuit, str):
            self.circuit = str(self.circuit)

        if self.x is not None and not isinstance(self.x, float):
            self.x = float(self.x)

        if not isinstance(self.ratings, list):
            self.ratings = [self.ratings] if self.ratings is not None else []
        self.ratings = [v if isinstance(v, float) else float(v) for v in self.ratings]

        if self.status is not None and not isinstance(self.status, int):
            self.status = int(self.status)

        if self.nstat is not None and not isinstance(self.nstat, int):
            self.nstat = int(self.nstat)

        if self.metered_end is not None and not isinstance(self.metered_end, int):
            self.metered_end = int(self.metered_end)

        if self.stype is not None and not isinstance(self.stype, int):
            self.stype = int(self.stype)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class TransformerRecord(YAMLRoot):
    """
    Transformer data record (2 or 3 winding).

    Multi-line format:
    - Line 1: Basic identification and ownership
    - Line 2: Impedance data
    - Line 3: Winding 1 data
    - Line 4: Winding 2 data
    - Line 5: Winding 3 data (only if K != 0)

    Maps to CIM: cim.PowerTransformer, cim.PowerTransformerEnd
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["TransformerRecord"]
    class_class_curie: ClassVar[str] = "raw:TransformerRecord"
    class_name: ClassVar[str] = "TransformerRecord"
    class_model_uri: ClassVar[URIRef] = RAW.TransformerRecord

    i: int = None
    j: int = None
    x1_2: float = None
    k: Optional[int] = None
    circuit: Optional[str] = None
    cw: Optional[int] = None
    cz: Optional[int] = None
    cm: Optional[int] = None
    mag1: Optional[float] = None
    mag2: Optional[float] = None
    nmetr: Optional[int] = None
    name: Optional[str] = None
    status: Optional[int] = None
    o1: Optional[int] = None
    f1: Optional[float] = None
    o2: Optional[int] = None
    f2: Optional[float] = None
    o3: Optional[int] = None
    f3: Optional[float] = None
    o4: Optional[int] = None
    f4: Optional[float] = None
    vecgrp: Optional[str] = None
    zcod: Optional[int] = None
    r1_2: Optional[float] = None
    sbase1_2: Optional[float] = None
    r2_3: Optional[float] = None
    x2_3: Optional[float] = None
    sbase2_3: Optional[float] = None
    r3_1: Optional[float] = None
    x3_1: Optional[float] = None
    sbase3_1: Optional[float] = None
    vmstar: Optional[float] = None
    anstar: Optional[float] = None
    windv1: Optional[float] = None
    nomv1: Optional[float] = None
    ang1: Optional[float] = None
    rate1_1: Optional[float] = None
    rate1_2: Optional[float] = None
    rate1_3: Optional[float] = None
    rate1_4: Optional[float] = None
    rate1_5: Optional[float] = None
    rate1_6: Optional[float] = None
    rate1_7: Optional[float] = None
    rate1_8: Optional[float] = None
    rate1_9: Optional[float] = None
    rate1_10: Optional[float] = None
    rate1_11: Optional[float] = None
    rate1_12: Optional[float] = None
    cod1: Optional[int] = None
    cont1: Optional[int] = None
    rma1: Optional[float] = None
    rmi1: Optional[float] = None
    vma1: Optional[float] = None
    vmi1: Optional[float] = None
    ntp1: Optional[int] = None
    tab1: Optional[int] = None
    cr1: Optional[float] = None
    cx1: Optional[float] = None
    cnxa1: Optional[float] = None
    nod1: Optional[int] = None
    windv2: Optional[float] = None
    nomv2: Optional[float] = None
    ang2: Optional[float] = None
    rate2_1: Optional[float] = None
    rate2_2: Optional[float] = None
    rate2_3: Optional[float] = None
    rate2_4: Optional[float] = None
    rate2_5: Optional[float] = None
    rate2_6: Optional[float] = None
    rate2_7: Optional[float] = None
    rate2_8: Optional[float] = None
    rate2_9: Optional[float] = None
    rate2_10: Optional[float] = None
    rate2_11: Optional[float] = None
    rate2_12: Optional[float] = None
    cod2: Optional[int] = None
    cont2: Optional[int] = None
    rma2: Optional[float] = None
    rmi2: Optional[float] = None
    vma2: Optional[float] = None
    vmi2: Optional[float] = None
    ntp2: Optional[int] = None
    tab2: Optional[int] = None
    cr2: Optional[float] = None
    cx2: Optional[float] = None
    cnxa2: Optional[float] = None
    nod2: Optional[int] = None
    windv3: Optional[float] = None
    nomv3: Optional[float] = None
    ang3: Optional[float] = None
    rate3_1: Optional[float] = None
    rate3_2: Optional[float] = None
    rate3_3: Optional[float] = None
    rate3_4: Optional[float] = None
    rate3_5: Optional[float] = None
    rate3_6: Optional[float] = None
    rate3_7: Optional[float] = None
    rate3_8: Optional[float] = None
    rate3_9: Optional[float] = None
    rate3_10: Optional[float] = None
    rate3_11: Optional[float] = None
    rate3_12: Optional[float] = None
    cod3: Optional[int] = None
    cont3: Optional[int] = None
    rma3: Optional[float] = None
    rmi3: Optional[float] = None
    vma3: Optional[float] = None
    vmi3: Optional[float] = None
    ntp3: Optional[int] = None
    tab3: Optional[int] = None
    cr3: Optional[float] = None
    cx3: Optional[float] = None
    cnxa3: Optional[float] = None
    nod3: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.i):
            self.MissingRequiredField("i")
        if not isinstance(self.i, int):
            self.i = int(self.i)

        if self._is_empty(self.j):
            self.MissingRequiredField("j")
        if not isinstance(self.j, int):
            self.j = int(self.j)

        if self._is_empty(self.x1_2):
            self.MissingRequiredField("x1_2")
        if not isinstance(self.x1_2, float):
            self.x1_2 = float(self.x1_2)

        if self.k is not None and not isinstance(self.k, int):
            self.k = int(self.k)

        if self.circuit is not None and not isinstance(self.circuit, str):
            self.circuit = str(self.circuit)

        if self.cw is not None and not isinstance(self.cw, int):
            self.cw = int(self.cw)

        if self.cz is not None and not isinstance(self.cz, int):
            self.cz = int(self.cz)

        if self.cm is not None and not isinstance(self.cm, int):
            self.cm = int(self.cm)

        if self.mag1 is not None and not isinstance(self.mag1, float):
            self.mag1 = float(self.mag1)

        if self.mag2 is not None and not isinstance(self.mag2, float):
            self.mag2 = float(self.mag2)

        if self.nmetr is not None and not isinstance(self.nmetr, int):
            self.nmetr = int(self.nmetr)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.status is not None and not isinstance(self.status, int):
            self.status = int(self.status)

        if self.o1 is not None and not isinstance(self.o1, int):
            self.o1 = int(self.o1)

        if self.f1 is not None and not isinstance(self.f1, float):
            self.f1 = float(self.f1)

        if self.o2 is not None and not isinstance(self.o2, int):
            self.o2 = int(self.o2)

        if self.f2 is not None and not isinstance(self.f2, float):
            self.f2 = float(self.f2)

        if self.o3 is not None and not isinstance(self.o3, int):
            self.o3 = int(self.o3)

        if self.f3 is not None and not isinstance(self.f3, float):
            self.f3 = float(self.f3)

        if self.o4 is not None and not isinstance(self.o4, int):
            self.o4 = int(self.o4)

        if self.f4 is not None and not isinstance(self.f4, float):
            self.f4 = float(self.f4)

        if self.vecgrp is not None and not isinstance(self.vecgrp, str):
            self.vecgrp = str(self.vecgrp)

        if self.zcod is not None and not isinstance(self.zcod, int):
            self.zcod = int(self.zcod)

        if self.r1_2 is not None and not isinstance(self.r1_2, float):
            self.r1_2 = float(self.r1_2)

        if self.sbase1_2 is not None and not isinstance(self.sbase1_2, float):
            self.sbase1_2 = float(self.sbase1_2)

        if self.r2_3 is not None and not isinstance(self.r2_3, float):
            self.r2_3 = float(self.r2_3)

        if self.x2_3 is not None and not isinstance(self.x2_3, float):
            self.x2_3 = float(self.x2_3)

        if self.sbase2_3 is not None and not isinstance(self.sbase2_3, float):
            self.sbase2_3 = float(self.sbase2_3)

        if self.r3_1 is not None and not isinstance(self.r3_1, float):
            self.r3_1 = float(self.r3_1)

        if self.x3_1 is not None and not isinstance(self.x3_1, float):
            self.x3_1 = float(self.x3_1)

        if self.sbase3_1 is not None and not isinstance(self.sbase3_1, float):
            self.sbase3_1 = float(self.sbase3_1)

        if self.vmstar is not None and not isinstance(self.vmstar, float):
            self.vmstar = float(self.vmstar)

        if self.anstar is not None and not isinstance(self.anstar, float):
            self.anstar = float(self.anstar)

        if self.windv1 is not None and not isinstance(self.windv1, float):
            self.windv1 = float(self.windv1)

        if self.nomv1 is not None and not isinstance(self.nomv1, float):
            self.nomv1 = float(self.nomv1)

        if self.ang1 is not None and not isinstance(self.ang1, float):
            self.ang1 = float(self.ang1)

        if self.rate1_1 is not None and not isinstance(self.rate1_1, float):
            self.rate1_1 = float(self.rate1_1)

        if self.rate1_2 is not None and not isinstance(self.rate1_2, float):
            self.rate1_2 = float(self.rate1_2)

        if self.rate1_3 is not None and not isinstance(self.rate1_3, float):
            self.rate1_3 = float(self.rate1_3)

        if self.rate1_4 is not None and not isinstance(self.rate1_4, float):
            self.rate1_4 = float(self.rate1_4)

        if self.rate1_5 is not None and not isinstance(self.rate1_5, float):
            self.rate1_5 = float(self.rate1_5)

        if self.rate1_6 is not None and not isinstance(self.rate1_6, float):
            self.rate1_6 = float(self.rate1_6)

        if self.rate1_7 is not None and not isinstance(self.rate1_7, float):
            self.rate1_7 = float(self.rate1_7)

        if self.rate1_8 is not None and not isinstance(self.rate1_8, float):
            self.rate1_8 = float(self.rate1_8)

        if self.rate1_9 is not None and not isinstance(self.rate1_9, float):
            self.rate1_9 = float(self.rate1_9)

        if self.rate1_10 is not None and not isinstance(self.rate1_10, float):
            self.rate1_10 = float(self.rate1_10)

        if self.rate1_11 is not None and not isinstance(self.rate1_11, float):
            self.rate1_11 = float(self.rate1_11)

        if self.rate1_12 is not None and not isinstance(self.rate1_12, float):
            self.rate1_12 = float(self.rate1_12)

        if self.cod1 is not None and not isinstance(self.cod1, int):
            self.cod1 = int(self.cod1)

        if self.cont1 is not None and not isinstance(self.cont1, int):
            self.cont1 = int(self.cont1)

        if self.rma1 is not None and not isinstance(self.rma1, float):
            self.rma1 = float(self.rma1)

        if self.rmi1 is not None and not isinstance(self.rmi1, float):
            self.rmi1 = float(self.rmi1)

        if self.vma1 is not None and not isinstance(self.vma1, float):
            self.vma1 = float(self.vma1)

        if self.vmi1 is not None and not isinstance(self.vmi1, float):
            self.vmi1 = float(self.vmi1)

        if self.ntp1 is not None and not isinstance(self.ntp1, int):
            self.ntp1 = int(self.ntp1)

        if self.tab1 is not None and not isinstance(self.tab1, int):
            self.tab1 = int(self.tab1)

        if self.cr1 is not None and not isinstance(self.cr1, float):
            self.cr1 = float(self.cr1)

        if self.cx1 is not None and not isinstance(self.cx1, float):
            self.cx1 = float(self.cx1)

        if self.cnxa1 is not None and not isinstance(self.cnxa1, float):
            self.cnxa1 = float(self.cnxa1)

        if self.nod1 is not None and not isinstance(self.nod1, int):
            self.nod1 = int(self.nod1)

        if self.windv2 is not None and not isinstance(self.windv2, float):
            self.windv2 = float(self.windv2)

        if self.nomv2 is not None and not isinstance(self.nomv2, float):
            self.nomv2 = float(self.nomv2)

        if self.ang2 is not None and not isinstance(self.ang2, float):
            self.ang2 = float(self.ang2)

        if self.rate2_1 is not None and not isinstance(self.rate2_1, float):
            self.rate2_1 = float(self.rate2_1)

        if self.rate2_2 is not None and not isinstance(self.rate2_2, float):
            self.rate2_2 = float(self.rate2_2)

        if self.rate2_3 is not None and not isinstance(self.rate2_3, float):
            self.rate2_3 = float(self.rate2_3)

        if self.rate2_4 is not None and not isinstance(self.rate2_4, float):
            self.rate2_4 = float(self.rate2_4)

        if self.rate2_5 is not None and not isinstance(self.rate2_5, float):
            self.rate2_5 = float(self.rate2_5)

        if self.rate2_6 is not None and not isinstance(self.rate2_6, float):
            self.rate2_6 = float(self.rate2_6)

        if self.rate2_7 is not None and not isinstance(self.rate2_7, float):
            self.rate2_7 = float(self.rate2_7)

        if self.rate2_8 is not None and not isinstance(self.rate2_8, float):
            self.rate2_8 = float(self.rate2_8)

        if self.rate2_9 is not None and not isinstance(self.rate2_9, float):
            self.rate2_9 = float(self.rate2_9)

        if self.rate2_10 is not None and not isinstance(self.rate2_10, float):
            self.rate2_10 = float(self.rate2_10)

        if self.rate2_11 is not None and not isinstance(self.rate2_11, float):
            self.rate2_11 = float(self.rate2_11)

        if self.rate2_12 is not None and not isinstance(self.rate2_12, float):
            self.rate2_12 = float(self.rate2_12)

        if self.cod2 is not None and not isinstance(self.cod2, int):
            self.cod2 = int(self.cod2)

        if self.cont2 is not None and not isinstance(self.cont2, int):
            self.cont2 = int(self.cont2)

        if self.rma2 is not None and not isinstance(self.rma2, float):
            self.rma2 = float(self.rma2)

        if self.rmi2 is not None and not isinstance(self.rmi2, float):
            self.rmi2 = float(self.rmi2)

        if self.vma2 is not None and not isinstance(self.vma2, float):
            self.vma2 = float(self.vma2)

        if self.vmi2 is not None and not isinstance(self.vmi2, float):
            self.vmi2 = float(self.vmi2)

        if self.ntp2 is not None and not isinstance(self.ntp2, int):
            self.ntp2 = int(self.ntp2)

        if self.tab2 is not None and not isinstance(self.tab2, int):
            self.tab2 = int(self.tab2)

        if self.cr2 is not None and not isinstance(self.cr2, float):
            self.cr2 = float(self.cr2)

        if self.cx2 is not None and not isinstance(self.cx2, float):
            self.cx2 = float(self.cx2)

        if self.cnxa2 is not None and not isinstance(self.cnxa2, float):
            self.cnxa2 = float(self.cnxa2)

        if self.nod2 is not None and not isinstance(self.nod2, int):
            self.nod2 = int(self.nod2)

        if self.windv3 is not None and not isinstance(self.windv3, float):
            self.windv3 = float(self.windv3)

        if self.nomv3 is not None and not isinstance(self.nomv3, float):
            self.nomv3 = float(self.nomv3)

        if self.ang3 is not None and not isinstance(self.ang3, float):
            self.ang3 = float(self.ang3)

        if self.rate3_1 is not None and not isinstance(self.rate3_1, float):
            self.rate3_1 = float(self.rate3_1)

        if self.rate3_2 is not None and not isinstance(self.rate3_2, float):
            self.rate3_2 = float(self.rate3_2)

        if self.rate3_3 is not None and not isinstance(self.rate3_3, float):
            self.rate3_3 = float(self.rate3_3)

        if self.rate3_4 is not None and not isinstance(self.rate3_4, float):
            self.rate3_4 = float(self.rate3_4)

        if self.rate3_5 is not None and not isinstance(self.rate3_5, float):
            self.rate3_5 = float(self.rate3_5)

        if self.rate3_6 is not None and not isinstance(self.rate3_6, float):
            self.rate3_6 = float(self.rate3_6)

        if self.rate3_7 is not None and not isinstance(self.rate3_7, float):
            self.rate3_7 = float(self.rate3_7)

        if self.rate3_8 is not None and not isinstance(self.rate3_8, float):
            self.rate3_8 = float(self.rate3_8)

        if self.rate3_9 is not None and not isinstance(self.rate3_9, float):
            self.rate3_9 = float(self.rate3_9)

        if self.rate3_10 is not None and not isinstance(self.rate3_10, float):
            self.rate3_10 = float(self.rate3_10)

        if self.rate3_11 is not None and not isinstance(self.rate3_11, float):
            self.rate3_11 = float(self.rate3_11)

        if self.rate3_12 is not None and not isinstance(self.rate3_12, float):
            self.rate3_12 = float(self.rate3_12)

        if self.cod3 is not None and not isinstance(self.cod3, int):
            self.cod3 = int(self.cod3)

        if self.cont3 is not None and not isinstance(self.cont3, int):
            self.cont3 = int(self.cont3)

        if self.rma3 is not None and not isinstance(self.rma3, float):
            self.rma3 = float(self.rma3)

        if self.rmi3 is not None and not isinstance(self.rmi3, float):
            self.rmi3 = float(self.rmi3)

        if self.vma3 is not None and not isinstance(self.vma3, float):
            self.vma3 = float(self.vma3)

        if self.vmi3 is not None and not isinstance(self.vmi3, float):
            self.vmi3 = float(self.vmi3)

        if self.ntp3 is not None and not isinstance(self.ntp3, int):
            self.ntp3 = int(self.ntp3)

        if self.tab3 is not None and not isinstance(self.tab3, int):
            self.tab3 = int(self.tab3)

        if self.cr3 is not None and not isinstance(self.cr3, float):
            self.cr3 = float(self.cr3)

        if self.cx3 is not None and not isinstance(self.cx3, float):
            self.cx3 = float(self.cx3)

        if self.cnxa3 is not None and not isinstance(self.cnxa3, float):
            self.cnxa3 = float(self.cnxa3)

        if self.nod3 is not None and not isinstance(self.nod3, int):
            self.nod3 = int(self.nod3)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class AreaInterchangeRecord(YAMLRoot):
    """
    Area interchange data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["AreaInterchangeRecord"]
    class_class_curie: ClassVar[str] = "raw:AreaInterchangeRecord"
    class_name: ClassVar[str] = "AreaInterchangeRecord"
    class_model_uri: ClassVar[URIRef] = RAW.AreaInterchangeRecord

    area_number: Union[int, AreaInterchangeRecordAreaNumber] = None
    bus_number: Optional[int] = None
    pdes: Optional[float] = None
    ptol: Optional[float] = None
    name: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.area_number):
            self.MissingRequiredField("area_number")
        if not isinstance(self.area_number, AreaInterchangeRecordAreaNumber):
            self.area_number = AreaInterchangeRecordAreaNumber(self.area_number)

        if self.bus_number is not None and not isinstance(self.bus_number, int):
            self.bus_number = int(self.bus_number)

        if self.pdes is not None and not isinstance(self.pdes, float):
            self.pdes = float(self.pdes)

        if self.ptol is not None and not isinstance(self.ptol, float):
            self.ptol = float(self.ptol)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class TwoTerminalDCRecord(YAMLRoot):
    """
    Two-terminal DC transmission line data record.

    Multi-line format:
    - Line 1: DC line identification and control
    - Line 2: Rectifier (converter) end data
    - Line 3: Inverter (converter) end data

    Maps to CIM: cim.DCLineSegment, cim.ACDCConverter
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["TwoTerminalDCRecord"]
    class_class_curie: ClassVar[str] = "raw:TwoTerminalDCRecord"
    class_name: ClassVar[str] = "TwoTerminalDCRecord"
    class_model_uri: ClassVar[URIRef] = RAW.TwoTerminalDCRecord

    name: Union[str, TwoTerminalDCRecordName] = None
    rdc: float = None
    setvl: float = None
    vschd: float = None
    ipr: int = None
    nbr: int = None
    anmxr: float = None
    anmnr: float = None
    rcr: float = None
    xcr: float = None
    ebasr: float = None
    ipi: int = None
    nbi: int = None
    anmxi: float = None
    anmni: float = None
    rci: float = None
    xci: float = None
    ebasi: float = None
    mdc: Optional[int] = None
    vcmod: Optional[float] = None
    rcomp: Optional[float] = None
    delti: Optional[float] = None
    meter: Optional[str] = None
    dcvmin: Optional[float] = None
    cccitmx: Optional[int] = None
    cccacc: Optional[float] = None
    trr: Optional[float] = None
    tapr: Optional[float] = None
    tmxr: Optional[float] = None
    tmnr: Optional[float] = None
    stpr: Optional[float] = None
    icr: Optional[int] = None
    ifr: Optional[int] = None
    itr: Optional[int] = None
    idr: Optional[str] = None
    xcapr: Optional[float] = None
    ndr: Optional[int] = None
    tri: Optional[float] = None
    tapi: Optional[float] = None
    tmxi: Optional[float] = None
    tmni: Optional[float] = None
    stpi: Optional[float] = None
    ici: Optional[int] = None
    ifi: Optional[int] = None
    iti: Optional[int] = None
    idi: Optional[str] = None
    xcapi: Optional[float] = None
    ndi: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, TwoTerminalDCRecordName):
            self.name = TwoTerminalDCRecordName(self.name)

        if self._is_empty(self.rdc):
            self.MissingRequiredField("rdc")
        if not isinstance(self.rdc, float):
            self.rdc = float(self.rdc)

        if self._is_empty(self.setvl):
            self.MissingRequiredField("setvl")
        if not isinstance(self.setvl, float):
            self.setvl = float(self.setvl)

        if self._is_empty(self.vschd):
            self.MissingRequiredField("vschd")
        if not isinstance(self.vschd, float):
            self.vschd = float(self.vschd)

        if self._is_empty(self.ipr):
            self.MissingRequiredField("ipr")
        if not isinstance(self.ipr, int):
            self.ipr = int(self.ipr)

        if self._is_empty(self.nbr):
            self.MissingRequiredField("nbr")
        if not isinstance(self.nbr, int):
            self.nbr = int(self.nbr)

        if self._is_empty(self.anmxr):
            self.MissingRequiredField("anmxr")
        if not isinstance(self.anmxr, float):
            self.anmxr = float(self.anmxr)

        if self._is_empty(self.anmnr):
            self.MissingRequiredField("anmnr")
        if not isinstance(self.anmnr, float):
            self.anmnr = float(self.anmnr)

        if self._is_empty(self.rcr):
            self.MissingRequiredField("rcr")
        if not isinstance(self.rcr, float):
            self.rcr = float(self.rcr)

        if self._is_empty(self.xcr):
            self.MissingRequiredField("xcr")
        if not isinstance(self.xcr, float):
            self.xcr = float(self.xcr)

        if self._is_empty(self.ebasr):
            self.MissingRequiredField("ebasr")
        if not isinstance(self.ebasr, float):
            self.ebasr = float(self.ebasr)

        if self._is_empty(self.ipi):
            self.MissingRequiredField("ipi")
        if not isinstance(self.ipi, int):
            self.ipi = int(self.ipi)

        if self._is_empty(self.nbi):
            self.MissingRequiredField("nbi")
        if not isinstance(self.nbi, int):
            self.nbi = int(self.nbi)

        if self._is_empty(self.anmxi):
            self.MissingRequiredField("anmxi")
        if not isinstance(self.anmxi, float):
            self.anmxi = float(self.anmxi)

        if self._is_empty(self.anmni):
            self.MissingRequiredField("anmni")
        if not isinstance(self.anmni, float):
            self.anmni = float(self.anmni)

        if self._is_empty(self.rci):
            self.MissingRequiredField("rci")
        if not isinstance(self.rci, float):
            self.rci = float(self.rci)

        if self._is_empty(self.xci):
            self.MissingRequiredField("xci")
        if not isinstance(self.xci, float):
            self.xci = float(self.xci)

        if self._is_empty(self.ebasi):
            self.MissingRequiredField("ebasi")
        if not isinstance(self.ebasi, float):
            self.ebasi = float(self.ebasi)

        if self.mdc is not None and not isinstance(self.mdc, int):
            self.mdc = int(self.mdc)

        if self.vcmod is not None and not isinstance(self.vcmod, float):
            self.vcmod = float(self.vcmod)

        if self.rcomp is not None and not isinstance(self.rcomp, float):
            self.rcomp = float(self.rcomp)

        if self.delti is not None and not isinstance(self.delti, float):
            self.delti = float(self.delti)

        if self.meter is not None and not isinstance(self.meter, str):
            self.meter = str(self.meter)

        if self.dcvmin is not None and not isinstance(self.dcvmin, float):
            self.dcvmin = float(self.dcvmin)

        if self.cccitmx is not None and not isinstance(self.cccitmx, int):
            self.cccitmx = int(self.cccitmx)

        if self.cccacc is not None and not isinstance(self.cccacc, float):
            self.cccacc = float(self.cccacc)

        if self.trr is not None and not isinstance(self.trr, float):
            self.trr = float(self.trr)

        if self.tapr is not None and not isinstance(self.tapr, float):
            self.tapr = float(self.tapr)

        if self.tmxr is not None and not isinstance(self.tmxr, float):
            self.tmxr = float(self.tmxr)

        if self.tmnr is not None and not isinstance(self.tmnr, float):
            self.tmnr = float(self.tmnr)

        if self.stpr is not None and not isinstance(self.stpr, float):
            self.stpr = float(self.stpr)

        if self.icr is not None and not isinstance(self.icr, int):
            self.icr = int(self.icr)

        if self.ifr is not None and not isinstance(self.ifr, int):
            self.ifr = int(self.ifr)

        if self.itr is not None and not isinstance(self.itr, int):
            self.itr = int(self.itr)

        if self.idr is not None and not isinstance(self.idr, str):
            self.idr = str(self.idr)

        if self.xcapr is not None and not isinstance(self.xcapr, float):
            self.xcapr = float(self.xcapr)

        if self.ndr is not None and not isinstance(self.ndr, int):
            self.ndr = int(self.ndr)

        if self.tri is not None and not isinstance(self.tri, float):
            self.tri = float(self.tri)

        if self.tapi is not None and not isinstance(self.tapi, float):
            self.tapi = float(self.tapi)

        if self.tmxi is not None and not isinstance(self.tmxi, float):
            self.tmxi = float(self.tmxi)

        if self.tmni is not None and not isinstance(self.tmni, float):
            self.tmni = float(self.tmni)

        if self.stpi is not None and not isinstance(self.stpi, float):
            self.stpi = float(self.stpi)

        if self.ici is not None and not isinstance(self.ici, int):
            self.ici = int(self.ici)

        if self.ifi is not None and not isinstance(self.ifi, int):
            self.ifi = int(self.ifi)

        if self.iti is not None and not isinstance(self.iti, int):
            self.iti = int(self.iti)

        if self.idi is not None and not isinstance(self.idi, str):
            self.idi = str(self.idi)

        if self.xcapi is not None and not isinstance(self.xcapi, float):
            self.xcapi = float(self.xcapi)

        if self.ndi is not None and not isinstance(self.ndi, int):
            self.ndi = int(self.ndi)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class VscDcRecord(YAMLRoot):
    """
    Voltage source converter (VSC) DC transmission line data record.

    Multi-line format:
    - Line 1: VSC DC line identification, resistance, and ownership
    - Line 2: Converter data and control parameters

    Maps to CIM: cim.DCLineSegment, cim.VsConverter
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["VscDcRecord"]
    class_class_curie: ClassVar[str] = "raw:VscDcRecord"
    class_name: ClassVar[str] = "VscDcRecord"
    class_model_uri: ClassVar[URIRef] = RAW.VscDcRecord

    name: str = None
    rdc: float = None
    ibus: int = None
    converter_type: int = None
    dcset: float = None
    mdc: Optional[int] = None
    o1: Optional[int] = None
    f1: Optional[float] = None
    o2: Optional[int] = None
    f2: Optional[float] = None
    o3: Optional[int] = None
    f3: Optional[float] = None
    o4: Optional[int] = None
    f4: Optional[float] = None
    mode: Optional[int] = None
    acset: Optional[float] = None
    aloss: Optional[float] = None
    bloss: Optional[float] = None
    minloss: Optional[float] = None
    smax: Optional[float] = None
    imax: Optional[float] = None
    pwf: Optional[float] = None
    maxq: Optional[float] = None
    minq: Optional[float] = None
    vsreg: Optional[int] = None
    rmpct: Optional[float] = None
    nreg: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, str):
            self.name = str(self.name)

        if self._is_empty(self.rdc):
            self.MissingRequiredField("rdc")
        if not isinstance(self.rdc, float):
            self.rdc = float(self.rdc)

        if self._is_empty(self.ibus):
            self.MissingRequiredField("ibus")
        if not isinstance(self.ibus, int):
            self.ibus = int(self.ibus)

        if self._is_empty(self.converter_type):
            self.MissingRequiredField("converter_type")
        if not isinstance(self.converter_type, int):
            self.converter_type = int(self.converter_type)

        if self._is_empty(self.dcset):
            self.MissingRequiredField("dcset")
        if not isinstance(self.dcset, float):
            self.dcset = float(self.dcset)

        if self.mdc is not None and not isinstance(self.mdc, int):
            self.mdc = int(self.mdc)

        if self.o1 is not None and not isinstance(self.o1, int):
            self.o1 = int(self.o1)

        if self.f1 is not None and not isinstance(self.f1, float):
            self.f1 = float(self.f1)

        if self.o2 is not None and not isinstance(self.o2, int):
            self.o2 = int(self.o2)

        if self.f2 is not None and not isinstance(self.f2, float):
            self.f2 = float(self.f2)

        if self.o3 is not None and not isinstance(self.o3, int):
            self.o3 = int(self.o3)

        if self.f3 is not None and not isinstance(self.f3, float):
            self.f3 = float(self.f3)

        if self.o4 is not None and not isinstance(self.o4, int):
            self.o4 = int(self.o4)

        if self.f4 is not None and not isinstance(self.f4, float):
            self.f4 = float(self.f4)

        if self.mode is not None and not isinstance(self.mode, int):
            self.mode = int(self.mode)

        if self.acset is not None and not isinstance(self.acset, float):
            self.acset = float(self.acset)

        if self.aloss is not None and not isinstance(self.aloss, float):
            self.aloss = float(self.aloss)

        if self.bloss is not None and not isinstance(self.bloss, float):
            self.bloss = float(self.bloss)

        if self.minloss is not None and not isinstance(self.minloss, float):
            self.minloss = float(self.minloss)

        if self.smax is not None and not isinstance(self.smax, float):
            self.smax = float(self.smax)

        if self.imax is not None and not isinstance(self.imax, float):
            self.imax = float(self.imax)

        if self.pwf is not None and not isinstance(self.pwf, float):
            self.pwf = float(self.pwf)

        if self.maxq is not None and not isinstance(self.maxq, float):
            self.maxq = float(self.maxq)

        if self.minq is not None and not isinstance(self.minq, float):
            self.minq = float(self.minq)

        if self.vsreg is not None and not isinstance(self.vsreg, int):
            self.vsreg = int(self.vsreg)

        if self.rmpct is not None and not isinstance(self.rmpct, float):
            self.rmpct = float(self.rmpct)

        if self.nreg is not None and not isinstance(self.nreg, int):
            self.nreg = int(self.nreg)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class ImpedanceCorrectionRecord(YAMLRoot):
    """
    Transformer impedance correction table data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["ImpedanceCorrectionRecord"]
    class_class_curie: ClassVar[str] = "raw:ImpedanceCorrectionRecord"
    class_name: ClassVar[str] = "ImpedanceCorrectionRecord"
    class_model_uri: ClassVar[URIRef] = RAW.ImpedanceCorrectionRecord

    table_number: Union[int, ImpedanceCorrectionRecordTableNumber] = None
    t1: Optional[float] = None
    f1_real: Optional[float] = None
    f1_imag: Optional[float] = None
    t2: Optional[float] = None
    f2_real: Optional[float] = None
    f2_imag: Optional[float] = None
    t3: Optional[float] = None
    f3_real: Optional[float] = None
    f3_imag: Optional[float] = None
    t4: Optional[float] = None
    f4_real: Optional[float] = None
    f4_imag: Optional[float] = None
    t5: Optional[float] = None
    f5_real: Optional[float] = None
    f5_imag: Optional[float] = None
    t6: Optional[float] = None
    f6_real: Optional[float] = None
    f6_imag: Optional[float] = None
    t7: Optional[float] = None
    f7_real: Optional[float] = None
    f7_imag: Optional[float] = None
    t8: Optional[float] = None
    f8_real: Optional[float] = None
    f8_imag: Optional[float] = None
    t9: Optional[float] = None
    f9_real: Optional[float] = None
    f9_imag: Optional[float] = None
    t10: Optional[float] = None
    f10_real: Optional[float] = None
    f10_imag: Optional[float] = None
    t11: Optional[float] = None
    f11_real: Optional[float] = None
    f11_imag: Optional[float] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.table_number):
            self.MissingRequiredField("table_number")
        if not isinstance(self.table_number, ImpedanceCorrectionRecordTableNumber):
            self.table_number = ImpedanceCorrectionRecordTableNumber(self.table_number)

        if self.t1 is not None and not isinstance(self.t1, float):
            self.t1 = float(self.t1)

        if self.f1_real is not None and not isinstance(self.f1_real, float):
            self.f1_real = float(self.f1_real)

        if self.f1_imag is not None and not isinstance(self.f1_imag, float):
            self.f1_imag = float(self.f1_imag)

        if self.t2 is not None and not isinstance(self.t2, float):
            self.t2 = float(self.t2)

        if self.f2_real is not None and not isinstance(self.f2_real, float):
            self.f2_real = float(self.f2_real)

        if self.f2_imag is not None and not isinstance(self.f2_imag, float):
            self.f2_imag = float(self.f2_imag)

        if self.t3 is not None and not isinstance(self.t3, float):
            self.t3 = float(self.t3)

        if self.f3_real is not None and not isinstance(self.f3_real, float):
            self.f3_real = float(self.f3_real)

        if self.f3_imag is not None and not isinstance(self.f3_imag, float):
            self.f3_imag = float(self.f3_imag)

        if self.t4 is not None and not isinstance(self.t4, float):
            self.t4 = float(self.t4)

        if self.f4_real is not None and not isinstance(self.f4_real, float):
            self.f4_real = float(self.f4_real)

        if self.f4_imag is not None and not isinstance(self.f4_imag, float):
            self.f4_imag = float(self.f4_imag)

        if self.t5 is not None and not isinstance(self.t5, float):
            self.t5 = float(self.t5)

        if self.f5_real is not None and not isinstance(self.f5_real, float):
            self.f5_real = float(self.f5_real)

        if self.f5_imag is not None and not isinstance(self.f5_imag, float):
            self.f5_imag = float(self.f5_imag)

        if self.t6 is not None and not isinstance(self.t6, float):
            self.t6 = float(self.t6)

        if self.f6_real is not None and not isinstance(self.f6_real, float):
            self.f6_real = float(self.f6_real)

        if self.f6_imag is not None and not isinstance(self.f6_imag, float):
            self.f6_imag = float(self.f6_imag)

        if self.t7 is not None and not isinstance(self.t7, float):
            self.t7 = float(self.t7)

        if self.f7_real is not None and not isinstance(self.f7_real, float):
            self.f7_real = float(self.f7_real)

        if self.f7_imag is not None and not isinstance(self.f7_imag, float):
            self.f7_imag = float(self.f7_imag)

        if self.t8 is not None and not isinstance(self.t8, float):
            self.t8 = float(self.t8)

        if self.f8_real is not None and not isinstance(self.f8_real, float):
            self.f8_real = float(self.f8_real)

        if self.f8_imag is not None and not isinstance(self.f8_imag, float):
            self.f8_imag = float(self.f8_imag)

        if self.t9 is not None and not isinstance(self.t9, float):
            self.t9 = float(self.t9)

        if self.f9_real is not None and not isinstance(self.f9_real, float):
            self.f9_real = float(self.f9_real)

        if self.f9_imag is not None and not isinstance(self.f9_imag, float):
            self.f9_imag = float(self.f9_imag)

        if self.t10 is not None and not isinstance(self.t10, float):
            self.t10 = float(self.t10)

        if self.f10_real is not None and not isinstance(self.f10_real, float):
            self.f10_real = float(self.f10_real)

        if self.f10_imag is not None and not isinstance(self.f10_imag, float):
            self.f10_imag = float(self.f10_imag)

        if self.t11 is not None and not isinstance(self.t11, float):
            self.t11 = float(self.t11)

        if self.f11_real is not None and not isinstance(self.f11_real, float):
            self.f11_real = float(self.f11_real)

        if self.f11_imag is not None and not isinstance(self.f11_imag, float):
            self.f11_imag = float(self.f11_imag)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class MultiTerminalDCRecord(YAMLRoot):
    """
    Multi-terminal DC transmission line system definition record (one per line).
    Followed by NCONV MultiTerminalConverterRecord, NDCBS MultiTerminalDCBusRecord
    and NDCLN MultiTerminalDCLinkRecord records, in that order.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["MultiTerminalDCRecord"]
    class_class_curie: ClassVar[str] = "raw:MultiTerminalDCRecord"
    class_name: ClassVar[str] = "MultiTerminalDCRecord"
    class_model_uri: ClassVar[URIRef] = RAW.MultiTerminalDCRecord

    name: str = None
    nconv: int = None
    ndcbs: int = None
    ndcln: int = None
    vconv: int = None
    mdc: Optional[int] = None
    vcmod: Optional[float] = None
    vconvn: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, str):
            self.name = str(self.name)

        if self._is_empty(self.nconv):
            self.MissingRequiredField("nconv")
        if not isinstance(self.nconv, int):
            self.nconv = int(self.nconv)

        if self._is_empty(self.ndcbs):
            self.MissingRequiredField("ndcbs")
        if not isinstance(self.ndcbs, int):
            self.ndcbs = int(self.ndcbs)

        if self._is_empty(self.ndcln):
            self.MissingRequiredField("ndcln")
        if not isinstance(self.ndcln, int):
            self.ndcln = int(self.ndcln)

        if self._is_empty(self.vconv):
            self.MissingRequiredField("vconv")
        if not isinstance(self.vconv, int):
            self.vconv = int(self.vconv)

        if self.mdc is not None and not isinstance(self.mdc, int):
            self.mdc = int(self.mdc)

        if self.vcmod is not None and not isinstance(self.vcmod, float):
            self.vcmod = float(self.vcmod)

        if self.vconvn is not None and not isinstance(self.vconvn, int):
            self.vconvn = int(self.vconvn)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class MultiTerminalConverterRecord(YAMLRoot):
    """
    Converter station record of a multi-terminal DC line (NCONV per line).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["MultiTerminalConverterRecord"]
    class_class_curie: ClassVar[str] = "raw:MultiTerminalConverterRecord"
    class_name: ClassVar[str] = "MultiTerminalConverterRecord"
    class_model_uri: ClassVar[URIRef] = RAW.MultiTerminalConverterRecord

    ib: int = None
    n: int = None
    angmx: float = None
    angmn: float = None
    rc: float = None
    xc: float = None
    ebas: float = None
    setvl: float = None
    tr: Optional[float] = None
    tap: Optional[float] = None
    tpmx: Optional[float] = None
    tpmn: Optional[float] = None
    tstp: Optional[float] = None
    dcpf: Optional[float] = None
    marg: Optional[float] = None
    cnvcod: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.ib):
            self.MissingRequiredField("ib")
        if not isinstance(self.ib, int):
            self.ib = int(self.ib)

        if self._is_empty(self.n):
            self.MissingRequiredField("n")
        if not isinstance(self.n, int):
            self.n = int(self.n)

        if self._is_empty(self.angmx):
            self.MissingRequiredField("angmx")
        if not isinstance(self.angmx, float):
            self.angmx = float(self.angmx)

        if self._is_empty(self.angmn):
            self.MissingRequiredField("angmn")
        if not isinstance(self.angmn, float):
            self.angmn = float(self.angmn)

        if self._is_empty(self.rc):
            self.MissingRequiredField("rc")
        if not isinstance(self.rc, float):
            self.rc = float(self.rc)

        if self._is_empty(self.xc):
            self.MissingRequiredField("xc")
        if not isinstance(self.xc, float):
            self.xc = float(self.xc)

        if self._is_empty(self.ebas):
            self.MissingRequiredField("ebas")
        if not isinstance(self.ebas, float):
            self.ebas = float(self.ebas)

        if self._is_empty(self.setvl):
            self.MissingRequiredField("setvl")
        if not isinstance(self.setvl, float):
            self.setvl = float(self.setvl)

        if self.tr is not None and not isinstance(self.tr, float):
            self.tr = float(self.tr)

        if self.tap is not None and not isinstance(self.tap, float):
            self.tap = float(self.tap)

        if self.tpmx is not None and not isinstance(self.tpmx, float):
            self.tpmx = float(self.tpmx)

        if self.tpmn is not None and not isinstance(self.tpmn, float):
            self.tpmn = float(self.tpmn)

        if self.tstp is not None and not isinstance(self.tstp, float):
            self.tstp = float(self.tstp)

        if self.dcpf is not None and not isinstance(self.dcpf, float):
            self.dcpf = float(self.dcpf)

        if self.marg is not None and not isinstance(self.marg, float):
            self.marg = float(self.marg)

        if self.cnvcod is not None and not isinstance(self.cnvcod, int):
            self.cnvcod = int(self.cnvcod)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class MultiTerminalDCBusRecord(YAMLRoot):
    """
    DC bus record of a multi-terminal DC line (NDCBS per line).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["MultiTerminalDCBusRecord"]
    class_class_curie: ClassVar[str] = "raw:MultiTerminalDCBusRecord"
    class_name: ClassVar[str] = "MultiTerminalDCBusRecord"
    class_model_uri: ClassVar[URIRef] = RAW.MultiTerminalDCBusRecord

    idc: int = None
    ib: Optional[int] = None
    area: Optional[int] = None
    zone: Optional[int] = None
    dcname: Optional[str] = None
    idc2: Optional[int] = None
    rgrnd: Optional[float] = None
    owner: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.idc):
            self.MissingRequiredField("idc")
        if not isinstance(self.idc, int):
            self.idc = int(self.idc)

        if self.ib is not None and not isinstance(self.ib, int):
            self.ib = int(self.ib)

        if self.area is not None and not isinstance(self.area, int):
            self.area = int(self.area)

        if self.zone is not None and not isinstance(self.zone, int):
            self.zone = int(self.zone)

        if self.dcname is not None and not isinstance(self.dcname, str):
            self.dcname = str(self.dcname)

        if self.idc2 is not None and not isinstance(self.idc2, int):
            self.idc2 = int(self.idc2)

        if self.rgrnd is not None and not isinstance(self.rgrnd, float):
            self.rgrnd = float(self.rgrnd)

        if self.owner is not None and not isinstance(self.owner, int):
            self.owner = int(self.owner)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class MultiTerminalDCLinkRecord(YAMLRoot):
    """
    DC link record of a multi-terminal DC line (NDCLN per line).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["MultiTerminalDCLinkRecord"]
    class_class_curie: ClassVar[str] = "raw:MultiTerminalDCLinkRecord"
    class_name: ClassVar[str] = "MultiTerminalDCLinkRecord"
    class_model_uri: ClassVar[URIRef] = RAW.MultiTerminalDCLinkRecord

    idc: int = None
    jdc: int = None
    rdc: float = None
    ckt: Optional[str] = None
    met: Optional[int] = None
    ldc: Optional[float] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.idc):
            self.MissingRequiredField("idc")
        if not isinstance(self.idc, int):
            self.idc = int(self.idc)

        if self._is_empty(self.jdc):
            self.MissingRequiredField("jdc")
        if not isinstance(self.jdc, int):
            self.jdc = int(self.jdc)

        if self._is_empty(self.rdc):
            self.MissingRequiredField("rdc")
        if not isinstance(self.rdc, float):
            self.rdc = float(self.rdc)

        if self.ckt is not None and not isinstance(self.ckt, str):
            self.ckt = str(self.ckt)

        if self.met is not None and not isinstance(self.met, int):
            self.met = int(self.met)

        if self.ldc is not None and not isinstance(self.ldc, float):
            self.ldc = float(self.ldc)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class MultiSectionLineRecord(YAMLRoot):
    """
    Multi-section line grouping data record.

    Variable-length format:
    - Fixed fields: I, J, ID, MET
    - Variable section identifiers: Up to 9 dummy integer fields (DUM1-DUM9)
    - Only non-zero section identifiers are serialized

    A multi-section line groups several branch sections that are treated as a
    single transmission line for operational purposes. Each section references
    a branch record by its bus endpoints.

    Maps to CIM: cim.Line (grouping multiple cim.ACLineSegment objects)
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["MultiSectionLineRecord"]
    class_class_curie: ClassVar[str] = "raw:MultiSectionLineRecord"
    class_name: ClassVar[str] = "MultiSectionLineRecord"
    class_model_uri: ClassVar[URIRef] = RAW.MultiSectionLineRecord

    i: int = None
    j: int = None
    dum1: int = None
    line_id: Optional[str] = None
    met: Optional[int] = None
    dum2: Optional[int] = None
    dum3: Optional[int] = None
    dum4: Optional[int] = None
    dum5: Optional[int] = None
    dum6: Optional[int] = None
    dum7: Optional[int] = None
    dum8: Optional[int] = None
    dum9: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.i):
            self.MissingRequiredField("i")
        if not isinstance(self.i, int):
            self.i = int(self.i)

        if self._is_empty(self.j):
            self.MissingRequiredField("j")
        if not isinstance(self.j, int):
            self.j = int(self.j)

        if self._is_empty(self.dum1):
            self.MissingRequiredField("dum1")
        if not isinstance(self.dum1, int):
            self.dum1 = int(self.dum1)

        if self.line_id is not None and not isinstance(self.line_id, str):
            self.line_id = str(self.line_id)

        if self.met is not None and not isinstance(self.met, int):
            self.met = int(self.met)

        if self.dum2 is not None and not isinstance(self.dum2, int):
            self.dum2 = int(self.dum2)

        if self.dum3 is not None and not isinstance(self.dum3, int):
            self.dum3 = int(self.dum3)

        if self.dum4 is not None and not isinstance(self.dum4, int):
            self.dum4 = int(self.dum4)

        if self.dum5 is not None and not isinstance(self.dum5, int):
            self.dum5 = int(self.dum5)

        if self.dum6 is not None and not isinstance(self.dum6, int):
            self.dum6 = int(self.dum6)

        if self.dum7 is not None and not isinstance(self.dum7, int):
            self.dum7 = int(self.dum7)

        if self.dum8 is not None and not isinstance(self.dum8, int):
            self.dum8 = int(self.dum8)

        if self.dum9 is not None and not isinstance(self.dum9, int):
            self.dum9 = int(self.dum9)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class ZoneRecord(YAMLRoot):
    """
    Zone data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["ZoneRecord"]
    class_class_curie: ClassVar[str] = "raw:ZoneRecord"
    class_name: ClassVar[str] = "ZoneRecord"
    class_model_uri: ClassVar[URIRef] = RAW.ZoneRecord

    zone_number: Union[int, ZoneRecordZoneNumber] = None
    zone_name: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.zone_number):
            self.MissingRequiredField("zone_number")
        if not isinstance(self.zone_number, ZoneRecordZoneNumber):
            self.zone_number = ZoneRecordZoneNumber(self.zone_number)

        if self.zone_name is not None and not isinstance(self.zone_name, str):
            self.zone_name = str(self.zone_name)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class InterareaTransferRecord(YAMLRoot):
    """
    Interarea transfer data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["InterareaTransferRecord"]
    class_class_curie: ClassVar[str] = "raw:InterareaTransferRecord"
    class_name: ClassVar[str] = "InterareaTransferRecord"
    class_model_uri: ClassVar[URIRef] = RAW.InterareaTransferRecord

    from_area: int = None
    to_area: int = None
    transfer_id: Optional[str] = None
    power_transfer: Optional[float] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.from_area):
            self.MissingRequiredField("from_area")
        if not isinstance(self.from_area, int):
            self.from_area = int(self.from_area)

        if self._is_empty(self.to_area):
            self.MissingRequiredField("to_area")
        if not isinstance(self.to_area, int):
            self.to_area = int(self.to_area)

        if self.transfer_id is not None and not isinstance(self.transfer_id, str):
            self.transfer_id = str(self.transfer_id)

        if self.power_transfer is not None and not isinstance(self.power_transfer, float):
            self.power_transfer = float(self.power_transfer)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class OwnerRecord(YAMLRoot):
    """
    Owner data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["OwnerRecord"]
    class_class_curie: ClassVar[str] = "raw:OwnerRecord"
    class_name: ClassVar[str] = "OwnerRecord"
    class_model_uri: ClassVar[URIRef] = RAW.OwnerRecord

    owner_number: Union[int, OwnerRecordOwnerNumber] = None
    owner_name: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.owner_number):
            self.MissingRequiredField("owner_number")
        if not isinstance(self.owner_number, OwnerRecordOwnerNumber):
            self.owner_number = OwnerRecordOwnerNumber(self.owner_number)

        if self.owner_name is not None and not isinstance(self.owner_name, str):
            self.owner_name = str(self.owner_name)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class FactsDeviceRecord(YAMLRoot):
    """
    FACTS control device data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["FactsDeviceRecord"]
    class_class_curie: ClassVar[str] = "raw:FactsDeviceRecord"
    class_name: ClassVar[str] = "FactsDeviceRecord"
    class_model_uri: ClassVar[URIRef] = RAW.FactsDeviceRecord

    name: str = None
    ibus: int = None
    jbus: Optional[int] = None
    mode: Optional[int] = None
    pdes: Optional[float] = None
    qdes: Optional[float] = None
    vset: Optional[float] = None
    shmx: Optional[float] = None
    trmx: Optional[float] = None
    vtmn: Optional[float] = None
    vtmx: Optional[float] = None
    vsmx: Optional[float] = None
    imx: Optional[float] = None
    linx: Optional[float] = None
    rmpct: Optional[float] = None
    owner: Optional[int] = None
    set1: Optional[float] = None
    set2: Optional[float] = None
    vsref: Optional[int] = None
    remot: Optional[int] = None
    mname: Optional[str] = None
    nreg: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, str):
            self.name = str(self.name)

        if self._is_empty(self.ibus):
            self.MissingRequiredField("ibus")
        if not isinstance(self.ibus, int):
            self.ibus = int(self.ibus)

        if self.jbus is not None and not isinstance(self.jbus, int):
            self.jbus = int(self.jbus)

        if self.mode is not None and not isinstance(self.mode, int):
            self.mode = int(self.mode)

        if self.pdes is not None and not isinstance(self.pdes, float):
            self.pdes = float(self.pdes)

        if self.qdes is not None and not isinstance(self.qdes, float):
            self.qdes = float(self.qdes)

        if self.vset is not None and not isinstance(self.vset, float):
            self.vset = float(self.vset)

        if self.shmx is not None and not isinstance(self.shmx, float):
            self.shmx = float(self.shmx)

        if self.trmx is not None and not isinstance(self.trmx, float):
            self.trmx = float(self.trmx)

        if self.vtmn is not None and not isinstance(self.vtmn, float):
            self.vtmn = float(self.vtmn)

        if self.vtmx is not None and not isinstance(self.vtmx, float):
            self.vtmx = float(self.vtmx)

        if self.vsmx is not None and not isinstance(self.vsmx, float):
            self.vsmx = float(self.vsmx)

        if self.imx is not None and not isinstance(self.imx, float):
            self.imx = float(self.imx)

        if self.linx is not None and not isinstance(self.linx, float):
            self.linx = float(self.linx)

        if self.rmpct is not None and not isinstance(self.rmpct, float):
            self.rmpct = float(self.rmpct)

        if self.owner is not None and not isinstance(self.owner, int):
            self.owner = int(self.owner)

        if self.set1 is not None and not isinstance(self.set1, float):
            self.set1 = float(self.set1)

        if self.set2 is not None and not isinstance(self.set2, float):
            self.set2 = float(self.set2)

        if self.vsref is not None and not isinstance(self.vsref, int):
            self.vsref = int(self.vsref)

        if self.remot is not None and not isinstance(self.remot, int):
            self.remot = int(self.remot)

        if self.mname is not None and not isinstance(self.mname, str):
            self.mname = str(self.mname)

        if self.nreg is not None and not isinstance(self.nreg, int):
            self.nreg = int(self.nreg)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class SwitchedShuntRecord(YAMLRoot):
    """
    Switched shunt compensator data record.
    Variable-length format:
    - Fixed fields: I, MODSW, ADJM, STAT, VSWHI, VSWLO, SWREG, RMPCT, RMIDNT, BINIT
    - Variable blocks: Up to 8 N/B pairs (only non-zero blocks are serialized)
    - Final field: NREG (only if remote regulation is used)
    Maps to CIM: cim.ShuntCompensator, cim.LinearShuntCompensator
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["SwitchedShuntRecord"]
    class_class_curie: ClassVar[str] = "raw:SwitchedShuntRecord"
    class_name: ClassVar[str] = "SwitchedShuntRecord"
    class_model_uri: ClassVar[URIRef] = RAW.SwitchedShuntRecord

    bus_number: int = None
    modsw: Optional[int] = None
    adjm: Optional[int] = None
    status: Optional[int] = None
    vswhi: Optional[float] = None
    vswlo: Optional[float] = None
    swreg: Optional[int] = None
    rmpct: Optional[float] = None
    rmidnt: Optional[str] = None
    binit: Optional[float] = None
    n1: Optional[int] = None
    b1: Optional[float] = None
    n2: Optional[int] = None
    b2: Optional[float] = None
    n3: Optional[int] = None
    b3: Optional[float] = None
    n4: Optional[int] = None
    b4: Optional[float] = None
    n5: Optional[int] = None
    b5: Optional[float] = None
    n6: Optional[int] = None
    b6: Optional[float] = None
    n7: Optional[int] = None
    b7: Optional[float] = None
    n8: Optional[int] = None
    b8: Optional[float] = None
    nreg: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.bus_number):
            self.MissingRequiredField("bus_number")
        if not isinstance(self.bus_number, int):
            self.bus_number = int(self.bus_number)

        if self.modsw is not None and not isinstance(self.modsw, int):
            self.modsw = int(self.modsw)

        if self.adjm is not None and not isinstance(self.adjm, int):
            self.adjm = int(self.adjm)

        if self.status is not None and not isinstance(self.status, int):
            self.status = int(self.status)

        if self.vswhi is not None and not isinstance(self.vswhi, float):
            self.vswhi = float(self.vswhi)

        if self.vswlo is not None and not isinstance(self.vswlo, float):
            self.vswlo = float(self.vswlo)

        if self.swreg is not None and not isinstance(self.swreg, int):
            self.swreg = int(self.swreg)

        if self.rmpct is not None and not isinstance(self.rmpct, float):
            self.rmpct = float(self.rmpct)

        if self.rmidnt is not None and not isinstance(self.rmidnt, str):
            self.rmidnt = str(self.rmidnt)

        if self.binit is not None and not isinstance(self.binit, float):
            self.binit = float(self.binit)

        if self.n1 is not None and not isinstance(self.n1, int):
            self.n1 = int(self.n1)

        if self.b1 is not None and not isinstance(self.b1, float):
            self.b1 = float(self.b1)

        if self.n2 is not None and not isinstance(self.n2, int):
            self.n2 = int(self.n2)

        if self.b2 is not None and not isinstance(self.b2, float):
            self.b2 = float(self.b2)

        if self.n3 is not None and not isinstance(self.n3, int):
            self.n3 = int(self.n3)

        if self.b3 is not None and not isinstance(self.b3, float):
            self.b3 = float(self.b3)

        if self.n4 is not None and not isinstance(self.n4, int):
            self.n4 = int(self.n4)

        if self.b4 is not None and not isinstance(self.b4, float):
            self.b4 = float(self.b4)

        if self.n5 is not None and not isinstance(self.n5, int):
            self.n5 = int(self.n5)

        if self.b5 is not None and not isinstance(self.b5, float):
            self.b5 = float(self.b5)

        if self.n6 is not None and not isinstance(self.n6, int):
            self.n6 = int(self.n6)

        if self.b6 is not None and not isinstance(self.b6, float):
            self.b6 = float(self.b6)

        if self.n7 is not None and not isinstance(self.n7, int):
            self.n7 = int(self.n7)

        if self.b7 is not None and not isinstance(self.b7, float):
            self.b7 = float(self.b7)

        if self.n8 is not None and not isinstance(self.n8, int):
            self.n8 = int(self.n8)

        if self.b8 is not None and not isinstance(self.b8, float):
            self.b8 = float(self.b8)

        if self.nreg is not None and not isinstance(self.nreg, int):
            self.nreg = int(self.nreg)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class GneDeviceRecord(YAMLRoot):
    """
    General network element device data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["GneDeviceRecord"]
    class_class_curie: ClassVar[str] = "raw:GneDeviceRecord"
    class_name: ClassVar[str] = "GneDeviceRecord"
    class_model_uri: ClassVar[URIRef] = RAW.GneDeviceRecord

    name: str = None
    model: str = None
    nterm: int = None
    bus_numbers: Optional[Union[int, list[int]]] = empty_list()
    nreal: Optional[int] = None
    nintg: Optional[int] = None
    nchar: Optional[int] = None
    status: Optional[int] = None
    owner: Optional[int] = None
    nmetr: Optional[int] = None
    real_data: Optional[Union[float, list[float]]] = empty_list()
    integer_data: Optional[Union[int, list[int]]] = empty_list()
    character_data: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, str):
            self.name = str(self.name)

        if self._is_empty(self.model):
            self.MissingRequiredField("model")
        if not isinstance(self.model, str):
            self.model = str(self.model)

        if self._is_empty(self.nterm):
            self.MissingRequiredField("nterm")
        if not isinstance(self.nterm, int):
            self.nterm = int(self.nterm)

        if not isinstance(self.bus_numbers, list):
            self.bus_numbers = [self.bus_numbers] if self.bus_numbers is not None else []
        self.bus_numbers = [v if isinstance(v, int) else int(v) for v in self.bus_numbers]

        if self.nreal is not None and not isinstance(self.nreal, int):
            self.nreal = int(self.nreal)

        if self.nintg is not None and not isinstance(self.nintg, int):
            self.nintg = int(self.nintg)

        if self.nchar is not None and not isinstance(self.nchar, int):
            self.nchar = int(self.nchar)

        if self.status is not None and not isinstance(self.status, int):
            self.status = int(self.status)

        if self.owner is not None and not isinstance(self.owner, int):
            self.owner = int(self.owner)

        if self.nmetr is not None and not isinstance(self.nmetr, int):
            self.nmetr = int(self.nmetr)

        if not isinstance(self.real_data, list):
            self.real_data = [self.real_data] if self.real_data is not None else []
        self.real_data = [v if isinstance(v, float) else float(v) for v in self.real_data]

        if not isinstance(self.integer_data, list):
            self.integer_data = [self.integer_data] if self.integer_data is not None else []
        self.integer_data = [v if isinstance(v, int) else int(v) for v in self.integer_data]

        if not isinstance(self.character_data, list):
            self.character_data = [self.character_data] if self.character_data is not None else []
        self.character_data = [v if isinstance(v, str) else str(v) for v in self.character_data]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class InductionMachineRecord(YAMLRoot):
    """
    Induction machine data record
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["InductionMachineRecord"]
    class_class_curie: ClassVar[str] = "raw:InductionMachineRecord"
    class_name: ClassVar[str] = "InductionMachineRecord"
    class_model_uri: ClassVar[URIRef] = RAW.InductionMachineRecord

    bus_id: int = None
    name: Optional[str] = None
    status: Optional[int] = None
    scode: Optional[int] = None
    dcode: Optional[int] = None
    area: Optional[int] = None
    zone: Optional[int] = None
    owner: Optional[int] = None
    tcode: Optional[int] = None
    bcode: Optional[int] = None
    mbase: Optional[float] = None
    ratekv: Optional[float] = None
    pcode: Optional[int] = None
    pset: Optional[float] = None
    h: Optional[float] = None
    a: Optional[float] = None
    b: Optional[float] = None
    d: Optional[float] = None
    e: Optional[float] = None
    ra: Optional[float] = None
    xa: Optional[float] = None
    xm: Optional[float] = None
    r1: Optional[float] = None
    x1: Optional[float] = None
    r2: Optional[float] = None
    x2: Optional[float] = None
    x3: Optional[float] = None
    e1: Optional[float] = None
    se1: Optional[float] = None
    e2: Optional[float] = None
    se2: Optional[float] = None
    ia1: Optional[float] = None
    ia2: Optional[float] = None
    xamult: Optional[float] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.bus_id):
            self.MissingRequiredField("bus_id")
        if not isinstance(self.bus_id, int):
            self.bus_id = int(self.bus_id)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.status is not None and not isinstance(self.status, int):
            self.status = int(self.status)

        if self.scode is not None and not isinstance(self.scode, int):
            self.scode = int(self.scode)

        if self.dcode is not None and not isinstance(self.dcode, int):
            self.dcode = int(self.dcode)

        if self.area is not None and not isinstance(self.area, int):
            self.area = int(self.area)

        if self.zone is not None and not isinstance(self.zone, int):
            self.zone = int(self.zone)

        if self.owner is not None and not isinstance(self.owner, int):
            self.owner = int(self.owner)

        if self.tcode is not None and not isinstance(self.tcode, int):
            self.tcode = int(self.tcode)

        if self.bcode is not None and not isinstance(self.bcode, int):
            self.bcode = int(self.bcode)

        if self.mbase is not None and not isinstance(self.mbase, float):
            self.mbase = float(self.mbase)

        if self.ratekv is not None and not isinstance(self.ratekv, float):
            self.ratekv = float(self.ratekv)

        if self.pcode is not None and not isinstance(self.pcode, int):
            self.pcode = int(self.pcode)

        if self.pset is not None and not isinstance(self.pset, float):
            self.pset = float(self.pset)

        if self.h is not None and not isinstance(self.h, float):
            self.h = float(self.h)

        if self.a is not None and not isinstance(self.a, float):
            self.a = float(self.a)

        if self.b is not None and not isinstance(self.b, float):
            self.b = float(self.b)

        if self.d is not None and not isinstance(self.d, float):
            self.d = float(self.d)

        if self.e is not None and not isinstance(self.e, float):
            self.e = float(self.e)

        if self.ra is not None and not isinstance(self.ra, float):
            self.ra = float(self.ra)

        if self.xa is not None and not isinstance(self.xa, float):
            self.xa = float(self.xa)

        if self.xm is not None and not isinstance(self.xm, float):
            self.xm = float(self.xm)

        if self.r1 is not None and not isinstance(self.r1, float):
            self.r1 = float(self.r1)

        if self.x1 is not None and not isinstance(self.x1, float):
            self.x1 = float(self.x1)

        if self.r2 is not None and not isinstance(self.r2, float):
            self.r2 = float(self.r2)

        if self.x2 is not None and not isinstance(self.x2, float):
            self.x2 = float(self.x2)

        if self.x3 is not None and not isinstance(self.x3, float):
            self.x3 = float(self.x3)

        if self.e1 is not None and not isinstance(self.e1, float):
            self.e1 = float(self.e1)

        if self.se1 is not None and not isinstance(self.se1, float):
            self.se1 = float(self.se1)

        if self.e2 is not None and not isinstance(self.e2, float):
            self.e2 = float(self.e2)

        if self.se2 is not None and not isinstance(self.se2, float):
            self.se2 = float(self.se2)

        if self.ia1 is not None and not isinstance(self.ia1, float):
            self.ia1 = float(self.ia1)

        if self.ia2 is not None and not isinstance(self.ia2, float):
            self.ia2 = float(self.ia2)

        if self.xamult is not None and not isinstance(self.xamult, float):
            self.xamult = float(self.xamult)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class SubstationRecord(YAMLRoot):
    """
    Substation data record; the first record of each substation block
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["SubstationRecord"]
    class_class_curie: ClassVar[str] = "raw:SubstationRecord"
    class_name: ClassVar[str] = "SubstationRecord"
    class_model_uri: ClassVar[URIRef] = RAW.SubstationRecord

    substation_number: Union[int, SubstationRecordSubstationNumber] = None
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    grounding_resistance: Optional[float] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.substation_number):
            self.MissingRequiredField("substation_number")
        if not isinstance(self.substation_number, SubstationRecordSubstationNumber):
            self.substation_number = SubstationRecordSubstationNumber(self.substation_number)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.latitude is not None and not isinstance(self.latitude, float):
            self.latitude = float(self.latitude)

        if self.longitude is not None and not isinstance(self.longitude, float):
            self.longitude = float(self.longitude)

        if self.grounding_resistance is not None and not isinstance(self.grounding_resistance, float):
            self.grounding_resistance = float(self.grounding_resistance)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class SubstationNodeRecord(YAMLRoot):
    """
    Substation node data record; each node is a connection point inside a substation
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["SubstationNodeRecord"]
    class_class_curie: ClassVar[str] = "raw:SubstationNodeRecord"
    class_name: ClassVar[str] = "SubstationNodeRecord"
    class_model_uri: ClassVar[URIRef] = RAW.SubstationNodeRecord

    node_number: int = None
    bus_number: int = None
    name: Optional[str] = None
    status: Optional[int] = None
    vm: Optional[float] = None
    va: Optional[float] = None
    substation_number: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.node_number):
            self.MissingRequiredField("node_number")
        if not isinstance(self.node_number, int):
            self.node_number = int(self.node_number)

        if self._is_empty(self.bus_number):
            self.MissingRequiredField("bus_number")
        if not isinstance(self.bus_number, int):
            self.bus_number = int(self.bus_number)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.status is not None and not isinstance(self.status, int):
            self.status = int(self.status)

        if self.vm is not None and not isinstance(self.vm, float):
            self.vm = float(self.vm)

        if self.va is not None and not isinstance(self.va, float):
            self.va = float(self.va)

        if self.substation_number is not None and not isinstance(self.substation_number, int):
            self.substation_number = int(self.substation_number)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class StationSwitchingDeviceRecord(YAMLRoot):
    """
    Station switching device record; a breaker, disconnect or generic connector between two nodes of a substation
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["StationSwitchingDeviceRecord"]
    class_class_curie: ClassVar[str] = "raw:StationSwitchingDeviceRecord"
    class_name: ClassVar[str] = "StationSwitchingDeviceRecord"
    class_model_uri: ClassVar[URIRef] = RAW.StationSwitchingDeviceRecord

    from_node: int = None
    to_node: int = None
    device_type: int = None
    circuit: Optional[str] = None
    name: Optional[str] = None
    status: Optional[int] = None
    normal_status: Optional[int] = None
    reactance: Optional[float] = None
    rate1: Optional[float] = None
    rate2: Optional[float] = None
    rate3: Optional[float] = None
    substation_number: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.from_node):
            self.MissingRequiredField("from_node")
        if not isinstance(self.from_node, int):
            self.from_node = int(self.from_node)

        if self._is_empty(self.to_node):
            self.MissingRequiredField("to_node")
        if not isinstance(self.to_node, int):
            self.to_node = int(self.to_node)

        if self._is_empty(self.device_type):
            self.MissingRequiredField("device_type")
        if not isinstance(self.device_type, int):
            self.device_type = int(self.device_type)

        if self.circuit is not None and not isinstance(self.circuit, str):
            self.circuit = str(self.circuit)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.status is not None and not isinstance(self.status, int):
            self.status = int(self.status)

        if self.normal_status is not None and not isinstance(self.normal_status, int):
            self.normal_status = int(self.normal_status)

        if self.reactance is not None and not isinstance(self.reactance, float):
            self.reactance = float(self.reactance)

        if self.rate1 is not None and not isinstance(self.rate1, float):
            self.rate1 = float(self.rate1)

        if self.rate2 is not None and not isinstance(self.rate2, float):
            self.rate2 = float(self.rate2)

        if self.rate3 is not None and not isinstance(self.rate3, float):
            self.rate3 = float(self.rate3)

        if self.substation_number is not None and not isinstance(self.substation_number, int):
            self.substation_number = int(self.substation_number)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class EquipmentTerminalRecord(YAMLRoot):
    """
    Equipment terminal record connecting a piece of equipment to a substation node. One record shape covers every
    equipment form; TYP selects the form and tells which optional fields are used (J/K for branches and transformers,
    identifier for the equipment ID, CKT or NAME).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RAW["EquipmentTerminalRecord"]
    class_class_curie: ClassVar[str] = "raw:EquipmentTerminalRecord"
    class_name: ClassVar[str] = "EquipmentTerminalRecord"
    class_model_uri: ClassVar[URIRef] = RAW.EquipmentTerminalRecord

    bus_number: int = None
    node_number: int = None
    terminal_type: str = None
    j_bus: Optional[int] = None
    k_bus: Optional[int] = None
    identifier: Optional[str] = None
    substation_number: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.bus_number):
            self.MissingRequiredField("bus_number")
        if not isinstance(self.bus_number, int):
            self.bus_number = int(self.bus_number)

        if self._is_empty(self.node_number):
            self.MissingRequiredField("node_number")
        if not isinstance(self.node_number, int):
            self.node_number = int(self.node_number)

        if self._is_empty(self.terminal_type):
            self.MissingRequiredField("terminal_type")
        if not isinstance(self.terminal_type, str):
            self.terminal_type = str(self.terminal_type)

        if self.j_bus is not None and not isinstance(self.j_bus, int):
            self.j_bus = int(self.j_bus)

        if self.k_bus is not None and not isinstance(self.k_bus, int):
            self.k_bus = int(self.k_bus)

        if self.identifier is not None and not isinstance(self.identifier, str):
            self.identifier = str(self.identifier)

        if self.substation_number is not None and not isinstance(self.substation_number, int):
            self.substation_number = int(self.substation_number)

        super().__post_init__(**kwargs)


# Enumerations


# Slots
class slots:
    pass

slots.rawModel__case_record = Slot(uri=RAW.case_record, name="rawModel__case_record", curie=RAW.curie('case_record'),
                   model_uri=RAW.rawModel__case_record, domain=None, range=Union[dict, CaseIdentificationRecord])

slots.rawModel__bus_records = Slot(uri=RAW.bus_records, name="rawModel__bus_records", curie=RAW.curie('bus_records'),
                   model_uri=RAW.rawModel__bus_records, domain=None, range=Optional[Union[dict[Union[int, BusRecordBusNumber], Union[dict, BusRecord]], list[Union[dict, BusRecord]]]])

slots.rawModel__load_records = Slot(uri=RAW.load_records, name="rawModel__load_records", curie=RAW.curie('load_records'),
                   model_uri=RAW.rawModel__load_records, domain=None, range=Optional[Union[Union[dict, LoadRecord], list[Union[dict, LoadRecord]]]])

slots.rawModel__fixed_shunt_records = Slot(uri=RAW.fixed_shunt_records, name="rawModel__fixed_shunt_records", curie=RAW.curie('fixed_shunt_records'),
                   model_uri=RAW.rawModel__fixed_shunt_records, domain=None, range=Optional[Union[Union[dict, FixedShuntRecord], list[Union[dict, FixedShuntRecord]]]])

slots.rawModel__generator_records = Slot(uri=RAW.generator_records, name="rawModel__generator_records", curie=RAW.curie('generator_records'),
                   model_uri=RAW.rawModel__generator_records, domain=None, range=Optional[Union[Union[dict, GeneratorRecord], list[Union[dict, GeneratorRecord]]]])

slots.rawModel__branch_records = Slot(uri=RAW.branch_records, name="rawModel__branch_records", curie=RAW.curie('branch_records'),
                   model_uri=RAW.rawModel__branch_records, domain=None, range=Optional[Union[Union[dict, BranchRecord], list[Union[dict, BranchRecord]]]])

slots.rawModel__switch_records = Slot(uri=RAW.switch_records, name="rawModel__switch_records", curie=RAW.curie('switch_records'),
                   model_uri=RAW.rawModel__switch_records, domain=None, range=Optional[Union[Union[dict, SwitchRecord], list[Union[dict, SwitchRecord]]]])

slots.rawModel__transformer_records = Slot(uri=RAW.transformer_records, name="rawModel__transformer_records", curie=RAW.curie('transformer_records'),
                   model_uri=RAW.rawModel__transformer_records, domain=None, range=Optional[Union[Union[dict, TransformerRecord], list[Union[dict, TransformerRecord]]]])

slots.rawModel__area_interchange_records = Slot(uri=RAW.area_interchange_records, name="rawModel__area_interchange_records", curie=RAW.curie('area_interchange_records'),
                   model_uri=RAW.rawModel__area_interchange_records, domain=None, range=Optional[Union[dict[Union[int, AreaInterchangeRecordAreaNumber], Union[dict, AreaInterchangeRecord]], list[Union[dict, AreaInterchangeRecord]]]])

slots.rawModel__two_terminal_dc_records = Slot(uri=RAW.two_terminal_dc_records, name="rawModel__two_terminal_dc_records", curie=RAW.curie('two_terminal_dc_records'),
                   model_uri=RAW.rawModel__two_terminal_dc_records, domain=None, range=Optional[Union[dict[Union[str, TwoTerminalDCRecordName], Union[dict, TwoTerminalDCRecord]], list[Union[dict, TwoTerminalDCRecord]]]])

slots.rawModel__vsc_dc_records = Slot(uri=RAW.vsc_dc_records, name="rawModel__vsc_dc_records", curie=RAW.curie('vsc_dc_records'),
                   model_uri=RAW.rawModel__vsc_dc_records, domain=None, range=Optional[Union[Union[dict, VscDcRecord], list[Union[dict, VscDcRecord]]]])

slots.rawModel__impedance_correction_records = Slot(uri=RAW.impedance_correction_records, name="rawModel__impedance_correction_records", curie=RAW.curie('impedance_correction_records'),
                   model_uri=RAW.rawModel__impedance_correction_records, domain=None, range=Optional[Union[dict[Union[int, ImpedanceCorrectionRecordTableNumber], Union[dict, ImpedanceCorrectionRecord]], list[Union[dict, ImpedanceCorrectionRecord]]]])

slots.rawModel__multi_terminal_dc_records = Slot(uri=RAW.multi_terminal_dc_records, name="rawModel__multi_terminal_dc_records", curie=RAW.curie('multi_terminal_dc_records'),
                   model_uri=RAW.rawModel__multi_terminal_dc_records, domain=None, range=Optional[Union[Union[dict, MultiTerminalDCRecord], list[Union[dict, MultiTerminalDCRecord]]]])

slots.rawModel__multi_section_line_records = Slot(uri=RAW.multi_section_line_records, name="rawModel__multi_section_line_records", curie=RAW.curie('multi_section_line_records'),
                   model_uri=RAW.rawModel__multi_section_line_records, domain=None, range=Optional[Union[Union[dict, MultiSectionLineRecord], list[Union[dict, MultiSectionLineRecord]]]])

slots.rawModel__zone_records = Slot(uri=RAW.zone_records, name="rawModel__zone_records", curie=RAW.curie('zone_records'),
                   model_uri=RAW.rawModel__zone_records, domain=None, range=Optional[Union[dict[Union[int, ZoneRecordZoneNumber], Union[dict, ZoneRecord]], list[Union[dict, ZoneRecord]]]])

slots.rawModel__interarea_transfer_records = Slot(uri=RAW.interarea_transfer_records, name="rawModel__interarea_transfer_records", curie=RAW.curie('interarea_transfer_records'),
                   model_uri=RAW.rawModel__interarea_transfer_records, domain=None, range=Optional[Union[Union[dict, InterareaTransferRecord], list[Union[dict, InterareaTransferRecord]]]])

slots.rawModel__owner_records = Slot(uri=RAW.owner_records, name="rawModel__owner_records", curie=RAW.curie('owner_records'),
                   model_uri=RAW.rawModel__owner_records, domain=None, range=Optional[Union[dict[Union[int, OwnerRecordOwnerNumber], Union[dict, OwnerRecord]], list[Union[dict, OwnerRecord]]]])

slots.rawModel__facts_device_records = Slot(uri=RAW.facts_device_records, name="rawModel__facts_device_records", curie=RAW.curie('facts_device_records'),
                   model_uri=RAW.rawModel__facts_device_records, domain=None, range=Optional[Union[Union[dict, FactsDeviceRecord], list[Union[dict, FactsDeviceRecord]]]])

slots.rawModel__switched_shunt_records = Slot(uri=RAW.switched_shunt_records, name="rawModel__switched_shunt_records", curie=RAW.curie('switched_shunt_records'),
                   model_uri=RAW.rawModel__switched_shunt_records, domain=None, range=Optional[Union[Union[dict, SwitchedShuntRecord], list[Union[dict, SwitchedShuntRecord]]]])

slots.rawModel__gne_device_records = Slot(uri=RAW.gne_device_records, name="rawModel__gne_device_records", curie=RAW.curie('gne_device_records'),
                   model_uri=RAW.rawModel__gne_device_records, domain=None, range=Optional[Union[Union[dict, GneDeviceRecord], list[Union[dict, GneDeviceRecord]]]])

slots.rawModel__induction_machine_records = Slot(uri=RAW.induction_machine_records, name="rawModel__induction_machine_records", curie=RAW.curie('induction_machine_records'),
                   model_uri=RAW.rawModel__induction_machine_records, domain=None, range=Optional[Union[Union[dict, InductionMachineRecord], list[Union[dict, InductionMachineRecord]]]])

slots.rawModel__substation_records = Slot(uri=RAW.substation_records, name="rawModel__substation_records", curie=RAW.curie('substation_records'),
                   model_uri=RAW.rawModel__substation_records, domain=None, range=Optional[Union[dict[Union[int, SubstationRecordSubstationNumber], Union[dict, SubstationRecord]], list[Union[dict, SubstationRecord]]]])

slots.rawModel__substation_node_records = Slot(uri=RAW.substation_node_records, name="rawModel__substation_node_records", curie=RAW.curie('substation_node_records'),
                   model_uri=RAW.rawModel__substation_node_records, domain=None, range=Optional[Union[Union[dict, SubstationNodeRecord], list[Union[dict, SubstationNodeRecord]]]])

slots.rawModel__station_switching_device_records = Slot(uri=RAW.station_switching_device_records, name="rawModel__station_switching_device_records", curie=RAW.curie('station_switching_device_records'),
                   model_uri=RAW.rawModel__station_switching_device_records, domain=None, range=Optional[Union[Union[dict, StationSwitchingDeviceRecord], list[Union[dict, StationSwitchingDeviceRecord]]]])

slots.rawModel__equipment_terminal_records = Slot(uri=RAW.equipment_terminal_records, name="rawModel__equipment_terminal_records", curie=RAW.curie('equipment_terminal_records'),
                   model_uri=RAW.rawModel__equipment_terminal_records, domain=None, range=Optional[Union[Union[dict, EquipmentTerminalRecord], list[Union[dict, EquipmentTerminalRecord]]]])

slots.rawModel__multi_terminal_converter_records = Slot(uri=RAW.multi_terminal_converter_records, name="rawModel__multi_terminal_converter_records", curie=RAW.curie('multi_terminal_converter_records'),
                   model_uri=RAW.rawModel__multi_terminal_converter_records, domain=None, range=Optional[Union[Union[dict, MultiTerminalConverterRecord], list[Union[dict, MultiTerminalConverterRecord]]]])

slots.rawModel__multi_terminal_dc_bus_records = Slot(uri=RAW.multi_terminal_dc_bus_records, name="rawModel__multi_terminal_dc_bus_records", curie=RAW.curie('multi_terminal_dc_bus_records'),
                   model_uri=RAW.rawModel__multi_terminal_dc_bus_records, domain=None, range=Optional[Union[Union[dict, MultiTerminalDCBusRecord], list[Union[dict, MultiTerminalDCBusRecord]]]])

slots.rawModel__multi_terminal_dc_link_records = Slot(uri=RAW.multi_terminal_dc_link_records, name="rawModel__multi_terminal_dc_link_records", curie=RAW.curie('multi_terminal_dc_link_records'),
                   model_uri=RAW.rawModel__multi_terminal_dc_link_records, domain=None, range=Optional[Union[Union[dict, MultiTerminalDCLinkRecord], list[Union[dict, MultiTerminalDCLinkRecord]]]])

slots.caseIdentificationRecord__new_case_flag = Slot(uri=RAW.new_case_flag, name="caseIdentificationRecord__new_case_flag", curie=RAW.curie('new_case_flag'),
                   model_uri=RAW.caseIdentificationRecord__new_case_flag, domain=None, range=URIRef)

slots.caseIdentificationRecord__system_base_mva = Slot(uri=RAW.system_base_mva, name="caseIdentificationRecord__system_base_mva", curie=RAW.curie('system_base_mva'),
                   model_uri=RAW.caseIdentificationRecord__system_base_mva, domain=None, range=Optional[float])

slots.caseIdentificationRecord__revision = Slot(uri=RAW.revision, name="caseIdentificationRecord__revision", curie=RAW.curie('revision'),
                   model_uri=RAW.caseIdentificationRecord__revision, domain=None, range=Optional[float])

slots.caseIdentificationRecord__transformer_ratings_units = Slot(uri=RAW.transformer_ratings_units, name="caseIdentificationRecord__transformer_ratings_units", curie=RAW.curie('transformer_ratings_units'),
                   model_uri=RAW.caseIdentificationRecord__transformer_ratings_units, domain=None, range=Optional[int])

slots.caseIdentificationRecord__branch_ratings_units = Slot(uri=RAW.branch_ratings_units, name="caseIdentificationRecord__branch_ratings_units", curie=RAW.curie('branch_ratings_units'),
                   model_uri=RAW.caseIdentificationRecord__branch_ratings_units, domain=None, range=Optional[int])

slots.caseIdentificationRecord__system_base_frequency = Slot(uri=RAW.system_base_frequency, name="caseIdentificationRecord__system_base_frequency", curie=RAW.curie('system_base_frequency'),
                   model_uri=RAW.caseIdentificationRecord__system_base_frequency, domain=None, range=Optional[float])

slots.caseIdentificationRecord__titles = Slot(uri=RAW.titles, name="caseIdentificationRecord__titles", curie=RAW.curie('titles'),
                   model_uri=RAW.caseIdentificationRecord__titles, domain=None, range=Optional[Union[str, list[str]]])

slots.caseIdentificationRecord__general = Slot(uri=RAW.general, name="caseIdentificationRecord__general", curie=RAW.curie('general'),
                   model_uri=RAW.caseIdentificationRecord__general, domain=None, range=Optional[str])

slots.caseIdentificationRecord__gauss = Slot(uri=RAW.gauss, name="caseIdentificationRecord__gauss", curie=RAW.curie('gauss'),
                   model_uri=RAW.caseIdentificationRecord__gauss, domain=None, range=Optional[str])

slots.caseIdentificationRecord__newton = Slot(uri=RAW.newton, name="caseIdentificationRecord__newton", curie=RAW.curie('newton'),
                   model_uri=RAW.caseIdentificationRecord__newton, domain=None, range=Optional[str])

slots.caseIdentificationRecord__adjust = Slot(uri=RAW.adjust, name="caseIdentificationRecord__adjust", curie=RAW.curie('adjust'),
                   model_uri=RAW.caseIdentificationRecord__adjust, domain=None, range=Optional[str])

slots.caseIdentificationRecord__tysl = Slot(uri=RAW.tysl, name="caseIdentificationRecord__tysl", curie=RAW.curie('tysl'),
                   model_uri=RAW.caseIdentificationRecord__tysl, domain=None, range=Optional[str])

slots.caseIdentificationRecord__solver = Slot(uri=RAW.solver, name="caseIdentificationRecord__solver", curie=RAW.curie('solver'),
                   model_uri=RAW.caseIdentificationRecord__solver, domain=None, range=Optional[str])

slots.caseIdentificationRecord__ratings = Slot(uri=RAW.ratings, name="caseIdentificationRecord__ratings", curie=RAW.curie('ratings'),
                   model_uri=RAW.caseIdentificationRecord__ratings, domain=None, range=Optional[Union[dict[Union[int, RatingRecordRatingSetNumber], Union[dict, RatingRecord]], list[Union[dict, RatingRecord]]]])

slots.ratingRecord__rating_set_number = Slot(uri=RAW.rating_set_number, name="ratingRecord__rating_set_number", curie=RAW.curie('rating_set_number'),
                   model_uri=RAW.ratingRecord__rating_set_number, domain=None, range=URIRef)

slots.ratingRecord__rating_name = Slot(uri=RAW.rating_name, name="ratingRecord__rating_name", curie=RAW.curie('rating_name'),
                   model_uri=RAW.ratingRecord__rating_name, domain=None, range=str)

slots.ratingRecord__rating_description = Slot(uri=RAW.rating_description, name="ratingRecord__rating_description", curie=RAW.curie('rating_description'),
                   model_uri=RAW.ratingRecord__rating_description, domain=None, range=str)

slots.busRecord__bus_number = Slot(uri=RAW.bus_number, name="busRecord__bus_number", curie=RAW.curie('bus_number'),
                   model_uri=RAW.busRecord__bus_number, domain=None, range=URIRef)

slots.busRecord__name = Slot(uri=RAW.name, name="busRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.busRecord__name, domain=None, range=Optional[str])

slots.busRecord__base_voltage = Slot(uri=RAW.base_voltage, name="busRecord__base_voltage", curie=RAW.curie('base_voltage'),
                   model_uri=RAW.busRecord__base_voltage, domain=None, range=Optional[float])

slots.busRecord__bus_type = Slot(uri=RAW.bus_type, name="busRecord__bus_type", curie=RAW.curie('bus_type'),
                   model_uri=RAW.busRecord__bus_type, domain=None, range=Optional[int])

slots.busRecord__area = Slot(uri=RAW.area, name="busRecord__area", curie=RAW.curie('area'),
                   model_uri=RAW.busRecord__area, domain=None, range=Optional[int])

slots.busRecord__zone = Slot(uri=RAW.zone, name="busRecord__zone", curie=RAW.curie('zone'),
                   model_uri=RAW.busRecord__zone, domain=None, range=Optional[int])

slots.busRecord__owner = Slot(uri=RAW.owner, name="busRecord__owner", curie=RAW.curie('owner'),
                   model_uri=RAW.busRecord__owner, domain=None, range=Optional[int])

slots.busRecord__voltage_magnitude = Slot(uri=RAW.voltage_magnitude, name="busRecord__voltage_magnitude", curie=RAW.curie('voltage_magnitude'),
                   model_uri=RAW.busRecord__voltage_magnitude, domain=None, range=Optional[float])

slots.busRecord__voltage_angle = Slot(uri=RAW.voltage_angle, name="busRecord__voltage_angle", curie=RAW.curie('voltage_angle'),
                   model_uri=RAW.busRecord__voltage_angle, domain=None, range=Optional[float])

slots.busRecord__normal_voltage_magnitude_high_limit = Slot(uri=RAW.normal_voltage_magnitude_high_limit, name="busRecord__normal_voltage_magnitude_high_limit", curie=RAW.curie('normal_voltage_magnitude_high_limit'),
                   model_uri=RAW.busRecord__normal_voltage_magnitude_high_limit, domain=None, range=Optional[float])

slots.busRecord__normal_voltage_magnitude_low_limit = Slot(uri=RAW.normal_voltage_magnitude_low_limit, name="busRecord__normal_voltage_magnitude_low_limit", curie=RAW.curie('normal_voltage_magnitude_low_limit'),
                   model_uri=RAW.busRecord__normal_voltage_magnitude_low_limit, domain=None, range=Optional[float])

slots.busRecord__emergency_voltage_magnitude_high_limit = Slot(uri=RAW.emergency_voltage_magnitude_high_limit, name="busRecord__emergency_voltage_magnitude_high_limit", curie=RAW.curie('emergency_voltage_magnitude_high_limit'),
                   model_uri=RAW.busRecord__emergency_voltage_magnitude_high_limit, domain=None, range=Optional[float])

slots.busRecord__emergency_voltage_magnitude_low_limit = Slot(uri=RAW.emergency_voltage_magnitude_low_limit, name="busRecord__emergency_voltage_magnitude_low_limit", curie=RAW.curie('emergency_voltage_magnitude_low_limit'),
                   model_uri=RAW.busRecord__emergency_voltage_magnitude_low_limit, domain=None, range=Optional[float])

slots.loadRecord__bus_number = Slot(uri=RAW.bus_number, name="loadRecord__bus_number", curie=RAW.curie('bus_number'),
                   model_uri=RAW.loadRecord__bus_number, domain=None, range=int)

slots.loadRecord__load_id = Slot(uri=RAW.load_id, name="loadRecord__load_id", curie=RAW.curie('load_id'),
                   model_uri=RAW.loadRecord__load_id, domain=None, range=Optional[str])

slots.loadRecord__status = Slot(uri=RAW.status, name="loadRecord__status", curie=RAW.curie('status'),
                   model_uri=RAW.loadRecord__status, domain=None, range=Optional[int])

slots.loadRecord__area = Slot(uri=RAW.area, name="loadRecord__area", curie=RAW.curie('area'),
                   model_uri=RAW.loadRecord__area, domain=None, range=Optional[int])

slots.loadRecord__zone = Slot(uri=RAW.zone, name="loadRecord__zone", curie=RAW.curie('zone'),
                   model_uri=RAW.loadRecord__zone, domain=None, range=Optional[int])

slots.loadRecord__constant_real_power = Slot(uri=RAW.constant_real_power, name="loadRecord__constant_real_power", curie=RAW.curie('constant_real_power'),
                   model_uri=RAW.loadRecord__constant_real_power, domain=None, range=Optional[float])

slots.loadRecord__constant_imag_power = Slot(uri=RAW.constant_imag_power, name="loadRecord__constant_imag_power", curie=RAW.curie('constant_imag_power'),
                   model_uri=RAW.loadRecord__constant_imag_power, domain=None, range=Optional[float])

slots.loadRecord__constant_current_real_power = Slot(uri=RAW.constant_current_real_power, name="loadRecord__constant_current_real_power", curie=RAW.curie('constant_current_real_power'),
                   model_uri=RAW.loadRecord__constant_current_real_power, domain=None, range=Optional[float])

slots.loadRecord__constant_current_imag_power = Slot(uri=RAW.constant_current_imag_power, name="loadRecord__constant_current_imag_power", curie=RAW.curie('constant_current_imag_power'),
                   model_uri=RAW.loadRecord__constant_current_imag_power, domain=None, range=Optional[float])

slots.loadRecord__constant_admittance_real_power = Slot(uri=RAW.constant_admittance_real_power, name="loadRecord__constant_admittance_real_power", curie=RAW.curie('constant_admittance_real_power'),
                   model_uri=RAW.loadRecord__constant_admittance_real_power, domain=None, range=Optional[float])

slots.loadRecord__constant_admittance_imag_power = Slot(uri=RAW.constant_admittance_imag_power, name="loadRecord__constant_admittance_imag_power", curie=RAW.curie('constant_admittance_imag_power'),
                   model_uri=RAW.loadRecord__constant_admittance_imag_power, domain=None, range=Optional[float])

slots.loadRecord__owner = Slot(uri=RAW.owner, name="loadRecord__owner", curie=RAW.curie('owner'),
                   model_uri=RAW.loadRecord__owner, domain=None, range=Optional[int])

slots.loadRecord__scale = Slot(uri=RAW.scale, name="loadRecord__scale", curie=RAW.curie('scale'),
                   model_uri=RAW.loadRecord__scale, domain=None, range=Optional[int])

slots.loadRecord__interruptible = Slot(uri=RAW.interruptible, name="loadRecord__interruptible", curie=RAW.curie('interruptible'),
                   model_uri=RAW.loadRecord__interruptible, domain=None, range=Optional[int])

slots.loadRecord__dgenp = Slot(uri=RAW.dgenp, name="loadRecord__dgenp", curie=RAW.curie('dgenp'),
                   model_uri=RAW.loadRecord__dgenp, domain=None, range=Optional[float])

slots.loadRecord__dgenq = Slot(uri=RAW.dgenq, name="loadRecord__dgenq", curie=RAW.curie('dgenq'),
                   model_uri=RAW.loadRecord__dgenq, domain=None, range=Optional[float])

slots.loadRecord__dgenf = Slot(uri=RAW.dgenf, name="loadRecord__dgenf", curie=RAW.curie('dgenf'),
                   model_uri=RAW.loadRecord__dgenf, domain=None, range=Optional[int])

slots.fixedShuntRecord__bus_number = Slot(uri=RAW.bus_number, name="fixedShuntRecord__bus_number", curie=RAW.curie('bus_number'),
                   model_uri=RAW.fixedShuntRecord__bus_number, domain=None, range=int)

slots.fixedShuntRecord__shunt_id = Slot(uri=RAW.shunt_id, name="fixedShuntRecord__shunt_id", curie=RAW.curie('shunt_id'),
                   model_uri=RAW.fixedShuntRecord__shunt_id, domain=None, range=Optional[str])

slots.fixedShuntRecord__status = Slot(uri=RAW.status, name="fixedShuntRecord__status", curie=RAW.curie('status'),
                   model_uri=RAW.fixedShuntRecord__status, domain=None, range=Optional[int])

slots.fixedShuntRecord__gl = Slot(uri=RAW.gl, name="fixedShuntRecord__gl", curie=RAW.curie('gl'),
                   model_uri=RAW.fixedShuntRecord__gl, domain=None, range=Optional[float])

slots.fixedShuntRecord__bl = Slot(uri=RAW.bl, name="fixedShuntRecord__bl", curie=RAW.curie('bl'),
                   model_uri=RAW.fixedShuntRecord__bl, domain=None, range=Optional[float])

slots.generatorRecord__bus_number = Slot(uri=RAW.bus_number, name="generatorRecord__bus_number", curie=RAW.curie('bus_number'),
                   model_uri=RAW.generatorRecord__bus_number, domain=None, range=int)

slots.generatorRecord__gen_id = Slot(uri=RAW.gen_id, name="generatorRecord__gen_id", curie=RAW.curie('gen_id'),
                   model_uri=RAW.generatorRecord__gen_id, domain=None, range=Optional[str])

slots.generatorRecord__p_output = Slot(uri=RAW.p_output, name="generatorRecord__p_output", curie=RAW.curie('p_output'),
                   model_uri=RAW.generatorRecord__p_output, domain=None, range=Optional[float])

slots.generatorRecord__q_output = Slot(uri=RAW.q_output, name="generatorRecord__q_output", curie=RAW.curie('q_output'),
                   model_uri=RAW.generatorRecord__q_output, domain=None, range=Optional[float])

slots.generatorRecord__max_q_output = Slot(uri=RAW.max_q_output, name="generatorRecord__max_q_output", curie=RAW.curie('max_q_output'),
                   model_uri=RAW.generatorRecord__max_q_output, domain=None, range=Optional[float])

slots.generatorRecord__min_q_output = Slot(uri=RAW.min_q_output, name="generatorRecord__min_q_output", curie=RAW.curie('min_q_output'),
                   model_uri=RAW.generatorRecord__min_q_output, domain=None, range=Optional[float])

slots.generatorRecord__regulated_voltage_setpoint = Slot(uri=RAW.regulated_voltage_setpoint, name="generatorRecord__regulated_voltage_setpoint", curie=RAW.curie('regulated_voltage_setpoint'),
                   model_uri=RAW.generatorRecord__regulated_voltage_setpoint, domain=None, range=Optional[float])

slots.generatorRecord__regulated_bus_number = Slot(uri=RAW.regulated_bus_number, name="generatorRecord__regulated_bus_number", curie=RAW.curie('regulated_bus_number'),
                   model_uri=RAW.generatorRecord__regulated_bus_number, domain=None, range=Optional[int])

slots.generatorRecord__rated_mva = Slot(uri=RAW.rated_mva, name="generatorRecord__rated_mva", curie=RAW.curie('rated_mva'),
                   model_uri=RAW.generatorRecord__rated_mva, domain=None, range=Optional[float])

slots.generatorRecord__zr = Slot(uri=RAW.zr, name="generatorRecord__zr", curie=RAW.curie('zr'),
                   model_uri=RAW.generatorRecord__zr, domain=None, range=Optional[float])

slots.generatorRecord__zx = Slot(uri=RAW.zx, name="generatorRecord__zx", curie=RAW.curie('zx'),
                   model_uri=RAW.generatorRecord__zx, domain=None, range=Optional[float])

slots.generatorRecord__rt = Slot(uri=RAW.rt, name="generatorRecord__rt", curie=RAW.curie('rt'),
                   model_uri=RAW.generatorRecord__rt, domain=None, range=Optional[float])

slots.generatorRecord__xt = Slot(uri=RAW.xt, name="generatorRecord__xt", curie=RAW.curie('xt'),
                   model_uri=RAW.generatorRecord__xt, domain=None, range=Optional[float])

slots.generatorRecord__gtap = Slot(uri=RAW.gtap, name="generatorRecord__gtap", curie=RAW.curie('gtap'),
                   model_uri=RAW.generatorRecord__gtap, domain=None, range=Optional[float])

slots.generatorRecord__status = Slot(uri=RAW.status, name="generatorRecord__status", curie=RAW.curie('status'),
                   model_uri=RAW.generatorRecord__status, domain=None, range=Optional[int])

slots.generatorRecord__rmpct = Slot(uri=RAW.rmpct, name="generatorRecord__rmpct", curie=RAW.curie('rmpct'),
                   model_uri=RAW.generatorRecord__rmpct, domain=None, range=Optional[float])

slots.generatorRecord__max_p_output = Slot(uri=RAW.max_p_output, name="generatorRecord__max_p_output", curie=RAW.curie('max_p_output'),
                   model_uri=RAW.generatorRecord__max_p_output, domain=None, range=Optional[float])

slots.generatorRecord__min_p_output = Slot(uri=RAW.min_p_output, name="generatorRecord__min_p_output", curie=RAW.curie('min_p_output'),
                   model_uri=RAW.generatorRecord__min_p_output, domain=None, range=Optional[float])

slots.generatorRecord__o1 = Slot(uri=RAW.o1, name="generatorRecord__o1", curie=RAW.curie('o1'),
                   model_uri=RAW.generatorRecord__o1, domain=None, range=Optional[int])

slots.generatorRecord__f1 = Slot(uri=RAW.f1, name="generatorRecord__f1", curie=RAW.curie('f1'),
                   model_uri=RAW.generatorRecord__f1, domain=None, range=Optional[float])

slots.generatorRecord__o2 = Slot(uri=RAW.o2, name="generatorRecord__o2", curie=RAW.curie('o2'),
                   model_uri=RAW.generatorRecord__o2, domain=None, range=Optional[int])

slots.generatorRecord__f2 = Slot(uri=RAW.f2, name="generatorRecord__f2", curie=RAW.curie('f2'),
                   model_uri=RAW.generatorRecord__f2, domain=None, range=Optional[float])

slots.generatorRecord__o3 = Slot(uri=RAW.o3, name="generatorRecord__o3", curie=RAW.curie('o3'),
                   model_uri=RAW.generatorRecord__o3, domain=None, range=Optional[int])

slots.generatorRecord__f3 = Slot(uri=RAW.f3, name="generatorRecord__f3", curie=RAW.curie('f3'),
                   model_uri=RAW.generatorRecord__f3, domain=None, range=Optional[float])

slots.generatorRecord__o4 = Slot(uri=RAW.o4, name="generatorRecord__o4", curie=RAW.curie('o4'),
                   model_uri=RAW.generatorRecord__o4, domain=None, range=Optional[int])

slots.generatorRecord__f4 = Slot(uri=RAW.f4, name="generatorRecord__f4", curie=RAW.curie('f4'),
                   model_uri=RAW.generatorRecord__f4, domain=None, range=Optional[float])

slots.generatorRecord__wmod = Slot(uri=RAW.wmod, name="generatorRecord__wmod", curie=RAW.curie('wmod'),
                   model_uri=RAW.generatorRecord__wmod, domain=None, range=Optional[int])

slots.generatorRecord__wpf = Slot(uri=RAW.wpf, name="generatorRecord__wpf", curie=RAW.curie('wpf'),
                   model_uri=RAW.generatorRecord__wpf, domain=None, range=Optional[float])

slots.generatorRecord__nreg = Slot(uri=RAW.nreg, name="generatorRecord__nreg", curie=RAW.curie('nreg'),
                   model_uri=RAW.generatorRecord__nreg, domain=None, range=Optional[int])

slots.branchRecord__from_bus_number = Slot(uri=RAW.from_bus_number, name="branchRecord__from_bus_number", curie=RAW.curie('from_bus_number'),
                   model_uri=RAW.branchRecord__from_bus_number, domain=None, range=int)

slots.branchRecord__to_bus_number = Slot(uri=RAW.to_bus_number, name="branchRecord__to_bus_number", curie=RAW.curie('to_bus_number'),
                   model_uri=RAW.branchRecord__to_bus_number, domain=None, range=int)

slots.branchRecord__circuit = Slot(uri=RAW.circuit, name="branchRecord__circuit", curie=RAW.curie('circuit'),
                   model_uri=RAW.branchRecord__circuit, domain=None, range=Optional[str])

slots.branchRecord__r = Slot(uri=RAW.r, name="branchRecord__r", curie=RAW.curie('r'),
                   model_uri=RAW.branchRecord__r, domain=None, range=float)

slots.branchRecord__x = Slot(uri=RAW.x, name="branchRecord__x", curie=RAW.curie('x'),
                   model_uri=RAW.branchRecord__x, domain=None, range=float)

slots.branchRecord__b = Slot(uri=RAW.b, name="branchRecord__b", curie=RAW.curie('b'),
                   model_uri=RAW.branchRecord__b, domain=None, range=Optional[float])

slots.branchRecord__name = Slot(uri=RAW.name, name="branchRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.branchRecord__name, domain=None, range=Optional[str])

slots.branchRecord__ratings = Slot(uri=RAW.ratings, name="branchRecord__ratings", curie=RAW.curie('ratings'),
                   model_uri=RAW.branchRecord__ratings, domain=None, range=Optional[Union[float, list[float]]])

slots.branchRecord__g_from = Slot(uri=RAW.g_from, name="branchRecord__g_from", curie=RAW.curie('g_from'),
                   model_uri=RAW.branchRecord__g_from, domain=None, range=Optional[float])

slots.branchRecord__b_from = Slot(uri=RAW.b_from, name="branchRecord__b_from", curie=RAW.curie('b_from'),
                   model_uri=RAW.branchRecord__b_from, domain=None, range=Optional[float])

slots.branchRecord__g_to = Slot(uri=RAW.g_to, name="branchRecord__g_to", curie=RAW.curie('g_to'),
                   model_uri=RAW.branchRecord__g_to, domain=None, range=Optional[float])

slots.branchRecord__b_to = Slot(uri=RAW.b_to, name="branchRecord__b_to", curie=RAW.curie('b_to'),
                   model_uri=RAW.branchRecord__b_to, domain=None, range=Optional[float])

slots.branchRecord__status = Slot(uri=RAW.status, name="branchRecord__status", curie=RAW.curie('status'),
                   model_uri=RAW.branchRecord__status, domain=None, range=Optional[int])

slots.branchRecord__metered_end = Slot(uri=RAW.metered_end, name="branchRecord__metered_end", curie=RAW.curie('metered_end'),
                   model_uri=RAW.branchRecord__metered_end, domain=None, range=Optional[int])

slots.branchRecord__length = Slot(uri=RAW.length, name="branchRecord__length", curie=RAW.curie('length'),
                   model_uri=RAW.branchRecord__length, domain=None, range=Optional[float])

slots.branchRecord__o1 = Slot(uri=RAW.o1, name="branchRecord__o1", curie=RAW.curie('o1'),
                   model_uri=RAW.branchRecord__o1, domain=None, range=Optional[int])

slots.branchRecord__f1 = Slot(uri=RAW.f1, name="branchRecord__f1", curie=RAW.curie('f1'),
                   model_uri=RAW.branchRecord__f1, domain=None, range=Optional[float])

slots.branchRecord__o2 = Slot(uri=RAW.o2, name="branchRecord__o2", curie=RAW.curie('o2'),
                   model_uri=RAW.branchRecord__o2, domain=None, range=Optional[int])

slots.branchRecord__f2 = Slot(uri=RAW.f2, name="branchRecord__f2", curie=RAW.curie('f2'),
                   model_uri=RAW.branchRecord__f2, domain=None, range=Optional[float])

slots.branchRecord__o3 = Slot(uri=RAW.o3, name="branchRecord__o3", curie=RAW.curie('o3'),
                   model_uri=RAW.branchRecord__o3, domain=None, range=Optional[int])

slots.branchRecord__f3 = Slot(uri=RAW.f3, name="branchRecord__f3", curie=RAW.curie('f3'),
                   model_uri=RAW.branchRecord__f3, domain=None, range=Optional[float])

slots.branchRecord__o4 = Slot(uri=RAW.o4, name="branchRecord__o4", curie=RAW.curie('o4'),
                   model_uri=RAW.branchRecord__o4, domain=None, range=Optional[int])

slots.branchRecord__f4 = Slot(uri=RAW.f4, name="branchRecord__f4", curie=RAW.curie('f4'),
                   model_uri=RAW.branchRecord__f4, domain=None, range=Optional[float])

slots.switchRecord__from_bus_number = Slot(uri=RAW.from_bus_number, name="switchRecord__from_bus_number", curie=RAW.curie('from_bus_number'),
                   model_uri=RAW.switchRecord__from_bus_number, domain=None, range=int)

slots.switchRecord__to_bus_number = Slot(uri=RAW.to_bus_number, name="switchRecord__to_bus_number", curie=RAW.curie('to_bus_number'),
                   model_uri=RAW.switchRecord__to_bus_number, domain=None, range=int)

slots.switchRecord__circuit = Slot(uri=RAW.circuit, name="switchRecord__circuit", curie=RAW.curie('circuit'),
                   model_uri=RAW.switchRecord__circuit, domain=None, range=Optional[str])

slots.switchRecord__x = Slot(uri=RAW.x, name="switchRecord__x", curie=RAW.curie('x'),
                   model_uri=RAW.switchRecord__x, domain=None, range=Optional[float])

slots.switchRecord__ratings = Slot(uri=RAW.ratings, name="switchRecord__ratings", curie=RAW.curie('ratings'),
                   model_uri=RAW.switchRecord__ratings, domain=None, range=Optional[Union[float, list[float]]])

slots.switchRecord__status = Slot(uri=RAW.status, name="switchRecord__status", curie=RAW.curie('status'),
                   model_uri=RAW.switchRecord__status, domain=None, range=Optional[int])

slots.switchRecord__nstat = Slot(uri=RAW.nstat, name="switchRecord__nstat", curie=RAW.curie('nstat'),
                   model_uri=RAW.switchRecord__nstat, domain=None, range=Optional[int])

slots.switchRecord__metered_end = Slot(uri=RAW.metered_end, name="switchRecord__metered_end", curie=RAW.curie('metered_end'),
                   model_uri=RAW.switchRecord__metered_end, domain=None, range=Optional[int])

slots.switchRecord__stype = Slot(uri=RAW.stype, name="switchRecord__stype", curie=RAW.curie('stype'),
                   model_uri=RAW.switchRecord__stype, domain=None, range=Optional[int])

slots.switchRecord__name = Slot(uri=RAW.name, name="switchRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.switchRecord__name, domain=None, range=Optional[str])

slots.transformerRecord__i = Slot(uri=RAW.i, name="transformerRecord__i", curie=RAW.curie('i'),
                   model_uri=RAW.transformerRecord__i, domain=None, range=int)

slots.transformerRecord__j = Slot(uri=RAW.j, name="transformerRecord__j", curie=RAW.curie('j'),
                   model_uri=RAW.transformerRecord__j, domain=None, range=int)

slots.transformerRecord__k = Slot(uri=RAW.k, name="transformerRecord__k", curie=RAW.curie('k'),
                   model_uri=RAW.transformerRecord__k, domain=None, range=Optional[int])

slots.transformerRecord__circuit = Slot(uri=RAW.circuit, name="transformerRecord__circuit", curie=RAW.curie('circuit'),
                   model_uri=RAW.transformerRecord__circuit, domain=None, range=Optional[str])

slots.transformerRecord__cw = Slot(uri=RAW.cw, name="transformerRecord__cw", curie=RAW.curie('cw'),
                   model_uri=RAW.transformerRecord__cw, domain=None, range=Optional[int])

slots.transformerRecord__cz = Slot(uri=RAW.cz, name="transformerRecord__cz", curie=RAW.curie('cz'),
                   model_uri=RAW.transformerRecord__cz, domain=None, range=Optional[int])

slots.transformerRecord__cm = Slot(uri=RAW.cm, name="transformerRecord__cm", curie=RAW.curie('cm'),
                   model_uri=RAW.transformerRecord__cm, domain=None, range=Optional[int])

slots.transformerRecord__mag1 = Slot(uri=RAW.mag1, name="transformerRecord__mag1", curie=RAW.curie('mag1'),
                   model_uri=RAW.transformerRecord__mag1, domain=None, range=Optional[float])

slots.transformerRecord__mag2 = Slot(uri=RAW.mag2, name="transformerRecord__mag2", curie=RAW.curie('mag2'),
                   model_uri=RAW.transformerRecord__mag2, domain=None, range=Optional[float])

slots.transformerRecord__nmetr = Slot(uri=RAW.nmetr, name="transformerRecord__nmetr", curie=RAW.curie('nmetr'),
                   model_uri=RAW.transformerRecord__nmetr, domain=None, range=Optional[int])

slots.transformerRecord__name = Slot(uri=RAW.name, name="transformerRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.transformerRecord__name, domain=None, range=Optional[str])

slots.transformerRecord__status = Slot(uri=RAW.status, name="transformerRecord__status", curie=RAW.curie('status'),
                   model_uri=RAW.transformerRecord__status, domain=None, range=Optional[int])

slots.transformerRecord__o1 = Slot(uri=RAW.o1, name="transformerRecord__o1", curie=RAW.curie('o1'),
                   model_uri=RAW.transformerRecord__o1, domain=None, range=Optional[int])

slots.transformerRecord__f1 = Slot(uri=RAW.f1, name="transformerRecord__f1", curie=RAW.curie('f1'),
                   model_uri=RAW.transformerRecord__f1, domain=None, range=Optional[float])

slots.transformerRecord__o2 = Slot(uri=RAW.o2, name="transformerRecord__o2", curie=RAW.curie('o2'),
                   model_uri=RAW.transformerRecord__o2, domain=None, range=Optional[int])

slots.transformerRecord__f2 = Slot(uri=RAW.f2, name="transformerRecord__f2", curie=RAW.curie('f2'),
                   model_uri=RAW.transformerRecord__f2, domain=None, range=Optional[float])

slots.transformerRecord__o3 = Slot(uri=RAW.o3, name="transformerRecord__o3", curie=RAW.curie('o3'),
                   model_uri=RAW.transformerRecord__o3, domain=None, range=Optional[int])

slots.transformerRecord__f3 = Slot(uri=RAW.f3, name="transformerRecord__f3", curie=RAW.curie('f3'),
                   model_uri=RAW.transformerRecord__f3, domain=None, range=Optional[float])

slots.transformerRecord__o4 = Slot(uri=RAW.o4, name="transformerRecord__o4", curie=RAW.curie('o4'),
                   model_uri=RAW.transformerRecord__o4, domain=None, range=Optional[int])

slots.transformerRecord__f4 = Slot(uri=RAW.f4, name="transformerRecord__f4", curie=RAW.curie('f4'),
                   model_uri=RAW.transformerRecord__f4, domain=None, range=Optional[float])

slots.transformerRecord__vecgrp = Slot(uri=RAW.vecgrp, name="transformerRecord__vecgrp", curie=RAW.curie('vecgrp'),
                   model_uri=RAW.transformerRecord__vecgrp, domain=None, range=Optional[str])

slots.transformerRecord__zcod = Slot(uri=RAW.zcod, name="transformerRecord__zcod", curie=RAW.curie('zcod'),
                   model_uri=RAW.transformerRecord__zcod, domain=None, range=Optional[int])

slots.transformerRecord__r1_2 = Slot(uri=RAW.r1_2, name="transformerRecord__r1_2", curie=RAW.curie('r1_2'),
                   model_uri=RAW.transformerRecord__r1_2, domain=None, range=Optional[float])

slots.transformerRecord__x1_2 = Slot(uri=RAW.x1_2, name="transformerRecord__x1_2", curie=RAW.curie('x1_2'),
                   model_uri=RAW.transformerRecord__x1_2, domain=None, range=float)

slots.transformerRecord__sbase1_2 = Slot(uri=RAW.sbase1_2, name="transformerRecord__sbase1_2", curie=RAW.curie('sbase1_2'),
                   model_uri=RAW.transformerRecord__sbase1_2, domain=None, range=Optional[float])

slots.transformerRecord__r2_3 = Slot(uri=RAW.r2_3, name="transformerRecord__r2_3", curie=RAW.curie('r2_3'),
                   model_uri=RAW.transformerRecord__r2_3, domain=None, range=Optional[float])

slots.transformerRecord__x2_3 = Slot(uri=RAW.x2_3, name="transformerRecord__x2_3", curie=RAW.curie('x2_3'),
                   model_uri=RAW.transformerRecord__x2_3, domain=None, range=Optional[float])

slots.transformerRecord__sbase2_3 = Slot(uri=RAW.sbase2_3, name="transformerRecord__sbase2_3", curie=RAW.curie('sbase2_3'),
                   model_uri=RAW.transformerRecord__sbase2_3, domain=None, range=Optional[float])

slots.transformerRecord__r3_1 = Slot(uri=RAW.r3_1, name="transformerRecord__r3_1", curie=RAW.curie('r3_1'),
                   model_uri=RAW.transformerRecord__r3_1, domain=None, range=Optional[float])

slots.transformerRecord__x3_1 = Slot(uri=RAW.x3_1, name="transformerRecord__x3_1", curie=RAW.curie('x3_1'),
                   model_uri=RAW.transformerRecord__x3_1, domain=None, range=Optional[float])

slots.transformerRecord__sbase3_1 = Slot(uri=RAW.sbase3_1, name="transformerRecord__sbase3_1", curie=RAW.curie('sbase3_1'),
                   model_uri=RAW.transformerRecord__sbase3_1, domain=None, range=Optional[float])

slots.transformerRecord__vmstar = Slot(uri=RAW.vmstar, name="transformerRecord__vmstar", curie=RAW.curie('vmstar'),
                   model_uri=RAW.transformerRecord__vmstar, domain=None, range=Optional[float])

slots.transformerRecord__anstar = Slot(uri=RAW.anstar, name="transformerRecord__anstar", curie=RAW.curie('anstar'),
                   model_uri=RAW.transformerRecord__anstar, domain=None, range=Optional[float])

slots.transformerRecord__windv1 = Slot(uri=RAW.windv1, name="transformerRecord__windv1", curie=RAW.curie('windv1'),
                   model_uri=RAW.transformerRecord__windv1, domain=None, range=Optional[float])

slots.transformerRecord__nomv1 = Slot(uri=RAW.nomv1, name="transformerRecord__nomv1", curie=RAW.curie('nomv1'),
                   model_uri=RAW.transformerRecord__nomv1, domain=None, range=Optional[float])

slots.transformerRecord__ang1 = Slot(uri=RAW.ang1, name="transformerRecord__ang1", curie=RAW.curie('ang1'),
                   model_uri=RAW.transformerRecord__ang1, domain=None, range=Optional[float])

slots.transformerRecord__rate1_1 = Slot(uri=RAW.rate1_1, name="transformerRecord__rate1_1", curie=RAW.curie('rate1_1'),
                   model_uri=RAW.transformerRecord__rate1_1, domain=None, range=Optional[float])

slots.transformerRecord__rate1_2 = Slot(uri=RAW.rate1_2, name="transformerRecord__rate1_2", curie=RAW.curie('rate1_2'),
                   model_uri=RAW.transformerRecord__rate1_2, domain=None, range=Optional[float])

slots.transformerRecord__rate1_3 = Slot(uri=RAW.rate1_3, name="transformerRecord__rate1_3", curie=RAW.curie('rate1_3'),
                   model_uri=RAW.transformerRecord__rate1_3, domain=None, range=Optional[float])

slots.transformerRecord__rate1_4 = Slot(uri=RAW.rate1_4, name="transformerRecord__rate1_4", curie=RAW.curie('rate1_4'),
                   model_uri=RAW.transformerRecord__rate1_4, domain=None, range=Optional[float])

slots.transformerRecord__rate1_5 = Slot(uri=RAW.rate1_5, name="transformerRecord__rate1_5", curie=RAW.curie('rate1_5'),
                   model_uri=RAW.transformerRecord__rate1_5, domain=None, range=Optional[float])

slots.transformerRecord__rate1_6 = Slot(uri=RAW.rate1_6, name="transformerRecord__rate1_6", curie=RAW.curie('rate1_6'),
                   model_uri=RAW.transformerRecord__rate1_6, domain=None, range=Optional[float])

slots.transformerRecord__rate1_7 = Slot(uri=RAW.rate1_7, name="transformerRecord__rate1_7", curie=RAW.curie('rate1_7'),
                   model_uri=RAW.transformerRecord__rate1_7, domain=None, range=Optional[float])

slots.transformerRecord__rate1_8 = Slot(uri=RAW.rate1_8, name="transformerRecord__rate1_8", curie=RAW.curie('rate1_8'),
                   model_uri=RAW.transformerRecord__rate1_8, domain=None, range=Optional[float])

slots.transformerRecord__rate1_9 = Slot(uri=RAW.rate1_9, name="transformerRecord__rate1_9", curie=RAW.curie('rate1_9'),
                   model_uri=RAW.transformerRecord__rate1_9, domain=None, range=Optional[float])

slots.transformerRecord__rate1_10 = Slot(uri=RAW.rate1_10, name="transformerRecord__rate1_10", curie=RAW.curie('rate1_10'),
                   model_uri=RAW.transformerRecord__rate1_10, domain=None, range=Optional[float])

slots.transformerRecord__rate1_11 = Slot(uri=RAW.rate1_11, name="transformerRecord__rate1_11", curie=RAW.curie('rate1_11'),
                   model_uri=RAW.transformerRecord__rate1_11, domain=None, range=Optional[float])

slots.transformerRecord__rate1_12 = Slot(uri=RAW.rate1_12, name="transformerRecord__rate1_12", curie=RAW.curie('rate1_12'),
                   model_uri=RAW.transformerRecord__rate1_12, domain=None, range=Optional[float])

slots.transformerRecord__cod1 = Slot(uri=RAW.cod1, name="transformerRecord__cod1", curie=RAW.curie('cod1'),
                   model_uri=RAW.transformerRecord__cod1, domain=None, range=Optional[int])

slots.transformerRecord__cont1 = Slot(uri=RAW.cont1, name="transformerRecord__cont1", curie=RAW.curie('cont1'),
                   model_uri=RAW.transformerRecord__cont1, domain=None, range=Optional[int])

slots.transformerRecord__rma1 = Slot(uri=RAW.rma1, name="transformerRecord__rma1", curie=RAW.curie('rma1'),
                   model_uri=RAW.transformerRecord__rma1, domain=None, range=Optional[float])

slots.transformerRecord__rmi1 = Slot(uri=RAW.rmi1, name="transformerRecord__rmi1", curie=RAW.curie('rmi1'),
                   model_uri=RAW.transformerRecord__rmi1, domain=None, range=Optional[float])

slots.transformerRecord__vma1 = Slot(uri=RAW.vma1, name="transformerRecord__vma1", curie=RAW.curie('vma1'),
                   model_uri=RAW.transformerRecord__vma1, domain=None, range=Optional[float])

slots.transformerRecord__vmi1 = Slot(uri=RAW.vmi1, name="transformerRecord__vmi1", curie=RAW.curie('vmi1'),
                   model_uri=RAW.transformerRecord__vmi1, domain=None, range=Optional[float])

slots.transformerRecord__ntp1 = Slot(uri=RAW.ntp1, name="transformerRecord__ntp1", curie=RAW.curie('ntp1'),
                   model_uri=RAW.transformerRecord__ntp1, domain=None, range=Optional[int])

slots.transformerRecord__tab1 = Slot(uri=RAW.tab1, name="transformerRecord__tab1", curie=RAW.curie('tab1'),
                   model_uri=RAW.transformerRecord__tab1, domain=None, range=Optional[int])

slots.transformerRecord__cr1 = Slot(uri=RAW.cr1, name="transformerRecord__cr1", curie=RAW.curie('cr1'),
                   model_uri=RAW.transformerRecord__cr1, domain=None, range=Optional[float])

slots.transformerRecord__cx1 = Slot(uri=RAW.cx1, name="transformerRecord__cx1", curie=RAW.curie('cx1'),
                   model_uri=RAW.transformerRecord__cx1, domain=None, range=Optional[float])

slots.transformerRecord__cnxa1 = Slot(uri=RAW.cnxa1, name="transformerRecord__cnxa1", curie=RAW.curie('cnxa1'),
                   model_uri=RAW.transformerRecord__cnxa1, domain=None, range=Optional[float])

slots.transformerRecord__nod1 = Slot(uri=RAW.nod1, name="transformerRecord__nod1", curie=RAW.curie('nod1'),
                   model_uri=RAW.transformerRecord__nod1, domain=None, range=Optional[int])

slots.transformerRecord__windv2 = Slot(uri=RAW.windv2, name="transformerRecord__windv2", curie=RAW.curie('windv2'),
                   model_uri=RAW.transformerRecord__windv2, domain=None, range=Optional[float])

slots.transformerRecord__nomv2 = Slot(uri=RAW.nomv2, name="transformerRecord__nomv2", curie=RAW.curie('nomv2'),
                   model_uri=RAW.transformerRecord__nomv2, domain=None, range=Optional[float])

slots.transformerRecord__ang2 = Slot(uri=RAW.ang2, name="transformerRecord__ang2", curie=RAW.curie('ang2'),
                   model_uri=RAW.transformerRecord__ang2, domain=None, range=Optional[float])

slots.transformerRecord__rate2_1 = Slot(uri=RAW.rate2_1, name="transformerRecord__rate2_1", curie=RAW.curie('rate2_1'),
                   model_uri=RAW.transformerRecord__rate2_1, domain=None, range=Optional[float])

slots.transformerRecord__rate2_2 = Slot(uri=RAW.rate2_2, name="transformerRecord__rate2_2", curie=RAW.curie('rate2_2'),
                   model_uri=RAW.transformerRecord__rate2_2, domain=None, range=Optional[float])

slots.transformerRecord__rate2_3 = Slot(uri=RAW.rate2_3, name="transformerRecord__rate2_3", curie=RAW.curie('rate2_3'),
                   model_uri=RAW.transformerRecord__rate2_3, domain=None, range=Optional[float])

slots.transformerRecord__rate2_4 = Slot(uri=RAW.rate2_4, name="transformerRecord__rate2_4", curie=RAW.curie('rate2_4'),
                   model_uri=RAW.transformerRecord__rate2_4, domain=None, range=Optional[float])

slots.transformerRecord__rate2_5 = Slot(uri=RAW.rate2_5, name="transformerRecord__rate2_5", curie=RAW.curie('rate2_5'),
                   model_uri=RAW.transformerRecord__rate2_5, domain=None, range=Optional[float])

slots.transformerRecord__rate2_6 = Slot(uri=RAW.rate2_6, name="transformerRecord__rate2_6", curie=RAW.curie('rate2_6'),
                   model_uri=RAW.transformerRecord__rate2_6, domain=None, range=Optional[float])

slots.transformerRecord__rate2_7 = Slot(uri=RAW.rate2_7, name="transformerRecord__rate2_7", curie=RAW.curie('rate2_7'),
                   model_uri=RAW.transformerRecord__rate2_7, domain=None, range=Optional[float])

slots.transformerRecord__rate2_8 = Slot(uri=RAW.rate2_8, name="transformerRecord__rate2_8", curie=RAW.curie('rate2_8'),
                   model_uri=RAW.transformerRecord__rate2_8, domain=None, range=Optional[float])

slots.transformerRecord__rate2_9 = Slot(uri=RAW.rate2_9, name="transformerRecord__rate2_9", curie=RAW.curie('rate2_9'),
                   model_uri=RAW.transformerRecord__rate2_9, domain=None, range=Optional[float])

slots.transformerRecord__rate2_10 = Slot(uri=RAW.rate2_10, name="transformerRecord__rate2_10", curie=RAW.curie('rate2_10'),
                   model_uri=RAW.transformerRecord__rate2_10, domain=None, range=Optional[float])

slots.transformerRecord__rate2_11 = Slot(uri=RAW.rate2_11, name="transformerRecord__rate2_11", curie=RAW.curie('rate2_11'),
                   model_uri=RAW.transformerRecord__rate2_11, domain=None, range=Optional[float])

slots.transformerRecord__rate2_12 = Slot(uri=RAW.rate2_12, name="transformerRecord__rate2_12", curie=RAW.curie('rate2_12'),
                   model_uri=RAW.transformerRecord__rate2_12, domain=None, range=Optional[float])

slots.transformerRecord__cod2 = Slot(uri=RAW.cod2, name="transformerRecord__cod2", curie=RAW.curie('cod2'),
                   model_uri=RAW.transformerRecord__cod2, domain=None, range=Optional[int])

slots.transformerRecord__cont2 = Slot(uri=RAW.cont2, name="transformerRecord__cont2", curie=RAW.curie('cont2'),
                   model_uri=RAW.transformerRecord__cont2, domain=None, range=Optional[int])

slots.transformerRecord__rma2 = Slot(uri=RAW.rma2, name="transformerRecord__rma2", curie=RAW.curie('rma2'),
                   model_uri=RAW.transformerRecord__rma2, domain=None, range=Optional[float])

slots.transformerRecord__rmi2 = Slot(uri=RAW.rmi2, name="transformerRecord__rmi2", curie=RAW.curie('rmi2'),
                   model_uri=RAW.transformerRecord__rmi2, domain=None, range=Optional[float])

slots.transformerRecord__vma2 = Slot(uri=RAW.vma2, name="transformerRecord__vma2", curie=RAW.curie('vma2'),
                   model_uri=RAW.transformerRecord__vma2, domain=None, range=Optional[float])

slots.transformerRecord__vmi2 = Slot(uri=RAW.vmi2, name="transformerRecord__vmi2", curie=RAW.curie('vmi2'),
                   model_uri=RAW.transformerRecord__vmi2, domain=None, range=Optional[float])

slots.transformerRecord__ntp2 = Slot(uri=RAW.ntp2, name="transformerRecord__ntp2", curie=RAW.curie('ntp2'),
                   model_uri=RAW.transformerRecord__ntp2, domain=None, range=Optional[int])

slots.transformerRecord__tab2 = Slot(uri=RAW.tab2, name="transformerRecord__tab2", curie=RAW.curie('tab2'),
                   model_uri=RAW.transformerRecord__tab2, domain=None, range=Optional[int])

slots.transformerRecord__cr2 = Slot(uri=RAW.cr2, name="transformerRecord__cr2", curie=RAW.curie('cr2'),
                   model_uri=RAW.transformerRecord__cr2, domain=None, range=Optional[float])

slots.transformerRecord__cx2 = Slot(uri=RAW.cx2, name="transformerRecord__cx2", curie=RAW.curie('cx2'),
                   model_uri=RAW.transformerRecord__cx2, domain=None, range=Optional[float])

slots.transformerRecord__cnxa2 = Slot(uri=RAW.cnxa2, name="transformerRecord__cnxa2", curie=RAW.curie('cnxa2'),
                   model_uri=RAW.transformerRecord__cnxa2, domain=None, range=Optional[float])

slots.transformerRecord__nod2 = Slot(uri=RAW.nod2, name="transformerRecord__nod2", curie=RAW.curie('nod2'),
                   model_uri=RAW.transformerRecord__nod2, domain=None, range=Optional[int])

slots.transformerRecord__windv3 = Slot(uri=RAW.windv3, name="transformerRecord__windv3", curie=RAW.curie('windv3'),
                   model_uri=RAW.transformerRecord__windv3, domain=None, range=Optional[float])

slots.transformerRecord__nomv3 = Slot(uri=RAW.nomv3, name="transformerRecord__nomv3", curie=RAW.curie('nomv3'),
                   model_uri=RAW.transformerRecord__nomv3, domain=None, range=Optional[float])

slots.transformerRecord__ang3 = Slot(uri=RAW.ang3, name="transformerRecord__ang3", curie=RAW.curie('ang3'),
                   model_uri=RAW.transformerRecord__ang3, domain=None, range=Optional[float])

slots.transformerRecord__rate3_1 = Slot(uri=RAW.rate3_1, name="transformerRecord__rate3_1", curie=RAW.curie('rate3_1'),
                   model_uri=RAW.transformerRecord__rate3_1, domain=None, range=Optional[float])

slots.transformerRecord__rate3_2 = Slot(uri=RAW.rate3_2, name="transformerRecord__rate3_2", curie=RAW.curie('rate3_2'),
                   model_uri=RAW.transformerRecord__rate3_2, domain=None, range=Optional[float])

slots.transformerRecord__rate3_3 = Slot(uri=RAW.rate3_3, name="transformerRecord__rate3_3", curie=RAW.curie('rate3_3'),
                   model_uri=RAW.transformerRecord__rate3_3, domain=None, range=Optional[float])

slots.transformerRecord__rate3_4 = Slot(uri=RAW.rate3_4, name="transformerRecord__rate3_4", curie=RAW.curie('rate3_4'),
                   model_uri=RAW.transformerRecord__rate3_4, domain=None, range=Optional[float])

slots.transformerRecord__rate3_5 = Slot(uri=RAW.rate3_5, name="transformerRecord__rate3_5", curie=RAW.curie('rate3_5'),
                   model_uri=RAW.transformerRecord__rate3_5, domain=None, range=Optional[float])

slots.transformerRecord__rate3_6 = Slot(uri=RAW.rate3_6, name="transformerRecord__rate3_6", curie=RAW.curie('rate3_6'),
                   model_uri=RAW.transformerRecord__rate3_6, domain=None, range=Optional[float])

slots.transformerRecord__rate3_7 = Slot(uri=RAW.rate3_7, name="transformerRecord__rate3_7", curie=RAW.curie('rate3_7'),
                   model_uri=RAW.transformerRecord__rate3_7, domain=None, range=Optional[float])

slots.transformerRecord__rate3_8 = Slot(uri=RAW.rate3_8, name="transformerRecord__rate3_8", curie=RAW.curie('rate3_8'),
                   model_uri=RAW.transformerRecord__rate3_8, domain=None, range=Optional[float])

slots.transformerRecord__rate3_9 = Slot(uri=RAW.rate3_9, name="transformerRecord__rate3_9", curie=RAW.curie('rate3_9'),
                   model_uri=RAW.transformerRecord__rate3_9, domain=None, range=Optional[float])

slots.transformerRecord__rate3_10 = Slot(uri=RAW.rate3_10, name="transformerRecord__rate3_10", curie=RAW.curie('rate3_10'),
                   model_uri=RAW.transformerRecord__rate3_10, domain=None, range=Optional[float])

slots.transformerRecord__rate3_11 = Slot(uri=RAW.rate3_11, name="transformerRecord__rate3_11", curie=RAW.curie('rate3_11'),
                   model_uri=RAW.transformerRecord__rate3_11, domain=None, range=Optional[float])

slots.transformerRecord__rate3_12 = Slot(uri=RAW.rate3_12, name="transformerRecord__rate3_12", curie=RAW.curie('rate3_12'),
                   model_uri=RAW.transformerRecord__rate3_12, domain=None, range=Optional[float])

slots.transformerRecord__cod3 = Slot(uri=RAW.cod3, name="transformerRecord__cod3", curie=RAW.curie('cod3'),
                   model_uri=RAW.transformerRecord__cod3, domain=None, range=Optional[int])

slots.transformerRecord__cont3 = Slot(uri=RAW.cont3, name="transformerRecord__cont3", curie=RAW.curie('cont3'),
                   model_uri=RAW.transformerRecord__cont3, domain=None, range=Optional[int])

slots.transformerRecord__rma3 = Slot(uri=RAW.rma3, name="transformerRecord__rma3", curie=RAW.curie('rma3'),
                   model_uri=RAW.transformerRecord__rma3, domain=None, range=Optional[float])

slots.transformerRecord__rmi3 = Slot(uri=RAW.rmi3, name="transformerRecord__rmi3", curie=RAW.curie('rmi3'),
                   model_uri=RAW.transformerRecord__rmi3, domain=None, range=Optional[float])

slots.transformerRecord__vma3 = Slot(uri=RAW.vma3, name="transformerRecord__vma3", curie=RAW.curie('vma3'),
                   model_uri=RAW.transformerRecord__vma3, domain=None, range=Optional[float])

slots.transformerRecord__vmi3 = Slot(uri=RAW.vmi3, name="transformerRecord__vmi3", curie=RAW.curie('vmi3'),
                   model_uri=RAW.transformerRecord__vmi3, domain=None, range=Optional[float])

slots.transformerRecord__ntp3 = Slot(uri=RAW.ntp3, name="transformerRecord__ntp3", curie=RAW.curie('ntp3'),
                   model_uri=RAW.transformerRecord__ntp3, domain=None, range=Optional[int])

slots.transformerRecord__tab3 = Slot(uri=RAW.tab3, name="transformerRecord__tab3", curie=RAW.curie('tab3'),
                   model_uri=RAW.transformerRecord__tab3, domain=None, range=Optional[int])

slots.transformerRecord__cr3 = Slot(uri=RAW.cr3, name="transformerRecord__cr3", curie=RAW.curie('cr3'),
                   model_uri=RAW.transformerRecord__cr3, domain=None, range=Optional[float])

slots.transformerRecord__cx3 = Slot(uri=RAW.cx3, name="transformerRecord__cx3", curie=RAW.curie('cx3'),
                   model_uri=RAW.transformerRecord__cx3, domain=None, range=Optional[float])

slots.transformerRecord__cnxa3 = Slot(uri=RAW.cnxa3, name="transformerRecord__cnxa3", curie=RAW.curie('cnxa3'),
                   model_uri=RAW.transformerRecord__cnxa3, domain=None, range=Optional[float])

slots.transformerRecord__nod3 = Slot(uri=RAW.nod3, name="transformerRecord__nod3", curie=RAW.curie('nod3'),
                   model_uri=RAW.transformerRecord__nod3, domain=None, range=Optional[int])

slots.areaInterchangeRecord__area_number = Slot(uri=RAW.area_number, name="areaInterchangeRecord__area_number", curie=RAW.curie('area_number'),
                   model_uri=RAW.areaInterchangeRecord__area_number, domain=None, range=URIRef)

slots.areaInterchangeRecord__bus_number = Slot(uri=RAW.bus_number, name="areaInterchangeRecord__bus_number", curie=RAW.curie('bus_number'),
                   model_uri=RAW.areaInterchangeRecord__bus_number, domain=None, range=Optional[int])

slots.areaInterchangeRecord__pdes = Slot(uri=RAW.pdes, name="areaInterchangeRecord__pdes", curie=RAW.curie('pdes'),
                   model_uri=RAW.areaInterchangeRecord__pdes, domain=None, range=Optional[float])

slots.areaInterchangeRecord__ptol = Slot(uri=RAW.ptol, name="areaInterchangeRecord__ptol", curie=RAW.curie('ptol'),
                   model_uri=RAW.areaInterchangeRecord__ptol, domain=None, range=Optional[float])

slots.areaInterchangeRecord__name = Slot(uri=RAW.name, name="areaInterchangeRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.areaInterchangeRecord__name, domain=None, range=Optional[str])

slots.twoTerminalDCRecord__name = Slot(uri=RAW.name, name="twoTerminalDCRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.twoTerminalDCRecord__name, domain=None, range=URIRef)

slots.twoTerminalDCRecord__mdc = Slot(uri=RAW.mdc, name="twoTerminalDCRecord__mdc", curie=RAW.curie('mdc'),
                   model_uri=RAW.twoTerminalDCRecord__mdc, domain=None, range=Optional[int])

slots.twoTerminalDCRecord__rdc = Slot(uri=RAW.rdc, name="twoTerminalDCRecord__rdc", curie=RAW.curie('rdc'),
                   model_uri=RAW.twoTerminalDCRecord__rdc, domain=None, range=float)

slots.twoTerminalDCRecord__setvl = Slot(uri=RAW.setvl, name="twoTerminalDCRecord__setvl", curie=RAW.curie('setvl'),
                   model_uri=RAW.twoTerminalDCRecord__setvl, domain=None, range=float)

slots.twoTerminalDCRecord__vschd = Slot(uri=RAW.vschd, name="twoTerminalDCRecord__vschd", curie=RAW.curie('vschd'),
                   model_uri=RAW.twoTerminalDCRecord__vschd, domain=None, range=float)

slots.twoTerminalDCRecord__vcmod = Slot(uri=RAW.vcmod, name="twoTerminalDCRecord__vcmod", curie=RAW.curie('vcmod'),
                   model_uri=RAW.twoTerminalDCRecord__vcmod, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__rcomp = Slot(uri=RAW.rcomp, name="twoTerminalDCRecord__rcomp", curie=RAW.curie('rcomp'),
                   model_uri=RAW.twoTerminalDCRecord__rcomp, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__delti = Slot(uri=RAW.delti, name="twoTerminalDCRecord__delti", curie=RAW.curie('delti'),
                   model_uri=RAW.twoTerminalDCRecord__delti, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__meter = Slot(uri=RAW.meter, name="twoTerminalDCRecord__meter", curie=RAW.curie('meter'),
                   model_uri=RAW.twoTerminalDCRecord__meter, domain=None, range=Optional[str])

slots.twoTerminalDCRecord__dcvmin = Slot(uri=RAW.dcvmin, name="twoTerminalDCRecord__dcvmin", curie=RAW.curie('dcvmin'),
                   model_uri=RAW.twoTerminalDCRecord__dcvmin, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__cccitmx = Slot(uri=RAW.cccitmx, name="twoTerminalDCRecord__cccitmx", curie=RAW.curie('cccitmx'),
                   model_uri=RAW.twoTerminalDCRecord__cccitmx, domain=None, range=Optional[int])

slots.twoTerminalDCRecord__cccacc = Slot(uri=RAW.cccacc, name="twoTerminalDCRecord__cccacc", curie=RAW.curie('cccacc'),
                   model_uri=RAW.twoTerminalDCRecord__cccacc, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__ipr = Slot(uri=RAW.ipr, name="twoTerminalDCRecord__ipr", curie=RAW.curie('ipr'),
                   model_uri=RAW.twoTerminalDCRecord__ipr, domain=None, range=int)

slots.twoTerminalDCRecord__nbr = Slot(uri=RAW.nbr, name="twoTerminalDCRecord__nbr", curie=RAW.curie('nbr'),
                   model_uri=RAW.twoTerminalDCRecord__nbr, domain=None, range=int)

slots.twoTerminalDCRecord__anmxr = Slot(uri=RAW.anmxr, name="twoTerminalDCRecord__anmxr", curie=RAW.curie('anmxr'),
                   model_uri=RAW.twoTerminalDCRecord__anmxr, domain=None, range=float)

slots.twoTerminalDCRecord__anmnr = Slot(uri=RAW.anmnr, name="twoTerminalDCRecord__anmnr", curie=RAW.curie('anmnr'),
                   model_uri=RAW.twoTerminalDCRecord__anmnr, domain=None, range=float)

slots.twoTerminalDCRecord__rcr = Slot(uri=RAW.rcr, name="twoTerminalDCRecord__rcr", curie=RAW.curie('rcr'),
                   model_uri=RAW.twoTerminalDCRecord__rcr, domain=None, range=float)

slots.twoTerminalDCRecord__xcr = Slot(uri=RAW.xcr, name="twoTerminalDCRecord__xcr", curie=RAW.curie('xcr'),
                   model_uri=RAW.twoTerminalDCRecord__xcr, domain=None, range=float)

slots.twoTerminalDCRecord__ebasr = Slot(uri=RAW.ebasr, name="twoTerminalDCRecord__ebasr", curie=RAW.curie('ebasr'),
                   model_uri=RAW.twoTerminalDCRecord__ebasr, domain=None, range=float)

slots.twoTerminalDCRecord__trr = Slot(uri=RAW.trr, name="twoTerminalDCRecord__trr", curie=RAW.curie('trr'),
                   model_uri=RAW.twoTerminalDCRecord__trr, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__tapr = Slot(uri=RAW.tapr, name="twoTerminalDCRecord__tapr", curie=RAW.curie('tapr'),
                   model_uri=RAW.twoTerminalDCRecord__tapr, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__tmxr = Slot(uri=RAW.tmxr, name="twoTerminalDCRecord__tmxr", curie=RAW.curie('tmxr'),
                   model_uri=RAW.twoTerminalDCRecord__tmxr, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__tmnr = Slot(uri=RAW.tmnr, name="twoTerminalDCRecord__tmnr", curie=RAW.curie('tmnr'),
                   model_uri=RAW.twoTerminalDCRecord__tmnr, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__stpr = Slot(uri=RAW.stpr, name="twoTerminalDCRecord__stpr", curie=RAW.curie('stpr'),
                   model_uri=RAW.twoTerminalDCRecord__stpr, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__icr = Slot(uri=RAW.icr, name="twoTerminalDCRecord__icr", curie=RAW.curie('icr'),
                   model_uri=RAW.twoTerminalDCRecord__icr, domain=None, range=Optional[int])

slots.twoTerminalDCRecord__ifr = Slot(uri=RAW.ifr, name="twoTerminalDCRecord__ifr", curie=RAW.curie('ifr'),
                   model_uri=RAW.twoTerminalDCRecord__ifr, domain=None, range=Optional[int])

slots.twoTerminalDCRecord__itr = Slot(uri=RAW.itr, name="twoTerminalDCRecord__itr", curie=RAW.curie('itr'),
                   model_uri=RAW.twoTerminalDCRecord__itr, domain=None, range=Optional[int])

slots.twoTerminalDCRecord__idr = Slot(uri=RAW.idr, name="twoTerminalDCRecord__idr", curie=RAW.curie('idr'),
                   model_uri=RAW.twoTerminalDCRecord__idr, domain=None, range=Optional[str])

slots.twoTerminalDCRecord__xcapr = Slot(uri=RAW.xcapr, name="twoTerminalDCRecord__xcapr", curie=RAW.curie('xcapr'),
                   model_uri=RAW.twoTerminalDCRecord__xcapr, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__ndr = Slot(uri=RAW.ndr, name="twoTerminalDCRecord__ndr", curie=RAW.curie('ndr'),
                   model_uri=RAW.twoTerminalDCRecord__ndr, domain=None, range=Optional[int])

slots.twoTerminalDCRecord__ipi = Slot(uri=RAW.ipi, name="twoTerminalDCRecord__ipi", curie=RAW.curie('ipi'),
                   model_uri=RAW.twoTerminalDCRecord__ipi, domain=None, range=int)

slots.twoTerminalDCRecord__nbi = Slot(uri=RAW.nbi, name="twoTerminalDCRecord__nbi", curie=RAW.curie('nbi'),
                   model_uri=RAW.twoTerminalDCRecord__nbi, domain=None, range=int)

slots.twoTerminalDCRecord__anmxi = Slot(uri=RAW.anmxi, name="twoTerminalDCRecord__anmxi", curie=RAW.curie('anmxi'),
                   model_uri=RAW.twoTerminalDCRecord__anmxi, domain=None, range=float)

slots.twoTerminalDCRecord__anmni = Slot(uri=RAW.anmni, name="twoTerminalDCRecord__anmni", curie=RAW.curie('anmni'),
                   model_uri=RAW.twoTerminalDCRecord__anmni, domain=None, range=float)

slots.twoTerminalDCRecord__rci = Slot(uri=RAW.rci, name="twoTerminalDCRecord__rci", curie=RAW.curie('rci'),
                   model_uri=RAW.twoTerminalDCRecord__rci, domain=None, range=float)

slots.twoTerminalDCRecord__xci = Slot(uri=RAW.xci, name="twoTerminalDCRecord__xci", curie=RAW.curie('xci'),
                   model_uri=RAW.twoTerminalDCRecord__xci, domain=None, range=float)

slots.twoTerminalDCRecord__ebasi = Slot(uri=RAW.ebasi, name="twoTerminalDCRecord__ebasi", curie=RAW.curie('ebasi'),
                   model_uri=RAW.twoTerminalDCRecord__ebasi, domain=None, range=float)

slots.twoTerminalDCRecord__tri = Slot(uri=RAW.tri, name="twoTerminalDCRecord__tri", curie=RAW.curie('tri'),
                   model_uri=RAW.twoTerminalDCRecord__tri, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__tapi = Slot(uri=RAW.tapi, name="twoTerminalDCRecord__tapi", curie=RAW.curie('tapi'),
                   model_uri=RAW.twoTerminalDCRecord__tapi, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__tmxi = Slot(uri=RAW.tmxi, name="twoTerminalDCRecord__tmxi", curie=RAW.curie('tmxi'),
                   model_uri=RAW.twoTerminalDCRecord__tmxi, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__tmni = Slot(uri=RAW.tmni, name="twoTerminalDCRecord__tmni", curie=RAW.curie('tmni'),
                   model_uri=RAW.twoTerminalDCRecord__tmni, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__stpi = Slot(uri=RAW.stpi, name="twoTerminalDCRecord__stpi", curie=RAW.curie('stpi'),
                   model_uri=RAW.twoTerminalDCRecord__stpi, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__ici = Slot(uri=RAW.ici, name="twoTerminalDCRecord__ici", curie=RAW.curie('ici'),
                   model_uri=RAW.twoTerminalDCRecord__ici, domain=None, range=Optional[int])

slots.twoTerminalDCRecord__ifi = Slot(uri=RAW.ifi, name="twoTerminalDCRecord__ifi", curie=RAW.curie('ifi'),
                   model_uri=RAW.twoTerminalDCRecord__ifi, domain=None, range=Optional[int])

slots.twoTerminalDCRecord__iti = Slot(uri=RAW.iti, name="twoTerminalDCRecord__iti", curie=RAW.curie('iti'),
                   model_uri=RAW.twoTerminalDCRecord__iti, domain=None, range=Optional[int])

slots.twoTerminalDCRecord__idi = Slot(uri=RAW.idi, name="twoTerminalDCRecord__idi", curie=RAW.curie('idi'),
                   model_uri=RAW.twoTerminalDCRecord__idi, domain=None, range=Optional[str])

slots.twoTerminalDCRecord__xcapi = Slot(uri=RAW.xcapi, name="twoTerminalDCRecord__xcapi", curie=RAW.curie('xcapi'),
                   model_uri=RAW.twoTerminalDCRecord__xcapi, domain=None, range=Optional[float])

slots.twoTerminalDCRecord__ndi = Slot(uri=RAW.ndi, name="twoTerminalDCRecord__ndi", curie=RAW.curie('ndi'),
                   model_uri=RAW.twoTerminalDCRecord__ndi, domain=None, range=Optional[int])

slots.vscDcRecord__name = Slot(uri=RAW.name, name="vscDcRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.vscDcRecord__name, domain=None, range=str)

slots.vscDcRecord__mdc = Slot(uri=RAW.mdc, name="vscDcRecord__mdc", curie=RAW.curie('mdc'),
                   model_uri=RAW.vscDcRecord__mdc, domain=None, range=Optional[int])

slots.vscDcRecord__rdc = Slot(uri=RAW.rdc, name="vscDcRecord__rdc", curie=RAW.curie('rdc'),
                   model_uri=RAW.vscDcRecord__rdc, domain=None, range=float)

slots.vscDcRecord__o1 = Slot(uri=RAW.o1, name="vscDcRecord__o1", curie=RAW.curie('o1'),
                   model_uri=RAW.vscDcRecord__o1, domain=None, range=Optional[int])

slots.vscDcRecord__f1 = Slot(uri=RAW.f1, name="vscDcRecord__f1", curie=RAW.curie('f1'),
                   model_uri=RAW.vscDcRecord__f1, domain=None, range=Optional[float])

slots.vscDcRecord__o2 = Slot(uri=RAW.o2, name="vscDcRecord__o2", curie=RAW.curie('o2'),
                   model_uri=RAW.vscDcRecord__o2, domain=None, range=Optional[int])

slots.vscDcRecord__f2 = Slot(uri=RAW.f2, name="vscDcRecord__f2", curie=RAW.curie('f2'),
                   model_uri=RAW.vscDcRecord__f2, domain=None, range=Optional[float])

slots.vscDcRecord__o3 = Slot(uri=RAW.o3, name="vscDcRecord__o3", curie=RAW.curie('o3'),
                   model_uri=RAW.vscDcRecord__o3, domain=None, range=Optional[int])

slots.vscDcRecord__f3 = Slot(uri=RAW.f3, name="vscDcRecord__f3", curie=RAW.curie('f3'),
                   model_uri=RAW.vscDcRecord__f3, domain=None, range=Optional[float])

slots.vscDcRecord__o4 = Slot(uri=RAW.o4, name="vscDcRecord__o4", curie=RAW.curie('o4'),
                   model_uri=RAW.vscDcRecord__o4, domain=None, range=Optional[int])

slots.vscDcRecord__f4 = Slot(uri=RAW.f4, name="vscDcRecord__f4", curie=RAW.curie('f4'),
                   model_uri=RAW.vscDcRecord__f4, domain=None, range=Optional[float])

slots.vscDcRecord__ibus = Slot(uri=RAW.ibus, name="vscDcRecord__ibus", curie=RAW.curie('ibus'),
                   model_uri=RAW.vscDcRecord__ibus, domain=None, range=int)

slots.vscDcRecord__converter_type = Slot(uri=RAW.converter_type, name="vscDcRecord__converter_type", curie=RAW.curie('converter_type'),
                   model_uri=RAW.vscDcRecord__converter_type, domain=None, range=int)

slots.vscDcRecord__mode = Slot(uri=RAW.mode, name="vscDcRecord__mode", curie=RAW.curie('mode'),
                   model_uri=RAW.vscDcRecord__mode, domain=None, range=Optional[int])

slots.vscDcRecord__dcset = Slot(uri=RAW.dcset, name="vscDcRecord__dcset", curie=RAW.curie('dcset'),
                   model_uri=RAW.vscDcRecord__dcset, domain=None, range=float)

slots.vscDcRecord__acset = Slot(uri=RAW.acset, name="vscDcRecord__acset", curie=RAW.curie('acset'),
                   model_uri=RAW.vscDcRecord__acset, domain=None, range=Optional[float])

slots.vscDcRecord__aloss = Slot(uri=RAW.aloss, name="vscDcRecord__aloss", curie=RAW.curie('aloss'),
                   model_uri=RAW.vscDcRecord__aloss, domain=None, range=Optional[float])

slots.vscDcRecord__bloss = Slot(uri=RAW.bloss, name="vscDcRecord__bloss", curie=RAW.curie('bloss'),
                   model_uri=RAW.vscDcRecord__bloss, domain=None, range=Optional[float])

slots.vscDcRecord__minloss = Slot(uri=RAW.minloss, name="vscDcRecord__minloss", curie=RAW.curie('minloss'),
                   model_uri=RAW.vscDcRecord__minloss, domain=None, range=Optional[float])

slots.vscDcRecord__smax = Slot(uri=RAW.smax, name="vscDcRecord__smax", curie=RAW.curie('smax'),
                   model_uri=RAW.vscDcRecord__smax, domain=None, range=Optional[float])

slots.vscDcRecord__imax = Slot(uri=RAW.imax, name="vscDcRecord__imax", curie=RAW.curie('imax'),
                   model_uri=RAW.vscDcRecord__imax, domain=None, range=Optional[float])

slots.vscDcRecord__pwf = Slot(uri=RAW.pwf, name="vscDcRecord__pwf", curie=RAW.curie('pwf'),
                   model_uri=RAW.vscDcRecord__pwf, domain=None, range=Optional[float])

slots.vscDcRecord__maxq = Slot(uri=RAW.maxq, name="vscDcRecord__maxq", curie=RAW.curie('maxq'),
                   model_uri=RAW.vscDcRecord__maxq, domain=None, range=Optional[float])

slots.vscDcRecord__minq = Slot(uri=RAW.minq, name="vscDcRecord__minq", curie=RAW.curie('minq'),
                   model_uri=RAW.vscDcRecord__minq, domain=None, range=Optional[float])

slots.vscDcRecord__vsreg = Slot(uri=RAW.vsreg, name="vscDcRecord__vsreg", curie=RAW.curie('vsreg'),
                   model_uri=RAW.vscDcRecord__vsreg, domain=None, range=Optional[int])

slots.vscDcRecord__rmpct = Slot(uri=RAW.rmpct, name="vscDcRecord__rmpct", curie=RAW.curie('rmpct'),
                   model_uri=RAW.vscDcRecord__rmpct, domain=None, range=Optional[float])

slots.vscDcRecord__nreg = Slot(uri=RAW.nreg, name="vscDcRecord__nreg", curie=RAW.curie('nreg'),
                   model_uri=RAW.vscDcRecord__nreg, domain=None, range=Optional[int])

slots.impedanceCorrectionRecord__table_number = Slot(uri=RAW.table_number, name="impedanceCorrectionRecord__table_number", curie=RAW.curie('table_number'),
                   model_uri=RAW.impedanceCorrectionRecord__table_number, domain=None, range=URIRef)

slots.impedanceCorrectionRecord__t1 = Slot(uri=RAW.t1, name="impedanceCorrectionRecord__t1", curie=RAW.curie('t1'),
                   model_uri=RAW.impedanceCorrectionRecord__t1, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f1_real = Slot(uri=RAW.f1_real, name="impedanceCorrectionRecord__f1_real", curie=RAW.curie('f1_real'),
                   model_uri=RAW.impedanceCorrectionRecord__f1_real, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f1_imag = Slot(uri=RAW.f1_imag, name="impedanceCorrectionRecord__f1_imag", curie=RAW.curie('f1_imag'),
                   model_uri=RAW.impedanceCorrectionRecord__f1_imag, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__t2 = Slot(uri=RAW.t2, name="impedanceCorrectionRecord__t2", curie=RAW.curie('t2'),
                   model_uri=RAW.impedanceCorrectionRecord__t2, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f2_real = Slot(uri=RAW.f2_real, name="impedanceCorrectionRecord__f2_real", curie=RAW.curie('f2_real'),
                   model_uri=RAW.impedanceCorrectionRecord__f2_real, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f2_imag = Slot(uri=RAW.f2_imag, name="impedanceCorrectionRecord__f2_imag", curie=RAW.curie('f2_imag'),
                   model_uri=RAW.impedanceCorrectionRecord__f2_imag, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__t3 = Slot(uri=RAW.t3, name="impedanceCorrectionRecord__t3", curie=RAW.curie('t3'),
                   model_uri=RAW.impedanceCorrectionRecord__t3, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f3_real = Slot(uri=RAW.f3_real, name="impedanceCorrectionRecord__f3_real", curie=RAW.curie('f3_real'),
                   model_uri=RAW.impedanceCorrectionRecord__f3_real, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f3_imag = Slot(uri=RAW.f3_imag, name="impedanceCorrectionRecord__f3_imag", curie=RAW.curie('f3_imag'),
                   model_uri=RAW.impedanceCorrectionRecord__f3_imag, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__t4 = Slot(uri=RAW.t4, name="impedanceCorrectionRecord__t4", curie=RAW.curie('t4'),
                   model_uri=RAW.impedanceCorrectionRecord__t4, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f4_real = Slot(uri=RAW.f4_real, name="impedanceCorrectionRecord__f4_real", curie=RAW.curie('f4_real'),
                   model_uri=RAW.impedanceCorrectionRecord__f4_real, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f4_imag = Slot(uri=RAW.f4_imag, name="impedanceCorrectionRecord__f4_imag", curie=RAW.curie('f4_imag'),
                   model_uri=RAW.impedanceCorrectionRecord__f4_imag, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__t5 = Slot(uri=RAW.t5, name="impedanceCorrectionRecord__t5", curie=RAW.curie('t5'),
                   model_uri=RAW.impedanceCorrectionRecord__t5, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f5_real = Slot(uri=RAW.f5_real, name="impedanceCorrectionRecord__f5_real", curie=RAW.curie('f5_real'),
                   model_uri=RAW.impedanceCorrectionRecord__f5_real, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f5_imag = Slot(uri=RAW.f5_imag, name="impedanceCorrectionRecord__f5_imag", curie=RAW.curie('f5_imag'),
                   model_uri=RAW.impedanceCorrectionRecord__f5_imag, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__t6 = Slot(uri=RAW.t6, name="impedanceCorrectionRecord__t6", curie=RAW.curie('t6'),
                   model_uri=RAW.impedanceCorrectionRecord__t6, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f6_real = Slot(uri=RAW.f6_real, name="impedanceCorrectionRecord__f6_real", curie=RAW.curie('f6_real'),
                   model_uri=RAW.impedanceCorrectionRecord__f6_real, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f6_imag = Slot(uri=RAW.f6_imag, name="impedanceCorrectionRecord__f6_imag", curie=RAW.curie('f6_imag'),
                   model_uri=RAW.impedanceCorrectionRecord__f6_imag, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__t7 = Slot(uri=RAW.t7, name="impedanceCorrectionRecord__t7", curie=RAW.curie('t7'),
                   model_uri=RAW.impedanceCorrectionRecord__t7, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f7_real = Slot(uri=RAW.f7_real, name="impedanceCorrectionRecord__f7_real", curie=RAW.curie('f7_real'),
                   model_uri=RAW.impedanceCorrectionRecord__f7_real, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f7_imag = Slot(uri=RAW.f7_imag, name="impedanceCorrectionRecord__f7_imag", curie=RAW.curie('f7_imag'),
                   model_uri=RAW.impedanceCorrectionRecord__f7_imag, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__t8 = Slot(uri=RAW.t8, name="impedanceCorrectionRecord__t8", curie=RAW.curie('t8'),
                   model_uri=RAW.impedanceCorrectionRecord__t8, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f8_real = Slot(uri=RAW.f8_real, name="impedanceCorrectionRecord__f8_real", curie=RAW.curie('f8_real'),
                   model_uri=RAW.impedanceCorrectionRecord__f8_real, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f8_imag = Slot(uri=RAW.f8_imag, name="impedanceCorrectionRecord__f8_imag", curie=RAW.curie('f8_imag'),
                   model_uri=RAW.impedanceCorrectionRecord__f8_imag, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__t9 = Slot(uri=RAW.t9, name="impedanceCorrectionRecord__t9", curie=RAW.curie('t9'),
                   model_uri=RAW.impedanceCorrectionRecord__t9, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f9_real = Slot(uri=RAW.f9_real, name="impedanceCorrectionRecord__f9_real", curie=RAW.curie('f9_real'),
                   model_uri=RAW.impedanceCorrectionRecord__f9_real, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f9_imag = Slot(uri=RAW.f9_imag, name="impedanceCorrectionRecord__f9_imag", curie=RAW.curie('f9_imag'),
                   model_uri=RAW.impedanceCorrectionRecord__f9_imag, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__t10 = Slot(uri=RAW.t10, name="impedanceCorrectionRecord__t10", curie=RAW.curie('t10'),
                   model_uri=RAW.impedanceCorrectionRecord__t10, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f10_real = Slot(uri=RAW.f10_real, name="impedanceCorrectionRecord__f10_real", curie=RAW.curie('f10_real'),
                   model_uri=RAW.impedanceCorrectionRecord__f10_real, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f10_imag = Slot(uri=RAW.f10_imag, name="impedanceCorrectionRecord__f10_imag", curie=RAW.curie('f10_imag'),
                   model_uri=RAW.impedanceCorrectionRecord__f10_imag, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__t11 = Slot(uri=RAW.t11, name="impedanceCorrectionRecord__t11", curie=RAW.curie('t11'),
                   model_uri=RAW.impedanceCorrectionRecord__t11, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f11_real = Slot(uri=RAW.f11_real, name="impedanceCorrectionRecord__f11_real", curie=RAW.curie('f11_real'),
                   model_uri=RAW.impedanceCorrectionRecord__f11_real, domain=None, range=Optional[float])

slots.impedanceCorrectionRecord__f11_imag = Slot(uri=RAW.f11_imag, name="impedanceCorrectionRecord__f11_imag", curie=RAW.curie('f11_imag'),
                   model_uri=RAW.impedanceCorrectionRecord__f11_imag, domain=None, range=Optional[float])

slots.multiTerminalDCRecord__name = Slot(uri=RAW.name, name="multiTerminalDCRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.multiTerminalDCRecord__name, domain=None, range=str)

slots.multiTerminalDCRecord__nconv = Slot(uri=RAW.nconv, name="multiTerminalDCRecord__nconv", curie=RAW.curie('nconv'),
                   model_uri=RAW.multiTerminalDCRecord__nconv, domain=None, range=int)

slots.multiTerminalDCRecord__ndcbs = Slot(uri=RAW.ndcbs, name="multiTerminalDCRecord__ndcbs", curie=RAW.curie('ndcbs'),
                   model_uri=RAW.multiTerminalDCRecord__ndcbs, domain=None, range=int)

slots.multiTerminalDCRecord__ndcln = Slot(uri=RAW.ndcln, name="multiTerminalDCRecord__ndcln", curie=RAW.curie('ndcln'),
                   model_uri=RAW.multiTerminalDCRecord__ndcln, domain=None, range=int)

slots.multiTerminalDCRecord__mdc = Slot(uri=RAW.mdc, name="multiTerminalDCRecord__mdc", curie=RAW.curie('mdc'),
                   model_uri=RAW.multiTerminalDCRecord__mdc, domain=None, range=Optional[int])

slots.multiTerminalDCRecord__vconv = Slot(uri=RAW.vconv, name="multiTerminalDCRecord__vconv", curie=RAW.curie('vconv'),
                   model_uri=RAW.multiTerminalDCRecord__vconv, domain=None, range=int)

slots.multiTerminalDCRecord__vcmod = Slot(uri=RAW.vcmod, name="multiTerminalDCRecord__vcmod", curie=RAW.curie('vcmod'),
                   model_uri=RAW.multiTerminalDCRecord__vcmod, domain=None, range=Optional[float])

slots.multiTerminalDCRecord__vconvn = Slot(uri=RAW.vconvn, name="multiTerminalDCRecord__vconvn", curie=RAW.curie('vconvn'),
                   model_uri=RAW.multiTerminalDCRecord__vconvn, domain=None, range=Optional[int])

slots.multiTerminalConverterRecord__ib = Slot(uri=RAW.ib, name="multiTerminalConverterRecord__ib", curie=RAW.curie('ib'),
                   model_uri=RAW.multiTerminalConverterRecord__ib, domain=None, range=int)

slots.multiTerminalConverterRecord__n = Slot(uri=RAW.n, name="multiTerminalConverterRecord__n", curie=RAW.curie('n'),
                   model_uri=RAW.multiTerminalConverterRecord__n, domain=None, range=int)

slots.multiTerminalConverterRecord__angmx = Slot(uri=RAW.angmx, name="multiTerminalConverterRecord__angmx", curie=RAW.curie('angmx'),
                   model_uri=RAW.multiTerminalConverterRecord__angmx, domain=None, range=float)

slots.multiTerminalConverterRecord__angmn = Slot(uri=RAW.angmn, name="multiTerminalConverterRecord__angmn", curie=RAW.curie('angmn'),
                   model_uri=RAW.multiTerminalConverterRecord__angmn, domain=None, range=float)

slots.multiTerminalConverterRecord__rc = Slot(uri=RAW.rc, name="multiTerminalConverterRecord__rc", curie=RAW.curie('rc'),
                   model_uri=RAW.multiTerminalConverterRecord__rc, domain=None, range=float)

slots.multiTerminalConverterRecord__xc = Slot(uri=RAW.xc, name="multiTerminalConverterRecord__xc", curie=RAW.curie('xc'),
                   model_uri=RAW.multiTerminalConverterRecord__xc, domain=None, range=float)

slots.multiTerminalConverterRecord__ebas = Slot(uri=RAW.ebas, name="multiTerminalConverterRecord__ebas", curie=RAW.curie('ebas'),
                   model_uri=RAW.multiTerminalConverterRecord__ebas, domain=None, range=float)

slots.multiTerminalConverterRecord__tr = Slot(uri=RAW.tr, name="multiTerminalConverterRecord__tr", curie=RAW.curie('tr'),
                   model_uri=RAW.multiTerminalConverterRecord__tr, domain=None, range=Optional[float])

slots.multiTerminalConverterRecord__tap = Slot(uri=RAW.tap, name="multiTerminalConverterRecord__tap", curie=RAW.curie('tap'),
                   model_uri=RAW.multiTerminalConverterRecord__tap, domain=None, range=Optional[float])

slots.multiTerminalConverterRecord__tpmx = Slot(uri=RAW.tpmx, name="multiTerminalConverterRecord__tpmx", curie=RAW.curie('tpmx'),
                   model_uri=RAW.multiTerminalConverterRecord__tpmx, domain=None, range=Optional[float])

slots.multiTerminalConverterRecord__tpmn = Slot(uri=RAW.tpmn, name="multiTerminalConverterRecord__tpmn", curie=RAW.curie('tpmn'),
                   model_uri=RAW.multiTerminalConverterRecord__tpmn, domain=None, range=Optional[float])

slots.multiTerminalConverterRecord__tstp = Slot(uri=RAW.tstp, name="multiTerminalConverterRecord__tstp", curie=RAW.curie('tstp'),
                   model_uri=RAW.multiTerminalConverterRecord__tstp, domain=None, range=Optional[float])

slots.multiTerminalConverterRecord__setvl = Slot(uri=RAW.setvl, name="multiTerminalConverterRecord__setvl", curie=RAW.curie('setvl'),
                   model_uri=RAW.multiTerminalConverterRecord__setvl, domain=None, range=float)

slots.multiTerminalConverterRecord__dcpf = Slot(uri=RAW.dcpf, name="multiTerminalConverterRecord__dcpf", curie=RAW.curie('dcpf'),
                   model_uri=RAW.multiTerminalConverterRecord__dcpf, domain=None, range=Optional[float])

slots.multiTerminalConverterRecord__marg = Slot(uri=RAW.marg, name="multiTerminalConverterRecord__marg", curie=RAW.curie('marg'),
                   model_uri=RAW.multiTerminalConverterRecord__marg, domain=None, range=Optional[float])

slots.multiTerminalConverterRecord__cnvcod = Slot(uri=RAW.cnvcod, name="multiTerminalConverterRecord__cnvcod", curie=RAW.curie('cnvcod'),
                   model_uri=RAW.multiTerminalConverterRecord__cnvcod, domain=None, range=Optional[int])

slots.multiTerminalDCBusRecord__idc = Slot(uri=RAW.idc, name="multiTerminalDCBusRecord__idc", curie=RAW.curie('idc'),
                   model_uri=RAW.multiTerminalDCBusRecord__idc, domain=None, range=int)

slots.multiTerminalDCBusRecord__ib = Slot(uri=RAW.ib, name="multiTerminalDCBusRecord__ib", curie=RAW.curie('ib'),
                   model_uri=RAW.multiTerminalDCBusRecord__ib, domain=None, range=Optional[int])

slots.multiTerminalDCBusRecord__area = Slot(uri=RAW.area, name="multiTerminalDCBusRecord__area", curie=RAW.curie('area'),
                   model_uri=RAW.multiTerminalDCBusRecord__area, domain=None, range=Optional[int])

slots.multiTerminalDCBusRecord__zone = Slot(uri=RAW.zone, name="multiTerminalDCBusRecord__zone", curie=RAW.curie('zone'),
                   model_uri=RAW.multiTerminalDCBusRecord__zone, domain=None, range=Optional[int])

slots.multiTerminalDCBusRecord__dcname = Slot(uri=RAW.dcname, name="multiTerminalDCBusRecord__dcname", curie=RAW.curie('dcname'),
                   model_uri=RAW.multiTerminalDCBusRecord__dcname, domain=None, range=Optional[str])

slots.multiTerminalDCBusRecord__idc2 = Slot(uri=RAW.idc2, name="multiTerminalDCBusRecord__idc2", curie=RAW.curie('idc2'),
                   model_uri=RAW.multiTerminalDCBusRecord__idc2, domain=None, range=Optional[int])

slots.multiTerminalDCBusRecord__rgrnd = Slot(uri=RAW.rgrnd, name="multiTerminalDCBusRecord__rgrnd", curie=RAW.curie('rgrnd'),
                   model_uri=RAW.multiTerminalDCBusRecord__rgrnd, domain=None, range=Optional[float])

slots.multiTerminalDCBusRecord__owner = Slot(uri=RAW.owner, name="multiTerminalDCBusRecord__owner", curie=RAW.curie('owner'),
                   model_uri=RAW.multiTerminalDCBusRecord__owner, domain=None, range=Optional[int])

slots.multiTerminalDCLinkRecord__idc = Slot(uri=RAW.idc, name="multiTerminalDCLinkRecord__idc", curie=RAW.curie('idc'),
                   model_uri=RAW.multiTerminalDCLinkRecord__idc, domain=None, range=int)

slots.multiTerminalDCLinkRecord__jdc = Slot(uri=RAW.jdc, name="multiTerminalDCLinkRecord__jdc", curie=RAW.curie('jdc'),
                   model_uri=RAW.multiTerminalDCLinkRecord__jdc, domain=None, range=int)

slots.multiTerminalDCLinkRecord__ckt = Slot(uri=RAW.ckt, name="multiTerminalDCLinkRecord__ckt", curie=RAW.curie('ckt'),
                   model_uri=RAW.multiTerminalDCLinkRecord__ckt, domain=None, range=Optional[str])

slots.multiTerminalDCLinkRecord__met = Slot(uri=RAW.met, name="multiTerminalDCLinkRecord__met", curie=RAW.curie('met'),
                   model_uri=RAW.multiTerminalDCLinkRecord__met, domain=None, range=Optional[int])

slots.multiTerminalDCLinkRecord__rdc = Slot(uri=RAW.rdc, name="multiTerminalDCLinkRecord__rdc", curie=RAW.curie('rdc'),
                   model_uri=RAW.multiTerminalDCLinkRecord__rdc, domain=None, range=float)

slots.multiTerminalDCLinkRecord__ldc = Slot(uri=RAW.ldc, name="multiTerminalDCLinkRecord__ldc", curie=RAW.curie('ldc'),
                   model_uri=RAW.multiTerminalDCLinkRecord__ldc, domain=None, range=Optional[float])

slots.multiSectionLineRecord__i = Slot(uri=RAW.i, name="multiSectionLineRecord__i", curie=RAW.curie('i'),
                   model_uri=RAW.multiSectionLineRecord__i, domain=None, range=int)

slots.multiSectionLineRecord__j = Slot(uri=RAW.j, name="multiSectionLineRecord__j", curie=RAW.curie('j'),
                   model_uri=RAW.multiSectionLineRecord__j, domain=None, range=int)

slots.multiSectionLineRecord__line_id = Slot(uri=RAW.line_id, name="multiSectionLineRecord__line_id", curie=RAW.curie('line_id'),
                   model_uri=RAW.multiSectionLineRecord__line_id, domain=None, range=Optional[str])

slots.multiSectionLineRecord__met = Slot(uri=RAW.met, name="multiSectionLineRecord__met", curie=RAW.curie('met'),
                   model_uri=RAW.multiSectionLineRecord__met, domain=None, range=Optional[int])

slots.multiSectionLineRecord__dum1 = Slot(uri=RAW.dum1, name="multiSectionLineRecord__dum1", curie=RAW.curie('dum1'),
                   model_uri=RAW.multiSectionLineRecord__dum1, domain=None, range=int)

slots.multiSectionLineRecord__dum2 = Slot(uri=RAW.dum2, name="multiSectionLineRecord__dum2", curie=RAW.curie('dum2'),
                   model_uri=RAW.multiSectionLineRecord__dum2, domain=None, range=Optional[int])

slots.multiSectionLineRecord__dum3 = Slot(uri=RAW.dum3, name="multiSectionLineRecord__dum3", curie=RAW.curie('dum3'),
                   model_uri=RAW.multiSectionLineRecord__dum3, domain=None, range=Optional[int])

slots.multiSectionLineRecord__dum4 = Slot(uri=RAW.dum4, name="multiSectionLineRecord__dum4", curie=RAW.curie('dum4'),
                   model_uri=RAW.multiSectionLineRecord__dum4, domain=None, range=Optional[int])

slots.multiSectionLineRecord__dum5 = Slot(uri=RAW.dum5, name="multiSectionLineRecord__dum5", curie=RAW.curie('dum5'),
                   model_uri=RAW.multiSectionLineRecord__dum5, domain=None, range=Optional[int])

slots.multiSectionLineRecord__dum6 = Slot(uri=RAW.dum6, name="multiSectionLineRecord__dum6", curie=RAW.curie('dum6'),
                   model_uri=RAW.multiSectionLineRecord__dum6, domain=None, range=Optional[int])

slots.multiSectionLineRecord__dum7 = Slot(uri=RAW.dum7, name="multiSectionLineRecord__dum7", curie=RAW.curie('dum7'),
                   model_uri=RAW.multiSectionLineRecord__dum7, domain=None, range=Optional[int])

slots.multiSectionLineRecord__dum8 = Slot(uri=RAW.dum8, name="multiSectionLineRecord__dum8", curie=RAW.curie('dum8'),
                   model_uri=RAW.multiSectionLineRecord__dum8, domain=None, range=Optional[int])

slots.multiSectionLineRecord__dum9 = Slot(uri=RAW.dum9, name="multiSectionLineRecord__dum9", curie=RAW.curie('dum9'),
                   model_uri=RAW.multiSectionLineRecord__dum9, domain=None, range=Optional[int])

slots.zoneRecord__zone_number = Slot(uri=RAW.zone_number, name="zoneRecord__zone_number", curie=RAW.curie('zone_number'),
                   model_uri=RAW.zoneRecord__zone_number, domain=None, range=URIRef)

slots.zoneRecord__zone_name = Slot(uri=RAW.zone_name, name="zoneRecord__zone_name", curie=RAW.curie('zone_name'),
                   model_uri=RAW.zoneRecord__zone_name, domain=None, range=Optional[str])

slots.interareaTransferRecord__from_area = Slot(uri=RAW.from_area, name="interareaTransferRecord__from_area", curie=RAW.curie('from_area'),
                   model_uri=RAW.interareaTransferRecord__from_area, domain=None, range=int)

slots.interareaTransferRecord__to_area = Slot(uri=RAW.to_area, name="interareaTransferRecord__to_area", curie=RAW.curie('to_area'),
                   model_uri=RAW.interareaTransferRecord__to_area, domain=None, range=int)

slots.interareaTransferRecord__transfer_id = Slot(uri=RAW.transfer_id, name="interareaTransferRecord__transfer_id", curie=RAW.curie('transfer_id'),
                   model_uri=RAW.interareaTransferRecord__transfer_id, domain=None, range=Optional[str])

slots.interareaTransferRecord__power_transfer = Slot(uri=RAW.power_transfer, name="interareaTransferRecord__power_transfer", curie=RAW.curie('power_transfer'),
                   model_uri=RAW.interareaTransferRecord__power_transfer, domain=None, range=Optional[float])

slots.ownerRecord__owner_number = Slot(uri=RAW.owner_number, name="ownerRecord__owner_number", curie=RAW.curie('owner_number'),
                   model_uri=RAW.ownerRecord__owner_number, domain=None, range=URIRef)

slots.ownerRecord__owner_name = Slot(uri=RAW.owner_name, name="ownerRecord__owner_name", curie=RAW.curie('owner_name'),
                   model_uri=RAW.ownerRecord__owner_name, domain=None, range=Optional[str])

slots.factsDeviceRecord__name = Slot(uri=RAW.name, name="factsDeviceRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.factsDeviceRecord__name, domain=None, range=str)

slots.factsDeviceRecord__ibus = Slot(uri=RAW.ibus, name="factsDeviceRecord__ibus", curie=RAW.curie('ibus'),
                   model_uri=RAW.factsDeviceRecord__ibus, domain=None, range=int)

slots.factsDeviceRecord__jbus = Slot(uri=RAW.jbus, name="factsDeviceRecord__jbus", curie=RAW.curie('jbus'),
                   model_uri=RAW.factsDeviceRecord__jbus, domain=None, range=Optional[int])

slots.factsDeviceRecord__mode = Slot(uri=RAW.mode, name="factsDeviceRecord__mode", curie=RAW.curie('mode'),
                   model_uri=RAW.factsDeviceRecord__mode, domain=None, range=Optional[int])

slots.factsDeviceRecord__pdes = Slot(uri=RAW.pdes, name="factsDeviceRecord__pdes", curie=RAW.curie('pdes'),
                   model_uri=RAW.factsDeviceRecord__pdes, domain=None, range=Optional[float])

slots.factsDeviceRecord__qdes = Slot(uri=RAW.qdes, name="factsDeviceRecord__qdes", curie=RAW.curie('qdes'),
                   model_uri=RAW.factsDeviceRecord__qdes, domain=None, range=Optional[float])

slots.factsDeviceRecord__vset = Slot(uri=RAW.vset, name="factsDeviceRecord__vset", curie=RAW.curie('vset'),
                   model_uri=RAW.factsDeviceRecord__vset, domain=None, range=Optional[float])

slots.factsDeviceRecord__shmx = Slot(uri=RAW.shmx, name="factsDeviceRecord__shmx", curie=RAW.curie('shmx'),
                   model_uri=RAW.factsDeviceRecord__shmx, domain=None, range=Optional[float])

slots.factsDeviceRecord__trmx = Slot(uri=RAW.trmx, name="factsDeviceRecord__trmx", curie=RAW.curie('trmx'),
                   model_uri=RAW.factsDeviceRecord__trmx, domain=None, range=Optional[float])

slots.factsDeviceRecord__vtmn = Slot(uri=RAW.vtmn, name="factsDeviceRecord__vtmn", curie=RAW.curie('vtmn'),
                   model_uri=RAW.factsDeviceRecord__vtmn, domain=None, range=Optional[float])

slots.factsDeviceRecord__vtmx = Slot(uri=RAW.vtmx, name="factsDeviceRecord__vtmx", curie=RAW.curie('vtmx'),
                   model_uri=RAW.factsDeviceRecord__vtmx, domain=None, range=Optional[float])

slots.factsDeviceRecord__vsmx = Slot(uri=RAW.vsmx, name="factsDeviceRecord__vsmx", curie=RAW.curie('vsmx'),
                   model_uri=RAW.factsDeviceRecord__vsmx, domain=None, range=Optional[float])

slots.factsDeviceRecord__imx = Slot(uri=RAW.imx, name="factsDeviceRecord__imx", curie=RAW.curie('imx'),
                   model_uri=RAW.factsDeviceRecord__imx, domain=None, range=Optional[float])

slots.factsDeviceRecord__linx = Slot(uri=RAW.linx, name="factsDeviceRecord__linx", curie=RAW.curie('linx'),
                   model_uri=RAW.factsDeviceRecord__linx, domain=None, range=Optional[float])

slots.factsDeviceRecord__rmpct = Slot(uri=RAW.rmpct, name="factsDeviceRecord__rmpct", curie=RAW.curie('rmpct'),
                   model_uri=RAW.factsDeviceRecord__rmpct, domain=None, range=Optional[float])

slots.factsDeviceRecord__owner = Slot(uri=RAW.owner, name="factsDeviceRecord__owner", curie=RAW.curie('owner'),
                   model_uri=RAW.factsDeviceRecord__owner, domain=None, range=Optional[int])

slots.factsDeviceRecord__set1 = Slot(uri=RAW.set1, name="factsDeviceRecord__set1", curie=RAW.curie('set1'),
                   model_uri=RAW.factsDeviceRecord__set1, domain=None, range=Optional[float])

slots.factsDeviceRecord__set2 = Slot(uri=RAW.set2, name="factsDeviceRecord__set2", curie=RAW.curie('set2'),
                   model_uri=RAW.factsDeviceRecord__set2, domain=None, range=Optional[float])

slots.factsDeviceRecord__vsref = Slot(uri=RAW.vsref, name="factsDeviceRecord__vsref", curie=RAW.curie('vsref'),
                   model_uri=RAW.factsDeviceRecord__vsref, domain=None, range=Optional[int])

slots.factsDeviceRecord__remot = Slot(uri=RAW.remot, name="factsDeviceRecord__remot", curie=RAW.curie('remot'),
                   model_uri=RAW.factsDeviceRecord__remot, domain=None, range=Optional[int])

slots.factsDeviceRecord__mname = Slot(uri=RAW.mname, name="factsDeviceRecord__mname", curie=RAW.curie('mname'),
                   model_uri=RAW.factsDeviceRecord__mname, domain=None, range=Optional[str])

slots.factsDeviceRecord__nreg = Slot(uri=RAW.nreg, name="factsDeviceRecord__nreg", curie=RAW.curie('nreg'),
                   model_uri=RAW.factsDeviceRecord__nreg, domain=None, range=Optional[int])

slots.switchedShuntRecord__bus_number = Slot(uri=RAW.bus_number, name="switchedShuntRecord__bus_number", curie=RAW.curie('bus_number'),
                   model_uri=RAW.switchedShuntRecord__bus_number, domain=None, range=int)

slots.switchedShuntRecord__modsw = Slot(uri=RAW.modsw, name="switchedShuntRecord__modsw", curie=RAW.curie('modsw'),
                   model_uri=RAW.switchedShuntRecord__modsw, domain=None, range=Optional[int])

slots.switchedShuntRecord__adjm = Slot(uri=RAW.adjm, name="switchedShuntRecord__adjm", curie=RAW.curie('adjm'),
                   model_uri=RAW.switchedShuntRecord__adjm, domain=None, range=Optional[int])

slots.switchedShuntRecord__status = Slot(uri=RAW.status, name="switchedShuntRecord__status", curie=RAW.curie('status'),
                   model_uri=RAW.switchedShuntRecord__status, domain=None, range=Optional[int])

slots.switchedShuntRecord__vswhi = Slot(uri=RAW.vswhi, name="switchedShuntRecord__vswhi", curie=RAW.curie('vswhi'),
                   model_uri=RAW.switchedShuntRecord__vswhi, domain=None, range=Optional[float])

slots.switchedShuntRecord__vswlo = Slot(uri=RAW.vswlo, name="switchedShuntRecord__vswlo", curie=RAW.curie('vswlo'),
                   model_uri=RAW.switchedShuntRecord__vswlo, domain=None, range=Optional[float])

slots.switchedShuntRecord__swreg = Slot(uri=RAW.swreg, name="switchedShuntRecord__swreg", curie=RAW.curie('swreg'),
                   model_uri=RAW.switchedShuntRecord__swreg, domain=None, range=Optional[int])

slots.switchedShuntRecord__rmpct = Slot(uri=RAW.rmpct, name="switchedShuntRecord__rmpct", curie=RAW.curie('rmpct'),
                   model_uri=RAW.switchedShuntRecord__rmpct, domain=None, range=Optional[float])

slots.switchedShuntRecord__rmidnt = Slot(uri=RAW.rmidnt, name="switchedShuntRecord__rmidnt", curie=RAW.curie('rmidnt'),
                   model_uri=RAW.switchedShuntRecord__rmidnt, domain=None, range=Optional[str])

slots.switchedShuntRecord__binit = Slot(uri=RAW.binit, name="switchedShuntRecord__binit", curie=RAW.curie('binit'),
                   model_uri=RAW.switchedShuntRecord__binit, domain=None, range=Optional[float])

slots.switchedShuntRecord__n1 = Slot(uri=RAW.n1, name="switchedShuntRecord__n1", curie=RAW.curie('n1'),
                   model_uri=RAW.switchedShuntRecord__n1, domain=None, range=Optional[int])

slots.switchedShuntRecord__b1 = Slot(uri=RAW.b1, name="switchedShuntRecord__b1", curie=RAW.curie('b1'),
                   model_uri=RAW.switchedShuntRecord__b1, domain=None, range=Optional[float])

slots.switchedShuntRecord__n2 = Slot(uri=RAW.n2, name="switchedShuntRecord__n2", curie=RAW.curie('n2'),
                   model_uri=RAW.switchedShuntRecord__n2, domain=None, range=Optional[int])

slots.switchedShuntRecord__b2 = Slot(uri=RAW.b2, name="switchedShuntRecord__b2", curie=RAW.curie('b2'),
                   model_uri=RAW.switchedShuntRecord__b2, domain=None, range=Optional[float])

slots.switchedShuntRecord__n3 = Slot(uri=RAW.n3, name="switchedShuntRecord__n3", curie=RAW.curie('n3'),
                   model_uri=RAW.switchedShuntRecord__n3, domain=None, range=Optional[int])

slots.switchedShuntRecord__b3 = Slot(uri=RAW.b3, name="switchedShuntRecord__b3", curie=RAW.curie('b3'),
                   model_uri=RAW.switchedShuntRecord__b3, domain=None, range=Optional[float])

slots.switchedShuntRecord__n4 = Slot(uri=RAW.n4, name="switchedShuntRecord__n4", curie=RAW.curie('n4'),
                   model_uri=RAW.switchedShuntRecord__n4, domain=None, range=Optional[int])

slots.switchedShuntRecord__b4 = Slot(uri=RAW.b4, name="switchedShuntRecord__b4", curie=RAW.curie('b4'),
                   model_uri=RAW.switchedShuntRecord__b4, domain=None, range=Optional[float])

slots.switchedShuntRecord__n5 = Slot(uri=RAW.n5, name="switchedShuntRecord__n5", curie=RAW.curie('n5'),
                   model_uri=RAW.switchedShuntRecord__n5, domain=None, range=Optional[int])

slots.switchedShuntRecord__b5 = Slot(uri=RAW.b5, name="switchedShuntRecord__b5", curie=RAW.curie('b5'),
                   model_uri=RAW.switchedShuntRecord__b5, domain=None, range=Optional[float])

slots.switchedShuntRecord__n6 = Slot(uri=RAW.n6, name="switchedShuntRecord__n6", curie=RAW.curie('n6'),
                   model_uri=RAW.switchedShuntRecord__n6, domain=None, range=Optional[int])

slots.switchedShuntRecord__b6 = Slot(uri=RAW.b6, name="switchedShuntRecord__b6", curie=RAW.curie('b6'),
                   model_uri=RAW.switchedShuntRecord__b6, domain=None, range=Optional[float])

slots.switchedShuntRecord__n7 = Slot(uri=RAW.n7, name="switchedShuntRecord__n7", curie=RAW.curie('n7'),
                   model_uri=RAW.switchedShuntRecord__n7, domain=None, range=Optional[int])

slots.switchedShuntRecord__b7 = Slot(uri=RAW.b7, name="switchedShuntRecord__b7", curie=RAW.curie('b7'),
                   model_uri=RAW.switchedShuntRecord__b7, domain=None, range=Optional[float])

slots.switchedShuntRecord__n8 = Slot(uri=RAW.n8, name="switchedShuntRecord__n8", curie=RAW.curie('n8'),
                   model_uri=RAW.switchedShuntRecord__n8, domain=None, range=Optional[int])

slots.switchedShuntRecord__b8 = Slot(uri=RAW.b8, name="switchedShuntRecord__b8", curie=RAW.curie('b8'),
                   model_uri=RAW.switchedShuntRecord__b8, domain=None, range=Optional[float])

slots.switchedShuntRecord__nreg = Slot(uri=RAW.nreg, name="switchedShuntRecord__nreg", curie=RAW.curie('nreg'),
                   model_uri=RAW.switchedShuntRecord__nreg, domain=None, range=Optional[int])

slots.gneDeviceRecord__name = Slot(uri=RAW.name, name="gneDeviceRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.gneDeviceRecord__name, domain=None, range=str)

slots.gneDeviceRecord__model = Slot(uri=RAW.model, name="gneDeviceRecord__model", curie=RAW.curie('model'),
                   model_uri=RAW.gneDeviceRecord__model, domain=None, range=str)

slots.gneDeviceRecord__nterm = Slot(uri=RAW.nterm, name="gneDeviceRecord__nterm", curie=RAW.curie('nterm'),
                   model_uri=RAW.gneDeviceRecord__nterm, domain=None, range=int)

slots.gneDeviceRecord__bus_numbers = Slot(uri=RAW.bus_numbers, name="gneDeviceRecord__bus_numbers", curie=RAW.curie('bus_numbers'),
                   model_uri=RAW.gneDeviceRecord__bus_numbers, domain=None, range=Optional[Union[int, list[int]]])

slots.gneDeviceRecord__nreal = Slot(uri=RAW.nreal, name="gneDeviceRecord__nreal", curie=RAW.curie('nreal'),
                   model_uri=RAW.gneDeviceRecord__nreal, domain=None, range=Optional[int])

slots.gneDeviceRecord__nintg = Slot(uri=RAW.nintg, name="gneDeviceRecord__nintg", curie=RAW.curie('nintg'),
                   model_uri=RAW.gneDeviceRecord__nintg, domain=None, range=Optional[int])

slots.gneDeviceRecord__nchar = Slot(uri=RAW.nchar, name="gneDeviceRecord__nchar", curie=RAW.curie('nchar'),
                   model_uri=RAW.gneDeviceRecord__nchar, domain=None, range=Optional[int])

slots.gneDeviceRecord__status = Slot(uri=RAW.status, name="gneDeviceRecord__status", curie=RAW.curie('status'),
                   model_uri=RAW.gneDeviceRecord__status, domain=None, range=Optional[int])

slots.gneDeviceRecord__owner = Slot(uri=RAW.owner, name="gneDeviceRecord__owner", curie=RAW.curie('owner'),
                   model_uri=RAW.gneDeviceRecord__owner, domain=None, range=Optional[int])

slots.gneDeviceRecord__nmetr = Slot(uri=RAW.nmetr, name="gneDeviceRecord__nmetr", curie=RAW.curie('nmetr'),
                   model_uri=RAW.gneDeviceRecord__nmetr, domain=None, range=Optional[int])

slots.gneDeviceRecord__real_data = Slot(uri=RAW.real_data, name="gneDeviceRecord__real_data", curie=RAW.curie('real_data'),
                   model_uri=RAW.gneDeviceRecord__real_data, domain=None, range=Optional[Union[float, list[float]]])

slots.gneDeviceRecord__integer_data = Slot(uri=RAW.integer_data, name="gneDeviceRecord__integer_data", curie=RAW.curie('integer_data'),
                   model_uri=RAW.gneDeviceRecord__integer_data, domain=None, range=Optional[Union[int, list[int]]])

slots.gneDeviceRecord__character_data = Slot(uri=RAW.character_data, name="gneDeviceRecord__character_data", curie=RAW.curie('character_data'),
                   model_uri=RAW.gneDeviceRecord__character_data, domain=None, range=Optional[Union[str, list[str]]])

slots.inductionMachineRecord__bus_id = Slot(uri=RAW.bus_id, name="inductionMachineRecord__bus_id", curie=RAW.curie('bus_id'),
                   model_uri=RAW.inductionMachineRecord__bus_id, domain=None, range=int)

slots.inductionMachineRecord__name = Slot(uri=RAW.name, name="inductionMachineRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.inductionMachineRecord__name, domain=None, range=Optional[str])

slots.inductionMachineRecord__status = Slot(uri=RAW.status, name="inductionMachineRecord__status", curie=RAW.curie('status'),
                   model_uri=RAW.inductionMachineRecord__status, domain=None, range=Optional[int])

slots.inductionMachineRecord__scode = Slot(uri=RAW.scode, name="inductionMachineRecord__scode", curie=RAW.curie('scode'),
                   model_uri=RAW.inductionMachineRecord__scode, domain=None, range=Optional[int])

slots.inductionMachineRecord__dcode = Slot(uri=RAW.dcode, name="inductionMachineRecord__dcode", curie=RAW.curie('dcode'),
                   model_uri=RAW.inductionMachineRecord__dcode, domain=None, range=Optional[int])

slots.inductionMachineRecord__area = Slot(uri=RAW.area, name="inductionMachineRecord__area", curie=RAW.curie('area'),
                   model_uri=RAW.inductionMachineRecord__area, domain=None, range=Optional[int])

slots.inductionMachineRecord__zone = Slot(uri=RAW.zone, name="inductionMachineRecord__zone", curie=RAW.curie('zone'),
                   model_uri=RAW.inductionMachineRecord__zone, domain=None, range=Optional[int])

slots.inductionMachineRecord__owner = Slot(uri=RAW.owner, name="inductionMachineRecord__owner", curie=RAW.curie('owner'),
                   model_uri=RAW.inductionMachineRecord__owner, domain=None, range=Optional[int])

slots.inductionMachineRecord__tcode = Slot(uri=RAW.tcode, name="inductionMachineRecord__tcode", curie=RAW.curie('tcode'),
                   model_uri=RAW.inductionMachineRecord__tcode, domain=None, range=Optional[int])

slots.inductionMachineRecord__bcode = Slot(uri=RAW.bcode, name="inductionMachineRecord__bcode", curie=RAW.curie('bcode'),
                   model_uri=RAW.inductionMachineRecord__bcode, domain=None, range=Optional[int])

slots.inductionMachineRecord__mbase = Slot(uri=RAW.mbase, name="inductionMachineRecord__mbase", curie=RAW.curie('mbase'),
                   model_uri=RAW.inductionMachineRecord__mbase, domain=None, range=Optional[float])

slots.inductionMachineRecord__ratekv = Slot(uri=RAW.ratekv, name="inductionMachineRecord__ratekv", curie=RAW.curie('ratekv'),
                   model_uri=RAW.inductionMachineRecord__ratekv, domain=None, range=Optional[float])

slots.inductionMachineRecord__pcode = Slot(uri=RAW.pcode, name="inductionMachineRecord__pcode", curie=RAW.curie('pcode'),
                   model_uri=RAW.inductionMachineRecord__pcode, domain=None, range=Optional[int])

slots.inductionMachineRecord__pset = Slot(uri=RAW.pset, name="inductionMachineRecord__pset", curie=RAW.curie('pset'),
                   model_uri=RAW.inductionMachineRecord__pset, domain=None, range=Optional[float])

slots.inductionMachineRecord__h = Slot(uri=RAW.h, name="inductionMachineRecord__h", curie=RAW.curie('h'),
                   model_uri=RAW.inductionMachineRecord__h, domain=None, range=Optional[float])

slots.inductionMachineRecord__a = Slot(uri=RAW.a, name="inductionMachineRecord__a", curie=RAW.curie('a'),
                   model_uri=RAW.inductionMachineRecord__a, domain=None, range=Optional[float])

slots.inductionMachineRecord__b = Slot(uri=RAW.b, name="inductionMachineRecord__b", curie=RAW.curie('b'),
                   model_uri=RAW.inductionMachineRecord__b, domain=None, range=Optional[float])

slots.inductionMachineRecord__d = Slot(uri=RAW.d, name="inductionMachineRecord__d", curie=RAW.curie('d'),
                   model_uri=RAW.inductionMachineRecord__d, domain=None, range=Optional[float])

slots.inductionMachineRecord__e = Slot(uri=RAW.e, name="inductionMachineRecord__e", curie=RAW.curie('e'),
                   model_uri=RAW.inductionMachineRecord__e, domain=None, range=Optional[float])

slots.inductionMachineRecord__ra = Slot(uri=RAW.ra, name="inductionMachineRecord__ra", curie=RAW.curie('ra'),
                   model_uri=RAW.inductionMachineRecord__ra, domain=None, range=Optional[float])

slots.inductionMachineRecord__xa = Slot(uri=RAW.xa, name="inductionMachineRecord__xa", curie=RAW.curie('xa'),
                   model_uri=RAW.inductionMachineRecord__xa, domain=None, range=Optional[float])

slots.inductionMachineRecord__xm = Slot(uri=RAW.xm, name="inductionMachineRecord__xm", curie=RAW.curie('xm'),
                   model_uri=RAW.inductionMachineRecord__xm, domain=None, range=Optional[float])

slots.inductionMachineRecord__r1 = Slot(uri=RAW.r1, name="inductionMachineRecord__r1", curie=RAW.curie('r1'),
                   model_uri=RAW.inductionMachineRecord__r1, domain=None, range=Optional[float])

slots.inductionMachineRecord__x1 = Slot(uri=RAW.x1, name="inductionMachineRecord__x1", curie=RAW.curie('x1'),
                   model_uri=RAW.inductionMachineRecord__x1, domain=None, range=Optional[float])

slots.inductionMachineRecord__r2 = Slot(uri=RAW.r2, name="inductionMachineRecord__r2", curie=RAW.curie('r2'),
                   model_uri=RAW.inductionMachineRecord__r2, domain=None, range=Optional[float])

slots.inductionMachineRecord__x2 = Slot(uri=RAW.x2, name="inductionMachineRecord__x2", curie=RAW.curie('x2'),
                   model_uri=RAW.inductionMachineRecord__x2, domain=None, range=Optional[float])

slots.inductionMachineRecord__x3 = Slot(uri=RAW.x3, name="inductionMachineRecord__x3", curie=RAW.curie('x3'),
                   model_uri=RAW.inductionMachineRecord__x3, domain=None, range=Optional[float])

slots.inductionMachineRecord__e1 = Slot(uri=RAW.e1, name="inductionMachineRecord__e1", curie=RAW.curie('e1'),
                   model_uri=RAW.inductionMachineRecord__e1, domain=None, range=Optional[float])

slots.inductionMachineRecord__se1 = Slot(uri=RAW.se1, name="inductionMachineRecord__se1", curie=RAW.curie('se1'),
                   model_uri=RAW.inductionMachineRecord__se1, domain=None, range=Optional[float])

slots.inductionMachineRecord__e2 = Slot(uri=RAW.e2, name="inductionMachineRecord__e2", curie=RAW.curie('e2'),
                   model_uri=RAW.inductionMachineRecord__e2, domain=None, range=Optional[float])

slots.inductionMachineRecord__se2 = Slot(uri=RAW.se2, name="inductionMachineRecord__se2", curie=RAW.curie('se2'),
                   model_uri=RAW.inductionMachineRecord__se2, domain=None, range=Optional[float])

slots.inductionMachineRecord__ia1 = Slot(uri=RAW.ia1, name="inductionMachineRecord__ia1", curie=RAW.curie('ia1'),
                   model_uri=RAW.inductionMachineRecord__ia1, domain=None, range=Optional[float])

slots.inductionMachineRecord__ia2 = Slot(uri=RAW.ia2, name="inductionMachineRecord__ia2", curie=RAW.curie('ia2'),
                   model_uri=RAW.inductionMachineRecord__ia2, domain=None, range=Optional[float])

slots.inductionMachineRecord__xamult = Slot(uri=RAW.xamult, name="inductionMachineRecord__xamult", curie=RAW.curie('xamult'),
                   model_uri=RAW.inductionMachineRecord__xamult, domain=None, range=Optional[float])

slots.substationRecord__substation_number = Slot(uri=RAW.substation_number, name="substationRecord__substation_number", curie=RAW.curie('substation_number'),
                   model_uri=RAW.substationRecord__substation_number, domain=None, range=URIRef)

slots.substationRecord__name = Slot(uri=RAW.name, name="substationRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.substationRecord__name, domain=None, range=Optional[str])

slots.substationRecord__latitude = Slot(uri=RAW.latitude, name="substationRecord__latitude", curie=RAW.curie('latitude'),
                   model_uri=RAW.substationRecord__latitude, domain=None, range=Optional[float])

slots.substationRecord__longitude = Slot(uri=RAW.longitude, name="substationRecord__longitude", curie=RAW.curie('longitude'),
                   model_uri=RAW.substationRecord__longitude, domain=None, range=Optional[float])

slots.substationRecord__grounding_resistance = Slot(uri=RAW.grounding_resistance, name="substationRecord__grounding_resistance", curie=RAW.curie('grounding_resistance'),
                   model_uri=RAW.substationRecord__grounding_resistance, domain=None, range=Optional[float])

slots.substationNodeRecord__node_number = Slot(uri=RAW.node_number, name="substationNodeRecord__node_number", curie=RAW.curie('node_number'),
                   model_uri=RAW.substationNodeRecord__node_number, domain=None, range=int)

slots.substationNodeRecord__name = Slot(uri=RAW.name, name="substationNodeRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.substationNodeRecord__name, domain=None, range=Optional[str])

slots.substationNodeRecord__bus_number = Slot(uri=RAW.bus_number, name="substationNodeRecord__bus_number", curie=RAW.curie('bus_number'),
                   model_uri=RAW.substationNodeRecord__bus_number, domain=None, range=int)

slots.substationNodeRecord__status = Slot(uri=RAW.status, name="substationNodeRecord__status", curie=RAW.curie('status'),
                   model_uri=RAW.substationNodeRecord__status, domain=None, range=Optional[int])

slots.substationNodeRecord__vm = Slot(uri=RAW.vm, name="substationNodeRecord__vm", curie=RAW.curie('vm'),
                   model_uri=RAW.substationNodeRecord__vm, domain=None, range=Optional[float])

slots.substationNodeRecord__va = Slot(uri=RAW.va, name="substationNodeRecord__va", curie=RAW.curie('va'),
                   model_uri=RAW.substationNodeRecord__va, domain=None, range=Optional[float])

slots.substationNodeRecord__substation_number = Slot(uri=RAW.substation_number, name="substationNodeRecord__substation_number", curie=RAW.curie('substation_number'),
                   model_uri=RAW.substationNodeRecord__substation_number, domain=None, range=Optional[int])

slots.stationSwitchingDeviceRecord__from_node = Slot(uri=RAW.from_node, name="stationSwitchingDeviceRecord__from_node", curie=RAW.curie('from_node'),
                   model_uri=RAW.stationSwitchingDeviceRecord__from_node, domain=None, range=int)

slots.stationSwitchingDeviceRecord__to_node = Slot(uri=RAW.to_node, name="stationSwitchingDeviceRecord__to_node", curie=RAW.curie('to_node'),
                   model_uri=RAW.stationSwitchingDeviceRecord__to_node, domain=None, range=int)

slots.stationSwitchingDeviceRecord__circuit = Slot(uri=RAW.circuit, name="stationSwitchingDeviceRecord__circuit", curie=RAW.curie('circuit'),
                   model_uri=RAW.stationSwitchingDeviceRecord__circuit, domain=None, range=Optional[str])

slots.stationSwitchingDeviceRecord__name = Slot(uri=RAW.name, name="stationSwitchingDeviceRecord__name", curie=RAW.curie('name'),
                   model_uri=RAW.stationSwitchingDeviceRecord__name, domain=None, range=Optional[str])

slots.stationSwitchingDeviceRecord__device_type = Slot(uri=RAW.device_type, name="stationSwitchingDeviceRecord__device_type", curie=RAW.curie('device_type'),
                   model_uri=RAW.stationSwitchingDeviceRecord__device_type, domain=None, range=int)

slots.stationSwitchingDeviceRecord__status = Slot(uri=RAW.status, name="stationSwitchingDeviceRecord__status", curie=RAW.curie('status'),
                   model_uri=RAW.stationSwitchingDeviceRecord__status, domain=None, range=Optional[int])

slots.stationSwitchingDeviceRecord__normal_status = Slot(uri=RAW.normal_status, name="stationSwitchingDeviceRecord__normal_status", curie=RAW.curie('normal_status'),
                   model_uri=RAW.stationSwitchingDeviceRecord__normal_status, domain=None, range=Optional[int])

slots.stationSwitchingDeviceRecord__reactance = Slot(uri=RAW.reactance, name="stationSwitchingDeviceRecord__reactance", curie=RAW.curie('reactance'),
                   model_uri=RAW.stationSwitchingDeviceRecord__reactance, domain=None, range=Optional[float])

slots.stationSwitchingDeviceRecord__rate1 = Slot(uri=RAW.rate1, name="stationSwitchingDeviceRecord__rate1", curie=RAW.curie('rate1'),
                   model_uri=RAW.stationSwitchingDeviceRecord__rate1, domain=None, range=Optional[float])

slots.stationSwitchingDeviceRecord__rate2 = Slot(uri=RAW.rate2, name="stationSwitchingDeviceRecord__rate2", curie=RAW.curie('rate2'),
                   model_uri=RAW.stationSwitchingDeviceRecord__rate2, domain=None, range=Optional[float])

slots.stationSwitchingDeviceRecord__rate3 = Slot(uri=RAW.rate3, name="stationSwitchingDeviceRecord__rate3", curie=RAW.curie('rate3'),
                   model_uri=RAW.stationSwitchingDeviceRecord__rate3, domain=None, range=Optional[float])

slots.stationSwitchingDeviceRecord__substation_number = Slot(uri=RAW.substation_number, name="stationSwitchingDeviceRecord__substation_number", curie=RAW.curie('substation_number'),
                   model_uri=RAW.stationSwitchingDeviceRecord__substation_number, domain=None, range=Optional[int])

slots.equipmentTerminalRecord__bus_number = Slot(uri=RAW.bus_number, name="equipmentTerminalRecord__bus_number", curie=RAW.curie('bus_number'),
                   model_uri=RAW.equipmentTerminalRecord__bus_number, domain=None, range=int)

slots.equipmentTerminalRecord__node_number = Slot(uri=RAW.node_number, name="equipmentTerminalRecord__node_number", curie=RAW.curie('node_number'),
                   model_uri=RAW.equipmentTerminalRecord__node_number, domain=None, range=int)

slots.equipmentTerminalRecord__terminal_type = Slot(uri=RAW.terminal_type, name="equipmentTerminalRecord__terminal_type", curie=RAW.curie('terminal_type'),
                   model_uri=RAW.equipmentTerminalRecord__terminal_type, domain=None, range=str)

slots.equipmentTerminalRecord__j_bus = Slot(uri=RAW.j_bus, name="equipmentTerminalRecord__j_bus", curie=RAW.curie('j_bus'),
                   model_uri=RAW.equipmentTerminalRecord__j_bus, domain=None, range=Optional[int])

slots.equipmentTerminalRecord__k_bus = Slot(uri=RAW.k_bus, name="equipmentTerminalRecord__k_bus", curie=RAW.curie('k_bus'),
                   model_uri=RAW.equipmentTerminalRecord__k_bus, domain=None, range=Optional[int])

slots.equipmentTerminalRecord__identifier = Slot(uri=RAW.identifier, name="equipmentTerminalRecord__identifier", curie=RAW.curie('identifier'),
                   model_uri=RAW.equipmentTerminalRecord__identifier, domain=None, range=Optional[str])

slots.equipmentTerminalRecord__substation_number = Slot(uri=RAW.substation_number, name="equipmentTerminalRecord__substation_number", curie=RAW.curie('substation_number'),
                   model_uri=RAW.equipmentTerminalRecord__substation_number, domain=None, range=Optional[int])

