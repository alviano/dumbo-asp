import pytest

from dumbo_asp.primitives.models import Model
from dumbo_asp.primitives.programs import SymbolicProgram
from dumbo_asp.primitives.templates import Template


def test_template_for_tc_from_core_lib():
    program = Template.expand_program(SymbolicProgram.parse("""
link(a,b).
link(b,a).
__apply_template__("@dumbo/transitive closure", (relation, link), (closure, link)).
    """.strip()))
    assert Model.of_program(program) == Model.of_atoms("link(a,b) link(b,a) link(a,a) link(b,b)".split())


def test_template_for_transitive_closure_guaranteed():
    program = Template.expand_program(SymbolicProgram.parse("""
link(a,b).
link(b,a).
__apply_template__("@dumbo/transitive closure guaranteed", (relation, link), (closure, link)).
    """.strip()))
    assert Model.of_program(program).filter(when=lambda atom: atom.predicate_name == "link") == \
           Model.of_atoms("link(a,b) link(b,a) link(a,a) link(b,b)".split())

    program = Template.expand_program(SymbolicProgram.parse("""
link(a,b).
closure(a,a).
__apply_template__("@dumbo/transitive closure guaranteed", (relation, link)).
__apply_template__("@dumbo/fail if debug messages").
    """.strip()))
    with pytest.raises(Model.NoModelError):
        Model.of_program(program)


def test_template_reflexive_closure():
    program = Template.expand_program(SymbolicProgram.parse("""
element(a).
element(b).
link(a,b).
__apply_template__("@dumbo/reflexive closure", (relation, link), (closure, link)).
    """.strip()))
    assert Model.of_program(program) == Model.of_atoms("element(a) element(b) link(a,b) link(a,a) link(b,b)".split())
