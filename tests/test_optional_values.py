import cel
import pytest


def empty_context():
    return cel.Context()


def test_optional_of_wrapper():
    opt = cel.evaluate("optional.of(42)", empty_context())
    assert isinstance(opt, cel.OptionalValue)
    assert opt.has_value() is True
    assert opt.value() == 42
    assert opt.or_value(0) == 42
    assert bool(opt) is True


def test_optional_none_wrapper():
    opt = cel.evaluate("optional.none()", empty_context())
    assert isinstance(opt, cel.OptionalValue)
    assert opt.has_value() is False
    assert opt.or_value("default") == "default"
    assert bool(opt) is False
    with pytest.raises(ValueError, match="optional.none"):
        opt.value()


def test_optional_of_null_distinct():
    opt = cel.evaluate("optional.of(null)", empty_context())
    assert isinstance(opt, cel.OptionalValue)
    assert opt.has_value() is True
    assert opt.value() is None
    assert opt.or_value("default") is None


def test_optional_in_context():
    context = cel.Context()
    opt = cel.OptionalValue.of(123)
    context.add_variable("opt", cel.prepare(opt))
    assert cel.evaluate("opt.orValue(0)", context) == 123
    assert cel.evaluate("opt.hasValue()", context) is True

    none_opt = cel.OptionalValue.none()
    context.add_variable("opt", cel.prepare(none_opt))
    assert cel.evaluate("opt.orValue(7)", context) == 7
    assert cel.evaluate("opt.hasValue()", context) is False
