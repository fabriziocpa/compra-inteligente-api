from dataclasses import dataclass
from uuid import uuid4

from src.shared.domain.entity import AggregateRoot, Entity
from src.shared.domain.events import DomainEvent


@dataclass(eq=False)
class _Foo(Entity):
    pass


@dataclass(eq=False)
class _Bar(Entity):
    pass


@dataclass(eq=False)
class _Agg(AggregateRoot):
    pass


def test_entity_equality_uses_id_only() -> None:
    eid = uuid4()
    a = _Foo(id=eid)
    b = _Foo(id=eid)
    assert a == b
    assert hash(a) == hash(b)


def test_entity_inequality_when_different_id() -> None:
    a = _Foo()
    b = _Foo()
    assert a != b


def test_entity_inequality_across_types() -> None:
    eid = uuid4()
    assert _Foo(id=eid) != _Bar(id=eid)


def test_touch_updates_updated_at() -> None:
    e = _Foo()
    original = e.updated_at
    e.touch()
    assert e.updated_at >= original


def test_aggregate_records_and_pulls_events() -> None:
    agg = _Agg()
    ev = DomainEvent()
    agg.record_event(ev)
    pulled = agg.pull_events()
    assert pulled == [ev]
    assert agg.pull_events() == []
