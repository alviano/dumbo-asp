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
