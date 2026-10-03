import time

from apps.core.ids import uuid7


def test_version_and_variant():
    value = uuid7()
    assert value.version == 7
    assert value.variant == "specified in RFC 4122"


def test_ids_from_different_milliseconds_sort_by_time():
    first = uuid7()
    time.sleep(0.002)
    second = uuid7()
    assert first < second


def test_ids_are_unique():
    assert len({uuid7() for _ in range(10_000)}) == 10_000
