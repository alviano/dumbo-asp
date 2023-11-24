from dumbo_asp.primitives.terms import SymbolicTerm


def test_symbolic_term_parse():
    assert str(SymbolicTerm.parse("1")) == "1"


def test_symbolic_term_string():
    term = SymbolicTerm.parse('"foo"')
    assert term.is_string()
    assert str(term) == '"foo"'


def test_symbolic_term_function():
    term = SymbolicTerm.parse("foo(bar)")
    assert term.is_function()
    assert term.function_name == "foo"
    assert term.function_arity == 1


def test_symbolic_term_int():
    term = SymbolicTerm.parse("123")
    assert term.is_int()
    assert term.int_value() == 123
