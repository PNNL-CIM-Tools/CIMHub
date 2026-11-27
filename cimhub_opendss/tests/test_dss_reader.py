"""Tests for the DSS file reader (dss_name_map + dss_reader).

Covers:
  A. YAML-driven name mapping
  B. Parsing primitives (comment stripping, parameter tokenization)
  C. Type conversion (scalars, enums, arrays)
  D. Integration tests against the ieee13 test model
  E. GraphModel integration
"""
from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Locate test model directory
# ---------------------------------------------------------------------------
_TESTS_DIR = Path(__file__).parent
_MASTER_DSS = str(_TESTS_DIR / "decks" / "IEEE" / "IEEE13_CDPSM" / "IEEE13_CDPSM.dss")


# ===========================================================================
# A. Name mapping tests
# ===========================================================================

class TestDssNameMap:
    """Tests for dss_name_map module."""

    def test_load_class_map_pct_mean(self):
        """Load: '%mean' -> 'pct_mean'."""
        from cimhub_opendss.dss_name_map import get_class_map
        from cimhub_opendss.schema.opendss_schema import Load

        cm = get_class_map(Load)
        assert cm.param_to_field.get("%mean") == "pct_mean"

    def test_load_class_map_pct_stddev(self):
        """Load: '%stddev' -> 'pct_stddev'."""
        from cimhub_opendss.dss_name_map import get_class_map
        from cimhub_opendss.schema.opendss_schema import Load

        cm = get_class_map(Load)
        assert cm.param_to_field.get("%stddev") == "pct_stddev"

    def test_load_class_map_class_to_load_class(self):
        """Load: 'class' -> 'load_class' (dss_name annotation)."""
        from cimhub_opendss.dss_name_map import get_class_map
        from cimhub_opendss.schema.opendss_schema import Load

        cm = get_class_map(Load)
        assert cm.param_to_field.get("class") == "load_class"

    def test_load_class_map_seriesrl(self):
        """Load: '%seriesrl' -> 'pct_SeriesRL' (dss_name annotation)."""
        from cimhub_opendss.dss_name_map import get_class_map
        from cimhub_opendss.schema.opendss_schema import Load

        cm = get_class_map(Load)
        assert cm.param_to_field.get("%seriesrl") == "pct_SeriesRL"

    def test_transformer_class_map_pct_r(self):
        """Transformer: '%r' -> 'pct_R'."""
        from cimhub_opendss.dss_name_map import get_class_map
        from cimhub_opendss.schema.opendss_schema import Transformer

        cm = get_class_map(Transformer)
        assert cm.param_to_field.get("%r") == "pct_R"

    def test_case_insensitive_field_lookup(self):
        """Field lookup should be case-insensitive."""
        from cimhub_opendss.dss_name_map import get_class_map
        from cimhub_opendss.schema.opendss_schema import Load

        cm = get_class_map(Load)
        # All should resolve to the same field
        assert cm.param_to_field.get("bus1") == "bus1"
        assert cm.param_to_field.get("kv") == "kV"
        assert cm.param_to_field.get("kva") == "kVA"

    def test_enum_connection_type(self):
        """ConnectionType: 'wye', 'delta', 'y', 'ln', 'll' all resolve."""
        from cimhub_opendss.dss_name_map import get_class_map
        from cimhub_opendss.schema.opendss_schema import Load, ConnectionType

        cm = get_class_map(Load)
        enum_map = cm.enum_value_maps.get("conn", {})

        assert enum_map.get("wye") == ConnectionType.wye
        assert enum_map.get("delta") == ConnectionType.delta
        assert enum_map.get("y") == ConnectionType.wye
        assert enum_map.get("ln") == ConnectionType.wye
        assert enum_map.get("ll") == ConnectionType.delta

    def test_enum_load_model_by_number(self):
        """LoadModel: '1' -> ConstantPQ, '2' -> ConstantZ."""
        from cimhub_opendss.dss_name_map import get_class_map
        from cimhub_opendss.schema.opendss_schema import Load, LoadModel

        cm = get_class_map(Load)
        enum_map = cm.enum_value_maps.get("model", {})

        assert enum_map.get("1") == LoadModel.ConstantPQ
        assert enum_map.get("2") == LoadModel.ConstantZ
        assert enum_map.get("5") == LoadModel.ConstantI

    def test_type_registry_load(self):
        """'load' maps to Load class."""
        from cimhub_opendss.dss_name_map import build_type_registry
        from cimhub_opendss.schema.opendss_schema import Load

        registry = build_type_registry()
        assert registry.get("load") is Load

    def test_type_registry_circuit_alias(self):
        """'circuit' maps to Vsource class."""
        from cimhub_opendss.dss_name_map import build_type_registry
        from cimhub_opendss.schema.opendss_schema import Vsource

        registry = build_type_registry()
        assert registry.get("circuit") is Vsource

    def test_multivalued_detection(self):
        """Transformer buses, kVs, kVAs should be detected as multivalued."""
        from cimhub_opendss.dss_name_map import get_class_map
        from cimhub_opendss.schema.opendss_schema import Transformer

        cm = get_class_map(Transformer)
        # These should be in multivalued based on YAML multivalued: true
        assert "kVs" in cm.multivalued or "kvs" in {f.lower() for f in cm.multivalued}


