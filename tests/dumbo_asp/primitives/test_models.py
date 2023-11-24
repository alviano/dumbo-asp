from builtins import ValueError

import clingo
import clingo.ast
import pytest

from dumbo_asp.primitives.models import Model
from dumbo_asp.primitives.parsers import Parser
from dumbo_asp.primitives.predicates import Predicate


@pytest.mark.parametrize("atoms", [
    ["a", "b", "c"],
    ["a", "-b", "c"],
    ["a(1)", "a(2)", "a(b)"],
])
def test_valid_model_of_atoms(atoms):
    assert len(Model.of_atoms(atoms)) == len(atoms)
    assert len(Model.of_atoms(*atoms)) == len(atoms)


@pytest.mark.parametrize("atoms", [
    ["\"a\"", "b", "c"],
    ["a", "not b", "c"],
    ["a(X)", "a(2)", "a(b)"],
])
def test_invalid_model_of_atoms(atoms):
    with pytest.raises(ValueError):
        Model.of_atoms(atoms)


def test_model_of_empty_program():
    assert len(Model.of_program("")) == 0


def test_model_drop():
    assert len(Model.of_atoms("a(1)", "a(1,2)", "b(1)", "c(2)").drop(Predicate.parse("b"))) == 3
    assert len(Model.of_atoms("a(1)", "a(1,2)", "b(1)", "c(2)").drop(Predicate.parse("a"))) == 2
    assert len(Model.of_atoms("a(1)", "a(1,2)", "b(1)", "c(2)").drop(Predicate.parse("a/2"))) == 3
    assert len(Model.of_elements("a(1)", "1", '"a(1)"').drop(Predicate.parse("a/1"))) == 2
    assert len(Model.of_elements("a(1)", "1", 2, '"a(1)"').drop(numbers=True)) == 3
    assert len(Model.of_elements("a(1)", "1", 2, '"a(1)"').drop(numbers=True, strings=True)) == 1


def test_model_of_control():
    control = clingo.Control()
    control.add("base", [], "c. a. b.")
    control.ground([("base", [])])
    model = Model.of_control(control)
    assert len(model) == 3
    assert model[0].predicate == Predicate.parse("a/0")
    assert model[1].predicate == Predicate.parse("b/0")
    assert model[2].predicate == Predicate.parse("c/0")


def test_model_of_control_with_show_numbers():
    control = clingo.Control()
    control.add("base", [], "#show 1.")
    control.ground([("base", [])])
    model = Model.of_control(control)
    assert len(model) == 1
    assert model[0] == 1


def test_no_model():
    control = clingo.Control()
    control.add("base", [], "a :- not a.")
    control.ground([("base", [])])
    with pytest.raises(ValueError):
        Model.of_control(control)


def test_model_of_control_cannot_be_used_for_more_than_one_model():
    control = clingo.Control(["0"])
    control.add("base", [], "{a}.")
    control.ground([("base", [])])
    with pytest.raises(ValueError):
        Model.of_control(control)


def test_model_as_facts():
    assert Model.of_atoms("a", "b", "c").as_facts == "a.\nb.\nc."


def test_model_block_up():
    assert Model.of_atoms("a", "b").block_up == ":- a, b."


def test_model_project():
    assert Model.of_atoms("a(1,2,3)").project(Predicate.parse("a/3"), 1).as_facts == "a(2,3)."


def test_model_substitute():
    assert Model.of_atoms("a(1,2,3)").substitute(Predicate.parse("a/3"), 1, Parser.parse_ground_term("5")).as_facts == \
           "a(5,2,3)."


def test_model_of_elements():
    assert Model.of_elements(1, "2", "\"3\"").as_facts == """
__number(1).
__string(\"2\").
__string(\"3\").
    """.strip()
