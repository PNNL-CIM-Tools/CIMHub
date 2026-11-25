# Auto generated from opendss.yaml by pythongen.py version: 0.0.1
# Schema: opendss
#
# id: https://gridappsd.github.io/dss-graph/opendss
# description: Complete LinkML schema for all OpenDSS component types. This schema imports all individual component schemas from their respective categories.
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

from linkml_runtime.linkml_model.types import Boolean, Float, Integer, String
from linkml_runtime.utils.metamodelcore import Bool

metamodel_version = "1.12.0"
version = "1.0.0"

# Namespaces
CIM = CurieNamespace('cim', 'http://cim.ucaiug.io/cim101/draft#')
DSS = CurieNamespace('dss', 'https://gridappsd.github.io/dss-graph/')
LINKML = CurieNamespace('linkml', 'https://w3id.org/linkml/')
DEFAULT_ = DSS


# Types

# Class references
class LoadName(extended_str):
    pass


class GeneratorName(extended_str):
    pass


class Generic5Name(extended_str):
    pass


class GiclineName(extended_str):
    pass


class Indmach012Name(extended_str):
    pass


class PvsystemName(extended_str):
    pass


class StorageName(extended_str):
    pass


class UpfcName(extended_str):
    pass


class VccsName(extended_str):
    pass


class VsconverterName(extended_str):
    pass


class WindgenName(extended_str):
    pass


class AutotransName(extended_str):
    pass


class CapacitorName(extended_str):
    pass


class GictransformerName(extended_str):
    pass


class LineName(extended_str):
    pass


class ReactorName(extended_str):
    pass


class TransformerName(extended_str):
    pass


class CapcontrolName(extended_str):
    pass


class EspvlcontrolName(extended_str):
    pass


class ExpcontrolName(extended_str):
    pass


class FuseName(extended_str):
    pass


class GendispatcherName(extended_str):
    pass


class InvcontrolName(extended_str):
    pass


class PycontrolName(extended_str):
    pass


class RecloserName(extended_str):
    pass


class RegcontrolName(extended_str):
    pass


class RelayName(extended_str):
    pass


class StoragecontrollerName(extended_str):
    pass


class SwtcontrolName(extended_str):
    pass


class UpfccontrolName(extended_str):
    pass


class BuscoordsName(extended_str):
    pass


class CndataName(extended_str):
    pass


class DynamicexpName(extended_str):
    pass


class GrowthshapeName(extended_str):
    pass


class LinecodeName(extended_str):
    pass


class LinegeometryName(extended_str):
    pass


class LinespacingName(extended_str):
    pass


class LoadshapeName(extended_str):
    pass


class PriceshapeName(extended_str):
    pass


class SpectrumName(extended_str):
    pass


class TccCurveName(extended_str):
    pass


class TsdataName(extended_str):
    pass


class TshapeName(extended_str):
    pass


class WiredataName(extended_str):
    pass


class XfmrcodeName(extended_str):
    pass


class XycurveName(extended_str):
    pass


class EnergymeterName(extended_str):
    pass


class FmonitorName(extended_str):
    pass


class MonitorName(extended_str):
    pass


class SensorName(extended_str):
    pass


class FaultName(extended_str):
    pass


class GicsourceName(extended_str):
    pass


class IsourceName(extended_str):
    pass


class OptionsName(extended_str):
    pass


class VsourceName(extended_str):
    pass


@dataclass(repr=False)
class Load(YAMLRoot):
    """
    A Load object in OpenDSS representing an energy consumer connected to a bus in the distribution system.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Load"]
    class_class_curie: ClassVar[str] = "dss:Load"
    class_name: ClassVar[str] = "Load"
    class_model_uri: ClassVar[URIRef] = DSS.Load

    name: Union[str, LoadName] = None
    bus1: str = None
    phases: Optional[int] = None
    kV: Optional[float] = None
    kW: Optional[float] = None
    pf: Optional[float] = None
    model: Optional[Union[str, "LoadModel"]] = None
    yearly: Optional[str] = None
    daily: Optional[str] = None
    duty: Optional[str] = None
    growth: Optional[str] = None
    conn: Optional[Union[str, "ConnectionType"]] = None
    kvar: Optional[float] = None
    Rneut: Optional[float] = None
    Xneut: Optional[float] = None
    status: Optional[Union[str, "LoadStatus"]] = None
    load_class: Optional[int] = None
    Vminpu: Optional[float] = None
    Vmaxpu: Optional[float] = None
    Vminnorm: Optional[float] = None
    Vminemerg: Optional[float] = None
    xfkVA: Optional[float] = None
    allocationfactor: Optional[float] = None
    kVA: Optional[float] = None
    pct_mean: Optional[float] = None
    pct_stddev: Optional[float] = None
    CVRwatts: Optional[float] = None
    CVRvars: Optional[float] = None
    kwh: Optional[float] = None
    kwhdays: Optional[float] = None
    Cfactor: Optional[float] = None
    CVRcurve: Optional[str] = None
    NumCust: Optional[int] = None
    ZIPV: Optional[Union[float, list[float]]] = empty_list()
    pct_SeriesRL: Optional[float] = None
    RelWeight: Optional[float] = None
    Vlowpu: Optional[float] = None
    puXharm: Optional[float] = None
    XRharm: Optional[float] = None
    spectrum: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, LoadName):
            self.name = LoadName(self.name)

        if self._is_empty(self.bus1):
            self.MissingRequiredField("bus1")
        if not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.kV is not None and not isinstance(self.kV, float):
            self.kV = float(self.kV)

        if self.kW is not None and not isinstance(self.kW, float):
            self.kW = float(self.kW)

        if self.pf is not None and not isinstance(self.pf, float):
            self.pf = float(self.pf)

        if self.model is not None and not isinstance(self.model, LoadModel):
            self.model = LoadModel(self.model)

        if self.yearly is not None and not isinstance(self.yearly, str):
            self.yearly = str(self.yearly)

        if self.daily is not None and not isinstance(self.daily, str):
            self.daily = str(self.daily)

        if self.duty is not None and not isinstance(self.duty, str):
            self.duty = str(self.duty)

        if self.growth is not None and not isinstance(self.growth, str):
            self.growth = str(self.growth)

        if self.conn is not None and not isinstance(self.conn, ConnectionType):
            self.conn = ConnectionType(self.conn)

        if self.kvar is not None and not isinstance(self.kvar, float):
            self.kvar = float(self.kvar)

        if self.Rneut is not None and not isinstance(self.Rneut, float):
            self.Rneut = float(self.Rneut)

        if self.Xneut is not None and not isinstance(self.Xneut, float):
            self.Xneut = float(self.Xneut)

        if self.status is not None and not isinstance(self.status, LoadStatus):
            self.status = LoadStatus(self.status)

        if self.load_class is not None and not isinstance(self.load_class, int):
            self.load_class = int(self.load_class)

        if self.Vminpu is not None and not isinstance(self.Vminpu, float):
            self.Vminpu = float(self.Vminpu)

        if self.Vmaxpu is not None and not isinstance(self.Vmaxpu, float):
            self.Vmaxpu = float(self.Vmaxpu)

        if self.Vminnorm is not None and not isinstance(self.Vminnorm, float):
            self.Vminnorm = float(self.Vminnorm)

        if self.Vminemerg is not None and not isinstance(self.Vminemerg, float):
            self.Vminemerg = float(self.Vminemerg)

        if self.xfkVA is not None and not isinstance(self.xfkVA, float):
            self.xfkVA = float(self.xfkVA)

        if self.allocationfactor is not None and not isinstance(self.allocationfactor, float):
            self.allocationfactor = float(self.allocationfactor)

        if self.kVA is not None and not isinstance(self.kVA, float):
            self.kVA = float(self.kVA)

        if self.pct_mean is not None and not isinstance(self.pct_mean, float):
            self.pct_mean = float(self.pct_mean)

        if self.pct_stddev is not None and not isinstance(self.pct_stddev, float):
            self.pct_stddev = float(self.pct_stddev)

        if self.CVRwatts is not None and not isinstance(self.CVRwatts, float):
            self.CVRwatts = float(self.CVRwatts)

        if self.CVRvars is not None and not isinstance(self.CVRvars, float):
            self.CVRvars = float(self.CVRvars)

        if self.kwh is not None and not isinstance(self.kwh, float):
            self.kwh = float(self.kwh)

        if self.kwhdays is not None and not isinstance(self.kwhdays, float):
            self.kwhdays = float(self.kwhdays)

        if self.Cfactor is not None and not isinstance(self.Cfactor, float):
            self.Cfactor = float(self.Cfactor)

        if self.CVRcurve is not None and not isinstance(self.CVRcurve, str):
            self.CVRcurve = str(self.CVRcurve)

        if self.NumCust is not None and not isinstance(self.NumCust, int):
            self.NumCust = int(self.NumCust)

        if not isinstance(self.ZIPV, list):
            self.ZIPV = [self.ZIPV] if self.ZIPV is not None else []
        self.ZIPV = [v if isinstance(v, float) else float(v) for v in self.ZIPV]

        if self.pct_SeriesRL is not None and not isinstance(self.pct_SeriesRL, float):
            self.pct_SeriesRL = float(self.pct_SeriesRL)

        if self.RelWeight is not None and not isinstance(self.RelWeight, float):
            self.RelWeight = float(self.RelWeight)

        if self.Vlowpu is not None and not isinstance(self.Vlowpu, float):
            self.Vlowpu = float(self.Vlowpu)

        if self.puXharm is not None and not isinstance(self.puXharm, float):
            self.puXharm = float(self.puXharm)

        if self.XRharm is not None and not isinstance(self.XRharm, float):
            self.XRharm = float(self.XRharm)

        if self.spectrum is not None and not isinstance(self.spectrum, str):
            self.spectrum = str(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Generator(YAMLRoot):
    """
    A Generator object in OpenDSS representing a power generator connected to a bus in the distribution system.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Generator"]
    class_class_curie: ClassVar[str] = "dss:Generator"
    class_name: ClassVar[str] = "Generator"
    class_model_uri: ClassVar[URIRef] = DSS.Generator

    name: Union[str, GeneratorName] = None
    phases: Optional[int] = None
    bus1: Optional[str] = None
    kv: Optional[float] = None
    kW: Optional[float] = None
    pf: Optional[float] = None
    kvar: Optional[float] = None
    model: Optional[Union[str, "GeneratorModel"]] = None
    Vminpu: Optional[float] = None
    Vmaxpu: Optional[float] = None
    yearly: Optional[str] = None
    daily: Optional[str] = None
    duty: Optional[str] = None
    dispmode: Optional[Union[str, "DispatchMode"]] = None
    dispvalue: Optional[float] = None
    conn: Optional[Union[str, "ConnectionType"]] = None
    status: Optional[Union[str, "GenStatus"]] = None
    gen_class: Optional[int] = None
    Vpu: Optional[float] = None
    maxkvar: Optional[float] = None
    minkvar: Optional[float] = None
    pvfactor: Optional[float] = None
    forceon: Optional[Union[bool, Bool]] = None
    kVA: Optional[float] = None
    MVA: Optional[float] = None
    Xd: Optional[float] = None
    Xdp: Optional[float] = None
    Xdpp: Optional[float] = None
    H: Optional[float] = None
    D: Optional[float] = None
    UserModel: Optional[str] = None
    UserData: Optional[str] = None
    ShaftModel: Optional[str] = None
    ShaftData: Optional[str] = None
    DutyStart: Optional[float] = None
    debugtrace: Optional[Union[bool, Bool]] = None
    Balanced: Optional[Union[bool, Bool]] = None
    XRdp: Optional[float] = None
    UseFuel: Optional[Union[bool, Bool]] = None
    FuelkWh: Optional[float] = None
    pct_Fuel: Optional[float] = None
    pct_Reserve: Optional[float] = None
    Refuel: Optional[Union[bool, Bool]] = None
    DynamicEq: Optional[str] = None
    DynOut: Optional[Union[str, list[str]]] = empty_list()
    spectrum: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, GeneratorName):
            self.name = GeneratorName(self.name)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.bus1 is not None and not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.kv is not None and not isinstance(self.kv, float):
            self.kv = float(self.kv)

        if self.kW is not None and not isinstance(self.kW, float):
            self.kW = float(self.kW)

        if self.pf is not None and not isinstance(self.pf, float):
            self.pf = float(self.pf)

        if self.kvar is not None and not isinstance(self.kvar, float):
            self.kvar = float(self.kvar)

        if self.model is not None and not isinstance(self.model, GeneratorModel):
            self.model = GeneratorModel(self.model)

        if self.Vminpu is not None and not isinstance(self.Vminpu, float):
            self.Vminpu = float(self.Vminpu)

        if self.Vmaxpu is not None and not isinstance(self.Vmaxpu, float):
            self.Vmaxpu = float(self.Vmaxpu)

        if self.yearly is not None and not isinstance(self.yearly, str):
            self.yearly = str(self.yearly)

        if self.daily is not None and not isinstance(self.daily, str):
            self.daily = str(self.daily)

        if self.duty is not None and not isinstance(self.duty, str):
            self.duty = str(self.duty)

        if self.dispmode is not None and not isinstance(self.dispmode, DispatchMode):
            self.dispmode = DispatchMode(self.dispmode)

        if self.dispvalue is not None and not isinstance(self.dispvalue, float):
            self.dispvalue = float(self.dispvalue)

        if self.conn is not None and not isinstance(self.conn, ConnectionType):
            self.conn = ConnectionType(self.conn)

        if self.status is not None and not isinstance(self.status, GenStatus):
            self.status = GenStatus(self.status)

        if self.gen_class is not None and not isinstance(self.gen_class, int):
            self.gen_class = int(self.gen_class)

        if self.Vpu is not None and not isinstance(self.Vpu, float):
            self.Vpu = float(self.Vpu)

        if self.maxkvar is not None and not isinstance(self.maxkvar, float):
            self.maxkvar = float(self.maxkvar)

        if self.minkvar is not None and not isinstance(self.minkvar, float):
            self.minkvar = float(self.minkvar)

        if self.pvfactor is not None and not isinstance(self.pvfactor, float):
            self.pvfactor = float(self.pvfactor)

        if self.forceon is not None and not isinstance(self.forceon, Bool):
            self.forceon = Bool(self.forceon)

        if self.kVA is not None and not isinstance(self.kVA, float):
            self.kVA = float(self.kVA)

        if self.MVA is not None and not isinstance(self.MVA, float):
            self.MVA = float(self.MVA)

        if self.Xd is not None and not isinstance(self.Xd, float):
            self.Xd = float(self.Xd)

        if self.Xdp is not None and not isinstance(self.Xdp, float):
            self.Xdp = float(self.Xdp)

        if self.Xdpp is not None and not isinstance(self.Xdpp, float):
            self.Xdpp = float(self.Xdpp)

        if self.H is not None and not isinstance(self.H, float):
            self.H = float(self.H)

        if self.D is not None and not isinstance(self.D, float):
            self.D = float(self.D)

        if self.UserModel is not None and not isinstance(self.UserModel, str):
            self.UserModel = str(self.UserModel)

        if self.UserData is not None and not isinstance(self.UserData, str):
            self.UserData = str(self.UserData)

        if self.ShaftModel is not None and not isinstance(self.ShaftModel, str):
            self.ShaftModel = str(self.ShaftModel)

        if self.ShaftData is not None and not isinstance(self.ShaftData, str):
            self.ShaftData = str(self.ShaftData)

        if self.DutyStart is not None and not isinstance(self.DutyStart, float):
            self.DutyStart = float(self.DutyStart)

        if self.debugtrace is not None and not isinstance(self.debugtrace, Bool):
            self.debugtrace = Bool(self.debugtrace)

        if self.Balanced is not None and not isinstance(self.Balanced, Bool):
            self.Balanced = Bool(self.Balanced)

        if self.XRdp is not None and not isinstance(self.XRdp, float):
            self.XRdp = float(self.XRdp)

        if self.UseFuel is not None and not isinstance(self.UseFuel, Bool):
            self.UseFuel = Bool(self.UseFuel)

        if self.FuelkWh is not None and not isinstance(self.FuelkWh, float):
            self.FuelkWh = float(self.FuelkWh)

        if self.pct_Fuel is not None and not isinstance(self.pct_Fuel, float):
            self.pct_Fuel = float(self.pct_Fuel)

        if self.pct_Reserve is not None and not isinstance(self.pct_Reserve, float):
            self.pct_Reserve = float(self.pct_Reserve)

        if self.Refuel is not None and not isinstance(self.Refuel, Bool):
            self.Refuel = Bool(self.Refuel)

        if self.DynamicEq is not None and not isinstance(self.DynamicEq, str):
            self.DynamicEq = str(self.DynamicEq)

        if not isinstance(self.DynOut, list):
            self.DynOut = [self.DynOut] if self.DynOut is not None else []
        self.DynOut = [v if isinstance(v, str) else str(v) for v in self.DynOut]

        if self.spectrum is not None and not isinstance(self.spectrum, str):
            self.spectrum = str(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Generic5(YAMLRoot):
    """
    A Generic5 object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Generic5"]
    class_class_curie: ClassVar[str] = "dss:Generic5"
    class_name: ClassVar[str] = "Generic5"
    class_model_uri: ClassVar[URIRef] = DSS.Generic5

    name: Union[str, Generic5Name] = None
    phases: Optional[int] = None
    bus1: Optional[str] = None
    kv: Optional[float] = None
    kW: Optional[float] = None
    pf: Optional[float] = None
    conn: Optional[str] = None
    kVA: Optional[float] = None
    H: Optional[float] = None
    D: Optional[str] = None
    P_ref1kW: Optional[float] = None
    P_ref2kW: Optional[float] = None
    P_ref3kW: Optional[float] = None
    V_ref1kVLN: Optional[float] = None
    V_ref2kVLN: Optional[float] = None
    V_ref3kVLN: Optional[float] = None
    MaxSlip: Optional[str] = None
    SlipOption: Optional[str] = None
    Yearly: Optional[str] = None
    Daily: Optional[str] = None
    Duty: Optional[int] = None
    Debugtrace: Optional[str] = None
    P_refkW: Optional[float] = None
    Q_refkVAr: Optional[float] = None
    Cluster_num: Optional[str] = None
    V_refkVLN: Optional[float] = None
    ctrl_mode: Optional[str] = None
    QV_flag: Optional[str] = None
    kcd: Optional[str] = None
    kcq: Optional[str] = None
    kqi: Optional[str] = None
    Q_ref1kVAr: Optional[float] = None
    Q_ref2kVAr: Optional[float] = None
    Q_ref3kVAr: Optional[float] = None
    PmaxkW: Optional[float] = None
    PminkW: Optional[float] = None
    PQpriority: Optional[str] = None
    PmppkW: Optional[float] = None
    Pfctr1: Optional[float] = None
    Pfctr2: Optional[float] = None
    Pfctr3: Optional[float] = None
    Pfctr4: Optional[float] = None
    Pfctr5: Optional[float] = None
    Pfctr6: Optional[float] = None
    PbiaskW: Optional[float] = None
    CC_Switch: Optional[str] = None
    kcq_drp2: Optional[str] = None
    Volt_Trhd: Optional[str] = None
    droop: Optional[int] = None
    spectrum: Optional[float] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, Generic5Name):
            self.name = Generic5Name(self.name)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.bus1 is not None and not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.kv is not None and not isinstance(self.kv, float):
            self.kv = float(self.kv)

        if self.kW is not None and not isinstance(self.kW, float):
            self.kW = float(self.kW)

        if self.pf is not None and not isinstance(self.pf, float):
            self.pf = float(self.pf)

        if self.conn is not None and not isinstance(self.conn, str):
            self.conn = str(self.conn)

        if self.kVA is not None and not isinstance(self.kVA, float):
            self.kVA = float(self.kVA)

        if self.H is not None and not isinstance(self.H, float):
            self.H = float(self.H)

        if self.D is not None and not isinstance(self.D, str):
            self.D = str(self.D)

        if self.P_ref1kW is not None and not isinstance(self.P_ref1kW, float):
            self.P_ref1kW = float(self.P_ref1kW)

        if self.P_ref2kW is not None and not isinstance(self.P_ref2kW, float):
            self.P_ref2kW = float(self.P_ref2kW)

        if self.P_ref3kW is not None and not isinstance(self.P_ref3kW, float):
            self.P_ref3kW = float(self.P_ref3kW)

        if self.V_ref1kVLN is not None and not isinstance(self.V_ref1kVLN, float):
            self.V_ref1kVLN = float(self.V_ref1kVLN)

        if self.V_ref2kVLN is not None and not isinstance(self.V_ref2kVLN, float):
            self.V_ref2kVLN = float(self.V_ref2kVLN)

        if self.V_ref3kVLN is not None and not isinstance(self.V_ref3kVLN, float):
            self.V_ref3kVLN = float(self.V_ref3kVLN)

        if self.MaxSlip is not None and not isinstance(self.MaxSlip, str):
            self.MaxSlip = str(self.MaxSlip)

        if self.SlipOption is not None and not isinstance(self.SlipOption, str):
            self.SlipOption = str(self.SlipOption)

        if self.Yearly is not None and not isinstance(self.Yearly, str):
            self.Yearly = str(self.Yearly)

        if self.Daily is not None and not isinstance(self.Daily, str):
            self.Daily = str(self.Daily)

        if self.Duty is not None and not isinstance(self.Duty, int):
            self.Duty = int(self.Duty)

        if self.Debugtrace is not None and not isinstance(self.Debugtrace, str):
            self.Debugtrace = str(self.Debugtrace)

        if self.P_refkW is not None and not isinstance(self.P_refkW, float):
            self.P_refkW = float(self.P_refkW)

        if self.Q_refkVAr is not None and not isinstance(self.Q_refkVAr, float):
            self.Q_refkVAr = float(self.Q_refkVAr)

        if self.Cluster_num is not None and not isinstance(self.Cluster_num, str):
            self.Cluster_num = str(self.Cluster_num)

        if self.V_refkVLN is not None and not isinstance(self.V_refkVLN, float):
            self.V_refkVLN = float(self.V_refkVLN)

        if self.ctrl_mode is not None and not isinstance(self.ctrl_mode, str):
            self.ctrl_mode = str(self.ctrl_mode)

        if self.QV_flag is not None and not isinstance(self.QV_flag, str):
            self.QV_flag = str(self.QV_flag)

        if self.kcd is not None and not isinstance(self.kcd, str):
            self.kcd = str(self.kcd)

        if self.kcq is not None and not isinstance(self.kcq, str):
            self.kcq = str(self.kcq)

        if self.kqi is not None and not isinstance(self.kqi, str):
            self.kqi = str(self.kqi)

        if self.Q_ref1kVAr is not None and not isinstance(self.Q_ref1kVAr, float):
            self.Q_ref1kVAr = float(self.Q_ref1kVAr)

        if self.Q_ref2kVAr is not None and not isinstance(self.Q_ref2kVAr, float):
            self.Q_ref2kVAr = float(self.Q_ref2kVAr)

        if self.Q_ref3kVAr is not None and not isinstance(self.Q_ref3kVAr, float):
            self.Q_ref3kVAr = float(self.Q_ref3kVAr)

        if self.PmaxkW is not None and not isinstance(self.PmaxkW, float):
            self.PmaxkW = float(self.PmaxkW)

        if self.PminkW is not None and not isinstance(self.PminkW, float):
            self.PminkW = float(self.PminkW)

        if self.PQpriority is not None and not isinstance(self.PQpriority, str):
            self.PQpriority = str(self.PQpriority)

        if self.PmppkW is not None and not isinstance(self.PmppkW, float):
            self.PmppkW = float(self.PmppkW)

        if self.Pfctr1 is not None and not isinstance(self.Pfctr1, float):
            self.Pfctr1 = float(self.Pfctr1)

        if self.Pfctr2 is not None and not isinstance(self.Pfctr2, float):
            self.Pfctr2 = float(self.Pfctr2)

        if self.Pfctr3 is not None and not isinstance(self.Pfctr3, float):
            self.Pfctr3 = float(self.Pfctr3)

        if self.Pfctr4 is not None and not isinstance(self.Pfctr4, float):
            self.Pfctr4 = float(self.Pfctr4)

        if self.Pfctr5 is not None and not isinstance(self.Pfctr5, float):
            self.Pfctr5 = float(self.Pfctr5)

        if self.Pfctr6 is not None and not isinstance(self.Pfctr6, float):
            self.Pfctr6 = float(self.Pfctr6)

        if self.PbiaskW is not None and not isinstance(self.PbiaskW, float):
            self.PbiaskW = float(self.PbiaskW)

        if self.CC_Switch is not None and not isinstance(self.CC_Switch, str):
            self.CC_Switch = str(self.CC_Switch)

        if self.kcq_drp2 is not None and not isinstance(self.kcq_drp2, str):
            self.kcq_drp2 = str(self.kcq_drp2)

        if self.Volt_Trhd is not None and not isinstance(self.Volt_Trhd, str):
            self.Volt_Trhd = str(self.Volt_Trhd)

        if self.droop is not None and not isinstance(self.droop, int):
            self.droop = int(self.droop)

        if self.spectrum is not None and not isinstance(self.spectrum, float):
            self.spectrum = float(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Gicline(YAMLRoot):
    """
    A Gicline object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Gicline"]
    class_class_curie: ClassVar[str] = "dss:Gicline"
    class_name: ClassVar[str] = "Gicline"
    class_model_uri: ClassVar[URIRef] = DSS.Gicline

    name: Union[str, GiclineName] = None
    bus1: Optional[str] = None
    bus2: Optional[str] = None
    Volts: Optional[float] = None
    Angle: Optional[float] = None
    frequency: Optional[str] = None
    phases: Optional[int] = None
    R: Optional[float] = None
    X: Optional[float] = None
    C: Optional[str] = None
    EN: Optional[float] = None
    EE: Optional[float] = None
    Lat1: Optional[str] = None
    Lon1: Optional[str] = None
    Lat2: Optional[str] = None
    Lon2: Optional[str] = None
    spectrum: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, GiclineName):
            self.name = GiclineName(self.name)

        if self.bus1 is not None and not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.bus2 is not None and not isinstance(self.bus2, str):
            self.bus2 = str(self.bus2)

        if self.Volts is not None and not isinstance(self.Volts, float):
            self.Volts = float(self.Volts)

        if self.Angle is not None and not isinstance(self.Angle, float):
            self.Angle = float(self.Angle)

        if self.frequency is not None and not isinstance(self.frequency, str):
            self.frequency = str(self.frequency)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.R is not None and not isinstance(self.R, float):
            self.R = float(self.R)

        if self.X is not None and not isinstance(self.X, float):
            self.X = float(self.X)

        if self.C is not None and not isinstance(self.C, str):
            self.C = str(self.C)

        if self.EN is not None and not isinstance(self.EN, float):
            self.EN = float(self.EN)

        if self.EE is not None and not isinstance(self.EE, float):
            self.EE = float(self.EE)

        if self.Lat1 is not None and not isinstance(self.Lat1, str):
            self.Lat1 = str(self.Lat1)

        if self.Lon1 is not None and not isinstance(self.Lon1, str):
            self.Lon1 = str(self.Lon1)

        if self.Lat2 is not None and not isinstance(self.Lat2, str):
            self.Lat2 = str(self.Lat2)

        if self.Lon2 is not None and not isinstance(self.Lon2, str):
            self.Lon2 = str(self.Lon2)

        if self.spectrum is not None and not isinstance(self.spectrum, str):
            self.spectrum = str(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Indmach012(YAMLRoot):
    """
    A Indmach012 object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Indmach012"]
    class_class_curie: ClassVar[str] = "dss:Indmach012"
    class_name: ClassVar[str] = "Indmach012"
    class_model_uri: ClassVar[URIRef] = DSS.Indmach012

    name: Union[str, Indmach012Name] = None
    phases: Optional[int] = None
    bus1: Optional[str] = None
    kv: Optional[float] = None
    kW: Optional[float] = None
    pf: Optional[float] = None
    conn: Optional[str] = None
    kVA: Optional[float] = None
    H: Optional[float] = None
    D: Optional[str] = None
    puRs: Optional[float] = None
    puXs: Optional[float] = None
    puRr: Optional[float] = None
    puXr: Optional[float] = None
    puXm: Optional[float] = None
    Slip: Optional[str] = None
    MaxSlip: Optional[str] = None
    SlipOption: Optional[str] = None
    Yearly: Optional[str] = None
    Daily: Optional[str] = None
    Duty: Optional[int] = None
    Debugtrace: Optional[str] = None
    spectrum: Optional[float] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, Indmach012Name):
            self.name = Indmach012Name(self.name)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.bus1 is not None and not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.kv is not None and not isinstance(self.kv, float):
            self.kv = float(self.kv)

        if self.kW is not None and not isinstance(self.kW, float):
            self.kW = float(self.kW)

        if self.pf is not None and not isinstance(self.pf, float):
            self.pf = float(self.pf)

        if self.conn is not None and not isinstance(self.conn, str):
            self.conn = str(self.conn)

        if self.kVA is not None and not isinstance(self.kVA, float):
            self.kVA = float(self.kVA)

        if self.H is not None and not isinstance(self.H, float):
            self.H = float(self.H)

        if self.D is not None and not isinstance(self.D, str):
            self.D = str(self.D)

        if self.puRs is not None and not isinstance(self.puRs, float):
            self.puRs = float(self.puRs)

        if self.puXs is not None and not isinstance(self.puXs, float):
            self.puXs = float(self.puXs)

        if self.puRr is not None and not isinstance(self.puRr, float):
            self.puRr = float(self.puRr)

        if self.puXr is not None and not isinstance(self.puXr, float):
            self.puXr = float(self.puXr)

        if self.puXm is not None and not isinstance(self.puXm, float):
            self.puXm = float(self.puXm)

        if self.Slip is not None and not isinstance(self.Slip, str):
            self.Slip = str(self.Slip)

        if self.MaxSlip is not None and not isinstance(self.MaxSlip, str):
            self.MaxSlip = str(self.MaxSlip)

        if self.SlipOption is not None and not isinstance(self.SlipOption, str):
            self.SlipOption = str(self.SlipOption)

        if self.Yearly is not None and not isinstance(self.Yearly, str):
            self.Yearly = str(self.Yearly)

        if self.Daily is not None and not isinstance(self.Daily, str):
            self.Daily = str(self.Daily)

        if self.Duty is not None and not isinstance(self.Duty, int):
            self.Duty = int(self.Duty)

        if self.Debugtrace is not None and not isinstance(self.Debugtrace, str):
            self.Debugtrace = str(self.Debugtrace)

        if self.spectrum is not None and not isinstance(self.spectrum, float):
            self.spectrum = float(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Pvsystem(YAMLRoot):
    """
    A Pvsystem object in OpenDSS representing a photovoltaic generator with inverter-based grid connection.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Pvsystem"]
    class_class_curie: ClassVar[str] = "dss:Pvsystem"
    class_name: ClassVar[str] = "Pvsystem"
    class_model_uri: ClassVar[URIRef] = DSS.Pvsystem

    name: Union[str, PvsystemName] = None
    phases: Optional[int] = None
    bus1: Optional[str] = None
    kv: Optional[float] = None
    irradiance: Optional[float] = None
    Pmpp: Optional[float] = None
    pct_Pmpp: Optional[float] = None
    Temperature: Optional[float] = None
    pf: Optional[float] = None
    conn: Optional[str] = None
    kvar: Optional[float] = None
    kVA: Optional[float] = None
    pct_Cutin: Optional[float] = None
    pct_Cutout: Optional[float] = None
    EffCurve: Optional[str] = None
    P_TCurve: Optional[str] = None
    pct_R: Optional[float] = None
    pct_X: Optional[float] = None
    model: Optional[int] = None
    Vminpu: Optional[float] = None
    Vmaxpu: Optional[float] = None
    Balanced: Optional[Union[bool, Bool]] = None
    LimitCurrent: Optional[Union[bool, Bool]] = None
    yearly: Optional[str] = None
    daily: Optional[str] = None
    duty: Optional[int] = None
    Tyearly: Optional[str] = None
    Tdaily: Optional[str] = None
    Tduty: Optional[int] = None
    class_class: Optional[int] = None
    UserModel: Optional[str] = None
    UserData: Optional[str] = None
    debugtrace: Optional[Union[bool, Bool]] = None
    VarFollowInverter: Optional[Union[bool, Bool]] = None
    DutyStart: Optional[str] = None
    WattPriority: Optional[Union[bool, Bool]] = None
    PFPriority: Optional[Union[bool, Bool]] = None
    pct_PminNoVars: Optional[float] = None
    pct_PminkvarMax: Optional[float] = None
    kvarMax: Optional[float] = None
    kvarMaxAbs: Optional[float] = None
    kVDC: Optional[float] = None
    Kp: Optional[str] = None
    PITol: Optional[str] = None
    SafeVoltage: Optional[float] = None
    SafeMode: Optional[str] = None
    DynamicEq: Optional[str] = None
    DynOut: Optional[float] = None
    ControlMode: Optional[str] = None
    AmpLimit: Optional[float] = None
    AmpLimitGain: Optional[float] = None
    spectrum: Optional[float] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, PvsystemName):
            self.name = PvsystemName(self.name)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.bus1 is not None and not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.kv is not None and not isinstance(self.kv, float):
            self.kv = float(self.kv)

        if self.irradiance is not None and not isinstance(self.irradiance, float):
            self.irradiance = float(self.irradiance)

        if self.Pmpp is not None and not isinstance(self.Pmpp, float):
            self.Pmpp = float(self.Pmpp)

        if self.pct_Pmpp is not None and not isinstance(self.pct_Pmpp, float):
            self.pct_Pmpp = float(self.pct_Pmpp)

        if self.Temperature is not None and not isinstance(self.Temperature, float):
            self.Temperature = float(self.Temperature)

        if self.pf is not None and not isinstance(self.pf, float):
            self.pf = float(self.pf)

        if self.conn is not None and not isinstance(self.conn, str):
            self.conn = str(self.conn)

        if self.kvar is not None and not isinstance(self.kvar, float):
            self.kvar = float(self.kvar)

        if self.kVA is not None and not isinstance(self.kVA, float):
            self.kVA = float(self.kVA)

        if self.pct_Cutin is not None and not isinstance(self.pct_Cutin, float):
            self.pct_Cutin = float(self.pct_Cutin)

        if self.pct_Cutout is not None and not isinstance(self.pct_Cutout, float):
            self.pct_Cutout = float(self.pct_Cutout)

        if self.EffCurve is not None and not isinstance(self.EffCurve, str):
            self.EffCurve = str(self.EffCurve)

        if self.P_TCurve is not None and not isinstance(self.P_TCurve, str):
            self.P_TCurve = str(self.P_TCurve)

        if self.pct_R is not None and not isinstance(self.pct_R, float):
            self.pct_R = float(self.pct_R)

        if self.pct_X is not None and not isinstance(self.pct_X, float):
            self.pct_X = float(self.pct_X)

        if self.model is not None and not isinstance(self.model, int):
            self.model = int(self.model)

        if self.Vminpu is not None and not isinstance(self.Vminpu, float):
            self.Vminpu = float(self.Vminpu)

        if self.Vmaxpu is not None and not isinstance(self.Vmaxpu, float):
            self.Vmaxpu = float(self.Vmaxpu)

        if self.Balanced is not None and not isinstance(self.Balanced, Bool):
            self.Balanced = Bool(self.Balanced)

        if self.LimitCurrent is not None and not isinstance(self.LimitCurrent, Bool):
            self.LimitCurrent = Bool(self.LimitCurrent)

        if self.yearly is not None and not isinstance(self.yearly, str):
            self.yearly = str(self.yearly)

        if self.daily is not None and not isinstance(self.daily, str):
            self.daily = str(self.daily)

        if self.duty is not None and not isinstance(self.duty, int):
            self.duty = int(self.duty)

        if self.Tyearly is not None and not isinstance(self.Tyearly, str):
            self.Tyearly = str(self.Tyearly)

        if self.Tdaily is not None and not isinstance(self.Tdaily, str):
            self.Tdaily = str(self.Tdaily)

        if self.Tduty is not None and not isinstance(self.Tduty, int):
            self.Tduty = int(self.Tduty)

        if self.class_class is not None and not isinstance(self.class_class, int):
            self.class_class = int(self.class_class)

        if self.UserModel is not None and not isinstance(self.UserModel, str):
            self.UserModel = str(self.UserModel)

        if self.UserData is not None and not isinstance(self.UserData, str):
            self.UserData = str(self.UserData)

        if self.debugtrace is not None and not isinstance(self.debugtrace, Bool):
            self.debugtrace = Bool(self.debugtrace)

        if self.VarFollowInverter is not None and not isinstance(self.VarFollowInverter, Bool):
            self.VarFollowInverter = Bool(self.VarFollowInverter)

        if self.DutyStart is not None and not isinstance(self.DutyStart, str):
            self.DutyStart = str(self.DutyStart)

        if self.WattPriority is not None and not isinstance(self.WattPriority, Bool):
            self.WattPriority = Bool(self.WattPriority)

        if self.PFPriority is not None and not isinstance(self.PFPriority, Bool):
            self.PFPriority = Bool(self.PFPriority)

        if self.pct_PminNoVars is not None and not isinstance(self.pct_PminNoVars, float):
            self.pct_PminNoVars = float(self.pct_PminNoVars)

        if self.pct_PminkvarMax is not None and not isinstance(self.pct_PminkvarMax, float):
            self.pct_PminkvarMax = float(self.pct_PminkvarMax)

        if self.kvarMax is not None and not isinstance(self.kvarMax, float):
            self.kvarMax = float(self.kvarMax)

        if self.kvarMaxAbs is not None and not isinstance(self.kvarMaxAbs, float):
            self.kvarMaxAbs = float(self.kvarMaxAbs)

        if self.kVDC is not None and not isinstance(self.kVDC, float):
            self.kVDC = float(self.kVDC)

        if self.Kp is not None and not isinstance(self.Kp, str):
            self.Kp = str(self.Kp)

        if self.PITol is not None and not isinstance(self.PITol, str):
            self.PITol = str(self.PITol)

        if self.SafeVoltage is not None and not isinstance(self.SafeVoltage, float):
            self.SafeVoltage = float(self.SafeVoltage)

        if self.SafeMode is not None and not isinstance(self.SafeMode, str):
            self.SafeMode = str(self.SafeMode)

        if self.DynamicEq is not None and not isinstance(self.DynamicEq, str):
            self.DynamicEq = str(self.DynamicEq)

        if self.DynOut is not None and not isinstance(self.DynOut, float):
            self.DynOut = float(self.DynOut)

        if self.ControlMode is not None and not isinstance(self.ControlMode, str):
            self.ControlMode = str(self.ControlMode)

        if self.AmpLimit is not None and not isinstance(self.AmpLimit, float):
            self.AmpLimit = float(self.AmpLimit)

        if self.AmpLimitGain is not None and not isinstance(self.AmpLimitGain, float):
            self.AmpLimitGain = float(self.AmpLimitGain)

        if self.spectrum is not None and not isinstance(self.spectrum, float):
            self.spectrum = float(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Storage(YAMLRoot):
    """
    A Storage object in OpenDSS representing a battery energy storage system with inverter-based grid connection.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Storage"]
    class_class_curie: ClassVar[str] = "dss:Storage"
    class_name: ClassVar[str] = "Storage"
    class_model_uri: ClassVar[URIRef] = DSS.Storage

    name: Union[str, StorageName] = None
    phases: Optional[int] = None
    bus1: Optional[str] = None
    kv: Optional[float] = None
    conn: Optional[str] = None
    kW: Optional[float] = None
    kvar: Optional[float] = None
    pf: Optional[float] = None
    kVA: Optional[float] = None
    pct_Cutin: Optional[float] = None
    pct_Cutout: Optional[float] = None
    EffCurve: Optional[str] = None
    VarFollowInverter: Optional[Union[bool, Bool]] = None
    kvarMax: Optional[float] = None
    kvarMaxAbs: Optional[float] = None
    WattPriority: Optional[Union[bool, Bool]] = None
    PFPriority: Optional[Union[bool, Bool]] = None
    pct_PminNoVars: Optional[float] = None
    pct_PminkvarMax: Optional[float] = None
    kWrated: Optional[float] = None
    pct_kWrated: Optional[float] = None
    kWhrated: Optional[float] = None
    kWhstored: Optional[float] = None
    pct_stored: Optional[float] = None
    pct_reserve: Optional[float] = None
    State: Optional[str] = None
    pct_Discharge: Optional[float] = None
    pct_Charge: Optional[float] = None
    pct_EffCharge: Optional[float] = None
    pct_EffDischarge: Optional[float] = None
    pct_IdlingkW: Optional[float] = None
    pct_Idlingkvar: Optional[float] = None
    pct_R: Optional[float] = None
    pct_X: Optional[float] = None
    model: Optional[int] = None
    Vminpu: Optional[float] = None
    Vmaxpu: Optional[float] = None
    Balanced: Optional[Union[bool, Bool]] = None
    LimitCurrent: Optional[Union[bool, Bool]] = None
    yearly: Optional[str] = None
    daily: Optional[str] = None
    duty: Optional[int] = None
    DispMode: Optional[str] = None
    DischargeTrigger: Optional[str] = None
    ChargeTrigger: Optional[str] = None
    TimeChargeTrig: Optional[str] = None
    class_class: Optional[int] = None
    DynaDLL: Optional[str] = None
    DynaData: Optional[str] = None
    UserModel: Optional[str] = None
    UserData: Optional[str] = None
    debugtrace: Optional[Union[bool, Bool]] = None
    kVDC: Optional[float] = None
    Kp: Optional[str] = None
    PITol: Optional[str] = None
    SafeVoltage: Optional[float] = None
    SafeMode: Optional[str] = None
    DynamicEq: Optional[str] = None
    DynOut: Optional[float] = None
    ControlMode: Optional[str] = None
    AmpLimit: Optional[float] = None
    AmpLimitGain: Optional[float] = None
    spectrum: Optional[float] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, StorageName):
            self.name = StorageName(self.name)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.bus1 is not None and not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.kv is not None and not isinstance(self.kv, float):
            self.kv = float(self.kv)

        if self.conn is not None and not isinstance(self.conn, str):
            self.conn = str(self.conn)

        if self.kW is not None and not isinstance(self.kW, float):
            self.kW = float(self.kW)

        if self.kvar is not None and not isinstance(self.kvar, float):
            self.kvar = float(self.kvar)

        if self.pf is not None and not isinstance(self.pf, float):
            self.pf = float(self.pf)

        if self.kVA is not None and not isinstance(self.kVA, float):
            self.kVA = float(self.kVA)

        if self.pct_Cutin is not None and not isinstance(self.pct_Cutin, float):
            self.pct_Cutin = float(self.pct_Cutin)

        if self.pct_Cutout is not None and not isinstance(self.pct_Cutout, float):
            self.pct_Cutout = float(self.pct_Cutout)

        if self.EffCurve is not None and not isinstance(self.EffCurve, str):
            self.EffCurve = str(self.EffCurve)

        if self.VarFollowInverter is not None and not isinstance(self.VarFollowInverter, Bool):
            self.VarFollowInverter = Bool(self.VarFollowInverter)

        if self.kvarMax is not None and not isinstance(self.kvarMax, float):
            self.kvarMax = float(self.kvarMax)

        if self.kvarMaxAbs is not None and not isinstance(self.kvarMaxAbs, float):
            self.kvarMaxAbs = float(self.kvarMaxAbs)

        if self.WattPriority is not None and not isinstance(self.WattPriority, Bool):
            self.WattPriority = Bool(self.WattPriority)

        if self.PFPriority is not None and not isinstance(self.PFPriority, Bool):
            self.PFPriority = Bool(self.PFPriority)

        if self.pct_PminNoVars is not None and not isinstance(self.pct_PminNoVars, float):
            self.pct_PminNoVars = float(self.pct_PminNoVars)

        if self.pct_PminkvarMax is not None and not isinstance(self.pct_PminkvarMax, float):
            self.pct_PminkvarMax = float(self.pct_PminkvarMax)

        if self.kWrated is not None and not isinstance(self.kWrated, float):
            self.kWrated = float(self.kWrated)

        if self.pct_kWrated is not None and not isinstance(self.pct_kWrated, float):
            self.pct_kWrated = float(self.pct_kWrated)

        if self.kWhrated is not None and not isinstance(self.kWhrated, float):
            self.kWhrated = float(self.kWhrated)

        if self.kWhstored is not None and not isinstance(self.kWhstored, float):
            self.kWhstored = float(self.kWhstored)

        if self.pct_stored is not None and not isinstance(self.pct_stored, float):
            self.pct_stored = float(self.pct_stored)

        if self.pct_reserve is not None and not isinstance(self.pct_reserve, float):
            self.pct_reserve = float(self.pct_reserve)

        if self.State is not None and not isinstance(self.State, str):
            self.State = str(self.State)

        if self.pct_Discharge is not None and not isinstance(self.pct_Discharge, float):
            self.pct_Discharge = float(self.pct_Discharge)

        if self.pct_Charge is not None and not isinstance(self.pct_Charge, float):
            self.pct_Charge = float(self.pct_Charge)

        if self.pct_EffCharge is not None and not isinstance(self.pct_EffCharge, float):
            self.pct_EffCharge = float(self.pct_EffCharge)

        if self.pct_EffDischarge is not None and not isinstance(self.pct_EffDischarge, float):
            self.pct_EffDischarge = float(self.pct_EffDischarge)

        if self.pct_IdlingkW is not None and not isinstance(self.pct_IdlingkW, float):
            self.pct_IdlingkW = float(self.pct_IdlingkW)

        if self.pct_Idlingkvar is not None and not isinstance(self.pct_Idlingkvar, float):
            self.pct_Idlingkvar = float(self.pct_Idlingkvar)

        if self.pct_R is not None and not isinstance(self.pct_R, float):
            self.pct_R = float(self.pct_R)

        if self.pct_X is not None and not isinstance(self.pct_X, float):
            self.pct_X = float(self.pct_X)

        if self.model is not None and not isinstance(self.model, int):
            self.model = int(self.model)

        if self.Vminpu is not None and not isinstance(self.Vminpu, float):
            self.Vminpu = float(self.Vminpu)

        if self.Vmaxpu is not None and not isinstance(self.Vmaxpu, float):
            self.Vmaxpu = float(self.Vmaxpu)

        if self.Balanced is not None and not isinstance(self.Balanced, Bool):
            self.Balanced = Bool(self.Balanced)

        if self.LimitCurrent is not None and not isinstance(self.LimitCurrent, Bool):
            self.LimitCurrent = Bool(self.LimitCurrent)

        if self.yearly is not None and not isinstance(self.yearly, str):
            self.yearly = str(self.yearly)

        if self.daily is not None and not isinstance(self.daily, str):
            self.daily = str(self.daily)

        if self.duty is not None and not isinstance(self.duty, int):
            self.duty = int(self.duty)

        if self.DispMode is not None and not isinstance(self.DispMode, str):
            self.DispMode = str(self.DispMode)

        if self.DischargeTrigger is not None and not isinstance(self.DischargeTrigger, str):
            self.DischargeTrigger = str(self.DischargeTrigger)

        if self.ChargeTrigger is not None and not isinstance(self.ChargeTrigger, str):
            self.ChargeTrigger = str(self.ChargeTrigger)

        if self.TimeChargeTrig is not None and not isinstance(self.TimeChargeTrig, str):
            self.TimeChargeTrig = str(self.TimeChargeTrig)

        if self.class_class is not None and not isinstance(self.class_class, int):
            self.class_class = int(self.class_class)

        if self.DynaDLL is not None and not isinstance(self.DynaDLL, str):
            self.DynaDLL = str(self.DynaDLL)

        if self.DynaData is not None and not isinstance(self.DynaData, str):
            self.DynaData = str(self.DynaData)

        if self.UserModel is not None and not isinstance(self.UserModel, str):
            self.UserModel = str(self.UserModel)

        if self.UserData is not None and not isinstance(self.UserData, str):
            self.UserData = str(self.UserData)

        if self.debugtrace is not None and not isinstance(self.debugtrace, Bool):
            self.debugtrace = Bool(self.debugtrace)

        if self.kVDC is not None and not isinstance(self.kVDC, float):
            self.kVDC = float(self.kVDC)

        if self.Kp is not None and not isinstance(self.Kp, str):
            self.Kp = str(self.Kp)

        if self.PITol is not None and not isinstance(self.PITol, str):
            self.PITol = str(self.PITol)

        if self.SafeVoltage is not None and not isinstance(self.SafeVoltage, float):
            self.SafeVoltage = float(self.SafeVoltage)

        if self.SafeMode is not None and not isinstance(self.SafeMode, str):
            self.SafeMode = str(self.SafeMode)

        if self.DynamicEq is not None and not isinstance(self.DynamicEq, str):
            self.DynamicEq = str(self.DynamicEq)

        if self.DynOut is not None and not isinstance(self.DynOut, float):
            self.DynOut = float(self.DynOut)

        if self.ControlMode is not None and not isinstance(self.ControlMode, str):
            self.ControlMode = str(self.ControlMode)

        if self.AmpLimit is not None and not isinstance(self.AmpLimit, float):
            self.AmpLimit = float(self.AmpLimit)

        if self.AmpLimitGain is not None and not isinstance(self.AmpLimitGain, float):
            self.AmpLimitGain = float(self.AmpLimitGain)

        if self.spectrum is not None and not isinstance(self.spectrum, float):
            self.spectrum = float(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Upfc(YAMLRoot):
    """
    A Upfc object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Upfc"]
    class_class_curie: ClassVar[str] = "dss:Upfc"
    class_name: ClassVar[str] = "Upfc"
    class_model_uri: ClassVar[URIRef] = DSS.Upfc

    name: Union[str, UpfcName] = None
    bus1: Optional[float] = None
    bus2: Optional[float] = None
    refkv: Optional[float] = None
    pf: Optional[float] = None
    frequency: Optional[str] = None
    phases: Optional[int] = None
    Xs: Optional[float] = None
    Tol1: Optional[float] = None
    Mode: Optional[int] = None
    VpqMax: Optional[float] = None
    LossCurve: Optional[float] = None
    VHLimit: Optional[float] = None
    VLLimit: Optional[float] = None
    CLimit: Optional[float] = None
    refkv2: Optional[float] = None
    kvarLimit: Optional[float] = None
    Element: Optional[float] = None
    spectrum: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, UpfcName):
            self.name = UpfcName(self.name)

        if self.bus1 is not None and not isinstance(self.bus1, float):
            self.bus1 = float(self.bus1)

        if self.bus2 is not None and not isinstance(self.bus2, float):
            self.bus2 = float(self.bus2)

        if self.refkv is not None and not isinstance(self.refkv, float):
            self.refkv = float(self.refkv)

        if self.pf is not None and not isinstance(self.pf, float):
            self.pf = float(self.pf)

        if self.frequency is not None and not isinstance(self.frequency, str):
            self.frequency = str(self.frequency)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.Xs is not None and not isinstance(self.Xs, float):
            self.Xs = float(self.Xs)

        if self.Tol1 is not None and not isinstance(self.Tol1, float):
            self.Tol1 = float(self.Tol1)

        if self.Mode is not None and not isinstance(self.Mode, int):
            self.Mode = int(self.Mode)

        if self.VpqMax is not None and not isinstance(self.VpqMax, float):
            self.VpqMax = float(self.VpqMax)

        if self.LossCurve is not None and not isinstance(self.LossCurve, float):
            self.LossCurve = float(self.LossCurve)

        if self.VHLimit is not None and not isinstance(self.VHLimit, float):
            self.VHLimit = float(self.VHLimit)

        if self.VLLimit is not None and not isinstance(self.VLLimit, float):
            self.VLLimit = float(self.VLLimit)

        if self.CLimit is not None and not isinstance(self.CLimit, float):
            self.CLimit = float(self.CLimit)

        if self.refkv2 is not None and not isinstance(self.refkv2, float):
            self.refkv2 = float(self.refkv2)

        if self.kvarLimit is not None and not isinstance(self.kvarLimit, float):
            self.kvarLimit = float(self.kvarLimit)

        if self.Element is not None and not isinstance(self.Element, float):
            self.Element = float(self.Element)

        if self.spectrum is not None and not isinstance(self.spectrum, str):
            self.spectrum = str(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Vccs(YAMLRoot):
    """
    A Vccs object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Vccs"]
    class_class_curie: ClassVar[str] = "dss:Vccs"
    class_name: ClassVar[str] = "Vccs"
    class_model_uri: ClassVar[URIRef] = DSS.Vccs

    name: Union[str, VccsName] = None
    bus1: Optional[str] = None
    phases: Optional[int] = None
    prated: Optional[float] = None
    vrated: Optional[float] = None
    ppct: Optional[float] = None
    bp1: Optional[float] = None
    bp2: Optional[float] = None
    filter: Optional[str] = None
    fsample: Optional[str] = None
    rmsmode: Optional[str] = None
    imaxpu: Optional[float] = None
    vrmstau: Optional[str] = None
    irmstau: Optional[str] = None
    spectrum: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, VccsName):
            self.name = VccsName(self.name)

        if self.bus1 is not None and not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.prated is not None and not isinstance(self.prated, float):
            self.prated = float(self.prated)

        if self.vrated is not None and not isinstance(self.vrated, float):
            self.vrated = float(self.vrated)

        if self.ppct is not None and not isinstance(self.ppct, float):
            self.ppct = float(self.ppct)

        if self.bp1 is not None and not isinstance(self.bp1, float):
            self.bp1 = float(self.bp1)

        if self.bp2 is not None and not isinstance(self.bp2, float):
            self.bp2 = float(self.bp2)

        if self.filter is not None and not isinstance(self.filter, str):
            self.filter = str(self.filter)

        if self.fsample is not None and not isinstance(self.fsample, str):
            self.fsample = str(self.fsample)

        if self.rmsmode is not None and not isinstance(self.rmsmode, str):
            self.rmsmode = str(self.rmsmode)

        if self.imaxpu is not None and not isinstance(self.imaxpu, float):
            self.imaxpu = float(self.imaxpu)

        if self.vrmstau is not None and not isinstance(self.vrmstau, str):
            self.vrmstau = str(self.vrmstau)

        if self.irmstau is not None and not isinstance(self.irmstau, str):
            self.irmstau = str(self.irmstau)

        if self.spectrum is not None and not isinstance(self.spectrum, str):
            self.spectrum = str(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Vsconverter(YAMLRoot):
    """
    A Vsconverter object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Vsconverter"]
    class_class_curie: ClassVar[str] = "dss:Vsconverter"
    class_name: ClassVar[str] = "Vsconverter"
    class_model_uri: ClassVar[URIRef] = DSS.Vsconverter

    name: Union[str, VsconverterName] = None
    phases: Optional[int] = None
    Bus1: Optional[str] = None
    kVac: Optional[float] = None
    kVdc: Optional[float] = None
    kW: Optional[float] = None
    Ndc: Optional[int] = None
    Rac: Optional[float] = None
    Xac: Optional[float] = None
    m0: Optional[str] = None
    d0: Optional[float] = None
    Mmin: Optional[str] = None
    Mmax: Optional[str] = None
    Iacmax: Optional[float] = None
    Idcmax: Optional[float] = None
    Vacref: Optional[float] = None
    Pacref: Optional[float] = None
    Qacref: Optional[float] = None
    Vdcref: Optional[float] = None
    VscMode: Optional[str] = None
    spectrum: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, VsconverterName):
            self.name = VsconverterName(self.name)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.Bus1 is not None and not isinstance(self.Bus1, str):
            self.Bus1 = str(self.Bus1)

        if self.kVac is not None and not isinstance(self.kVac, float):
            self.kVac = float(self.kVac)

        if self.kVdc is not None and not isinstance(self.kVdc, float):
            self.kVdc = float(self.kVdc)

        if self.kW is not None and not isinstance(self.kW, float):
            self.kW = float(self.kW)

        if self.Ndc is not None and not isinstance(self.Ndc, int):
            self.Ndc = int(self.Ndc)

        if self.Rac is not None and not isinstance(self.Rac, float):
            self.Rac = float(self.Rac)

        if self.Xac is not None and not isinstance(self.Xac, float):
            self.Xac = float(self.Xac)

        if self.m0 is not None and not isinstance(self.m0, str):
            self.m0 = str(self.m0)

        if self.d0 is not None and not isinstance(self.d0, float):
            self.d0 = float(self.d0)

        if self.Mmin is not None and not isinstance(self.Mmin, str):
            self.Mmin = str(self.Mmin)

        if self.Mmax is not None and not isinstance(self.Mmax, str):
            self.Mmax = str(self.Mmax)

        if self.Iacmax is not None and not isinstance(self.Iacmax, float):
            self.Iacmax = float(self.Iacmax)

        if self.Idcmax is not None and not isinstance(self.Idcmax, float):
            self.Idcmax = float(self.Idcmax)

        if self.Vacref is not None and not isinstance(self.Vacref, float):
            self.Vacref = float(self.Vacref)

        if self.Pacref is not None and not isinstance(self.Pacref, float):
            self.Pacref = float(self.Pacref)

        if self.Qacref is not None and not isinstance(self.Qacref, float):
            self.Qacref = float(self.Qacref)

        if self.Vdcref is not None and not isinstance(self.Vdcref, float):
            self.Vdcref = float(self.Vdcref)

        if self.VscMode is not None and not isinstance(self.VscMode, str):
            self.VscMode = str(self.VscMode)

        if self.spectrum is not None and not isinstance(self.spectrum, str):
            self.spectrum = str(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Windgen(YAMLRoot):
    """
    A Windgen object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Windgen"]
    class_class_curie: ClassVar[str] = "dss:Windgen"
    class_name: ClassVar[str] = "Windgen"
    class_model_uri: ClassVar[URIRef] = DSS.Windgen

    name: Union[str, WindgenName] = None
    phases: Optional[int] = None
    bus1: Optional[str] = None
    kv: Optional[float] = None
    kW: Optional[float] = None
    PF: Optional[float] = None
    model: Optional[int] = None
    yearly: Optional[int] = None
    daily: Optional[str] = None
    duty: Optional[int] = None
    conn: Optional[str] = None
    kvar: Optional[float] = None
    class_class: Optional[int] = None
    debugtrace: Optional[Union[bool, Bool]] = None
    Vminpu: Optional[float] = None
    Vmaxpu: Optional[float] = None
    kVA: Optional[float] = None
    MVA: Optional[float] = None
    UserModel: Optional[float] = None
    UserData: Optional[str] = None
    DutyStart: Optional[str] = None
    DynamicEq: Optional[str] = None
    DynOut: Optional[float] = None
    Rthev: Optional[str] = None
    Xthev: Optional[str] = None
    Vss: Optional[float] = None
    Pss: Optional[float] = None
    Qss: Optional[float] = None
    vwind: Optional[str] = None
    QMode: Optional[str] = None
    SimMechFlg: Optional[float] = None
    APCFlg: Optional[float] = None
    QFlg: Optional[float] = None
    delt0: Optional[str] = None
    N_WTG: Optional[int] = None
    VV_Curve: Optional[str] = None
    Ag: Optional[str] = None
    Cp: Optional[str] = None
    Lamda: Optional[str] = None
    P: Optional[int] = None
    pd: Optional[str] = None
    PLoss: Optional[float] = None
    Rad: Optional[str] = None
    VCutIn: Optional[str] = None
    VCutOut: Optional[str] = None
    spectrum: Optional[float] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, WindgenName):
            self.name = WindgenName(self.name)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.bus1 is not None and not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.kv is not None and not isinstance(self.kv, float):
            self.kv = float(self.kv)

        if self.kW is not None and not isinstance(self.kW, float):
            self.kW = float(self.kW)

        if self.PF is not None and not isinstance(self.PF, float):
            self.PF = float(self.PF)

        if self.model is not None and not isinstance(self.model, int):
            self.model = int(self.model)

        if self.yearly is not None and not isinstance(self.yearly, int):
            self.yearly = int(self.yearly)

        if self.daily is not None and not isinstance(self.daily, str):
            self.daily = str(self.daily)

        if self.duty is not None and not isinstance(self.duty, int):
            self.duty = int(self.duty)

        if self.conn is not None and not isinstance(self.conn, str):
            self.conn = str(self.conn)

        if self.kvar is not None and not isinstance(self.kvar, float):
            self.kvar = float(self.kvar)

        if self.class_class is not None and not isinstance(self.class_class, int):
            self.class_class = int(self.class_class)

        if self.debugtrace is not None and not isinstance(self.debugtrace, Bool):
            self.debugtrace = Bool(self.debugtrace)

        if self.Vminpu is not None and not isinstance(self.Vminpu, float):
            self.Vminpu = float(self.Vminpu)

        if self.Vmaxpu is not None and not isinstance(self.Vmaxpu, float):
            self.Vmaxpu = float(self.Vmaxpu)

        if self.kVA is not None and not isinstance(self.kVA, float):
            self.kVA = float(self.kVA)

        if self.MVA is not None and not isinstance(self.MVA, float):
            self.MVA = float(self.MVA)

        if self.UserModel is not None and not isinstance(self.UserModel, float):
            self.UserModel = float(self.UserModel)

        if self.UserData is not None and not isinstance(self.UserData, str):
            self.UserData = str(self.UserData)

        if self.DutyStart is not None and not isinstance(self.DutyStart, str):
            self.DutyStart = str(self.DutyStart)

        if self.DynamicEq is not None and not isinstance(self.DynamicEq, str):
            self.DynamicEq = str(self.DynamicEq)

        if self.DynOut is not None and not isinstance(self.DynOut, float):
            self.DynOut = float(self.DynOut)

        if self.Rthev is not None and not isinstance(self.Rthev, str):
            self.Rthev = str(self.Rthev)

        if self.Xthev is not None and not isinstance(self.Xthev, str):
            self.Xthev = str(self.Xthev)

        if self.Vss is not None and not isinstance(self.Vss, float):
            self.Vss = float(self.Vss)

        if self.Pss is not None and not isinstance(self.Pss, float):
            self.Pss = float(self.Pss)

        if self.Qss is not None and not isinstance(self.Qss, float):
            self.Qss = float(self.Qss)

        if self.vwind is not None and not isinstance(self.vwind, str):
            self.vwind = str(self.vwind)

        if self.QMode is not None and not isinstance(self.QMode, str):
            self.QMode = str(self.QMode)

        if self.SimMechFlg is not None and not isinstance(self.SimMechFlg, float):
            self.SimMechFlg = float(self.SimMechFlg)

        if self.APCFlg is not None and not isinstance(self.APCFlg, float):
            self.APCFlg = float(self.APCFlg)

        if self.QFlg is not None and not isinstance(self.QFlg, float):
            self.QFlg = float(self.QFlg)

        if self.delt0 is not None and not isinstance(self.delt0, str):
            self.delt0 = str(self.delt0)

        if self.N_WTG is not None and not isinstance(self.N_WTG, int):
            self.N_WTG = int(self.N_WTG)

        if self.VV_Curve is not None and not isinstance(self.VV_Curve, str):
            self.VV_Curve = str(self.VV_Curve)

        if self.Ag is not None and not isinstance(self.Ag, str):
            self.Ag = str(self.Ag)

        if self.Cp is not None and not isinstance(self.Cp, str):
            self.Cp = str(self.Cp)

        if self.Lamda is not None and not isinstance(self.Lamda, str):
            self.Lamda = str(self.Lamda)

        if self.P is not None and not isinstance(self.P, int):
            self.P = int(self.P)

        if self.pd is not None and not isinstance(self.pd, str):
            self.pd = str(self.pd)

        if self.PLoss is not None and not isinstance(self.PLoss, float):
            self.PLoss = float(self.PLoss)

        if self.Rad is not None and not isinstance(self.Rad, str):
            self.Rad = str(self.Rad)

        if self.VCutIn is not None and not isinstance(self.VCutIn, str):
            self.VCutIn = str(self.VCutIn)

        if self.VCutOut is not None and not isinstance(self.VCutOut, str):
            self.VCutOut = str(self.VCutOut)

        if self.spectrum is not None and not isinstance(self.spectrum, float):
            self.spectrum = float(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Autotrans(YAMLRoot):
    """
    A Autotrans object in OpenDSS representing an auto-transformer where the series and common windings share a
    magnetic core. Winding 1 is the series (high-side) winding; winding 2 is the common winding.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Autotrans"]
    class_class_curie: ClassVar[str] = "dss:Autotrans"
    class_name: ClassVar[str] = "Autotrans"
    class_model_uri: ClassVar[URIRef] = DSS.Autotrans

    name: Union[str, AutotransName] = None
    phases: Optional[int] = None
    windings: Optional[int] = None
    wdg: Optional[int] = None
    bus: Optional[str] = None
    conn: Optional[str] = None
    kV: Optional[float] = None
    kVA: Optional[float] = None
    tap: Optional[str] = None
    pct_R: Optional[float] = None
    Rdcohms: Optional[int] = None
    Core: Optional[str] = None
    buses: Optional[Union[str, list[str]]] = empty_list()
    conns: Optional[Union[str, list[str]]] = empty_list()
    kVs: Optional[Union[float, list[float]]] = empty_list()
    kVAs: Optional[Union[float, list[float]]] = empty_list()
    taps: Optional[str] = None
    XHX: Optional[float] = None
    XHT: Optional[float] = None
    XXT: Optional[float] = None
    XSCarray: Optional[Union[float, list[float]]] = empty_list()
    thermal: Optional[str] = None
    n: Optional[str] = None
    m: Optional[str] = None
    flrise: Optional[str] = None
    hsrise: Optional[str] = None
    pct_loadloss: Optional[float] = None
    pct_noloadloss: Optional[float] = None
    normhkVA: Optional[float] = None
    emerghkVA: Optional[float] = None
    sub: Optional[Union[bool, Bool]] = None
    MaxTap: Optional[str] = None
    MinTap: Optional[str] = None
    NumTaps: Optional[int] = None
    subname: Optional[str] = None
    pct_imag: Optional[float] = None
    ppm_antifloat: Optional[float] = None
    pct_Rs: Optional[Union[float, list[float]]] = empty_list()
    bank: Optional[str] = None
    XfmrCode: Optional[str] = None
    XRConst: Optional[Union[bool, Bool]] = None
    LeadLag: Optional[str] = None
    WdgCurrents: Optional[float] = None
    normamps: Optional[float] = None
    emergamps: Optional[float] = None
    faultrate: Optional[str] = None
    pctperm: Optional[float] = None
    repair: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, AutotransName):
            self.name = AutotransName(self.name)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.windings is not None and not isinstance(self.windings, int):
            self.windings = int(self.windings)

        if self.wdg is not None and not isinstance(self.wdg, int):
            self.wdg = int(self.wdg)

        if self.bus is not None and not isinstance(self.bus, str):
            self.bus = str(self.bus)

        if self.conn is not None and not isinstance(self.conn, str):
            self.conn = str(self.conn)

        if self.kV is not None and not isinstance(self.kV, float):
            self.kV = float(self.kV)

        if self.kVA is not None and not isinstance(self.kVA, float):
            self.kVA = float(self.kVA)

        if self.tap is not None and not isinstance(self.tap, str):
            self.tap = str(self.tap)

        if self.pct_R is not None and not isinstance(self.pct_R, float):
            self.pct_R = float(self.pct_R)

        if self.Rdcohms is not None and not isinstance(self.Rdcohms, int):
            self.Rdcohms = int(self.Rdcohms)

        if self.Core is not None and not isinstance(self.Core, str):
            self.Core = str(self.Core)

        if not isinstance(self.buses, list):
            self.buses = [self.buses] if self.buses is not None else []
        self.buses = [v if isinstance(v, str) else str(v) for v in self.buses]

        if not isinstance(self.conns, list):
            self.conns = [self.conns] if self.conns is not None else []
        self.conns = [v if isinstance(v, str) else str(v) for v in self.conns]

        if not isinstance(self.kVs, list):
            self.kVs = [self.kVs] if self.kVs is not None else []
        self.kVs = [v if isinstance(v, float) else float(v) for v in self.kVs]

        if not isinstance(self.kVAs, list):
            self.kVAs = [self.kVAs] if self.kVAs is not None else []
        self.kVAs = [v if isinstance(v, float) else float(v) for v in self.kVAs]

        if self.taps is not None and not isinstance(self.taps, str):
            self.taps = str(self.taps)

        if self.XHX is not None and not isinstance(self.XHX, float):
            self.XHX = float(self.XHX)

        if self.XHT is not None and not isinstance(self.XHT, float):
            self.XHT = float(self.XHT)

        if self.XXT is not None and not isinstance(self.XXT, float):
            self.XXT = float(self.XXT)

        if not isinstance(self.XSCarray, list):
            self.XSCarray = [self.XSCarray] if self.XSCarray is not None else []
        self.XSCarray = [v if isinstance(v, float) else float(v) for v in self.XSCarray]

        if self.thermal is not None and not isinstance(self.thermal, str):
            self.thermal = str(self.thermal)

        if self.n is not None and not isinstance(self.n, str):
            self.n = str(self.n)

        if self.m is not None and not isinstance(self.m, str):
            self.m = str(self.m)

        if self.flrise is not None and not isinstance(self.flrise, str):
            self.flrise = str(self.flrise)

        if self.hsrise is not None and not isinstance(self.hsrise, str):
            self.hsrise = str(self.hsrise)

        if self.pct_loadloss is not None and not isinstance(self.pct_loadloss, float):
            self.pct_loadloss = float(self.pct_loadloss)

        if self.pct_noloadloss is not None and not isinstance(self.pct_noloadloss, float):
            self.pct_noloadloss = float(self.pct_noloadloss)

        if self.normhkVA is not None and not isinstance(self.normhkVA, float):
            self.normhkVA = float(self.normhkVA)

        if self.emerghkVA is not None and not isinstance(self.emerghkVA, float):
            self.emerghkVA = float(self.emerghkVA)

        if self.sub is not None and not isinstance(self.sub, Bool):
            self.sub = Bool(self.sub)

        if self.MaxTap is not None and not isinstance(self.MaxTap, str):
            self.MaxTap = str(self.MaxTap)

        if self.MinTap is not None and not isinstance(self.MinTap, str):
            self.MinTap = str(self.MinTap)

        if self.NumTaps is not None and not isinstance(self.NumTaps, int):
            self.NumTaps = int(self.NumTaps)

        if self.subname is not None and not isinstance(self.subname, str):
            self.subname = str(self.subname)

        if self.pct_imag is not None and not isinstance(self.pct_imag, float):
            self.pct_imag = float(self.pct_imag)

        if self.ppm_antifloat is not None and not isinstance(self.ppm_antifloat, float):
            self.ppm_antifloat = float(self.ppm_antifloat)

        if not isinstance(self.pct_Rs, list):
            self.pct_Rs = [self.pct_Rs] if self.pct_Rs is not None else []
        self.pct_Rs = [v if isinstance(v, float) else float(v) for v in self.pct_Rs]

        if self.bank is not None and not isinstance(self.bank, str):
            self.bank = str(self.bank)

        if self.XfmrCode is not None and not isinstance(self.XfmrCode, str):
            self.XfmrCode = str(self.XfmrCode)

        if self.XRConst is not None and not isinstance(self.XRConst, Bool):
            self.XRConst = Bool(self.XRConst)

        if self.LeadLag is not None and not isinstance(self.LeadLag, str):
            self.LeadLag = str(self.LeadLag)

        if self.WdgCurrents is not None and not isinstance(self.WdgCurrents, float):
            self.WdgCurrents = float(self.WdgCurrents)

        if self.normamps is not None and not isinstance(self.normamps, float):
            self.normamps = float(self.normamps)

        if self.emergamps is not None and not isinstance(self.emergamps, float):
            self.emergamps = float(self.emergamps)

        if self.faultrate is not None and not isinstance(self.faultrate, str):
            self.faultrate = str(self.faultrate)

        if self.pctperm is not None and not isinstance(self.pctperm, float):
            self.pctperm = float(self.pctperm)

        if self.repair is not None and not isinstance(self.repair, str):
            self.repair = str(self.repair)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Capacitor(YAMLRoot):
    """
    A Capacitor object in OpenDSS representing a shunt or series capacitor bank connected to the distribution system.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Capacitor"]
    class_class_curie: ClassVar[str] = "dss:Capacitor"
    class_name: ClassVar[str] = "Capacitor"
    class_model_uri: ClassVar[URIRef] = DSS.Capacitor

    name: Union[str, CapacitorName] = None
    bus1: Optional[str] = None
    bus2: Optional[str] = None
    phases: Optional[int] = None
    kvar: Optional[Union[float, list[float]]] = empty_list()
    kv: Optional[float] = None
    conn: Optional[Union[str, "ConnectionType"]] = None
    cmatrix: Optional[Union[float, list[float]]] = empty_list()
    cuf: Optional[Union[float, list[float]]] = empty_list()
    R: Optional[Union[float, list[float]]] = empty_list()
    XL: Optional[Union[float, list[float]]] = empty_list()
    Harm: Optional[Union[float, list[float]]] = empty_list()
    Numsteps: Optional[int] = None
    states: Optional[Union[int, list[int]]] = empty_list()
    normamps: Optional[float] = None
    emergamps: Optional[float] = None
    faultrate: Optional[str] = None
    pctperm: Optional[float] = None
    repair: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, CapacitorName):
            self.name = CapacitorName(self.name)

        if self.bus1 is not None and not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.bus2 is not None and not isinstance(self.bus2, str):
            self.bus2 = str(self.bus2)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if not isinstance(self.kvar, list):
            self.kvar = [self.kvar] if self.kvar is not None else []
        self.kvar = [v if isinstance(v, float) else float(v) for v in self.kvar]

        if self.kv is not None and not isinstance(self.kv, float):
            self.kv = float(self.kv)

        if self.conn is not None and not isinstance(self.conn, ConnectionType):
            self.conn = ConnectionType(self.conn)

        if not isinstance(self.cmatrix, list):
            self.cmatrix = [self.cmatrix] if self.cmatrix is not None else []
        self.cmatrix = [v if isinstance(v, float) else float(v) for v in self.cmatrix]

        if not isinstance(self.cuf, list):
            self.cuf = [self.cuf] if self.cuf is not None else []
        self.cuf = [v if isinstance(v, float) else float(v) for v in self.cuf]

        if not isinstance(self.R, list):
            self.R = [self.R] if self.R is not None else []
        self.R = [v if isinstance(v, float) else float(v) for v in self.R]

        if not isinstance(self.XL, list):
            self.XL = [self.XL] if self.XL is not None else []
        self.XL = [v if isinstance(v, float) else float(v) for v in self.XL]

        if not isinstance(self.Harm, list):
            self.Harm = [self.Harm] if self.Harm is not None else []
        self.Harm = [v if isinstance(v, float) else float(v) for v in self.Harm]

        if self.Numsteps is not None and not isinstance(self.Numsteps, int):
            self.Numsteps = int(self.Numsteps)

        if not isinstance(self.states, list):
            self.states = [self.states] if self.states is not None else []
        self.states = [v if isinstance(v, int) else int(v) for v in self.states]

        if self.normamps is not None and not isinstance(self.normamps, float):
            self.normamps = float(self.normamps)

        if self.emergamps is not None and not isinstance(self.emergamps, float):
            self.emergamps = float(self.emergamps)

        if self.faultrate is not None and not isinstance(self.faultrate, str):
            self.faultrate = str(self.faultrate)

        if self.pctperm is not None and not isinstance(self.pctperm, float):
            self.pctperm = float(self.pctperm)

        if self.repair is not None and not isinstance(self.repair, str):
            self.repair = str(self.repair)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Gictransformer(YAMLRoot):
    """
    A Gictransformer object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Gictransformer"]
    class_class_curie: ClassVar[str] = "dss:Gictransformer"
    class_name: ClassVar[str] = "Gictransformer"
    class_model_uri: ClassVar[URIRef] = DSS.Gictransformer

    name: Union[str, GictransformerName] = None
    BusH: Optional[str] = None
    BusNH: Optional[str] = None
    BusX: Optional[str] = None
    BusNX: Optional[str] = None
    phases: Optional[int] = None
    Type: Optional[str] = None
    R1: Optional[float] = None
    R2: Optional[float] = None
    KVLL1: Optional[float] = None
    KVLL2: Optional[float] = None
    MVA: Optional[float] = None
    VarCurve: Optional[float] = None
    pct_R1: Optional[float] = None
    pct_R2: Optional[float] = None
    K: Optional[float] = None
    normamps: Optional[float] = None
    emergamps: Optional[float] = None
    faultrate: Optional[str] = None
    pctperm: Optional[float] = None
    repair: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, GictransformerName):
            self.name = GictransformerName(self.name)

        if self.BusH is not None and not isinstance(self.BusH, str):
            self.BusH = str(self.BusH)

        if self.BusNH is not None and not isinstance(self.BusNH, str):
            self.BusNH = str(self.BusNH)

        if self.BusX is not None and not isinstance(self.BusX, str):
            self.BusX = str(self.BusX)

        if self.BusNX is not None and not isinstance(self.BusNX, str):
            self.BusNX = str(self.BusNX)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.Type is not None and not isinstance(self.Type, str):
            self.Type = str(self.Type)

        if self.R1 is not None and not isinstance(self.R1, float):
            self.R1 = float(self.R1)

        if self.R2 is not None and not isinstance(self.R2, float):
            self.R2 = float(self.R2)

        if self.KVLL1 is not None and not isinstance(self.KVLL1, float):
            self.KVLL1 = float(self.KVLL1)

        if self.KVLL2 is not None and not isinstance(self.KVLL2, float):
            self.KVLL2 = float(self.KVLL2)

        if self.MVA is not None and not isinstance(self.MVA, float):
            self.MVA = float(self.MVA)

        if self.VarCurve is not None and not isinstance(self.VarCurve, float):
            self.VarCurve = float(self.VarCurve)

        if self.pct_R1 is not None and not isinstance(self.pct_R1, float):
            self.pct_R1 = float(self.pct_R1)

        if self.pct_R2 is not None and not isinstance(self.pct_R2, float):
            self.pct_R2 = float(self.pct_R2)

        if self.K is not None and not isinstance(self.K, float):
            self.K = float(self.K)

        if self.normamps is not None and not isinstance(self.normamps, float):
            self.normamps = float(self.normamps)

        if self.emergamps is not None and not isinstance(self.emergamps, float):
            self.emergamps = float(self.emergamps)

        if self.faultrate is not None and not isinstance(self.faultrate, str):
            self.faultrate = str(self.faultrate)

        if self.pctperm is not None and not isinstance(self.pctperm, float):
            self.pctperm = float(self.pctperm)

        if self.repair is not None and not isinstance(self.repair, str):
            self.repair = str(self.repair)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Line(YAMLRoot):
    """
    A Line object in OpenDSS representing a power delivery line connecting two buses in the distribution system. If
    Switch=True the element is treated as a switching device instead.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Line"]
    class_class_curie: ClassVar[str] = "dss:Line"
    class_name: ClassVar[str] = "Line"
    class_model_uri: ClassVar[URIRef] = DSS.Line

    name: Union[str, LineName] = None
    bus1: str = None
    bus2: Optional[str] = None
    linecode: Optional[str] = None
    length: Optional[float] = None
    phases: Optional[int] = None
    r1: Optional[float] = None
    x1: Optional[float] = None
    r0: Optional[float] = None
    x0: Optional[float] = None
    C1: Optional[float] = None
    C0: Optional[float] = None
    rmatrix: Optional[Union[float, list[float]]] = empty_list()
    xmatrix: Optional[Union[float, list[float]]] = empty_list()
    cmatrix: Optional[Union[float, list[float]]] = empty_list()
    Switch: Optional[Union[bool, Bool]] = None
    Rg: Optional[float] = None
    Xg: Optional[float] = None
    rho: Optional[float] = None
    geometry: Optional[str] = None
    units: Optional[Union[str, "LengthUnit"]] = None
    spacing: Optional[str] = None
    cncables: Optional[Union[str, list[str]]] = empty_list()
    tscables: Optional[Union[str, list[str]]] = empty_list()
    wires: Optional[Union[str, list[str]]] = empty_list()
    EarthModel: Optional[Union[str, "EarthModelType"]] = None
    B1: Optional[float] = None
    B0: Optional[float] = None
    Seasons: Optional[int] = None
    Ratings: Optional[Union[float, list[float]]] = empty_list()
    LineType: Optional[Union[str, "LineTypeCode"]] = None
    EpsRmedium: Optional[float] = None
    HeightOffset: Optional[float] = None
    HeightUnit: Optional[Union[str, "LengthUnit"]] = None
    conductors: Optional[Union[str, list[str]]] = empty_list()
    normamps: Optional[float] = None
    emergamps: Optional[float] = None
    faultrate: Optional[float] = None
    pct_perm: Optional[float] = None
    repair: Optional[float] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, LineName):
            self.name = LineName(self.name)

        if self._is_empty(self.bus1):
            self.MissingRequiredField("bus1")
        if not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.bus2 is not None and not isinstance(self.bus2, str):
            self.bus2 = str(self.bus2)

        if self.linecode is not None and not isinstance(self.linecode, str):
            self.linecode = str(self.linecode)

        if self.length is not None and not isinstance(self.length, float):
            self.length = float(self.length)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.r1 is not None and not isinstance(self.r1, float):
            self.r1 = float(self.r1)

        if self.x1 is not None and not isinstance(self.x1, float):
            self.x1 = float(self.x1)

        if self.r0 is not None and not isinstance(self.r0, float):
            self.r0 = float(self.r0)

        if self.x0 is not None and not isinstance(self.x0, float):
            self.x0 = float(self.x0)

        if self.C1 is not None and not isinstance(self.C1, float):
            self.C1 = float(self.C1)

        if self.C0 is not None and not isinstance(self.C0, float):
            self.C0 = float(self.C0)

        if not isinstance(self.rmatrix, list):
            self.rmatrix = [self.rmatrix] if self.rmatrix is not None else []
        self.rmatrix = [v if isinstance(v, float) else float(v) for v in self.rmatrix]

        if not isinstance(self.xmatrix, list):
            self.xmatrix = [self.xmatrix] if self.xmatrix is not None else []
        self.xmatrix = [v if isinstance(v, float) else float(v) for v in self.xmatrix]

        if not isinstance(self.cmatrix, list):
            self.cmatrix = [self.cmatrix] if self.cmatrix is not None else []
        self.cmatrix = [v if isinstance(v, float) else float(v) for v in self.cmatrix]

        if self.Switch is not None and not isinstance(self.Switch, Bool):
            self.Switch = Bool(self.Switch)

        if self.Rg is not None and not isinstance(self.Rg, float):
            self.Rg = float(self.Rg)

        if self.Xg is not None and not isinstance(self.Xg, float):
            self.Xg = float(self.Xg)

        if self.rho is not None and not isinstance(self.rho, float):
            self.rho = float(self.rho)

        if self.geometry is not None and not isinstance(self.geometry, str):
            self.geometry = str(self.geometry)

        if self.units is not None and not isinstance(self.units, LengthUnit):
            self.units = LengthUnit(self.units)

        if self.spacing is not None and not isinstance(self.spacing, str):
            self.spacing = str(self.spacing)

        if not isinstance(self.cncables, list):
            self.cncables = [self.cncables] if self.cncables is not None else []
        self.cncables = [v if isinstance(v, str) else str(v) for v in self.cncables]

        if not isinstance(self.tscables, list):
            self.tscables = [self.tscables] if self.tscables is not None else []
        self.tscables = [v if isinstance(v, str) else str(v) for v in self.tscables]

        if not isinstance(self.wires, list):
            self.wires = [self.wires] if self.wires is not None else []
        self.wires = [v if isinstance(v, str) else str(v) for v in self.wires]

        if self.EarthModel is not None and not isinstance(self.EarthModel, EarthModelType):
            self.EarthModel = EarthModelType(self.EarthModel)

        if self.B1 is not None and not isinstance(self.B1, float):
            self.B1 = float(self.B1)

        if self.B0 is not None and not isinstance(self.B0, float):
            self.B0 = float(self.B0)

        if self.Seasons is not None and not isinstance(self.Seasons, int):
            self.Seasons = int(self.Seasons)

        if not isinstance(self.Ratings, list):
            self.Ratings = [self.Ratings] if self.Ratings is not None else []
        self.Ratings = [v if isinstance(v, float) else float(v) for v in self.Ratings]

        if self.LineType is not None and not isinstance(self.LineType, LineTypeCode):
            self.LineType = LineTypeCode(self.LineType)

        if self.EpsRmedium is not None and not isinstance(self.EpsRmedium, float):
            self.EpsRmedium = float(self.EpsRmedium)

        if self.HeightOffset is not None and not isinstance(self.HeightOffset, float):
            self.HeightOffset = float(self.HeightOffset)

        if self.HeightUnit is not None and not isinstance(self.HeightUnit, LengthUnit):
            self.HeightUnit = LengthUnit(self.HeightUnit)

        if not isinstance(self.conductors, list):
            self.conductors = [self.conductors] if self.conductors is not None else []
        self.conductors = [v if isinstance(v, str) else str(v) for v in self.conductors]

        if self.normamps is not None and not isinstance(self.normamps, float):
            self.normamps = float(self.normamps)

        if self.emergamps is not None and not isinstance(self.emergamps, float):
            self.emergamps = float(self.emergamps)

        if self.faultrate is not None and not isinstance(self.faultrate, float):
            self.faultrate = float(self.faultrate)

        if self.pct_perm is not None and not isinstance(self.pct_perm, float):
            self.pct_perm = float(self.pct_perm)

        if self.repair is not None and not isinstance(self.repair, float):
            self.repair = float(self.repair)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Reactor(YAMLRoot):
    """
    A Reactor object in OpenDSS representing a series or shunt impedance branch. Two-terminal reactors (bus1 + bus2)
    are mapped to CIM SeriesCompensator. A single-terminal (shunt) reactor raises on import.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Reactor"]
    class_class_curie: ClassVar[str] = "dss:Reactor"
    class_name: ClassVar[str] = "Reactor"
    class_model_uri: ClassVar[URIRef] = DSS.Reactor

    name: Union[str, ReactorName] = None
    bus1: Optional[str] = None
    bus2: Optional[str] = None
    phases: Optional[int] = None
    kvar: Optional[float] = None
    kv: Optional[float] = None
    conn: Optional[str] = None
    Rmatrix: Optional[int] = None
    Xmatrix: Optional[int] = None
    Parallel: Optional[Union[bool, Bool]] = None
    R: Optional[float] = None
    X: Optional[float] = None
    Rp: Optional[float] = None
    Z1: Optional[Union[float, list[float]]] = empty_list()
    Z2: Optional[Union[float, list[float]]] = empty_list()
    Z0: Optional[Union[float, list[float]]] = empty_list()
    Z: Optional[Union[float, list[float]]] = empty_list()
    RCurve: Optional[float] = None
    LCurve: Optional[float] = None
    LmH: Optional[float] = None
    normamps: Optional[float] = None
    emergamps: Optional[float] = None
    faultrate: Optional[str] = None
    pctperm: Optional[float] = None
    repair: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, ReactorName):
            self.name = ReactorName(self.name)

        if self.bus1 is not None and not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.bus2 is not None and not isinstance(self.bus2, str):
            self.bus2 = str(self.bus2)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.kvar is not None and not isinstance(self.kvar, float):
            self.kvar = float(self.kvar)

        if self.kv is not None and not isinstance(self.kv, float):
            self.kv = float(self.kv)

        if self.conn is not None and not isinstance(self.conn, str):
            self.conn = str(self.conn)

        if self.Rmatrix is not None and not isinstance(self.Rmatrix, int):
            self.Rmatrix = int(self.Rmatrix)

        if self.Xmatrix is not None and not isinstance(self.Xmatrix, int):
            self.Xmatrix = int(self.Xmatrix)

        if self.Parallel is not None and not isinstance(self.Parallel, Bool):
            self.Parallel = Bool(self.Parallel)

        if self.R is not None and not isinstance(self.R, float):
            self.R = float(self.R)

        if self.X is not None and not isinstance(self.X, float):
            self.X = float(self.X)

        if self.Rp is not None and not isinstance(self.Rp, float):
            self.Rp = float(self.Rp)

        if not isinstance(self.Z1, list):
            self.Z1 = [self.Z1] if self.Z1 is not None else []
        self.Z1 = [v if isinstance(v, float) else float(v) for v in self.Z1]

        if not isinstance(self.Z2, list):
            self.Z2 = [self.Z2] if self.Z2 is not None else []
        self.Z2 = [v if isinstance(v, float) else float(v) for v in self.Z2]

        if not isinstance(self.Z0, list):
            self.Z0 = [self.Z0] if self.Z0 is not None else []
        self.Z0 = [v if isinstance(v, float) else float(v) for v in self.Z0]

        if not isinstance(self.Z, list):
            self.Z = [self.Z] if self.Z is not None else []
        self.Z = [v if isinstance(v, float) else float(v) for v in self.Z]

        if self.RCurve is not None and not isinstance(self.RCurve, float):
            self.RCurve = float(self.RCurve)

        if self.LCurve is not None and not isinstance(self.LCurve, float):
            self.LCurve = float(self.LCurve)

        if self.LmH is not None and not isinstance(self.LmH, float):
            self.LmH = float(self.LmH)

        if self.normamps is not None and not isinstance(self.normamps, float):
            self.normamps = float(self.normamps)

        if self.emergamps is not None and not isinstance(self.emergamps, float):
            self.emergamps = float(self.emergamps)

        if self.faultrate is not None and not isinstance(self.faultrate, str):
            self.faultrate = str(self.faultrate)

        if self.pctperm is not None and not isinstance(self.pctperm, float):
            self.pctperm = float(self.pctperm)

        if self.repair is not None and not isinstance(self.repair, str):
            self.repair = str(self.repair)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Transformer(YAMLRoot):
    """
    A Transformer object in OpenDSS representing a multi-winding transformer connecting two or more buses in the
    distribution system.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Transformer"]
    class_class_curie: ClassVar[str] = "dss:Transformer"
    class_name: ClassVar[str] = "Transformer"
    class_model_uri: ClassVar[URIRef] = DSS.Transformer

    name: Union[str, TransformerName] = None
    phases: Optional[int] = None
    windings: Optional[int] = None
    wdg: Optional[int] = None
    bus: Optional[str] = None
    conn: Optional[Union[str, "ConnectionType"]] = None
    kV: Optional[float] = None
    kVA: Optional[float] = None
    tap: Optional[float] = None
    pct_R: Optional[float] = None
    Rneut: Optional[float] = None
    Xneut: Optional[float] = None
    buses: Optional[Union[str, list[str]]] = empty_list()
    conns: Optional[Union[Union[str, "ConnectionType"], list[Union[str, "ConnectionType"]]]] = empty_list()
    kVs: Optional[Union[float, list[float]]] = empty_list()
    kVAs: Optional[Union[float, list[float]]] = empty_list()
    taps: Optional[Union[float, list[float]]] = empty_list()
    XHL: Optional[float] = None
    XHT: Optional[float] = None
    XLT: Optional[float] = None
    Xscarray: Optional[Union[float, list[float]]] = empty_list()
    thermal: Optional[float] = None
    n: Optional[float] = None
    m: Optional[float] = None
    flrise: Optional[float] = None
    hsrise: Optional[float] = None
    pct_loadloss: Optional[float] = None
    pct_noloadloss: Optional[float] = None
    normhkVA: Optional[float] = None
    emerghkVA: Optional[float] = None
    sub: Optional[Union[bool, Bool]] = None
    MaxTap: Optional[float] = None
    MinTap: Optional[float] = None
    NumTaps: Optional[int] = None
    subname: Optional[str] = None
    pct_imag: Optional[float] = None
    ppm_antifloat: Optional[float] = None
    pct_Rs: Optional[Union[float, list[float]]] = empty_list()
    bank: Optional[str] = None
    XfmrCode: Optional[str] = None
    XRConst: Optional[Union[bool, Bool]] = None
    X12: Optional[float] = None
    X13: Optional[float] = None
    X23: Optional[float] = None
    LeadLag: Optional[Union[str, "LeadLagType"]] = None
    Core: Optional[Union[str, "CoreType"]] = None
    RdcOhms: Optional[Union[float, list[float]]] = empty_list()
    Seasons: Optional[int] = None
    Ratings: Optional[Union[float, list[float]]] = empty_list()
    normamps: Optional[float] = None
    emergamps: Optional[float] = None
    faultrate: Optional[float] = None
    pct_perm: Optional[float] = None
    repair: Optional[float] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, TransformerName):
            self.name = TransformerName(self.name)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.windings is not None and not isinstance(self.windings, int):
            self.windings = int(self.windings)

        if self.wdg is not None and not isinstance(self.wdg, int):
            self.wdg = int(self.wdg)

        if self.bus is not None and not isinstance(self.bus, str):
            self.bus = str(self.bus)

        if self.conn is not None and not isinstance(self.conn, ConnectionType):
            self.conn = ConnectionType(self.conn)

        if self.kV is not None and not isinstance(self.kV, float):
            self.kV = float(self.kV)

        if self.kVA is not None and not isinstance(self.kVA, float):
            self.kVA = float(self.kVA)

        if self.tap is not None and not isinstance(self.tap, float):
            self.tap = float(self.tap)

        if self.pct_R is not None and not isinstance(self.pct_R, float):
            self.pct_R = float(self.pct_R)

        if self.Rneut is not None and not isinstance(self.Rneut, float):
            self.Rneut = float(self.Rneut)

        if self.Xneut is not None and not isinstance(self.Xneut, float):
            self.Xneut = float(self.Xneut)

        if not isinstance(self.buses, list):
            self.buses = [self.buses] if self.buses is not None else []
        self.buses = [v if isinstance(v, str) else str(v) for v in self.buses]

        if not isinstance(self.conns, list):
            self.conns = [self.conns] if self.conns is not None else []
        self.conns = [v if isinstance(v, ConnectionType) else ConnectionType(v) for v in self.conns]

        if not isinstance(self.kVs, list):
            self.kVs = [self.kVs] if self.kVs is not None else []
        self.kVs = [v if isinstance(v, float) else float(v) for v in self.kVs]

        if not isinstance(self.kVAs, list):
            self.kVAs = [self.kVAs] if self.kVAs is not None else []
        self.kVAs = [v if isinstance(v, float) else float(v) for v in self.kVAs]

        if not isinstance(self.taps, list):
            self.taps = [self.taps] if self.taps is not None else []
        self.taps = [v if isinstance(v, float) else float(v) for v in self.taps]

        if self.XHL is not None and not isinstance(self.XHL, float):
            self.XHL = float(self.XHL)

        if self.XHT is not None and not isinstance(self.XHT, float):
            self.XHT = float(self.XHT)

        if self.XLT is not None and not isinstance(self.XLT, float):
            self.XLT = float(self.XLT)

        if not isinstance(self.Xscarray, list):
            self.Xscarray = [self.Xscarray] if self.Xscarray is not None else []
        self.Xscarray = [v if isinstance(v, float) else float(v) for v in self.Xscarray]

        if self.thermal is not None and not isinstance(self.thermal, float):
            self.thermal = float(self.thermal)

        if self.n is not None and not isinstance(self.n, float):
            self.n = float(self.n)

        if self.m is not None and not isinstance(self.m, float):
            self.m = float(self.m)

        if self.flrise is not None and not isinstance(self.flrise, float):
            self.flrise = float(self.flrise)

        if self.hsrise is not None and not isinstance(self.hsrise, float):
            self.hsrise = float(self.hsrise)

        if self.pct_loadloss is not None and not isinstance(self.pct_loadloss, float):
            self.pct_loadloss = float(self.pct_loadloss)

        if self.pct_noloadloss is not None and not isinstance(self.pct_noloadloss, float):
            self.pct_noloadloss = float(self.pct_noloadloss)

        if self.normhkVA is not None and not isinstance(self.normhkVA, float):
            self.normhkVA = float(self.normhkVA)

        if self.emerghkVA is not None and not isinstance(self.emerghkVA, float):
            self.emerghkVA = float(self.emerghkVA)

        if self.sub is not None and not isinstance(self.sub, Bool):
            self.sub = Bool(self.sub)

        if self.MaxTap is not None and not isinstance(self.MaxTap, float):
            self.MaxTap = float(self.MaxTap)

        if self.MinTap is not None and not isinstance(self.MinTap, float):
            self.MinTap = float(self.MinTap)

        if self.NumTaps is not None and not isinstance(self.NumTaps, int):
            self.NumTaps = int(self.NumTaps)

        if self.subname is not None and not isinstance(self.subname, str):
            self.subname = str(self.subname)

        if self.pct_imag is not None and not isinstance(self.pct_imag, float):
            self.pct_imag = float(self.pct_imag)

        if self.ppm_antifloat is not None and not isinstance(self.ppm_antifloat, float):
            self.ppm_antifloat = float(self.ppm_antifloat)

        if not isinstance(self.pct_Rs, list):
            self.pct_Rs = [self.pct_Rs] if self.pct_Rs is not None else []
        self.pct_Rs = [v if isinstance(v, float) else float(v) for v in self.pct_Rs]

        if self.bank is not None and not isinstance(self.bank, str):
            self.bank = str(self.bank)

        if self.XfmrCode is not None and not isinstance(self.XfmrCode, str):
            self.XfmrCode = str(self.XfmrCode)

        if self.XRConst is not None and not isinstance(self.XRConst, Bool):
            self.XRConst = Bool(self.XRConst)

        if self.X12 is not None and not isinstance(self.X12, float):
            self.X12 = float(self.X12)

        if self.X13 is not None and not isinstance(self.X13, float):
            self.X13 = float(self.X13)

        if self.X23 is not None and not isinstance(self.X23, float):
            self.X23 = float(self.X23)

        if self.LeadLag is not None and not isinstance(self.LeadLag, LeadLagType):
            self.LeadLag = LeadLagType(self.LeadLag)

        if self.Core is not None and not isinstance(self.Core, CoreType):
            self.Core = CoreType(self.Core)

        if not isinstance(self.RdcOhms, list):
            self.RdcOhms = [self.RdcOhms] if self.RdcOhms is not None else []
        self.RdcOhms = [v if isinstance(v, float) else float(v) for v in self.RdcOhms]

        if self.Seasons is not None and not isinstance(self.Seasons, int):
            self.Seasons = int(self.Seasons)

        if not isinstance(self.Ratings, list):
            self.Ratings = [self.Ratings] if self.Ratings is not None else []
        self.Ratings = [v if isinstance(v, float) else float(v) for v in self.Ratings]

        if self.normamps is not None and not isinstance(self.normamps, float):
            self.normamps = float(self.normamps)

        if self.emergamps is not None and not isinstance(self.emergamps, float):
            self.emergamps = float(self.emergamps)

        if self.faultrate is not None and not isinstance(self.faultrate, float):
            self.faultrate = float(self.faultrate)

        if self.pct_perm is not None and not isinstance(self.pct_perm, float):
            self.pct_perm = float(self.pct_perm)

        if self.repair is not None and not isinstance(self.repair, float):
            self.repair = float(self.repair)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Capcontrol(YAMLRoot):
    """
    A Capcontrol object in OpenDSS representing a capacitor bank control that monitors a line or transformer and
    switches the capacitor ON or OFF.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Capcontrol"]
    class_class_curie: ClassVar[str] = "dss:Capcontrol"
    class_name: ClassVar[str] = "Capcontrol"
    class_model_uri: ClassVar[URIRef] = DSS.Capcontrol

    name: Union[str, CapcontrolName] = None
    element: Optional[str] = None
    terminal: Optional[int] = None
    capacitor: Optional[str] = None
    type: Optional[str] = None
    PTratio: Optional[float] = None
    CTratio: Optional[float] = None
    ONsetting: Optional[float] = None
    OFFsetting: Optional[float] = None
    Delay: Optional[float] = None
    VoltOverride: Optional[Union[bool, Bool]] = None
    Vmax: Optional[float] = None
    Vmin: Optional[float] = None
    DelayOFF: Optional[float] = None
    DeadTime: Optional[float] = None
    CTPhase: Optional[int] = None
    PTPhase: Optional[int] = None
    VBus: Optional[float] = None
    EventLog: Optional[str] = None
    UserModel: Optional[str] = None
    UserData: Optional[str] = None
    pctMinkvar: Optional[float] = None
    Reset: Optional[Union[bool, Bool]] = None
    ControlSignal: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, CapcontrolName):
            self.name = CapcontrolName(self.name)

        if self.element is not None and not isinstance(self.element, str):
            self.element = str(self.element)

        if self.terminal is not None and not isinstance(self.terminal, int):
            self.terminal = int(self.terminal)

        if self.capacitor is not None and not isinstance(self.capacitor, str):
            self.capacitor = str(self.capacitor)

        if self.type is not None and not isinstance(self.type, str):
            self.type = str(self.type)

        if self.PTratio is not None and not isinstance(self.PTratio, float):
            self.PTratio = float(self.PTratio)

        if self.CTratio is not None and not isinstance(self.CTratio, float):
            self.CTratio = float(self.CTratio)

        if self.ONsetting is not None and not isinstance(self.ONsetting, float):
            self.ONsetting = float(self.ONsetting)

        if self.OFFsetting is not None and not isinstance(self.OFFsetting, float):
            self.OFFsetting = float(self.OFFsetting)

        if self.Delay is not None and not isinstance(self.Delay, float):
            self.Delay = float(self.Delay)

        if self.VoltOverride is not None and not isinstance(self.VoltOverride, Bool):
            self.VoltOverride = Bool(self.VoltOverride)

        if self.Vmax is not None and not isinstance(self.Vmax, float):
            self.Vmax = float(self.Vmax)

        if self.Vmin is not None and not isinstance(self.Vmin, float):
            self.Vmin = float(self.Vmin)

        if self.DelayOFF is not None and not isinstance(self.DelayOFF, float):
            self.DelayOFF = float(self.DelayOFF)

        if self.DeadTime is not None and not isinstance(self.DeadTime, float):
            self.DeadTime = float(self.DeadTime)

        if self.CTPhase is not None and not isinstance(self.CTPhase, int):
            self.CTPhase = int(self.CTPhase)

        if self.PTPhase is not None and not isinstance(self.PTPhase, int):
            self.PTPhase = int(self.PTPhase)

        if self.VBus is not None and not isinstance(self.VBus, float):
            self.VBus = float(self.VBus)

        if self.EventLog is not None and not isinstance(self.EventLog, str):
            self.EventLog = str(self.EventLog)

        if self.UserModel is not None and not isinstance(self.UserModel, str):
            self.UserModel = str(self.UserModel)

        if self.UserData is not None and not isinstance(self.UserData, str):
            self.UserData = str(self.UserData)

        if self.pctMinkvar is not None and not isinstance(self.pctMinkvar, float):
            self.pctMinkvar = float(self.pctMinkvar)

        if self.Reset is not None and not isinstance(self.Reset, Bool):
            self.Reset = Bool(self.Reset)

        if self.ControlSignal is not None and not isinstance(self.ControlSignal, str):
            self.ControlSignal = str(self.ControlSignal)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Espvlcontrol(YAMLRoot):
    """
    A Espvlcontrol object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Espvlcontrol"]
    class_class_curie: ClassVar[str] = "dss:Espvlcontrol"
    class_name: ClassVar[str] = "Espvlcontrol"
    class_model_uri: ClassVar[URIRef] = DSS.Espvlcontrol

    name: Union[str, EspvlcontrolName] = None
    Element: Optional[str] = None
    Terminal: Optional[int] = None
    Type: Optional[str] = None
    kWBand: Optional[float] = None
    kvarlimit: Optional[float] = None
    LocalControlList: Optional[Union[str, list[str]]] = empty_list()
    LocalControlWeights: Optional[Union[float, list[float]]] = empty_list()
    PVSystemList: Optional[Union[str, list[str]]] = empty_list()
    PVSystemWeights: Optional[Union[float, list[float]]] = empty_list()
    StorageList: Optional[Union[str, list[str]]] = empty_list()
    StorageWeights: Optional[Union[float, list[float]]] = empty_list()
    Forecast: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, EspvlcontrolName):
            self.name = EspvlcontrolName(self.name)

        if self.Element is not None and not isinstance(self.Element, str):
            self.Element = str(self.Element)

        if self.Terminal is not None and not isinstance(self.Terminal, int):
            self.Terminal = int(self.Terminal)

        if self.Type is not None and not isinstance(self.Type, str):
            self.Type = str(self.Type)

        if self.kWBand is not None and not isinstance(self.kWBand, float):
            self.kWBand = float(self.kWBand)

        if self.kvarlimit is not None and not isinstance(self.kvarlimit, float):
            self.kvarlimit = float(self.kvarlimit)

        if not isinstance(self.LocalControlList, list):
            self.LocalControlList = [self.LocalControlList] if self.LocalControlList is not None else []
        self.LocalControlList = [v if isinstance(v, str) else str(v) for v in self.LocalControlList]

        if not isinstance(self.LocalControlWeights, list):
            self.LocalControlWeights = [self.LocalControlWeights] if self.LocalControlWeights is not None else []
        self.LocalControlWeights = [v if isinstance(v, float) else float(v) for v in self.LocalControlWeights]

        if not isinstance(self.PVSystemList, list):
            self.PVSystemList = [self.PVSystemList] if self.PVSystemList is not None else []
        self.PVSystemList = [v if isinstance(v, str) else str(v) for v in self.PVSystemList]

        if not isinstance(self.PVSystemWeights, list):
            self.PVSystemWeights = [self.PVSystemWeights] if self.PVSystemWeights is not None else []
        self.PVSystemWeights = [v if isinstance(v, float) else float(v) for v in self.PVSystemWeights]

        if not isinstance(self.StorageList, list):
            self.StorageList = [self.StorageList] if self.StorageList is not None else []
        self.StorageList = [v if isinstance(v, str) else str(v) for v in self.StorageList]

        if not isinstance(self.StorageWeights, list):
            self.StorageWeights = [self.StorageWeights] if self.StorageWeights is not None else []
        self.StorageWeights = [v if isinstance(v, float) else float(v) for v in self.StorageWeights]

        if self.Forecast is not None and not isinstance(self.Forecast, str):
            self.Forecast = str(self.Forecast)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Expcontrol(YAMLRoot):
    """
    A Expcontrol object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Expcontrol"]
    class_class_curie: ClassVar[str] = "dss:Expcontrol"
    class_name: ClassVar[str] = "Expcontrol"
    class_model_uri: ClassVar[URIRef] = DSS.Expcontrol

    name: Union[str, ExpcontrolName] = None
    PVSystemList: Optional[Union[str, list[str]]] = empty_list()
    Vreg: Optional[float] = None
    Slope: Optional[float] = None
    VregTau: Optional[float] = None
    Qbias: Optional[float] = None
    VregMin: Optional[str] = None
    VregMax: Optional[str] = None
    QmaxLead: Optional[float] = None
    QmaxLag: Optional[float] = None
    EventLog: Optional[str] = None
    DeltaQ_factor: Optional[int] = None
    PreferQ: Optional[float] = None
    Tresponse: Optional[float] = None
    DERList: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, ExpcontrolName):
            self.name = ExpcontrolName(self.name)

        if not isinstance(self.PVSystemList, list):
            self.PVSystemList = [self.PVSystemList] if self.PVSystemList is not None else []
        self.PVSystemList = [v if isinstance(v, str) else str(v) for v in self.PVSystemList]

        if self.Vreg is not None and not isinstance(self.Vreg, float):
            self.Vreg = float(self.Vreg)

        if self.Slope is not None and not isinstance(self.Slope, float):
            self.Slope = float(self.Slope)

        if self.VregTau is not None and not isinstance(self.VregTau, float):
            self.VregTau = float(self.VregTau)

        if self.Qbias is not None and not isinstance(self.Qbias, float):
            self.Qbias = float(self.Qbias)

        if self.VregMin is not None and not isinstance(self.VregMin, str):
            self.VregMin = str(self.VregMin)

        if self.VregMax is not None and not isinstance(self.VregMax, str):
            self.VregMax = str(self.VregMax)

        if self.QmaxLead is not None and not isinstance(self.QmaxLead, float):
            self.QmaxLead = float(self.QmaxLead)

        if self.QmaxLag is not None and not isinstance(self.QmaxLag, float):
            self.QmaxLag = float(self.QmaxLag)

        if self.EventLog is not None and not isinstance(self.EventLog, str):
            self.EventLog = str(self.EventLog)

        if self.DeltaQ_factor is not None and not isinstance(self.DeltaQ_factor, int):
            self.DeltaQ_factor = int(self.DeltaQ_factor)

        if self.PreferQ is not None and not isinstance(self.PreferQ, float):
            self.PreferQ = float(self.PreferQ)

        if self.Tresponse is not None and not isinstance(self.Tresponse, float):
            self.Tresponse = float(self.Tresponse)

        if self.DERList is not None and not isinstance(self.DERList, str):
            self.DERList = str(self.DERList)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Fuse(YAMLRoot):
    """
    A Fuse object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Fuse"]
    class_class_curie: ClassVar[str] = "dss:Fuse"
    class_name: ClassVar[str] = "Fuse"
    class_model_uri: ClassVar[URIRef] = DSS.Fuse

    name: Union[str, FuseName] = None
    MonitoredObj: Optional[str] = None
    MonitoredTerm: Optional[int] = None
    SwitchedObj: Optional[str] = None
    SwitchedTerm: Optional[int] = None
    FuseCurve: Optional[float] = None
    RatedCurrent: Optional[float] = None
    Delay: Optional[str] = None
    Action: Optional[str] = None
    Normal: Optional[Union[str, list[str]]] = empty_list()
    State: Optional[Union[str, list[str]]] = empty_list()
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, FuseName):
            self.name = FuseName(self.name)

        if self.MonitoredObj is not None and not isinstance(self.MonitoredObj, str):
            self.MonitoredObj = str(self.MonitoredObj)

        if self.MonitoredTerm is not None and not isinstance(self.MonitoredTerm, int):
            self.MonitoredTerm = int(self.MonitoredTerm)

        if self.SwitchedObj is not None and not isinstance(self.SwitchedObj, str):
            self.SwitchedObj = str(self.SwitchedObj)

        if self.SwitchedTerm is not None and not isinstance(self.SwitchedTerm, int):
            self.SwitchedTerm = int(self.SwitchedTerm)

        if self.FuseCurve is not None and not isinstance(self.FuseCurve, float):
            self.FuseCurve = float(self.FuseCurve)

        if self.RatedCurrent is not None and not isinstance(self.RatedCurrent, float):
            self.RatedCurrent = float(self.RatedCurrent)

        if self.Delay is not None and not isinstance(self.Delay, str):
            self.Delay = str(self.Delay)

        if self.Action is not None and not isinstance(self.Action, str):
            self.Action = str(self.Action)

        if not isinstance(self.Normal, list):
            self.Normal = [self.Normal] if self.Normal is not None else []
        self.Normal = [v if isinstance(v, str) else str(v) for v in self.Normal]

        if not isinstance(self.State, list):
            self.State = [self.State] if self.State is not None else []
        self.State = [v if isinstance(v, str) else str(v) for v in self.State]

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Gendispatcher(YAMLRoot):
    """
    A Gendispatcher object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Gendispatcher"]
    class_class_curie: ClassVar[str] = "dss:Gendispatcher"
    class_name: ClassVar[str] = "Gendispatcher"
    class_model_uri: ClassVar[URIRef] = DSS.Gendispatcher

    name: Union[str, GendispatcherName] = None
    Element: Optional[str] = None
    Terminal: Optional[int] = None
    kWLimit: Optional[float] = None
    kWBand: Optional[float] = None
    kvarlimit: Optional[float] = None
    GenList: Optional[Union[str, list[str]]] = empty_list()
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, GendispatcherName):
            self.name = GendispatcherName(self.name)

        if self.Element is not None and not isinstance(self.Element, str):
            self.Element = str(self.Element)

        if self.Terminal is not None and not isinstance(self.Terminal, int):
            self.Terminal = int(self.Terminal)

        if self.kWLimit is not None and not isinstance(self.kWLimit, float):
            self.kWLimit = float(self.kWLimit)

        if self.kWBand is not None and not isinstance(self.kWBand, float):
            self.kWBand = float(self.kWBand)

        if self.kvarlimit is not None and not isinstance(self.kvarlimit, float):
            self.kvarlimit = float(self.kvarlimit)

        if not isinstance(self.GenList, list):
            self.GenList = [self.GenList] if self.GenList is not None else []
        self.GenList = [v if isinstance(v, str) else str(v) for v in self.GenList]

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Invcontrol(YAMLRoot):
    """
    A Invcontrol object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Invcontrol"]
    class_class_curie: ClassVar[str] = "dss:Invcontrol"
    class_name: ClassVar[str] = "Invcontrol"
    class_model_uri: ClassVar[URIRef] = DSS.Invcontrol

    name: Union[str, InvcontrolName] = None
    DERList: Optional[Union[str, list[str]]] = empty_list()
    Mode: Optional[str] = None
    CombiMode: Optional[str] = None
    vvc_curve1: Optional[int] = None
    hysteresis_offset: Optional[float] = None
    voltage_curvex_ref: Optional[int] = None
    avgwindowlen: Optional[int] = None
    voltwatt_curve: Optional[int] = None
    DbVMin: Optional[float] = None
    DbVMax: Optional[float] = None
    ArGraLowV: Optional[float] = None
    ArGraHiV: Optional[float] = None
    DynReacavgwindowlen: Optional[int] = None
    deltaQ_Factor: Optional[int] = None
    VoltageChangeTolerance: Optional[float] = None
    VarChangeTolerance: Optional[float] = None
    VoltwattYAxis: Optional[float] = None
    RateofChangeMode: Optional[float] = None
    LPFTau: Optional[str] = None
    RiseFallLimit: Optional[float] = None
    deltaP_Factor: Optional[int] = None
    EventLog: Optional[str] = None
    RefReactivePower: Optional[float] = None
    ActivePChangeTolerance: Optional[float] = None
    monVoltageCalc: Optional[int] = None
    monBus: Optional[float] = None
    MonBusesVbase: Optional[Union[float, list[float]]] = empty_list()
    voltwattCH_curve: Optional[int] = None
    wattpf_curve: Optional[float] = None
    wattvar_curve: Optional[float] = None
    VV_RefReactivePower: Optional[float] = None
    PVSystemList: Optional[str] = None
    Vsetpoint: Optional[float] = None
    ControlModel: Optional[int] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, InvcontrolName):
            self.name = InvcontrolName(self.name)

        if not isinstance(self.DERList, list):
            self.DERList = [self.DERList] if self.DERList is not None else []
        self.DERList = [v if isinstance(v, str) else str(v) for v in self.DERList]

        if self.Mode is not None and not isinstance(self.Mode, str):
            self.Mode = str(self.Mode)

        if self.CombiMode is not None and not isinstance(self.CombiMode, str):
            self.CombiMode = str(self.CombiMode)

        if self.vvc_curve1 is not None and not isinstance(self.vvc_curve1, int):
            self.vvc_curve1 = int(self.vvc_curve1)

        if self.hysteresis_offset is not None and not isinstance(self.hysteresis_offset, float):
            self.hysteresis_offset = float(self.hysteresis_offset)

        if self.voltage_curvex_ref is not None and not isinstance(self.voltage_curvex_ref, int):
            self.voltage_curvex_ref = int(self.voltage_curvex_ref)

        if self.avgwindowlen is not None and not isinstance(self.avgwindowlen, int):
            self.avgwindowlen = int(self.avgwindowlen)

        if self.voltwatt_curve is not None and not isinstance(self.voltwatt_curve, int):
            self.voltwatt_curve = int(self.voltwatt_curve)

        if self.DbVMin is not None and not isinstance(self.DbVMin, float):
            self.DbVMin = float(self.DbVMin)

        if self.DbVMax is not None and not isinstance(self.DbVMax, float):
            self.DbVMax = float(self.DbVMax)

        if self.ArGraLowV is not None and not isinstance(self.ArGraLowV, float):
            self.ArGraLowV = float(self.ArGraLowV)

        if self.ArGraHiV is not None and not isinstance(self.ArGraHiV, float):
            self.ArGraHiV = float(self.ArGraHiV)

        if self.DynReacavgwindowlen is not None and not isinstance(self.DynReacavgwindowlen, int):
            self.DynReacavgwindowlen = int(self.DynReacavgwindowlen)

        if self.deltaQ_Factor is not None and not isinstance(self.deltaQ_Factor, int):
            self.deltaQ_Factor = int(self.deltaQ_Factor)

        if self.VoltageChangeTolerance is not None and not isinstance(self.VoltageChangeTolerance, float):
            self.VoltageChangeTolerance = float(self.VoltageChangeTolerance)

        if self.VarChangeTolerance is not None and not isinstance(self.VarChangeTolerance, float):
            self.VarChangeTolerance = float(self.VarChangeTolerance)

        if self.VoltwattYAxis is not None and not isinstance(self.VoltwattYAxis, float):
            self.VoltwattYAxis = float(self.VoltwattYAxis)

        if self.RateofChangeMode is not None and not isinstance(self.RateofChangeMode, float):
            self.RateofChangeMode = float(self.RateofChangeMode)

        if self.LPFTau is not None and not isinstance(self.LPFTau, str):
            self.LPFTau = str(self.LPFTau)

        if self.RiseFallLimit is not None and not isinstance(self.RiseFallLimit, float):
            self.RiseFallLimit = float(self.RiseFallLimit)

        if self.deltaP_Factor is not None and not isinstance(self.deltaP_Factor, int):
            self.deltaP_Factor = int(self.deltaP_Factor)

        if self.EventLog is not None and not isinstance(self.EventLog, str):
            self.EventLog = str(self.EventLog)

        if self.RefReactivePower is not None and not isinstance(self.RefReactivePower, float):
            self.RefReactivePower = float(self.RefReactivePower)

        if self.ActivePChangeTolerance is not None and not isinstance(self.ActivePChangeTolerance, float):
            self.ActivePChangeTolerance = float(self.ActivePChangeTolerance)

        if self.monVoltageCalc is not None and not isinstance(self.monVoltageCalc, int):
            self.monVoltageCalc = int(self.monVoltageCalc)

        if self.monBus is not None and not isinstance(self.monBus, float):
            self.monBus = float(self.monBus)

        if not isinstance(self.MonBusesVbase, list):
            self.MonBusesVbase = [self.MonBusesVbase] if self.MonBusesVbase is not None else []
        self.MonBusesVbase = [v if isinstance(v, float) else float(v) for v in self.MonBusesVbase]

        if self.voltwattCH_curve is not None and not isinstance(self.voltwattCH_curve, int):
            self.voltwattCH_curve = int(self.voltwattCH_curve)

        if self.wattpf_curve is not None and not isinstance(self.wattpf_curve, float):
            self.wattpf_curve = float(self.wattpf_curve)

        if self.wattvar_curve is not None and not isinstance(self.wattvar_curve, float):
            self.wattvar_curve = float(self.wattvar_curve)

        if self.VV_RefReactivePower is not None and not isinstance(self.VV_RefReactivePower, float):
            self.VV_RefReactivePower = float(self.VV_RefReactivePower)

        if self.PVSystemList is not None and not isinstance(self.PVSystemList, str):
            self.PVSystemList = str(self.PVSystemList)

        if self.Vsetpoint is not None and not isinstance(self.Vsetpoint, float):
            self.Vsetpoint = float(self.Vsetpoint)

        if self.ControlModel is not None and not isinstance(self.ControlModel, int):
            self.ControlModel = int(self.ControlModel)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Pycontrol(YAMLRoot):
    """
    A Pycontrol object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Pycontrol"]
    class_class_curie: ClassVar[str] = "dss:Pycontrol"
    class_name: ClassVar[str] = "Pycontrol"
    class_model_uri: ClassVar[URIRef] = DSS.Pycontrol

    name: Union[str, PycontrolName] = None
    pyScript: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, PycontrolName):
            self.name = PycontrolName(self.name)

        if self.pyScript is not None and not isinstance(self.pyScript, str):
            self.pyScript = str(self.pyScript)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Recloser(YAMLRoot):
    """
    A Recloser object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Recloser"]
    class_class_curie: ClassVar[str] = "dss:Recloser"
    class_name: ClassVar[str] = "Recloser"
    class_model_uri: ClassVar[URIRef] = DSS.Recloser

    name: Union[str, RecloserName] = None
    MonitoredObj: Optional[str] = None
    MonitoredTerm: Optional[int] = None
    SwitchedObj: Optional[str] = None
    SwitchedTerm: Optional[int] = None
    NumFast: Optional[int] = None
    PhaseFast: Optional[float] = None
    PhaseDelayed: Optional[float] = None
    GroundFast: Optional[float] = None
    GroundDelayed: Optional[float] = None
    PhaseTrip: Optional[str] = None
    GroundTrip: Optional[str] = None
    PhaseInst: Optional[str] = None
    GroundInst: Optional[str] = None
    Reset: Optional[str] = None
    Shots: Optional[int] = None
    RecloseIntervals: Optional[Union[float, list[float]]] = empty_list()
    Delay: Optional[str] = None
    Action: Optional[str] = None
    TDPhFast: Optional[str] = None
    TDGrFast: Optional[str] = None
    TDPhDelayed: Optional[str] = None
    TDGrDelayed: Optional[str] = None
    Normal: Optional[str] = None
    State: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, RecloserName):
            self.name = RecloserName(self.name)

        if self.MonitoredObj is not None and not isinstance(self.MonitoredObj, str):
            self.MonitoredObj = str(self.MonitoredObj)

        if self.MonitoredTerm is not None and not isinstance(self.MonitoredTerm, int):
            self.MonitoredTerm = int(self.MonitoredTerm)

        if self.SwitchedObj is not None and not isinstance(self.SwitchedObj, str):
            self.SwitchedObj = str(self.SwitchedObj)

        if self.SwitchedTerm is not None and not isinstance(self.SwitchedTerm, int):
            self.SwitchedTerm = int(self.SwitchedTerm)

        if self.NumFast is not None and not isinstance(self.NumFast, int):
            self.NumFast = int(self.NumFast)

        if self.PhaseFast is not None and not isinstance(self.PhaseFast, float):
            self.PhaseFast = float(self.PhaseFast)

        if self.PhaseDelayed is not None and not isinstance(self.PhaseDelayed, float):
            self.PhaseDelayed = float(self.PhaseDelayed)

        if self.GroundFast is not None and not isinstance(self.GroundFast, float):
            self.GroundFast = float(self.GroundFast)

        if self.GroundDelayed is not None and not isinstance(self.GroundDelayed, float):
            self.GroundDelayed = float(self.GroundDelayed)

        if self.PhaseTrip is not None and not isinstance(self.PhaseTrip, str):
            self.PhaseTrip = str(self.PhaseTrip)

        if self.GroundTrip is not None and not isinstance(self.GroundTrip, str):
            self.GroundTrip = str(self.GroundTrip)

        if self.PhaseInst is not None and not isinstance(self.PhaseInst, str):
            self.PhaseInst = str(self.PhaseInst)

        if self.GroundInst is not None and not isinstance(self.GroundInst, str):
            self.GroundInst = str(self.GroundInst)

        if self.Reset is not None and not isinstance(self.Reset, str):
            self.Reset = str(self.Reset)

        if self.Shots is not None and not isinstance(self.Shots, int):
            self.Shots = int(self.Shots)

        if not isinstance(self.RecloseIntervals, list):
            self.RecloseIntervals = [self.RecloseIntervals] if self.RecloseIntervals is not None else []
        self.RecloseIntervals = [v if isinstance(v, float) else float(v) for v in self.RecloseIntervals]

        if self.Delay is not None and not isinstance(self.Delay, str):
            self.Delay = str(self.Delay)

        if self.Action is not None and not isinstance(self.Action, str):
            self.Action = str(self.Action)

        if self.TDPhFast is not None and not isinstance(self.TDPhFast, str):
            self.TDPhFast = str(self.TDPhFast)

        if self.TDGrFast is not None and not isinstance(self.TDGrFast, str):
            self.TDGrFast = str(self.TDGrFast)

        if self.TDPhDelayed is not None and not isinstance(self.TDPhDelayed, str):
            self.TDPhDelayed = str(self.TDPhDelayed)

        if self.TDGrDelayed is not None and not isinstance(self.TDGrDelayed, str):
            self.TDGrDelayed = str(self.TDGrDelayed)

        if self.Normal is not None and not isinstance(self.Normal, str):
            self.Normal = str(self.Normal)

        if self.State is not None and not isinstance(self.State, str):
            self.State = str(self.State)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Regcontrol(YAMLRoot):
    """
    A Regcontrol object in OpenDSS representing a voltage regulator control that monitors a transformer winding and
    adjusts its tap to regulate voltage.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Regcontrol"]
    class_class_curie: ClassVar[str] = "dss:Regcontrol"
    class_name: ClassVar[str] = "Regcontrol"
    class_model_uri: ClassVar[URIRef] = DSS.Regcontrol

    name: Union[str, RegcontrolName] = None
    transformer: Optional[str] = None
    winding: Optional[int] = None
    vreg: Optional[float] = None
    band: Optional[float] = None
    ptratio: Optional[float] = None
    CTprim: Optional[float] = None
    R: Optional[float] = None
    X: Optional[float] = None
    bus: Optional[str] = None
    delay: Optional[float] = None
    reversible: Optional[Union[bool, Bool]] = None
    revvreg: Optional[float] = None
    revband: Optional[float] = None
    revR: Optional[float] = None
    revX: Optional[float] = None
    tapdelay: Optional[float] = None
    debugtrace: Optional[Union[bool, Bool]] = None
    maxtapchange: Optional[float] = None
    inversetime: Optional[Union[bool, Bool]] = None
    tapwinding: Optional[str] = None
    vlimit: Optional[float] = None
    PTphase: Optional[int] = None
    revThreshold: Optional[float] = None
    revDelay: Optional[float] = None
    revNeutral: Optional[Union[bool, Bool]] = None
    EventLog: Optional[str] = None
    RemotePTRatio: Optional[float] = None
    TapNum: Optional[int] = None
    Reset: Optional[Union[bool, Bool]] = None
    LDC_Z: Optional[float] = None
    rev_Z: Optional[float] = None
    Cogen: Optional[Union[bool, Bool]] = None
    idle: Optional[Union[bool, Bool]] = None
    idleReverse: Optional[Union[bool, Bool]] = None
    idleForward: Optional[Union[bool, Bool]] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, RegcontrolName):
            self.name = RegcontrolName(self.name)

        if self.transformer is not None and not isinstance(self.transformer, str):
            self.transformer = str(self.transformer)

        if self.winding is not None and not isinstance(self.winding, int):
            self.winding = int(self.winding)

        if self.vreg is not None and not isinstance(self.vreg, float):
            self.vreg = float(self.vreg)

        if self.band is not None and not isinstance(self.band, float):
            self.band = float(self.band)

        if self.ptratio is not None and not isinstance(self.ptratio, float):
            self.ptratio = float(self.ptratio)

        if self.CTprim is not None and not isinstance(self.CTprim, float):
            self.CTprim = float(self.CTprim)

        if self.R is not None and not isinstance(self.R, float):
            self.R = float(self.R)

        if self.X is not None and not isinstance(self.X, float):
            self.X = float(self.X)

        if self.bus is not None and not isinstance(self.bus, str):
            self.bus = str(self.bus)

        if self.delay is not None and not isinstance(self.delay, float):
            self.delay = float(self.delay)

        if self.reversible is not None and not isinstance(self.reversible, Bool):
            self.reversible = Bool(self.reversible)

        if self.revvreg is not None and not isinstance(self.revvreg, float):
            self.revvreg = float(self.revvreg)

        if self.revband is not None and not isinstance(self.revband, float):
            self.revband = float(self.revband)

        if self.revR is not None and not isinstance(self.revR, float):
            self.revR = float(self.revR)

        if self.revX is not None and not isinstance(self.revX, float):
            self.revX = float(self.revX)

        if self.tapdelay is not None and not isinstance(self.tapdelay, float):
            self.tapdelay = float(self.tapdelay)

        if self.debugtrace is not None and not isinstance(self.debugtrace, Bool):
            self.debugtrace = Bool(self.debugtrace)

        if self.maxtapchange is not None and not isinstance(self.maxtapchange, float):
            self.maxtapchange = float(self.maxtapchange)

        if self.inversetime is not None and not isinstance(self.inversetime, Bool):
            self.inversetime = Bool(self.inversetime)

        if self.tapwinding is not None and not isinstance(self.tapwinding, str):
            self.tapwinding = str(self.tapwinding)

        if self.vlimit is not None and not isinstance(self.vlimit, float):
            self.vlimit = float(self.vlimit)

        if self.PTphase is not None and not isinstance(self.PTphase, int):
            self.PTphase = int(self.PTphase)

        if self.revThreshold is not None and not isinstance(self.revThreshold, float):
            self.revThreshold = float(self.revThreshold)

        if self.revDelay is not None and not isinstance(self.revDelay, float):
            self.revDelay = float(self.revDelay)

        if self.revNeutral is not None and not isinstance(self.revNeutral, Bool):
            self.revNeutral = Bool(self.revNeutral)

        if self.EventLog is not None and not isinstance(self.EventLog, str):
            self.EventLog = str(self.EventLog)

        if self.RemotePTRatio is not None and not isinstance(self.RemotePTRatio, float):
            self.RemotePTRatio = float(self.RemotePTRatio)

        if self.TapNum is not None and not isinstance(self.TapNum, int):
            self.TapNum = int(self.TapNum)

        if self.Reset is not None and not isinstance(self.Reset, Bool):
            self.Reset = Bool(self.Reset)

        if self.LDC_Z is not None and not isinstance(self.LDC_Z, float):
            self.LDC_Z = float(self.LDC_Z)

        if self.rev_Z is not None and not isinstance(self.rev_Z, float):
            self.rev_Z = float(self.rev_Z)

        if self.Cogen is not None and not isinstance(self.Cogen, Bool):
            self.Cogen = Bool(self.Cogen)

        if self.idle is not None and not isinstance(self.idle, Bool):
            self.idle = Bool(self.idle)

        if self.idleReverse is not None and not isinstance(self.idleReverse, Bool):
            self.idleReverse = Bool(self.idleReverse)

        if self.idleForward is not None and not isinstance(self.idleForward, Bool):
            self.idleForward = Bool(self.idleForward)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Relay(YAMLRoot):
    """
    A Relay object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Relay"]
    class_class_curie: ClassVar[str] = "dss:Relay"
    class_name: ClassVar[str] = "Relay"
    class_model_uri: ClassVar[URIRef] = DSS.Relay

    name: Union[str, RelayName] = None
    MonitoredObj: Optional[str] = None
    MonitoredTerm: Optional[int] = None
    SwitchedObj: Optional[str] = None
    SwitchedTerm: Optional[int] = None
    type: Optional[str] = None
    Phasecurve: Optional[float] = None
    Groundcurve: Optional[float] = None
    PhaseTrip: Optional[str] = None
    GroundTrip: Optional[str] = None
    TDPhase: Optional[str] = None
    TDGround: Optional[str] = None
    PhaseInst: Optional[float] = None
    GroundInst: Optional[str] = None
    Reset: Optional[str] = None
    Shots: Optional[int] = None
    RecloseIntervals: Optional[Union[float, list[float]]] = empty_list()
    Delay: Optional[float] = None
    Overvoltcurve: Optional[float] = None
    Undervoltcurve: Optional[float] = None
    kvbase: Optional[int] = None
    pct_47_pickup: Optional[float] = None
    neg_seq_46_base_amps: Optional[float] = None
    pct_46_pickup: Optional[float] = None
    neg_seq_46_isqt: Optional[float] = None
    Variable: Optional[str] = None
    overtrip: Optional[str] = None
    undertrip: Optional[str] = None
    Breakertime: Optional[float] = None
    action: Optional[str] = None
    Z1mag: Optional[float] = None
    Z1ang: Optional[float] = None
    Z0mag: Optional[float] = None
    Z0ang: Optional[float] = None
    Mphase: Optional[str] = None
    Mground: Optional[str] = None
    EventLog: Optional[str] = None
    DebugTrace: Optional[str] = None
    DistReverse: Optional[str] = None
    Normal: Optional[str] = None
    State: Optional[str] = None
    DOC_TiltAngleLow: Optional[float] = None
    DOC_TiltAngleHigh: Optional[float] = None
    DOC_TripSettingLow: Optional[float] = None
    DOC_TripSettingHigh: Optional[float] = None
    DOC_TripSettingMag: Optional[float] = None
    DOC_DelayInner: Optional[str] = None
    DOC_PhaseCurveInner: Optional[float] = None
    DOC_PhaseTripInner: Optional[str] = None
    DOC_TDPhaseInner: Optional[str] = None
    DOC_P1Blocking: Optional[float] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, RelayName):
            self.name = RelayName(self.name)

        if self.MonitoredObj is not None and not isinstance(self.MonitoredObj, str):
            self.MonitoredObj = str(self.MonitoredObj)

        if self.MonitoredTerm is not None and not isinstance(self.MonitoredTerm, int):
            self.MonitoredTerm = int(self.MonitoredTerm)

        if self.SwitchedObj is not None and not isinstance(self.SwitchedObj, str):
            self.SwitchedObj = str(self.SwitchedObj)

        if self.SwitchedTerm is not None and not isinstance(self.SwitchedTerm, int):
            self.SwitchedTerm = int(self.SwitchedTerm)

        if self.type is not None and not isinstance(self.type, str):
            self.type = str(self.type)

        if self.Phasecurve is not None and not isinstance(self.Phasecurve, float):
            self.Phasecurve = float(self.Phasecurve)

        if self.Groundcurve is not None and not isinstance(self.Groundcurve, float):
            self.Groundcurve = float(self.Groundcurve)

        if self.PhaseTrip is not None and not isinstance(self.PhaseTrip, str):
            self.PhaseTrip = str(self.PhaseTrip)

        if self.GroundTrip is not None and not isinstance(self.GroundTrip, str):
            self.GroundTrip = str(self.GroundTrip)

        if self.TDPhase is not None and not isinstance(self.TDPhase, str):
            self.TDPhase = str(self.TDPhase)

        if self.TDGround is not None and not isinstance(self.TDGround, str):
            self.TDGround = str(self.TDGround)

        if self.PhaseInst is not None and not isinstance(self.PhaseInst, float):
            self.PhaseInst = float(self.PhaseInst)

        if self.GroundInst is not None and not isinstance(self.GroundInst, str):
            self.GroundInst = str(self.GroundInst)

        if self.Reset is not None and not isinstance(self.Reset, str):
            self.Reset = str(self.Reset)

        if self.Shots is not None and not isinstance(self.Shots, int):
            self.Shots = int(self.Shots)

        if not isinstance(self.RecloseIntervals, list):
            self.RecloseIntervals = [self.RecloseIntervals] if self.RecloseIntervals is not None else []
        self.RecloseIntervals = [v if isinstance(v, float) else float(v) for v in self.RecloseIntervals]

        if self.Delay is not None and not isinstance(self.Delay, float):
            self.Delay = float(self.Delay)

        if self.Overvoltcurve is not None and not isinstance(self.Overvoltcurve, float):
            self.Overvoltcurve = float(self.Overvoltcurve)

        if self.Undervoltcurve is not None and not isinstance(self.Undervoltcurve, float):
            self.Undervoltcurve = float(self.Undervoltcurve)

        if self.kvbase is not None and not isinstance(self.kvbase, int):
            self.kvbase = int(self.kvbase)

        if self.pct_47_pickup is not None and not isinstance(self.pct_47_pickup, float):
            self.pct_47_pickup = float(self.pct_47_pickup)

        if self.neg_seq_46_base_amps is not None and not isinstance(self.neg_seq_46_base_amps, float):
            self.neg_seq_46_base_amps = float(self.neg_seq_46_base_amps)

        if self.pct_46_pickup is not None and not isinstance(self.pct_46_pickup, float):
            self.pct_46_pickup = float(self.pct_46_pickup)

        if self.neg_seq_46_isqt is not None and not isinstance(self.neg_seq_46_isqt, float):
            self.neg_seq_46_isqt = float(self.neg_seq_46_isqt)

        if self.Variable is not None and not isinstance(self.Variable, str):
            self.Variable = str(self.Variable)

        if self.overtrip is not None and not isinstance(self.overtrip, str):
            self.overtrip = str(self.overtrip)

        if self.undertrip is not None and not isinstance(self.undertrip, str):
            self.undertrip = str(self.undertrip)

        if self.Breakertime is not None and not isinstance(self.Breakertime, float):
            self.Breakertime = float(self.Breakertime)

        if self.action is not None and not isinstance(self.action, str):
            self.action = str(self.action)

        if self.Z1mag is not None and not isinstance(self.Z1mag, float):
            self.Z1mag = float(self.Z1mag)

        if self.Z1ang is not None and not isinstance(self.Z1ang, float):
            self.Z1ang = float(self.Z1ang)

        if self.Z0mag is not None and not isinstance(self.Z0mag, float):
            self.Z0mag = float(self.Z0mag)

        if self.Z0ang is not None and not isinstance(self.Z0ang, float):
            self.Z0ang = float(self.Z0ang)

        if self.Mphase is not None and not isinstance(self.Mphase, str):
            self.Mphase = str(self.Mphase)

        if self.Mground is not None and not isinstance(self.Mground, str):
            self.Mground = str(self.Mground)

        if self.EventLog is not None and not isinstance(self.EventLog, str):
            self.EventLog = str(self.EventLog)

        if self.DebugTrace is not None and not isinstance(self.DebugTrace, str):
            self.DebugTrace = str(self.DebugTrace)

        if self.DistReverse is not None and not isinstance(self.DistReverse, str):
            self.DistReverse = str(self.DistReverse)

        if self.Normal is not None and not isinstance(self.Normal, str):
            self.Normal = str(self.Normal)

        if self.State is not None and not isinstance(self.State, str):
            self.State = str(self.State)

        if self.DOC_TiltAngleLow is not None and not isinstance(self.DOC_TiltAngleLow, float):
            self.DOC_TiltAngleLow = float(self.DOC_TiltAngleLow)

        if self.DOC_TiltAngleHigh is not None and not isinstance(self.DOC_TiltAngleHigh, float):
            self.DOC_TiltAngleHigh = float(self.DOC_TiltAngleHigh)

        if self.DOC_TripSettingLow is not None and not isinstance(self.DOC_TripSettingLow, float):
            self.DOC_TripSettingLow = float(self.DOC_TripSettingLow)

        if self.DOC_TripSettingHigh is not None and not isinstance(self.DOC_TripSettingHigh, float):
            self.DOC_TripSettingHigh = float(self.DOC_TripSettingHigh)

        if self.DOC_TripSettingMag is not None and not isinstance(self.DOC_TripSettingMag, float):
            self.DOC_TripSettingMag = float(self.DOC_TripSettingMag)

        if self.DOC_DelayInner is not None and not isinstance(self.DOC_DelayInner, str):
            self.DOC_DelayInner = str(self.DOC_DelayInner)

        if self.DOC_PhaseCurveInner is not None and not isinstance(self.DOC_PhaseCurveInner, float):
            self.DOC_PhaseCurveInner = float(self.DOC_PhaseCurveInner)

        if self.DOC_PhaseTripInner is not None and not isinstance(self.DOC_PhaseTripInner, str):
            self.DOC_PhaseTripInner = str(self.DOC_PhaseTripInner)

        if self.DOC_TDPhaseInner is not None and not isinstance(self.DOC_TDPhaseInner, str):
            self.DOC_TDPhaseInner = str(self.DOC_TDPhaseInner)

        if self.DOC_P1Blocking is not None and not isinstance(self.DOC_P1Blocking, float):
            self.DOC_P1Blocking = float(self.DOC_P1Blocking)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Storagecontroller(YAMLRoot):
    """
    A Storagecontroller object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Storagecontroller"]
    class_class_curie: ClassVar[str] = "dss:Storagecontroller"
    class_name: ClassVar[str] = "Storagecontroller"
    class_model_uri: ClassVar[URIRef] = DSS.Storagecontroller

    name: Union[str, StoragecontrollerName] = None
    Element: Optional[str] = None
    Terminal: Optional[int] = None
    MonPhase: Optional[int] = None
    kWTarget: Optional[float] = None
    kWTargetLow: Optional[float] = None
    pct_kWBand: Optional[float] = None
    kWBand: Optional[float] = None
    pct_kWBandLow: Optional[float] = None
    kWBandLow: Optional[float] = None
    ElementList: Optional[Union[str, list[str]]] = empty_list()
    Weights: Optional[Union[float, list[float]]] = empty_list()
    ModeDischarge: Optional[float] = None
    ModeCharge: Optional[float] = None
    TimeDischargeTrigger: Optional[float] = None
    TimeChargeTrigger: Optional[str] = None
    pct_RatekW: Optional[float] = None
    pct_RateCharge: Optional[float] = None
    pct_Reserve: Optional[str] = None
    kWhTotal: Optional[float] = None
    kWTotal: Optional[float] = None
    kWhActual: Optional[float] = None
    kWActual: Optional[float] = None
    kWneed: Optional[float] = None
    Yearly: Optional[str] = None
    Daily: Optional[str] = None
    Duty: Optional[str] = None
    EventLog: Optional[Union[bool, Bool]] = None
    InhibitTime: Optional[int] = None
    Tup: Optional[str] = None
    TFlat: Optional[str] = None
    Tdn: Optional[str] = None
    kWThreshold: Optional[float] = None
    DispFactor: Optional[float] = None
    ResetLevel: Optional[str] = None
    Seasons: Optional[int] = None
    SeasonTargets: Optional[Union[float, list[float]]] = empty_list()
    SeasonTargetsLow: Optional[Union[float, list[float]]] = empty_list()
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, StoragecontrollerName):
            self.name = StoragecontrollerName(self.name)

        if self.Element is not None and not isinstance(self.Element, str):
            self.Element = str(self.Element)

        if self.Terminal is not None and not isinstance(self.Terminal, int):
            self.Terminal = int(self.Terminal)

        if self.MonPhase is not None and not isinstance(self.MonPhase, int):
            self.MonPhase = int(self.MonPhase)

        if self.kWTarget is not None and not isinstance(self.kWTarget, float):
            self.kWTarget = float(self.kWTarget)

        if self.kWTargetLow is not None and not isinstance(self.kWTargetLow, float):
            self.kWTargetLow = float(self.kWTargetLow)

        if self.pct_kWBand is not None and not isinstance(self.pct_kWBand, float):
            self.pct_kWBand = float(self.pct_kWBand)

        if self.kWBand is not None and not isinstance(self.kWBand, float):
            self.kWBand = float(self.kWBand)

        if self.pct_kWBandLow is not None and not isinstance(self.pct_kWBandLow, float):
            self.pct_kWBandLow = float(self.pct_kWBandLow)

        if self.kWBandLow is not None and not isinstance(self.kWBandLow, float):
            self.kWBandLow = float(self.kWBandLow)

        if not isinstance(self.ElementList, list):
            self.ElementList = [self.ElementList] if self.ElementList is not None else []
        self.ElementList = [v if isinstance(v, str) else str(v) for v in self.ElementList]

        if not isinstance(self.Weights, list):
            self.Weights = [self.Weights] if self.Weights is not None else []
        self.Weights = [v if isinstance(v, float) else float(v) for v in self.Weights]

        if self.ModeDischarge is not None and not isinstance(self.ModeDischarge, float):
            self.ModeDischarge = float(self.ModeDischarge)

        if self.ModeCharge is not None and not isinstance(self.ModeCharge, float):
            self.ModeCharge = float(self.ModeCharge)

        if self.TimeDischargeTrigger is not None and not isinstance(self.TimeDischargeTrigger, float):
            self.TimeDischargeTrigger = float(self.TimeDischargeTrigger)

        if self.TimeChargeTrigger is not None and not isinstance(self.TimeChargeTrigger, str):
            self.TimeChargeTrigger = str(self.TimeChargeTrigger)

        if self.pct_RatekW is not None and not isinstance(self.pct_RatekW, float):
            self.pct_RatekW = float(self.pct_RatekW)

        if self.pct_RateCharge is not None and not isinstance(self.pct_RateCharge, float):
            self.pct_RateCharge = float(self.pct_RateCharge)

        if self.pct_Reserve is not None and not isinstance(self.pct_Reserve, str):
            self.pct_Reserve = str(self.pct_Reserve)

        if self.kWhTotal is not None and not isinstance(self.kWhTotal, float):
            self.kWhTotal = float(self.kWhTotal)

        if self.kWTotal is not None and not isinstance(self.kWTotal, float):
            self.kWTotal = float(self.kWTotal)

        if self.kWhActual is not None and not isinstance(self.kWhActual, float):
            self.kWhActual = float(self.kWhActual)

        if self.kWActual is not None and not isinstance(self.kWActual, float):
            self.kWActual = float(self.kWActual)

        if self.kWneed is not None and not isinstance(self.kWneed, float):
            self.kWneed = float(self.kWneed)

        if self.Yearly is not None and not isinstance(self.Yearly, str):
            self.Yearly = str(self.Yearly)

        if self.Daily is not None and not isinstance(self.Daily, str):
            self.Daily = str(self.Daily)

        if self.Duty is not None and not isinstance(self.Duty, str):
            self.Duty = str(self.Duty)

        if self.EventLog is not None and not isinstance(self.EventLog, Bool):
            self.EventLog = Bool(self.EventLog)

        if self.InhibitTime is not None and not isinstance(self.InhibitTime, int):
            self.InhibitTime = int(self.InhibitTime)

        if self.Tup is not None and not isinstance(self.Tup, str):
            self.Tup = str(self.Tup)

        if self.TFlat is not None and not isinstance(self.TFlat, str):
            self.TFlat = str(self.TFlat)

        if self.Tdn is not None and not isinstance(self.Tdn, str):
            self.Tdn = str(self.Tdn)

        if self.kWThreshold is not None and not isinstance(self.kWThreshold, float):
            self.kWThreshold = float(self.kWThreshold)

        if self.DispFactor is not None and not isinstance(self.DispFactor, float):
            self.DispFactor = float(self.DispFactor)

        if self.ResetLevel is not None and not isinstance(self.ResetLevel, str):
            self.ResetLevel = str(self.ResetLevel)

        if self.Seasons is not None and not isinstance(self.Seasons, int):
            self.Seasons = int(self.Seasons)

        if not isinstance(self.SeasonTargets, list):
            self.SeasonTargets = [self.SeasonTargets] if self.SeasonTargets is not None else []
        self.SeasonTargets = [v if isinstance(v, float) else float(v) for v in self.SeasonTargets]

        if not isinstance(self.SeasonTargetsLow, list):
            self.SeasonTargetsLow = [self.SeasonTargetsLow] if self.SeasonTargetsLow is not None else []
        self.SeasonTargetsLow = [v if isinstance(v, float) else float(v) for v in self.SeasonTargetsLow]

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Swtcontrol(YAMLRoot):
    """
    A Swtcontrol object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Swtcontrol"]
    class_class_curie: ClassVar[str] = "dss:Swtcontrol"
    class_name: ClassVar[str] = "Swtcontrol"
    class_model_uri: ClassVar[URIRef] = DSS.Swtcontrol

    name: Union[str, SwtcontrolName] = None
    SwitchedObj: Optional[str] = None
    SwitchedTerm: Optional[int] = None
    Action: Optional[str] = None
    Lock: Optional[Union[bool, Bool]] = None
    Delay: Optional[float] = None
    Normal: Optional[str] = None
    State: Optional[str] = None
    Reset: Optional[Union[bool, Bool]] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, SwtcontrolName):
            self.name = SwtcontrolName(self.name)

        if self.SwitchedObj is not None and not isinstance(self.SwitchedObj, str):
            self.SwitchedObj = str(self.SwitchedObj)

        if self.SwitchedTerm is not None and not isinstance(self.SwitchedTerm, int):
            self.SwitchedTerm = int(self.SwitchedTerm)

        if self.Action is not None and not isinstance(self.Action, str):
            self.Action = str(self.Action)

        if self.Lock is not None and not isinstance(self.Lock, Bool):
            self.Lock = Bool(self.Lock)

        if self.Delay is not None and not isinstance(self.Delay, float):
            self.Delay = float(self.Delay)

        if self.Normal is not None and not isinstance(self.Normal, str):
            self.Normal = str(self.Normal)

        if self.State is not None and not isinstance(self.State, str):
            self.State = str(self.State)

        if self.Reset is not None and not isinstance(self.Reset, Bool):
            self.Reset = Bool(self.Reset)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Upfccontrol(YAMLRoot):
    """
    A Upfccontrol object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Upfccontrol"]
    class_class_curie: ClassVar[str] = "dss:Upfccontrol"
    class_name: ClassVar[str] = "Upfccontrol"
    class_model_uri: ClassVar[URIRef] = DSS.Upfccontrol

    name: Union[str, UpfccontrolName] = None
    UPFCList: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, UpfccontrolName):
            self.name = UpfccontrolName(self.name)

        if self.UPFCList is not None and not isinstance(self.UPFCList, str):
            self.UPFCList = str(self.UPFCList)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Buscoords(YAMLRoot):
    """
    The geographic or projected position of a single bus, as one row of a BusCoords / LatLongCoords CSV (``BusName,
    c1, c2``).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Buscoords"]
    class_class_curie: ClassVar[str] = "dss:Buscoords"
    class_name: ClassVar[str] = "Buscoords"
    class_model_uri: ClassVar[URIRef] = DSS.Buscoords

    name: Union[str, BuscoordsName] = None
    x: Optional[float] = None
    y: Optional[float] = None
    geographic: Optional[Union[bool, Bool]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, BuscoordsName):
            self.name = BuscoordsName(self.name)

        if self.x is not None and not isinstance(self.x, float):
            self.x = float(self.x)

        if self.y is not None and not isinstance(self.y, float):
            self.y = float(self.y)

        if self.geographic is not None and not isinstance(self.geographic, Bool):
            self.geographic = Bool(self.geographic)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Cndata(YAMLRoot):
    """
    A Cndata object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Cndata"]
    class_class_curie: ClassVar[str] = "dss:Cndata"
    class_name: ClassVar[str] = "Cndata"
    class_model_uri: ClassVar[URIRef] = DSS.Cndata

    name: Union[str, CndataName] = None
    k: Optional[int] = None
    DiaStrand: Optional[float] = None
    GmrStrand: Optional[float] = None
    Rstrand: Optional[float] = None
    SemiconLayer: Optional[Union[bool, Bool]] = None
    EpsR: Optional[float] = None
    InsLayer: Optional[float] = None
    DiaIns: Optional[float] = None
    DiaCable: Optional[float] = None
    Rdc: Optional[float] = None
    Rac: Optional[float] = None
    Runits: Optional[str] = None
    GMRac: Optional[float] = None
    GMRunits: Optional[str] = None
    radius: Optional[float] = None
    radunits: Optional[str] = None
    normamps: Optional[float] = None
    emergamps: Optional[float] = None
    diam: Optional[float] = None
    Seasons: Optional[int] = None
    Ratings: Optional[Union[float, list[float]]] = empty_list()
    Capradius: Optional[float] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, CndataName):
            self.name = CndataName(self.name)

        if self.k is not None and not isinstance(self.k, int):
            self.k = int(self.k)

        if self.DiaStrand is not None and not isinstance(self.DiaStrand, float):
            self.DiaStrand = float(self.DiaStrand)

        if self.GmrStrand is not None and not isinstance(self.GmrStrand, float):
            self.GmrStrand = float(self.GmrStrand)

        if self.Rstrand is not None and not isinstance(self.Rstrand, float):
            self.Rstrand = float(self.Rstrand)

        if self.SemiconLayer is not None and not isinstance(self.SemiconLayer, Bool):
            self.SemiconLayer = Bool(self.SemiconLayer)

        if self.EpsR is not None and not isinstance(self.EpsR, float):
            self.EpsR = float(self.EpsR)

        if self.InsLayer is not None and not isinstance(self.InsLayer, float):
            self.InsLayer = float(self.InsLayer)

        if self.DiaIns is not None and not isinstance(self.DiaIns, float):
            self.DiaIns = float(self.DiaIns)

        if self.DiaCable is not None and not isinstance(self.DiaCable, float):
            self.DiaCable = float(self.DiaCable)

        if self.Rdc is not None and not isinstance(self.Rdc, float):
            self.Rdc = float(self.Rdc)

        if self.Rac is not None and not isinstance(self.Rac, float):
            self.Rac = float(self.Rac)

        if self.Runits is not None and not isinstance(self.Runits, str):
            self.Runits = str(self.Runits)

        if self.GMRac is not None and not isinstance(self.GMRac, float):
            self.GMRac = float(self.GMRac)

        if self.GMRunits is not None and not isinstance(self.GMRunits, str):
            self.GMRunits = str(self.GMRunits)

        if self.radius is not None and not isinstance(self.radius, float):
            self.radius = float(self.radius)

        if self.radunits is not None and not isinstance(self.radunits, str):
            self.radunits = str(self.radunits)

        if self.normamps is not None and not isinstance(self.normamps, float):
            self.normamps = float(self.normamps)

        if self.emergamps is not None and not isinstance(self.emergamps, float):
            self.emergamps = float(self.emergamps)

        if self.diam is not None and not isinstance(self.diam, float):
            self.diam = float(self.diam)

        if self.Seasons is not None and not isinstance(self.Seasons, int):
            self.Seasons = int(self.Seasons)

        if not isinstance(self.Ratings, list):
            self.Ratings = [self.Ratings] if self.Ratings is not None else []
        self.Ratings = [v if isinstance(v, float) else float(v) for v in self.Ratings]

        if self.Capradius is not None and not isinstance(self.Capradius, float):
            self.Capradius = float(self.Capradius)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Dynamicexp(YAMLRoot):
    """
    A Dynamicexp object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Dynamicexp"]
    class_class_curie: ClassVar[str] = "dss:Dynamicexp"
    class_name: ClassVar[str] = "Dynamicexp"
    class_model_uri: ClassVar[URIRef] = DSS.Dynamicexp

    name: Union[str, DynamicexpName] = None
    nvariables: Optional[int] = None
    varnames: Optional[Union[str, list[str]]] = empty_list()
    var: Optional[str] = None
    varidx: Optional[str] = None
    expression: Optional[str] = None
    Domain: Optional[str] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, DynamicexpName):
            self.name = DynamicexpName(self.name)

        if self.nvariables is not None and not isinstance(self.nvariables, int):
            self.nvariables = int(self.nvariables)

        if not isinstance(self.varnames, list):
            self.varnames = [self.varnames] if self.varnames is not None else []
        self.varnames = [v if isinstance(v, str) else str(v) for v in self.varnames]

        if self.var is not None and not isinstance(self.var, str):
            self.var = str(self.var)

        if self.varidx is not None and not isinstance(self.varidx, str):
            self.varidx = str(self.varidx)

        if self.expression is not None and not isinstance(self.expression, str):
            self.expression = str(self.expression)

        if self.Domain is not None and not isinstance(self.Domain, str):
            self.Domain = str(self.Domain)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Growthshape(YAMLRoot):
    """
    A Growthshape object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Growthshape"]
    class_class_curie: ClassVar[str] = "dss:Growthshape"
    class_name: ClassVar[str] = "Growthshape"
    class_model_uri: ClassVar[URIRef] = DSS.Growthshape

    name: Union[str, GrowthshapeName] = None
    npts: Optional[int] = None
    year: Optional[Union[int, list[int]]] = empty_list()
    mult: Optional[Union[float, list[float]]] = empty_list()
    csvfile: Optional[float] = None
    sngfile: Optional[float] = None
    dblfile: Optional[float] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, GrowthshapeName):
            self.name = GrowthshapeName(self.name)

        if self.npts is not None and not isinstance(self.npts, int):
            self.npts = int(self.npts)

        if not isinstance(self.year, list):
            self.year = [self.year] if self.year is not None else []
        self.year = [v if isinstance(v, int) else int(v) for v in self.year]

        if not isinstance(self.mult, list):
            self.mult = [self.mult] if self.mult is not None else []
        self.mult = [v if isinstance(v, float) else float(v) for v in self.mult]

        if self.csvfile is not None and not isinstance(self.csvfile, float):
            self.csvfile = float(self.csvfile)

        if self.sngfile is not None and not isinstance(self.sngfile, float):
            self.sngfile = float(self.sngfile)

        if self.dblfile is not None and not isinstance(self.dblfile, float):
            self.dblfile = float(self.dblfile)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Linecode(YAMLRoot):
    """
    A Linecode object in OpenDSS defining per-unit-length impedance data shared by multiple lines. Depending on
    whether sequence impedances or matrices are provided, the converter creates either a PerLengthSequenceImpedance or
    a PerLengthPhaseImpedance + PhaseImpedanceData.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Linecode"]
    class_class_curie: ClassVar[str] = "dss:Linecode"
    class_name: ClassVar[str] = "Linecode"
    class_model_uri: ClassVar[URIRef] = DSS.Linecode

    name: Union[str, LinecodeName] = None
    nphases: Optional[int] = None
    r1: Optional[float] = None
    x1: Optional[float] = None
    r0: Optional[float] = None
    x0: Optional[float] = None
    C1: Optional[str] = None
    C0: Optional[str] = None
    units: Optional[str] = None
    rmatrix: Optional[Union[float, list[float]]] = empty_list()
    xmatrix: Optional[Union[float, list[float]]] = empty_list()
    cmatrix: Optional[Union[float, list[float]]] = empty_list()
    baseFreq: Optional[str] = None
    normamps: Optional[float] = None
    emergamps: Optional[float] = None
    faultrate: Optional[float] = None
    pctperm: Optional[float] = None
    repair: Optional[str] = None
    Kron: Optional[str] = None
    Rg: Optional[float] = None
    Xg: Optional[float] = None
    rho: Optional[float] = None
    neutral: Optional[str] = None
    B1: Optional[str] = None
    B0: Optional[str] = None
    Seasons: Optional[int] = None
    Ratings: Optional[Union[float, list[float]]] = empty_list()
    LineType: Optional[float] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, LinecodeName):
            self.name = LinecodeName(self.name)

        if self.nphases is not None and not isinstance(self.nphases, int):
            self.nphases = int(self.nphases)

        if self.r1 is not None and not isinstance(self.r1, float):
            self.r1 = float(self.r1)

        if self.x1 is not None and not isinstance(self.x1, float):
            self.x1 = float(self.x1)

        if self.r0 is not None and not isinstance(self.r0, float):
            self.r0 = float(self.r0)

        if self.x0 is not None and not isinstance(self.x0, float):
            self.x0 = float(self.x0)

        if self.C1 is not None and not isinstance(self.C1, str):
            self.C1 = str(self.C1)

        if self.C0 is not None and not isinstance(self.C0, str):
            self.C0 = str(self.C0)

        if self.units is not None and not isinstance(self.units, str):
            self.units = str(self.units)

        if not isinstance(self.rmatrix, list):
            self.rmatrix = [self.rmatrix] if self.rmatrix is not None else []
        self.rmatrix = [v if isinstance(v, float) else float(v) for v in self.rmatrix]

        if not isinstance(self.xmatrix, list):
            self.xmatrix = [self.xmatrix] if self.xmatrix is not None else []
        self.xmatrix = [v if isinstance(v, float) else float(v) for v in self.xmatrix]

        if not isinstance(self.cmatrix, list):
            self.cmatrix = [self.cmatrix] if self.cmatrix is not None else []
        self.cmatrix = [v if isinstance(v, float) else float(v) for v in self.cmatrix]

        if self.baseFreq is not None and not isinstance(self.baseFreq, str):
            self.baseFreq = str(self.baseFreq)

        if self.normamps is not None and not isinstance(self.normamps, float):
            self.normamps = float(self.normamps)

        if self.emergamps is not None and not isinstance(self.emergamps, float):
            self.emergamps = float(self.emergamps)

        if self.faultrate is not None and not isinstance(self.faultrate, float):
            self.faultrate = float(self.faultrate)

        if self.pctperm is not None and not isinstance(self.pctperm, float):
            self.pctperm = float(self.pctperm)

        if self.repair is not None and not isinstance(self.repair, str):
            self.repair = str(self.repair)

        if self.Kron is not None and not isinstance(self.Kron, str):
            self.Kron = str(self.Kron)

        if self.Rg is not None and not isinstance(self.Rg, float):
            self.Rg = float(self.Rg)

        if self.Xg is not None and not isinstance(self.Xg, float):
            self.Xg = float(self.Xg)

        if self.rho is not None and not isinstance(self.rho, float):
            self.rho = float(self.rho)

        if self.neutral is not None and not isinstance(self.neutral, str):
            self.neutral = str(self.neutral)

        if self.B1 is not None and not isinstance(self.B1, str):
            self.B1 = str(self.B1)

        if self.B0 is not None and not isinstance(self.B0, str):
            self.B0 = str(self.B0)

        if self.Seasons is not None and not isinstance(self.Seasons, int):
            self.Seasons = int(self.Seasons)

        if not isinstance(self.Ratings, list):
            self.Ratings = [self.Ratings] if self.Ratings is not None else []
        self.Ratings = [v if isinstance(v, float) else float(v) for v in self.Ratings]

        if self.LineType is not None and not isinstance(self.LineType, float):
            self.LineType = float(self.LineType)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Linegeometry(YAMLRoot):
    """
    A Linegeometry object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Linegeometry"]
    class_class_curie: ClassVar[str] = "dss:Linegeometry"
    class_name: ClassVar[str] = "Linegeometry"
    class_model_uri: ClassVar[URIRef] = DSS.Linegeometry

    name: Union[str, LinegeometryName] = None
    nconds: Optional[int] = None
    nphases: Optional[int] = None
    cond: Optional[int] = None
    wire: Optional[str] = None
    x: Optional[float] = None
    h: Optional[float] = None
    units: Optional[str] = None
    normamps: Optional[float] = None
    emergamps: Optional[float] = None
    reduce: Optional[Union[bool, Bool]] = None
    spacing: Optional[str] = None
    wires: Optional[Union[str, list[str]]] = empty_list()
    cncable: Optional[str] = None
    tscable: Optional[str] = None
    cncables: Optional[Union[str, list[str]]] = empty_list()
    tscables: Optional[Union[str, list[str]]] = empty_list()
    xs: Optional[Union[float, list[float]]] = empty_list()
    hs: Optional[Union[float, list[float]]] = empty_list()
    Seasons: Optional[int] = None
    Ratings: Optional[Union[float, list[float]]] = empty_list()
    LineType: Optional[str] = None
    conductors: Optional[Union[str, list[str]]] = empty_list()
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, LinegeometryName):
            self.name = LinegeometryName(self.name)

        if self.nconds is not None and not isinstance(self.nconds, int):
            self.nconds = int(self.nconds)

        if self.nphases is not None and not isinstance(self.nphases, int):
            self.nphases = int(self.nphases)

        if self.cond is not None and not isinstance(self.cond, int):
            self.cond = int(self.cond)

        if self.wire is not None and not isinstance(self.wire, str):
            self.wire = str(self.wire)

        if self.x is not None and not isinstance(self.x, float):
            self.x = float(self.x)

        if self.h is not None and not isinstance(self.h, float):
            self.h = float(self.h)

        if self.units is not None and not isinstance(self.units, str):
            self.units = str(self.units)

        if self.normamps is not None and not isinstance(self.normamps, float):
            self.normamps = float(self.normamps)

        if self.emergamps is not None and not isinstance(self.emergamps, float):
            self.emergamps = float(self.emergamps)

        if self.reduce is not None and not isinstance(self.reduce, Bool):
            self.reduce = Bool(self.reduce)

        if self.spacing is not None and not isinstance(self.spacing, str):
            self.spacing = str(self.spacing)

        if not isinstance(self.wires, list):
            self.wires = [self.wires] if self.wires is not None else []
        self.wires = [v if isinstance(v, str) else str(v) for v in self.wires]

        if self.cncable is not None and not isinstance(self.cncable, str):
            self.cncable = str(self.cncable)

        if self.tscable is not None and not isinstance(self.tscable, str):
            self.tscable = str(self.tscable)

        if not isinstance(self.cncables, list):
            self.cncables = [self.cncables] if self.cncables is not None else []
        self.cncables = [v if isinstance(v, str) else str(v) for v in self.cncables]

        if not isinstance(self.tscables, list):
            self.tscables = [self.tscables] if self.tscables is not None else []
        self.tscables = [v if isinstance(v, str) else str(v) for v in self.tscables]

        if not isinstance(self.xs, list):
            self.xs = [self.xs] if self.xs is not None else []
        self.xs = [v if isinstance(v, float) else float(v) for v in self.xs]

        if not isinstance(self.hs, list):
            self.hs = [self.hs] if self.hs is not None else []
        self.hs = [v if isinstance(v, float) else float(v) for v in self.hs]

        if self.Seasons is not None and not isinstance(self.Seasons, int):
            self.Seasons = int(self.Seasons)

        if not isinstance(self.Ratings, list):
            self.Ratings = [self.Ratings] if self.Ratings is not None else []
        self.Ratings = [v if isinstance(v, float) else float(v) for v in self.Ratings]

        if self.LineType is not None and not isinstance(self.LineType, str):
            self.LineType = str(self.LineType)

        if not isinstance(self.conductors, list):
            self.conductors = [self.conductors] if self.conductors is not None else []
        self.conductors = [v if isinstance(v, str) else str(v) for v in self.conductors]

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Linespacing(YAMLRoot):
    """
    A Linespacing object in OpenDSS defining the physical arrangement (XY coordinates) of conductors in a
    cross-section, used for geometric impedance calculation.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Linespacing"]
    class_class_curie: ClassVar[str] = "dss:Linespacing"
    class_name: ClassVar[str] = "Linespacing"
    class_model_uri: ClassVar[URIRef] = DSS.Linespacing

    name: Union[str, LinespacingName] = None
    nconds: Optional[int] = None
    nphases: Optional[int] = None
    x: Optional[Union[float, list[float]]] = empty_list()
    h: Optional[Union[float, list[float]]] = empty_list()
    units: Optional[str] = None
    detailed: Optional[Union[bool, Bool]] = None
    EqDistPhPh: Optional[str] = None
    EqDistPhN: Optional[str] = None
    AvgPhaseHeight: Optional[str] = None
    AvgNeutralHeight: Optional[str] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, LinespacingName):
            self.name = LinespacingName(self.name)

        if self.nconds is not None and not isinstance(self.nconds, int):
            self.nconds = int(self.nconds)

        if self.nphases is not None and not isinstance(self.nphases, int):
            self.nphases = int(self.nphases)

        if not isinstance(self.x, list):
            self.x = [self.x] if self.x is not None else []
        self.x = [v if isinstance(v, float) else float(v) for v in self.x]

        if not isinstance(self.h, list):
            self.h = [self.h] if self.h is not None else []
        self.h = [v if isinstance(v, float) else float(v) for v in self.h]

        if self.units is not None and not isinstance(self.units, str):
            self.units = str(self.units)

        if self.detailed is not None and not isinstance(self.detailed, Bool):
            self.detailed = Bool(self.detailed)

        if self.EqDistPhPh is not None and not isinstance(self.EqDistPhPh, str):
            self.EqDistPhPh = str(self.EqDistPhPh)

        if self.EqDistPhN is not None and not isinstance(self.EqDistPhN, str):
            self.EqDistPhN = str(self.EqDistPhN)

        if self.AvgPhaseHeight is not None and not isinstance(self.AvgPhaseHeight, str):
            self.AvgPhaseHeight = str(self.AvgPhaseHeight)

        if self.AvgNeutralHeight is not None and not isinstance(self.AvgNeutralHeight, str):
            self.AvgNeutralHeight = str(self.AvgNeutralHeight)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Loadshape(YAMLRoot):
    """
    A Loadshape object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Loadshape"]
    class_class_curie: ClassVar[str] = "dss:Loadshape"
    class_name: ClassVar[str] = "Loadshape"
    class_model_uri: ClassVar[URIRef] = DSS.Loadshape

    name: Union[str, LoadshapeName] = None
    npts: Optional[int] = None
    interval: Optional[float] = None
    mult: Optional[Union[float, list[float]]] = empty_list()
    hour: Optional[Union[float, list[float]]] = empty_list()
    mean: Optional[float] = None
    stddev: Optional[float] = None
    csvfile: Optional[int] = None
    sngfile: Optional[int] = None
    dblfile: Optional[int] = None
    action: Optional[str] = None
    qmult: Optional[Union[float, list[float]]] = empty_list()
    UseActual: Optional[Union[bool, Bool]] = None
    Pmax: Optional[float] = None
    Qmax: Optional[float] = None
    sinterval: Optional[str] = None
    minterval: Optional[str] = None
    Pbase: Optional[str] = None
    Qbase: Optional[str] = None
    Pmult: Optional[str] = None
    PQCSVFile: Optional[float] = None
    MemoryMapping: Optional[Union[bool, Bool]] = None
    Mode: Optional[float] = None
    Interpolation: Optional[str] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, LoadshapeName):
            self.name = LoadshapeName(self.name)

        if self.npts is not None and not isinstance(self.npts, int):
            self.npts = int(self.npts)

        if self.interval is not None and not isinstance(self.interval, float):
            self.interval = float(self.interval)

        if not isinstance(self.mult, list):
            self.mult = [self.mult] if self.mult is not None else []
        self.mult = [v if isinstance(v, float) else float(v) for v in self.mult]

        if not isinstance(self.hour, list):
            self.hour = [self.hour] if self.hour is not None else []
        self.hour = [v if isinstance(v, float) else float(v) for v in self.hour]

        if self.mean is not None and not isinstance(self.mean, float):
            self.mean = float(self.mean)

        if self.stddev is not None and not isinstance(self.stddev, float):
            self.stddev = float(self.stddev)

        if self.csvfile is not None and not isinstance(self.csvfile, int):
            self.csvfile = int(self.csvfile)

        if self.sngfile is not None and not isinstance(self.sngfile, int):
            self.sngfile = int(self.sngfile)

        if self.dblfile is not None and not isinstance(self.dblfile, int):
            self.dblfile = int(self.dblfile)

        if self.action is not None and not isinstance(self.action, str):
            self.action = str(self.action)

        if not isinstance(self.qmult, list):
            self.qmult = [self.qmult] if self.qmult is not None else []
        self.qmult = [v if isinstance(v, float) else float(v) for v in self.qmult]

        if self.UseActual is not None and not isinstance(self.UseActual, Bool):
            self.UseActual = Bool(self.UseActual)

        if self.Pmax is not None and not isinstance(self.Pmax, float):
            self.Pmax = float(self.Pmax)

        if self.Qmax is not None and not isinstance(self.Qmax, float):
            self.Qmax = float(self.Qmax)

        if self.sinterval is not None and not isinstance(self.sinterval, str):
            self.sinterval = str(self.sinterval)

        if self.minterval is not None and not isinstance(self.minterval, str):
            self.minterval = str(self.minterval)

        if self.Pbase is not None and not isinstance(self.Pbase, str):
            self.Pbase = str(self.Pbase)

        if self.Qbase is not None and not isinstance(self.Qbase, str):
            self.Qbase = str(self.Qbase)

        if self.Pmult is not None and not isinstance(self.Pmult, str):
            self.Pmult = str(self.Pmult)

        if self.PQCSVFile is not None and not isinstance(self.PQCSVFile, float):
            self.PQCSVFile = float(self.PQCSVFile)

        if self.MemoryMapping is not None and not isinstance(self.MemoryMapping, Bool):
            self.MemoryMapping = Bool(self.MemoryMapping)

        if self.Mode is not None and not isinstance(self.Mode, float):
            self.Mode = float(self.Mode)

        if self.Interpolation is not None and not isinstance(self.Interpolation, str):
            self.Interpolation = str(self.Interpolation)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Priceshape(YAMLRoot):
    """
    A Priceshape object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Priceshape"]
    class_class_curie: ClassVar[str] = "dss:Priceshape"
    class_name: ClassVar[str] = "Priceshape"
    class_model_uri: ClassVar[URIRef] = DSS.Priceshape

    name: Union[str, PriceshapeName] = None
    npts: Optional[int] = None
    interval: Optional[float] = None
    price: Optional[Union[float, list[float]]] = empty_list()
    hour: Optional[Union[float, list[float]]] = empty_list()
    mean: Optional[float] = None
    stddev: Optional[float] = None
    csvfile: Optional[int] = None
    sngfile: Optional[int] = None
    dblfile: Optional[int] = None
    sinterval: Optional[str] = None
    minterval: Optional[str] = None
    action: Optional[str] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, PriceshapeName):
            self.name = PriceshapeName(self.name)

        if self.npts is not None and not isinstance(self.npts, int):
            self.npts = int(self.npts)

        if self.interval is not None and not isinstance(self.interval, float):
            self.interval = float(self.interval)

        if not isinstance(self.price, list):
            self.price = [self.price] if self.price is not None else []
        self.price = [v if isinstance(v, float) else float(v) for v in self.price]

        if not isinstance(self.hour, list):
            self.hour = [self.hour] if self.hour is not None else []
        self.hour = [v if isinstance(v, float) else float(v) for v in self.hour]

        if self.mean is not None and not isinstance(self.mean, float):
            self.mean = float(self.mean)

        if self.stddev is not None and not isinstance(self.stddev, float):
            self.stddev = float(self.stddev)

        if self.csvfile is not None and not isinstance(self.csvfile, int):
            self.csvfile = int(self.csvfile)

        if self.sngfile is not None and not isinstance(self.sngfile, int):
            self.sngfile = int(self.sngfile)

        if self.dblfile is not None and not isinstance(self.dblfile, int):
            self.dblfile = int(self.dblfile)

        if self.sinterval is not None and not isinstance(self.sinterval, str):
            self.sinterval = str(self.sinterval)

        if self.minterval is not None and not isinstance(self.minterval, str):
            self.minterval = str(self.minterval)

        if self.action is not None and not isinstance(self.action, str):
            self.action = str(self.action)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Spectrum(YAMLRoot):
    """
    A Spectrum object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Spectrum"]
    class_class_curie: ClassVar[str] = "dss:Spectrum"
    class_name: ClassVar[str] = "Spectrum"
    class_model_uri: ClassVar[URIRef] = DSS.Spectrum

    name: Union[str, SpectrumName] = None
    NumHarm: Optional[int] = None
    harmonic: Optional[Union[float, list[float]]] = empty_list()
    pct_mag: Optional[Union[float, list[float]]] = empty_list()
    angle: Optional[Union[float, list[float]]] = empty_list()
    CSVFile: Optional[float] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, SpectrumName):
            self.name = SpectrumName(self.name)

        if self.NumHarm is not None and not isinstance(self.NumHarm, int):
            self.NumHarm = int(self.NumHarm)

        if not isinstance(self.harmonic, list):
            self.harmonic = [self.harmonic] if self.harmonic is not None else []
        self.harmonic = [v if isinstance(v, float) else float(v) for v in self.harmonic]

        if not isinstance(self.pct_mag, list):
            self.pct_mag = [self.pct_mag] if self.pct_mag is not None else []
        self.pct_mag = [v if isinstance(v, float) else float(v) for v in self.pct_mag]

        if not isinstance(self.angle, list):
            self.angle = [self.angle] if self.angle is not None else []
        self.angle = [v if isinstance(v, float) else float(v) for v in self.angle]

        if self.CSVFile is not None and not isinstance(self.CSVFile, float):
            self.CSVFile = float(self.CSVFile)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class TccCurve(YAMLRoot):
    """
    A TccCurve object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["TccCurve"]
    class_class_curie: ClassVar[str] = "dss:TccCurve"
    class_name: ClassVar[str] = "TccCurve"
    class_model_uri: ClassVar[URIRef] = DSS.TccCurve

    name: Union[str, TccCurveName] = None
    npts: Optional[int] = None
    C_array: Optional[Union[float, list[float]]] = empty_list()
    T_array: Optional[Union[float, list[float]]] = empty_list()
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, TccCurveName):
            self.name = TccCurveName(self.name)

        if self.npts is not None and not isinstance(self.npts, int):
            self.npts = int(self.npts)

        if not isinstance(self.C_array, list):
            self.C_array = [self.C_array] if self.C_array is not None else []
        self.C_array = [v if isinstance(v, float) else float(v) for v in self.C_array]

        if not isinstance(self.T_array, list):
            self.T_array = [self.T_array] if self.T_array is not None else []
        self.T_array = [v if isinstance(v, float) else float(v) for v in self.T_array]

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Tsdata(YAMLRoot):
    """
    A Tsdata object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Tsdata"]
    class_class_curie: ClassVar[str] = "dss:Tsdata"
    class_name: ClassVar[str] = "Tsdata"
    class_model_uri: ClassVar[URIRef] = DSS.Tsdata

    name: Union[str, TsdataName] = None
    DiaShield: Optional[float] = None
    TapeLayer: Optional[float] = None
    TapeLap: Optional[float] = None
    EpsR: Optional[float] = None
    InsLayer: Optional[float] = None
    DiaIns: Optional[float] = None
    DiaCable: Optional[float] = None
    Rdc: Optional[float] = None
    Rac: Optional[float] = None
    Runits: Optional[str] = None
    GMRac: Optional[float] = None
    GMRunits: Optional[str] = None
    radius: Optional[float] = None
    radunits: Optional[str] = None
    normamps: Optional[float] = None
    emergamps: Optional[float] = None
    diam: Optional[float] = None
    Seasons: Optional[int] = None
    Ratings: Optional[Union[float, list[float]]] = empty_list()
    Capradius: Optional[float] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, TsdataName):
            self.name = TsdataName(self.name)

        if self.DiaShield is not None and not isinstance(self.DiaShield, float):
            self.DiaShield = float(self.DiaShield)

        if self.TapeLayer is not None and not isinstance(self.TapeLayer, float):
            self.TapeLayer = float(self.TapeLayer)

        if self.TapeLap is not None and not isinstance(self.TapeLap, float):
            self.TapeLap = float(self.TapeLap)

        if self.EpsR is not None and not isinstance(self.EpsR, float):
            self.EpsR = float(self.EpsR)

        if self.InsLayer is not None and not isinstance(self.InsLayer, float):
            self.InsLayer = float(self.InsLayer)

        if self.DiaIns is not None and not isinstance(self.DiaIns, float):
            self.DiaIns = float(self.DiaIns)

        if self.DiaCable is not None and not isinstance(self.DiaCable, float):
            self.DiaCable = float(self.DiaCable)

        if self.Rdc is not None and not isinstance(self.Rdc, float):
            self.Rdc = float(self.Rdc)

        if self.Rac is not None and not isinstance(self.Rac, float):
            self.Rac = float(self.Rac)

        if self.Runits is not None and not isinstance(self.Runits, str):
            self.Runits = str(self.Runits)

        if self.GMRac is not None and not isinstance(self.GMRac, float):
            self.GMRac = float(self.GMRac)

        if self.GMRunits is not None and not isinstance(self.GMRunits, str):
            self.GMRunits = str(self.GMRunits)

        if self.radius is not None and not isinstance(self.radius, float):
            self.radius = float(self.radius)

        if self.radunits is not None and not isinstance(self.radunits, str):
            self.radunits = str(self.radunits)

        if self.normamps is not None and not isinstance(self.normamps, float):
            self.normamps = float(self.normamps)

        if self.emergamps is not None and not isinstance(self.emergamps, float):
            self.emergamps = float(self.emergamps)

        if self.diam is not None and not isinstance(self.diam, float):
            self.diam = float(self.diam)

        if self.Seasons is not None and not isinstance(self.Seasons, int):
            self.Seasons = int(self.Seasons)

        if not isinstance(self.Ratings, list):
            self.Ratings = [self.Ratings] if self.Ratings is not None else []
        self.Ratings = [v if isinstance(v, float) else float(v) for v in self.Ratings]

        if self.Capradius is not None and not isinstance(self.Capradius, float):
            self.Capradius = float(self.Capradius)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Tshape(YAMLRoot):
    """
    A Tshape object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Tshape"]
    class_class_curie: ClassVar[str] = "dss:Tshape"
    class_name: ClassVar[str] = "Tshape"
    class_model_uri: ClassVar[URIRef] = DSS.Tshape

    name: Union[str, TshapeName] = None
    npts: Optional[int] = None
    interval: Optional[float] = None
    temp: Optional[Union[float, list[float]]] = empty_list()
    hour: Optional[Union[float, list[float]]] = empty_list()
    mean: Optional[float] = None
    stddev: Optional[float] = None
    csvfile: Optional[int] = None
    sngfile: Optional[int] = None
    dblfile: Optional[int] = None
    sinterval: Optional[str] = None
    minterval: Optional[str] = None
    action: Optional[str] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, TshapeName):
            self.name = TshapeName(self.name)

        if self.npts is not None and not isinstance(self.npts, int):
            self.npts = int(self.npts)

        if self.interval is not None and not isinstance(self.interval, float):
            self.interval = float(self.interval)

        if not isinstance(self.temp, list):
            self.temp = [self.temp] if self.temp is not None else []
        self.temp = [v if isinstance(v, float) else float(v) for v in self.temp]

        if not isinstance(self.hour, list):
            self.hour = [self.hour] if self.hour is not None else []
        self.hour = [v if isinstance(v, float) else float(v) for v in self.hour]

        if self.mean is not None and not isinstance(self.mean, float):
            self.mean = float(self.mean)

        if self.stddev is not None and not isinstance(self.stddev, float):
            self.stddev = float(self.stddev)

        if self.csvfile is not None and not isinstance(self.csvfile, int):
            self.csvfile = int(self.csvfile)

        if self.sngfile is not None and not isinstance(self.sngfile, int):
            self.sngfile = int(self.sngfile)

        if self.dblfile is not None and not isinstance(self.dblfile, int):
            self.dblfile = int(self.dblfile)

        if self.sinterval is not None and not isinstance(self.sinterval, str):
            self.sinterval = str(self.sinterval)

        if self.minterval is not None and not isinstance(self.minterval, str):
            self.minterval = str(self.minterval)

        if self.action is not None and not isinstance(self.action, str):
            self.action = str(self.action)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Wiredata(YAMLRoot):
    """
    A Wiredata object in OpenDSS defining physical conductor properties (resistance, GMR, radius) used by LineGeometry
    and Line objects for geometric impedance calculation.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Wiredata"]
    class_class_curie: ClassVar[str] = "dss:Wiredata"
    class_name: ClassVar[str] = "Wiredata"
    class_model_uri: ClassVar[URIRef] = DSS.Wiredata

    name: Union[str, WiredataName] = None
    Rdc: Optional[float] = None
    Rac: Optional[float] = None
    Runits: Optional[str] = None
    GMRac: Optional[float] = None
    GMRunits: Optional[str] = None
    radius: Optional[float] = None
    radunits: Optional[str] = None
    normamps: Optional[float] = None
    emergamps: Optional[float] = None
    diam: Optional[float] = None
    Seasons: Optional[int] = None
    Ratings: Optional[Union[float, list[float]]] = empty_list()
    Capradius: Optional[float] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, WiredataName):
            self.name = WiredataName(self.name)

        if self.Rdc is not None and not isinstance(self.Rdc, float):
            self.Rdc = float(self.Rdc)

        if self.Rac is not None and not isinstance(self.Rac, float):
            self.Rac = float(self.Rac)

        if self.Runits is not None and not isinstance(self.Runits, str):
            self.Runits = str(self.Runits)

        if self.GMRac is not None and not isinstance(self.GMRac, float):
            self.GMRac = float(self.GMRac)

        if self.GMRunits is not None and not isinstance(self.GMRunits, str):
            self.GMRunits = str(self.GMRunits)

        if self.radius is not None and not isinstance(self.radius, float):
            self.radius = float(self.radius)

        if self.radunits is not None and not isinstance(self.radunits, str):
            self.radunits = str(self.radunits)

        if self.normamps is not None and not isinstance(self.normamps, float):
            self.normamps = float(self.normamps)

        if self.emergamps is not None and not isinstance(self.emergamps, float):
            self.emergamps = float(self.emergamps)

        if self.diam is not None and not isinstance(self.diam, float):
            self.diam = float(self.diam)

        if self.Seasons is not None and not isinstance(self.Seasons, int):
            self.Seasons = int(self.Seasons)

        if not isinstance(self.Ratings, list):
            self.Ratings = [self.Ratings] if self.Ratings is not None else []
        self.Ratings = [v if isinstance(v, float) else float(v) for v in self.Ratings]

        if self.Capradius is not None and not isinstance(self.Capradius, float):
            self.Capradius = float(self.Capradius)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Xfmrcode(YAMLRoot):
    """
    A Xfmrcode object in OpenDSS representing a transformer library entry (catalog) that can be referenced by
    Transformer objects via the XfmrCode property.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Xfmrcode"]
    class_class_curie: ClassVar[str] = "dss:Xfmrcode"
    class_name: ClassVar[str] = "Xfmrcode"
    class_model_uri: ClassVar[URIRef] = DSS.Xfmrcode

    name: Union[str, XfmrcodeName] = None
    phases: Optional[int] = None
    windings: Optional[int] = None
    wdg: Optional[int] = None
    conn: Optional[Union[str, "ConnectionType"]] = None
    kV: Optional[float] = None
    kVA: Optional[float] = None
    tap: Optional[str] = None
    pct_R: Optional[float] = None
    Rneut: Optional[float] = None
    Xneut: Optional[float] = None
    conns: Optional[Union[Union[str, "ConnectionType"], list[Union[str, "ConnectionType"]]]] = empty_list()
    kVs: Optional[Union[float, list[float]]] = empty_list()
    kVAs: Optional[Union[float, list[float]]] = empty_list()
    taps: Optional[Union[float, list[float]]] = empty_list()
    Xhl: Optional[float] = None
    Xht: Optional[float] = None
    Xlt: Optional[float] = None
    Xscarray: Optional[Union[float, list[float]]] = empty_list()
    thermal: Optional[str] = None
    n: Optional[str] = None
    m: Optional[str] = None
    flrise: Optional[str] = None
    hsrise: Optional[str] = None
    pct_loadloss: Optional[float] = None
    pct_noloadloss: Optional[float] = None
    normhkVA: Optional[float] = None
    emerghkVA: Optional[float] = None
    MaxTap: Optional[str] = None
    MinTap: Optional[str] = None
    NumTaps: Optional[int] = None
    pct_imag: Optional[float] = None
    ppm_antifloat: Optional[float] = None
    pct_Rs: Optional[Union[float, list[float]]] = empty_list()
    X12: Optional[float] = None
    X13: Optional[float] = None
    X23: Optional[float] = None
    RdcOhms: Optional[Union[float, list[float]]] = empty_list()
    Seasons: Optional[int] = None
    Ratings: Optional[Union[float, list[float]]] = empty_list()
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, XfmrcodeName):
            self.name = XfmrcodeName(self.name)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.windings is not None and not isinstance(self.windings, int):
            self.windings = int(self.windings)

        if self.wdg is not None and not isinstance(self.wdg, int):
            self.wdg = int(self.wdg)

        if self.conn is not None and not isinstance(self.conn, ConnectionType):
            self.conn = ConnectionType(self.conn)

        if self.kV is not None and not isinstance(self.kV, float):
            self.kV = float(self.kV)

        if self.kVA is not None and not isinstance(self.kVA, float):
            self.kVA = float(self.kVA)

        if self.tap is not None and not isinstance(self.tap, str):
            self.tap = str(self.tap)

        if self.pct_R is not None and not isinstance(self.pct_R, float):
            self.pct_R = float(self.pct_R)

        if self.Rneut is not None and not isinstance(self.Rneut, float):
            self.Rneut = float(self.Rneut)

        if self.Xneut is not None and not isinstance(self.Xneut, float):
            self.Xneut = float(self.Xneut)

        if not isinstance(self.conns, list):
            self.conns = [self.conns] if self.conns is not None else []
        self.conns = [v if isinstance(v, ConnectionType) else ConnectionType(v) for v in self.conns]

        if not isinstance(self.kVs, list):
            self.kVs = [self.kVs] if self.kVs is not None else []
        self.kVs = [v if isinstance(v, float) else float(v) for v in self.kVs]

        if not isinstance(self.kVAs, list):
            self.kVAs = [self.kVAs] if self.kVAs is not None else []
        self.kVAs = [v if isinstance(v, float) else float(v) for v in self.kVAs]

        if not isinstance(self.taps, list):
            self.taps = [self.taps] if self.taps is not None else []
        self.taps = [v if isinstance(v, float) else float(v) for v in self.taps]

        if self.Xhl is not None and not isinstance(self.Xhl, float):
            self.Xhl = float(self.Xhl)

        if self.Xht is not None and not isinstance(self.Xht, float):
            self.Xht = float(self.Xht)

        if self.Xlt is not None and not isinstance(self.Xlt, float):
            self.Xlt = float(self.Xlt)

        if not isinstance(self.Xscarray, list):
            self.Xscarray = [self.Xscarray] if self.Xscarray is not None else []
        self.Xscarray = [v if isinstance(v, float) else float(v) for v in self.Xscarray]

        if self.thermal is not None and not isinstance(self.thermal, str):
            self.thermal = str(self.thermal)

        if self.n is not None and not isinstance(self.n, str):
            self.n = str(self.n)

        if self.m is not None and not isinstance(self.m, str):
            self.m = str(self.m)

        if self.flrise is not None and not isinstance(self.flrise, str):
            self.flrise = str(self.flrise)

        if self.hsrise is not None and not isinstance(self.hsrise, str):
            self.hsrise = str(self.hsrise)

        if self.pct_loadloss is not None and not isinstance(self.pct_loadloss, float):
            self.pct_loadloss = float(self.pct_loadloss)

        if self.pct_noloadloss is not None and not isinstance(self.pct_noloadloss, float):
            self.pct_noloadloss = float(self.pct_noloadloss)

        if self.normhkVA is not None and not isinstance(self.normhkVA, float):
            self.normhkVA = float(self.normhkVA)

        if self.emerghkVA is not None and not isinstance(self.emerghkVA, float):
            self.emerghkVA = float(self.emerghkVA)

        if self.MaxTap is not None and not isinstance(self.MaxTap, str):
            self.MaxTap = str(self.MaxTap)

        if self.MinTap is not None and not isinstance(self.MinTap, str):
            self.MinTap = str(self.MinTap)

        if self.NumTaps is not None and not isinstance(self.NumTaps, int):
            self.NumTaps = int(self.NumTaps)

        if self.pct_imag is not None and not isinstance(self.pct_imag, float):
            self.pct_imag = float(self.pct_imag)

        if self.ppm_antifloat is not None and not isinstance(self.ppm_antifloat, float):
            self.ppm_antifloat = float(self.ppm_antifloat)

        if not isinstance(self.pct_Rs, list):
            self.pct_Rs = [self.pct_Rs] if self.pct_Rs is not None else []
        self.pct_Rs = [v if isinstance(v, float) else float(v) for v in self.pct_Rs]

        if self.X12 is not None and not isinstance(self.X12, float):
            self.X12 = float(self.X12)

        if self.X13 is not None and not isinstance(self.X13, float):
            self.X13 = float(self.X13)

        if self.X23 is not None and not isinstance(self.X23, float):
            self.X23 = float(self.X23)

        if not isinstance(self.RdcOhms, list):
            self.RdcOhms = [self.RdcOhms] if self.RdcOhms is not None else []
        self.RdcOhms = [v if isinstance(v, float) else float(v) for v in self.RdcOhms]

        if self.Seasons is not None and not isinstance(self.Seasons, int):
            self.Seasons = int(self.Seasons)

        if not isinstance(self.Ratings, list):
            self.Ratings = [self.Ratings] if self.Ratings is not None else []
        self.Ratings = [v if isinstance(v, float) else float(v) for v in self.Ratings]

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Xycurve(YAMLRoot):
    """
    A Xycurve object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Xycurve"]
    class_class_curie: ClassVar[str] = "dss:Xycurve"
    class_name: ClassVar[str] = "Xycurve"
    class_model_uri: ClassVar[URIRef] = DSS.Xycurve

    name: Union[str, XycurveName] = None
    npts: Optional[int] = None
    Points: Optional[int] = None
    Yarray: Optional[int] = None
    Xarray: Optional[int] = None
    csvfile: Optional[int] = None
    sngfile: Optional[int] = None
    dblfile: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    Xshift: Optional[str] = None
    Yshift: Optional[str] = None
    Xscale: Optional[str] = None
    Yscale: Optional[str] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, XycurveName):
            self.name = XycurveName(self.name)

        if self.npts is not None and not isinstance(self.npts, int):
            self.npts = int(self.npts)

        if self.Points is not None and not isinstance(self.Points, int):
            self.Points = int(self.Points)

        if self.Yarray is not None and not isinstance(self.Yarray, int):
            self.Yarray = int(self.Yarray)

        if self.Xarray is not None and not isinstance(self.Xarray, int):
            self.Xarray = int(self.Xarray)

        if self.csvfile is not None and not isinstance(self.csvfile, int):
            self.csvfile = int(self.csvfile)

        if self.sngfile is not None and not isinstance(self.sngfile, int):
            self.sngfile = int(self.sngfile)

        if self.dblfile is not None and not isinstance(self.dblfile, int):
            self.dblfile = int(self.dblfile)

        if self.x is not None and not isinstance(self.x, float):
            self.x = float(self.x)

        if self.y is not None and not isinstance(self.y, float):
            self.y = float(self.y)

        if self.Xshift is not None and not isinstance(self.Xshift, str):
            self.Xshift = str(self.Xshift)

        if self.Yshift is not None and not isinstance(self.Yshift, str):
            self.Yshift = str(self.Yshift)

        if self.Xscale is not None and not isinstance(self.Xscale, str):
            self.Xscale = str(self.Xscale)

        if self.Yscale is not None and not isinstance(self.Yscale, str):
            self.Yscale = str(self.Yscale)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Energymeter(YAMLRoot):
    """
    A Energymeter object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Energymeter"]
    class_class_curie: ClassVar[str] = "dss:Energymeter"
    class_name: ClassVar[str] = "Energymeter"
    class_model_uri: ClassVar[URIRef] = DSS.Energymeter

    name: Union[str, EnergymeterName] = None
    element: Optional[str] = None
    terminal: Optional[int] = None
    action: Optional[float] = None
    option: Optional[Union[str, list[str]]] = empty_list()
    kVAnormal: Optional[float] = None
    kVAemerg: Optional[float] = None
    peakcurrent: Optional[Union[float, list[float]]] = empty_list()
    Zonelist: Optional[Union[str, list[str]]] = empty_list()
    LocalOnly: Optional[Union[bool, Bool]] = None
    Mask: Optional[str] = None
    Losses: Optional[Union[bool, Bool]] = None
    LineLosses: Optional[Union[bool, Bool]] = None
    XfmrLosses: Optional[Union[bool, Bool]] = None
    SeqLosses: Optional[Union[bool, Bool]] = None
    three_phase_losses: Optional[Union[bool, Bool]] = None
    VbaseLosses: Optional[Union[bool, Bool]] = None
    PhaseVoltageReport: Optional[Union[bool, Bool]] = None
    Int_Rate: Optional[int] = None
    Int_Duration: Optional[str] = None
    SAIFI: Optional[str] = None
    SAIFIkW: Optional[float] = None
    SAIDI: Optional[str] = None
    CAIDI: Optional[str] = None
    CustInterrupts: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, EnergymeterName):
            self.name = EnergymeterName(self.name)

        if self.element is not None and not isinstance(self.element, str):
            self.element = str(self.element)

        if self.terminal is not None and not isinstance(self.terminal, int):
            self.terminal = int(self.terminal)

        if self.action is not None and not isinstance(self.action, float):
            self.action = float(self.action)

        if not isinstance(self.option, list):
            self.option = [self.option] if self.option is not None else []
        self.option = [v if isinstance(v, str) else str(v) for v in self.option]

        if self.kVAnormal is not None and not isinstance(self.kVAnormal, float):
            self.kVAnormal = float(self.kVAnormal)

        if self.kVAemerg is not None and not isinstance(self.kVAemerg, float):
            self.kVAemerg = float(self.kVAemerg)

        if not isinstance(self.peakcurrent, list):
            self.peakcurrent = [self.peakcurrent] if self.peakcurrent is not None else []
        self.peakcurrent = [v if isinstance(v, float) else float(v) for v in self.peakcurrent]

        if not isinstance(self.Zonelist, list):
            self.Zonelist = [self.Zonelist] if self.Zonelist is not None else []
        self.Zonelist = [v if isinstance(v, str) else str(v) for v in self.Zonelist]

        if self.LocalOnly is not None and not isinstance(self.LocalOnly, Bool):
            self.LocalOnly = Bool(self.LocalOnly)

        if self.Mask is not None and not isinstance(self.Mask, str):
            self.Mask = str(self.Mask)

        if self.Losses is not None and not isinstance(self.Losses, Bool):
            self.Losses = Bool(self.Losses)

        if self.LineLosses is not None and not isinstance(self.LineLosses, Bool):
            self.LineLosses = Bool(self.LineLosses)

        if self.XfmrLosses is not None and not isinstance(self.XfmrLosses, Bool):
            self.XfmrLosses = Bool(self.XfmrLosses)

        if self.SeqLosses is not None and not isinstance(self.SeqLosses, Bool):
            self.SeqLosses = Bool(self.SeqLosses)

        if self.three_phase_losses is not None and not isinstance(self.three_phase_losses, Bool):
            self.three_phase_losses = Bool(self.three_phase_losses)

        if self.VbaseLosses is not None and not isinstance(self.VbaseLosses, Bool):
            self.VbaseLosses = Bool(self.VbaseLosses)

        if self.PhaseVoltageReport is not None and not isinstance(self.PhaseVoltageReport, Bool):
            self.PhaseVoltageReport = Bool(self.PhaseVoltageReport)

        if self.Int_Rate is not None and not isinstance(self.Int_Rate, int):
            self.Int_Rate = int(self.Int_Rate)

        if self.Int_Duration is not None and not isinstance(self.Int_Duration, str):
            self.Int_Duration = str(self.Int_Duration)

        if self.SAIFI is not None and not isinstance(self.SAIFI, str):
            self.SAIFI = str(self.SAIFI)

        if self.SAIFIkW is not None and not isinstance(self.SAIFIkW, float):
            self.SAIFIkW = float(self.SAIFIkW)

        if self.SAIDI is not None and not isinstance(self.SAIDI, str):
            self.SAIDI = str(self.SAIDI)

        if self.CAIDI is not None and not isinstance(self.CAIDI, str):
            self.CAIDI = str(self.CAIDI)

        if self.CustInterrupts is not None and not isinstance(self.CustInterrupts, str):
            self.CustInterrupts = str(self.CustInterrupts)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Fmonitor(YAMLRoot):
    """
    A Fmonitor object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Fmonitor"]
    class_class_curie: ClassVar[str] = "dss:Fmonitor"
    class_name: ClassVar[str] = "Fmonitor"
    class_model_uri: ClassVar[URIRef] = DSS.Fmonitor

    name: Union[str, FmonitorName] = None
    element: Optional[str] = None
    terminal: Optional[int] = None
    mode: Optional[int] = None
    action: Optional[float] = None
    residual: Optional[Union[bool, Bool]] = None
    VIPolar: Optional[Union[bool, Bool]] = None
    PPolar: Optional[Union[bool, Bool]] = None
    P_trans_ref: Optional[float] = None
    V_Sensor: Optional[float] = None
    P_Sensor: Optional[float] = None
    Node_num: Optional[str] = None
    Cluster_num: Optional[str] = None
    Total_Clusters: Optional[int] = None
    Nodes: Optional[str] = None
    CommVector: Optional[int] = None
    ElemTableLine: Optional[int] = None
    P_Mode: Optional[float] = None
    CommDelayVector: Optional[int] = None
    T_intvl_smpl: Optional[str] = None
    MaxLocalMem: Optional[int] = None
    Volt_limits_pu: Optional[float] = None
    b_Curt_Ctrl: Optional[float] = None
    up_dly: Optional[str] = None
    virtual_ld_node: Optional[str] = None
    EGen: Optional[float] = None
    attack_defense: Optional[str] = None
    Comm_hide: Optional[str] = None
    Comm_node_hide: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, FmonitorName):
            self.name = FmonitorName(self.name)

        if self.element is not None and not isinstance(self.element, str):
            self.element = str(self.element)

        if self.terminal is not None and not isinstance(self.terminal, int):
            self.terminal = int(self.terminal)

        if self.mode is not None and not isinstance(self.mode, int):
            self.mode = int(self.mode)

        if self.action is not None and not isinstance(self.action, float):
            self.action = float(self.action)

        if self.residual is not None and not isinstance(self.residual, Bool):
            self.residual = Bool(self.residual)

        if self.VIPolar is not None and not isinstance(self.VIPolar, Bool):
            self.VIPolar = Bool(self.VIPolar)

        if self.PPolar is not None and not isinstance(self.PPolar, Bool):
            self.PPolar = Bool(self.PPolar)

        if self.P_trans_ref is not None and not isinstance(self.P_trans_ref, float):
            self.P_trans_ref = float(self.P_trans_ref)

        if self.V_Sensor is not None and not isinstance(self.V_Sensor, float):
            self.V_Sensor = float(self.V_Sensor)

        if self.P_Sensor is not None and not isinstance(self.P_Sensor, float):
            self.P_Sensor = float(self.P_Sensor)

        if self.Node_num is not None and not isinstance(self.Node_num, str):
            self.Node_num = str(self.Node_num)

        if self.Cluster_num is not None and not isinstance(self.Cluster_num, str):
            self.Cluster_num = str(self.Cluster_num)

        if self.Total_Clusters is not None and not isinstance(self.Total_Clusters, int):
            self.Total_Clusters = int(self.Total_Clusters)

        if self.Nodes is not None and not isinstance(self.Nodes, str):
            self.Nodes = str(self.Nodes)

        if self.CommVector is not None and not isinstance(self.CommVector, int):
            self.CommVector = int(self.CommVector)

        if self.ElemTableLine is not None and not isinstance(self.ElemTableLine, int):
            self.ElemTableLine = int(self.ElemTableLine)

        if self.P_Mode is not None and not isinstance(self.P_Mode, float):
            self.P_Mode = float(self.P_Mode)

        if self.CommDelayVector is not None and not isinstance(self.CommDelayVector, int):
            self.CommDelayVector = int(self.CommDelayVector)

        if self.T_intvl_smpl is not None and not isinstance(self.T_intvl_smpl, str):
            self.T_intvl_smpl = str(self.T_intvl_smpl)

        if self.MaxLocalMem is not None and not isinstance(self.MaxLocalMem, int):
            self.MaxLocalMem = int(self.MaxLocalMem)

        if self.Volt_limits_pu is not None and not isinstance(self.Volt_limits_pu, float):
            self.Volt_limits_pu = float(self.Volt_limits_pu)

        if self.b_Curt_Ctrl is not None and not isinstance(self.b_Curt_Ctrl, float):
            self.b_Curt_Ctrl = float(self.b_Curt_Ctrl)

        if self.up_dly is not None and not isinstance(self.up_dly, str):
            self.up_dly = str(self.up_dly)

        if self.virtual_ld_node is not None and not isinstance(self.virtual_ld_node, str):
            self.virtual_ld_node = str(self.virtual_ld_node)

        if self.EGen is not None and not isinstance(self.EGen, float):
            self.EGen = float(self.EGen)

        if self.attack_defense is not None and not isinstance(self.attack_defense, str):
            self.attack_defense = str(self.attack_defense)

        if self.Comm_hide is not None and not isinstance(self.Comm_hide, str):
            self.Comm_hide = str(self.Comm_hide)

        if self.Comm_node_hide is not None and not isinstance(self.Comm_node_hide, str):
            self.Comm_node_hide = str(self.Comm_node_hide)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Monitor(YAMLRoot):
    """
    A Monitor object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Monitor"]
    class_class_curie: ClassVar[str] = "dss:Monitor"
    class_name: ClassVar[str] = "Monitor"
    class_model_uri: ClassVar[URIRef] = DSS.Monitor

    name: Union[str, MonitorName] = None
    element: Optional[str] = None
    terminal: Optional[int] = None
    mode: Optional[int] = None
    action: Optional[float] = None
    residual: Optional[Union[bool, Bool]] = None
    VIPolar: Optional[Union[bool, Bool]] = None
    PPolar: Optional[Union[bool, Bool]] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, MonitorName):
            self.name = MonitorName(self.name)

        if self.element is not None and not isinstance(self.element, str):
            self.element = str(self.element)

        if self.terminal is not None and not isinstance(self.terminal, int):
            self.terminal = int(self.terminal)

        if self.mode is not None and not isinstance(self.mode, int):
            self.mode = int(self.mode)

        if self.action is not None and not isinstance(self.action, float):
            self.action = float(self.action)

        if self.residual is not None and not isinstance(self.residual, Bool):
            self.residual = Bool(self.residual)

        if self.VIPolar is not None and not isinstance(self.VIPolar, Bool):
            self.VIPolar = Bool(self.VIPolar)

        if self.PPolar is not None and not isinstance(self.PPolar, Bool):
            self.PPolar = Bool(self.PPolar)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Sensor(YAMLRoot):
    """
    A Sensor object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Sensor"]
    class_class_curie: ClassVar[str] = "dss:Sensor"
    class_name: ClassVar[str] = "Sensor"
    class_model_uri: ClassVar[URIRef] = DSS.Sensor

    name: Union[str, SensorName] = None
    element: Optional[str] = None
    terminal: Optional[int] = None
    kvbase: Optional[float] = None
    clear: Optional[Union[bool, Bool]] = None
    kVs: Optional[Union[float, list[float]]] = empty_list()
    currents: Optional[Union[float, list[float]]] = empty_list()
    kWs: Optional[Union[float, list[float]]] = empty_list()
    kvars: Optional[Union[float, list[float]]] = empty_list()
    conn: Optional[float] = None
    Deltadirection: Optional[str] = None
    pct_Error: Optional[float] = None
    Weight: Optional[str] = None
    action: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, SensorName):
            self.name = SensorName(self.name)

        if self.element is not None and not isinstance(self.element, str):
            self.element = str(self.element)

        if self.terminal is not None and not isinstance(self.terminal, int):
            self.terminal = int(self.terminal)

        if self.kvbase is not None and not isinstance(self.kvbase, float):
            self.kvbase = float(self.kvbase)

        if self.clear is not None and not isinstance(self.clear, Bool):
            self.clear = Bool(self.clear)

        if not isinstance(self.kVs, list):
            self.kVs = [self.kVs] if self.kVs is not None else []
        self.kVs = [v if isinstance(v, float) else float(v) for v in self.kVs]

        if not isinstance(self.currents, list):
            self.currents = [self.currents] if self.currents is not None else []
        self.currents = [v if isinstance(v, float) else float(v) for v in self.currents]

        if not isinstance(self.kWs, list):
            self.kWs = [self.kWs] if self.kWs is not None else []
        self.kWs = [v if isinstance(v, float) else float(v) for v in self.kWs]

        if not isinstance(self.kvars, list):
            self.kvars = [self.kvars] if self.kvars is not None else []
        self.kvars = [v if isinstance(v, float) else float(v) for v in self.kvars]

        if self.conn is not None and not isinstance(self.conn, float):
            self.conn = float(self.conn)

        if self.Deltadirection is not None and not isinstance(self.Deltadirection, str):
            self.Deltadirection = str(self.Deltadirection)

        if self.pct_Error is not None and not isinstance(self.pct_Error, float):
            self.pct_Error = float(self.pct_Error)

        if self.Weight is not None and not isinstance(self.Weight, str):
            self.Weight = str(self.Weight)

        if self.action is not None and not isinstance(self.action, str):
            self.action = str(self.action)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Fault(YAMLRoot):
    """
    A Fault object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Fault"]
    class_class_curie: ClassVar[str] = "dss:Fault"
    class_name: ClassVar[str] = "Fault"
    class_model_uri: ClassVar[URIRef] = DSS.Fault

    name: Union[str, FaultName] = None
    bus1: Optional[str] = None
    bus2: Optional[str] = None
    phases: Optional[int] = None
    r: Optional[float] = None
    pct_stddev: Optional[float] = None
    Gmatrix: Optional[float] = None
    ONtime: Optional[str] = None
    temporary: Optional[Union[bool, Bool]] = None
    MinAmps: Optional[str] = None
    normamps: Optional[float] = None
    emergamps: Optional[float] = None
    faultrate: Optional[str] = None
    pctperm: Optional[float] = None
    repair: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, FaultName):
            self.name = FaultName(self.name)

        if self.bus1 is not None and not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.bus2 is not None and not isinstance(self.bus2, str):
            self.bus2 = str(self.bus2)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.r is not None and not isinstance(self.r, float):
            self.r = float(self.r)

        if self.pct_stddev is not None and not isinstance(self.pct_stddev, float):
            self.pct_stddev = float(self.pct_stddev)

        if self.Gmatrix is not None and not isinstance(self.Gmatrix, float):
            self.Gmatrix = float(self.Gmatrix)

        if self.ONtime is not None and not isinstance(self.ONtime, str):
            self.ONtime = str(self.ONtime)

        if self.temporary is not None and not isinstance(self.temporary, Bool):
            self.temporary = Bool(self.temporary)

        if self.MinAmps is not None and not isinstance(self.MinAmps, str):
            self.MinAmps = str(self.MinAmps)

        if self.normamps is not None and not isinstance(self.normamps, float):
            self.normamps = float(self.normamps)

        if self.emergamps is not None and not isinstance(self.emergamps, float):
            self.emergamps = float(self.emergamps)

        if self.faultrate is not None and not isinstance(self.faultrate, str):
            self.faultrate = str(self.faultrate)

        if self.pctperm is not None and not isinstance(self.pctperm, float):
            self.pctperm = float(self.pctperm)

        if self.repair is not None and not isinstance(self.repair, str):
            self.repair = str(self.repair)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Gicsource(YAMLRoot):
    """
    A Gicsource object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Gicsource"]
    class_class_curie: ClassVar[str] = "dss:Gicsource"
    class_name: ClassVar[str] = "Gicsource"
    class_model_uri: ClassVar[URIRef] = DSS.Gicsource

    name: Union[str, GicsourceName] = None
    Volts: Optional[float] = None
    angle: Optional[float] = None
    frequency: Optional[float] = None
    phases: Optional[int] = None
    EN: Optional[float] = None
    EE: Optional[float] = None
    Lat1: Optional[str] = None
    Lon1: Optional[str] = None
    Lat2: Optional[str] = None
    Lon2: Optional[str] = None
    spectrum: Optional[str] = None
    basefreq: Optional[str] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, GicsourceName):
            self.name = GicsourceName(self.name)

        if self.Volts is not None and not isinstance(self.Volts, float):
            self.Volts = float(self.Volts)

        if self.angle is not None and not isinstance(self.angle, float):
            self.angle = float(self.angle)

        if self.frequency is not None and not isinstance(self.frequency, float):
            self.frequency = float(self.frequency)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.EN is not None and not isinstance(self.EN, float):
            self.EN = float(self.EN)

        if self.EE is not None and not isinstance(self.EE, float):
            self.EE = float(self.EE)

        if self.Lat1 is not None and not isinstance(self.Lat1, str):
            self.Lat1 = str(self.Lat1)

        if self.Lon1 is not None and not isinstance(self.Lon1, str):
            self.Lon1 = str(self.Lon1)

        if self.Lat2 is not None and not isinstance(self.Lat2, str):
            self.Lat2 = str(self.Lat2)

        if self.Lon2 is not None and not isinstance(self.Lon2, str):
            self.Lon2 = str(self.Lon2)

        if self.spectrum is not None and not isinstance(self.spectrum, str):
            self.spectrum = str(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, str):
            self.basefreq = str(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Isource(YAMLRoot):
    """
    A Isource object in OpenDSS.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Isource"]
    class_class_curie: ClassVar[str] = "dss:Isource"
    class_name: ClassVar[str] = "Isource"
    class_model_uri: ClassVar[URIRef] = DSS.Isource

    name: Union[str, IsourceName] = None
    bus1: Optional[str] = None
    amps: Optional[float] = None
    angle: Optional[int] = None
    frequency: Optional[str] = None
    phases: Optional[int] = None
    scantype: Optional[float] = None
    sequence: Optional[float] = None
    Yearly: Optional[float] = None
    Daily: Optional[float] = None
    Duty: Optional[float] = None
    Bus2: Optional[str] = None
    spectrum: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, IsourceName):
            self.name = IsourceName(self.name)

        if self.bus1 is not None and not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.amps is not None and not isinstance(self.amps, float):
            self.amps = float(self.amps)

        if self.angle is not None and not isinstance(self.angle, int):
            self.angle = int(self.angle)

        if self.frequency is not None and not isinstance(self.frequency, str):
            self.frequency = str(self.frequency)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.scantype is not None and not isinstance(self.scantype, float):
            self.scantype = float(self.scantype)

        if self.sequence is not None and not isinstance(self.sequence, float):
            self.sequence = float(self.sequence)

        if self.Yearly is not None and not isinstance(self.Yearly, float):
            self.Yearly = float(self.Yearly)

        if self.Daily is not None and not isinstance(self.Daily, float):
            self.Daily = float(self.Daily)

        if self.Duty is not None and not isinstance(self.Duty, float):
            self.Duty = float(self.Duty)

        if self.Bus2 is not None and not isinstance(self.Bus2, str):
            self.Bus2 = str(self.Bus2)

        if self.spectrum is not None and not isinstance(self.spectrum, str):
            self.spectrum = str(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Options(YAMLRoot):
    """
    The circuit name and the kept ``Set`` options of one deck (``Set voltagebases=[...]``, ``Set defaultbasefreq=50``,
    ``Set earthmodel=carson``).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Options"]
    class_class_curie: ClassVar[str] = "dss:Options"
    class_name: ClassVar[str] = "Options"
    class_model_uri: ClassVar[URIRef] = DSS.Options

    name: Union[str, OptionsName] = None
    circuit: Optional[str] = None
    open_terminals: Optional[Union[str, list[str]]] = empty_list()
    voltagebases: Optional[Union[float, list[float]]] = empty_list()
    defaultbasefreq: Optional[float] = None
    earthmodel: Optional[Union[str, "EarthModelType"]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, OptionsName):
            self.name = OptionsName(self.name)

        if self.circuit is not None and not isinstance(self.circuit, str):
            self.circuit = str(self.circuit)

        if not isinstance(self.open_terminals, list):
            self.open_terminals = [self.open_terminals] if self.open_terminals is not None else []
        self.open_terminals = [v if isinstance(v, str) else str(v) for v in self.open_terminals]

        if not isinstance(self.voltagebases, list):
            self.voltagebases = [self.voltagebases] if self.voltagebases is not None else []
        self.voltagebases = [v if isinstance(v, float) else float(v) for v in self.voltagebases]

        if self.defaultbasefreq is not None and not isinstance(self.defaultbasefreq, float):
            self.defaultbasefreq = float(self.defaultbasefreq)

        if self.earthmodel is not None and not isinstance(self.earthmodel, EarthModelType):
            self.earthmodel = EarthModelType(self.earthmodel)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Vsource(YAMLRoot):
    """
    A Vsource object in OpenDSS representing an ideal voltage source (slack bus) in the distribution system. Used to
    represent the transmission-system equivalent or a substation source.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DSS["Vsource"]
    class_class_curie: ClassVar[str] = "dss:Vsource"
    class_name: ClassVar[str] = "Vsource"
    class_model_uri: ClassVar[URIRef] = DSS.Vsource

    name: Union[str, VsourceName] = None
    bus1: Optional[str] = None
    basekv: Optional[float] = None
    pu: Optional[float] = None
    angle: Optional[float] = None
    frequency: Optional[float] = None
    phases: Optional[int] = None
    MVAsc3: Optional[float] = None
    MVAsc1: Optional[float] = None
    x1r1: Optional[float] = None
    x0r0: Optional[float] = None
    Isc3: Optional[float] = None
    Isc1: Optional[float] = None
    R1: Optional[float] = None
    X1: Optional[float] = None
    R0: Optional[float] = None
    X0: Optional[float] = None
    ScanType: Optional[str] = None
    Sequence: Optional[str] = None
    bus2: Optional[str] = None
    Z1: Optional[Union[float, list[float]]] = empty_list()
    Z0: Optional[Union[float, list[float]]] = empty_list()
    Z2: Optional[Union[float, list[float]]] = empty_list()
    puZ1: Optional[Union[float, list[float]]] = empty_list()
    puZ0: Optional[Union[float, list[float]]] = empty_list()
    puZ2: Optional[Union[float, list[float]]] = empty_list()
    baseMVA: Optional[float] = None
    Yearly: Optional[str] = None
    Daily: Optional[str] = None
    Duty: Optional[str] = None
    Model: Optional[str] = None
    puZideal: Optional[float] = None
    spectrum: Optional[str] = None
    basefreq: Optional[float] = None
    enabled: Optional[Union[bool, Bool]] = None
    like: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.name):
            self.MissingRequiredField("name")
        if not isinstance(self.name, VsourceName):
            self.name = VsourceName(self.name)

        if self.bus1 is not None and not isinstance(self.bus1, str):
            self.bus1 = str(self.bus1)

        if self.basekv is not None and not isinstance(self.basekv, float):
            self.basekv = float(self.basekv)

        if self.pu is not None and not isinstance(self.pu, float):
            self.pu = float(self.pu)

        if self.angle is not None and not isinstance(self.angle, float):
            self.angle = float(self.angle)

        if self.frequency is not None and not isinstance(self.frequency, float):
            self.frequency = float(self.frequency)

        if self.phases is not None and not isinstance(self.phases, int):
            self.phases = int(self.phases)

        if self.MVAsc3 is not None and not isinstance(self.MVAsc3, float):
            self.MVAsc3 = float(self.MVAsc3)

        if self.MVAsc1 is not None and not isinstance(self.MVAsc1, float):
            self.MVAsc1 = float(self.MVAsc1)

        if self.x1r1 is not None and not isinstance(self.x1r1, float):
            self.x1r1 = float(self.x1r1)

        if self.x0r0 is not None and not isinstance(self.x0r0, float):
            self.x0r0 = float(self.x0r0)

        if self.Isc3 is not None and not isinstance(self.Isc3, float):
            self.Isc3 = float(self.Isc3)

        if self.Isc1 is not None and not isinstance(self.Isc1, float):
            self.Isc1 = float(self.Isc1)

        if self.R1 is not None and not isinstance(self.R1, float):
            self.R1 = float(self.R1)

        if self.X1 is not None and not isinstance(self.X1, float):
            self.X1 = float(self.X1)

        if self.R0 is not None and not isinstance(self.R0, float):
            self.R0 = float(self.R0)

        if self.X0 is not None and not isinstance(self.X0, float):
            self.X0 = float(self.X0)

        if self.ScanType is not None and not isinstance(self.ScanType, str):
            self.ScanType = str(self.ScanType)

        if self.Sequence is not None and not isinstance(self.Sequence, str):
            self.Sequence = str(self.Sequence)

        if self.bus2 is not None and not isinstance(self.bus2, str):
            self.bus2 = str(self.bus2)

        if not isinstance(self.Z1, list):
            self.Z1 = [self.Z1] if self.Z1 is not None else []
        self.Z1 = [v if isinstance(v, float) else float(v) for v in self.Z1]

        if not isinstance(self.Z0, list):
            self.Z0 = [self.Z0] if self.Z0 is not None else []
        self.Z0 = [v if isinstance(v, float) else float(v) for v in self.Z0]

        if not isinstance(self.Z2, list):
            self.Z2 = [self.Z2] if self.Z2 is not None else []
        self.Z2 = [v if isinstance(v, float) else float(v) for v in self.Z2]

        if not isinstance(self.puZ1, list):
            self.puZ1 = [self.puZ1] if self.puZ1 is not None else []
        self.puZ1 = [v if isinstance(v, float) else float(v) for v in self.puZ1]

        if not isinstance(self.puZ0, list):
            self.puZ0 = [self.puZ0] if self.puZ0 is not None else []
        self.puZ0 = [v if isinstance(v, float) else float(v) for v in self.puZ0]

        if not isinstance(self.puZ2, list):
            self.puZ2 = [self.puZ2] if self.puZ2 is not None else []
        self.puZ2 = [v if isinstance(v, float) else float(v) for v in self.puZ2]

        if self.baseMVA is not None and not isinstance(self.baseMVA, float):
            self.baseMVA = float(self.baseMVA)

        if self.Yearly is not None and not isinstance(self.Yearly, str):
            self.Yearly = str(self.Yearly)

        if self.Daily is not None and not isinstance(self.Daily, str):
            self.Daily = str(self.Daily)

        if self.Duty is not None and not isinstance(self.Duty, str):
            self.Duty = str(self.Duty)

        if self.Model is not None and not isinstance(self.Model, str):
            self.Model = str(self.Model)

        if self.puZideal is not None and not isinstance(self.puZideal, float):
            self.puZideal = float(self.puZideal)

        if self.spectrum is not None and not isinstance(self.spectrum, str):
            self.spectrum = str(self.spectrum)

        if self.basefreq is not None and not isinstance(self.basefreq, float):
            self.basefreq = float(self.basefreq)

        if self.enabled is not None and not isinstance(self.enabled, Bool):
            self.enabled = Bool(self.enabled)

        if self.like is not None and not isinstance(self.like, str):
            self.like = str(self.like)

        super().__post_init__(**kwargs)


# Enumerations
class ConnectionType(EnumDefinitionImpl):
    """
    Electrical connection topology
    """
    wye = PermissibleValue(
        text="wye",
        description="Wye (star) connection",
        meaning=CIM["WindingConnection.Y"])
    delta = PermissibleValue(
        text="delta",
        description="Delta connection",
        meaning=CIM["WindingConnection.D"])

    _defn = EnumDefinition(
        name="ConnectionType",
        description="Electrical connection topology",
    )

class GeneratorModel(EnumDefinitionImpl):
    """
    Integer code for generation variation model with voltage.
    """
    ConstantPQ = PermissibleValue(
        text="ConstantPQ",
        description="1: Generator injects constant kW at specified power factor",
        meaning=DSS["GeneratorModel.1"])
    ConstantZ = PermissibleValue(
        text="ConstantZ",
        description="2: Generator is modeled as constant admittance",
        meaning=DSS["GeneratorModel.2"])
    ConstantPV = PermissibleValue(
        text="ConstantPV",
        description="3: Const kW, constant kV (like transmission P-V generator)",
        meaning=DSS["GeneratorModel.3"])
    ConstantPFixedQ = PermissibleValue(
        text="ConstantPFixedQ",
        description="4: Const kW, Fixed Q (Q never varies)",
        meaning=DSS["GeneratorModel.4"])
    ConstantPFixedQX = PermissibleValue(
        text="ConstantPFixedQX",
        description="5: Const kW, Fixed Q as constant reactance",
        meaning=DSS["GeneratorModel.5"])
    UserModel = PermissibleValue(
        text="UserModel",
        description="6: Compute load injection from User-written Model",
        meaning=DSS["GeneratorModel.6"])
    CurrentLimited = PermissibleValue(
        text="CurrentLimited",
        description="7: Constant kW, kvar, but current-limited below Vminpu",
        meaning=DSS["GeneratorModel.7"])

    _defn = EnumDefinition(
        name="GeneratorModel",
        description="Integer code for generation variation model with voltage.",
    )

class DispatchMode(EnumDefinitionImpl):
    """
    Generator dispatch mode
    """
    Default = PermissibleValue(
        text="Default",
        description="Generator is either always on or follows dispatch curve")
    Loadlevel = PermissibleValue(
        text="Loadlevel",
        description="Generator comes on when load level exceeds dispatch value")
    Price = PermissibleValue(
        text="Price",
        description="Generator comes on when price exceeds dispatch value")

    _defn = EnumDefinition(
        name="DispatchMode",
        description="Generator dispatch mode",
    )

class GenStatus(EnumDefinitionImpl):
    """
    Generator dispatch status
    """
    Fixed = PermissibleValue(
        text="Fixed",
        description="Dispatch multipliers do not apply, always at full power when ON")
    Variable = PermissibleValue(
        text="Variable",
        description="Follows dispatch curves")

    _defn = EnumDefinition(
        name="GenStatus",
        description="Generator dispatch status",
    )

class LoadModel(EnumDefinitionImpl):
    """
    Integer code for load variation model with voltage.
    """
    ConstantPQ = PermissibleValue(
        text="ConstantPQ",
        description="1: Standard constant P+jQ load (Default)",
        meaning=DSS["LoadModel.1"])
    ConstantZ = PermissibleValue(
        text="ConstantZ",
        description="2: Constant impedance load",
        meaning=DSS["LoadModel.2"])
    ConstantPQuadQ = PermissibleValue(
        text="ConstantPQuadQ",
        description="3: Const P, Quadratic Q (like a motor)",
        meaning=DSS["LoadModel.3"])
    CVR = PermissibleValue(
        text="CVR",
        description="4: Nominal Linear P, Quadratic Q (feeder mix, use with CVRfactor)",
        meaning=DSS["LoadModel.4"])
    ConstantI = PermissibleValue(
        text="ConstantI",
        description="5: Constant Current Magnitude",
        meaning=DSS["LoadModel.5"])
    ConstantPFixedQ = PermissibleValue(
        text="ConstantPFixedQ",
        description="6: Const P, Fixed Q",
        meaning=DSS["LoadModel.6"])
    ConstantPFixedZQ = PermissibleValue(
        text="ConstantPFixedZQ",
        description="7: Const P, Fixed Impedance Q",
        meaning=DSS["LoadModel.7"])
    ZIPV = PermissibleValue(
        text="ZIPV",
        description="8: ZIPV model (7 values)",
        meaning=DSS["LoadModel.8"])

    _defn = EnumDefinition(
        name="LoadModel",
        description="Integer code for load variation model with voltage.",
    )

class LoadStatus(EnumDefinitionImpl):
    """
    Load participation in multiplier adjustments
    """
    Variable = PermissibleValue(
        text="Variable",
        description="All multipliers apply")
    Fixed = PermissibleValue(
        text="Fixed",
        description="No load multipliers apply; growth multipliers still apply")
    Exempt = PermissibleValue(
        text="Exempt",
        description="Not modified by global load multiplier; daily multipliers still apply")

    _defn = EnumDefinition(
        name="LoadStatus",
        description="Load participation in multiplier adjustments",
    )

class LeadLagType(EnumDefinitionImpl):
    """
    Phase shift designation for Delta-Wye connections
    """
    Lead = PermissibleValue(
        text="Lead",
        description="Lead phase shift")
    Lag = PermissibleValue(
        text="Lag",
        description="Lag phase shift (default)")
    ANSI = PermissibleValue(
        text="ANSI",
        description="ANSI 30 deg lag (same as Lag)")
    Euro = PermissibleValue(
        text="Euro",
        description="European Dy11 connection (same as Lead)")

    _defn = EnumDefinition(
        name="LeadLagType",
        description="Phase shift designation for Delta-Wye connections",
    )

class CoreType(EnumDefinitionImpl):
    """
    Transformer core type for GIC analysis
    """
    Shell = PermissibleValue(
        text="Shell",
        description="Shell core (default)")

    _defn = EnumDefinition(
        name="CoreType",
        description="Transformer core type for GIC analysis",
    )

    @classmethod
    def _addvals(cls):
        setattr(cls, "5-leg",
            PermissibleValue(
                text="5-leg",
                description="5-leg core"))
        setattr(cls, "3-Leg",
            PermissibleValue(
                text="3-Leg",
                description="3-leg core"))
        setattr(cls, "1-phase",
            PermissibleValue(
                text="1-phase",
                description="Single-phase core"))
        setattr(cls, "core-1-phase",
            PermissibleValue(
                text="core-1-phase",
                description="Core-type single-phase"))
        setattr(cls, "4-leg",
            PermissibleValue(
                text="4-leg",
                description="4-leg core"))

class LengthUnit(EnumDefinitionImpl):
    """
    Units of length measurement
    """
    none = PermissibleValue(
        text="none",
        description="No units specified - assumes length units match impedance units")
    mi = PermissibleValue(
        text="mi",
        description="Miles")
    kft = PermissibleValue(
        text="kft",
        description="Kilofeet")
    km = PermissibleValue(
        text="km",
        description="Kilometers")
    m = PermissibleValue(
        text="m",
        description="Meters")
    Ft = PermissibleValue(
        text="Ft",
        description="Feet")
    cm = PermissibleValue(
        text="cm",
        description="Centimeters")

    _defn = EnumDefinition(
        name="LengthUnit",
        description="Units of length measurement",
    )

    @classmethod
    def _addvals(cls):
        setattr(cls, "in",
            PermissibleValue(
                text="in",
                description="Inches"))

class EarthModelType(EnumDefinitionImpl):
    """
    Earth model for impedance calculations
    """
    Carson = PermissibleValue(
        text="Carson",
        description="Carson earth model")
    FullCarson = PermissibleValue(
        text="FullCarson",
        description="Full Carson earth model")
    Deri = PermissibleValue(
        text="Deri",
        description="Deri earth model")

    _defn = EnumDefinition(
        name="EarthModelType",
        description="Earth model for impedance calculations",
    )

class LineTypeCode(EnumDefinitionImpl):
    """
    Code designating the type of line
    """
    OH = PermissibleValue(
        text="OH",
        description="Overhead line (default)")
    UG = PermissibleValue(
        text="UG",
        description="Underground")
    UG_TS = PermissibleValue(
        text="UG_TS",
        description="Underground tape shield")
    UG_CN = PermissibleValue(
        text="UG_CN",
        description="Underground concentric neutral")
    SWT_LDBRK = PermissibleValue(
        text="SWT_LDBRK",
        description="Switch load break")
    SWT_FUSE = PermissibleValue(
        text="SWT_FUSE",
        description="Switch fuse")
    SWT_SECT = PermissibleValue(
        text="SWT_SECT",
        description="Switch sectionalizer")
    SWT_REC = PermissibleValue(
        text="SWT_REC",
        description="Switch recloser")
    SWT_DISC = PermissibleValue(
        text="SWT_DISC",
        description="Switch disconnect")
    SWT_BRK = PermissibleValue(
        text="SWT_BRK",
        description="Switch breaker")
    SWT_ELBOW = PermissibleValue(
        text="SWT_ELBOW",
        description="Switch elbow")
    BUSBAR = PermissibleValue(
        text="BUSBAR",
        description="Busbar")

    _defn = EnumDefinition(
        name="LineTypeCode",
        description="Code designating the type of line",
    )

class SwitchState(EnumDefinitionImpl):
    """
    Discrete state of switchable capacitor step
    """
    _defn = EnumDefinition(
        name="SwitchState",
        description="Discrete state of switchable capacitor step",
    )

    @classmethod
    def _addvals(cls):
        setattr(cls, "True",
            PermissibleValue(
                text="True",
                description="Capacitor step energized"))
        setattr(cls, "False",
            PermissibleValue(
                text="False",
                description="Capacitor step de-energized"))

# Slots
class slots:
    pass

slots.load__name = Slot(uri=DSS.name, name="load__name", curie=DSS.curie('name'),
                   model_uri=DSS.load__name, domain=None, range=URIRef)

slots.load__phases = Slot(uri=DSS.phases, name="load__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.load__phases, domain=None, range=Optional[int])

slots.load__bus1 = Slot(uri=DSS.bus1, name="load__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.load__bus1, domain=None, range=str)

slots.load__kV = Slot(uri=DSS.kV, name="load__kV", curie=DSS.curie('kV'),
                   model_uri=DSS.load__kV, domain=None, range=Optional[float])

slots.load__kW = Slot(uri=DSS.kW, name="load__kW", curie=DSS.curie('kW'),
                   model_uri=DSS.load__kW, domain=None, range=Optional[float])

slots.load__pf = Slot(uri=DSS.pf, name="load__pf", curie=DSS.curie('pf'),
                   model_uri=DSS.load__pf, domain=None, range=Optional[float])

slots.load__model = Slot(uri=DSS.model, name="load__model", curie=DSS.curie('model'),
                   model_uri=DSS.load__model, domain=None, range=Optional[Union[str, "LoadModel"]])

slots.load__yearly = Slot(uri=DSS.yearly, name="load__yearly", curie=DSS.curie('yearly'),
                   model_uri=DSS.load__yearly, domain=None, range=Optional[str])

slots.load__daily = Slot(uri=DSS.daily, name="load__daily", curie=DSS.curie('daily'),
                   model_uri=DSS.load__daily, domain=None, range=Optional[str])

slots.load__duty = Slot(uri=DSS.duty, name="load__duty", curie=DSS.curie('duty'),
                   model_uri=DSS.load__duty, domain=None, range=Optional[str])

slots.load__growth = Slot(uri=DSS.growth, name="load__growth", curie=DSS.curie('growth'),
                   model_uri=DSS.load__growth, domain=None, range=Optional[str])

slots.load__conn = Slot(uri=DSS.conn, name="load__conn", curie=DSS.curie('conn'),
                   model_uri=DSS.load__conn, domain=None, range=Optional[Union[str, "ConnectionType"]])

slots.load__kvar = Slot(uri=DSS.kvar, name="load__kvar", curie=DSS.curie('kvar'),
                   model_uri=DSS.load__kvar, domain=None, range=Optional[float])

slots.load__Rneut = Slot(uri=DSS.Rneut, name="load__Rneut", curie=DSS.curie('Rneut'),
                   model_uri=DSS.load__Rneut, domain=None, range=Optional[float])

slots.load__Xneut = Slot(uri=DSS.Xneut, name="load__Xneut", curie=DSS.curie('Xneut'),
                   model_uri=DSS.load__Xneut, domain=None, range=Optional[float])

slots.load__status = Slot(uri=DSS.status, name="load__status", curie=DSS.curie('status'),
                   model_uri=DSS.load__status, domain=None, range=Optional[Union[str, "LoadStatus"]])

slots.load__load_class = Slot(uri=DSS.load_class, name="load__load_class", curie=DSS.curie('load_class'),
                   model_uri=DSS.load__load_class, domain=None, range=Optional[int])

slots.load__Vminpu = Slot(uri=DSS.Vminpu, name="load__Vminpu", curie=DSS.curie('Vminpu'),
                   model_uri=DSS.load__Vminpu, domain=None, range=Optional[float])

slots.load__Vmaxpu = Slot(uri=DSS.Vmaxpu, name="load__Vmaxpu", curie=DSS.curie('Vmaxpu'),
                   model_uri=DSS.load__Vmaxpu, domain=None, range=Optional[float])

slots.load__Vminnorm = Slot(uri=DSS.Vminnorm, name="load__Vminnorm", curie=DSS.curie('Vminnorm'),
                   model_uri=DSS.load__Vminnorm, domain=None, range=Optional[float])

slots.load__Vminemerg = Slot(uri=DSS.Vminemerg, name="load__Vminemerg", curie=DSS.curie('Vminemerg'),
                   model_uri=DSS.load__Vminemerg, domain=None, range=Optional[float])

slots.load__xfkVA = Slot(uri=DSS.xfkVA, name="load__xfkVA", curie=DSS.curie('xfkVA'),
                   model_uri=DSS.load__xfkVA, domain=None, range=Optional[float])

slots.load__allocationfactor = Slot(uri=DSS.allocationfactor, name="load__allocationfactor", curie=DSS.curie('allocationfactor'),
                   model_uri=DSS.load__allocationfactor, domain=None, range=Optional[float])

slots.load__kVA = Slot(uri=DSS.kVA, name="load__kVA", curie=DSS.curie('kVA'),
                   model_uri=DSS.load__kVA, domain=None, range=Optional[float])

slots.load__pct_mean = Slot(uri=DSS.pct_mean, name="load__pct_mean", curie=DSS.curie('pct_mean'),
                   model_uri=DSS.load__pct_mean, domain=None, range=Optional[float])

slots.load__pct_stddev = Slot(uri=DSS.pct_stddev, name="load__pct_stddev", curie=DSS.curie('pct_stddev'),
                   model_uri=DSS.load__pct_stddev, domain=None, range=Optional[float])

slots.load__CVRwatts = Slot(uri=DSS.CVRwatts, name="load__CVRwatts", curie=DSS.curie('CVRwatts'),
                   model_uri=DSS.load__CVRwatts, domain=None, range=Optional[float])

slots.load__CVRvars = Slot(uri=DSS.CVRvars, name="load__CVRvars", curie=DSS.curie('CVRvars'),
                   model_uri=DSS.load__CVRvars, domain=None, range=Optional[float])

slots.load__kwh = Slot(uri=DSS.kwh, name="load__kwh", curie=DSS.curie('kwh'),
                   model_uri=DSS.load__kwh, domain=None, range=Optional[float])

slots.load__kwhdays = Slot(uri=DSS.kwhdays, name="load__kwhdays", curie=DSS.curie('kwhdays'),
                   model_uri=DSS.load__kwhdays, domain=None, range=Optional[float])

slots.load__Cfactor = Slot(uri=DSS.Cfactor, name="load__Cfactor", curie=DSS.curie('Cfactor'),
                   model_uri=DSS.load__Cfactor, domain=None, range=Optional[float])

slots.load__CVRcurve = Slot(uri=DSS.CVRcurve, name="load__CVRcurve", curie=DSS.curie('CVRcurve'),
                   model_uri=DSS.load__CVRcurve, domain=None, range=Optional[str])

slots.load__NumCust = Slot(uri=DSS.NumCust, name="load__NumCust", curie=DSS.curie('NumCust'),
                   model_uri=DSS.load__NumCust, domain=None, range=Optional[int])

slots.load__ZIPV = Slot(uri=DSS.ZIPV, name="load__ZIPV", curie=DSS.curie('ZIPV'),
                   model_uri=DSS.load__ZIPV, domain=None, range=Optional[Union[float, list[float]]])

slots.load__pct_SeriesRL = Slot(uri=DSS.pct_SeriesRL, name="load__pct_SeriesRL", curie=DSS.curie('pct_SeriesRL'),
                   model_uri=DSS.load__pct_SeriesRL, domain=None, range=Optional[float])

slots.load__RelWeight = Slot(uri=DSS.RelWeight, name="load__RelWeight", curie=DSS.curie('RelWeight'),
                   model_uri=DSS.load__RelWeight, domain=None, range=Optional[float])

slots.load__Vlowpu = Slot(uri=DSS.Vlowpu, name="load__Vlowpu", curie=DSS.curie('Vlowpu'),
                   model_uri=DSS.load__Vlowpu, domain=None, range=Optional[float])

slots.load__puXharm = Slot(uri=DSS.puXharm, name="load__puXharm", curie=DSS.curie('puXharm'),
                   model_uri=DSS.load__puXharm, domain=None, range=Optional[float])

slots.load__XRharm = Slot(uri=DSS.XRharm, name="load__XRharm", curie=DSS.curie('XRharm'),
                   model_uri=DSS.load__XRharm, domain=None, range=Optional[float])

slots.load__spectrum = Slot(uri=DSS.spectrum, name="load__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.load__spectrum, domain=None, range=Optional[str])

slots.load__basefreq = Slot(uri=DSS.basefreq, name="load__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.load__basefreq, domain=None, range=Optional[float])

slots.load__enabled = Slot(uri=DSS.enabled, name="load__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.load__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.load__like = Slot(uri=DSS.like, name="load__like", curie=DSS.curie('like'),
                   model_uri=DSS.load__like, domain=None, range=Optional[str])

slots.generator__name = Slot(uri=DSS.name, name="generator__name", curie=DSS.curie('name'),
                   model_uri=DSS.generator__name, domain=None, range=URIRef)

slots.generator__phases = Slot(uri=DSS.phases, name="generator__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.generator__phases, domain=None, range=Optional[int])

slots.generator__bus1 = Slot(uri=DSS.bus1, name="generator__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.generator__bus1, domain=None, range=Optional[str])

slots.generator__kv = Slot(uri=DSS.kv, name="generator__kv", curie=DSS.curie('kv'),
                   model_uri=DSS.generator__kv, domain=None, range=Optional[float])

slots.generator__kW = Slot(uri=DSS.kW, name="generator__kW", curie=DSS.curie('kW'),
                   model_uri=DSS.generator__kW, domain=None, range=Optional[float])

slots.generator__pf = Slot(uri=DSS.pf, name="generator__pf", curie=DSS.curie('pf'),
                   model_uri=DSS.generator__pf, domain=None, range=Optional[float])

slots.generator__kvar = Slot(uri=DSS.kvar, name="generator__kvar", curie=DSS.curie('kvar'),
                   model_uri=DSS.generator__kvar, domain=None, range=Optional[float])

slots.generator__model = Slot(uri=DSS.model, name="generator__model", curie=DSS.curie('model'),
                   model_uri=DSS.generator__model, domain=None, range=Optional[Union[str, "GeneratorModel"]])

slots.generator__Vminpu = Slot(uri=DSS.Vminpu, name="generator__Vminpu", curie=DSS.curie('Vminpu'),
                   model_uri=DSS.generator__Vminpu, domain=None, range=Optional[float])

slots.generator__Vmaxpu = Slot(uri=DSS.Vmaxpu, name="generator__Vmaxpu", curie=DSS.curie('Vmaxpu'),
                   model_uri=DSS.generator__Vmaxpu, domain=None, range=Optional[float])

slots.generator__yearly = Slot(uri=DSS.yearly, name="generator__yearly", curie=DSS.curie('yearly'),
                   model_uri=DSS.generator__yearly, domain=None, range=Optional[str])

slots.generator__daily = Slot(uri=DSS.daily, name="generator__daily", curie=DSS.curie('daily'),
                   model_uri=DSS.generator__daily, domain=None, range=Optional[str])

slots.generator__duty = Slot(uri=DSS.duty, name="generator__duty", curie=DSS.curie('duty'),
                   model_uri=DSS.generator__duty, domain=None, range=Optional[str])

slots.generator__dispmode = Slot(uri=DSS.dispmode, name="generator__dispmode", curie=DSS.curie('dispmode'),
                   model_uri=DSS.generator__dispmode, domain=None, range=Optional[Union[str, "DispatchMode"]])

slots.generator__dispvalue = Slot(uri=DSS.dispvalue, name="generator__dispvalue", curie=DSS.curie('dispvalue'),
                   model_uri=DSS.generator__dispvalue, domain=None, range=Optional[float])

slots.generator__conn = Slot(uri=DSS.conn, name="generator__conn", curie=DSS.curie('conn'),
                   model_uri=DSS.generator__conn, domain=None, range=Optional[Union[str, "ConnectionType"]])

slots.generator__status = Slot(uri=DSS.status, name="generator__status", curie=DSS.curie('status'),
                   model_uri=DSS.generator__status, domain=None, range=Optional[Union[str, "GenStatus"]])

slots.generator__gen_class = Slot(uri=DSS.gen_class, name="generator__gen_class", curie=DSS.curie('gen_class'),
                   model_uri=DSS.generator__gen_class, domain=None, range=Optional[int])

slots.generator__Vpu = Slot(uri=DSS.Vpu, name="generator__Vpu", curie=DSS.curie('Vpu'),
                   model_uri=DSS.generator__Vpu, domain=None, range=Optional[float])

slots.generator__maxkvar = Slot(uri=DSS.maxkvar, name="generator__maxkvar", curie=DSS.curie('maxkvar'),
                   model_uri=DSS.generator__maxkvar, domain=None, range=Optional[float])

slots.generator__minkvar = Slot(uri=DSS.minkvar, name="generator__minkvar", curie=DSS.curie('minkvar'),
                   model_uri=DSS.generator__minkvar, domain=None, range=Optional[float])

slots.generator__pvfactor = Slot(uri=DSS.pvfactor, name="generator__pvfactor", curie=DSS.curie('pvfactor'),
                   model_uri=DSS.generator__pvfactor, domain=None, range=Optional[float])

slots.generator__forceon = Slot(uri=DSS.forceon, name="generator__forceon", curie=DSS.curie('forceon'),
                   model_uri=DSS.generator__forceon, domain=None, range=Optional[Union[bool, Bool]])

slots.generator__kVA = Slot(uri=DSS.kVA, name="generator__kVA", curie=DSS.curie('kVA'),
                   model_uri=DSS.generator__kVA, domain=None, range=Optional[float])

slots.generator__MVA = Slot(uri=DSS.MVA, name="generator__MVA", curie=DSS.curie('MVA'),
                   model_uri=DSS.generator__MVA, domain=None, range=Optional[float])

slots.generator__Xd = Slot(uri=DSS.Xd, name="generator__Xd", curie=DSS.curie('Xd'),
                   model_uri=DSS.generator__Xd, domain=None, range=Optional[float])

slots.generator__Xdp = Slot(uri=DSS.Xdp, name="generator__Xdp", curie=DSS.curie('Xdp'),
                   model_uri=DSS.generator__Xdp, domain=None, range=Optional[float])

slots.generator__Xdpp = Slot(uri=DSS.Xdpp, name="generator__Xdpp", curie=DSS.curie('Xdpp'),
                   model_uri=DSS.generator__Xdpp, domain=None, range=Optional[float])

slots.generator__H = Slot(uri=DSS.H, name="generator__H", curie=DSS.curie('H'),
                   model_uri=DSS.generator__H, domain=None, range=Optional[float])

slots.generator__D = Slot(uri=DSS.D, name="generator__D", curie=DSS.curie('D'),
                   model_uri=DSS.generator__D, domain=None, range=Optional[float])

slots.generator__UserModel = Slot(uri=DSS.UserModel, name="generator__UserModel", curie=DSS.curie('UserModel'),
                   model_uri=DSS.generator__UserModel, domain=None, range=Optional[str])

slots.generator__UserData = Slot(uri=DSS.UserData, name="generator__UserData", curie=DSS.curie('UserData'),
                   model_uri=DSS.generator__UserData, domain=None, range=Optional[str])

slots.generator__ShaftModel = Slot(uri=DSS.ShaftModel, name="generator__ShaftModel", curie=DSS.curie('ShaftModel'),
                   model_uri=DSS.generator__ShaftModel, domain=None, range=Optional[str])

slots.generator__ShaftData = Slot(uri=DSS.ShaftData, name="generator__ShaftData", curie=DSS.curie('ShaftData'),
                   model_uri=DSS.generator__ShaftData, domain=None, range=Optional[str])

slots.generator__DutyStart = Slot(uri=DSS.DutyStart, name="generator__DutyStart", curie=DSS.curie('DutyStart'),
                   model_uri=DSS.generator__DutyStart, domain=None, range=Optional[float])

slots.generator__debugtrace = Slot(uri=DSS.debugtrace, name="generator__debugtrace", curie=DSS.curie('debugtrace'),
                   model_uri=DSS.generator__debugtrace, domain=None, range=Optional[Union[bool, Bool]])

slots.generator__Balanced = Slot(uri=DSS.Balanced, name="generator__Balanced", curie=DSS.curie('Balanced'),
                   model_uri=DSS.generator__Balanced, domain=None, range=Optional[Union[bool, Bool]])

slots.generator__XRdp = Slot(uri=DSS.XRdp, name="generator__XRdp", curie=DSS.curie('XRdp'),
                   model_uri=DSS.generator__XRdp, domain=None, range=Optional[float])

slots.generator__UseFuel = Slot(uri=DSS.UseFuel, name="generator__UseFuel", curie=DSS.curie('UseFuel'),
                   model_uri=DSS.generator__UseFuel, domain=None, range=Optional[Union[bool, Bool]])

slots.generator__FuelkWh = Slot(uri=DSS.FuelkWh, name="generator__FuelkWh", curie=DSS.curie('FuelkWh'),
                   model_uri=DSS.generator__FuelkWh, domain=None, range=Optional[float])

slots.generator__pct_Fuel = Slot(uri=DSS.pct_Fuel, name="generator__pct_Fuel", curie=DSS.curie('pct_Fuel'),
                   model_uri=DSS.generator__pct_Fuel, domain=None, range=Optional[float])

slots.generator__pct_Reserve = Slot(uri=DSS.pct_Reserve, name="generator__pct_Reserve", curie=DSS.curie('pct_Reserve'),
                   model_uri=DSS.generator__pct_Reserve, domain=None, range=Optional[float])

slots.generator__Refuel = Slot(uri=DSS.Refuel, name="generator__Refuel", curie=DSS.curie('Refuel'),
                   model_uri=DSS.generator__Refuel, domain=None, range=Optional[Union[bool, Bool]])

slots.generator__DynamicEq = Slot(uri=DSS.DynamicEq, name="generator__DynamicEq", curie=DSS.curie('DynamicEq'),
                   model_uri=DSS.generator__DynamicEq, domain=None, range=Optional[str])

slots.generator__DynOut = Slot(uri=DSS.DynOut, name="generator__DynOut", curie=DSS.curie('DynOut'),
                   model_uri=DSS.generator__DynOut, domain=None, range=Optional[Union[str, list[str]]])

slots.generator__spectrum = Slot(uri=DSS.spectrum, name="generator__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.generator__spectrum, domain=None, range=Optional[str])

slots.generator__basefreq = Slot(uri=DSS.basefreq, name="generator__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.generator__basefreq, domain=None, range=Optional[float])

slots.generator__enabled = Slot(uri=DSS.enabled, name="generator__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.generator__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.generator__like = Slot(uri=DSS.like, name="generator__like", curie=DSS.curie('like'),
                   model_uri=DSS.generator__like, domain=None, range=Optional[str])

slots.generic5__name = Slot(uri=DSS.name, name="generic5__name", curie=DSS.curie('name'),
                   model_uri=DSS.generic5__name, domain=None, range=URIRef)

slots.generic5__phases = Slot(uri=DSS.phases, name="generic5__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.generic5__phases, domain=None, range=Optional[int])

slots.generic5__bus1 = Slot(uri=DSS.bus1, name="generic5__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.generic5__bus1, domain=None, range=Optional[str])

slots.generic5__kv = Slot(uri=DSS.kv, name="generic5__kv", curie=DSS.curie('kv'),
                   model_uri=DSS.generic5__kv, domain=None, range=Optional[float])

slots.generic5__kW = Slot(uri=DSS.kW, name="generic5__kW", curie=DSS.curie('kW'),
                   model_uri=DSS.generic5__kW, domain=None, range=Optional[float])

slots.generic5__pf = Slot(uri=DSS.pf, name="generic5__pf", curie=DSS.curie('pf'),
                   model_uri=DSS.generic5__pf, domain=None, range=Optional[float])

slots.generic5__conn = Slot(uri=DSS.conn, name="generic5__conn", curie=DSS.curie('conn'),
                   model_uri=DSS.generic5__conn, domain=None, range=Optional[str])

slots.generic5__kVA = Slot(uri=DSS.kVA, name="generic5__kVA", curie=DSS.curie('kVA'),
                   model_uri=DSS.generic5__kVA, domain=None, range=Optional[float])

slots.generic5__H = Slot(uri=DSS.H, name="generic5__H", curie=DSS.curie('H'),
                   model_uri=DSS.generic5__H, domain=None, range=Optional[float])

slots.generic5__D = Slot(uri=DSS.D, name="generic5__D", curie=DSS.curie('D'),
                   model_uri=DSS.generic5__D, domain=None, range=Optional[str])

slots.generic5__P_ref1kW = Slot(uri=DSS.P_ref1kW, name="generic5__P_ref1kW", curie=DSS.curie('P_ref1kW'),
                   model_uri=DSS.generic5__P_ref1kW, domain=None, range=Optional[float])

slots.generic5__P_ref2kW = Slot(uri=DSS.P_ref2kW, name="generic5__P_ref2kW", curie=DSS.curie('P_ref2kW'),
                   model_uri=DSS.generic5__P_ref2kW, domain=None, range=Optional[float])

slots.generic5__P_ref3kW = Slot(uri=DSS.P_ref3kW, name="generic5__P_ref3kW", curie=DSS.curie('P_ref3kW'),
                   model_uri=DSS.generic5__P_ref3kW, domain=None, range=Optional[float])

slots.generic5__V_ref1kVLN = Slot(uri=DSS.V_ref1kVLN, name="generic5__V_ref1kVLN", curie=DSS.curie('V_ref1kVLN'),
                   model_uri=DSS.generic5__V_ref1kVLN, domain=None, range=Optional[float])

slots.generic5__V_ref2kVLN = Slot(uri=DSS.V_ref2kVLN, name="generic5__V_ref2kVLN", curie=DSS.curie('V_ref2kVLN'),
                   model_uri=DSS.generic5__V_ref2kVLN, domain=None, range=Optional[float])

slots.generic5__V_ref3kVLN = Slot(uri=DSS.V_ref3kVLN, name="generic5__V_ref3kVLN", curie=DSS.curie('V_ref3kVLN'),
                   model_uri=DSS.generic5__V_ref3kVLN, domain=None, range=Optional[float])

slots.generic5__MaxSlip = Slot(uri=DSS.MaxSlip, name="generic5__MaxSlip", curie=DSS.curie('MaxSlip'),
                   model_uri=DSS.generic5__MaxSlip, domain=None, range=Optional[str])

slots.generic5__SlipOption = Slot(uri=DSS.SlipOption, name="generic5__SlipOption", curie=DSS.curie('SlipOption'),
                   model_uri=DSS.generic5__SlipOption, domain=None, range=Optional[str])

slots.generic5__Yearly = Slot(uri=DSS.Yearly, name="generic5__Yearly", curie=DSS.curie('Yearly'),
                   model_uri=DSS.generic5__Yearly, domain=None, range=Optional[str])

slots.generic5__Daily = Slot(uri=DSS.Daily, name="generic5__Daily", curie=DSS.curie('Daily'),
                   model_uri=DSS.generic5__Daily, domain=None, range=Optional[str])

slots.generic5__Duty = Slot(uri=DSS.Duty, name="generic5__Duty", curie=DSS.curie('Duty'),
                   model_uri=DSS.generic5__Duty, domain=None, range=Optional[int])

slots.generic5__Debugtrace = Slot(uri=DSS.Debugtrace, name="generic5__Debugtrace", curie=DSS.curie('Debugtrace'),
                   model_uri=DSS.generic5__Debugtrace, domain=None, range=Optional[str])

slots.generic5__P_refkW = Slot(uri=DSS.P_refkW, name="generic5__P_refkW", curie=DSS.curie('P_refkW'),
                   model_uri=DSS.generic5__P_refkW, domain=None, range=Optional[float])

slots.generic5__Q_refkVAr = Slot(uri=DSS.Q_refkVAr, name="generic5__Q_refkVAr", curie=DSS.curie('Q_refkVAr'),
                   model_uri=DSS.generic5__Q_refkVAr, domain=None, range=Optional[float])

slots.generic5__Cluster_num = Slot(uri=DSS.Cluster_num, name="generic5__Cluster_num", curie=DSS.curie('Cluster_num'),
                   model_uri=DSS.generic5__Cluster_num, domain=None, range=Optional[str])

slots.generic5__V_refkVLN = Slot(uri=DSS.V_refkVLN, name="generic5__V_refkVLN", curie=DSS.curie('V_refkVLN'),
                   model_uri=DSS.generic5__V_refkVLN, domain=None, range=Optional[float])

slots.generic5__ctrl_mode = Slot(uri=DSS.ctrl_mode, name="generic5__ctrl_mode", curie=DSS.curie('ctrl_mode'),
                   model_uri=DSS.generic5__ctrl_mode, domain=None, range=Optional[str])

slots.generic5__QV_flag = Slot(uri=DSS.QV_flag, name="generic5__QV_flag", curie=DSS.curie('QV_flag'),
                   model_uri=DSS.generic5__QV_flag, domain=None, range=Optional[str])

slots.generic5__kcd = Slot(uri=DSS.kcd, name="generic5__kcd", curie=DSS.curie('kcd'),
                   model_uri=DSS.generic5__kcd, domain=None, range=Optional[str])

slots.generic5__kcq = Slot(uri=DSS.kcq, name="generic5__kcq", curie=DSS.curie('kcq'),
                   model_uri=DSS.generic5__kcq, domain=None, range=Optional[str])

slots.generic5__kqi = Slot(uri=DSS.kqi, name="generic5__kqi", curie=DSS.curie('kqi'),
                   model_uri=DSS.generic5__kqi, domain=None, range=Optional[str])

slots.generic5__Q_ref1kVAr = Slot(uri=DSS.Q_ref1kVAr, name="generic5__Q_ref1kVAr", curie=DSS.curie('Q_ref1kVAr'),
                   model_uri=DSS.generic5__Q_ref1kVAr, domain=None, range=Optional[float])

slots.generic5__Q_ref2kVAr = Slot(uri=DSS.Q_ref2kVAr, name="generic5__Q_ref2kVAr", curie=DSS.curie('Q_ref2kVAr'),
                   model_uri=DSS.generic5__Q_ref2kVAr, domain=None, range=Optional[float])

slots.generic5__Q_ref3kVAr = Slot(uri=DSS.Q_ref3kVAr, name="generic5__Q_ref3kVAr", curie=DSS.curie('Q_ref3kVAr'),
                   model_uri=DSS.generic5__Q_ref3kVAr, domain=None, range=Optional[float])

slots.generic5__PmaxkW = Slot(uri=DSS.PmaxkW, name="generic5__PmaxkW", curie=DSS.curie('PmaxkW'),
                   model_uri=DSS.generic5__PmaxkW, domain=None, range=Optional[float])

slots.generic5__PminkW = Slot(uri=DSS.PminkW, name="generic5__PminkW", curie=DSS.curie('PminkW'),
                   model_uri=DSS.generic5__PminkW, domain=None, range=Optional[float])

slots.generic5__PQpriority = Slot(uri=DSS.PQpriority, name="generic5__PQpriority", curie=DSS.curie('PQpriority'),
                   model_uri=DSS.generic5__PQpriority, domain=None, range=Optional[str])

slots.generic5__PmppkW = Slot(uri=DSS.PmppkW, name="generic5__PmppkW", curie=DSS.curie('PmppkW'),
                   model_uri=DSS.generic5__PmppkW, domain=None, range=Optional[float])

slots.generic5__Pfctr1 = Slot(uri=DSS.Pfctr1, name="generic5__Pfctr1", curie=DSS.curie('Pfctr1'),
                   model_uri=DSS.generic5__Pfctr1, domain=None, range=Optional[float])

slots.generic5__Pfctr2 = Slot(uri=DSS.Pfctr2, name="generic5__Pfctr2", curie=DSS.curie('Pfctr2'),
                   model_uri=DSS.generic5__Pfctr2, domain=None, range=Optional[float])

slots.generic5__Pfctr3 = Slot(uri=DSS.Pfctr3, name="generic5__Pfctr3", curie=DSS.curie('Pfctr3'),
                   model_uri=DSS.generic5__Pfctr3, domain=None, range=Optional[float])

slots.generic5__Pfctr4 = Slot(uri=DSS.Pfctr4, name="generic5__Pfctr4", curie=DSS.curie('Pfctr4'),
                   model_uri=DSS.generic5__Pfctr4, domain=None, range=Optional[float])

slots.generic5__Pfctr5 = Slot(uri=DSS.Pfctr5, name="generic5__Pfctr5", curie=DSS.curie('Pfctr5'),
                   model_uri=DSS.generic5__Pfctr5, domain=None, range=Optional[float])

slots.generic5__Pfctr6 = Slot(uri=DSS.Pfctr6, name="generic5__Pfctr6", curie=DSS.curie('Pfctr6'),
                   model_uri=DSS.generic5__Pfctr6, domain=None, range=Optional[float])

slots.generic5__PbiaskW = Slot(uri=DSS.PbiaskW, name="generic5__PbiaskW", curie=DSS.curie('PbiaskW'),
                   model_uri=DSS.generic5__PbiaskW, domain=None, range=Optional[float])

slots.generic5__CC_Switch = Slot(uri=DSS.CC_Switch, name="generic5__CC_Switch", curie=DSS.curie('CC_Switch'),
                   model_uri=DSS.generic5__CC_Switch, domain=None, range=Optional[str])

slots.generic5__kcq_drp2 = Slot(uri=DSS.kcq_drp2, name="generic5__kcq_drp2", curie=DSS.curie('kcq_drp2'),
                   model_uri=DSS.generic5__kcq_drp2, domain=None, range=Optional[str])

slots.generic5__Volt_Trhd = Slot(uri=DSS.Volt_Trhd, name="generic5__Volt_Trhd", curie=DSS.curie('Volt_Trhd'),
                   model_uri=DSS.generic5__Volt_Trhd, domain=None, range=Optional[str])

slots.generic5__droop = Slot(uri=DSS.droop, name="generic5__droop", curie=DSS.curie('droop'),
                   model_uri=DSS.generic5__droop, domain=None, range=Optional[int])

slots.generic5__spectrum = Slot(uri=DSS.spectrum, name="generic5__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.generic5__spectrum, domain=None, range=Optional[float])

slots.generic5__basefreq = Slot(uri=DSS.basefreq, name="generic5__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.generic5__basefreq, domain=None, range=Optional[float])

slots.generic5__enabled = Slot(uri=DSS.enabled, name="generic5__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.generic5__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.generic5__like = Slot(uri=DSS.like, name="generic5__like", curie=DSS.curie('like'),
                   model_uri=DSS.generic5__like, domain=None, range=Optional[str])

slots.gicline__name = Slot(uri=DSS.name, name="gicline__name", curie=DSS.curie('name'),
                   model_uri=DSS.gicline__name, domain=None, range=URIRef)

slots.gicline__bus1 = Slot(uri=DSS.bus1, name="gicline__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.gicline__bus1, domain=None, range=Optional[str])

slots.gicline__bus2 = Slot(uri=DSS.bus2, name="gicline__bus2", curie=DSS.curie('bus2'),
                   model_uri=DSS.gicline__bus2, domain=None, range=Optional[str])

slots.gicline__Volts = Slot(uri=DSS.Volts, name="gicline__Volts", curie=DSS.curie('Volts'),
                   model_uri=DSS.gicline__Volts, domain=None, range=Optional[float])

slots.gicline__Angle = Slot(uri=DSS.Angle, name="gicline__Angle", curie=DSS.curie('Angle'),
                   model_uri=DSS.gicline__Angle, domain=None, range=Optional[float])

slots.gicline__frequency = Slot(uri=DSS.frequency, name="gicline__frequency", curie=DSS.curie('frequency'),
                   model_uri=DSS.gicline__frequency, domain=None, range=Optional[str])

slots.gicline__phases = Slot(uri=DSS.phases, name="gicline__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.gicline__phases, domain=None, range=Optional[int])

slots.gicline__R = Slot(uri=DSS.R, name="gicline__R", curie=DSS.curie('R'),
                   model_uri=DSS.gicline__R, domain=None, range=Optional[float])

slots.gicline__X = Slot(uri=DSS.X, name="gicline__X", curie=DSS.curie('X'),
                   model_uri=DSS.gicline__X, domain=None, range=Optional[float])

slots.gicline__C = Slot(uri=DSS.C, name="gicline__C", curie=DSS.curie('C'),
                   model_uri=DSS.gicline__C, domain=None, range=Optional[str])

slots.gicline__EN = Slot(uri=DSS.EN, name="gicline__EN", curie=DSS.curie('EN'),
                   model_uri=DSS.gicline__EN, domain=None, range=Optional[float])

slots.gicline__EE = Slot(uri=DSS.EE, name="gicline__EE", curie=DSS.curie('EE'),
                   model_uri=DSS.gicline__EE, domain=None, range=Optional[float])

slots.gicline__Lat1 = Slot(uri=DSS.Lat1, name="gicline__Lat1", curie=DSS.curie('Lat1'),
                   model_uri=DSS.gicline__Lat1, domain=None, range=Optional[str])

slots.gicline__Lon1 = Slot(uri=DSS.Lon1, name="gicline__Lon1", curie=DSS.curie('Lon1'),
                   model_uri=DSS.gicline__Lon1, domain=None, range=Optional[str])

slots.gicline__Lat2 = Slot(uri=DSS.Lat2, name="gicline__Lat2", curie=DSS.curie('Lat2'),
                   model_uri=DSS.gicline__Lat2, domain=None, range=Optional[str])

slots.gicline__Lon2 = Slot(uri=DSS.Lon2, name="gicline__Lon2", curie=DSS.curie('Lon2'),
                   model_uri=DSS.gicline__Lon2, domain=None, range=Optional[str])

slots.gicline__spectrum = Slot(uri=DSS.spectrum, name="gicline__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.gicline__spectrum, domain=None, range=Optional[str])

slots.gicline__basefreq = Slot(uri=DSS.basefreq, name="gicline__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.gicline__basefreq, domain=None, range=Optional[float])

slots.gicline__enabled = Slot(uri=DSS.enabled, name="gicline__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.gicline__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.gicline__like = Slot(uri=DSS.like, name="gicline__like", curie=DSS.curie('like'),
                   model_uri=DSS.gicline__like, domain=None, range=Optional[str])

slots.indmach012__name = Slot(uri=DSS.name, name="indmach012__name", curie=DSS.curie('name'),
                   model_uri=DSS.indmach012__name, domain=None, range=URIRef)

slots.indmach012__phases = Slot(uri=DSS.phases, name="indmach012__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.indmach012__phases, domain=None, range=Optional[int])

slots.indmach012__bus1 = Slot(uri=DSS.bus1, name="indmach012__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.indmach012__bus1, domain=None, range=Optional[str])

slots.indmach012__kv = Slot(uri=DSS.kv, name="indmach012__kv", curie=DSS.curie('kv'),
                   model_uri=DSS.indmach012__kv, domain=None, range=Optional[float])

slots.indmach012__kW = Slot(uri=DSS.kW, name="indmach012__kW", curie=DSS.curie('kW'),
                   model_uri=DSS.indmach012__kW, domain=None, range=Optional[float])

slots.indmach012__pf = Slot(uri=DSS.pf, name="indmach012__pf", curie=DSS.curie('pf'),
                   model_uri=DSS.indmach012__pf, domain=None, range=Optional[float])

slots.indmach012__conn = Slot(uri=DSS.conn, name="indmach012__conn", curie=DSS.curie('conn'),
                   model_uri=DSS.indmach012__conn, domain=None, range=Optional[str])

slots.indmach012__kVA = Slot(uri=DSS.kVA, name="indmach012__kVA", curie=DSS.curie('kVA'),
                   model_uri=DSS.indmach012__kVA, domain=None, range=Optional[float])

slots.indmach012__H = Slot(uri=DSS.H, name="indmach012__H", curie=DSS.curie('H'),
                   model_uri=DSS.indmach012__H, domain=None, range=Optional[float])

slots.indmach012__D = Slot(uri=DSS.D, name="indmach012__D", curie=DSS.curie('D'),
                   model_uri=DSS.indmach012__D, domain=None, range=Optional[str])

slots.indmach012__puRs = Slot(uri=DSS.puRs, name="indmach012__puRs", curie=DSS.curie('puRs'),
                   model_uri=DSS.indmach012__puRs, domain=None, range=Optional[float])

slots.indmach012__puXs = Slot(uri=DSS.puXs, name="indmach012__puXs", curie=DSS.curie('puXs'),
                   model_uri=DSS.indmach012__puXs, domain=None, range=Optional[float])

slots.indmach012__puRr = Slot(uri=DSS.puRr, name="indmach012__puRr", curie=DSS.curie('puRr'),
                   model_uri=DSS.indmach012__puRr, domain=None, range=Optional[float])

slots.indmach012__puXr = Slot(uri=DSS.puXr, name="indmach012__puXr", curie=DSS.curie('puXr'),
                   model_uri=DSS.indmach012__puXr, domain=None, range=Optional[float])

slots.indmach012__puXm = Slot(uri=DSS.puXm, name="indmach012__puXm", curie=DSS.curie('puXm'),
                   model_uri=DSS.indmach012__puXm, domain=None, range=Optional[float])

slots.indmach012__Slip = Slot(uri=DSS.Slip, name="indmach012__Slip", curie=DSS.curie('Slip'),
                   model_uri=DSS.indmach012__Slip, domain=None, range=Optional[str])

slots.indmach012__MaxSlip = Slot(uri=DSS.MaxSlip, name="indmach012__MaxSlip", curie=DSS.curie('MaxSlip'),
                   model_uri=DSS.indmach012__MaxSlip, domain=None, range=Optional[str])

slots.indmach012__SlipOption = Slot(uri=DSS.SlipOption, name="indmach012__SlipOption", curie=DSS.curie('SlipOption'),
                   model_uri=DSS.indmach012__SlipOption, domain=None, range=Optional[str])

slots.indmach012__Yearly = Slot(uri=DSS.Yearly, name="indmach012__Yearly", curie=DSS.curie('Yearly'),
                   model_uri=DSS.indmach012__Yearly, domain=None, range=Optional[str])

slots.indmach012__Daily = Slot(uri=DSS.Daily, name="indmach012__Daily", curie=DSS.curie('Daily'),
                   model_uri=DSS.indmach012__Daily, domain=None, range=Optional[str])

slots.indmach012__Duty = Slot(uri=DSS.Duty, name="indmach012__Duty", curie=DSS.curie('Duty'),
                   model_uri=DSS.indmach012__Duty, domain=None, range=Optional[int])

slots.indmach012__Debugtrace = Slot(uri=DSS.Debugtrace, name="indmach012__Debugtrace", curie=DSS.curie('Debugtrace'),
                   model_uri=DSS.indmach012__Debugtrace, domain=None, range=Optional[str])

slots.indmach012__spectrum = Slot(uri=DSS.spectrum, name="indmach012__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.indmach012__spectrum, domain=None, range=Optional[float])

slots.indmach012__basefreq = Slot(uri=DSS.basefreq, name="indmach012__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.indmach012__basefreq, domain=None, range=Optional[float])

slots.indmach012__enabled = Slot(uri=DSS.enabled, name="indmach012__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.indmach012__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.indmach012__like = Slot(uri=DSS.like, name="indmach012__like", curie=DSS.curie('like'),
                   model_uri=DSS.indmach012__like, domain=None, range=Optional[str])

slots.pvsystem__name = Slot(uri=DSS.name, name="pvsystem__name", curie=DSS.curie('name'),
                   model_uri=DSS.pvsystem__name, domain=None, range=URIRef)

slots.pvsystem__phases = Slot(uri=DSS.phases, name="pvsystem__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.pvsystem__phases, domain=None, range=Optional[int])

slots.pvsystem__bus1 = Slot(uri=DSS.bus1, name="pvsystem__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.pvsystem__bus1, domain=None, range=Optional[str])

slots.pvsystem__kv = Slot(uri=DSS.kv, name="pvsystem__kv", curie=DSS.curie('kv'),
                   model_uri=DSS.pvsystem__kv, domain=None, range=Optional[float])

slots.pvsystem__irradiance = Slot(uri=DSS.irradiance, name="pvsystem__irradiance", curie=DSS.curie('irradiance'),
                   model_uri=DSS.pvsystem__irradiance, domain=None, range=Optional[float])

slots.pvsystem__Pmpp = Slot(uri=DSS.Pmpp, name="pvsystem__Pmpp", curie=DSS.curie('Pmpp'),
                   model_uri=DSS.pvsystem__Pmpp, domain=None, range=Optional[float])

slots.pvsystem__pct_Pmpp = Slot(uri=DSS.pct_Pmpp, name="pvsystem__pct_Pmpp", curie=DSS.curie('pct_Pmpp'),
                   model_uri=DSS.pvsystem__pct_Pmpp, domain=None, range=Optional[float])

slots.pvsystem__Temperature = Slot(uri=DSS.Temperature, name="pvsystem__Temperature", curie=DSS.curie('Temperature'),
                   model_uri=DSS.pvsystem__Temperature, domain=None, range=Optional[float])

slots.pvsystem__pf = Slot(uri=DSS.pf, name="pvsystem__pf", curie=DSS.curie('pf'),
                   model_uri=DSS.pvsystem__pf, domain=None, range=Optional[float])

slots.pvsystem__conn = Slot(uri=DSS.conn, name="pvsystem__conn", curie=DSS.curie('conn'),
                   model_uri=DSS.pvsystem__conn, domain=None, range=Optional[str])

slots.pvsystem__kvar = Slot(uri=DSS.kvar, name="pvsystem__kvar", curie=DSS.curie('kvar'),
                   model_uri=DSS.pvsystem__kvar, domain=None, range=Optional[float])

slots.pvsystem__kVA = Slot(uri=DSS.kVA, name="pvsystem__kVA", curie=DSS.curie('kVA'),
                   model_uri=DSS.pvsystem__kVA, domain=None, range=Optional[float])

slots.pvsystem__pct_Cutin = Slot(uri=DSS.pct_Cutin, name="pvsystem__pct_Cutin", curie=DSS.curie('pct_Cutin'),
                   model_uri=DSS.pvsystem__pct_Cutin, domain=None, range=Optional[float])

slots.pvsystem__pct_Cutout = Slot(uri=DSS.pct_Cutout, name="pvsystem__pct_Cutout", curie=DSS.curie('pct_Cutout'),
                   model_uri=DSS.pvsystem__pct_Cutout, domain=None, range=Optional[float])

slots.pvsystem__EffCurve = Slot(uri=DSS.EffCurve, name="pvsystem__EffCurve", curie=DSS.curie('EffCurve'),
                   model_uri=DSS.pvsystem__EffCurve, domain=None, range=Optional[str])

slots.pvsystem__P_TCurve = Slot(uri=DSS.P_TCurve, name="pvsystem__P_TCurve", curie=DSS.curie('P_TCurve'),
                   model_uri=DSS.pvsystem__P_TCurve, domain=None, range=Optional[str])

slots.pvsystem__pct_R = Slot(uri=DSS.pct_R, name="pvsystem__pct_R", curie=DSS.curie('pct_R'),
                   model_uri=DSS.pvsystem__pct_R, domain=None, range=Optional[float])

slots.pvsystem__pct_X = Slot(uri=DSS.pct_X, name="pvsystem__pct_X", curie=DSS.curie('pct_X'),
                   model_uri=DSS.pvsystem__pct_X, domain=None, range=Optional[float])

slots.pvsystem__model = Slot(uri=DSS.model, name="pvsystem__model", curie=DSS.curie('model'),
                   model_uri=DSS.pvsystem__model, domain=None, range=Optional[int])

slots.pvsystem__Vminpu = Slot(uri=DSS.Vminpu, name="pvsystem__Vminpu", curie=DSS.curie('Vminpu'),
                   model_uri=DSS.pvsystem__Vminpu, domain=None, range=Optional[float])

slots.pvsystem__Vmaxpu = Slot(uri=DSS.Vmaxpu, name="pvsystem__Vmaxpu", curie=DSS.curie('Vmaxpu'),
                   model_uri=DSS.pvsystem__Vmaxpu, domain=None, range=Optional[float])

slots.pvsystem__Balanced = Slot(uri=DSS.Balanced, name="pvsystem__Balanced", curie=DSS.curie('Balanced'),
                   model_uri=DSS.pvsystem__Balanced, domain=None, range=Optional[Union[bool, Bool]])

slots.pvsystem__LimitCurrent = Slot(uri=DSS.LimitCurrent, name="pvsystem__LimitCurrent", curie=DSS.curie('LimitCurrent'),
                   model_uri=DSS.pvsystem__LimitCurrent, domain=None, range=Optional[Union[bool, Bool]])

slots.pvsystem__yearly = Slot(uri=DSS.yearly, name="pvsystem__yearly", curie=DSS.curie('yearly'),
                   model_uri=DSS.pvsystem__yearly, domain=None, range=Optional[str])

slots.pvsystem__daily = Slot(uri=DSS.daily, name="pvsystem__daily", curie=DSS.curie('daily'),
                   model_uri=DSS.pvsystem__daily, domain=None, range=Optional[str])

slots.pvsystem__duty = Slot(uri=DSS.duty, name="pvsystem__duty", curie=DSS.curie('duty'),
                   model_uri=DSS.pvsystem__duty, domain=None, range=Optional[int])

slots.pvsystem__Tyearly = Slot(uri=DSS.Tyearly, name="pvsystem__Tyearly", curie=DSS.curie('Tyearly'),
                   model_uri=DSS.pvsystem__Tyearly, domain=None, range=Optional[str])

slots.pvsystem__Tdaily = Slot(uri=DSS.Tdaily, name="pvsystem__Tdaily", curie=DSS.curie('Tdaily'),
                   model_uri=DSS.pvsystem__Tdaily, domain=None, range=Optional[str])

slots.pvsystem__Tduty = Slot(uri=DSS.Tduty, name="pvsystem__Tduty", curie=DSS.curie('Tduty'),
                   model_uri=DSS.pvsystem__Tduty, domain=None, range=Optional[int])

slots.pvsystem__class_class = Slot(uri=DSS.class_class, name="pvsystem__class_class", curie=DSS.curie('class_class'),
                   model_uri=DSS.pvsystem__class_class, domain=None, range=Optional[int])

slots.pvsystem__UserModel = Slot(uri=DSS.UserModel, name="pvsystem__UserModel", curie=DSS.curie('UserModel'),
                   model_uri=DSS.pvsystem__UserModel, domain=None, range=Optional[str])

slots.pvsystem__UserData = Slot(uri=DSS.UserData, name="pvsystem__UserData", curie=DSS.curie('UserData'),
                   model_uri=DSS.pvsystem__UserData, domain=None, range=Optional[str])

slots.pvsystem__debugtrace = Slot(uri=DSS.debugtrace, name="pvsystem__debugtrace", curie=DSS.curie('debugtrace'),
                   model_uri=DSS.pvsystem__debugtrace, domain=None, range=Optional[Union[bool, Bool]])

slots.pvsystem__VarFollowInverter = Slot(uri=DSS.VarFollowInverter, name="pvsystem__VarFollowInverter", curie=DSS.curie('VarFollowInverter'),
                   model_uri=DSS.pvsystem__VarFollowInverter, domain=None, range=Optional[Union[bool, Bool]])

slots.pvsystem__DutyStart = Slot(uri=DSS.DutyStart, name="pvsystem__DutyStart", curie=DSS.curie('DutyStart'),
                   model_uri=DSS.pvsystem__DutyStart, domain=None, range=Optional[str])

slots.pvsystem__WattPriority = Slot(uri=DSS.WattPriority, name="pvsystem__WattPriority", curie=DSS.curie('WattPriority'),
                   model_uri=DSS.pvsystem__WattPriority, domain=None, range=Optional[Union[bool, Bool]])

slots.pvsystem__PFPriority = Slot(uri=DSS.PFPriority, name="pvsystem__PFPriority", curie=DSS.curie('PFPriority'),
                   model_uri=DSS.pvsystem__PFPriority, domain=None, range=Optional[Union[bool, Bool]])

slots.pvsystem__pct_PminNoVars = Slot(uri=DSS.pct_PminNoVars, name="pvsystem__pct_PminNoVars", curie=DSS.curie('pct_PminNoVars'),
                   model_uri=DSS.pvsystem__pct_PminNoVars, domain=None, range=Optional[float])

slots.pvsystem__pct_PminkvarMax = Slot(uri=DSS.pct_PminkvarMax, name="pvsystem__pct_PminkvarMax", curie=DSS.curie('pct_PminkvarMax'),
                   model_uri=DSS.pvsystem__pct_PminkvarMax, domain=None, range=Optional[float])

slots.pvsystem__kvarMax = Slot(uri=DSS.kvarMax, name="pvsystem__kvarMax", curie=DSS.curie('kvarMax'),
                   model_uri=DSS.pvsystem__kvarMax, domain=None, range=Optional[float])

slots.pvsystem__kvarMaxAbs = Slot(uri=DSS.kvarMaxAbs, name="pvsystem__kvarMaxAbs", curie=DSS.curie('kvarMaxAbs'),
                   model_uri=DSS.pvsystem__kvarMaxAbs, domain=None, range=Optional[float])

slots.pvsystem__kVDC = Slot(uri=DSS.kVDC, name="pvsystem__kVDC", curie=DSS.curie('kVDC'),
                   model_uri=DSS.pvsystem__kVDC, domain=None, range=Optional[float])

slots.pvsystem__Kp = Slot(uri=DSS.Kp, name="pvsystem__Kp", curie=DSS.curie('Kp'),
                   model_uri=DSS.pvsystem__Kp, domain=None, range=Optional[str])

slots.pvsystem__PITol = Slot(uri=DSS.PITol, name="pvsystem__PITol", curie=DSS.curie('PITol'),
                   model_uri=DSS.pvsystem__PITol, domain=None, range=Optional[str])

slots.pvsystem__SafeVoltage = Slot(uri=DSS.SafeVoltage, name="pvsystem__SafeVoltage", curie=DSS.curie('SafeVoltage'),
                   model_uri=DSS.pvsystem__SafeVoltage, domain=None, range=Optional[float])

slots.pvsystem__SafeMode = Slot(uri=DSS.SafeMode, name="pvsystem__SafeMode", curie=DSS.curie('SafeMode'),
                   model_uri=DSS.pvsystem__SafeMode, domain=None, range=Optional[str])

slots.pvsystem__DynamicEq = Slot(uri=DSS.DynamicEq, name="pvsystem__DynamicEq", curie=DSS.curie('DynamicEq'),
                   model_uri=DSS.pvsystem__DynamicEq, domain=None, range=Optional[str])

slots.pvsystem__DynOut = Slot(uri=DSS.DynOut, name="pvsystem__DynOut", curie=DSS.curie('DynOut'),
                   model_uri=DSS.pvsystem__DynOut, domain=None, range=Optional[float])

slots.pvsystem__ControlMode = Slot(uri=DSS.ControlMode, name="pvsystem__ControlMode", curie=DSS.curie('ControlMode'),
                   model_uri=DSS.pvsystem__ControlMode, domain=None, range=Optional[str])

slots.pvsystem__AmpLimit = Slot(uri=DSS.AmpLimit, name="pvsystem__AmpLimit", curie=DSS.curie('AmpLimit'),
                   model_uri=DSS.pvsystem__AmpLimit, domain=None, range=Optional[float])

slots.pvsystem__AmpLimitGain = Slot(uri=DSS.AmpLimitGain, name="pvsystem__AmpLimitGain", curie=DSS.curie('AmpLimitGain'),
                   model_uri=DSS.pvsystem__AmpLimitGain, domain=None, range=Optional[float])

slots.pvsystem__spectrum = Slot(uri=DSS.spectrum, name="pvsystem__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.pvsystem__spectrum, domain=None, range=Optional[float])

slots.pvsystem__basefreq = Slot(uri=DSS.basefreq, name="pvsystem__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.pvsystem__basefreq, domain=None, range=Optional[float])

slots.pvsystem__enabled = Slot(uri=DSS.enabled, name="pvsystem__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.pvsystem__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.pvsystem__like = Slot(uri=DSS.like, name="pvsystem__like", curie=DSS.curie('like'),
                   model_uri=DSS.pvsystem__like, domain=None, range=Optional[str])

slots.storage__name = Slot(uri=DSS.name, name="storage__name", curie=DSS.curie('name'),
                   model_uri=DSS.storage__name, domain=None, range=URIRef)

slots.storage__phases = Slot(uri=DSS.phases, name="storage__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.storage__phases, domain=None, range=Optional[int])

slots.storage__bus1 = Slot(uri=DSS.bus1, name="storage__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.storage__bus1, domain=None, range=Optional[str])

slots.storage__kv = Slot(uri=DSS.kv, name="storage__kv", curie=DSS.curie('kv'),
                   model_uri=DSS.storage__kv, domain=None, range=Optional[float])

slots.storage__conn = Slot(uri=DSS.conn, name="storage__conn", curie=DSS.curie('conn'),
                   model_uri=DSS.storage__conn, domain=None, range=Optional[str])

slots.storage__kW = Slot(uri=DSS.kW, name="storage__kW", curie=DSS.curie('kW'),
                   model_uri=DSS.storage__kW, domain=None, range=Optional[float])

slots.storage__kvar = Slot(uri=DSS.kvar, name="storage__kvar", curie=DSS.curie('kvar'),
                   model_uri=DSS.storage__kvar, domain=None, range=Optional[float])

slots.storage__pf = Slot(uri=DSS.pf, name="storage__pf", curie=DSS.curie('pf'),
                   model_uri=DSS.storage__pf, domain=None, range=Optional[float])

slots.storage__kVA = Slot(uri=DSS.kVA, name="storage__kVA", curie=DSS.curie('kVA'),
                   model_uri=DSS.storage__kVA, domain=None, range=Optional[float])

slots.storage__pct_Cutin = Slot(uri=DSS.pct_Cutin, name="storage__pct_Cutin", curie=DSS.curie('pct_Cutin'),
                   model_uri=DSS.storage__pct_Cutin, domain=None, range=Optional[float])

slots.storage__pct_Cutout = Slot(uri=DSS.pct_Cutout, name="storage__pct_Cutout", curie=DSS.curie('pct_Cutout'),
                   model_uri=DSS.storage__pct_Cutout, domain=None, range=Optional[float])

slots.storage__EffCurve = Slot(uri=DSS.EffCurve, name="storage__EffCurve", curie=DSS.curie('EffCurve'),
                   model_uri=DSS.storage__EffCurve, domain=None, range=Optional[str])

slots.storage__VarFollowInverter = Slot(uri=DSS.VarFollowInverter, name="storage__VarFollowInverter", curie=DSS.curie('VarFollowInverter'),
                   model_uri=DSS.storage__VarFollowInverter, domain=None, range=Optional[Union[bool, Bool]])

slots.storage__kvarMax = Slot(uri=DSS.kvarMax, name="storage__kvarMax", curie=DSS.curie('kvarMax'),
                   model_uri=DSS.storage__kvarMax, domain=None, range=Optional[float])

slots.storage__kvarMaxAbs = Slot(uri=DSS.kvarMaxAbs, name="storage__kvarMaxAbs", curie=DSS.curie('kvarMaxAbs'),
                   model_uri=DSS.storage__kvarMaxAbs, domain=None, range=Optional[float])

slots.storage__WattPriority = Slot(uri=DSS.WattPriority, name="storage__WattPriority", curie=DSS.curie('WattPriority'),
                   model_uri=DSS.storage__WattPriority, domain=None, range=Optional[Union[bool, Bool]])

slots.storage__PFPriority = Slot(uri=DSS.PFPriority, name="storage__PFPriority", curie=DSS.curie('PFPriority'),
                   model_uri=DSS.storage__PFPriority, domain=None, range=Optional[Union[bool, Bool]])

slots.storage__pct_PminNoVars = Slot(uri=DSS.pct_PminNoVars, name="storage__pct_PminNoVars", curie=DSS.curie('pct_PminNoVars'),
                   model_uri=DSS.storage__pct_PminNoVars, domain=None, range=Optional[float])

slots.storage__pct_PminkvarMax = Slot(uri=DSS.pct_PminkvarMax, name="storage__pct_PminkvarMax", curie=DSS.curie('pct_PminkvarMax'),
                   model_uri=DSS.storage__pct_PminkvarMax, domain=None, range=Optional[float])

slots.storage__kWrated = Slot(uri=DSS.kWrated, name="storage__kWrated", curie=DSS.curie('kWrated'),
                   model_uri=DSS.storage__kWrated, domain=None, range=Optional[float])

slots.storage__pct_kWrated = Slot(uri=DSS.pct_kWrated, name="storage__pct_kWrated", curie=DSS.curie('pct_kWrated'),
                   model_uri=DSS.storage__pct_kWrated, domain=None, range=Optional[float])

slots.storage__kWhrated = Slot(uri=DSS.kWhrated, name="storage__kWhrated", curie=DSS.curie('kWhrated'),
                   model_uri=DSS.storage__kWhrated, domain=None, range=Optional[float])

slots.storage__kWhstored = Slot(uri=DSS.kWhstored, name="storage__kWhstored", curie=DSS.curie('kWhstored'),
                   model_uri=DSS.storage__kWhstored, domain=None, range=Optional[float])

slots.storage__pct_stored = Slot(uri=DSS.pct_stored, name="storage__pct_stored", curie=DSS.curie('pct_stored'),
                   model_uri=DSS.storage__pct_stored, domain=None, range=Optional[float])

slots.storage__pct_reserve = Slot(uri=DSS.pct_reserve, name="storage__pct_reserve", curie=DSS.curie('pct_reserve'),
                   model_uri=DSS.storage__pct_reserve, domain=None, range=Optional[float])

slots.storage__State = Slot(uri=DSS.State, name="storage__State", curie=DSS.curie('State'),
                   model_uri=DSS.storage__State, domain=None, range=Optional[str])

slots.storage__pct_Discharge = Slot(uri=DSS.pct_Discharge, name="storage__pct_Discharge", curie=DSS.curie('pct_Discharge'),
                   model_uri=DSS.storage__pct_Discharge, domain=None, range=Optional[float])

slots.storage__pct_Charge = Slot(uri=DSS.pct_Charge, name="storage__pct_Charge", curie=DSS.curie('pct_Charge'),
                   model_uri=DSS.storage__pct_Charge, domain=None, range=Optional[float])

slots.storage__pct_EffCharge = Slot(uri=DSS.pct_EffCharge, name="storage__pct_EffCharge", curie=DSS.curie('pct_EffCharge'),
                   model_uri=DSS.storage__pct_EffCharge, domain=None, range=Optional[float])

slots.storage__pct_EffDischarge = Slot(uri=DSS.pct_EffDischarge, name="storage__pct_EffDischarge", curie=DSS.curie('pct_EffDischarge'),
                   model_uri=DSS.storage__pct_EffDischarge, domain=None, range=Optional[float])

slots.storage__pct_IdlingkW = Slot(uri=DSS.pct_IdlingkW, name="storage__pct_IdlingkW", curie=DSS.curie('pct_IdlingkW'),
                   model_uri=DSS.storage__pct_IdlingkW, domain=None, range=Optional[float])

slots.storage__pct_Idlingkvar = Slot(uri=DSS.pct_Idlingkvar, name="storage__pct_Idlingkvar", curie=DSS.curie('pct_Idlingkvar'),
                   model_uri=DSS.storage__pct_Idlingkvar, domain=None, range=Optional[float])

slots.storage__pct_R = Slot(uri=DSS.pct_R, name="storage__pct_R", curie=DSS.curie('pct_R'),
                   model_uri=DSS.storage__pct_R, domain=None, range=Optional[float])

slots.storage__pct_X = Slot(uri=DSS.pct_X, name="storage__pct_X", curie=DSS.curie('pct_X'),
                   model_uri=DSS.storage__pct_X, domain=None, range=Optional[float])

slots.storage__model = Slot(uri=DSS.model, name="storage__model", curie=DSS.curie('model'),
                   model_uri=DSS.storage__model, domain=None, range=Optional[int])

slots.storage__Vminpu = Slot(uri=DSS.Vminpu, name="storage__Vminpu", curie=DSS.curie('Vminpu'),
                   model_uri=DSS.storage__Vminpu, domain=None, range=Optional[float])

slots.storage__Vmaxpu = Slot(uri=DSS.Vmaxpu, name="storage__Vmaxpu", curie=DSS.curie('Vmaxpu'),
                   model_uri=DSS.storage__Vmaxpu, domain=None, range=Optional[float])

slots.storage__Balanced = Slot(uri=DSS.Balanced, name="storage__Balanced", curie=DSS.curie('Balanced'),
                   model_uri=DSS.storage__Balanced, domain=None, range=Optional[Union[bool, Bool]])

slots.storage__LimitCurrent = Slot(uri=DSS.LimitCurrent, name="storage__LimitCurrent", curie=DSS.curie('LimitCurrent'),
                   model_uri=DSS.storage__LimitCurrent, domain=None, range=Optional[Union[bool, Bool]])

slots.storage__yearly = Slot(uri=DSS.yearly, name="storage__yearly", curie=DSS.curie('yearly'),
                   model_uri=DSS.storage__yearly, domain=None, range=Optional[str])

slots.storage__daily = Slot(uri=DSS.daily, name="storage__daily", curie=DSS.curie('daily'),
                   model_uri=DSS.storage__daily, domain=None, range=Optional[str])

slots.storage__duty = Slot(uri=DSS.duty, name="storage__duty", curie=DSS.curie('duty'),
                   model_uri=DSS.storage__duty, domain=None, range=Optional[int])

slots.storage__DispMode = Slot(uri=DSS.DispMode, name="storage__DispMode", curie=DSS.curie('DispMode'),
                   model_uri=DSS.storage__DispMode, domain=None, range=Optional[str])

slots.storage__DischargeTrigger = Slot(uri=DSS.DischargeTrigger, name="storage__DischargeTrigger", curie=DSS.curie('DischargeTrigger'),
                   model_uri=DSS.storage__DischargeTrigger, domain=None, range=Optional[str])

slots.storage__ChargeTrigger = Slot(uri=DSS.ChargeTrigger, name="storage__ChargeTrigger", curie=DSS.curie('ChargeTrigger'),
                   model_uri=DSS.storage__ChargeTrigger, domain=None, range=Optional[str])

slots.storage__TimeChargeTrig = Slot(uri=DSS.TimeChargeTrig, name="storage__TimeChargeTrig", curie=DSS.curie('TimeChargeTrig'),
                   model_uri=DSS.storage__TimeChargeTrig, domain=None, range=Optional[str])

slots.storage__class_class = Slot(uri=DSS.class_class, name="storage__class_class", curie=DSS.curie('class_class'),
                   model_uri=DSS.storage__class_class, domain=None, range=Optional[int])

slots.storage__DynaDLL = Slot(uri=DSS.DynaDLL, name="storage__DynaDLL", curie=DSS.curie('DynaDLL'),
                   model_uri=DSS.storage__DynaDLL, domain=None, range=Optional[str])

slots.storage__DynaData = Slot(uri=DSS.DynaData, name="storage__DynaData", curie=DSS.curie('DynaData'),
                   model_uri=DSS.storage__DynaData, domain=None, range=Optional[str])

slots.storage__UserModel = Slot(uri=DSS.UserModel, name="storage__UserModel", curie=DSS.curie('UserModel'),
                   model_uri=DSS.storage__UserModel, domain=None, range=Optional[str])

slots.storage__UserData = Slot(uri=DSS.UserData, name="storage__UserData", curie=DSS.curie('UserData'),
                   model_uri=DSS.storage__UserData, domain=None, range=Optional[str])

slots.storage__debugtrace = Slot(uri=DSS.debugtrace, name="storage__debugtrace", curie=DSS.curie('debugtrace'),
                   model_uri=DSS.storage__debugtrace, domain=None, range=Optional[Union[bool, Bool]])

slots.storage__kVDC = Slot(uri=DSS.kVDC, name="storage__kVDC", curie=DSS.curie('kVDC'),
                   model_uri=DSS.storage__kVDC, domain=None, range=Optional[float])

slots.storage__Kp = Slot(uri=DSS.Kp, name="storage__Kp", curie=DSS.curie('Kp'),
                   model_uri=DSS.storage__Kp, domain=None, range=Optional[str])

slots.storage__PITol = Slot(uri=DSS.PITol, name="storage__PITol", curie=DSS.curie('PITol'),
                   model_uri=DSS.storage__PITol, domain=None, range=Optional[str])

slots.storage__SafeVoltage = Slot(uri=DSS.SafeVoltage, name="storage__SafeVoltage", curie=DSS.curie('SafeVoltage'),
                   model_uri=DSS.storage__SafeVoltage, domain=None, range=Optional[float])

slots.storage__SafeMode = Slot(uri=DSS.SafeMode, name="storage__SafeMode", curie=DSS.curie('SafeMode'),
                   model_uri=DSS.storage__SafeMode, domain=None, range=Optional[str])

slots.storage__DynamicEq = Slot(uri=DSS.DynamicEq, name="storage__DynamicEq", curie=DSS.curie('DynamicEq'),
                   model_uri=DSS.storage__DynamicEq, domain=None, range=Optional[str])

slots.storage__DynOut = Slot(uri=DSS.DynOut, name="storage__DynOut", curie=DSS.curie('DynOut'),
                   model_uri=DSS.storage__DynOut, domain=None, range=Optional[float])

slots.storage__ControlMode = Slot(uri=DSS.ControlMode, name="storage__ControlMode", curie=DSS.curie('ControlMode'),
                   model_uri=DSS.storage__ControlMode, domain=None, range=Optional[str])

slots.storage__AmpLimit = Slot(uri=DSS.AmpLimit, name="storage__AmpLimit", curie=DSS.curie('AmpLimit'),
                   model_uri=DSS.storage__AmpLimit, domain=None, range=Optional[float])

slots.storage__AmpLimitGain = Slot(uri=DSS.AmpLimitGain, name="storage__AmpLimitGain", curie=DSS.curie('AmpLimitGain'),
                   model_uri=DSS.storage__AmpLimitGain, domain=None, range=Optional[float])

slots.storage__spectrum = Slot(uri=DSS.spectrum, name="storage__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.storage__spectrum, domain=None, range=Optional[float])

slots.storage__basefreq = Slot(uri=DSS.basefreq, name="storage__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.storage__basefreq, domain=None, range=Optional[float])

slots.storage__enabled = Slot(uri=DSS.enabled, name="storage__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.storage__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.storage__like = Slot(uri=DSS.like, name="storage__like", curie=DSS.curie('like'),
                   model_uri=DSS.storage__like, domain=None, range=Optional[str])

slots.upfc__name = Slot(uri=DSS.name, name="upfc__name", curie=DSS.curie('name'),
                   model_uri=DSS.upfc__name, domain=None, range=URIRef)

slots.upfc__bus1 = Slot(uri=DSS.bus1, name="upfc__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.upfc__bus1, domain=None, range=Optional[float])

slots.upfc__bus2 = Slot(uri=DSS.bus2, name="upfc__bus2", curie=DSS.curie('bus2'),
                   model_uri=DSS.upfc__bus2, domain=None, range=Optional[float])

slots.upfc__refkv = Slot(uri=DSS.refkv, name="upfc__refkv", curie=DSS.curie('refkv'),
                   model_uri=DSS.upfc__refkv, domain=None, range=Optional[float])

slots.upfc__pf = Slot(uri=DSS.pf, name="upfc__pf", curie=DSS.curie('pf'),
                   model_uri=DSS.upfc__pf, domain=None, range=Optional[float])

slots.upfc__frequency = Slot(uri=DSS.frequency, name="upfc__frequency", curie=DSS.curie('frequency'),
                   model_uri=DSS.upfc__frequency, domain=None, range=Optional[str])

slots.upfc__phases = Slot(uri=DSS.phases, name="upfc__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.upfc__phases, domain=None, range=Optional[int])

slots.upfc__Xs = Slot(uri=DSS.Xs, name="upfc__Xs", curie=DSS.curie('Xs'),
                   model_uri=DSS.upfc__Xs, domain=None, range=Optional[float])

slots.upfc__Tol1 = Slot(uri=DSS.Tol1, name="upfc__Tol1", curie=DSS.curie('Tol1'),
                   model_uri=DSS.upfc__Tol1, domain=None, range=Optional[float])

slots.upfc__Mode = Slot(uri=DSS.Mode, name="upfc__Mode", curie=DSS.curie('Mode'),
                   model_uri=DSS.upfc__Mode, domain=None, range=Optional[int])

slots.upfc__VpqMax = Slot(uri=DSS.VpqMax, name="upfc__VpqMax", curie=DSS.curie('VpqMax'),
                   model_uri=DSS.upfc__VpqMax, domain=None, range=Optional[float])

slots.upfc__LossCurve = Slot(uri=DSS.LossCurve, name="upfc__LossCurve", curie=DSS.curie('LossCurve'),
                   model_uri=DSS.upfc__LossCurve, domain=None, range=Optional[float])

slots.upfc__VHLimit = Slot(uri=DSS.VHLimit, name="upfc__VHLimit", curie=DSS.curie('VHLimit'),
                   model_uri=DSS.upfc__VHLimit, domain=None, range=Optional[float])

slots.upfc__VLLimit = Slot(uri=DSS.VLLimit, name="upfc__VLLimit", curie=DSS.curie('VLLimit'),
                   model_uri=DSS.upfc__VLLimit, domain=None, range=Optional[float])

slots.upfc__CLimit = Slot(uri=DSS.CLimit, name="upfc__CLimit", curie=DSS.curie('CLimit'),
                   model_uri=DSS.upfc__CLimit, domain=None, range=Optional[float])

slots.upfc__refkv2 = Slot(uri=DSS.refkv2, name="upfc__refkv2", curie=DSS.curie('refkv2'),
                   model_uri=DSS.upfc__refkv2, domain=None, range=Optional[float])

slots.upfc__kvarLimit = Slot(uri=DSS.kvarLimit, name="upfc__kvarLimit", curie=DSS.curie('kvarLimit'),
                   model_uri=DSS.upfc__kvarLimit, domain=None, range=Optional[float])

slots.upfc__Element = Slot(uri=DSS.Element, name="upfc__Element", curie=DSS.curie('Element'),
                   model_uri=DSS.upfc__Element, domain=None, range=Optional[float])

slots.upfc__spectrum = Slot(uri=DSS.spectrum, name="upfc__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.upfc__spectrum, domain=None, range=Optional[str])

slots.upfc__basefreq = Slot(uri=DSS.basefreq, name="upfc__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.upfc__basefreq, domain=None, range=Optional[float])

slots.upfc__enabled = Slot(uri=DSS.enabled, name="upfc__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.upfc__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.upfc__like = Slot(uri=DSS.like, name="upfc__like", curie=DSS.curie('like'),
                   model_uri=DSS.upfc__like, domain=None, range=Optional[str])

slots.vccs__name = Slot(uri=DSS.name, name="vccs__name", curie=DSS.curie('name'),
                   model_uri=DSS.vccs__name, domain=None, range=URIRef)

slots.vccs__bus1 = Slot(uri=DSS.bus1, name="vccs__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.vccs__bus1, domain=None, range=Optional[str])

slots.vccs__phases = Slot(uri=DSS.phases, name="vccs__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.vccs__phases, domain=None, range=Optional[int])

slots.vccs__prated = Slot(uri=DSS.prated, name="vccs__prated", curie=DSS.curie('prated'),
                   model_uri=DSS.vccs__prated, domain=None, range=Optional[float])

slots.vccs__vrated = Slot(uri=DSS.vrated, name="vccs__vrated", curie=DSS.curie('vrated'),
                   model_uri=DSS.vccs__vrated, domain=None, range=Optional[float])

slots.vccs__ppct = Slot(uri=DSS.ppct, name="vccs__ppct", curie=DSS.curie('ppct'),
                   model_uri=DSS.vccs__ppct, domain=None, range=Optional[float])

slots.vccs__bp1 = Slot(uri=DSS.bp1, name="vccs__bp1", curie=DSS.curie('bp1'),
                   model_uri=DSS.vccs__bp1, domain=None, range=Optional[float])

slots.vccs__bp2 = Slot(uri=DSS.bp2, name="vccs__bp2", curie=DSS.curie('bp2'),
                   model_uri=DSS.vccs__bp2, domain=None, range=Optional[float])

slots.vccs__filter = Slot(uri=DSS.filter, name="vccs__filter", curie=DSS.curie('filter'),
                   model_uri=DSS.vccs__filter, domain=None, range=Optional[str])

slots.vccs__fsample = Slot(uri=DSS.fsample, name="vccs__fsample", curie=DSS.curie('fsample'),
                   model_uri=DSS.vccs__fsample, domain=None, range=Optional[str])

slots.vccs__rmsmode = Slot(uri=DSS.rmsmode, name="vccs__rmsmode", curie=DSS.curie('rmsmode'),
                   model_uri=DSS.vccs__rmsmode, domain=None, range=Optional[str])

slots.vccs__imaxpu = Slot(uri=DSS.imaxpu, name="vccs__imaxpu", curie=DSS.curie('imaxpu'),
                   model_uri=DSS.vccs__imaxpu, domain=None, range=Optional[float])

slots.vccs__vrmstau = Slot(uri=DSS.vrmstau, name="vccs__vrmstau", curie=DSS.curie('vrmstau'),
                   model_uri=DSS.vccs__vrmstau, domain=None, range=Optional[str])

slots.vccs__irmstau = Slot(uri=DSS.irmstau, name="vccs__irmstau", curie=DSS.curie('irmstau'),
                   model_uri=DSS.vccs__irmstau, domain=None, range=Optional[str])

slots.vccs__spectrum = Slot(uri=DSS.spectrum, name="vccs__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.vccs__spectrum, domain=None, range=Optional[str])

slots.vccs__basefreq = Slot(uri=DSS.basefreq, name="vccs__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.vccs__basefreq, domain=None, range=Optional[float])

slots.vccs__enabled = Slot(uri=DSS.enabled, name="vccs__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.vccs__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.vccs__like = Slot(uri=DSS.like, name="vccs__like", curie=DSS.curie('like'),
                   model_uri=DSS.vccs__like, domain=None, range=Optional[str])

slots.vsconverter__name = Slot(uri=DSS.name, name="vsconverter__name", curie=DSS.curie('name'),
                   model_uri=DSS.vsconverter__name, domain=None, range=URIRef)

slots.vsconverter__phases = Slot(uri=DSS.phases, name="vsconverter__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.vsconverter__phases, domain=None, range=Optional[int])

slots.vsconverter__Bus1 = Slot(uri=DSS.Bus1, name="vsconverter__Bus1", curie=DSS.curie('Bus1'),
                   model_uri=DSS.vsconverter__Bus1, domain=None, range=Optional[str])

slots.vsconverter__kVac = Slot(uri=DSS.kVac, name="vsconverter__kVac", curie=DSS.curie('kVac'),
                   model_uri=DSS.vsconverter__kVac, domain=None, range=Optional[float])

slots.vsconverter__kVdc = Slot(uri=DSS.kVdc, name="vsconverter__kVdc", curie=DSS.curie('kVdc'),
                   model_uri=DSS.vsconverter__kVdc, domain=None, range=Optional[float])

slots.vsconverter__kW = Slot(uri=DSS.kW, name="vsconverter__kW", curie=DSS.curie('kW'),
                   model_uri=DSS.vsconverter__kW, domain=None, range=Optional[float])

slots.vsconverter__Ndc = Slot(uri=DSS.Ndc, name="vsconverter__Ndc", curie=DSS.curie('Ndc'),
                   model_uri=DSS.vsconverter__Ndc, domain=None, range=Optional[int])

slots.vsconverter__Rac = Slot(uri=DSS.Rac, name="vsconverter__Rac", curie=DSS.curie('Rac'),
                   model_uri=DSS.vsconverter__Rac, domain=None, range=Optional[float])

slots.vsconverter__Xac = Slot(uri=DSS.Xac, name="vsconverter__Xac", curie=DSS.curie('Xac'),
                   model_uri=DSS.vsconverter__Xac, domain=None, range=Optional[float])

slots.vsconverter__m0 = Slot(uri=DSS.m0, name="vsconverter__m0", curie=DSS.curie('m0'),
                   model_uri=DSS.vsconverter__m0, domain=None, range=Optional[str])

slots.vsconverter__d0 = Slot(uri=DSS.d0, name="vsconverter__d0", curie=DSS.curie('d0'),
                   model_uri=DSS.vsconverter__d0, domain=None, range=Optional[float])

slots.vsconverter__Mmin = Slot(uri=DSS.Mmin, name="vsconverter__Mmin", curie=DSS.curie('Mmin'),
                   model_uri=DSS.vsconverter__Mmin, domain=None, range=Optional[str])

slots.vsconverter__Mmax = Slot(uri=DSS.Mmax, name="vsconverter__Mmax", curie=DSS.curie('Mmax'),
                   model_uri=DSS.vsconverter__Mmax, domain=None, range=Optional[str])

slots.vsconverter__Iacmax = Slot(uri=DSS.Iacmax, name="vsconverter__Iacmax", curie=DSS.curie('Iacmax'),
                   model_uri=DSS.vsconverter__Iacmax, domain=None, range=Optional[float])

slots.vsconverter__Idcmax = Slot(uri=DSS.Idcmax, name="vsconverter__Idcmax", curie=DSS.curie('Idcmax'),
                   model_uri=DSS.vsconverter__Idcmax, domain=None, range=Optional[float])

slots.vsconverter__Vacref = Slot(uri=DSS.Vacref, name="vsconverter__Vacref", curie=DSS.curie('Vacref'),
                   model_uri=DSS.vsconverter__Vacref, domain=None, range=Optional[float])

slots.vsconverter__Pacref = Slot(uri=DSS.Pacref, name="vsconverter__Pacref", curie=DSS.curie('Pacref'),
                   model_uri=DSS.vsconverter__Pacref, domain=None, range=Optional[float])

slots.vsconverter__Qacref = Slot(uri=DSS.Qacref, name="vsconverter__Qacref", curie=DSS.curie('Qacref'),
                   model_uri=DSS.vsconverter__Qacref, domain=None, range=Optional[float])

slots.vsconverter__Vdcref = Slot(uri=DSS.Vdcref, name="vsconverter__Vdcref", curie=DSS.curie('Vdcref'),
                   model_uri=DSS.vsconverter__Vdcref, domain=None, range=Optional[float])

slots.vsconverter__VscMode = Slot(uri=DSS.VscMode, name="vsconverter__VscMode", curie=DSS.curie('VscMode'),
                   model_uri=DSS.vsconverter__VscMode, domain=None, range=Optional[str])

slots.vsconverter__spectrum = Slot(uri=DSS.spectrum, name="vsconverter__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.vsconverter__spectrum, domain=None, range=Optional[str])

slots.vsconverter__basefreq = Slot(uri=DSS.basefreq, name="vsconverter__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.vsconverter__basefreq, domain=None, range=Optional[float])

slots.vsconverter__enabled = Slot(uri=DSS.enabled, name="vsconverter__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.vsconverter__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.vsconverter__like = Slot(uri=DSS.like, name="vsconverter__like", curie=DSS.curie('like'),
                   model_uri=DSS.vsconverter__like, domain=None, range=Optional[str])

slots.windgen__name = Slot(uri=DSS.name, name="windgen__name", curie=DSS.curie('name'),
                   model_uri=DSS.windgen__name, domain=None, range=URIRef)

slots.windgen__phases = Slot(uri=DSS.phases, name="windgen__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.windgen__phases, domain=None, range=Optional[int])

slots.windgen__bus1 = Slot(uri=DSS.bus1, name="windgen__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.windgen__bus1, domain=None, range=Optional[str])

slots.windgen__kv = Slot(uri=DSS.kv, name="windgen__kv", curie=DSS.curie('kv'),
                   model_uri=DSS.windgen__kv, domain=None, range=Optional[float])

slots.windgen__kW = Slot(uri=DSS.kW, name="windgen__kW", curie=DSS.curie('kW'),
                   model_uri=DSS.windgen__kW, domain=None, range=Optional[float])

slots.windgen__PF = Slot(uri=DSS.PF, name="windgen__PF", curie=DSS.curie('PF'),
                   model_uri=DSS.windgen__PF, domain=None, range=Optional[float])

slots.windgen__model = Slot(uri=DSS.model, name="windgen__model", curie=DSS.curie('model'),
                   model_uri=DSS.windgen__model, domain=None, range=Optional[int])

slots.windgen__yearly = Slot(uri=DSS.yearly, name="windgen__yearly", curie=DSS.curie('yearly'),
                   model_uri=DSS.windgen__yearly, domain=None, range=Optional[int])

slots.windgen__daily = Slot(uri=DSS.daily, name="windgen__daily", curie=DSS.curie('daily'),
                   model_uri=DSS.windgen__daily, domain=None, range=Optional[str])

slots.windgen__duty = Slot(uri=DSS.duty, name="windgen__duty", curie=DSS.curie('duty'),
                   model_uri=DSS.windgen__duty, domain=None, range=Optional[int])

slots.windgen__conn = Slot(uri=DSS.conn, name="windgen__conn", curie=DSS.curie('conn'),
                   model_uri=DSS.windgen__conn, domain=None, range=Optional[str])

slots.windgen__kvar = Slot(uri=DSS.kvar, name="windgen__kvar", curie=DSS.curie('kvar'),
                   model_uri=DSS.windgen__kvar, domain=None, range=Optional[float])

slots.windgen__class_class = Slot(uri=DSS.class_class, name="windgen__class_class", curie=DSS.curie('class_class'),
                   model_uri=DSS.windgen__class_class, domain=None, range=Optional[int])

slots.windgen__debugtrace = Slot(uri=DSS.debugtrace, name="windgen__debugtrace", curie=DSS.curie('debugtrace'),
                   model_uri=DSS.windgen__debugtrace, domain=None, range=Optional[Union[bool, Bool]])

slots.windgen__Vminpu = Slot(uri=DSS.Vminpu, name="windgen__Vminpu", curie=DSS.curie('Vminpu'),
                   model_uri=DSS.windgen__Vminpu, domain=None, range=Optional[float])

slots.windgen__Vmaxpu = Slot(uri=DSS.Vmaxpu, name="windgen__Vmaxpu", curie=DSS.curie('Vmaxpu'),
                   model_uri=DSS.windgen__Vmaxpu, domain=None, range=Optional[float])

slots.windgen__kVA = Slot(uri=DSS.kVA, name="windgen__kVA", curie=DSS.curie('kVA'),
                   model_uri=DSS.windgen__kVA, domain=None, range=Optional[float])

slots.windgen__MVA = Slot(uri=DSS.MVA, name="windgen__MVA", curie=DSS.curie('MVA'),
                   model_uri=DSS.windgen__MVA, domain=None, range=Optional[float])

slots.windgen__UserModel = Slot(uri=DSS.UserModel, name="windgen__UserModel", curie=DSS.curie('UserModel'),
                   model_uri=DSS.windgen__UserModel, domain=None, range=Optional[float])

slots.windgen__UserData = Slot(uri=DSS.UserData, name="windgen__UserData", curie=DSS.curie('UserData'),
                   model_uri=DSS.windgen__UserData, domain=None, range=Optional[str])

slots.windgen__DutyStart = Slot(uri=DSS.DutyStart, name="windgen__DutyStart", curie=DSS.curie('DutyStart'),
                   model_uri=DSS.windgen__DutyStart, domain=None, range=Optional[str])

slots.windgen__DynamicEq = Slot(uri=DSS.DynamicEq, name="windgen__DynamicEq", curie=DSS.curie('DynamicEq'),
                   model_uri=DSS.windgen__DynamicEq, domain=None, range=Optional[str])

slots.windgen__DynOut = Slot(uri=DSS.DynOut, name="windgen__DynOut", curie=DSS.curie('DynOut'),
                   model_uri=DSS.windgen__DynOut, domain=None, range=Optional[float])

slots.windgen__Rthev = Slot(uri=DSS.Rthev, name="windgen__Rthev", curie=DSS.curie('Rthev'),
                   model_uri=DSS.windgen__Rthev, domain=None, range=Optional[str])

slots.windgen__Xthev = Slot(uri=DSS.Xthev, name="windgen__Xthev", curie=DSS.curie('Xthev'),
                   model_uri=DSS.windgen__Xthev, domain=None, range=Optional[str])

slots.windgen__Vss = Slot(uri=DSS.Vss, name="windgen__Vss", curie=DSS.curie('Vss'),
                   model_uri=DSS.windgen__Vss, domain=None, range=Optional[float])

slots.windgen__Pss = Slot(uri=DSS.Pss, name="windgen__Pss", curie=DSS.curie('Pss'),
                   model_uri=DSS.windgen__Pss, domain=None, range=Optional[float])

slots.windgen__Qss = Slot(uri=DSS.Qss, name="windgen__Qss", curie=DSS.curie('Qss'),
                   model_uri=DSS.windgen__Qss, domain=None, range=Optional[float])

slots.windgen__vwind = Slot(uri=DSS.vwind, name="windgen__vwind", curie=DSS.curie('vwind'),
                   model_uri=DSS.windgen__vwind, domain=None, range=Optional[str])

slots.windgen__QMode = Slot(uri=DSS.QMode, name="windgen__QMode", curie=DSS.curie('QMode'),
                   model_uri=DSS.windgen__QMode, domain=None, range=Optional[str])

slots.windgen__SimMechFlg = Slot(uri=DSS.SimMechFlg, name="windgen__SimMechFlg", curie=DSS.curie('SimMechFlg'),
                   model_uri=DSS.windgen__SimMechFlg, domain=None, range=Optional[float])

slots.windgen__APCFlg = Slot(uri=DSS.APCFlg, name="windgen__APCFlg", curie=DSS.curie('APCFlg'),
                   model_uri=DSS.windgen__APCFlg, domain=None, range=Optional[float])

slots.windgen__QFlg = Slot(uri=DSS.QFlg, name="windgen__QFlg", curie=DSS.curie('QFlg'),
                   model_uri=DSS.windgen__QFlg, domain=None, range=Optional[float])

slots.windgen__delt0 = Slot(uri=DSS.delt0, name="windgen__delt0", curie=DSS.curie('delt0'),
                   model_uri=DSS.windgen__delt0, domain=None, range=Optional[str])

slots.windgen__N_WTG = Slot(uri=DSS.N_WTG, name="windgen__N_WTG", curie=DSS.curie('N_WTG'),
                   model_uri=DSS.windgen__N_WTG, domain=None, range=Optional[int])

slots.windgen__VV_Curve = Slot(uri=DSS.VV_Curve, name="windgen__VV_Curve", curie=DSS.curie('VV_Curve'),
                   model_uri=DSS.windgen__VV_Curve, domain=None, range=Optional[str])

slots.windgen__Ag = Slot(uri=DSS.Ag, name="windgen__Ag", curie=DSS.curie('Ag'),
                   model_uri=DSS.windgen__Ag, domain=None, range=Optional[str])

slots.windgen__Cp = Slot(uri=DSS.Cp, name="windgen__Cp", curie=DSS.curie('Cp'),
                   model_uri=DSS.windgen__Cp, domain=None, range=Optional[str])

slots.windgen__Lamda = Slot(uri=DSS.Lamda, name="windgen__Lamda", curie=DSS.curie('Lamda'),
                   model_uri=DSS.windgen__Lamda, domain=None, range=Optional[str])

slots.windgen__P = Slot(uri=DSS.P, name="windgen__P", curie=DSS.curie('P'),
                   model_uri=DSS.windgen__P, domain=None, range=Optional[int])

slots.windgen__pd = Slot(uri=DSS.pd, name="windgen__pd", curie=DSS.curie('pd'),
                   model_uri=DSS.windgen__pd, domain=None, range=Optional[str])

slots.windgen__PLoss = Slot(uri=DSS.PLoss, name="windgen__PLoss", curie=DSS.curie('PLoss'),
                   model_uri=DSS.windgen__PLoss, domain=None, range=Optional[float])

slots.windgen__Rad = Slot(uri=DSS.Rad, name="windgen__Rad", curie=DSS.curie('Rad'),
                   model_uri=DSS.windgen__Rad, domain=None, range=Optional[str])

slots.windgen__VCutIn = Slot(uri=DSS.VCutIn, name="windgen__VCutIn", curie=DSS.curie('VCutIn'),
                   model_uri=DSS.windgen__VCutIn, domain=None, range=Optional[str])

slots.windgen__VCutOut = Slot(uri=DSS.VCutOut, name="windgen__VCutOut", curie=DSS.curie('VCutOut'),
                   model_uri=DSS.windgen__VCutOut, domain=None, range=Optional[str])

slots.windgen__spectrum = Slot(uri=DSS.spectrum, name="windgen__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.windgen__spectrum, domain=None, range=Optional[float])

slots.windgen__basefreq = Slot(uri=DSS.basefreq, name="windgen__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.windgen__basefreq, domain=None, range=Optional[float])

slots.windgen__enabled = Slot(uri=DSS.enabled, name="windgen__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.windgen__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.windgen__like = Slot(uri=DSS.like, name="windgen__like", curie=DSS.curie('like'),
                   model_uri=DSS.windgen__like, domain=None, range=Optional[str])

slots.autotrans__name = Slot(uri=DSS.name, name="autotrans__name", curie=DSS.curie('name'),
                   model_uri=DSS.autotrans__name, domain=None, range=URIRef)

slots.autotrans__phases = Slot(uri=DSS.phases, name="autotrans__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.autotrans__phases, domain=None, range=Optional[int])

slots.autotrans__windings = Slot(uri=DSS.windings, name="autotrans__windings", curie=DSS.curie('windings'),
                   model_uri=DSS.autotrans__windings, domain=None, range=Optional[int])

slots.autotrans__wdg = Slot(uri=DSS.wdg, name="autotrans__wdg", curie=DSS.curie('wdg'),
                   model_uri=DSS.autotrans__wdg, domain=None, range=Optional[int])

slots.autotrans__bus = Slot(uri=DSS.bus, name="autotrans__bus", curie=DSS.curie('bus'),
                   model_uri=DSS.autotrans__bus, domain=None, range=Optional[str])

slots.autotrans__conn = Slot(uri=DSS.conn, name="autotrans__conn", curie=DSS.curie('conn'),
                   model_uri=DSS.autotrans__conn, domain=None, range=Optional[str])

slots.autotrans__kV = Slot(uri=DSS.kV, name="autotrans__kV", curie=DSS.curie('kV'),
                   model_uri=DSS.autotrans__kV, domain=None, range=Optional[float])

slots.autotrans__kVA = Slot(uri=DSS.kVA, name="autotrans__kVA", curie=DSS.curie('kVA'),
                   model_uri=DSS.autotrans__kVA, domain=None, range=Optional[float])

slots.autotrans__tap = Slot(uri=DSS.tap, name="autotrans__tap", curie=DSS.curie('tap'),
                   model_uri=DSS.autotrans__tap, domain=None, range=Optional[str])

slots.autotrans__pct_R = Slot(uri=DSS.pct_R, name="autotrans__pct_R", curie=DSS.curie('pct_R'),
                   model_uri=DSS.autotrans__pct_R, domain=None, range=Optional[float])

slots.autotrans__Rdcohms = Slot(uri=DSS.Rdcohms, name="autotrans__Rdcohms", curie=DSS.curie('Rdcohms'),
                   model_uri=DSS.autotrans__Rdcohms, domain=None, range=Optional[int])

slots.autotrans__Core = Slot(uri=DSS.Core, name="autotrans__Core", curie=DSS.curie('Core'),
                   model_uri=DSS.autotrans__Core, domain=None, range=Optional[str])

slots.autotrans__buses = Slot(uri=DSS.buses, name="autotrans__buses", curie=DSS.curie('buses'),
                   model_uri=DSS.autotrans__buses, domain=None, range=Optional[Union[str, list[str]]])

slots.autotrans__conns = Slot(uri=DSS.conns, name="autotrans__conns", curie=DSS.curie('conns'),
                   model_uri=DSS.autotrans__conns, domain=None, range=Optional[Union[str, list[str]]])

slots.autotrans__kVs = Slot(uri=DSS.kVs, name="autotrans__kVs", curie=DSS.curie('kVs'),
                   model_uri=DSS.autotrans__kVs, domain=None, range=Optional[Union[float, list[float]]])

slots.autotrans__kVAs = Slot(uri=DSS.kVAs, name="autotrans__kVAs", curie=DSS.curie('kVAs'),
                   model_uri=DSS.autotrans__kVAs, domain=None, range=Optional[Union[float, list[float]]])

slots.autotrans__taps = Slot(uri=DSS.taps, name="autotrans__taps", curie=DSS.curie('taps'),
                   model_uri=DSS.autotrans__taps, domain=None, range=Optional[str])

slots.autotrans__XHX = Slot(uri=DSS.XHX, name="autotrans__XHX", curie=DSS.curie('XHX'),
                   model_uri=DSS.autotrans__XHX, domain=None, range=Optional[float])

slots.autotrans__XHT = Slot(uri=DSS.XHT, name="autotrans__XHT", curie=DSS.curie('XHT'),
                   model_uri=DSS.autotrans__XHT, domain=None, range=Optional[float])

slots.autotrans__XXT = Slot(uri=DSS.XXT, name="autotrans__XXT", curie=DSS.curie('XXT'),
                   model_uri=DSS.autotrans__XXT, domain=None, range=Optional[float])

slots.autotrans__XSCarray = Slot(uri=DSS.XSCarray, name="autotrans__XSCarray", curie=DSS.curie('XSCarray'),
                   model_uri=DSS.autotrans__XSCarray, domain=None, range=Optional[Union[float, list[float]]])

slots.autotrans__thermal = Slot(uri=DSS.thermal, name="autotrans__thermal", curie=DSS.curie('thermal'),
                   model_uri=DSS.autotrans__thermal, domain=None, range=Optional[str])

slots.autotrans__n = Slot(uri=DSS.n, name="autotrans__n", curie=DSS.curie('n'),
                   model_uri=DSS.autotrans__n, domain=None, range=Optional[str])

slots.autotrans__m = Slot(uri=DSS.m, name="autotrans__m", curie=DSS.curie('m'),
                   model_uri=DSS.autotrans__m, domain=None, range=Optional[str])

slots.autotrans__flrise = Slot(uri=DSS.flrise, name="autotrans__flrise", curie=DSS.curie('flrise'),
                   model_uri=DSS.autotrans__flrise, domain=None, range=Optional[str])

slots.autotrans__hsrise = Slot(uri=DSS.hsrise, name="autotrans__hsrise", curie=DSS.curie('hsrise'),
                   model_uri=DSS.autotrans__hsrise, domain=None, range=Optional[str])

slots.autotrans__pct_loadloss = Slot(uri=DSS.pct_loadloss, name="autotrans__pct_loadloss", curie=DSS.curie('pct_loadloss'),
                   model_uri=DSS.autotrans__pct_loadloss, domain=None, range=Optional[float])

slots.autotrans__pct_noloadloss = Slot(uri=DSS.pct_noloadloss, name="autotrans__pct_noloadloss", curie=DSS.curie('pct_noloadloss'),
                   model_uri=DSS.autotrans__pct_noloadloss, domain=None, range=Optional[float])

slots.autotrans__normhkVA = Slot(uri=DSS.normhkVA, name="autotrans__normhkVA", curie=DSS.curie('normhkVA'),
                   model_uri=DSS.autotrans__normhkVA, domain=None, range=Optional[float])

slots.autotrans__emerghkVA = Slot(uri=DSS.emerghkVA, name="autotrans__emerghkVA", curie=DSS.curie('emerghkVA'),
                   model_uri=DSS.autotrans__emerghkVA, domain=None, range=Optional[float])

slots.autotrans__sub = Slot(uri=DSS.sub, name="autotrans__sub", curie=DSS.curie('sub'),
                   model_uri=DSS.autotrans__sub, domain=None, range=Optional[Union[bool, Bool]])

slots.autotrans__MaxTap = Slot(uri=DSS.MaxTap, name="autotrans__MaxTap", curie=DSS.curie('MaxTap'),
                   model_uri=DSS.autotrans__MaxTap, domain=None, range=Optional[str])

slots.autotrans__MinTap = Slot(uri=DSS.MinTap, name="autotrans__MinTap", curie=DSS.curie('MinTap'),
                   model_uri=DSS.autotrans__MinTap, domain=None, range=Optional[str])

slots.autotrans__NumTaps = Slot(uri=DSS.NumTaps, name="autotrans__NumTaps", curie=DSS.curie('NumTaps'),
                   model_uri=DSS.autotrans__NumTaps, domain=None, range=Optional[int])

slots.autotrans__subname = Slot(uri=DSS.subname, name="autotrans__subname", curie=DSS.curie('subname'),
                   model_uri=DSS.autotrans__subname, domain=None, range=Optional[str])

slots.autotrans__pct_imag = Slot(uri=DSS.pct_imag, name="autotrans__pct_imag", curie=DSS.curie('pct_imag'),
                   model_uri=DSS.autotrans__pct_imag, domain=None, range=Optional[float])

slots.autotrans__ppm_antifloat = Slot(uri=DSS.ppm_antifloat, name="autotrans__ppm_antifloat", curie=DSS.curie('ppm_antifloat'),
                   model_uri=DSS.autotrans__ppm_antifloat, domain=None, range=Optional[float])

slots.autotrans__pct_Rs = Slot(uri=DSS.pct_Rs, name="autotrans__pct_Rs", curie=DSS.curie('pct_Rs'),
                   model_uri=DSS.autotrans__pct_Rs, domain=None, range=Optional[Union[float, list[float]]])

slots.autotrans__bank = Slot(uri=DSS.bank, name="autotrans__bank", curie=DSS.curie('bank'),
                   model_uri=DSS.autotrans__bank, domain=None, range=Optional[str])

slots.autotrans__XfmrCode = Slot(uri=DSS.XfmrCode, name="autotrans__XfmrCode", curie=DSS.curie('XfmrCode'),
                   model_uri=DSS.autotrans__XfmrCode, domain=None, range=Optional[str])

slots.autotrans__XRConst = Slot(uri=DSS.XRConst, name="autotrans__XRConst", curie=DSS.curie('XRConst'),
                   model_uri=DSS.autotrans__XRConst, domain=None, range=Optional[Union[bool, Bool]])

slots.autotrans__LeadLag = Slot(uri=DSS.LeadLag, name="autotrans__LeadLag", curie=DSS.curie('LeadLag'),
                   model_uri=DSS.autotrans__LeadLag, domain=None, range=Optional[str])

slots.autotrans__WdgCurrents = Slot(uri=DSS.WdgCurrents, name="autotrans__WdgCurrents", curie=DSS.curie('WdgCurrents'),
                   model_uri=DSS.autotrans__WdgCurrents, domain=None, range=Optional[float])

slots.autotrans__normamps = Slot(uri=DSS.normamps, name="autotrans__normamps", curie=DSS.curie('normamps'),
                   model_uri=DSS.autotrans__normamps, domain=None, range=Optional[float])

slots.autotrans__emergamps = Slot(uri=DSS.emergamps, name="autotrans__emergamps", curie=DSS.curie('emergamps'),
                   model_uri=DSS.autotrans__emergamps, domain=None, range=Optional[float])

slots.autotrans__faultrate = Slot(uri=DSS.faultrate, name="autotrans__faultrate", curie=DSS.curie('faultrate'),
                   model_uri=DSS.autotrans__faultrate, domain=None, range=Optional[str])

slots.autotrans__pctperm = Slot(uri=DSS.pctperm, name="autotrans__pctperm", curie=DSS.curie('pctperm'),
                   model_uri=DSS.autotrans__pctperm, domain=None, range=Optional[float])

slots.autotrans__repair = Slot(uri=DSS.repair, name="autotrans__repair", curie=DSS.curie('repair'),
                   model_uri=DSS.autotrans__repair, domain=None, range=Optional[str])

slots.autotrans__basefreq = Slot(uri=DSS.basefreq, name="autotrans__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.autotrans__basefreq, domain=None, range=Optional[float])

slots.autotrans__enabled = Slot(uri=DSS.enabled, name="autotrans__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.autotrans__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.autotrans__like = Slot(uri=DSS.like, name="autotrans__like", curie=DSS.curie('like'),
                   model_uri=DSS.autotrans__like, domain=None, range=Optional[str])

slots.capacitor__name = Slot(uri=DSS.name, name="capacitor__name", curie=DSS.curie('name'),
                   model_uri=DSS.capacitor__name, domain=None, range=URIRef)

slots.capacitor__bus1 = Slot(uri=DSS.bus1, name="capacitor__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.capacitor__bus1, domain=None, range=Optional[str])

slots.capacitor__bus2 = Slot(uri=DSS.bus2, name="capacitor__bus2", curie=DSS.curie('bus2'),
                   model_uri=DSS.capacitor__bus2, domain=None, range=Optional[str])

slots.capacitor__phases = Slot(uri=DSS.phases, name="capacitor__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.capacitor__phases, domain=None, range=Optional[int])

slots.capacitor__kvar = Slot(uri=DSS.kvar, name="capacitor__kvar", curie=DSS.curie('kvar'),
                   model_uri=DSS.capacitor__kvar, domain=None, range=Optional[Union[float, list[float]]])

slots.capacitor__kv = Slot(uri=DSS.kv, name="capacitor__kv", curie=DSS.curie('kv'),
                   model_uri=DSS.capacitor__kv, domain=None, range=Optional[float])

slots.capacitor__conn = Slot(uri=DSS.conn, name="capacitor__conn", curie=DSS.curie('conn'),
                   model_uri=DSS.capacitor__conn, domain=None, range=Optional[Union[str, "ConnectionType"]])

slots.capacitor__cmatrix = Slot(uri=DSS.cmatrix, name="capacitor__cmatrix", curie=DSS.curie('cmatrix'),
                   model_uri=DSS.capacitor__cmatrix, domain=None, range=Optional[Union[float, list[float]]])

slots.capacitor__cuf = Slot(uri=DSS.cuf, name="capacitor__cuf", curie=DSS.curie('cuf'),
                   model_uri=DSS.capacitor__cuf, domain=None, range=Optional[Union[float, list[float]]])

slots.capacitor__R = Slot(uri=DSS.R, name="capacitor__R", curie=DSS.curie('R'),
                   model_uri=DSS.capacitor__R, domain=None, range=Optional[Union[float, list[float]]])

slots.capacitor__XL = Slot(uri=DSS.XL, name="capacitor__XL", curie=DSS.curie('XL'),
                   model_uri=DSS.capacitor__XL, domain=None, range=Optional[Union[float, list[float]]])

slots.capacitor__Harm = Slot(uri=DSS.Harm, name="capacitor__Harm", curie=DSS.curie('Harm'),
                   model_uri=DSS.capacitor__Harm, domain=None, range=Optional[Union[float, list[float]]])

slots.capacitor__Numsteps = Slot(uri=DSS.Numsteps, name="capacitor__Numsteps", curie=DSS.curie('Numsteps'),
                   model_uri=DSS.capacitor__Numsteps, domain=None, range=Optional[int])

slots.capacitor__states = Slot(uri=DSS.states, name="capacitor__states", curie=DSS.curie('states'),
                   model_uri=DSS.capacitor__states, domain=None, range=Optional[Union[int, list[int]]])

slots.capacitor__normamps = Slot(uri=DSS.normamps, name="capacitor__normamps", curie=DSS.curie('normamps'),
                   model_uri=DSS.capacitor__normamps, domain=None, range=Optional[float])

slots.capacitor__emergamps = Slot(uri=DSS.emergamps, name="capacitor__emergamps", curie=DSS.curie('emergamps'),
                   model_uri=DSS.capacitor__emergamps, domain=None, range=Optional[float])

slots.capacitor__faultrate = Slot(uri=DSS.faultrate, name="capacitor__faultrate", curie=DSS.curie('faultrate'),
                   model_uri=DSS.capacitor__faultrate, domain=None, range=Optional[str])

slots.capacitor__pctperm = Slot(uri=DSS.pctperm, name="capacitor__pctperm", curie=DSS.curie('pctperm'),
                   model_uri=DSS.capacitor__pctperm, domain=None, range=Optional[float])

slots.capacitor__repair = Slot(uri=DSS.repair, name="capacitor__repair", curie=DSS.curie('repair'),
                   model_uri=DSS.capacitor__repair, domain=None, range=Optional[str])

slots.capacitor__basefreq = Slot(uri=DSS.basefreq, name="capacitor__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.capacitor__basefreq, domain=None, range=Optional[float])

slots.capacitor__enabled = Slot(uri=DSS.enabled, name="capacitor__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.capacitor__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.capacitor__like = Slot(uri=DSS.like, name="capacitor__like", curie=DSS.curie('like'),
                   model_uri=DSS.capacitor__like, domain=None, range=Optional[str])

slots.gictransformer__name = Slot(uri=DSS.name, name="gictransformer__name", curie=DSS.curie('name'),
                   model_uri=DSS.gictransformer__name, domain=None, range=URIRef)

slots.gictransformer__BusH = Slot(uri=DSS.BusH, name="gictransformer__BusH", curie=DSS.curie('BusH'),
                   model_uri=DSS.gictransformer__BusH, domain=None, range=Optional[str])

slots.gictransformer__BusNH = Slot(uri=DSS.BusNH, name="gictransformer__BusNH", curie=DSS.curie('BusNH'),
                   model_uri=DSS.gictransformer__BusNH, domain=None, range=Optional[str])

slots.gictransformer__BusX = Slot(uri=DSS.BusX, name="gictransformer__BusX", curie=DSS.curie('BusX'),
                   model_uri=DSS.gictransformer__BusX, domain=None, range=Optional[str])

slots.gictransformer__BusNX = Slot(uri=DSS.BusNX, name="gictransformer__BusNX", curie=DSS.curie('BusNX'),
                   model_uri=DSS.gictransformer__BusNX, domain=None, range=Optional[str])

slots.gictransformer__phases = Slot(uri=DSS.phases, name="gictransformer__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.gictransformer__phases, domain=None, range=Optional[int])

slots.gictransformer__Type = Slot(uri=DSS.Type, name="gictransformer__Type", curie=DSS.curie('Type'),
                   model_uri=DSS.gictransformer__Type, domain=None, range=Optional[str])

slots.gictransformer__R1 = Slot(uri=DSS.R1, name="gictransformer__R1", curie=DSS.curie('R1'),
                   model_uri=DSS.gictransformer__R1, domain=None, range=Optional[float])

slots.gictransformer__R2 = Slot(uri=DSS.R2, name="gictransformer__R2", curie=DSS.curie('R2'),
                   model_uri=DSS.gictransformer__R2, domain=None, range=Optional[float])

slots.gictransformer__KVLL1 = Slot(uri=DSS.KVLL1, name="gictransformer__KVLL1", curie=DSS.curie('KVLL1'),
                   model_uri=DSS.gictransformer__KVLL1, domain=None, range=Optional[float])

slots.gictransformer__KVLL2 = Slot(uri=DSS.KVLL2, name="gictransformer__KVLL2", curie=DSS.curie('KVLL2'),
                   model_uri=DSS.gictransformer__KVLL2, domain=None, range=Optional[float])

slots.gictransformer__MVA = Slot(uri=DSS.MVA, name="gictransformer__MVA", curie=DSS.curie('MVA'),
                   model_uri=DSS.gictransformer__MVA, domain=None, range=Optional[float])

slots.gictransformer__VarCurve = Slot(uri=DSS.VarCurve, name="gictransformer__VarCurve", curie=DSS.curie('VarCurve'),
                   model_uri=DSS.gictransformer__VarCurve, domain=None, range=Optional[float])

slots.gictransformer__pct_R1 = Slot(uri=DSS.pct_R1, name="gictransformer__pct_R1", curie=DSS.curie('pct_R1'),
                   model_uri=DSS.gictransformer__pct_R1, domain=None, range=Optional[float])

slots.gictransformer__pct_R2 = Slot(uri=DSS.pct_R2, name="gictransformer__pct_R2", curie=DSS.curie('pct_R2'),
                   model_uri=DSS.gictransformer__pct_R2, domain=None, range=Optional[float])

slots.gictransformer__K = Slot(uri=DSS.K, name="gictransformer__K", curie=DSS.curie('K'),
                   model_uri=DSS.gictransformer__K, domain=None, range=Optional[float])

slots.gictransformer__normamps = Slot(uri=DSS.normamps, name="gictransformer__normamps", curie=DSS.curie('normamps'),
                   model_uri=DSS.gictransformer__normamps, domain=None, range=Optional[float])

slots.gictransformer__emergamps = Slot(uri=DSS.emergamps, name="gictransformer__emergamps", curie=DSS.curie('emergamps'),
                   model_uri=DSS.gictransformer__emergamps, domain=None, range=Optional[float])

slots.gictransformer__faultrate = Slot(uri=DSS.faultrate, name="gictransformer__faultrate", curie=DSS.curie('faultrate'),
                   model_uri=DSS.gictransformer__faultrate, domain=None, range=Optional[str])

slots.gictransformer__pctperm = Slot(uri=DSS.pctperm, name="gictransformer__pctperm", curie=DSS.curie('pctperm'),
                   model_uri=DSS.gictransformer__pctperm, domain=None, range=Optional[float])

slots.gictransformer__repair = Slot(uri=DSS.repair, name="gictransformer__repair", curie=DSS.curie('repair'),
                   model_uri=DSS.gictransformer__repair, domain=None, range=Optional[str])

slots.gictransformer__basefreq = Slot(uri=DSS.basefreq, name="gictransformer__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.gictransformer__basefreq, domain=None, range=Optional[float])

slots.gictransformer__enabled = Slot(uri=DSS.enabled, name="gictransformer__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.gictransformer__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.gictransformer__like = Slot(uri=DSS.like, name="gictransformer__like", curie=DSS.curie('like'),
                   model_uri=DSS.gictransformer__like, domain=None, range=Optional[str])

slots.line__name = Slot(uri=DSS.name, name="line__name", curie=DSS.curie('name'),
                   model_uri=DSS.line__name, domain=None, range=URIRef)

slots.line__bus1 = Slot(uri=DSS.bus1, name="line__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.line__bus1, domain=None, range=str)

slots.line__bus2 = Slot(uri=DSS.bus2, name="line__bus2", curie=DSS.curie('bus2'),
                   model_uri=DSS.line__bus2, domain=None, range=Optional[str])

slots.line__linecode = Slot(uri=DSS.linecode, name="line__linecode", curie=DSS.curie('linecode'),
                   model_uri=DSS.line__linecode, domain=None, range=Optional[str])

slots.line__length = Slot(uri=DSS.length, name="line__length", curie=DSS.curie('length'),
                   model_uri=DSS.line__length, domain=None, range=Optional[float])

slots.line__phases = Slot(uri=DSS.phases, name="line__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.line__phases, domain=None, range=Optional[int])

slots.line__r1 = Slot(uri=DSS.r1, name="line__r1", curie=DSS.curie('r1'),
                   model_uri=DSS.line__r1, domain=None, range=Optional[float])

slots.line__x1 = Slot(uri=DSS.x1, name="line__x1", curie=DSS.curie('x1'),
                   model_uri=DSS.line__x1, domain=None, range=Optional[float])

slots.line__r0 = Slot(uri=DSS.r0, name="line__r0", curie=DSS.curie('r0'),
                   model_uri=DSS.line__r0, domain=None, range=Optional[float])

slots.line__x0 = Slot(uri=DSS.x0, name="line__x0", curie=DSS.curie('x0'),
                   model_uri=DSS.line__x0, domain=None, range=Optional[float])

slots.line__C1 = Slot(uri=DSS.C1, name="line__C1", curie=DSS.curie('C1'),
                   model_uri=DSS.line__C1, domain=None, range=Optional[float])

slots.line__C0 = Slot(uri=DSS.C0, name="line__C0", curie=DSS.curie('C0'),
                   model_uri=DSS.line__C0, domain=None, range=Optional[float])

slots.line__rmatrix = Slot(uri=DSS.rmatrix, name="line__rmatrix", curie=DSS.curie('rmatrix'),
                   model_uri=DSS.line__rmatrix, domain=None, range=Optional[Union[float, list[float]]])

slots.line__xmatrix = Slot(uri=DSS.xmatrix, name="line__xmatrix", curie=DSS.curie('xmatrix'),
                   model_uri=DSS.line__xmatrix, domain=None, range=Optional[Union[float, list[float]]])

slots.line__cmatrix = Slot(uri=DSS.cmatrix, name="line__cmatrix", curie=DSS.curie('cmatrix'),
                   model_uri=DSS.line__cmatrix, domain=None, range=Optional[Union[float, list[float]]])

slots.line__Switch = Slot(uri=DSS.Switch, name="line__Switch", curie=DSS.curie('Switch'),
                   model_uri=DSS.line__Switch, domain=None, range=Optional[Union[bool, Bool]])

slots.line__Rg = Slot(uri=DSS.Rg, name="line__Rg", curie=DSS.curie('Rg'),
                   model_uri=DSS.line__Rg, domain=None, range=Optional[float])

slots.line__Xg = Slot(uri=DSS.Xg, name="line__Xg", curie=DSS.curie('Xg'),
                   model_uri=DSS.line__Xg, domain=None, range=Optional[float])

slots.line__rho = Slot(uri=DSS.rho, name="line__rho", curie=DSS.curie('rho'),
                   model_uri=DSS.line__rho, domain=None, range=Optional[float])

slots.line__geometry = Slot(uri=DSS.geometry, name="line__geometry", curie=DSS.curie('geometry'),
                   model_uri=DSS.line__geometry, domain=None, range=Optional[str])

slots.line__units = Slot(uri=DSS.units, name="line__units", curie=DSS.curie('units'),
                   model_uri=DSS.line__units, domain=None, range=Optional[Union[str, "LengthUnit"]])

slots.line__spacing = Slot(uri=DSS.spacing, name="line__spacing", curie=DSS.curie('spacing'),
                   model_uri=DSS.line__spacing, domain=None, range=Optional[str])

slots.line__cncables = Slot(uri=DSS.cncables, name="line__cncables", curie=DSS.curie('cncables'),
                   model_uri=DSS.line__cncables, domain=None, range=Optional[Union[str, list[str]]])

slots.line__tscables = Slot(uri=DSS.tscables, name="line__tscables", curie=DSS.curie('tscables'),
                   model_uri=DSS.line__tscables, domain=None, range=Optional[Union[str, list[str]]])

slots.line__wires = Slot(uri=DSS.wires, name="line__wires", curie=DSS.curie('wires'),
                   model_uri=DSS.line__wires, domain=None, range=Optional[Union[str, list[str]]])

slots.line__EarthModel = Slot(uri=DSS.EarthModel, name="line__EarthModel", curie=DSS.curie('EarthModel'),
                   model_uri=DSS.line__EarthModel, domain=None, range=Optional[Union[str, "EarthModelType"]])

slots.line__B1 = Slot(uri=DSS.B1, name="line__B1", curie=DSS.curie('B1'),
                   model_uri=DSS.line__B1, domain=None, range=Optional[float])

slots.line__B0 = Slot(uri=DSS.B0, name="line__B0", curie=DSS.curie('B0'),
                   model_uri=DSS.line__B0, domain=None, range=Optional[float])

slots.line__Seasons = Slot(uri=DSS.Seasons, name="line__Seasons", curie=DSS.curie('Seasons'),
                   model_uri=DSS.line__Seasons, domain=None, range=Optional[int])

slots.line__Ratings = Slot(uri=DSS.Ratings, name="line__Ratings", curie=DSS.curie('Ratings'),
                   model_uri=DSS.line__Ratings, domain=None, range=Optional[Union[float, list[float]]])

slots.line__LineType = Slot(uri=DSS.LineType, name="line__LineType", curie=DSS.curie('LineType'),
                   model_uri=DSS.line__LineType, domain=None, range=Optional[Union[str, "LineTypeCode"]])

slots.line__EpsRmedium = Slot(uri=DSS.EpsRmedium, name="line__EpsRmedium", curie=DSS.curie('EpsRmedium'),
                   model_uri=DSS.line__EpsRmedium, domain=None, range=Optional[float])

slots.line__HeightOffset = Slot(uri=DSS.HeightOffset, name="line__HeightOffset", curie=DSS.curie('HeightOffset'),
                   model_uri=DSS.line__HeightOffset, domain=None, range=Optional[float])

slots.line__HeightUnit = Slot(uri=DSS.HeightUnit, name="line__HeightUnit", curie=DSS.curie('HeightUnit'),
                   model_uri=DSS.line__HeightUnit, domain=None, range=Optional[Union[str, "LengthUnit"]])

slots.line__conductors = Slot(uri=DSS.conductors, name="line__conductors", curie=DSS.curie('conductors'),
                   model_uri=DSS.line__conductors, domain=None, range=Optional[Union[str, list[str]]])

slots.line__normamps = Slot(uri=DSS.normamps, name="line__normamps", curie=DSS.curie('normamps'),
                   model_uri=DSS.line__normamps, domain=None, range=Optional[float])

slots.line__emergamps = Slot(uri=DSS.emergamps, name="line__emergamps", curie=DSS.curie('emergamps'),
                   model_uri=DSS.line__emergamps, domain=None, range=Optional[float])

slots.line__faultrate = Slot(uri=DSS.faultrate, name="line__faultrate", curie=DSS.curie('faultrate'),
                   model_uri=DSS.line__faultrate, domain=None, range=Optional[float])

slots.line__pct_perm = Slot(uri=DSS.pct_perm, name="line__pct_perm", curie=DSS.curie('pct_perm'),
                   model_uri=DSS.line__pct_perm, domain=None, range=Optional[float])

slots.line__repair = Slot(uri=DSS.repair, name="line__repair", curie=DSS.curie('repair'),
                   model_uri=DSS.line__repair, domain=None, range=Optional[float])

slots.line__basefreq = Slot(uri=DSS.basefreq, name="line__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.line__basefreq, domain=None, range=Optional[float])

slots.line__enabled = Slot(uri=DSS.enabled, name="line__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.line__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.line__like = Slot(uri=DSS.like, name="line__like", curie=DSS.curie('like'),
                   model_uri=DSS.line__like, domain=None, range=Optional[str])

slots.reactor__name = Slot(uri=DSS.name, name="reactor__name", curie=DSS.curie('name'),
                   model_uri=DSS.reactor__name, domain=None, range=URIRef)

slots.reactor__bus1 = Slot(uri=DSS.bus1, name="reactor__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.reactor__bus1, domain=None, range=Optional[str])

slots.reactor__bus2 = Slot(uri=DSS.bus2, name="reactor__bus2", curie=DSS.curie('bus2'),
                   model_uri=DSS.reactor__bus2, domain=None, range=Optional[str])

slots.reactor__phases = Slot(uri=DSS.phases, name="reactor__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.reactor__phases, domain=None, range=Optional[int])

slots.reactor__kvar = Slot(uri=DSS.kvar, name="reactor__kvar", curie=DSS.curie('kvar'),
                   model_uri=DSS.reactor__kvar, domain=None, range=Optional[float])

slots.reactor__kv = Slot(uri=DSS.kv, name="reactor__kv", curie=DSS.curie('kv'),
                   model_uri=DSS.reactor__kv, domain=None, range=Optional[float])

slots.reactor__conn = Slot(uri=DSS.conn, name="reactor__conn", curie=DSS.curie('conn'),
                   model_uri=DSS.reactor__conn, domain=None, range=Optional[str])

slots.reactor__Rmatrix = Slot(uri=DSS.Rmatrix, name="reactor__Rmatrix", curie=DSS.curie('Rmatrix'),
                   model_uri=DSS.reactor__Rmatrix, domain=None, range=Optional[int])

slots.reactor__Xmatrix = Slot(uri=DSS.Xmatrix, name="reactor__Xmatrix", curie=DSS.curie('Xmatrix'),
                   model_uri=DSS.reactor__Xmatrix, domain=None, range=Optional[int])

slots.reactor__Parallel = Slot(uri=DSS.Parallel, name="reactor__Parallel", curie=DSS.curie('Parallel'),
                   model_uri=DSS.reactor__Parallel, domain=None, range=Optional[Union[bool, Bool]])

slots.reactor__R = Slot(uri=DSS.R, name="reactor__R", curie=DSS.curie('R'),
                   model_uri=DSS.reactor__R, domain=None, range=Optional[float])

slots.reactor__X = Slot(uri=DSS.X, name="reactor__X", curie=DSS.curie('X'),
                   model_uri=DSS.reactor__X, domain=None, range=Optional[float])

slots.reactor__Rp = Slot(uri=DSS.Rp, name="reactor__Rp", curie=DSS.curie('Rp'),
                   model_uri=DSS.reactor__Rp, domain=None, range=Optional[float])

slots.reactor__Z1 = Slot(uri=DSS.Z1, name="reactor__Z1", curie=DSS.curie('Z1'),
                   model_uri=DSS.reactor__Z1, domain=None, range=Optional[Union[float, list[float]]])

slots.reactor__Z2 = Slot(uri=DSS.Z2, name="reactor__Z2", curie=DSS.curie('Z2'),
                   model_uri=DSS.reactor__Z2, domain=None, range=Optional[Union[float, list[float]]])

slots.reactor__Z0 = Slot(uri=DSS.Z0, name="reactor__Z0", curie=DSS.curie('Z0'),
                   model_uri=DSS.reactor__Z0, domain=None, range=Optional[Union[float, list[float]]])

slots.reactor__Z = Slot(uri=DSS.Z, name="reactor__Z", curie=DSS.curie('Z'),
                   model_uri=DSS.reactor__Z, domain=None, range=Optional[Union[float, list[float]]])

slots.reactor__RCurve = Slot(uri=DSS.RCurve, name="reactor__RCurve", curie=DSS.curie('RCurve'),
                   model_uri=DSS.reactor__RCurve, domain=None, range=Optional[float])

slots.reactor__LCurve = Slot(uri=DSS.LCurve, name="reactor__LCurve", curie=DSS.curie('LCurve'),
                   model_uri=DSS.reactor__LCurve, domain=None, range=Optional[float])

slots.reactor__LmH = Slot(uri=DSS.LmH, name="reactor__LmH", curie=DSS.curie('LmH'),
                   model_uri=DSS.reactor__LmH, domain=None, range=Optional[float])

slots.reactor__normamps = Slot(uri=DSS.normamps, name="reactor__normamps", curie=DSS.curie('normamps'),
                   model_uri=DSS.reactor__normamps, domain=None, range=Optional[float])

slots.reactor__emergamps = Slot(uri=DSS.emergamps, name="reactor__emergamps", curie=DSS.curie('emergamps'),
                   model_uri=DSS.reactor__emergamps, domain=None, range=Optional[float])

slots.reactor__faultrate = Slot(uri=DSS.faultrate, name="reactor__faultrate", curie=DSS.curie('faultrate'),
                   model_uri=DSS.reactor__faultrate, domain=None, range=Optional[str])

slots.reactor__pctperm = Slot(uri=DSS.pctperm, name="reactor__pctperm", curie=DSS.curie('pctperm'),
                   model_uri=DSS.reactor__pctperm, domain=None, range=Optional[float])

slots.reactor__repair = Slot(uri=DSS.repair, name="reactor__repair", curie=DSS.curie('repair'),
                   model_uri=DSS.reactor__repair, domain=None, range=Optional[str])

slots.reactor__basefreq = Slot(uri=DSS.basefreq, name="reactor__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.reactor__basefreq, domain=None, range=Optional[float])

slots.reactor__enabled = Slot(uri=DSS.enabled, name="reactor__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.reactor__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.reactor__like = Slot(uri=DSS.like, name="reactor__like", curie=DSS.curie('like'),
                   model_uri=DSS.reactor__like, domain=None, range=Optional[str])

slots.transformer__name = Slot(uri=DSS.name, name="transformer__name", curie=DSS.curie('name'),
                   model_uri=DSS.transformer__name, domain=None, range=URIRef)

slots.transformer__phases = Slot(uri=DSS.phases, name="transformer__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.transformer__phases, domain=None, range=Optional[int])

slots.transformer__windings = Slot(uri=DSS.windings, name="transformer__windings", curie=DSS.curie('windings'),
                   model_uri=DSS.transformer__windings, domain=None, range=Optional[int])

slots.transformer__wdg = Slot(uri=DSS.wdg, name="transformer__wdg", curie=DSS.curie('wdg'),
                   model_uri=DSS.transformer__wdg, domain=None, range=Optional[int])

slots.transformer__bus = Slot(uri=DSS.bus, name="transformer__bus", curie=DSS.curie('bus'),
                   model_uri=DSS.transformer__bus, domain=None, range=Optional[str])

slots.transformer__conn = Slot(uri=DSS.conn, name="transformer__conn", curie=DSS.curie('conn'),
                   model_uri=DSS.transformer__conn, domain=None, range=Optional[Union[str, "ConnectionType"]])

slots.transformer__kV = Slot(uri=DSS.kV, name="transformer__kV", curie=DSS.curie('kV'),
                   model_uri=DSS.transformer__kV, domain=None, range=Optional[float])

slots.transformer__kVA = Slot(uri=DSS.kVA, name="transformer__kVA", curie=DSS.curie('kVA'),
                   model_uri=DSS.transformer__kVA, domain=None, range=Optional[float])

slots.transformer__tap = Slot(uri=DSS.tap, name="transformer__tap", curie=DSS.curie('tap'),
                   model_uri=DSS.transformer__tap, domain=None, range=Optional[float])

slots.transformer__pct_R = Slot(uri=DSS.pct_R, name="transformer__pct_R", curie=DSS.curie('pct_R'),
                   model_uri=DSS.transformer__pct_R, domain=None, range=Optional[float])

slots.transformer__Rneut = Slot(uri=DSS.Rneut, name="transformer__Rneut", curie=DSS.curie('Rneut'),
                   model_uri=DSS.transformer__Rneut, domain=None, range=Optional[float])

slots.transformer__Xneut = Slot(uri=DSS.Xneut, name="transformer__Xneut", curie=DSS.curie('Xneut'),
                   model_uri=DSS.transformer__Xneut, domain=None, range=Optional[float])

slots.transformer__buses = Slot(uri=DSS.buses, name="transformer__buses", curie=DSS.curie('buses'),
                   model_uri=DSS.transformer__buses, domain=None, range=Optional[Union[str, list[str]]])

slots.transformer__conns = Slot(uri=DSS.conns, name="transformer__conns", curie=DSS.curie('conns'),
                   model_uri=DSS.transformer__conns, domain=None, range=Optional[Union[Union[str, "ConnectionType"], list[Union[str, "ConnectionType"]]]])

slots.transformer__kVs = Slot(uri=DSS.kVs, name="transformer__kVs", curie=DSS.curie('kVs'),
                   model_uri=DSS.transformer__kVs, domain=None, range=Optional[Union[float, list[float]]])

slots.transformer__kVAs = Slot(uri=DSS.kVAs, name="transformer__kVAs", curie=DSS.curie('kVAs'),
                   model_uri=DSS.transformer__kVAs, domain=None, range=Optional[Union[float, list[float]]])

slots.transformer__taps = Slot(uri=DSS.taps, name="transformer__taps", curie=DSS.curie('taps'),
                   model_uri=DSS.transformer__taps, domain=None, range=Optional[Union[float, list[float]]])

slots.transformer__XHL = Slot(uri=DSS.XHL, name="transformer__XHL", curie=DSS.curie('XHL'),
                   model_uri=DSS.transformer__XHL, domain=None, range=Optional[float])

slots.transformer__XHT = Slot(uri=DSS.XHT, name="transformer__XHT", curie=DSS.curie('XHT'),
                   model_uri=DSS.transformer__XHT, domain=None, range=Optional[float])

slots.transformer__XLT = Slot(uri=DSS.XLT, name="transformer__XLT", curie=DSS.curie('XLT'),
                   model_uri=DSS.transformer__XLT, domain=None, range=Optional[float])

slots.transformer__Xscarray = Slot(uri=DSS.Xscarray, name="transformer__Xscarray", curie=DSS.curie('Xscarray'),
                   model_uri=DSS.transformer__Xscarray, domain=None, range=Optional[Union[float, list[float]]])

slots.transformer__thermal = Slot(uri=DSS.thermal, name="transformer__thermal", curie=DSS.curie('thermal'),
                   model_uri=DSS.transformer__thermal, domain=None, range=Optional[float])

slots.transformer__n = Slot(uri=DSS.n, name="transformer__n", curie=DSS.curie('n'),
                   model_uri=DSS.transformer__n, domain=None, range=Optional[float])

slots.transformer__m = Slot(uri=DSS.m, name="transformer__m", curie=DSS.curie('m'),
                   model_uri=DSS.transformer__m, domain=None, range=Optional[float])

slots.transformer__flrise = Slot(uri=DSS.flrise, name="transformer__flrise", curie=DSS.curie('flrise'),
                   model_uri=DSS.transformer__flrise, domain=None, range=Optional[float])

slots.transformer__hsrise = Slot(uri=DSS.hsrise, name="transformer__hsrise", curie=DSS.curie('hsrise'),
                   model_uri=DSS.transformer__hsrise, domain=None, range=Optional[float])

slots.transformer__pct_loadloss = Slot(uri=DSS.pct_loadloss, name="transformer__pct_loadloss", curie=DSS.curie('pct_loadloss'),
                   model_uri=DSS.transformer__pct_loadloss, domain=None, range=Optional[float])

slots.transformer__pct_noloadloss = Slot(uri=DSS.pct_noloadloss, name="transformer__pct_noloadloss", curie=DSS.curie('pct_noloadloss'),
                   model_uri=DSS.transformer__pct_noloadloss, domain=None, range=Optional[float])

slots.transformer__normhkVA = Slot(uri=DSS.normhkVA, name="transformer__normhkVA", curie=DSS.curie('normhkVA'),
                   model_uri=DSS.transformer__normhkVA, domain=None, range=Optional[float])

slots.transformer__emerghkVA = Slot(uri=DSS.emerghkVA, name="transformer__emerghkVA", curie=DSS.curie('emerghkVA'),
                   model_uri=DSS.transformer__emerghkVA, domain=None, range=Optional[float])

slots.transformer__sub = Slot(uri=DSS.sub, name="transformer__sub", curie=DSS.curie('sub'),
                   model_uri=DSS.transformer__sub, domain=None, range=Optional[Union[bool, Bool]])

slots.transformer__MaxTap = Slot(uri=DSS.MaxTap, name="transformer__MaxTap", curie=DSS.curie('MaxTap'),
                   model_uri=DSS.transformer__MaxTap, domain=None, range=Optional[float])

slots.transformer__MinTap = Slot(uri=DSS.MinTap, name="transformer__MinTap", curie=DSS.curie('MinTap'),
                   model_uri=DSS.transformer__MinTap, domain=None, range=Optional[float])

slots.transformer__NumTaps = Slot(uri=DSS.NumTaps, name="transformer__NumTaps", curie=DSS.curie('NumTaps'),
                   model_uri=DSS.transformer__NumTaps, domain=None, range=Optional[int])

slots.transformer__subname = Slot(uri=DSS.subname, name="transformer__subname", curie=DSS.curie('subname'),
                   model_uri=DSS.transformer__subname, domain=None, range=Optional[str])

slots.transformer__pct_imag = Slot(uri=DSS.pct_imag, name="transformer__pct_imag", curie=DSS.curie('pct_imag'),
                   model_uri=DSS.transformer__pct_imag, domain=None, range=Optional[float])

slots.transformer__ppm_antifloat = Slot(uri=DSS.ppm_antifloat, name="transformer__ppm_antifloat", curie=DSS.curie('ppm_antifloat'),
                   model_uri=DSS.transformer__ppm_antifloat, domain=None, range=Optional[float])

slots.transformer__pct_Rs = Slot(uri=DSS.pct_Rs, name="transformer__pct_Rs", curie=DSS.curie('pct_Rs'),
                   model_uri=DSS.transformer__pct_Rs, domain=None, range=Optional[Union[float, list[float]]])

slots.transformer__bank = Slot(uri=DSS.bank, name="transformer__bank", curie=DSS.curie('bank'),
                   model_uri=DSS.transformer__bank, domain=None, range=Optional[str])

slots.transformer__XfmrCode = Slot(uri=DSS.XfmrCode, name="transformer__XfmrCode", curie=DSS.curie('XfmrCode'),
                   model_uri=DSS.transformer__XfmrCode, domain=None, range=Optional[str])

slots.transformer__XRConst = Slot(uri=DSS.XRConst, name="transformer__XRConst", curie=DSS.curie('XRConst'),
                   model_uri=DSS.transformer__XRConst, domain=None, range=Optional[Union[bool, Bool]])

slots.transformer__X12 = Slot(uri=DSS.X12, name="transformer__X12", curie=DSS.curie('X12'),
                   model_uri=DSS.transformer__X12, domain=None, range=Optional[float])

slots.transformer__X13 = Slot(uri=DSS.X13, name="transformer__X13", curie=DSS.curie('X13'),
                   model_uri=DSS.transformer__X13, domain=None, range=Optional[float])

slots.transformer__X23 = Slot(uri=DSS.X23, name="transformer__X23", curie=DSS.curie('X23'),
                   model_uri=DSS.transformer__X23, domain=None, range=Optional[float])

slots.transformer__LeadLag = Slot(uri=DSS.LeadLag, name="transformer__LeadLag", curie=DSS.curie('LeadLag'),
                   model_uri=DSS.transformer__LeadLag, domain=None, range=Optional[Union[str, "LeadLagType"]])

slots.transformer__Core = Slot(uri=DSS.Core, name="transformer__Core", curie=DSS.curie('Core'),
                   model_uri=DSS.transformer__Core, domain=None, range=Optional[Union[str, "CoreType"]])

slots.transformer__RdcOhms = Slot(uri=DSS.RdcOhms, name="transformer__RdcOhms", curie=DSS.curie('RdcOhms'),
                   model_uri=DSS.transformer__RdcOhms, domain=None, range=Optional[Union[float, list[float]]])

slots.transformer__Seasons = Slot(uri=DSS.Seasons, name="transformer__Seasons", curie=DSS.curie('Seasons'),
                   model_uri=DSS.transformer__Seasons, domain=None, range=Optional[int])

slots.transformer__Ratings = Slot(uri=DSS.Ratings, name="transformer__Ratings", curie=DSS.curie('Ratings'),
                   model_uri=DSS.transformer__Ratings, domain=None, range=Optional[Union[float, list[float]]])

slots.transformer__normamps = Slot(uri=DSS.normamps, name="transformer__normamps", curie=DSS.curie('normamps'),
                   model_uri=DSS.transformer__normamps, domain=None, range=Optional[float])

slots.transformer__emergamps = Slot(uri=DSS.emergamps, name="transformer__emergamps", curie=DSS.curie('emergamps'),
                   model_uri=DSS.transformer__emergamps, domain=None, range=Optional[float])

slots.transformer__faultrate = Slot(uri=DSS.faultrate, name="transformer__faultrate", curie=DSS.curie('faultrate'),
                   model_uri=DSS.transformer__faultrate, domain=None, range=Optional[float])

slots.transformer__pct_perm = Slot(uri=DSS.pct_perm, name="transformer__pct_perm", curie=DSS.curie('pct_perm'),
                   model_uri=DSS.transformer__pct_perm, domain=None, range=Optional[float])

slots.transformer__repair = Slot(uri=DSS.repair, name="transformer__repair", curie=DSS.curie('repair'),
                   model_uri=DSS.transformer__repair, domain=None, range=Optional[float])

slots.transformer__basefreq = Slot(uri=DSS.basefreq, name="transformer__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.transformer__basefreq, domain=None, range=Optional[float])

slots.transformer__enabled = Slot(uri=DSS.enabled, name="transformer__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.transformer__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.transformer__like = Slot(uri=DSS.like, name="transformer__like", curie=DSS.curie('like'),
                   model_uri=DSS.transformer__like, domain=None, range=Optional[str])

slots.capcontrol__name = Slot(uri=DSS.name, name="capcontrol__name", curie=DSS.curie('name'),
                   model_uri=DSS.capcontrol__name, domain=None, range=URIRef)

slots.capcontrol__element = Slot(uri=DSS.element, name="capcontrol__element", curie=DSS.curie('element'),
                   model_uri=DSS.capcontrol__element, domain=None, range=Optional[str])

slots.capcontrol__terminal = Slot(uri=DSS.terminal, name="capcontrol__terminal", curie=DSS.curie('terminal'),
                   model_uri=DSS.capcontrol__terminal, domain=None, range=Optional[int])

slots.capcontrol__capacitor = Slot(uri=DSS.capacitor, name="capcontrol__capacitor", curie=DSS.curie('capacitor'),
                   model_uri=DSS.capcontrol__capacitor, domain=None, range=Optional[str])

slots.capcontrol__type = Slot(uri=DSS.type, name="capcontrol__type", curie=DSS.curie('type'),
                   model_uri=DSS.capcontrol__type, domain=None, range=Optional[str])

slots.capcontrol__PTratio = Slot(uri=DSS.PTratio, name="capcontrol__PTratio", curie=DSS.curie('PTratio'),
                   model_uri=DSS.capcontrol__PTratio, domain=None, range=Optional[float])

slots.capcontrol__CTratio = Slot(uri=DSS.CTratio, name="capcontrol__CTratio", curie=DSS.curie('CTratio'),
                   model_uri=DSS.capcontrol__CTratio, domain=None, range=Optional[float])

slots.capcontrol__ONsetting = Slot(uri=DSS.ONsetting, name="capcontrol__ONsetting", curie=DSS.curie('ONsetting'),
                   model_uri=DSS.capcontrol__ONsetting, domain=None, range=Optional[float])

slots.capcontrol__OFFsetting = Slot(uri=DSS.OFFsetting, name="capcontrol__OFFsetting", curie=DSS.curie('OFFsetting'),
                   model_uri=DSS.capcontrol__OFFsetting, domain=None, range=Optional[float])

slots.capcontrol__Delay = Slot(uri=DSS.Delay, name="capcontrol__Delay", curie=DSS.curie('Delay'),
                   model_uri=DSS.capcontrol__Delay, domain=None, range=Optional[float])

slots.capcontrol__VoltOverride = Slot(uri=DSS.VoltOverride, name="capcontrol__VoltOverride", curie=DSS.curie('VoltOverride'),
                   model_uri=DSS.capcontrol__VoltOverride, domain=None, range=Optional[Union[bool, Bool]])

slots.capcontrol__Vmax = Slot(uri=DSS.Vmax, name="capcontrol__Vmax", curie=DSS.curie('Vmax'),
                   model_uri=DSS.capcontrol__Vmax, domain=None, range=Optional[float])

slots.capcontrol__Vmin = Slot(uri=DSS.Vmin, name="capcontrol__Vmin", curie=DSS.curie('Vmin'),
                   model_uri=DSS.capcontrol__Vmin, domain=None, range=Optional[float])

slots.capcontrol__DelayOFF = Slot(uri=DSS.DelayOFF, name="capcontrol__DelayOFF", curie=DSS.curie('DelayOFF'),
                   model_uri=DSS.capcontrol__DelayOFF, domain=None, range=Optional[float])

slots.capcontrol__DeadTime = Slot(uri=DSS.DeadTime, name="capcontrol__DeadTime", curie=DSS.curie('DeadTime'),
                   model_uri=DSS.capcontrol__DeadTime, domain=None, range=Optional[float])

slots.capcontrol__CTPhase = Slot(uri=DSS.CTPhase, name="capcontrol__CTPhase", curie=DSS.curie('CTPhase'),
                   model_uri=DSS.capcontrol__CTPhase, domain=None, range=Optional[int])

slots.capcontrol__PTPhase = Slot(uri=DSS.PTPhase, name="capcontrol__PTPhase", curie=DSS.curie('PTPhase'),
                   model_uri=DSS.capcontrol__PTPhase, domain=None, range=Optional[int])

slots.capcontrol__VBus = Slot(uri=DSS.VBus, name="capcontrol__VBus", curie=DSS.curie('VBus'),
                   model_uri=DSS.capcontrol__VBus, domain=None, range=Optional[float])

slots.capcontrol__EventLog = Slot(uri=DSS.EventLog, name="capcontrol__EventLog", curie=DSS.curie('EventLog'),
                   model_uri=DSS.capcontrol__EventLog, domain=None, range=Optional[str])

slots.capcontrol__UserModel = Slot(uri=DSS.UserModel, name="capcontrol__UserModel", curie=DSS.curie('UserModel'),
                   model_uri=DSS.capcontrol__UserModel, domain=None, range=Optional[str])

slots.capcontrol__UserData = Slot(uri=DSS.UserData, name="capcontrol__UserData", curie=DSS.curie('UserData'),
                   model_uri=DSS.capcontrol__UserData, domain=None, range=Optional[str])

slots.capcontrol__pctMinkvar = Slot(uri=DSS.pctMinkvar, name="capcontrol__pctMinkvar", curie=DSS.curie('pctMinkvar'),
                   model_uri=DSS.capcontrol__pctMinkvar, domain=None, range=Optional[float])

slots.capcontrol__Reset = Slot(uri=DSS.Reset, name="capcontrol__Reset", curie=DSS.curie('Reset'),
                   model_uri=DSS.capcontrol__Reset, domain=None, range=Optional[Union[bool, Bool]])

slots.capcontrol__ControlSignal = Slot(uri=DSS.ControlSignal, name="capcontrol__ControlSignal", curie=DSS.curie('ControlSignal'),
                   model_uri=DSS.capcontrol__ControlSignal, domain=None, range=Optional[str])

slots.capcontrol__basefreq = Slot(uri=DSS.basefreq, name="capcontrol__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.capcontrol__basefreq, domain=None, range=Optional[float])

slots.capcontrol__enabled = Slot(uri=DSS.enabled, name="capcontrol__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.capcontrol__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.capcontrol__like = Slot(uri=DSS.like, name="capcontrol__like", curie=DSS.curie('like'),
                   model_uri=DSS.capcontrol__like, domain=None, range=Optional[str])

slots.espvlcontrol__name = Slot(uri=DSS.name, name="espvlcontrol__name", curie=DSS.curie('name'),
                   model_uri=DSS.espvlcontrol__name, domain=None, range=URIRef)

slots.espvlcontrol__Element = Slot(uri=DSS.Element, name="espvlcontrol__Element", curie=DSS.curie('Element'),
                   model_uri=DSS.espvlcontrol__Element, domain=None, range=Optional[str])

slots.espvlcontrol__Terminal = Slot(uri=DSS.Terminal, name="espvlcontrol__Terminal", curie=DSS.curie('Terminal'),
                   model_uri=DSS.espvlcontrol__Terminal, domain=None, range=Optional[int])

slots.espvlcontrol__Type = Slot(uri=DSS.Type, name="espvlcontrol__Type", curie=DSS.curie('Type'),
                   model_uri=DSS.espvlcontrol__Type, domain=None, range=Optional[str])

slots.espvlcontrol__kWBand = Slot(uri=DSS.kWBand, name="espvlcontrol__kWBand", curie=DSS.curie('kWBand'),
                   model_uri=DSS.espvlcontrol__kWBand, domain=None, range=Optional[float])

slots.espvlcontrol__kvarlimit = Slot(uri=DSS.kvarlimit, name="espvlcontrol__kvarlimit", curie=DSS.curie('kvarlimit'),
                   model_uri=DSS.espvlcontrol__kvarlimit, domain=None, range=Optional[float])

slots.espvlcontrol__LocalControlList = Slot(uri=DSS.LocalControlList, name="espvlcontrol__LocalControlList", curie=DSS.curie('LocalControlList'),
                   model_uri=DSS.espvlcontrol__LocalControlList, domain=None, range=Optional[Union[str, list[str]]])

slots.espvlcontrol__LocalControlWeights = Slot(uri=DSS.LocalControlWeights, name="espvlcontrol__LocalControlWeights", curie=DSS.curie('LocalControlWeights'),
                   model_uri=DSS.espvlcontrol__LocalControlWeights, domain=None, range=Optional[Union[float, list[float]]])

slots.espvlcontrol__PVSystemList = Slot(uri=DSS.PVSystemList, name="espvlcontrol__PVSystemList", curie=DSS.curie('PVSystemList'),
                   model_uri=DSS.espvlcontrol__PVSystemList, domain=None, range=Optional[Union[str, list[str]]])

slots.espvlcontrol__PVSystemWeights = Slot(uri=DSS.PVSystemWeights, name="espvlcontrol__PVSystemWeights", curie=DSS.curie('PVSystemWeights'),
                   model_uri=DSS.espvlcontrol__PVSystemWeights, domain=None, range=Optional[Union[float, list[float]]])

slots.espvlcontrol__StorageList = Slot(uri=DSS.StorageList, name="espvlcontrol__StorageList", curie=DSS.curie('StorageList'),
                   model_uri=DSS.espvlcontrol__StorageList, domain=None, range=Optional[Union[str, list[str]]])

slots.espvlcontrol__StorageWeights = Slot(uri=DSS.StorageWeights, name="espvlcontrol__StorageWeights", curie=DSS.curie('StorageWeights'),
                   model_uri=DSS.espvlcontrol__StorageWeights, domain=None, range=Optional[Union[float, list[float]]])

slots.espvlcontrol__Forecast = Slot(uri=DSS.Forecast, name="espvlcontrol__Forecast", curie=DSS.curie('Forecast'),
                   model_uri=DSS.espvlcontrol__Forecast, domain=None, range=Optional[str])

slots.espvlcontrol__basefreq = Slot(uri=DSS.basefreq, name="espvlcontrol__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.espvlcontrol__basefreq, domain=None, range=Optional[float])

slots.espvlcontrol__enabled = Slot(uri=DSS.enabled, name="espvlcontrol__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.espvlcontrol__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.espvlcontrol__like = Slot(uri=DSS.like, name="espvlcontrol__like", curie=DSS.curie('like'),
                   model_uri=DSS.espvlcontrol__like, domain=None, range=Optional[str])

slots.expcontrol__name = Slot(uri=DSS.name, name="expcontrol__name", curie=DSS.curie('name'),
                   model_uri=DSS.expcontrol__name, domain=None, range=URIRef)

slots.expcontrol__PVSystemList = Slot(uri=DSS.PVSystemList, name="expcontrol__PVSystemList", curie=DSS.curie('PVSystemList'),
                   model_uri=DSS.expcontrol__PVSystemList, domain=None, range=Optional[Union[str, list[str]]])

slots.expcontrol__Vreg = Slot(uri=DSS.Vreg, name="expcontrol__Vreg", curie=DSS.curie('Vreg'),
                   model_uri=DSS.expcontrol__Vreg, domain=None, range=Optional[float])

slots.expcontrol__Slope = Slot(uri=DSS.Slope, name="expcontrol__Slope", curie=DSS.curie('Slope'),
                   model_uri=DSS.expcontrol__Slope, domain=None, range=Optional[float])

slots.expcontrol__VregTau = Slot(uri=DSS.VregTau, name="expcontrol__VregTau", curie=DSS.curie('VregTau'),
                   model_uri=DSS.expcontrol__VregTau, domain=None, range=Optional[float])

slots.expcontrol__Qbias = Slot(uri=DSS.Qbias, name="expcontrol__Qbias", curie=DSS.curie('Qbias'),
                   model_uri=DSS.expcontrol__Qbias, domain=None, range=Optional[float])

slots.expcontrol__VregMin = Slot(uri=DSS.VregMin, name="expcontrol__VregMin", curie=DSS.curie('VregMin'),
                   model_uri=DSS.expcontrol__VregMin, domain=None, range=Optional[str])

slots.expcontrol__VregMax = Slot(uri=DSS.VregMax, name="expcontrol__VregMax", curie=DSS.curie('VregMax'),
                   model_uri=DSS.expcontrol__VregMax, domain=None, range=Optional[str])

slots.expcontrol__QmaxLead = Slot(uri=DSS.QmaxLead, name="expcontrol__QmaxLead", curie=DSS.curie('QmaxLead'),
                   model_uri=DSS.expcontrol__QmaxLead, domain=None, range=Optional[float])

slots.expcontrol__QmaxLag = Slot(uri=DSS.QmaxLag, name="expcontrol__QmaxLag", curie=DSS.curie('QmaxLag'),
                   model_uri=DSS.expcontrol__QmaxLag, domain=None, range=Optional[float])

slots.expcontrol__EventLog = Slot(uri=DSS.EventLog, name="expcontrol__EventLog", curie=DSS.curie('EventLog'),
                   model_uri=DSS.expcontrol__EventLog, domain=None, range=Optional[str])

slots.expcontrol__DeltaQ_factor = Slot(uri=DSS.DeltaQ_factor, name="expcontrol__DeltaQ_factor", curie=DSS.curie('DeltaQ_factor'),
                   model_uri=DSS.expcontrol__DeltaQ_factor, domain=None, range=Optional[int])

slots.expcontrol__PreferQ = Slot(uri=DSS.PreferQ, name="expcontrol__PreferQ", curie=DSS.curie('PreferQ'),
                   model_uri=DSS.expcontrol__PreferQ, domain=None, range=Optional[float])

slots.expcontrol__Tresponse = Slot(uri=DSS.Tresponse, name="expcontrol__Tresponse", curie=DSS.curie('Tresponse'),
                   model_uri=DSS.expcontrol__Tresponse, domain=None, range=Optional[float])

slots.expcontrol__DERList = Slot(uri=DSS.DERList, name="expcontrol__DERList", curie=DSS.curie('DERList'),
                   model_uri=DSS.expcontrol__DERList, domain=None, range=Optional[str])

slots.expcontrol__basefreq = Slot(uri=DSS.basefreq, name="expcontrol__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.expcontrol__basefreq, domain=None, range=Optional[float])

slots.expcontrol__enabled = Slot(uri=DSS.enabled, name="expcontrol__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.expcontrol__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.expcontrol__like = Slot(uri=DSS.like, name="expcontrol__like", curie=DSS.curie('like'),
                   model_uri=DSS.expcontrol__like, domain=None, range=Optional[str])

slots.fuse__name = Slot(uri=DSS.name, name="fuse__name", curie=DSS.curie('name'),
                   model_uri=DSS.fuse__name, domain=None, range=URIRef)

slots.fuse__MonitoredObj = Slot(uri=DSS.MonitoredObj, name="fuse__MonitoredObj", curie=DSS.curie('MonitoredObj'),
                   model_uri=DSS.fuse__MonitoredObj, domain=None, range=Optional[str])

slots.fuse__MonitoredTerm = Slot(uri=DSS.MonitoredTerm, name="fuse__MonitoredTerm", curie=DSS.curie('MonitoredTerm'),
                   model_uri=DSS.fuse__MonitoredTerm, domain=None, range=Optional[int])

slots.fuse__SwitchedObj = Slot(uri=DSS.SwitchedObj, name="fuse__SwitchedObj", curie=DSS.curie('SwitchedObj'),
                   model_uri=DSS.fuse__SwitchedObj, domain=None, range=Optional[str])

slots.fuse__SwitchedTerm = Slot(uri=DSS.SwitchedTerm, name="fuse__SwitchedTerm", curie=DSS.curie('SwitchedTerm'),
                   model_uri=DSS.fuse__SwitchedTerm, domain=None, range=Optional[int])

slots.fuse__FuseCurve = Slot(uri=DSS.FuseCurve, name="fuse__FuseCurve", curie=DSS.curie('FuseCurve'),
                   model_uri=DSS.fuse__FuseCurve, domain=None, range=Optional[float])

slots.fuse__RatedCurrent = Slot(uri=DSS.RatedCurrent, name="fuse__RatedCurrent", curie=DSS.curie('RatedCurrent'),
                   model_uri=DSS.fuse__RatedCurrent, domain=None, range=Optional[float])

slots.fuse__Delay = Slot(uri=DSS.Delay, name="fuse__Delay", curie=DSS.curie('Delay'),
                   model_uri=DSS.fuse__Delay, domain=None, range=Optional[str])

slots.fuse__Action = Slot(uri=DSS.Action, name="fuse__Action", curie=DSS.curie('Action'),
                   model_uri=DSS.fuse__Action, domain=None, range=Optional[str])

slots.fuse__Normal = Slot(uri=DSS.Normal, name="fuse__Normal", curie=DSS.curie('Normal'),
                   model_uri=DSS.fuse__Normal, domain=None, range=Optional[Union[str, list[str]]])

slots.fuse__State = Slot(uri=DSS.State, name="fuse__State", curie=DSS.curie('State'),
                   model_uri=DSS.fuse__State, domain=None, range=Optional[Union[str, list[str]]])

slots.fuse__basefreq = Slot(uri=DSS.basefreq, name="fuse__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.fuse__basefreq, domain=None, range=Optional[float])

slots.fuse__enabled = Slot(uri=DSS.enabled, name="fuse__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.fuse__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.fuse__like = Slot(uri=DSS.like, name="fuse__like", curie=DSS.curie('like'),
                   model_uri=DSS.fuse__like, domain=None, range=Optional[str])

slots.gendispatcher__name = Slot(uri=DSS.name, name="gendispatcher__name", curie=DSS.curie('name'),
                   model_uri=DSS.gendispatcher__name, domain=None, range=URIRef)

slots.gendispatcher__Element = Slot(uri=DSS.Element, name="gendispatcher__Element", curie=DSS.curie('Element'),
                   model_uri=DSS.gendispatcher__Element, domain=None, range=Optional[str])

slots.gendispatcher__Terminal = Slot(uri=DSS.Terminal, name="gendispatcher__Terminal", curie=DSS.curie('Terminal'),
                   model_uri=DSS.gendispatcher__Terminal, domain=None, range=Optional[int])

slots.gendispatcher__kWLimit = Slot(uri=DSS.kWLimit, name="gendispatcher__kWLimit", curie=DSS.curie('kWLimit'),
                   model_uri=DSS.gendispatcher__kWLimit, domain=None, range=Optional[float])

slots.gendispatcher__kWBand = Slot(uri=DSS.kWBand, name="gendispatcher__kWBand", curie=DSS.curie('kWBand'),
                   model_uri=DSS.gendispatcher__kWBand, domain=None, range=Optional[float])

slots.gendispatcher__kvarlimit = Slot(uri=DSS.kvarlimit, name="gendispatcher__kvarlimit", curie=DSS.curie('kvarlimit'),
                   model_uri=DSS.gendispatcher__kvarlimit, domain=None, range=Optional[float])

slots.gendispatcher__GenList = Slot(uri=DSS.GenList, name="gendispatcher__GenList", curie=DSS.curie('GenList'),
                   model_uri=DSS.gendispatcher__GenList, domain=None, range=Optional[Union[str, list[str]]])

slots.gendispatcher__basefreq = Slot(uri=DSS.basefreq, name="gendispatcher__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.gendispatcher__basefreq, domain=None, range=Optional[float])

slots.gendispatcher__enabled = Slot(uri=DSS.enabled, name="gendispatcher__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.gendispatcher__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.gendispatcher__like = Slot(uri=DSS.like, name="gendispatcher__like", curie=DSS.curie('like'),
                   model_uri=DSS.gendispatcher__like, domain=None, range=Optional[str])

slots.invcontrol__name = Slot(uri=DSS.name, name="invcontrol__name", curie=DSS.curie('name'),
                   model_uri=DSS.invcontrol__name, domain=None, range=URIRef)

slots.invcontrol__DERList = Slot(uri=DSS.DERList, name="invcontrol__DERList", curie=DSS.curie('DERList'),
                   model_uri=DSS.invcontrol__DERList, domain=None, range=Optional[Union[str, list[str]]])

slots.invcontrol__Mode = Slot(uri=DSS.Mode, name="invcontrol__Mode", curie=DSS.curie('Mode'),
                   model_uri=DSS.invcontrol__Mode, domain=None, range=Optional[str])

slots.invcontrol__CombiMode = Slot(uri=DSS.CombiMode, name="invcontrol__CombiMode", curie=DSS.curie('CombiMode'),
                   model_uri=DSS.invcontrol__CombiMode, domain=None, range=Optional[str])

slots.invcontrol__vvc_curve1 = Slot(uri=DSS.vvc_curve1, name="invcontrol__vvc_curve1", curie=DSS.curie('vvc_curve1'),
                   model_uri=DSS.invcontrol__vvc_curve1, domain=None, range=Optional[int])

slots.invcontrol__hysteresis_offset = Slot(uri=DSS.hysteresis_offset, name="invcontrol__hysteresis_offset", curie=DSS.curie('hysteresis_offset'),
                   model_uri=DSS.invcontrol__hysteresis_offset, domain=None, range=Optional[float])

slots.invcontrol__voltage_curvex_ref = Slot(uri=DSS.voltage_curvex_ref, name="invcontrol__voltage_curvex_ref", curie=DSS.curie('voltage_curvex_ref'),
                   model_uri=DSS.invcontrol__voltage_curvex_ref, domain=None, range=Optional[int])

slots.invcontrol__avgwindowlen = Slot(uri=DSS.avgwindowlen, name="invcontrol__avgwindowlen", curie=DSS.curie('avgwindowlen'),
                   model_uri=DSS.invcontrol__avgwindowlen, domain=None, range=Optional[int])

slots.invcontrol__voltwatt_curve = Slot(uri=DSS.voltwatt_curve, name="invcontrol__voltwatt_curve", curie=DSS.curie('voltwatt_curve'),
                   model_uri=DSS.invcontrol__voltwatt_curve, domain=None, range=Optional[int])

slots.invcontrol__DbVMin = Slot(uri=DSS.DbVMin, name="invcontrol__DbVMin", curie=DSS.curie('DbVMin'),
                   model_uri=DSS.invcontrol__DbVMin, domain=None, range=Optional[float])

slots.invcontrol__DbVMax = Slot(uri=DSS.DbVMax, name="invcontrol__DbVMax", curie=DSS.curie('DbVMax'),
                   model_uri=DSS.invcontrol__DbVMax, domain=None, range=Optional[float])

slots.invcontrol__ArGraLowV = Slot(uri=DSS.ArGraLowV, name="invcontrol__ArGraLowV", curie=DSS.curie('ArGraLowV'),
                   model_uri=DSS.invcontrol__ArGraLowV, domain=None, range=Optional[float])

slots.invcontrol__ArGraHiV = Slot(uri=DSS.ArGraHiV, name="invcontrol__ArGraHiV", curie=DSS.curie('ArGraHiV'),
                   model_uri=DSS.invcontrol__ArGraHiV, domain=None, range=Optional[float])

slots.invcontrol__DynReacavgwindowlen = Slot(uri=DSS.DynReacavgwindowlen, name="invcontrol__DynReacavgwindowlen", curie=DSS.curie('DynReacavgwindowlen'),
                   model_uri=DSS.invcontrol__DynReacavgwindowlen, domain=None, range=Optional[int])

slots.invcontrol__deltaQ_Factor = Slot(uri=DSS.deltaQ_Factor, name="invcontrol__deltaQ_Factor", curie=DSS.curie('deltaQ_Factor'),
                   model_uri=DSS.invcontrol__deltaQ_Factor, domain=None, range=Optional[int])

slots.invcontrol__VoltageChangeTolerance = Slot(uri=DSS.VoltageChangeTolerance, name="invcontrol__VoltageChangeTolerance", curie=DSS.curie('VoltageChangeTolerance'),
                   model_uri=DSS.invcontrol__VoltageChangeTolerance, domain=None, range=Optional[float])

slots.invcontrol__VarChangeTolerance = Slot(uri=DSS.VarChangeTolerance, name="invcontrol__VarChangeTolerance", curie=DSS.curie('VarChangeTolerance'),
                   model_uri=DSS.invcontrol__VarChangeTolerance, domain=None, range=Optional[float])

slots.invcontrol__VoltwattYAxis = Slot(uri=DSS.VoltwattYAxis, name="invcontrol__VoltwattYAxis", curie=DSS.curie('VoltwattYAxis'),
                   model_uri=DSS.invcontrol__VoltwattYAxis, domain=None, range=Optional[float])

slots.invcontrol__RateofChangeMode = Slot(uri=DSS.RateofChangeMode, name="invcontrol__RateofChangeMode", curie=DSS.curie('RateofChangeMode'),
                   model_uri=DSS.invcontrol__RateofChangeMode, domain=None, range=Optional[float])

slots.invcontrol__LPFTau = Slot(uri=DSS.LPFTau, name="invcontrol__LPFTau", curie=DSS.curie('LPFTau'),
                   model_uri=DSS.invcontrol__LPFTau, domain=None, range=Optional[str])

slots.invcontrol__RiseFallLimit = Slot(uri=DSS.RiseFallLimit, name="invcontrol__RiseFallLimit", curie=DSS.curie('RiseFallLimit'),
                   model_uri=DSS.invcontrol__RiseFallLimit, domain=None, range=Optional[float])

slots.invcontrol__deltaP_Factor = Slot(uri=DSS.deltaP_Factor, name="invcontrol__deltaP_Factor", curie=DSS.curie('deltaP_Factor'),
                   model_uri=DSS.invcontrol__deltaP_Factor, domain=None, range=Optional[int])

slots.invcontrol__EventLog = Slot(uri=DSS.EventLog, name="invcontrol__EventLog", curie=DSS.curie('EventLog'),
                   model_uri=DSS.invcontrol__EventLog, domain=None, range=Optional[str])

slots.invcontrol__RefReactivePower = Slot(uri=DSS.RefReactivePower, name="invcontrol__RefReactivePower", curie=DSS.curie('RefReactivePower'),
                   model_uri=DSS.invcontrol__RefReactivePower, domain=None, range=Optional[float])

slots.invcontrol__ActivePChangeTolerance = Slot(uri=DSS.ActivePChangeTolerance, name="invcontrol__ActivePChangeTolerance", curie=DSS.curie('ActivePChangeTolerance'),
                   model_uri=DSS.invcontrol__ActivePChangeTolerance, domain=None, range=Optional[float])

slots.invcontrol__monVoltageCalc = Slot(uri=DSS.monVoltageCalc, name="invcontrol__monVoltageCalc", curie=DSS.curie('monVoltageCalc'),
                   model_uri=DSS.invcontrol__monVoltageCalc, domain=None, range=Optional[int])

slots.invcontrol__monBus = Slot(uri=DSS.monBus, name="invcontrol__monBus", curie=DSS.curie('monBus'),
                   model_uri=DSS.invcontrol__monBus, domain=None, range=Optional[float])

slots.invcontrol__MonBusesVbase = Slot(uri=DSS.MonBusesVbase, name="invcontrol__MonBusesVbase", curie=DSS.curie('MonBusesVbase'),
                   model_uri=DSS.invcontrol__MonBusesVbase, domain=None, range=Optional[Union[float, list[float]]])

slots.invcontrol__voltwattCH_curve = Slot(uri=DSS.voltwattCH_curve, name="invcontrol__voltwattCH_curve", curie=DSS.curie('voltwattCH_curve'),
                   model_uri=DSS.invcontrol__voltwattCH_curve, domain=None, range=Optional[int])

slots.invcontrol__wattpf_curve = Slot(uri=DSS.wattpf_curve, name="invcontrol__wattpf_curve", curie=DSS.curie('wattpf_curve'),
                   model_uri=DSS.invcontrol__wattpf_curve, domain=None, range=Optional[float])

slots.invcontrol__wattvar_curve = Slot(uri=DSS.wattvar_curve, name="invcontrol__wattvar_curve", curie=DSS.curie('wattvar_curve'),
                   model_uri=DSS.invcontrol__wattvar_curve, domain=None, range=Optional[float])

slots.invcontrol__VV_RefReactivePower = Slot(uri=DSS.VV_RefReactivePower, name="invcontrol__VV_RefReactivePower", curie=DSS.curie('VV_RefReactivePower'),
                   model_uri=DSS.invcontrol__VV_RefReactivePower, domain=None, range=Optional[float])

slots.invcontrol__PVSystemList = Slot(uri=DSS.PVSystemList, name="invcontrol__PVSystemList", curie=DSS.curie('PVSystemList'),
                   model_uri=DSS.invcontrol__PVSystemList, domain=None, range=Optional[str])

slots.invcontrol__Vsetpoint = Slot(uri=DSS.Vsetpoint, name="invcontrol__Vsetpoint", curie=DSS.curie('Vsetpoint'),
                   model_uri=DSS.invcontrol__Vsetpoint, domain=None, range=Optional[float])

slots.invcontrol__ControlModel = Slot(uri=DSS.ControlModel, name="invcontrol__ControlModel", curie=DSS.curie('ControlModel'),
                   model_uri=DSS.invcontrol__ControlModel, domain=None, range=Optional[int])

slots.invcontrol__basefreq = Slot(uri=DSS.basefreq, name="invcontrol__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.invcontrol__basefreq, domain=None, range=Optional[float])

slots.invcontrol__enabled = Slot(uri=DSS.enabled, name="invcontrol__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.invcontrol__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.invcontrol__like = Slot(uri=DSS.like, name="invcontrol__like", curie=DSS.curie('like'),
                   model_uri=DSS.invcontrol__like, domain=None, range=Optional[str])

slots.pycontrol__name = Slot(uri=DSS.name, name="pycontrol__name", curie=DSS.curie('name'),
                   model_uri=DSS.pycontrol__name, domain=None, range=URIRef)

slots.pycontrol__pyScript = Slot(uri=DSS.pyScript, name="pycontrol__pyScript", curie=DSS.curie('pyScript'),
                   model_uri=DSS.pycontrol__pyScript, domain=None, range=Optional[str])

slots.pycontrol__basefreq = Slot(uri=DSS.basefreq, name="pycontrol__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.pycontrol__basefreq, domain=None, range=Optional[float])

slots.pycontrol__enabled = Slot(uri=DSS.enabled, name="pycontrol__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.pycontrol__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.pycontrol__like = Slot(uri=DSS.like, name="pycontrol__like", curie=DSS.curie('like'),
                   model_uri=DSS.pycontrol__like, domain=None, range=Optional[str])

slots.recloser__name = Slot(uri=DSS.name, name="recloser__name", curie=DSS.curie('name'),
                   model_uri=DSS.recloser__name, domain=None, range=URIRef)

slots.recloser__MonitoredObj = Slot(uri=DSS.MonitoredObj, name="recloser__MonitoredObj", curie=DSS.curie('MonitoredObj'),
                   model_uri=DSS.recloser__MonitoredObj, domain=None, range=Optional[str])

slots.recloser__MonitoredTerm = Slot(uri=DSS.MonitoredTerm, name="recloser__MonitoredTerm", curie=DSS.curie('MonitoredTerm'),
                   model_uri=DSS.recloser__MonitoredTerm, domain=None, range=Optional[int])

slots.recloser__SwitchedObj = Slot(uri=DSS.SwitchedObj, name="recloser__SwitchedObj", curie=DSS.curie('SwitchedObj'),
                   model_uri=DSS.recloser__SwitchedObj, domain=None, range=Optional[str])

slots.recloser__SwitchedTerm = Slot(uri=DSS.SwitchedTerm, name="recloser__SwitchedTerm", curie=DSS.curie('SwitchedTerm'),
                   model_uri=DSS.recloser__SwitchedTerm, domain=None, range=Optional[int])

slots.recloser__NumFast = Slot(uri=DSS.NumFast, name="recloser__NumFast", curie=DSS.curie('NumFast'),
                   model_uri=DSS.recloser__NumFast, domain=None, range=Optional[int])

slots.recloser__PhaseFast = Slot(uri=DSS.PhaseFast, name="recloser__PhaseFast", curie=DSS.curie('PhaseFast'),
                   model_uri=DSS.recloser__PhaseFast, domain=None, range=Optional[float])

slots.recloser__PhaseDelayed = Slot(uri=DSS.PhaseDelayed, name="recloser__PhaseDelayed", curie=DSS.curie('PhaseDelayed'),
                   model_uri=DSS.recloser__PhaseDelayed, domain=None, range=Optional[float])

slots.recloser__GroundFast = Slot(uri=DSS.GroundFast, name="recloser__GroundFast", curie=DSS.curie('GroundFast'),
                   model_uri=DSS.recloser__GroundFast, domain=None, range=Optional[float])

slots.recloser__GroundDelayed = Slot(uri=DSS.GroundDelayed, name="recloser__GroundDelayed", curie=DSS.curie('GroundDelayed'),
                   model_uri=DSS.recloser__GroundDelayed, domain=None, range=Optional[float])

slots.recloser__PhaseTrip = Slot(uri=DSS.PhaseTrip, name="recloser__PhaseTrip", curie=DSS.curie('PhaseTrip'),
                   model_uri=DSS.recloser__PhaseTrip, domain=None, range=Optional[str])

slots.recloser__GroundTrip = Slot(uri=DSS.GroundTrip, name="recloser__GroundTrip", curie=DSS.curie('GroundTrip'),
                   model_uri=DSS.recloser__GroundTrip, domain=None, range=Optional[str])

slots.recloser__PhaseInst = Slot(uri=DSS.PhaseInst, name="recloser__PhaseInst", curie=DSS.curie('PhaseInst'),
                   model_uri=DSS.recloser__PhaseInst, domain=None, range=Optional[str])

slots.recloser__GroundInst = Slot(uri=DSS.GroundInst, name="recloser__GroundInst", curie=DSS.curie('GroundInst'),
                   model_uri=DSS.recloser__GroundInst, domain=None, range=Optional[str])

slots.recloser__Reset = Slot(uri=DSS.Reset, name="recloser__Reset", curie=DSS.curie('Reset'),
                   model_uri=DSS.recloser__Reset, domain=None, range=Optional[str])

slots.recloser__Shots = Slot(uri=DSS.Shots, name="recloser__Shots", curie=DSS.curie('Shots'),
                   model_uri=DSS.recloser__Shots, domain=None, range=Optional[int])

slots.recloser__RecloseIntervals = Slot(uri=DSS.RecloseIntervals, name="recloser__RecloseIntervals", curie=DSS.curie('RecloseIntervals'),
                   model_uri=DSS.recloser__RecloseIntervals, domain=None, range=Optional[Union[float, list[float]]])

slots.recloser__Delay = Slot(uri=DSS.Delay, name="recloser__Delay", curie=DSS.curie('Delay'),
                   model_uri=DSS.recloser__Delay, domain=None, range=Optional[str])

slots.recloser__Action = Slot(uri=DSS.Action, name="recloser__Action", curie=DSS.curie('Action'),
                   model_uri=DSS.recloser__Action, domain=None, range=Optional[str])

slots.recloser__TDPhFast = Slot(uri=DSS.TDPhFast, name="recloser__TDPhFast", curie=DSS.curie('TDPhFast'),
                   model_uri=DSS.recloser__TDPhFast, domain=None, range=Optional[str])

slots.recloser__TDGrFast = Slot(uri=DSS.TDGrFast, name="recloser__TDGrFast", curie=DSS.curie('TDGrFast'),
                   model_uri=DSS.recloser__TDGrFast, domain=None, range=Optional[str])

slots.recloser__TDPhDelayed = Slot(uri=DSS.TDPhDelayed, name="recloser__TDPhDelayed", curie=DSS.curie('TDPhDelayed'),
                   model_uri=DSS.recloser__TDPhDelayed, domain=None, range=Optional[str])

slots.recloser__TDGrDelayed = Slot(uri=DSS.TDGrDelayed, name="recloser__TDGrDelayed", curie=DSS.curie('TDGrDelayed'),
                   model_uri=DSS.recloser__TDGrDelayed, domain=None, range=Optional[str])

slots.recloser__Normal = Slot(uri=DSS.Normal, name="recloser__Normal", curie=DSS.curie('Normal'),
                   model_uri=DSS.recloser__Normal, domain=None, range=Optional[str])

slots.recloser__State = Slot(uri=DSS.State, name="recloser__State", curie=DSS.curie('State'),
                   model_uri=DSS.recloser__State, domain=None, range=Optional[str])

slots.recloser__basefreq = Slot(uri=DSS.basefreq, name="recloser__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.recloser__basefreq, domain=None, range=Optional[float])

slots.recloser__enabled = Slot(uri=DSS.enabled, name="recloser__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.recloser__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.recloser__like = Slot(uri=DSS.like, name="recloser__like", curie=DSS.curie('like'),
                   model_uri=DSS.recloser__like, domain=None, range=Optional[str])

slots.regcontrol__name = Slot(uri=DSS.name, name="regcontrol__name", curie=DSS.curie('name'),
                   model_uri=DSS.regcontrol__name, domain=None, range=URIRef)

slots.regcontrol__transformer = Slot(uri=DSS.transformer, name="regcontrol__transformer", curie=DSS.curie('transformer'),
                   model_uri=DSS.regcontrol__transformer, domain=None, range=Optional[str])

slots.regcontrol__winding = Slot(uri=DSS.winding, name="regcontrol__winding", curie=DSS.curie('winding'),
                   model_uri=DSS.regcontrol__winding, domain=None, range=Optional[int])

slots.regcontrol__vreg = Slot(uri=DSS.vreg, name="regcontrol__vreg", curie=DSS.curie('vreg'),
                   model_uri=DSS.regcontrol__vreg, domain=None, range=Optional[float])

slots.regcontrol__band = Slot(uri=DSS.band, name="regcontrol__band", curie=DSS.curie('band'),
                   model_uri=DSS.regcontrol__band, domain=None, range=Optional[float])

slots.regcontrol__ptratio = Slot(uri=DSS.ptratio, name="regcontrol__ptratio", curie=DSS.curie('ptratio'),
                   model_uri=DSS.regcontrol__ptratio, domain=None, range=Optional[float])

slots.regcontrol__CTprim = Slot(uri=DSS.CTprim, name="regcontrol__CTprim", curie=DSS.curie('CTprim'),
                   model_uri=DSS.regcontrol__CTprim, domain=None, range=Optional[float])

slots.regcontrol__R = Slot(uri=DSS.R, name="regcontrol__R", curie=DSS.curie('R'),
                   model_uri=DSS.regcontrol__R, domain=None, range=Optional[float])

slots.regcontrol__X = Slot(uri=DSS.X, name="regcontrol__X", curie=DSS.curie('X'),
                   model_uri=DSS.regcontrol__X, domain=None, range=Optional[float])

slots.regcontrol__bus = Slot(uri=DSS.bus, name="regcontrol__bus", curie=DSS.curie('bus'),
                   model_uri=DSS.regcontrol__bus, domain=None, range=Optional[str])

slots.regcontrol__delay = Slot(uri=DSS.delay, name="regcontrol__delay", curie=DSS.curie('delay'),
                   model_uri=DSS.regcontrol__delay, domain=None, range=Optional[float])

slots.regcontrol__reversible = Slot(uri=DSS.reversible, name="regcontrol__reversible", curie=DSS.curie('reversible'),
                   model_uri=DSS.regcontrol__reversible, domain=None, range=Optional[Union[bool, Bool]])

slots.regcontrol__revvreg = Slot(uri=DSS.revvreg, name="regcontrol__revvreg", curie=DSS.curie('revvreg'),
                   model_uri=DSS.regcontrol__revvreg, domain=None, range=Optional[float])

slots.regcontrol__revband = Slot(uri=DSS.revband, name="regcontrol__revband", curie=DSS.curie('revband'),
                   model_uri=DSS.regcontrol__revband, domain=None, range=Optional[float])

slots.regcontrol__revR = Slot(uri=DSS.revR, name="regcontrol__revR", curie=DSS.curie('revR'),
                   model_uri=DSS.regcontrol__revR, domain=None, range=Optional[float])

slots.regcontrol__revX = Slot(uri=DSS.revX, name="regcontrol__revX", curie=DSS.curie('revX'),
                   model_uri=DSS.regcontrol__revX, domain=None, range=Optional[float])

slots.regcontrol__tapdelay = Slot(uri=DSS.tapdelay, name="regcontrol__tapdelay", curie=DSS.curie('tapdelay'),
                   model_uri=DSS.regcontrol__tapdelay, domain=None, range=Optional[float])

slots.regcontrol__debugtrace = Slot(uri=DSS.debugtrace, name="regcontrol__debugtrace", curie=DSS.curie('debugtrace'),
                   model_uri=DSS.regcontrol__debugtrace, domain=None, range=Optional[Union[bool, Bool]])

slots.regcontrol__maxtapchange = Slot(uri=DSS.maxtapchange, name="regcontrol__maxtapchange", curie=DSS.curie('maxtapchange'),
                   model_uri=DSS.regcontrol__maxtapchange, domain=None, range=Optional[float])

slots.regcontrol__inversetime = Slot(uri=DSS.inversetime, name="regcontrol__inversetime", curie=DSS.curie('inversetime'),
                   model_uri=DSS.regcontrol__inversetime, domain=None, range=Optional[Union[bool, Bool]])

slots.regcontrol__tapwinding = Slot(uri=DSS.tapwinding, name="regcontrol__tapwinding", curie=DSS.curie('tapwinding'),
                   model_uri=DSS.regcontrol__tapwinding, domain=None, range=Optional[str])

slots.regcontrol__vlimit = Slot(uri=DSS.vlimit, name="regcontrol__vlimit", curie=DSS.curie('vlimit'),
                   model_uri=DSS.regcontrol__vlimit, domain=None, range=Optional[float])

slots.regcontrol__PTphase = Slot(uri=DSS.PTphase, name="regcontrol__PTphase", curie=DSS.curie('PTphase'),
                   model_uri=DSS.regcontrol__PTphase, domain=None, range=Optional[int])

slots.regcontrol__revThreshold = Slot(uri=DSS.revThreshold, name="regcontrol__revThreshold", curie=DSS.curie('revThreshold'),
                   model_uri=DSS.regcontrol__revThreshold, domain=None, range=Optional[float])

slots.regcontrol__revDelay = Slot(uri=DSS.revDelay, name="regcontrol__revDelay", curie=DSS.curie('revDelay'),
                   model_uri=DSS.regcontrol__revDelay, domain=None, range=Optional[float])

slots.regcontrol__revNeutral = Slot(uri=DSS.revNeutral, name="regcontrol__revNeutral", curie=DSS.curie('revNeutral'),
                   model_uri=DSS.regcontrol__revNeutral, domain=None, range=Optional[Union[bool, Bool]])

slots.regcontrol__EventLog = Slot(uri=DSS.EventLog, name="regcontrol__EventLog", curie=DSS.curie('EventLog'),
                   model_uri=DSS.regcontrol__EventLog, domain=None, range=Optional[str])

slots.regcontrol__RemotePTRatio = Slot(uri=DSS.RemotePTRatio, name="regcontrol__RemotePTRatio", curie=DSS.curie('RemotePTRatio'),
                   model_uri=DSS.regcontrol__RemotePTRatio, domain=None, range=Optional[float])

slots.regcontrol__TapNum = Slot(uri=DSS.TapNum, name="regcontrol__TapNum", curie=DSS.curie('TapNum'),
                   model_uri=DSS.regcontrol__TapNum, domain=None, range=Optional[int])

slots.regcontrol__Reset = Slot(uri=DSS.Reset, name="regcontrol__Reset", curie=DSS.curie('Reset'),
                   model_uri=DSS.regcontrol__Reset, domain=None, range=Optional[Union[bool, Bool]])

slots.regcontrol__LDC_Z = Slot(uri=DSS.LDC_Z, name="regcontrol__LDC_Z", curie=DSS.curie('LDC_Z'),
                   model_uri=DSS.regcontrol__LDC_Z, domain=None, range=Optional[float])

slots.regcontrol__rev_Z = Slot(uri=DSS.rev_Z, name="regcontrol__rev_Z", curie=DSS.curie('rev_Z'),
                   model_uri=DSS.regcontrol__rev_Z, domain=None, range=Optional[float])

slots.regcontrol__Cogen = Slot(uri=DSS.Cogen, name="regcontrol__Cogen", curie=DSS.curie('Cogen'),
                   model_uri=DSS.regcontrol__Cogen, domain=None, range=Optional[Union[bool, Bool]])

slots.regcontrol__idle = Slot(uri=DSS.idle, name="regcontrol__idle", curie=DSS.curie('idle'),
                   model_uri=DSS.regcontrol__idle, domain=None, range=Optional[Union[bool, Bool]])

slots.regcontrol__idleReverse = Slot(uri=DSS.idleReverse, name="regcontrol__idleReverse", curie=DSS.curie('idleReverse'),
                   model_uri=DSS.regcontrol__idleReverse, domain=None, range=Optional[Union[bool, Bool]])

slots.regcontrol__idleForward = Slot(uri=DSS.idleForward, name="regcontrol__idleForward", curie=DSS.curie('idleForward'),
                   model_uri=DSS.regcontrol__idleForward, domain=None, range=Optional[Union[bool, Bool]])

slots.regcontrol__basefreq = Slot(uri=DSS.basefreq, name="regcontrol__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.regcontrol__basefreq, domain=None, range=Optional[float])

slots.regcontrol__enabled = Slot(uri=DSS.enabled, name="regcontrol__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.regcontrol__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.regcontrol__like = Slot(uri=DSS.like, name="regcontrol__like", curie=DSS.curie('like'),
                   model_uri=DSS.regcontrol__like, domain=None, range=Optional[str])

slots.relay__name = Slot(uri=DSS.name, name="relay__name", curie=DSS.curie('name'),
                   model_uri=DSS.relay__name, domain=None, range=URIRef)

slots.relay__MonitoredObj = Slot(uri=DSS.MonitoredObj, name="relay__MonitoredObj", curie=DSS.curie('MonitoredObj'),
                   model_uri=DSS.relay__MonitoredObj, domain=None, range=Optional[str])

slots.relay__MonitoredTerm = Slot(uri=DSS.MonitoredTerm, name="relay__MonitoredTerm", curie=DSS.curie('MonitoredTerm'),
                   model_uri=DSS.relay__MonitoredTerm, domain=None, range=Optional[int])

slots.relay__SwitchedObj = Slot(uri=DSS.SwitchedObj, name="relay__SwitchedObj", curie=DSS.curie('SwitchedObj'),
                   model_uri=DSS.relay__SwitchedObj, domain=None, range=Optional[str])

slots.relay__SwitchedTerm = Slot(uri=DSS.SwitchedTerm, name="relay__SwitchedTerm", curie=DSS.curie('SwitchedTerm'),
                   model_uri=DSS.relay__SwitchedTerm, domain=None, range=Optional[int])

slots.relay__type = Slot(uri=DSS.type, name="relay__type", curie=DSS.curie('type'),
                   model_uri=DSS.relay__type, domain=None, range=Optional[str])

slots.relay__Phasecurve = Slot(uri=DSS.Phasecurve, name="relay__Phasecurve", curie=DSS.curie('Phasecurve'),
                   model_uri=DSS.relay__Phasecurve, domain=None, range=Optional[float])

slots.relay__Groundcurve = Slot(uri=DSS.Groundcurve, name="relay__Groundcurve", curie=DSS.curie('Groundcurve'),
                   model_uri=DSS.relay__Groundcurve, domain=None, range=Optional[float])

slots.relay__PhaseTrip = Slot(uri=DSS.PhaseTrip, name="relay__PhaseTrip", curie=DSS.curie('PhaseTrip'),
                   model_uri=DSS.relay__PhaseTrip, domain=None, range=Optional[str])

slots.relay__GroundTrip = Slot(uri=DSS.GroundTrip, name="relay__GroundTrip", curie=DSS.curie('GroundTrip'),
                   model_uri=DSS.relay__GroundTrip, domain=None, range=Optional[str])

slots.relay__TDPhase = Slot(uri=DSS.TDPhase, name="relay__TDPhase", curie=DSS.curie('TDPhase'),
                   model_uri=DSS.relay__TDPhase, domain=None, range=Optional[str])

slots.relay__TDGround = Slot(uri=DSS.TDGround, name="relay__TDGround", curie=DSS.curie('TDGround'),
                   model_uri=DSS.relay__TDGround, domain=None, range=Optional[str])

slots.relay__PhaseInst = Slot(uri=DSS.PhaseInst, name="relay__PhaseInst", curie=DSS.curie('PhaseInst'),
                   model_uri=DSS.relay__PhaseInst, domain=None, range=Optional[float])

slots.relay__GroundInst = Slot(uri=DSS.GroundInst, name="relay__GroundInst", curie=DSS.curie('GroundInst'),
                   model_uri=DSS.relay__GroundInst, domain=None, range=Optional[str])

slots.relay__Reset = Slot(uri=DSS.Reset, name="relay__Reset", curie=DSS.curie('Reset'),
                   model_uri=DSS.relay__Reset, domain=None, range=Optional[str])

slots.relay__Shots = Slot(uri=DSS.Shots, name="relay__Shots", curie=DSS.curie('Shots'),
                   model_uri=DSS.relay__Shots, domain=None, range=Optional[int])

slots.relay__RecloseIntervals = Slot(uri=DSS.RecloseIntervals, name="relay__RecloseIntervals", curie=DSS.curie('RecloseIntervals'),
                   model_uri=DSS.relay__RecloseIntervals, domain=None, range=Optional[Union[float, list[float]]])

slots.relay__Delay = Slot(uri=DSS.Delay, name="relay__Delay", curie=DSS.curie('Delay'),
                   model_uri=DSS.relay__Delay, domain=None, range=Optional[float])

slots.relay__Overvoltcurve = Slot(uri=DSS.Overvoltcurve, name="relay__Overvoltcurve", curie=DSS.curie('Overvoltcurve'),
                   model_uri=DSS.relay__Overvoltcurve, domain=None, range=Optional[float])

slots.relay__Undervoltcurve = Slot(uri=DSS.Undervoltcurve, name="relay__Undervoltcurve", curie=DSS.curie('Undervoltcurve'),
                   model_uri=DSS.relay__Undervoltcurve, domain=None, range=Optional[float])

slots.relay__kvbase = Slot(uri=DSS.kvbase, name="relay__kvbase", curie=DSS.curie('kvbase'),
                   model_uri=DSS.relay__kvbase, domain=None, range=Optional[int])

slots.relay__pct_47_pickup = Slot(uri=DSS.pct_47_pickup, name="relay__pct_47_pickup", curie=DSS.curie('pct_47_pickup'),
                   model_uri=DSS.relay__pct_47_pickup, domain=None, range=Optional[float])

slots.relay__neg_seq_46_base_amps = Slot(uri=DSS.neg_seq_46_base_amps, name="relay__neg_seq_46_base_amps", curie=DSS.curie('neg_seq_46_base_amps'),
                   model_uri=DSS.relay__neg_seq_46_base_amps, domain=None, range=Optional[float])

slots.relay__pct_46_pickup = Slot(uri=DSS.pct_46_pickup, name="relay__pct_46_pickup", curie=DSS.curie('pct_46_pickup'),
                   model_uri=DSS.relay__pct_46_pickup, domain=None, range=Optional[float])

slots.relay__neg_seq_46_isqt = Slot(uri=DSS.neg_seq_46_isqt, name="relay__neg_seq_46_isqt", curie=DSS.curie('neg_seq_46_isqt'),
                   model_uri=DSS.relay__neg_seq_46_isqt, domain=None, range=Optional[float])

slots.relay__Variable = Slot(uri=DSS.Variable, name="relay__Variable", curie=DSS.curie('Variable'),
                   model_uri=DSS.relay__Variable, domain=None, range=Optional[str])

slots.relay__overtrip = Slot(uri=DSS.overtrip, name="relay__overtrip", curie=DSS.curie('overtrip'),
                   model_uri=DSS.relay__overtrip, domain=None, range=Optional[str])

slots.relay__undertrip = Slot(uri=DSS.undertrip, name="relay__undertrip", curie=DSS.curie('undertrip'),
                   model_uri=DSS.relay__undertrip, domain=None, range=Optional[str])

slots.relay__Breakertime = Slot(uri=DSS.Breakertime, name="relay__Breakertime", curie=DSS.curie('Breakertime'),
                   model_uri=DSS.relay__Breakertime, domain=None, range=Optional[float])

slots.relay__action = Slot(uri=DSS.action, name="relay__action", curie=DSS.curie('action'),
                   model_uri=DSS.relay__action, domain=None, range=Optional[str])

slots.relay__Z1mag = Slot(uri=DSS.Z1mag, name="relay__Z1mag", curie=DSS.curie('Z1mag'),
                   model_uri=DSS.relay__Z1mag, domain=None, range=Optional[float])

slots.relay__Z1ang = Slot(uri=DSS.Z1ang, name="relay__Z1ang", curie=DSS.curie('Z1ang'),
                   model_uri=DSS.relay__Z1ang, domain=None, range=Optional[float])

slots.relay__Z0mag = Slot(uri=DSS.Z0mag, name="relay__Z0mag", curie=DSS.curie('Z0mag'),
                   model_uri=DSS.relay__Z0mag, domain=None, range=Optional[float])

slots.relay__Z0ang = Slot(uri=DSS.Z0ang, name="relay__Z0ang", curie=DSS.curie('Z0ang'),
                   model_uri=DSS.relay__Z0ang, domain=None, range=Optional[float])

slots.relay__Mphase = Slot(uri=DSS.Mphase, name="relay__Mphase", curie=DSS.curie('Mphase'),
                   model_uri=DSS.relay__Mphase, domain=None, range=Optional[str])

slots.relay__Mground = Slot(uri=DSS.Mground, name="relay__Mground", curie=DSS.curie('Mground'),
                   model_uri=DSS.relay__Mground, domain=None, range=Optional[str])

slots.relay__EventLog = Slot(uri=DSS.EventLog, name="relay__EventLog", curie=DSS.curie('EventLog'),
                   model_uri=DSS.relay__EventLog, domain=None, range=Optional[str])

slots.relay__DebugTrace = Slot(uri=DSS.DebugTrace, name="relay__DebugTrace", curie=DSS.curie('DebugTrace'),
                   model_uri=DSS.relay__DebugTrace, domain=None, range=Optional[str])

slots.relay__DistReverse = Slot(uri=DSS.DistReverse, name="relay__DistReverse", curie=DSS.curie('DistReverse'),
                   model_uri=DSS.relay__DistReverse, domain=None, range=Optional[str])

slots.relay__Normal = Slot(uri=DSS.Normal, name="relay__Normal", curie=DSS.curie('Normal'),
                   model_uri=DSS.relay__Normal, domain=None, range=Optional[str])

slots.relay__State = Slot(uri=DSS.State, name="relay__State", curie=DSS.curie('State'),
                   model_uri=DSS.relay__State, domain=None, range=Optional[str])

slots.relay__DOC_TiltAngleLow = Slot(uri=DSS.DOC_TiltAngleLow, name="relay__DOC_TiltAngleLow", curie=DSS.curie('DOC_TiltAngleLow'),
                   model_uri=DSS.relay__DOC_TiltAngleLow, domain=None, range=Optional[float])

slots.relay__DOC_TiltAngleHigh = Slot(uri=DSS.DOC_TiltAngleHigh, name="relay__DOC_TiltAngleHigh", curie=DSS.curie('DOC_TiltAngleHigh'),
                   model_uri=DSS.relay__DOC_TiltAngleHigh, domain=None, range=Optional[float])

slots.relay__DOC_TripSettingLow = Slot(uri=DSS.DOC_TripSettingLow, name="relay__DOC_TripSettingLow", curie=DSS.curie('DOC_TripSettingLow'),
                   model_uri=DSS.relay__DOC_TripSettingLow, domain=None, range=Optional[float])

slots.relay__DOC_TripSettingHigh = Slot(uri=DSS.DOC_TripSettingHigh, name="relay__DOC_TripSettingHigh", curie=DSS.curie('DOC_TripSettingHigh'),
                   model_uri=DSS.relay__DOC_TripSettingHigh, domain=None, range=Optional[float])

slots.relay__DOC_TripSettingMag = Slot(uri=DSS.DOC_TripSettingMag, name="relay__DOC_TripSettingMag", curie=DSS.curie('DOC_TripSettingMag'),
                   model_uri=DSS.relay__DOC_TripSettingMag, domain=None, range=Optional[float])

slots.relay__DOC_DelayInner = Slot(uri=DSS.DOC_DelayInner, name="relay__DOC_DelayInner", curie=DSS.curie('DOC_DelayInner'),
                   model_uri=DSS.relay__DOC_DelayInner, domain=None, range=Optional[str])

slots.relay__DOC_PhaseCurveInner = Slot(uri=DSS.DOC_PhaseCurveInner, name="relay__DOC_PhaseCurveInner", curie=DSS.curie('DOC_PhaseCurveInner'),
                   model_uri=DSS.relay__DOC_PhaseCurveInner, domain=None, range=Optional[float])

slots.relay__DOC_PhaseTripInner = Slot(uri=DSS.DOC_PhaseTripInner, name="relay__DOC_PhaseTripInner", curie=DSS.curie('DOC_PhaseTripInner'),
                   model_uri=DSS.relay__DOC_PhaseTripInner, domain=None, range=Optional[str])

slots.relay__DOC_TDPhaseInner = Slot(uri=DSS.DOC_TDPhaseInner, name="relay__DOC_TDPhaseInner", curie=DSS.curie('DOC_TDPhaseInner'),
                   model_uri=DSS.relay__DOC_TDPhaseInner, domain=None, range=Optional[str])

slots.relay__DOC_P1Blocking = Slot(uri=DSS.DOC_P1Blocking, name="relay__DOC_P1Blocking", curie=DSS.curie('DOC_P1Blocking'),
                   model_uri=DSS.relay__DOC_P1Blocking, domain=None, range=Optional[float])

slots.relay__basefreq = Slot(uri=DSS.basefreq, name="relay__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.relay__basefreq, domain=None, range=Optional[float])

slots.relay__enabled = Slot(uri=DSS.enabled, name="relay__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.relay__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.relay__like = Slot(uri=DSS.like, name="relay__like", curie=DSS.curie('like'),
                   model_uri=DSS.relay__like, domain=None, range=Optional[str])

slots.storagecontroller__name = Slot(uri=DSS.name, name="storagecontroller__name", curie=DSS.curie('name'),
                   model_uri=DSS.storagecontroller__name, domain=None, range=URIRef)

slots.storagecontroller__Element = Slot(uri=DSS.Element, name="storagecontroller__Element", curie=DSS.curie('Element'),
                   model_uri=DSS.storagecontroller__Element, domain=None, range=Optional[str])

slots.storagecontroller__Terminal = Slot(uri=DSS.Terminal, name="storagecontroller__Terminal", curie=DSS.curie('Terminal'),
                   model_uri=DSS.storagecontroller__Terminal, domain=None, range=Optional[int])

slots.storagecontroller__MonPhase = Slot(uri=DSS.MonPhase, name="storagecontroller__MonPhase", curie=DSS.curie('MonPhase'),
                   model_uri=DSS.storagecontroller__MonPhase, domain=None, range=Optional[int])

slots.storagecontroller__kWTarget = Slot(uri=DSS.kWTarget, name="storagecontroller__kWTarget", curie=DSS.curie('kWTarget'),
                   model_uri=DSS.storagecontroller__kWTarget, domain=None, range=Optional[float])

slots.storagecontroller__kWTargetLow = Slot(uri=DSS.kWTargetLow, name="storagecontroller__kWTargetLow", curie=DSS.curie('kWTargetLow'),
                   model_uri=DSS.storagecontroller__kWTargetLow, domain=None, range=Optional[float])

slots.storagecontroller__pct_kWBand = Slot(uri=DSS.pct_kWBand, name="storagecontroller__pct_kWBand", curie=DSS.curie('pct_kWBand'),
                   model_uri=DSS.storagecontroller__pct_kWBand, domain=None, range=Optional[float])

slots.storagecontroller__kWBand = Slot(uri=DSS.kWBand, name="storagecontroller__kWBand", curie=DSS.curie('kWBand'),
                   model_uri=DSS.storagecontroller__kWBand, domain=None, range=Optional[float])

slots.storagecontroller__pct_kWBandLow = Slot(uri=DSS.pct_kWBandLow, name="storagecontroller__pct_kWBandLow", curie=DSS.curie('pct_kWBandLow'),
                   model_uri=DSS.storagecontroller__pct_kWBandLow, domain=None, range=Optional[float])

slots.storagecontroller__kWBandLow = Slot(uri=DSS.kWBandLow, name="storagecontroller__kWBandLow", curie=DSS.curie('kWBandLow'),
                   model_uri=DSS.storagecontroller__kWBandLow, domain=None, range=Optional[float])

slots.storagecontroller__ElementList = Slot(uri=DSS.ElementList, name="storagecontroller__ElementList", curie=DSS.curie('ElementList'),
                   model_uri=DSS.storagecontroller__ElementList, domain=None, range=Optional[Union[str, list[str]]])

slots.storagecontroller__Weights = Slot(uri=DSS.Weights, name="storagecontroller__Weights", curie=DSS.curie('Weights'),
                   model_uri=DSS.storagecontroller__Weights, domain=None, range=Optional[Union[float, list[float]]])

slots.storagecontroller__ModeDischarge = Slot(uri=DSS.ModeDischarge, name="storagecontroller__ModeDischarge", curie=DSS.curie('ModeDischarge'),
                   model_uri=DSS.storagecontroller__ModeDischarge, domain=None, range=Optional[float])

slots.storagecontroller__ModeCharge = Slot(uri=DSS.ModeCharge, name="storagecontroller__ModeCharge", curie=DSS.curie('ModeCharge'),
                   model_uri=DSS.storagecontroller__ModeCharge, domain=None, range=Optional[float])

slots.storagecontroller__TimeDischargeTrigger = Slot(uri=DSS.TimeDischargeTrigger, name="storagecontroller__TimeDischargeTrigger", curie=DSS.curie('TimeDischargeTrigger'),
                   model_uri=DSS.storagecontroller__TimeDischargeTrigger, domain=None, range=Optional[float])

slots.storagecontroller__TimeChargeTrigger = Slot(uri=DSS.TimeChargeTrigger, name="storagecontroller__TimeChargeTrigger", curie=DSS.curie('TimeChargeTrigger'),
                   model_uri=DSS.storagecontroller__TimeChargeTrigger, domain=None, range=Optional[str])

slots.storagecontroller__pct_RatekW = Slot(uri=DSS.pct_RatekW, name="storagecontroller__pct_RatekW", curie=DSS.curie('pct_RatekW'),
                   model_uri=DSS.storagecontroller__pct_RatekW, domain=None, range=Optional[float])

slots.storagecontroller__pct_RateCharge = Slot(uri=DSS.pct_RateCharge, name="storagecontroller__pct_RateCharge", curie=DSS.curie('pct_RateCharge'),
                   model_uri=DSS.storagecontroller__pct_RateCharge, domain=None, range=Optional[float])

slots.storagecontroller__pct_Reserve = Slot(uri=DSS.pct_Reserve, name="storagecontroller__pct_Reserve", curie=DSS.curie('pct_Reserve'),
                   model_uri=DSS.storagecontroller__pct_Reserve, domain=None, range=Optional[str])

slots.storagecontroller__kWhTotal = Slot(uri=DSS.kWhTotal, name="storagecontroller__kWhTotal", curie=DSS.curie('kWhTotal'),
                   model_uri=DSS.storagecontroller__kWhTotal, domain=None, range=Optional[float])

slots.storagecontroller__kWTotal = Slot(uri=DSS.kWTotal, name="storagecontroller__kWTotal", curie=DSS.curie('kWTotal'),
                   model_uri=DSS.storagecontroller__kWTotal, domain=None, range=Optional[float])

slots.storagecontroller__kWhActual = Slot(uri=DSS.kWhActual, name="storagecontroller__kWhActual", curie=DSS.curie('kWhActual'),
                   model_uri=DSS.storagecontroller__kWhActual, domain=None, range=Optional[float])

slots.storagecontroller__kWActual = Slot(uri=DSS.kWActual, name="storagecontroller__kWActual", curie=DSS.curie('kWActual'),
                   model_uri=DSS.storagecontroller__kWActual, domain=None, range=Optional[float])

slots.storagecontroller__kWneed = Slot(uri=DSS.kWneed, name="storagecontroller__kWneed", curie=DSS.curie('kWneed'),
                   model_uri=DSS.storagecontroller__kWneed, domain=None, range=Optional[float])

slots.storagecontroller__Yearly = Slot(uri=DSS.Yearly, name="storagecontroller__Yearly", curie=DSS.curie('Yearly'),
                   model_uri=DSS.storagecontroller__Yearly, domain=None, range=Optional[str])

slots.storagecontroller__Daily = Slot(uri=DSS.Daily, name="storagecontroller__Daily", curie=DSS.curie('Daily'),
                   model_uri=DSS.storagecontroller__Daily, domain=None, range=Optional[str])

slots.storagecontroller__Duty = Slot(uri=DSS.Duty, name="storagecontroller__Duty", curie=DSS.curie('Duty'),
                   model_uri=DSS.storagecontroller__Duty, domain=None, range=Optional[str])

slots.storagecontroller__EventLog = Slot(uri=DSS.EventLog, name="storagecontroller__EventLog", curie=DSS.curie('EventLog'),
                   model_uri=DSS.storagecontroller__EventLog, domain=None, range=Optional[Union[bool, Bool]])

slots.storagecontroller__InhibitTime = Slot(uri=DSS.InhibitTime, name="storagecontroller__InhibitTime", curie=DSS.curie('InhibitTime'),
                   model_uri=DSS.storagecontroller__InhibitTime, domain=None, range=Optional[int])

slots.storagecontroller__Tup = Slot(uri=DSS.Tup, name="storagecontroller__Tup", curie=DSS.curie('Tup'),
                   model_uri=DSS.storagecontroller__Tup, domain=None, range=Optional[str])

slots.storagecontroller__TFlat = Slot(uri=DSS.TFlat, name="storagecontroller__TFlat", curie=DSS.curie('TFlat'),
                   model_uri=DSS.storagecontroller__TFlat, domain=None, range=Optional[str])

slots.storagecontroller__Tdn = Slot(uri=DSS.Tdn, name="storagecontroller__Tdn", curie=DSS.curie('Tdn'),
                   model_uri=DSS.storagecontroller__Tdn, domain=None, range=Optional[str])

slots.storagecontroller__kWThreshold = Slot(uri=DSS.kWThreshold, name="storagecontroller__kWThreshold", curie=DSS.curie('kWThreshold'),
                   model_uri=DSS.storagecontroller__kWThreshold, domain=None, range=Optional[float])

slots.storagecontroller__DispFactor = Slot(uri=DSS.DispFactor, name="storagecontroller__DispFactor", curie=DSS.curie('DispFactor'),
                   model_uri=DSS.storagecontroller__DispFactor, domain=None, range=Optional[float])

slots.storagecontroller__ResetLevel = Slot(uri=DSS.ResetLevel, name="storagecontroller__ResetLevel", curie=DSS.curie('ResetLevel'),
                   model_uri=DSS.storagecontroller__ResetLevel, domain=None, range=Optional[str])

slots.storagecontroller__Seasons = Slot(uri=DSS.Seasons, name="storagecontroller__Seasons", curie=DSS.curie('Seasons'),
                   model_uri=DSS.storagecontroller__Seasons, domain=None, range=Optional[int])

slots.storagecontroller__SeasonTargets = Slot(uri=DSS.SeasonTargets, name="storagecontroller__SeasonTargets", curie=DSS.curie('SeasonTargets'),
                   model_uri=DSS.storagecontroller__SeasonTargets, domain=None, range=Optional[Union[float, list[float]]])

slots.storagecontroller__SeasonTargetsLow = Slot(uri=DSS.SeasonTargetsLow, name="storagecontroller__SeasonTargetsLow", curie=DSS.curie('SeasonTargetsLow'),
                   model_uri=DSS.storagecontroller__SeasonTargetsLow, domain=None, range=Optional[Union[float, list[float]]])

slots.storagecontroller__basefreq = Slot(uri=DSS.basefreq, name="storagecontroller__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.storagecontroller__basefreq, domain=None, range=Optional[float])

slots.storagecontroller__enabled = Slot(uri=DSS.enabled, name="storagecontroller__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.storagecontroller__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.storagecontroller__like = Slot(uri=DSS.like, name="storagecontroller__like", curie=DSS.curie('like'),
                   model_uri=DSS.storagecontroller__like, domain=None, range=Optional[str])

slots.swtcontrol__name = Slot(uri=DSS.name, name="swtcontrol__name", curie=DSS.curie('name'),
                   model_uri=DSS.swtcontrol__name, domain=None, range=URIRef)

slots.swtcontrol__SwitchedObj = Slot(uri=DSS.SwitchedObj, name="swtcontrol__SwitchedObj", curie=DSS.curie('SwitchedObj'),
                   model_uri=DSS.swtcontrol__SwitchedObj, domain=None, range=Optional[str])

slots.swtcontrol__SwitchedTerm = Slot(uri=DSS.SwitchedTerm, name="swtcontrol__SwitchedTerm", curie=DSS.curie('SwitchedTerm'),
                   model_uri=DSS.swtcontrol__SwitchedTerm, domain=None, range=Optional[int])

slots.swtcontrol__Action = Slot(uri=DSS.Action, name="swtcontrol__Action", curie=DSS.curie('Action'),
                   model_uri=DSS.swtcontrol__Action, domain=None, range=Optional[str])

slots.swtcontrol__Lock = Slot(uri=DSS.Lock, name="swtcontrol__Lock", curie=DSS.curie('Lock'),
                   model_uri=DSS.swtcontrol__Lock, domain=None, range=Optional[Union[bool, Bool]])

slots.swtcontrol__Delay = Slot(uri=DSS.Delay, name="swtcontrol__Delay", curie=DSS.curie('Delay'),
                   model_uri=DSS.swtcontrol__Delay, domain=None, range=Optional[float])

slots.swtcontrol__Normal = Slot(uri=DSS.Normal, name="swtcontrol__Normal", curie=DSS.curie('Normal'),
                   model_uri=DSS.swtcontrol__Normal, domain=None, range=Optional[str])

slots.swtcontrol__State = Slot(uri=DSS.State, name="swtcontrol__State", curie=DSS.curie('State'),
                   model_uri=DSS.swtcontrol__State, domain=None, range=Optional[str])

slots.swtcontrol__Reset = Slot(uri=DSS.Reset, name="swtcontrol__Reset", curie=DSS.curie('Reset'),
                   model_uri=DSS.swtcontrol__Reset, domain=None, range=Optional[Union[bool, Bool]])

slots.swtcontrol__basefreq = Slot(uri=DSS.basefreq, name="swtcontrol__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.swtcontrol__basefreq, domain=None, range=Optional[float])

slots.swtcontrol__enabled = Slot(uri=DSS.enabled, name="swtcontrol__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.swtcontrol__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.swtcontrol__like = Slot(uri=DSS.like, name="swtcontrol__like", curie=DSS.curie('like'),
                   model_uri=DSS.swtcontrol__like, domain=None, range=Optional[str])

slots.upfccontrol__name = Slot(uri=DSS.name, name="upfccontrol__name", curie=DSS.curie('name'),
                   model_uri=DSS.upfccontrol__name, domain=None, range=URIRef)

slots.upfccontrol__UPFCList = Slot(uri=DSS.UPFCList, name="upfccontrol__UPFCList", curie=DSS.curie('UPFCList'),
                   model_uri=DSS.upfccontrol__UPFCList, domain=None, range=Optional[str])

slots.upfccontrol__basefreq = Slot(uri=DSS.basefreq, name="upfccontrol__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.upfccontrol__basefreq, domain=None, range=Optional[float])

slots.upfccontrol__enabled = Slot(uri=DSS.enabled, name="upfccontrol__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.upfccontrol__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.upfccontrol__like = Slot(uri=DSS.like, name="upfccontrol__like", curie=DSS.curie('like'),
                   model_uri=DSS.upfccontrol__like, domain=None, range=Optional[str])

slots.buscoords__name = Slot(uri=DSS.name, name="buscoords__name", curie=DSS.curie('name'),
                   model_uri=DSS.buscoords__name, domain=None, range=URIRef)

slots.buscoords__x = Slot(uri=DSS.x, name="buscoords__x", curie=DSS.curie('x'),
                   model_uri=DSS.buscoords__x, domain=None, range=Optional[float])

slots.buscoords__y = Slot(uri=DSS.y, name="buscoords__y", curie=DSS.curie('y'),
                   model_uri=DSS.buscoords__y, domain=None, range=Optional[float])

slots.buscoords__geographic = Slot(uri=DSS.geographic, name="buscoords__geographic", curie=DSS.curie('geographic'),
                   model_uri=DSS.buscoords__geographic, domain=None, range=Optional[Union[bool, Bool]])

slots.cndata__name = Slot(uri=DSS.name, name="cndata__name", curie=DSS.curie('name'),
                   model_uri=DSS.cndata__name, domain=None, range=URIRef)

slots.cndata__k = Slot(uri=DSS.k, name="cndata__k", curie=DSS.curie('k'),
                   model_uri=DSS.cndata__k, domain=None, range=Optional[int])

slots.cndata__DiaStrand = Slot(uri=DSS.DiaStrand, name="cndata__DiaStrand", curie=DSS.curie('DiaStrand'),
                   model_uri=DSS.cndata__DiaStrand, domain=None, range=Optional[float])

slots.cndata__GmrStrand = Slot(uri=DSS.GmrStrand, name="cndata__GmrStrand", curie=DSS.curie('GmrStrand'),
                   model_uri=DSS.cndata__GmrStrand, domain=None, range=Optional[float])

slots.cndata__Rstrand = Slot(uri=DSS.Rstrand, name="cndata__Rstrand", curie=DSS.curie('Rstrand'),
                   model_uri=DSS.cndata__Rstrand, domain=None, range=Optional[float])

slots.cndata__SemiconLayer = Slot(uri=DSS.SemiconLayer, name="cndata__SemiconLayer", curie=DSS.curie('SemiconLayer'),
                   model_uri=DSS.cndata__SemiconLayer, domain=None, range=Optional[Union[bool, Bool]])

slots.cndata__EpsR = Slot(uri=DSS.EpsR, name="cndata__EpsR", curie=DSS.curie('EpsR'),
                   model_uri=DSS.cndata__EpsR, domain=None, range=Optional[float])

slots.cndata__InsLayer = Slot(uri=DSS.InsLayer, name="cndata__InsLayer", curie=DSS.curie('InsLayer'),
                   model_uri=DSS.cndata__InsLayer, domain=None, range=Optional[float])

slots.cndata__DiaIns = Slot(uri=DSS.DiaIns, name="cndata__DiaIns", curie=DSS.curie('DiaIns'),
                   model_uri=DSS.cndata__DiaIns, domain=None, range=Optional[float])

slots.cndata__DiaCable = Slot(uri=DSS.DiaCable, name="cndata__DiaCable", curie=DSS.curie('DiaCable'),
                   model_uri=DSS.cndata__DiaCable, domain=None, range=Optional[float])

slots.cndata__Rdc = Slot(uri=DSS.Rdc, name="cndata__Rdc", curie=DSS.curie('Rdc'),
                   model_uri=DSS.cndata__Rdc, domain=None, range=Optional[float])

slots.cndata__Rac = Slot(uri=DSS.Rac, name="cndata__Rac", curie=DSS.curie('Rac'),
                   model_uri=DSS.cndata__Rac, domain=None, range=Optional[float])

slots.cndata__Runits = Slot(uri=DSS.Runits, name="cndata__Runits", curie=DSS.curie('Runits'),
                   model_uri=DSS.cndata__Runits, domain=None, range=Optional[str])

slots.cndata__GMRac = Slot(uri=DSS.GMRac, name="cndata__GMRac", curie=DSS.curie('GMRac'),
                   model_uri=DSS.cndata__GMRac, domain=None, range=Optional[float])

slots.cndata__GMRunits = Slot(uri=DSS.GMRunits, name="cndata__GMRunits", curie=DSS.curie('GMRunits'),
                   model_uri=DSS.cndata__GMRunits, domain=None, range=Optional[str])

slots.cndata__radius = Slot(uri=DSS.radius, name="cndata__radius", curie=DSS.curie('radius'),
                   model_uri=DSS.cndata__radius, domain=None, range=Optional[float])

slots.cndata__radunits = Slot(uri=DSS.radunits, name="cndata__radunits", curie=DSS.curie('radunits'),
                   model_uri=DSS.cndata__radunits, domain=None, range=Optional[str])

slots.cndata__normamps = Slot(uri=DSS.normamps, name="cndata__normamps", curie=DSS.curie('normamps'),
                   model_uri=DSS.cndata__normamps, domain=None, range=Optional[float])

slots.cndata__emergamps = Slot(uri=DSS.emergamps, name="cndata__emergamps", curie=DSS.curie('emergamps'),
                   model_uri=DSS.cndata__emergamps, domain=None, range=Optional[float])

slots.cndata__diam = Slot(uri=DSS.diam, name="cndata__diam", curie=DSS.curie('diam'),
                   model_uri=DSS.cndata__diam, domain=None, range=Optional[float])

slots.cndata__Seasons = Slot(uri=DSS.Seasons, name="cndata__Seasons", curie=DSS.curie('Seasons'),
                   model_uri=DSS.cndata__Seasons, domain=None, range=Optional[int])

slots.cndata__Ratings = Slot(uri=DSS.Ratings, name="cndata__Ratings", curie=DSS.curie('Ratings'),
                   model_uri=DSS.cndata__Ratings, domain=None, range=Optional[Union[float, list[float]]])

slots.cndata__Capradius = Slot(uri=DSS.Capradius, name="cndata__Capradius", curie=DSS.curie('Capradius'),
                   model_uri=DSS.cndata__Capradius, domain=None, range=Optional[float])

slots.cndata__like = Slot(uri=DSS.like, name="cndata__like", curie=DSS.curie('like'),
                   model_uri=DSS.cndata__like, domain=None, range=Optional[str])

slots.dynamicexp__name = Slot(uri=DSS.name, name="dynamicexp__name", curie=DSS.curie('name'),
                   model_uri=DSS.dynamicexp__name, domain=None, range=URIRef)

slots.dynamicexp__nvariables = Slot(uri=DSS.nvariables, name="dynamicexp__nvariables", curie=DSS.curie('nvariables'),
                   model_uri=DSS.dynamicexp__nvariables, domain=None, range=Optional[int])

slots.dynamicexp__varnames = Slot(uri=DSS.varnames, name="dynamicexp__varnames", curie=DSS.curie('varnames'),
                   model_uri=DSS.dynamicexp__varnames, domain=None, range=Optional[Union[str, list[str]]])

slots.dynamicexp__var = Slot(uri=DSS.var, name="dynamicexp__var", curie=DSS.curie('var'),
                   model_uri=DSS.dynamicexp__var, domain=None, range=Optional[str])

slots.dynamicexp__varidx = Slot(uri=DSS.varidx, name="dynamicexp__varidx", curie=DSS.curie('varidx'),
                   model_uri=DSS.dynamicexp__varidx, domain=None, range=Optional[str])

slots.dynamicexp__expression = Slot(uri=DSS.expression, name="dynamicexp__expression", curie=DSS.curie('expression'),
                   model_uri=DSS.dynamicexp__expression, domain=None, range=Optional[str])

slots.dynamicexp__Domain = Slot(uri=DSS.Domain, name="dynamicexp__Domain", curie=DSS.curie('Domain'),
                   model_uri=DSS.dynamicexp__Domain, domain=None, range=Optional[str])

slots.dynamicexp__like = Slot(uri=DSS.like, name="dynamicexp__like", curie=DSS.curie('like'),
                   model_uri=DSS.dynamicexp__like, domain=None, range=Optional[str])

slots.growthshape__name = Slot(uri=DSS.name, name="growthshape__name", curie=DSS.curie('name'),
                   model_uri=DSS.growthshape__name, domain=None, range=URIRef)

slots.growthshape__npts = Slot(uri=DSS.npts, name="growthshape__npts", curie=DSS.curie('npts'),
                   model_uri=DSS.growthshape__npts, domain=None, range=Optional[int])

slots.growthshape__year = Slot(uri=DSS.year, name="growthshape__year", curie=DSS.curie('year'),
                   model_uri=DSS.growthshape__year, domain=None, range=Optional[Union[int, list[int]]])

slots.growthshape__mult = Slot(uri=DSS.mult, name="growthshape__mult", curie=DSS.curie('mult'),
                   model_uri=DSS.growthshape__mult, domain=None, range=Optional[Union[float, list[float]]])

slots.growthshape__csvfile = Slot(uri=DSS.csvfile, name="growthshape__csvfile", curie=DSS.curie('csvfile'),
                   model_uri=DSS.growthshape__csvfile, domain=None, range=Optional[float])

slots.growthshape__sngfile = Slot(uri=DSS.sngfile, name="growthshape__sngfile", curie=DSS.curie('sngfile'),
                   model_uri=DSS.growthshape__sngfile, domain=None, range=Optional[float])

slots.growthshape__dblfile = Slot(uri=DSS.dblfile, name="growthshape__dblfile", curie=DSS.curie('dblfile'),
                   model_uri=DSS.growthshape__dblfile, domain=None, range=Optional[float])

slots.growthshape__like = Slot(uri=DSS.like, name="growthshape__like", curie=DSS.curie('like'),
                   model_uri=DSS.growthshape__like, domain=None, range=Optional[str])

slots.linecode__name = Slot(uri=DSS.name, name="linecode__name", curie=DSS.curie('name'),
                   model_uri=DSS.linecode__name, domain=None, range=URIRef)

slots.linecode__nphases = Slot(uri=DSS.nphases, name="linecode__nphases", curie=DSS.curie('nphases'),
                   model_uri=DSS.linecode__nphases, domain=None, range=Optional[int])

slots.linecode__r1 = Slot(uri=DSS.r1, name="linecode__r1", curie=DSS.curie('r1'),
                   model_uri=DSS.linecode__r1, domain=None, range=Optional[float])

slots.linecode__x1 = Slot(uri=DSS.x1, name="linecode__x1", curie=DSS.curie('x1'),
                   model_uri=DSS.linecode__x1, domain=None, range=Optional[float])

slots.linecode__r0 = Slot(uri=DSS.r0, name="linecode__r0", curie=DSS.curie('r0'),
                   model_uri=DSS.linecode__r0, domain=None, range=Optional[float])

slots.linecode__x0 = Slot(uri=DSS.x0, name="linecode__x0", curie=DSS.curie('x0'),
                   model_uri=DSS.linecode__x0, domain=None, range=Optional[float])

slots.linecode__C1 = Slot(uri=DSS.C1, name="linecode__C1", curie=DSS.curie('C1'),
                   model_uri=DSS.linecode__C1, domain=None, range=Optional[str])

slots.linecode__C0 = Slot(uri=DSS.C0, name="linecode__C0", curie=DSS.curie('C0'),
                   model_uri=DSS.linecode__C0, domain=None, range=Optional[str])

slots.linecode__units = Slot(uri=DSS.units, name="linecode__units", curie=DSS.curie('units'),
                   model_uri=DSS.linecode__units, domain=None, range=Optional[str])

slots.linecode__rmatrix = Slot(uri=DSS.rmatrix, name="linecode__rmatrix", curie=DSS.curie('rmatrix'),
                   model_uri=DSS.linecode__rmatrix, domain=None, range=Optional[Union[float, list[float]]])

slots.linecode__xmatrix = Slot(uri=DSS.xmatrix, name="linecode__xmatrix", curie=DSS.curie('xmatrix'),
                   model_uri=DSS.linecode__xmatrix, domain=None, range=Optional[Union[float, list[float]]])

slots.linecode__cmatrix = Slot(uri=DSS.cmatrix, name="linecode__cmatrix", curie=DSS.curie('cmatrix'),
                   model_uri=DSS.linecode__cmatrix, domain=None, range=Optional[Union[float, list[float]]])

slots.linecode__baseFreq = Slot(uri=DSS.baseFreq, name="linecode__baseFreq", curie=DSS.curie('baseFreq'),
                   model_uri=DSS.linecode__baseFreq, domain=None, range=Optional[str])

slots.linecode__normamps = Slot(uri=DSS.normamps, name="linecode__normamps", curie=DSS.curie('normamps'),
                   model_uri=DSS.linecode__normamps, domain=None, range=Optional[float])

slots.linecode__emergamps = Slot(uri=DSS.emergamps, name="linecode__emergamps", curie=DSS.curie('emergamps'),
                   model_uri=DSS.linecode__emergamps, domain=None, range=Optional[float])

slots.linecode__faultrate = Slot(uri=DSS.faultrate, name="linecode__faultrate", curie=DSS.curie('faultrate'),
                   model_uri=DSS.linecode__faultrate, domain=None, range=Optional[float])

slots.linecode__pctperm = Slot(uri=DSS.pctperm, name="linecode__pctperm", curie=DSS.curie('pctperm'),
                   model_uri=DSS.linecode__pctperm, domain=None, range=Optional[float])

slots.linecode__repair = Slot(uri=DSS.repair, name="linecode__repair", curie=DSS.curie('repair'),
                   model_uri=DSS.linecode__repair, domain=None, range=Optional[str])

slots.linecode__Kron = Slot(uri=DSS.Kron, name="linecode__Kron", curie=DSS.curie('Kron'),
                   model_uri=DSS.linecode__Kron, domain=None, range=Optional[str])

slots.linecode__Rg = Slot(uri=DSS.Rg, name="linecode__Rg", curie=DSS.curie('Rg'),
                   model_uri=DSS.linecode__Rg, domain=None, range=Optional[float])

slots.linecode__Xg = Slot(uri=DSS.Xg, name="linecode__Xg", curie=DSS.curie('Xg'),
                   model_uri=DSS.linecode__Xg, domain=None, range=Optional[float])

slots.linecode__rho = Slot(uri=DSS.rho, name="linecode__rho", curie=DSS.curie('rho'),
                   model_uri=DSS.linecode__rho, domain=None, range=Optional[float])

slots.linecode__neutral = Slot(uri=DSS.neutral, name="linecode__neutral", curie=DSS.curie('neutral'),
                   model_uri=DSS.linecode__neutral, domain=None, range=Optional[str])

slots.linecode__B1 = Slot(uri=DSS.B1, name="linecode__B1", curie=DSS.curie('B1'),
                   model_uri=DSS.linecode__B1, domain=None, range=Optional[str])

slots.linecode__B0 = Slot(uri=DSS.B0, name="linecode__B0", curie=DSS.curie('B0'),
                   model_uri=DSS.linecode__B0, domain=None, range=Optional[str])

slots.linecode__Seasons = Slot(uri=DSS.Seasons, name="linecode__Seasons", curie=DSS.curie('Seasons'),
                   model_uri=DSS.linecode__Seasons, domain=None, range=Optional[int])

slots.linecode__Ratings = Slot(uri=DSS.Ratings, name="linecode__Ratings", curie=DSS.curie('Ratings'),
                   model_uri=DSS.linecode__Ratings, domain=None, range=Optional[Union[float, list[float]]])

slots.linecode__LineType = Slot(uri=DSS.LineType, name="linecode__LineType", curie=DSS.curie('LineType'),
                   model_uri=DSS.linecode__LineType, domain=None, range=Optional[float])

slots.linecode__like = Slot(uri=DSS.like, name="linecode__like", curie=DSS.curie('like'),
                   model_uri=DSS.linecode__like, domain=None, range=Optional[str])

slots.linegeometry__name = Slot(uri=DSS.name, name="linegeometry__name", curie=DSS.curie('name'),
                   model_uri=DSS.linegeometry__name, domain=None, range=URIRef)

slots.linegeometry__nconds = Slot(uri=DSS.nconds, name="linegeometry__nconds", curie=DSS.curie('nconds'),
                   model_uri=DSS.linegeometry__nconds, domain=None, range=Optional[int])

slots.linegeometry__nphases = Slot(uri=DSS.nphases, name="linegeometry__nphases", curie=DSS.curie('nphases'),
                   model_uri=DSS.linegeometry__nphases, domain=None, range=Optional[int])

slots.linegeometry__cond = Slot(uri=DSS.cond, name="linegeometry__cond", curie=DSS.curie('cond'),
                   model_uri=DSS.linegeometry__cond, domain=None, range=Optional[int])

slots.linegeometry__wire = Slot(uri=DSS.wire, name="linegeometry__wire", curie=DSS.curie('wire'),
                   model_uri=DSS.linegeometry__wire, domain=None, range=Optional[str])

slots.linegeometry__x = Slot(uri=DSS.x, name="linegeometry__x", curie=DSS.curie('x'),
                   model_uri=DSS.linegeometry__x, domain=None, range=Optional[float])

slots.linegeometry__h = Slot(uri=DSS.h, name="linegeometry__h", curie=DSS.curie('h'),
                   model_uri=DSS.linegeometry__h, domain=None, range=Optional[float])

slots.linegeometry__units = Slot(uri=DSS.units, name="linegeometry__units", curie=DSS.curie('units'),
                   model_uri=DSS.linegeometry__units, domain=None, range=Optional[str])

slots.linegeometry__normamps = Slot(uri=DSS.normamps, name="linegeometry__normamps", curie=DSS.curie('normamps'),
                   model_uri=DSS.linegeometry__normamps, domain=None, range=Optional[float])

slots.linegeometry__emergamps = Slot(uri=DSS.emergamps, name="linegeometry__emergamps", curie=DSS.curie('emergamps'),
                   model_uri=DSS.linegeometry__emergamps, domain=None, range=Optional[float])

slots.linegeometry__reduce = Slot(uri=DSS.reduce, name="linegeometry__reduce", curie=DSS.curie('reduce'),
                   model_uri=DSS.linegeometry__reduce, domain=None, range=Optional[Union[bool, Bool]])

slots.linegeometry__spacing = Slot(uri=DSS.spacing, name="linegeometry__spacing", curie=DSS.curie('spacing'),
                   model_uri=DSS.linegeometry__spacing, domain=None, range=Optional[str])

slots.linegeometry__wires = Slot(uri=DSS.wires, name="linegeometry__wires", curie=DSS.curie('wires'),
                   model_uri=DSS.linegeometry__wires, domain=None, range=Optional[Union[str, list[str]]])

slots.linegeometry__cncable = Slot(uri=DSS.cncable, name="linegeometry__cncable", curie=DSS.curie('cncable'),
                   model_uri=DSS.linegeometry__cncable, domain=None, range=Optional[str])

slots.linegeometry__tscable = Slot(uri=DSS.tscable, name="linegeometry__tscable", curie=DSS.curie('tscable'),
                   model_uri=DSS.linegeometry__tscable, domain=None, range=Optional[str])

slots.linegeometry__cncables = Slot(uri=DSS.cncables, name="linegeometry__cncables", curie=DSS.curie('cncables'),
                   model_uri=DSS.linegeometry__cncables, domain=None, range=Optional[Union[str, list[str]]])

slots.linegeometry__tscables = Slot(uri=DSS.tscables, name="linegeometry__tscables", curie=DSS.curie('tscables'),
                   model_uri=DSS.linegeometry__tscables, domain=None, range=Optional[Union[str, list[str]]])

slots.linegeometry__xs = Slot(uri=DSS.xs, name="linegeometry__xs", curie=DSS.curie('xs'),
                   model_uri=DSS.linegeometry__xs, domain=None, range=Optional[Union[float, list[float]]])

slots.linegeometry__hs = Slot(uri=DSS.hs, name="linegeometry__hs", curie=DSS.curie('hs'),
                   model_uri=DSS.linegeometry__hs, domain=None, range=Optional[Union[float, list[float]]])

slots.linegeometry__Seasons = Slot(uri=DSS.Seasons, name="linegeometry__Seasons", curie=DSS.curie('Seasons'),
                   model_uri=DSS.linegeometry__Seasons, domain=None, range=Optional[int])

slots.linegeometry__Ratings = Slot(uri=DSS.Ratings, name="linegeometry__Ratings", curie=DSS.curie('Ratings'),
                   model_uri=DSS.linegeometry__Ratings, domain=None, range=Optional[Union[float, list[float]]])

slots.linegeometry__LineType = Slot(uri=DSS.LineType, name="linegeometry__LineType", curie=DSS.curie('LineType'),
                   model_uri=DSS.linegeometry__LineType, domain=None, range=Optional[str])

slots.linegeometry__conductors = Slot(uri=DSS.conductors, name="linegeometry__conductors", curie=DSS.curie('conductors'),
                   model_uri=DSS.linegeometry__conductors, domain=None, range=Optional[Union[str, list[str]]])

slots.linegeometry__like = Slot(uri=DSS.like, name="linegeometry__like", curie=DSS.curie('like'),
                   model_uri=DSS.linegeometry__like, domain=None, range=Optional[str])

slots.linespacing__name = Slot(uri=DSS.name, name="linespacing__name", curie=DSS.curie('name'),
                   model_uri=DSS.linespacing__name, domain=None, range=URIRef)

slots.linespacing__nconds = Slot(uri=DSS.nconds, name="linespacing__nconds", curie=DSS.curie('nconds'),
                   model_uri=DSS.linespacing__nconds, domain=None, range=Optional[int])

slots.linespacing__nphases = Slot(uri=DSS.nphases, name="linespacing__nphases", curie=DSS.curie('nphases'),
                   model_uri=DSS.linespacing__nphases, domain=None, range=Optional[int])

slots.linespacing__x = Slot(uri=DSS.x, name="linespacing__x", curie=DSS.curie('x'),
                   model_uri=DSS.linespacing__x, domain=None, range=Optional[Union[float, list[float]]])

slots.linespacing__h = Slot(uri=DSS.h, name="linespacing__h", curie=DSS.curie('h'),
                   model_uri=DSS.linespacing__h, domain=None, range=Optional[Union[float, list[float]]])

slots.linespacing__units = Slot(uri=DSS.units, name="linespacing__units", curie=DSS.curie('units'),
                   model_uri=DSS.linespacing__units, domain=None, range=Optional[str])

slots.linespacing__detailed = Slot(uri=DSS.detailed, name="linespacing__detailed", curie=DSS.curie('detailed'),
                   model_uri=DSS.linespacing__detailed, domain=None, range=Optional[Union[bool, Bool]])

slots.linespacing__EqDistPhPh = Slot(uri=DSS.EqDistPhPh, name="linespacing__EqDistPhPh", curie=DSS.curie('EqDistPhPh'),
                   model_uri=DSS.linespacing__EqDistPhPh, domain=None, range=Optional[str])

slots.linespacing__EqDistPhN = Slot(uri=DSS.EqDistPhN, name="linespacing__EqDistPhN", curie=DSS.curie('EqDistPhN'),
                   model_uri=DSS.linespacing__EqDistPhN, domain=None, range=Optional[str])

slots.linespacing__AvgPhaseHeight = Slot(uri=DSS.AvgPhaseHeight, name="linespacing__AvgPhaseHeight", curie=DSS.curie('AvgPhaseHeight'),
                   model_uri=DSS.linespacing__AvgPhaseHeight, domain=None, range=Optional[str])

slots.linespacing__AvgNeutralHeight = Slot(uri=DSS.AvgNeutralHeight, name="linespacing__AvgNeutralHeight", curie=DSS.curie('AvgNeutralHeight'),
                   model_uri=DSS.linespacing__AvgNeutralHeight, domain=None, range=Optional[str])

slots.linespacing__like = Slot(uri=DSS.like, name="linespacing__like", curie=DSS.curie('like'),
                   model_uri=DSS.linespacing__like, domain=None, range=Optional[str])

slots.loadshape__name = Slot(uri=DSS.name, name="loadshape__name", curie=DSS.curie('name'),
                   model_uri=DSS.loadshape__name, domain=None, range=URIRef)

slots.loadshape__npts = Slot(uri=DSS.npts, name="loadshape__npts", curie=DSS.curie('npts'),
                   model_uri=DSS.loadshape__npts, domain=None, range=Optional[int])

slots.loadshape__interval = Slot(uri=DSS.interval, name="loadshape__interval", curie=DSS.curie('interval'),
                   model_uri=DSS.loadshape__interval, domain=None, range=Optional[float])

slots.loadshape__mult = Slot(uri=DSS.mult, name="loadshape__mult", curie=DSS.curie('mult'),
                   model_uri=DSS.loadshape__mult, domain=None, range=Optional[Union[float, list[float]]])

slots.loadshape__hour = Slot(uri=DSS.hour, name="loadshape__hour", curie=DSS.curie('hour'),
                   model_uri=DSS.loadshape__hour, domain=None, range=Optional[Union[float, list[float]]])

slots.loadshape__mean = Slot(uri=DSS.mean, name="loadshape__mean", curie=DSS.curie('mean'),
                   model_uri=DSS.loadshape__mean, domain=None, range=Optional[float])

slots.loadshape__stddev = Slot(uri=DSS.stddev, name="loadshape__stddev", curie=DSS.curie('stddev'),
                   model_uri=DSS.loadshape__stddev, domain=None, range=Optional[float])

slots.loadshape__csvfile = Slot(uri=DSS.csvfile, name="loadshape__csvfile", curie=DSS.curie('csvfile'),
                   model_uri=DSS.loadshape__csvfile, domain=None, range=Optional[int])

slots.loadshape__sngfile = Slot(uri=DSS.sngfile, name="loadshape__sngfile", curie=DSS.curie('sngfile'),
                   model_uri=DSS.loadshape__sngfile, domain=None, range=Optional[int])

slots.loadshape__dblfile = Slot(uri=DSS.dblfile, name="loadshape__dblfile", curie=DSS.curie('dblfile'),
                   model_uri=DSS.loadshape__dblfile, domain=None, range=Optional[int])

slots.loadshape__action = Slot(uri=DSS.action, name="loadshape__action", curie=DSS.curie('action'),
                   model_uri=DSS.loadshape__action, domain=None, range=Optional[str])

slots.loadshape__qmult = Slot(uri=DSS.qmult, name="loadshape__qmult", curie=DSS.curie('qmult'),
                   model_uri=DSS.loadshape__qmult, domain=None, range=Optional[Union[float, list[float]]])

slots.loadshape__UseActual = Slot(uri=DSS.UseActual, name="loadshape__UseActual", curie=DSS.curie('UseActual'),
                   model_uri=DSS.loadshape__UseActual, domain=None, range=Optional[Union[bool, Bool]])

slots.loadshape__Pmax = Slot(uri=DSS.Pmax, name="loadshape__Pmax", curie=DSS.curie('Pmax'),
                   model_uri=DSS.loadshape__Pmax, domain=None, range=Optional[float])

slots.loadshape__Qmax = Slot(uri=DSS.Qmax, name="loadshape__Qmax", curie=DSS.curie('Qmax'),
                   model_uri=DSS.loadshape__Qmax, domain=None, range=Optional[float])

slots.loadshape__sinterval = Slot(uri=DSS.sinterval, name="loadshape__sinterval", curie=DSS.curie('sinterval'),
                   model_uri=DSS.loadshape__sinterval, domain=None, range=Optional[str])

slots.loadshape__minterval = Slot(uri=DSS.minterval, name="loadshape__minterval", curie=DSS.curie('minterval'),
                   model_uri=DSS.loadshape__minterval, domain=None, range=Optional[str])

slots.loadshape__Pbase = Slot(uri=DSS.Pbase, name="loadshape__Pbase", curie=DSS.curie('Pbase'),
                   model_uri=DSS.loadshape__Pbase, domain=None, range=Optional[str])

slots.loadshape__Qbase = Slot(uri=DSS.Qbase, name="loadshape__Qbase", curie=DSS.curie('Qbase'),
                   model_uri=DSS.loadshape__Qbase, domain=None, range=Optional[str])

slots.loadshape__Pmult = Slot(uri=DSS.Pmult, name="loadshape__Pmult", curie=DSS.curie('Pmult'),
                   model_uri=DSS.loadshape__Pmult, domain=None, range=Optional[str])

slots.loadshape__PQCSVFile = Slot(uri=DSS.PQCSVFile, name="loadshape__PQCSVFile", curie=DSS.curie('PQCSVFile'),
                   model_uri=DSS.loadshape__PQCSVFile, domain=None, range=Optional[float])

slots.loadshape__MemoryMapping = Slot(uri=DSS.MemoryMapping, name="loadshape__MemoryMapping", curie=DSS.curie('MemoryMapping'),
                   model_uri=DSS.loadshape__MemoryMapping, domain=None, range=Optional[Union[bool, Bool]])

slots.loadshape__Mode = Slot(uri=DSS.Mode, name="loadshape__Mode", curie=DSS.curie('Mode'),
                   model_uri=DSS.loadshape__Mode, domain=None, range=Optional[float])

slots.loadshape__Interpolation = Slot(uri=DSS.Interpolation, name="loadshape__Interpolation", curie=DSS.curie('Interpolation'),
                   model_uri=DSS.loadshape__Interpolation, domain=None, range=Optional[str])

slots.loadshape__like = Slot(uri=DSS.like, name="loadshape__like", curie=DSS.curie('like'),
                   model_uri=DSS.loadshape__like, domain=None, range=Optional[str])

slots.priceshape__name = Slot(uri=DSS.name, name="priceshape__name", curie=DSS.curie('name'),
                   model_uri=DSS.priceshape__name, domain=None, range=URIRef)

slots.priceshape__npts = Slot(uri=DSS.npts, name="priceshape__npts", curie=DSS.curie('npts'),
                   model_uri=DSS.priceshape__npts, domain=None, range=Optional[int])

slots.priceshape__interval = Slot(uri=DSS.interval, name="priceshape__interval", curie=DSS.curie('interval'),
                   model_uri=DSS.priceshape__interval, domain=None, range=Optional[float])

slots.priceshape__price = Slot(uri=DSS.price, name="priceshape__price", curie=DSS.curie('price'),
                   model_uri=DSS.priceshape__price, domain=None, range=Optional[Union[float, list[float]]])

slots.priceshape__hour = Slot(uri=DSS.hour, name="priceshape__hour", curie=DSS.curie('hour'),
                   model_uri=DSS.priceshape__hour, domain=None, range=Optional[Union[float, list[float]]])

slots.priceshape__mean = Slot(uri=DSS.mean, name="priceshape__mean", curie=DSS.curie('mean'),
                   model_uri=DSS.priceshape__mean, domain=None, range=Optional[float])

slots.priceshape__stddev = Slot(uri=DSS.stddev, name="priceshape__stddev", curie=DSS.curie('stddev'),
                   model_uri=DSS.priceshape__stddev, domain=None, range=Optional[float])

slots.priceshape__csvfile = Slot(uri=DSS.csvfile, name="priceshape__csvfile", curie=DSS.curie('csvfile'),
                   model_uri=DSS.priceshape__csvfile, domain=None, range=Optional[int])

slots.priceshape__sngfile = Slot(uri=DSS.sngfile, name="priceshape__sngfile", curie=DSS.curie('sngfile'),
                   model_uri=DSS.priceshape__sngfile, domain=None, range=Optional[int])

slots.priceshape__dblfile = Slot(uri=DSS.dblfile, name="priceshape__dblfile", curie=DSS.curie('dblfile'),
                   model_uri=DSS.priceshape__dblfile, domain=None, range=Optional[int])

slots.priceshape__sinterval = Slot(uri=DSS.sinterval, name="priceshape__sinterval", curie=DSS.curie('sinterval'),
                   model_uri=DSS.priceshape__sinterval, domain=None, range=Optional[str])

slots.priceshape__minterval = Slot(uri=DSS.minterval, name="priceshape__minterval", curie=DSS.curie('minterval'),
                   model_uri=DSS.priceshape__minterval, domain=None, range=Optional[str])

slots.priceshape__action = Slot(uri=DSS.action, name="priceshape__action", curie=DSS.curie('action'),
                   model_uri=DSS.priceshape__action, domain=None, range=Optional[str])

slots.priceshape__like = Slot(uri=DSS.like, name="priceshape__like", curie=DSS.curie('like'),
                   model_uri=DSS.priceshape__like, domain=None, range=Optional[str])

slots.spectrum__name = Slot(uri=DSS.name, name="spectrum__name", curie=DSS.curie('name'),
                   model_uri=DSS.spectrum__name, domain=None, range=URIRef)

slots.spectrum__NumHarm = Slot(uri=DSS.NumHarm, name="spectrum__NumHarm", curie=DSS.curie('NumHarm'),
                   model_uri=DSS.spectrum__NumHarm, domain=None, range=Optional[int])

slots.spectrum__harmonic = Slot(uri=DSS.harmonic, name="spectrum__harmonic", curie=DSS.curie('harmonic'),
                   model_uri=DSS.spectrum__harmonic, domain=None, range=Optional[Union[float, list[float]]])

slots.spectrum__pct_mag = Slot(uri=DSS.pct_mag, name="spectrum__pct_mag", curie=DSS.curie('pct_mag'),
                   model_uri=DSS.spectrum__pct_mag, domain=None, range=Optional[Union[float, list[float]]])

slots.spectrum__angle = Slot(uri=DSS.angle, name="spectrum__angle", curie=DSS.curie('angle'),
                   model_uri=DSS.spectrum__angle, domain=None, range=Optional[Union[float, list[float]]])

slots.spectrum__CSVFile = Slot(uri=DSS.CSVFile, name="spectrum__CSVFile", curie=DSS.curie('CSVFile'),
                   model_uri=DSS.spectrum__CSVFile, domain=None, range=Optional[float])

slots.spectrum__like = Slot(uri=DSS.like, name="spectrum__like", curie=DSS.curie('like'),
                   model_uri=DSS.spectrum__like, domain=None, range=Optional[str])

slots.tccCurve__name = Slot(uri=DSS.name, name="tccCurve__name", curie=DSS.curie('name'),
                   model_uri=DSS.tccCurve__name, domain=None, range=URIRef)

slots.tccCurve__npts = Slot(uri=DSS.npts, name="tccCurve__npts", curie=DSS.curie('npts'),
                   model_uri=DSS.tccCurve__npts, domain=None, range=Optional[int])

slots.tccCurve__C_array = Slot(uri=DSS.C_array, name="tccCurve__C_array", curie=DSS.curie('C_array'),
                   model_uri=DSS.tccCurve__C_array, domain=None, range=Optional[Union[float, list[float]]])

slots.tccCurve__T_array = Slot(uri=DSS.T_array, name="tccCurve__T_array", curie=DSS.curie('T_array'),
                   model_uri=DSS.tccCurve__T_array, domain=None, range=Optional[Union[float, list[float]]])

slots.tccCurve__like = Slot(uri=DSS.like, name="tccCurve__like", curie=DSS.curie('like'),
                   model_uri=DSS.tccCurve__like, domain=None, range=Optional[str])

slots.tsdata__name = Slot(uri=DSS.name, name="tsdata__name", curie=DSS.curie('name'),
                   model_uri=DSS.tsdata__name, domain=None, range=URIRef)

slots.tsdata__DiaShield = Slot(uri=DSS.DiaShield, name="tsdata__DiaShield", curie=DSS.curie('DiaShield'),
                   model_uri=DSS.tsdata__DiaShield, domain=None, range=Optional[float])

slots.tsdata__TapeLayer = Slot(uri=DSS.TapeLayer, name="tsdata__TapeLayer", curie=DSS.curie('TapeLayer'),
                   model_uri=DSS.tsdata__TapeLayer, domain=None, range=Optional[float])

slots.tsdata__TapeLap = Slot(uri=DSS.TapeLap, name="tsdata__TapeLap", curie=DSS.curie('TapeLap'),
                   model_uri=DSS.tsdata__TapeLap, domain=None, range=Optional[float])

slots.tsdata__EpsR = Slot(uri=DSS.EpsR, name="tsdata__EpsR", curie=DSS.curie('EpsR'),
                   model_uri=DSS.tsdata__EpsR, domain=None, range=Optional[float])

slots.tsdata__InsLayer = Slot(uri=DSS.InsLayer, name="tsdata__InsLayer", curie=DSS.curie('InsLayer'),
                   model_uri=DSS.tsdata__InsLayer, domain=None, range=Optional[float])

slots.tsdata__DiaIns = Slot(uri=DSS.DiaIns, name="tsdata__DiaIns", curie=DSS.curie('DiaIns'),
                   model_uri=DSS.tsdata__DiaIns, domain=None, range=Optional[float])

slots.tsdata__DiaCable = Slot(uri=DSS.DiaCable, name="tsdata__DiaCable", curie=DSS.curie('DiaCable'),
                   model_uri=DSS.tsdata__DiaCable, domain=None, range=Optional[float])

slots.tsdata__Rdc = Slot(uri=DSS.Rdc, name="tsdata__Rdc", curie=DSS.curie('Rdc'),
                   model_uri=DSS.tsdata__Rdc, domain=None, range=Optional[float])

slots.tsdata__Rac = Slot(uri=DSS.Rac, name="tsdata__Rac", curie=DSS.curie('Rac'),
                   model_uri=DSS.tsdata__Rac, domain=None, range=Optional[float])

slots.tsdata__Runits = Slot(uri=DSS.Runits, name="tsdata__Runits", curie=DSS.curie('Runits'),
                   model_uri=DSS.tsdata__Runits, domain=None, range=Optional[str])

slots.tsdata__GMRac = Slot(uri=DSS.GMRac, name="tsdata__GMRac", curie=DSS.curie('GMRac'),
                   model_uri=DSS.tsdata__GMRac, domain=None, range=Optional[float])

slots.tsdata__GMRunits = Slot(uri=DSS.GMRunits, name="tsdata__GMRunits", curie=DSS.curie('GMRunits'),
                   model_uri=DSS.tsdata__GMRunits, domain=None, range=Optional[str])

slots.tsdata__radius = Slot(uri=DSS.radius, name="tsdata__radius", curie=DSS.curie('radius'),
                   model_uri=DSS.tsdata__radius, domain=None, range=Optional[float])

slots.tsdata__radunits = Slot(uri=DSS.radunits, name="tsdata__radunits", curie=DSS.curie('radunits'),
                   model_uri=DSS.tsdata__radunits, domain=None, range=Optional[str])

slots.tsdata__normamps = Slot(uri=DSS.normamps, name="tsdata__normamps", curie=DSS.curie('normamps'),
                   model_uri=DSS.tsdata__normamps, domain=None, range=Optional[float])

slots.tsdata__emergamps = Slot(uri=DSS.emergamps, name="tsdata__emergamps", curie=DSS.curie('emergamps'),
                   model_uri=DSS.tsdata__emergamps, domain=None, range=Optional[float])

slots.tsdata__diam = Slot(uri=DSS.diam, name="tsdata__diam", curie=DSS.curie('diam'),
                   model_uri=DSS.tsdata__diam, domain=None, range=Optional[float])

slots.tsdata__Seasons = Slot(uri=DSS.Seasons, name="tsdata__Seasons", curie=DSS.curie('Seasons'),
                   model_uri=DSS.tsdata__Seasons, domain=None, range=Optional[int])

slots.tsdata__Ratings = Slot(uri=DSS.Ratings, name="tsdata__Ratings", curie=DSS.curie('Ratings'),
                   model_uri=DSS.tsdata__Ratings, domain=None, range=Optional[Union[float, list[float]]])

slots.tsdata__Capradius = Slot(uri=DSS.Capradius, name="tsdata__Capradius", curie=DSS.curie('Capradius'),
                   model_uri=DSS.tsdata__Capradius, domain=None, range=Optional[float])

slots.tsdata__like = Slot(uri=DSS.like, name="tsdata__like", curie=DSS.curie('like'),
                   model_uri=DSS.tsdata__like, domain=None, range=Optional[str])

slots.tshape__name = Slot(uri=DSS.name, name="tshape__name", curie=DSS.curie('name'),
                   model_uri=DSS.tshape__name, domain=None, range=URIRef)

slots.tshape__npts = Slot(uri=DSS.npts, name="tshape__npts", curie=DSS.curie('npts'),
                   model_uri=DSS.tshape__npts, domain=None, range=Optional[int])

slots.tshape__interval = Slot(uri=DSS.interval, name="tshape__interval", curie=DSS.curie('interval'),
                   model_uri=DSS.tshape__interval, domain=None, range=Optional[float])

slots.tshape__temp = Slot(uri=DSS.temp, name="tshape__temp", curie=DSS.curie('temp'),
                   model_uri=DSS.tshape__temp, domain=None, range=Optional[Union[float, list[float]]])

slots.tshape__hour = Slot(uri=DSS.hour, name="tshape__hour", curie=DSS.curie('hour'),
                   model_uri=DSS.tshape__hour, domain=None, range=Optional[Union[float, list[float]]])

slots.tshape__mean = Slot(uri=DSS.mean, name="tshape__mean", curie=DSS.curie('mean'),
                   model_uri=DSS.tshape__mean, domain=None, range=Optional[float])

slots.tshape__stddev = Slot(uri=DSS.stddev, name="tshape__stddev", curie=DSS.curie('stddev'),
                   model_uri=DSS.tshape__stddev, domain=None, range=Optional[float])

slots.tshape__csvfile = Slot(uri=DSS.csvfile, name="tshape__csvfile", curie=DSS.curie('csvfile'),
                   model_uri=DSS.tshape__csvfile, domain=None, range=Optional[int])

slots.tshape__sngfile = Slot(uri=DSS.sngfile, name="tshape__sngfile", curie=DSS.curie('sngfile'),
                   model_uri=DSS.tshape__sngfile, domain=None, range=Optional[int])

slots.tshape__dblfile = Slot(uri=DSS.dblfile, name="tshape__dblfile", curie=DSS.curie('dblfile'),
                   model_uri=DSS.tshape__dblfile, domain=None, range=Optional[int])

slots.tshape__sinterval = Slot(uri=DSS.sinterval, name="tshape__sinterval", curie=DSS.curie('sinterval'),
                   model_uri=DSS.tshape__sinterval, domain=None, range=Optional[str])

slots.tshape__minterval = Slot(uri=DSS.minterval, name="tshape__minterval", curie=DSS.curie('minterval'),
                   model_uri=DSS.tshape__minterval, domain=None, range=Optional[str])

slots.tshape__action = Slot(uri=DSS.action, name="tshape__action", curie=DSS.curie('action'),
                   model_uri=DSS.tshape__action, domain=None, range=Optional[str])

slots.tshape__like = Slot(uri=DSS.like, name="tshape__like", curie=DSS.curie('like'),
                   model_uri=DSS.tshape__like, domain=None, range=Optional[str])

slots.wiredata__name = Slot(uri=DSS.name, name="wiredata__name", curie=DSS.curie('name'),
                   model_uri=DSS.wiredata__name, domain=None, range=URIRef)

slots.wiredata__Rdc = Slot(uri=DSS.Rdc, name="wiredata__Rdc", curie=DSS.curie('Rdc'),
                   model_uri=DSS.wiredata__Rdc, domain=None, range=Optional[float])

slots.wiredata__Rac = Slot(uri=DSS.Rac, name="wiredata__Rac", curie=DSS.curie('Rac'),
                   model_uri=DSS.wiredata__Rac, domain=None, range=Optional[float])

slots.wiredata__Runits = Slot(uri=DSS.Runits, name="wiredata__Runits", curie=DSS.curie('Runits'),
                   model_uri=DSS.wiredata__Runits, domain=None, range=Optional[str])

slots.wiredata__GMRac = Slot(uri=DSS.GMRac, name="wiredata__GMRac", curie=DSS.curie('GMRac'),
                   model_uri=DSS.wiredata__GMRac, domain=None, range=Optional[float])

slots.wiredata__GMRunits = Slot(uri=DSS.GMRunits, name="wiredata__GMRunits", curie=DSS.curie('GMRunits'),
                   model_uri=DSS.wiredata__GMRunits, domain=None, range=Optional[str])

slots.wiredata__radius = Slot(uri=DSS.radius, name="wiredata__radius", curie=DSS.curie('radius'),
                   model_uri=DSS.wiredata__radius, domain=None, range=Optional[float])

slots.wiredata__radunits = Slot(uri=DSS.radunits, name="wiredata__radunits", curie=DSS.curie('radunits'),
                   model_uri=DSS.wiredata__radunits, domain=None, range=Optional[str])

slots.wiredata__normamps = Slot(uri=DSS.normamps, name="wiredata__normamps", curie=DSS.curie('normamps'),
                   model_uri=DSS.wiredata__normamps, domain=None, range=Optional[float])

slots.wiredata__emergamps = Slot(uri=DSS.emergamps, name="wiredata__emergamps", curie=DSS.curie('emergamps'),
                   model_uri=DSS.wiredata__emergamps, domain=None, range=Optional[float])

slots.wiredata__diam = Slot(uri=DSS.diam, name="wiredata__diam", curie=DSS.curie('diam'),
                   model_uri=DSS.wiredata__diam, domain=None, range=Optional[float])

slots.wiredata__Seasons = Slot(uri=DSS.Seasons, name="wiredata__Seasons", curie=DSS.curie('Seasons'),
                   model_uri=DSS.wiredata__Seasons, domain=None, range=Optional[int])

slots.wiredata__Ratings = Slot(uri=DSS.Ratings, name="wiredata__Ratings", curie=DSS.curie('Ratings'),
                   model_uri=DSS.wiredata__Ratings, domain=None, range=Optional[Union[float, list[float]]])

slots.wiredata__Capradius = Slot(uri=DSS.Capradius, name="wiredata__Capradius", curie=DSS.curie('Capradius'),
                   model_uri=DSS.wiredata__Capradius, domain=None, range=Optional[float])

slots.wiredata__like = Slot(uri=DSS.like, name="wiredata__like", curie=DSS.curie('like'),
                   model_uri=DSS.wiredata__like, domain=None, range=Optional[str])

slots.xfmrcode__name = Slot(uri=DSS.name, name="xfmrcode__name", curie=DSS.curie('name'),
                   model_uri=DSS.xfmrcode__name, domain=None, range=URIRef)

slots.xfmrcode__phases = Slot(uri=DSS.phases, name="xfmrcode__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.xfmrcode__phases, domain=None, range=Optional[int])

slots.xfmrcode__windings = Slot(uri=DSS.windings, name="xfmrcode__windings", curie=DSS.curie('windings'),
                   model_uri=DSS.xfmrcode__windings, domain=None, range=Optional[int])

slots.xfmrcode__wdg = Slot(uri=DSS.wdg, name="xfmrcode__wdg", curie=DSS.curie('wdg'),
                   model_uri=DSS.xfmrcode__wdg, domain=None, range=Optional[int])

slots.xfmrcode__conn = Slot(uri=DSS.conn, name="xfmrcode__conn", curie=DSS.curie('conn'),
                   model_uri=DSS.xfmrcode__conn, domain=None, range=Optional[Union[str, "ConnectionType"]])

slots.xfmrcode__kV = Slot(uri=DSS.kV, name="xfmrcode__kV", curie=DSS.curie('kV'),
                   model_uri=DSS.xfmrcode__kV, domain=None, range=Optional[float])

slots.xfmrcode__kVA = Slot(uri=DSS.kVA, name="xfmrcode__kVA", curie=DSS.curie('kVA'),
                   model_uri=DSS.xfmrcode__kVA, domain=None, range=Optional[float])

slots.xfmrcode__tap = Slot(uri=DSS.tap, name="xfmrcode__tap", curie=DSS.curie('tap'),
                   model_uri=DSS.xfmrcode__tap, domain=None, range=Optional[str])

slots.xfmrcode__pct_R = Slot(uri=DSS.pct_R, name="xfmrcode__pct_R", curie=DSS.curie('pct_R'),
                   model_uri=DSS.xfmrcode__pct_R, domain=None, range=Optional[float])

slots.xfmrcode__Rneut = Slot(uri=DSS.Rneut, name="xfmrcode__Rneut", curie=DSS.curie('Rneut'),
                   model_uri=DSS.xfmrcode__Rneut, domain=None, range=Optional[float])

slots.xfmrcode__Xneut = Slot(uri=DSS.Xneut, name="xfmrcode__Xneut", curie=DSS.curie('Xneut'),
                   model_uri=DSS.xfmrcode__Xneut, domain=None, range=Optional[float])

slots.xfmrcode__conns = Slot(uri=DSS.conns, name="xfmrcode__conns", curie=DSS.curie('conns'),
                   model_uri=DSS.xfmrcode__conns, domain=None, range=Optional[Union[Union[str, "ConnectionType"], list[Union[str, "ConnectionType"]]]])

slots.xfmrcode__kVs = Slot(uri=DSS.kVs, name="xfmrcode__kVs", curie=DSS.curie('kVs'),
                   model_uri=DSS.xfmrcode__kVs, domain=None, range=Optional[Union[float, list[float]]])

slots.xfmrcode__kVAs = Slot(uri=DSS.kVAs, name="xfmrcode__kVAs", curie=DSS.curie('kVAs'),
                   model_uri=DSS.xfmrcode__kVAs, domain=None, range=Optional[Union[float, list[float]]])

slots.xfmrcode__taps = Slot(uri=DSS.taps, name="xfmrcode__taps", curie=DSS.curie('taps'),
                   model_uri=DSS.xfmrcode__taps, domain=None, range=Optional[Union[float, list[float]]])

slots.xfmrcode__Xhl = Slot(uri=DSS.Xhl, name="xfmrcode__Xhl", curie=DSS.curie('Xhl'),
                   model_uri=DSS.xfmrcode__Xhl, domain=None, range=Optional[float])

slots.xfmrcode__Xht = Slot(uri=DSS.Xht, name="xfmrcode__Xht", curie=DSS.curie('Xht'),
                   model_uri=DSS.xfmrcode__Xht, domain=None, range=Optional[float])

slots.xfmrcode__Xlt = Slot(uri=DSS.Xlt, name="xfmrcode__Xlt", curie=DSS.curie('Xlt'),
                   model_uri=DSS.xfmrcode__Xlt, domain=None, range=Optional[float])

slots.xfmrcode__Xscarray = Slot(uri=DSS.Xscarray, name="xfmrcode__Xscarray", curie=DSS.curie('Xscarray'),
                   model_uri=DSS.xfmrcode__Xscarray, domain=None, range=Optional[Union[float, list[float]]])

slots.xfmrcode__thermal = Slot(uri=DSS.thermal, name="xfmrcode__thermal", curie=DSS.curie('thermal'),
                   model_uri=DSS.xfmrcode__thermal, domain=None, range=Optional[str])

slots.xfmrcode__n = Slot(uri=DSS.n, name="xfmrcode__n", curie=DSS.curie('n'),
                   model_uri=DSS.xfmrcode__n, domain=None, range=Optional[str])

slots.xfmrcode__m = Slot(uri=DSS.m, name="xfmrcode__m", curie=DSS.curie('m'),
                   model_uri=DSS.xfmrcode__m, domain=None, range=Optional[str])

slots.xfmrcode__flrise = Slot(uri=DSS.flrise, name="xfmrcode__flrise", curie=DSS.curie('flrise'),
                   model_uri=DSS.xfmrcode__flrise, domain=None, range=Optional[str])

slots.xfmrcode__hsrise = Slot(uri=DSS.hsrise, name="xfmrcode__hsrise", curie=DSS.curie('hsrise'),
                   model_uri=DSS.xfmrcode__hsrise, domain=None, range=Optional[str])

slots.xfmrcode__pct_loadloss = Slot(uri=DSS.pct_loadloss, name="xfmrcode__pct_loadloss", curie=DSS.curie('pct_loadloss'),
                   model_uri=DSS.xfmrcode__pct_loadloss, domain=None, range=Optional[float])

slots.xfmrcode__pct_noloadloss = Slot(uri=DSS.pct_noloadloss, name="xfmrcode__pct_noloadloss", curie=DSS.curie('pct_noloadloss'),
                   model_uri=DSS.xfmrcode__pct_noloadloss, domain=None, range=Optional[float])

slots.xfmrcode__normhkVA = Slot(uri=DSS.normhkVA, name="xfmrcode__normhkVA", curie=DSS.curie('normhkVA'),
                   model_uri=DSS.xfmrcode__normhkVA, domain=None, range=Optional[float])

slots.xfmrcode__emerghkVA = Slot(uri=DSS.emerghkVA, name="xfmrcode__emerghkVA", curie=DSS.curie('emerghkVA'),
                   model_uri=DSS.xfmrcode__emerghkVA, domain=None, range=Optional[float])

slots.xfmrcode__MaxTap = Slot(uri=DSS.MaxTap, name="xfmrcode__MaxTap", curie=DSS.curie('MaxTap'),
                   model_uri=DSS.xfmrcode__MaxTap, domain=None, range=Optional[str])

slots.xfmrcode__MinTap = Slot(uri=DSS.MinTap, name="xfmrcode__MinTap", curie=DSS.curie('MinTap'),
                   model_uri=DSS.xfmrcode__MinTap, domain=None, range=Optional[str])

slots.xfmrcode__NumTaps = Slot(uri=DSS.NumTaps, name="xfmrcode__NumTaps", curie=DSS.curie('NumTaps'),
                   model_uri=DSS.xfmrcode__NumTaps, domain=None, range=Optional[int])

slots.xfmrcode__pct_imag = Slot(uri=DSS.pct_imag, name="xfmrcode__pct_imag", curie=DSS.curie('pct_imag'),
                   model_uri=DSS.xfmrcode__pct_imag, domain=None, range=Optional[float])

slots.xfmrcode__ppm_antifloat = Slot(uri=DSS.ppm_antifloat, name="xfmrcode__ppm_antifloat", curie=DSS.curie('ppm_antifloat'),
                   model_uri=DSS.xfmrcode__ppm_antifloat, domain=None, range=Optional[float])

slots.xfmrcode__pct_Rs = Slot(uri=DSS.pct_Rs, name="xfmrcode__pct_Rs", curie=DSS.curie('pct_Rs'),
                   model_uri=DSS.xfmrcode__pct_Rs, domain=None, range=Optional[Union[float, list[float]]])

slots.xfmrcode__X12 = Slot(uri=DSS.X12, name="xfmrcode__X12", curie=DSS.curie('X12'),
                   model_uri=DSS.xfmrcode__X12, domain=None, range=Optional[float])

slots.xfmrcode__X13 = Slot(uri=DSS.X13, name="xfmrcode__X13", curie=DSS.curie('X13'),
                   model_uri=DSS.xfmrcode__X13, domain=None, range=Optional[float])

slots.xfmrcode__X23 = Slot(uri=DSS.X23, name="xfmrcode__X23", curie=DSS.curie('X23'),
                   model_uri=DSS.xfmrcode__X23, domain=None, range=Optional[float])

slots.xfmrcode__RdcOhms = Slot(uri=DSS.RdcOhms, name="xfmrcode__RdcOhms", curie=DSS.curie('RdcOhms'),
                   model_uri=DSS.xfmrcode__RdcOhms, domain=None, range=Optional[Union[float, list[float]]])

slots.xfmrcode__Seasons = Slot(uri=DSS.Seasons, name="xfmrcode__Seasons", curie=DSS.curie('Seasons'),
                   model_uri=DSS.xfmrcode__Seasons, domain=None, range=Optional[int])

slots.xfmrcode__Ratings = Slot(uri=DSS.Ratings, name="xfmrcode__Ratings", curie=DSS.curie('Ratings'),
                   model_uri=DSS.xfmrcode__Ratings, domain=None, range=Optional[Union[float, list[float]]])

slots.xfmrcode__like = Slot(uri=DSS.like, name="xfmrcode__like", curie=DSS.curie('like'),
                   model_uri=DSS.xfmrcode__like, domain=None, range=Optional[str])

slots.xycurve__name = Slot(uri=DSS.name, name="xycurve__name", curie=DSS.curie('name'),
                   model_uri=DSS.xycurve__name, domain=None, range=URIRef)

slots.xycurve__npts = Slot(uri=DSS.npts, name="xycurve__npts", curie=DSS.curie('npts'),
                   model_uri=DSS.xycurve__npts, domain=None, range=Optional[int])

slots.xycurve__Points = Slot(uri=DSS.Points, name="xycurve__Points", curie=DSS.curie('Points'),
                   model_uri=DSS.xycurve__Points, domain=None, range=Optional[int])

slots.xycurve__Yarray = Slot(uri=DSS.Yarray, name="xycurve__Yarray", curie=DSS.curie('Yarray'),
                   model_uri=DSS.xycurve__Yarray, domain=None, range=Optional[int])

slots.xycurve__Xarray = Slot(uri=DSS.Xarray, name="xycurve__Xarray", curie=DSS.curie('Xarray'),
                   model_uri=DSS.xycurve__Xarray, domain=None, range=Optional[int])

slots.xycurve__csvfile = Slot(uri=DSS.csvfile, name="xycurve__csvfile", curie=DSS.curie('csvfile'),
                   model_uri=DSS.xycurve__csvfile, domain=None, range=Optional[int])

slots.xycurve__sngfile = Slot(uri=DSS.sngfile, name="xycurve__sngfile", curie=DSS.curie('sngfile'),
                   model_uri=DSS.xycurve__sngfile, domain=None, range=Optional[int])

slots.xycurve__dblfile = Slot(uri=DSS.dblfile, name="xycurve__dblfile", curie=DSS.curie('dblfile'),
                   model_uri=DSS.xycurve__dblfile, domain=None, range=Optional[int])

slots.xycurve__x = Slot(uri=DSS.x, name="xycurve__x", curie=DSS.curie('x'),
                   model_uri=DSS.xycurve__x, domain=None, range=Optional[float])

slots.xycurve__y = Slot(uri=DSS.y, name="xycurve__y", curie=DSS.curie('y'),
                   model_uri=DSS.xycurve__y, domain=None, range=Optional[float])

slots.xycurve__Xshift = Slot(uri=DSS.Xshift, name="xycurve__Xshift", curie=DSS.curie('Xshift'),
                   model_uri=DSS.xycurve__Xshift, domain=None, range=Optional[str])

slots.xycurve__Yshift = Slot(uri=DSS.Yshift, name="xycurve__Yshift", curie=DSS.curie('Yshift'),
                   model_uri=DSS.xycurve__Yshift, domain=None, range=Optional[str])

slots.xycurve__Xscale = Slot(uri=DSS.Xscale, name="xycurve__Xscale", curie=DSS.curie('Xscale'),
                   model_uri=DSS.xycurve__Xscale, domain=None, range=Optional[str])

slots.xycurve__Yscale = Slot(uri=DSS.Yscale, name="xycurve__Yscale", curie=DSS.curie('Yscale'),
                   model_uri=DSS.xycurve__Yscale, domain=None, range=Optional[str])

slots.xycurve__like = Slot(uri=DSS.like, name="xycurve__like", curie=DSS.curie('like'),
                   model_uri=DSS.xycurve__like, domain=None, range=Optional[str])

slots.energymeter__name = Slot(uri=DSS.name, name="energymeter__name", curie=DSS.curie('name'),
                   model_uri=DSS.energymeter__name, domain=None, range=URIRef)

slots.energymeter__element = Slot(uri=DSS.element, name="energymeter__element", curie=DSS.curie('element'),
                   model_uri=DSS.energymeter__element, domain=None, range=Optional[str])

slots.energymeter__terminal = Slot(uri=DSS.terminal, name="energymeter__terminal", curie=DSS.curie('terminal'),
                   model_uri=DSS.energymeter__terminal, domain=None, range=Optional[int])

slots.energymeter__action = Slot(uri=DSS.action, name="energymeter__action", curie=DSS.curie('action'),
                   model_uri=DSS.energymeter__action, domain=None, range=Optional[float])

slots.energymeter__option = Slot(uri=DSS.option, name="energymeter__option", curie=DSS.curie('option'),
                   model_uri=DSS.energymeter__option, domain=None, range=Optional[Union[str, list[str]]])

slots.energymeter__kVAnormal = Slot(uri=DSS.kVAnormal, name="energymeter__kVAnormal", curie=DSS.curie('kVAnormal'),
                   model_uri=DSS.energymeter__kVAnormal, domain=None, range=Optional[float])

slots.energymeter__kVAemerg = Slot(uri=DSS.kVAemerg, name="energymeter__kVAemerg", curie=DSS.curie('kVAemerg'),
                   model_uri=DSS.energymeter__kVAemerg, domain=None, range=Optional[float])

slots.energymeter__peakcurrent = Slot(uri=DSS.peakcurrent, name="energymeter__peakcurrent", curie=DSS.curie('peakcurrent'),
                   model_uri=DSS.energymeter__peakcurrent, domain=None, range=Optional[Union[float, list[float]]])

slots.energymeter__Zonelist = Slot(uri=DSS.Zonelist, name="energymeter__Zonelist", curie=DSS.curie('Zonelist'),
                   model_uri=DSS.energymeter__Zonelist, domain=None, range=Optional[Union[str, list[str]]])

slots.energymeter__LocalOnly = Slot(uri=DSS.LocalOnly, name="energymeter__LocalOnly", curie=DSS.curie('LocalOnly'),
                   model_uri=DSS.energymeter__LocalOnly, domain=None, range=Optional[Union[bool, Bool]])

slots.energymeter__Mask = Slot(uri=DSS.Mask, name="energymeter__Mask", curie=DSS.curie('Mask'),
                   model_uri=DSS.energymeter__Mask, domain=None, range=Optional[str])

slots.energymeter__Losses = Slot(uri=DSS.Losses, name="energymeter__Losses", curie=DSS.curie('Losses'),
                   model_uri=DSS.energymeter__Losses, domain=None, range=Optional[Union[bool, Bool]])

slots.energymeter__LineLosses = Slot(uri=DSS.LineLosses, name="energymeter__LineLosses", curie=DSS.curie('LineLosses'),
                   model_uri=DSS.energymeter__LineLosses, domain=None, range=Optional[Union[bool, Bool]])

slots.energymeter__XfmrLosses = Slot(uri=DSS.XfmrLosses, name="energymeter__XfmrLosses", curie=DSS.curie('XfmrLosses'),
                   model_uri=DSS.energymeter__XfmrLosses, domain=None, range=Optional[Union[bool, Bool]])

slots.energymeter__SeqLosses = Slot(uri=DSS.SeqLosses, name="energymeter__SeqLosses", curie=DSS.curie('SeqLosses'),
                   model_uri=DSS.energymeter__SeqLosses, domain=None, range=Optional[Union[bool, Bool]])

slots.energymeter__three_phase_losses = Slot(uri=DSS.three_phase_losses, name="energymeter__three_phase_losses", curie=DSS.curie('three_phase_losses'),
                   model_uri=DSS.energymeter__three_phase_losses, domain=None, range=Optional[Union[bool, Bool]])

slots.energymeter__VbaseLosses = Slot(uri=DSS.VbaseLosses, name="energymeter__VbaseLosses", curie=DSS.curie('VbaseLosses'),
                   model_uri=DSS.energymeter__VbaseLosses, domain=None, range=Optional[Union[bool, Bool]])

slots.energymeter__PhaseVoltageReport = Slot(uri=DSS.PhaseVoltageReport, name="energymeter__PhaseVoltageReport", curie=DSS.curie('PhaseVoltageReport'),
                   model_uri=DSS.energymeter__PhaseVoltageReport, domain=None, range=Optional[Union[bool, Bool]])

slots.energymeter__Int_Rate = Slot(uri=DSS.Int_Rate, name="energymeter__Int_Rate", curie=DSS.curie('Int_Rate'),
                   model_uri=DSS.energymeter__Int_Rate, domain=None, range=Optional[int])

slots.energymeter__Int_Duration = Slot(uri=DSS.Int_Duration, name="energymeter__Int_Duration", curie=DSS.curie('Int_Duration'),
                   model_uri=DSS.energymeter__Int_Duration, domain=None, range=Optional[str])

slots.energymeter__SAIFI = Slot(uri=DSS.SAIFI, name="energymeter__SAIFI", curie=DSS.curie('SAIFI'),
                   model_uri=DSS.energymeter__SAIFI, domain=None, range=Optional[str])

slots.energymeter__SAIFIkW = Slot(uri=DSS.SAIFIkW, name="energymeter__SAIFIkW", curie=DSS.curie('SAIFIkW'),
                   model_uri=DSS.energymeter__SAIFIkW, domain=None, range=Optional[float])

slots.energymeter__SAIDI = Slot(uri=DSS.SAIDI, name="energymeter__SAIDI", curie=DSS.curie('SAIDI'),
                   model_uri=DSS.energymeter__SAIDI, domain=None, range=Optional[str])

slots.energymeter__CAIDI = Slot(uri=DSS.CAIDI, name="energymeter__CAIDI", curie=DSS.curie('CAIDI'),
                   model_uri=DSS.energymeter__CAIDI, domain=None, range=Optional[str])

slots.energymeter__CustInterrupts = Slot(uri=DSS.CustInterrupts, name="energymeter__CustInterrupts", curie=DSS.curie('CustInterrupts'),
                   model_uri=DSS.energymeter__CustInterrupts, domain=None, range=Optional[str])

slots.energymeter__basefreq = Slot(uri=DSS.basefreq, name="energymeter__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.energymeter__basefreq, domain=None, range=Optional[float])

slots.energymeter__enabled = Slot(uri=DSS.enabled, name="energymeter__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.energymeter__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.energymeter__like = Slot(uri=DSS.like, name="energymeter__like", curie=DSS.curie('like'),
                   model_uri=DSS.energymeter__like, domain=None, range=Optional[str])

slots.fmonitor__name = Slot(uri=DSS.name, name="fmonitor__name", curie=DSS.curie('name'),
                   model_uri=DSS.fmonitor__name, domain=None, range=URIRef)

slots.fmonitor__element = Slot(uri=DSS.element, name="fmonitor__element", curie=DSS.curie('element'),
                   model_uri=DSS.fmonitor__element, domain=None, range=Optional[str])

slots.fmonitor__terminal = Slot(uri=DSS.terminal, name="fmonitor__terminal", curie=DSS.curie('terminal'),
                   model_uri=DSS.fmonitor__terminal, domain=None, range=Optional[int])

slots.fmonitor__mode = Slot(uri=DSS.mode, name="fmonitor__mode", curie=DSS.curie('mode'),
                   model_uri=DSS.fmonitor__mode, domain=None, range=Optional[int])

slots.fmonitor__action = Slot(uri=DSS.action, name="fmonitor__action", curie=DSS.curie('action'),
                   model_uri=DSS.fmonitor__action, domain=None, range=Optional[float])

slots.fmonitor__residual = Slot(uri=DSS.residual, name="fmonitor__residual", curie=DSS.curie('residual'),
                   model_uri=DSS.fmonitor__residual, domain=None, range=Optional[Union[bool, Bool]])

slots.fmonitor__VIPolar = Slot(uri=DSS.VIPolar, name="fmonitor__VIPolar", curie=DSS.curie('VIPolar'),
                   model_uri=DSS.fmonitor__VIPolar, domain=None, range=Optional[Union[bool, Bool]])

slots.fmonitor__PPolar = Slot(uri=DSS.PPolar, name="fmonitor__PPolar", curie=DSS.curie('PPolar'),
                   model_uri=DSS.fmonitor__PPolar, domain=None, range=Optional[Union[bool, Bool]])

slots.fmonitor__P_trans_ref = Slot(uri=DSS.P_trans_ref, name="fmonitor__P_trans_ref", curie=DSS.curie('P_trans_ref'),
                   model_uri=DSS.fmonitor__P_trans_ref, domain=None, range=Optional[float])

slots.fmonitor__V_Sensor = Slot(uri=DSS.V_Sensor, name="fmonitor__V_Sensor", curie=DSS.curie('V_Sensor'),
                   model_uri=DSS.fmonitor__V_Sensor, domain=None, range=Optional[float])

slots.fmonitor__P_Sensor = Slot(uri=DSS.P_Sensor, name="fmonitor__P_Sensor", curie=DSS.curie('P_Sensor'),
                   model_uri=DSS.fmonitor__P_Sensor, domain=None, range=Optional[float])

slots.fmonitor__Node_num = Slot(uri=DSS.Node_num, name="fmonitor__Node_num", curie=DSS.curie('Node_num'),
                   model_uri=DSS.fmonitor__Node_num, domain=None, range=Optional[str])

slots.fmonitor__Cluster_num = Slot(uri=DSS.Cluster_num, name="fmonitor__Cluster_num", curie=DSS.curie('Cluster_num'),
                   model_uri=DSS.fmonitor__Cluster_num, domain=None, range=Optional[str])

slots.fmonitor__Total_Clusters = Slot(uri=DSS.Total_Clusters, name="fmonitor__Total_Clusters", curie=DSS.curie('Total_Clusters'),
                   model_uri=DSS.fmonitor__Total_Clusters, domain=None, range=Optional[int])

slots.fmonitor__Nodes = Slot(uri=DSS.Nodes, name="fmonitor__Nodes", curie=DSS.curie('Nodes'),
                   model_uri=DSS.fmonitor__Nodes, domain=None, range=Optional[str])

slots.fmonitor__CommVector = Slot(uri=DSS.CommVector, name="fmonitor__CommVector", curie=DSS.curie('CommVector'),
                   model_uri=DSS.fmonitor__CommVector, domain=None, range=Optional[int])

slots.fmonitor__ElemTableLine = Slot(uri=DSS.ElemTableLine, name="fmonitor__ElemTableLine", curie=DSS.curie('ElemTableLine'),
                   model_uri=DSS.fmonitor__ElemTableLine, domain=None, range=Optional[int])

slots.fmonitor__P_Mode = Slot(uri=DSS.P_Mode, name="fmonitor__P_Mode", curie=DSS.curie('P_Mode'),
                   model_uri=DSS.fmonitor__P_Mode, domain=None, range=Optional[float])

slots.fmonitor__CommDelayVector = Slot(uri=DSS.CommDelayVector, name="fmonitor__CommDelayVector", curie=DSS.curie('CommDelayVector'),
                   model_uri=DSS.fmonitor__CommDelayVector, domain=None, range=Optional[int])

slots.fmonitor__T_intvl_smpl = Slot(uri=DSS.T_intvl_smpl, name="fmonitor__T_intvl_smpl", curie=DSS.curie('T_intvl_smpl'),
                   model_uri=DSS.fmonitor__T_intvl_smpl, domain=None, range=Optional[str])

slots.fmonitor__MaxLocalMem = Slot(uri=DSS.MaxLocalMem, name="fmonitor__MaxLocalMem", curie=DSS.curie('MaxLocalMem'),
                   model_uri=DSS.fmonitor__MaxLocalMem, domain=None, range=Optional[int])

slots.fmonitor__Volt_limits_pu = Slot(uri=DSS.Volt_limits_pu, name="fmonitor__Volt_limits_pu", curie=DSS.curie('Volt_limits_pu'),
                   model_uri=DSS.fmonitor__Volt_limits_pu, domain=None, range=Optional[float])

slots.fmonitor__b_Curt_Ctrl = Slot(uri=DSS.b_Curt_Ctrl, name="fmonitor__b_Curt_Ctrl", curie=DSS.curie('b_Curt_Ctrl'),
                   model_uri=DSS.fmonitor__b_Curt_Ctrl, domain=None, range=Optional[float])

slots.fmonitor__up_dly = Slot(uri=DSS.up_dly, name="fmonitor__up_dly", curie=DSS.curie('up_dly'),
                   model_uri=DSS.fmonitor__up_dly, domain=None, range=Optional[str])

slots.fmonitor__virtual_ld_node = Slot(uri=DSS.virtual_ld_node, name="fmonitor__virtual_ld_node", curie=DSS.curie('virtual_ld_node'),
                   model_uri=DSS.fmonitor__virtual_ld_node, domain=None, range=Optional[str])

slots.fmonitor__EGen = Slot(uri=DSS.EGen, name="fmonitor__EGen", curie=DSS.curie('EGen'),
                   model_uri=DSS.fmonitor__EGen, domain=None, range=Optional[float])

slots.fmonitor__attack_defense = Slot(uri=DSS.attack_defense, name="fmonitor__attack_defense", curie=DSS.curie('attack_defense'),
                   model_uri=DSS.fmonitor__attack_defense, domain=None, range=Optional[str])

slots.fmonitor__Comm_hide = Slot(uri=DSS.Comm_hide, name="fmonitor__Comm_hide", curie=DSS.curie('Comm_hide'),
                   model_uri=DSS.fmonitor__Comm_hide, domain=None, range=Optional[str])

slots.fmonitor__Comm_node_hide = Slot(uri=DSS.Comm_node_hide, name="fmonitor__Comm_node_hide", curie=DSS.curie('Comm_node_hide'),
                   model_uri=DSS.fmonitor__Comm_node_hide, domain=None, range=Optional[str])

slots.fmonitor__basefreq = Slot(uri=DSS.basefreq, name="fmonitor__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.fmonitor__basefreq, domain=None, range=Optional[float])

slots.fmonitor__enabled = Slot(uri=DSS.enabled, name="fmonitor__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.fmonitor__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.fmonitor__like = Slot(uri=DSS.like, name="fmonitor__like", curie=DSS.curie('like'),
                   model_uri=DSS.fmonitor__like, domain=None, range=Optional[str])

slots.monitor__name = Slot(uri=DSS.name, name="monitor__name", curie=DSS.curie('name'),
                   model_uri=DSS.monitor__name, domain=None, range=URIRef)

slots.monitor__element = Slot(uri=DSS.element, name="monitor__element", curie=DSS.curie('element'),
                   model_uri=DSS.monitor__element, domain=None, range=Optional[str])

slots.monitor__terminal = Slot(uri=DSS.terminal, name="monitor__terminal", curie=DSS.curie('terminal'),
                   model_uri=DSS.monitor__terminal, domain=None, range=Optional[int])

slots.monitor__mode = Slot(uri=DSS.mode, name="monitor__mode", curie=DSS.curie('mode'),
                   model_uri=DSS.monitor__mode, domain=None, range=Optional[int])

slots.monitor__action = Slot(uri=DSS.action, name="monitor__action", curie=DSS.curie('action'),
                   model_uri=DSS.monitor__action, domain=None, range=Optional[float])

slots.monitor__residual = Slot(uri=DSS.residual, name="monitor__residual", curie=DSS.curie('residual'),
                   model_uri=DSS.monitor__residual, domain=None, range=Optional[Union[bool, Bool]])

slots.monitor__VIPolar = Slot(uri=DSS.VIPolar, name="monitor__VIPolar", curie=DSS.curie('VIPolar'),
                   model_uri=DSS.monitor__VIPolar, domain=None, range=Optional[Union[bool, Bool]])

slots.monitor__PPolar = Slot(uri=DSS.PPolar, name="monitor__PPolar", curie=DSS.curie('PPolar'),
                   model_uri=DSS.monitor__PPolar, domain=None, range=Optional[Union[bool, Bool]])

slots.monitor__basefreq = Slot(uri=DSS.basefreq, name="monitor__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.monitor__basefreq, domain=None, range=Optional[float])

slots.monitor__enabled = Slot(uri=DSS.enabled, name="monitor__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.monitor__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.monitor__like = Slot(uri=DSS.like, name="monitor__like", curie=DSS.curie('like'),
                   model_uri=DSS.monitor__like, domain=None, range=Optional[str])

slots.sensor__name = Slot(uri=DSS.name, name="sensor__name", curie=DSS.curie('name'),
                   model_uri=DSS.sensor__name, domain=None, range=URIRef)

slots.sensor__element = Slot(uri=DSS.element, name="sensor__element", curie=DSS.curie('element'),
                   model_uri=DSS.sensor__element, domain=None, range=Optional[str])

slots.sensor__terminal = Slot(uri=DSS.terminal, name="sensor__terminal", curie=DSS.curie('terminal'),
                   model_uri=DSS.sensor__terminal, domain=None, range=Optional[int])

slots.sensor__kvbase = Slot(uri=DSS.kvbase, name="sensor__kvbase", curie=DSS.curie('kvbase'),
                   model_uri=DSS.sensor__kvbase, domain=None, range=Optional[float])

slots.sensor__clear = Slot(uri=DSS.clear, name="sensor__clear", curie=DSS.curie('clear'),
                   model_uri=DSS.sensor__clear, domain=None, range=Optional[Union[bool, Bool]])

slots.sensor__kVs = Slot(uri=DSS.kVs, name="sensor__kVs", curie=DSS.curie('kVs'),
                   model_uri=DSS.sensor__kVs, domain=None, range=Optional[Union[float, list[float]]])

slots.sensor__currents = Slot(uri=DSS.currents, name="sensor__currents", curie=DSS.curie('currents'),
                   model_uri=DSS.sensor__currents, domain=None, range=Optional[Union[float, list[float]]])

slots.sensor__kWs = Slot(uri=DSS.kWs, name="sensor__kWs", curie=DSS.curie('kWs'),
                   model_uri=DSS.sensor__kWs, domain=None, range=Optional[Union[float, list[float]]])

slots.sensor__kvars = Slot(uri=DSS.kvars, name="sensor__kvars", curie=DSS.curie('kvars'),
                   model_uri=DSS.sensor__kvars, domain=None, range=Optional[Union[float, list[float]]])

slots.sensor__conn = Slot(uri=DSS.conn, name="sensor__conn", curie=DSS.curie('conn'),
                   model_uri=DSS.sensor__conn, domain=None, range=Optional[float])

slots.sensor__Deltadirection = Slot(uri=DSS.Deltadirection, name="sensor__Deltadirection", curie=DSS.curie('Deltadirection'),
                   model_uri=DSS.sensor__Deltadirection, domain=None, range=Optional[str])

slots.sensor__pct_Error = Slot(uri=DSS.pct_Error, name="sensor__pct_Error", curie=DSS.curie('pct_Error'),
                   model_uri=DSS.sensor__pct_Error, domain=None, range=Optional[float])

slots.sensor__Weight = Slot(uri=DSS.Weight, name="sensor__Weight", curie=DSS.curie('Weight'),
                   model_uri=DSS.sensor__Weight, domain=None, range=Optional[str])

slots.sensor__action = Slot(uri=DSS.action, name="sensor__action", curie=DSS.curie('action'),
                   model_uri=DSS.sensor__action, domain=None, range=Optional[str])

slots.sensor__basefreq = Slot(uri=DSS.basefreq, name="sensor__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.sensor__basefreq, domain=None, range=Optional[float])

slots.sensor__enabled = Slot(uri=DSS.enabled, name="sensor__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.sensor__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.sensor__like = Slot(uri=DSS.like, name="sensor__like", curie=DSS.curie('like'),
                   model_uri=DSS.sensor__like, domain=None, range=Optional[str])

slots.fault__name = Slot(uri=DSS.name, name="fault__name", curie=DSS.curie('name'),
                   model_uri=DSS.fault__name, domain=None, range=URIRef)

slots.fault__bus1 = Slot(uri=DSS.bus1, name="fault__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.fault__bus1, domain=None, range=Optional[str])

slots.fault__bus2 = Slot(uri=DSS.bus2, name="fault__bus2", curie=DSS.curie('bus2'),
                   model_uri=DSS.fault__bus2, domain=None, range=Optional[str])

slots.fault__phases = Slot(uri=DSS.phases, name="fault__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.fault__phases, domain=None, range=Optional[int])

slots.fault__r = Slot(uri=DSS.r, name="fault__r", curie=DSS.curie('r'),
                   model_uri=DSS.fault__r, domain=None, range=Optional[float])

slots.fault__pct_stddev = Slot(uri=DSS.pct_stddev, name="fault__pct_stddev", curie=DSS.curie('pct_stddev'),
                   model_uri=DSS.fault__pct_stddev, domain=None, range=Optional[float])

slots.fault__Gmatrix = Slot(uri=DSS.Gmatrix, name="fault__Gmatrix", curie=DSS.curie('Gmatrix'),
                   model_uri=DSS.fault__Gmatrix, domain=None, range=Optional[float])

slots.fault__ONtime = Slot(uri=DSS.ONtime, name="fault__ONtime", curie=DSS.curie('ONtime'),
                   model_uri=DSS.fault__ONtime, domain=None, range=Optional[str])

slots.fault__temporary = Slot(uri=DSS.temporary, name="fault__temporary", curie=DSS.curie('temporary'),
                   model_uri=DSS.fault__temporary, domain=None, range=Optional[Union[bool, Bool]])

slots.fault__MinAmps = Slot(uri=DSS.MinAmps, name="fault__MinAmps", curie=DSS.curie('MinAmps'),
                   model_uri=DSS.fault__MinAmps, domain=None, range=Optional[str])

slots.fault__normamps = Slot(uri=DSS.normamps, name="fault__normamps", curie=DSS.curie('normamps'),
                   model_uri=DSS.fault__normamps, domain=None, range=Optional[float])

slots.fault__emergamps = Slot(uri=DSS.emergamps, name="fault__emergamps", curie=DSS.curie('emergamps'),
                   model_uri=DSS.fault__emergamps, domain=None, range=Optional[float])

slots.fault__faultrate = Slot(uri=DSS.faultrate, name="fault__faultrate", curie=DSS.curie('faultrate'),
                   model_uri=DSS.fault__faultrate, domain=None, range=Optional[str])

slots.fault__pctperm = Slot(uri=DSS.pctperm, name="fault__pctperm", curie=DSS.curie('pctperm'),
                   model_uri=DSS.fault__pctperm, domain=None, range=Optional[float])

slots.fault__repair = Slot(uri=DSS.repair, name="fault__repair", curie=DSS.curie('repair'),
                   model_uri=DSS.fault__repair, domain=None, range=Optional[str])

slots.fault__basefreq = Slot(uri=DSS.basefreq, name="fault__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.fault__basefreq, domain=None, range=Optional[float])

slots.fault__enabled = Slot(uri=DSS.enabled, name="fault__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.fault__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.fault__like = Slot(uri=DSS.like, name="fault__like", curie=DSS.curie('like'),
                   model_uri=DSS.fault__like, domain=None, range=Optional[str])

slots.gicsource__name = Slot(uri=DSS.name, name="gicsource__name", curie=DSS.curie('name'),
                   model_uri=DSS.gicsource__name, domain=None, range=URIRef)

slots.gicsource__Volts = Slot(uri=DSS.Volts, name="gicsource__Volts", curie=DSS.curie('Volts'),
                   model_uri=DSS.gicsource__Volts, domain=None, range=Optional[float])

slots.gicsource__angle = Slot(uri=DSS.angle, name="gicsource__angle", curie=DSS.curie('angle'),
                   model_uri=DSS.gicsource__angle, domain=None, range=Optional[float])

slots.gicsource__frequency = Slot(uri=DSS.frequency, name="gicsource__frequency", curie=DSS.curie('frequency'),
                   model_uri=DSS.gicsource__frequency, domain=None, range=Optional[float])

slots.gicsource__phases = Slot(uri=DSS.phases, name="gicsource__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.gicsource__phases, domain=None, range=Optional[int])

slots.gicsource__EN = Slot(uri=DSS.EN, name="gicsource__EN", curie=DSS.curie('EN'),
                   model_uri=DSS.gicsource__EN, domain=None, range=Optional[float])

slots.gicsource__EE = Slot(uri=DSS.EE, name="gicsource__EE", curie=DSS.curie('EE'),
                   model_uri=DSS.gicsource__EE, domain=None, range=Optional[float])

slots.gicsource__Lat1 = Slot(uri=DSS.Lat1, name="gicsource__Lat1", curie=DSS.curie('Lat1'),
                   model_uri=DSS.gicsource__Lat1, domain=None, range=Optional[str])

slots.gicsource__Lon1 = Slot(uri=DSS.Lon1, name="gicsource__Lon1", curie=DSS.curie('Lon1'),
                   model_uri=DSS.gicsource__Lon1, domain=None, range=Optional[str])

slots.gicsource__Lat2 = Slot(uri=DSS.Lat2, name="gicsource__Lat2", curie=DSS.curie('Lat2'),
                   model_uri=DSS.gicsource__Lat2, domain=None, range=Optional[str])

slots.gicsource__Lon2 = Slot(uri=DSS.Lon2, name="gicsource__Lon2", curie=DSS.curie('Lon2'),
                   model_uri=DSS.gicsource__Lon2, domain=None, range=Optional[str])

slots.gicsource__spectrum = Slot(uri=DSS.spectrum, name="gicsource__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.gicsource__spectrum, domain=None, range=Optional[str])

slots.gicsource__basefreq = Slot(uri=DSS.basefreq, name="gicsource__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.gicsource__basefreq, domain=None, range=Optional[str])

slots.gicsource__enabled = Slot(uri=DSS.enabled, name="gicsource__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.gicsource__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.gicsource__like = Slot(uri=DSS.like, name="gicsource__like", curie=DSS.curie('like'),
                   model_uri=DSS.gicsource__like, domain=None, range=Optional[str])

slots.isource__name = Slot(uri=DSS.name, name="isource__name", curie=DSS.curie('name'),
                   model_uri=DSS.isource__name, domain=None, range=URIRef)

slots.isource__bus1 = Slot(uri=DSS.bus1, name="isource__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.isource__bus1, domain=None, range=Optional[str])

slots.isource__amps = Slot(uri=DSS.amps, name="isource__amps", curie=DSS.curie('amps'),
                   model_uri=DSS.isource__amps, domain=None, range=Optional[float])

slots.isource__angle = Slot(uri=DSS.angle, name="isource__angle", curie=DSS.curie('angle'),
                   model_uri=DSS.isource__angle, domain=None, range=Optional[int])

slots.isource__frequency = Slot(uri=DSS.frequency, name="isource__frequency", curie=DSS.curie('frequency'),
                   model_uri=DSS.isource__frequency, domain=None, range=Optional[str])

slots.isource__phases = Slot(uri=DSS.phases, name="isource__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.isource__phases, domain=None, range=Optional[int])

slots.isource__scantype = Slot(uri=DSS.scantype, name="isource__scantype", curie=DSS.curie('scantype'),
                   model_uri=DSS.isource__scantype, domain=None, range=Optional[float])

slots.isource__sequence = Slot(uri=DSS.sequence, name="isource__sequence", curie=DSS.curie('sequence'),
                   model_uri=DSS.isource__sequence, domain=None, range=Optional[float])

slots.isource__Yearly = Slot(uri=DSS.Yearly, name="isource__Yearly", curie=DSS.curie('Yearly'),
                   model_uri=DSS.isource__Yearly, domain=None, range=Optional[float])

slots.isource__Daily = Slot(uri=DSS.Daily, name="isource__Daily", curie=DSS.curie('Daily'),
                   model_uri=DSS.isource__Daily, domain=None, range=Optional[float])

slots.isource__Duty = Slot(uri=DSS.Duty, name="isource__Duty", curie=DSS.curie('Duty'),
                   model_uri=DSS.isource__Duty, domain=None, range=Optional[float])

slots.isource__Bus2 = Slot(uri=DSS.Bus2, name="isource__Bus2", curie=DSS.curie('Bus2'),
                   model_uri=DSS.isource__Bus2, domain=None, range=Optional[str])

slots.isource__spectrum = Slot(uri=DSS.spectrum, name="isource__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.isource__spectrum, domain=None, range=Optional[str])

slots.isource__basefreq = Slot(uri=DSS.basefreq, name="isource__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.isource__basefreq, domain=None, range=Optional[float])

slots.isource__enabled = Slot(uri=DSS.enabled, name="isource__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.isource__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.isource__like = Slot(uri=DSS.like, name="isource__like", curie=DSS.curie('like'),
                   model_uri=DSS.isource__like, domain=None, range=Optional[str])

slots.options__name = Slot(uri=DSS.name, name="options__name", curie=DSS.curie('name'),
                   model_uri=DSS.options__name, domain=None, range=URIRef)

slots.options__circuit = Slot(uri=DSS.circuit, name="options__circuit", curie=DSS.curie('circuit'),
                   model_uri=DSS.options__circuit, domain=None, range=Optional[str])

slots.options__open_terminals = Slot(uri=DSS.open_terminals, name="options__open_terminals", curie=DSS.curie('open_terminals'),
                   model_uri=DSS.options__open_terminals, domain=None, range=Optional[Union[str, list[str]]])

slots.options__voltagebases = Slot(uri=DSS.voltagebases, name="options__voltagebases", curie=DSS.curie('voltagebases'),
                   model_uri=DSS.options__voltagebases, domain=None, range=Optional[Union[float, list[float]]])

slots.options__defaultbasefreq = Slot(uri=DSS.defaultbasefreq, name="options__defaultbasefreq", curie=DSS.curie('defaultbasefreq'),
                   model_uri=DSS.options__defaultbasefreq, domain=None, range=Optional[float])

slots.options__earthmodel = Slot(uri=DSS.earthmodel, name="options__earthmodel", curie=DSS.curie('earthmodel'),
                   model_uri=DSS.options__earthmodel, domain=None, range=Optional[Union[str, "EarthModelType"]])

slots.vsource__name = Slot(uri=DSS.name, name="vsource__name", curie=DSS.curie('name'),
                   model_uri=DSS.vsource__name, domain=None, range=URIRef)

slots.vsource__bus1 = Slot(uri=DSS.bus1, name="vsource__bus1", curie=DSS.curie('bus1'),
                   model_uri=DSS.vsource__bus1, domain=None, range=Optional[str])

slots.vsource__basekv = Slot(uri=DSS.basekv, name="vsource__basekv", curie=DSS.curie('basekv'),
                   model_uri=DSS.vsource__basekv, domain=None, range=Optional[float])

slots.vsource__pu = Slot(uri=DSS.pu, name="vsource__pu", curie=DSS.curie('pu'),
                   model_uri=DSS.vsource__pu, domain=None, range=Optional[float])

slots.vsource__angle = Slot(uri=DSS.angle, name="vsource__angle", curie=DSS.curie('angle'),
                   model_uri=DSS.vsource__angle, domain=None, range=Optional[float])

slots.vsource__frequency = Slot(uri=DSS.frequency, name="vsource__frequency", curie=DSS.curie('frequency'),
                   model_uri=DSS.vsource__frequency, domain=None, range=Optional[float])

slots.vsource__phases = Slot(uri=DSS.phases, name="vsource__phases", curie=DSS.curie('phases'),
                   model_uri=DSS.vsource__phases, domain=None, range=Optional[int])

slots.vsource__MVAsc3 = Slot(uri=DSS.MVAsc3, name="vsource__MVAsc3", curie=DSS.curie('MVAsc3'),
                   model_uri=DSS.vsource__MVAsc3, domain=None, range=Optional[float])

slots.vsource__MVAsc1 = Slot(uri=DSS.MVAsc1, name="vsource__MVAsc1", curie=DSS.curie('MVAsc1'),
                   model_uri=DSS.vsource__MVAsc1, domain=None, range=Optional[float])

slots.vsource__x1r1 = Slot(uri=DSS.x1r1, name="vsource__x1r1", curie=DSS.curie('x1r1'),
                   model_uri=DSS.vsource__x1r1, domain=None, range=Optional[float])

slots.vsource__x0r0 = Slot(uri=DSS.x0r0, name="vsource__x0r0", curie=DSS.curie('x0r0'),
                   model_uri=DSS.vsource__x0r0, domain=None, range=Optional[float])

slots.vsource__Isc3 = Slot(uri=DSS.Isc3, name="vsource__Isc3", curie=DSS.curie('Isc3'),
                   model_uri=DSS.vsource__Isc3, domain=None, range=Optional[float])

slots.vsource__Isc1 = Slot(uri=DSS.Isc1, name="vsource__Isc1", curie=DSS.curie('Isc1'),
                   model_uri=DSS.vsource__Isc1, domain=None, range=Optional[float])

slots.vsource__R1 = Slot(uri=DSS.R1, name="vsource__R1", curie=DSS.curie('R1'),
                   model_uri=DSS.vsource__R1, domain=None, range=Optional[float])

slots.vsource__X1 = Slot(uri=DSS.X1, name="vsource__X1", curie=DSS.curie('X1'),
                   model_uri=DSS.vsource__X1, domain=None, range=Optional[float])

slots.vsource__R0 = Slot(uri=DSS.R0, name="vsource__R0", curie=DSS.curie('R0'),
                   model_uri=DSS.vsource__R0, domain=None, range=Optional[float])

slots.vsource__X0 = Slot(uri=DSS.X0, name="vsource__X0", curie=DSS.curie('X0'),
                   model_uri=DSS.vsource__X0, domain=None, range=Optional[float])

slots.vsource__ScanType = Slot(uri=DSS.ScanType, name="vsource__ScanType", curie=DSS.curie('ScanType'),
                   model_uri=DSS.vsource__ScanType, domain=None, range=Optional[str])

slots.vsource__Sequence = Slot(uri=DSS.Sequence, name="vsource__Sequence", curie=DSS.curie('Sequence'),
                   model_uri=DSS.vsource__Sequence, domain=None, range=Optional[str])

slots.vsource__bus2 = Slot(uri=DSS.bus2, name="vsource__bus2", curie=DSS.curie('bus2'),
                   model_uri=DSS.vsource__bus2, domain=None, range=Optional[str])

slots.vsource__Z1 = Slot(uri=DSS.Z1, name="vsource__Z1", curie=DSS.curie('Z1'),
                   model_uri=DSS.vsource__Z1, domain=None, range=Optional[Union[float, list[float]]])

slots.vsource__Z0 = Slot(uri=DSS.Z0, name="vsource__Z0", curie=DSS.curie('Z0'),
                   model_uri=DSS.vsource__Z0, domain=None, range=Optional[Union[float, list[float]]])

slots.vsource__Z2 = Slot(uri=DSS.Z2, name="vsource__Z2", curie=DSS.curie('Z2'),
                   model_uri=DSS.vsource__Z2, domain=None, range=Optional[Union[float, list[float]]])

slots.vsource__puZ1 = Slot(uri=DSS.puZ1, name="vsource__puZ1", curie=DSS.curie('puZ1'),
                   model_uri=DSS.vsource__puZ1, domain=None, range=Optional[Union[float, list[float]]])

slots.vsource__puZ0 = Slot(uri=DSS.puZ0, name="vsource__puZ0", curie=DSS.curie('puZ0'),
                   model_uri=DSS.vsource__puZ0, domain=None, range=Optional[Union[float, list[float]]])

slots.vsource__puZ2 = Slot(uri=DSS.puZ2, name="vsource__puZ2", curie=DSS.curie('puZ2'),
                   model_uri=DSS.vsource__puZ2, domain=None, range=Optional[Union[float, list[float]]])

slots.vsource__baseMVA = Slot(uri=DSS.baseMVA, name="vsource__baseMVA", curie=DSS.curie('baseMVA'),
                   model_uri=DSS.vsource__baseMVA, domain=None, range=Optional[float])

slots.vsource__Yearly = Slot(uri=DSS.Yearly, name="vsource__Yearly", curie=DSS.curie('Yearly'),
                   model_uri=DSS.vsource__Yearly, domain=None, range=Optional[str])

slots.vsource__Daily = Slot(uri=DSS.Daily, name="vsource__Daily", curie=DSS.curie('Daily'),
                   model_uri=DSS.vsource__Daily, domain=None, range=Optional[str])

slots.vsource__Duty = Slot(uri=DSS.Duty, name="vsource__Duty", curie=DSS.curie('Duty'),
                   model_uri=DSS.vsource__Duty, domain=None, range=Optional[str])

slots.vsource__Model = Slot(uri=DSS.Model, name="vsource__Model", curie=DSS.curie('Model'),
                   model_uri=DSS.vsource__Model, domain=None, range=Optional[str])

slots.vsource__puZideal = Slot(uri=DSS.puZideal, name="vsource__puZideal", curie=DSS.curie('puZideal'),
                   model_uri=DSS.vsource__puZideal, domain=None, range=Optional[float])

slots.vsource__spectrum = Slot(uri=DSS.spectrum, name="vsource__spectrum", curie=DSS.curie('spectrum'),
                   model_uri=DSS.vsource__spectrum, domain=None, range=Optional[str])

slots.vsource__basefreq = Slot(uri=DSS.basefreq, name="vsource__basefreq", curie=DSS.curie('basefreq'),
                   model_uri=DSS.vsource__basefreq, domain=None, range=Optional[float])

slots.vsource__enabled = Slot(uri=DSS.enabled, name="vsource__enabled", curie=DSS.curie('enabled'),
                   model_uri=DSS.vsource__enabled, domain=None, range=Optional[Union[bool, Bool]])

slots.vsource__like = Slot(uri=DSS.like, name="vsource__like", curie=DSS.curie('like'),
                   model_uri=DSS.vsource__like, domain=None, range=Optional[str])