# ===========================================================================
# B. Parsing primitive tests
# ===========================================================================

class TestParsingPrimitives:
    """Tests for comment stripping, tokenization, and parameter parsing."""

    def test_strip_comment_bang(self):
        """'New Load.x Bus1=a ! comment' -> 'New Load.x Bus1=a '."""
        from cimhub_opendss.dss_reader import _strip_comment

        result = _strip_comment('New Load.x Bus1=a ! comment')
        assert result.strip() == "New Load.x Bus1=a"

    def test_strip_comment_double_slash(self):
        """'New Load.x Bus1=a // comment' -> 'New Load.x Bus1=a '."""
        from cimhub_opendss.dss_reader import _strip_comment

        result = _strip_comment('New Load.x Bus1=a // comment')
        assert result.strip() == "New Load.x Bus1=a"

    def test_strip_comment_preserves_quoted_bang(self):
        """Quoted '!' should not be treated as comment."""
        from cimhub_opendss.dss_reader import _strip_comment

        result = _strip_comment('New Load.x name="a!b"')
        assert 'a!b' in result

    def test_strip_comment_no_comment(self):
        """Line without comment is returned unchanged."""
        from cimhub_opendss.dss_reader import _strip_comment

        line = 'New Load.x Bus1=671 kW=100'
        assert _strip_comment(line) == line

    def test_parse_params_simple(self):
        """Simple key=value pairs."""
        from cimhub_opendss.dss_reader import DssReader

        reader = DssReader("")
        params = dict(reader._parse_params("Bus1=671 Model=1 kV=4.16"))
        assert params["Bus1"] == "671"
        assert params["Model"] == "1"
        assert params["kV"] == "4.16"

    def test_parse_params_array_comma(self):
        """Comma-separated array in brackets."""
        from cimhub_opendss.dss_reader import DssReader

        reader = DssReader("")
        params = dict(reader._parse_params("kVs=[115, 4.16, 13.2]"))
        assert "kVs" in params
        assert "115" in params["kVs"]
        assert "4.16" in params["kVs"]

    def test_parse_params_array_space(self):
        """Space-separated array in brackets."""
        from cimhub_opendss.dss_reader import DssReader

        reader = DssReader("")
        params = dict(reader._parse_params("XSCArray=[ 0.00979 0.02491 0.02491]"))
        assert "XSCArray" in params
        assert "0.00979" in params["XSCArray"]

    def test_parse_params_mixed(self):
        """Mix of simple params and arrays."""
        from cimhub_opendss.dss_reader import DssReader

        reader = DssReader("")
        params = dict(reader._parse_params(
            "Phases=3 Windings=3 Buses=[sourcebus, 650, 650z, ] kVAs=[1000, 1000, 1000, ]"
        ))
        assert params["Phases"] == "3"
        assert params["Windings"] == "3"
        assert "sourcebus" in params["Buses"]
        assert "1000" in params["kVAs"]

    def test_parse_params_pct_prefix(self):
        """Parameters with % prefix."""
        from cimhub_opendss.dss_reader import DssReader

        reader = DssReader("")
        params = dict(reader._parse_params("%R=0.5 %Mean=50 %StdDev=10"))
        assert params["%R"] == "0.5"
        assert params["%Mean"] == "50"
        assert params["%StdDev"] == "10"


