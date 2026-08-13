import datetime
from collections import UserDict

import cel
import pytest


def execute_value(value):
    context = cel.Context()
    context.add_variable("value", cel.prepare(value))
    return cel.compile("value").execute(context)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (None, None),
        (False, False),
        (42, 42),
        (2**63, 2**63),
        (3.5, 3.5),
        ("hello", "hello"),
        (b"hello", b"hello"),
        ([1, "two", None], [1, "two", None]),
        ((1, 2, 3), [1, 2, 3]),
        ({"nested": {"values": [1, 2]}}, {"nested": {"values": [1, 2]}}),
        (UserDict({"answer": 42}), {"answer": 42}),
        (datetime.timedelta(seconds=90), datetime.timedelta(seconds=90)),
    ],
)
def test_prepare_supported_values(source, expected):
    assert execute_value(source) == expected


def test_prepare_signed_and_unsigned_range_boundaries():
    assert execute_value(-(2**63)) == -(2**63)
    assert execute_value(2**63 - 1) == 2**63 - 1
    assert execute_value(2**64 - 1) == 2**64 - 1


def test_prepare_bytes_and_nested_tuple_snapshot():
    source = (b"payload", {"items": (1, 2)})
    prepared = cel.prepare(source)
    context = cel.Context()
    context.add_variable("data", prepared)
    assert cel.compile("data[0]").execute(context) == b"payload"
    assert cel.compile("data[1].items[1]").execute(context) == 2


def test_prepare_dict_subclass_uses_mapping_protocol():
    class DictSubclass(dict):
        def __getitem__(self, key):
            if key == "dynamic":
                return 42
            return super().__getitem__(key)

        def keys(self):
            return ["dynamic"]

    assert execute_value(DictSubclass()) == {"dynamic": 42}


def test_prepare_datetime_values():
    aware = datetime.datetime(2024, 1, 2, 3, 4, tzinfo=datetime.timezone.utc)
    assert execute_value(aware) == aware

    naive = datetime.datetime(2024, 1, 2, 3, 4)
    result = execute_value(naive)
    assert result.replace(tzinfo=None) == naive


def test_prepare_optional_values():
    value = cel.OptionalValue.of({"answer": 42})
    result = execute_value(value)
    assert isinstance(result, cel.OptionalValue)
    assert result.value() == {"answer": 42}

    result = execute_value(cel.OptionalValue.none())
    assert isinstance(result, cel.OptionalValue)
    assert result.has_value() is False


def test_prepare_is_a_snapshot_and_survives_source_deletion():
    source = {"objects": [{"enabled": True}]}
    prepared = cel.prepare(source)
    source["objects"][0]["enabled"] = False
    source["objects"].append({"enabled": False})
    del source

    context = cel.Context()
    context.add_variable("data", prepared)
    assert cel.compile("data.objects[0].enabled").execute(context) is True
    assert cel.compile("size(data.objects)").execute(context) == 1


def test_prepared_value_is_reusable_and_prepare_is_idempotent():
    prepared = cel.prepare({"answer": 42})
    prepared_again = cel.prepare(prepared)

    first = cel.Context()
    second = cel.Context()
    first.add_variable("data", prepared)
    second.add_variable("data", prepared_again)

    program = cel.compile("data.answer")
    assert program.execute(first) == 42
    assert program.execute(second) == 42


def test_prepared_repr_is_opaque():
    secret = "do-not-render-this-payload"
    prepared = cel.prepare({"secret": secret, "items": list(range(100))})
    representation = repr(prepared)
    assert "PreparedValue" in representation
    assert secret not in representation
    assert "99" not in representation


def test_unsupported_values_fail_during_prepare():
    with pytest.raises(ValueError, match="Failed to prepare"):
        cel.prepare(object())

    with pytest.raises(ValueError, match="Failed to prepare"):
        cel.prepare(lambda: None)


def test_prepared_value_has_no_public_constructor():
    with pytest.raises(TypeError):
        cel.PreparedValue()
