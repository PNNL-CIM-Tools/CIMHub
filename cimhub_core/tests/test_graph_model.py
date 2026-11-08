"""Unit tests for GraphModel — the format-agnostic {type: {id: obj}} store."""

from dataclasses import dataclass


from cimhub_core import GraphModel


@dataclass
class Bus:
    name: str
    kv: float = 0.0


@dataclass
class Branch:
    name: str


def test_from_objects_groups_by_class():
    model = GraphModel.from_objects([Bus("b1"), Bus("b2"), Branch("l1")])

    assert len(model.list_by_class(Bus)) == 2
    assert len(model.list_by_class(Branch)) == 1


def test_from_objects_empty():
    assert len(GraphModel.from_objects([])) == 0


def test_from_objects_matches_add_to_graph():
    """The classmethod is exactly the add_to_graph loop it replaces."""
    objects = [Bus("b1"), Branch("l1"), Bus("b2")]

    manual = GraphModel()
    for obj in objects:
        manual.add_to_graph(obj)

    assert GraphModel.from_objects(objects).graph == manual.graph


def test_from_objects_accepts_a_generator():
    model = GraphModel.from_objects(Bus(f"b{i}") for i in range(3))
    assert len(model.list_by_class(Bus)) == 3


def test_from_objects_drops_duplicate_identifiers(caplog):
    """Identifier collisions keep the first object and warn — they lose data.

    Callers building a model from a flat list need to know this happens; see the
    distopf CapacitorRecord case where same-bus banks share an id.
    """
    first, dupe = Bus("b1", kv=12.47), Bus("b1", kv=4.16)

    model = GraphModel.from_objects([first, dupe])

    assert len(model.list_by_class(Bus)) == 1
    assert model.list_by_class(Bus)[0].kv == 12.47
    assert "already in graph" in caplog.text


def test_list_by_class_sorted_by_identifier():
    model = GraphModel.from_objects([Bus("b3"), Bus("b1"), Bus("b2")])
    assert [b.name for b in model.list_by_class(Bus)] == ["b1", "b2", "b3"]


def test_list_by_class_absent_class_is_empty():
    assert GraphModel.from_objects([Bus("b1")]).list_by_class(Branch) == []


def test_contains_and_count():
    model = GraphModel.from_objects([Bus("b1"), Bus("b2")])

    assert Bus in model
    assert Branch not in model
    assert model.count(Bus) == 2
    assert model.count(Branch) == 0


def test_first_and_next():
    model = GraphModel.from_objects([Bus("b1"), Bus("b2")])

    assert model.first(Bus).name == "b1"
    assert model.next(Bus).name == "b2"


def test_first_on_absent_class_is_none():
    assert GraphModel.from_objects([Bus("b1")]).first(Branch) is None


def test_find_by_attribute():
    model = GraphModel.from_objects([Bus("b1", kv=12.47), Bus("b2", kv=4.16)])

    found = model.find_by_attribute(Bus, "kv", 4.16)
    assert [b.name for b in found] == ["b2"]


def test_iter_all_yields_every_object():
    model = GraphModel.from_objects([Bus("b1"), Branch("l1"), Bus("b2")])
    assert sorted(o.name for o in model.iter_all()) == ["b1", "b2", "l1"]