# ===========================================================================
# C. Type conversion tests
# ===========================================================================

class TestTypeConversion:
    """Tests for scalar/enum/array type conversion."""

    def test_convert_float(self):
        """String '4.16' -> float 4.16."""
        from cimhub_opendss.dss_reader import DssReader

        reader = DssReader("")
        result = reader._convert_scalar("4.16", float)
        assert isinstance(result, float)
        assert abs(result - 4.16) < 1e-9

    def test_convert_int_from_float_string(self):
        """String '3.0' -> int 3."""
        from cimhub_opendss.dss_reader import DssReader

        reader = DssReader("")
        result = reader._convert_scalar("3.0", int)
        assert isinstance(result, int)
        assert result == 3

    def test_convert_bool_yes(self):
        """'Yes' -> True."""
        from cimhub_opendss.dss_reader import DssReader

        reader = DssReader("")
        assert reader._convert_scalar("Yes", bool) is True
        assert reader._convert_scalar("No", bool) is False
        assert reader._convert_scalar("True", bool) is True
        assert reader._convert_scalar("False", bool) is False

    def test_parse_array_float(self):
        """'[115, 4.16, 13.2, ]' -> [115.0, 4.16, 13.2]."""
        from cimhub_opendss.dss_reader import DssReader
        from cimhub_opendss.dss_name_map import DssClassMap

        reader = DssReader("")
        # Use a minimal class_map just for the array test
        result = reader._parse_array(
            "[115, 4.16, 13.2, ]", "kVs", object, DssClassMap(object, "", {}, set(), {})
        )
        assert len(result) == 3
        assert abs(result[0] - 115.0) < 1e-9
        assert abs(result[1] - 4.16) < 1e-9
        assert abs(result[2] - 13.2) < 1e-9

    def test_parse_array_space_separated(self):
        """'[ 0.00979 0.02491 0.02491]' -> [0.00979, 0.02491, 0.02491]."""
        from cimhub_opendss.dss_reader import DssReader
        from cimhub_opendss.dss_name_map import DssClassMap

        reader = DssReader("")
        result = reader._parse_array(
            "[ 0.00979 0.02491 0.02491]", "XSCArray", object,
            DssClassMap(object, "", {}, set(), {})
        )
        assert len(result) == 3
        assert abs(result[0] - 0.00979) < 1e-9

    def test_parse_array_single_bracket(self):
        """'[ 400]' -> [400.0]."""
        from cimhub_opendss.dss_reader import DssReader
        from cimhub_opendss.dss_name_map import DssClassMap

        reader = DssReader("")
        result = reader._parse_array(
            "[ 400]", "Ratings", object,
            DssClassMap(object, "", {}, set(), {})
        )
        assert len(result) == 1
        assert abs(result[0] - 400.0) < 1e-9

    def test_parse_array_names_stay_text(self):
        """Numeric bus and wire names are names: '[XF1 634]' -> ['XF1', '634'], not 634.0."""
        from cimhub_opendss.dss_reader import DssReader
        from cimhub_opendss.dss_name_map import DssClassMap
        import cimhub_opendss.schema.opendss_schema as dss

        reader = DssReader("")
        class_map = DssClassMap(dss.Transformer, "", {}, set(), {})
        assert reader._parse_array("[XF1 634]", "buses", dss.Transformer, class_map) == ["XF1", "634"]
        assert reader._parse_array("[650.1.2.3.4, '799']", "buses", dss.Transformer, class_map) == ["650.1.2.3.4", "799"]

    def test_quotes_delimit_arrays(self, tmp_path):
        """IEEE37: conns='delta delta' kvs="4.8 4.8" are arrays, and like= copies them."""
        from cimhub_opendss.dss_reader import DssReader
        import cimhub_opendss.schema.opendss_schema as dss

        deck = tmp_path / "quoted.dss"
        deck.write_text("new transformer.reg1a phases=1 windings=2 buses=(799.1.2 799r.1.2) conns='delta delta' "
                        "kvs=\"4.8 4.8\" kvas=\"2000 2000\" XHL=1\n"
                        "new transformer.reg1c like=reg1a buses=(799.3.2 799r.3.2)\n")
        transformers = DssReader(deck).read_all().graph[dss.Transformer]
        for name in ("reg1a", "reg1c"):
            assert transformers[name].kVs == [4.8, 4.8]
            assert [str(conn) for conn in transformers[name].conns] == ["delta", "delta"]

    def test_neutral_impedance_after_arrays_is_the_last_windings(self, tmp_path):
        """Sub3 in array form: an array leaves the last winding active, so OpenDSS puts Rneut/Xneut on winding 3
        and leaves the 4.16 kV winding 2 ungrounded (its node 4 floats). The ``wdg=2`` form grounds winding 2."""
        from cimhub_opendss.dss_reader import DssReader
        import cimhub_opendss.schema.opendss_schema as dss

        deck = tmp_path / "arrays.dss"
        deck.write_text("new Transformer.Sub3 windings=3 buses=[SourceBus 650.1.2.3.4 650z] conns=[delta wye wye] "
                        "kVs=[115.0 4.16 13.2] kVAs=[5000.0 5000.0 1000.0] XHL=0.01 XHT=0.025 XLT=0.025 "
                        "%Rs=[0.0005 0.0005 0.0005] Rneut=0.0 Xneut=0.4\n")
        sub3 = DssReader(deck).read_all().graph[dss.Transformer]["Sub3"]
        assert (sub3.wdg, sub3.Rneut, sub3.Xneut) == (3, 0.0, 0.4)

    def test_blanks_around_equals(self, tmp_path):
        """4bus-OYOD-UnBal: '~ wdg=1 bus=... kv= 7.20 kva=2000' keeps the kV."""
        from cimhub_opendss.dss_reader import DssReader
        import cimhub_opendss.schema.opendss_schema as dss

        deck = tmp_path / "blanks.dss"
        deck.write_text("New Transformer.t Phases=1 Windings=2 Xhl=6\n"
                        "~ wdg=1 bus=a.1.0 conn=Wye kv= 7.20 kva=2000\n"
                        "~ wdg=2 bus=b.1.2 conn=Delta kv =4.16 kva = 2000\n")
        [transformer] = DssReader(deck).read_all().graph[dss.Transformer].values()
        assert transformer.kVs == [7.2, 4.16] and transformer.kVAs == [2000.0, 2000.0]

    def test_unbuildable_object_raises(self, tmp_path):
        from cimhub_opendss.dss_reader import DssParseError, DssReader

        deck = tmp_path / "bad.dss"
        deck.write_text("new transformer.t phases=1 windings=2 buses=[a b] conns=[wye zigzag]\n")
        with pytest.raises(DssParseError, match=r"transformer.t: conns='\[wye,zigzag\]': 'zigzag' is not one of .* at line 1"):
            DssReader(deck).read_all()


