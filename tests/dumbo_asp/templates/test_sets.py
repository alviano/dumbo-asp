from dumbo_asp.primitives.models import Model
from dumbo_asp.primitives.programs import SymbolicProgram
from dumbo_asp.primitives.templates import Template


def test_subsets():
    program = SymbolicProgram.parse("""
in_set(1,s1).
in_set(1,s2).
in_set(2,s2).
in_set(1,s3).
in_set(2,s3).
__apply_template__("@dumbo/collect argument 2 of 2", (input, in_set), (output, set)).
__apply_template__("@dumbo/subsets").
    """)
    program = Template.expand_program(program)
    model = Model.of_program(program)
    assert len(model.filter(when=lambda atom: atom.predicate_name == "subset")) == 4


def test_supersets():
    program = SymbolicProgram.parse("""
in_set(1,s1).
in_set(1,s2).
in_set(2,s2).
in_set(1,s3).
in_set(2,s3).
__apply_template__("@dumbo/collect argument 2 of 2", (input, in_set), (output, set)).
__apply_template__("@dumbo/supersets").
    """)
    program = Template.expand_program(program)
    model = Model.of_program(program)
    assert len(model.filter(when=lambda atom: atom.predicate_name == "superset")) == 4


def test_strict_subsets():
    program = SymbolicProgram.parse("""
in_set(1,s1).
in_set(1,s2).
in_set(2,s2).
in_set(1,s3).
in_set(2,s3).
__apply_template__("@dumbo/collect argument 2 of 2", (input, in_set), (output, set)).
__apply_template__("@dumbo/strict subsets").
    """)
    program = Template.expand_program(program)
    model = Model.of_program(program)
    assert len(model.filter(when=lambda atom: atom.predicate_name == "subset")) == 2


def test_strict_supersets():
    program = SymbolicProgram.parse("""
in_set(1,s1).
in_set(1,s2).
in_set(2,s2).
in_set(1,s3).
in_set(2,s3).
__apply_template__("@dumbo/collect argument 2 of 2", (input, in_set), (output, set)).
__apply_template__("@dumbo/strict supersets").
    """)
    program = Template.expand_program(program)
    model = Model.of_program(program)
    assert len(model.filter(when=lambda atom: atom.predicate_name == "superset")) == 2


def test_discard_duplicate_sets():
    program = SymbolicProgram.parse("""
in_set(1,s1).
in_set(2,s1).
in_set(3,s1).
in_set(1,s2).
in_set(2,s2).
in_set(3,s2).
in_set(1,s3).
in_set(2,s3).
__apply_template__("@dumbo/collect argument 2 of 2", (input, in_set), (output, set)).
__apply_template__("@dumbo/discard duplicate sets").
    """)
    program = Template.expand_program(program)
    model = Model.of_program(program)
    assert len(model.filter(when=lambda atom: atom.predicate_name == "unique")) == 2
