"""Tests for compiled-program static analysis (Program.references)."""

import cel


class TestProgramReferences:
    """Program.variables(), .functions(), .references() and .source."""

    def test_variables_simple(self):
        program = cel.compile("a + b * c")
        assert program.variables() == ["a", "b", "c"]

    def test_variables_deduplicated_and_sorted(self):
        program = cel.compile("x + x + y")
        assert program.variables() == ["x", "y"]

    def test_variables_from_member_access(self):
        # Only the root identifier is a variable; field names are not.
        program = cel.compile("user.profile.name")
        assert program.variables() == ["user"]

    def test_no_variables_for_literal(self):
        program = cel.compile("1 + 2")
        assert program.variables() == []

    def test_functions_includes_named_and_operators(self):
        program = cel.compile("size(items) > 0")
        functions = program.functions()
        assert "size" in functions
        # Operators are reported using their CEL overload identifiers.
        assert "_>_" in functions

    def test_functions_for_macro(self):
        program = cel.compile("[1, 2, 3].map(x, x * 2)")
        # The comprehension variable is reported as a referenced variable.
        assert "x" in program.variables()

    def test_references_dict(self):
        program = cel.compile("user.age >= min_age && size(roles) > 0")
        refs = program.references()
        assert set(refs.keys()) == {"variables", "functions"}
        assert refs["variables"] == ["min_age", "roles", "user"]
        assert "size" in refs["functions"]

    def test_references_match_helper_methods(self):
        program = cel.compile("a + f(b)")
        refs = program.references()
        assert refs["variables"] == program.variables()
        assert refs["functions"] == program.functions()

    def test_source_getter(self):
        source = "a + b"
        program = cel.compile(source)
        assert program.source == source

    def test_repr(self):
        program = cel.compile("1 + 1")
        assert repr(program) == 'Program("1 + 1")'

    def test_references_use_case_validate_context(self):
        """Static analysis can validate that a context supplies all variables."""
        program = cel.compile("price * quantity")
        provided = {"price": 10, "quantity": 3}
        missing = [v for v in program.variables() if v not in provided]
        assert missing == []
        assert program.execute(provided) == 30