# ===========================================================================
# D. IEEE 13 integration tests
# ===========================================================================

@pytest.fixture(scope="module")
def model():
    """Every object in the ieee13 test model, parsed once.

    ``read_all`` parses the whole file tree in a single pass, so there is
    nothing to gain from re-reading per test — and module scope keeps these
    tests honest about the contract: read once, then query the graph by class.
    """
    from cimhub_opendss.dss_reader import DssReader

    return DssReader(_MASTER_DSS).read_all()


class TestIeee13Integration:
    """Integration tests against the ieee13 test model."""

    def test_read_loads(self, model):
        """Read all Load instances from ieee13."""
        from cimhub_opendss.schema.opendss_schema import Load

        assert model.count(Load) == 16

    def test_load_671_properties(self, model):
        """Check specific properties on Load.671."""
        from cimhub_opendss.schema.opendss_schema import Load, ConnectionType

        loads = model.list_by_class(Load)
        load_671 = next(load for load in loads if "671" in str(load.name))

        assert load_671.conn.code == ConnectionType.delta

    def test_load_634a_single_phase(self, model):
        """Load.634a should be single-phase wye."""
        from cimhub_opendss.schema.opendss_schema import Load, ConnectionType

        loads = model.list_by_class(Load)
        load_634a = next(load for load in loads if "634a" in str(load.name))

        assert load_634a.phases == 1
        assert load_634a.conn.code == ConnectionType.wye

    def test_read_lines(self, model):
        """Read all Line instances from ieee13."""
        from cimhub_opendss.schema.opendss_schema import Line

        assert model.count(Line) == 16  # 15 lines + switch Sect1

    def test_line_650632_properties(self, model):
        """Check properties on Line.650632."""
        from cimhub_opendss.schema.opendss_schema import Line

        lines = model.list_by_class(Line)
        line_650632 = next(line for line in lines if "650632" in str(line.name))

        assert str(line_650632.bus1).lower() == "rg60.1.2.3"
        assert str(line_650632.bus2).lower() == "632.1.2.3"
        assert line_650632.phases == 3
        assert abs(line_650632.length - 2000.0) < 0.01

    def test_read_transformers(self, model):
        """Read all Transformer instances from ieee13."""
        from cimhub_opendss.schema.opendss_schema import Transformer

        assert model.count(Transformer) == 6

    def test_transformer_sub3_multiwinding(self, model):
        """Transformer.sub3 should have 3 windings with array properties."""
        from cimhub_opendss.schema.opendss_schema import Transformer

        xfmrs = model.list_by_class(Transformer)
        sub3 = next(x for x in xfmrs if "sub3" in str(x.name).lower())

        assert sub3.phases == 3
        assert sub3.windings == 3

    def test_transformer_sub3_neutral_impedance_keeps_winding(self, model):
        """``Rneut``/``Xneut`` must keep the winding they were declared under.

        ieee13 defines Sub3 with per-winding continuation lines, and the neutral
        impedance appears on winding 2::

            ~ wdg=2 bus=650.1.2.3.4 Rneut=0 Xneut=0.4 conn=wye kv=4.16 ...

        Flattening those to bare scalars loses the binding: they are per-winding
        DSS properties, so on re-export with no ``wdg=`` OpenDSS applies them to
        the *last* winding and leaves the 4.16 kV secondary ungrounded.
        """
        from cimhub_opendss.schema.opendss_schema import Transformer

        xfmrs = model.list_by_class(Transformer)
        sub3 = next(x for x in xfmrs if "sub3" in str(x.name).lower())

        assert sub3.wdg == 2, f"Neutral impedance lost its winding: wdg={sub3.wdg}"
        assert sub3.Rneut == 0.0
        assert abs(sub3.Xneut - 0.4) < 1e-9
        assert ".1.2.3.4" in sub3.buses[1], (
            f"Winding 2 needs the neutral conductor, got {sub3.buses[1]}"
        )

    def test_read_capacitors(self, model):
        """Read all Capacitor instances from ieee13."""
        from cimhub_opendss.schema.opendss_schema import Capacitor

        assert model.count(Capacitor) == 2

    def test_capacitor_properties(self, model):
        """Check Capacitor.cap1 properties."""
        from cimhub_opendss.schema.opendss_schema import Capacitor

        caps = model.list_by_class(Capacitor)
        cap1 = next(c for c in caps if "cap1" in str(c.name).lower())

        assert cap1.phases == 3
        assert abs(cap1.kv - 4.16) < 0.01
        # kvar is multivalued, should be a list
        assert isinstance(cap1.kvar, list)
        assert len(cap1.kvar) == 1
        assert abs(cap1.kvar[0] - 600.0) < 0.01

    def test_read_vsource_with_edit(self, model):
        """Vsource.source should be created by 'New Circuit' and modified by 'Edit'."""
        from cimhub_opendss.schema.opendss_schema import Vsource

        vsources = model.list_by_class(Vsource)
        assert len(vsources) >= 1

        source = next(v for v in vsources if "source" in str(v.name))
        assert source.MVAsc3 == 20000.0
        assert source.basekv == 115.0

    def test_read_storage(self, model):
        """Read all Storage instances from ieee13."""
        from cimhub_opendss.schema.opendss_schema import Storage

        assert model.count(Storage) == 3

    def test_read_buscoords(self, model):
        """Bus coordinates come from a referenced CSV, not from a New command."""
        from cimhub_opendss.schema.opendss_schema import Buscoords

        coords = model.list_by_class(Buscoords)
        assert coords, "expected coordinates from the BusCoords directive"
        for bc in coords:
            assert bc.x is not None and bc.y is not None
            # Bus names are lower-cased on read: DSS bus names are
            # case-insensitive, so the graph key has to be too.
            assert str(bc.name) == str(bc.name).lower()

    def test_read_all_is_cached(self):
        """A second read_all() returns the same model, not a re-parse."""
        from cimhub_opendss.dss_reader import DssReader

        reader = DssReader(_MASTER_DSS)
        assert reader.read_all() is reader.read_all()

    def test_absent_class_returns_empty(self, model):
        """A class with no instances is simply absent from the graph."""
        from cimhub_opendss.schema.opendss_schema import Gicline

        assert model.list_by_class(Gicline) == []


