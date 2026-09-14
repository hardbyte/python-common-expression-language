"""The hand-written type stubs must describe the extension as it really is.

``python/cel/cel.pyi`` is maintained by hand, so it can drift from the PyO3
signatures. The consequence is nasty: a keyword call that satisfies the type
checker fails at runtime, or the working spelling fails to type-check. This
test parses the stub and compares every function and method signature it
declares against the runtime object, and checks that every public runtime
attribute is declared in the stub.
"""

import ast
import inspect
from pathlib import Path

import cel
import pytest

STUB_PATH = Path(cel.__file__).with_name("cel.pyi")


def _stub_module() -> ast.Module:
    return ast.parse(STUB_PATH.read_text(), filename=str(STUB_PATH))


def _parameter_names(node: ast.FunctionDef) -> list[str]:
    args = node.args
    names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
    return [n for n in names if n not in ("self", "cls")]


def _runtime_parameter_names(obj) -> list[str]:
    names = [p.name for p in inspect.signature(obj).parameters.values()]
    return [n for n in names if n not in ("self", "cls")]


def _stub_functions(module: ast.Module) -> dict[str, ast.FunctionDef]:
    return {n.name: n for n in module.body if isinstance(n, ast.FunctionDef)}


def _stub_classes(module: ast.Module) -> dict[str, ast.ClassDef]:
    return {n.name: n for n in module.body if isinstance(n, ast.ClassDef)}


def _is_property(node: ast.FunctionDef) -> bool:
    return any(isinstance(d, ast.Name) and d.id == "property" for d in node.decorator_list)


def _is_classmethod(node: ast.FunctionDef) -> bool:
    return any(isinstance(d, ast.Name) and d.id == "classmethod" for d in node.decorator_list)


@pytest.mark.parametrize("name", ["evaluate", "compile"])
def test_module_function_parameters_match_runtime(name):
    stub = _stub_functions(_stub_module())[name]
    assert _parameter_names(stub) == _runtime_parameter_names(getattr(cel, name))


@pytest.mark.parametrize(
    ("class_name", "method"),
    [
        ("Context", "__init__"),
        ("Context", "add_variable"),
        ("Context", "add_function"),
        ("Context", "set_variable_resolver"),
        ("Context", "update"),
        ("Program", "execute"),
        ("Program", "variables"),
        ("Program", "functions"),
        ("Program", "references"),
        ("OptionalValue", "of"),
        ("OptionalValue", "none"),
        ("OptionalValue", "has_value"),
        ("OptionalValue", "value"),
        ("OptionalValue", "or_value"),
        ("OptionalValue", "or_optional"),
    ],
)
def test_method_parameters_match_runtime(class_name, method):
    class_node = _stub_classes(_stub_module())[class_name]
    stub_methods = {n.name: n for n in class_node.body if isinstance(n, ast.FunctionDef)}
    stub = stub_methods[method]
    runtime_cls = getattr(cel, class_name)
    # PyO3 puts the constructor signature on the class itself; ``__init__`` is
    # the generic object slot wrapper.
    runtime = runtime_cls if method == "__init__" else getattr(runtime_cls, method)
    assert _parameter_names(stub) == _runtime_parameter_names(runtime), (
        f"{class_name}.{method}: stub declares {_parameter_names(stub)}, "
        f"runtime accepts {_runtime_parameter_names(runtime)}"
    )


@pytest.mark.parametrize("class_name", ["Context", "Program", "OptionalValue"])
def test_public_runtime_attributes_are_declared(class_name):
    """Every public method/property on the extension class appears in the stub."""
    class_node = _stub_classes(_stub_module())[class_name]
    declared = {n.name for n in class_node.body if isinstance(n, ast.FunctionDef)}
    runtime_cls = getattr(cel, class_name)
    public = {
        name
        for name, member in vars(runtime_cls).items()
        if not name.startswith("_")
        and (
            inspect.isroutine(member)
            or isinstance(member, (property, type(runtime_cls.__dict__.get("__init__"))))
            or type(member).__name__ in ("getset_descriptor", "method_descriptor")
        )
    }
    assert public <= declared, (
        f"{class_name} runtime members missing from stub: {public - declared}"
    )


@pytest.mark.parametrize(
    ("class_name", "attribute"),
    [("Context", "variables"), ("Context", "functions"), ("Program", "source")],
)
def test_properties_are_declared_as_properties(class_name, attribute):
    class_node = _stub_classes(_stub_module())[class_name]
    stub = {n.name: n for n in class_node.body if isinstance(n, ast.FunctionDef)}[attribute]
    assert _is_property(stub)
    assert isinstance(inspect.getattr_static(getattr(cel, class_name), attribute), property) or (
        type(inspect.getattr_static(getattr(cel, class_name), attribute)).__name__
        == "getset_descriptor"
    )


def test_optional_value_constructors_are_classmethods():
    class_node = _stub_classes(_stub_module())["OptionalValue"]
    stub = {n.name: n for n in class_node.body if isinstance(n, ast.FunctionDef)}
    assert _is_classmethod(stub["of"]) and _is_classmethod(stub["none"])
    # A PyO3 classmethod is a builtin bound to the class rather than a Python
    # ``method`` object, so check what it is bound to.
    assert cel.OptionalValue.of.__self__ is cel.OptionalValue
    assert cel.OptionalValue.none.__self__ is cel.OptionalValue
