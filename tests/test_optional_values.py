import cel
import pytest


def test_optional_of_wrapper():
    opt = cel.evaluate("optional.of(42)")
    assert isinstance(opt, cel.OptionalValue)
    assert opt.has_value() is True
    assert opt.value() == 42
    assert opt.or_value(0) == 42
    assert bool(opt) is True


def test_optional_none_wrapper():
    opt = cel.evaluate("optional.none()")
    assert isinstance(opt, cel.OptionalValue)
    assert opt.has_value() is False
    assert opt.or_value("default") == "default"
    assert bool(opt) is False
    with pytest.raises(ValueError, match="optional.none"):
        opt.value()


def test_optional_of_null_distinct():
    opt = cel.evaluate("optional.of(null)")
    assert isinstance(opt, cel.OptionalValue)
    assert opt.has_value() is True
    assert opt.value() is None
    assert opt.or_value("default") is None


def test_optional_in_context():
    opt = cel.OptionalValue.of(123)
    assert cel.evaluate("opt.orValue(0)", {"opt": opt}) == 123
    assert cel.evaluate("opt.hasValue()", {"opt": opt}) is True

    none_opt = cel.OptionalValue.none()
    assert cel.evaluate("opt.orValue(7)", {"opt": none_opt}) == 7
    assert cel.evaluate("opt.hasValue()", {"opt": none_opt}) is False