# ===========================================================================
# E. GraphModel integration
# ===========================================================================

class TestGraphModelIntegration:
    """``read_all`` returns a GraphModel keyed by schema class."""

    def test_graph_model_counts(self, model):
        """Every parsed class is queryable by type."""
        from cimhub_opendss.schema.opendss_schema import Load, Line, Transformer

        assert model.count(Load) == 16
        assert model.count(Line) == 16  # 15 lines + switch Sect1
        assert model.count(Transformer) == 6

    def test_graph_model_retrieval(self, model):
        """Retrieved objects should have expected attributes."""
        from cimhub_opendss.schema.opendss_schema import Load

        loads = model.list_by_class(Load)

        assert len(loads) == 16
        for load in loads:
            assert hasattr(load, "name")
            assert hasattr(load, "bus1")
            assert load.name is not None


# ===========================================================================
# G. Auto-sanitization via DssReader
# ===========================================================================

class TestValuesVerbatim:
    """The reader keeps every value as the deck wrote it: no clamping, no defaults substituted."""

    @pytest.mark.parametrize("text, slot, expected", [
        ("New PVSystem.pv1 bus1=bus1 kVA=100 model=7", "model", 7),
        ("New PVSystem.pv1 bus1=bus1 kVA=100 pf=1.5", "pf", 1.5),
        ("New PVSystem.pv1 bus1=bus1 kVA=100 kv=-1.0", "kv", -1.0),
        ("New Load.ld1 bus1=bus1 kW=100 pf=-2.0", "pf", -2.0),
        ("New Linecode.lc nphases=4 r1=0.1", "nphases", 4),
    ])
    def test_out_of_range_value_is_kept(self, tmp_path, text, slot, expected):
        from cimhub_opendss.dss_reader import DssReader

        deck = tmp_path / "deck.dss"
        deck.write_text(text + "\n")
        [obj] = list(DssReader(deck).read_all().iter_all())
        assert getattr(obj, slot) == expected

