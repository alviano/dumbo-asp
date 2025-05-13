import pytest

from dumbo_asp.primitives.models import Model
from dumbo_asp.primitives.programs import SymbolicProgram
from dumbo_asp.primitives.templates import Template


def test_collect_argument():
    program = SymbolicProgram.parse("""
foo(1,2,3,4).
__apply_template__("@dumbo/collect argument 2 of 4", (input, foo), (output, output)).
    """)
    program = Template.expand_program(program)
    model = Model.of_program(program)
    assert model.filter(when=lambda atom: atom.predicate_name == "output") == Model.of_atoms("output(2)")


def test_exact_copy():
    program = SymbolicProgram.parse("""
foo(1).
bar(2).
__apply_template__("@dumbo/exact copy (arity 1)", (input, foo), (output, bar)).
    """)
    program = Template.expand_program(program)
    model = Model.of_program(program)
    assert '__debug__("@dumbo/exact copy (arity 1): unexpected ",bar(2)," without ",foo(2))' in model.as_facts


def test_debug_off():
    program = SymbolicProgram.parse("""
foo(1).
bar(2).
__apply_template__("@dumbo/exact copy (arity 1)", (input, foo), (output, bar)).
__apply_template__("@dumbo/debug off").
    """)
    program = Template.expand_program(program)
    model = Model.of_program(program)
    assert '__debug__("@dumbo/exact copy (arity 1): unexpected ",bar(2)," without ",foo(2))' not in model.as_facts


def test_fail_if_debug_messages():
    program = SymbolicProgram.parse("""
__debug__(1,2,3,4,5,6,7).
__apply_template__("@dumbo/fail if debug messages").
    """)
    program = Template.expand_program(program)
    with pytest.raises(Model.NoModelError):
        Model.of_program(program)
