import pytest

from dumbo_asp.primitives.atoms import GroundAtom, SymbolicAtom


@pytest.mark.parametrize("atom", [
    "foo(",
    "foo(1,)",
    "foo(_)",
    "foo(X)",
    "foo(1) bar(2)",
])
def test_invalid_ground_atom(atom):
    with pytest.raises(ValueError):
        GroundAtom.parse(atom)


@pytest.mark.parametrize("atom", [
    "foo",
    "foo(1)",
    "foo(x)",
])
def test_valid_ground_atom(atom):
    assert GroundAtom.parse(atom).predicate.name == atom.split('(')[0]


def test_ground_atom_order():
    assert GroundAtom.parse("a(1)") < GroundAtom.parse("a(2)")
    assert GroundAtom.parse("a(b)") > GroundAtom.parse("a(2)")
    assert GroundAtom.parse("a(b)") > GroundAtom.parse("a(a)")
    assert GroundAtom.parse("a(b)") > GroundAtom.parse("a(\"a\")")
    assert GroundAtom.parse("c(\"b\")") < GroundAtom.parse("c(a)")
    assert GroundAtom.parse("a(-1)") < GroundAtom.parse("a(0)")
    assert GroundAtom.parse("a(-a)") < GroundAtom.parse("a(a)")


def test_symbolic_atom_match():
    atom1 = SymbolicAtom.parse("foo(bar)")
    atom2 = SymbolicAtom.parse("foo(X)")
    assert atom1.match(atom2)


def test_symbolic_atom_match_nested():
    atom1 = SymbolicAtom.parse("foo(bar(buzz))")
    atom2 = SymbolicAtom.parse("foo(bar(X))")
    assert atom1.match(atom2)