class TestEdgeCases:
    """Edge case tests."""

    def test_missing_file_raises(self):
        """Reading a nonexistent Master.dss should raise FileNotFoundError.

        Construction stays cheap and side-effect-free, so the error surfaces
        from ``read_all``, not from ``__init__``.
        """
        from cimhub_opendss.dss_reader import DssReader

        reader = DssReader("/nonexistent/path/Master.dss")
        with pytest.raises(FileNotFoundError):
            reader.read_all()

    def test_empty_params(self):
        """Parsing empty parameter string returns no pairs."""
        from cimhub_opendss.dss_reader import DssReader

        reader = DssReader("")
        assert reader._parse_params("") == []
        assert reader._parse_params("  ") == []

    def test_continuation_line_joining(self):
        """Lines starting with ~ should be joined to predecessor."""
        from cimhub_opendss.dss_reader import DssReader

        reader = DssReader("")
        raw = [
            ("New Transformer.t1 phases=3", Path("t.dss"), 1),
            ("~ wdg=1 bus=a kv=115", Path("t.dss"), 2),
            ("~ wdg=2 bus=b kv=4.16", Path("t.dss"), 3),
        ]
        joined = reader._join_continuation_lines(raw)
        assert len(joined) == 1
        assert "wdg=1" in joined[0][0]
        assert "wdg=2" in joined[0][0]
